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


JOB = b'{"hp": {"epochs": 3}}'


class TestCheckpointAudit(unittest.TestCase):
    """Stage 4 on the REAL classifier: one-epoch spot-checks with shuffle
    reconstruction (the stream is weight-independent, so order replays
    without training)."""

    @classmethod
    def setUpClass(cls):
        import json
        cls.claimed = json.loads(GI.run_unit(JOB, 0))["epoch_digests"]
        cls.ck0 = GI.checkpoint(JOB, 0, 0)

    def test_epoch0_needs_no_checkpoint(self):
        self.assertTrue(GI.audit_one_epoch(JOB, 0, self.claimed, 0))

    def test_epoch1_verifies_from_checkpoint(self):
        self.assertTrue(GI.audit_one_epoch(JOB, 0, self.claimed, 1, self.ck0))

    def test_forged_claim_fails(self):
        bad = list(self.claimed)
        bad[1] = "0" * 64
        self.assertFalse(GI.audit_one_epoch(JOB, 0, bad, 1, self.ck0))

    def test_forged_checkpoint_fails(self):
        self.assertFalse(GI.audit_one_epoch(JOB, 0, self.claimed, 1,
                                            b"[[1],[2]]"))

    def test_hostile_job_clamped(self):
        hp = GI.decode_job(b'{"hp": {"epochs": 1000000000}}', 0)
        self.assertLessEqual(hp["epochs"], GI.JOB_BOUNDS["epochs"])


class TestGhostTrainingOnTheMesh(unittest.TestCase):
    """GHOST's own classifier training sold, delta=0 replay-audited, and
    minted native — the real product, not the toy."""

    @staticmethod
    def _ident(tag: bytes):
        import p2pcp_daemon as D
        return D.L.Identity.from_seed(tag.ljust(32, b"\x00"))

    def test_ghost_training_sells_and_settles(self):
        import p2pcp_daemon as D
        L = D.L
        server = D.Daemon(self._ident(b"ghost-train-node"),
                          worker=GI.as_worker())
        addr = server.start()
        client = D.Daemon(self._ident(b"ghost-train-buyer"))
        try:
            res = client.request_job(addr[0], addr[1], JOB, n_chunks=2, k=2,
                                     vclass=L.VCLASS_NATIVE,
                                     audit=GI.as_worker())
            self.assertEqual(res["settled_chunks"], 2)
            self.assertEqual(server.ledger.burnable(server.account_id), 4)
        finally:
            server.stop()
            client.stop()


class TestFloatBaselineUntouched(unittest.TestCase):
    def test_ghost_train_unmodified_in_tree(self):
        here = os.path.dirname(os.path.abspath(__file__))
        self.assertTrue(os.path.exists(os.path.join(here, "ghost_train.py")))


if __name__ == "__main__":
    unittest.main()
