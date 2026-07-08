"""test_font_import.py — font-import conversion core (UI-free, pure geometry).

Proves the deterministic heart of the pipeline with synthetic outlines: Bézier
flattening, grid normalisation, and codepoint→house-ordinal mapping (unknowns
flagged, never guessed). The TTF/OTF parser is a separate thin adapter.
"""

import unittest

import ternoo_font_import as F
import ternoo_glyph as G


class TestFlatten(unittest.TestCase):
    def test_quad_hits_endpoint_and_count(self):
        pts = F.flatten_quad((0, 0), (0, 10), (10, 10), steps=4)
        self.assertEqual(len(pts), 4)
        self.assertEqual(pts[-1], (10, 10))          # ends on p1

    def test_cubic_hits_endpoint(self):
        pts = F.flatten_cubic((0, 0), (0, 9), (9, 9), (9, 0), steps=6)
        self.assertEqual(pts[-1], (9, 0))

    def test_contour_starts_at_start(self):
        poly = F.flatten_contour((1, 2), [('line', (3, 4))])
        self.assertEqual(poly[0], (1, 2))
        self.assertEqual(poly[-1], (3, 4))


class TestNormalize(unittest.TestCase):
    def test_cap_height_maps_to_six(self):
        grid, adv = F.normalize([[(0, 0), (500, 1000), (1000, 0)]], 1000)
        self.assertEqual(grid[0][0], (0.0, 0.0))     # baseline stays 0
        self.assertEqual(grid[0][1], (3.0, 6.0))     # cap height -> 6
        self.assertEqual(adv, 6.0)

    def test_left_edge_to_zero(self):
        grid, adv = F.normalize([[(200, 0), (400, 600)]], 600)
        self.assertEqual(grid[0][0], (0.0, 0.0))     # min-x translated to 0
        self.assertAlmostEqual(adv, 2.0)


class TestMapChar(unittest.TestCase):
    def test_upper_lower_digit_symbol(self):
        self.assertEqual(F.map_char('A'), (G.ORDINAL['A'], +1))
        self.assertEqual(F.map_char('a'), (G.ORDINAL['A'], -1))
        self.assertEqual(F.map_char('5'), (G.ORDINAL['5'], 0))
        self.assertEqual(F.map_char('+'), (G.ORDINAL['+'], 0))

    def test_unmapped_returns_none(self):
        self.assertIsNone(F.map_char('€'))


class TestImportGlyph(unittest.TestCase):
    # a crude triangular 'A' with a crossbar, in 1000-unit font space
    A_CONTOURS = [((0, 0), [('line', (500, 1000)), ('line', (1000, 0))]),
                  ((200, 400), [('line', (800, 400))])]

    def test_mapped_glyph(self):
        r = F.import_glyph('A', self.A_CONTOURS, cap_height=1000)
        self.assertFalse(r['unmapped'])
        self.assertEqual(r['ordinal'], G.ORDINAL['A'])
        self.assertEqual(r['case'], +1)
        self.assertTrue(r['strokes'])
        self.assertEqual(G.get_ordinal(r['word']), G.ORDINAL['A'])
        # strokes normalised into grid height (cap → 6)
        ys = [y for poly in r['strokes'] for (_, y) in poly]
        self.assertAlmostEqual(max(ys), 6.0)

    def test_unmapped_glyph_flagged_not_dropped(self):
        r = F.import_glyph('€', [((0, 0), [('line', (500, 500))])],
                           cap_height=1000)
        self.assertTrue(r['unmapped'])
        self.assertTrue(r['strokes'])                # still converted, just no ordinal


if __name__ == '__main__':
    unittest.main()
