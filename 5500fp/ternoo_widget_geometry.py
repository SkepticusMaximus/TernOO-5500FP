#!/usr/bin/env python3
"""
TernOO Widget Geometry — CC-09
==============================
Canonical render-geometry for each GUI widget type, expressed as sequences
of TernOO renderer words: RNODE / RLINE / RPOINT / RENDER.

These are NOT pixel bitmaps, SVG blobs, or text approximations.
Each word is a normalised-coordinate geometry primitive that the GHOST Canvas
renderer interprets at draw time, and that the GHOST geometry brain trains on.

Word dict schema
----------------
  RNODE  {'op':'RNODE', 'shape':str, 'role':str, 'x0':f, 'y0':f, 'x1':f, 'y1':f}
  RLINE  {'op':'RLINE', 'style':str, 'role':str, 'x0':f, 'y0':f, 'x1':f, 'y1':f}
  RPOINT {'op':'RPOINT', 'role':str, 'x':f, 'y':f}
  RENDER {'op':'RENDER'}

All coordinates normalised 0..1 over the widget tile bounding box (top-left=0,0).
The renderer scales to actual pixel dimensions at draw time.

Markov token = word_token(w) → "RNODE:rect:body", "RLINE:h:divider", etc.
These tokens are the vocabulary that ghost_geometry_brain.json learns.

Added: 01 Jun 2026, Adelaide
Authors: Stevo + Claude
Companion: private/TernOO-5500FP-Companion.md § G6 (CC-09)
"""

# ── Word constructors ─────────────────────────────────────────────────────────

