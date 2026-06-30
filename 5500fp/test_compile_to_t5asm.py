"""test_compile_to_t5asm.py — Unit tests for the FlowCode compiler.

Tests compile_wordstream_to_t5asm() in compile_to_t5asm.py.
Pure unit tests — no subprocess, no tkinter, no display required.

Run:
    cd ~/dev/SkepticusMaximus/TernOO-5500FP/5500fp
    python3 -m unittest test_compile_to_t5asm

Date: 2026-06-23, Adelaide (Phase 7b-4 additions)
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compile_to_t5asm import compile_wordstream_to_t5asm, CompileError
from word_stream import WordStream

# Signal IDs (from widget_lib / flowcode_signals)
_SIGNAL_CLICKED = 300
_SIGNAL_TOGGLED = 301
_SIGNAL_CHANGED = 302


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

        # Dispatch to handler for terminator 10 (Phase 7b-4: CALL not JMP)
        self.assertIn('handler_term_10', out,
                      "Expected handler_term_10 label in output")
        self.assertIn('CALL handler_term_10', out,
                      "Expected CALL to handler_term_10 in hit-test block")

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

        # Block ends with RET (Phase 7b-4: handlers are CALLed, return to caller)
        self.assertIn('RET', handler_section)


    # =========================================================================
    # Phase 7b-4 tests (T16–T26) — walk-up, TOGGLED/CHANGED, layout, state
    # =========================================================================

    # ── T16. Walk-up: binding on parent, child has none → child click fires ─

    def test_16_walkup_binding_on_parent(self):
        """Binding on window (not button) → click button fires handler via walk-up."""
        term = _make_terminator(20, 'From parent', is_entry=True, x=700, y=100)
        # Button has parent_id=1 (window), window has the binding
        win = _make_widget(1, 'gui_window', 10, 10, 600, 300, 'W',
                           signal_ids={_SIGNAL_CLICKED: {'dst_x': 700, 'dst_y': 100}})
        btn = _make_widget(2, 'gui_button', 50, 50, 100, 40, 'Go')
        btn['parent_id'] = 1  # button's parent is the window
        stream = _stream_with_gui(widgets={1: win, 2: btn}, terminators=[term])
        out = compile_wordstream_to_t5asm(stream)

        # Button hit-test must be present (it has an action via walk-up)
        self.assertIn('skip_wid_2', out,
                      "Button (child) must have hit-test even when binding is on parent")
        # Handler for terminator 20 must be emitted
        self.assertIn('handler_term_20', out)
        # Dispatch must be via CALL
        self.assertIn('CALL handler_term_20', out)

    # ── T17. Walk-up: child binding wins over parent binding ─────────────────

    def test_17_walkup_child_wins_over_parent(self):
        """Both parent and child have CLICKED binding → child's handler fires."""
        term_parent = _make_terminator(30, 'Parent handler', is_entry=True, x=700, y=100)
        term_child  = _make_terminator(31, 'Child handler',  is_entry=True, x=700, y=200)
        win = _make_widget(1, 'gui_window', 10, 10, 600, 300, 'W',
                           signal_ids={_SIGNAL_CLICKED: {'dst_x': 700, 'dst_y': 100}})
        btn = _make_widget(2, 'gui_button', 50, 50, 100, 40, 'Go',
                           signal_ids={_SIGNAL_CLICKED: {'dst_x': 700, 'dst_y': 200}})
        btn['parent_id'] = 1
        stream = _stream_with_gui(
            widgets={1: win, 2: btn},
            terminators=[term_parent, term_child])
        out = compile_wordstream_to_t5asm(stream)

        # Button dispatches to child's handler (31), not parent's (30)
        self.assertIn('CALL handler_term_31', out,
                      "Child binding wins: expected dispatch to handler_term_31")
        # Parent handler may appear (window may have its own hit-test) but
        # button's dispatch must NOT go to parent's term
        btn_skip = 'skip_wid_2'
        btn_idx  = out.index(btn_skip)
        btn_block = out[:btn_idx]  # text before skip_wid_2 = the hit-test for widget 2
        self.assertNotIn('CALL handler_term_30', btn_block,
                         "Button block must not dispatch to parent's handler_term_30")

    # ── T18. Walk-up: no binding anywhere → no dispatch, no handler block ──

    def test_18_walkup_no_binding_no_dispatch(self):
        """Widget with no binding in its entire parent chain → no hit-test entry."""
        win = _make_widget(1, 'gui_window', 10, 10, 600, 300, 'W')
        btn = _make_widget(2, 'gui_button', 50, 50, 100, 40, 'Go')
        btn['parent_id'] = 1
        stream = _stream_with_gui(widgets={1: win, 2: btn})
        out = compile_wordstream_to_t5asm(stream)

        self.assertNotIn('skip_wid_2', out,
                         "Button with no binding must not get a hit-test entry")
        self.assertNotIn('handler_term_', out)

    # ── T19. TOGGLED signal — gui_check emits state flip + CALL TOGGLED handler

    def test_19_toggled_dispatch_for_gui_check(self):
        """gui_check with TOGGLED binding → hit-test includes state flip + CALL."""
        term = _make_terminator(40, 'Toggled!', is_entry=True, x=700, y=100)
        chk  = _make_widget(5, 'gui_check', 100, 100, 80, 30, 'Check me',
                             signal_ids={_SIGNAL_TOGGLED: {'dst_x': 700, 'dst_y': 100}})
        stream = _stream_with_gui(widgets={5: chk}, terminators=[term])
        out = compile_wordstream_to_t5asm(stream)

        # Hit-test for widget 5
        self.assertIn('skip_wid_5', out, "Expected hit-test for gui_check")

        # State flip present: SUB R15, R16, R15 (toggle 0↔1)
        self.assertIn('SUB  R15, R16, R15', out, "Expected state flip (SUB)")

        # Dispatch to handler 40
        self.assertIn('CALL handler_term_40', out)

        # Handler block ends with RET
        self.assertIn('handler_term_40:', out)
        idx = out.index('handler_term_40:')
        self.assertIn('RET', out[idx:], "Handler must end with RET")

    # ── T20. CHANGED signal — gui_entry emits key handler + CALL CHANGED ───

    def test_20_changed_dispatch_for_gui_entry(self):
        """gui_entry with CHANGED binding → key handler block + dispatch."""
        term  = _make_terminator(50, 'Changed!', is_entry=True, x=700, y=100)
        entry = _make_widget(6, 'gui_entry', 100, 100, 200, 30, '',
                             signal_ids={_SIGNAL_CHANGED: {'dst_x': 700, 'dst_y': 100}})
        stream = _stream_with_gui(widgets={6: entry}, terminators=[term])
        out = compile_wordstream_to_t5asm(stream)

        # Key handler entry point present
        self.assertIn('handle_key_down', out)
        self.assertIn('key_on_entry_6', out)

        # Append logic: ADD R20, R20, R13 (dynamic address compute)
        self.assertIn('ADD  R20, R20, R13', out)

        # CALL to CHANGED handler
        self.assertIn('CALL handler_term_50', out)

        # Key-down event dispatch in event poll
        self.assertIn('handle_key_down', out)

    # ── T21. State region: toggleable widget gets checked word in data ──────

    def test_21_state_region_toggleable(self):
        """gui_check → state_checked_N label in data section."""
        chk = _make_widget(7, 'gui_check', 50, 50, 80, 30, 'Opt')
        stream = _stream_with_gui(widgets={7: chk})
        out = compile_wordstream_to_t5asm(stream)

        self.assertIn('state_checked_7:', out,
                      "Expected state_checked_7 data label for gui_check #7")

    # ── T22. State region: entry widget gets text buffer in data ────────────

    def test_22_state_region_entry(self):
        """gui_entry → state_text_N and state_textlen_N labels in data section."""
        entry = _make_widget(8, 'gui_entry', 50, 50, 200, 30, 'hello')
        stream = _stream_with_gui(widgets={8: entry})
        out = compile_wordstream_to_t5asm(stream)

        self.assertIn('state_text_8:', out,    "Expected state_text_8 data label")
        self.assertIn('state_textlen_8:', out, "Expected state_textlen_8 data label")
        # Initial text 'hello' (5 chars) initializes the buffer
        self.assertIn('LI   R4, state_text_8', out,
                      "Entry render must use state_text_8 as text pointer")

    # ── T23. LAYOUT_VBOX positions children stacked vertically ──────────────

    def test_23_layout_vbox_positions_children(self):
        """Parent at (100,100) with layout_mode=vbox → children stacked vertically."""
        # Parent window at (100,100), VBOX, h=300
        win = _make_widget(1, 'gui_window', 100, 100, 400, 300, 'W')
        win['layout_mode'] = 'vbox'
        # Three buttons, h=40 each; effective positions should be:
        # btn_A: (104, 104, 100, 40)   (parent.x+4, parent.y+4)
        # btn_B: (104, 148, 100, 40)   (parent.x+4, parent.y+4+40+4)
        # btn_C: (104, 192, 100, 40)   (parent.x+4, parent.y+4+40+4+40+4)
        btn_a = _make_widget(2, 'gui_button', 0, 0, 100, 40, 'A')
        btn_b = _make_widget(3, 'gui_button', 0, 0, 100, 40, 'B')
        btn_c = _make_widget(4, 'gui_button', 0, 0, 100, 40, 'C')
        btn_a['parent_id'] = btn_b['parent_id'] = btn_c['parent_id'] = 1
        stream = _stream_with_gui(
            widgets={1: win, 2: btn_a, 3: btn_b, 4: btn_c})
        out = compile_wordstream_to_t5asm(stream)

        # btn_A y should be 104 (parent.y + padding = 100 + 4)
        self.assertIn('LI   R3, 104', out,
                      "VBOX first child y should be parent.y + 4 = 104")
        # btn_B y should be 148 (104 + 40 + 4)
        self.assertIn('LI   R3, 148', out,
                      "VBOX second child y should be 148")
        # btn_C y should be 192 (148 + 40 + 4)
        self.assertIn('LI   R3, 192', out,
                      "VBOX third child y should be 192")

    # ── T24. LAYOUT_HBOX positions children horizontally ────────────────────

    def test_24_layout_hbox_positions_children(self):
        """Parent at (50,50) with layout_mode=hbox → children stacked horizontally."""
        win = _make_widget(1, 'gui_window', 50, 50, 400, 200, 'W')
        win['layout_mode'] = 'hbox'
        # Two buttons w=80 each:
        # btn_A: (54, 54, 80, 40)   (parent.x+4, parent.y+4)
        # btn_B: (138, 54, 80, 40)  (parent.x+4+80+4, parent.y+4)
        btn_a = _make_widget(2, 'gui_button', 0, 0, 80, 40, 'X')
        btn_b = _make_widget(3, 'gui_button', 0, 0, 80, 40, 'Y')
        btn_a['parent_id'] = btn_b['parent_id'] = 1
        stream = _stream_with_gui(
            widgets={1: win, 2: btn_a, 3: btn_b})
        out = compile_wordstream_to_t5asm(stream)

        # btn_A x = 54 (parent.x + 4)
        self.assertIn('LI   R2, 54', out,
                      "HBOX first child x should be parent.x + 4 = 54")
        # btn_B x = 138 (54 + 80 + 4)
        self.assertIn('LI   R2, 138', out,
                      "HBOX second child x should be 138")

    # ── T25. LAYOUT_ABSOLUTE adds parent + child positions ──────────────────

    def test_25_layout_absolute_adds_positions(self):
        """Window at (100,100) absolute + button at (50,50) → button at (150,150)."""
        win = _make_widget(1, 'gui_window', 100, 100, 400, 300, 'W')
        # default layout_mode is 'absolute'
        btn = _make_widget(2, 'gui_button', 50, 50, 100, 40, 'B',
                           signal_ids={_SIGNAL_CLICKED: {'dst_x': 700, 'dst_y': 200}})
        btn['parent_id'] = 1
        term = _make_terminator(60, 'OK', is_entry=True, x=700, y=200)
        stream = _stream_with_gui(widgets={1: win, 2: btn}, terminators=[term])
        out = compile_wordstream_to_t5asm(stream)

        # Effective x=150 and y=150 should appear in the output
        # (in both render and hit-test)
        self.assertIn('LI   R2, 150', out,
                      "LAYOUT_ABSOLUTE: effective x = parent.x + child.x = 150")
        self.assertIn('LI   R3, 150', out,
                      "LAYOUT_ABSOLUTE: effective y = parent.y + child.y = 150")

    # ── T26. Comprehensive fixture: VBOX window + check + entry + button ────

    def test_26_comprehensive_vbox_fixture(self):
        """Window/VBOX containing gui_check, gui_entry, gui_button all with bindings."""
        term_chk = _make_terminator(70, 'Box toggled', is_entry=True, x=700, y=100)
        term_ent = _make_terminator(71, 'Text changed', is_entry=True, x=700, y=200)
        term_btn = _make_terminator(72, 'Button hit',  is_entry=True, x=700, y=300)

        win = _make_widget(1, 'gui_window', 100, 100, 400, 300, 'Demo')
        win['layout_mode'] = 'vbox'

        chk = _make_widget(2, 'gui_check', 0, 0, 200, 30, 'Enable',
                           signal_ids={_SIGNAL_TOGGLED: {'dst_x': 700, 'dst_y': 100}})
        ent = _make_widget(3, 'gui_entry', 0, 0, 200, 30, '',
                           signal_ids={_SIGNAL_CHANGED: {'dst_x': 700, 'dst_y': 200}})
        btn = _make_widget(4, 'gui_button', 0, 0, 100, 40, 'Go',
                           signal_ids={_SIGNAL_CLICKED: {'dst_x': 700, 'dst_y': 300}})
        chk['parent_id'] = ent['parent_id'] = btn['parent_id'] = 1

        stream = _stream_with_gui(
            widgets={1: win, 2: chk, 3: ent, 4: btn},
            terminators=[term_chk, term_ent, term_btn])
        out = compile_wordstream_to_t5asm(stream)

        # All three handlers emitted
        self.assertIn('handler_term_70:', out)
        self.assertIn('handler_term_71:', out)
        self.assertIn('handler_term_72:', out)

        # All three state allocations
        self.assertIn('state_checked_2:', out)
        self.assertIn('state_text_3:', out)
        self.assertIn('state_textlen_3:', out)

        # Key handler present (entry exists)
        self.assertIn('handle_key_down', out)

        # CALL dispatch for each
        self.assertIn('CALL handler_term_70', out)
        self.assertIn('CALL handler_term_71', out)
        self.assertIn('CALL handler_term_72', out)

        # VBOX: check (child 2) at y = parent.y + 4 = 104
        self.assertIn('LI   R3, 104', out, "VBOX first child y = 104")

        # All handlers end with RET (search from each handler label to end)
        for tid in (70, 71, 72):
            idx = out.index(f'handler_term_{tid}:')
            next_handler = out.find('handler_term_', idx + 1)
            segment = out[idx:next_handler] if next_handler != -1 else out[idx:]
            self.assertIn('RET', segment,
                          f"handler_term_{tid} must end with RET")


