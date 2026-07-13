"""test_help_editor — laws for the help editor's write path (HelpTopics.save()).

The editor is the first machine in the project that overwrites human-authored files,
so its write path is guarded here: atomic replace, one-level backup, id safety, and
the live-lint helper. CF5 ruling 2026-07-13 (safe writes are non-negotiable).

Pure-logic tests against a temp base_dir — no Tk, no real docs/help touched.
"""
import os
import shutil
import tempfile
import unittest

import help_topics as HT


class SaveWriteLaws(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="helped_")
        self.store = HT.HelpTopics(base_dir=self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _bak(self, tid):
        return os.path.join(self.d, tid + ".md" + HT.BAK_SUFFIX)

    def test_roundtrip_and_index(self):
        raw = "Alpha\nsection: Start here\n\n# Alpha\nbody\n"
        self.store.save("alpha", raw)
        self.assertEqual(self.store.raw("alpha"), raw)
        self.assertIn("alpha", self.store.ids())
        self.assertEqual(self.store.topic("alpha")["title"], "Alpha")

    def test_backup_preserves_prior_on_saveover(self):
        self.store.save("alpha", "v1")
        self.store.save("alpha", "v2")
        self.assertEqual(self.store.raw("alpha"), "v2")          # new content live
        with open(self._bak("alpha"), encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "v1")                    # prior recoverable

    def test_first_save_makes_no_backup(self):
        self.store.save("beta", "hello")
        self.assertFalse(os.path.exists(self._bak("beta")))

    def test_atomic_leaves_no_temp_litter(self):
        self.store.save("gamma", "x" * 5000)
        leftovers = [f for f in os.listdir(self.d) if f.endswith(".tmp")]
        self.assertEqual(leftovers, [], f"temp files left behind: {leftovers}")

    def test_save_over_is_still_atomic_and_complete(self):
        self.store.save("delta", "first")
        self.store.save("delta", "second-longer-content")
        self.assertEqual(self.store.raw("delta"), "second-longer-content")
        self.assertEqual([f for f in os.listdir(self.d) if f.endswith(".tmp")], [])

    def test_unsafe_ids_rejected(self):
        for bad in ["../evil", "a/b", "Upper", "a.b", "", "-lead", "under_score",
                    "space bar", "..", "."]:
            with self.assertRaises(ValueError, msg=f"{bad!r} should be rejected"):
                self.store.save(bad, "x")
        # nothing bad was written
        self.assertEqual(self.store.ids(), [])

    def test_valid_ids_accepted(self):
        for good in ["nine-primaries", "first-program", "a", "a1", "x9y-z"]:
            self.assertTrue(self.store.is_valid_id(good), good)

    def test_missing_targets_for_live_lint(self):
        self.store.save("a", "A\nsection: X\n\n")
        raw = "B\nsection: X\n\nsee [[a|A]], [[ghost|G]] and [[a#anchor|deep]]\n"
        # a exists; ghost does not; the #anchor resolves to base id 'a'
        self.assertEqual(self.store.missing_targets(raw), ["ghost"])

    def test_missing_targets_empty_when_all_resolve(self):
        self.store.save("a", "A\nsection: X\n\n")
        self.store.save("b", "B\nsection: X\n\n")
        self.assertEqual(self.store.missing_targets("X\n\n[[a]] [[b]]"), [])


class TwoTierLintLaw(unittest.TestCase):
    """The editor's save is warn-and-allow; the repo gate stays strict (CF5). A draft
    with a dead link saves fine, but dead_links() — what test_docs_lint asserts empty —
    still reports it, so a commit carrying the loose end fails the sweep."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="tier_")
        self.store = HT.HelpTopics(base_dir=self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_save_allows_dead_link_but_repo_gate_flags_it(self):
        self.store.save("a", "A\nsection: X\n\nsee [[ghost|G]]\n")   # ghost missing
        self.assertIn("a", self.store.ids())                          # save allowed
        self.assertEqual(self.store.dead_links(), {"a": ["ghost"]})   # gate would fail
        self.store.save("ghost", "GHOST\nsection: X\n\nhi\n")         # resolve the end
        self.assertEqual(self.store.dead_links(), {})                 # gate now clean


if __name__ == "__main__":
    unittest.main()
