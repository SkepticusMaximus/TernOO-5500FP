#!/usr/bin/env python3
"""flowcode_bridge.py — FlowCode → widget_lib bridge (TernOO v0.7)

Translates an FCCanvas (FlowCode in-memory graph) into a MeccanoProgram
(TernOO PIGART word stream), ready for ASCII or tkinter rendering.

Scale convention:
  FCSymbol.x / FCSymbol.y are pixel coordinates (GRID=40px per cell).
  SYMBOL_W=120px, SYMBOL_H=60px is the standard symbol bounding box.
  FC_GRID_TO_MECCANO converts pixels → Meccano coordinate units.
  At FC_GRID_TO_MECCANO=10:  120px→12 units wide, 60px→6 units tall.
  A 60×20 ASCII canvas holds roughly 5 columns × 3 rows of symbols.

Extensibility:
  FLOWCODE_SHAPE_MAP maps the 4 current FC symbol kinds to SHAPE_* IDs.
  Adding a new FC kind = one new line in FLOWCODE_SHAPE_MAP + a SHAPE_*
  constant in widget_lib.py. The bridge logic itself does not change.

Date: 2026-06-15, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations
import os
import sys
import importlib.util as _ilu
from typing import Optional

# ── Load widget_lib via importlib (same pattern as renderers) ─────────────────
_wl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widget_lib.py')
_wl_spec = _ilu.spec_from_file_location('widget_lib', _wl_path)
_wl      = _ilu.module_from_spec(_wl_spec)
_wl_spec.loader.exec_module(_wl)

MeccanoProgram           = _wl.MeccanoProgram
build_opcode_word        = _wl.build_opcode_word
build_rnode_shape_labeled = _wl.build_rnode_shape_labeled
build_redge_styled       = _wl.build_redge_styled
build_redge_labeled      = _wl.build_redge_labeled
OPF_PIGART               = _wl.OPF_PIGART
OP_RENDER                = _wl.OP_RENDER
SHAPE_RECTANGLE          = _wl.SHAPE_RECTANGLE
SHAPE_TERMINATOR         = _wl.SHAPE_TERMINATOR
SHAPE_PROCESS            = _wl.SHAPE_PROCESS
SHAPE_DECISION           = _wl.SHAPE_DECISION
SHAPE_IO                 = _wl.SHAPE_IO

# ── Load FlowCode module ──────────────────────────────────────────────────────
_fc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        '..', 'FlowCode', 'flowcode.py')
_fc_spec = _ilu.spec_from_file_location('flowcode', _fc_path)
_fc      = _ilu.module_from_spec(_fc_spec)
_fc_spec.loader.exec_module(_fc)

FCCanvas         = _fc.FCCanvas
FCSymbol         = _fc.FCSymbol
FCEdge           = _fc.FCEdge
SYMBOL_PROCESS   = _fc.SYMBOL_PROCESS
SYMBOL_DECISION  = _fc.SYMBOL_DECISION
SYMBOL_IO        = _fc.SYMBOL_IO
SYMBOL_TERMINATOR = _fc.SYMBOL_TERMINATOR
# FC pixel layout constants
_SYMBOL_W = _fc.SYMBOL_W   # 120 px
_SYMBOL_H = _fc.SYMBOL_H   # 60  px


# ═══════════════════════════════════════════════════════════════════════════════
# Public constants
# ═══════════════════════════════════════════════════════════════════════════════

FC_GRID_TO_MECCANO: int = 10
"""Pixel-to-Meccano-unit divisor.

At 10: a 120×60 px FC symbol → 12×6 Meccano units.
Five such symbols fit horizontally in a default 60-unit-wide ASCII canvas.
Change this constant to rescale all bridge output uniformly — no other code
needs to change. The value is deliberately not inferred from GRID (=40px)
so that the mapping can be tuned independently of FC's internal grid size.
"""

FLOWCODE_SHAPE_MAP: dict = {
    SYMBOL_PROCESS:    SHAPE_PROCESS,
    SYMBOL_DECISION:   SHAPE_DECISION,
    SYMBOL_IO:         SHAPE_IO,
    SYMBOL_TERMINATOR: SHAPE_TERMINATOR,
}
"""Maps FlowCode symbol kinds to widget_lib SHAPE_* IDs.

Only the 4 currently-defined FC symbol kinds are listed.
If FlowCode introduces a new kind, add one entry here and a SHAPE_*
constant in widget_lib.py. The bridge function does not need to change.
Unmapped kinds fall back to SHAPE_RECTANGLE.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# Bridge function
# ═══════════════════════════════════════════════════════════════════════════════

