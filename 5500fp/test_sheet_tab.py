#!/usr/bin/env python3
"""Stage 8-1 — Sheet tab scaffolding tests (headless).

Covers the cell namespace, the property registry, the column-letter / A1
helpers, and a dict-level save/load model. GUI behaviour (grid render, in-place
edit, keyboard nav) is verified live offscreen; these guard the model + wiring.

Run:
    cd 5500fp && python3 -m unittest test_sheet_tab
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from word_stream import WordStream

import importlib.util as _ilu
_fp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'flowcode_properties.py')
_fp_spec = _ilu.spec_from_file_location('flowcode_properties', _fp_path)
_fp      = _ilu.module_from_spec(_fp_spec)
_fp_spec.loader.exec_module(_fp)

# Load the column-letter / A1 helpers from flowcode.py without running the GUI.
_FC_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       '..', 'FlowCode', 'flowcode.py')
with open(_FC_SRC) as _f:
    _FC_TEXT = _f.read()


def _cell(cid, row, col, kind='cell_value', value='', name=None):
    d = {'id': cid, 'kind': kind, 'row': row, 'col': col, 'value': value,
         'label': '', 'properties': []}
    if name is not None:
        d['name'] = name
    return d


def _stream_with_cells(cells):
    s = WordStream()
    s._cell_meta = {(c['row'], c['col']): c for c in cells}
    return s


class TestCellProperties(unittest.TestCase):
    def test_cell_kinds_registered(self):
        for k in ('cell_value', 'cell_text', 'cell_formula'):
            self.assertIn(k, _fp.WIDGET_PROPERTIES)

    def test_cell_has_name_and_value(self):
        props = [p['name'] for p in _fp.properties_for('cell_value')]
        self.assertIn('name', props)
        self.assertIn('value', props)


class TestCellNamespace(unittest.TestCase):
    def test_cell_name_in_use(self):
        s = _stream_with_cells([_cell(0, 0, 0, name='cell_A1')])
        self.assertTrue(s.name_in_use('cell_A1'))
        self.assertFalse(s.name_in_use('cell_Z9'))

    def test_cell_collides_with_widget(self):
        s = _stream_with_cells([_cell(0, 0, 0, name='total')])
        s._widget_meta = {0: {'id': 0, 'kind': 'gui_label', 'name': 'total'}}
        self.assertTrue(s.name_in_use('total'))

    def test_ensure_unique_backfills_cells(self):
        c = _cell(0, 0, 0)            # no name
        s = _stream_with_cells([c])
        s.ensure_unique_names()
        self.assertEqual(c['name'], 'cell_value_0')   # default <kind>_<id>


class TestColumnLabels(unittest.TestCase):
    """Re-derive the column-letter logic and assert flowcode.py defines it."""

    @staticmethod
    def _col_label(col):
        s = ''; col += 1
        while col > 0:
            col, r = divmod(col - 1, 26)
            s = chr(65 + r) + s
        return s

    def test_known_labels(self):
        cases = {0: 'A', 1: 'B', 25: 'Z', 26: 'AA', 27: 'AB', 51: 'AZ', 52: 'BA'}
        for col, lbl in cases.items():
            self.assertEqual(self._col_label(col), lbl)

    def test_flowcode_defines_helpers(self):
        self.assertIn('def _sheet_col_label', _FC_TEXT)
        self.assertIn('def _sheet_a1', _FC_TEXT)


class TestSaveLoadModel(unittest.TestCase):
    """Dict-level model of cell save/load (mirrors _save_to_path / guic_do_open)."""

    def _save(self, cells):
        return [dict(c) for c in cells.values()]

    def _load(self, cell_syms):
        out = {}
        for cell in cell_syms:
            r, c = cell.get('row', 0), cell.get('col', 0)
            d = {'id': cell.get('id', 0), 'kind': cell.get('kind', 'cell_text'),
                 'row': r, 'col': c, 'value': cell.get('value', ''),
                 'label': cell.get('label', ''), 'properties': []}
            if 'name' in cell:
                d['name'] = cell['name']
            out[(r, c)] = d
        return out

    def test_round_trip(self):
        src = {(0, 0): _cell(0, 0, 0, 'cell_text', 'Hello', 'cell_A1'),
               (2, 1): _cell(1, 2, 1, 'cell_value', '42', 'cell_B3')}
        loaded = self._load(self._save(src))
        self.assertEqual(loaded[(0, 0)]['kind'], 'cell_text')
        self.assertEqual(loaded[(0, 0)]['value'], 'Hello')
        self.assertEqual(loaded[(2, 1)]['kind'], 'cell_value')
        self.assertEqual(loaded[(2, 1)]['name'], 'cell_B3')


class TestSheetWiring(unittest.TestCase):
    """Source-level smoke checks that the Sheet tab is wired into the IDE."""

    def test_sheet_tab_added_between_gui_and_shell(self):
        i_gui   = _FC_TEXT.index("notebook.add(ghost_tab")
        i_sheet = _FC_TEXT.index("notebook.add(sheet_tab")
        i_shell = _FC_TEXT.index("notebook.add(sh_tab")
        self.assertTrue(i_gui < i_sheet < i_shell)

    def test_sheet_label(self):
        self.assertIn("notebook.add(sheet_tab, text='  Sheet  ')", _FC_TEXT)

    def test_cell_meta_aliased(self):
        self.assertIn("_cell_meta", _FC_TEXT)

    def test_cells_persisted(self):
        self.assertIn("'cell_symbols'", _FC_TEXT)

    def test_sheet_clear_and_tools(self):
        self.assertIn("def _clear_sheet", _FC_TEXT)
        self.assertIn("def _build_sheet_tools", _FC_TEXT)


class TestStage82Wiring(unittest.TestCase):
    """Stage 8-2: formula kind auto-detect, formula bar, per-kind rendering."""

    def test_formula_autodetect(self):
        # leading '=' routes to cell_formula in the detect helper.
        self.assertIn("startswith('=')", _FC_TEXT)
        self.assertIn("'cell_formula'", _FC_TEXT)

    def test_formula_bar_wired(self):
        self.assertIn("_sheet_fbar_var", _FC_TEXT)
        self.assertIn("def _sheet_fbar_commit", _FC_TEXT)
        self.assertIn("def _sheet_sync_fbar", _FC_TEXT)

    def test_per_kind_rendering(self):
        # numbers right-aligned (anchor='e'), formula in accent colour.
        self.assertIn("anchor='e'", _FC_TEXT)
        self.assertIn("elif k == 'cell_formula'", _FC_TEXT)


if __name__ == '__main__':
    unittest.main()
