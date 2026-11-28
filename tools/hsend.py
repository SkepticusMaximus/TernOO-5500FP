#!/usr/bin/env python3
"""hsend — hermetic send, scriptable. The seat that owns this machine seals a letter to named
recipients and pushes it to the wire, AS ITSELF.

This is how a crew agent sends its own mail with no human relaying it: same path Tmail's backend
uses (HermeticMailbox → the wire clone → push), just callable from a script instead of a GUI. It
is the thing that ends the "captain pastes CC's words from his account" ferry — once CC runs as
its own seat (ternid-cc) with its own key, CC calls this and corresponds directly.

  hsend.py --to CF5 --subject "..." --body "..."
  hsend.py --to CF5,CCC --subject "..." --body-file note.md
  echo "body" | hsend.py --to CF5 --subject "..."

Loads the seat key UNWRAPPED (agent keys are not passphrase-wrapped). A passphrase-wrapped key —
the captain's D3 key — is refused with a pointer to Tmail: a human sends through the app so the
passphrase is typed, never scripted.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from keyholder import Keyholder
from hermetic_mailbox import HermeticMailbox
from hermetic_wire import Wire

KEYFILE = os.path.expanduser(os.environ.get("TERNOO_KEY", "~/.config/ternoo/keys/seat.key"))
WIRE = os.path.expanduser(os.environ.get("TERNOO_WIRE", "~/.local/state/ternoo/wire"))


def load_seat_key(keyfile=KEYFILE):
    try:
        return Keyholder.load(keyfile)                        # agent seats: unwrapped
    except Exception as e:
        raise SystemExit(
            "could not load %s unwrapped (%s). hsend is for agent seats whose key is not "
            "passphrase-wrapped; a wrapped key (the captain's) sends via Tmail, where the "
            "passphrase is typed, never scripted." % (keyfile, type(e).__name__))


def resolve(mbx, names):
    """Map recipient display names -> AIDs via the wire directory (never guess a handle)."""
    contacts = {c["display_name"]: c["handle"] for c in mbx.contacts()}
    handles = []
    for n in (x.strip() for x in names):
        if n not in contacts:
            raise SystemExit("no card on the wire for %r (have: %s)" % (n, sorted(contacts)))
        handles.append(contacts[n])
    return handles


def send_as(kh, to_names, subject, body, wire_path=WIRE, push=True):
    """Seal one envelope to every recipient (+ a self-copy) and push. Returns (result, pushed)."""
    mbx = HermeticMailbox(kh, wire_path)
    handles = resolve(mbx, to_names)
    res = mbx.send_group(from_account=kh.aid, to_contacts=handles, subject=subject, body=body)
    pushed = False
    if push:
        Wire(wire_path).sync(push=True)                      # same push Tmail does after a send
        pushed = True
    return res, pushed


def main(argv=None):
    ap = argparse.ArgumentParser(description="hermetic send — seal + push a letter as this seat")
    ap.add_argument("--to", required=True, help="comma-separated recipient display names")
    ap.add_argument("--subject", default="")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--body")
    g.add_argument("--body-file")
    ap.add_argument("--no-push", action="store_true", help="seal into the clone; let the carrier push")
    a = ap.parse_args(argv)
    body = a.body if a.body is not None else (
        open(a.body_file).read() if a.body_file else sys.stdin.read())

    kh = load_seat_key()
    res, pushed = send_as(kh, a.to.split(","), a.subject, body, push=not a.no_push)
    tail = ", pushed to the wire" if pushed else ", sealed (carrier pushes within 3 min)"
    print("sent as %s -> %s  (id %s%s)" % (kh.display, ", ".join(res["recipients"]),
                                           res["message_id"], tail))


if __name__ == "__main__":
    main()