def flowcode_to_meccano(canvas: FCCanvas,
                        name: str = 'flowcode_program',
                        category: str = 'pigart') -> MeccanoProgram:
    """Translate a FlowCode FCCanvas to a TernOO MeccanoProgram.

    Each FCSymbol becomes an RNODE (FORM_SHAPE) with its label.
    Each FCEdge becomes a lean REDGE (no condition) or labeled REDGE
    (when edge.condition is non-empty).

    Symbol layout:
      FCSymbol.x / .y are pixel centres. Top-left in Meccano units:
        tl_x = (sym.x - _SYMBOL_W//2) // FC_GRID_TO_MECCANO
        tl_y = (sym.y - _SYMBOL_H//2) // FC_GRID_TO_MECCANO
      Symbol size: (_SYMBOL_W // FC_GRID_TO_MECCANO, _SYMBOL_H // FC_GRID_TO_MECCANO)

    Edge endpoints:
      src → south midpoint of source symbol (bottom-centre)
      dst → north midpoint of dest symbol   (top-centre)
    Waypoints are ignored in v0.7 (direct src→dst line).

    Args:
        canvas:   FCCanvas with .symbols (Dict[int, FCSymbol]) and
                  .edges (List[FCEdge]).
        name:     Name for the returned MeccanoProgram (default: 'flowcode_program').
        category: MeccanoProgram category (default: 'pigart').

    Returns:
        MeccanoProgram containing one RNODE per symbol and one REDGE per edge,
        followed by a RENDER opcode.
    """
    sym_w_m = _SYMBOL_W // FC_GRID_TO_MECCANO   # symbol width  in Meccano units
    sym_h_m = _SYMBOL_H // FC_GRID_TO_MECCANO   # symbol height in Meccano units

    words: list[int] = []

    # Bounding box lookup: symbol_id → (tl_x, tl_y, w, h)
    sym_boxes: dict[int, tuple[int, int, int, int]] = {}

    # ── Emit one RNODE per symbol ─────────────────────────────────────────────
    for sid, sym in canvas.symbols.items():
        tl_x = (sym.x - _SYMBOL_W // 2) // FC_GRID_TO_MECCANO
        tl_y = (sym.y - _SYMBOL_H // 2) // FC_GRID_TO_MECCANO
        shape_id = FLOWCODE_SHAPE_MAP.get(sym.kind, SHAPE_RECTANGLE)
        words.extend(
            build_rnode_shape_labeled((tl_x, tl_y), (sym_w_m, sym_h_m),
                                      shape_id, sym.label)
        )
        sym_boxes[sid] = (tl_x, tl_y, sym_w_m, sym_h_m)

    # ── Emit one REDGE per edge ───────────────────────────────────────────────
    for edge in canvas.edges:
        if edge.src_id not in sym_boxes or edge.dst_id not in sym_boxes:
            continue  # skip orphaned edges
        sx, sy, sw, sh = sym_boxes[edge.src_id]
        dx, dy, dw, dh = sym_boxes[edge.dst_id]
        # Connect source south-midpoint → destination north-midpoint
        src_pt = (sx + sw // 2, sy + sh)   # bottom-centre of source
        dst_pt = (dx + dw // 2, dy)         # top-centre of destination
        if edge.condition:
            words.extend(
                build_redge_labeled(src_pt, dst_pt, SHAPE_RECTANGLE, edge.condition)
            )
        else:
            words.extend(
                build_redge_styled(src_pt, dst_pt, SHAPE_RECTANGLE)
            )

    # ── Final RENDER opcode ───────────────────────────────────────────────────
    words.append(build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER))

    return MeccanoProgram(
        name=name,
        opcode_words=words,
        category=category,
        description=(
            f'FlowCode bridge: {len(canvas.symbols)} symbol(s), '
            f'{len(canvas.edges)} edge(s)'
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# __main__ — demo
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if '--demo' in sys.argv:
        # Construct a sample FlowCode graph programmatically.
        cv = FCCanvas()
        start  = cv.add_symbol(SYMBOL_TERMINATOR, 120,  40, 'Start')
        decide = cv.add_symbol(SYMBOL_DECISION,   120, 160, 'OK?')
        proc   = cv.add_symbol(SYMBOL_PROCESS,    280, 280, 'Retry')
        end    = cv.add_symbol(SYMBOL_TERMINATOR, 120, 400, 'End')

        cv.add_edge(start.id,  decide.id)
        cv.add_edge(decide.id, end.id,  condition='yes')
        cv.add_edge(decide.id, proc.id, condition='no')
        cv.add_edge(proc.id,   decide.id)

        prog = flowcode_to_meccano(cv, name='bridge_demo')

        print(f"FlowCode bridge demo — {prog.description}")
        print(f"MeccanoProgram: {repr(prog)}")
        print(f"Body words: {len(prog.words)}")
        print(f"Bounds: {prog.bounds()}")
        print()
        print("── ASCII render (80×30) ──")
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from pigart_ascii_renderer import render as _render
        print(_render(prog, width=80, height=30))

        if '--gui' in sys.argv:
            from pigart_tkinter_renderer import render_gui as _render_gui
            _render_gui(prog)

        sys.exit(0)

    print("Usage: flowcode_bridge.py --demo [--gui]")
    sys.exit(2)