if __name__ == '__main__':
    unittest.main(verbosity=2)


class TestStage83RTStaticCells(unittest.TestCase):
    """Stage 8-3-RT: static formula cells compile to state-region literals."""

    def _stream(self, cells, with_gui=True):
        s = WordStream()
        if with_gui:
            s._widget_meta = {0: _make_widget(0, 'gui_window', 0, 0, 400, 300, 'W')}
        s._cell_meta = cells
        return s

    def test_static_formula_literals(self):
        s = self._stream({
            (0, 0): {'id': 1, 'kind': 'cell_formula', 'row': 0, 'col': 0,
                     'name': 'cell_A1', 'value': '=2+3'},
            (1, 0): {'id': 2, 'kind': 'cell_formula', 'row': 1, 'col': 0,
                     'name': 'cell_A2', 'value': '=A1*10'}})
        asm = compile_wordstream_to_t5asm(s, 'sheet.fc')
        self.assertIn('state_cell_1:', asm)
        self.assertRegex(asm, r'state_cell_1:\s*\n\s*\.word 5\b')
        self.assertRegex(asm, r'state_cell_2:\s*\n\s*\.word 50\b')
        self.assertIn('cellstr_1', asm)   # draw-text label
        self.assertIn('cellstr_2', asm)

    def test_dynamic_cell_placeholder(self):
        s = self._stream({
            (0, 0): {'id': 1, 'kind': 'cell_formula', 'row': 0, 'col': 0,
                     'name': 'cell_A1', 'value': '=WIDGET("x").label'}})
        asm = compile_wordstream_to_t5asm(s, 'sheet.fc')
        # dynamic → placeholder 0 in the state region
        self.assertRegex(asm, r'state_cell_1:\s*\n\s*\.word 0\b')
        self.assertIn('dynamic(placeholder)', asm)

    def test_cells_only_compiles(self):
        s = self._stream({(0, 0): {'id': 1, 'kind': 'cell_value', 'row': 0,
                                   'col': 0, 'name': 'cell_A1', 'value': '42'}},
                         with_gui=False)
        asm = compile_wordstream_to_t5asm(s, 'sheet.fc')
        self.assertIn('state_cell_1:', asm)
        self.assertRegex(asm, r'state_cell_1:\s*\n\s*\.word 42\b')
        # Cells route to the full PIGART path (window-open syscall), not trivial.
        self.assertIn('event_loop_top:', asm)
        self.assertIn('LI   R1, 100', asm)   # PIGART_OPEN_WINDOW


