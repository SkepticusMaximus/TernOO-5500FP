"""test_entry_exit_points.py — Phase 7c-4b entry/exit port data model + compile.

Pure unit tests (no tkinter / display). The GUI wiring (properties dialog,
port rendering, cross-scope edge drawing, Ctrl+click nav) is verified by
source-level checks in test_shell_tab-style suites and on-screen by Stevo.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import flowcode_ports as fp


class TestPortDataModel(unittest.TestCase):

    def _container(self):
        return {'id': 1, 'kind': 'flow_process', 'name': 'compute_score',
                'entry_points': [fp.make_port('input_value', 'number', 'the input')],
                'exit_points':  [fp.make_port('result', 'number', 'the output')]}

    def test_make_port_normalises(self):
        p = fp.make_port('  x ', 'number', 'd')
        self.assertEqual(p, {'name': 'x', 'type': 'number', 'description': 'd'})
        # unknown type falls back to number
        self.assertEqual(fp.make_port('y', 'bogus')['type'], 'number')

    def test_is_container(self):
        self.assertTrue(fp.is_container('flow_process'))
        self.assertTrue(fp.is_container('flow_subroutine'))
        self.assertFalse(fp.is_container('flow_terminator'))

    def test_port_names_span_entry_and_exit(self):
        c = self._container()
        self.assertEqual(fp.port_names(c), {'input_value', 'result'})

    def test_find_port(self):
        c = self._container()
        self.assertEqual(fp.find_port(c, 'input_value')[0], 'entry')
        self.assertEqual(fp.find_port(c, 'result')[0], 'exit')
        self.assertEqual(fp.find_port(c, 'nope'), (None, None))

    def test_validate_uniqueness_across_entry_and_exit(self):
        c = self._container()
        ok, _ = fp.validate_new_port(c, 'fresh', 'number')
        self.assertTrue(ok)
        # an exit cannot reuse an entry's name
        ok, msg = fp.validate_new_port(c, 'input_value', 'number')
        self.assertFalse(ok)
        self.assertIn('already used', msg)

    def test_validate_rejects_empty_and_bad_name(self):
        c = self._container()
        self.assertFalse(fp.validate_new_port(c, '', 'number')[0])
        self.assertFalse(fp.validate_new_port(c, 'has space', 'number')[0])
        self.assertFalse(fp.validate_new_port(c, 'ok', 'weird_type')[0])

    def test_validate_exclude_self_when_editing(self):
        c = self._container()
        port = c['entry_points'][0]
        # editing the same port (same name) must not clash with itself
        ok, _ = fp.validate_new_port(c, 'input_value', 'text', exclude=port)
        self.assertTrue(ok)

    def test_slot_names(self):
        self.assertEqual(fp.entry_slot('compute_score', 'input_value'),
                         'state_entry_compute_score_input_value')
        self.assertEqual(fp.exit_slot('compute_score', 'result'),
                         'state_exit_compute_score_result')

    def test_port_edge_compatibility(self):
        self.assertTrue(fp.port_edge_compatible('number', 'number'))
        self.assertTrue(fp.port_edge_compatible('boolean', 'number'))   # num class
        self.assertTrue(fp.port_edge_compatible('list_of_text', 'list_of_number'))
        self.assertFalse(fp.port_edge_compatible('text', 'number'))
        self.assertTrue(fp.port_edge_compatible('', 'number'))          # unknown → any

    def test_exit_port_expr(self):
        p = fp.make_port('result', 'number', 'out', expr='input_value * 2')
        self.assertEqual(p.get('expr'), 'input_value * 2')
        # entry ports (no expr) omit the field
        self.assertNotIn('expr', fp.make_port('input_value', 'number'))

    def test_json_round_trip(self):
        c = self._container()
        # the .fc save path dumps flow symbols (incl. entry/exit points) to JSON
        loaded = json.loads(json.dumps(c))
        self.assertEqual(fp.port_names(loaded), {'input_value', 'result'})
        self.assertEqual(loaded['entry_points'][0]['type'], 'number')
        self.assertEqual(loaded['exit_points'][0]['description'], 'the output')


class TestPortsUISourceWiring(unittest.TestCase):
    """Source-level checks that the properties dialog wires the ports UI (the
    tkinter dialog itself is screen-only — verified on-screen by Stevo)."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'FlowCode', 'flowcode.py')
        with open(path) as f:
            cls.src = f.read()

    def test_ports_module_loaded(self):
        self.assertIn('flowcode_ports', self.src)
        self.assertIn('_flowcode_ports', self.src)

    def test_properties_dialog_has_port_sections(self):
        self.assertIn('Entry Points', self.src)
        self.assertIn('Exit Points', self.src)
        self.assertIn('_ports_section', self.src)
        self.assertIn('_port_add_edit', self.src)
        self.assertIn('validate_new_port', self.src)

    def test_port_rendering_wired(self):
        self.assertIn('_fc_port_positions', self.src)
        self.assertIn('_fc_port_at', self.src)          # hit-test for edges (P4)
        # ports drawn in draw_symbol (dots on container edges)
        self.assertIn("pp = _fc_port_positions(s)", self.src)

    def test_cross_scope_edge_binding_wired(self):
        # edges can bind to a port by name; load preserves bound_port_name
        self.assertIn('bound_port_name', self.src)
        self.assertIn('port_hit = _fc_port_at(x, y)', self.src)
        self.assertIn("_ne['bound_port_name'] = e['bound_port_name']", self.src)
        # exit-port expr field (interior computation)
        self.assertIn("Expr (= interior formula)", self.src)


