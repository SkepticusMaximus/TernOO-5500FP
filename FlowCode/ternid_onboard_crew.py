#!/usr/bin/env python3
"""Onboard the crew into the live ternid-agent: one real seat per member
(idempotent) and a full-mesh invite exchange so every seat can mail every other.

Run with the agent up and TERNID_AGENT_SOCK pointing at its socket:
    TERNID_AGENT_SOCK=$XDG_RUNTIME_DIR/ternid-agent.sock python3 ternid_onboard_crew.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ternid_agent_protocol import Client

CREW = ["Stevo", "CC", "CCC", "CF5", "CAI", "Professor"]


def main():
    c = Client(os.environ.get("TERNID_AGENT_SOCK") or None)

    # display -> handle for any seats that already exist (idempotent re-runs)
    existing = {c.account_display(account_handle=h): h for h in c.list_accounts()}
    handle = {}
    for name in CREW:
        if name in existing:
            handle[name] = existing[name]
            print(f"  seat exists:  {name:10} -> {handle[name]}")
        else:
            handle[name] = c.create_account(display_name=name)["account_handle"]
            print(f"  created seat: {name:10} -> {handle[name]}")

    # full mesh: for each ordered pair (a, b), a invites and b accepts, so b can mail a
    wired = 0
    for a in CREW:
        for b in CREW:
            if a == b:
                continue
            if any(ct.get("display_name") == a for ct in c.contacts(account=handle[b])):
                continue  # b already has a as a contact
            inv = c.create_invite(account=handle[a], for_display_name=b)["invite"]
            c.add_contact(account=handle[b], invite=inv)
            wired += 1
    print(f"\n  wired {wired} new directed contact links (full mesh of {len(CREW)} seats)")
    print("  crew home:", ", ".join(CREW))


if __name__ == "__main__":
    main()
