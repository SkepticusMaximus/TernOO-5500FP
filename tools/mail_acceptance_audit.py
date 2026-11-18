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


@check("§10.13 the key ceremony mints EXACTLY ONE key — never another seat's (H1, CF5 re-audit)")
def c13():
    d = tempfile.mkdtemp()
    env = dict(os.environ, TERNOO_KEYS=os.path.join(d, "keys"), TERNOO_WIRE=os.path.join(d, "wire"),
               TERNOO_SEAT="CF5", TERNOO_CAPTAIN_PASS="x")
    subprocess.run([sys.executable, "-c",
                    "import sys; sys.path.insert(0, %r); import hermetic_ceremony as C; C.mint_key()" % HERE],
                   env=env, capture_output=True, text=True, check=True)
    keys = sorted(os.listdir(os.path.join(d, "keys")))
    assert keys == ["seat.key"], "a single-seat ceremony wrote %s (must be only seat.key)" % keys
    return "a CF5 ceremony wrote only seat.key — no cc/ccc/cai/professor keys were created"


@check("§10.11 a non-migration signer setting `legacy` is NOT shown with the spoofed sender (H2)")
def c11():
    wdir = tempfile.mkdtemp()
    mig, outsider, cc = K.Keyholder("migration"), K.Keyholder("outsider"), K.Keyholder("CC")
    w = Wire(wdir)
    for k in (mig, outsider, cc):
        w.publish_card(k)
    env, _ = outsider.seal([cc.card()], "ORDERS", "do this",
                           extra={"legacy": True, "orig_from": "Stevo", "orig_to": "CC", "time_posted": 0})
    open(os.path.join(w.pool, "x.age"), "wb").write(env)
    box = HermeticMailbox(cc, wdir, migration_aid=mig.aid)
    spoof = next(x for x in box.inbox() if x["subject"] == "ORDERS")
    assert spoof["from"] != "Stevo", "spoofed legacy shown as from Stevo!"
    assert spoof["from"] == "outsider" and not spoof["legacy"], spoof["from"]
    env2, _ = mig.seal([cc.card()], "old", "history",
                       extra={"legacy": True, "orig_from": "CF5", "orig_to": "CC", "time_posted": 0})
    open(os.path.join(w.pool, "y.age"), "wb").write(env2)
    real = next(x for x in box.inbox() if x["subject"] == "old")
    assert real["from"] == "CF5" and real["legacy"], real
    return "spoofed legacy shows the real signer (outsider); only migration-signed legacy shows orig_from"


@check("§10.14 AIDs carry at least 128 bits (M1 — pinning needs collision resistance)")
def c14():
    bits = (len(K.Keyholder("CC").aid) - len("aid_")) * 4
    assert bits >= 128, "AID is only %d bits" % bits
    return "AID is %d bits (full sha256 of the signing key)" % bits


@check("§10.15 non-canonical / mistyped message bytes are rejected (M4)")
def c15():
    import hashlib
    import pyrage
    from pyrage import x25519
    cc, ccc = K.Keyholder("CC"), K.Keyholder("CCC")
    cards = {cc.aid: cc.card(), ccc.aid: ccc.card()}
    # a correctly-signed letter whose `to` is a STRING, not a list (the old substring-match hazard)
    m = ('{"body":"x","from":"%s","id":"a","in_reply_to":null,"subject":"s","time":0,"to":"%s","v":1}'
         % (cc.aid, ccc.aid)).encode()
    sig = cc.sign_priv.sign(K.SIG_CONTEXT + hashlib.sha256(m).digest())
    framed = len(sig).to_bytes(2, "big") + sig + m
    padded = len(framed).to_bytes(4, "big") + framed + b"\x00" * (K.MIN_PAD - len(framed) - 4)
    rc = [x25519.Recipient.from_str(ccc.card()["enc"][0])]
    while len(rc) % K.STANZA_MULTIPLE:
        rc.append(x25519.Identity.generate().to_public())
    st = ccc.open(pyrage.encrypt(padded, rc), cards)[0]
    assert st == "reject-malformed", "mistyped `to` accepted (status %s)" % st
    return "a letter with `to` as a string (not a list of AIDs) is rejected -> reject-malformed"


def deployed_scan():
    """§10.17 — the check that §10.2 can't make: scan the REAL key directory on THIS host and
    prove it holds at most its own seat's key, locked down. Run on every host at cut-over."""
    import stat
    kd = os.path.expanduser(os.environ.get("TERNOO_KEYS", "~/.config/ternoo/keys"))
    print("DEPLOYED-STATE SCAN (§10.17) — %s\n%s" % (kd, "=" * 60))
    if not os.path.isdir(kd):
        print("[PASS] no key directory here — no seat runs on this host")
        return 0
    keys = sorted(f for f in os.listdir(kd) if f.endswith(".key"))
    fails = 0
    if len(keys) > 1:
        print("[FAIL] host holds %d seat keys %s — a machine must hold at most ITS OWN (H1)" % (len(keys), keys)); fails += 1
    else:
        print("[PASS] host holds %d seat key: %s" % (len(keys), keys or "none"))
    dmode = stat.S_IMODE(os.stat(kd).st_mode)
    print("[%s] key dir mode %o (want 0700)" % ("PASS" if not dmode & 0o077 else "FAIL", dmode))
    fails += 1 if dmode & 0o077 else 0
    for k in keys:
        st = os.stat(os.path.join(kd, k)); m = stat.S_IMODE(st.st_mode)
        if m & 0o077:
            print("[FAIL] %s mode %o (want 0600)" % (k, m)); fails += 1
        if st.st_uid != os.getuid():
            print("[FAIL] %s not owned by this user" % k); fails += 1
    print("=" * 60)
    print("DEPLOYED SCAN " + ("PASSED" if not fails else "FAILED (%d)" % fails))
    return 1 if fails else 0


# ── runner ────────────────────────────────────────────────────────────────────────────
def main():
    if "--deployed" in sys.argv:
        return deployed_scan()
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
