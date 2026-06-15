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
    # Role note: 'divider' lines render as _lc default → col (widget colour).
    # Using 'track' renders dim (subtle); 'cross' also dim.  Choose per intent.

    'gui_window': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'titlebar',   0,    0,    1,    0.22),
        _rl('h',      'track',      0,    0.22, 1,    0.22),   # title bar edge
        _rn('circle', 'ctrl_close', 0.86, 0.03, 0.96, 0.19),
        _rn('circle', 'ctrl_min',   0.74, 0.03, 0.84, 0.19),
        _rn('circle', 'ctrl_max',   0.62, 0.03, 0.72, 0.19),
        RENDER,
    ],

    'gui_dialog': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'titlebar',   0,    0,    1,    0.2 ),
        _rl('h',      'track',      0,    0.2,  1,    0.2 ),
        _rl('h',      'track',      0,    0.78, 1,    0.78),
        _rn('rect',   'strip',      0,    0.78, 1,    1   ),
        _rn('rect',   'button',     0.58, 0.82, 0.82, 0.96),   # OK
        _rn('rect',   'button',     0.84, 0.82, 0.98, 0.96),   # Cancel
        RENDER,
    ],

    'gui_box': [
        # dashed rect drawn by gc_draw_widget before _gc_render_words is called
        _rl('v',      'cross',      0.33, 0.2,  0.33, 0.95),   # column guides
        _rl('v',      'cross',      0.67, 0.2,  0.67, 0.95),
        RENDER,
    ],

    'gui_grid': [
        # dashed rect pre-drawn
        _rl('v',      'cross',      0.33, 0.2,  0.33, 0.95),
        _rl('v',      'cross',      0.67, 0.2,  0.67, 0.95),
        _rl('h',      'cross',      0,    0.5,  1,    0.5 ),
        RENDER,
    ],

    'gui_frame': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'titlebar',   0.05, 0,    0.45, 0.22),   # label notch
        RENDER,
    ],

    'gui_scroll': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rl('v',      'track',      0.88, 0,    0.88, 1   ),    # scrollbar groove
        _rn('rect',   'thumb',      0.88, 0.2,  1,    0.65),   # scrollbar thumb
        RENDER,
    ],

    'gui_notebook': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'tab',        0,    0,    0.28, 0.22),    # active tab
        _rn('rect',   'strip',      0.3,  0,    0.58, 0.22),   # inactive tab
        _rl('h',      'track',      0,    0.22, 1,    0.22),   # tab edge
        RENDER,
    ],

    'gui_stack': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rl('h',      'cross',      0,    0.5,  1,    0.5 ),
        RENDER,
    ],

    'gui_paned': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rl('v',      'track',      0.5,  0,    0.5,  1   ),    # split handle
        _rn('rect',   'thumb',      0.46, 0.4,  0.54, 0.6 ),   # drag grip
        RENDER,
    ],

    'gui_expander': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'strip',      0,    0,    1,    0.28),    # header strip
        # right-pointing tri: span_y=0.31*72=22.3 > span_x=0.08*160=12.8 ✓
        _rn('tri',    'body',       0.03, 0.04, 0.11, 0.35),   # ▶ expand arrow
        _rl('h',      'track',      0,    0.28, 1,    0.28),   # header edge
        RENDER,
    ],

    'gui_revealer': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        # right-pointing tri: span_y (0.44*72=31.7) > span_x (0.13*160=20.8)
        _rn('tri',    'body',       0.85, 0.28, 0.98, 0.72),
        RENDER,
    ],

    'gui_overlay': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'button',     0.5,  0.4,  0.97, 0.9 ),   # overlaid pane
        RENDER,
    ],

    'gui_headerbar': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('circle', 'button',     0.04, 0.18, 0.22, 0.82),   # nav back
        _rn('circle', 'button',     0.26, 0.18, 0.44, 0.82),   # nav forward
        _rn('rect',   'button',     0.76, 0.1,  0.97, 0.9 ),   # menu button
        RENDER,
    ],

    'gui_actionbar': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'button',     0.03, 0.12, 0.2,  0.88),
        _rn('rect',   'button',     0.23, 0.12, 0.4,  0.88),
        _rn('rect',   'button',     0.43, 0.12, 0.6,  0.88),
        RENDER,
    ],

    # ── Controls ──────────────────────────────────────────────────────────────

    'gui_button': [
        _rn('rect',   'body',       0.01, 0.08, 0.99, 0.92),   # outer surface
        _rn('rect',   'strip',      0.01, 0.08, 0.99, 0.22),   # top bevel (lighter)
        _rn('rect',   'thumb',      0.01, 0.78, 0.99, 0.92),   # bottom shadow
        RENDER,
    ],

    'gui_toggle': [
        # pill track on left, circular knob on right (ON state)
        _rn('rect',   'body',       0.03, 0.22, 0.55, 0.78),   # track
        _rn('circle', 'ctrl_max',   0.32, 0.22, 0.55, 0.78),   # knob (green=ON)
        RENDER,
    ],

    'gui_check': [
        _rn('square', 'check',      0.02, 0.22, 0.3,  0.78),   # checkbox (txt/dim)
        _rl('diag',   'cursor',     0.06, 0.55, 0.14, 0.72),   # checkmark left
        _rl('diag',   'cursor',     0.14, 0.72, 0.27, 0.3 ),   # checkmark right
        _rl('h',      'track',      0.37, 0.5,  0.95, 0.5 ),   # label hint
        RENDER,
    ],

    'gui_radio': [
        _rn('circle', 'radio',      0.02, 0.22, 0.3,  0.78),   # outer ring (txt/dim)
        _rn('circle', 'fill',       0.09, 0.36, 0.23, 0.64),   # inner dot (txt)
        _rl('h',      'track',      0.37, 0.5,  0.95, 0.5 ),   # label hint
        RENDER,
    ],

    # ── Inputs ────────────────────────────────────────────────────────────────

    'gui_entry': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'input',      0.03, 0.14, 0.97, 0.86),   # field inset
        _rl('v',      'cursor',     0.08, 0.2,  0.08, 0.8 ),   # text cursor (txt)
        _rl('h',      'track',      0.12, 0.5,  0.7,  0.5 ),   # placeholder hint
        RENDER,
    ],

    'gui_textview': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'input',      0.02, 0.06, 0.86, 0.94),   # text area
        _rl('h',      'track',      0.05, 0.22, 0.82, 0.22),   # text line 1
        _rl('h',      'track',      0.05, 0.38, 0.68, 0.38),   # text line 2 (shorter)
        _rl('h',      'track',      0.05, 0.54, 0.82, 0.54),   # text line 3
        _rl('v',      'track',      0.88, 0,    0.88, 1   ),    # scrollbar groove
        _rn('rect',   'thumb',      0.88, 0.1,  1,    0.5 ),   # scrollbar thumb
        RENDER,
    ],

    'gui_spinbutton': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'input',      0,    0,    0.78, 1   ),
        _rl('v',      'track',      0.78, 0,    0.78, 1   ),
        _rn('rect',   'spinner',    0.8,  0.05, 0.98, 0.48),   # up region (no fill)
        _rn('rect',   'spinner',    0.8,  0.52, 0.98, 0.95),   # down region
        # down-pointing tri (span_x=0.18*160=28.8 > span_y=0.2*72=14.4)
        _rn('tri',    'body',       0.82, 0.08, 0.96, 0.28),   # ▼ up arrow
        _rn('tri',    'body',       0.82, 0.72, 0.96, 0.92),   # ▼ down arrow
        RENDER,
    ],

    'gui_scale': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rl('h',      'track',      0.04, 0.5,  0.96, 0.5 ),   # slider track (dim)
        _rn('circle', 'thumb',      0.36, 0.18, 0.56, 0.82),   # drag knob
        RENDER,
    ],

    'gui_combo': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'input',      0,    0,    0.8,  1   ),
        _rl('v',      'track',      0.8,  0,    0.8,  1   ),
        _rn('rect',   'dropdown',   0.8,  0,    1,    1   ),
        # down-pointing tri: span_x=0.14*160=22.4 > span_y=0.44*72=31.7 → NO
        # Use wider bounds: span_x=0.18*160=28.8 > span_y=0.15*72=10.8 → down ✓
        _rn('tri',    'body',       0.83, 0.35, 1,    0.65),
        RENDER,
    ],

    'gui_calendar': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'titlebar',   0,    0,    1,    0.22),
        _rl('h',      'track',      0,    0.22, 1,    0.22),
        _rl('v',      'cross',      0.14, 0.22, 0.14, 1   ),
        _rl('v',      'cross',      0.28, 0.22, 0.28, 1   ),
        _rl('v',      'cross',      0.42, 0.22, 0.42, 1   ),
        _rl('v',      'cross',      0.56, 0.22, 0.56, 1   ),
        _rl('v',      'cross',      0.7,  0.22, 0.7,  1   ),
        _rl('v',      'cross',      0.86, 0.22, 0.86, 1   ),
        _rl('h',      'cross',      0,    0.5,  1,    0.5 ),
        _rl('h',      'cross',      0,    0.75, 1,    0.75),
        RENDER,
    ],

    'gui_colorpicker': [
        _rn('rect',   'body',       0,    0,    1,    0.75),
        _rl('h',      'track',      0,    0.75, 1,    0.75),
        _rn('rect',   'strip',      0,    0.77, 1,    1   ),    # hue/alpha strip
        _rn('circle', 'ctrl_close', 0.04, 0.05, 0.2,  0.35),   # red swatch
        _rn('circle', 'ctrl_max',   0.25, 0.05, 0.41, 0.35),   # green swatch
        _rn('circle', 'ctrl_min',   0.46, 0.05, 0.62, 0.35),   # yellow swatch
        RENDER,
    ],

    # ── Display ───────────────────────────────────────────────────────────────

    'gui_label': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rl('h',      'track',      0.1,  0.5,  0.9,  0.5 ),   # text hint
        RENDER,
    ],

    'gui_image': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'icon',       0.05, 0.08, 0.95, 0.92),   # image frame
        _rl('diag',   'cross',      0.05, 0.08, 0.95, 0.92),   # broken-image X
        _rl('diag',   'cross',      0.95, 0.08, 0.05, 0.92),
        RENDER,
    ],

    'gui_progress': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'input',      0.02, 0.28, 0.98, 0.72),   # track
        _rn('rect',   'fill',       0.02, 0.28, 0.6,  0.72),   # ~60% fill
        RENDER,
    ],

    'gui_separator': [
        _rl('h',      'track',      0,    0.5,  1,    0.5 ),
        RENDER,
    ],

    'gui_statusbar': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'strip',      0,    0,    1,    1   ),    # strip bg
        _rl('v',      'cross',      0.48, 0,    0.48, 1   ),
        _rl('v',      'cross',      0.76, 0,    0.76, 1   ),
        RENDER,
    ],

    'gui_spinner': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('circle', 'spinner',    0.1,  0.05, 0.9,  0.95),   # ring outline
        RENDER,
    ],

    'gui_canvas': [
        # dashed rect pre-drawn by gc_draw_widget; interior empty by design
        RENDER,
    ],

    # ── Menu / Action ─────────────────────────────────────────────────────────

    'gui_menubar': [
        _rn('rect',   'strip',      0,    0,    1,    1   ),
        _rl('v',      'track',      0.22, 0,    0.22, 1   ),
        _rl('v',      'track',      0.44, 0,    0.44, 1   ),
        _rl('v',      'track',      0.66, 0,    0.66, 1   ),
        RENDER,
    ],

    'gui_toolbar': [
        _rn('rect',   'strip',      0,    0,    1,    1   ),
        _rn('square', 'icon',       0.03, 0.08, 0.21, 0.92),
        _rn('square', 'icon',       0.25, 0.08, 0.43, 0.92),
        _rn('square', 'icon',       0.47, 0.08, 0.65, 0.92),
        _rl('v',      'track',      0.69, 0.1,  0.69, 0.9 ),   # separator
        _rn('square', 'icon',       0.73, 0.08, 0.91, 0.92),
        RENDER,
    ],

    'gui_menu': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'row',        0,    0.02, 1,    0.25),    # row (no fill)
        _rn('rect',   'row',        0,    0.28, 1,    0.51),
        _rl('h',      'track',      0,    0.54, 1,    0.54),   # separator
        _rn('rect',   'row',        0,    0.57, 1,    0.8 ),
        RENDER,
    ],

    'gui_menuitem': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        # right-pointing tri: span_y=0.44*72=31.7 > span_x=0.1*160=16 → right ✓
        _rn('tri',    'body',       0.88, 0.28, 0.98, 0.72),   # ▶ submenu arrow
        RENDER,
    ],

    # ── Lists / Tree ──────────────────────────────────────────────────────────

    'gui_treeview': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'header',     0,    0,    1,    0.24),
        _rl('h',      'track',      0,    0.24, 1,    0.24),
        _rl('v',      'track',      0.5,  0,    0.5,  1   ),    # column divider
        _rn('rect',   'row',        0,    0.25, 1,    0.5 ),
        _rn('rect',   'row',        0,    0.5,  1,    0.75),
        _rn('rect',   'row',        0,    0.75, 1,    1   ),
        RENDER,
    ],

    'gui_listbox': [
        _rn('rect',   'body',       0,    0,    1,    1   ),
        _rn('rect',   'tab',        0,    0.01, 1,    0.3 ),    # selected row (tab = pal_btn)
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
        _rn('square', 'icon',       0.36, 0.52, 0.64, 0.96),
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
