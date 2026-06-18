"""ghost_meccano.py — GHOST canvas + FlowCode dict → MeccanoProgram bridges (Phase 6E).

Extracted from flowcode_bridge.py during Stage 6 closure cleanup.
Contains only the three translation functions that flowcode.py uses to rebuild
the canonical WordStream from the in-memory gst-dict state.

  ghost_to_meccano          — fc_state['widgets'] + edges  → MeccanoProgram
  flow_symbols_to_meccano   — fc_state['flow_symbols'] + edges → MeccanoProgram
  update_meccano_for_widget — incremental single-widget word splice

These functions take plain dicts (no FCCanvas objects), so no import of
flowcode.py is required.  They depend only on widget_lib.

The old flowcode_to_meccano (FCCanvas → MeccanoProgram) is test-only and
is inlined directly in widget_lib.py's test section.

Date: 2026-06-19, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations
import os
import importlib.util as _ilu

# ── Load widget_lib via importlib ─────────────────────────────────────────────
_wl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widget_lib.py')
_wl_spec = _ilu.spec_from_file_location('widget_lib', _wl_path)
_wl      = _ilu.module_from_spec(_wl_spec)
_wl_spec.loader.exec_module(_wl)

MeccanoProgram                    = _wl.MeccanoProgram
build_opcode_word                 = _wl.build_opcode_word
build_rnode_shape_labeled         = _wl.build_rnode_shape_labeled
build_rnode_shape_labeled_layout  = _wl.build_rnode_shape_labeled_layout
build_redge_styled                = _wl.build_redge_styled
build_redge                       = _wl.build_redge
OPF_PIGART                        = _wl.OPF_PIGART
OP_RENDER                         = _wl.OP_RENDER
SHAPE_RECTANGLE                   = _wl.SHAPE_RECTANGLE
STYLE_CONTAIN                     = _wl.STYLE_CONTAIN
FLOW_SHAPE_MAP                    = _wl.FLOW_SHAPE_MAP
LAYOUT_ABSOLUTE = _wl.LAYOUT_ABSOLUTE
LAYOUT_HBOX     = _wl.LAYOUT_HBOX
LAYOUT_VBOX     = _wl.LAYOUT_VBOX
LAYOUT_GRID     = _wl.LAYOUT_GRID
LAYOUT_STACKED  = _wl.LAYOUT_STACKED

# ── Constants ─────────────────────────────────────────────────────────────────

FC_GRID_TO_MECCANO: int = 10
"""Pixel-to-Meccano-unit divisor.

At 10: a 120×60 px FC symbol → 12×6 Meccano units.
"""

_SYMBOL_W = 120   # standard FC symbol width in pixels
_SYMBOL_H = 60    # standard FC symbol height in pixels

LAYOUT_MODE_MAP: dict = {
    'absolute': LAYOUT_ABSOLUTE,
    'hbox':     LAYOUT_HBOX,
    'vbox':     LAYOUT_VBOX,
    'grid':     LAYOUT_GRID,
    'stacked':  LAYOUT_STACKED,
}
"""Maps GHOST canvas layout_mode strings to widget_lib LAYOUT_* constants."""


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
    prog._ghost_word_map = word_map
    return prog


def flow_symbols_to_meccano(flow_symbols: dict, flow_edges: list,
                             name: str = 'flow_program',
                             category: str = 'pigart') -> 'MeccanoProgram':
    """Translate gst['flow_symbols'] + gst['flow_edges'] to a MeccanoProgram.

    Phase 6C canonical bridge.  Unlike the FCCanvas-based flowcode_to_meccano,
    this function takes the gst-dict representation used by the FlowCode tab.

    flow_symbols schema (per symbol):
        {id: {'id': int, 'kind': str, 'x': int, 'y': int,
              'w': int, 'h': int, 'label': str, 'properties': list}}

    flow_edges schema (per edge):
        {'src': int, 'dst': int, 'waypoints': list, 'condition': str}

    Encoding:
      - Each flow symbol → RNODE via FLOW_SHAPE_MAP[kind] (FORM_SHAPE with label).
      - Each flow edge → build_redge (lean FORM_LEAN, arity=2, no style symbol).
      - Scale: pixel coords divided by FC_GRID_TO_MECCANO.
      - Produces a ._flow_word_map attribute: {symbol_id: (start, end)}.
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
