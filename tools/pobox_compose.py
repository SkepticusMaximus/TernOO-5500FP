#!/usr/bin/env python3
"""pobox_compose — the captain's mail composer: makes the file manager a mail app.

Prompts for To / Cc / Subject, creates a correctly named + stamped mail file,
opens it for the body, then commits+pushes to origin master — the actual "send".
All sending happens in the dedicated POBOX worktree (~/.local/state/pobox/hbwt),
so the main working tree is never touched.

Usage:  python3 tools/pobox_compose.py            compose + send as Stevo
        python3 tools/pobox_compose.py --from CC  sign as another seat

Convention (POBOX/README.md): filename YYYY-MM-DD-HHMM-FROM-to-TO-topic.md;
first line in-file "HH:MM DD/MM/YYYY ACST" (Adelaide). Unsent drafts wait in
~/.local/state/pobox/outbox/ and are offered for sending on the next run;
sent mail is archived in outbox/sent/.
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys

try:
    from zoneinfo import ZoneInfo
    ADL = ZoneInfo("Australia/Adelaide")
except Exception:          # pragma: no cover — box runs Adelaide time anyway
    ADL = None

REPO = os.path.expanduser("~/dev/SkepticusMaximus/TernOO-5500FP")
WT = os.path.expanduser("~/.local/state/pobox/hbwt")
OUTBOX = os.path.expanduser("~/.local/state/pobox/outbox")
SENT = os.path.join(OUTBOX, "sent")


def now():
    return datetime.datetime.now(ADL) if ADL else datetime.datetime.now().astimezone()


def slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip()).strip("-").lower()
    return s or "no-subject"


def run(cwd, *a):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


def ensure_worktree():
    if not os.path.exists(WT):
        run(REPO, "git", "fetch", "--quiet", "origin", "master")
        run(REPO, "git", "worktree", "add", "--detach", WT, "origin/master")


def send(path):
    """Commit+push one mail file to origin master via the dedicated worktree."""
    name = os.path.basename(path)
    ensure_worktree()
    for _ in range(3):
        run(REPO, "git", "fetch", "--quiet", "origin", "master")
        run(WT, "git", "reset", "--hard", "origin/master")
        shutil.copy(path, os.path.join(WT, "private/POBOX", name))
        run(WT, "git", "add", "-f", f"private/POBOX/{name}")
        run(WT, "git", "commit", "-q", "-m", f"POBOX mail: {name}")
        if run(WT, "git", "push", "-q", "origin", "HEAD:master").returncode == 0:
            os.makedirs(SENT, exist_ok=True)
            shutil.move(path, os.path.join(SENT, name))
            print(f"SENT ✉  {name}")
            return True
    print(f"send failed after 3 tries (push race?) — draft kept: {path}")
    print("rerun this script to retry sending it.")
    return False


def main():
    ap = argparse.ArgumentParser(description="compose + send POBOX mail")
    ap.add_argument("--from", dest="sender", default="Stevo",
                    help="sender name for the From: field (default Stevo)")
    a = ap.parse_args()
    os.makedirs(OUTBOX, exist_ok=True)

    # offer any unsent drafts before composing new mail
    for d in sorted(f for f in os.listdir(OUTBOX) if f.endswith(".md")):
        if input(f"Unsent draft: {d} — send now? [y/N] ").strip().lower() == "y":
            send(os.path.join(OUTBOX, d))

    print("New mail — crew names: CC, CF5, CAI, Stevo, crew "
          "(workers: CC-worker, CF5-worker, CAI-worker)")
    to = input("To (comma-separated): ").strip()
    if not to:
        sys.exit("no addressee — aborted")
    cc = input("Cc (optional, Enter to skip): ").strip()
    subject = input("Subject: ").strip()
    if not subject:
        sys.exit("no subject — aborted")

    dt = now()
    stamp = dt.strftime("%H:%M %d/%m/%Y %Z")            # 21:47 16/07/2026 ACST
    to_part = "+".join(t.strip() for t in to.split(",") if t.strip())
    fname = f"{dt.strftime('%Y-%m-%d-%H%M')}-{a.sender}-to-{to_part}-{slug(subject)}.md"
    path = os.path.join(OUTBOX, fname)

    with open(path, "w") as f:
        f.write(f"{stamp}\n\n# {a.sender} → {to} — {subject}\n\n"
                f"From: {a.sender}\nTo: {to}\n")
        if cc:
            f.write(f"Cc: {cc}\n")
        f.write(f"Re: {subject}\n\n\n— {a.sender}\n")

    editor = os.environ.get("EDITOR")
    if editor:
        subprocess.call([editor, path])
    else:
        subprocess.Popen(["xdg-open", path],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"\nDraft: {path}")
    try:
        input("Write the body, SAVE the file, then press Enter here to SEND "
              "(Ctrl-C keeps it as a draft) ")
    except KeyboardInterrupt:
        print(f"\nkept as draft: {path}")
        return
    send(path)


if __name__ == "__main__":
    main()
