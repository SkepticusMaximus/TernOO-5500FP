"""test_compile_from_words.py — grammar v2 closure test.

The whitepaper's central claim, made mechanical: a program compiled from
its WORD STREAM must be identical to the same program compiled from the
editor's dicts.  If this suite is green, "the word stream is the program"
is present tense.

Path A: dicts → compile_wordstream_to_t5asm
Path B: dicts → (bridges + model-word encoders) → words
              → rehydrate_wordstream → compile_wordstream_to_t5asm

The assertion is t5asm equality modulo the generated-timestamp header.

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import importlib.util as _ilu
import os
import re
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gm = _load('ghost_meccano')
ws_mod = _load('word_stream')
C = _load('compile_to_t5asm')
sig = _load('flowcode_signals')


def _strip_header(asm: str) -> str:
    """Normalize for comparison: drop volatile comments; canonicalize
    id-bearing labels (ids are session artifacts — names are identity —
    so equality is 'identical modulo consistent id renumbering')."""
    body = '\n'.join(l for l in asm.splitlines()
                     if not re.match(r'\s*;', l)).strip()
    mapping = {}
    def _canon(m):
        key = (m.group(1), m.group(2))
        if key not in mapping:
            mapping[key] = f"{m.group(1)}ID{len(mapping)}"
        return mapping[key]
    body = re.sub(r'\b(command_|wstr_|skip_wid_|wid_|widget_|state_cmd_)(\d+)',
                  _canon, body)
    return re.sub(r'#\d+', '#ID', body)


def _dict_stream(widgets, flows, cells, cmds, cmd_edges):
    s = ws_mod.WordStream([])
    s._widget_meta = widgets
    s._flow_meta = flows
    s._cell_meta = cells
    s._cmd_meta = cmds
    s._cmd_edges = cmd_edges
    sig.materialize_auto_wired_bindings(s)
    return s


def _word_stream(widgets, flows, cells, cmds, cmd_edges, flow_edges=None):
    words = []
    if widgets:
        words += list(gm.ghost_to_meccano(widgets, []).words)
    if flows:
        words += list(gm.flow_symbols_to_meccano(flows, flow_edges or []).words)
    words += gm.cells_to_model_words(cells)
    words += gm.cmds_to_model_words(cmds)
    words += gm.edges_to_model_words(flow_edges or [], flows,
                                     cmd_edges, cmds)
    return words


class TestCompileFromWords(unittest.TestCase):

    def _both_paths(self, widgets, flows, cells, cmds, cmd_edges,
                    flow_edges=None):
        a = C.compile_wordstream_to_t5asm(
            _dict_stream(dict(widgets), dict(flows), dict(cells),
                         dict(cmds), list(cmd_edges)))
        words = _word_stream(widgets, flows, cells, cmds, cmd_edges,
                             flow_edges)
        b = gm.compile_from_words(words)
        return _strip_header(a), _strip_header(b)

    def test_flow_print_program(self):
        """Minimal Phase 7b-1 program: one entry terminator."""
        flows = {1: {'id': 1, 'kind': 'flow_terminator',
                           'x': 100, 'y': 100, 'w': 120, 'h': 60,
                           'label': 'Hi Stevo', 'name': 'hello',
                           'properties': [{'name': 'is_entry', 'value': True}]}}
        a, b = self._both_paths({}, flows, {}, {}, [])
        self.assertEqual(a, b)

    def test_gui_program_with_binding(self):
        """GUI window + button auto-wired by name to a flow terminator —
        exercises geometry, layout, containment, name-materialized
        bindings."""
        widgets = {
            1: {'id': 1, 'kind': 'gui_window', 'x': 200, 'y': 150,
                    'w': 400, 'h': 300, 'label': 'Main', 'name': 'main_win',
                    'layout_mode': 'absolute', 'parent_id': None,
                    'properties': [], 'signal_ids': {}},
            2: {'id': 2, 'kind': 'gui_button', 'x': 200, 'y': 200,
                    'w': 120, 'h': 60, 'label': 'Go', 'name': 'go',
                    'layout_mode': 'absolute', 'parent_id': 1,
                    'properties': [], 'signal_ids': {}},
        }
        flows = {3: {'id': 3, 'kind': 'flow_terminator', 'x': 500,
                       'y': 400, 'w': 120, 'h': 60, 'label': 'clicked',
                       'name': 'on_go_clicked', 'properties': []}}
        a, b = self._both_paths(widgets, flows, {}, {}, [])
        self.assertEqual(a, b)

    def test_sheet_cells_static_and_formula(self):
        cells = {(0, 0): {'kind': 'cell_number', 'value': 7},
                 (0, 1): {'kind': 'cell_number', 'value': 2},
                 (1, 0): {'kind': 'cell_formula', 'value': '=A1*B1+3'}}
        a, b = self._both_paths({}, {}, cells, {}, [])
        self.assertEqual(a, b)

    def test_shell_pipeline_with_typed_pipe(self):
        cmds = {11: {'id': 11, 'kind': 'cmd_math_add', 'x': 10, 'y': 10,
                       'params': {'a': 4, 'b': 5}},
                12: {'id': 12, 'kind': 'cmd_math_multiply', 'x': 60,
                       'y': 10, 'params': {'b': 3}}}
        edges = [{'src': 11, 'dst': 12, 'dst_param': 'a'}]
        a, b = self._both_paths({}, {}, {}, cmds, edges)
        self.assertEqual(a, b)

    def test_ports_and_scope_round_trip_into_stream(self):
        """Container with pocket scope + named ports: rehydrated stream
        must carry parent_scope / entry_points / exit_points verbatim."""
        flows = {
            1: {'id': 1, 'kind': 'flow_process', 'x': 300, 'y': 200,
                    'w': 120, 'h': 60, 'label': 'Doubler', 'name': 'doubler',
                    'properties': [],
                    'entry_points': [{'name': 'input_value',
                                      'type': 'number', 'description': 'in'}],
                    'exit_points': [{'name': 'output_value',
                                     'type': 'number',
                                     'expr': 'input_value * 2',
                                     'description': ''}]},
            2: {'id': 2, 'kind': 'flow_process', 'x': 320,
                      'y': 220, 'w': 120, 'h': 60, 'label': 'step',
                      'name': 'step1', 'parent_scope': 'doubler',
                      'properties': []},
        }
        words = _word_stream({}, flows, {}, {}, [])
        s = gm.rehydrate_wordstream(words)
        box = next(f for f in s._flow_meta.values() if f['name'] == 'doubler')
        self.assertEqual(box['entry_points'][0]['name'], 'input_value')
        self.assertEqual(box['exit_points'][0]['expr'], 'input_value * 2')
        step = next(f for f in s._flow_meta.values() if f['name'] == 'step1')
        self.assertEqual(step['parent_scope'], 'doubler')

    def test_combined_trinity_program(self):
        """GUI + flow + cells + piped commands in ONE stream, both paths."""
        widgets = {
            1: {'id': 1, 'kind': 'gui_window', 'x': 200, 'y': 150,
                    'w': 400, 'h': 300, 'label': 'App', 'name': 'app_win',
                    'layout_mode': 'vbox', 'parent_id': None,
                    'properties': [], 'signal_ids': {}}}
        flows = {5: {'id': 5, 'kind': 'flow_terminator', 'x': 700,
                       'y': 100, 'w': 120, 'h': 60, 'label': 'go',
                       'name': 'runner',
                       'properties': [{'name': 'is_entry',
                                       'value': True}]}}
        cells = {(0, 0): {'kind': 'cell_number', 'value': 10},
                 (1, 0): {'kind': 'cell_formula', 'value': '=A1+A1'}}
        cmds = {21: {'id': 21, 'kind': 'cmd_math_abs', 'x': 5, 'y': 5,
                       'params': {'x': -9}}}
        a, b = self._both_paths(widgets, flows, cells, cmds, [])
        self.assertEqual(a, b)


if __name__ == '__main__':
    unittest.main(verbosity=1)
