#!/usr/bin/env python3
"""ternui_font_ttf.py — the thin adapter the production line waited for.

FOSS font file (TTF/OTF) → fontTools pen API → the PROVEN conversion
core (5500fp/ternoo_font_import.py) → THF1 binary for the native
renderer. Proportional advances and true lowercase forms come along;
the ruled ordinal table is the map. Ships any FOSS font as house
strokes in one command.

THF1 record: {i32 ordinal, i8 case, u8 advance*4, u8 npolys,
              [u8 npts, (i8 x*4, i8 y*4)*npts]*}
(quarter-grid fixed point: grid stays 0..~8 x -2..6, i8 covers ±31.75)

Usage: ternui_font_ttf.py /path/font.ttf out.thf
Added: 23 Sep 2026 (Road B — font import). Authors: Stevo + Claude.
"""
import os
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "5500fp"))
import ternoo_font_import as FI                  # noqa: E402
import ternoo_glyph as G                         # noqa: E402

from fontTools.ttLib import TTFont               # noqa: E402
from fontTools.pens.recordingPen import RecordingPen  # noqa: E402

CHARS = ("0123456789"
         "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
         " .,:;!?~-'\"()+=<>/\\*^%_|#[]{}")


def contours_of(font, glyf_name, glyph_set):
    pen = RecordingPen()
    glyph_set[glyf_name].draw(pen)
    out, start, segs, cur = [], None, [], None
    for op, args in pen.value:
        if op == "moveTo":
            if start is not None:
                out.append((start, segs))
            start, segs, cur = args[0], [], args[0]
        elif op == "lineTo":
            segs.append(("line", args[0])); cur = args[0]
        elif op == "qCurveTo":
            pts = list(args)
            if pts[-1] is None:                  # TrueType all-offcurve
                pts[-1] = start
            ctrls, end = pts[:-1], pts[-1]
            # implied on-curve midpoints between consecutive off-curves
            for k, cpt in enumerate(ctrls):
                if k < len(ctrls) - 1:
                    mid = ((cpt[0] + ctrls[k + 1][0]) / 2,
                           (cpt[1] + ctrls[k + 1][1]) / 2)
                    segs.append(("quad", cpt, mid))
                else:
                    segs.append(("quad", cpt, end))
            cur = end
        elif op == "curveTo":
            segs.append(("cubic", args[0], args[1], args[2]))
            cur = args[2]
        elif op == "closePath" and start is not None:
            segs.append(("line", start))
    if start is not None:
        out.append((start, segs))
    return out


def main():
    src, out = sys.argv[1], sys.argv[2]
    font = TTFont(src)
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    try:
        cap = font["OS/2"].sCapHeight or font["head"].unitsPerEm * 0.7
    except Exception:                            # noqa: BLE001
        cap = font["head"].unitsPerEm * 0.7
    n, skipped = 0, 0
    with open(out, "wb") as f:
        f.write(b"THF1")
        for ch in CHARS:
            gname = cmap.get(ord(ch))
            if not gname:
                skipped += 1
                continue
            rec = FI.import_glyph(ch, contours_of(font, gname, gs),
                                  cap, steps=4)
            if rec.get("unmapped"):
                skipped += 1
                continue
            polys = []
            for pl in rec["strokes"]:            # chunk, never truncate
                while len(pl) > 60:
                    polys.append(pl[:60])
                    pl = pl[59:]                 # share the seam point
                if pl:
                    polys.append(pl)
            adv = max(1, min(63, round(rec["advance"] * 4)))
            f.write(struct.pack("<ibBB", rec["ordinal"], rec["case"],
                                adv, min(len(polys), 255)))
            for pl in polys[:255]:
                pts = pl[:60]
                f.write(struct.pack("<B", len(pts)))
                for x, y in pts:
                    xi = max(-127, min(127, round(x * 4)))
                    yi = max(-127, min(127, round(y * 4)))
                    f.write(struct.pack("<bb", xi, yi))
            n += 1
    print(f"{n} glyphs imported from {os.path.basename(src)} -> {out} "
          f"({skipped} skipped)")


if __name__ == "__main__":
    main()
