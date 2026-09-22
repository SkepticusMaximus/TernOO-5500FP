"""pobox_store.py — face-free mailbox primitives.

The POBOX paths, letter listing, and header parsing, importable by ANY
face (DPG mail tab, web server, future native) without dragging a
toolkit along. Split out of terndoc_mail when the web face showed the
layering smell: transport-adjacent logic must never live in a face file.

Added: 22 Sep 2026 (Road A). Authors: Stevo + Claude.
"""

from __future__ import annotations

import os
import re

_HERE = os.path.dirname(os.path.abspath(__file__))
POBOX = os.path.join(os.path.dirname(_HERE), "private", "POBOX")
OUTBOX = os.path.join(POBOX, "Outbox")
ROSTER = "CC, CF5, CAI, Stevo, crew"


def list_mail():
    """Letter filenames, dated-newest first; README and friends last."""
    if not os.path.isdir(POBOX):
        return []
    out = [f for f in os.listdir(POBOX)
           if os.path.isfile(os.path.join(POBOX, f)) and f.endswith(".md")]
    return sorted(out, key=lambda f: (f[0].isdigit(), f), reverse=True)


def parse_headers(text):
    """Best-effort From/To/Subject from the ship's letter conventions."""
    hdr = {"from": "?", "to": "?", "subject": ""}
    for ln in text.splitlines()[:14]:
        m = re.match(r"(From|To|Subject):\s*(.+)", ln.strip())
        if m:
            hdr[m.group(1).lower()] = m.group(2).strip()
        m2 = re.match(r"#\s+(.*)", ln.strip())
        if m2 and not hdr["subject"]:
            hdr["subject"] = m2.group(1)
    return hdr


def drop_letter(to, subject, body_md, sender="CC"):
    """Write a letter into the Outbox — the drop IS the send (the standing
    watcher stamps, names, commits, pushes, archives). Returns the path."""
    if not body_md.strip():
        raise ValueError("refusing an empty letter")
    os.makedirs(OUTBOX, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-",
                  (subject or "letter").lower()).strip("-")[:48] or "letter"
    path = os.path.join(OUTBOX, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"To: {to or 'crew'}\nFrom: {sender}\n"
                f"Subject: {subject or 'no subject'}\n\n{body_md}\n")
    return path
