"""test_p2pcp_emulator.py — the 5500FP as a mesh worker: real native compute.

A ternary program is sold over the wire, settled per chunk, and the worker's
credit is WEIGHT-BEARING (§10) — because the requester replays the same program
on its own 5500FP and gets identical trits (§3). This is the native seat the SHA3
DeterministicWorker held open, now filled with the actual machine.

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_emulator``
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
EM = _load("p2pcp_emulator")
E = _load("5500fp_ternoo_v03")
L = D.L


def ident(tag: bytes):
    return L.Identity.from_seed(tag.ljust(32, b"\x00"))


def add100_program():
    """R3 = R1 + 100; HLT.  R1 is the per-chunk input the mesh injects."""
    cpu = E.CPU5500FP()
    asm = E.Asm(cpu)
    return [asm.LDI(2, 100), asm.ADD(3, 1, 2), asm.HLT()]


class TestEmulatorWorker(unittest.TestCase):
    def test_runs_a_program_deterministically(self):
        w = EM.EmulatorWorker()
        job = EM.program_job(add100_program(), in_reg=1, out_regs=[3])
        self.assertEqual(w.run_chunk(job, 5), b"[105]")     # 5 + 100
        self.assertEqual(w.run_chunk(job, 5), b"[105]")     # replay → identical
        self.assertEqual(w.run_chunk(job, 42), b"[142]")

    def test_program_bought_over_the_wire_is_weight_bearing(self):
        node = D.Daemon(ident(b"emu-node"), worker=EM.EmulatorWorker())
        addr = node.start()
        client = D.Daemon(ident(b"emu-client"))
        job = EM.program_job(add100_program(), in_reg=1, out_regs=[3])
        try:
            # 3 chunks map the program over inputs 0,1,2 → [100],[101],[102].
            res = client.request_job(addr[0], addr[1], job, n_chunks=3, k=2,
                                     vclass=L.VCLASS_NATIVE,
                                     audit=EM.EmulatorWorker())   # replay-audit
            self.assertEqual(res["settled_chunks"], 3)
            self.assertEqual(res["outputs"], [b"[100]", b"[101]", b"[102]"])
            self.assertEqual(node.ledger.balance(node.account_id), 6)     # 3×2
            self.assertEqual(node.ledger.burnable(node.account_id), 6)    # a vote
            # The node advertises native compute (capability discovery §15).
            self.assertIn("compute:native", node.caps)
        finally:
            node.stop()
            client.stop()

    def test_a_forged_emulator_result_is_never_paid(self):
        # A node that CLAIMS to run the program but returns junk is caught by the
        # requester's replay before a coin moves — the determinism moat (§3).
        class Forger(EM.EmulatorWorker):
            def run_chunk(self, job, index):
                return b"[999]"

        node = D.Daemon(ident(b"emu-forger"), worker=Forger())
        addr = node.start()
        client = D.Daemon(ident(b"emu-auditor"))
        job = EM.program_job(add100_program(), in_reg=1, out_regs=[3])
        try:
            res = client.request_job(addr[0], addr[1], job, n_chunks=2, k=2,
                                     vclass=L.VCLASS_NATIVE,
                                     audit=EM.EmulatorWorker())
            self.assertEqual(res["settled_chunks"], 0)          # nothing settled
            self.assertEqual(node.ledger.balance(node.account_id), 0)
        finally:
            node.stop()
            client.stop()


if __name__ == "__main__":
    unittest.main()
