"""p2pcp_worker.py — worker adapters (RFC §4 node anatomy, spec §3).

A worker adapter turns a job (cargo octets) into output octets, one chunk at a
time. Its ``vclass`` declares how the network verifies the output (§3):

  * REPLAY-CLASS (deterministic) — any peer re-runs it and gets identical bits,
    so the work is auditable by replay and is WEIGHT-BEARING (§10). The TernOO-
    native integer models live here.
  * FLOAT-CLASS (quorum) — llama.cpp / GPU accumulation is not bit-reproducible,
    so it is verified by redundant sampling, earns money but never a vote (§3).
    ``bonsai_runner`` (the Professor) is the real float adapter and drops in
    behind this same interface — not wired here, but its seat is kept.

The daemon holds ONE adapter and never knows which; a local model discovers
remote compute by asking its own daemon (the harness seam), exactly as GHOST's
none→consent→delegate works today.

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import hashlib

# Mirror of p2pcp_ledger's verification classes (§3). Plain ints, so they compare
# across module instances; the ledger owns the canon and these MUST match it.
VCLASS_NATIVE = 1       # replay-class, weight-bearing (== L.VCLASS_NATIVE)
VCLASS_FLOAT = -1       # quorum-class, rent not votes  (== L.VCLASS_FLOAT)


class WorkerAdapter:
    """Base adapter. ``vclass`` declares the verification class (§3); subclasses
    implement ``run_chunk``."""

    vclass = None

    def run_chunk(self, job: bytes, index: int) -> bytes:
        raise NotImplementedError


class DeterministicWorker(WorkerAdapter):
    """A REPLAY-CLASS testnet adapter (§3). Output is a pure, deterministic
    function of (job, chunk index): any peer replays it and gets identical bits —
    which is exactly what makes the work weight-bearing and auditable by
    challenge (§10). It stands in for a TernOO-native integer model until one is
    wired; the transform is a SHA3 fold (the point is bit-exact reproducibility,
    not the arithmetic)."""

    vclass = VCLASS_NATIVE

    def run_chunk(self, job: bytes, index: int) -> bytes:
        return hashlib.sha3_256(job + b"|chunk|" + index.to_bytes(4, "big")).digest()


class FunctionWorker(WorkerAdapter):
    """Wrap any callable ``fn(job: bytes, index: int) -> bytes`` as a mesh worker,
    so the mesh is extensible beyond the built-in adapters. Declare ``vclass``
    HONESTLY (§3): native only if the function is deterministic and bit-exactly
    reproducible (any peer can replay-audit it); float otherwise."""

    def __init__(self, fn, vclass=VCLASS_NATIVE):
        self._fn = fn
        self.vclass = vclass

    def run_chunk(self, job: bytes, index: int) -> bytes:
        out = self._fn(job, index)
        return out if isinstance(out, (bytes, bytearray)) else str(out).encode("utf-8")
