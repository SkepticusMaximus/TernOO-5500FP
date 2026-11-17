#!/usr/bin/env python3
"""Hermetic-mail key ceremony — stand up the sealed mailbox (CF5 spec §5 + §8).

Run ONCE to bring the hermetic system up on this machine:

  1. mint a keypair for every seat (idempotent — an existing key file is kept, never overwritten)
  2. publish every seat's signed card to the wire directory
  3. restore the full POBOX history into the sealed pool (open-restore: the pre-today mail was
     never private, so every seat gets it back — the captain's 18-11 ruling)

The captain's key is passphrase-wrapped (D3): the passphrase is read from getpass (never echoed,
never stored, never seen by the tooling). The other seats' key files are mode-0600 in a 0700 dir;
their custody is the seat's own runtime — the honest limit already on the record. The wire never
sees a private key or a byte of plaintext.

After this runs, `mailbox_qt.py` finds ~/.config/ternoo/keys/seat.key and opens hermetically.

  Captain, real run:   TERNOO_SEAT=Stevo python3 tools/hermetic_ceremony.py
  then:                python3 FlowCode/mailbox_qt.py

Nothing here disables or deletes the old system — that is cut-over, and it stays gated.
"""
import getpass
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import keyholder as K
from hermetic_import import import_all
from hermetic_wire import Wire

SEATS = ["Stevo", "CC", "CCC", "CF5", "CAI", "Professor"]
KEYS = os.path.expanduser(os.environ.get("TERNOO_KEYS", "~/.config/ternoo/keys"))
WIRE = os.path.expanduser(os.environ.get("TERNOO_WIRE", "~/.local/state/ternoo/wire"))
POBOX = os.environ.get("TERNOO_POBOX", "https://github.com/SkepticusMaximus/Tmail-POBOX.git")
SEAT = os.environ.get("TERNOO_SEAT", "Stevo")                 # which seat THIS machine holds


def _keyfile(seat):
    # the seat that owns this machine lands on the path mailbox_qt.py looks for
    return os.path.join(KEYS, "seat.key") if seat == SEAT else os.path.join(KEYS, seat.lower() + ".key")


def _captain_pass():
    # env override exists ONLY for the automated self-test; a real run uses getpass (no echo)
    return os.environ.get("TERNOO_CAPTAIN_PASS") or getpass.getpass("Captain's key passphrase: ")


def mint_keys():
    """One key file per seat. Existing files are loaded, never clobbered. Returns {seat: Keyholder}."""
    os.makedirs(KEYS, mode=0o700, exist_ok=True)
    seats = {}
    for name in SEATS:
        path = _keyfile(name)
        if os.path.exists(path):
            pw = _captain_pass() if name == "Stevo" else None
            seats[name] = K.Keyholder.load(path, passphrase=pw)
            print("  kept   %-10s %s" % (name, path))
        else:
            kh = K.Keyholder(name)
            kh.save(path, passphrase=_captain_pass() if name == "Stevo" else None)
            seats[name] = kh
            print("  minted %-10s %s%s" % (name, path, "  (passphrase-wrapped)" if name == "Stevo" else ""))
    return seats


def run(pobox_dir=None):
    print("Hermetic ceremony — seat on this machine: %s" % SEAT)
    seats = mint_keys()
    wire = Wire(WIRE)
    migration = K.Keyholder("migration")                     # signs the ported history
    for k in list(seats.values()) + [migration]:             # publish cards so legacy sigs verify
        wire.publish_card(k)
    print("  directory: %d cards published (+ migration)" % len(seats))

    if glob.glob(os.path.join(wire.pool, "*.age")):
        print("  pool already has sealed mail — skipping import (delete %s to re-restore)" % wire.pool)
        return seats, wire, 0

    src = pobox_dir
    if src is None:
        if os.path.isdir(POBOX):
            src = POBOX
        else:
            import subprocess
            import tempfile
            src = os.path.join(tempfile.mkdtemp(), "pobox")
            print("  cloning the private history from the wire remote…")
            subprocess.run(["git", "-c", "credential.helper=store", "clone", "--quiet", POBOX, src], check=True)
    cards = {k.aid: k.card() for k in seats.values()}
    n, per, lost = import_all(src, wire.pool, migration, cards, restore_open=True)
    print("  restored %d letters into the sealed pool (%d unroutable -> flagged)" % (n, lost))
    for name in SEATS:
        print("    %-10s %d letters" % (name, len(wire.fetch(seats[name], set()))))
    print("Done. `python3 FlowCode/mailbox_qt.py` now opens the hermetic mailbox for %s." % SEAT)
    print("(The old system is untouched — cut-over stays gated.)")
    return seats, wire, n


if __name__ == "__main__":
    run()
