"""dick_kernel.py — DICK: the Deterministic Inference Colony Kernel (v0.1).

Named by the captain, movie night 12-09-2026; filed under its full name for
the ledger's honesty and the crew's evident amusement (CF5's 2120 handoff).

WHAT THIS IS. The colony's float-ask class (proven breathing 12-09, 23:15)
is rent-class by design: float accumulation is not bit-reproducible across
hardware, so buyers trust a quorum. DICK closes that gap for TERNARY models:
weights live in {-1, 0, +1}, every accumulation is an integer, every
requantisation is a trit-shift (floor-division by a power of three) — so a
forward pass is BIT-EXACT on any CPU, any OS, any endianness. That makes
colony inference REPLAY-AUDITABLE: any peer recomputes any layer and gets
identical bytes, so the work can be NATIVE-class — weight-bearing, mint-
eligible, slashable — per the earn→burn→vote→slash loop.

THE AUDIT DIGEST IS SHA3, NOT THE SPONGE. CF5's handoff sketched "digest via
the HexMesh fold/MMID"; but ternary_sponge is provably GF(3)-affine
collidable (sponge_mod3_attack.py), and a mint gate on a collidable digest
is a forgeable audit. Standing ruling: SHA3 stays on the wire. So the
MINT-GATING digest here is SHA3-256 over canonical layer bytes; the ternary
STORE MMID rides alongside as the native-flavour label only (same dual-
digest pattern as p2pcp_ledger).

THE LEASH, both sentences, always: determinism proves WHAT ran, not that
it is SAFE. Carried forward unchanged from the 04-09 colony letter.

V0.1 SCOPE (honest): a demo-scale network — seed-derived ternary layers,
integer ReLU MLP — NOT a large language model. The kernel contract, the
audit protocol and the cross-machine bit-exactness are the deliverables;
scaling the kernel to real model weights is the next leg, and llama.cpp's
TQ2_0 does NOT qualify (it accumulates in float — old CC's note stands).

Run:  python3 dick_kernel.py            (acceptance self-check)
      python3 dick_kernel.py --digest JOB_JSON   (one-line digest, for
      cross-machine comparison: same JSON in, same digest out, anywhere)

Added: 13 Sep 2026, Adelaide (~01:30, coffee-powered)
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Design authority: captain's go via CF5's 2026-09-12-2120 handoff; scope
per old CC's 04-09 colony letter §3/§6. Status: FIRST CUT.
"""

import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── deterministic pseudo-randomness (NO python random; replay demands it) ────
# A tiny integer LCG: same seed → same stream on every machine, forever.
_LCG_M = 2**31 - 1
_LCG_A = 48271


def _lcg(seed):
    s = (int(seed) % _LCG_M) or 1
    while True:
        s = (s * _LCG_A) % _LCG_M
        yield s


def ternary_layer(seed, n_in, n_out):
    """A deterministic ternary weight matrix: entries in {-1, 0, +1},
    derived from the seed alone — the auditor REGENERATES it, so job cargo
    stays tiny (no weight shipping in v0.1)."""
    g = _lcg(seed)
    return [[(next(g) % 3) - 1 for _ in range(n_in)] for _ in range(n_out)]


# ── the kernel: integer-only forward pass ─────────────────────────────────────
RELU_CAP = 3**9          # activation ceiling: keeps ints bounded, replay-exact
TRIT_SHIFT = 2           # requantise by //3**TRIT_SHIFT each layer


def tmatmul(W, x):
    """Ternary matmul, integer accumulation throughout. The inner loop is
    adds and subtracts only — the multiplications are by -1/0/+1, which is
    the whole point of ternary weights (and of the 5500FP's arithmetic)."""
    out = []
    for row in W:
        acc = 0
        for w, v in zip(row, x):
            if w == 1:
                acc += v
            elif w == -1:
                acc -= v
        out.append(acc)
    return out


