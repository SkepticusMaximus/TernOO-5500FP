"""test_p2pcp_node.py — the launchable node: ask a Professor, get the answer.

Proves the `ask` path returns the actual inference output (not just the
settlement) — the payoff made usable. Uses EchoBackend, no model needed.

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_node``
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


N = _load("p2pcp_node")
D = _load("p2pcp_daemon")
P = _load("p2pcp_bonsai")
B = _load("bonsai_runner")


class TestNode(unittest.TestCase):
    def test_identity_from_seed_is_stable(self):
        self.assertEqual(N.identity_from_seed("x").account_id,
                         N.identity_from_seed("x").account_id)
        self.assertNotEqual(N.identity_from_seed("x").account_id,
                            N.identity_from_seed("y").account_id)

    def test_ask_returns_the_professors_answer(self):
        prof = D.Daemon(N.identity_from_seed("prof-test"),
                        worker=P.BonsaiWorker(backend=B.EchoBackend()))
        addr = prof.start()
        client = None
        try:
            client, res = N.ask(addr[0], addr[1],
                                "what is balanced ternary?", k=5, seed="client-t")
            self.assertEqual(res["settled_chunks"], 1)
            self.assertEqual(res["paid"], 5)
            self.assertIn(b"echo professor", res["outputs"][0])   # the ANSWER
        finally:
            if client is not None:
                client.stop()
            prof.stop()


if __name__ == "__main__":
    unittest.main()
