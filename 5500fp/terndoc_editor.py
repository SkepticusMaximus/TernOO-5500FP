"""terndoc_editor.py — TernDoc S2 core: face-blind layout + input engine.

The half of a "custom editor" that must never be rebuilt: given a TernDoc
and a measuring function, LAYOUT computes wrapped lines, caret geometry,
and hit-testing; CONTROLLER turns abstract input events (typed text, keys,
clicks, drags) into document operations and cursor motion. A face — DPG
today, anything tomorrow — supplies two things only: a `measure(text,
style_key) -> width_px` callback and pixels on a screen. Every behavior
in here is testable with a monospace stub, no toolkit anywhere.

Style keys: "r" regular, "b" bold, "i" italic, "bi", "c" code — faces map
these to fonts/colors however they can; layout only needs widths.

Added: 22 Sep 2026 (S2, captain's non-stop order). Authors: Stevo + Claude.
"""

from __future__ import annotations

import terndoc as TD


def style_key(st, is_code_block=False):
    if is_code_block or "c" in st:
        return "c"
    b, i = "b" in st, "i" in st
    return "bi" if (b and i) else "b" if b else "i" if i else "r"


# ── layout ───────────────────────────────────────────────────────────────────
class Layout:
    """Wrapped-line geometry for one document at one width.

    Produces `lines`: dicts of
      bi        block index
      start,end offsets (codec units) of this visual line within its block
      segs      [(text, style_key, href, px_width, block_off_of_seg_start)]
      y         top of the line (px)
      h         line height (px)
    plus per-block prefix info (bullets, heading scale) the face may draw.
    """

    def __init__(self, doc, measure, wrap_px, line_h, pad_between_blocks=6,
                 heading_scale=(1.6, 1.35, 1.15)):
        self.doc = doc
        self.measure = measure
        self.wrap_px = max(40, wrap_px)
        self.line_h = line_h
        self.pad = pad_between_blocks
        self.hscale = heading_scale
        self.lines = []
        self.block_meta = []
        self._build()

    def _line_h_for(self, kind):
        if kind == "h1":
            return int(self.line_h * self.hscale[0])
        if kind == "h2":
            return int(self.line_h * self.hscale[1])
        if kind == "h3":
            return int(self.line_h * self.hscale[2])
        return self.line_h

    def _runs_of(self, b):
        """Flatten a block to (char, style_key, href, block_off) runs —
        char-granular so wrapping can break anywhere a word demands."""
        if b["kind"] == "code":
            return [(b["text"], "c", None, 0)] if b["text"] else []
        runs, off = [], 0
        for s in b["spans"]:
            runs.append((s["t"], style_key(s["st"]), s["href"], off))
            off += self.doc.codec.units(s["t"])
        return runs

    def _build(self):
        y = 0
        for bi, b in enumerate(self.doc.blocks):
            kind = b["kind"]
            lh = self._line_h_for(kind)
            self.block_meta.append(
                {"kind": kind, "line_h": lh,
                 "prefix": "• " if kind == "ul"
                           else "1. " if kind == "ol" else ""})
            text = self.doc.text_of(bi)
            # explicit newlines only inside code blocks
            paragraphs = text.split("\n") if kind == "code" else [text]
            base = 0
            runs = self._runs_of(b)
            emitted = False
            for para in paragraphs:
                for start, end in self._wrap_offsets(para, kind):
                    segs = self._segs_between(runs, base + start, base + end)
                    self.lines.append({"bi": bi, "start": base + start,
                                       "end": base + end, "segs": segs,
                                       "y": y, "h": lh})
                    y += lh
                    emitted = True
                base += self.doc.codec.units(para) + 1
            if not emitted:                       # empty block still a line
                self.lines.append({"bi": bi, "start": 0, "end": 0,
                                   "segs": [], "y": y, "h": lh})
                y += lh
            y += self.pad
        self.height = y

    def _wrap_offsets(self, text, kind):
        """Greedy word wrap by measured width; yields (start, end) offsets."""
        n = len(text)
        if n == 0:
            return
        sk = "c" if kind == "code" else "r"
        start = 0
        while start < n:
            lo, hi = start + 1, n
            while lo < hi:                       # widest fitting prefix
                mid = (lo + hi + 1) // 2
                if self.measure(text[start:mid], sk) <= self.wrap_px:
                    lo = mid
                else:
                    hi = mid - 1
            end = lo
            if end < n:                          # try to break at a space
                sp = text.rfind(" ", start + 1, end + 1)
                if sp > start:
                    end = sp
            yield start, end
            start = end
            while start < n and text[start] == " ":
                start += 1

    def _segs_between(self, runs, a, b):
        segs, off_ct = [], a
        for t, sk, href, roff in runs:
            rn = len(t)
            s0, s1 = max(a, roff), min(b, roff + rn)
            if s0 < s1:
                frag = t[s0 - roff:s1 - roff]
                segs.append((frag, sk, href, self.measure(frag, sk), s0))
        return segs

    # ── geometry queries ───────────────────────────────────────────────
    def line_index_of(self, bi, off):
        cand = [i for i, ln in enumerate(self.lines) if ln["bi"] == bi]
        for i in cand:
            ln = self.lines[i]
            if ln["start"] <= off < ln["end"]:
                return i
        # end-of-block cursor sits on the block's last line
        return cand[-1] if cand else 0

    def caret_xy(self, bi, off):
        i = self.line_index_of(bi, off)
        ln = self.lines[i]
        x = 0
        for frag, sk, _h, w, s0 in ln["segs"]:
            fn = len(frag)
            if off <= s0:
                break
            if off >= s0 + fn:
                x += w
            else:
                x += self.measure(frag[:off - s0], sk)
                break
        return x, ln["y"], ln["h"]

    def hit_test(self, x, y):
        """Pixel → (bi, off). Clamps to nearest line / nearest char."""
        if not self.lines:
            return (0, 0)
        ln = self.lines[-1]
        for cand in self.lines:
            if cand["y"] <= y < cand["y"] + cand["h"]:
                ln = cand
                break
        else:
            if y < self.lines[0]["y"]:
                ln = self.lines[0]
        off, acc = ln["start"], 0
        for frag, sk, _h, w, s0 in ln["segs"]:
            if x > acc + w:
                acc += w
                off = s0 + len(frag)
                continue
            # inside this segment: scan char by char
            for k in range(1, len(frag) + 1):
                if self.measure(frag[:k], sk) > x - acc:
                    return (ln["bi"], s0 + k - 1)
            return (ln["bi"], s0 + len(frag))
        return (ln["bi"], off)


