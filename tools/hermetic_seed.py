#!/usr/bin/env python3
"""Deterministic seat-key derivation from a persistent secret (spec §12 D4 — cloud seats).

A cloud seat (CCC / CF5 / CAI) runs in an ephemeral container: its filesystem is wiped on every
rebuild, so a key minted to a file does not survive. The durable home for such a seat's identity
is a **per-seat secret the captain sets on that seat's session environment** (spec §5 / §12 D4).
This module turns that one secret into the seat's fixed TernID identity, the same every session:

    ed25519 signing seed = HKDF-SHA256(secret, info="ternid-seat-ed25519-v1", L=32)
    x25519  scalar       = HKDF-SHA256(secret, info="ternid-seat-x25519-v1",  L=32)
    age identity         = Bech32("age-secret-key-", scalar).upper()     # what pyrage/age accept

No private key is ever generated here or written to the wire; the seat's keys are a pure function
of the captain-chosen secret, which lives only in that seat's environment and never in chat or git.

CONVENTION TO AGREE WITH CC (cloud Python client) + mirror in the Rust keyholder + vectors:
the two HKDF info labels and the Bech32 encoding above are the interop contract. Change them and
a seat's AID changes.
"""
import hashlib
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pyrage import x25519

ENV_SEED = "TERNOO_SEED"  # the captain sets this on the seat's own session environment
MIN_SEED_LEN = 24         # a captain-chosen random value; reject obviously weak input

_CH = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"


# --- Bech32 (BIP173), just enough to encode an age X25519 secret key ---

def _polymod(values):
    gen = [0x3b6a57b2, 0x26508e6d, 0x1ea119fa, 0x3d4233dd, 0x2a1462b3]
    chk = 1
    for v in values:
        b = chk >> 25
        chk = ((chk & 0x1ffffff) << 5) ^ v
        for i in range(5):
            if (b >> i) & 1:
                chk ^= gen[i]
    return chk


def _hrp_expand(hrp):
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _checksum(hrp, data):
    pm = _polymod(_hrp_expand(hrp) + data + [0] * 6) ^ 1
    return [(pm >> 5 * (5 - i)) & 31 for i in range(6)]


def _to5(data):
    acc = bits = 0
    out = []
    for b in data:
        acc = (acc << 8) | b
        bits += 8
        while bits >= 5:
            bits -= 5
            out.append((acc >> bits) & 31)
    if bits:
        out.append((acc << (5 - bits)) & 31)
    return out


def _bech32(hrp_lower, raw):
    # checksum is computed over the LOWERCASE hrp; age secret keys are the UPPERCASE form.
    d = _to5(list(raw))
    comb = d + _checksum(hrp_lower, d)
    return hrp_lower + "1" + "".join(_CH[x] for x in comb)


def _age_secret_from_scalar(scalar32):
    return _bech32("age-secret-key-", scalar32).upper()


# --- derivation ---

def _hkdf(ikm, info, n=32):
    return HKDF(algorithm=hashes.SHA256(), length=n, salt=b"", info=info).derive(ikm)


def derive_material(secret):
    """(ed25519 32-byte seed, age-secret-key string) from a secret (str or bytes)."""
    ikm = secret.encode() if isinstance(secret, str) else secret
    ed = _hkdf(ikm, b"ternid-seat-ed25519-v1")
    age = _age_secret_from_scalar(_hkdf(ikm, b"ternid-seat-x25519-v1"))
    return ed, age


def derive_keyholder(display, secret, keyholder_module):
    """Build a Keyholder for `display` deterministically from `secret`.

    `keyholder_module` is the imported `keyholder` module (passed in so this file has no import
    cycle with the ceremony). Raises ValueError on a too-short secret.
    """
    if secret is None or len(secret) < MIN_SEED_LEN:
        raise ValueError(
            f"{ENV_SEED} must be at least {MIN_SEED_LEN} characters of captain-chosen randomness"
        )
    ed, age = derive_material(secret)
    sign_priv = Ed25519PrivateKey.from_private_bytes(ed)
    enc_priv = x25519.Identity.from_str(age)
    return keyholder_module.Keyholder(display, sign_priv, enc_priv)


def seed_from_env():
    """The captain-set per-seat secret, or None if this seat has no durable seed configured."""
    s = os.environ.get(ENV_SEED)
    return s if s else None


if __name__ == "__main__":
    # Self-test: determinism + a valid, loadable age identity + self seal/open.
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import keyholder as K

    s = "captain-chosen-strong-random-seed-value-abc123"
    a = derive_keyholder("CCC", s, K)
    b = derive_keyholder("CCC", s, K)
    assert a.aid == b.aid, "derivation must be reproducible"
    env, _ = a.seal([a.card()], "self", "durable identity ✓")
    assert a.open(env, {a.aid: a.card()})[0] == "ok", "self-open"
    try:
        derive_keyholder("CCC", "tooshort", K)
        raise SystemExit("FAIL: short seed accepted")
    except ValueError:
        pass
    print("hermetic_seed self-test OK — AID", a.aid)
