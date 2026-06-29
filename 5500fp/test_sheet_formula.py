#!/usr/bin/env python3
"""Stage 8-3 — formula engine tests (headless).

Parser, dependency extraction, whole-sheet evaluation (static + cell→cell
dynamic), builtins, ranges, and circular-dependency detection.

Run:
    cd 5500fp && python3 -m unittest test_sheet_formula
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sheet_formula as sf


def _cell(kind, value, name=None):
    d = {'kind': kind, 'value': value}
    if name:
        d['name'] = name
    return d


def _evalsheet(grid):
    """grid: {(r,c): (kind, value[, name])} → (results, errors)."""
    cells = {}
    for rc, spec in grid.items():
        cells[rc] = _cell(*spec)
    return sf.evaluate_sheet(cells)


class TestA1(unittest.TestCase):
    def test_a1_to_rc(self):
        self.assertEqual(sf.a1_to_rc('A1'), (0, 0))
        self.assertEqual(sf.a1_to_rc('B3'), (2, 1))
        self.assertEqual(sf.a1_to_rc('AA12'), (11, 26))
        self.assertIsNone(sf.a1_to_rc('cell_x'))

    def test_rc_to_a1(self):
        self.assertEqual(sf.rc_to_a1(0, 0), 'A1')
        self.assertEqual(sf.rc_to_a1(2, 1), 'B3')


class TestParse(unittest.TestCase):
    def test_parse_arith(self):
        self.assertEqual(sf.parse('2+3'), ('bin', '+', ('num', 2), ('num', 3)))

    def test_precedence(self):
        # 2+3*4 → 2 + (3*4)
        ast = sf.parse('2+3*4')
        self.assertEqual(ast[0], 'bin'); self.assertEqual(ast[1], '+')
        self.assertEqual(ast[3][1], '*')

    def test_refs_and_range(self):
        self.assertEqual(sf.extract_refs(sf.parse('A1+B1')), {'A1', 'B1'})
        self.assertEqual(sf.extract_refs(sf.parse('SUM(A1:A3)')),
                         {'A1', 'A2', 'A3'})

    def test_named_ref(self):
        self.assertEqual(sf.extract_refs(sf.parse('cell_total+1')), {'cell_total'})


class TestStaticEval(unittest.TestCase):
    def test_constant(self):
        res, err = _evalsheet({(0, 0): ('cell_formula', '=2+3')})
        self.assertEqual(res[(0, 0)], 5)
        self.assertEqual(err, {})

    def test_precedence_eval(self):
        res, _ = _evalsheet({(0, 0): ('cell_formula', '=2+3*4')})
        self.assertEqual(res[(0, 0)], 14)

    def test_div_by_zero(self):
        res, err = _evalsheet({(0, 0): ('cell_formula', '=1/0')})
        self.assertEqual(err[(0, 0)], '#DIV/0!')


class TestCellRefEval(unittest.TestCase):
    def test_a1_refs(self):
        res, _ = _evalsheet({
            (0, 0): ('cell_value', '10'),     # A1
            (0, 1): ('cell_value', '20'),     # B1
            (1, 0): ('cell_formula', '=A1+B1')})  # A2
        self.assertEqual(res[(1, 0)], 30)

    def test_update_on_change(self):
        grid = {(0, 0): ('cell_value', '10'),
                (1, 0): ('cell_formula', '=A1*2')}
        res, _ = _evalsheet(grid)
        self.assertEqual(res[(1, 0)], 20)
        grid[(0, 0)] = ('cell_value', '15')   # change A1
        res, _ = _evalsheet(grid)
        self.assertEqual(res[(1, 0)], 30)     # recomputed

    def test_named_ref_eval(self):
        res, _ = _evalsheet({
            (0, 0): ('cell_value', '7', 'cell_total'),
            (1, 0): ('cell_formula', '=cell_total+3')})
        self.assertEqual(res[(1, 0)], 10)

    def test_chain(self):
        res, _ = _evalsheet({
            (0, 0): ('cell_value', '2'),
            (1, 0): ('cell_formula', '=A1*3'),    # A2 = 6
            (2, 0): ('cell_formula', '=A2+A1')})  # A3 = 8
        self.assertEqual(res[(2, 0)], 8)


class TestBuiltins(unittest.TestCase):
    def test_sum_range(self):
        grid = {(r, 0): ('cell_value', str(r + 1)) for r in range(5)}  # A1..A5 = 1..5
        grid[(5, 0)] = ('cell_formula', '=SUM(A1:A5)')
        res, _ = _evalsheet(grid)
        self.assertEqual(res[(5, 0)], 15)

    def test_if(self):
        res, _ = _evalsheet({(0, 0): ('cell_value', '5'),
                             (1, 0): ('cell_formula', '=IF(A1>0, "pos", "neg")')})
        self.assertEqual(res[(1, 0)], 'pos')
        res, _ = _evalsheet({(0, 0): ('cell_value', '-3'),
                             (1, 0): ('cell_formula', '=IF(A1>0, "pos", "neg")')})
        self.assertEqual(res[(1, 0)], 'neg')

    def test_min_max_avg_count_abs_round(self):
        grid = {(0, 0): ('cell_value', '4'), (0, 1): ('cell_value', '8')}
        for f, exp in [('=MIN(A1:B1)', 4), ('=MAX(A1:B1)', 8),
                       ('=AVERAGE(A1:B1)', 6), ('=COUNT(A1:B1)', 2),
                       ('=ABS(0-9)', 9), ('=ROUND(3.14159, 2)', 3.14)]:
            g = dict(grid); g[(2, 0)] = ('cell_formula', f)
            res, err = _evalsheet(g)
            self.assertEqual(res[(2, 0)], exp, f)

    def test_logical(self):
        res, _ = _evalsheet({(0, 0): ('cell_formula', '=AND(1>0, 2>1)')})
        self.assertTrue if False else self.assertEqual(res[(0, 0)], True)
        res, _ = _evalsheet({(0, 0): ('cell_formula', '=NOT(1>0)')})
        self.assertEqual(res[(0, 0)], False)


class TestCycles(unittest.TestCase):
    def test_self_cycle(self):
        res, err = _evalsheet({(0, 0): ('cell_formula', '=A1+1')})
        self.assertEqual(err.get((0, 0)), '#CYCLE!')

    def test_mutual_cycle(self):
        res, err = _evalsheet({
            (0, 0): ('cell_formula', '=B1+1'),     # A1
            (0, 1): ('cell_formula', '=A1+1')})    # B1
        self.assertTrue(err.get((0, 0)) == '#CYCLE!' or err.get((0, 1)) == '#CYCLE!')

    def test_no_false_cycle(self):
        res, err = _evalsheet({
            (0, 0): ('cell_value', '1'),
            (1, 0): ('cell_formula', '=A1+1'),
            (2, 0): ('cell_formula', '=A2+1')})
        self.assertEqual(err, {})
        self.assertEqual(res[(2, 0)], 3)


class TestNameError(unittest.TestCase):
    def test_unknown_function(self):
        res, err = _evalsheet({(0, 0): ('cell_formula', '=BOGUS(1)')})
        self.assertEqual(err.get((0, 0)), '#NAME? BOGUS')


if __name__ == '__main__':
    unittest.main()
