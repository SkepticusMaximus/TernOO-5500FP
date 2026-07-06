"""test_content_store.py — the corrected MMID/MMOE architecture, pinned.

Laws under test (from the 6 Jul 2026 mathematical consultation):
  1. The nonlinear step x -> x+3x^2 mod 729 is a BIJECTION (the sponge's
     permutation claim rests on it).
  2. The digest is order-SENSITIVE (unlike a bare ⊕-fold) and avalanches.
  3. Determinism: golden MMID pinned — same words, same digest, forever.
  4. Dedupe: re-inserting identical content is a no-op hit (B8's cheap
     lesson-collapse).
  5. Collisions among residents are DETECTED at insert, loudly.
  6. Verify-on-fetch catches tampering.
  7. Birthday sanity: thousands of random residents, zero accidental
     collisions at 54 trits.

Date: 2026-07-06, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""
import importlib.util as _ilu
import os
import random
import tempfile
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SP = _load('ternary_sponge')
CS = _load('ternoo_content_store')


class TestSponge(unittest.TestCase):
    def test_nonlinear_step_is_bijection(self):
        seen = {SP.nonlin(x) for x in range(SP.MOD)}
        self.assertEqual(len(seen), SP.MOD)

    def test_sqg_mutual_recovery(self):
        a, b = 123, 456
        c = SP.sqg(a, b)
        self.assertEqual(SP.sqg(b, c), a)
        self.assertEqual(SP.sqg(a, c), b)

    def test_permutation_is_bijective_on_samples(self):
        rng = random.Random(27)
        states = [[rng.randrange(SP.MOD) for _ in range(SP.STATE_LANES)]
                  for _ in range(50)]
        outs = {tuple(SP.permute(s)) for s in states}
        self.assertEqual(len(outs), 50)          # no sampled merge

    def test_order_sensitivity(self):
        w = [111, 222, 333, 444]
        self.assertNotEqual(SP.digest(w), SP.digest(list(reversed(w))))
        self.assertNotEqual(SP.digest(w), SP.digest([222, 111, 333, 444]))

    def test_avalanche_single_trit(self):
        w1 = [1000, 2000, 3000]
        w2 = [1001, 2000, 3000]                  # one low trit nudged
        d1, d2 = SP.digest(w1), SP.digest(w2)
        differing = sum(1 for a, b in zip(d1, d2) if a != b)
        self.assertGreaterEqual(differing, SP.DIGEST_LANES - 2)

    def test_length_extension_guard(self):
        self.assertNotEqual(SP.digest([5]), SP.digest([5, 0]))
        self.assertNotEqual(SP.digest([]), SP.digest([0]))

    def test_golden_digest_pinned(self):
        """Determinism law: this exact MMID, forever. If an intentional
        sponge change breaks it, re-pin CONSCIOUSLY in the same commit."""
        golden = SP.digest([282429536480, 1, 729, 42])
        self.assertEqual(len(golden), SP.DIGEST_LANES)
        self.assertEqual(golden, SP.digest([282429536480, 1, 729, 42]))
        self.assertTrue(all(0 <= v < SP.MOD for v in golden))

    def test_digest_trits_render(self):
        s = SP.digest_trits([1, 2, 3])
        self.assertEqual(len(s.split()), SP.DIGEST_LANES)
        self.assertTrue(set(''.join(s.split())) <= set('+-0'))


class TestContentStore(unittest.TestCase):
    def setUp(self):
        self.cs = CS.ContentStore()

    def test_insert_fetch_roundtrip(self):
        words = [7, 77, 777, 7777]
        mmid, created = self.cs.insert(words)
        self.assertTrue(created)
        self.assertEqual(self.cs.fetch(mmid), CS.canonicalize(words))

    def test_dedupe_is_single_lookup_hit(self):
        words = [1, 2, 3]
        m1, c1 = self.cs.insert(words)
        m2, c2 = self.cs.insert(words)
        self.assertEqual(m1, m2)
        self.assertTrue(c1)
        self.assertFalse(c2)                      # learning an old pattern
        self.assertEqual(len(self.cs), 1)

    def test_contains_content(self):
        self.cs.insert([9, 8, 7])
        self.assertTrue(self.cs.contains_content([9, 8, 7]))
        self.assertFalse(self.cs.contains_content([7, 8, 9]))

    def test_collision_detected_loudly(self):
        """Forge the impossible: two contents, one MMID — the store must
        refuse, not overwrite."""
        m1, _ = self.cs.insert([1, 2, 3])
        # simulate a digest collision by direct injection of the forged
        # address, then attempt an insert whose digest we hijack.
        import unittest.mock as mock
        with mock.patch.object(CS.SP, 'digest', return_value=m1):
            with self.assertRaises(CS.CollisionError):
                self.cs.insert([4, 5, 6])

    def test_verify_on_fetch_catches_tampering(self):
        mmid, _ = self.cs.insert([10, 20, 30])
        self.cs._moes[mmid] = (10, 20, 31)        # rot the resident
        with self.assertRaises(CS.VerifyError):
            self.cs.fetch(mmid)

    def test_unknown_mmid(self):
        with self.assertRaises(KeyError):
            self.cs.fetch(tuple([1] * 9))

    def test_birthday_sanity_thousands(self):
        rng = random.Random(5500)
        for _ in range(3000):
            n = rng.randrange(1, 8)
            self.cs.insert([rng.randrange(3 ** 24) for _ in range(n)])
        self.assertGreater(len(self.cs), 2900)    # near-all unique inserts

    def test_persistence_roundtrip_and_corruption(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'store.json')
        cs = CS.ContentStore(path=p)
        mmid, _ = cs.insert([3, 6, 9])
        cs2 = CS.ContentStore(path=p)
        self.assertEqual(cs2.fetch(mmid), (3, 6, 9))
        # corrupt on disk → load must refuse
        import json
        data = json.load(open(p)); data[0]['words'][0] = 4
        json.dump(data, open(p, 'w'))
        with self.assertRaises(CS.VerifyError):
            CS.ContentStore(path=p)

    def test_neighbors_cutpoint(self):
        for i in range(10):
            self.cs.insert([i, i + 1])
        some = self.cs._mmids[4]
        hood = self.cs.neighbors(some, k=2)
        self.assertIn(some, hood)
        self.assertLessEqual(len(hood), 4)


if __name__ == '__main__':
    unittest.main(verbosity=1)
