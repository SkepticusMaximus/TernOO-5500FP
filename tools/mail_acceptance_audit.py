#!/usr/bin/env python3
"""Hermetic-mail ACCEPTANCE AUDIT — CF5 spec §10.

Runs the REAL components (keyholder, wire, mailbox) and asserts every security property the
system claims. It is deliberately adversarial: it forges, re-seals, and greps for plaintext.

    exit 0  -> every property holds
    exit 1  -> a property FAILED (printed)

This is the gate an outside auditor or CI runs. It does NOT touch the live wire or any real
keys — every check builds throwaway keyholders and temp dirs.

    python3 tools/mail_acceptance_audit.py            # full audit
    python3 tools/mail_acceptance_audit.py -q         # summary only
"""
import glob
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import keyholder as K
from hermetic_wire import Wire
from hermetic_mailbox import HermeticMailbox

CHECKS = []


def check(title):
    def deco(fn):
        CHECKS.append((title, fn))
        return fn
    return deco


def seats(*names):
    return {n: K.Keyholder(n) for n in names}


# ── the properties ────────────────────────────────────────────────────────────────────
@check("§10.1 encrypt-to-recipient: a sealed letter opens ONLY for its addressees (+ sender)")
def c1():
    s = seats("Stevo", "CC", "CCC", "CF5", "CAI", "Professor")
    cards = {k.aid: k.card() for k in s.values()}
    env, _ = s["CC"].seal([s["CCC"].card()], "x", "eyes only CCC")
    openers = sorted(n for n, k in s.items() if k.open(env, cards)[0] == "ok")
    assert openers == ["CC", "CCC"], "opened for %s" % openers
    return "opened only for CC (sender self-copy) + CCC; the other 4 got not-for-us"


@check("§10.2 no override: NO key reads a letter it is not party to — captain included")
def c2():
    s = seats("Stevo", "CC", "CCC", "CF5", "CAI", "Professor")
    cards = {k.aid: k.card() for k in s.values()}
    env, _ = s["CF5"].seal([s["CAI"].card()], "x", "CF5 to CAI, private")
    for n in ("Stevo", "CC", "CCC", "Professor"):               # every non-party, incl. the captain
        st = s[n].open(env, cards)[0]
        assert st != "ok", "%s could open a CF5->CAI letter (status %s)" % (n, st)
    assert s["Stevo"].open(env, cards)[0] == "not-for-us"
    return "CF5->CAI letter is unreadable to Stevo/CC/CCC/Professor — there is no master key"


@check("§10.3 authenticity: a forged sender (from=Stevo, signed by CF5) is REJECTED")
def c3():
    import hashlib
    s = seats("Stevo", "CC", "CF5")
    cards = {k.aid: k.card() for k in s.values()}
    msg = {"v": 1, "from": s["Stevo"].aid, "to": [s["CC"].aid], "subject": "x",
           "body": "forged order", "time": 0, "id": "f", "in_reply_to": None}
    m = K._canon(msg)
    sig = s["CF5"].sign_priv.sign(K.SIG_CONTEXT + hashlib.sha256(m).digest())   # CF5 signs as 'Stevo'
    framed = len(sig).to_bytes(2, "big") + sig + m
    padded = len(framed).to_bytes(4, "big") + framed + b"\x00" * (K.MIN_PAD - len(framed) - 4)
    import pyrage
    from pyrage import x25519
    rc = [x25519.Recipient.from_str(s["CC"].card()["enc"][0])]
    while len(rc) % K.STANZA_MULTIPLE:
        rc.append(x25519.Identity.generate().to_public())
    st = s["CC"].open(pyrage.encrypt(padded, rc), cards)[0]
    assert st == "reject-badsig", "forgery not rejected (status %s)" % st
    return "signature over the sender's key fails -> reject-badsig; you can't spoof a sender"


@check("§10.4 non-malleability: a sealed letter re-sealed to a new recipient is REJECTED")
def c4():
    import pyrage
    from pyrage import x25519
    s = seats("CC", "CCC", "CAI")
    cards = {k.aid: k.card() for k in s.values()}
    env, _ = s["CC"].seal([s["CCC"].card()], "x", "for CCC")
    padded = pyrage.decrypt(env, [s["CCC"].enc_priv])           # CCC unwraps, tries to re-seal to CAI
    rc = [x25519.Recipient.from_str(s["CAI"].card()["enc"][0])]
    while len(rc) % K.STANZA_MULTIPLE:
        rc.append(x25519.Identity.generate().to_public())
    st = s["CAI"].open(pyrage.encrypt(padded, rc), cards)[0]
    assert st == "reject-notaddressed", "re-seal accepted (status %s)" % st
    return "the inner `to` list is signed, so a re-wrapped letter -> reject-notaddressed"


@check("§10.5 no plaintext in the sealed envelope bytes")
def c5():
    s = seats("CC", "CCC")
    env, _ = s["CC"].seal([s["CCC"].card()], "secret-subject", "secret-body-xyzzy")
    assert b"secret-body-xyzzy" not in env and b"secret-subject" not in env
    return "known subject + body do not appear anywhere in the ciphertext"


