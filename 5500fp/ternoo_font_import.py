"""ternoo_font_import.py — the font-import conversion core (deterministic).

The heart of the production line (design note CC-Submit-2026-07-09_160000):
turn a foreign glyph's vector OUTLINE into TernOO stroke polylines on the
design grid, and map its character to a house ordinal. Pure geometry — no
model, no OCR, no font-file parsing here. The parser (TTF/OTF outline -> the
contour form below) is a thin adapter written against a FOSS font library's
pen API when we point it at real fonts; THIS module is the part that's
provable in isolation, and it is.

Contour form (a pen decomposed): a glyph is a list of contours; each contour
is (start_point, [segment, ...]) where a segment is one of
    ('line',  end)
    ('quad',  ctrl, end)
    ('cubic', ctrl1, ctrl2, end)
points are (x, y) in the font's own units (baseline y=0, up = +y).

Normalisation maps the font's cap-height to grid y=6 (baseline stays y=0),
uniform scale so proportions are kept, left edge to x=0; the resulting advance
width is REPORTED, not forced — the coarse-grid / monospace-vs-proportional
decision is the charter's fork (O4), deliberately left open here.

Date: 2026-07-09, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import os
import importlib.util as _ilu

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = _load('ternoo_glyph')

GRID_CAP = 6                # grid y at cap height (matches ternoo_glyph_strokes)
DEFAULT_STEPS = 8          # Bézier flattening subdivisions


# ═══════════════════════════════════════════════════════════════════════════
# Bézier flattening (de Casteljau)
# ═══════════════════════════════════════════════════════════════════════════

def _lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def flatten_quad(p0, c, p1, steps=DEFAULT_STEPS):
    """Quadratic Bézier -> points for t in (0,1] (p0 is the running end)."""
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        out.append(_lerp(_lerp(p0, c, t), _lerp(c, p1, t), t))
    return out


def flatten_cubic(p0, c1, c2, p1, steps=DEFAULT_STEPS):
    """Cubic Bézier -> points for t in (0,1]."""
    out = []
    for i in range(1, steps + 1):
        t = i / steps
        a, b, c = _lerp(p0, c1, t), _lerp(c1, c2, t), _lerp(c2, p1, t)
        out.append(_lerp(_lerp(a, b, t), _lerp(b, c, t), t))
    return out


def flatten_contour(start, segments, steps=DEFAULT_STEPS):
    """One contour -> a polyline (list of points), starting at `start`."""
    poly = [tuple(start)]
    cur = tuple(start)
    for seg in segments:
        kind = seg[0]
        if kind == 'line':
            cur = tuple(seg[1]); poly.append(cur)
        elif kind == 'quad':
            poly.extend(flatten_quad(cur, tuple(seg[1]), tuple(seg[2]), steps))
            cur = tuple(seg[2])
        elif kind == 'cubic':
            poly.extend(flatten_cubic(cur, tuple(seg[1]), tuple(seg[2]),
                                      tuple(seg[3]), steps))
            cur = tuple(seg[3])
        else:
            raise ValueError(f'unknown segment kind {kind!r}')
    return poly


def flatten_glyph(contours, steps=DEFAULT_STEPS):
    return [flatten_contour(s, segs, steps) for s, segs in contours]


# ═══════════════════════════════════════════════════════════════════════════
# Normalisation onto the design grid
# ═══════════════════════════════════════════════════════════════════════════

def normalize(polylines, cap_height, baseline=0):
    """Uniform-scale so cap height -> grid y=6 (baseline -> 0), left edge -> 0.
    Returns (grid_polylines, advance_width). Proportions preserved; the advance
    is reported for the charter to decide monospace-vs-proportional."""
    if cap_height <= 0:
        raise ValueError('cap_height must be positive')
    scale = GRID_CAP / float(cap_height)
    scaled = [[(x * scale, (y - baseline) * scale) for (x, y) in poly]
              for poly in polylines]
    xs = [x for poly in scaled for (x, _) in poly]
    minx = min(xs) if xs else 0.0
    grid = [[(x - minx, y) for (x, y) in poly] for poly in scaled]
    advance = (max(xs) - minx) if xs else 0.0
    return grid, advance


# ═══════════════════════════════════════════════════════════════════════════
# Character -> house ordinal (deterministic; unknowns flagged, never guessed)
# ═══════════════════════════════════════════════════════════════════════════

def map_char(ch: str):
    """(ordinal, case) for a single character, or None if the house table has
    no home for it (that codepoint is the O4 charter's queue, not a silent
    substitution)."""
    if 'A' <= ch <= 'Z':
        return G.ORDINAL[ch], +1
    if 'a' <= ch <= 'z':
        return G.ORDINAL[ch.upper()], -1
    if ch in G.ORDINAL:
        return G.ORDINAL[ch], 0
    return None


# ═══════════════════════════════════════════════════════════════════════════
# The unit of import
# ═══════════════════════════════════════════════════════════════════════════

def import_glyph(ch: str, contours, cap_height, steps=DEFAULT_STEPS) -> dict:
    """Convert one foreign glyph. Returns a record: on success the grid strokes
    + house ordinal/case + advance; on a codepoint with no house ordinal, a
    flagged record (unmapped: True) — the charter decides its ordinal."""
    mapped = map_char(ch)
    grid, advance = normalize(flatten_glyph(contours, steps), cap_height)
    if mapped is None:
        return {'char': ch, 'unmapped': True, 'strokes': grid,
                'advance': advance}
    ordinal, case = mapped
    return {'char': ch, 'unmapped': False, 'ordinal': ordinal, 'case': case,
            'strokes': grid, 'advance': advance,
            'word': G.make_glyph(ordinal, case)}