# ── controller ───────────────────────────────────────────────────────────────
class Editor:
    """Face-blind input handling. The face forwards events; this mutates
    the doc and cursor. `relayout()` must be given a fresh Layout after
    anything that changes text or width — the face owns WHEN to relayout
    (typically once per frame or per event), we own WHAT happens."""

    def __init__(self, doc):
        self.doc = doc
        self.layout = None
        self.prefer_x = None                     # sticky column for up/down

    def attach_layout(self, layout):
        self.layout = layout

    # — selection helpers —
    def _sel(self):
        d = self.doc
        if d.anchor is None or d.anchor == d.cursor:
            return None
        (ab, ao), (cb, co) = d.anchor, d.cursor
        if ab != cb:                             # cross-block: clamp S2 scope
            return None
        return (ab, min(ao, co), max(ao, co))

    def _delete_selection(self):
        sel = self._sel()
        if sel:
            bi, a, b = sel
            self.doc.delete_range(bi, a, b)
            return True
        return False

    # — events —
    def type_text(self, text):
        self._delete_selection()
        bi, off = self.doc.cursor
        self.doc.insert_text(bi, off, text)
        self.prefer_x = None

    def key_enter(self):
        self._delete_selection()
        bi, off = self.doc.cursor
        self.doc.split_block(bi, off)
        self.prefer_x = None

    def key_backspace(self):
        if self._delete_selection():
            return
        bi, off = self.doc.cursor
        if off > 0:
            self.doc.delete_range(bi, off - 1, off)
        else:
            self.doc.merge_with_previous(bi)
        self.prefer_x = None

    def key_delete(self):
        if self._delete_selection():
            return
        bi, off = self.doc.cursor
        if off < self.doc.block_len(bi):
            self.doc.delete_range(bi, off, off + 1)
        elif bi + 1 < len(self.doc.blocks):
            self.doc.merge_with_previous(bi + 1)
        self.prefer_x = None

    def move_h(self, delta, select=False):
        d = self.doc
        bi, off = d.cursor
        if select and d.anchor is None:
            d.anchor = d.cursor
        if not select:
            d.anchor = None
        off += delta
        if off < 0:
            if bi > 0:
                bi -= 1
                off = d.block_len(bi)
            else:
                off = 0
        elif off > d.block_len(bi):
            if bi + 1 < len(d.blocks):
                bi, off = bi + 1, 0
            else:
                off = d.block_len(bi)
        d.cursor = (bi, off)
        self.prefer_x = None

    def move_v(self, delta, select=False):
        d, L = self.doc, self.layout
        if L is None:
            return
        if select and d.anchor is None:
            d.anchor = d.cursor
        if not select:
            d.anchor = None
        bi, off = d.cursor
        x, y, h = L.caret_xy(bi, off)
        if self.prefer_x is None:
            self.prefer_x = x
        i = L.line_index_of(bi, off) + delta
        if 0 <= i < len(L.lines):
            ln = L.lines[i]
            d.cursor = L.hit_test(self.prefer_x, ln["y"] + 1)

    def home(self, select=False):
        d, L = self.doc, self.layout
        if select and d.anchor is None:
            d.anchor = d.cursor
        if not select:
            d.anchor = None
        bi, off = d.cursor
        ln = L.lines[L.line_index_of(bi, off)] if L else None
        d.cursor = (bi, ln["start"] if ln else 0)
        self.prefer_x = None

    def end(self, select=False):
        d, L = self.doc, self.layout
        if select and d.anchor is None:
            d.anchor = d.cursor
        if not select:
            d.anchor = None
        bi, off = d.cursor
        ln = L.lines[L.line_index_of(bi, off)] if L else None
        d.cursor = (bi, ln["end"] if ln else self.doc.block_len(bi))
        self.prefer_x = None

    def click(self, x, y, select=False):
        if self.layout is None:
            return
        pos = self.layout.hit_test(x, y)
        d = self.doc
        if select:
            if d.anchor is None:
                d.anchor = d.cursor
        else:
            d.anchor = pos
        d.cursor = pos
        self.prefer_x = None

    def drag(self, x, y):
        if self.layout is None:
            return
        self.doc.cursor = self.layout.hit_test(x, y)

    def select_all_block(self):
        bi, _ = self.doc.cursor
        self.doc.anchor = (bi, 0)
        self.doc.cursor = (bi, self.doc.block_len(bi))

    # — styling / structure shortcuts —
    def toggle(self, flag):
        sel = self._sel()
        if sel:
            bi, a, b = sel
            self.doc.toggle_style(bi, a, b, flag)

    def set_kind(self, kind, lang=""):
        bi, _ = self.doc.cursor
        self.doc.set_kind(bi, kind, lang)

    def undo(self):
        self.doc.undo()

    def redo(self):
        self.doc.redo()

    def selected_text(self):
        sel = self._sel()
        if not sel:
            return ""
        bi, a, b = sel
        return self.doc.codec.slice(self.doc.text_of(bi), a, b)
