"""p2pcp_emulator.py — the 5500FP itself as a mesh worker (native, replay-class).

This is the real native-compute seat the DeterministicWorker's SHA3 fold has been
holding open (§3). The 5500FP is a balanced-ternary integer machine with NO
floating point and no RNG in its datapath, so a program's result is bit-exact and
REPRODUCIBLE: any peer replays it and gets identical trits. That is exactly what
makes the work weight-bearing (§10) — a vote you earn by doing arithmetic the
whole mesh can check.

Job protocol (cargo octets → output octets):
  * The job cargo is a JSON program spec — see ``program_job``:
        {"program": [word, ...], "in": R_in, "out": [R_out, ...]}
  * Chunk ``i`` loads the chunk index into register ``in`` (so a multi-chunk job
    maps the program over inputs 0..n-1) and runs to HLT (bounded by max_cycles).
  * The output is the ``out`` registers as a JSON int list — deterministic bytes.

Requester and worker must agree on ``max_cycles`` (part of the class contract,
like vclass): a non-halting program is still deterministic *given the cap*, so
replay-audit only matches when both sides cap identically. Imports the emulator
and the worker base — never ``socket`` (the one-organ boundary, §1.5).

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


E = _load("5500fp_ternoo_v03")          # the CPU (module name starts with a digit)
WK = _load("p2pcp_worker")

DEFAULT_MAX_CYCLES = 100_000            # bounds compute per chunk (worker DoS guard)


class EmulatorWorker(WK.WorkerAdapter):
    """Run a deterministic 5500FP program as replay-class native work. Weight-
    bearing because it is bit-exactly reproducible: the requester (and any peer)
    re-runs the same program and gets the same trits, so a forged result is caught
    by replay before a coin is paid (§3)."""

    vclass = WK.VCLASS_NATIVE

    def __init__(self, max_cycles=DEFAULT_MAX_CYCLES):
        self.max_cycles = int(max_cycles)

    def run_chunk(self, job: bytes, index: int) -> bytes:
        spec = json.loads(job.decode("utf-8"))
        program = [int(w) for w in spec["program"]]
        in_reg = int(spec.get("in", 1))
        out_regs = [int(r) for r in spec.get("out", [3])]
        cpu = E.CPU5500FP()
        cpu.reset()
        cpu.load_program(program)
        if in_reg:                                  # feed the chunk index as input
            cpu.write_reg(in_reg, int(index))
        cpu.run(max_cycles=self.max_cycles)
        vals = [cpu.read_reg(r) for r in out_regs]
        return json.dumps(vals, separators=(",", ":")).encode("utf-8")


def program_job(program, in_reg=1, out_regs=(3,)):
    """Build a job cargo (bytes) for EmulatorWorker from a program (list of 24-trit
    words) plus the input/output register convention. ``in_reg=0`` disables index
    injection (the program is pure)."""
    return json.dumps(
        {"program": [int(w) for w in program],
         "in": int(in_reg), "out": [int(r) for r in out_regs]},
        separators=(",", ":")).encode("utf-8")
