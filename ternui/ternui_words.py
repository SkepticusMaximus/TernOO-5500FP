#!/usr/bin/env python3
"""ternui_words.py — Road B stage 1: the design as CANONICAL WORDS.

Exports a design's GUI family through the committed encoder
(ghost_meccano.ghost_to_meccano) as a raw word-stream binary:
  magic 'TUW0' | uint32 LE count | count x int64 LE words
With --tsv, also decodes back through meccano_to_model and emits the
renderer TSV — the parity reference the C decoder must match exactly.

Per CF5's 23-09 rulings: widgets stay PIGART RNODE spans (no new
primary); containment rides the stream as words (MSCOPE by name +
STYLE_CONTAIN REDGEs, both already canon). The stage-0 TSV dump is
retired by this file.

Added: 23 Sep 2026 (Road B stage 1). Authors: Stevo + Claude.
"""
import json
import os
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "5500fp"))
import ghost_meccano as GM                      # noqa: E402

FC_GRID_TO_MECCANO = 10


def load_widgets(path):
    """Design file → bridge-shaped widgets dict (centre coords, abs)."""
    doc = json.load(open(path, encoding="utf-8"))
    ws = {int(s["id"]): dict(s) for s in doc.get("symbols", [])
          if str(s.get("kind", "")).startswith("gui_")}

    def depth(i, seen=()):
        p = ws.get(i, {}).get("parent_id")
        return 0 if p is None or p not in ws or i in seen \
            else 1 + depth(p, seen + (i,))
    for i in sorted(ws, key=depth):             # Tk offsets → absolute
        w, p = ws[i], ws.get(ws[i].get("parent_id"))
        if p is not None:
            w["x"] = int(p["x"] + p["w"] / 2 + w["x"] - w["w"] / 2)
            w["y"] = int(p["y"] + p["h"] / 2 + w["y"] - w["h"] / 2)
        elif w.get("parent_id") is not None:
            w["parent_id"] = None
    for w in ws.values():                       # bridge wants CENTRES
        w["x"] = int(w["x"] + w.get("w", 0) / 2)
        w["y"] = int(w["y"] + w.get("h", 0) / 2)
        w.setdefault("name", f"{w.get('kind', 'widget')}_{w['id']}")
        # RNODE label arity ceiling: 12 chars with layout word, 15 bare
        cap = 12 if w.get("layout_mode") is not None else 15
        w["label"] = str(w.get("label", ""))[:cap]
    return ws


def main():
    design, out = sys.argv[1], sys.argv[2]
    tsv = sys.argv[4] if len(sys.argv) > 4 and sys.argv[3] == "--tsv" \
        else None
    ws = load_widgets(design)
    prog = GM.ghost_to_meccano(ws, [], name=os.path.basename(design))
    words = list(prog.words)
    with open(out, "wb") as f:
        f.write(b"TUW0" + struct.pack("<I", len(words)))
        for w in words:
            f.write(struct.pack("<q", w))
    print(f"{len(ws)} widgets -> {len(words)} words -> {out}")
    if tsv:
        model = GM.meccano_to_model(words)
        with open(tsv, "w", encoding="utf-8") as f:
            for n in model["nodes"]:
                f.write(f"{n.get('kind', '')}\t"
                        f"{n['x'] * FC_GRID_TO_MECCANO}\t"
                        f"{n['y'] * FC_GRID_TO_MECCANO}\t"
                        f"{n['w'] * FC_GRID_TO_MECCANO}\t"
                        f"{n['h'] * FC_GRID_TO_MECCANO}\t"
                        f"{n.get('label', '')}\t"
                        f"{n.get('name', '')}\t"
                        f"{n.get('parent_scope', '')}\n")
        print(f"reference decode -> {tsv}")


if __name__ == "__main__":
    main()
