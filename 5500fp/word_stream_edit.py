"""word_stream_edit.py — Primitive mutation on a WordStream (Phase 6A).

Each user action in the GHOST Canvas decomposes into one or more
WordStreamEdit primitives.  The undo system stores these as both:
  - word-level entries (Alt+Z/Y steps through primitives one-by-one)
  - semantic groups (Ctrl+Z/Y reverses a whole user-visible action at once)

Date: 2026-06-16, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class WordStreamEdit:
    """A primitive mutation on a WordStream.

    Operations are minimal: replace the entire word list (used in Phase 6A
    where each semantic action is one coarse replace), or insert / delete a
    span of words at a given position (used in Phase 6B+ for fine-grained edits).

    Fields
    ------
    op : str
        'insert' | 'delete' | 'replace'
    position : int
        Word index where the operation begins.  For 'replace', 0 (whole list).
    words_before : list[int]
        Words that exist at *position* before the edit (for undo).
    words_after : list[int]
        Words that exist at *position* after the edit (for redo).
    semantic_label : str | None
        Human-readable label for the enclosing semantic group, e.g.
        "Place button", "Change label", "Resize window".
        None for bare word-level primitives that are not part of a user action.
    """

    op: str                            # 'insert' | 'delete' | 'replace'
    position: int                      # word index where operation begins
    words_before: List[int]            # state before (for undo)
    words_after: List[int]             # state after (for redo)
    semantic_label: Optional[str] = None

    def invert(self) -> 'WordStreamEdit':
        """Return the edit that exactly undoes this one.

        insert  ↔  delete   (swap op)
        replace ↔  replace  (swap before ↔ after)
        position and label are preserved.
        """
        op_inv = {'insert': 'delete', 'delete': 'insert', 'replace': 'replace'}
        return WordStreamEdit(
            op=op_inv[self.op],
            position=self.position,
            words_before=self.words_after,
            words_after=self.words_before,
            semantic_label=self.semantic_label,
        )

    def __repr__(self) -> str:
        nb = len(self.words_before)
        na = len(self.words_after)
        lab = f' [{self.semantic_label}]' if self.semantic_label else ''
        return (f'WordStreamEdit(op={self.op!r}, pos={self.position}, '
                f'before={nb}w, after={na}w{lab})')
