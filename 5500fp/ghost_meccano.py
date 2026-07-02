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
build_model_kind                  = _wl.build_model_kind
build_model_name                  = _wl.build_model_name
build_model_cell                  = _wl.build_model_cell
build_model_cmd                   = _wl.build_model_cmd
build_model_scope                 = _wl.build_model_scope
build_model_port                  = _wl.build_model_port
build_model_edge                  = _wl.build_model_edge
build_model_flag                  = _wl.build_model_flag
build_model_note                  = _wl.build_model_note
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
        # Grammar extension v1 (3 Jul 2026): the stream carries the model —
        # kind and name ride as OPF_MODEL words inside the widget's span.
        words.extend(build_model_kind(w.get('kind', '')))
        if w.get('name'):
            words.extend(build_model_name(w['name']))
        # v2: containment by parent NAME (rehydrated ids are names)
        _pid = w.get('parent_id')
        if _pid is not None and _pid in widgets:
            _pname = widgets[_pid].get('name') or str(_pid)
            words.extend(build_model_scope(_pname))
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
        words.extend(build_model_kind(sym.get('kind', '')))
        if sym.get('name'):
            words.extend(build_model_name(sym['name']))
        if sym.get('parent_scope'):
            words.extend(build_model_scope(sym['parent_scope']))
        _is_entry = sym.get('is_entry') or any(
            p.get('name') == 'is_entry' and p.get('value')
            for p in (sym.get('properties') or []))
        if _is_entry:
            words.extend(build_model_flag('is_entry', 1))
        for _p in (sym.get('entry_points') or []):
            words.extend(build_model_port(_wl.MPORT_ENTRY, _p.get('name',''),
                                          _p.get('type','number'),
                                          _p.get('expr',''),
                                          _p.get('description','')))
        for _p in (sym.get('exit_points') or []):
            words.extend(build_model_port(_wl.MPORT_EXIT, _p.get('name',''),
                                          _p.get('type','number'),
                                          _p.get('expr',''),
                                          _p.get('description','')))
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


# ═══════════════════════════════════════════════════════════════════════════════
# Words → dicts decoder (3 July 2026 — verified-projection closure)
# ═══════════════════════════════════════════════════════════════════════════════
#
# WHAT THE WORDS ENCODE (the projection's honest capability map):
#   per RNODE : geometry (Meccano-unit quantized: pixels // FC_GRID_TO_MECCANO),
#               label text, shape_id, layout_id (FORM_SHAPE_LAYOUT only)
#   per REDGE : endpoint coordinates (Meccano units) [, style, label]
#   plus, since grammar extension v1 (OPF_MODEL, 3 Jul 2026):
#   per node  : kind (MKIND), name (MNAME)
#   free-form : Sheet cells (MCELL: number/text/formula),
#               Shell command widgets + params (MCMDW/MPARM)
# STILL DICT-ONLY (v2 scope: MPORT/MSCOPE + typed-edge annotation):
#   signal bindings, pockets/parent_scope, entry/exit ports, pipe types.

_FORM_LEAN          = _wl.FORM_LEAN
_FORM_SHAPE         = _wl.FORM_SHAPE
_get_field          = _wl.get_field
_decode_map_word    = _wl.decode_map_word
_iterate            = _wl.iterate_instructions


def _xy_from_map(map_word: int) -> tuple:
    d = _decode_map_word(map_word)
    c = d.get('coords', {})
    return int(c.get('X', 0)), int(c.get('Y', 0))


def _label_from_words(string_operands) -> str:
    try:
        return _wl.decode_label_words(list(string_operands))
    except Exception:
        return ''


