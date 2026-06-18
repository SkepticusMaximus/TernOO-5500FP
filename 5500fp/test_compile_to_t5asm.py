"""test_compile_to_t5asm.py — Unit tests for the FlowCode compiler.

Tests compile_wordstream_to_t5asm() in compile_to_t5asm.py.
Pure unit tests — no subprocess, no tkinter, no display required.

Run:
    cd ~/dev/SkepticusMaximus/TernOO-5500FP/5500fp
    python3 -m unittest test_compile_to_t5asm

Date: 2026-06-19, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from compile_to_t5asm import compile_wordstream_to_t5asm, CompileError
from word_stream import WordStream


# ---------------------------------------------------------------------------
# Helpers — build minimal WordStream fixtures with flow_meta injected
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
# Test suite
# ---------------------------------------------------------------------------

class TestCompileToT5Asm(unittest.TestCase):

    # ── 1. Single entry terminator, simple label ──────────────────────────

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

    # ── 2. Empty label → only PRINT_NL + HALT, no PRINT_CHAR ─────────────

    def test_02_empty_label(self):
        """Entry terminator with empty label → PRINT_NL + HALT, no LI R2."""
        stream = _stream_with(_make_terminator(0, '', is_entry=True))
        out    = compile_wordstream_to_t5asm(stream)
        # No character load: LI R1, 3 (PRINT_CHAR) and LI R2 lines must be absent
        self.assertNotIn('LI   R1, 3', out,
                         "SYSCALL PRINT_CHAR should not appear for empty label")
        self.assertIn('LI   R1, 6', out)
        self.assertIn('HALT', out)

    # ── 3. No entry terminator → CompileError ────────────────────────────

    def test_03_no_entry_raises_compile_error(self):
        """Terminator with is_entry=False → CompileError."""
        stream = _stream_with(_make_terminator(0, 'Should not compile', is_entry=False))
        with self.assertRaises(CompileError) as ctx:
            compile_wordstream_to_t5asm(stream)
        self.assertIn('entry', str(ctx.exception).lower())

    # ── 4. Multiple entries — first (lowest id / insertion order) wins ────

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

    # ── 5. Header block present ───────────────────────────────────────────

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

    # ── 6. Empty stream → CompileError ────────────────────────────────────

    def test_06_empty_stream_raises_compile_error(self):
        """WordStream with no flow_meta symbols → CompileError."""
        stream = WordStream()   # _flow_meta is {} by default
        with self.assertRaises(CompileError):
            compile_wordstream_to_t5asm(stream)

    # ── 7. Unicode label — code points emitted ────────────────────────────

    def test_07_unicode_label(self):
        """Unicode label 'héllo' — each character's code point is emitted.

        Note: the C emulator's PRINT_CHAR does `putchar(arg & 0x7F)` so only
        the low 7 bits are printed. The compiler emits the full Unicode code
        point. For ASCII-range chars this is identical; for non-ASCII (é=233)
        the emitted value is truncated by the engine. This is a known MVP
        limitation (TODO: multi-byte UTF-8 encoding for Phase 7b-3+).
        """
        stream = _stream_with(_make_terminator(0, 'héllo', is_entry=True))
        out    = compile_wordstream_to_t5asm(stream)
        # 'h' = 104
        self.assertIn('LI   R2, 104', out, "Expected 104 for 'h'")
        # 'é' = 233 (Unicode code point; engine will truncate to 233 & 0x7F = 105)
        self.assertIn('LI   R2, 233', out, "Expected 233 for 'é'")
        # 'l' = 108
        self.assertIn('LI   R2, 108', out, "Expected 108 for 'l'")
        self.assertIn('HALT', out)


if __name__ == '__main__':
    unittest.main(verbosity=2)
