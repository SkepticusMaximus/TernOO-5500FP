"""test_ghost.py — GHOST First Breath golden verification.

Law 1 (golden): the emulator's forward pass equals ghost_train.ref_forward
bit-for-bit — class index AND margin — over the eval set.
Law 2 (floor): held-out routing accuracy >= 90%.
Law 3 (humility): out-of-domain phrases refuse (route to none).
Law 4 (words): the exported model decodes as NEURAL_CONNECTION words.

Date: 2026-07-05, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""
import importlib.util as _ilu
import json
import os
import subprocess
import tempfile
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = _load('ghost_train')
GEN = _load('gen_ghost_t5asm')
_EMU = os.path.join(_here, '..', 'NASM-TernOO-5500FP-Emulator',
                    'c_emulator', '5500fp')
_MODEL = os.path.join(_here, 'ghost_model.json')


def _emu_forward(text, model):
    asm = GEN.emit_forward(text, model)
    with tempfile.NamedTemporaryFile('w', suffix='.t5asm', delete=False) as f:
        f.write(asm); path = f.name
    try:
        out = subprocess.run([_EMU, '--run', path], capture_output=True,
                             text=True, timeout=60).stdout
    finally:
        os.unlink(path)
    nums = [int(l) for l in out.splitlines()
            if l.strip().lstrip('-').isdigit()]
    return nums[0], nums[1]


@unittest.skipUnless(os.path.exists(_EMU) and os.path.exists(_MODEL),
                     "emulator or model missing")
class TestGhostGolden(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = json.load(open(_MODEL))
        cls.W1, cls.W2 = cls.m['W1'], cls.m['W2']

    EVAL = ['make this loud', 'lowercase the message', 'add 4 and 5',
            'sort my shopping list', 'reverse the polarity',
            'how long is my string', 'remainder of 22 divided by 7',
            'open the pod bay doors', 'remove duplicates from the list',
            'what is variable x', 'bring me a shrubbery']

    def test_golden_bit_exact(self):
        for text in self.EVAL:
            with self.subTest(text=text):
                ref_cls, ref_margin, _ = G.ref_forward(text, self.W1, self.W2)
                emu_cls, emu_margin = _emu_forward(text, self.m)
                self.assertEqual((emu_cls, emu_margin),
                                 (ref_cls, ref_margin),
                                 f"emulator diverged on {text!r}")

    def test_accuracy_floor(self):
        _, held = G.build_corpus()
        self.assertGreaterEqual(G.accuracy(held, self.W1, self.W2), 0.90)

    def test_humility_refuses_out_of_domain(self):
        for text in ('open the pod bay doors', 'sing me a song',
                     'book a flight to mars'):
            cls, _m = G.route(text, self.W1, self.W2)
            self.assertEqual(cls, 'none', text)

    def test_model_as_words(self):
        words = G.export_neural_words(self.W1, self.W2)
        self.assertGreater(len(words), 1000)
        v = _load('5500fp_ternoo_v03')
        d = v.decode_word(words[0])
        self.assertEqual(d['type'], 'NEURAL_CONNECTION')
        self.assertIn('weight', d)


if __name__ == '__main__':
    unittest.main(verbosity=1)
