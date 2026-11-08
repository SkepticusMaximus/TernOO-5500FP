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
import datetime

SRC = os.path.expanduser("~/.config/ternoo/todo.json")
SEATS = ["Stevo", "CC", "CCC", "CF5", "CAI", "CO5", "Professor"]
_STAT = {"pending": "· ", "progress": "▸ ", "complete": "✓ "}
_PRI = {1: "[+]", 0: "[0]", -1: "[−]"}


def _line(it):
    pr = _PRI.get(it.get("priority", 0), "[0]")
    area = f"  _({it['area']})_" if it.get("area") else ""
    return f"- {_STAT.get(it.get('status'), '· ')}{pr} **{it['id']}** ({it.get('status')}) — {it.get('text','')}{area}"


def export(repo):
    """Write the mirror under repo/private/POBOX/terndo/. Returns the dir, or None if no store."""
    try:
        d = json.load(open(SRC))
    except Exception:
        return None
    items = d.get("items", [])
    out_dir = os.path.join(repo, "private", "POBOX", "terndo")
    os.makedirs(os.path.join(out_dir, "by-seat"), exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    mirror = {
        "_mirror_of": "~/.config/ternoo/todo.json — this is a READ-ONLY export",
        "_exported": stamp,
        "_how_to_slate": "Mail the task; the local TernDO store is the single writer (one writer, many readers).",
        "seq": d.get("seq"),
        "items": items,
    }
    json.dump(mirror, open(os.path.join(out_dir, "todo.json"), "w"), indent=1)

    for seat in SEATS:
        mine = [it for it in items if seat in (it.get("assignees") or [])]
        open_mine = [it for it in mine if it.get("status") != "complete"]
        done = [it for it in mine if it.get("status") == "complete"]
        with open(os.path.join(out_dir, "by-seat", f"{seat}.md"), "w") as f:
            f.write(f"# TernDO — tasks naming {seat}\n\n")
            f.write(f"_Read-only mirror, exported {stamp}. To slate/change a task: mail it; "
                    "TernDO ingests (one writer, many readers). Session-start protocol step 3._\n\n")
            if not mine:
                f.write("No open or closed tasks name this seat.\n")
                continue
            f.write(f"## Open ({len(open_mine)})\n")
            for it in sorted(open_mine, key=lambda x: (-(x.get("priority") or 0), x["id"])):
                f.write(_line(it) + "\n")
            if done:
                f.write(f"\n## Done ({len(done)})\n")
                for it in sorted(done, key=lambda x: x["id"]):
                    f.write(_line(it) + "\n")
    return out_dir


if __name__ == "__main__":
    repo = os.environ.get("TERNOO_REPO", os.path.expanduser("~/dev/SkepticusMaximus/TernOO-5500FP"))
    d = export(repo)
    print("TernDO mirror ->", d if d else "(no local store found)")
