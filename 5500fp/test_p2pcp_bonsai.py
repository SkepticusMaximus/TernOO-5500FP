"""test_p2pcp_bonsai.py — the Professor trades inference on the mesh (payoff loop).

The whole reason P2PCP exists: Bonsai was starving for compute. Now the Professor
is a mesh worker that SELLS inference for CompuToken. Tested with bonsai_runner's
EchoBackend, so the full prompt -> reply -> paid settlement loop runs without the
2.2 GB model.

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_bonsai``
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


P = _load("p2pcp_bonsai")
D = _load("p2pcp_daemon")
L = D.L
B = _load("bonsai_runner")

PROMPT = b"Question: what is balanced ternary?\nAnswer:"


def ident(tag: bytes):
    return L.Identity.from_seed(tag.ljust(32, b"\x00"))


class TestBonsaiWorker(unittest.TestCase):
    def test_is_float_class_and_generates(self):
        w = P.BonsaiWorker(backend=B.EchoBackend())
        self.assertEqual(w.vclass, L.VCLASS_FLOAT)        # money, never a vote
        out = w.run_chunk(PROMPT, 0)
        self.assertIsInstance(out, bytes)
        self.assertIn(b"echo professor", out)

    def test_backend_assembles_without_crashing(self):
        # Auto-discovery returns a real LlamaBackend or degrades to the echo mock;
        # either way it is a present, callable professor — never a crash.
        backend = P.professor_backend()
        self.assertTrue(callable(getattr(backend, "generate", None)))


class TestProfessorOnTheMesh(unittest.TestCase):
    def test_professor_sells_inference_for_compucoin(self):
        prof = D.Daemon(ident(b"professor"),
                        worker=P.BonsaiWorker(backend=B.EchoBackend()))
        addr = prof.start()
        client = D.Daemon(ident(b"student"))
        try:
            res = client.request_job(addr[0], addr[1], PROMPT, n_chunks=1, k=5,
                                     vclass=L.VCLASS_FLOAT, audit=None)
            self.assertEqual(res["settled_chunks"], 1)
            self.assertEqual(res["paid"], 5)
            # The Professor earned spendable CompuCoin — but no franchise weight.
            self.assertEqual(prof.ledger.balance(prof.account_id), +5)
            self.assertEqual(prof.ledger.burnable(prof.account_id), 0)
            self.assertEqual(client.ledger.balance(client.account_id), -5)
        finally:
            prof.stop()
            client.stop()


if __name__ == "__main__":
    unittest.main()