class TestStage83RTDynamicCells(unittest.TestCase):
    """Stage 8-3-RT-dynamic (Part 3): recompute subroutines + per-frame trigger."""

    def _stream(self):
        s = WordStream()
        s._widget_meta = {
            0: _make_widget(0, 'gui_window', 0, 0, 400, 300, 'W'),
            1: dict(_make_widget(1, 'gui_toggle', 20, 40, 80, 30, 'T'),
                    name='t1', properties=[{'name': 'checked', 'value': False}]),
        }
        s._cell_meta = {
            (0, 0): {'id': 5, 'kind': 'cell_formula', 'row': 0, 'col': 0,
                     'name': 'cell_A1', 'value': '=WIDGET("t1").checked * 100'}}
        return s

    def test_recompute_subroutine_emitted(self):
        asm = compile_wordstream_to_t5asm(self._stream(), 'd.fc')
        self.assertIn('recompute_cell_5:', asm)
        self.assertIn('recompute_all_cells:', asm)
        self.assertIn('STW  R21, R20', asm)          # store result to state slot

    def test_recompute_called_each_frame(self):
        asm = compile_wordstream_to_t5asm(self._stream(), 'd.fc')
        self.assertIn('CALL recompute_all_cells', asm)

    def test_static_unaffected(self):
        # A purely static formula stays a literal — no recompute subroutine.
        s = WordStream()
        s._widget_meta = {0: _make_widget(0, 'gui_window', 0, 0, 400, 300, 'W')}
        s._cell_meta = {(0, 0): {'id': 9, 'kind': 'cell_formula', 'row': 0,
                                 'col': 0, 'name': 'cell_A1', 'value': '=2+3'}}
        asm = compile_wordstream_to_t5asm(s, 'd.fc')
        self.assertNotIn('recompute_cell_9:', asm)
        self.assertRegex(asm, r'state_cell_9:\s*\n\s*\.word 5\b')


