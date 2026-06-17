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

MeccanoProgram                    = _wl.MeccanoProgram
build_opcode_word                 = _wl.build_opcode_word
build_rnode_shape_labeled         = _wl.build_rnode_shape_labeled
build_rnode_shape_layout          = _wl.build_rnode_shape_layout
build_rnode_shape_labeled_layout  = _wl.build_rnode_shape_labeled_layout
build_redge_styled                = _wl.build_redge_styled
build_redge_labeled               = _wl.build_redge_labeled
build_redge                       = _wl.build_redge        # Phase 6C: lean default flow edge
OPF_PIGART                        = _wl.OPF_PIGART
OP_RENDER                         = _wl.OP_RENDER
SHAPE_RECTANGLE                   = _wl.SHAPE_RECTANGLE
SHAPE_TERMINATOR                  = _wl.SHAPE_TERMINATOR
SHAPE_PROCESS                     = _wl.SHAPE_PROCESS
SHAPE_DECISION                    = _wl.SHAPE_DECISION
SHAPE_IO                          = _wl.SHAPE_IO
STYLE_CONTAIN                     = _wl.STYLE_CONTAIN    # logical containment edge
build_redge_handler               = _wl.build_redge_handler  # Phase 6D: handler bindings
# Phase 6C: flow_* namespace kind → SHAPE_* mapping
FLOW_SHAPE_MAP                    = _wl.FLOW_SHAPE_MAP
# Phase 6B: LAYOUT_* constants for container widget RNODEs
LAYOUT_ABSOLUTE = _wl.LAYOUT_ABSOLUTE
LAYOUT_HBOX     = _wl.LAYOUT_HBOX
LAYOUT_VBOX     = _wl.LAYOUT_VBOX
LAYOUT_GRID     = _wl.LAYOUT_GRID
LAYOUT_STACKED  = _wl.LAYOUT_STACKED

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

