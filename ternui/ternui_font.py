#!/usr/bin/env python3
"""ternui_font.py — export the house stroke font for the native renderer.

Walks the ruled ordinal table through ternoo_glyph_strokes and writes a
THF0 binary: {i32 ordinal, u8 npolys, [u8 npts, (i8 x, i8 y)*npts]*}.
The C side draws these polylines at any scale — one font, every size,
no glyph atlas, no font files. Substrate test (§3): the DATA is the
ship's; the C only pushes pixels.

Added: 23 Sep 2026 (Road B — stroke text). Authors: Stevo + Claude.
"""
import os
import struct
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_HERE), "5500fp"))
import ternoo_glyph as G                        # noqa: E402
import ternoo_glyph_strokes as S                # noqa: E402


def export(out):
    n = 0
    with open(out, "wb") as f:
        f.write(b"THF0")
        for o in range(-121, 122):
            if o == 0:
                continue
            polys = S.strokes_for_ordinal(o)
            if not polys:
                continue
            f.write(struct.pack("<iB", o, len(polys)))
            for pl in polys:
                f.write(struct.pack("<B", len(pl)))
                for x, y in pl:
                    f.write(struct.pack("<bb", int(x), int(y)))
            n += 1
    print(f"{n} glyphs -> {out}")


if __name__ == "__main__":
    export(sys.argv[1] if len(sys.argv) > 1
           else os.path.join(_HERE, "house_font.thf"))