class TestStage88RTSignalLast(unittest.TestCase):
    """Stage 8-8-RT (Part 6): SIGNAL_LAST live signal slots."""

    def _stream(self):
        s = WordStream()
        s._widget_meta = {
            0: _make_widget(0, 'gui_window', 0, 0, 400, 300, 'W'),
            1: dict(_make_widget(1, 'gui_button', 20, 40, 80, 30, 'B'), name='btn1'),
        }
        s._cell_meta = {(0, 0): {'id': 5, 'kind': 'cell_formula', 'row': 0,
                                 'col': 0, 'name': 'cell_A1',
                                 'value': '=SIGNAL_LAST("btn1_clicked")'}}
        return s

    def test_signal_slot_and_counter(self):
        asm = compile_wordstream_to_t5asm(self._stream(), 'd.fc')
        self.assertIn('state_signal_last_btn1_clicked:', asm)
        self.assertIn('fire counter', asm)                  # incremented on click
        self.assertIn('recompute_cell_5:', asm)             # cell reads the slot
        self.assertIn('state_signal_last_btn1_clicked', asm)


class TestStage85RTWriteBack(unittest.TestCase):
    """Stage 8-5-RT (Part 5): runtime cell↔widget write-back."""

    def test_toggle_writes_bound_cell(self):
        s = WordStream()
        s._widget_meta = {
            0: _make_widget(0, 'gui_window', 0, 0, 400, 300, 'W'),
            1: dict(_make_widget(1, 'gui_toggle', 20, 40, 80, 30, 'T'), name='tog',
                    properties=[{'name': 'checked', 'value': False},
                                {'name': 'bind_value_to', 'value': 'cell_input'}]),
        }
        s._cell_meta = {(0, 0): {'id': 5, 'kind': 'cell_value', 'row': 0,
                                 'col': 0, 'name': 'cell_input', 'value': '0'}}
        asm = compile_wordstream_to_t5asm(s, 'd.fc')
        self.assertIn('write-back to cell_input', asm)
        self.assertIn('state_cell_5', asm)

    def test_no_quotes_or_unicode_in_emitted_comments(self):
        # Assembler tokenizer mis-handles quotes/unicode in comments — keep ASCII.
        s = WordStream()
        s._widget_meta = {0: _make_widget(0, 'gui_window', 0, 0, 400, 300, 'W')}
        s._cell_meta = {(0, 0): {'id': 5, 'kind': 'cell_formula', 'row': 0,
                                 'col': 0, 'name': 'cell_A1',
                                 'value': '=WIDGET("x").checked'}}
        asm = compile_wordstream_to_t5asm(s, 'd.fc')
        self.assertNotIn('"', asm.split('; ============ Data')[0])  # no quotes in code
        self.assertNotIn('→', asm)
