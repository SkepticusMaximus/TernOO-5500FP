"""test_compile_to_t5asm.py — Unit tests for the FlowCode compiler.

Tests compile_wordstream_to_t5asm() in compile_to_t5asm.py.
Pure unit tests — no subprocess, no tkinter, no display required.

Run:
    cd ~/dev/SkepticusMaximus/TernOO-5500FP/5500fp
    python3 -m unittest test_compile_to_t5asm

Date: 2026-06-22, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compile_to_t5asm import compile_wordstream_to_t5asm, CompileError
from word_stream import WordStream

# SIGNAL_CLICKED = 300 (from flowcode_signals / widget_lib)
_SIGNAL_CLICKED = 300


# ---------------------------------------------------------------------------
# Helpers — flow-only (Phase 7b-1 fixtures)
# ---------------------------------------------------------------------------

def _make_terminator(tid: int, label: str, is_entry: bool,
                     x: int = 100, y: int = 100) -> dict:
    """Return a flow_terminator symbol dict matching the fc_state schema."""
    return {
        'id':   tid,
        'kind': 'flow_terminator',
        'x': x, 'y': y, 'w': 120, 'h': 60,
        'label': label,
        'properties': [{'name': 'is_entry', 'value': is_entry}],
    }


def _stream_with(*terminators) -> WordStream:
    """Return a WordStream whose _flow_meta is populated with the given terminator dicts."""
    stream = WordStream()
    for sym in terminators:
        stream._flow_meta[sym['id']] = sym
    return stream


# ---------------------------------------------------------------------------
# Helpers — GUI + flow (Phase 7b-3 fixtures)
# ---------------------------------------------------------------------------

def _make_widget(wid: int, kind: str, x: int, y: int, w: int, h: int,
                 label: str = '', signal_ids: dict = None) -> dict:
    """Return a gui widget dict matching the fc_state['widgets'] schema."""
    return {
        'id':          wid,
        'kind':        kind,
        'x':           x, 'y': y,
        'w':           w, 'h': h,
        'label':       label,
        'parent_id':   None,
        'layout_mode': 'absolute',
        'properties':  [],
        'signal_ids':  dict(signal_ids) if signal_ids else {},
    }


def _stream_with_gui(widgets: dict = None, terminators: list = None) -> WordStream:
    """Return a WordStream with _widget_meta and _flow_meta populated.

    Args:
        widgets:     {widget_id: widget_dict} — populates _widget_meta.
        terminators: list of terminator dicts — populates _flow_meta.
    """
    stream = WordStream()
    for wid, w in (widgets or {}).items():
        stream._widget_meta[wid] = w
    for sym in (terminators or []):
        stream._flow_meta[sym['id']] = sym
    return stream


# ---------------------------------------------------------------------------
# Phase 7b-1 tests (T1–T7) — trivial print-and-halt path
# ---------------------------------------------------------------------------

class TestCompileToT5Asm(unittest.TestCase):

    # ── T1. Single entry terminator, simple label ─────────────────────────

    def test_01_simple_label(self):
        """Single entry terminator 'Hi' → PRINT_CHAR H(72) i(105), PRINT_NL, HALT."""
        stream = _stream_with(_make_terminator(0, 'Hi', is_entry=True))
        out    = compile_wordstream_to_t5asm(stream, source_path='test.ternoo')
        self.assertIn('LI   R2, 72', out,
                      "Expected LI R2, 72 for 'H' (ASCII 72)")
        self.assertIn('LI   R2, 105', out,
                      "Expected LI R2, 105 for 'i' (ASCII 105)")
        self.assertIn('LI   R1, 6', out,
                      "Expected LI R1, 6 for PRINT_NL")
        self.assertIn('HALT', out)

    # ── T2. Empty label → only PRINT_NL + HALT, no PRINT_CHAR ───────────

    def test_02_empty_label(self):
        """Entry terminator with empty label → PRINT_NL + HALT, no LI R2."""
        stream = _stream_with(_make_terminator(0, '', is_entry=True))
        out    = compile_wordstream_to_t5asm(stream)
        # No character load: LI R1, 3 (PRINT_CHAR) must be absent
        self.assertNotIn('LI   R1, 3', out,
                         "SYSCALL PRINT_CHAR should not appear for empty label")
        self.assertIn('LI   R1, 6', out)
        self.assertIn('HALT', out)

    # ── T3. No entry terminator → CompileError ───────────────────────────

    def test_03_no_entry_raises_compile_error(self):
        """Terminator with is_entry=False → CompileError."""
        stream = _stream_with(_make_terminator(0, 'Should not compile', is_entry=False))
        with self.assertRaises(CompileError) as ctx:
            compile_wordstream_to_t5asm(stream)
        self.assertIn('entry', str(ctx.exception).lower())

    # ── T4. Multiple entries — first (insertion order) wins ──────────────

    def test_04_multiple_entries_first_wins(self):
        """Two entry terminators: 'First' and 'Second' — 'First' (id=0) wins."""
        stream = _stream_with(
            _make_terminator(0, 'First',  is_entry=True, x=100, y=100),
            _make_terminator(1, 'Second', is_entry=True, x=300, y=100),
        )
        out = compile_wordstream_to_t5asm(stream)
        # 'F' = 70
        self.assertIn('LI   R2, 70', out,
                      "Expected 'F' (70) from 'First', not from 'Second'")
        # 'S' = 83 — must NOT appear (would mean 'Second' was compiled)
        self.assertNotIn('LI   R2, 83', out,
                         "'S' (83) should not appear — 'Second' is not the first entry")

    # ── T5. Header block present ─────────────────────────────────────────

    def test_05_header_block_present(self):
        """Output starts with comment lines including timestamp, source, entry info."""
        stream = _stream_with(_make_terminator(0, 'Test', is_entry=True))
        out    = compile_wordstream_to_t5asm(stream, source_path='/designs/test.ternoo')
        lines  = out.splitlines()
        self.assertTrue(lines[0].startswith('; Auto-generated'),
                        f"First line should start with '; Auto-generated', got: {lines[0]!r}")
        combined = '\n'.join(lines[:8])
        self.assertIn('test.ternoo', combined, "source filename missing from header")
        self.assertIn('Generated:', combined,  "Generated timestamp missing from header")
        self.assertIn('Test',       combined,  "Entry label missing from header")

    # ── T6. Empty stream → CompileError ──────────────────────────────────

    def test_06_empty_stream_raises_compile_error(self):
        """WordStream with no flow_meta symbols → CompileError."""
        stream = WordStream()   # _flow_meta is {} by default
        with self.assertRaises(CompileError):
            compile_wordstream_to_t5asm(stream)

    # ── T7. Unicode label — code points emitted ───────────────────────────

    def test_07_unicode_label(self):
        """Unicode label 'héllo' — each character's code point is emitted."""
        stream = _stream_with(_make_terminator(0, 'héllo', is_entry=True))
        out    = compile_wordstream_to_t5asm(stream)
        self.assertIn('LI   R2, 104', out, "Expected 104 for 'h'")
        self.assertIn('LI   R2, 233', out, "Expected 233 for 'é'")
        self.assertIn('LI   R2, 108', out, "Expected 108 for 'l'")
        self.assertIn('HALT', out)

    # =========================================================================
    # Phase 7b-3 tests (T8–T15) — PIGART full-program path
    # =========================================================================

    # ── T8. Window-only: no other widgets, no flow entries ────────────────

    def test_08_window_only_gui_path(self):
        """Stream with one gui_window → Phase 7b-3 path: OPEN_WINDOW + event loop."""
        stream = _stream_with_gui(
            widgets={1: _make_widget(1, 'gui_window', 10, 10, 600, 300, 'Demo')})
        out = compile_wordstream_to_t5asm(stream)

        # Must take the Phase 7b-3 path
        self.assertIn(f'LI   R1, 100', out,   # PIGART_OPEN_WINDOW
                      "Expected LI R1, 100 (OPEN_WINDOW)")
        self.assertIn('event_loop_top', out,
                      "Expected event_loop_top label in output")
        self.assertIn('no_event_this_tick', out)
        self.assertIn('exit_prog', out)

        # No handler blocks (no bindings)
        self.assertNotIn('handler_term_', out)

        # No HALT in the traditional 7b-1 sense (the program loops until close)
        # The only HALT is in exit_prog after CLOSE_WINDOW
        self.assertIn('HALT', out)   # exits cleanly via exit_prog

    # ── T9. Button without handler: renders, no hit-test entry ───────────

    def test_09_button_without_handler(self):
        """Button with no binding → renders (DRAW_RECT), no hit-test entry, no handler."""
        widgets = {
            1: _make_widget(1, 'gui_window', 10, 10, 600, 300, ''),
            2: _make_widget(2, 'gui_button', 250, 130, 100, 40, 'Go'),
        }
        stream = _stream_with_gui(widgets=widgets)
        out = compile_wordstream_to_t5asm(stream)

        # Button renders via DRAW_RECT (syscall 102)
        self.assertIn('LI   R1, 102', out, "Expected DRAW_RECT (102) for button")

        # No hit-test skip label for widget 2 (it has no binding)
        self.assertNotIn('skip_wid_2', out,
                         "No hit-test entry expected for unbound button")
        self.assertNotIn('handler_term_', out,
                         "No handler block expected when button has no binding")

    # ── T10. Button with handler: hit-test + handler block ────────────────

    def test_10_button_with_handler(self):
        """Button bound to a terminator → hit-test skip label + JMP to handler."""
        term = _make_terminator(10, 'You pressed it!', is_entry=True, x=700, y=200)
        widgets = {
            1: _make_widget(1, 'gui_window', 10, 10, 600, 300, ''),
            2: _make_widget(2, 'gui_button', 250, 130, 100, 40, 'Press Me',
                            signal_ids={_SIGNAL_CLICKED: {'dst_x': 700, 'dst_y': 200}}),
        }
        stream = _stream_with_gui(widgets=widgets, terminators=[term])
        out = compile_wordstream_to_t5asm(stream)

        # Hit-test labels for widget 2
        self.assertIn('skip_wid_2', out,
                      "Expected skip_wid_2 label in hit-test block")

        # Jump to handler for terminator 10
        self.assertIn('handler_term_10', out,
                      "Expected handler_term_10 label in output")
        self.assertIn('JMP  handler_term_10', out,
                      "Expected JMP to handler_term_10 in hit-test block")

        # Handler block emitted once
        self.assertGreaterEqual(out.count('handler_term_10:'), 1,
                                "Expected handler_term_10: label definition")

    # ── T11. Multiple buttons, same handler → single handler block ─────────

    def test_11_multiple_buttons_same_handler_dedup(self):
        """Two buttons bound to the same terminator → two hit-tests, one handler block."""
        binding = {_SIGNAL_CLICKED: {'dst_x': 700, 'dst_y': 200}}
        term    = _make_terminator(10, 'Shared', is_entry=True, x=700, y=200)
        widgets = {
            1: _make_widget(1, 'gui_button', 100, 100, 100, 40, 'A',
                            signal_ids=binding),
            2: _make_widget(2, 'gui_button', 300, 100, 100, 40, 'B',
                            signal_ids=binding),
        }
        stream = _stream_with_gui(widgets=widgets, terminators=[term])
        out = compile_wordstream_to_t5asm(stream)

        # Both skip labels present (two hit-tests)
        self.assertIn('skip_wid_1', out)
        self.assertIn('skip_wid_2', out)

        # Exactly one handler block definition
        self.assertEqual(out.count('handler_term_10:'), 1,
                         "handler_term_10: must appear exactly once (deduplicated)")

    # ── T12. Stream order in hit-test: reverse iteration (topmost first) ──

    def test_12_hit_test_reverse_stream_order(self):
        """Widgets with bindings are hit-tested in reverse stream order (topmost wins)."""
        term1 = _make_terminator(10, 'First',  is_entry=True, x=700, y=100)
        term2 = _make_terminator(11, 'Second', is_entry=True, x=700, y=200)
        # Widget 1 inserted before widget 2 → widget 2 is "topmost" (drawn last)
        widgets = {
            1: _make_widget(1, 'gui_button', 100, 100, 100, 40, 'A',
                            signal_ids={_SIGNAL_CLICKED: {'dst_x': 700, 'dst_y': 100}}),
            2: _make_widget(2, 'gui_button', 200, 100, 100, 40, 'B',
                            signal_ids={_SIGNAL_CLICKED: {'dst_x': 700, 'dst_y': 200}}),
        }
        stream = _stream_with_gui(widgets=widgets, terminators=[term1, term2])
        out = compile_wordstream_to_t5asm(stream)

        # skip_wid_2 must appear BEFORE skip_wid_1 in the output
        pos_skip2 = out.index('skip_wid_2')
        pos_skip1 = out.index('skip_wid_1')
        self.assertLess(pos_skip2, pos_skip1,
                        "Widget 2 (topmost = last drawn) should be hit-tested first "
                        f"but skip_wid_2 at {pos_skip2} vs skip_wid_1 at {pos_skip1}")

    # ── T13. Backward compat: entry-only stream → 7b-1 path ──────────────

    def test_13_backward_compat_trivial_path(self):
        """Stream with only flow_meta (no gui_* widgets) falls back to Phase 7b-1."""
        stream = _stream_with(_make_terminator(0, 'Hello', is_entry=True))
        out = compile_wordstream_to_t5asm(stream)

        # 7b-1 path: no OPEN_WINDOW (syscall 100)
        self.assertNotIn('LI   R1, 100', out,
                         "OPEN_WINDOW should NOT appear in 7b-1 fallback path")
        # 7b-1 path: no event loop
        self.assertNotIn('event_loop_top', out)
        # 7b-1 path: prints 'H' (72)
        self.assertIn('LI   R2, 72', out, "Expected 'H' (72) in 7b-1 output")
        self.assertIn('HALT', out)

    # ── T14. No gui_window → defaults to 800×600 ─────────────────────────

    def test_14_no_window_defaults_800x600(self):
        """Stream with gui_* widgets but no gui_window → OPEN_WINDOW uses 800×600."""
        widgets = {
            1: _make_widget(1, 'gui_button', 100, 100, 100, 40, 'Click'),
        }
        stream = _stream_with_gui(widgets=widgets)
        out = compile_wordstream_to_t5asm(stream)

        # Should be in the Phase 7b-3 path
        self.assertIn('LI   R1, 100', out, "Expected OPEN_WINDOW (100)")

        # Default width 800 and height 600
        self.assertIn('LI   R2, 800', out,
                      "Expected default window width 800")
        self.assertIn('LI   R3, 600', out,
                      "Expected default window height 600")

    # ── T15. Handler block emits correct PRINT_CHAR for "Hi" ─────────────

    def test_15_handler_block_print_char_sequence(self):
        """Handler block for terminator 'Hi' contains LI R2, 72 ('H') and LI R2, 105 ('i')."""
        term = _make_terminator(5, 'Hi', is_entry=True, x=500, y=200)
        widgets = {
            1: _make_widget(1, 'gui_button', 100, 100, 100, 40, 'Press',
                            signal_ids={_SIGNAL_CLICKED: {'dst_x': 500, 'dst_y': 200}}),
        }
        stream = _stream_with_gui(widgets=widgets, terminators=[term])
        out = compile_wordstream_to_t5asm(stream)

        # Locate the handler block
        self.assertIn('handler_term_5:', out)
        handler_idx     = out.index('handler_term_5:')
        handler_section = out[handler_idx:]

        # 'H' = 72, 'i' = 105
        self.assertIn('LI   R2, 72', handler_section,
                      "Expected LI R2, 72 for 'H' in handler_term_5 block")
        self.assertIn('LI   R2, 105', handler_section,
                      "Expected LI R2, 105 for 'i' in handler_term_5 block")

        # Block ends with JMP back to event loop
        self.assertIn('JMP  event_loop_top', handler_section)


if __name__ == '__main__':
    unittest.main(verbosity=2)
