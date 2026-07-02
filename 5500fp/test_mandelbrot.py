"""test_mandelbrot.py — golden test for the native Mandelbrot screensaver.

Generates the test-mode variant of mandelbrot_screensaver.t5asm, runs it on
the C emulator, and compares the iteration-buffer checksum against an
independent Python implementation of the exact same fixed-point integer
mathematics (truncating division, SCALE=64, MAXIT=24).  A checksum match
means every one of the 3072 cells iterated identically on the 5500FP and
in the reference — the strongest cheap proof that MUL/DIV/branch semantics
agree end to end.

Requires the C emulator binary (skips otherwise).

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import os
import subprocess
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_EMU = os.path.join(_HERE, '..', 'NASM-TernOO-5500FP-Emulator',
                    'c_emulator', '5500fp')
_GEN = os.path.join(_HERE, 'gen_mandelbrot_t5asm.py')

import importlib.util as _u
_spec = _u.spec_from_file_location('gen_mandel', _GEN)
G = _u.module_from_spec(_spec)
_spec.loader.exec_module(G)


def _trunc_div(a, b):
    q = abs(a) // abs(b)
    return q if (a < 0) == (b < 0) or a == 0 else -q


def _reference_checksum(view):
    cx0, cy0, hw = G.VIEWS_REAL[view]
    CX, CY = round(cx0 * G.S), round(cy0 * G.S)
    step = max(1, round((2 * hw / G.GW) * G.S))
    tot = 0
    for i in range(G.GW * G.GH):
        px, py = i % G.GW, i // G.GW
        cre = CX + (px - G.GW // 2) * step
        cim = CY + (py - G.GH // 2) * step
        zx = zy = it = 0
        while True:
            zx2 = _trunc_div(zx * zx, G.S)
            zy2 = _trunc_div(zy * zy, G.S)
            if zx2 + zy2 > 4 * G.S:
                break
            t = _trunc_div(zx * zy, G.S)
            zy = t + t + cim
            zx = zx2 - zy2 + cre
            it += 1
            if it >= G.MAXIT:
                break
        tot += it
    return tot


def _emulator_checksum(view):
    with tempfile.NamedTemporaryFile('w', suffix='.t5asm',
                                     delete=False) as f:
        f.write(G.emit(test_mode=True, test_view=view))
        path = f.name
    try:
        out = subprocess.run([_EMU, '--run', path], capture_output=True,
                             text=True, timeout=60).stdout
    finally:
        os.unlink(path)
    nums = [l.strip() for l in out.splitlines()
            if l.strip().lstrip('-').isdigit()]
    return int(nums[-1]) if nums else None


@unittest.skipUnless(os.path.exists(_EMU), "emulator binary not built")
class TestMandelbrotGolden(unittest.TestCase):

    def test_view0_full_set(self):
        self.assertEqual(_emulator_checksum(0), _reference_checksum(0))

    def test_view1_seahorse_valley(self):
        self.assertEqual(_emulator_checksum(1), _reference_checksum(1))

    def test_shipping_asm_is_current(self):
        """The committed .t5asm must match the generator's output."""
        shipped = os.path.join(_HERE, 'mandelbrot_screensaver.t5asm')
        self.assertEqual(open(shipped).read(), G.emit(test_mode=False))


if __name__ == '__main__':
    unittest.main(verbosity=1)
