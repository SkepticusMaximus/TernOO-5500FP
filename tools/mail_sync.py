#!/usr/bin/env python3
"""mail_sync — one responsive, SAFE sync of the agent <-> git-POBOX bridge.

Runs on the captain's mail-call (Tmail Refresh) and after a Send, so mail moves in
seconds, not on the hourly heartbeat. Works ENTIRELY inside a dedicated git worktree
(~/.local/state/pobox/syncwt) so it never touches the main working tree or its
uncommitted files. Event-driven: fires only when triggered — nothing while idle, so it
doesn't burn the tether.

  pull the wire -> import new wire mail into the agent (Tmail sees cloud replies)
               -> mirror new agent mail onto the wire (cloud seats see it)
               -> commit + push.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
WT = os.path.expanduser("~/.local/state/pobox/syncwt")
sys.path.insert(0, HERE)


def _r(cwd, *a, timeout=90):
    try:
        return subprocess.run(["git", *a], cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except Exception as e:
        return subprocess.CompletedProcess(a, 1, "", str(e))


def _ensure_wt():
    if not os.path.isdir(os.path.join(WT, ".git")):
        os.makedirs(os.path.dirname(WT), exist_ok=True)
        _r(REPO, "fetch", "--quiet", "origin", "master")
        _r(REPO, "worktree", "add", "--detach", WT, "origin/master")


def sync(push=True):
    """Returns {imported, mirrored, pushed, ...}. Never raises; errors are reported in the dict."""
    out = {"imported": 0, "mirrored": 0, "pushed": False}
    _ensure_wt()
    _r(REPO, "fetch", "--quiet", "origin", "master")
    _r(WT, "reset", "--hard", "origin/master")          # clean, at the wire's tip
    _r(WT, "clean", "-fdq", "private/POBOX/")
    pobox = os.path.join(WT, "private", "POBOX")
    try:
        from pobox_to_agent import import_new
        out["imported"] = import_new(pobox=pobox)        # wire -> agent (state-deduped)
    except Exception as e:
        out["import_err"] = str(e)[:70]
    try:
        from agent_to_pobox import mirror
        out["mirrored"] = len(mirror(pobox=pobox))       # agent -> wire
    except Exception as e:
        out["mirror_err"] = str(e)[:70]
    if push:
        _r(WT, "add", "-f", "private/POBOX/")
        if _r(WT, "diff", "--cached", "--quiet").returncode != 0:
            _r(WT, "commit", "-q", "-m", "mail_sync: agent<->wire bridge")
            p = _r(WT, "push", "origin", "HEAD:master")
            out["pushed"] = (p.returncode == 0)
            if p.returncode != 0:
                out["push_note"] = "raced/offline; next sync self-heals"
    return out


if __name__ == "__main__":
    print(sync(push=("--no-push" not in sys.argv)))
