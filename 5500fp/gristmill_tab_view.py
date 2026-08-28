"""gristmill_tab_view.py — GristMill tab for FlowCode (Bundle 13).

Read-only OTree/vocabulary browser.  Third tab after Flow and GUI.

Left pane:  Treeview with two root sections:
              Vocabulary  — static Meccano registries (opcodes, shapes, styles, layouts, signals)
              Program     — current stream's widgets/flow symbols hierarchy + handler bindings
Right pane: scrollable plain-text details panel for the selected node.

Pure functions (no tkinter, safe to import in headless tests):
    build_vocabulary_data()     → list of typed section dicts
    build_program_data(fc)      → nested dict ready to walk
    render_detail(data, fc)     → str for the details Text widget

Tkinter class (requires display):
    GristMillTabView            → full UI; call on_stream_change() to trigger rebuild

Date: 2026-06-19, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations
import os
import sys
import importlib.util as _ilu

# ── Load widget_lib via importlib (avoids circular import when loaded by flowcode.py) ─
_wl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widget_lib.py')
_wl_spec = _ilu.spec_from_file_location('widget_lib', _wl_path)
_wl      = _ilu.module_from_spec(_wl_spec)
_wl_spec.loader.exec_module(_wl)

# ── Pull SIGNAL_REGISTRY from flowcode_signals ────────────────────────────────
_fs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flowcode_signals.py')
try:
    _fs_spec = _ilu.spec_from_file_location('flowcode_signals', _fs_path)
    _fs      = _ilu.module_from_spec(_fs_spec)
    _fs_spec.loader.exec_module(_fs)
    SIGNAL_REGISTRY = _fs.SIGNAL_REGISTRY
except Exception:
    SIGNAL_REGISTRY = {}

# ─────────────────────────────────────────────────────────────────────────────
# Registry tables (sourced from widget_lib constants)
# ─────────────────────────────────────────────────────────────────────────────

SHAPE_NAMES: dict = {
    _wl.SHAPE_RECTANGLE:  'SHAPE_RECTANGLE',
    _wl.SHAPE_TERMINATOR: 'SHAPE_TERMINATOR',
    _wl.SHAPE_PROCESS:    'SHAPE_PROCESS',
    _wl.SHAPE_DECISION:   'SHAPE_DECISION',
    _wl.SHAPE_IO:         'SHAPE_IO',
    _wl.SHAPE_SUBROUTINE: 'SHAPE_SUBROUTINE',
    _wl.SHAPE_CONNECTOR:  'SHAPE_CONNECTOR',
    _wl.SHAPE_OFFPAGE:    'SHAPE_OFFPAGE',
    _wl.SHAPE_DOCUMENT:   'SHAPE_DOCUMENT',
    _wl.SHAPE_DATA:       'SHAPE_DATA',
    _wl.SHAPE_LABELED_BOX:'SHAPE_LABELED_BOX',
    _wl.SHAPE_WINDOW:     'SHAPE_WINDOW',
    _wl.SHAPE_BUTTON:     'SHAPE_BUTTON',
}

STYLE_NAMES: dict = {
    _wl.STYLE_CONTAIN: 'STYLE_CONTAIN',
    _wl.STYLE_HANDLER: 'STYLE_HANDLER',
}

LAYOUT_NAMES: dict = {
    _wl.LAYOUT_ABSOLUTE: 'LAYOUT_ABSOLUTE',
    _wl.LAYOUT_HBOX:     'LAYOUT_HBOX',
    _wl.LAYOUT_VBOX:     'LAYOUT_VBOX',
    _wl.LAYOUT_GRID:     'LAYOUT_GRID',
    _wl.LAYOUT_STACKED:  'LAYOUT_STACKED',
}

SIGNAL_NAMES: dict = {
    _wl.SIGNAL_CLICKED:           'SIGNAL_CLICKED',
    _wl.SIGNAL_TOGGLED:           'SIGNAL_TOGGLED',
    _wl.SIGNAL_CHANGED:           'SIGNAL_CHANGED',
    _wl.SIGNAL_ACTIVATED:         'SIGNAL_ACTIVATED',
    _wl.SIGNAL_CLOSE_REQUESTED:   'SIGNAL_CLOSE_REQUESTED',
    _wl.SIGNAL_FOCUS_CHANGED:     'SIGNAL_FOCUS_CHANGED',
    _wl.SIGNAL_VALUE_CHANGED:     'SIGNAL_VALUE_CHANGED',
    _wl.SIGNAL_SELECTION_CHANGED: 'SIGNAL_SELECTION_CHANGED',
}

SIGNAL_HUMAN: dict = {
    _wl.SIGNAL_CLICKED:           'clicked',
    _wl.SIGNAL_TOGGLED:           'toggled',
    _wl.SIGNAL_CHANGED:           'changed',
    _wl.SIGNAL_ACTIVATED:         'activated',
    _wl.SIGNAL_CLOSE_REQUESTED:   'close-requested',
    _wl.SIGNAL_FOCUS_CHANGED:     'focus-changed',
    _wl.SIGNAL_VALUE_CHANGED:     'value-changed',
    _wl.SIGNAL_SELECTION_CHANGED: 'selection-changed',
}

# Opcode display (numeric values from widget_lib via 5500fp_ternoo_v03)
OPCODE_NAMES: dict = {
    _wl.OP_RNODE:  'RNODE',
    _wl.OP_REDGE:  'REDGE',
    _wl.OP_RENDER: 'RENDER',
    _wl.OP_RPOINT: 'RPOINT',
    _wl.OP_RLINE:  'RLINE',
}

# Flow kind → shape id (reverse of FLOW_SHAPE_MAP, for display)
_FLOW_KIND_TO_SHAPE: dict = {v: k for k, v in _wl.FLOW_SHAPE_MAP.items()}

# Layout string → id (for detail lookup)
_LAYOUT_STR_TO_ID: dict = {
    'absolute': _wl.LAYOUT_ABSOLUTE,
    'hbox':     _wl.LAYOUT_HBOX,
    'vbox':     _wl.LAYOUT_VBOX,
    'grid':     _wl.LAYOUT_GRID,
    'stacked':  _wl.LAYOUT_STACKED,
}


# =============================================================================
# Pure data functions (no tkinter dependency)
# =============================================================================

def build_vocabulary_data() -> list:
    """Return the static vocabulary registry as a list of section dicts.

    Each section dict:
        {'section': str, 'entries': [{'name': str, 'id': int|None, ...}]}

    Sections: 'Opcodes', 'Shapes', 'Styles', 'Layouts', 'Signals'
    """
    sections = []

    # Opcodes
    opcode_entries = []
    for op_id, op_name in sorted(OPCODE_NAMES.items(), key=lambda kv: kv[1]):
        opcode_entries.append({'type': 'opcode', 'name': op_name, 'id': op_id})
    sections.append({'section': 'Opcodes', 'entries': opcode_entries})

    # Shapes
    shape_entries = []
    for sid in sorted(SHAPE_NAMES):
        shape_entries.append({'type': 'shape', 'name': SHAPE_NAMES[sid], 'id': sid})
    sections.append({'section': 'Shapes', 'entries': shape_entries})

    # Styles
    style_entries = []
    for sid in sorted(STYLE_NAMES):
        style_entries.append({'type': 'style', 'name': STYLE_NAMES[sid], 'id': sid})
    sections.append({'section': 'Styles', 'entries': style_entries})

    # Layouts
    layout_entries = []
    for lid in sorted(LAYOUT_NAMES):
        layout_entries.append({'type': 'layout', 'name': LAYOUT_NAMES[lid], 'id': lid})
    sections.append({'section': 'Layouts', 'entries': layout_entries})

    # Signals
    signal_entries = []
    for sid in sorted(SIGNAL_NAMES):
        human = SIGNAL_HUMAN.get(sid, '')
        # Which widget kinds emit this signal?
        emitters = [kind for kind, entries in SIGNAL_REGISTRY.items()
                    for e in entries if e.get('id') == sid]
        signal_entries.append({
            'type':     'signal',
            'name':     SIGNAL_NAMES[sid],
            'id':       sid,
            'human':    human,
            'emitters': emitters,
        })
    sections.append({'section': 'Signals', 'entries': signal_entries})

    return sections


def build_program_data(fc_state: dict) -> dict:
    """Build the Program tree data from fc_state.  Pure — no tkinter.

    Returns:
        {
          'widget_roots': [wid, ...],          # root widget ids (no parent)
          'widget_children': {wid: [cid,...]}, # containment map
          'widgets': {wid: {...}},              # full widget dicts
          'flow_symbols': {sid: {...}},         # full flow symbol dicts
          'bindings': [                         # handler binding entries
              {'wid': int, 'sig_id': int, 'binfo': dict,
               'sig_name': str, 'src_kind': str, 'src_label': str,
               'dst_label': str}, ...
          ],
          'word_map': {wid: (start, end)},     # from stream._word_map (may be {})
        }
    """
    widgets    = dict(fc_state.get('widgets')     or {})
    flow_syms  = dict(fc_state.get('flow_symbols') or {})
    stream     = fc_state.get('stream')

    # Word spans from stream (GUI widgets only; flow symbols omitted per flag-back)
    word_map: dict = {}
    if stream is not None:
        wm = getattr(stream, '_word_map', None) or {}
        word_map = dict(wm)

    # Build containment hierarchy
    children: dict = {}
    roots: list = []
    for wid, w in widgets.items():
        pid = w.get('parent_id')
        if pid is None:
            roots.append(wid)
        else:
            children.setdefault(pid, []).append(wid)

    # Build bindings list
    bindings = []
    for wid, w in widgets.items():
        sig_ids = w.get('signal_ids') or {}
        kind    = w.get('kind', '?')
        label   = w.get('label', '') or kind
        for sig_id_key, binfo in sig_ids.items():
            if not binfo:
                continue
            sig_id = int(sig_id_key)
            sig_name = SIGNAL_HUMAN.get(sig_id, str(sig_id))
            # Find the destination flow symbol label
            dst_x = binfo.get('dst_x', 0)
            dst_y = binfo.get('dst_y', 0)
            dst_label = '?'
            for sym in flow_syms.values():
                if sym.get('x') == dst_x and sym.get('y') == dst_y:
                    dst_label = sym.get('label', '?')
                    break
            bindings.append({
                'wid':       wid,
                'sig_id':    sig_id,
                'binfo':     binfo,
                'sig_name':  sig_name,
                'src_kind':  kind,
                'src_label': label,
                'dst_label': dst_label,
            })

    return {
        'widget_roots':    sorted(roots),
        'widget_children': children,
        'widgets':         widgets,
        'flow_symbols':    flow_syms,
        'bindings':        bindings,
        'word_map':        word_map,
    }


def render_detail(data: dict, fc_state: dict | None = None) -> str:
    """Render a plain-text details string for a selected tree node.

    Args:
        data:     The node metadata dict stored in GristMillTabView._node_data.
        fc_state: The live fc_state dict; used for containment counts.  May be None.

    Returns:
        A multi-line string for the details Text widget.
    """
    t = data.get('type', '')
    fc = fc_state or {}

    # ── Vocabulary nodes ──────────────────────────────────────────────────────

    if t == 'opcode':
        name = data['name']
        oid  = data['id']
        desc = {
            'RNODE':  'Composite node: widget or flow symbol.',
            'REDGE':  'Directed edge: connection, containment, or handler binding.',
            'RENDER': 'Renderer trigger — last word in a program stream.',
            'RPOINT': 'Single-point geometry node.',
            'RLINE':  'Line geometry node.',
        }.get(name, '')
        forms = (
            "Forms (RNODE immediate T20):\n"
            "  FORM_LEAN (0)          — MAP + DATA\n"
            "  FORM_SHAPE (1)         — MAP + DATA + DATA-SYMBOL(shape)\n"
            "  FORM_SHAPE_UDP (2)     — MAP + DATA + DATA-SYMBOL(shape) + UDP\n"
            "  +FORM_HAS_LAYOUT (|4)  — any form + DATA-SYMBOL(LAYOUT_*)\n"
            "  FORM_HANDLER (-1)      — 4-operand REDGE binding (Bundle 12)"
            if name == 'RNODE' else
            "Forms (REDGE immediate T20):\n"
            "  FORM_LEAN (0)          — src MAP + dst MAP\n"
            "  FORM_SHAPE (1)         — src MAP + dst MAP + DATA-SYMBOL(style)\n"
            "  FORM_HANDLER (-1)      — src MAP + dst MAP + DATA-SYMBOL(signal) + DATA (4 ops, 5 words)"
            if name == 'REDGE' else ''
        )
        return (f"Opcode:  {name}\n"
                f"Value:   {oid}\n"
                f"\n{desc}\n"
                + (f"\n{forms}" if forms else ''))

    if t == 'shape':
        sid  = data['id']
        name = data['name']
        flow_kind = _FLOW_KIND_TO_SHAPE.get(sid, '')
        gui_kind = (
            'gui_window'  if sid == _wl.SHAPE_WINDOW else
            'gui_button'  if sid == _wl.SHAPE_BUTTON else
            'gui_* (LABELED_BOX fallback)' if sid == _wl.SHAPE_LABELED_BOX else ''
        )
        used = flow_kind or gui_kind or '(generic / fallback)'
        return (f"Shape:    {name}\n"
                f"ID:       {sid}\n"
                f"Used by:  {used}\n"
                f"Encoded:  DATA-POINTER-SYMBOL (T17-T12 trits in DATA word)")

    if t == 'style':
        sid  = data['id']
        name = data['name']
        desc = {
            _wl.STYLE_CONTAIN: (
                "Logical containment: parent RNODE → child RNODE.\n"
                "REDGE form: FORM_SHAPE, DATA-SYMBOL=STYLE_CONTAIN.\n"
                "Not rendered visually; used to build Program hierarchy."
            ),
            _wl.STYLE_HANDLER: (
                "Handler binding: src widget → dst flow_terminator.\n"
                "REDGE form: FORM_HANDLER (T20=−1), 4 operands, 5 words.\n"
                "Introduced in Bundle 12 (SIGNAL_* integer-ID encoding)."
            ),
        }.get(sid, '')
        return (f"Style:    {name}\n"
                f"ID:       {sid}\n"
                f"Encoded:  DATA-POINTER-SYMBOL (T17-T12 trits in DATA word)\n"
                + (f"\n{desc}" if desc else ''))

    if t == 'layout':
        lid  = data['id']
        name = data['name']
        desc = {
            _wl.LAYOUT_ABSOLUTE: 'Free positioning — children placed at explicit (x, y).',
            _wl.LAYOUT_HBOX:     'Horizontal box — children laid out left to right.',
            _wl.LAYOUT_VBOX:     'Vertical box — children laid out top to bottom.',
            _wl.LAYOUT_GRID:     'Grid — children in rows and columns.',
            _wl.LAYOUT_STACKED:  'Stacked — children occupy the same space (notebook/tabs).',
        }.get(lid, '')
        return (f"Layout:   {name}\n"
                f"ID:       {lid}\n"
                f"Encoded:  DATA-POINTER-SYMBOL (T17-T12 trits in DATA word)\n"
                f"Used on:  container RNODEs with FORM_HAS_LAYOUT qualifier\n"
                + (f"\n{desc}" if desc else ''))

    if t == 'signal':
        sid      = data['id']
        name     = data['name']
        human    = data.get('human', '')
        emitters = data.get('emitters', [])
        # Collect args from SIGNAL_REGISTRY
        args_lines = ''
        for entries in SIGNAL_REGISTRY.values():
            for e in entries:
                if e.get('id') == sid and e.get('args'):
                    args_lines = f"Args:     {', '.join(e['args'])}\n"
                    break
            if args_lines:
                break
        emit_str = ', '.join(emitters) if emitters else '(none defined)'
        return (f"Signal:   {name}  (\"{human}\")\n"
                f"ID:       {sid}\n"
                f"{args_lines}"
                f"Emitted by: {emit_str}\n"
                f"Encoded:  DATA-POINTER-SYMBOL (T17-T12 trits in DATA word)")

    # ── Program nodes ─────────────────────────────────────────────────────────

    if t == 'widget':
        wid   = data['wid']
        w     = data['w']
        span  = data.get('span')
        kind  = w.get('kind', '?')
        # Properties — multiple sources
        props = []
        if w.get('label'):
            props.append(f"  label: {w['label']!r}")
        for key in ('title', 'placeholder', 'text'):
            val = w.get(key) or w.get('properties_extra', {}).get(key)
            if val:
                props.append(f"  {key}: {val!r}")
        lm = w.get('layout_mode')
        if lm:
            lm_id = _LAYOUT_STR_TO_ID.get(lm)
            lm_str = f"{lm}"
            if lm_id is not None:
                lm_str += f"  ({LAYOUT_NAMES.get(lm_id, str(lm_id))})"
            props.append(f"  layout_mode: {lm_str}")
        for p in (w.get('properties') or []):
            if isinstance(p, dict):
                props.append(f"  {p.get('name','?')}: {p.get('value','')}")
        props_str = '\n'.join(props) + '\n' if props else '  (none)\n'

        # Signals bound on this widget
        sig_ids = w.get('signal_ids') or {}
        sig_str = ', '.join(
            SIGNAL_HUMAN.get(int(k), str(k)) for k in sig_ids
        ) if sig_ids else '(none)'

        # Child count
        widgets_all = fc.get('widgets', {})
        n_children = sum(1 for ww in widgets_all.values() if ww.get('parent_id') == wid)

        span_str = f"stream[{span[0]}..{span[1]}]" if span else 'N/A'
        return (f"Kind:      {kind}\n"
                f"ID:        {wid}\n"
                f"Position:  ({w.get('x', 0)}, {w.get('y', 0)})\n"
                f"Dims:      {w.get('w', 0)} × {w.get('h', 0)}\n"
                f"Properties:\n{props_str}"
                f"Signals:   {sig_str}\n"
                f"Contains:  {n_children} widget(s)\n"
                f"Word span: {span_str}")

    if t == 'flow_symbol':
        sid   = data['sid']
        sym   = data['sym']
        kind  = sym.get('kind', '?')
        label = sym.get('label', '')
        props = []
        for p in (sym.get('properties') or []):
            if isinstance(p, dict):
                props.append(f"  {p.get('name','?')}: {p.get('value','')}")
        props_str = '\n'.join(props) + '\n' if props else '  (none)\n'
        # Count handler bindings pointing here
        tx, ty = sym.get('x', 0), sym.get('y', 0)
        n_bound = sum(
            1
            for w in (fc.get('widgets', {}) or {}).values()
            for binfo in (w.get('signal_ids') or {}).values()
            if binfo and binfo.get('dst_x') == tx and binfo.get('dst_y') == ty
        )
        return (f"Kind:      {kind}\n"
                f"ID:        {sid}\n"
                f"Label:     {label!r}\n"
                f"Position:  ({sym.get('x', 0)}, {sym.get('y', 0)})\n"
                f"Dims:      {sym.get('w', 0)} × {sym.get('h', 0)}\n"
                f"Properties:\n{props_str}"
                f"Handlers:  {n_bound} binding(s) point here")

    if t == 'binding':
        wid       = data['wid']
        sig_id    = data['sig_id']
        sig_name  = data['sig_name']
        src_kind  = data['src_kind']
        src_label = data['src_label']
        dst_label = data['dst_label']
        binfo     = data['binfo']
        sig_full  = SIGNAL_NAMES.get(sig_id, str(sig_id))
        w         = (fc.get('widgets', {}) or {}).get(wid, {})
        return (f"Binding (REDGE FORM_HANDLER / T20=−1)\n"
                f"\n"
                f"Src widget: {src_label} #{wid} ({src_kind})\n"
                f"            at ({w.get('x', 0)}, {w.get('y', 0)})\n"
                f"Signal:     {sig_name} ({sig_full}, id {sig_id})\n"
                f"Dst:        {dst_label} (flow_terminator)\n"
                f"            at ({binfo.get('dst_x', 0)}, {binfo.get('dst_y', 0)})\n"
                f"Encoding:   4-operand REDGE — 5 words (Bundle 12)")

    return str(data)


# =============================================================================
# GristMillTabView — tkinter UI
# =============================================================================

class GristMillTabView:
    """Tkinter GristMill tab: Treeview + details panel.

    Instantiate AFTER the notebook frame exists.  Pass the tk.Frame for the tab,
    the shared fc_state dict, the C colours dict, and the root window widget.

    Subscribe on_stream_change() to the WordStream so the Program section
    refreshes automatically when widgets or flow symbols change in another tab.

    Usage (from flowcode.py):
        gm_tab = tk.Frame(notebook, bg=C['bg'])
        notebook.add(gm_tab, text='  GristMill  ')
        _gristmill_view = GristMillTabView(gm_tab, fc_state, C, root)
        fc_state['stream'].subscribe(_gristmill_view.on_stream_change)
    """

    def __init__(self, frame, fc_state: dict, C: dict, root):
        self._fc   = fc_state
        self._C    = C
        self._root = root

        # iid → typed metadata dict for the details panel
        self._node_data: dict = {}
        # Track the Program section's root iid so we can delete/recreate it
        self._prog_iid = None

        self._tree   = None
        self._detail = None
        self._build_ui(frame)
        self._populate_vocabulary()
        self._rebuild_program()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self, frame):
        try:
            import tkinter as tk
            from tkinter import ttk
        except ImportError:
            return   # headless / test environment

        C = self._C

        paned = tk.PanedWindow(frame, orient='horizontal',
                               bg=C['bg'], sashwidth=4, sashrelief='flat')
        paned.pack(fill='both', expand=True)

        # ── Left: Treeview + vertical scrollbar ───────────────────────────────
        tree_frame = tk.Frame(paned, bg=C['bg'])
        paned.add(tree_frame, minsize=220)

        style = ttk.Style()
        # Rowheight follows the FONT (29-08, same clipping class as the
        # POBOX Mail fix): ttk's fixed default ignores font metrics, so
        # HiDPI/large-font desktops clip every row to a fraction.
        import tkinter.font as _tkf
        _gm_font = _tkf.Font(family='Monospace', size=9)
        style.configure('GM.Treeview',
                        background=C.get('canvas', '#16213e'),
                        foreground=C.get('text',   '#e0e0e0'),
                        fieldbackground=C.get('canvas', '#16213e'),
                        rowheight=_gm_font.metrics('linespace') + 4,
                        font=('Monospace', 9))
        style.configure('GM.Treeview.Heading',
                        background=C.get('palette', '#0d1117'),
                        foreground=C.get('text',    '#e0e0e0'),
                        font=('Monospace', 9, 'bold'))
        style.map('GM.Treeview',
                  background=[('selected', C.get('pal_active', '#0f3460'))],
                  foreground=[('selected', C.get('text',       '#e0e0e0'))])

        self._tree = ttk.Treeview(tree_frame, style='GM.Treeview',
                                   selectmode='browse', show='tree')
        vsb = ttk.Scrollbar(tree_frame, orient='vertical',
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side='right', fill='y')
        self._tree.pack(fill='both', expand=True)
        self._tree.bind('<<TreeviewSelect>>', self._on_select)

        # Tag for section headers (slightly brighter)
        self._tree.tag_configure('section',
                                  font=('Monospace', 9, 'bold'),
                                  foreground=C.get('pal_border', '#4a9eff'))

        # ── Right: details Text + vertical scrollbar ──────────────────────────
        detail_frame = tk.Frame(paned, bg=C['bg'])
        paned.add(detail_frame, minsize=220)

        self._detail = tk.Text(detail_frame,
                               bg=C.get('inspect',    '#0a0f1a'),
                               fg=C.get('inspect_fg', '#7ab4ff'),
                               font=('Monospace', 9),
                               wrap='word',
                               relief='flat',
                               state='disabled',
                               padx=8, pady=8)
        dvsb = ttk.Scrollbar(detail_frame, orient='vertical',
                             command=self._detail.yview)
        self._detail.configure(yscrollcommand=dvsb.set)
        dvsb.pack(side='right', fill='y')
        self._detail.pack(fill='both', expand=True)

    def _add_node(self, parent_iid: str, text: str, data: dict | None = None,
                  tags=()) -> str:
        """Insert one Treeview item; optionally store its data dict."""
        iid = self._tree.insert(parent_iid, 'end', text=text, tags=tags)
        if data is not None:
            self._node_data[iid] = data
        return iid

    def _set_detail(self, text: str):
        """Replace the contents of the details Text widget."""
        if self._detail is None:
            return
        self._detail.config(state='normal')
        self._detail.delete('1.0', 'end')
        self._detail.insert('end', text)
        self._detail.config(state='disabled')

    # ── Vocabulary (static) ───────────────────────────────────────────────────

    def _populate_vocabulary(self):
        """Build the static Vocabulary root node from widget_lib registries."""
        if self._tree is None:
            return

        vocab_iid = self._tree.insert('', 'end', text='Vocabulary',
                                       open=True, tags=('section',))

        for section in build_vocabulary_data():
            sec_name = section['section']
            sec_iid  = self._tree.insert(vocab_iid, 'end', text=sec_name,
                                          open=False, tags=('section',))
            for entry in section['entries']:
                eid = entry['id']
                name = entry['name']
                t    = entry['type']
                if t == 'opcode':
                    disp = name
                else:
                    disp = f'{eid:3d}  {name}'
                self._add_node(sec_iid, disp, data=entry)

    # ── Program (dynamic, rebuilt on each stream change) ──────────────────────

    def _rebuild_program(self):
        """Destroy and recreate the Program subtree from current fc_state."""
        if self._tree is None:
            return

        # Remove previous Program section
        if self._prog_iid and self._tree.exists(self._prog_iid):
            # Purge stale node_data entries
            stale = [k for k in self._node_data if not self._tree.exists(k)]
            for k in stale:
                del self._node_data[k]
            self._tree.delete(self._prog_iid)

        prog_iid = self._tree.insert('', 'end', text='Program',
                                      open=True, tags=('section',))
        self._prog_iid = prog_iid

        pd = build_program_data(self._fc)

        # ── GUI widget tree (containment hierarchy) ───────────────────────────
        widgets   = pd['widgets']
        children  = pd['widget_children']
        word_map  = pd['word_map']

        def _add_widget(parent_iid, wid):
            w     = widgets[wid]
            kind  = w.get('kind', '?')
            label = w.get('label', '')
            disp  = (f'{label}  #{wid}  ({kind})' if label
                     else f'#{wid}  ({kind})')
            span  = word_map.get(wid)
            node_iid = self._add_node(parent_iid, disp, data={
                'type': 'widget', 'wid': wid, 'w': w, 'span': span,
            })
            for cid in sorted(children.get(wid, [])):
                _add_widget(node_iid, cid)

        if widgets:
            for wid in pd['widget_roots']:
                _add_widget(prog_iid, wid)

        # ── Flow symbols (flat — no containment) ─────────────────────────────
        flow_syms = pd['flow_symbols']
        if flow_syms:
            fs_iid = self._tree.insert(prog_iid, 'end',
                                        text='Flow Symbols', tags=('section',))
            for sid, sym in sorted(flow_syms.items()):
                kind  = sym.get('kind', '?')
                label = sym.get('label', '')
                star  = '★' if any(
                    isinstance(p, dict) and p.get('name') == 'is_entry'
                    and p.get('value') for p in (sym.get('properties') or [])
                ) else ''
                disp  = f'{label or kind}  #{sid}{("  " + star) if star else ""}'
                self._add_node(fs_iid, disp, data={
                    'type': 'flow_symbol', 'sid': sid, 'sym': sym,
                })

        # ── Handler bindings ──────────────────────────────────────────────────
        bindings = pd['bindings']
        if bindings:
            bind_iid = self._tree.insert(prog_iid, 'end',
                                          text='Bindings', tags=('section',))
            for b in sorted(bindings, key=lambda x: (x['wid'], x['sig_id'])):
                disp = (f'{b["src_label"]}.{b["sig_name"]} '
                        f'→ {b["dst_label"]}')
                self._add_node(bind_iid, disp, data=dict(b, type='binding'))

    # ── Selection → details ───────────────────────────────────────────────────

    def _on_select(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        iid  = sel[0]
        data = self._node_data.get(iid)
        if data is None:
            self._set_detail('')
            return
        self._set_detail(render_detail(data, self._fc))

    # ── WordStream subscriber callback ────────────────────────────────────────

    def on_stream_change(self):
        """Called by WordStream._notify() on any stream mutation.

        Schedules a Program-section rebuild via root.after_idle so the
        update happens on the main thread, never mid-draw.
        """
        try:
            self._root.after_idle(self._rebuild_program)
        except Exception:
            pass   # root may not yet exist during startup
