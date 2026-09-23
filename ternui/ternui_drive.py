#!/usr/bin/env python3
"""ternui_drive.py — Road B stage 2: the engine answers the native window.

Watches <stream>.sig (the native window's click signals). On each new
signal it walks the design's flow through the SAME engine every other
face uses (flowcode_walker + the cross-tab resolver), lands the walk's
watch-writes on widget labels, and RE-EMITS THE WORD STREAM — the
native window sees the mtime change, re-decodes, repaints. The whole
conversation happens in words and one signal file; no RPC, no JSON on
the wire.

Run:  python3 ternui/ternui_drive.py <design.(fc|ternoo)> <stream.tuw>

Added: 23 Sep 2026 (Road B stage 2). Authors: Stevo + Claude.
"""
import json
import os
import struct
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "5500fp"))
sys.path.insert(0, _HERE)
import ternoo_web as TW                          # noqa: E402  (engine mounts;
import ghost_meccano as GM                       # noqa: E402   no server runs)
from ternui_words import load_widgets            # noqa: E402

# ASCII seam (until STRING_UNICODE / the ruled glyph plane land in the
# label path): transliterate the FlowCode house glyphs the encoder
# would otherwise mangle through the base-128 char words.
_ASCII = str.maketrans({"−": "-", "·": ".", "—": "-",
                        "–": "-", "⇐": "<=", "⇒": "=>"})


def emit(widgets, out):
    for w in widgets.values():
        w["label"] = str(w.get("label", "")).translate(_ASCII)
    prog = GM.ghost_to_meccano(widgets, [], name=os.path.basename(out))
    words = list(prog.words)
    tmp = out + ".tmp"
    with open(tmp, "wb") as f:
        f.write(b"TUW0" + struct.pack("<I", len(words)))
        for w in words:
            f.write(struct.pack("<q", w))
    os.replace(tmp, out)                         # atomic: one mtime tick
    return len(words)


def main():
    design, out = sys.argv[1], sys.argv[2]
    sig = out + ".sig"
    doc = json.load(open(design, encoding="utf-8"))
    syms = {s["id"]: s for s in doc.get("flow_symbols", [])}
    edges = doc.get("flow_edges", doc.get("edges", []))
    widgets = load_widgets(design)               # bridge shape, labels capped
    by_name = {w.get("name"): w for w in widgets.values()}
    n = emit(widgets, out)
    print(f"stream up: {len(widgets)} widgets, {n} words -> {out}")
    print(f"listening on {sig} — click the native window")
    seen = 0
    while True:
        try:
            with open(sig, encoding="utf-8") as f:
                lines = f.readlines()
        except FileNotFoundError:
            lines = []
        if len(lines) > seen:
            for ln in lines[seen:]:
                name = ln.split("\t")[0].strip()
                print(f"⚡ {name} clicked — walking the design")
            seen = len(lines)
            try:
                rep = TW.WALKER.walk(syms, edges,
                                     resolver=TW._design_resolver(doc),
                                     variables={})
            except Exception as e:               # noqa: BLE001
                print(f"✗ walk failed: {e}")
                time.sleep(0.5)
                continue
            painted = 0
            for ev in rep.get("events", []):
                if ev[0] == "watch" and ev[1] in by_name:
                    cap = 12 if by_name[ev[1]].get("layout_mode") \
                        is not None else 15
                    by_name[ev[1]]["label"] = str(ev[2])[:cap]
                    painted += 1
            emit(widgets, out)
            print(f"  walk complete: {rep['steps']} steps, {painted} "
                  "widget writes — words re-emitted, window repaints")
        time.sleep(0.25)


if __name__ == "__main__":
    main()
