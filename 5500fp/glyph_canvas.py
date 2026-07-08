"""glyph_canvas.py — the classroom canvas renderer (Deliverable C).

A GlyphSurface draws native glyph words onto a tk.Canvas, laying them out
left-to-right at a monospace advance with simple line-wrap, and retaining
drawn lines so scrolling is a translate (canvas.move), never a re-jitter.

Two VOICES, same geometry, different stroke projection — the babble-fish
point (one original, many renderings):
  * chalk (the board): light strokes on the dark slate, small deterministic
    per-line jitter (seed = line index, so redraws never shimmer), a faint
    second dust pass.
  * ink (the book): smooth strokes, round caps/joins, dark ink on the page.

The renderer REFUSES a literal (T18 != 0): parse_glyph raises, and we let it —
a number must be projected to digit glyph words first (S4). A Y the house font
cannot supply renders the '~' placeholder (R1) — screen only; the stored words
remain the kept original (a rendering is a lossy projection). X and Z are
ignored in v1 layout (see O1/O2): order comes from layout_order(), the single
place that decides sequence.

Date: 2026-07-08, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import random

import ternoo_glyph as G
import ternoo_glyph_strokes as S

# voice → drawing config
VOICES = {
    'chalk': {'color': '#e8e4d8', 'width': 2, 'jitter': 0.6, 'dust': True},
    'ink':   {'color': '#2a2018', 'width': 2, 'jitter': 0.0, 'dust': False},
}


# ═══════════════════════════════════════════════════════════════════════════
# Pure layout / geometry (UI-free — pinned in test_glyph_canvas.py)
# ═══════════════════════════════════════════════════════════════════════════

def scale_for(size: float, case: int) -> float:
    """px per grid unit. size = cap height in px; lowercase renders at 2/3
    (small-caps interim), upper/caseless at full scale."""
    s = size / 6.0
    return s * (2.0 / 3.0) if case == -1 else s


def advance_px(size: float) -> float:
    """Monospace cell advance — independent of case (data is monospaced)."""
    return S.ADVANCE * (size / 6.0)


def grid_to_xy(gx, gy, ox, baseline, scale):
    """Design-grid point → canvas point (grid y is up, canvas y is down)."""
    return (ox + gx * scale, baseline - gy * scale)


def resolve_glyph(word: int):
    """(ordinal, case, polylines, is_placeholder). Raises on a literal — the
    renderer refuses it. A Y with no house-font member falls to '~' (R1)."""
    ordinal, case = G.parse_glyph(word)          # raises GlyphError on literal
    strokes = S.strokes_for_ordinal(ordinal)
    placeholder = strokes is None
    if placeholder:
        strokes = S.strokes_for_ordinal(G.PLACEHOLDER_ORD)
    return ordinal, case, strokes, placeholder


def layout_order(words):
    """THE single place sequence is decided. v1: produced order (== X order by
    construction this build). O2 (dense vs fractional X) is the open item; no
    other code may assume adjacency or arithmetic on X."""
    return list(words)


def plan_layout(words, width_px: float, size: float, x0: float = 4.0):
    """Assign each word a (cell_x, line_index) with monospace advance and a
    wrap at width_px. Pure — testable without a display."""
    adv = advance_px(size)
    x = x0
    line = 0
    out = []
    for w in layout_order(words):
        if x > x0 and x + adv > width_px:
            x = x0
            line += 1
        out.append((w, x, line))
        x += adv
    return out


# ═══════════════════════════════════════════════════════════════════════════
# GlyphSurface (furniture — screen-verified by Stevo)
# ═══════════════════════════════════════════════════════════════════════════

class GlyphSurface:
    """Wraps a tk.Canvas as a scrolling glyph surface in one voice."""

    def __init__(self, canvas, voice='ink', size=18, pad_top=8, line_gap=1.5):
        self.canvas = canvas
        self.voice = voice if voice in VOICES else 'ink'
        self.size = size
        self.pad_top = pad_top
        self.line_gap = line_gap
        self._lines = []                 # list of word-lists (the drawn history)
        self._y = pad_top                # next baseline offset (content coords)

    def clear(self):
        self.canvas.delete('glyph')
        self._lines = []
        self._y = self.pad_top

    def append_words(self, words):
        """Draw one logical line (wrapping as needed) beneath the last."""
        self._lines.append(list(words))
        width = self.canvas.winfo_width() or 600
        placed = plan_layout(words, width, self.size)
        line_h = self.size * self.line_gap
        max_line = max((ln for _, _, ln in placed), default=0)
        base0 = self._y + self.size          # first baseline (cap sits above)
        for w, cx, ln in placed:
            self._draw_glyph(w, cx, base0 + ln * line_h, len(self._lines))
        self._y = base0 + (max_line + 1) * line_h - self.size
        self._scroll_into_view()

    def append_text(self, text):
        """Convenience: normalize + project to glyph words (the shared
        to_house_words front-end — saddle §1), one logical line per newline.
        A newline is a line break, never a glyph. Screen path only; the ~
        placeholder always leaves a paper trail in the growth ledger."""
        for line in text.split('\n'):
            self.append_words(G.to_house_words(line))

    def _draw_glyph(self, word, ox, baseline, line_index):
        try:
            _, case, strokes, _ph = resolve_glyph(word)
        except G.GlyphError:
            raise                              # literal reaching the renderer
        scale = scale_for(self.size, case)
        cfg = VOICES[self.voice]
        rng = random.Random(line_index * 1009 + int(ox))
        jit = cfg['jitter']

        def pt(gx, gy):
            x, y = grid_to_xy(gx, gy, ox, baseline, scale)
            if jit:
                x += rng.uniform(-jit, jit)
                y += rng.uniform(-jit, jit)
            return x, y

        for poly in strokes:
            pts = [pt(gx, gy) for gx, gy in poly]
            if len(pts) == 1:                  # single point → dot
                x, y = pts[0]
                r = cfg['width'] / 2.0
                self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                        fill=cfg['color'], outline='',
                                        tags='glyph')
                continue
            flat = [c for p in pts for c in p]
            # smooth=True splines the polyline — curves flow instead of facet,
            # which suits a chalk/ink hand. capstyle/joinstyle keep ends soft.
            if cfg['dust']:
                self.canvas.create_line(*flat, fill=cfg['color'],
                                        width=cfg['width'] + 1, tags='glyph',
                                        capstyle='round', joinstyle='round',
                                        smooth=True)
            self.canvas.create_line(*flat, fill=cfg['color'],
                                    width=cfg['width'], tags='glyph',
                                    capstyle='round', joinstyle='round',
                                    smooth=True)

    def redraw(self):
        """Re-lay the retained history (first map / resize rewrap)."""
        lines = self._lines
        self.clear()
        for wl in lines:
            self.append_words(wl)

    def _scroll_into_view(self):
        h = self.canvas.winfo_height() or 300
        overflow = self._y - h + self.size
        if overflow > 0:
            self.canvas.move('glyph', 0, -overflow)
            self._y -= overflow