def relu_requant(v):
    """Integer ReLU + trit-shift requantisation + cap. floor-div by 3**k is
    exact and identical everywhere; the cap bounds growth so every value
    stays a small int (no bignum drift between platforms — Python ints are
    exact anyway, but the cap keeps outputs comparable and compact)."""
    return [min(x // (3**TRIT_SHIFT), RELU_CAP) if x > 0 else 0 for x in v]


def forward(seed, x, n_layers, width):
    """Run the seed-derived n_layers×width MLP on integer vector x.
    Returns the list of per-layer OUTPUTS (post ReLU/requant) — the audit
    surface: each entry is what a verifier must reproduce bit-for-bit."""
    outs = []
    v = list(map(int, x))
    n_in = len(v)
    for i in range(n_layers):
        W = ternary_layer(seed + i * 7919, n_in, width)   # 7919: 1000th prime
        v = relu_requant(tmatmul(W, v))
        outs.append(v)
        n_in = width
    return outs


# ── digests: SHA3 gates the mint; the ternary MMID is the native label ───────
def canonical_bytes(vec):
    """One canonical byte form per layer output — JSON, no spaces, ASCII.
    Anything canonical works; it must simply be THE SAME everywhere."""
    return json.dumps(list(map(int, vec)), separators=(",", ":")).encode()


def layer_digest(vec):
    """The MINT-GATING digest: SHA3-256. See module docstring for why the
    ternary sponge is NOT allowed on this path (collidable ≠ auditable)."""
    return hashlib.sha3_256(canonical_bytes(vec)).hexdigest()


def native_label(vec):
    """The ternary STORE MMID as a native-flavour LABEL (never a gate):
    best-effort — absent TernOO modules just mean no label."""
    try:
        import importlib.util as ilu
        here = os.path.dirname(os.path.abspath(__file__))
        spec = ilu.spec_from_file_location(
            "p2pcp_ledger", os.path.join(here, "p2pcp_ledger.py"))
        led = ilu.module_from_spec(spec)
        spec.loader.exec_module(led)
        words = [int(x) for x in vec[:9]] or [0]
        return "T" + "".join(str(t) for t in led.store_mmid(words))[:27]
    except Exception:                            # noqa: BLE001
        return None


# ── the job: run, digest, audit ───────────────────────────────────────────────
def decode_job(job: bytes, index: int):
    """Deterministically derive (seed, x, n_layers, width) from cargo+index.
    JSON {"seed":..,"x":[..],"layers":..,"width":..} or arbitrary bytes
    (folded through SHA3 into a seed; x from the bytes). Chunk index
    perturbs the seed: distinct chunks are distinct units."""
    seed = None
    try:
        obj = json.loads(job.decode("utf-8"))
        if isinstance(obj, dict) and "seed" in obj:
            seed = int(obj["seed"])
            x = [int(v) for v in obj.get("x", [1, 2, 3])]
            n_layers = max(1, min(int(obj.get("layers", 4)), 64))
            width = max(2, min(int(obj.get("width", 27)), 729))
    except Exception:                            # noqa: BLE001
        pass
    if seed is None:
        digest = hashlib.sha3_256(job or b"\x00").digest()
        seed = int.from_bytes(digest[:4], "big")
        x = [b - 128 for b in (job[:27] or b"\x01")]
        n_layers, width = 4, 27
    return seed + int(index), x, n_layers, width


def run_unit(job: bytes, index: int = 0) -> bytes:
    """The DICK unit of work: forward pass + per-layer SHA3 digests.
    Canonical JSON bytes out — an auditor re-running (job, index) gets
    identical bytes, and can ALSO spot-check any single layer (below)."""
    seed, x, n_layers, width = decode_job(job, index)
    outs = forward(seed, x, n_layers, width)
    digests = [layer_digest(v) for v in outs]
    out = {
        "v": 1,
        "unit": "dick-v0-mlp",
        "index": int(index),
        "layers": n_layers,
        "width": width,
        "layer_digests": digests,
        "final": outs[-1][:9],
        "final_digest": digests[-1],
        "native_label": native_label(outs[-1]),
    }
    return json.dumps(out, separators=(",", ":"), sort_keys=True).encode()


def audit_layers(job: bytes, index: int, claimed_digests, k: int = 3,
                 audit_seed: int = 1) -> bool:
    """Spot-check k pseudo-randomly chosen layers of a CLAIMED result:
    recompute the full pass (v0.1 recomputes all — layer checkpointing
    arrives with big models), compare the k sampled digests. The sample
    choice derives from audit_seed so an auditor's picks are themselves
    reproducible — auditors can be audited."""
    seed, x, n_layers, width = decode_job(job, index)
    if len(claimed_digests) != n_layers:
        return False
    outs = forward(seed, x, n_layers, width)
    g = _lcg(audit_seed + seed)
    picks = {next(g) % n_layers for _ in range(max(1, k))}
    return all(layer_digest(outs[i]) == claimed_digests[i] for i in picks)


# ── mesh worker (optional glue, zero hard dependency — earn_unit pattern) ────
VCLASS_NATIVE = "native"


def as_worker():
    """DICK as a REPLAY-CLASS mesh worker. Same optional-wrapper discipline
    as earn_unit.as_worker: the kernel carries no p2pcp dependency."""
    try:
        from p2pcp_worker import WorkerAdapter, VCLASS_NATIVE as _VN
    except Exception:                            # noqa: BLE001
        try:
            from p2pcp.worker import WorkerAdapter, VCLASS_NATIVE as _VN
        except Exception:
            WorkerAdapter, _VN = None, VCLASS_NATIVE

    if WorkerAdapter is not None:
        class DickWorker(WorkerAdapter):
            """REPLAY-CLASS: bit-exactly reproducible → weight-bearing."""
            vclass = _VN

            def run_chunk(self, job: bytes, index: int) -> bytes:
                return run_unit(job, index)
        return DickWorker()

    class _DickWorker:                           # duck-typed fallback
        vclass = VCLASS_NATIVE

        def run_chunk(self, job: bytes, index: int) -> bytes:
            return run_unit(job, index)
    return _DickWorker()


# ── acceptance self-check ─────────────────────────────────────────────────────
def run_acceptance() -> bool:
    print("=" * 62)
    print("  DICK v0.1 — Acceptance Self-check (deterministic colony kernel)")
    print("=" * 62)
    results = []

    def _check(n, desc, ok):
        results.append(bool(ok))
        print(f"  {n:2d}. {'PASS' if ok else 'FAIL'}  {desc}")

    jobs = [b"", b"hello colony",
            json.dumps({"seed": 42, "x": [3, -1, 4, -1, 5],
                        "layers": 6, "width": 27}).encode(),
            bytes(range(0, 200, 7))]

    _check(1, "Determinism: run_unit(job,i) stable over repeats",
           all(run_unit(j, i) == run_unit(j, i)
               for j in jobs for i in range(3)))

    pure = True
    for j in jobs:
        out = json.loads(run_unit(j, 0))
        for v in out["final"]:
            if not isinstance(v, int):
                pure = False
    _check(2, "Integer purity: no float anywhere in the output", pure)

    ok3 = True
    for j in jobs:
        claimed = json.loads(run_unit(j, 1))["layer_digests"]
        if not audit_layers(j, 1, claimed, k=3):
            ok3 = False
    _check(3, "Replay-audit: k-layer spot check passes on honest work", ok3)

    forged = json.loads(run_unit(b"hello colony", 0))["layer_digests"]
    forged[1] = "0" * 64
    _check(4, "Forgery: a doctored layer digest is CAUGHT",
           not audit_layers(b"hello colony", 0, forged, k=8))

    w = as_worker()
    _check(5, "Worker contract: replay-class adapter, chunk == unit",
           getattr(w, "vclass", None) is not None
           and w.run_chunk(b"x", 2) == run_unit(b"x", 2))

    d1 = json.loads(run_unit(jobs[2], 0))["final_digest"]
    _check(6, "Digest is SHA3 (64 hex chars), sponge nowhere on the gate",
           len(d1) == 64 and all(c in "0123456789abcdef" for c in d1))

    print("-" * 62)
    total = sum(results)
    print(f"  Total: {total}/{len(results)}")
    print("  ✓ All PASS — ready for commit." if all(results)
          else "  ✗ FAILURES — do not commit.")
    return all(results)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--digest"]:
        job = (argv[1] if len(argv) > 1 else "").encode()
        out = json.loads(run_unit(job, 0))
        print(out["final_digest"])
        return
    ok = run_acceptance()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
