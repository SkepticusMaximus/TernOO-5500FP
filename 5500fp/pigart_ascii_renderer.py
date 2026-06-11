#!/usr/bin/env python3
"""PIGART ASCII renderer — Meccano Library v0.2

Walks a MeccanoProgram's word stream and produces a text-art canvas.
v0.2 supports RPOINT, RLINE, RNODE, RENDER.
REDGE is deferred to v0.3.

Coordinate convention (v0.2):
  MAP words are built in ON_PLANE mode (axis_yz=1, axis_xz=1, axis_xy=0).
  decode_map_word returns coords={'X': col, 'Y': row}.
  Canvas units = character columns/rows directly (no scaling).

Size convention (v0.2):
  DATA/SCALAR int words carry (width, height) packed as two tribbles:
    T11-T6 (tb) = width
    T5-T0  (tc) = height
  Extracted via get_field(w, 6, 6) and get_field(w, 0, 6).

Label convention (v0.2):
  DATA/SCALAR int word with value = label_id (small integer).
  Looked up in LABEL_TABLE for the display string.

Date: 2026-06-11, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Companion spec: Meccano-Library-v02-CWC-Spec.md
"""

from __future__ import annotations
import os
import sys
import importlib.util as _ilu
from typing import List

# ── Load 5500fp_ternoo_v03 via importlib (filename starts with a digit) ───────
_v03_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '5500fp_ternoo_v03.py')
_v03_spec = _ilu.spec_from_file_location('ternoo_v03', _v03_path)
_v03      = _ilu.module_from_spec(_v03_spec)
_v03_spec.loader.exec_module(_v03)

decode_opcode_word = _v03.decode_opcode_word
decode_word        = _v03.decode_word
decode_map_word    = _v03.decode_map_word
get_primary        = _v03.get_primary
get_field          = _v03.get_field
PRIMARY_OPCODE     = _v03.PRIMARY_OPCODE
OPF_PIGART         = _v03.OPF_PIGART


# ── Label table for v0.2 (proper text encoding is v0.3) ───────────────────────
LABEL_TABLE: dict[int, str] = {
    0: '',
    1: 'Title',
    2: 'OK',
    3: 'Cancel',
    4: 'File',
    5: 'Edit',
    6: 'Hello',
}


# ═══════════════════════════════════════════════════════════════════════════════
# AsciiCanvas
# ═══════════════════════════════════════════════════════════════════════════════

