"""test_dick_train.py — the integer trainer's laws, pinned.

Stage 1 of the integer-training brief: training in which every quantity —
weights, activations, errors, pseudo-gradients, updates — is an integer,
so a run is bit-reproducible anywhere. These tests pin determinism, the
golden digest (HP, 19-09-2026), that the thing actually LEARNS, and the
primitives' exact semantics. The cross-machine twin of the digest pin is
the Lenny run recorded in the ledger.

Run:  cd 5500fp && python3 -m unittest test_dick_train
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dick_train as T

# One full training run, shared across tests (deterministic, ~1 s).
RESULT = T.train()

# Pinned on the HP, 19-09-2026, after the o_shift rescale landed.
GOLDEN = "6872169745e899c061c80978cd7b2c8fbda1221cb78ca918b92f8c629d84d7be"


class TestDeterminism(unittest.TestCase):
    def test_two_runs_bit_identical(self):
        again = T.train()
        self.assertEqual(RESULT["final_digest"], again["final_digest"])
        self.assertEqual(RESULT["epoch_digests"], again["epoch_digests"])

    def test_pinned_digest_never_drifts(self):
        # if this changes, the trainer is no longer the audited trainer —
        # an audit event, never a silent one
        self.assertEqual(RESULT["final_digest"], GOLDEN)

    def test_epoch_chain_length(self):
        self.assertEqual(len(RESULT["epoch_digests"]), T.HP["epochs"])

    def test_epoch_digests_all_distinct(self):
        # every epoch moves the weights; a repeated digest means training
        # froze mid-run
        self.assertEqual(len(set(RESULT["epoch_digests"])),
                         len(RESULT["epoch_digests"]))


class TestItActuallyLearns(unittest.TestCase):
    def test_exact_accuracy_counts(self):
        # deterministic training ⇒ accuracy is EXACT, not a threshold
        self.assertEqual(RESULT["train_acc"], [185, 243])
        self.assertEqual(RESULT["test_acc"], [40, 81])

    def test_beats_chance_by_a_wide_margin(self):
        # 9 classes → chance ≈ 9/81 on the test split; require > 3×
        good, n = RESULT["test_acc"]
        self.assertGreater(good, 3 * n // 9)


class TestPrimitives(unittest.TestCase):
    def test_sym_shift_truncates_toward_zero(self):
        # Python's >> floors: -1 >> 4 == -1. That bias would make every
        # tiny negative gradient a permanent -1 drift. sym_shift doesn't.
        self.assertEqual(T.sym_shift(-1, 4), 0)
        self.assertEqual(T.sym_shift(1, 4), 0)
        self.assertEqual(T.sym_shift(-17, 4), -1)
        self.assertEqual(T.sym_shift(17, 4), 1)
        self.assertEqual(T.sym_shift(-32, 4), -2)

    def test_argmax_ties_to_lowest_index(self):
        self.assertEqual(T.argmax_low([5, 9, 9, 1]), 1)

    def test_no_floats_in_final_weights(self):
        hp = dict(T.HP)
        W1, W2 = T.make_net(hp)
        B = T.make_dfa(hp)
        tr, _ = T.make_dataset(hp)
        for x, y in tr[:20]:
            T.train_step(W1, W2, B, x, y, hp)
        for M in (W1, W2):
            for row in M:
                for v in row:
                    self.assertIsInstance(v, int)


class TestFloatBaselineUntouched(unittest.TestCase):
    def test_ghost_train_still_present(self):
        # the float trainer stays in the tree as the accuracy baseline,
        # per the brief — this trainer supplements, never replaces
        here = os.path.dirname(os.path.abspath(__file__))
        self.assertTrue(os.path.exists(os.path.join(here, "ghost_train.py")))


if __name__ == "__main__":
    unittest.main()
