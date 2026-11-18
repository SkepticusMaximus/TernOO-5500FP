#!/usr/bin/env python3
"""Signed release manifest for the mail code (M3, CF5 re-audit 18-11).

Tmail runs keyholder.py / hermetic_*.py straight from the repo checkout. A crew member with
push access could land code there that copies the captain's key the next time Tmail runs — the
one back door no envelope stops. This pins the trusted version: the captain SIGNS a manifest of
{file: sha256} for the security-critical files with his own key; Tmail verifies the live files
against it before it ever unlocks a key, and refuses a keyholder that doesn't match. Re-signing
after review is the only way to update it — an explicit captain action.

    release_manifest.py sign     # captain unlocks seat.key, signs -> <keys>/keyholder-release.json
    release_manifest.py verify   # prints the (ok, detail) for the live tree
"""
import glob
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import keyholder as K
from ternid_pins import load_pins

# the security-critical surface: everything that touches a key or seals/opens a letter
CRITICAL = ["keyholder.py", "hermetic_wire.py", "hermetic_mailbox.py", "hermetic_store.py",
            "ternid_pins.py", "hermetic_import.py", "release_manifest.py"]

RELEASE_FILE = os.path.join(
    os.path.expanduser(os.environ.get("TERNOO_KEYS", "~/.config/ternoo/keys")), "keyholder-release.json")


def compute():
    """{filename: sha256} over the critical files, sorted — the thing that gets signed."""
    out = {}
    for name in sorted(CRITICAL):
        p = os.path.join(HERE, name)
        out[name] = hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else ""
    return out


def _signed_bytes(manifest):
    return b"ternid-release-v1" + hashlib.sha256(K._canon({"v": 1, "manifest": manifest})).digest()


def sign(keyholder, path=RELEASE_FILE):
    """Captain signs the current manifest. The signer's CARD is embedded so verify() can check
    the signature cryptographically (the card self-certifies its own key)."""
    manifest = compute()
    rel = {"v": 1, "manifest": manifest, "signer_card": keyholder.card(),
           "sig": keyholder.sign_priv.sign(_signed_bytes(manifest)).hex()}
    os.makedirs(os.path.dirname(os.path.abspath(path)), mode=0o700, exist_ok=True)
    json.dump(rel, open(path, "w"), indent=1, sort_keys=True)
    return rel


def verify(path=RELEASE_FILE, pins=None):
    """(ok, detail). ok only if a signed manifest exists, its card self-certifies, the signer is
    the PINNED captain, the signature verifies, and every live file matches its signed hash. No
    manifest yet -> (True, 'unsigned') so development isn't blocked before cut-over."""
    if not os.path.exists(path):
        return (True, "unsigned (no release manifest yet — pre-cut-over)")
    try:
        rel = json.load(open(path))
    except Exception as e:
        return (False, "release manifest unreadable: %s" % e)
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    card = rel.get("signer_card", {})
    if not K.verify_card(card):
        return (False, "release signer card does not self-certify")
    captain = (load_pins() if pins is None else pins).get("Stevo")
    if captain and card.get("aid") != captain:
        return (False, "release signed by a key that is NOT the pinned captain")
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(card["sign"])).verify(
            bytes.fromhex(rel["sig"]), _signed_bytes(rel.get("manifest", {})))
    except Exception:
        return (False, "release signature is invalid")
    live = compute()
    bad = [f for f in rel.get("manifest", {}) if live.get(f) != rel["manifest"][f]]
    if bad:
        return (False, "mail code changed since it was signed: " + ", ".join(bad))
    return (True, "verified against the captain-signed release")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "sign":
        import getpass
        kh = K.Keyholder.load(
            os.path.join(os.path.expanduser(os.environ.get("TERNOO_KEYS", "~/.config/ternoo/keys")), "seat.key"),
            passphrase=os.environ.get("TERNOO_CAPTAIN_PASS") or getpass.getpass("Captain's key passphrase: "))
        sign(kh)
        print("signed keyholder-release.json over %d files; re-sign after any review of the mail code." % len(CRITICAL))
    else:
        ok, detail = verify()
        print(("OK: " if ok else "REFUSE: ") + detail)
        sys.exit(0 if ok else 1)
