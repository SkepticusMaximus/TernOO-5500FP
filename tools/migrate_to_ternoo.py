#!/usr/bin/env python3
"""tools/migrate_to_ternoo.py — One-time migration utility (Bundle 11)

Converts legacy .tgui (Phase 6B/6C) and .json (Bundle-7-era FCCanvas) files
to the .ternoo format used from Bundle 11 onward.

Usage:
    python3 tools/migrate_to_ternoo.py <path1> [<path2> ...]
    python3 tools/migrate_to_ternoo.py --archive <directory>

The --archive form scans a directory for .tgui and .json files, migrates each
to .ternoo in place, and moves the originals into ./_archive/ subdirectory.
Without --archive, originals are left alone next to the new .ternoo files.

Date: 16 June 2026, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations
import json
import os
import shutil
import sys

# ── Legacy FCCanvas kind mapping (Bundle-7-era .json files) ──────────────────
_LEGACY_KIND_MAP = {
    'terminator': 'flow_terminator',
    'process':    'flow_process',
    'decision':   'flow_decision',
    'io':         'flow_io',
    'subroutine': 'flow_subroutine',
    'connector':  'flow_connector',
}

# Default symbol dimensions (matches SYMBOL_W / SYMBOL_H in flowcode.py)
_SYMBOL_W = 120
_SYMBOL_H = 60


def _load_file(path: str) -> dict:
    """Load a .tgui or .json file and normalise to internal dict."""
    with open(path) as f:
        data = json.load(f)

    # Already a .ternoo / .tgui Phase-6B+ file
    if 'ternoo_version' in data or 'tgui_version' in data:
        return data

    # Legacy FCCanvas .json: top-level 'symbols' with bare kind names
    first_kind = (data.get('symbols') or [{}])[0].get('kind', '')
    if first_kind in _LEGACY_KIND_MAP:
        return _convert_legacy_json(data)

    raise ValueError(
        f"Unrecognised file format in {path!r} — "
        "expected ternoo_version, tgui_version, or FCCanvas symbols."
    )


def _convert_legacy_json(data: dict) -> dict:
    """Convert Bundle-7-era FCCanvas JSON to internal ternoo dict."""
    flow_syms: list = []
    next_sid = 0
    for ls in data.get('symbols', []):
        sid = ls.get('id', next_sid)
        next_sid = max(next_sid, sid + 1)
        flow_syms.append({
            'id':         sid,
            'kind':       _LEGACY_KIND_MAP.get(ls['kind'], 'flow_process'),
            'x':          ls.get('x', 0),
            'y':          ls.get('y', 0),
            'w':          _SYMBOL_W,
            'h':          _SYMBOL_H,
            'label':      ls.get('label', ''),
            'properties': [],
        })
    flow_edges: list = []
    for le in data.get('edges', []):
        flow_edges.append({
            'src':       le['src'],
            'dst':       le['dst'],
            'waypoints': [tuple(w) for w in le.get('waypoints', [])],
            'condition': le.get('condition', ''),
        })
    return {
        'ternoo_version': '0.3',
        'source_type':    'ternoo_design',
        'symbols':        [],
        'edges':          [],
        'flow_symbols':   flow_syms,
        'flow_edges':     flow_edges,
    }


def _to_ternoo(data: dict) -> dict:
    """Normalise any loaded dict to ternoo v0.3 format."""
    out = dict(data)
    out.pop('tgui_version', None)
    out['ternoo_version'] = '0.3'
    out['source_type']    = 'ternoo_design'
    return out


def migrate_file(src_path: str, archive_dir: str | None = None) -> str:
    """Migrate one file to .ternoo. Returns the output path."""
    data = _load_file(src_path)
    out  = _to_ternoo(data)
    stem = os.path.splitext(src_path)[0]
    dst  = stem + '.ternoo'

    with open(dst, 'w') as f:
        json.dump(out, f, indent=2)

    if archive_dir is not None:
        os.makedirs(archive_dir, exist_ok=True)
        shutil.move(src_path, os.path.join(archive_dir, os.path.basename(src_path)))

    return dst


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    archive_mode = '--archive' in args
    if archive_mode:
        args.remove('--archive')
        if len(args) != 1:
            print("Usage: migrate_to_ternoo.py --archive <directory>")
            sys.exit(1)
        directory   = args[0]
        targets     = [
            os.path.join(directory, fn)
            for fn in os.listdir(directory)
            if fn.endswith('.tgui') or fn.endswith('.json')
        ]
        if not targets:
            print(f"No .tgui or .json files found in {directory!r}")
            sys.exit(0)
        archive_dir = os.path.join(directory, '_archive')
    else:
        targets     = args
        archive_dir = None

    ok = err = 0
    for src in sorted(targets):
        try:
            dst = migrate_file(src, archive_dir)
            archived = f" (original → {archive_dir})" if archive_dir else ""
            print(f"  migrated  {os.path.basename(src)}  →  {os.path.basename(dst)}{archived}")
            ok += 1
        except Exception as e:
            print(f"  ERROR     {os.path.basename(src)}: {e}")
            err += 1

    print(f"\n{ok} migrated, {err} errors.")
    if archive_dir and ok:
        print(f"Originals archived in: {archive_dir}")


if __name__ == '__main__':
    main()
