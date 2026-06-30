#!/usr/bin/env python3
"""Stage 9-1A — Shell command registry tests (headless).

Run:
    cd 5500fp && python3 -m unittest test_flowcode_commands
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util as _ilu
_p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flowcode_commands.py')
_s = _ilu.spec_from_file_location('flowcode_commands', _p)
fc = _ilu.module_from_spec(_s); _s.loader.exec_module(fc)


def run(_cmd, **args):
    return fc.run_command(_cmd, args)


class TestText(unittest.TestCase):
    def test_upper_lower_trim_len(self):
        self.assertEqual(run('cmd_text_upper', text='hi'), 'HI')
        self.assertEqual(run('cmd_text_lower', text='HI'), 'hi')
        self.assertEqual(run('cmd_text_trim', text='  x  '), 'x')
        self.assertEqual(run('cmd_text_length', text='hello'), 5)

    def test_replace(self):
        self.assertEqual(run('cmd_text_replace', text='aAa', find='a', **{'with': 'b'},
                             case_sensitive=True), 'bAb')
        self.assertEqual(run('cmd_text_replace', text='aAa', find='a', **{'with': 'b'},
                             case_sensitive=False), 'bbb')

    def test_split_join(self):
        self.assertEqual(run('cmd_text_split', text='a,b,c', delimiter=','),
                         ['a', 'b', 'c'])
        self.assertEqual(run('cmd_text_join', list='a,b,c', separator='-'), 'a-b-c')

    def test_format(self):
        self.assertEqual(run('cmd_text_format', template='Hi {0}', args='Stevo'),
                         'Hi Stevo')


class TestMath(unittest.TestCase):
    def test_arith(self):
        self.assertEqual(run('cmd_math_add', a='2', b='3'), 5)
        self.assertEqual(run('cmd_math_subtract', a='5', b='2'), 3)
        self.assertEqual(run('cmd_math_multiply', a='4', b='3'), 12)
        self.assertEqual(run('cmd_math_divide', a='10', b='2'), 5)
        self.assertEqual(run('cmd_math_mod', a='7', b='3'), 1)
        self.assertEqual(run('cmd_math_abs', x='-9'), 9)
        self.assertEqual(run('cmd_math_power', base='2', exp='8'), 256)
        self.assertEqual(run('cmd_math_round', x='3.14159', places='2'), 3.14)

    def test_div_zero(self):
        self.assertEqual(run('cmd_math_divide', a='1', b='0'), '#DIV/0!')


class TestList(unittest.TestCase):
    def test_list_ops(self):
        self.assertEqual(run('cmd_list_count', list='a,b,c'), 3)
        self.assertEqual(run('cmd_list_first', list='a,b,c'), 'a')
        self.assertEqual(run('cmd_list_last', list='a,b,c'), 'c')
        self.assertEqual(run('cmd_list_reverse', list='a,b,c'), ['c', 'b', 'a'])
        self.assertEqual(run('cmd_list_sort', list='c,a,b', ascending=True),
                         ['a', 'b', 'c'])
        self.assertEqual(run('cmd_list_sort', list='a,b,c', ascending=False),
                         ['c', 'b', 'a'])
        self.assertEqual(run('cmd_list_unique', list='a,b,a,c,b'), ['a', 'b', 'c'])


class TestRegistry(unittest.TestCase):
    def test_unknown(self):
        self.assertEqual(run('cmd_bogus', x='1'), '#CMD? cmd_bogus')

    def test_registry_shape(self):
        for name, spec in fc.COMMAND_REGISTRY.items():
            self.assertIn('desc', spec)
            self.assertIn('params', spec)
            self.assertIn('output', spec)
            self.assertTrue(callable(spec['fn']))

    def test_counts(self):
        names = fc.command_names()
        self.assertEqual(sum(n.startswith('cmd_text_') for n in names), 8)
        self.assertEqual(sum(n.startswith('cmd_math_') for n in names), 8)
        self.assertEqual(sum(n.startswith('cmd_list_') for n in names), 6)
        self.assertEqual(sum(n.startswith('cmd_env_') for n in names), 3)
        self.assertEqual(sum(n.startswith('cmd_ctl_') for n in names), 3)


class TestEnvControl(unittest.TestCase):
    """Stage 9-1B: env (in-program) + control commands, editor-side."""

    def test_env_roundtrip(self):
        run('cmd_env_set', name='greeting', value='hi')
        self.assertEqual(run('cmd_env_get', name='greeting'), 'hi')
        self.assertTrue(run('cmd_env_exists', name='greeting'))
        self.assertFalse(run('cmd_env_exists', name='nope'))

    def test_ctl_if(self):
        self.assertEqual(run('cmd_ctl_if', condition='1', then_value='Y',
                             else_value='N'), 'Y')
        self.assertEqual(run('cmd_ctl_if', condition='0', then_value='Y',
                             else_value='N'), 'N')

    def test_ctl_repeat(self):
        self.assertEqual(run('cmd_ctl_repeat', count='3', value='x'),
                         ['x', 'x', 'x'])


if __name__ == '__main__':
    unittest.main()
