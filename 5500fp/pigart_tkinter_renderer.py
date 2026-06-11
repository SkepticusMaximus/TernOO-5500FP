#!/usr/bin/env python3
"""PIGART tkinter renderer — Meccano Library v0.6

Walks a MeccanoProgram's word stream and renders it to a tkinter Canvas.
Same dispatch shape as pigart_ascii_renderer — same five PIGART opcodes,
same operand layout, same v0.4 DATA-STRING decoding.

Coordinate convention:
  Meccano units map to pixels via `scale` (default 12 px/unit).
  A point at (x, y) renders at pixel (x*scale + padding, y*scale + padding).
  tkinter Canvas uses top-left = (0, 0) with Y increasing downward —
  identical to the ASCII renderer convention. No coordinate flip needed.

Label convention (v0.4):
  DATA-STRING/ASCII words, 3 chars per word, base-128 packed.
  Decoded by _decode_label_words() — duplicated from pigart_ascii_renderer
  to keep this module self-contained. v0.7 factoring will consolidate both.

CAI flag (v0.6):
  Helper duplication (decode_xy, decode_size, decode_label_words) is
  intentional for v0.6. v0.7 spec should factor these into a shared
  meccano_pigart_helpers.py. See Meccano-Library-v06-CWC-Spec.md §Flags.

Date: 2026-06-11, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Companion specs: Meccano-Library-v06-CWC-Spec.md
"""

from __future__ import annotations
import os
import sys
import importlib.util as _ilu
from typing import Optional, List

import tkinter as tk

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
OP_RPOINT          = _v03.OP_RPOINT
OP_RLINE           = _v03.OP_RLINE
OP_RNODE           = _v03.OP_RNODE
OP_REDGE           = _v03.OP_REDGE
OP_RENDER          = _v03.OP_RENDER


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers (duplicated from pigart_ascii_renderer — v0.7 will factor these out)
# ═══════════════════════════════════════════════════════════════════════════════

def _decode_xy(map_word: int) -> tuple[int, int]:
    """Extract (x, y) from an ON_PLANE MAP word.

    MAP words built by _build_xy_map(x, y) use ON_PLANE mode (axis_xy=0):
      decode_map_word returns mode='ON_PLANE', coords={'X': col, 'Y': row}

    For ORIGIN-mode v0.1 MAP words, defaults to (0, 0).
    """
    d      = decode_map_word(map_word)
    coords = d.get('coords', {})
    return int(coords.get('X', 0)), int(coords.get('Y', 0))


def _decode_size(size_word: int) -> tuple[int, int]:
    """Extract (width, height) from a DATA size word.

    Size word convention (v0.2+):
      T11-T6 (tb tribble) = width
      T5-T0  (tc tribble) = height
    """
    w = int(get_field(size_word, 6, 6))  # T11-T6
    h = int(get_field(size_word, 0, 6))  # T5-T0
    return w, h


