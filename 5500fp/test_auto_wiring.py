#!/usr/bin/env python3
"""Phase 7c-2 — name-based auto-wiring tests (headless, no tkinter).

Covers the pure auto-wiring layer in flowcode_signals.py:
  - canonical handler-name convention (incl. hyphen→underscore normalisation)
  - compute / materialize of auto-wired bindings from name agreement
  - rename cascade (widget rename, terminator rename, delete) via re-materialise
  - manual bindings preserved and winning per-signal
  - legacy reconciliation: conforming manual edges become auto; non-conforming
    are reported for the one-time prompt; 'Update names' conforms them
  - save/load model: auto-wired entries omitted from save, regenerated on load

Run:
    cd 5500fp && python3 -m unittest test_auto_wiring
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from word_stream import WordStream

import importlib.util as _ilu
_fs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'flowcode_signals.py')
_fs_spec = _ilu.spec_from_file_location('flowcode_signals', _fs_path)
_fs      = _ilu.module_from_spec(_fs_spec)
_fs_spec.loader.exec_module(_fs)

CLICKED  = _fs.SIGNAL_CLICKED
CHANGED  = _fs.SIGNAL_CHANGED
ACTIVATED = _fs.SIGNAL_ACTIVATED
VALUE_CHANGED = _fs.SIGNAL_VALUE_CHANGED


def _widget(wid, kind, name, x=100, y=100, signal_ids=None):
    return {'id': wid, 'kind': kind, 'name': name, 'x': x, 'y': y,
            'w': 160, 'h': 72, 'signal_ids': signal_ids or {}}


def _term(sid, name, x=500, y=300, is_entry=True):
    return {'id': sid, 'kind': 'flow_terminator', 'name': name,
            'x': x, 'y': y, 'w': 120, 'h': 60,
            'properties': [{'name': 'is_entry', 'value': is_entry}]}


def _stream(widgets=None, terms=None):
    s = WordStream()
    s._widget_meta = {w['id']: w for w in (widgets or [])}
    s._flow_meta   = {t['id']: t for t in (terms or [])}
    return s


class TestCanonicalName(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(_fs.canonical_handler_name('submit_button', 'clicked'),
                         'submit_button_clicked')

    def test_hyphen_normalised(self):
        self.assertEqual(_fs.canonical_handler_name('slider', 'value-changed'),
                         'slider_value_changed')

    def test_empty_name(self):
        self.assertEqual(_fs.canonical_handler_name('', 'clicked'), '')


class TestComputeAndMaterialize(unittest.TestCase):
    def test_match_creates_binding(self):
        s = _stream([_widget(0, 'gui_button', 'go')],
                    [_term(1, 'go_clicked', x=500, y=300)])
        comp = _fs.compute_auto_wired_bindings(s)
        self.assertEqual(comp, {0: {CLICKED: {'dst_x': 500, 'dst_y': 300}}})
        n = _fs.materialize_auto_wired_bindings(s)
        self.assertEqual(n, 1)
        si = s._widget_meta[0]['signal_ids']
        self.assertTrue(si[CLICKED]['auto_wired'])
        self.assertEqual((si[CLICKED]['dst_x'], si[CLICKED]['dst_y']), (500, 300))

    def test_no_match_no_binding(self):
        s = _stream([_widget(0, 'gui_button', 'go')],
                    [_term(1, 'something_else')])
        _fs.materialize_auto_wired_bindings(s)
        self.assertEqual(s._widget_meta[0]['signal_ids'], {})

    def test_requires_is_entry(self):
        s = _stream([_widget(0, 'gui_button', 'go')],
                    [_term(1, 'go_clicked', is_entry=False)])
        _fs.materialize_auto_wired_bindings(s)
        self.assertEqual(s._widget_meta[0]['signal_ids'], {})

    def test_nameless_widget_not_wired(self):
        s = _stream([_widget(0, 'gui_button', '')], [_term(1, '_clicked')])
        _fs.materialize_auto_wired_bindings(s)
        self.assertEqual(s._widget_meta[0]['signal_ids'], {})

    def test_multi_signal_widget(self):
        # gui_entry emits changed + activated
        s = _stream([_widget(0, 'gui_entry', 'field')],
                    [_term(1, 'field_changed', x=10, y=20),
                     _term(2, 'field_activated', x=30, y=40)])
        _fs.materialize_auto_wired_bindings(s)
        si = s._widget_meta[0]['signal_ids']
        self.assertEqual((si[CHANGED]['dst_x'], si[CHANGED]['dst_y']), (10, 20))
        self.assertEqual((si[ACTIVATED]['dst_x'], si[ACTIVATED]['dst_y']), (30, 40))

    def test_idempotent(self):
        s = _stream([_widget(0, 'gui_button', 'go')], [_term(1, 'go_clicked')])
        _fs.materialize_auto_wired_bindings(s)
        self.assertEqual(_fs.materialize_auto_wired_bindings(s), 0)


class TestRenameCascade(unittest.TestCase):
    def test_widget_rename_moves_binding(self):
        w = _widget(0, 'gui_button', 'go')
        s = _stream([w], [_term(1, 'go_clicked'), _term(2, 'start_clicked')])
        _fs.materialize_auto_wired_bindings(s)
        self.assertIn(CLICKED, w['signal_ids'])
        # rename widget go → start: binding should now point at start_clicked
        w['name'] = 'start'
        _fs.materialize_auto_wired_bindings(s)
        self.assertEqual(w['signal_ids'][CLICKED]['dst_y'],
                         s._flow_meta[2]['y'])

    def test_widget_rename_orphans_binding(self):
        w = _widget(0, 'gui_button', 'go')
        s = _stream([w], [_term(1, 'go_clicked')])
        _fs.materialize_auto_wired_bindings(s)
        self.assertIn(CLICKED, w['signal_ids'])
        w['name'] = 'nomatch'
        _fs.materialize_auto_wired_bindings(s)
        self.assertEqual(w['signal_ids'], {})   # auto binding dropped

    def test_terminator_rename(self):
        t = _term(1, 'wrong_clicked')
        w = _widget(0, 'gui_button', 'go')
        s = _stream([w], [t])
        _fs.materialize_auto_wired_bindings(s)
        self.assertEqual(w['signal_ids'], {})
        t['name'] = 'go_clicked'
        _fs.materialize_auto_wired_bindings(s)
        self.assertIn(CLICKED, w['signal_ids'])

    def test_terminator_delete(self):
        w = _widget(0, 'gui_button', 'go')
        s = _stream([w], [_term(1, 'go_clicked')])
        _fs.materialize_auto_wired_bindings(s)
        self.assertIn(CLICKED, w['signal_ids'])
        del s._flow_meta[1]
        _fs.materialize_auto_wired_bindings(s)
        self.assertEqual(w['signal_ids'], {})

    def test_terminator_move_updates_dst(self):
        t = _term(1, 'go_clicked', x=500, y=300)
        w = _widget(0, 'gui_button', 'go')
        s = _stream([w], [t])
        _fs.materialize_auto_wired_bindings(s)
        t['x'], t['y'] = 640, 360
        _fs.materialize_auto_wired_bindings(s)
        self.assertEqual((w['signal_ids'][CLICKED]['dst_x'],
                          w['signal_ids'][CLICKED]['dst_y']), (640, 360))


class TestManualBindings(unittest.TestCase):
    def test_manual_preserved_and_wins(self):
        # Manual binding on clicked to a custom position; an auto match also
        # exists — manual must win for that signal.
        w = _widget(0, 'gui_button', 'go',
                    signal_ids={CLICKED: {'dst_x': 99, 'dst_y': 88}})  # no auto_wired
        s = _stream([w], [_term(1, 'go_clicked', x=500, y=300)])
        _fs.materialize_auto_wired_bindings(s)
        self.assertEqual((w['signal_ids'][CLICKED]['dst_x'],
                          w['signal_ids'][CLICKED]['dst_y']), (99, 88))
        self.assertFalse(w['signal_ids'][CLICKED].get('auto_wired'))


class TestLegacyReconcile(unittest.TestCase):
    def test_conforming_manual_becomes_auto(self):
        # Manual edge whose terminator name already matches the convention.
        w = _widget(0, 'gui_button', 'go',
                    signal_ids={CLICKED: {'dst_x': 500, 'dst_y': 300}})
        s = _stream([w], [_term(1, 'go_clicked', x=500, y=300)])
        nonconf = _fs.reconcile_loaded_bindings(s)
        self.assertEqual(nonconf, [])
        self.assertTrue(w['signal_ids'][CLICKED]['auto_wired'])

    def test_nonconforming_reported(self):
        # Manual edge to a terminator whose name doesn't match the convention.
        w = _widget(0, 'gui_button', 'go',
                    signal_ids={CLICKED: {'dst_x': 700, 'dst_y': 200}})
        s = _stream([w], [_term(1, 'handle_it', x=700, y=200)])
        nonconf = _fs.reconcile_loaded_bindings(s)
        self.assertEqual(len(nonconf), 1)
        self.assertEqual(nonconf[0]['handler'], 'go_clicked')
        # preserved as manual
        self.assertFalse(w['signal_ids'][CLICKED].get('auto_wired'))

    def test_update_names_conforms(self):
        w = _widget(0, 'gui_button', 'go',
                    signal_ids={CLICKED: {'dst_x': 700, 'dst_y': 200}})
        t = _term(1, 'handle_it', x=700, y=200)
        s = _stream([w], [t])
        _fs.reconcile_loaded_bindings(s)
        renamed = _fs.conform_manual_bindings(s)
        self.assertEqual(renamed, 1)
        self.assertEqual(t['name'], 'go_clicked')
        self.assertTrue(w['signal_ids'][CLICKED]['auto_wired'])


class TestHandlerNameHelpers(unittest.TestCase):
    def test_all_handler_names(self):
        s = _stream([_widget(0, 'gui_button', 'go'),
                     _widget(1, 'gui_entry', 'field')], [])
        names = _fs.all_handler_names(s)
        self.assertIn('go_clicked', names)
        self.assertIn('field_changed', names)
        self.assertIn('field_activated', names)

    def test_auto_handler_names_for_widget(self):
        triples = _fs.auto_handler_names_for_widget(_widget(0, 'gui_entry', 'field'))
        handlers = {h for (_id, _n, h) in triples}
        self.assertEqual(handlers, {'field_changed', 'field_activated'})


class TestSaveLoadModel(unittest.TestCase):
    """Model the save (omit auto-wired) / load (regenerate) round-trip."""

    def _save_signal_ids(self, w):
        # Mirrors _save_to_path: omit auto_wired entries, strip the flag.
        out = {}
        for k, v in (w.get('signal_ids') or {}).items():
            if v.get('auto_wired'):
                continue
            out[str(k)] = {kk: vv for kk, vv in v.items() if kk != 'auto_wired'}
        return out

    def test_auto_omitted_then_regenerated(self):
        w = _widget(0, 'gui_button', 'go')
        s = _stream([w], [_term(1, 'go_clicked', x=500, y=300)])
        _fs.materialize_auto_wired_bindings(s)
        saved = self._save_signal_ids(w)
        self.assertEqual(saved, {})   # nothing saved (it's derived)
        # reload: fresh widget with no signal_ids, same terminator → regenerated
        w2 = _widget(0, 'gui_button', 'go', signal_ids=saved)
        s2 = _stream([w2], [_term(1, 'go_clicked', x=500, y=300)])
        _fs.reconcile_loaded_bindings(s2)
        self.assertTrue(w2['signal_ids'][CLICKED]['auto_wired'])

    def test_manual_saved(self):
        w = _widget(0, 'gui_button', 'go',
                    signal_ids={CLICKED: {'dst_x': 99, 'dst_y': 88}})
        s = _stream([w], [])
        _fs.materialize_auto_wired_bindings(s)
        saved = self._save_signal_ids(w)
        self.assertEqual(saved, {str(CLICKED): {'dst_x': 99, 'dst_y': 88}})


if __name__ == '__main__':
    unittest.main()
