"""test_name_property.py — Phase 7c-1: widget `name` property.

Headless coverage for the foundation layer of Phase 7c (named-handler
auto-wiring). Exercises the pieces that live outside the tkinter GUI:

  - flowcode_properties: 'name' is the topmost COMMON property (Identity
    section), present for every widget kind.
  - WordStream.name_in_use:  uniqueness across the widget + flow namespaces;
    empty name never collides; self-exclusion on edit.
  - WordStream.default_name: <kind>_<id> convention.
  - WordStream.ensure_unique_names: legacy backfill (missing name → default),
    explicit-empty preservation, duplicate disambiguation.
  - WordStream.iter_widgets: exposes name.
  - Save/load round-trip semantics at the dict level (names preserved;
    legacy entries without a name get defaults on load).

Run:
    cd ~/dev/SkepticusMaximus/TernOO-5500FP/5500fp
    python3 -m unittest test_name_property

Date: 2026-06-28, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
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


def _w(wid, kind, **kw):
    """Build a minimal widget/flow dict for testing."""
    d = {'id': wid, 'kind': kind}
    d.update(kw)
    return d


def _stream_with(widgets=None, flows=None):
    """WordStream whose _widget_meta / _flow_meta alias the given dicts
    (mirrors the editor's aliasing of fc_state['widgets'/'flow_symbols'])."""
    s = WordStream()
    s._widget_meta = {w['id']: w for w in (widgets or [])}
    s._flow_meta   = {f['id']: f for f in (flows or [])}
    return s


class TestNameInRegistry(unittest.TestCase):

    def test_name_is_common_property(self):
        for kind in ('gui_button', 'gui_window', 'flow_terminator', 'flow_decision'):
            names = [p['name'] for p in _fp.properties_for(kind)]
            self.assertIn('name', names, f"name missing for {kind}")

    def test_name_is_topmost(self):
        # First COMMON property → first in every merged list → topmost panel row.
        self.assertEqual(_fp.COMMON_PROPERTIES[0]['name'], 'name')
        self.assertEqual(_fp.properties_for('gui_button')[0]['name'], 'name')

    def test_name_descriptor(self):
        nameprop = next(p for p in _fp.COMMON_PROPERTIES if p['name'] == 'name')
        self.assertEqual(nameprop['kind'], 'string')
        self.assertEqual(nameprop['section'], 'Identity')

    def test_name_distinct_from_label(self):
        names = [p['name'] for p in _fp.COMMON_PROPERTIES]
        self.assertIn('name', names)
        self.assertIn('label', names)

    def test_name_in_multi_select_intersection(self):
        common = _fp.common_properties_for_kinds(['gui_button', 'gui_entry'])
        self.assertIn('name', [p['name'] for p in common])


class TestDefaultName(unittest.TestCase):

    def test_default_name_convention(self):
        self.assertEqual(WordStream.default_name({'kind': 'gui_button', 'id': 5}),
                         'gui_button_5')
        self.assertEqual(WordStream.default_name({'kind': 'flow_terminator', 'id': 3}),
                         'flow_terminator_3')

    def test_default_unique_across_namespaces(self):
        # Same id in both namespaces still yields distinct defaults (kind differs).
        self.assertNotEqual(WordStream.default_name({'kind': 'gui_button', 'id': 0}),
                            WordStream.default_name({'kind': 'flow_process', 'id': 0}))


class TestNameInUse(unittest.TestCase):

    def test_empty_never_collides(self):
        s = _stream_with([_w(0, 'gui_button', name=''), _w(1, 'gui_label', name='')])
        self.assertFalse(s.name_in_use(''))

    def test_detects_duplicate(self):
        s = _stream_with([_w(0, 'gui_button', name='ok_btn')])
        self.assertTrue(s.name_in_use('ok_btn'))
        self.assertFalse(s.name_in_use('other'))

    def test_spans_widget_and_flow_namespaces(self):
        s = _stream_with([_w(0, 'gui_button', name='shared')],
                         [_w(0, 'flow_terminator', name='entry')])
        self.assertTrue(s.name_in_use('shared'))
        self.assertTrue(s.name_in_use('entry'))

    def test_exclude_allows_self_keep(self):
        btn = _w(0, 'gui_button', name='ok_btn')
        s = _stream_with([btn, _w(1, 'gui_label', name='title')])
        # Editing btn and keeping its own name must not report a collision.
        self.assertFalse(s.name_in_use('ok_btn', exclude=btn))
        # But re-using another widget's name is still a collision.
        self.assertTrue(s.name_in_use('title', exclude=btn))


class TestEnsureUniqueNames(unittest.TestCase):

    def test_legacy_backfill(self):
        # Entries without a 'name' key are legacy → get the default.
        s = _stream_with([_w(0, 'gui_button'), _w(1, 'gui_entry')],
                         [_w(0, 'flow_process')])
        changed = s.ensure_unique_names()
        self.assertEqual(changed, 3)
        self.assertEqual(s._widget_meta[0]['name'], 'gui_button_0')
        self.assertEqual(s._widget_meta[1]['name'], 'gui_entry_1')
        self.assertEqual(s._flow_meta[0]['name'], 'flow_process_0')

    def test_explicit_empty_preserved(self):
        # A present-but-empty name is intentional and must survive.
        s = _stream_with([_w(0, 'gui_button', name='')])
        s.ensure_unique_names()
        self.assertEqual(s._widget_meta[0]['name'], '')

    def test_duplicates_disambiguated(self):
        s = _stream_with([_w(0, 'gui_button', name='dup'),
                          _w(1, 'gui_label',  name='dup'),
                          _w(2, 'gui_entry',  name='dup')])
        s.ensure_unique_names()
        names = [s._widget_meta[i]['name'] for i in (0, 1, 2)]
        self.assertEqual(names[0], 'dup')          # first kept
        self.assertEqual(len(set(names)), 3)       # all unique
        self.assertTrue(all(n.startswith('dup') for n in names))

    def test_idempotent(self):
        s = _stream_with([_w(0, 'gui_button'), _w(1, 'gui_button', name='dup'),
                          _w(2, 'gui_label', name='dup')])
        s.ensure_unique_names()
        first = {i: s._widget_meta[i]['name'] for i in (0, 1, 2)}
        changed2 = s.ensure_unique_names()
        self.assertEqual(changed2, 0)
        self.assertEqual(first, {i: s._widget_meta[i]['name'] for i in (0, 1, 2)})


class TestIterWidgetsExposesName(unittest.TestCase):

    def test_name_in_namespace(self):
        s = _stream_with([_w(0, 'gui_button', name='ok_btn', label='OK')])
        widgets = list(s.iter_widgets())
        self.assertEqual(widgets[0].name, 'ok_btn')


class TestSaveLoadRoundTrip(unittest.TestCase):
    """Dict-level model of _save_to_path / guic_do_open name handling."""

    @staticmethod
    def _save(stream):
        # Mirrors save_syms: name written as a top-level field.
        return [{'id': w['id'], 'kind': w['kind'], 'name': w.get('name', '')}
                for w in stream._widget_meta.values()]

    @staticmethod
    def _load(saved):
        # Mirrors load: preserve 'name' if present (incl. empty), then backfill.
        widgets = []
        for sym in saved:
            d = {'id': sym['id'], 'kind': sym['kind']}
            if 'name' in sym:
                d['name'] = sym['name']
            widgets.append(d)
        s = _stream_with(widgets)
        s.ensure_unique_names()
        return s

    def test_names_preserved(self):
        src = _stream_with([_w(0, 'gui_button', name='go'),
                            _w(1, 'gui_label',  name='')])
        loaded = self._load(self._save(src))
        self.assertEqual(loaded._widget_meta[0]['name'], 'go')
        self.assertEqual(loaded._widget_meta[1]['name'], '')   # empty preserved

    def test_legacy_file_gets_defaults(self):
        # Legacy saved entries lack the name key entirely.
        legacy = [{'id': 0, 'kind': 'gui_button'},
                  {'id': 1, 'kind': 'gui_entry'}]
        loaded = self._load(legacy)
        self.assertEqual(loaded._widget_meta[0]['name'], 'gui_button_0')
        self.assertEqual(loaded._widget_meta[1]['name'], 'gui_entry_1')


if __name__ == '__main__':
    unittest.main()
