"""help_topics — the docs/help topic store (pure logic, no Tk).

A directory of helpdown topic files, one per topic: docs/help/<id>.md. Provides
listing, existence checks, parsed topics, the Documentation tab's substring search,
and the dead-link report the docs-lint test uses. Format lives in helpdown.py.
"""

import os

import helpdown

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DIR = os.path.abspath(os.path.join(_HERE, "..", "docs", "help"))


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
