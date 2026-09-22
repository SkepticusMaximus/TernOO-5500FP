"""test_terndoc.py — TernDoc S1's laws.

The face-blind document engine: model ops + undo, markdown round-trip,
html render-out, spellcheck pass, and — the captain's forward-compat
demand — proof the TextCodec seam actually swaps (a fake ternary codec
drives the same model untouched).

Run:  cd 5500fp && python3 -m unittest test_terndoc
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import terndoc as TD

MD = """# The Ship's Log

A **bold** claim with *style* and `code` and a [link](https://x.net/d).

## Cargo
- first item
- second **heavy** item

1. ordered one

```python
x = 1  # not prose, never spellchecked
```
"""


class TestModelOps(unittest.TestCase):
    def test_insert_and_cursor(self):
        d = TD.TernDoc()
        d.insert_text(0, 0, "hello world")
        self.assertEqual(d.text_of(0), "hello world")
        self.assertEqual(d.cursor, (0, 11))

    def test_styled_insert_merges_spans(self):
        d = TD.TernDoc()
        d.insert_text(0, 0, "ab")
        d.insert_text(0, 2, "cd")
        self.assertEqual(len(d.blocks[0]["spans"]), 1)   # same attrs merge

    def test_toggle_style_and_toggle_back(self):
        d = TD.TernDoc()
        d.insert_text(0, 0, "make me bold")
        d.toggle_style(0, 8, 12, "b")
        self.assertIn("b", d.blocks[0]["spans"][-1]["st"])
        d.toggle_style(0, 8, 12, "b")
        self.assertEqual(len(d.blocks[0]["spans"]), 1)   # merged back clean

    def test_delete_range(self):
        d = TD.TernDoc()
        d.insert_text(0, 0, "abcdef")
        d.delete_range(0, 2, 4)
        self.assertEqual(d.text_of(0), "abef")
        self.assertEqual(d.cursor, (0, 2))

    def test_split_and_merge_roundtrip(self):
        d = TD.TernDoc()
        d.insert_text(0, 0, "onetwo")
        d.split_block(0, 3)
        self.assertEqual([d.text_of(0), d.text_of(1)], ["one", "two"])
        self.assertEqual(d.cursor, (1, 0))
        d.merge_with_previous(1)
        self.assertEqual(d.text_of(0), "onetwo")
        self.assertEqual(d.cursor, (0, 3))

    def test_set_kind_prose_code_prose(self):
        d = TD.TernDoc()
        d.insert_text(0, 0, "print(1)")
        d.set_kind(0, "code", "python")
        self.assertEqual(d.blocks[0]["kind"], "code")
        d.set_kind(0, "p")
        self.assertEqual(d.text_of(0), "print(1)")

    def test_undo_redo(self):
        d = TD.TernDoc()
        d.insert_text(0, 0, "alpha")
        d.insert_text(0, 5, " beta")
        self.assertTrue(d.undo())
        self.assertEqual(d.text_of(0), "alpha")
        self.assertTrue(d.redo())
        self.assertEqual(d.text_of(0), "alpha beta")

    def test_link(self):
        d = TD.TernDoc()
        d.insert_text(0, 0, "see the docs here")
        d.set_link(0, 8, 12, "https://x.net")
        hrefs = [s["href"] for s in d.blocks[0]["spans"]]
        self.assertIn("https://x.net", hrefs)


class TestMarkdown(unittest.TestCase):
    def test_parse_shapes(self):
        d = TD.from_markdown(MD)
        kinds = [b["kind"] for b in d.blocks]
        self.assertEqual(kinds, ["h1", "p", "h2", "ul", "ul", "ol", "code"])

    def test_inline_styles_parsed(self):
        d = TD.from_markdown(MD)
        p = d.blocks[1]["spans"]
        self.assertTrue(any("b" in s["st"] for s in p))
        self.assertTrue(any("i" in s["st"] for s in p))
        self.assertTrue(any("c" in s["st"] for s in p))
        self.assertTrue(any(s["href"] for s in p))

    def test_round_trip_is_stable(self):
        d1 = TD.from_markdown(MD)
        md1 = TD.to_markdown(d1)
        d2 = TD.from_markdown(md1)
        self.assertEqual(TD.to_markdown(d2), md1)        # fixpoint
        self.assertEqual(d1.digest(), d2.digest())       # same model

    def test_code_block_survives_verbatim(self):
        d = TD.from_markdown(MD)
        code = next(b for b in d.blocks if b["kind"] == "code")
        self.assertEqual(code["lang"], "python")
        self.assertIn("# not prose", code["text"])


class TestHtml(unittest.TestCase):
    def test_render_out(self):
        h = TD.to_html(TD.from_markdown(MD), title="log")
        for frag in ("<h1>", "<strong>bold</strong>", "<em>style</em>",
                     "<code>code</code>", '<a href="https://x.net/d">',
                     "<ul>", "</ul>", "<ol>", "<pre><code>"):
            self.assertIn(frag, h)

    def test_escaping(self):
        d = TD.TernDoc()
        d.insert_text(0, 0, "a < b & c")
        self.assertIn("a &lt; b &amp; c", TD.to_html(d))

    def test_save_as_by_extension(self):
        d = TD.from_markdown(MD)
        with tempfile.TemporaryDirectory() as tmp:
            TD.save_as(d, os.path.join(tmp, "x.md"))
            TD.save_as(d, os.path.join(tmp, "x.html"))
            self.assertTrue(os.path.getsize(os.path.join(tmp, "x.html")))
            with self.assertRaises(ValueError):
                TD.save_as(d, os.path.join(tmp, "x.docx"))


class TestSpellcheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.checker = TD.WordlistChecker()

    def test_wordlist_loaded(self):
        self.assertGreater(len(self.checker.words), 10000)

    def test_finds_misspelling_with_suggestion(self):
        d = TD.from_markdown("The shipp sails tonight.\n")
        issues = TD.spellcheck(d, self.checker)
        words = [w for _, _, _, w, _ in issues]
        self.assertIn("shipp", words)
        sug = next(s for _, _, _, w, s in issues if w == "shipp")
        self.assertIn("ship", sug)

    def test_code_is_never_prose(self):
        d = TD.from_markdown("```\nxyzzyq garblefarb\n```\n")
        self.assertEqual(TD.spellcheck(d, self.checker), [])
        d2 = TD.from_markdown("run `garblefarb` now\n")
        words = [w for _, _, _, w, _ in TD.spellcheck(d2, self.checker)]
        self.assertNotIn("garblefarb", words)

    def test_offsets_point_at_the_word(self):
        d = TD.from_markdown("a shipp sails\n")
        bi, a, z, w, _ = TD.spellcheck(d, self.checker)[0]
        self.assertEqual(d.codec.slice(d.text_of(bi), a, z), w)


class FakeTernaryCodec(TD.UnicodeCodec):
    """Stand-in for the future glyph-plane codec: proves the seam swaps.
    Same contract, different name + canonical bytes flavor."""
    name = "ternary-glyph-plane-fake"

    def canonical_bytes(self, s):
        return b"T3:" + s.encode("utf-8")


class TestCodecSeam(unittest.TestCase):
    def test_model_runs_on_a_swapped_codec(self):
        d = TD.TernDoc(codec=FakeTernaryCodec())
        d.insert_text(0, 0, "native text someday")
        d.toggle_style(0, 0, 6, "b")
        d.split_block(0, 6)
        self.assertEqual(d.codec.name, "ternary-glyph-plane-fake")
        self.assertEqual([d.text_of(0), d.text_of(1)],
                         ["native", " text someday"])

    def test_markdown_parses_under_swapped_codec(self):
        d = TD.from_markdown(MD, codec=FakeTernaryCodec())
        self.assertEqual(len(d.blocks), 7)


class TestCanonicalForm(unittest.TestCase):
    def test_digest_is_deterministic(self):
        a = TD.from_markdown(MD).digest()
        b = TD.from_markdown(MD).digest()
        self.assertEqual(a, b)
        self.assertEqual(len(a), 64)


if __name__ == "__main__":
    unittest.main()
