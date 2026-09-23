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


_LAST = {"words": None}


def _build(widgets, out):
    for w in widgets.values():
        w["label"] = str(w.get("label", "")).translate(_ASCII)
    prog = GM.ghost_to_meccano(widgets, [], name=os.path.basename(out))
    return list(prog.words)


def word_delta(old, new):
    """Minimal WordStreamEdit replace-record between two streams:
    (position, n_deleted, inserted_words). Q3 constraints: container-
    position addressing, applied atomically, pure integer ops."""
    a, b = 0, 0
    while a < len(old) and a < len(new) and old[a] == new[a]:
        a += 1
    while (b < len(old) - a and b < len(new) - a
           and old[-1 - b] == new[-1 - b]):
        b += 1
    return a, len(old) - a - b, new[a:len(new) - b]


def apply_delta(words, pos, ndel, ins):
    """The receiver's side of the wire — deterministic by construction."""
    return words[:pos] + list(ins) + words[pos + ndel:]


def emit(widgets, out):
    """First call writes the TUW0 baseline; every later call appends a
    TUD0 delta record — the Q3 wire format (WordStreamEdit 'replace')."""
    words = _build(widgets, out)
    if _LAST["words"] is None:
        tmp = out + ".tmp"
        with open(tmp, "wb") as f:
            f.write(b"TUW0" + struct.pack("<I", len(words)))
            for w in words:
                f.write(struct.pack("<q", w))
        os.replace(tmp, out)                     # atomic: one mtime tick
        open(out + ".tud", "wb").write(b"TUD0")
    else:
        pos, ndel, ins = word_delta(_LAST["words"], words)
        assert apply_delta(_LAST["words"], pos, ndel, ins) == words
        with open(out + ".tud", "ab") as f:
            f.write(struct.pack("<III", pos, ndel, len(ins)))
            for w in ins:
                f.write(struct.pack("<q", w))
        print(f"  Δ replace @{pos}: -{ndel} +{len(ins)} words on the wire")
        # compaction: when the journal outweighs the baseline, rewrite
        # the baseline and truncate — the native side sees the mtime
        # tick, reloads, and resets its journal offset (already built)
        if os.path.getsize(out + ".tud") > 8 * len(words):
            _LAST["words"] = None
            n = emit(widgets, out)
            print(f"  ⌁ journal compacted into a fresh baseline "
                  f"({n} words)")
            return n
    _LAST["words"] = words
    return len(words)


_PRIMARY = {"--": (-1, -1), "-0": (-1, 0), "-+": (-1, 1),
            "0-": (0, -1), "00": (0, 0), "0+": (0, 1),
            "+-": (1, -1), "+0": (1, 0), "++": (1, 1)}


def retune_a1(doc, radio_label):
    """A radio names a primary; retune cell A1's word to it — same
    payload, new top trits — so the walk decodes the chosen primary."""
    glyphs = str(radio_label).translate(_ASCII).split()[0]
    tt = _PRIMARY.get(glyphs)
    if tt is None:
        return
    for c in doc.get("cell_symbols", []):
        if c.get("row") == 0 and c.get("col") == 0:
            try:
                v = int(str(c.get("value", "0")))
            except ValueError:
                return
            body = v % (3 ** 22)                 # strip T23,T22 (balanced)
            if body > (3 ** 22 - 1) // 2:
                body -= 3 ** 22
            nv = tt[0] * 3 ** 23 + tt[1] * 3 ** 22 + body
            c["value"] = str(nv)
            print(f"  A1 retuned to primary {glyphs}: {nv}")
            return


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
                w = by_name.get(name)
                if w and w.get("kind") == "gui_radio":
                    retune_a1(doc, w.get("label", ""))
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
                    by_name[ev[1]]["label"] = str(ev[2])
                    painted += 1
            emit(widgets, out)
            print(f"  walk complete: {rep['steps']} steps, {painted} "
                  "widget writes — words re-emitted, window repaints")
        time.sleep(0.25)


if __name__ == "__main__":
    main()
