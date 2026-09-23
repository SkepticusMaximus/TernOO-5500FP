"""test_model_props.py — Q1+Q2 ruled grammar: MPROP / MBIND / MVALUE.

Properties and signal bindings ride the stream via dedicated ops
(siblings of MPARM, targets by name); a tri-state control's value is
a DATA word in its span.  Round-trip through ghost_to_meccano →
meccano_to_model is the acceptance.

Added: 23 Sep 2026 (Q1+Q2). Authors: Stevo + Claude.
"""
import importlib.util as ilu
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = ilu.spec_from_file_location(
        name, os.path.join(_HERE, name + '.py'))
    mod = ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GM = _load('ghost_meccano')


def _widgets():
    return {
        0: {'id': 0, 'kind': 'gui_window', 'x': 400, 'y': 300,
            'w': 600, 'h': 400, 'label': 'win', 'name': 'win_0'},
        1: {'id': 1, 'kind': 'gui_tritoggle', 'x': 200, 'y': 150,
            'w': 120, 'h': 40, 'label': 'power', 'name': 'tog_1',
            'parent_id': 0, 'value': -1,
            'properties': [{'name': 'direction', 'value': 'in'},
                           {'name': 'address', 'value': 'p_state'}],
            'bindings': {'toggled': 'on_power'}},
    }


class TestModelProps(unittest.TestCase):
    def setUp(self):
        prog = GM.ghost_to_meccano(_widgets(), [])
        self.model = GM.meccano_to_model(prog.words)
        self.tog = next(n for n in self.model['nodes']
                        if n.get('name') == 'tog_1')

    def test_kind_survives(self):
        self.assertEqual(self.tog['kind'], 'gui_tritoggle')

    def test_properties_ride_the_stream(self):
        props = {p['name']: p['value'] for p in self.tog['properties']}
        self.assertEqual(props['direction'], 'in')
        self.assertEqual(props['address'], 'p_state')

    def test_binding_by_name(self):
        self.assertEqual(self.tog['bindings'], {'toggled': 'on_power'})

    def test_value_is_a_data_word_in_span(self):
        self.assertEqual(self.tog['value'], -1)

    def test_plain_widget_gains_nothing(self):
        win = next(n for n in self.model['nodes']
                   if n.get('name') == 'win_0')
        self.assertNotIn('value', win)
        self.assertNotIn('bindings', win)


if __name__ == '__main__':
    unittest.main()
