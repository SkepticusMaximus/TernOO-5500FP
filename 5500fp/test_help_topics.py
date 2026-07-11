"""test_help_topics — the docs/help topic store (pure logic, no Tk)."""

import os
import tempfile
import unittest

from help_topics import HelpTopics


def _mk(base, tid, text):
    with open(os.path.join(base, tid + ".md"), "w", encoding="utf-8") as fh:
        fh.write(text)


class TestHelpTopics(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        _mk(self.dir, "mesh",
            "The Mesh Tab\nsection: Tabs\n\nSell compute. See [[p2pcp]] and "
            "[[ghost|the router]] and [[nope|dead]].")
        _mk(self.dir, "p2pcp", "P2PCP\nsection: Concepts\n\nTrustless compute.")
        _mk(self.dir, "ghost", "GHOST\nsection: Concepts\n\nThe router.")
        self.T = HelpTopics(self.dir)

    def test_ids_and_exists(self):
        self.assertEqual(self.T.ids(), ["ghost", "mesh", "p2pcp"])
        self.assertTrue(self.T.exists("mesh"))
        self.assertFalse(self.T.exists("nope"))

    def test_topic_parses_or_none(self):
        self.assertEqual(self.T.topic("mesh")["title"], "The Mesh Tab")
        self.assertIsNone(self.T.topic("nope"))

    def test_index_grouped_by_section(self):
        idx = self.T.index()
        self.assertIn(("ghost", "GHOST", "Concepts"), idx)
        self.assertIn(("mesh", "The Mesh Tab", "Tabs"), idx)

    def test_search_substring_over_body(self):
        self.assertEqual([tid for tid, _ in self.T.search("trustless")], ["p2pcp"])
        # link LABELS are searchable text too — mesh links to "the router"
        self.assertEqual([tid for tid, _ in self.T.search("router")],
                         ["ghost", "mesh"])
        self.assertEqual(self.T.search(""), [])

    def test_dead_links_reported(self):
        dead = self.T.dead_links()
        self.assertEqual(dead, {"mesh": ["nope"]})   # p2pcp + ghost exist

    def test_missing_dir_is_empty(self):
        self.assertEqual(HelpTopics("/no/such/dir").ids(), [])


if __name__ == "__main__":
    unittest.main()
