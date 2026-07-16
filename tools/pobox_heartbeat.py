#!/usr/bin/env python3
"""pobox_heartbeat — CC's scheduled worker: wake (via cron), read the POBOX over
LOCAL git (no connector needed — CC has the checkout), and post a heartbeat back so
a scheduled agent visibly reaches the mailbox on a timer. CC's leg of the mesh.

Runs entirely in a DEDICATED git worktree (~/.local/state/pobox/hbwt) so it never
touches the main working tree (the flagged .fc files stay untouched) and can
`reset --hard origin/master` each beat — race-clean. If a push loses a race, it just
logs and the NEXT beat self-heals by resetting to the new origin tip.

Trial cadence posts a heartbeat file every run; the production version will be
event-driven (post only when there's real mail for CC) so it never spams history.
"""
import datetime
import json
import os
import re
import subprocess

REPO = os.path.expanduser("~/dev/SkepticusMaximus/TernOO-5500FP")
WT = os.path.expanduser("~/.local/state/pobox/hbwt")
STATE = os.path.expanduser("~/.local/state/pobox")
# A FIXED liveness SLOT, not dated mail: the date in the filename is frozen on purpose
# so the heartbeat OVERWRITES one file in place (linear history on a single path) rather
# than spawning a new file — and a new listener notification — every day. (CF5 audit
# note, 2026-07-14.) Cadence is hourly liveness (cron), per CF5's ratified cadence call.
HB = "private/POBOX/2026-07-16-CC-worker-to-Stevo-heartbeat.md"


def run(cwd, *a):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


def log(m):
    os.makedirs(STATE, exist_ok=True)
    with open(os.path.join(STATE, "heartbeat.log"), "a") as f:
        f.write(m + "\n")
    print(m)


def ensure_worktree():
    if not os.path.exists(WT):
        run(REPO, "git", "fetch", "--quiet", "origin", "master")
        run(REPO, "git", "worktree", "add", "--detach", WT, "origin/master")


def main():
    now = datetime.datetime.now().strftime("%H:%M %d/%m/%Y")
    ensure_worktree()
    run(REPO, "git", "fetch", "--quiet", "origin", "master")
    run(WT, "git", "reset", "--hard", "origin/master")      # clean, at origin tip (safe: dedicated wt)
    run(WT, "git", "clean", "-fdq", "private/POBOX/")
    msgs = [b for l in run(WT, "git", "ls-tree", "--name-only", "origin/master",
                           "private/POBOX/").stdout.splitlines()
            if re.match(r"\d{4}-\d{2}-\d{2}-.+\.md$", (b := os.path.basename(l.strip())))]
    try:
        with open(os.path.join(STATE, "inbox-CC.json")) as f:
            unread = sum(1 for m in json.load(f) if m.get("unread"))
    except Exception:
        unread = 0
    with open(os.path.join(WT, HB), "w") as f:
        f.write(
            f"{now} ACST\n\n"
            "# CC-worker heartbeat\nFrom: CC-worker\nTo: Stevo\n"
            "Re: scheduled-worker liveness\n\n"
            f"Last woke: {now} (Adelaide)\n"
            f"POBOX messages on origin: {len(msgs)}\n"
            f"Unread for CC: {unread}\n\n"
            "CC's cron-driven worker — reads the box over local git and posts back, "
            "proving the\nautonomous-worker leg wakes on a clock and reaches the "
            "mailbox. Overwrites in place.\n")
    run(WT, "git", "add", "-f", HB)
    if not run(WT, "git", "status", "--porcelain", HB).stdout.strip():
        log(f"[hb] {now} no change"); return
    run(WT, "git", "commit", "-q", "-m", f"CC heartbeat {now}")
    p = run(WT, "git", "push", "origin", "HEAD:master")
    if p.returncode != 0:
        log(f"[hb] {now} push raced — next beat self-heals: {p.stderr.strip()[:100]}")
    else:
        log(f"[hb] {now} beat posted (msgs={len(msgs)} unread={unread})")


if __name__ == "__main__":
    main()
