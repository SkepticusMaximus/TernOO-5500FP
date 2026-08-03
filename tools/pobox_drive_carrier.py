#!/usr/bin/env python3
"""pobox_drive_carrier — the last-mile ferry.

Carry crew CHAT-SEAT replies from the shared Google Drive back-channel INTO
private/POBOX/ (commit + push), so a seat that holds no git push credential (the
CF5 / CAI cloud seats) still lands in the box. The git-side WORKERS
(CF5-worker / CAI-worker) already push directly and are ignored here.

WHY THIS EXISTS: pobox_listener watches ORIGIN for new POBOX commits — but the
cloud seats can only DROP on Drive. So their rulings sat marooned in Drive until
carried by hand (the recurring "ferry" pain). This closes the gap: poll the Drive
folder, export new seat drops to text, land them in the box, commit + push — then
pobox_listener notifies as usual. Idempotent; safe on a timer.

ONE-TIME SETUP (the only step that needs a human — it authorises YOUR account):
    rclone config
      n) new remote   name> gdrive   Storage> drive
      client_id/secret> (blank — Enter)     scope> drive.readonly
      (shared drive? if asked, yes → pick the crew drive)
      Use auto config> y   → browser → sign in as mskepticus@gmail → allow
Then a dry check:  rclone lsjson gdrive: --drive-root-folder-id 0APKIflT86y5BUk9PVA
                   | python3 -c "import sys,json;print(len(json.load(sys.stdin)),'docs')"

RUN:  python3 tools/pobox_drive_carrier.py           (once)
      python3 tools/pobox_drive_carrier.py --dry-run  (list what WOULD carry)
On a timer: a systemd --user timer every ~5 min (added once this is proven live).

STATUS: scaffolding — PENDING rclone auth. Not yet proven end-to-end; the carry
logic is verified against real Drive only after the one-time setup above.

Date: 2026-08-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POBOX = os.path.join(REPO, 'private', 'POBOX')
STATE = os.path.join(REPO, 'state', 'carried-drive-ids.json')
REMOTE = os.environ.get('POBOX_DRIVE_REMOTE', 'gdrive')
FOLDER_ID = os.environ.get('POBOX_DRIVE_FOLDER_ID', '0APKIflT86y5BUk9PVA')
# Chat-seat drops only. The git-side workers push directly, so we never carry them.
CARRY_PREFIXES = ('CF5-Submit', 'CAI-Submit')


def _rclone(*args):
    return subprocess.run(['rclone', *args, '--drive-root-folder-id', FOLDER_ID],
                          capture_output=True, text=True)


def _load_state():
    try:
        return set(json.load(open(STATE)))
    except Exception:
        return set()


def _save_state(ids):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(sorted(ids), open(STATE, 'w'), indent=1)


def list_docs():
    r = _rclone('lsjson', f'{REMOTE}:')
    if r.returncode != 0:
        print('rclone lsjson failed (is the remote configured?):',
              r.stderr.strip()[:200], file=sys.stderr)
        return []
    return json.loads(r.stdout or '[]')


def export_text(path):
    r = _rclone('cat', f'{REMOTE}:{path}', '--drive-export-formats', 'txt')
    return r.stdout if r.returncode == 0 else None


def _unescape(md):
    """Google-Doc round-trip escapes markdown (\\#, \\*, \\-, \\!); undo that."""
    for a, b in (('\\#', '#'), ('\\*', '*'), ('\\-', '-'), ('\\!', '!'),
                 ('\\_', '_'), ('\\`', '`'), ('\\>', '>'), ('\\[', '['),
                 ('\\]', ']'), ('\\|', '|')):
        md = md.replace(a, b)
    return md


def target_name(title, content):
    """Prefer the seat's explicit 'land this ... as <name>.md' instruction; else
    derive YYYY-MM-DD-HHMM-<FROM>-drive-carry.md from the header/title."""
    m = re.search(r'land\s+this[^\n]*?as\s+([0-9A-Za-z._\-]+\.md)', content, re.I)
    if m:
        return m.group(1)
    who = 'CF5' if title.startswith('CF5') else ('CAI' if title.startswith('CAI') else 'seat')
    d = re.search(r'(\d{4})-(\d{2})-(\d{2})[_\-]?(\d{4})?', title)
    stamp = (f"{d.group(1)}-{d.group(2)}-{d.group(3)}-{d.group(4) or '0000'}"
             if d else 'undated')
    return f"{stamp}-{who}-to-crew-drive-carry.md"


def main(dry=False):
    carried = _load_state()
    docs = [d for d in list_docs()
            if any(d.get('Name', '').startswith(p) for p in CARRY_PREFIXES)
            and d.get('ID') not in carried]
    if not docs:
        print('no new seat drops to carry')
        return 0
    landed = []
    for d in docs:
        content = export_text(d['Path'])
        if not content:
            print('  skip (no text):', d.get('Name'))
            continue
        name = target_name(d.get('Name', ''), content)
        path = os.path.join(POBOX, name)
        if os.path.exists(path):
            carried.add(d['ID'])
            continue                     # already in the box
        if dry:
            print(f"  WOULD carry: {d.get('Name')!r} -> private/POBOX/{name}")
            continue
        with open(path, 'w', encoding='utf-8') as f:
            f.write(_unescape(content).lstrip('\n'))
        landed.append(name)
        carried.add(d['ID'])
        print('  carried:', name)
    if landed and not dry:
        rel = [os.path.join('private/POBOX', n) for n in landed]
        subprocess.run(['git', '-C', REPO, 'add', '-f', *rel])
        subprocess.run(['git', '-C', REPO, 'commit', '-q', '-m',
                        'POBOX: auto-carry crew seat drops from Drive back-channel '
                        f"({', '.join(landed)})"])
        subprocess.run(['git', '-C', REPO, 'push', '-q', 'origin', 'master'])
    if not dry:
        _save_state(carried)
    return 0


if __name__ == '__main__':
    sys.exit(main(dry='--dry-run' in sys.argv))
