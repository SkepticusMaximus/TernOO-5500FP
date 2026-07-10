"""test_p2pcp_demo.py — the end-to-end mesh demo settles all three classes.

Guards p2pcp_demo.py from bit-rot: the one-command showcase must keep working as
the protocol evolves. run_demo() already asserts internally; this pins the
results too.

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_demo``
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


DEMO = _load("p2pcp_demo")


class TestDemo(unittest.TestCase):
    def test_full_mesh_session_settles_all_classes(self):
        r = DEMO.run_demo(verbose=False)
        # discovery separated the classes correctly
        self.assertEqual(len(r["discovery"]["float"]), 1)     # only the professor
        self.assertEqual(len(r["discovery"]["native"]), 2)    # ghost + emulator
        # ① float ask
        self.assertEqual(r["ask"]["served_by"][0], "127.0.0.1")
        self.assertIn("echo professor", r["ask"]["answer"])
        # ② native classify
        self.assertEqual(r["classify"]["settled"], 1)
        # ③ native emulator compute
        self.assertEqual(r["compute"]["outputs"], ["[100]", "[101]", "[102]"])
        # economics: native minted votes, float minted none
        self.assertEqual(r["wallets"]["Professor"]["weight_bearing"], 0)
        self.assertEqual(r["wallets"]["Emulator"]["weight_bearing"], 6)
        self.assertEqual(r["wallets"]["Client"]["balance"], -14)   # 5 + 3 + 6
        # ④ governance: GHOST burned 2 of its earned 3 → 1 burnable left, weight up
        self.assertEqual(r["wallets"]["GHOST"]["weight_bearing"], 1)
        self.assertEqual(r["governance"]["weight_before"], 0.0)
        self.assertGreater(r["governance"]["weight_after"], 0.0)


if __name__ == "__main__":
    unittest.main()
