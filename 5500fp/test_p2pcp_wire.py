"""test_p2pcp_wire.py — the paid job crosses the wire (§14 step 5).

The milestone: the first job that crosses between two loopback daemons is already
a PAID job, settled per chunk against the block-lattice (§5/§11). Plus the
adversarial cases that make it honest: a deadbeat worker (exposure bounded to k),
a forged output (caught by replay before a coin is paid, §3), and float work
(earns money, never a vote, §10).

Imports the daemon/worker/wire/ledger — never `socket` (the one-organ boundary).

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_wire``
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


D = _load("p2pcp_daemon")
W = _load("p2pcp_wire")
WK = _load("p2pcp_worker")
L = D.L                         # the daemon's OWN ledger module (one instance)


def ident(tag: bytes):
    return L.Identity.from_seed(tag.ljust(32, b"\x00"))


# ── fault-injecting adapters for the adversarial cases ───────────────────────

class FaultyWorker(WK.DeterministicWorker):
    """Delivers `deliver` chunks, then cannot deliver more (a deadbeat)."""

    def __init__(self, deliver):
        self.deliver = deliver

    def run_chunk(self, job, index):
        if index >= self.deliver:
            raise RuntimeError("worker halts")
        return super().run_chunk(job, index)


class ForgingWorker(WK.DeterministicWorker):
    """Claims replay-class but returns output it did not honestly compute."""

    def run_chunk(self, job, index):
        return b"forged|" + index.to_bytes(4, "big")


class FloatWorker(WK.DeterministicWorker):
    """Quorum-class: earns money, never a vote (§3/§10)."""

    vclass = WK.VCLASS_FLOAT


# ═══════════════════════════════════════════════════════════════════════════

class TestWirePure(unittest.TestCase):
    """Frame + receipt serialization, no socket."""

    def test_frame_roundtrip(self):
        f = {"t": W.JOB, "job": "aa", "job_mmid": "bb", "n_chunks": 3, "k": 2}
        self.assertEqual(W.decode(W.encode(f)), f)

    def test_receipt_dict_roundtrip(self):
        rec = L.make_receipt(ident(b"w"), ident(b"r"), 4, b"job", b"out",
                             vclass=L.VCLASS_NATIVE, nonce=b"n" * 16)
        back = W.receipt_from_dict(L.Receipt, W.receipt_to_dict(rec))
        self.assertEqual(back.signing_bytes(), rec.signing_bytes())
        self.assertEqual(back.worker_sig, rec.worker_sig)
        self.assertEqual(back.requester_sig, rec.requester_sig)


class TestPaidJob(unittest.TestCase):
    """Two loopback daemons; a job crosses and settles per chunk."""

    def _worker(self, tag, adapter):
        w = D.Daemon(ident(tag), worker=adapter)
        return w, w.start()

    def test_honest_paid_job_settles_per_chunk(self):
        w, addr = self._worker(b"worker-h", WK.DeterministicWorker())
        r = D.Daemon(ident(b"req-h"))
        try:
            res = r.request_job(addr[0], addr[1], b"model-shard", 5, 2,
                                vclass=L.VCLASS_NATIVE,
                                audit=WK.DeterministicWorker())
            self.assertEqual(res["settled_chunks"], 5)
            self.assertEqual(res["paid"], 10)
            # Double-entry across the TWO ledgers: +10 worker, −10 requester.
            self.assertEqual(w.ledger.balance(w.account_id), +10)
            self.assertEqual(r.ledger.balance(r.account_id), -10)
            # The worker's credit is weight-bearing (native, replay-class §10).
            self.assertEqual(w.ledger.burnable(w.account_id), 10)
            # Every receipt is both-signed and binds job + output (§7).
            self.assertEqual(len(res["receipts"]), 5)
            for rec in res["receipts"]:
                self.assertTrue(rec.worker_sig and rec.requester_sig)
        finally:
            w.stop()
            r.stop()

    def test_deadbeat_worker_exposure_bounded(self):
        # Worker delivers 3 of 5 then halts. Only delivered chunks settle; the 2
        # undelivered leave ZERO ledger footprint — exposure never exceeds k (§11).
        w, addr = self._worker(b"worker-d", FaultyWorker(deliver=3))
        r = D.Daemon(ident(b"req-d"))
        try:
            res = r.request_job(addr[0], addr[1], b"shard", 5, 2,
                                vclass=L.VCLASS_NATIVE,
                                audit=WK.DeterministicWorker())
            self.assertEqual(res["settled_chunks"], 3)
            self.assertEqual(w.ledger.balance(w.account_id), +6)
            self.assertEqual(r.ledger.balance(r.account_id), -6)
        finally:
            w.stop()
            r.stop()

    def test_forged_output_is_never_paid(self):
        # Worker returns output it did not compute. The requester replays each
        # chunk (§3) and refuses to pay — the determinism moat, pre-payment.
        w, addr = self._worker(b"worker-f", ForgingWorker())
        r = D.Daemon(ident(b"req-f"))
        try:
            res = r.request_job(addr[0], addr[1], b"shard", 5, 2,
                                vclass=L.VCLASS_NATIVE,
                                audit=WK.DeterministicWorker())
            self.assertEqual(res["settled_chunks"], 0)
            self.assertEqual(w.ledger.balance(w.account_id), 0)
            self.assertEqual(r.ledger.balance(r.account_id), 0)
        finally:
            w.stop()
            r.stop()

    def test_float_job_earns_money_not_weight(self):
        # A genuine float job (both agree vclass=−1): it settles and pays, but the
        # worker's credit is NOT weight-bearing — money, never a vote (§3/§10).
        w, addr = self._worker(b"worker-fl", FloatWorker())
        r = D.Daemon(ident(b"req-fl"))
        try:
            res = r.request_job(addr[0], addr[1], b"shard", 4, 3,
                                vclass=L.VCLASS_FLOAT, audit=None)
            self.assertEqual(res["settled_chunks"], 4)
            self.assertEqual(w.ledger.balance(w.account_id), +12)   # money
            self.assertEqual(w.ledger.burnable(w.account_id), 0)    # never a vote
        finally:
            w.stop()
            r.stop()

    def test_vclass_mismatch_refused(self):
        # Worker's adapter is float; requester asks native (replay). The worker
        # won't misrepresent its class (§3) → nothing settles.
        w, addr = self._worker(b"worker-vm", FloatWorker())
        r = D.Daemon(ident(b"req-vm"))
        try:
            res = r.request_job(addr[0], addr[1], b"shard", 3, 1,
                                vclass=L.VCLASS_NATIVE,
                                audit=WK.DeterministicWorker())
            self.assertEqual(res["settled_chunks"], 0)
        finally:
            w.stop()
            r.stop()


class TestMultiWorker(unittest.TestCase):
    """One node can serve MULTIPLE verification classes, dispatching by vclass."""

    def test_node_serves_both_native_and_float(self):
        class FloatDet(WK.DeterministicWorker):
            vclass = WK.VCLASS_FLOAT

        node = D.Daemon(ident(b"multi"),
                        workers=[WK.DeterministicWorker(), FloatDet()])
        addr = node.start()
        client = D.Daemon(ident(b"multi-client"))
        try:
            r1 = client.request_job(addr[0], addr[1], b"n", n_chunks=1, k=3,
                                    vclass=L.VCLASS_NATIVE,
                                    audit=WK.DeterministicWorker())
            r2 = client.request_job(addr[0], addr[1], b"f", n_chunks=1, k=2,
                                    vclass=L.VCLASS_FLOAT, audit=None)
            self.assertEqual(r1["settled_chunks"], 1)
            self.assertEqual(r2["settled_chunks"], 1)
            self.assertEqual(node.ledger.balance(node.account_id), 5)   # 3 + 2
            self.assertEqual(node.ledger.burnable(node.account_id), 3)  # native only
        finally:
            node.stop()
            client.stop()

    def test_unavailable_class_is_declined(self):
        # A float-only node declines a native job (no worker for that class).
        class FloatDet(WK.DeterministicWorker):
            vclass = WK.VCLASS_FLOAT

        node = D.Daemon(ident(b"float-only"), worker=FloatDet())
        addr = node.start()
        client = D.Daemon(ident(b"fo-client"))
        try:
            r = client.request_job(addr[0], addr[1], b"n", n_chunks=1, k=1,
                                   vclass=L.VCLASS_NATIVE,
                                   audit=WK.DeterministicWorker())
            self.assertEqual(r["settled_chunks"], 0)     # declined
        finally:
            node.stop()
            client.stop()


class TestFunctionWorker(unittest.TestCase):
    """Any function becomes a mesh worker (extensibility)."""

    def test_wraps_a_function_as_replay_class_and_is_audited(self):
        def upper(job, index):
            return job.upper()

        node = D.Daemon(ident(b"fnw"), worker=WK.FunctionWorker(upper))
        addr = node.start()
        client = D.Daemon(ident(b"fnw-client"))
        try:
            res = client.request_job(addr[0], addr[1], b"hello", n_chunks=1, k=2,
                                     vclass=L.VCLASS_NATIVE,
                                     audit=WK.FunctionWorker(upper))
            self.assertEqual(res["settled_chunks"], 1)
            self.assertEqual(res["outputs"][0], b"HELLO")
            self.assertEqual(node.ledger.burnable(node.account_id), 2)  # a vote
        finally:
            node.stop()
            client.stop()


if __name__ == "__main__":
    unittest.main()