def meccano_to_ghost(words) -> tuple:
    """Invert ghost_to_meccano / flow_symbols_to_meccano over the surface the
    word grammar encodes.  Returns (nodes, edges):

      nodes — list of dicts: {'x','y','w','h' (Meccano units), 'label',
               'shape_id' (or None for FORM_LEAN), 'layout_id' (or None)}
      edges — list of dicts: {'x1','y1','x2','y2'}

    This is intentionally shape-level, not kind-level: the words do not carry
    widget kind or name (see capability map above), so a faithful decoder
    must not invent them.  test_word_roundtrip.py pins this contract.
    """
    nodes, edges, cells, cmds, iedges, notes = [], [], {}, [], [], []
    pending = [None]   # deferred MPORT/MEDGE packed-string accumulator

    def _finalize_pending():
        if not pending[0]:
            return
        tag, node, dirn, chunks = pending[0]
        packed = ''.join(chunks)
        if tag == 'port':
            f = packed.split(_wl.MODEL_SEP)
            f += [''] * (4 - len(f))
            port = {'name': f[0], 'type': f[1] or 'number',
                    'description': f[3]}
            if f[2]:
                port['expr'] = f[2]
            key = ('entry_points' if dirn == _wl.MPORT_ENTRY
                   else 'exit_points')
            node.setdefault(key, []).append(port)
        elif tag == 'edge':
            f = packed.split(_wl.MODEL_SEP)
            if f and f[0] == 'flow' and len(f) >= 3:
                iedges.append({'kind': 'flow', 'src': f[1], 'dst': f[2]})
            elif f and f[0] == 'pipe' and len(f) >= 3:
                iedges.append({'kind': 'pipe', 'src': f[1], 'dst': f[2],
                               'dst_param': f[3] if len(f) > 3 else ''})
        pending[0] = None
    _last_model = None   # ('node', node_dict) | ('cell', key) | ('cmd', cmd)
    def _sjoin(dst_get, dst_set, ops):
        dst_set(dst_get() + _label_from_words(ops))
    for dec, form, ops in _iterate(list(words)):
        mn = dec.get('mnemonic')
        if mn == 'MKIND' and nodes:
            _finalize_pending()
            nodes[-1]['kind'] = _label_from_words(ops)
            _last_model = ('nkind', nodes[-1]); continue
        if mn == 'MNAME':
            _finalize_pending()
            if _last_model and _last_model[0] in ('cmd', 'parm', 'cmdname'):
                _c = (_last_model[1][0] if _last_model[0] == 'parm'
                      else _last_model[1])
                _c['name'] = _label_from_words(ops)
                _last_model = ('cmdname', _c); continue
            if nodes:
                nodes[-1]['name'] = _label_from_words(ops)
                _last_model = ('nname', nodes[-1]); continue
            continue
        if mn == 'MSCOPE' and nodes:
            _finalize_pending()
            nodes[-1]['parent_scope'] = _label_from_words(ops)
            _last_model = ('nscope', nodes[-1]); continue
        if mn == 'MPORT' and nodes and len(ops) >= 1:
            _finalize_pending()
            _dir = int(_get_field(ops[0], 12, 6))
            pending[0] = ('port', nodes[-1], _dir,
                          [_label_from_words(ops[1:])])
            _last_model = ('pend', None); continue
        if mn == 'MEDGE':
            _finalize_pending()
            pending[0] = ('edge', None, None, [_label_from_words(ops)])
            _last_model = ('pend', None); continue
        if mn == 'MNOTE':
            _finalize_pending()
            notes.append({'index': len(nodes) + len(cmds),
                          'text': _label_from_words(ops)})
            _last_model = ('note', notes[-1]); continue
        if mn == 'MFLAG' and nodes:
            _finalize_pending()
            kv = _label_from_words(ops)
            k, _, vv = kv.partition('=')
            try:
                vv = int(vv)
            except ValueError:
                pass
            nodes[-1][k] = vv
            _last_model = None; continue
        if mn == 'MCELL' and len(ops) >= 2:
            _finalize_pending()
            col, row = _xy_from_map(ops[0])
            ck = int(_get_field(ops[1], 12, 6))   # DATA-SYMBOL id lives T17-T12
            if ck == _wl.MCELL_NUMBER and len(ops) >= 3:
                d = _wl.decode_word(ops[2])
                cells[(row, col)] = {'kind': 'cell_number',
                                     'value': int(d.get('value', 0))}
                _last_model = None
            else:
                kind = 'cell_formula' if ck == _wl.MCELL_FORMULA else 'cell_text'
                cells[(row, col)] = {'kind': kind,
                                     'value': _label_from_words(ops[2:])}
                _last_model = ('cell', (row, col))
            continue
        if mn == 'MCMDW' and len(ops) >= 1:
            _finalize_pending()
            x, y = _xy_from_map(ops[0])
            cmds.append({'x': x, 'y': y,
                         'kind': _label_from_words(ops[1:]), 'params': {}})
            _last_model = ('cmd', cmds[-1]); continue
        if mn == 'MPARM' and cmds:
            _finalize_pending()
            kv = _label_from_words(ops)
            k, _, v = kv.partition('=')
            cmds[-1]['params'][k] = v
            _last_model = ('parm', (cmds[-1], k)); continue
        if mn == 'MMORE' and _last_model is not None:
            tag, ref = _last_model
            if tag == 'pend' and pending[0]:
                pending[0][3].append(_label_from_words(ops))
                continue
            extra = _label_from_words(ops)
            if tag == 'nkind':   ref['kind'] += extra
            elif tag == 'nname': ref['name'] += extra
            elif tag == 'cell':  cells[ref]['value'] += extra
            elif tag == 'note':  ref['text'] += extra
            elif tag == 'cmd':   ref['kind'] += extra
            elif tag == 'parm':
                c, k = ref
                c['params'][k] += extra
            continue
        if mn == 'RNODE' and len(ops) >= 2:
            _finalize_pending()
            x, y = _xy_from_map(ops[0])
            w = int(_get_field(ops[1], 6, 6))
            h = int(_get_field(ops[1], 0, 6))
            lay = _wl.decode_rnode_layout(form, list(ops))
            shape_id  = lay.get('shape_id')
            layout_id = lay.get('layout_id')
            label_ops = ops[(3 if shape_id is not None else 2):]
            if lay.get('has_layout') and label_ops:
                label_ops = label_ops[:-1]
            if lay.get('udp_word') is not None and label_ops:
                label_ops = label_ops[:-1]
            nodes.append({'x': x, 'y': y, 'w': w, 'h': h,
                          'label': _label_from_words(label_ops),
                          'shape_id': shape_id, 'layout_id': layout_id})
        elif mn == 'REDGE' and len(ops) >= 2:
            x1, y1 = _xy_from_map(ops[0])
            x2, y2 = _xy_from_map(ops[1])
            edges.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
    _finalize_pending()
    meccano_to_ghost._cells = cells
    meccano_to_ghost._cmds = cmds
    meccano_to_ghost._iedges = iedges
    meccano_to_ghost._notes = notes
    return nodes, edges


