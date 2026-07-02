"""test_repl.py — Shell REPL engine.

Registry commands run on the real emulator through the real compiler (the
REPL is the visual Shell in text form); fs commands run through the
FileSystem abstraction against a temp directory.

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


R = _load('flowcode_repl')
FS = _load('filesystem')

_EMU_OK = os.path.exists(R._EMU) and os.access(R._EMU, os.X_OK)


class TestFsCommands(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.repl = R.Repl(fs=FS.HostFileSystem(self.dir))

    def test_pwd_ls_touch(self):
        self.assertEqual(self.repl.execute('pwd'), self.dir)
        self.assertEqual(self.repl.execute('touch a.txt && ls'), 'a.txt')

    def test_echo_redirect_cat_pipe_free(self):
        self.repl.execute('echo "raining trits" > note.txt')
        self.assertEqual(self.repl.execute('cat note.txt'), 'raining trits')
        self.repl.execute('echo "more" >> note.txt')
        self.assertEqual(self.repl.execute('cat note.txt'),
                         'raining trits\nmore')

    def test_cd_is_sandboxed(self):
        host = os.getcwd()
        self.repl.execute('mkdir sub && cd sub && touch in_sub.txt')
        self.assertEqual(os.getcwd(), host)
        self.assertTrue(os.path.exists(os.path.join(self.dir, 'sub',
                                                    'in_sub.txt')))

    def test_cp_mv_rm(self):
        self.repl.execute('echo "x" > a && cp a b && mv b c && rm a')
        self.assertEqual(self.repl.execute('ls'), 'c')

    def test_error_short_circuits_and(self):
        out = self.repl.execute('cat missing.txt && touch never.txt')
        self.assertIn('error:', out)
        self.assertNotIn('never.txt', self.repl.execute('ls'))

    def test_history(self):
        self.repl.execute('pwd')
        self.repl.execute('ls')
        h = self.repl.execute('history')
        self.assertIn('1  pwd', h)
        self.assertIn('2  ls', h)

    def test_help_lists_both_families(self):
        h = self.repl.execute('help')
        self.assertIn('math_add', h)
        self.assertIn('run', h)


@unittest.skipUnless(_EMU_OK, "emulator binary not built")
class TestRegistryCommands(unittest.TestCase):
    def setUp(self):
        self.repl = R.Repl(fs=FS.HostFileSystem(tempfile.mkdtemp()))

    def test_single_call(self):
        self.assertEqual(self.repl.execute('math_add(a=4, b=5)'), '9')

    def test_pipe_default_param(self):
        self.assertEqual(
            self.repl.execute('math_add(a=4, b=5) | math_multiply(b=3)'),
            '27')

    def test_pipe_explicit_param(self):
        self.assertEqual(
            self.repl.execute('math_add(a=20, b=2) | math_divide(a=66).b'),
            '3')

    def test_text_chain(self):
        self.assertEqual(
            self.repl.execute('text_split("a,b,c", ",") | list_count'), '3')

    def test_bareword_env_roundtrip(self):
        """env values are numeric at runtime (v1 substrate boundary); env
        state persists across && because a line compiles to ONE program."""
        self.assertEqual(self.repl.execute('env_set N "7" && env_get N'),
                         '7')

    def test_mixed_fs_and_registry_interleave(self):
        out = self.repl.execute('touch x.txt && math_add(a=1, b=1) && ls')
        self.assertEqual(out, '2\nx.txt')

    def test_unknown_command(self):
        self.assertIn('error:', self.repl.execute('frobnicate(x=1)'))

    def test_capture_last(self):
        self.repl.execute('math_add(a=1, b=2) | math_multiply(b=10)')
        cmds, edges = self.repl.capture_last()
        self.assertEqual(len(cmds), 2)
        self.assertEqual(edges[0]['dst_param'], 'a')
        kinds = [c['kind'] for c in cmds.values()]
        self.assertEqual(kinds, ['cmd_math_add', 'cmd_math_multiply'])

    def test_run_program_ascii(self):
        """`run` executes a .t5asm through the abstraction: rung 1 of the
        session layer."""
        d = self.repl.fs.getcwd()
        prog = os.path.join(d, 'hello.t5asm')
        with open(prog, 'w') as f:
            f.write('main:\n    LI R2, 42\n    LI R1, 1\n    SYSCALL\n'
                    '    LI R1, 6\n    SYSCALL\n    HALT\n')
        out = self.repl.execute('run hello.t5asm')
        self.assertIn('42', out)


if __name__ == '__main__':
    unittest.main(verbosity=1)
