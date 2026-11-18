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
    # env override exists ONLY for the automated self-test; a real run uses getpass (no echo).
    # L3: ask for a real passphrase (>= 12 chars). Note: Python can't reliably wipe it from
    # memory afterwards — acceptable for v1, stated plainly.
    env = os.environ.get("TERNOO_CAPTAIN_PASS")
    if env:
        return env
    while True:
        pw = getpass.getpass("Captain's key passphrase (>= 12 chars): ")
        if len(pw) >= 12:
            return pw
        print("  too short — use at least 12 characters (a passphrase, not a password).")


def mint_key():
    """Mint/load ONLY the seat that owns THIS machine (H1 fix, CF5 re-audit 18-11).

    A ceremony NEVER mints another seat's private key — each seat mints its own, on its own
    side (spec §5). This is the whole point: no machine ends up holding the crew's keys.
    """
    os.makedirs(KEYS, mode=0o700, exist_ok=True)
    path = _keyfile(SEAT)
    pw = _captain_pass() if SEAT == "Stevo" else None
    if os.path.exists(path):
        kh = K.Keyholder.load(path, passphrase=pw)
        print("  kept   %-10s %s" % (SEAT, path))
    else:
        kh = K.Keyholder(SEAT)
        kh.save(path, passphrase=pw)
        print("  minted %-10s %s%s" % (SEAT, path, "  (passphrase-wrapped)" if SEAT == "Stevo" else ""))
    return kh


def _history_src(pobox_dir):
    if pobox_dir:
        return pobox_dir
    if os.path.isdir(POBOX):
        return POBOX
    import subprocess
    import tempfile
    src = os.path.join(tempfile.mkdtemp(), "pobox")
    print("  cloning the private history from the wire remote…")
    subprocess.run(["git", "-c", "credential.helper=store", "clone", "--quiet", POBOX, src], check=True)
    return src


def run(pobox_dir=None):
    print("Hermetic ceremony — seat on this machine: %s (mints ONLY this seat's key — H1)" % SEAT)
    kh = mint_key()
    wire = Wire(WIRE)
    wire.publish_card(kh)                                     # publish MY PUBLIC card; no private key leaves
    cards = wire.directory()
    have = sorted(c["display"] for c in cards.values() if c["display"] in SEATS)
    print("  published %s's card; seats present on the wire: %d/%d %s" % (SEAT, len(have), len(SEATS), have))
    if len(have) < len(SEATS):
        print("  restoring history to the %d seat(s) present now — others get theirs when they mint." % len(have))

    # H3 (CF5 re-audit): pin ONLY yourself. Auto-pinning whatever is on the wire at mint time is
    # trust-on-first-use — an impostor present at that moment would be silently pinned. Other seats
    # are confirmed one at a time, out of band, via Tmail's "Trust sender".
    from ternid_pins import fingerprint, load_pins, save_pins
    pins = load_pins()
    pins[SEAT] = kh.aid
    save_pins(pins)
    print("  PINNED your own identity: %-10s %s" % (SEAT, fingerprint(kh.aid)))
    print("  -> READ this fingerprint to the crew OUT OF BAND so each of them can confirm + pin you.")
    print("  -> Other seats are NOT auto-trusted; confirm each of theirs via Trust sender.")

    marker = os.path.join(KEYS, "history-restored")
    if os.path.exists(marker):
        print("  history already restored for %s — skipping (delete %s to redo)" % (SEAT, marker))
        return kh, wire, 0

    # Restore the shared history to THIS seat ONLY — its own private copy, sealed to its own card.
    # Each seat does this independently, so it never duplicates into another seat's inbox on the
    # shared wire. The migration key signs it and its AID is pinned locally (H2).
    migration = K.Keyholder("migration")
    wire.publish_card(migration)                             # published only so legacy signatures verify
    open(os.path.join(KEYS, "migration.aid"), "w").write(migration.aid)
    src = _history_src(pobox_dir)
    n, per, lost = import_all(src, wire.pool, migration, {kh.aid: kh.card()}, restore_open=True)
    open(marker, "w").write(SEAT)
    print("  restored %d letters to %s's own sealed pool (%d unroutable -> flagged)" % (n, SEAT, lost))
    print("Done — each seat opens its own history with ITS OWN key. (Cut-over stays gated.)")
    return kh, wire, n


if __name__ == "__main__":
    run()
