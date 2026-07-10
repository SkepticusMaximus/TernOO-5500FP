"""test_p2pcp_service.py — the GUI bridge: start a node, sell, buy, check wallet.

The MeshService is what the FlowCode/Academy panel calls; all the logic lives here
and is tested without a screen.

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_service``
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


S = _load("p2pcp_service")


class TestMeshService(unittest.TestCase):
    def test_start_wallet_stop(self):
        svc = S.MeshService(worker_kind="professor", mock=True, seed="svc-a")
        addr = svc.start()
        try:
            self.assertTrue(svc.running)
            self.assertEqual(addr[0], "127.0.0.1")
            w = svc.wallet()
            self.assertIsNotNone(w["account"])
            self.assertEqual(w["balance"], 0)
        finally:
            svc.stop()
        self.assertFalse(svc.running)

    def test_operator_buys_inference_and_seller_wallet_grows(self):
        seller = S.MeshService(worker_kind="professor", mock=True, seed="seller")
        addr = seller.start()
        buyer = S.MeshService(worker_kind=None, seed="buyer")   # buy-only node
        buyer.start()
        try:
            answer = buyer.ask(addr[0], addr[1], "what is balanced ternary?", k=5)
            self.assertIn("echo professor", answer)
            self.assertEqual(seller.wallet()["balance"], 5)     # seller earned 5
            self.assertEqual(buyer.wallet()["balance"], -5)     # buyer paid 5
        finally:
            seller.stop()
            buyer.stop()

    def test_classify_earns_weight_bearing(self):
        seller = S.MeshService(worker_kind="ghost", seed="g-seller")
        addr = seller.start()
        buyer = S.MeshService(worker_kind=None, seed="g-buyer")
        buyer.start()
        try:
            cls = buyer.classify(addr[0], addr[1], "save the file", k=3)
            self.assertIsNotNone(cls)
            w = seller.wallet()
            self.assertEqual(w["balance"], 3)
            self.assertEqual(w["weight_bearing"], 3)            # native => a vote
        finally:
            seller.stop()
            buyer.stop()


if __name__ == "__main__":
    unittest.main()
