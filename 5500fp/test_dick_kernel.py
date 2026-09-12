"""test_dick_kernel.py — the DICK's laws, pinned.

The kernel's one promise: a ternary integer forward pass that is bit-exact
everywhere, with per-layer SHA3 digests an auditor can spot-check. These
tests pin determinism, integer purity, audit honesty (and its refusal),
the worker contract, and the mesh round trip. The cross-MACHINE proof
lives in the ledger (HP == Lenny digest, 13-09-2026, 059ad515...).

Run:  cd 5500fp && python3 -m unittest test_dick_kernel
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import dick_kernel as K

JOBS = [
    b"",
    b"hello colony",
    json.dumps({"seed": 42, "x": [3, -1, 4, -1, 5],
                "layers": 6, "width": 27}).encode(),
    json.dumps({"seed": 424242, "x": [1, -2, 3, -4, 5, -6, 7, -8, 9],
                "layers": 8, "width": 81}).encode(),
    bytes(range(0, 200, 7)),
]


class TestDeterminism(unittest.TestCase):
    def test_identical_bytes_over_repeats(self):
        for j in JOBS:
            for i in range(3):
                self.assertEqual(K.run_unit(j, i), K.run_unit(j, i))

    def test_chunk_index_changes_the_unit(self):
        self.assertNotEqual(K.run_unit(b"x", 0), K.run_unit(b"x", 1))

    def test_pinned_digest_never_drifts(self):
        # the exact digest proven equal on HP and Lenny, 13-09-2026 —
        # if this changes, the kernel is no longer the audited kernel
        job = JOBS[3]
        out = json.loads(K.run_unit(job, 0))
        self.assertEqual(
            out["final_digest"],
            "059ad51539726c00917f9666135e1ff4d20ecb2844ef56d002295145b029dce9")


class TestIntegerPurity(unittest.TestCase):
    def test_no_floats_in_output(self):
        for j in JOBS:
            out = json.loads(K.run_unit(j, 0))
            for v in out["final"]:
                self.assertIsInstance(v, int)

    def test_matmul_is_pure_addition(self):
        self.assertEqual(K.tmatmul([[1, -1, 0]], [5, 3, 999]), [2])

    def test_requant_is_floor_div_and_cap(self):
        self.assertEqual(K.relu_requant([9, -9, 10**12]),
                         [1, 0, K.RELU_CAP])


class TestAudit(unittest.TestCase):
    def test_honest_work_passes(self):
        for j in JOBS:
            claimed = json.loads(K.run_unit(j, 1))["layer_digests"]
            self.assertTrue(K.audit_layers(j, 1, claimed, k=3))

    def test_forged_layer_is_caught(self):
        claimed = json.loads(K.run_unit(b"hello colony", 0))["layer_digests"]
        claimed[1] = "0" * 64
        self.assertFalse(K.audit_layers(b"hello colony", 0, claimed, k=8))

    def test_wrong_layer_count_is_refused(self):
        self.assertFalse(K.audit_layers(b"x", 0, ["a"], k=1))

    def test_audit_picks_are_reproducible(self):
        j = JOBS[2]
        claimed = json.loads(K.run_unit(j, 0))["layer_digests"]
        a = K.audit_layers(j, 0, claimed, k=2, audit_seed=7)
        b = K.audit_layers(j, 0, claimed, k=2, audit_seed=7)
        self.assertEqual(a, b)


class TestOnTheMesh(unittest.TestCase):
    """DICK sells verifiable inference and earns a vote — the colony's
    native-class economics, end to end."""

    @staticmethod
    def _ident(tag: bytes):
        import p2pcp_daemon as D
        return D.L.Identity.from_seed(tag.ljust(32, b"\x00"))

    def test_dick_sells_and_forger_is_slashed_from_settlement(self):
        import p2pcp_daemon as D
        L = D.L
        job = JOBS[2]
        server = D.Daemon(self._ident(b"dick-node"), worker=K.as_worker())
        addr = server.start()
        client = D.Daemon(self._ident(b"colony-buyer"))
        try:
            res = client.request_job(addr[0], addr[1], job, n_chunks=2, k=2,
                                     vclass=L.VCLASS_NATIVE,
                                     audit=K.as_worker())
            self.assertEqual(res["settled_chunks"], 2)
            self.assertEqual(server.ledger.burnable(server.account_id), 4)
            for i, out in enumerate(res["outputs"]):
                self.assertEqual(out, K.run_unit(job, i))
        finally:
            server.stop()
            client.stop()


if __name__ == "__main__":
    unittest.main()
