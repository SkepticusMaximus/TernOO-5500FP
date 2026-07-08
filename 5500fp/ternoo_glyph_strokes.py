"""ternoo_glyph_strokes.py — the house-font seed stroke library (v1).

Each glyph is a list of polylines on an integer design grid: x in 0..4,
y in -2..6 (baseline y=0, cap height y=6, descenders to -2). Advance width is
6 grid units (monospace v1). A polyline is a list of (x,y) points; a single-
point polyline renders as a dot at stroke width. This is the widget_geometry
idiom — normalized stroke sequences, the renderer scales.

Lowercase (case trit -1) renders these same strokes at 2/3 scale, baseline-
aligned (small-caps interim); true lowercase forms are a library growth item.
Caseless (0) renders full scale. Case is DATA (the word), not picture.

The stroke set is the DEFAULT house font/map convention (register O4 open),
NOT a decree. The ~ (placeholder) and idea marks are founding residents by the
captain's history — keep them.

Date: 2026-07-08, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import ternoo_glyph as _glyph

ADVANCE = 6          # grid units per character cell (monospace)
GRID_X = (0, 4)
GRID_Y = (-2, 6)

# name/char -> list of polylines (each a list of (x, y) points)
STROKES = {
    'A': [[(0, 0), (2, 6), (4, 0)], [(1, 2), (3, 2)]],
    'B': [[(0, 0), (0, 6)], [(0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)],
          [(3, 3), (4, 2), (4, 1), (3, 0), (0, 0)]],
    'C': [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5)]],
    'D': [[(0, 0), (0, 6)], [(0, 6), (3, 6), (4, 4), (4, 2), (3, 0), (0, 0)]],
    'E': [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    'F': [[(0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    'G': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1),
           (4, 3), (2, 3)]],
    'H': [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    'I': [[(1, 0), (3, 0)], [(2, 0), (2, 6)], [(1, 6), (3, 6)]],
    'J': [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 6)]],
    'K': [[(0, 0), (0, 6)], [(4, 6), (0, 3), (4, 0)]],
    'L': [[(0, 6), (0, 0), (4, 0)]],
    'M': [[(0, 0), (0, 6), (2, 3), (4, 6), (4, 0)]],
    'N': [[(0, 0), (0, 6)], [(0, 6), (4, 0)], [(4, 0), (4, 6)]],
    'O': [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1),
           (1, 0)]],
    'P': [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)]],
    'Q': [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1),
           (1, 0)], [(2, 2), (4, 0)]],
    'R': [[(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)],
          [(2, 3), (4, 0)]],
    'S': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 4), (1, 3), (3, 3), (4, 2),
           (4, 1), (3, 0), (1, 0), (0, 1)]],
    'T': [[(0, 6), (4, 6)], [(2, 6), (2, 0)]],
    'U': [[(0, 6), (0, 1), (1, 0), (3, 0), (4, 1), (4, 6)]],
    'V': [[(0, 6), (2, 0), (4, 6)]],
    'W': [[(0, 6), (1, 0), (2, 4), (3, 0), (4, 6)]],
    'X': [[(0, 0), (4, 6)], [(0, 6), (4, 0)]],
    'Y': [[(0, 6), (2, 3), (4, 6)], [(2, 3), (2, 0)]],
    'Z': [[(0, 6), (4, 6), (0, 0), (4, 0)]],
    '0': [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1),
           (1, 0)]],
    '1': [[(1, 5), (2, 6), (2, 0)], [(1, 0), (3, 0)]],
    '2': [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (0, 0), (4, 0)]],
    '3': [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (1, 3)],
          [(3, 3), (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)]],
    '4': [[(3, 0), (3, 6), (0, 2), (4, 2)]],
    '5': [[(4, 6), (0, 6), (0, 3), (3, 3), (4, 2), (4, 1), (3, 0), (1, 0),
           (0, 1)]],
    '6': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1),
           (4, 2), (3, 3), (0, 3)]],
    '7': [[(0, 6), (4, 6), (1, 0)]],
    '8': [[(1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3),
           (1, 3)], [(1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2),
                     (3, 3)]],
    '9': [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5),
           (0, 4), (1, 3), (4, 3)]],
    'period': [[(2, 0)]],
    'comma': [[(2, 1), (2, 0), (1, -1)]],
    'colon': [[(2, 4)], [(2, 1)]],
    'semicolon': [[(2, 4)], [(2, 1), (2, 0), (1, -1)]],
    '!': [[(2, 6), (2, 2)], [(2, 0)]],
    '?': [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (2, 3), (2, 2)],
          [(2, 0)]],
    'answer': [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 4), (1, 3), (2, 3),
                (2, 2)], [(2, 0)]],
    'idea': [[(2, 2), (2, 3), (3, 3), (4, 4), (4, 5), (3, 6), (2, 6)],
             [(2, 2), (2, 3), (1, 3), (0, 4), (0, 5), (1, 6), (2, 6)],
             [(2, 0)]],
    '~': [[(0, 3), (1, 4), (2, 3), (3, 2), (4, 3)]],
    'hyphen': [[(1, 3), (3, 3)]],
    'apostrophe': [[(2, 6), (2, 5)]],
    'quote': [[(1, 6), (1, 5)], [(3, 6), (3, 5)]],
    '(': [[(3, 6), (2, 4), (2, 2), (3, 0)]],
    ')': [[(1, 6), (2, 4), (2, 2), (1, 0)]],
    'space': [],
}

# ordinal -> stroke key (the house table's ordering; O1: Y IS this index)
_ORD_TO_KEY = {}
for _ch, _o in _glyph.ORDINAL.items():
    if _ch == ' ':
        _ORD_TO_KEY[_o] = 'space'
    else:
        _ORD_TO_KEY[_o] = _ch
_ORD_TO_KEY[_glyph.ANSWER_ORD] = 'answer'      # -7
_ORD_TO_KEY[_glyph.IDEA_ORD] = 'idea'          # -8 (has no single-char key)
# named punctuation whose ORDINAL key is the char itself already resolves above
_ORD_TO_KEY[_glyph.ORDINAL['.']] = 'period'
_ORD_TO_KEY[_glyph.ORDINAL[',']] = 'comma'
_ORD_TO_KEY[_glyph.ORDINAL[':']] = 'colon'
_ORD_TO_KEY[_glyph.ORDINAL[';']] = 'semicolon'
_ORD_TO_KEY[_glyph.ORDINAL['-']] = 'hyphen'
_ORD_TO_KEY[_glyph.ORDINAL["'"]] = 'apostrophe'
_ORD_TO_KEY[_glyph.ORDINAL['"']] = 'quote'


def strokes_for_ordinal(ordinal: int):
    """The polylines for a house-font ordinal, or None if the font has no
    member for it (the caller falls to the ~ placeholder — R1)."""
    key = _ORD_TO_KEY.get(ordinal)
    if key is None:
        return None
    return STROKES.get(key)


def has_glyph(ordinal: int) -> bool:
    return strokes_for_ordinal(ordinal) is not None
