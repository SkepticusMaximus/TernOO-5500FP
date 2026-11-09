#!/usr/bin/env python3
"""agent -> git-POBOX mirror.

The mail-two-worlds gap: Tmail (and the captain's app) send THROUGH the TernID
agent, whose store (~/.ternid/data) is NOT the repo. Cloud seats (CF5/CAI) read
git-POBOX, so anything sent agent-only never reaches them. CF5 flagged this
2026-11-09. This mirrors agent messages the wire doesn't already have into
private/POBOX/*.md so the cloud seats see them. Content-deduped (idempotent).

Run manually to backfill, and on the heartbeat to keep it synced. One direction
(agent -> wire); the POBOX -> agent importer is the other half of the bridge.
"""
import datetime
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "FlowCode"))
from ternid_agent_protocol import Client

SOCK = os.environ.get("TERNID_AGENT_SOCK", "/run/ternid/agent.sock")
POBOX = os.path.join(REPO, "private", "POBOX")


def mirror(pobox=None):
    pobox = pobox or POBOX
    c = Client(SOCK)
    existing = ""
    for f in glob.glob(os.path.join(pobox, "*.md")):
        try:
            existing += open(f, encoding="utf-8", errors="replace").read()
        except Exception:
            pass
    # every message in the agent, deduped by body, with its recipients aggregated
    seen = {}
    for a in c.list_accounts():
        disp = c.account_display(account_handle=a)
        for m in c.inbox(account=a):
            frm, subj = str(m.get("from", "")).lower(), str(m.get("subject", "")).lower()
            if "worker" in frm or "liveness" in subj or "heartbeat" in subj:
                continue                             # skip liveness beacons — not mail, content moves each beat
            k = str(m.get("body", ""))[:120]
            e = seen.setdefault(k, {"m": m, "to": set()})
            e["to"].add(disp)
    written = []
    for k, e in seen.items():
        if not k.strip() or k.strip() in existing:
            continue                                   # already on the wire — skip
        m, tos = e["m"], sorted(e["to"])
        frm = str(m.get("from", "?"))
        to = "crew" if len(tos) >= 5 else ", ".join(tos)
        try:
            dt = datetime.datetime.fromtimestamp(int(m.get("time", 0)))
        except (ValueError, TypeError, OSError):
            dt = datetime.datetime.now()
        slug = (re.sub(r"\W+", "-", (m.get("subject") or "").lower()).strip("-")[:40]) or "msg"
        fn = "%s-%s-to-%s-%s.md" % (dt.strftime("%Y-%m-%d-%H%M"), re.sub(r"\W+", "", frm),
                                    "crew" if to == "crew" else re.sub(r"\W+", "", to), slug)
        with open(os.path.join(pobox, fn), "w", encoding="utf-8") as f:
            f.write("%s\n\nFrom: %s\nTo: %s\nRe: %s\n\n%s\n"
                    % (dt.strftime("%H:%M %d/%m/%Y ACDT"), frm, to, m.get("subject", ""), m.get("body", "")))
        written.append(fn)
    return written


if __name__ == "__main__":
    out = mirror()
    for fn in out:
        print("mirrored:", fn)
    print("agent -> POBOX: %d message(s) brought to the wire" % len(out))