def _decode_label_words(string_operands: List[int]) -> str:
    """Decode a sequence of DATA-STRING/ASCII words into a Python string.

    Each word was encoded by _encode_label() in meccano_lib:
      packed = c0 + c1*128 + c2*128²   (base-128, 3 chars per word)

    Non-STRING words terminate decoding early (defensive).
    Trailing null bytes are stripped.
    """
    chars: List[int] = []
    for w in string_operands:
        d = decode_word(w)
        if d.get('type') != 'STRING':
            break
        n = int(d['length_or_addr'])
        chars.append(n % 128)
        chars.append((n // 128) % 128)
        chars.append((n // 16384) % 128)
    while chars and chars[-1] == 0:
        chars.pop()
    return ''.join(chr(c) for c in chars)


# ═══════════════════════════════════════════════════════════════════════════════
# Per-opcode dispatchers
# ═══════════════════════════════════════════════════════════════════════════════

def _dispatch_rpoint(canvas: tk.Canvas, operands: List[int],
                     scale: int, padding: int) -> None:
    """RPOINT: MAP(position) [+ DATA(colour)].

    Draws a small filled dot (3×3 pixels centred on the coordinate).
    Colour operand is accepted but ignored in v0.6 (monochrome).
    """
    if not operands:
        return
    x, y = _decode_xy(operands[0])
    px, py = x * scale + padding, y * scale + padding
    canvas.create_oval(px - 1, py - 1, px + 1, py + 1,
                       fill='black', outline='black')


def _dispatch_rline(canvas: tk.Canvas, operands: List[int],
                    scale: int, padding: int) -> None:
    """RLINE: MAP(start) + MAP(end) [+ DATA(style)].

    Draws a plain black line between the two positions.
    Style operand ignored in v0.6.
    """
    if len(operands) < 2:
        return
    x1, y1 = _decode_xy(operands[0])
    x2, y2 = _decode_xy(operands[1])
    canvas.create_line(
        x1 * scale + padding, y1 * scale + padding,
        x2 * scale + padding, y2 * scale + padding,
        fill='black', width=1,
    )


def _dispatch_rnode(canvas: tk.Canvas, operands: List[int],
                    scale: int, padding: int) -> None:
    """RNODE: MAP(top-left) + DATA(size) [+ DATA-STRING words for label].

    Draws a rectangle outline (1px black border, transparent fill).
    If label words are present, centres the label text inside the rectangle.

    Font: Courier 10 — monospace, pairs naturally with ASCII-derived coordinates.
    If label text clips visually, this is flagged for v0.7 (font metrics vs
    Meccano coordinate units can diverge; see spec §Flags item 3).
    """
    if len(operands) < 2:
        return

    x, y   = _decode_xy(operands[0])
    w, h   = _decode_size(operands[1])
    label  = _decode_label_words(operands[2:]) if len(operands) > 2 else ''

    # Convert to pixel corners
    x0 = x * scale + padding
    y0 = y * scale + padding
    x1 = (x + w) * scale + padding
    y1 = (y + h) * scale + padding

    canvas.create_rectangle(x0, y0, x1, y1,
                             outline='black', fill='', width=1)

    if label:
        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        canvas.create_text(cx, cy, text=label,
                           font=('Courier', 10), anchor='center')


def _dispatch_redge(canvas: tk.Canvas, operands: List[int],
                    scale: int, padding: int) -> None:
    """REDGE: MAP(start) + MAP(end) [+ DATA(style)].

    Draws a directed line with an arrowhead at the endpoint.
    Uses tkinter's built-in arrow='last' for the arrowhead.
    """
    if len(operands) < 2:
        return
    x1, y1 = _decode_xy(operands[0])
    x2, y2 = _decode_xy(operands[1])
    canvas.create_line(
        x1 * scale + padding, y1 * scale + padding,
        x2 * scale + padding, y2 * scale + padding,
        fill='black', width=1, arrow='last',
        arrowshape=(8, 10, 4),   # (d1, d2, d3) — compact arrowhead
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Core builder
# ═══════════════════════════════════════════════════════════════════════════════

def _build_canvas(program,
                  scale: int = 12,
                  padding: int = 20) -> tuple[tk.Tk, tk.Canvas]:
    """Build a tkinter Canvas with the program's shapes drawn on it.

    Walks program.to_words(), skips the two-word TTree/OTree header, then
    dispatches each PIGART opcode exactly as pigart_ascii_renderer does —
    same words, different output.

    Window size is derived from program.bounds(): the canvas is sized to
    contain the entire rendered area with `padding` pixels of margin on all
    sides.

    Returns (root, canvas). The root is in a withdrawn (hidden) state.
    Caller decides whether to deiconify + mainloop (render_gui) or inspect
    + destroy (tests).

    Raises:
        ValueError:  non-PIGART OPCODE or unknown mnemonic encountered.
        tk.TclError: if no display is available (headless environment).
    """
    # Compute canvas pixel size from program bounds
    try:
        min_x, min_y, max_x, max_y = program.bounds()
    except (ValueError, AttributeError):
        # Fallback for programs with no positioned opcodes or missing bounds()
        min_x = min_y = 0
        max_x, max_y  = 60, 20

    canvas_w = (max_x + 1) * scale + 2 * padding
    canvas_h = (max_y + 1) * scale + 2 * padding

    # Build root + canvas (root is hidden until caller decides to show it)
    root   = tk.Tk()
    root.withdraw()

    canvas = tk.Canvas(root, width=canvas_w, height=canvas_h,
                       background='white')
    canvas.pack()

    # Walk word stream — same dispatch logic as pigart_ascii_renderer.render()
    words = program.to_words()
    i = 2   # skip TTree MAP header (words[0]) and OTree MAP header (words[1])

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
            _dispatch_rpoint(canvas, operands, scale, padding)
        elif mnemonic == 'RLINE':
            _dispatch_rline(canvas, operands, scale, padding)
        elif mnemonic == 'RNODE':
            _dispatch_rnode(canvas, operands, scale, padding)
        elif mnemonic == 'REDGE':
            _dispatch_redge(canvas, operands, scale, padding)
        elif mnemonic == 'RENDER':
            canvas.update_idletasks()
        else:
            raise ValueError(f"unknown PIGART opcode: {mnemonic!r}")

        i += 1 + arity

    return root, canvas


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════

def render_gui(program,
               scale: int = 12,
               padding: int = 20,
               title: Optional[str] = None,
               blocking: bool = True) -> tk.Tk:
    """Open a tkinter window and render the program as GUI shapes.

    Window size is computed from program.bounds() so the rendered output
    fits with `padding` pixels of margin around it.

    Args:
        program:  MeccanoProgram instance.
        scale:    Pixels per Meccano coordinate unit (default 12 —
                  roughly matches a monospace character cell at 12pt).
        padding:  Pixels of margin around the rendered area (default 20).
        title:    Window title (default: program.name).
        blocking: If True (default), calls mainloop() and blocks until
                  the window is closed. If False, returns the Tk root
                  immediately for programmatic control or tests.

    Returns:
        The Tk root window (for tests or non-blocking callers).
    """
    root, canvas = _build_canvas(program, scale=scale, padding=padding)

    # Set window title
    name  = getattr(program, 'name', 'MeccanoProgram')
    root.title(title if title is not None else name)

    # Size the root window to exactly fit the canvas
    root.geometry(f"{canvas['width']}x{canvas['height']}")

    # Show the window
    root.deiconify()

    if blocking:
        root.mainloop()

    return root


# ═══════════════════════════════════════════════════════════════════════════════
# __main__ — smoke test (headless-safe)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    import sys
    print("pigart_tkinter_renderer: import OK, use meccano_lib.py --render-gui <program>")
    sys.exit(0)
