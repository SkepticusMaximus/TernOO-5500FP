"""test_stage6_workflow.py — End-to-end Stage 6 workflow integration test.

Exercises the unified pipeline using the actual library API (Phase 6A–6E +
Bundles 11–12), confirming every Stage 6 capability works together as a whole:

  - WordStream as canonical source of truth
  - Widget placement (RNODE with gui_* kind, via widget_lib builders)
  - Flow symbol placement (RNODE with flow_* kind)
  - Layout mode encoding (LAYOUT_VBOX on a container RNODE)
  - Signal binding (REDGE T20=−1 handler form, SIGNAL_CLICKED encoding)
  - Handler resolution (handler_for returns (otree, signal_name, symbolic_name))
  - Undo through WordStreamEdit.invert()
  - .ternoo save/load roundtrip preserves the word stream

Run:
    cd ~/dev/SkepticusMaximus/TernOO-5500FP/5500fp
    python3 -m unittest test_stage6_workflow

Date: 2026-06-19, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import os
import sys
import json
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from word_stream import WordStream
from word_stream_edit import WordStreamEdit

# ── Load widget_lib via importlib (avoids top-level circular imports) ─────────
import importlib.util as _ilu
_wl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widget_lib.py')
_wl_spec = _ilu.spec_from_file_location('widget_lib', _wl_path)
_wl      = _ilu.module_from_spec(_wl_spec)
_wl_spec.loader.exec_module(_wl)

SIGNAL_CLICKED   = _wl.SIGNAL_CLICKED
LAYOUT_VBOX      = _wl.LAYOUT_VBOX
SHAPE_RECTANGLE  = _wl.SHAPE_RECTANGLE
FLOW_SHAPE_MAP   = _wl.FLOW_SHAPE_MAP
OPF_PIGART       = _wl.OPF_PIGART
OP_RENDER        = _wl.OP_RENDER

build_rnode_shape_labeled_layout = _wl.build_rnode_shape_labeled_layout
build_rnode_shape_labeled        = _wl.build_rnode_shape_labeled
build_redge_handler              = _wl.build_redge_handler
build_data_symbol                = _wl.build_data_symbol
build_opcode_word                = _wl.build_opcode_word
MeccanoProgram                   = _wl.MeccanoProgram

GC_SCALE = 10   # pixels → Meccano units (matches ghost_meccano.FC_GRID_TO_MECCANO)


class TestStage6Workflow(unittest.TestCase):
    """End-to-end Stage 6 integration test — one scenario, all capabilities."""

    # ── Fixture helpers ───────────────────────────────────────────────────────

    # Fixed pixel coords for the three objects in our test canvas
    WINDOW_X,  WINDOW_Y  = 100, 100
    BUTTON_X,  BUTTON_Y  = 150, 150
    TERM_X,    TERM_Y    = 500, 200

    def _build_all_words(self):
        """Build word lists for gui_window + gui_button + flow_terminator + handler.

        Returns:
            (window_words, button_words, term_words, handler_words)
        """
        window_words = build_rnode_shape_labeled_layout(
            (self.WINDOW_X // GC_SCALE, self.WINDOW_Y // GC_SCALE),
            (40, 30),                   # 400 px / 10, 300 px / 10
            SHAPE_RECTANGLE,
            'TestWindow',
            LAYOUT_VBOX,
        )
        button_words = build_rnode_shape_labeled(
            (self.BUTTON_X // GC_SCALE, self.BUTTON_Y // GC_SCALE),
            (10, 3),
            SHAPE_RECTANGLE,
            'Submit',
        )
        term_shape = FLOW_SHAPE_MAP.get('flow_terminator', SHAPE_RECTANGLE)
        term_words = build_rnode_shape_labeled(
            (self.TERM_X // GC_SCALE, self.TERM_Y // GC_SCALE),
            (12, 4),
            term_shape,
            'on_submit',
        )
        handler_words = build_redge_handler(
            (self.BUTTON_X // GC_SCALE, self.BUTTON_Y // GC_SCALE),
            (self.TERM_X   // GC_SCALE, self.TERM_Y   // GC_SCALE),
            SIGNAL_CLICKED,
        )
        return window_words, button_words, term_words, handler_words

    def _populated_stream(self):
        """Return a WordStream containing all four word groups."""
        window_words, button_words, term_words, handler_words = self._build_all_words()
        all_words = window_words + button_words + term_words + handler_words
        stream = WordStream()
        stream.apply(WordStreamEdit(op='replace', position=0,
                                    words_before=[], words_after=all_words))
        return stream, window_words, button_words, term_words, handler_words

    def _wire_metadata(self, stream):
        """Attach _widget_meta and _flow_meta to stream (simulates Phase 6B alias)."""
        button_id, term_id = 1, 2
        stream._widget_meta = {
            button_id: {
                'id': button_id, 'kind': 'gui_button',
                'x': self.BUTTON_X, 'y': self.BUTTON_Y,
                'signal_ids': {
                    SIGNAL_CLICKED: {'dst_x': self.TERM_X, 'dst_y': self.TERM_Y}
                },
            }
        }
        stream._flow_meta = {
            term_id: {
                'id': term_id, 'kind': 'flow_terminator',
                'x': self.TERM_X, 'y': self.TERM_Y,
                'label': 'on_submit',
                'properties': [{'name': 'is_entry', 'value': True}],
            }
        }
        return button_id, term_id

    # ── Tests ─────────────────────────────────────────────────────────────────

    def test_01_widget_placement_in_stream(self):
        """Widget placement: RNODE words for gui_* kinds land in stream."""
        stream, window_words, button_words, term_words, handler_words = \
            self._populated_stream()
        # Stream contains all emitted words in order
        all_words = window_words + button_words + term_words + handler_words
        self.assertEqual(stream.words, all_words)
        self.assertGreater(len(stream.words), 0)

    def test_02_layout_encoding(self):
        """Layout mode: LAYOUT_VBOX word is present in the stream (gui_window RNODE)."""
        stream, *_ = self._populated_stream()
        layout_word = build_data_symbol(LAYOUT_VBOX)
        self.assertIn(layout_word, stream.words,
                      "LAYOUT_VBOX not encoded in stream")

    def test_03_signal_binding_in_stream(self):
        """Signal binding: SIGNAL_CLICKED word is present in the stream (handler REDGE)."""
        stream, *_ = self._populated_stream()
        signal_word = build_data_symbol(SIGNAL_CLICKED)
        self.assertIn(signal_word, stream.words,
                      "SIGNAL_CLICKED not encoded in stream")

    def test_04_handler_for_resolution(self):
        """Handler resolution: handler_for returns correct (otree, signal_name, symbolic_name)."""
        stream, *_ = self._populated_stream()
        button_id, _ = self._wire_metadata(stream)

        handler = stream.handler_for(button_id, SIGNAL_CLICKED)
        self.assertIsNotNone(handler, "handler_for returned None")
        otree_addr, signal_name, symbolic_name = handler
        self.assertEqual(signal_name, 'clicked',
                         f"Expected signal_name='clicked', got {signal_name!r}")
        self.assertEqual(symbolic_name, 'on_submit',
                         f"Expected symbolic_name='on_submit', got {symbolic_name!r}")
        # otree_addr is None until Stage 7 native stream-walking (per spec)

    def test_05_unbound_signal_returns_none(self):
        """handler_for returns None for a signal that is not bound."""
        stream, *_ = self._populated_stream()
        button_id, _ = self._wire_metadata(stream)
        SIGNAL_TOGGLED = _wl.SIGNAL_TOGGLED
        self.assertIsNone(stream.handler_for(button_id, SIGNAL_TOGGLED))

    def test_06_ternoo_save_load_roundtrip(self):
        """Save/load roundtrip: word stream is identical after .ternoo JSON round-trip."""
        stream, *_ = self._populated_stream()
        original_words = list(stream.words)

        with tempfile.NamedTemporaryFile(suffix='.ternoo', mode='w',
                                         delete=False) as f:
            json.dump({
                'tgui_version': '0.3',
                'source_type': 'ternoo_design',
                'word_stream': stream.words,
            }, f)
            tmpfile = f.name

        try:
            with open(tmpfile) as f:
                loaded = json.load(f)
            reloaded = WordStream(loaded['word_stream'])
            self.assertEqual(reloaded.words, original_words,
                             ".ternoo roundtrip: word stream not preserved")
        finally:
            os.unlink(tmpfile)

    def test_07_undo_via_edit_invert(self):
        """Undo: WordStreamEdit.invert() restores stream to pre-binding state."""
        stream, window_words, button_words, term_words, handler_words = \
            self._populated_stream()
        signal_word = build_data_symbol(SIGNAL_CLICKED)
        words_before_undo = list(stream.words)

        # Remove handler words via a delete edit
        handler_start = len(window_words) + len(button_words) + len(term_words)
        remove_edit = WordStreamEdit(
            op='delete',
            position=handler_start,
            words_before=handler_words,   # 5 words (Bundle 12 4-operand form)
            words_after=[],
            semantic_label='remove handler',
        )
        stream.apply(remove_edit)
        self.assertNotIn(signal_word, stream.words,
                         "Signal word still present after handler removal")
        self.assertEqual(len(stream.words),
                         len(window_words) + len(button_words) + len(term_words))

        # Invert (undo) to restore
        undo_edit = remove_edit.invert()
        stream.apply(undo_edit)
        self.assertIn(signal_word, stream.words,
                      "Signal word missing after undo")
        self.assertEqual(stream.words, words_before_undo,
                         "Undo did not fully restore original stream")

    def test_08_wordstream_subscriber_notified(self):
        """Subscriber callbacks are called after each stream mutation."""
        stream = WordStream()
        calls = []
        stream.subscribe(lambda: calls.append(1))
        stream.apply(WordStreamEdit(op='replace', position=0,
                                    words_before=[], words_after=[1, 2, 3]))
        self.assertEqual(len(calls), 1, "Subscriber not called after apply()")

    def test_09_flow_entries_yields_entry_terminators(self):
        """flow_entries() yields only is_entry=True flow_terminator symbols."""
        stream = WordStream()
        stream._flow_meta = {
            10: {'id': 10, 'kind': 'flow_terminator', 'x': 100, 'y': 200,
                 'label': 'on_click',
                 'properties': [{'name': 'is_entry', 'value': True}]},
            11: {'id': 11, 'kind': 'flow_terminator', 'x': 200, 'y': 200,
                 'label': 'on_close',
                 'properties': [{'name': 'is_entry', 'value': True}]},
            12: {'id': 12, 'kind': 'flow_process', 'x': 150, 'y': 300,
                 'label': 'doWork', 'properties': []},
        }
        entries = list(stream.flow_entries())
        labels = [e[1] for e in entries]
        self.assertIn('on_click', labels)
        self.assertIn('on_close', labels)
        self.assertNotIn('doWork', labels,
                         "flow_process should not appear in flow_entries()")
        self.assertEqual(labels, sorted(labels), "flow_entries() not sorted alphabetically")

    def test_10_handler_words_count(self):
        """Bundle 12: build_redge_handler emits exactly 5 words (4-operand form)."""
        handler_words = build_redge_handler(
            (self.BUTTON_X // GC_SCALE, self.BUTTON_Y // GC_SCALE),
            (self.TERM_X   // GC_SCALE, self.TERM_Y   // GC_SCALE),
            SIGNAL_CLICKED,
        )
        self.assertEqual(len(handler_words), 5,
                         f"Expected 5 handler words, got {len(handler_words)}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
