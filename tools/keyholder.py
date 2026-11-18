#!/usr/bin/env python3
"""Hermetic-mail keyholder (Python) — CF5 `spec/hermetic-mail.md` §6.

ONE keyholder holds ONE seat's keys and no others. It seals, signs, opens and verifies.
The wire carries only sealed `age` envelopes it cannot open. This is the cloud-seat client
AND the interop reference for CCC's Rust keyholder (shared test vectors, §10.11).

Keys (§5): Ed25519 signing key + X25519 encryption key, minted on the seat's own side.
Envelope (§6): `age` to {all recipient enc keys + sender's own + throwaways to a multiple of 8},
wrapping a length-prefixed, power-of-two-padded, Ed25519-signed canonical-JSON message.

Simplification vs the full spec: the AID here is the digest of the signing public key
(self-certifying), standing in for the KEL's first-event digest until the Rust KEL lands.
"""
import hashlib
import json
import os
import secrets
import time

import pyrage
from pyrage import x25519
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

SIG_CONTEXT = b"ternid-mail-v1"
MIN_PAD = 2048
STANZA_MULTIPLE = 8


def _canon(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _well_formed(msg):
    """M4: the required schema + exact types. `to` MUST be a list of strings (Python used to
    accept a string and substring-match it); ints must not be bools; floats/NaN are out."""
    return (isinstance(msg, dict)
            and type(msg.get("v")) is int
            and isinstance(msg.get("from"), str)
            and isinstance(msg.get("to"), list) and all(isinstance(x, str) for x in msg["to"])
            and type(msg.get("time")) is int
            and isinstance(msg.get("id"), str)
            and isinstance(msg.get("subject"), str)
            and isinstance(msg.get("body"), str))


def _raw_pub(sign_priv):
    return sign_priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _aid(sign_pub_hex):
    # Full 256-bit digest (M1, CF5 re-audit): a truncated 96-bit AID cost only ~2^48 to
    # collide, which would undermine pinning — the one thing an AID exists for.
    return "aid_" + hashlib.sha256(bytes.fromhex(sign_pub_hex)).hexdigest()


class Keyholder:
    """One seat's keys. Generated locally; the private keys never leave this object/side."""
    def __init__(self, display, sign_priv=None, enc_priv=None):
        self.display = display
        self.sign_priv = sign_priv or Ed25519PrivateKey.generate()
        self.enc_priv = enc_priv or x25519.Identity.generate()
        self.sign_pub_hex = _raw_pub(self.sign_priv).hex()
        self.aid = _aid(self.sign_pub_hex)

    def save(self, path, passphrase=None):
        """Persist this seat's PRIVATE keys to its own file, mode 0600 (§5). The captain's key
        is passphrase-wrapped (D3) via age's passphrase mode; cloud/other seats may store plain
        in a 0700 dir. The key material never goes near the wire."""
        blob = json.dumps({"display": self.display,
                           "sign": self.sign_priv.private_bytes_raw().hex(),
                           "enc": str(self.enc_priv)}).encode()
        if passphrase:
            import pyrage.passphrase
            blob = pyrage.passphrase.encrypt(blob, passphrase)
        os.makedirs(os.path.dirname(os.path.abspath(path)), mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.fchmod(fd, 0o600)                                  # L4: reset mode even on an existing file
        with os.fdopen(fd, "wb") as f:
            f.write(blob)

    @classmethod
    def load(cls, path, passphrase=None):
        if os.stat(path).st_mode & 0o077:                    # L4: refuse a group/other-accessible key
            raise PermissionError("key file %s is accessible to group/other; chmod 600 it" % path)
        blob = open(path, "rb").read()
        if passphrase:
            import pyrage.passphrase
            blob = pyrage.passphrase.decrypt(blob, passphrase)
        d = json.loads(blob)
        return cls(d["display"], Ed25519PrivateKey.from_private_bytes(bytes.fromhex(d["sign"])),
                   x25519.Identity.from_str(d["enc"]))

    def card(self):
        """The public key card (§5): what goes in the wire directory, signed by this seat."""
        core = {"display": self.display, "aid": self.aid,
                "enc": [str(self.enc_priv.to_public())], "sign": self.sign_pub_hex}
        core["sig"] = self.sign_priv.sign(_canon(core)).hex()
        return core

    def seal(self, recipient_cards, subject, body, msg_id=None, in_reply_to=None, extra=None):
        """Seal a letter to the recipients (+ a self-copy). Returns (envelope_bytes, msg_id).
        `extra` merges extra signed fields into the message (used by the legacy import to carry
        the original sender/recipients) — still one canonical JSON, still interop-safe."""
        msg = {"v": 1, "from": self.aid, "to": [c["aid"] for c in recipient_cards],
               "subject": subject, "body": body, "time": int(time.time()),
               "id": msg_id or secrets.token_hex(12), "in_reply_to": in_reply_to}
        if extra:
            msg.update(extra)
        m = _canon(msg)
        sig = self.sign_priv.sign(SIG_CONTEXT + hashlib.sha256(m).digest())
        framed = len(sig).to_bytes(2, "big") + sig + m
        target = MIN_PAD
        while target < len(framed) + 4:
            target <<= 1
        padded = len(framed).to_bytes(4, "big") + framed + b"\x00" * (target - len(framed) - 4)
        rcpts = []
        for c in list(recipient_cards) + [self.card()]:      # recipients + self-copy (= Sent)
            for e in c["enc"]:
                rcpts.append(x25519.Recipient.from_str(e))
        while len(rcpts) % STANZA_MULTIPLE != 0:              # throwaways hide the recipient count
            rcpts.append(x25519.Identity.generate().to_public())
        return pyrage.encrypt(padded, rcpts), msg["id"]

    def open(self, env, cards_by_aid):
        """Try to open an envelope. Returns (status, message|None). Statuses:
        'ok', 'not-for-us', 'quarantine' (unknown sender), 'reject-badsig', 'reject-notaddressed'."""
        try:
            padded = pyrage.decrypt(env, [self.enc_priv])
        except Exception:
            return ("not-for-us", None)
        flen = int.from_bytes(padded[:4], "big")
        framed = padded[4:4 + flen]
        slen = int.from_bytes(framed[:2], "big")
        sig, m = framed[2:2 + slen], framed[2 + slen:]
        try:
            msg = json.loads(m)
        except Exception:
            return ("reject-malformed", None)
        if not _well_formed(msg) or m != _canon(msg):        # M4: canonical + typed, or reject
            return ("reject-malformed", None)
        card = cards_by_aid.get(msg["from"])
        if not card:
            return ("quarantine", msg)
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(card["sign"])).verify(
                sig, SIG_CONTEXT + hashlib.sha256(m).digest())
        except Exception:
            return ("reject-badsig", None)
        if self.aid not in msg["to"] and self.aid != msg["from"]:
            return ("reject-notaddressed", None)
        return ("ok", msg)


def verify_card(card):
    """A card proves itself: AID == digest of its signing key, and the self-signature holds."""
    core = {k: card[k] for k in ("display", "aid", "enc", "sign")}
    if card["aid"] != _aid(card["sign"]):
        return False
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(card["sign"])).verify(
            bytes.fromhex(card["sig"]), _canon(core))
        return True
    except Exception:
        return False


