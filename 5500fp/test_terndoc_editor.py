"""test_terndoc_editor.py — S2's laws: layout geometry and input handling,
proven with a monospace measuring stub. No toolkit anywhere: everything a
face will ever draw or route is asserted here first.

Run:  cd 5500fp && python3 -m unittest test_terndoc_editor
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import terndoc as TD
import terndoc_editor as ED

CW = 10                                  # monospace stub: 10px per char


def measure(text, _style):
    return CW * len(text)


def make(md, wrap_chars=20):
    doc = TD.from_markdown(md)
    lay = ED.Layout(doc, measure, wrap_px=wrap_chars * CW, line_h=16)
    ed = ED.Editor(doc)
    ed.attach_layout(lay)
    return doc, lay, ed


def relayout(ed, wrap_chars=20):
    lay = ED.Layout(ed.doc, measure, wrap_px=wrap_chars * CW, line_h=16)
    ed.attach_layout(lay)
    return lay


class TestLayout(unittest.TestCase):
    def test_wraps_at_word_boundaries(self):
        _, lay, _ = make("alpha beta gamma delta epsilon\n")
        texts = ["".join(f for f, *_ in ln["segs"]) for ln in lay.lines]
        self.assertGreater(len(texts), 1)
        for t in texts:
            self.assertLessEqual(len(t), 20)
        self.assertEqual(" ".join(texts).split(),
                         "alpha beta gamma delta epsilon".split())

    def test_long_word_breaks_hard(self):
        _, lay, _ = make("a" * 50 + "\n")
        self.assertEqual(len(lay.lines), 3)          # 20+20+10

    def test_heading_line_taller(self):
        _, lay, _ = make("# Title\n\nbody\n")
        self.assertGreater(lay.lines[0]["h"], lay.lines[1]["h"])

    def test_styled_segments_carry_style_keys(self):
        _, lay, _ = make("a **b** *c* `d`\n")
        keys = [sk for ln in lay.lines for _f, sk, *_ in ln["segs"]]
        for want in ("r", "b", "i", "c"):
            self.assertIn(want, keys)

    def test_code_block_newlines_make_lines(self):
        _, lay, _ = make("```\none\ntwo\nthree\n```\n")
        self.assertEqual(len(lay.lines), 3)

    def test_empty_block_still_has_a_line(self):
        doc = TD.TernDoc()
        lay = ED.Layout(doc, measure, 200, 16)
        self.assertEqual(len(lay.lines), 1)

    def test_caret_xy_and_hit_test_are_inverses(self):
        _, lay, _ = make("alpha beta gamma delta\n")
        for off in (0, 3, 7, 12, 18):
            x, y, _h = lay.caret_xy(0, off)
            self.assertEqual(lay.hit_test(x + 1, y + 1), (0, off))

    def test_hit_test_clamps_below_content(self):
        _, lay, _ = make("word\n")
        bi, off = lay.hit_test(500, 5000)
        self.assertEqual(bi, 0)
        self.assertEqual(off, 4)


class TestEditing(unittest.TestCase):
    def test_typing_inserts_at_cursor(self):
        doc, _, ed = make("hello\n")
        doc.cursor = (0, 5)
        ed.type_text(" world")
        self.assertEqual(doc.text_of(0), "hello world")

    def test_enter_splits_backspace_rejoins(self):
        doc, _, ed = make("onetwo\n")
        doc.cursor = (0, 3)
        ed.key_enter()
        relayout(ed)
        self.assertEqual([doc.text_of(0), doc.text_of(1)], ["one", "two"])
        ed.key_backspace()                        # at (1,0) → merge
        self.assertEqual(doc.text_of(0), "onetwo")

    def test_backspace_deletes_selection_first(self):
        doc, _, ed = make("abcdef\n")
        doc.anchor, doc.cursor = (0, 1), (0, 4)
        ed.key_backspace()
        self.assertEqual(doc.text_of(0), "aef")

    def test_horizontal_motion_crosses_blocks(self):
        doc, _, ed = make("ab\n\ncd\n")
        doc.cursor = (0, 2)
        ed.move_h(+1)
        self.assertEqual(doc.cursor, (1, 0))
        ed.move_h(-1)
        self.assertEqual(doc.cursor, (0, 2))

    def test_vertical_motion_keeps_column(self):
        doc, lay, ed = make("alpha beta gamma delta epsilon zeta\n", 12)
        doc.cursor = (0, 3)
        ed.move_v(+1)
        _bi, off = doc.cursor
        self.assertNotEqual(off, 3)               # moved to next visual line
        x, _y, _h = lay.caret_xy(*doc.cursor)
        self.assertEqual(x, 30)                   # same pixel column

    def test_click_places_cursor_and_drag_selects(self):
        doc, lay, ed = make("alpha beta\n")
        ed.click(CW * 2 + 1, 1)
        self.assertEqual(doc.cursor, (0, 2))
        ed.drag(CW * 7 + 1, 1)
        self.assertEqual(ed.selected_text(), "pha b")

    def test_toggle_bold_on_selection(self):
        doc, _, ed = make("make me bold\n")
        doc.anchor, doc.cursor = (0, 8), (0, 12)
        ed.toggle("b")
        self.assertTrue(any("b" in s["st"] for s in doc.blocks[0]["spans"]))

    def test_set_kind_heading(self):
        doc, _, ed = make("title\n")
        ed.set_kind("h2")
        self.assertEqual(doc.blocks[0]["kind"], "h2")

    def test_undo_through_controller(self):
        doc, _, ed = make("x\n")
        doc.cursor = (0, 1)
        ed.type_text("y")
        ed.undo()
        self.assertEqual(doc.text_of(0), "x")


class TestRoundTripAfterEditing(unittest.TestCase):
    def test_edited_doc_serializes_cleanly(self):
        doc, _, ed = make("# T\n\nhello\n")
        doc.cursor = (1, 5)
        ed.type_text(" brave world")
        doc.anchor, doc.cursor = (1, 6), (1, 11)
        ed.toggle("b")
        md = TD.to_markdown(doc)
        self.assertIn("hello **brave** world", md)
        d2 = TD.from_markdown(md)
        self.assertEqual(d2.digest(), doc.digest())


if __name__ == "__main__":
    unittest.main()