def _rn(shape, role, x0, y0, x1, y1):
    """RNODE — a shape node: rect, circle, square, tri."""
    return {'op': 'RNODE', 'shape': shape, 'role': role,
            'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1}

def _rl(style, role, x0, y0, x1, y1):
    """RLINE — a line segment: style = h, v, or diag."""
    return {'op': 'RLINE', 'style': style, 'role': role,
            'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1}

def _rp(role, x, y):
    """RPOINT — a point / text anchor."""
    return {'op': 'RPOINT', 'role': role, 'x': x, 'y': y}

RENDER = {'op': 'RENDER'}   # sequence terminator

# ── Markov token ──────────────────────────────────────────────────────────────

def word_token(w: dict) -> str:
    """Reduce a geometry word to its Markov vocabulary token."""
    op = w['op']
    if op == 'RNODE':  return f"RNODE:{w['shape']}:{w['role']}"
    if op == 'RLINE':  return f"RLINE:{w['style']}:{w['role']}"
    if op == 'RPOINT': return f"RPOINT:{w['role']}"
    return 'RENDER'

# ── Canonical widget geometry ─────────────────────────────────────────────────
#
#   One entry per gui_* type from GUI_MMOE_TYPES.
#   Sequences designed to:
#     - Be visually distinctive per widget class
#     - Encode actual structural semantics (titlebar ≠ input area ≠ button strip)
#     - Remain simple enough for GHOST to learn transitions
#
#   Shared structural roles:
#     body       — outer bounding rect of the widget
#     titlebar   — window / frame / header title area
#     header     — column / tree header bar
#     strip      — menu / toolbar / status strip
#     tab        — notebook tab selector
#     row        — list / tree / menu row
#     cell       — grid or calendar cell boundary
#     button     — embedded action button
#     input      — text entry field area
#     dropdown   — combo / spinner dropdown target
#     thumb      — scrollbar or scale drag handle
#     fill       — progress fill region
#     icon       — image / icon placeholder
#     ctrl_close / ctrl_min / ctrl_max  — window control dots
#     radio / check / spinner / arrow   — indicator shapes

WIDGET_GEOMETRY: dict = {

    # ── Containers ────────────────────────────────────────────────────────────

    'gui_window': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'titlebar',   0,    0,    1,    0.22),
        _rl('h',      'divider',    0,    0.22, 1,    0.22),
        _rn('circle', 'ctrl_close', 0.86, 0.03, 0.96, 0.19),
        _rn('circle', 'ctrl_min',   0.74, 0.03, 0.84, 0.19),
        _rn('circle', 'ctrl_max',   0.62, 0.03, 0.72, 0.19),
        RENDER,
    ],

    'gui_dialog': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'titlebar',   0,    0,    1,    0.2 ),
        _rl('h',      'divider',    0,    0.2,  1,    0.2 ),
        _rl('h',      'divider',    0,    0.78, 1,    0.78),
        _rn('rect',   'strip',      0,    0.78, 1,    1   ),
        _rn('rect',   'button',     0.58, 0.82, 0.82, 0.96),
        _rn('rect',   'button',     0.84, 0.82, 0.98, 0.96),
        RENDER,
    ],

    'gui_box': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        RENDER,
    ],

    'gui_grid': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rl('h',      'divider',    0,    0.5,  1,    0.5 ),
        _rl('v',      'divider',    0.5,  0,    0.5,  1   ),
        RENDER,
    ],

    'gui_frame': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'titlebar',   0.05, 0,    0.45, 0.22),
        RENDER,
    ],

    'gui_scroll': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rl('v',      'divider',    0.88, 0,    0.88, 1   ),
        _rn('rect',   'thumb',      0.88, 0.2,  1,    0.65),
        RENDER,
    ],

    'gui_notebook': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'tab',        0,    0,    0.28, 0.22),
        _rn('rect',   'tab',        0.3,  0,    0.58, 0.22),
        _rl('h',      'divider',    0,    0.22, 1,    0.22),
        RENDER,
    ],

    'gui_stack': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rl('h',      'divider',    0,    0.5,  1,    0.5 ),
        RENDER,
    ],

    'gui_paned': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rl('v',      'divider',    0.5,  0,    0.5,  1   ),
        RENDER,
    ],

    'gui_expander': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('tri',    'arrow',      0.03, 0.25, 0.16, 0.75),
        _rp(          'center',     0.55, 0.5  ),
        RENDER,
    ],

    'gui_revealer': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('tri',    'arrow',      0.85, 0.28, 0.98, 0.72),
        RENDER,
    ],

    'gui_overlay': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'button',     0.5,  0.4,  0.97, 0.9 ),
        RENDER,
    ],

    'gui_headerbar': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rp(          'center',     0.5,  0.5  ),
        _rn('rect',   'button',     0.76, 0.1,  0.97, 0.9 ),
        _rn('circle', 'ctrl_close', 0.06, 0.15, 0.2,  0.85),
        RENDER,
    ],

    'gui_actionbar': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'button',     0.03, 0.12, 0.2,  0.88),
        _rn('rect',   'button',     0.23, 0.12, 0.4,  0.88),
        RENDER,
    ],

    # ── Controls ──────────────────────────────────────────────────────────────

    'gui_button': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rp(          'center',     0.5,  0.5  ),
        RENDER,
    ],

    'gui_toggle': [
        _rn('rect',   'body',       0.03, 0.18, 0.58, 0.82),
        _rn('circle', 'thumb',      0.33, 0.18, 0.58, 0.82),
        RENDER,
    ],

    'gui_check': [
        _rn('square', 'check',      0.02, 0.22, 0.3,  0.78),
        _rp(          'center',     0.63, 0.5  ),
        RENDER,
    ],

    'gui_radio': [
        _rn('circle', 'radio',      0.02, 0.22, 0.3,  0.78),
        _rp(          'center',     0.63, 0.5  ),
        RENDER,
    ],

    # ── Inputs ────────────────────────────────────────────────────────────────

    'gui_entry': [
        _rn('rect',   'input',      0,    0,    1,    1   ),
        _rl('v',      'cursor',     0.08, 0.2,  0.08, 0.8 ),
        RENDER,
    ],

    'gui_textview': [
        _rn('rect',   'input',      0,    0,    0.88, 1   ),
        _rl('v',      'divider',    0.88, 0,    0.88, 1   ),
        _rn('rect',   'thumb',      0.88, 0.1,  1,    0.55),
        RENDER,
    ],

    'gui_spinbutton': [
        _rn('rect',   'input',      0,    0,    0.78, 1   ),
        _rl('v',      'divider',    0.78, 0,    0.78, 1   ),
        _rn('tri',    'arrow',      0.8,  0.05, 0.98, 0.46),
        _rn('tri',    'arrow',      0.8,  0.54, 0.98, 0.95),
        RENDER,
    ],

    'gui_scale': [
        _rl('h',      'track',      0.04, 0.5,  0.96, 0.5 ),
        _rn('circle', 'thumb',      0.48, 0.18, 0.68, 0.82),
        RENDER,
    ],

    'gui_combo': [
        _rn('rect',   'input',      0,    0,    0.8,  1   ),
        _rl('v',      'divider',    0.8,  0,    0.8,  1   ),
        _rn('rect',   'dropdown',   0.8,  0,    1,    1   ),
        _rn('tri',    'arrow',      0.83, 0.28, 0.97, 0.72),
        RENDER,
    ],

    'gui_calendar': [
        _rn('rect',   'titlebar',   0,    0,    1,    0.22),
        _rl('h',      'divider',    0,    0.22, 1,    0.22),
        _rl('v',      'divider',    0.14, 0.22, 0.14, 1   ),
        _rl('v',      'divider',    0.28, 0.22, 0.28, 1   ),
        _rl('v',      'divider',    0.42, 0.22, 0.42, 1   ),
        _rl('v',      'divider',    0.56, 0.22, 0.56, 1   ),
        _rl('v',      'divider',    0.7,  0.22, 0.7,  1   ),
        _rl('v',      'divider',    0.86, 0.22, 0.86, 1   ),
        _rl('h',      'divider',    0,    0.5,  1,    0.5 ),
        _rl('h',      'divider',    0,    0.75, 1,    0.75),
        RENDER,
    ],

    'gui_colorpicker': [
        _rn('rect',   'body',       0,    0,    1,    0.78),
        _rl('h',      'divider',    0,    0.78, 1,    0.78),
        _rn('rect',   'strip',      0,    0.8,  1,    1   ),
        RENDER,
    ],

    # ── Display ───────────────────────────────────────────────────────────────

    'gui_label': [
        _rp(          'center',     0.5,  0.5  ),
        RENDER,
    ],

    'gui_image': [
        _rn('rect',   'icon',       0.05, 0.08, 0.95, 0.92),
        _rl('diag',   'cross',      0.05, 0.08, 0.95, 0.92),
        _rl('diag',   'cross',      0.95, 0.08, 0.05, 0.92),
        RENDER,
    ],

    'gui_progress': [
        _rn('rect',   'body',       0,    0.2,  1,    0.8 ),
        _rn('rect',   'fill',       0,    0.2,  0.62, 0.8 ),
        RENDER,
    ],

    'gui_separator': [
        _rl('h',      'divider',    0,    0.5,  1,    0.5 ),
        RENDER,
    ],

    'gui_statusbar': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rl('v',      'divider',    0.48, 0,    0.48, 1   ),
        _rl('v',      'divider',    0.76, 0,    0.76, 1   ),
        RENDER,
    ],

    'gui_spinner': [
        _rn('circle', 'spinner',    0.1,  0.05, 0.9,  0.95),
        RENDER,
    ],

    'gui_canvas': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        RENDER,
    ],

    # ── Menu / Action ─────────────────────────────────────────────────────────

    'gui_menubar': [
        _rn('rect',   'strip',      0,    0,    1,    1   ),
        _rl('v',      'divider',    0.22, 0,    0.22, 1   ),
        _rl('v',      'divider',    0.44, 0,    0.44, 1   ),
        _rl('v',      'divider',    0.66, 0,    0.66, 1   ),
        RENDER,
    ],

    'gui_toolbar': [
        _rn('rect',   'strip',      0,    0,    1,    1   ),
        _rn('square', 'icon',       0.03, 0.08, 0.21, 0.92),
        _rn('square', 'icon',       0.25, 0.08, 0.43, 0.92),
        _rn('square', 'icon',       0.47, 0.08, 0.65, 0.92),
        _rl('v',      'divider',    0.69, 0.1,  0.69, 0.9 ),
        _rn('square', 'icon',       0.73, 0.08, 0.91, 0.92),
        RENDER,
    ],

    'gui_menu': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'row',        0,    0.02, 1,    0.25),
        _rn('rect',   'row',        0,    0.28, 1,    0.51),
        _rl('h',      'divider',    0,    0.54, 1,    0.54),
        _rn('rect',   'row',        0,    0.57, 1,    0.8 ),
        RENDER,
    ],

    'gui_menuitem': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('tri',    'arrow',      0.88, 0.28, 0.98, 0.72),
        RENDER,
    ],

    # ── Lists / Tree ──────────────────────────────────────────────────────────

    'gui_treeview': [
        _rn('rect',   'header',     0,    0,    1,    0.24),
        _rl('h',      'divider',    0,    0.24, 1,    0.24),
        _rl('v',      'divider',    0.5,  0,    0.5,  1   ),
        _rn('rect',   'row',        0,    0.25, 1,    0.5 ),
        _rn('rect',   'row',        0,    0.5,  1,    0.75),
        _rn('rect',   'row',        0,    0.75, 1,    1   ),
        RENDER,
    ],

    'gui_listbox': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'row',        0,    0.01, 1,    0.3 ),
        _rn('rect',   'row',        0,    0.35, 1,    0.64),
        _rn('rect',   'row',        0,    0.69, 1,    0.98),
        RENDER,
    ],

    'gui_iconview': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('square', 'icon',       0.04, 0.04, 0.32, 0.48),
        _rn('square', 'icon',       0.36, 0.04, 0.64, 0.48),
        _rn('square', 'icon',       0.68, 0.04, 0.96, 0.48),
        _rn('square', 'icon',       0.04, 0.52, 0.32, 0.96),
        RENDER,
    ],
}



# ── Fallback for unmapped types ───────────────────────────────────────────────

_FALLBACK_GEOMETRY = [
    _rn('rect',   'body',       0,    0,    1,    1   ),
    RENDER,
]

def get_geometry(widget_type: str) -> list:
    """Return the geometry word sequence for a widget type, or a fallback rect."""
    return WIDGET_GEOMETRY.get(widget_type, _FALLBACK_GEOMETRY)


# ── Token sequence helper ─────────────────────────────────────────────────────

def get_token_sequence(widget_type: str) -> list:
    """Return the Markov token sequence for a widget type."""
    return [word_token(w) for w in get_geometry(widget_type)]


if __name__ == '__main__':
    # Quick sanity print
    for wtype, words in WIDGET_GEOMETRY.items():
        tokens = [word_token(w) for w in words]
        print(f"{wtype:22s}  [{len(words)-1:2d} words]  {' → '.join(tokens)}")
