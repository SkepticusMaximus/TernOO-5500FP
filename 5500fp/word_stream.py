"""word_stream.py — Canonical TernOO word-stream data structure (Phase 6A/6B).

The WordStream is the single source of truth for a TernOO program.  In
Phase 6A it lived alongside gst['widgets'] in GHOST Canvas and was kept in
lockstep with it.  From Phase 6B onward all editor surfaces read from this
stream directly; gst['widgets'] is an alias for _widget_meta.

Phase 6B additions
------------------
- _widget_meta: dict   — the live widget metadata dict (same object as
  gst['widgets'] after the alias; populated by set_from_program from
  the bridge's ._ghost_word_map companion data or by direct canvas edits).
- _word_map: dict      — widget_id → (start, end) half-open word indices;
  populated by set_from_program from prog._ghost_word_map.
- widget_span(wid)     — fast lookup into _word_map.
- _rebuild_indices()   — now a no-op placeholder preserved for Phase 6C+
  when native index structures (containment, handler_bindings) are added.

Date: 2026-06-16, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations
from typing import Callable, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from word_stream_edit import WordStreamEdit


class WordStream:
    """Canonical representation of a TernOO program as an ordered word list.

    Editor surfaces (GHOST Canvas, FlowCode tab, OTree explorer) read from
    a WordStream and translate user actions into WordStreamEdit mutations that
    are applied here.

    Indices
    -------
    Phase 6A: no indices (placeholder _rebuild_indices).
    Phase 6B: widget_span, containment, opcode_index, handler_bindings.

    Subscribers
    -----------
    Each subscribed view's on-change callback is called after every mutation.
    Callbacks receive no arguments; they should re-derive their display from
    the (now-updated) stream.
    """

    def __init__(self, words: Optional[List[int]] = None):
        self.words: List[int] = list(words) if words else []
        self._mmid_word: Optional[int] = None    # set externally via set_from_program
        self._otree_word: Optional[int] = None   # set externally via set_from_program
        self._subscribers: List[Callable] = []
        # Phase 6B: widget metadata and word-index map
        self._widget_meta: dict = {}   # same object as fc_state['widgets'] (alias Phase 6B)
        self._word_map: dict = {}      # widget_id → (start, end) half-open word indices
        # Phase 6C: flow symbol metadata
        self._flow_meta: dict = {}     # same object as fc_state['flow_symbols'] (alias Phase 6C)
        # Stage 9-0: Shell command-widget metadata
        self._cmd_meta: dict = {}      # same object as fc_state['cmd_widgets'] (alias Stage 9-0)
        # Stage 9-2: typed pipe edges between commands
        self._cmd_edges: list = []     # same object as fc_state['cmd_edges'] (alias Stage 9-2)
        # Stage 8-1: Sheet cell metadata
        self._cell_meta: dict = {}     # same object as fc_state['cells'] (alias Stage 8-1)
        self._rebuild_indices()

    # ── External sync ────────────────────────────────────────────────────────

    def set_from_program(self, prog) -> None:
        """Sync word list and identity coordinates from a MeccanoProgram.

        Called by _gc_sync_stream() in flowcode.py after every widget-dict
        mutation.  prog must have:
            .words             — list[int] body words (no header)
            .mmid.word         — TTree MAP coordinate (structural identity)
            .otree_word        — OTree MAP coordinate (content address)
            ._ghost_word_map   — optional dict: widget_id → (start, end)
                                 (present on programs produced by ghost_to_meccano)

        Phase 6B: also copies ._ghost_word_map into self._word_map so that
        GhostCanvasView can locate per-widget word spans without re-parsing.
        _widget_meta is NOT updated here — it is an alias to gst['widgets'],
        which flowcode.py maintains directly.
        """
        self.words = list(prog.words)
        self._mmid_word = prog.mmid.word
        self._otree_word = prog.otree_word
        # Phase 6B: copy word-index map if the bridge provided one
        ghost_map = getattr(prog, '_ghost_word_map', None)
        if ghost_map is not None:
            self._word_map = dict(ghost_map)
        self._rebuild_indices()
        self._notify()

    # ── Identity coordinates ─────────────────────────────────────────────────

    def mmid(self) -> Optional[int]:
        """Return the TTree MAP (structural identity) word, or None if unset."""
        return self._mmid_word

    def otree(self) -> Optional[int]:
        """Return the OTree MAP (content address) word, or None if unset."""
        return self._otree_word

    # ── Write operations (always via WordStreamEdit) ─────────────────────────

    def apply(self, edit: 'WordStreamEdit') -> None:
        """Apply a WordStreamEdit atomically; rebuild indices; notify subscribers.

        Supported operations
        --------------------
        'replace'  — replace the entire word list with edit.words_after
                     (Phase 6A primary operation; position ignored).
        'insert'   — insert edit.words_after at edit.position.
        'delete'   — remove len(edit.words_before) words starting at edit.position.

        After apply(), mmid() and otree() are stale until set_from_program()
        is called again — in Phase 6A this happens immediately inside
        _gc_sync_stream().  Phase 6B will compute them natively here.
        """
        op = edit.op
        pos = edit.position
        if op == 'replace':
            self.words = list(edit.words_after)
        elif op == 'insert':
            self.words = (self.words[:pos]
                          + list(edit.words_after)
                          + self.words[pos:])
        elif op == 'delete':
            n = len(edit.words_before)
            self.words = self.words[:pos] + self.words[pos + n:]
        else:
            raise ValueError(f"Unknown WordStreamEdit op: {op!r}")
        self._rebuild_indices()
        self._notify()

    # ── Subscription ─────────────────────────────────────────────────────────

    def subscribe(self, listener: Callable) -> None:
        """Register a view callback to be called after every stream mutation."""
        if listener not in self._subscribers:
            self._subscribers.append(listener)

    # ── Widget span lookup (Phase 6B) ────────────────────────────────────────

    def widget_span(self, widget_id) -> Optional[tuple]:
        """Return the half-open word-index span (start, end) for a widget.

        The span covers the OPCODE word and all its operands for the widget's
        RNODE instruction.  Returns None if widget_id is not in _word_map.

        _word_map is populated by set_from_program when the source MeccanoProgram
        carries a ._ghost_word_map attribute (set by ghost_to_meccano).
        """
        return self._word_map.get(widget_id)

    # ── Indices (Phase 6B: placeholder for future native indices) ────────────

    def _rebuild_indices(self) -> None:
        """Rebuild lookup indices after a mutation.

        Phase 6B: _word_map is populated from _ghost_word_map in
        set_from_program rather than derived by walking the stream.
        Native stream-walking indices (containment tree, handler_bindings,
        opcode_index) are deferred to Phase 6C+.
        """
        pass  # Phase 6C+: rebuild containment tree, handler_bindings, etc.

    # ── Internal ─────────────────────────────────────────────────────────────

    def _notify(self) -> None:
        """Call all registered subscriber callbacks."""
        for cb in self._subscribers:
            try:
                cb()
            except Exception:
                pass  # views must not crash the stream

    # ── Bundle 12: Signal binding helpers ────────────────────────────────────

    def handler_for(self, widget_id: int, signal_id: int):
        """Return (otree_addr, signal_name, symbolic_name) for the handler
        bound to (widget_id, signal_id), or None if not bound.

        Reads from the widget metadata (_widget_meta, aliased to
        fc_state['widgets']).  The 'signal_ids' dict maps SIGNAL_* int IDs
        to {'dst_x': int, 'dst_y': int} — the canonical Bundle 12 storage.

        Returns:
          (None, signal_name, symbolic_name)
            — otree_addr is None until Stage 7+ native stream-walking is added;
              signal_name is the human-readable name from flowcode_signals;
              symbolic_name is the dst terminator's current 'label'.
          None — if not bound or widget/terminator not found.
        """
        w = self._widget_meta.get(widget_id)
        if w is None:
            return None
        sig_ids = w.get('signal_ids') or {}
        binfo = sig_ids.get(signal_id)
        if binfo is None:
            return None
        # Look up the symbolic name from the flow terminator
        dst_x = binfo.get('dst_x', 0)
        dst_y = binfo.get('dst_y', 0)
        symbolic_name = ''
        for sym in self._flow_meta.values():
            if (sym.get('x', 0) == dst_x and sym.get('y', 0) == dst_y
                    and sym.get('kind') == 'flow_terminator'):
                symbolic_name = sym.get('label', '')
                break
        # Look up the signal name from the imported helper (lazy import to avoid
        # circular imports — flowcode_signals imports widget_lib, not word_stream)
        try:
            import os as _os
            import importlib.util as _ilu
            _fs_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                     'flowcode_signals.py')
            _fs_spec = _ilu.spec_from_file_location('flowcode_signals', _fs_path)
            _fs      = _ilu.module_from_spec(_fs_spec)
            _fs_spec.loader.exec_module(_fs)
            signal_name = _fs.signal_id_to_name(signal_id) or str(signal_id)
        except Exception:
            signal_name = str(signal_id)
        return (None, signal_name, symbolic_name)

    def flow_entries(self):
        """Yield (sym_id, label, x, y) for every flow_terminator with is_entry=True.

        Results are sorted alphabetically by label.  Reads from
        _flow_meta (aliased to fc_state['flow_symbols']).

        Phase 6D: used by the signal picker to populate the list of
        bindable handler targets.
        """
        if not self._flow_meta:
            return
        entries = []
        for sid, sym in self._flow_meta.items():
            if sym.get('kind') != 'flow_terminator':
                continue
            # Check is_entry property
            is_entry = False
            for p in sym.get('properties', []):
                if p.get('name') == 'is_entry':
                    is_entry = bool(p.get('value', False))
                    break
            if is_entry:
                label = sym.get('label', '')
                entries.append((sid, label, sym.get('x', 0), sym.get('y', 0)))
        entries.sort(key=lambda t: t[1])
        yield from entries

    # ── Phase 7c-1: Widget name (programmatic identity) ──────────────────────

    @staticmethod
    def default_name(entry: dict) -> str:
        """Canonical default name for a widget/flow-symbol dict: <kind>_<id>.

        e.g. {'kind': 'gui_button', 'id': 5} → 'gui_button_5'. Unique by
        construction within a namespace (ids are unique) and across namespaces
        (kind prefixes differ: gui_* vs flow_*).
        """
        return f"{entry.get('kind', 'widget')}_{entry.get('id', 0)}"

    def name_in_use(self, name: str, exclude=None) -> bool:
        """True if a non-empty `name` is already used by another widget or
        flow symbol in this stream.

        Names are a single global namespace spanning _widget_meta, _flow_meta
        and _cmd_meta (Stage 9-0) — two entries anywhere in the same WordStream
        may not share a non-empty name. The empty string is legal and never
        collides ("no programmatic name"), so it always returns False.

        Args:
            name:    the candidate name to test.
            exclude: a widget/symbol dict to skip (compared by identity), so a
                     widget can keep its own name on edit without self-collision.
        """
        if not name:
            return False
        for coll in (self._widget_meta, self._flow_meta, self._cmd_meta,
                     self._cell_meta):
            for entry in coll.values():
                if entry is exclude:
                    continue
                if entry.get('name') == name:
                    return True
        return False

    def ensure_unique_names(self) -> int:
        """Backward-compat + integrity pass over all widgets and flow symbols.

        - Any entry missing the 'name' key (legacy files predating Phase 7c-1)
          is assigned the default <kind>_<id>.
        - An entry whose 'name' is explicitly '' is left empty (empty is legal).
        - Duplicate non-empty names are disambiguated with a numeric suffix,
          keeping the first occurrence in iteration order (widgets, then flow
          symbols, then Shell command widgets).

        Operates in place on _widget_meta / _flow_meta / _cmd_meta (which are
        aliased to the editor's live widget/flow/command dicts). Returns the
        count of names assigned or changed.
        """
        changed = 0
        seen: set = set()
        for coll in (self._widget_meta, self._flow_meta, self._cmd_meta,
                     self._cell_meta):
            for entry in coll.values():
                if 'name' not in entry:
                    entry['name'] = self.default_name(entry)
                    changed += 1
                nm = entry['name']
                if not nm:
                    continue  # empty is legal and not deduped
                if nm in seen:
                    base, n = nm, 1
                    while f"{base}_{n}" in seen:
                        n += 1
                    nm = f"{base}_{n}"
                    entry['name'] = nm
                    changed += 1
                seen.add(nm)
        return changed

    # ── Phase 7b-3: Compiler helpers ─────────────────────────────────────────

    def iter_widgets(self, kind_prefix: str = ''):
        """Yield SimpleNamespace objects for each widget in _widget_meta (insertion order).

        Each namespace exposes: id, kind, x, y, w, h, label, parent_id,
        layout_mode, signal_ids, properties — matching the widget dict schema.

        Args:
            kind_prefix: if given, only yield widgets whose kind starts with
                         this prefix (e.g. 'gui_' for all GUI widgets).

        Yields:
            types.SimpleNamespace with the widget attributes.
        """
        from types import SimpleNamespace
        for wid, w in self._widget_meta.items():
            k = w.get('kind', '')
            if kind_prefix and not k.startswith(kind_prefix):
                continue
            yield SimpleNamespace(
                id          = wid,
                kind        = k,
                name        = w.get('name', ''),
                x           = w.get('x', 0),
                y           = w.get('y', 0),
                w           = w.get('w', 0),
                h           = w.get('h', 0),
                label       = w.get('label', ''),
                parent_id   = w.get('parent_id'),
                layout_mode = w.get('layout_mode', 'absolute'),
                signal_ids  = w.get('signal_ids') or {},
                properties  = w.get('properties') or [],
            )

    def find_terminator_for(self, widget_id: int, signal_id: int):
        """Return the flow_terminator sym dict bound to (widget_id, signal_id), or None.

        Reads the signal_ids binding (dst_x, dst_y) from _widget_meta, then
        scans _flow_meta for a flow_terminator at that canvas position.

        This is the Phase 7b-3 positional lookup: OTree-native resolution is
        deferred to Phase 7b-4 when stream-walking index is added.

        Args:
            widget_id:  int widget identifier (key in _widget_meta).
            signal_id:  int signal identifier (e.g. SIGNAL_CLICKED = 300).

        Returns:
            sym dict from _flow_meta, or None if no binding / no matching terminator.
        """
        w = self._widget_meta.get(widget_id)
        if w is None:
            return None
        sig_ids = w.get('signal_ids') or {}
        # signal_ids keys may be int (in-memory) or str (JSON-round-tripped);
        # try both so lookups survive a save/load cycle.
        binfo = sig_ids.get(signal_id) or sig_ids.get(str(signal_id))
        if binfo is None:
            return None
        dst_x = binfo.get('dst_x', 0)
        dst_y = binfo.get('dst_y', 0)
        for sym in self._flow_meta.values():
            if (sym.get('kind') == 'flow_terminator'
                    and sym.get('x', 0) == dst_x
                    and sym.get('y', 0) == dst_y):
                return sym
        return None

    # ── Helpers ──────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.words)

    def __repr__(self) -> str:
        ot = f'otree={self._otree_word!r}' if self._otree_word is not None else 'otree=?'
        return f'WordStream({len(self.words)} words, {ot})'
