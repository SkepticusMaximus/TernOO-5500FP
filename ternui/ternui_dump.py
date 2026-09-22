#!/usr/bin/env python3
"""ternui_dump.py — Road B stage 0: feed the native renderer.

Exports a design's GUI family as a flat TSV the C spike can read with
no JSON machinery: kind, abs-x, abs-y, w, h, label. The Tk-schema
centre-offset transform is applied here (parents first), so the C side
draws at honest absolute positions.

TEMPORARY SEAM: this dump exists only until the widget word vocabulary
is ruled (CF5 gate) — then the renderer reads TernOO words directly.

Added: 23 Sep 2026 (Road B stage 0). Authors: Stevo + Claude.
"""
import json
import os
import sys


def depth_of(widgets, wid, seen=()):
    p = widgets.get(wid, {}).get("parent_id")
    if p is None or p not in widgets or wid in seen:
        return 0
    return 1 + depth_of(widgets, p, seen + (wid,))


def dump(path, out):
    doc = json.load(open(path, encoding="utf-8"))
    widgets = {int(s["id"]): dict(s) for s in doc.get("symbols", [])
               if str(s.get("kind", "")).startswith("gui_")}
    for wid in sorted(widgets, key=lambda i: depth_of(widgets, i)):
        w = widgets[wid]
        p = widgets.get(w.get("parent_id"))
        if p is not None:               # Tk schema: centre offsets
            w["x"] = int(p["x"] + p["w"] / 2 + w["x"] - w["w"] / 2)
            w["y"] = int(p["y"] + p["h"] / 2 + w["y"] - w["h"] / 2)
    seq = [int(i) for i in doc.get("sequence", []) if int(i) in widgets]
    seq += [i for i in widgets if i not in seq]
    kids = {}
    for i in seq:
        par = widgets[i].get("parent_id")
        kids.setdefault(par if par in widgets else None, []).append(i)
    order = []

    def walk(i):
        order.append(i)
        for c in kids.get(i, []):
            walk(c)
    for r in kids.get(None, []):
        walk(r)
    with open(out, "w", encoding="utf-8") as f:
        f.write(f"# ternui dump v0 — {os.path.basename(path)}\n")
        for i in order:
            w = widgets[i]
            label = str(w.get("label", "")).replace("\t", " ")
            f.write(f"{w['kind']}\t{int(w['x'])}\t{int(w['y'])}"
                    f"\t{int(w['w'])}\t{int(w['h'])}\t{label}\n")
    print(f"dumped {len(order)} widgets -> {out}")


if __name__ == "__main__":
    dump(sys.argv[1], sys.argv[2])
