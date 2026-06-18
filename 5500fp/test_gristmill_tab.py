"""test_gristmill_tab.py — Unit tests for the GristMill tab (Bundle 13).

Tests the pure (headless) functions in gristmill_tab_view.py:
    build_vocabulary_data()     — static Meccano vocabulary registry
    build_program_data()        — fc_state → program tree data
    render_detail()             — details-panel text per node type

Does NOT require a display or tkinter; GristMillTabView (the tkinter class)
is not instantiated here.

Run:
    cd ~/dev/SkepticusMaximus/TernOO-5500FP/5500fp
    python3 -m unittest test_gristmill_tab

Date: 2026-06-19, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# WordStream and edit are imported directly (no circular risk)
from word_stream import WordStream
from word_stream_edit import WordStreamEdit

# Import gristmill_tab_view
import importlib.util as _ilu
_gm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         'gristmill_tab_view.py')
_gm_spec = _ilu.spec_from_file_location('gristmill_tab_view', _gm_path)
_gm      = _ilu.module_from_spec(_gm_spec)
_gm_spec.loader.exec_module(_gm)

build_vocabulary_data = _gm.build_vocabulary_data
build_program_data    = _gm.build_program_data
render_detail         = _gm.render_detail
SIGNAL_NAMES          = _gm.SIGNAL_NAMES
SIGNAL_HUMAN          = _gm.SIGNAL_HUMAN
SHAPE_NAMES           = _gm.SHAPE_NAMES
STYLE_NAMES           = _gm.STYLE_NAMES
LAYOUT_NAMES          = _gm.LAYOUT_NAMES
OPCODE_NAMES          = _gm.OPCODE_NAMES

# Also load widget_lib to build test fixtures
_wl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widget_lib.py')
_wl_spec = _ilu.spec_from_file_location('widget_lib', _wl_path)
_wl      = _ilu.module_from_spec(_wl_spec)
_wl_spec.loader.exec_module(_wl)

SIGNAL_CLICKED = _wl.SIGNAL_CLICKED
SIGNAL_TOGGLED = _wl.SIGNAL_TOGGLED


# =============================================================================
# Helpers for building minimal fc_state fixtures
# =============================================================================

def _make_fc_state(widgets=None, flow_symbols=None, stream=None):
    """Return a minimal fc_state dict with the given overrides."""
    return {
        'widgets':      widgets      if widgets      is not None else {},
        'flow_symbols': flow_symbols if flow_symbols is not None else {},
        'edges':        [],
        'flow_edges':   [],
        'stream':       stream       if stream       is not None else WordStream(),
    }


def _make_window(wid=0, label='TestWindow', x=100, y=100, w=400, h=300,
                 layout_mode='vbox', children=None):
    """Return a gui_window widget dict."""
    return {
        'id': wid, 'kind': 'gui_window',
        'x': x, 'y': y, 'w': w, 'h': h,
        'label': label,
        'parent_id': None,
        'layout_mode': layout_mode,
        'signal_ids': {SIGNAL_CLICKED: None},   # no binding
        'properties': [{'name': 'title', 'value': 'My App'}],
    }


def _make_button(wid=1, label='Submit', x=150, y=150, parent_id=0):
    """Return a gui_button widget dict with no binding."""
    return {
        'id': wid, 'kind': 'gui_button',
        'x': x, 'y': y, 'w': 100, 'h': 30,
        'label': label,
        'parent_id': parent_id,
        'layout_mode': None,
        'signal_ids': {},
        'properties': [],
    }


def _make_button_bound(wid=1, label='Submit', x=150, y=150,
                       parent_id=0, dst_x=500, dst_y=200):
    """Return a gui_button with a SIGNAL_CLICKED binding."""
    return {
        'id': wid, 'kind': 'gui_button',
        'x': x, 'y': y, 'w': 100, 'h': 30,
        'label': label,
        'parent_id': parent_id,
        'layout_mode': None,
        'signal_ids': {SIGNAL_CLICKED: {'dst_x': dst_x, 'dst_y': dst_y}},
        'properties': [],
    }


def _make_terminator(sid=2, label='on_submit', x=500, y=200):
    """Return a flow_terminator symbol dict."""
    return {
        'id': sid, 'kind': 'flow_terminator',
        'x': x, 'y': y, 'w': 120, 'h': 60,
        'label': label,
        'properties': [{'name': 'is_entry', 'value': True}],
    }


# =============================================================================
# Test suite
# =============================================================================

class TestGristMillVocabulary(unittest.TestCase):
    """Tests for build_vocabulary_data() — static Meccano registry."""

    def setUp(self):
        self.vocab = build_vocabulary_data()

    def _section(self, name):
        for s in self.vocab:
            if s['section'] == name:
                return s
        return None

    def test_01_five_sections_returned(self):
        """Vocabulary has exactly 5 sections: Opcodes, Shapes, Styles, Layouts, Signals."""
        names = [s['section'] for s in self.vocab]
        self.assertEqual(names, ['Opcodes', 'Shapes', 'Styles', 'Layouts', 'Signals'],
                         f"Unexpected sections: {names}")

    def test_02_shapes_section_has_13_entries(self):
        """Shapes section lists all 13 SHAPE_* constants (0–12)."""
        sec = self._section('Shapes')
        self.assertIsNotNone(sec)
        self.assertEqual(len(sec['entries']), 13,
                         f"Expected 13 shapes, got {len(sec['entries'])}")

    def test_03_signals_section_has_8_entries(self):
        """Signals section lists all 8 SIGNAL_* constants (300–307)."""
        sec = self._section('Signals')
        self.assertIsNotNone(sec)
        self.assertEqual(len(sec['entries']), 8,
                         f"Expected 8 signals, got {len(sec['entries'])}")

    def test_04_signal_ids_in_range_300_307(self):
        """All Signal entry IDs are in the range 300–307."""
        sec = self._section('Signals')
        ids = [e['id'] for e in sec['entries']]
        self.assertTrue(all(300 <= i <= 307 for i in ids),
                        f"Signal IDs out of range: {ids}")

    def test_05_layouts_section_has_5_entries(self):
        """Layouts section lists all 5 LAYOUT_* constants (200–204)."""
        sec = self._section('Layouts')
        self.assertIsNotNone(sec)
        self.assertEqual(len(sec['entries']), 5,
                         f"Expected 5 layouts, got {len(sec['entries'])}")

    def test_06_opcodes_include_rnode_and_redge(self):
        """Opcodes section includes RNODE and REDGE."""
        sec = self._section('Opcodes')
        names = [e['name'] for e in sec['entries']]
        self.assertIn('RNODE', names)
        self.assertIn('REDGE', names)

    def test_07_signal_clicked_has_emitter_gui_button(self):
        """SIGNAL_CLICKED entry lists gui_button as an emitter."""
        sec = self._section('Signals')
        clicked = next((e for e in sec['entries'] if e['id'] == SIGNAL_CLICKED), None)
        self.assertIsNotNone(clicked, "SIGNAL_CLICKED not found in Signals section")
        self.assertIn('gui_button', clicked.get('emitters', []),
                      "gui_button should be an emitter of SIGNAL_CLICKED")


class TestGristMillProgramData(unittest.TestCase):
    """Tests for build_program_data() — dynamic program tree from fc_state."""

    def test_08_empty_state_returns_empty_program(self):
        """Empty fc_state returns empty program data."""
        pd = build_program_data(_make_fc_state())
        self.assertEqual(pd['widget_roots'], [])
        self.assertEqual(pd['bindings'], [])
        self.assertEqual(pd['flow_symbols'], {})

    def test_09_root_widget_has_no_parent(self):
        """Widget with parent_id=None appears as a root."""
        win = _make_window(wid=0)
        fc  = _make_fc_state(widgets={0: win})
        pd  = build_program_data(fc)
        self.assertIn(0, pd['widget_roots'],
                      "Window (parent_id=None) should be a root")

    def test_10_child_widget_appears_in_children_map(self):
        """Widget with parent_id set appears as child of parent in widget_children."""
        win = _make_window(wid=0)
        btn = _make_button(wid=1, parent_id=0)
        fc  = _make_fc_state(widgets={0: win, 1: btn})
        pd  = build_program_data(fc)
        self.assertNotIn(1, pd['widget_roots'],
                         "Button (parent_id=0) should not be a root")
        self.assertIn(1, pd['widget_children'].get(0, []),
                      "Button should be in children of window")

    def test_11_bound_signal_appears_in_bindings(self):
        """Widget with a non-None binding in signal_ids produces a binding entry."""
        win = _make_window(wid=0)
        btn = _make_button_bound(wid=1, parent_id=0, dst_x=500, dst_y=200)
        trm = _make_terminator(sid=2, label='on_submit', x=500, y=200)
        fc  = _make_fc_state(widgets={0: win, 1: btn}, flow_symbols={2: trm})
        pd  = build_program_data(fc)
        self.assertEqual(len(pd['bindings']), 1,
                         f"Expected 1 binding, got {len(pd['bindings'])}")
        b = pd['bindings'][0]
        self.assertEqual(b['wid'],      1)
        self.assertEqual(b['sig_id'],   SIGNAL_CLICKED)
        self.assertEqual(b['dst_label'], 'on_submit')
        self.assertEqual(b['sig_name'],  'clicked')

    def test_12_flow_symbol_appears_in_flow_symbols(self):
        """Flow symbols dict is returned unchanged in program data."""
        trm = _make_terminator(sid=5, label='run_flow')
        fc  = _make_fc_state(flow_symbols={5: trm})
        pd  = build_program_data(fc)
        self.assertIn(5, pd['flow_symbols'],
                      "flow_terminator should appear in program data flow_symbols")
        self.assertEqual(pd['flow_symbols'][5]['label'], 'run_flow')

    def test_13_word_map_from_stream_attribute(self):
        """Word spans from stream._word_map are surfaced in program data."""
        stream = WordStream()
        stream._word_map = {7: (0, 5)}
        win = _make_window(wid=7)
        fc  = _make_fc_state(widgets={7: win}, stream=stream)
        pd  = build_program_data(fc)
        self.assertEqual(pd['word_map'].get(7), (0, 5),
                         "Word span should be (0, 5) from stream._word_map")


class TestGristMillRenderDetail(unittest.TestCase):
    """Tests for render_detail() — details panel text rendering."""

    def test_14_opcode_detail_contains_name_and_value(self):
        """Opcode node detail includes the opcode name and numeric value."""
        data = {'type': 'opcode', 'name': 'RNODE', 'id': _wl.OP_RNODE}
        text = render_detail(data)
        self.assertIn('RNODE', text)
        self.assertIn(str(_wl.OP_RNODE), text)

    def test_15_shape_detail_contains_id_and_name(self):
        """Shape node detail includes the shape name and numeric ID."""
        data = {'type': 'shape', 'name': 'SHAPE_BUTTON', 'id': _wl.SHAPE_BUTTON}
        text = render_detail(data)
        self.assertIn('SHAPE_BUTTON', text)
        self.assertIn(str(_wl.SHAPE_BUTTON), text)

    def test_16_signal_detail_contains_human_name_and_id(self):
        """Signal node detail includes human name and numeric ID."""
        data = {
            'type': 'signal',
            'name': 'SIGNAL_CLICKED',
            'id': SIGNAL_CLICKED,
            'human': 'clicked',
            'emitters': ['gui_button'],
        }
        text = render_detail(data)
        self.assertIn('clicked', text)
        self.assertIn(str(SIGNAL_CLICKED), text)
        self.assertIn('gui_button', text)

    def test_17_widget_detail_contains_kind_and_position(self):
        """Widget node detail includes kind, position, and word span if available."""
        w = _make_window(wid=0, x=200, y=300)
        fc = _make_fc_state(widgets={0: w})
        data = {'type': 'widget', 'wid': 0, 'w': w, 'span': (10, 17)}
        text = render_detail(data, fc)
        self.assertIn('gui_window', text)
        self.assertIn('200', text)   # x coordinate
        self.assertIn('300', text)   # y coordinate
        self.assertIn('stream[10..17]', text)

    def test_18_binding_detail_contains_src_signal_dst(self):
        """Binding node detail contains src widget, signal name, and dst terminator."""
        w   = _make_button_bound(wid=1, label='Go', dst_x=500, dst_y=200)
        fc  = _make_fc_state(widgets={1: w})
        data = {
            'type':      'binding',
            'wid':       1,
            'sig_id':    SIGNAL_CLICKED,
            'sig_name':  'clicked',
            'src_kind':  'gui_button',
            'src_label': 'Go',
            'dst_label': 'on_submit',
            'binfo':     {'dst_x': 500, 'dst_y': 200},
        }
        text = render_detail(data, fc)
        self.assertIn('Go', text)
        self.assertIn('clicked', text)
        self.assertIn('on_submit', text)

    def test_19_flow_symbol_detail_contains_label(self):
        """Flow symbol node detail contains kind, label, and binding count."""
        sym = _make_terminator(sid=3, label='on_login', x=400, y=300)
        fc  = _make_fc_state(flow_symbols={3: sym})
        data = {'type': 'flow_symbol', 'sid': 3, 'sym': sym}
        text = render_detail(data, fc)
        self.assertIn('flow_terminator', text)
        self.assertIn('on_login', text)


class TestGristMillLiveUpdate(unittest.TestCase):
    """Tests for WordStream subscriber / live update behaviour."""

    def test_20_on_stream_change_reschedules_rebuild(self):
        """on_stream_change() callback does not raise when root is None.

        Full after_idle scheduling needs a running Tk event loop; here we
        verify the callback handles the start-up / headless guard correctly
        (the method's try/except swallows the AttributeError silently).
        """
        class _FakeView:
            """Minimal stand-in — avoids tkinter construction."""
            _root     = None   # simulates pre-startup / no display
            _tree     = None
            _detail   = None
            _prog_iid = None
            _node_data: dict = {}

            def _rebuild_program(self):
                pass   # nothing to rebuild in the headless stand-in

            # Borrow the real method
            on_stream_change = _gm.GristMillTabView.on_stream_change

        view = _FakeView()
        try:
            view.on_stream_change()
        except Exception as exc:
            self.fail(f"on_stream_change() raised unexpectedly: {exc}")

    def test_21_subscriber_triggered_on_stream_mutation(self):
        """WordStream.subscribe() + stream.apply() correctly triggers the callback."""
        stream = WordStream()
        calls  = []
        stream.subscribe(lambda: calls.append(1))
        stream.apply(WordStreamEdit(op='replace', position=0,
                                    words_before=[], words_after=[42, 99, 7]))
        self.assertEqual(len(calls), 1,
                         "Subscriber should be called once after apply()")

    def test_22_rebuild_program_data_after_widget_add(self):
        """build_program_data reflects added widgets without needing stream walk."""
        # Start empty
        widgets = {}
        fc = _make_fc_state(widgets=widgets)
        pd = build_program_data(fc)
        self.assertEqual(pd['widget_roots'], [])

        # Add a window
        win = _make_window(wid=0)
        widgets[0] = win
        pd2 = build_program_data(fc)   # re-call with mutated fc
        self.assertIn(0, pd2['widget_roots'],
                      "Added window should now appear as a root")


if __name__ == '__main__':
    unittest.main(verbosity=2)
