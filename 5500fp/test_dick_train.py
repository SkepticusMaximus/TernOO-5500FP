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


JOB = (b'{"hp": {"epochs": 5, "n_train": 60, "n_test": 30}}')


class TestCheckpointAudit(unittest.TestCase):
    """Stage 4: verify ONE epoch from its predecessor's checkpoint — the
    cheap audit that makes long training runs economically auditable."""

    @classmethod
    def setUpClass(cls):
        cls.claimed = __import__("json").loads(
            T.run_unit(JOB, 0))["epoch_digests"]
        cls.ck1 = T.checkpoint(JOB, 0, 1)

    def test_epoch0_needs_no_checkpoint(self):
        self.assertTrue(T.audit_one_epoch(JOB, 0, self.claimed, 0))

    def test_middle_epoch_verifies_from_checkpoint(self):
        self.assertTrue(T.audit_one_epoch(JOB, 0, self.claimed, 2, self.ck1))

    def test_forged_claim_fails(self):
        bad = list(self.claimed)
        bad[2] = "0" * 64
        self.assertFalse(T.audit_one_epoch(JOB, 0, bad, 2, self.ck1))

    def test_forged_checkpoint_fails(self):
        self.assertFalse(T.audit_one_epoch(JOB, 0, self.claimed, 2,
                                           b"[[1],[2]]"))

    def test_out_of_range_refused(self):
        self.assertFalse(T.audit_one_epoch(JOB, 0, self.claimed, 99))

    def test_hostile_job_clamped(self):
        hp = T.decode_job(b'{"hp": {"epochs": 1000000000}}', 0)
        self.assertLessEqual(hp["epochs"], T.JOB_BOUNDS["epochs"])

    def test_index_makes_independent_runs(self):
        a = T.decode_job(JOB, 0)["seed_weights"]
        b = T.decode_job(JOB, 1)["seed_weights"]
        self.assertNotEqual(a, b)


class TestTrainingOnTheMesh(unittest.TestCase):
    """TRAINING work sold, delta=0 replay-audited, PAID — and per R1
    (captain, 20-09) NOT convertible to governance weight until the
    weight-pricing item closes. Verification-class: closed. Franchise:
    deliberately deferred."""

    @staticmethod
    def _ident(tag: bytes):
        import p2pcp_daemon as D
        return D.L.Identity.from_seed(tag.ljust(32, b"\x00"))

    def test_training_sells_and_settles_native(self):
        import p2pcp_daemon as D
        L = D.L
        server = D.Daemon(self._ident(b"train-node"), worker=T.as_worker())
        addr = server.start()
        client = D.Daemon(self._ident(b"train-buyer"))
        try:
            res = client.request_job(addr[0], addr[1], JOB, n_chunks=2, k=2,
                                     vclass=L.VCLASS_TRAINING,
                                     audit=T.as_worker())
            self.assertEqual(res["settled_chunks"], 2)
            # R1 posture (captain, 20-09): paid in full, ZERO franchise
            self.assertEqual(server.ledger.balance(server.account_id), 4)
            self.assertEqual(server.ledger.burnable(server.account_id), 0)
            for i, out in enumerate(res["outputs"]):
                self.assertEqual(out.decode() if isinstance(out, bytes) else out,
                                 T.run_unit(JOB, i))
        finally:
            server.stop()
            client.stop()


class TestFloatBaselineUntouched(unittest.TestCase):
    def test_ghost_train_still_present(self):
        # the float trainer stays in the tree as the accuracy baseline,
        # per the brief — this trainer supplements, never replaces
        here = os.path.dirname(os.path.abspath(__file__))
        self.assertTrue(os.path.exists(os.path.join(here, "ghost_train.py")))


if __name__ == "__main__":
    unittest.main()