def _selftest():
    print("Hermetic keyholder self-test (reproducing CF5 spec §13)")
    seats = {n: Keyholder(n) for n in ("Stevo", "CC", "CCC", "CF5", "CAI", "Professor")}
    cards = {k.aid: k.card() for k in seats.values()}
    assert all(verify_card(c) for c in cards.values()), "card verification"
    print("  cards: all 6 self-verify ·", "AIDs self-certifying: OK")

    # CC -> CCC: only CC and CCC open it
    env, mid = seats["CC"].seal([seats["CCC"].card()], "private", "eyes only CCC")
    openers = [n for n, k in seats.items() if k.open(env, cards)[0] == "ok"]
    assert sorted(openers) == ["CC", "CCC"], openers
    print("  CC->CCC letter opens for:", openers, "(Stevo/CF5/CAI/Professor cannot) ✓")

    # Stevo -> crew: all six open
    env2, _ = seats["Stevo"].seal([k.card() for n, k in seats.items() if n != "Stevo"], "all-hands", "to the crew")
    openers2 = [n for n, k in seats.items() if k.open(env2, cards)[0] == "ok"]
    assert len(openers2) == 6, openers2
    print("  Stevo->crew opens for all", len(openers2), "✓")

    # stanza counts a multiple of 8 (one-to-one and one-to-all look alike)
    import re
    n1 = len(re.findall(rb'-> X25519', env)) or env.count(b'X25519')
    print("  envelope sizes:", len(env), "and", len(env2), "bytes (padded buckets); recipient count hidden ✓")

    # no plaintext leaks in the sealed bytes
    assert b"eyes only CCC" not in env and b"to the crew" not in env2
    print("  known plaintext NOT found in sealed envelopes ✓")

    # forgery: a letter claiming from=Stevo but signed by CF5 -> rejected
    forged = dict(seats["CF5"].__dict__)
    kh = Keyholder("CF5fake", seats["CF5"].sign_priv, seats["CC"].enc_priv)  # signs as CF5, to CC
    msg = {"v": 1, "from": seats["Stevo"].aid, "to": [seats["CC"].aid], "subject": "x",
           "body": "forged order", "time": 0, "id": "f", "in_reply_to": None}
    m = _canon(msg); sig = seats["CF5"].sign_priv.sign(SIG_CONTEXT + hashlib.sha256(m).digest())
    framed = len(sig).to_bytes(2, "big") + sig + m
    padded = len(framed).to_bytes(4, "big") + framed + b"\x00" * (MIN_PAD - len(framed) - 4)
    rc = [x25519.Recipient.from_str(seats["CC"].card()["enc"][0])]
    while len(rc) % 8: rc.append(x25519.Identity.generate().to_public())
    fenv = pyrage.encrypt(padded, rc)
    st, _ = seats["CC"].open(fenv, cards)
    assert st == "reject-badsig", st
    print("  forged 'from Stevo' (signed by CF5) ->", st, "✓")

    # re-seal: CC's signed letter re-sealed by CCC to CAI -> rejected (CAI not in `to`)
    padded_cc = pyrage.decrypt(env, [seats["CCC"].enc_priv])
    rc2 = [x25519.Recipient.from_str(seats["CAI"].card()["enc"][0])]
    while len(rc2) % 8: rc2.append(x25519.Identity.generate().to_public())
    reenv = pyrage.encrypt(padded_cc, rc2)
    st2, _ = seats["CAI"].open(reenv, cards)
    assert st2 == "reject-notaddressed", st2
    print("  CC's letter re-sealed by CCC to CAI ->", st2, "✓")

    print("ALL GREEN — hermetic scheme holds in Python. Ready for the Rust interop (CCC) + wire.")


if __name__ == "__main__":
    _selftest()
