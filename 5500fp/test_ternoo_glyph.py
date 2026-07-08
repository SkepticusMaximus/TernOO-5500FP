"""test_ternoo_glyph.py — native glyph-plane laws (register v0.3, UI-free).

Pins the ratified STRING subtype (+1,−1) so no future doc can silently
re-import the DATA_STRING bug; round-trip, case-as-writes, literal range,
the ~ placeholder path, and the O1 X/Z amendments.
"""

import unittest

import ternoo_glyph as G


class TestSubtypePin(unittest.TestCase):
    def test_ratified_string_subtype_and_plane(self):
        w = G.make_glyph(G.ORDINAL['A'], +1)
        self.assertEqual(G.V.get_trit(w, 21), +1)   # STRING subtype hi
        self.assertEqual(G.V.get_trit(w, 20), -1)   # STRING subtype lo (canon)
        self.assertEqual(G.V.get_trit(w, 19), +1)   # native plane (STRING_TERNARY)
        self.assertTrue(G.is_glyph_plane(w))


class TestTextWords(unittest.TestCase):
    def test_roundtrip_encode_parse(self):
        w = G.make_glyph(G.ORDINAL['Q'], -1)
        self.assertEqual(G.parse_glyph(w), (G.ORDINAL['Q'], -1))

    def test_ordinal_zero_rejected(self):
        with self.assertRaises(G.GlyphError):
            G.make_glyph(0)

    def test_case_ops_are_writes_not_arithmetic(self):
        w = G.make_glyph(G.ORDINAL['M'], +1)
        self.assertEqual(G.get_case(G.to_lower(w)), -1)
        self.assertEqual(G.get_case(G.to_caseless(w)), 0)
        # ordinal is untouched by case writes
        self.assertEqual(G.get_ordinal(G.to_lower(w)), G.ORDINAL['M'])

    def test_fold_idempotent(self):
        w = G.make_glyph(G.ORDINAL['Z'], +1)
        self.assertEqual(G.fold_case(G.fold_case(w)), G.fold_case(w))

    def test_same_identity_vs_folded(self):
        up = G.make_glyph(G.ORDINAL['A'], +1)
        lo = G.make_glyph(G.ORDINAL['A'], -1)
        self.assertFalse(G.same_identity(up, lo))   # case differs → Y differs
        self.assertTrue(G.same_folded(up, lo))       # case-insensitive equal

    def test_Z_zero_and_X_produce_order(self):
        words = G.text_to_words('HELLO')
        for i, w in enumerate(words):
            self.assertEqual(G.get_font(w), 0)       # Z == 0 (house font)
            self.assertEqual(G.get_position(w), i)   # X == produce-order


class TestConversion(unittest.TestCase):
    def test_text_roundtrip(self):
        s = 'Trit Vague, 42!'
        self.assertEqual(G.words_to_text(G.text_to_words(s)), s)

    def test_math_roundtrip(self):
        s = 'E = M×C^2 ± √2 → ∞'
        self.assertEqual(G.words_to_text(G.text_to_words(s)), s)

    def test_unknown_strict_raises(self):
        with self.assertRaises(G.GlyphError):
            G.text_to_words('cost €5')

    def test_unknown_nonstrict_placeholder(self):
        words = G.text_to_words('€', strict=False)
        self.assertEqual(G.get_ordinal(words[0]), G.PLACEHOLDER_ORD)


class TestLiterals(unittest.TestCase):
    def test_literal_roundtrip(self):
        for v in (0, 1, -1, 12345, -193710244, 193710244):
            self.assertEqual(G.literal_value(G.make_literal(v)), v)

    def test_literal_overflow_raises(self):
        with self.assertRaises(G.GlyphError):
            G.make_literal(193710245)

    def test_literal_is_not_text(self):
        lit = G.make_literal(7)
        self.assertTrue(G.is_literal(lit))
        with self.assertRaises(G.GlyphError):          # renderer must refuse it
            G.parse_glyph(lit)

    def test_literal_to_digit_words(self):
        self.assertEqual(G.words_to_text(G.literal_to_digit_words(-42)), '-42')
        self.assertEqual(G.words_to_text(G.literal_to_digit_words(0)), '0')


class TestDecoderRecognition(unittest.TestCase):
    def test_decode_word_delegates_glyph(self):
        d = G.V.decode_word(G.make_glyph(G.ORDINAL['A'], +1))
        self.assertEqual(d['type'], 'STRING')
        self.assertEqual(d.get('plane'), 'native')
        self.assertEqual(d['glyph']['char'], 'A')

    def test_decode_word_literal(self):
        d = G.V.decode_word(G.make_literal(-7))
        self.assertEqual(d['glyph']['mode'], 'literal')
        self.assertEqual(d['glyph']['value'], -7)

    def test_ascii_string_unaffected(self):
        d = G.V.decode_word(G.V.build_string_word(G.V.STRING_ASCII, 123))
        self.assertEqual(d['encoding'], 'ascii')
        self.assertEqual(d['length_or_addr'], 123)


if __name__ == '__main__':
    unittest.main()
