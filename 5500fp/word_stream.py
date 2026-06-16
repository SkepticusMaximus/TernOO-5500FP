"""word_stream.py — Canonical TernOO word-stream data structure (Phase 6A).

The WordStream is the single source of truth for a TernOO program.  In
Phase 6A it lives alongside gst['widgets'] in GHOST Canvas and is kept in
lockstep with it — every widget-dict mutation produces a matching update here.
From Phase 6B onward, all editor surfaces read from this stream directly and
gst['widgets'] becomes a derived view.

Phase 6A scope
--------------
- Store the ordered body word list (no header — mmid and otree_word are
  stored separately, populated externally via set_from_program).
- notify subscribers on every mutation (apply / set_from_program).
- Expose mmid() and otree() as simple getters returning the last values
  set by set_from_program (recomputed from the bridge in Phase 6A; computed
  natively from Phase 6B).
- _rebuild_indices() is a no-op placeholder; the real index structures
  (widget_span, containment, handler_bindings) arrive in Phase 6B.

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
        self._rebuild_indices()

    # ── External sync ────────────────────────────────────────────────────────

    def set_from_program(self, prog) -> None:
        """Sync word list and identity coordinates from a MeccanoProgram.

        Called by _gc_sync_stream() in flowcode.py after every widget-dict
        mutation in Phase 6A.  prog must have:
            .words        — list[int] body words (no header)
            .mmid.word    — TTree MAP coordinate (structural identity)
            .otree_word   — OTree MAP coordinate (content address)
        """
        self.words = list(prog.words)
        self._mmid_word = prog.mmid.word
        self._otree_word = prog.otree_word
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

    # ── Indices (Phase 6A: no-op placeholder) ────────────────────────────────

    def _rebuild_indices(self) -> None:
        """Rebuild lookup indices after a mutation.

        Phase 6A: no-op.  Indices (widget_span, containment,
        opcode_index, handler_bindings) are added in Phase 6B when the
        canvas reads from the stream directly.
        """
        pass  # Phase 6B: rebuild widget_span, containment, etc.

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
