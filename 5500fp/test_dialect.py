"""test_dialect.py — textual FlowCode dialect + FileSystem abstraction.

Round-trip laws pinned:
  project(parse(t)) == t          for canonical t
  parse(project(m)) ~= m          (semantic equality on the fields carried)
Plus: parse errors carry line numbers and never partially mutate anything
(parse is pure — it returns or raises).

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import os
import tempfile
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load('flowcode_dialect')
FS = _load('filesystem')

CANON = '''# customer demo
window main_win "Main" at 200,150 size 400x300 layout vbox:
    button save_btn "Save" at 200,200 size 120x60
    entry cust_name "" at 200,260 size 160x30
terminator on_save "clicked" at 700,100 size 120x60 entry
process doubler "Doubler" at 300,200 size 120x60:
    in input_value: number
    out output_value: number = input_value * 2
    process step1 "step" at 320,220 size 120x60
edge on_save -> doubler
cell A1 = 10
cell B1 = "Name"
cell A2 = =A1+A1
cmd k1 = math_add(a=4, b=5) at 10,10
cmd k2 = math_multiply(b=3) at 60,10
pipe k1 -> k2.a
'''


class TestDialectRoundTrip(unittest.TestCase):

    def test_text_model_text_identity(self):
        m = D.parse(CANON)
        self.assertEqual(D.project(m), CANON)

    def test_model_semantics(self):
        m = D.parse(CANON)
        self.assertEqual(len(m['widgets']), 3)
        self.assertEqual(len(m['flows']), 3)
        btn = next(w for w in m['widgets'].values()
                   if w['name'] == 'save_btn')
        win = next(w for w in m['widgets'].values()
                   if w['name'] == 'main_win')
        self.assertEqual(btn['parent_id'], win['id'])
        self.assertEqual(win['layout_mode'], 'vbox')
        step = next(f for f in m['flows'].values() if f['name'] == 'step1')
        self.assertEqual(step['parent_scope'], 'doubler')
        dbl = next(f for f in m['flows'].values() if f['name'] == 'doubler')
        self.assertEqual(dbl['exit_points'][0]['expr'], 'input_value * 2')
        term = next(f for f in m['flows'].values() if f['name'] == 'on_save')
        self.assertTrue(any(p['name'] == 'is_entry' and p['value']
                            for p in term['properties']))
        self.assertEqual(m['cells'][(1, 0)],
                         {'kind': 'cell_formula', 'value': '=A1+A1'})
        k1 = next(c for c in m['cmds'].values() if c['name'] == 'k1')
        self.assertEqual({p['name']: p['value'] for p in k1['properties']},
                         {'a': 4, 'b': 5})
        self.assertEqual(m['cmd_edges'][0]['dst_param'], 'a')

    def test_double_round_trip_stability(self):
        once = D.project(D.parse(CANON))
        self.assertEqual(D.project(D.parse(once)), once)

    def test_parse_error_carries_line_number(self):
        bad = CANON + "wibble wobble\n"
        with self.assertRaises(D.DialectError) as cm:
            D.parse(bad)
        self.assertEqual(cm.exception.line_no,
                         len(CANON.splitlines()) + 1)

    def test_bad_indent_reported(self):
        with self.assertRaises(D.DialectError) as cm:
            D.parse('window w "x" at 0,0 size 10x10:\n   button b "y" at 0,0 size 5x5\n')
        self.assertEqual(cm.exception.line_no, 2)

    def test_gui_inside_flow_rejected(self):
        with self.assertRaises(D.DialectError):
            D.parse('process p "x" at 0,0 size 10x10:\n'
                    '    button b "y" at 0,0 size 5x5\n')

    def test_compiles_via_substrate(self):
        """Dialect model → words → compile_from_words: the full babel path."""
        gm = _load('ghost_meccano')
        m = D.parse('terminator hi "Hello" at 100,100 size 120x60 entry\n')
        words = list(gm.flow_symbols_to_meccano(m['flows'],
                                                m['flow_edges']).words)
        asm = gm.compile_from_words(words)
        self.assertIn('main:', asm)


class TestViewLogicHeadless(unittest.TestCase):
    """View modules import without tkinter; mode gating is pure logic."""

    def test_text_tab_mode_for(self):
        ttv = _load('text_tab_view')
        self.assertEqual(ttv.mode_for('prog.fc'), 'flowcode')
        self.assertEqual(ttv.mode_for('PROG.FC'), 'flowcode')
        self.assertEqual(ttv.mode_for('notes.md'), 'text')
        self.assertEqual(ttv.mode_for(None), 'text')

    def test_translator_view_imports_headless(self):
        trv = _load('translator_view')
        self.assertEqual([k for k, _ in trv.DIALECT_LABELS],
                         list(_load('flowcode_lingo_translate').DIALECTS))


class TestFileSystem(unittest.TestCase):

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.fs = FS.HostFileSystem(self.dir)

    def test_save_read_roundtrip(self):
        self.fs.save('a.txt', 'raining trits')
        self.assertEqual(self.fs.read('a.txt'), 'raining trits')

    def test_cwd_is_private_to_instance(self):
        import os as _os
        host_cwd = _os.getcwd()
        self.fs.mkdir('sub')
        self.fs.chdir('sub')
        self.assertEqual(_os.getcwd(), host_cwd)   # host untouched
        self.fs.save('b.txt', 'x')
        self.assertTrue(self.fs.exists('b.txt'))
        self.assertIn('b.txt', self.fs.list('.'))

    def test_copy_move_delete_touch(self):
        self.fs.save('a.txt', 'one')
        self.fs.copy('a.txt', 'b.txt')
        self.fs.move('b.txt', 'c.txt')
        self.assertFalse(self.fs.exists('b.txt'))
        self.assertEqual(self.fs.read('c.txt'), 'one')
        self.fs.touch('d.txt')
        self.assertTrue(self.fs.exists('d.txt'))
        self.fs.delete('d.txt')
        self.assertFalse(self.fs.exists('d.txt'))

    def test_binary_roundtrip(self):
        blob = bytes(range(256)) * 4          # decidedly not text
        self.fs.save_bytes('w.bin', blob)
        self.assertEqual(self.fs.read_bytes('w.bin'), blob)

    def test_append(self):
        self.fs.save('a.txt', 'ab')
        self.fs.append('a.txt', 'cd')
        self.assertEqual(self.fs.read('a.txt'), 'abcd')

    def test_native_stub_raises(self):
        with self.assertRaises(NotImplementedError):
            FS.NativeFileSystem().read('/anything')

    def test_registry(self):
        old = FS.get_fs()
        try:
            FS.set_fs(self.fs)
            self.assertIs(FS.get_fs(), self.fs)
        finally:
            FS.set_fs(old)


if __name__ == '__main__':
    unittest.main(verbosity=1)
