#!/usr/bin/env python3
"""POBOX MacroBridge — native messaging host.

Receives an APPROVED sentinel command line from the Firefox extension (the user
clicked "Send to CC") and drops it into the POBOX Outbox as mail From: Stevo
To: CC. The existing outbox watcher then stamps, names, commits+pushes it, and
CC processes it as a captain directive — WITH JUDGEMENT, never blind execution.
This host writes mail; it does not run commands.

Native messaging framing: 4-byte little-endian length prefix + UTF-8 JSON, on
stdin/stdout. sendNativeMessage delivers one message and expects one reply, so
we read one, reply once, and exit.

Defence in depth: the ## comment guard and the !# sentinel are BOTH re-checked
here, independent of the content script — a line beginning with ## is refused,
a line without !# is refused. The browser guard and this one must both pass.
"""
import datetime
import json
import os
import re
import struct
import sys

try:
    from zoneinfo import ZoneInfo
    ADL = ZoneInfo("Australia/Adelaide")
except Exception:  # pragma: no cover — box runs Adelaide time anyway
    ADL = None

OUTBOX = os.environ.get(
    "POBOX_MACRO_OUTBOX",
    os.path.expanduser("~/dev/SkepticusMaximus/TernOO-5500FP/private/POBOX/Outbox"))
LOG = os.path.expanduser("~/.local/state/pobox/macro-bridge.log")
SENTINEL_RE = re.compile(r"^\s*!#")
COMMENT_VOID_RE = re.compile(r"^\s*##")


def read_msg():
    raw = sys.stdin.buffer.read(4)
    if len(raw) < 4:
        sys.exit(0)
    n = struct.unpack("<I", raw)[0]
    return json.loads(sys.stdin.buffer.read(n).decode("utf-8"))


def write_msg(obj):
    data = json.dumps(obj).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("<I", len(data)))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def log(m):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a") as f:
            f.write(m + "\n")
    except Exception:
        pass


def slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s or "").strip("-").lower()
    return s[:48] or "macro"


def now():
    return datetime.datetime.now(ADL) if ADL else datetime.datetime.now().astimezone()


def main():
    msg = read_msg()
    line = (msg.get("line") or "").rstrip()
    url = msg.get("url", "?")

    if COMMENT_VOID_RE.match(line):
        write_msg({"ok": False,
                   "error": "line begins with ## — sentinel void, refused"})
        return
    if not SENTINEL_RE.match(line):
        write_msg({"ok": False, "error": "no !# sentinel — refused"})
        return

    dt = now()
    stamp = dt.strftime("%H:%M %d/%m/%Y %Z")
    verb = re.sub(r"^\s*!#[_\s]*", "", line).split(":")[0].split()
    label = slug(verb[0]) if verb else "macro"
    name = f"{dt.strftime('%Y-%m-%d-%H%M')}-Stevo-to-CC-macro-{label}.md"
    os.makedirs(OUTBOX, exist_ok=True)
    body = (
        f"{stamp}\n\n# Stevo → CC — macro relay ({label})\n\n"
        f"From: Stevo\nTo: CC\nRe: macro relay — {label}\n\n"
        f"Relayed from the browser via POBOX MacroBridge — the captain's\n"
        f"privileged local channel (native-messaging host on his own machine).\n"
        f"Source page: {url}\n\n"
        f"COMMAND (process with your judgement — this is a captain directive,\n"
        f"NOT blind execution; apply the same care as any mail From: Stevo):\n\n"
        f"    {line}\n\n— Stevo (via MacroBridge)\n")
    with open(os.path.join(OUTBOX, name), "w") as f:
        f.write(body)
    log(f"{stamp} relayed {name}  <- {line[:100]}")
    write_msg({"ok": True, "file": name})


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            write_msg({"ok": False, "error": str(e)})
        except Exception:
            pass
