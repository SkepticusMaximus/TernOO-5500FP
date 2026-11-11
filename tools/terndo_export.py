#!/usr/bin/env python3
"""Export the local TernDO task store to the repo so CLOUD SEATS can read it.

CF5's flag (2026-11-08): step 3 of the session-start protocol — "check TernDO for
tasks naming your seat" — can't run from a wiped cloud container, because the store
lives only in ~/.config/ternoo/todo.json on the captain's machine and isn't in the repo.

Fix, per CF5: ONE WRITER (the local TernDO store, mirrored here by the heartbeat),
MANY READERS (this repo export). Writes stay local; a seat that wants to slate a task
does it by mail and TernDO ingests it — nothing forks.

Writes under <repo>/private/POBOX/terndo/ :
  todo.json          — full read-only mirror of the store
  by-seat/<SEAT>.md  — per-seat digest of the tasks naming that seat (session-start step 3)
"""
import json
import os
import re
import datetime

SRC = os.path.expanduser("~/.config/ternoo/todo.json")
# ONE WRITER: only the host holding the authoritative TernDO store exports it. Huey
# (where the captain's TernDO GUI writes) carries this marker; the HP does not, so the
# HP heartbeat stops clobbering the wire mirror with its stale copy (the frozen-at-Sunday
# bug CF5/CCC kept flagging). Create it on the authoritative box: touch ~/.config/ternoo/terndo.authoritative
MARKER = os.path.expanduser("~/.config/ternoo/terndo.authoritative")
SEATS = ["Stevo", "CC", "CCC", "CF5", "CAI", "CO5", "Professor"]


def _write_if_changed(path, new_text, volatile=r"(?m)^.*_exported.*$|exported \d{4}-\d\d-\d\d[^\n]*"):
    """Write only when the MEANINGFUL content changed — strip the volatile 'exported'
    timestamp before comparing, so an unchanged task list doesn't churn a new commit
    every run (the 3-min timer / hourly heartbeat spam). Returns True if written.
    volatile=None compares full content (use when the time-ish fields are already
    idempotent — shared with the list's seq/export-time, so they only move on a real change)."""
    def norm(t):
        return re.sub(volatile, "", t or "") if volatile else (t or "")
    try:
        if norm(open(path).read()) == norm(new_text):
            return False
    except Exception:
        pass
    with open(path, "w") as f:
        f.write(new_text)
    return True
_STAT = {"pending": "· ", "progress": "▸ ", "complete": "✓ "}
_PRI = {1: "[+]", 0: "[0]", -1: "[−]"}


def _line(it):
    pr = _PRI.get(it.get("priority", 0), "[0]")
    area = f"  _({it['area']})_" if it.get("area") else ""
    return f"- {_STAT.get(it.get('status'), '· ')}{pr} **{it['id']}** ({it.get('status')}) — {it.get('text','')}{area}"


def export(repo):
    """Write the mirror under repo/private/POBOX/terndo/. Returns True if anything
    actually changed (so callers commit only on a real change), False/None otherwise.
    Only the authoritative host (carrying MARKER) exports — one writer, many readers."""
    if not os.path.exists(MARKER):
        return None                    # not the authoritative store; don't clobber the wire
    try:
        d = json.load(open(SRC))
    except Exception:
        return None
    items = d.get("items", [])
    out_dir = os.path.join(repo, "private", "POBOX", "terndo")
    os.makedirs(os.path.join(out_dir, "by-seat"), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    changed = False

    mirror = {
        "_mirror_of": "~/.config/ternoo/todo.json — this is a READ-ONLY export",
        "_exported": stamp,
        "_how_to_slate": "Mail the task; the local TernDO store is the single writer (one writer, many readers).",
        "seq": d.get("seq"),
        "items": items,
    }
    changed |= _write_if_changed(os.path.join(out_dir, "todo.json"),
                                 json.dumps(mirror, indent=1))
    # The list's EFFECTIVE export time — old if the list didn't change (idempotent). Share it
    # (with the seq) on every per-seat page so a seat whose own tasks didn't change doesn't see
    # a per-page stamp OLDER than todo.json and read it as "stale" (CF5's flag, 2026-11-11).
    try:
        asof = json.load(open(os.path.join(out_dir, "todo.json"))).get("_exported", stamp)
    except Exception:
        asof = stamp
    seq = d.get("seq")

    for seat in SEATS:
        mine = [it for it in items if seat in (it.get("assignees") or [])]
        open_mine = [it for it in mine if it.get("status") != "complete"]
        done = [it for it in mine if it.get("status") == "complete"]
        lines = [f"# TernDO — tasks naming {seat}\n\n",
                 f"_Read-only mirror — full list at seq {seq}, as of {asof}. To slate/change a "
                 "task: mail it; TernDO ingests (one writer, many readers). Session-start step 3._\n\n"]
        if not mine:
            lines.append("No open or closed tasks name this seat.\n")
        else:
            lines.append(f"## Open ({len(open_mine)})\n")
            for it in sorted(open_mine, key=lambda x: (-(x.get("priority") or 0), x["id"])):
                lines.append(_line(it) + "\n")
            if done:
                lines.append(f"\n## Done ({len(done)})\n")
                for it in sorted(done, key=lambda x: x["id"]):
                    lines.append(_line(it) + "\n")
        # seq + asof are idempotent (move only on a real list change), so full-content compare:
        # every list change refreshes ALL pages' freshness; idle runs rewrite nothing.
        changed |= _write_if_changed(os.path.join(out_dir, "by-seat", f"{seat}.md"),
                                     "".join(lines), volatile=None)
    return changed


if __name__ == "__main__":
    repo = os.environ.get("TERNOO_REPO", os.path.expanduser("~/dev/SkepticusMaximus/TernOO-5500FP"))
    d = export(repo)
    print("TernDO mirror ->", d if d else "(no local store found)")
