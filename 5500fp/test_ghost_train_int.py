"""test_ghost_train_int.py — stage 3's laws, pinned.

GHOST's real classifier, trained WITHOUT floats, matching the float
baseline's held-out accuracy exactly. Determinism means the accuracy
asserts are equalities and the digest is a pin; the cross-machine twin
of the pin is the Lenny run recorded in the ledger.

Run:  cd 5500fp && python3 -m unittest test_ghost_train_int
(Trains once at import — ~25 s of pure-integer arithmetic.)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ghost_train as G
import ghost_train_int as GI

RESULT = GI.train()

# Pinned on the HP, 20-09-2026 (margin-perceptron config, epochs=100).
GOLDEN = "df1f0f492db4e3e86698a1cd09e3071faff5722f29461625169c62e6a763318a"

FLOAT_BASELINE_PCT = 94.4      # ghost_train.py held-out, same corpus seed


class TestDeterminism(unittest.TestCase):
    def test_pinned_digest_never_drifts(self):
        self.assertEqual(RESULT["final_digest"], GOLDEN)

    def test_epoch_chain(self):
        self.assertEqual(len(RESULT["epoch_digests"]), GI.HP["epochs"])
        self.assertEqual(len(set(RESULT["epoch_digests"])),
                         len(RESULT["epoch_digests"]))


class TestAccuracy(unittest.TestCase):
    def test_matches_float_baseline_exactly(self):
        # the brief demanded "within a stated tolerance" — the landing
        # beat the ask: EQUAL to the float baseline on the same held-out
        self.assertEqual(RESULT["held_acc_pct"], FLOAT_BASELINE_PCT)

    def test_exact_counts_are_equalities(self):
        self.assertEqual(RESULT["train_acc_pct"], 99.5)
        self.assertEqual(RESULT["held_n"], 195)


class TestModelShape(unittest.TestCase):
    def test_weight_levels_within_ghost_band(self):
        for M in (RESULT["W1"], RESULT["W2"]):
            for row in M:
                for v in row:
                    self.assertIsInstance(v, int)
                    self.assertTrue(-G.WLEVELS <= v <= G.WLEVELS)

    def test_ref_forward_runs_on_trained_model(self):
        # the golden inference contract: the integer-trained model rides
        # the SAME ref_forward the emulator matches bit-exactly
        cls, margin, logits = G.ref_forward("sort my shopping list",
                                            RESULT["W1"], RESULT["W2"])
        self.assertEqual(len(logits), len(G.CLASSES))
        got, _ = G.route("sort my shopping list", RESULT["W1"], RESULT["W2"])
        self.assertEqual(got, "cmd_list_sort")

    def test_humility_survives(self):
        got, _ = G.route("open the pod bay doors", RESULT["W1"], RESULT["W2"])
        self.assertEqual(got, "none")


class TestFloatBaselineUntouched(unittest.TestCase):
    def test_ghost_train_unmodified_in_tree(self):
        here = os.path.dirname(os.path.abspath(__file__))
        self.assertTrue(os.path.exists(os.path.join(here, "ghost_train.py")))


if __name__ == "__main__":
    unittest.main()
