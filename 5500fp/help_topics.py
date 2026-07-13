"""help_topics — the docs/help topic store (pure logic, no Tk).

A directory of helpdown topic files, one per topic: docs/help/<id>.md. Provides
listing, existence checks, parsed topics, the Documentation tab's substring search,
and the dead-link report the docs-lint test uses. Format lives in helpdown.py.
"""

import os
import re
import shutil
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:                       # importable when FlowCode execs us
    sys.path.insert(0, _HERE)

import helpdown                                  # noqa: E402
DEFAULT_DIR = os.path.abspath(os.path.join(_HERE, "..", "docs", "help"))

BAK_SUFFIX = ".bak"                              # one-level saved-over backup
# A safe topic id: lowercase alnum + hyphens, alnum-led — matches the on-disk
# convention ('nine-primaries', 'first-program') and forbids path parts/traversal.
_ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class HelpTopics:
    """The on-disk set of helpdown topics under `base_dir` (default docs/help)."""

    def __init__(self, base_dir=None):
        self.base_dir = base_dir or DEFAULT_DIR

    def _path(self, topic_id):
        return os.path.join(self.base_dir, topic_id + ".md")

    def ids(self):
        """Sorted topic ids (filenames without .md) present on disk."""
        if not os.path.isdir(self.base_dir):
            return []
        return sorted(f[:-3] for f in os.listdir(self.base_dir)
                      if f.endswith(".md"))

    def exists(self, topic_id):
        return os.path.isfile(self._path(topic_id))

    def raw(self, topic_id):
        with open(self._path(topic_id), encoding="utf-8") as fh:
            return fh.read()

    def topic(self, topic_id):
        """Parsed topic dict, or None if the id has no file."""
        if not self.exists(topic_id):
            return None
        return helpdown.parse_topic(self.raw(topic_id))

    def index(self):
        """[(topic_id, title, section)] for every topic, sorted by
        (section, title) — the source for the Documentation tab's index tree."""
        rows = []
        for tid in self.ids():
            t = self.topic(tid)
            if t:
                rows.append((tid, t["title"], t["section"] or "Other"))
        return sorted(rows, key=lambda r: (r[2].casefold(), r[1].casefold()))

    def search(self, query):
        """Case-folded substring search over title + body of every topic (v1).
        Returns [(topic_id, title)], sorted by title."""
        q = (query or "").strip().casefold()
        if not q:
            return []
        hits = []
        for tid in self.ids():
            t = self.topic(tid)
            if t and q in helpdown.plain_text(t).casefold():
                hits.append((tid, t["title"]))
        return sorted(hits, key=lambda x: x[1].casefold())

    def dead_links(self):
        """{topic_id: [missing_target, ...]} — links whose target topic has no
        file (an intra-topic #anchor is ignored, v1). The docs-lint check fails
        if this is non-empty."""
        out = {}
        known = set(self.ids())
        for tid in self.ids():
            t = self.topic(tid)
            missing = sorted({tgt for tgt in helpdown.topic_links(t)
                              if tgt.split("#", 1)[0] not in known})
            if missing:
                out[tid] = missing
        return out

    # ── editor support (the ONE write path + live-lint helpers) ─────────────────
    def is_valid_id(self, topic_id):
        """A topic id is safe iff it is alnum-led lowercase alnum + hyphens — no
        path separators, no traversal, no extension. Used by save() and the
        editor's New-Topic validation."""
        return bool(_ID_RE.match(topic_id or ""))

    def missing_targets(self, raw):
        """Dead-link targets in a single raw helpdown string — [[id|label]] whose
        id has no file (intra-topic #anchors ignored, v1). Powers the editor's
        LIVE lint so the author sees loose ends while typing, before Save."""
        known = set(self.ids())
        t = helpdown.parse_topic(raw or "")
        return sorted({tgt for tgt in helpdown.topic_links(t)
                       if tgt.split("#", 1)[0] not in known})

    def save(self, topic_id, raw):
        """Write a topic's raw helpdown to docs/help/<id>.md. This is the ONE write
        path in the whole codebase — every other module only reads (one-organ
        discipline). If help ever migrates to the native content store
        (GristMill/MMID thread), only this method's innards change; nothing else
        knows where the bytes live. Returns the path written.

        Two safety riders are law (CF5 ruling 2026-07-13 — this project has
        document-corruption scar tissue):
          * ATOMIC — content is written to a temp file in the same directory, then
            os.replace()'d over the target (atomic on POSIX). A crash mid-write can
            never leave a half-written topic; readers see old-or-new, never partial.
          * ONE-LEVEL BACKUP — the prior version is copied to <id>.md.bak first
            (git-ignored), so a save-over is recoverable. The editor's in-buffer
            Revert covers the not-yet-saved case; the .bak covers the saved-over one.

        TWO-TIER LINT (CF5): save() is WARN-AND-ALLOW. It will happily persist a
        draft that still carries dead links or parse oddities — the editor surfaces
        those live, but never blocks, matching the framework's soft dead-link law.
        The REPO gate does not relax: test_docs_lint still fails the sweep on any
        dead link, so committed canon stays clean even while working drafts don't.
        """
        if not self.is_valid_id(topic_id):
            raise ValueError(f"unsafe topic id: {topic_id!r}")
        os.makedirs(self.base_dir, exist_ok=True)
        target = self._path(topic_id)
        if os.path.isfile(target):                      # preserve one step of history
            shutil.copy2(target, target + BAK_SUFFIX)
        fd, tmp = tempfile.mkstemp(dir=self.base_dir,   # same dir → rename is atomic
                                   prefix="." + topic_id + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(raw)
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, target)                      # atomic swap
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
        return target
