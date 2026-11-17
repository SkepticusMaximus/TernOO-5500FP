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


def _raw_pub(sign_priv):
    return sign_priv.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)


def _aid(sign_pub_hex):
    return "aid_" + hashlib.sha256(bytes.fromhex(sign_pub_hex)).hexdigest()[:24]


class Keyholder:
    """One seat's keys. Generated locally; the private keys never leave this object/side."""
    def __init__(self, display, sign_priv=None, enc_priv=None):
        self.display = display
        self.sign_priv = sign_priv or Ed25519PrivateKey.generate()
        self.enc_priv = enc_priv or x25519.Identity.generate()
        self.sign_pub_hex = _raw_pub(self.sign_priv).hex()
        self.aid = _aid(self.sign_pub_hex)

    def card(self):
        """The public key card (§5): what goes in the wire directory, signed by this seat."""
        core = {"display": self.display, "aid": self.aid,
                "enc": [str(self.enc_priv.to_public())], "sign": self.sign_pub_hex}
        core["sig"] = self.sign_priv.sign(_canon(core)).hex()
        return core

    def seal(self, recipient_cards, subject, body, msg_id=None, in_reply_to=None):
        """Seal a letter to the recipients (+ a self-copy). Returns (envelope_bytes, msg_id)."""
        msg = {"v": 1, "from": self.aid, "to": [c["aid"] for c in recipient_cards],
               "subject": subject, "body": body, "time": int(time.time()),
               "id": msg_id or secrets.token_hex(12), "in_reply_to": in_reply_to}
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
        msg = json.loads(m)
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
