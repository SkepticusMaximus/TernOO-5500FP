"""test_ghost_senses.py — the sensory loop's testable core (no hardware).

The capture edge (arecord) is manual; everything downstream of it — slicing,
ternarizing, the trit learner, surprise — is pure integers and is pinned here
on synthetic streams. The load-bearing claim: on a repeating pattern the
learner's surprise DROPS, and on the same recorded stream the whole loop
replays bit-exactly (the corpus is future mesh cargo; determinism is its
mint-worthiness).

Run: ``cd 5500fp && python3 -m unittest test_ghost_senses``
"""

import importlib.util as _ilu
import os
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


S = _load("ghost_senses")


def synth_tick(level):
    """A tick of constant amplitude `level` (400 samples)."""
    return [level, -level] * 200


class TestSliceRms(unittest.TestCase):
    def test_constant_signal_uniform_slices(self):
        rms = S.slice_rms(synth_tick(100))
        self.assertEqual(len(rms), S.SLICES)
        self.assertTrue(all(r == rms[0] for r in rms))

    def test_silence_is_zero(self):
        self.assertEqual(S.slice_rms([0] * 400), [0] * S.SLICES)


class TestTernarizer(unittest.TestCase):
    def test_first_tick_is_neutral(self):
        t = S.Ternarizer()
        self.assertEqual(t.tick([50] * S.SLICES), [0] * S.SLICES)

    def test_rise_fall_same(self):
        t = S.Ternarizer()
        t.tick([50] * S.SLICES)
        self.assertEqual(t.tick([500] * S.SLICES), [1] * S.SLICES)
        self.assertEqual(t.tick([5] * S.SLICES), [-1] * S.SLICES)
        # tiny wiggle within the deadband reads as "same"
        self.assertEqual(t.tick([5] * S.SLICES), [0] * S.SLICES)

    def test_deterministic_replay(self):
        stream = [[i * 7 % 300] * S.SLICES for i in range(60)]
        a = S.Ternarizer()
        b = S.Ternarizer()
        self.assertEqual([a.tick(x) for x in stream],
                         [b.tick(x) for x in stream])


class TestLearnerSurpriseDrops(unittest.TestCase):
    def test_repeating_pattern_becomes_unsurprising(self):
        # An alternating loud/quiet pattern: after enough exposure the
        # learner should anticipate the alternation.
        pattern = [[1] * S.SLICES, [-1] * S.SLICES] * 60
        brain = S.TritLearner()
        surprises = []
        for word in pattern:
            surprises.append(S.surprise(brain.predict(), word))
            brain.observe(word)
        half = len(surprises) // 2
        early = sum(surprises[:half])
        late = sum(surprises[half:])
        self.assertLess(late, early)            # learning visible
        self.assertEqual(surprises[-1], 0)      # the pattern is anticipated

    def test_counts_are_integers_only(self):
        brain = S.TritLearner()
        for word in ([1] * S.SLICES, [0] * S.SLICES, [-1] * S.SLICES):
            brain.observe(word)
        for sl in brain.counts:
            for row in sl:
                for c in row:
                    self.assertIsInstance(c, int)


class TestSurprise(unittest.TestCase):
    def test_bounds(self):
        z = [0] * S.SLICES
        self.assertEqual(S.surprise(z, z), 0)
        self.assertEqual(S.surprise([1] * S.SLICES, [-1] * S.SLICES),
                         2 * S.SLICES)


if __name__ == "__main__":
    unittest.main()
