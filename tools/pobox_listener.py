#!/usr/bin/env python3
"""pobox_listener — watch the private/POBOX mailbox on origin and route new mail
to per-recipient inbox queues + (optional) desktop notifications.

WHY origin, not local: private/ is gitignored, so CF5/CAI post mail via the GitHub
API — new mail lands on origin/master, never the local tree until pulled. So we poll
ORIGIN: fetch, then read each new message's header straight off origin
(`git show origin/master:...`) without touching the working tree.

WHAT it does per new message:
  * parse From: / To: / CC: (recipients = known crew tokens in those lines; the
    filename YYYY-MM-DD-FROM-to-TO-thread.md is the fallback + the thread label),
  * append it to each recipient's inbox queue  (state/inbox-<AGENT>.json),
  * fire a desktop notification for the configured notify set (default CC,Stevo).

It NEVER edits the box (read your mail, act, leave it). This is the shared transport
layer; who then ACTS on a queue (CC's cron, CF5/CAI's routines) rides on top.

Session-trial by default; promote to a systemd --user service once it behaves.
"""
import argparse
import json
import os
import re
import subprocess
import time

AGENTS = ["CC", "CF5", "CAI", "Stevo"]                 # known crew tokens
MSG_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-.+\.md$")     # dated message files only
NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-([A-Za-z0-9]+)-to-([A-Za-z0-9,]+)-(.+)\.md$")


def sh(args, cwd):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def origin_messages(repo):
    fetch = sh(["git", "fetch", "--quiet", "origin", "master"], repo)
    if fetch.returncode != 0:
        raise RuntimeError(fetch.stderr.strip() or "git fetch failed")
    r = sh(["git", "ls-tree", "--name-only", "origin/master", "private/POBOX/"], repo)
    return [os.path.basename(l.strip()) for l in r.stdout.splitlines()
            if MSG_RE.match(os.path.basename(l.strip()))]


def read_message(repo, name):
    return sh(["git", "show", f"origin/master:private/POBOX/{name}"], repo).stdout


def parse(name, body):
    frm_hdr, to_line, subject = "", "", ""
    for line in body.splitlines()[:14]:
        l = line.strip()
        low = l.lower()
        if low.startswith("from:") and not frm_hdr:
            frm_hdr = l.split(":", 1)[1].strip()
        elif low.startswith(("to:", "cc:")):
            to_line += " " + l
        elif low.startswith("re:") and not subject:
            subject = l.split(":", 1)[1].strip()
    m = NAME_RE.match(name)
    fn_from, fn_to = (m.group(1), m.group(2)) if m else ("?", "")
    thread = (m.group(3) if m else name[:-3]).replace("-", " ")
    # From: first known agent named in the From: header, else the filename field.
    frm = next((a for a in AGENTS if re.search(rf"\b{a}\b", frm_hdr)), None) or fn_from
    # Recipients: known agents in the To:/CC: lines. Strip the carbon-copy keyword
    # "CC:" first so it doesn't false-match the agent named CC (real CC recipients,
    # written "CC (…)" without a trailing colon, still match).
    scan = re.sub(r"\bCC:\s*", " ", to_line)
    recips = [a for a in AGENTS if re.search(rf"\b{a}\b", scan)]
    if not recips and fn_to:
        recips = [a for a in AGENTS if a.lower() in fn_to.lower()]
    if not subject:
        first = next((x for x in body.splitlines() if x.strip()), thread)
        subject = first.lstrip("# ").strip()
    return {"file": name, "from": frm, "to": recips, "thread": thread, "subject": subject}


def notify(title, msg):
    try:
        subprocess.run(["notify-send", "-a", "POBOX", "-i", "mail-message-new",
                        title, msg], timeout=5)
    except Exception:
        pass


def _load(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def _save(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.replace(tmp, p)


def run_pass(repo, state_dir, notify_agents, log):
    seen_p = os.path.join(state_dir, "seen.json")
    seen = set(_load(seen_p, []))
    found = []
    for name in origin_messages(repo):
        if name in seen:
            continue
        meta = parse(name, read_message(repo, name))
        found.append(meta)
        for a in meta["to"]:
            ip = os.path.join(state_dir, f"inbox-{a}.json")
            q = _load(ip, [])
            q.append({**meta, "unread": True})
            _save(ip, q)
        hit = [a for a in meta["to"] if a in notify_agents]
        if hit:
            notify(f"POBOX — {meta['from']} to {', '.join(meta['to'])}", meta["thread"])
        log(f"[pobox] NEW {name}  from={meta['from']}  to={meta['to']}  "
            f"thread='{meta['thread']}'" + (f"  -> desktop {hit}" if hit else
                                            "  -> queued (no desktop for these)"))
        seen.add(name)
    _save(seen_p, sorted(seen))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=os.path.expanduser(
        "~/dev/SkepticusMaximus/TernOO-5500FP"))
    ap.add_argument("--state-dir", default=os.path.expanduser("~/.local/state/pobox"))
    ap.add_argument("--interval", type=int, default=45)
    ap.add_argument("--notify", default="CC,Stevo",
                    help="recipients whose mail also fires a desktop popup")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    notify_agents = {x.strip() for x in a.notify.split(",") if x.strip()}

    def log(m):
        print(m, flush=True)

    log(f"[pobox] listener up — repo={a.repo}  interval={a.interval}s  "
        f"desktop-notify={sorted(notify_agents)}  state={a.state_dir}")
    while True:
        try:
            run_pass(a.repo, a.state_dir, notify_agents, log)
        except Exception as e:                          # keep the daemon alive
            log(f"[pobox] pass error: {e}")
        if a.once:
            break
        time.sleep(a.interval)


if __name__ == "__main__":
    main()
