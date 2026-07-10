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

    def test_persistent_identity_survives_reload(self):
        import tempfile
        path = os.path.join(tempfile.mkdtemp(), "keys", "node.key")
        created = N.load_or_create_identity(path)        # creates key + parent dir
        reloaded = N.load_or_create_identity(path)        # same key back
        self.assertEqual(created.account_id, reloaded.account_id)
        self.assertEqual(oct(os.stat(path).st_mode)[-3:], "600")   # owner-only

    def test_wallet_reads_persisted_earnings(self):
        import tempfile
        key = os.path.join(tempfile.mkdtemp(), "w.key")
        idn = N.load_or_create_identity(key)             # persist the key
        led = D.L.Ledger()
        cust = N.identity_from_seed("wallet-cust")
        led.open_account(idn)
        led.open_account(cust)
        led.settle_work(idn, cust, 7)                    # idn earns 7 (weight-bearing)
        led.save(key + ".ledger")
        w = N.wallet(key)
        self.assertEqual(w["account"], idn.account_id.hex())
        self.assertEqual(w["balance"], 7)
        self.assertEqual(w["weight_bearing"], 7)

    def test_parse_peers(self):
        self.assertEqual(N.parse_peers("1.2.3.4:9000, :9001"),
                         [("1.2.3.4", 9000), ("127.0.0.1", 9001)])
        self.assertEqual(N.parse_peers(""), [])

    def test_load_node_config(self):
        import json
        import tempfile
        p = os.path.join(tempfile.mkdtemp(), "p2pcp.json")
        with open(p, "w") as f:
            json.dump({"port": 9000, "mock": True, "peers": "1.2.3.4:9000"}, f)
        cfg = N.load_node_config(p)
        self.assertEqual(cfg["port"], 9000)
        self.assertTrue(cfg["mock"])
        self.assertEqual(N.load_node_config("/nope/x.json"), {})    # absent -> {}

    def test_join_mesh_bootstraps_and_discovers(self):
        c = D.Daemon(N.identity_from_seed("boot-c"))
        b = D.Daemon(N.identity_from_seed("boot-b"))
        a = D.Daemon(N.identity_from_seed("boot-a"))
        c_addr, b_addr = c.start(), b.start()
        b.add_peer(*c_addr)                              # B knows C
        try:
            known = N.join_mesh(a, [b_addr])            # A boots off B only
            self.assertIn(b_addr, a.known_peers())       # knows the seed
            self.assertIn(c_addr, a.known_peers())       # discovered C via B
            self.assertGreaterEqual(known, 2)
        finally:
            a.stop()
            b.stop()
            c.stop()

    def test_find_providers_discovers_by_class(self):
        prof = D.Daemon(N.identity_from_seed("find-prof"),
                        worker=P.BonsaiWorker(backend=B.EchoBackend()))  # float
        addr = prof.start()
        try:
            self.assertEqual(N.find_providers("compute:float", [addr]), [addr])
            self.assertEqual(N.find_providers("compute:native", [addr]), [])
        finally:
            prof.stop()

    def test_ask_mesh_discovers_a_professor_among_peers(self):
        prof = D.Daemon(N.identity_from_seed("mesh-prof"),
                        worker=P.BonsaiWorker(backend=B.EchoBackend()))
        addr = prof.start()
        client = None
        try:
            client, served, res = N.ask_mesh([("127.0.0.1", 1), addr],   # 1st dead
                                             "what is ternary?", k=5, seed="mc")
            self.assertEqual(served, addr)                 # found & named the prof
            self.assertEqual(res["settled_chunks"], 1)
            self.assertIn(b"echo professor", res["outputs"][0])
        finally:
            if client is not None:
                client.stop()
            prof.stop()

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
