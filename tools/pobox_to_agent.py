#!/usr/bin/env python3
"""POBOX -> agent importer (the other leg of the mail bridge).

Brings NEW wire mail (git-POBOX *.md) into the TernID agent, so the captain's Tmail
(which reads the agent) sees mail that arrived only on the wire — e.g. a cloud seat's
reply committed to the repo.

Dedup is by FILENAME STATE (a json list of .md basenames already imported), NOT by
content — content-matching is fragile and re-created duplicates once (the agent has no
delete). Each .md is imported at most once, ever.

Usage:
  pobox_to_agent.py --seed     mark every current .md as already-imported, import nothing
  pobox_to_agent.py --dry      list what WOULD import, change nothing
  pobox_to_agent.py            import the new ones
"""
import datetime
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "FlowCode"))
from ternid_agent_protocol import Client

SOCK = os.environ.get("TERNID_AGENT_SOCK", "/run/ternid/agent.sock")
POBOX = os.path.join(REPO, "private", "POBOX")
STATE = os.path.expanduser("~/.ternid/pobox_imported.json")


def _state():
    try:
        return set(json.load(open(STATE)))
    except Exception:
        return set()


def _save(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(sorted(s), open(STATE, "w"), indent=0)


def _parse(fname, txt):
    lines = txt.splitlines()

    def hdr(k):
        for ln in lines[:12]:
            m = re.match(r"^%s:\s*(.+)" % k, ln)
            if m:
                return m.group(1).strip()
        return ""
    frm = re.sub(r"\s*\(.*\)", "", hdr("From")) or (re.search(r"-([A-Za-z0-9+]+)-to-", fname) or [0, "?"])[1]
    to = hdr("To") or (re.search(r"-to-([A-Za-z0-9+]+)-", fname) or [0, "?"])[1]
    subj = hdr("Re") or fname.rsplit(".", 1)[0]
    idx = next((i for i, l in enumerate(lines) if l.startswith("Re:")), None)
    body = "\n".join(lines[idx + 1:]).strip() if idx is not None else txt
    return str(frm), str(to), subj, body


def _time(fname):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:-(\d{2})(\d{2}))?", fname)
    if not m:
        return int(datetime.datetime.now().timestamp())
    try:
        return int(datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                                     int(m.group(4) or 0), int(m.group(5) or 0)).timestamp())
    except ValueError:
        return int(datetime.datetime.now().timestamp())


def _new_files(pobox):
    done = _state()
    return done, [os.path.basename(p) for p in sorted(glob.glob(os.path.join(pobox, "*.md")))
                  if os.path.basename(p) not in done
                  and "worker" not in os.path.basename(p).lower()
                  and "heartbeat" not in os.path.basename(p).lower()]


def import_new(pobox=None, dry=False, seed=False):
    pobox = pobox or POBOX
    done, new = _new_files(pobox)
    if seed:
        _save(done | {os.path.basename(p) for p in glob.glob(os.path.join(pobox, "*.md"))})
        return 0
    if dry:
        return new                                   # list of filenames that would import
    c = Client(SOCK)
    accounts = {c.account_display(account_handle=a): a for a in c.list_accounts()}

    def recips(to_str):
        toks = [t for t in re.split(r"[^A-Za-z0-9]+", to_str or "") if t]
        if any(t.lower().startswith("crew") for t in toks):
            return list(accounts.values())
        out = []
        for t in toks:
            norm = re.sub(r"(worker|cloud|hp|lenny)$", "", t, flags=re.I)
            for disp, h in accounts.items():
                if disp.lower() in (t.lower(), norm.lower()):
                    out.append(h)
        return out

    imported = 0
    for fn in new:
        try:
            txt = open(os.path.join(pobox, fn), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        frm, to, subj, body = _parse(fn, txt)
        for h in recips(to):
            try:
                c.call("import_message", account=h, from_display=frm, subject=subj, body=body, time=_time(fn))
                imported += 1
            except Exception:
                pass
        done.add(fn)
    _save(done)
    return imported


if __name__ == "__main__":
    if "--seed" in sys.argv:
        import_new(seed=True)
        print("seeded: all current .md marked imported; nothing sent to the agent")
    elif "--dry" in sys.argv:
        new = import_new(dry=True)
        print("would import %d file(s):" % len(new))
        for f in new[:30]:
            print("  ", f)
    else:
        print("POBOX -> agent: imported %d message(s)" % import_new())
