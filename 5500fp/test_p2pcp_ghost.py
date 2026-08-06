"""test_p2pcp_ghost.py — GHOST sells verifiable work and earns a vote (the flagship).

The replay-class half of the two-mind mesh: deterministic native inference the
requester can REPLAY-AUDIT, so a forger is caught and honest work earns
WEIGHT-BEARING credit (§3/§10) — the contrast with float Bonsai (money, never a
vote).

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_ghost``
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


P = _load("p2pcp_ghost")
D = _load("p2pcp_daemon")
L = D.L

JOB = b"save the file"


def ident(tag: bytes):
    return L.Identity.from_seed(tag.ljust(32, b"\x00"))


class TestGhostWorker(unittest.TestCase):
    def test_is_native_and_classifies_deterministically(self):
        w = P.GhostWorker()
        self.assertEqual(w.vclass, L.VCLASS_NATIVE)      # replay-class, weight-bearing
        a = w.run_chunk(JOB, 0)
        b = w.run_chunk(JOB, 0)
        self.assertEqual(a, b)                           # bit-exact deterministic
        self.assertIn(b"\t", a)                          # "class\tmargin"


@unittest.skipUnless(P.native_available(), "C emulator binary missing")
class TestGhostNativeBackend(unittest.TestCase):
    """The C shim on the mesh: native execution must be indistinguishable from
    the host reference at the byte level, or it may not sell."""

    def test_native_backend_selected_and_bit_exact(self):
        w = P.GhostWorker(backend="native")
        self.assertEqual(w.backend, "native")            # probe passed
        host = P.GhostWorker(backend="host")
        for text in (b"save the file", b"make this loud", b"sort my shopping list",
                     b"bring me a shrubbery"):
            self.assertEqual(w.run_chunk(text, 0), host.run_chunk(text, 0))

    def test_native_worker_settles_under_host_audit(self):
        # Mixed-backend economy: a native worker's output must survive a
        # replay audit performed by a host-reference auditor.
        model = P.load_model()
        ghost = D.Daemon(ident(b"ghost-native"),
                         worker=P.GhostWorker(model=model, backend="native"))
        addr = ghost.start()
        client = D.Daemon(ident(b"caller3"))
        try:
            res = client.request_job(addr[0], addr[1], JOB, n_chunks=1, k=4,
                                     vclass=L.VCLASS_NATIVE,
                                     audit=P.GhostWorker(model=model,
                                                         backend="host"))
            self.assertEqual(res["settled_chunks"], 1)
            self.assertEqual(ghost.ledger.burnable(ghost.account_id), 4)
        finally:
            ghost.stop()
            client.stop()


class TestGhostOnTheMesh(unittest.TestCase):
    def test_ghost_sells_verifiable_work_and_earns_a_vote(self):
        model = P.load_model()
        ghost = D.Daemon(ident(b"ghost"), worker=P.GhostWorker(model=model))
        addr = ghost.start()
        client = D.Daemon(ident(b"caller"))
        try:
            # The requester REPLAY-AUDITS with its own GhostWorker (§3) — it only
            # pays for work it re-derived bit-for-bit.
            res = client.request_job(addr[0], addr[1], JOB, n_chunks=1, k=4,
                                     vclass=L.VCLASS_NATIVE,
                                     audit=P.GhostWorker(model=model))
            self.assertEqual(res["settled_chunks"], 1)
            self.assertEqual(ghost.ledger.balance(ghost.account_id), +4)
            # NATIVE replay-class => WEIGHT-BEARING (a vote), unlike float Bonsai.
            self.assertEqual(ghost.ledger.burnable(ghost.account_id), 4)
            self.assertIn(b"\t", res["outputs"][0])
        finally:
            ghost.stop()
            client.stop()

    def test_forged_classification_fails_replay_audit(self):
        model = P.load_model()

        class Forger(P.GhostWorker):
            def run_chunk(self, job, index):
                return b"cmd_delete_everything\t99"       # a lie, not the real class

        ghost = D.Daemon(ident(b"forger"), worker=Forger(model=model))
        addr = ghost.start()
        client = D.Daemon(ident(b"caller2"))
        try:
            res = client.request_job(addr[0], addr[1], JOB, n_chunks=1, k=4,
                                     vclass=L.VCLASS_NATIVE,
                                     audit=P.GhostWorker(model=model))
            self.assertEqual(res["settled_chunks"], 0)   # replay caught the lie
            self.assertEqual(ghost.ledger.balance(ghost.account_id), 0)
        finally:
            ghost.stop()
            client.stop()


if __name__ == "__main__":
    unittest.main()
