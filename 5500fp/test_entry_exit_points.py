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

    def test_json_round_trip(self):
        c = self._container()
        # the .fc save path dumps flow symbols (incl. entry/exit points) to JSON
        loaded = json.loads(json.dumps(c))
        self.assertEqual(fp.port_names(loaded), {'input_value', 'result'})
        self.assertEqual(loaded['entry_points'][0]['type'], 'number')
        self.assertEqual(loaded['exit_points'][0]['description'], 'the output')


if __name__ == '__main__':
    unittest.main()
