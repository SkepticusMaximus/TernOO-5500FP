#!/usr/bin/env python3
"""Interop driver for the hermetic-mail keyholder (CF5 spec §10.11).

Mirrors the Rust `keyholder` CLI so sealed `age` envelopes can be handed between the Python and
Rust keyholders and proven to interoperate. Loads the shared vectors file (pinned seat material),
and seals / opens / checks against it.

  keyholder_interop.py vectors-check <vectors.json>
  keyholder_interop.py seal  <vectors.json> <from> <to_csv> <subject> <body> <out.age>
  keyholder_interop.py open  <vectors.json> <as>   <in.age>
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pyrage import x25519
import keyholder as K


def load(path):
    v = json.load(open(path))
    seats, cards = {}, {}
    for s in v["seats"]:
        sign_priv = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(s["ed_seed_hex"]))
        enc_priv = x25519.Identity.from_str(s["age_secret"])
        kh = K.Keyholder(s["display"], sign_priv, enc_priv)
        seats[s["display"]] = kh
        cards[kh.aid] = kh.card()
    return v, seats, cards


def cmd_vectors_check(path):
    v, seats, cards = load(path)
    n = 0
    for s in v["seats"]:
        kh = seats[s["display"]]
        assert kh.aid == s["aid"], f'{s["display"]} AID'
        assert kh.card() == s["card"], f'{s["display"]} card'
        assert K.verify_card(kh.card()), f'{s["display"]} self-verify'
        n += 1
    mv = v["message_vector"]
    stevo = seats[mv["from"]]
    msg = {"v": 1, "from": stevo.aid, "to": [seats[d].aid for d in mv["to"]],
           "subject": mv["subject"], "body": mv["body"], "time": mv["time"],
           "id": mv["id"], "in_reply_to": mv["in_reply_to"]}
    m = K._canon(msg)
    assert m.hex() == mv["canon_hex"], "canon"
    assert hashlib.sha256(m).hexdigest() == mv["sha256_canon"], "sha256"
    sig = stevo.sign_priv.sign(K.SIG_CONTEXT + hashlib.sha256(m).digest())
    assert sig.hex() == mv["sig_hex"], "sig"
    n += 1
    print(f"vectors-check OK — {n} deterministic vectors reproduced (Python)")


def cmd_seal(path, frm, to_csv, subject, body, out):
    _, seats, _ = load(path)
    kh = seats[frm]
    cards = [seats[d].card() for d in to_csv.split(",")]
    env, mid = kh.seal(cards, subject, body)
    open(out, "wb").write(env)
    print(f"sealed {len(env)} bytes -> {out} (id {mid})")


def cmd_open(path, who, infile):
    _, seats, cards = load(path)
    env = open(infile, "rb").read()
    status, msg = seats[who].open(env, cards)
    subject = (msg or {}).get("subject", "")
    body = (msg or {}).get("body", "")
    print(f"{status}\t{subject}\t{body}")
    sys.exit(0 if status == "ok" else 1)


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__); sys.exit(2)
    if a[0] == "vectors-check":
        cmd_vectors_check(a[1])
    elif a[0] == "seal":
        cmd_seal(a[1], a[2], a[3], a[4], a[5], a[6])
    elif a[0] == "open":
        cmd_open(a[1], a[2], a[3])
    else:
        print(__doc__); sys.exit(2)
