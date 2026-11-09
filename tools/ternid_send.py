#!/usr/bin/env python3
"""Send crew mail through the LIVE TernID agent — the mailbox POBOX Mail actually reads.

This retires the git-POBOX ferry for the last mile: instead of committing a .md file
that only the stub backend sees, CC (or anyone) delivers mail straight into the real
TernID agent over its socket, so it lands in the recipients' inboxes and shows up in
the Mail app. Only display names + opaque handles cross the wire (the golden rule).

Usage:
  ternid_send.py --from CC --to crew    --subject "..." --body-file note.md
  ternid_send.py --from CC --to Stevo   --subject "..." --body "one-liner"
  ternid_send.py --list                 # show accounts + contacts, send nothing
"""
import argparse, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "FlowCode"))
from ternid_agent_protocol import Client, default_sock


def resolve_account(c, display):
    for a in c.list_accounts():
        if c.account_display(account_handle=a) == display:
            return a
    raise SystemExit("no account with display name %r (have: %s)"
                     % (display, [c.account_display(account_handle=a) for a in c.list_accounts()]))


def resolve_targets(c, from_acct, to):
    """`crew` -> every contact of the sender; else a single display name -> its contact handle."""
    contacts = c.contacts(account=from_acct)
    if to.lower() == "crew":
        return [(x["display_name"], x["handle"]) for x in contacts]
    for x in contacts:
        if x["display_name"] == to:
            return [(to, x["handle"])]
    raise SystemExit("%r is not a contact of the sender (have: %s)"
                     % (to, [x["display_name"] for x in contacts]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="frm")
    ap.add_argument("--to")
    ap.add_argument("--subject", default="(no subject)")
    ap.add_argument("--body")
    ap.add_argument("--body-file")
    ap.add_argument("--sock", default=default_sock() if os.environ.get("TERNID_AGENT_SOCK") else "/run/ternid/agent.sock")
    ap.add_argument("--list", action="store_true", help="show accounts/contacts and exit")
    a = ap.parse_args()

    c = Client(a.sock)
    if a.list:
        for acct in c.list_accounts():
            print("%s = %s" % (c.account_display(account_handle=acct), acct))
            for x in c.contacts(account=acct):
                print("   -> %s (%s)" % (x["display_name"], x["handle"]))
        return
    if not (a.frm and a.to):
        raise SystemExit("need --from and --to (or --list)")

    body = a.body
    if a.body_file:
        body = open(a.body_file, encoding="utf-8", errors="replace").read()
    if body is None:
        raise SystemExit("need --body or --body-file")

    frm = resolve_account(c, a.frm)
    targets = resolve_targets(c, frm, a.to)
    sent = 0
    for disp, handle in targets:
        if disp == a.frm:
            continue  # don't mail yourself
        res = c.send(from_account=frm, to_contact=handle, subject=a.subject, body=body)
        mid = res.get("message_id") if isinstance(res, dict) else res
        print("  -> %-10s delivered (%s)" % (disp, mid))
        sent += 1
    print("sent %d message(s) from %s through the TernID agent." % (sent, a.frm))


if __name__ == "__main__":
    main()
