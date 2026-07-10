"""test_sponge_mod3_attack.py — runs the mod-3 attack, verifying DM's finding.

This is the house religion applied to a cryptanalyst: don't take "the sponge's
mod-3 projection is affine" on trust — run the attack and see the collision fall
out of linear algebra. It also exercises the falsification gate on a candidate
cure DIRECTION.

Run: ``cd 5500fp && python3 -m unittest test_sponge_mod3_attack``
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


A = _load("sponge_mod3_attack")


class TestMod3Leak(unittest.TestCase):
    """DM's finding, made reproducible."""

    def test_digest_mod3_projection_is_affine(self):
        # The break: an ideal hash's mod-3 projection would be nonlinear; this one
        # is GF(3)-affine (the second difference vanishes over 200 random probes).
        self.assertTrue(A.is_mod3_affine(trials=200))

    def test_collision_falls_out_of_linear_algebra(self):
        # Two distinct streams with an identical digest low trit-plane, found by
        # Gaussian elimination over GF(3) — no birthday search, no grinding.
        pair = A.find_mod3_collision()
        self.assertIsNotNone(pair)
        a, b = pair
        self.assertNotEqual(a, b)                       # genuinely different inputs
        self.assertEqual(A.d3(a), A.d3(b))              # same digest mod 3
        # It is a LOW-PLANE collision: the full digests still differ (this attack
        # cheaply fixes 9 trits ≈ 14 bits; a bigger kernel fixes more).
        self.assertNotEqual(A.raw_digest(a), A.raw_digest(b))


class TestFalsificationGate(unittest.TestCase):
    """The gate can DETECT nonlinearity — so it can kill bad candidates. It can
    NEVER bless a survivor (external review only). This is that, demonstrated."""

    def test_candidate_direction_defeats_this_attack(self):
        # A multiplicative cross-lane term (mod-3-nonlinear) breaks the affinity
        # the attack relies on. This shows the DIRECTION of a cure — NOT that the
        # patched construction is safe (a single post-hoc layer is not a fix).
        self.assertFalse(A.is_mod3_affine(A.patched_permute, trials=50))


class TestStructure(unittest.TestCase):
    """The mixing matrix M, answering DM Pro's question — reproducible facts."""

    def test_mixing_is_full_rank_circulant_and_leaks_by_truncation(self):
        s = A.analyze_mod3_structure()
        self.assertEqual(s["state_lanes"], 45)          # 3^2 * 5 (divisible by 3)
        self.assertEqual(s["permute_rank"], 45)         # bijective mod 3 — NOT a collapse
        self.assertTrue(s["permute_circulant"])         # product of circulants
        # The leak is truncation + linearity: 9 of 45 lanes out => 18-dim kernel.
        self.assertEqual(s["collision_dim"], 18)        # 3^18 collisions/block by linalg


if __name__ == "__main__":
    unittest.main()