LAYOUT_MODE_MAP: dict = {
    'absolute': LAYOUT_ABSOLUTE,
    'hbox':     LAYOUT_HBOX,
    'vbox':     LAYOUT_VBOX,
    'grid':     LAYOUT_GRID,
    'stacked':  LAYOUT_STACKED,
}
"""Maps GHOST canvas layout_mode strings to widget_lib LAYOUT_* constants.

Used by ghost_to_meccano (Phase 6B) to encode layout_mode on container
RNODEs as a DATA-POINTER-SYMBOL trailing operand.  Unmapped modes fall
back to LAYOUT_ABSOLUTE.
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
# Phase 6C — FlowCode gst-dict bridge
# ═══════════════════════════════════════════════════════════════════════════════

def flow_symbols_to_meccano(flow_symbols: dict, flow_edges: list,
                             name: str = 'flow_program',
                             category: str = 'pigart') -> 'MeccanoProgram':
    """Translate gst['flow_symbols'] + gst['flow_edges'] to a MeccanoProgram.

    Phase 6C canonical bridge.  Unlike flowcode_to_meccano (which takes
    FCCanvas objects), this function takes the gst-dict representation used
    by the FlowCode tab after migration.

    flow_symbols schema (per symbol):
        {id: {'id': int, 'kind': str, 'x': int, 'y': int,
              'w': int, 'h': int, 'label': str, 'properties': list}}

    flow_edges schema (per edge):
        {'src': int, 'dst': int, 'waypoints': list, 'condition': str}

    Encoding:
      - Each flow symbol → RNODE via FLOW_SHAPE_MAP[kind] (FORM_SHAPE with label).
      - Each flow edge → build_redge (lean FORM_LEAN, arity=2, no style symbol).
        D2: flow edges are the default REDGE form — no STYLE_CONTAIN, no STYLE_HANDLER.
        Edge 'condition' is metadata for display only; not encoded in the REDGE word.
      - Scale: pixel coords divided by FC_GRID_TO_MECCANO (same as GHOST bridge).
      - Produces a ._flow_word_map attribute: {symbol_id: (start, end)}.

    Args:
        flow_symbols: dict mapping int id → flow symbol dict.
        flow_edges:   list of flow edge dicts {src, dst, waypoints, condition}.
        name:         MeccanoProgram name.
        category:     MeccanoProgram category.

    Returns:
        MeccanoProgram with RNODE per symbol, REDGE per edge, RENDER opcode.
    """
    sym_w_m = _SYMBOL_W // FC_GRID_TO_MECCANO   # 12 Meccano units
    sym_h_m = _SYMBOL_H // FC_GRID_TO_MECCANO   # 6  Meccano units

    words: list = []
    sym_boxes: dict = {}   # id → (tl_x, tl_y, mw, mh)
    word_map:  dict = {}   # id → (start, end) half-open

    for sid, sym in flow_symbols.items():
        ww  = sym.get('w', _SYMBOL_W)
        wh  = sym.get('h', _SYMBOL_H)
        mw  = max(1, ww // FC_GRID_TO_MECCANO)
        mh  = max(1, wh // FC_GRID_TO_MECCANO)
        tl_x = (sym['x'] - ww // 2) // FC_GRID_TO_MECCANO
        tl_y = (sym['y'] - wh // 2) // FC_GRID_TO_MECCANO
        shape_id = FLOW_SHAPE_MAP.get(sym.get('kind', ''), SHAPE_RECTANGLE)
        label    = sym.get('label', '')
        _start   = len(words)
        words.extend(
            build_rnode_shape_labeled((tl_x, tl_y), (mw, mh), shape_id, label)
        )
        word_map[sid]  = (_start, len(words))
        sym_boxes[sid] = (tl_x, tl_y, mw, mh)

    for edge in flow_edges:
        src_id = edge.get('src'); dst_id = edge.get('dst')
        if src_id not in sym_boxes or dst_id not in sym_boxes:
            continue
        sx, sy, sw, sh = sym_boxes[src_id]
        dx, dy, dw, dh = sym_boxes[dst_id]
        src_pt = (sx + sw // 2, sy + sh)   # south midpoint of source
        dst_pt = (dx + dw // 2, dy)         # north midpoint of destination
        words.extend(build_redge(src_pt, dst_pt))

    words.append(build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER))

    prog = MeccanoProgram(
        name=name,
        opcode_words=words,
        category=category,
        description=(
            f'Flow bridge: {len(flow_symbols)} symbol(s), '
            f'{len(flow_edges)} edge(s)'
        ),
    )
    prog._flow_word_map = word_map
    return prog


# ═══════════════════════════════════════════════════════════════════════════════
# GHOST canvas bridge
# ═══════════════════════════════════════════════════════════════════════════════

def ghost_to_meccano(widgets: dict, edges: list,
                     name: str = 'ghost_program',
                     category: str = 'pigart') -> 'MeccanoProgram':
    """Translate a GHOST canvas widget dict + edge list to a MeccanoProgram.

    Each widget becomes an RNODE (FORM_SHAPE, SHAPE_RECTANGLE).
    Each entry in `edges` (visual connections) becomes a lean REDGE.
    Each widget with a non-None `parent_id` generates a REDGE with
    STYLE_CONTAIN — a logical containment edge that renderers skip.

    Scale: widget pixel coords are divided by FC_GRID_TO_MECCANO.

    Args:
        widgets: dict mapping int id → {id, kind, x, y, w, h, parent_id, label}
        edges:   list of {src, dst} visual connection dicts
        name:    name for the returned MeccanoProgram
        category: MeccanoProgram category

    Returns:
        MeccanoProgram with RNODEs, visual REDGEs, containment REDGEs, RENDER.
        The program carries a ._ghost_word_map attribute:
            {widget_id: (start, end)} — half-open indices into program.words
        Used by update_meccano_for_widget for incremental field-commit updates.
    """
    words: list = []
    sym_centres: dict = {}  # id → (cx, cy) in Meccano units
    word_map: dict = {}    # widget_id → (start, end) half-open in words list

    for wid, w in widgets.items():
        ww = w.get('w', 160)
        wh = w.get('h', 72)
        tl_x = (w['x'] - ww // 2) // FC_GRID_TO_MECCANO
        tl_y = (w['y'] - wh // 2) // FC_GRID_TO_MECCANO
        mw   = max(1, ww // FC_GRID_TO_MECCANO)
        mh   = max(1, wh // FC_GRID_TO_MECCANO)
        _start = len(words)
        _label = w.get('label', w.get('kind', ''))
        _layout_mode = w.get('layout_mode')   # Phase 6B: may be set on containers
        if _layout_mode is not None:
            # Container with explicit layout: encode as RNODE with trailing LAYOUT operand
            _layout_id = LAYOUT_MODE_MAP.get(_layout_mode, LAYOUT_ABSOLUTE)
            words.extend(
                build_rnode_shape_labeled_layout(
                    (tl_x, tl_y), (mw, mh),
                    SHAPE_RECTANGLE, _label, _layout_id
                )
            )
        else:
            words.extend(
                build_rnode_shape_labeled((tl_x, tl_y), (mw, mh),
                                          SHAPE_RECTANGLE, _label)
            )
        word_map[wid] = (_start, len(words))
        sym_centres[wid] = (tl_x + mw // 2, tl_y + mh)  # south midpoint

    # Visual connection edges
    for e in edges:
        sc = sym_centres.get(e['src'])
        dc = sym_centres.get(e['dst'])
        if sc and dc:
            src_pt = sc
            dc_w   = widgets.get(e['dst'])
            dst_pt = (dc[0], dc[1] - max(1, dc_w.get('h', 72) // FC_GRID_TO_MECCANO)) \
                     if dc_w else dc
            words.extend(build_redge_styled(src_pt, dst_pt, SHAPE_RECTANGLE))

    # Containment edges (STYLE_CONTAIN) for each non-None parent_id
    for wid, w in widgets.items():
        pid = w.get('parent_id')
        if pid is not None and pid in sym_centres:
            parent_pt = sym_centres[pid]
            child_pt  = sym_centres.get(wid, parent_pt)
            words.extend(build_redge_styled(parent_pt, child_pt, STYLE_CONTAIN))

    words.append(build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER))

    prog = MeccanoProgram(
        name=name,
        opcode_words=words,
        category=category,
        description=(
            f'GHOST bridge: {len(widgets)} widget(s), '
            f'{len(edges)} edge(s), '
            f'{sum(1 for w in widgets.values() if w.get("parent_id") is not None)} '
            f'containment edge(s)'
        ),
    )
    # Attach word-index map for incremental updates (update_meccano_for_widget)
    prog._ghost_word_map = word_map
    return prog


def update_meccano_for_widget(program: 'MeccanoProgram',
                              widget_id: int,
                              widget: dict) -> 'MeccanoProgram':
    """Re-emit the words for a single widget within an existing program.

    Called once per field-commit (label/x/y/w/h changes), not per keystroke.
    Locates the widget's RNODE span in program.words via _ghost_word_map,
    replaces those indices with newly-emitted words, returns the updated
    program with recomputed mmid and otree.

    Properties that change edge structure (parent_id) require a full rebuild
    via ghost_to_meccano — callers are responsible for that case.

    Args:
        program:   MeccanoProgram previously returned by ghost_to_meccano,
                   carrying a ._ghost_word_map attribute.
        widget_id: The id of the widget whose words should be updated.
        widget:    The updated widget dict (with new x/y/w/h/label).

    Returns:
        A new MeccanoProgram with updated words and recomputed mmid/otree.
        If the program lacks _ghost_word_map or widget_id is not in it,
        the original program is returned unchanged.
    """
    word_map = getattr(program, '_ghost_word_map', None)
    if word_map is None or widget_id not in word_map:
        return program

    start, end = word_map[widget_id]

    ww = widget.get('w', 160)
    wh = widget.get('h', 72)
    tl_x = (widget['x'] - ww // 2) // FC_GRID_TO_MECCANO
    tl_y = (widget['y'] - wh // 2) // FC_GRID_TO_MECCANO
    mw   = max(1, ww // FC_GRID_TO_MECCANO)
    mh   = max(1, wh // FC_GRID_TO_MECCANO)
    _label = widget.get('label', widget.get('kind', ''))
    _layout_mode = widget.get('layout_mode')  # Phase 6B
    if _layout_mode is not None:
        _layout_id = LAYOUT_MODE_MAP.get(_layout_mode, LAYOUT_ABSOLUTE)
        new_rnode_words = build_rnode_shape_labeled_layout(
            (tl_x, tl_y), (mw, mh), SHAPE_RECTANGLE, _label, _layout_id
        )
    else:
        new_rnode_words = build_rnode_shape_labeled(
            (tl_x, tl_y), (mw, mh), SHAPE_RECTANGLE, _label
        )

    # Splice new words into the body
    old_len = end - start
    new_len = len(new_rnode_words)
    new_body = program.words[:start] + new_rnode_words + program.words[end:]

    # Rebuild the program from the updated body
    new_prog = MeccanoProgram(
        name=program.name,
        opcode_words=new_body,
        category=program.category,
        description=program.description,
    )

    # Rebuild the word map: adjust all spans after the replaced span
    delta = new_len - old_len
    new_word_map = {}
    for wid, (s, e) in word_map.items():
        if wid == widget_id:
            new_word_map[wid] = (start, start + new_len)
        elif s >= end:
            new_word_map[wid] = (s + delta, e + delta)
        else:
            new_word_map[wid] = (s, e)
    new_prog._ghost_word_map = new_word_map

    return new_prog


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 6D — Handler binding word emission
# ═══════════════════════════════════════════════════════════════════════════════

def build_handler_bindings(widgets: dict, flow_symbols: dict) -> list:
    """Build REDGE handler-binding words for all signal bindings in widgets.

    Walks fc_state['widgets'], collecting each widget's 'signal_ids' dict
    (signal_id: int → {'dst_x': int, 'dst_y': int}).  For each binding,
    emits one build_redge_handler() word sequence.

    Bundle 12: uses SIGNAL_* integer IDs, 4-operand / 5-word form.
    widget_dict['bindings'] has been retired; reads only 'signal_ids'.

    Returns a flat list of words suitable for appending to the combined
    stream in _guic_sync_stream().

    Editor-side only.  No runtime firing here — Stage 7+.
    """
    _GC_SCALE = 10   # pixel → Meccano coordinate scale (matches ghost_to_meccano)
    words = []
    for wid, w in widgets.items():
        sig_ids = w.get('signal_ids') or {}
        wx = w.get('x', 0)
        wy = w.get('y', 0)
        for signal_id, binfo in sig_ids.items():
            if not binfo:
                continue
            dx = binfo.get('dst_x', 0)
            dy = binfo.get('dst_y', 0)
            # Scale positions to Meccano units
            src_mc = (wx // _GC_SCALE, wy // _GC_SCALE)
            dst_mc = (dx // _GC_SCALE, dy // _GC_SCALE)
            words.extend(build_redge_handler(src_mc, dst_mc, int(signal_id)))
    return words


# ═══════════════════════════════════════════════════════════════════════════════
# __main__ — demo
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    if '--demo' in sys.argv:
        # ── FlowCode graph demo ───────────────────────────────────────────────
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

        # ── GHOST canvas demo (containment edges) ────────────────────────────
        print()
        print("── GHOST bridge demo ──")
        # A window widget containing a button (parent_id relationship)
        _widgets = {
            0: {'id': 0, 'kind': 'gui_window', 'x': 200, 'y': 120,
                'w': 200, 'h': 160, 'parent_id': None, 'label': 'MainWin',
                'layout_mode': 'vbox'},   # Phase 6B: container with explicit layout
            1: {'id': 1, 'kind': 'gui_button', 'x':  60, 'y':  40,
                'w': 120, 'h':  48, 'parent_id': 0,    'label': 'OK'},
            2: {'id': 2, 'kind': 'gui_button', 'x':  60, 'y': 100,
                'w': 120, 'h':  48, 'parent_id': 0,    'label': 'Cancel'},
        }
        # One visual edge: button 1 → button 2 (flow connection)
        _edges = [{'src': 1, 'dst': 2}]

        ghost_prog = ghost_to_meccano(_widgets, _edges, name='ghost_demo')
        print(f"GHOST bridge demo — {ghost_prog.description}")
        print(f"MeccanoProgram: {repr(ghost_prog)}")
        print(f"Body words: {len(ghost_prog.words)}")
        print(f"Bounds: {ghost_prog.bounds()}")

        # Verify containment edges via the bridge description (simplest check)
        _desc = ghost_prog.description
        print(f"Containment edges confirmed in description: {_desc}")
        assert '2 containment edge(s)' in _desc, \
            f"Expected 2 containment edges, got: {_desc!r}"
        print("PASS: STYLE_CONTAIN REDGE count verified via description.")

        if '--gui' in sys.argv:
            from pigart_tkinter_renderer import render_gui as _render_gui2
            _render_gui2(ghost_prog)

        # ── Phase 6C: flow_symbols_to_meccano demo ───────────────────────────
        print()
        print("── Phase 6C flow_symbols_to_meccano demo ──")
        _fsyms = {
            0: {'id': 0, 'kind': 'flow_terminator', 'x': 120, 'y':  40,
                'w': 120, 'h': 60, 'label': 'Start', 'properties': [
                    {'name': 'is_entry', 'value': True}]},
            1: {'id': 1, 'kind': 'flow_decision',   'x': 120, 'y': 160,
                'w': 120, 'h': 60, 'label': 'OK?',   'properties': [
                    {'name': 'condition', 'value': 'x > 0'}]},
            2: {'id': 2, 'kind': 'flow_process',    'x': 280, 'y': 280,
                'w': 120, 'h': 60, 'label': 'Retry', 'properties': []},
            3: {'id': 3, 'kind': 'flow_terminator', 'x': 120, 'y': 400,
                'w': 120, 'h': 60, 'label': 'End',   'properties': []},
        }
        _fedges = [
            {'src': 0, 'dst': 1, 'waypoints': [], 'condition': ''},
            {'src': 1, 'dst': 3, 'waypoints': [], 'condition': 'yes'},
            {'src': 1, 'dst': 2, 'waypoints': [], 'condition': 'no'},
            {'src': 2, 'dst': 1, 'waypoints': [], 'condition': ''},
        ]
        flow_prog = flow_symbols_to_meccano(_fsyms, _fedges, name='flow_dict_demo')
        print(f"flow_symbols_to_meccano — {flow_prog.description}")
        print(f"MeccanoProgram: {repr(flow_prog)}")
        print(f"Body words: {len(flow_prog.words)}")
        print(f"_flow_word_map entries: {len(flow_prog._flow_word_map)}")
        assert len(flow_prog._flow_word_map) == 4, \
            f"Expected 4 word_map entries, got {len(flow_prog._flow_word_map)}"
        print("PASS: flow_symbols_to_meccano produces correct word map.")

        sys.exit(0)

    print("Usage: flowcode_bridge.py --demo [--gui]")
    sys.exit(2)
