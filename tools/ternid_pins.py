#!/usr/bin/env python3
"""Pinned display-name ↔ AID bindings (H3, CF5 re-audit 18-11).

A display name is attacker-chosen; an AID self-certifies a key. Pinning binds the two. Each
seat keeps a local `pins.json` {display: aid}, confirmed out of band (AIDs read aloud / on
paper at the ceremony). A crypto-valid card is then classified:

    verified   — display is pinned AND the AID matches the pin
    impostor   — display is pinned but the AID does NOT match   -> REFUSED, never shown as that name
    unverified — display is not pinned                          -> shown 'unverified', never picked by name

Names are compared after NFKC normalisation; a name carrying control, bidirectional or
zero-width characters is rejected outright (it can never be trusted or pinned).
"""
import json
import os
import unicodedata

PINS_FILE = os.path.join(
    os.path.expanduser(os.environ.get("TERNOO_KEYS", "~/.config/ternoo/keys")), "pins.json")

# control (incl. DEL), zero-width, and bidirectional-override code points
_BAD_CP = ({0x7f} | {0x200b, 0x200c, 0x200d, 0x200e, 0x200f, 0xfeff, 0x2060}
           | set(range(0x202a, 0x202f)) | set(range(0x2066, 0x206a)))


def normalize_name(s):
    """NFKC-normalised, trimmed name — or None if it carries control/bidi/zero-width chars."""
    if not isinstance(s, str) or not s:
        return None
    for ch in s:
        if ord(ch) in _BAD_CP or unicodedata.category(ch) in ("Cc", "Cf", "Cs", "Co", "Cn"):
            return None
    out = unicodedata.normalize("NFKC", s).strip()
    return out or None


def load_pins(path=PINS_FILE):
    try:
        d = json.load(open(path))
        return {normalize_name(k): v for k, v in d.items() if normalize_name(k)}
    except Exception:
        return {}


def save_pins(mapping, path=PINS_FILE):
    clean = {normalize_name(k): v for k, v in mapping.items() if normalize_name(k)}
    os.makedirs(os.path.dirname(os.path.abspath(path)), mode=0o700, exist_ok=True)
    json.dump(clean, open(path, "w"), indent=1, sort_keys=True)
    return clean


def classify(card, pins):
    """verified | impostor | unverified for an already-crypto-valid card, against the pins."""
    name = normalize_name(card.get("display", ""))
    if name is None:
        return "impostor"                                 # unrenderable name -> never trust
    pinned = pins.get(name)
    if pinned is None:
        return "unverified"
    return "verified" if pinned == card.get("aid") else "impostor"


def fingerprint(aid):
    """A short, human-checkable form of an AID for out-of-band confirmation."""
    h = aid[4:] if aid.startswith("aid_") else aid
    return " ".join(h[i:i + 4] for i in range(0, 12, 4))  # e.g. '3af0 0d12 ab34'


def _selftest():
    print("ternid_pins self-test (H3)")
    assert normalize_name("Stevo") == "Stevo"
    assert normalize_name("Ste​vo") is None, "zero-width not rejected"
    assert normalize_name("Stevo‮") is None, "bidi override not rejected"
    assert normalize_name("ﬁle") == "file", "NFKC fold (ﬁ -> fi)"   # ligature collides
    pins = {"Stevo": "aid_realstevo", "CC": "aid_cc"}
    assert classify({"display": "Stevo", "aid": "aid_realstevo"}, pins) == "verified"
    assert classify({"display": "Stevo", "aid": "aid_impostor"}, pins) == "impostor"
    assert classify({"display": "Mallory", "aid": "aid_m"}, pins) == "unverified"
    assert classify({"display": "Ste​vo", "aid": "aid_x"}, pins) == "impostor"
    print("  fingerprint:", fingerprint("aid_3af00d12ab34cd56"))
    print("ALL GREEN — names bind to AIDs; impostors and tricky names are caught.")


if __name__ == "__main__":
    _selftest()
