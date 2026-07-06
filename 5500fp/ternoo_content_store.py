"""ternoo_content_store.py — content-addressable residence, the
corrected MMID/MMOE architecture as running code (6 Jul 2026).

The month's mathematics, operationalized:
  * MMOE  — the pattern itself: a canonical sequence of 24-trit words,
            RESIDENT in the store. Never derived from anything.
  * MMID  — the pattern's 54-trit sponge digest (ternary_sponge),
            computed ONCE at insert (the B8 transposition: expensive
            derivation at learning time, cheap CALL forever after).
  * Search — ordered search over resident MMIDs (the bubble-sort
            cut-point role, done honestly: residents are kept sorted;
            lookup is O(log n) bisection).
  * Verify-on-fetch — the digest is recomputed from what was found;
            what you fetched MUST be what was filed.
  * Insert-time collision handling — same MMID + same content = dedupe
            hit (returns the existing entry; learning an old pattern
            costs one lookup); same MMID + different content = a
            DETECTED collision, raised loudly, never silent.

Uniqueness is claimed only among residents — never against the
unbounded hypothetical set. The store never traverses the infinite;
it folds real content and searches the finite.

Date: 2026-07-06, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import bisect
import importlib.util as _ilu
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SP = _load('ternary_sponge')


class CollisionError(ValueError):
    """Same MMID, different content — detected at insert, never silent."""


class VerifyError(ValueError):
    """Fetched content no longer matches its MMID — tampering or rot."""


def canonicalize(words) -> tuple:
    """The canonical MMOE form: a tuple of ints, each reduced to a
    lawful 24-trit word value. One shape per pattern — many
    descriptions, one canon (B8 step 1)."""
    return tuple(int(w) % (SP.MOD ** SP.TRIBBLES_PER_WORD) for w in words)


class ContentStore:
    """In-memory reference implementation with optional JSON persistence.
    Residents are kept MMID-sorted; the sorted order is the mesh."""

    def __init__(self, path: str = None):
        self._mmids = []      # sorted list of mmid tuples
        self._moes = {}       # mmid tuple -> canonical word tuple
        self._path = path
        if path and os.path.exists(path):
            self._load_file(path)

    # ── insert: canonicalize → digest → search → collide/dedupe/file ──
    def insert(self, words) -> tuple:
        """File a pattern. Returns (mmid, created:bool).
        Dedupe: identical content → existing mmid, created=False.
        Collision: same mmid, different content → CollisionError."""
        moe = canonicalize(words)
        if not moe:
            raise ValueError("empty pattern")
        mmid = SP.digest(moe)
        i = bisect.bisect_left(self._mmids, mmid)
        if i < len(self._mmids) and self._mmids[i] == mmid:
            if self._moes[mmid] == moe:
                return mmid, False            # dedupe: one lookup, done
            raise CollisionError(
                f"MMID collision detected at insert: {mmid} already "
                f"resident with different content — full comparison "
                f"caught it (this is the design working, not failing)")
        self._mmids.insert(i, mmid)
        self._moes[mmid] = moe
        if self._path:
            self._save_file(self._path)
        return mmid, True

    # ── fetch: search → verify → deliver ───────────────────────────────
    def fetch(self, mmid) -> tuple:
        """Navigate to an MMID among residents and return its MMOE,
        re-verifying the digest of what was found (verify-on-fetch)."""
        mmid = tuple(mmid)
        i = bisect.bisect_left(self._mmids, mmid)
        if i >= len(self._mmids) or self._mmids[i] != mmid:
            raise KeyError(f"no resident pattern with MMID {mmid}")
        moe = self._moes[mmid]
        if SP.digest(moe) != mmid:
            raise VerifyError(
                f"verify-on-fetch FAILED for {mmid}: resident content "
                f"does not re-digest to its address")
        return moe

    def contains_content(self, words) -> bool:
        """Is this pattern already known? One digest + one bisection —
        the cheap CALL that learning-time derivation buys (B8)."""
        moe = canonicalize(words)
        mmid = SP.digest(moe)
        i = bisect.bisect_left(self._mmids, mmid)
        return (i < len(self._mmids) and self._mmids[i] == mmid
                and self._moes[mmid] == moe)

    def neighbors(self, mmid, k: int = 3):
        """The k resident MMIDs nearest in sort order — the cut-point
        neighborhood the navigation lands in."""
        mmid = tuple(mmid)
        i = bisect.bisect_left(self._mmids, mmid)
        lo = max(0, i - k)
        return self._mmids[lo:i + k]

    def __len__(self):
        return len(self._mmids)

    # ── persistence (reference-grade) ──────────────────────────────────
    def _save_file(self, path):
        data = [{'mmid': list(m), 'words': list(self._moes[m])}
                for m in self._mmids]
        with open(path, 'w') as f:
            json.dump(data, f)

    def _load_file(self, path):
        for e in json.load(open(path)):
            moe = tuple(e['words'])
            mmid = tuple(e['mmid'])
            if SP.digest(moe) != mmid:
                raise VerifyError(f"store file corrupt at {mmid}")
            i = bisect.bisect_left(self._mmids, mmid)
            self._mmids.insert(i, mmid)
            self._moes[mmid] = moe