@check("§10.6 no plaintext on the WIRE: the git host cannot grep it from any revision")
def c6():
    root = tempfile.mkdtemp()
    bare = os.path.join(root, "wire.git")
    subprocess.run(["git", "init", "--bare", "-q", "-b", "master", bare], check=True)

    def clone(name):
        p = os.path.join(root, name)
        subprocess.run(["git", "clone", "-q", bare, p], check=True, capture_output=True)
        subprocess.run(["git", "-C", p, "config", "user.email", "x@ternoo"], check=True)
        subprocess.run(["git", "-C", p, "config", "user.name", name], check=True)
        return Wire(p)
    s = seats("CC", "CCC")
    cc, ccc = clone("CC"), clone("CCC")
    cc.publish_card(s["CC"]); cc.publish_card(s["CCC"])
    cc.post(s["CC"], [s["CCC"].card()], "sync", "PLAINTEXT-NEEDLE-42")
    cc.sync()
    leak = subprocess.run(
        "cd %s && git rev-list --all 2>/dev/null | xargs -I{} git grep -a -l PLAINTEXT-NEEDLE-42 {} 2>/dev/null" % bare,
        shell=True, capture_output=True, text=True).stdout.strip()
    assert not leak, "plaintext found in the bare repo history: %s" % leak
    ccc.sync()
    assert any(m["body"] == "PLAINTEXT-NEEDLE-42" for m in ccc.fetch(s["CCC"]))   # but CCC can read it
    return "the needle is unfindable in every git revision of the host, yet CCC opens it fine"


@check("§10.7 cards self-certify; a tampered card is rejected")
def c7():
    k = K.Keyholder("CC")
    card = k.card()
    assert K.verify_card(card), "a good card failed to verify"
    bad = dict(card); bad["display"] = "CC-the-impostor"      # tamper after signing
    assert not K.verify_card(bad), "a tampered card verified"
    bad2 = dict(card); bad2["aid"] = "aid_" + "0" * 24         # AID not == digest(sign key)
    assert not K.verify_card(bad2), "a card with a forged AID verified"
    return "AID == sha256(signing key) and the self-signature binds display/enc/sign; tampering is caught"


@check("§10.8 recipient count hidden: stanza count padded to a multiple of 8, sizes bucketed")
def c8():
    s = seats("Stevo", "CC", "CCC", "CF5", "CAI", "Professor")
    one, _ = s["CC"].seal([s["CCC"].card()], "x", "one to one")
    allc, _ = s["Stevo"].seal([k.card() for n, k in s.items() if n != "Stevo"], "x", "one to all")
    n1 = one.count(b"-> X25519") or one.count(b"X25519")
    nA = allc.count(b"-> X25519") or allc.count(b"X25519")
    assert n1 % K.STANZA_MULTIPLE == 0 and nA % K.STANZA_MULTIPLE == 0, (n1, nA)
    return "1-recipient envelope has %d stanzas, 6-recipient has %d — both multiples of 8" % (n1, nA)


@check("§10.9 mailbox: the captain's inbox excludes a letter he is not party to")
def c9():
    wdir = tempfile.mkdtemp()
    cc, ccc, stevo = K.Keyholder("CC"), K.Keyholder("CCC"), K.Keyholder("Stevo")
    boxes = {k.display: HermeticMailbox(k, wdir) for k in (cc, ccc, stevo)}
    for b in boxes.values():
        b.publish_card()
    boxes["CC"].send(to_contact=ccc.aid, subject="x", body="CCC only")
    assert boxes["Stevo"].inbox() == [], "captain saw a CC->CCC letter in his inbox"
    assert any(m["body"] == "CCC only" for m in boxes["CCC"].inbox())
    return "HermeticMailbox surfaces only openable letters; Stevo's inbox is empty, CCC's has it"


@check("§10.10 interop: the deterministic vectors reproduce (Python; Rust+stock-age proven separately)")
def c10():
    vec = os.path.join(HERE, "hermetic-vectors.json")
    tool = os.path.join(HERE, "keyholder_interop.py")
    if not (os.path.exists(vec) and os.path.exists(tool)):
        return "SKIP — shared vectors not present (tools/hermetic-vectors.json)"
    r = subprocess.run([sys.executable, tool, "vectors-check", vec], capture_output=True, text=True)
    assert r.returncode == 0 and "OK" in (r.stdout + r.stderr), r.stdout + r.stderr
    return r.stdout.strip().splitlines()[-1]


# ── runner ────────────────────────────────────────────────────────────────────────────
def main():
    quiet = "-q" in sys.argv
    print("HERMETIC MAIL — ACCEPTANCE AUDIT (CF5 §10)\n" + "=" * 60)
    failed = 0
    for title, fn in CHECKS:
        try:
            detail = fn()
            ok = not (isinstance(detail, str) and detail.startswith("SKIP"))
            mark = "PASS" if ok else "SKIP"
            print("[%s] %s" % (mark, title))
            if not quiet and detail:
                print("       %s" % detail)
        except Exception as e:
            failed += 1
            print("[FAIL] %s\n       -> %s" % (title, e))
    print("=" * 60)
    if failed:
        print("AUDIT FAILED — %d propert%s did not hold." % (failed, "y" if failed == 1 else "ies"))
        return 1
    print("AUDIT PASSED — every claimed hermetic property holds.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
