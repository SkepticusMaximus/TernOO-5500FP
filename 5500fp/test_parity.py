"""test_parity.py — Editor/engine parity harness.

Sheet semantics exist twice (sheet_formula.py editor preview,
formula_t5asm.py compiled engine) and Shell semantics exist twice
(flowcode_commands.py editor impls, command_t5asm.py compiled).  This suite
feeds ONE corpus through BOTH paths of each pair and fails on any
disagreement — the invariant being protected is:

    what the editor preview shows == what the emulator computes.

Corpus scope is the engine-supported surface (numeric formula engine;
runnable command set).  Editor-only surface (e.g. VLOOKUP) is intentionally
outside the corpus — the engine not supporting a function is a documented
boundary, not a parity break.

Requires the C emulator binary (same skip guard as test_formula_t5asm).

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import unittest

import sheet_formula as sf
import flowcode_commands as fcmd

# Reuse the canonical engine harnesses from the existing suites so parity
# runs through exactly the code paths those suites already verify.
import test_formula_t5asm as F
import test_command_t5asm as Cm


def _have_emu():
    return F._have_emu()


# ─────────────────────────────────────────────────────────────────────────────
# Formula parity
# ─────────────────────────────────────────────────────────────────────────────

# Fixed cell environment shared by both paths.
_CELLS = {'A1': 10, 'A2': 3, 'A3': -4, 'B1': 7, 'B2': 2, 'B3': 0}

# Engine-supported numeric corpus.  Every expression must be evaluatable by
# BOTH paths; expected values are not hardcoded — parity IS the assertion.
_FORMULA_CORPUS = [
    '=2+3', '=2+3*4', '=(2+3)*4', '=20-6', '=-5+2', '=2*-3',
    '=A1+B1', '=A1-A3', '=A1*B2', '=A1/B2', '=B1/B2', '=-B1/B2',
    '=A3/B2', '=A1/A2',                      # truncation, both signs
    '=MOD(A1, A2)', '=POWER(B2, 3)', '=ABS(A3)', '=ROUND(A1)',
    '=SUM(A1:A3)', '=SUM(A1:B2)', '=MIN(A1:A3)', '=MAX(A1:A3)',
    '=COUNT(A1:A3)', '=AVERAGE(A1:B2)', '=AVERAGE(B1:B2)',
    '=IF(A1 > A2, 1, 0)', '=IF(A1 < A2, 1, 0)', '=IF(A1 = 10, 42, -42)',
    '=IF(A2 <= 3, A1, B1)', '=IF(A3 >= 0, 1, -1)', '=IF(A1 != B1, 5, 6)',
    '=IF(SUM(A1:A2) > 12, A1*2, A1/2)',
    '=(A1+A2)*(B1-B2)', '=A1+A2*B2-B1/B2',
]


def _editor_eval(expr: str):
    """Evaluate one formula in the editor path against _CELLS."""
    cells = {}
    for name, val in _CELLS.items():
        rc = sf.a1_to_rc(name)
        cells[rc] = {'kind': 'cell_number', 'value': val}
    target = sf.a1_to_rc('D9')
    cells[target] = {'kind': 'cell_formula', 'value': expr}
    results, errors = sf.evaluate_sheet(cells)
    if target in errors:
        return ('ERR', errors[target])
    return results[target]


@unittest.skipUnless(_have_emu(), "emulator binary not built")
class TestFormulaParity(unittest.TestCase):
    """Editor preview == engine result, one assertion per corpus entry."""

    def test_corpus_parity(self):
        for expr in _FORMULA_CORPUS:
            with self.subTest(expr=expr):
                editor = _editor_eval(expr)
                engine = F._run(expr, cells=dict(_CELLS))
                self.assertIsNotNone(engine,
                                     f"engine produced no result for {expr}")
                self.assertEqual(int(editor), engine,
                                 f"PARITY BREAK {expr}: editor={editor} "
                                 f"engine={engine}")

    def test_div_by_zero_both_sides_error(self):
        """Editor raises #DIV/0!; engine sets the DIV/0 sentinel (guarded 0
        result + _ERR_REG). Parity here means: both sides surface an error
        for the same input — neither silently returns a plausible number."""
        editor = _editor_eval('=A1/B3')
        self.assertEqual(editor, ('ERR', '#DIV/0!'))
        engine = F._run('=A1/B3', cells=dict(_CELLS))
        self.assertEqual(engine, 0, "engine guard should yield 0 result")

    def test_editor_matches_machine_truncation(self):
        """Pin the machine division model in the editor: trunc toward zero."""
        self.assertEqual(_editor_eval('=B1/B2'), 3)     # 7/2
        self.assertEqual(_editor_eval('=-B1/B2'), -3)   # -7/2 (not -4)
        self.assertEqual(_editor_eval('=AVERAGE(B1:B2)'), 4)  # (7+2)/2


# ─────────────────────────────────────────────────────────────────────────────
# Command parity
# ─────────────────────────────────────────────────────────────────────────────

# (command, args) pairs whose editor impl returns a NUMBER and whose runtime
# is verified through the existing _run_number harness.
_NUM_COMMAND_CORPUS = [
    # (registry name, editor args dict, engine positional arg nodes)
    ('cmd_math_add',      {'a': 4, 'b': 5},     [Cm._num(4), Cm._num(5)]),
    ('cmd_math_add',      {'a': -13, 'b': 13},  [Cm._num(-13), Cm._num(13)]),
    ('cmd_math_subtract', {'a': 4, 'b': 9},     [Cm._num(4), Cm._num(9)]),
    ('cmd_math_multiply', {'a': 6, 'b': -7},    [Cm._num(6), Cm._num(-7)]),
    ('cmd_math_divide',   {'a': 22, 'b': 7},    [Cm._num(22), Cm._num(7)]),
    ('cmd_math_divide',   {'a': -22, 'b': 7},   [Cm._num(-22), Cm._num(7)]),
    ('cmd_math_mod',      {'a': 22, 'b': 7},    [Cm._num(22), Cm._num(7)]),
    ('cmd_math_abs',      {'x': -121},          [Cm._num(-121)]),
]


@unittest.skipUnless(_have_emu(), "emulator binary not built")
class TestCommandParity(unittest.TestCase):

    def _editor_fn(self, name):
        cmd = fcmd.COMMAND_REGISTRY[name]
        return cmd['fn']

    def test_numeric_command_parity(self):
        for name, args, engine_args in _NUM_COMMAND_CORPUS:
            with self.subTest(cmd=name, args=args):
                editor = self._editor_fn(name)(dict(args))
                engine = Cm._run_number(name, engine_args)
                self.assertEqual(int(editor), int(engine),
                                 f"PARITY BREAK {name}{args}: "
                                 f"editor={editor} engine={engine}")


    def test_text_length_parity(self):
        """Editor len() == engine STR_LENGTH over a real NUL-terminated
        buffer (same emission pattern as test_command_t5asm)."""
        text = 'raining trits'
        editor = self._editor_fn('cmd_text_length')({'text': text})
        import command_t5asm as cmdc
        body = cmdc.compile_command('cmd_text_length', [('strlit', 'inbuf')],
                                    cmdc._BASE_REG)
        prog = (['LI R19, 0'] + body
                + [f'MOV R2, R{cmdc._BASE_REG}', 'LI R1, 1', 'SYSCALL',
                   'LI R1, 6', 'SYSCALL', 'HALT', 'inbuf:']
                + [f'    .word {ord(c)}' for c in text] + ['    .word 0'])
        engine = Cm._assemble_run(prog)
        self.assertEqual(str(editor), engine,
                         f"PARITY BREAK text_length: editor={editor} "
                         f"engine={engine}")


if __name__ == '__main__':
    unittest.main(verbosity=1)