class AsciiCanvas:
    """Fixed-size character grid. Default 60 columns × 20 rows."""

    def __init__(self, width: int = 60, height: int = 20):
        self.width  = width
        self.height = height
        self.grid   = [[' '] * width for _ in range(height)]

    def set(self, x: int, y: int, ch: str) -> None:
        """Place a character at (x, y) if in bounds."""
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = ch

    def draw_line(self, x1: int, y1: int, x2: int, y2: int) -> None:
        """Draw a line between two points.

        Horizontal lines use '-', vertical lines use '|'.
        Diagonal lines use Bresenham's algorithm with '*'.
        v0.2 widget rectangles only need H/V — diagonal is included for RLINE.
        """
        if y1 == y2:          # horizontal
            ch = '-'
            for x in range(min(x1, x2), max(x1, x2) + 1):
                self.set(x, y1, ch)
        elif x1 == x2:        # vertical
            ch = '|'
            for y in range(min(y1, y2), max(y1, y2) + 1):
                self.set(x1, y, ch)
        else:                  # diagonal — Bresenham
            dx  = abs(x2 - x1); dy = abs(y2 - y1)
            sx  = 1 if x2 > x1 else -1
            sy  = 1 if y2 > y1 else -1
            err = dx - dy
            x, y = x1, y1
            while True:
                self.set(x, y, '*')
                if x == x2 and y == y2:
                    break
                e2 = 2 * err
                if e2 > -dy:
                    err -= dy; x += sx
                if e2 <  dx:
                    err += dx; y += sy

    def draw_rect(self, x: int, y: int, w: int, h: int) -> None:
        """Draw a rectangle border using '+', '-', '|'.

        Corners: '+'   Horizontal edges: '-'   Vertical edges: '|'
        Interior is left blank (caller may fill with draw_label).
        Clamps silently to canvas bounds via self.set().
        """
        if w < 2 or h < 2:
            return  # degenerate rectangle — nothing to draw
        # Corners
        self.set(x,       y,       '+')
        self.set(x + w-1, y,       '+')
        self.set(x,       y + h-1, '+')
        self.set(x + w-1, y + h-1, '+')
        # Horizontal edges
        for col in range(x + 1, x + w - 1):
            self.set(col, y,       '-')
            self.set(col, y + h-1, '-')
        # Vertical edges
        for row in range(y + 1, y + h - 1):
            self.set(x,       row, '|')
            self.set(x + w-1, row, '|')

    def draw_label(self, x: int, y: int, text: str, max_width: int) -> None:
        """Draw text starting at (x, y), truncating to max_width characters."""
        text = text[:max_width]
        for i, ch in enumerate(text):
            self.set(x + i, y, ch)

    def __str__(self) -> str:
        return '\n'.join(''.join(row) for row in self.grid)


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def render(program, width: int = 60, height: int = 20) -> str:
    """Render a MeccanoProgram to ASCII text.

    Args:
        program: MeccanoProgram instance
        width, height: canvas dimensions in characters

    Returns:
        ASCII canvas as a multi-line string (width * height characters
        split across height lines)

    Raises:
        ValueError:         unknown OPCODE family or unsupported opcode
        NotImplementedError: REDGE encountered (deferred to v0.3)
    """
    canvas = AsciiCanvas(width, height)
    words  = program.to_words()

    # words[0] = TTree MAP header, words[1] = OTree MAP header — skip both
    i = 2
    while i < len(words):
        w = words[i]

        if get_primary(w) != PRIMARY_OPCODE:
            raise ValueError(
                f"expected OPCODE at word index {i}, "
                f"got primary={get_primary(w)} (word={w})"
            )

        decoded  = decode_opcode_word(w)
        if decoded['family'] != OPF_PIGART:
            raise ValueError(
                f"non-PIGART OPCODE in render stream at index {i}: "
                f"family={decoded['family_name']!r}"
            )

        mnemonic = decoded['mnemonic']
        arity    = decoded['arity']
        operands = words[i + 1 : i + 1 + arity]

        if mnemonic == 'RPOINT':
            _dispatch_rpoint(canvas, operands)
        elif mnemonic == 'RLINE':
            _dispatch_rline(canvas, operands)
        elif mnemonic == 'RNODE':
            _dispatch_rnode(canvas, operands)
        elif mnemonic == 'REDGE':
            raise NotImplementedError("REDGE deferred to v0.3")
        elif mnemonic == 'RENDER':
            pass  # no double-buffering in v0.2 — canvas updates are immediate
        else:
            raise ValueError(f"unknown PIGART opcode: {mnemonic!r}")

        i += 1 + arity

    return str(canvas)


# ═══════════════════════════════════════════════════════════════════════════════
# Dispatch helpers
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_xy(map_word: int) -> tuple[int, int]:
    """Extract (x, y) from an ON_PLANE MAP word.

    MAP words built by _build_xy_map(x, y) use ON_PLANE mode (axis_xy=0):
      decode_map_word returns mode='ON_PLANE', coords={'X': col, 'Y': row}

    If the word is in a different MAP mode (e.g. ORIGIN from v0.1 examples),
    coords may lack 'X'/'Y'; defaults to (0, 0) to fail softly.
    """
    d      = decode_map_word(map_word)
    coords = d.get('coords', {})
    return int(coords.get('X', 0)), int(coords.get('Y', 0))


def _dispatch_rpoint(canvas: AsciiCanvas, operands: List[int]) -> None:
    """RPOINT: MAP(position) [+ DATA(colour/char)].

    Draws '*' at the MAP position. Colour operand is accepted but ignored
    in ASCII mode — v0.3 may map colour values to Unicode block chars.
    """
    if not operands:
        return
    x, y = _extract_xy(operands[0])
    canvas.set(x, y, '*')