def meccano_to_model(words) -> dict:
    """Full rehydration: nodes (with kind/name where MODEL words present),
    edges, cells, command widgets.  meccano_to_ghost remains the 2-tuple
    compatibility wrapper over the same walk."""
    nodes, edges = meccano_to_ghost(words)
    return {'nodes': nodes, 'edges': edges,
            'cells': meccano_to_ghost._cells,
            'cmds':  meccano_to_ghost._cmds,
            'identity_edges': meccano_to_ghost._iedges,
            'notes': meccano_to_ghost._notes}


def cells_to_model_words(cell_meta: dict) -> list:
    """fc_state['cells'] → MCELL words.  cell_meta keys are (row, col);
    values carry {'kind': 'cell_number'|'cell_text'|'cell_formula',
    'value': ...}."""
    from widget_lib import MCELL_NUMBER, MCELL_TEXT, MCELL_FORMULA  # noqa
    kmap = {'cell_number': _wl.MCELL_NUMBER, 'cell_text': _wl.MCELL_TEXT,
            'cell_formula': _wl.MCELL_FORMULA}
    words = []
    for (r, c), cell in sorted(cell_meta.items()):
        ck = kmap.get(cell.get('kind'), _wl.MCELL_TEXT)
        words += build_model_cell(r, c, ck, cell.get('value', ''))
    return words