import subprocess
import tempfile

import compile_to_t5asm as C
from word_stream import WordStream

_EMU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'NASM-TernOO-5500FP-Emulator', 'c_emulator', '5500fp')
_HAVE_EMU = os.path.exists(_EMU)


def _demo_stream(input_value):
    """compute_score container: entry pulls input_cell, exit doubles it;
    an output cell reads the exit port."""
    s = WordStream()
    s._cell_meta = {
        (0, 0): {'id': 1, 'kind': 'cell_value', 'row': 0, 'col': 0,
                 'name': 'input_cell', 'value': input_value, 'properties': []},
        (0, 1): {'id': 2, 'kind': 'cell_formula', 'row': 0, 'col': 1,
                 'name': 'out', 'value': '=compute_score_result', 'properties': []},
    }
    s._flow_meta = {100: {'id': 100, 'kind': 'flow_process', 'x': 0, 'y': 0,
                          'w': 1, 'h': 1, 'label': 'CS', 'name': 'compute_score',
                          'entry_points': [{'name': 'input_value', 'type': 'number',
                                            'expr': 'input_cell'}],
                          'exit_points': [{'name': 'result', 'type': 'number',
                                           'expr': 'input_value * 2'}]}}
    return s


class TestPortCompilation(unittest.TestCase):

    def test_port_slots_and_recompute_emitted(self):
        asm = C.compile_wordstream_to_t5asm(_demo_stream(5), 'demo.fc')
        self.assertIn('state_entry_compute_score_input_value:', asm)
        self.assertIn('state_exit_compute_score_result:', asm)
        self.assertIn('recompute_all_ports', asm)
        self.assertIn('CALL recompute_all_ports', asm)   # per-frame trigger
        self.assertNotIn('uncompilable', asm)

    @unittest.skipUnless(_HAVE_EMU, 'C emulator binary not built')
    def test_cross_scope_dataflow_runs(self):
        for inp, exp in ((5, '10'), (7, '14')):
            asm = C.compile_wordstream_to_t5asm(_demo_stream(inp), 'demo.fc')
            tail = asm[asm.index('; ---- Container entry/exit ports'):]
            driver = ['main:', '    CALL recompute_all_ports',
                      '    CALL recompute_all_cells',
                      '    LI R20, state_cell_2', '    LDW R2, R20, 0',
                      '    LI R1, 1', '    SYSCALL', '    LI R1, 6', '    SYSCALL',
                      '    HALT', '']
            with tempfile.NamedTemporaryFile('w', suffix='.t5asm', delete=False) as f:
                f.write('\n'.join(driver) + '\n' + tail)
                path = f.name
            try:
                r = subprocess.run([_EMU, '--run', path], capture_output=True,
                                   text=True, timeout=10)
            finally:
                os.unlink(path)
            digits = [x for x in r.stdout.splitlines() if x.strip().lstrip('-').isdigit()]
            self.assertEqual(digits[-1:], [exp],
                             f'input {inp} should double to {exp}')


if __name__ == '__main__':
    unittest.main()