def _dispatch_rline(canvas: AsciiCanvas, operands: List[int]) -> None:
    """RLINE: MAP(start) + MAP(end) [+ DATA(style)].

    Draws a line between the two MAP positions using AsciiCanvas.draw_line().
    Style operand is accepted but ignored in v0.2.
    """
    if len(operands) < 2:
        return
    x1, y1 = _extract_xy(operands[0])
    x2, y2 = _extract_xy(operands[1])
    canvas.draw_line(x1, y1, x2, y2)


def _dispatch_rnode(canvas: AsciiCanvas, operands: List[int]) -> None:
    """RNODE: MAP(top-left) + DATA(size) [+ DATA(label_id)].

    Size DATA word convention (v0.2):
      T11-T6 (tb tribble) = width
      T5-T0  (tc tribble) = height
    Extracted via get_field(w, 6, 6) and get_field(w, 0, 6).

    Label DATA word: DATA/SCALAR int, value = label_id, looked up in LABEL_TABLE.
    Label is drawn centred horizontally in the first interior row.
    """
    if len(operands) < 2:
        return

    # Position
    x, y = _extract_xy(operands[0])

    # Size — packed two-tribble encoding
    size_word = operands[1]
    w = int(get_field(size_word, 6, 6))   # T11-T6 = width
    h = int(get_field(size_word, 0, 6))   # T5-T0  = height

    canvas.draw_rect(x, y, w, h)

    # Label (optional third operand)
    if len(operands) >= 3 and w > 4 and h > 2:
        label_word = operands[2]
        d          = decode_word(label_word)
        label_id   = int(d.get('value', 0))
        label_text = LABEL_TABLE.get(label_id, '')
        if label_text:
            # Centre horizontally in the interior; place in first interior row
            interior_width = w - 2
            pad            = max(0, (interior_width - len(label_text)) // 2)
            lx             = x + 1 + pad
            ly             = y + 1
            canvas.draw_label(lx, ly, label_text, interior_width)


# ═══════════════════════════════════════════════════════════════════════════════
# __main__ — self-test
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if '--self-test' in sys.argv:
        # Minimal smoke test: build a one-rectangle program inline and render it.
        # Does not import meccano_lib to keep the renderer self-contained.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from ternoo_gristmill import MMID, MOD, ternary_op, extract_tribbles, build_otree_mmoe

        from_trits = _v03.from_trits
        to_trits   = _v03.to_trits
        build_opcode_word = _v03.build_opcode_word
        build_map_word    = _v03.build_map_word
        build_int_word    = _v03.build_int_word
        OP_RNODE          = _v03.OP_RNODE
        OP_RENDER         = _v03.OP_RENDER

        def _bxy(x, y):
            return build_map_word(1, 1, 0, from_trits(to_trits(y, 9) + to_trits(x, 9)))

        def _bsz(w, h):
            return build_int_word(from_trits(to_trits(h, 6) + to_trits(w, 6) + [0]*6))

        # Inline stub program (avoids circular import with meccano_lib)
        class _Stub:
            def __init__(self):
                op_rnode = build_opcode_word(OPF_PIGART, arity=2, op_index=OP_RNODE)
                op_render = build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER)
                pos  = _bxy(2, 1)
                size = _bsz(20, 8)
                body = [op_rnode, pos, size, op_render]
                mmid       = MMID('meccano_program_pigart')
                S = 0
                for i, w in enumerate(body):
                    ta, tb, _ = extract_tribbles(w)
                    S = (S + ternary_op(ta * (i+1), tb)) % MOD
                otree_word = build_otree_mmoe(S)
                self._words = [mmid.word, otree_word] + body

            def to_words(self):
                return self._words

        stub = _Stub()
        output = render(stub)
        assert isinstance(output, str) and len(output) > 0, "render produced empty output"
        assert any(c in output for c in '+-|'), "render produced no rectangle chars"
        print("pigart_ascii_renderer --self-test: PASS")
        sys.exit(0)

    print("Usage: pigart_ascii_renderer.py --self-test")
    sys.exit(2)
