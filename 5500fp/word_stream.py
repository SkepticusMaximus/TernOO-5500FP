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
        self._widget_meta: dict = {}   # same object as gst['widgets'] (alias in Phase 6B)
        self._word_map: dict = {}      # widget_id → (start, end) half-open word indices
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

    # ── Helpers ──────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self.words)

    def __repr__(self) -> str:
        ot = f'otree={self._otree_word!r}' if self._otree_word is not None else 'otree=?'
        return f'WordStream({len(self.words)} words, {ot})'
