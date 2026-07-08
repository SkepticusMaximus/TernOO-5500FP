"""test_glyph_canvas.py — renderer layout/geometry laws (UI-free).

The GlyphSurface drawing is screen-verified by Stevo; these pin the pure
decisions: scale (incl. small-caps), monospace advance, literal-refusal,
missing-glyph → '~' placeholder, and line-wrap.
"""

import unittest

import glyph_canvas as GC
import ternoo_glyph as G
import ternoo_glyph_strokes as S


class TestScale(unittest.TestCase):
    def test_upper_full_scale(self):
        self.assertAlmostEqual(GC.scale_for(18, +1), 3.0)

    def test_caseless_full_scale(self):
        self.assertAlmostEqual(GC.scale_for(18, 0), 3.0)

    def test_lower_two_thirds(self):
        self.assertAlmostEqual(GC.scale_for(18, -1), 2.0)

    def test_advance_is_monospace_regardless_of_case(self):
        # advance depends only on size, so caps and small-caps share a cell
        self.assertAlmostEqual(GC.advance_px(18), 18.0)


class TestResolve(unittest.TestCase):
    def test_known_glyph_has_strokes(self):
        _o, _c, strokes, ph = GC.resolve_glyph(G.make_glyph(G.ORDINAL['A'], +1))
        self.assertFalse(ph)
        self.assertTrue(len(strokes) >= 1)

    def test_missing_glyph_falls_to_placeholder(self):
        # ordinal 40 is a valid text word but unassigned in the house font
        _o, _c, strokes, ph = GC.resolve_glyph(G.make_glyph(40))
        self.assertTrue(ph)
        self.assertEqual(strokes, S.strokes_for_ordinal(G.PLACEHOLDER_ORD))

    def test_literal_is_refused(self):
        with self.assertRaises(G.GlyphError):
            GC.resolve_glyph(G.make_literal(9))


class TestLayout(unittest.TestCase):
    def test_wrap_produces_multiple_lines(self):
        words = G.text_to_words('A' * 40)
        placed = GC.plan_layout(words, width_px=100, size=18)
        lines = {ln for _, _, ln in placed}
        self.assertGreater(len(lines), 1)
        # every line starts back at the left margin
        firsts = {}
        for w, x, ln in placed:
            firsts.setdefault(ln, x)
        for x in firsts.values():
            self.assertAlmostEqual(x, 4.0)

    def test_single_line_when_it_fits(self):
        placed = GC.plan_layout(G.text_to_words('HI'), width_px=600, size=18)
        self.assertEqual({ln for _, _, ln in placed}, {0})


if __name__ == '__main__':
    unittest.main()
