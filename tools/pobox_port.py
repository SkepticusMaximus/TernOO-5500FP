#!/usr/bin/env python3
"""Port the git-POBOX history into the live TernID agent (Path A, g46).

Uses CCC's import_message (TernID main) which preserves the ORIGINAL timestamp +
sender, so the 3-pane face shows the true history. Idempotent: message_id is the
content-address, so re-runs dedupe. The agent has NO delete, so this is one-way —
run once.

Each POBOX .md -> parsed (StubBackend) -> deposited into its recipient account box
with the real date (from the filename). 'to crew' fans out to every seat box.
"""
import os
import re
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "FlowCode"))
from ternid_agent_protocol import Client
from mailbox_qt import StubBackend

SOCK = os.environ.get("TERNID_AGENT_SOCK", "/run/ternid/agent.sock")


def time_from_name(fname):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:-(\d{2})(\d{2}))?", fname)
    if not m:
        return None
    y, mo, da = int(m.group(1)), int(m.group(2)), int(m.group(3))
    hh, mm = int(m.group(4) or 0), int(m.group(5) or 0)
    try:
        return int(datetime.datetime(y, mo, da, hh, mm).timestamp())
    except ValueError:
        return None


def resolve_recipients(to_str, accounts):
    """to_str -> set of recipient account handles. 'crew' -> everyone."""
    toks = [t for t in re.split(r"[^A-Za-z0-9]+", to_str or "") if t]
    if any(t.lower().startswith("crew") for t in toks):
        return set(accounts.values())
    out = set()
    for t in toks:
        norm = re.sub(r"(worker|cloud|hp|lenny)$", "", t, flags=re.I)
        for disp, h in accounts.items():
            if disp.lower() in (t.lower(), norm.lower()):
                out.add(h)
    return out


def main():
    execute = "--go" in sys.argv
    c = Client(SOCK)
    accounts = {c.account_display(account_handle=a): a for a in c.list_accounts()}
    print("accounts:", list(accounts))

    b = StubBackend()
    plan = []          # (fname, from, time, [recipient handles])
    skipped = []
    for m in b._msgs:
        fname = m["id"]
        t = time_from_name(fname)
        if t is None:
            skipped.append((fname, "no date"))
            continue
        recips = resolve_recipients(m.get("to", ""), accounts)
        if not recips:
            skipped.append((fname, "to=%r unmatched" % m.get("to")))
            continue
        plan.append((m, t, sorted(recips)))

    imports = sum(len(r) for _, _, r in plan)
    print("PLAN: %d files -> %d imports across boxes;  %d skipped" % (len(plan), imports, len(skipped)))
    for fn, why in skipped[:20]:
        print("   skip %-55s (%s)" % (fn[:55], why))

    if not execute:
        print("\n(dry-run) pass --go to execute")
        return

    done = fail = 0
    for m, t, recips in plan:
        for h in recips:
            try:
                c.call("import_message", account=h, from_display=str(m.get("from", "?")),
                       subject=str(m.get("subject", "")), body=str(m.get("body", "")), time=t)
                done += 1
            except Exception as e:
                fail += 1
                if fail <= 10:
                    print("   FAIL %s -> %s: %s" % (m["id"][:40], h, str(e)[:80]))
    print("\nIMPORTED %d, failed %d" % (done, fail))


if __name__ == "__main__":
    main()
