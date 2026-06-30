#!/usr/bin/env python3
"""AST→t5asm compiler tests — compile formulas and EXECUTE them on the emulator.

Each test compiles an expression to t5asm that computes the value into R40,
prints it as a decimal integer (SYS_PRINT_INT), and halts; the emulator runs it
and we assert on stdout. This proves the emitted arithmetic actually executes
on the engine, not just that it parses.

Skipped automatically if the emulator binary isn't built.

Run:
    cd 5500fp && python3 -m unittest test_formula_t5asm
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib.util as _ilu
_ft_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'formula_t5asm.py')
_ft_spec = _ilu.spec_from_file_location('formula_t5asm', _ft_path)
ft = _ilu.module_from_spec(_ft_spec); _ft_spec.loader.exec_module(ft)
sf = ft.sheet_formula

_EMU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'NASM-TernOO-5500FP-Emulator', 'c_emulator', '5500fp')


def _have_emu():
    return os.path.isfile(_EMU) and os.access(_EMU, os.X_OK)


def _compile_program(expr, cells=None, widgets=None):
    cells = cells or {}
    widgets = widgets or {}

    def resolver(ref):
        if isinstance(ref, tuple) and ref[0] == 'widget':
            return f"tw_{ref[1]}" if ref[1] in widgets else None
        if ref in cells:
            return f"tc_{ref}"
        # bare A1 with no provided value → unknown
        return None

    ast = sf.parse(expr[1:] if expr.startswith('=') else expr)
    body = ft.compile_ast(ast, ft._BASE_REG, resolver)
    lines = ['main:']
    lines += body
    lines += [
        f'    MOV  R2, R{ft._BASE_REG}',
        '    LI   R1, 1          ; SYS_PRINT_INT',
        '    SYSCALL',
        '    LI   R1, 6          ; SYS_PRINT_NL',
        '    SYSCALL',
        '    HALT',
        '',
    ]
    for name, val in cells.items():
        lines.append(f'tc_{name}:')
        lines.append(f'    .word {int(val)}')
    for name, val in widgets.items():
        lines.append(f'tw_{name}:')
        lines.append(f'    .word {int(val)}')
    return '\n'.join(lines) + '\n'


def _run(expr, cells=None, widgets=None):
    asm = _compile_program(expr, cells, widgets)
    with tempfile.NamedTemporaryFile('w', suffix='.t5asm', delete=False) as f:
        f.write(asm); path = f.name
    try:
        out = subprocess.run([_EMU, '--run', path], capture_output=True,
                             text=True, timeout=15)
        # The program prints its result via SYS_PRINT_INT on its own line;
        # the emulator wraps it in a banner + "[N cycles]" footer. Find the
        # pure-integer line.
        import re
        for line in out.stdout.splitlines():
            if re.fullmatch(r'-?\d+', line.strip()):
                return int(line.strip())
        return None
    finally:
        os.unlink(path)


@unittest.skipUnless(_have_emu(), "emulator binary not built")
class TestArithmeticOnEngine(unittest.TestCase):
    def test_const(self):
        self.assertEqual(_run('=2+3'), 5)

    def test_precedence(self):
        self.assertEqual(_run('=2+3*4'), 14)

    def test_sub_mul_div(self):
        self.assertEqual(_run('=20-6'), 14)
        self.assertEqual(_run('=6*7'), 42)
        self.assertEqual(_run('=100/4'), 25)

    def test_div_by_zero_guarded(self):
        self.assertEqual(_run('=5/0'), 0)   # guarded → 0, no crash

    def test_unary_minus(self):
        self.assertEqual(_run('=0-(3+4)'), -7)
        self.assertEqual(_run('=-9+2'), -7)

    def test_parens(self):
        self.assertEqual(_run('=(2+3)*4'), 20)


@unittest.skipUnless(_have_emu(), "emulator binary not built")
class TestRefsOnEngine(unittest.TestCase):
    def test_cell_refs(self):
        self.assertEqual(_run('=A1+B1', cells={'A1': 10, 'B1': 20}), 30)

    def test_cell_arith(self):
        self.assertEqual(_run('=A1*A2', cells={'A1': 6, 'A2': 7}), 42)

    def test_widget_ref(self):
        self.assertEqual(_run('=WIDGET("slider").value + 1',
                              widgets={'slider': 41}), 42)

    def test_unknown_name_is_zero(self):
        self.assertEqual(_run('=ghost + 5', cells={}), 5)   # #NAME? ref → 0


@unittest.skipUnless(_have_emu(), "emulator binary not built")
class TestComparisonsAndIf(unittest.TestCase):
    def test_compare(self):
        self.assertEqual(_run('=5>3'), 1)
        self.assertEqual(_run('=5<3'), 0)
        self.assertEqual(_run('=4>=4'), 1)
        self.assertEqual(_run('=4<=3'), 0)
        self.assertEqual(_run('=7=7'), 1)
        self.assertEqual(_run('=7!=7'), 0)

    def test_if(self):
        self.assertEqual(_run('=IF(A1>0, 100, 200)', cells={'A1': 5}), 100)
        self.assertEqual(_run('=IF(A1>0, 100, 200)', cells={'A1': -5}), 200)

    def test_if_nested(self):
        self.assertEqual(_run('=IF(A1>10, 1, IF(A1>5, 2, 3))',
                              cells={'A1': 7}), 2)


@unittest.skipUnless(_have_emu(), "emulator binary not built")
class TestFunctionsOnEngine(unittest.TestCase):
    def _range(self):
        return {'A1': 1, 'A2': 2, 'A3': 3, 'A4': 4, 'A5': 5}

    def test_sum(self):
        self.assertEqual(_run('=SUM(A1:A5)', cells=self._range()), 15)

    def test_min_max(self):
        self.assertEqual(_run('=MIN(A1:A5)', cells=self._range()), 1)
        self.assertEqual(_run('=MAX(A1:A5)', cells=self._range()), 5)

    def test_average_count(self):
        self.assertEqual(_run('=AVERAGE(A1:A5)', cells=self._range()), 3)
        self.assertEqual(_run('=COUNT(A1:A5)', cells=self._range()), 5)

    def test_abs_mod_power(self):
        self.assertEqual(_run('=ABS(0-9)'), 9)
        self.assertEqual(_run('=MOD(17, 5)'), 2)
        self.assertEqual(_run('=POWER(2, 10)'), 1024)


class TestCompilePure(unittest.TestCase):
    """Structural checks that don't need the emulator."""

    def test_emits_add(self):
        lines = ft.compile_ast(sf.parse('A1+B1'), ft._BASE_REG,
                               lambda r: f'tc_{r}' if r in ('A1', 'B1') else None)
        self.assertTrue(any(f'ADD  R{ft._BASE_REG}' in l for l in lines))
        self.assertTrue(any('LDW' in l for l in lines))

    def test_range_unrolls(self):
        lines = ft.compile_ast(sf.parse('SUM(A1:A3)'), ft._BASE_REG, lambda r: f'tc_{r}')
        self.assertEqual(sum('ADD' in l for l in lines), 2)   # 3 terms → 2 adds


if __name__ == '__main__':
    unittest.main()
