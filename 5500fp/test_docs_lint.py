"""test_docs_lint — the docs phase's own sweep line (CF5 acceptance #4).

Every docs/help/*.md must (a) parse without the helpdown parser ever raising — that's
the never-crash law — and (b) have no dead [[links]] (a link whose target topic has no
file). A broken link fails the sweep with the offenders listed.
"""

import unittest

import helpdown
from help_topics import HelpTopics


class TestDocsLint(unittest.TestCase):
    def setUp(self):
        self.T = HelpTopics()                    # the real docs/help directory

    def test_every_topic_parses_without_raising(self):
        for tid in self.T.ids():
            try:
                helpdown.parse_topic(self.T.raw(tid))
            except Exception as e:               # noqa: BLE001 — that's the point
                self.fail(f"helpdown raised on {tid}.md: {e!r}")

    def test_no_dead_links(self):
        dead = self.T.dead_links()
        self.assertEqual(dead, {}, f"dead help links (missing target topic): {dead}")

    def test_proof_topics_present(self):
        ids = self.T.ids()
        self.assertIn("mesh", ids)               # the migrated proof topic
        self.assertIn("p2pcp", ids)              # mesh links here — two real topics


if __name__ == "__main__":
    unittest.main()