def cmds_to_model_words(cmd_meta: dict) -> list:
    """fc_state['cmd_widgets'] → MCMDW [+MNAME identity] /MPARM words."""
    words = []
    for cid, cmd in sorted(cmd_meta.items()):
        _p = {p.get('name'): p.get('value')
              for p in (cmd.get('properties') or [])}
        _p.update(cmd.get('params') or {})       # legacy fallback
        words += build_model_cmd(int(cmd.get('x', 0)), int(cmd.get('y', 0)),
                                 cmd.get('kind', ''), _p)
        ident = cmd.get('name') or str(cid)
        words += build_model_name(ident)
    return words


def _name_of(meta: dict, ref):
    ent = meta.get(ref)
    return (ent.get('name') if ent else None) or str(ref)


def edges_to_model_words(flow_edges: list = None, flow_symbols: dict = None,
                         cmd_edges: list = None, cmd_meta: dict = None) -> list:
    """Identity edges (v2).  flow edges → 'flow' MEDGE (src/dst names);
    pipe edges → 'pipe' MEDGE (src/dst cmd names + dst_param)."""
    words = []
    for e in (flow_edges or []):
        words += build_model_edge('flow',
                                  _name_of(flow_symbols or {}, e.get('src')),
                                  _name_of(flow_symbols or {}, e.get('dst')))
    for e in (cmd_edges or []):
        words += build_model_edge('pipe',
                                  _name_of(cmd_meta or {}, e.get('src')),
                                  _name_of(cmd_meta or {}, e.get('dst')),
                                  str(e.get('dst_param') or ''))
    return words


# ═══════════════════════════════════════════════════════════════════════════════
# Grammar v2 closure — words → WordStream (compile-from-words)
# ═══════════════════════════════════════════════════════════════════════════════

