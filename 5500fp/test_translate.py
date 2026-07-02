"""test_translate.py — Lingo Translator projections.

All five dialects must render the reference program without crashing and
contain the tokens a programmer of that flavor would recognize.  The
flowcode dialect must be the canonical projector (identity with
flowcode_dialect.project).

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import os
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


T = _load('flowcode_lingo_translate')
D = _load('flowcode_dialect')

PROGRAM = D.parse('''# demo
window main_win "Customer" at 200,150 size 400x300 layout vbox:
    button save_btn "Save" at 200,200 size 120x60
terminator on_save "clicked" at 700,100 size 120x60 entry
process doubler "Doubler" at 300,200 size 120x60:
    in input_value: number
    out output_value: number = input_value * 2
edge on_save -> doubler
cell A1 = 10
cell A2 = =A1+A1
cmd k1 = math_add(a=4, b=5) at 10,10
cmd k2 = math_multiply(b=3) at 60,10
pipe k1 -> k2.a
''')


class TestTranslator(unittest.TestCase):

    def test_all_dialects_render(self):
        for d in T.DIALECTS:
            out = T.render(PROGRAM, d)
            self.assertTrue(out.strip(), f"{d} rendered empty")
            self.assertIn('doubler', out, d)
            self.assertIn('main_win', out, d)

    def test_flowcode_is_canonical_projection(self):
        self.assertEqual(T.render(PROGRAM, 'flowcode'), D.project(PROGRAM))

    def test_python_flavor(self):
        out = T.render(PROGRAM, 'python')
        self.assertIn('def on_save():', out)
        self.assertIn('def doubler(input_value):', out)
        self.assertIn('return input_value * 2', out)
        self.assertIn("sheet['A2'] = A1+A1", out)
        self.assertIn('shell.math_add(a=4, b=5)', out)

    def test_java_flavor(self):
        out = T.render(PROGRAM, 'java')
        self.assertIn('int doubler(int input_value) {', out)
        self.assertIn('return input_value * 2;', out)
        self.assertIn('var k1 =', out)

    def test_vb_flavor(self):
        out = T.render(PROGRAM, 'vb')
        self.assertIn('Function doubler(input_value As Integer) As Integer',
                      out)
        self.assertIn('Sub on_save()', out)
        self.assertIn('Return input_value * 2', out)

    def test_c_flavor(self):
        out = T.render(PROGRAM, 'c')
        self.assertIn('int doubler(int input_value) {', out)
        self.assertIn('int k1 =', out)

    def test_unknown_dialect_raises(self):
        with self.assertRaises(ValueError):
            T.render(PROGRAM, 'cobol_on_wheels')


if __name__ == '__main__':
    unittest.main(verbosity=1)
