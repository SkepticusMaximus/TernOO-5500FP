#!/usr/bin/env python3
"""pobox_outbox_watcher — save = send: the file manager IS the mail app.

Watches ~/POBOX/Outbox. Any finished .md that lands there (dropped or saved)
is automatically: stamped (Adelaide first line "HH:MM DD/MM/YYYY ACST"),
named to convention (YYYY-MM-DD-HHMM-FROM-to-TO-topic.md), committed+pushed
to origin master (that push IS delivery — the shared box lives on origin),
archived to ~/POBOX/Sent/, and confirmed with a desktop notification.

The captain's workflow, zero terminal:
  right-click > New Document > "POBOX mail" (template) anywhere,
  fill To: / Re:, write the body, then DROP the file into ~/POBOX/Outbox —
  dropping it in the out-tray is the send gesture, like a real desk.

Safety: a file with no "To:" header is held (notified once) until edited —
so a half-written draft saved in the wrong folder never sends. Failed pushes
retry every minute. ~/POBOX/Inbox is a symlink into the repo's box; this
watcher also fast-forwards the repo every 5 min so the Inbox stays fresh.

Runs as a systemd --user service (tools/pobox-outbox.service).
"""
import datetime
import hashlib
import os
import re
import subprocess
import time

try:
    from zoneinfo import ZoneInfo
    ADL = ZoneInfo("Australia/Adelaide")
except Exception:  # pragma: no cover — the box runs Adelaide time anyway
    ADL = None

REPO = os.path.expanduser("~/dev/SkepticusMaximus/TernOO-5500FP")
WT = os.path.expanduser("~/.local/state/pobox/hbwt")
BASE = os.path.expanduser("~/POBOX")
OUTBOX = os.path.join(BASE, "Outbox")
SENT = os.path.join(BASE, "Sent")
DRAFTS = os.path.join(BASE, "Drafts")
POLL = 2            # seconds between Outbox scans
SETTLE = 2          # stable scans required before sending (~4-6 s after drop)
PULL_EVERY = 300    # keep the repo (= Inbox symlink) fresh
RETRY_EVERY = 60    # failed-push retry interval
STAMP_RE = re.compile(r"^\d{2}:\d{2} \d{2}/\d{2}/\d{4}")


def now():
    return datetime.datetime.now(ADL) if ADL else datetime.datetime.now().astimezone()


def run(cwd, *a):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)


def notify(title, body):
    subprocess.Popen(["notify-send", "-a", "POBOX", title, body],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip()).strip("-").lower()
    return s[:60] or "mail"


def header(text, key):
    m = re.search(rf"^{key}:\s*(.+)$", text, re.M | re.I)
    return m.group(1).strip() if m else ""


def ensure_worktree():
    if not os.path.exists(WT):
        run(REPO, "git", "fetch", "--quiet", "origin", "master")
        run(REPO, "git", "worktree", "add", "--detach", WT, "origin/master")


def deliver(name, content):
    """Commit+push one mail file to origin master via the dedicated worktree."""
    ensure_worktree()
    for _ in range(3):
        run(REPO, "git", "fetch", "--quiet", "origin", "master")
        run(WT, "git", "reset", "--hard", "origin/master")
        with open(os.path.join(WT, "private/POBOX", name), "w") as f:
            f.write(content)
        run(WT, "git", "add", "-f", f"private/POBOX/{name}")
        run(WT, "git", "commit", "-q", "-m", f"POBOX mail: {name}")
        if run(WT, "git", "push", "-q", "origin", "HEAD:master").returncode == 0:
            return True
        time.sleep(2)
    return False


def process(path):
    """Returns ('sent', filename, to) | ('hold', reason) | ('retry', reason)."""
    with open(path) as f:
        text = f.read()
    to = header(text, "To")
    if not to:
        return ("hold", "no To: header — add one (e.g. 'To: CC') and re-save")
    sender = header(text, "From") or "Stevo"
    text = re.sub(r"<!--.*?-->\s*", "", text, flags=re.S)  # strip template hints
    dt = now()
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    if not STAMP_RE.match(first):
        text = f"{dt.strftime('%H:%M %d/%m/%Y %Z')}\n\n" + text.lstrip("\n")
    topic = (header(text, "Re")
             or next((l[2:].strip() for l in text.splitlines()
                      if l.startswith("# ")), "")
             or os.path.splitext(os.path.basename(path))[0])
    to_part = "+".join(t.strip() for t in re.split(r"[,;]", to) if t.strip())
    name = f"{dt.strftime('%Y-%m-%d-%H%M')}-{sender}-to-{to_part}-{slug(topic)}.md"
    if not deliver(name, text):
        return ("retry", "push to origin failed — retrying every minute")
    os.makedirs(SENT, exist_ok=True)
    with open(os.path.join(SENT, name), "w") as f:
        f.write(text)
    os.remove(path)
    return ("sent", name, to)


def scan_outbox():
    try:
        return [e for e in os.scandir(OUTBOX)
                if e.is_file() and e.name.endswith(".md")
                and not e.name.startswith(".") and not e.name.endswith("~")]
    except FileNotFoundError:
        os.makedirs(OUTBOX, exist_ok=True)
        return []


def main():
    for d in (OUTBOX, SENT, DRAFTS):
        os.makedirs(d, exist_ok=True)
    seen = {}       # path -> [ (size, mtime), stable_scans ]
    parked = {}     # path -> {"h": content-hash, "kind": hold|retry, "at": ts}
    last_pull = 0.0
    while True:
        if time.time() - last_pull > PULL_EVERY:
            run(REPO, "git", "fetch", "--quiet", "origin", "master")
            run(REPO, "git", "pull", "--ff-only", "--quiet", "origin", "master")
            last_pull = time.time()
        live = set()
        for e in scan_outbox():
            st = e.stat()
            sig = (st.st_size, st.st_mtime)
            live.add(e.path)
            prev = seen.get(e.path)
            if not prev or prev[0] != sig:
                seen[e.path] = [sig, 0]
                continue
            prev[1] += 1
            if prev[1] < SETTLE:
                continue
            with open(e.path, "rb") as f:
                h = hashlib.sha1(f.read()).hexdigest()
            p = parked.get(e.path)
            if p and p["h"] == h:
                if p["kind"] == "hold":
                    continue                       # wait for the captain to edit
                if time.time() - p["at"] < RETRY_EVERY:
                    continue                       # not yet time to retry push
            res = process(e.path)
            if res[0] == "sent":
                _, name, to = res
                notify("POBOX ✉ SENT", f"{name}\nto: {to}")
                seen.pop(e.path, None)
                parked.pop(e.path, None)
            else:
                kind, reason = res
                if not p or p["h"] != h:           # notify once per content version
                    notify("POBOX ✋ not sent", f"{e.name}: {reason}")
                parked[e.path] = {"h": h, "kind": kind, "at": time.time()}
        for d in (seen, parked):
            for pth in [p for p in d if p not in live]:
                d.pop(pth)
        time.sleep(POLL)


if __name__ == "__main__":
    main()