def rehydrate_wordstream(words):
    """Reconstruct a compile-ready WordStream from a v2 word stream.

    Rehydrated entity ids are their NAMES (unique per the Phase 7c-1
    namespace); geometry returns from Meccano units to pixels
    (× FC_GRID_TO_MECCANO, centre-anchored — the bridges' inverse).
    Signal bindings are NOT decoded from words: they are re-materialized
    from names via flowcode_signals.materialize_auto_wired_bindings, the
    same path the IDE uses.  Ports/pockets/pipes come from MPORT/MSCOPE/
    MEDGE words.
    """
    import os as _os, importlib.util as _u
    _here = _os.path.dirname(_os.path.abspath(__file__))
    def _load(n):
        s = _u.spec_from_file_location(n, _os.path.join(_here, n + '.py'))
        m = _u.module_from_spec(s); s.loader.exec_module(m); return m
    ws_mod = _load('word_stream')
    m = meccano_to_model(list(words))

    stream = ws_mod.WordStream(list(words))
    widgets, flows = {}, {}
    name_to_id = {}
    _GEOM = ('x', 'y', 'w', 'h', 'label', 'shape_id', 'layout_id',
             'kind', 'name', 'parent_scope', 'entry_points', 'exit_points')
    for i, n in enumerate(m['nodes']):
        kind = n.get('kind', '')
        ident = i + 1                       # compiler requires integer ids
        if n.get('name'):
            name_to_id[n['name']] = ident
        px = (n['x'] + n['w'] // 2) * FC_GRID_TO_MECCANO
        py = (n['y'] + n['h'] // 2) * FC_GRID_TO_MECCANO
        ent = {'id': ident, 'kind': kind, 'label': n.get('label', ''),
               'name': n.get('name', ''),
               'x': px, 'y': py,
               'w': n['w'] * FC_GRID_TO_MECCANO,
               'h': n['h'] * FC_GRID_TO_MECCANO,
               'properties': [], 'signal_ids': {}}
        for k, v in n.items():              # MFLAG attrs (is_entry, …)
            if k not in _GEOM and k not in ent:
                ent[k] = v
        if ent.pop('is_entry', None):       # compiler reads it from properties
            ent['properties'] = [{'name': 'is_entry', 'value': True}]
        if kind.startswith('flow_'):
            if n.get('parent_scope'):
                ent['parent_scope'] = n['parent_scope']   # scope by NAME
            for k in ('entry_points', 'exit_points'):
                if n.get(k):
                    ent[k] = n[k]
            ent.pop('signal_ids')
            flows[ident] = ent
        else:
            _lay = {v: k for k, v in LAYOUT_MODE_MAP.items()}.get(
                n.get('layout_id'))
            if _lay:
                ent['layout_mode'] = _lay
            ent['_parent_name'] = n.get('parent_scope')   # resolve below
            widgets[ident] = ent
    for w in widgets.values():
        pn = w.pop('_parent_name', None)
        w['parent_id'] = name_to_id.get(pn) if pn else None
    cmds = {}
    try:
        _reg = _load('flowcode_commands').COMMAND_REGISTRY
    except Exception:
        _reg = {}
    cmd_name_to_id = {}
    for i, c in enumerate(m['cmds']):
        ident = 1000 + i                    # integer ids, distinct range
        if c.get('name'):
            cmd_name_to_id[c['name']] = ident
        params = dict(c['params'])
        # Typed rehydration: MPARM values are strings; coerce per the
        # command signature registry (the same source .fc-JSON loads use).
        spec = _reg.get(c['kind'])
        if spec:
            for p in spec.get('params', []):
                nm, ty = p.get('name'), p.get('type')
                if nm in params and ty == 'number':
                    try:
                        params[nm] = int(params[nm])
                    except (TypeError, ValueError):
                        try:
                            params[nm] = float(params[nm])
                        except (TypeError, ValueError):
                            pass
        cmds[ident] = {'id': ident, 'kind': c['kind'], 'x': c['x'],
                       'y': c['y'], 'w': 160, 'h': 80, 'label': '',
                       'name': c.get('name', ''),
                       'properties': [{'name': k, 'value': v}
                                      for k, v in params.items()]}
    stream._widget_meta = widgets
    stream._flow_meta = flows
    stream._cell_meta = dict(m['cells'])
    stream._cmd_meta = cmds
    stream._cmd_edges = [
        {'src': cmd_name_to_id.get(e['src'], e['src']),
         'dst': cmd_name_to_id.get(e['dst'], e['dst']),
         'dst_param': e.get('dst_param')}
        for e in m['identity_edges'] if e['kind'] == 'pipe']
    stream._flow_edges = [
        {'src': e['src'], 'dst': e['dst']}
        for e in m['identity_edges'] if e['kind'] == 'flow']
    try:
        _sig = _load('flowcode_signals')
        _sig.materialize_auto_wired_bindings(stream)
    except Exception:
        pass  # streams with no GUI/flow pairs have nothing to wire
    return stream


def compile_from_words(words, **kw):
    """THE closure: t5asm directly from the word stream.
    compile_from_words(w) == compile_wordstream_to_t5asm(rehydrate(w))."""
    import os as _os, importlib.util as _u
    _here = _os.path.dirname(_os.path.abspath(__file__))
    s = _u.spec_from_file_location(
        'compile_to_t5asm', _os.path.join(_here, 'compile_to_t5asm.py'))
    C = _u.module_from_spec(s); s.loader.exec_module(C)
    return C.compile_wordstream_to_t5asm(rehydrate_wordstream(words), **kw)
