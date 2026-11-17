#!/usr/bin/env python3
"""Hermetic-mail sync daemon — CF5 `spec/hermetic-mail.md` §7.

ONE daemon does the git work for Huey's local seats. Seats' keyholders drop OUTGOING sealed
envelopes (and their card) into a spool directory; the daemon moves them into the wire clone's
pool/ (directory/), pushes, and pulls incoming. It handles ONLY sealed files — it holds no
keys and reads nothing — so it does not matter what user it runs as. It replaces mail_sync.py,
agent_to_pobox.py and pobox_to_agent.py, and it never writes plaintext anywhere.

  spool (outgoing):  ~/.config/ternoo/mail-spool/{pool,directory}/*
  wire clone:        ~/.local/state/ternoo/wire   (clone of the PRIVATE Tmail-POBOX)
  seats READ incoming from the clone's pool/ and the directory/.
"""
import glob
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hermetic_wire import Wire

WIRE_REMOTE = os.environ.get("TERNOO_WIRE_REMOTE", "https://github.com/SkepticusMaximus/Tmail-POBOX.git")
CLONE = os.path.expanduser("~/.local/state/ternoo/wire")
SPOOL = os.path.expanduser("~/.config/ternoo/mail-spool")


def _git(*a, cwd=CLONE):
    return subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True)


def ensure_clone():
    if not os.path.isdir(os.path.join(CLONE, ".git")):
        os.makedirs(os.path.dirname(CLONE), exist_ok=True)
        subprocess.run(["git", "clone", "--quiet", WIRE_REMOTE, CLONE])
        _git("config", "credential.helper", "store")
        _git("config", "user.email", "wire@ternoo")
        _git("config", "user.name", "hermetic-syncd")
    for sub in ("pool", "directory"):
        os.makedirs(os.path.join(CLONE, sub), exist_ok=True)


def run(push=True):
    """One sync pass. Returns a short status dict. Never raises — the daemon must not die."""
    out = {"spooled": 0, "pushed": False}
    try:
        ensure_clone()
        for sub in ("directory", "pool"):                      # move OUTGOING spool -> clone
            src = os.path.join(SPOOL, sub)
            if os.path.isdir(src):
                for f in glob.glob(os.path.join(src, "*")):
                    if os.path.basename(f).endswith((".age", ".card")):
                        shutil.move(f, os.path.join(CLONE, sub, os.path.basename(f)))
                        out["spooled"] += 1
        w = Wire(CLONE)
        w.sync(push=push)                                      # commit sealed files + pull + push
        out["pushed"] = push
    except Exception as e:
        out["error"] = str(e)[:80]
    return out


if __name__ == "__main__":
    print(run(push=("--no-push" not in sys.argv)))
