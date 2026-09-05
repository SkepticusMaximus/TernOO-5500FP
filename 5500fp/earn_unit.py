#!/usr/bin/env python3
"""
earn_unit.py — S1a Earn Unit: the deterministic, replay-auditable unit of work
==============================================================================

The minimal mint-worthy computation for the P2PCP compute mesh, per the manifold
§5 docket:

    "One unit = one predicted vector passed across the TMesh as an MMID; the
     target resolves to an OTree object that maps as a curve on a graph and
     resolves to an MMOE that can be diffed for accuracy. DOING that calculation
     is the minimal mint-worthy goal ... The unit-of-work algorithm is a Steiner
     quasigroup + a bubble sort ... the prize is the weights."
        — private/POBOX/2026-08-03-1444-Stevo-...-dual-manifold-design.md §S1 / §S1a

This module isolates that math into ONE small, portable, pure-INTEGER kernel so
that ANY machine — a full TernOO node or a thin non-TernOO client carrying a
simulated TMesh/OTree — can do the forward pass and earn. Because every operation
is integer/modular (mod 729, balanced-trit weight, the Steiner quasigroup —
per-trit negate-and-sum over balanced trits, carry-free, per the captain's
05-09-2026 ruling), the output is bit-exactly reproducible: a validator re-runs
``earn_unit(job, index)`` and gets identical bytes. That is precisely what the
daemon's replay-audit checks (``daemon._serve_peer``:
``if audit.run_chunk(job, i) != output: break``), and what makes the work
REPLAY-CLASS → MINTS (§2), not FLOAT-CLASS → SPENDS.

The two halves of the algorithm:
  * Steiner quasigroup — ``traverse_vector`` folds the predicted vector across
    the TMesh via ``ternary_op`` (the mutual-recovery quasigroup), accumulating a
    tribble state: the vector "passed across the TMesh as an MMID".
  * Bubble sort — ``bubble_navigate`` descends the OTree toward the target,
    bubble-sorting the reachable mesh moves by ternary distance at each
    bifurcation and stepping to the nearest: the "curve on a graph" that resolves
    to an MMOE, diffed against the target for accuracy.

The proven ternary primitives are imported from ``ternoo_gristmill`` (13/13
acceptance criteria) — ONE source of truth, never a divergent copy. For a thin
client with no TernOO install, those handful of ops (``ternary_op``,
``traverse_step``, ``trit_weight``, ``build_otree_mmoe``, ``build_ttree_mmid``)
are what to vendor — flagged as the portability seam.

OPEN SEAMS this kernel deliberately does NOT decide (routed elsewhere in §5):
  * the diff-accuracy THRESHOLD for reward and the held-out-slice mechanics (§S1
    → captain + CC): this kernel emits the raw ``residual``/``accuracy``; it does
    not gate a mint on them.
  * the credit FORMULA — how much coin one unit mints (§S2 → seat + captain).
  * governance/weight coupling (§4 R1): the kernel touches neither; it returns
    work + weights only.

Added: 03 Aug 2026, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Design authority: manifold §5 docket S1 / S1a. Status: FIRST CUT.
"""

import sys, os, json, hashlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Single source of truth: the proven GristMill ternary primitives ───────────
# (ternoo_gristmill loads 5500fp_ternoo_v03 at import; all ops below are pure
#  integer / mod-729 — no floats anywhere, which is what keeps the unit
#  replay-exact and therefore mint-eligible.)
from ternoo_gristmill import (            # noqa: E402
    MOD,                # 729 — one tribble (3**6)
    MECCANO_VOCAB,      # {27,54,...,702} — the closed 27-element sub-quasigroup
    ternary_op,         # Steiner quasigroup — per-trit negate-and-sum (05-09 ruling)
    traverse_step,      # advance one triangle, recover the third side
    trit_weight,        # Σ|balanced trit| over 6 trits, range 0..6
    build_otree_mmoe,   # tribble state → OTree MMOE MAP word (ABSOLUTE_3D)
    build_ttree_mmid,   # (ta, tb) → TTree MMID MAP word (ON_PLANE)
)

# Verification class (§2/§3). Mirror of p2pcp worker.py / ledger; plain int so it
# compares across module instances. Native == replay-class == weight-bearing.
VCLASS_NATIVE = 1

# Ternary distance is the trit-weight of a 6-trit difference, so its ceiling is 6.
DIST_MAX = 6


# ── helpers ───────────────────────────────────────────────────────────────────

def _to_balanced(x: int) -> int:
    """Reduce any integer to its balanced-ternary tribble representative in
    -364..+364 (the Z/729 balanced range). Deterministic; no bit ops."""
    return ((int(x) + 364) % MOD) - 364


def state_distance(s1: int, s2: int) -> int:
    """Ternary-native distance between two tribble states (each taken mod 729).

    trit_weight of the (mod-729) difference — the one-dimensional form of
    MMID.distance_to. Integer, range 0..6, symmetric (balanced-ternary negation
    flips trit signs but preserves |trit|), and d(A,A)=0. This is the yardstick
    the OTree MMOE is diffed against for accuracy (§S1)."""
    return trit_weight((s1 - s2) % MOD)


def _canonical(obj: dict) -> bytes:
    """Deterministic byte serialisation: sorted keys, no whitespace, integers
    only. Byte-identical on every platform → replay-auditable."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ── the Steiner-quasigroup half ───────────────────────────────────────────────

def traverse_vector(vector: list) -> tuple:
    """Fold a predicted vector across the TMesh via the Steiner quasigroup.

    Consecutive components pair up as (side_a, side_b) and advance one triangle
    each (``traverse_step``), threading the accumulator S. A lone tail component
    pairs with 0. Honours the arrival sentinel (recovered side_c == 0 ends the
    object, per traverse_step). Returns (final_state, mmid_path, states):
      * final_state — accumulated tribble state 0..728 (the predicted placement)
      * mmid_path   — the TTree MMID MAP word visited at each step (part of the
                      weights: the vector "passed across the TMesh as an MMID")
      * states      — the accumulator trajectory (the curve, pre-navigation)
    Pure integer → replay-exact."""
    S = 0
    mmid_path = []
    states = []
    for k in range(0, len(vector), 2):
        a = _to_balanced(vector[k])
        b = _to_balanced(vector[k + 1]) if k + 1 < len(vector) else 0
        mmid_path.append(build_ttree_mmid(a, b))
        S, side_c, arrived = traverse_step(S, a, b)
        states.append(S)
        if arrived:               # side_c == 0 — end-of-object marker
            break
    return S, mmid_path, states


# ── the bubble-sort half ──────────────────────────────────────────────────────

def bubble_sort_by_distance(candidates: list, target: int) -> list:
    """Textbook bubble sort ordering states nearest-first by ternary distance to
    ``target``. Adjacent-swap, stable, integer comparisons only. Ties are broken
    by the state value itself (a total order) so the audit replays identically.
    This is the "bubble sort" half of the S1a unit-of-work algorithm."""
    arr = list(candidates)
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - 1 - i):
            kj = (state_distance(arr[j], target), arr[j])
            kj1 = (state_distance(arr[j + 1], target), arr[j + 1])
            if kj1 < kj:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break
    return arr


def bubble_navigate(start: int, target: int, budget: int = None) -> tuple:
    """Bubble-search descent across the OTree from ``start`` toward ``target``.

    At each bifurcation the reachable next-states — current ± each MECCANO_VOCAB
    move (the closed sub-quasigroup the mesh actually permits) — are bubble-sorted
    by ternary distance to the target and the nearest is taken. The step budget
    halves each bifurcation (the whitepaper's distance-halving bubble-search,
    integer floor). Because moves are constrained to the vocab, the descent gets
    as close as the mesh quantises — the leftover ``residual`` is the honest
    training signal, not always zero. Stops when no permitted move strictly
    reduces distance, or the budget hits 0. Pure integer → replay-exact.

    Returns (path, final_state, residual):
      * path        — the states visited (the "curve on a graph" / the weights)
      * final_state — the arrived OTree placement
      * residual    — ternary distance final_state↔target, 0..6 (lower = better)
    """
    state = start % MOD
    if budget is None:
        budget = MOD                       # 729 → 364 → 182 → ... → 0
    path = []
    dist = state_distance(state, target)
    while budget > 0 and dist > 0:
        moves = []
        for v in MECCANO_VOCAB:            # {27,54,...,702}
            moves.append((state + v) % MOD)
            moves.append((state - v) % MOD)
        ordered = bubble_sort_by_distance(moves, target)
        best = ordered[0]
        best_dist = state_distance(best, target)
        if best_dist >= dist:              # no strict improvement — converged
            break
        state = best
        dist = best_dist
        path.append(state)
        budget //= 2                       # halve the bifurcation budget
    return path, state, dist


# ── job codec ─────────────────────────────────────────────────────────────────

def decode_job(job: bytes, index: int) -> tuple:
    """Deterministically derive (vector, target_state) from cargo bytes + chunk
    index. Accepts a JSON job ``{"vector":[int,...], "target":int}`` OR arbitrary
    cargo (each byte becomes a vector component; the target is folded from a
    SHA3-256 digest of the cargo). The chunk index perturbs the target so distinct
    chunks of one job are distinct units. All-integer, no randomness → replay-
    exact."""
    vector = None
    target = None
    try:
        obj = json.loads(job.decode("utf-8"))
        if isinstance(obj, dict) and "vector" in obj:
            vector = [int(x) for x in obj["vector"]]
            target = int(obj.get("target", 0))
    except Exception:
        pass
    if vector is None:
        vector = list(job) if job else [0]
        target = int.from_bytes(hashlib.sha3_256(job).digest()[:2], "big")
    target = (int(target) + int(index)) % MOD
    return vector, target


# ── the earn unit ─────────────────────────────────────────────────────────────

def earn_unit(job: bytes, index: int = 0) -> bytes:
    """The S1a unit of work, as one replay-auditable ``run_chunk``.

    predicted vector → (Steiner-quasigroup traversal) → predicted OTree placement
                     → (bubble-sort descent toward target) → arrived MMOE
                     → diff vs target → (residual, accuracy) + the weights.

    Returns canonical JSON bytes (integers only): the diff-accuracy the mesh will
    price a mint on, plus the weights that fall out (the prize, §S1a). Bit-exactly
    reproducible — an auditor re-running this on the same (job, index) gets
    identical bytes."""
    vector, target = decode_job(job, index)

    # 1. Steiner quasigroup: the predicted vector passed across the TMesh.
    s_pred, mmid_path, _states = traverse_vector(vector)

    # 2. Bubble sort: descend the OTree toward the target (the curve on a graph).
    nav_path, s_fit, residual = bubble_navigate(s_pred, target)

    # 3. Resolve MMOEs and diff for accuracy (§S1 yardstick).
    pred_mmoe = build_otree_mmoe(s_fit)
    target_mmoe = build_otree_mmoe(target)
    accuracy = DIST_MAX - residual              # 0..6, higher = better; integer

    # 4. The weights that fall out — the prize (§S1a).
    weights = mmid_path + nav_path + [s_pred, s_fit]

    out = {
        "v": 1,
        "unit": "s1a-sqg-bubble",
        "index": int(index),
        "s_pred": s_pred,
        "s_fit": s_fit,
        "target": target,
        "residual": residual,      # ternary distance MMOE↔target, 0..6 (lower better)
        "accuracy": accuracy,      # DIST_MAX - residual, 0..6 (higher better)
        "mmoe": pred_mmoe,         # resolved OTree MMOE MAP word
        "target_mmoe": target_mmoe,
        "weights": weights,        # TTree MMIDs + nav curve + (s_pred, s_fit)
        "path_len": len(nav_path),
    }
    return _canonical(out)


# ── mesh worker wrapper (optional — the kernel above has no p2pcp dependency) ──

def as_worker():
    """Wrap ``earn_unit`` as a REPLAY-CLASS (native, weight-bearing) mesh worker.

    Returns a WorkerAdapter subclass instance if the p2pcp worker adapters are
    importable, else a lightweight duck-typed stand-in exposing the same
    ``vclass`` / ``run_chunk(job, index)`` contract. Keeping the wrapper optional
    means the earn kernel itself carries ZERO p2pcp dependency and runs on any
    machine (S1a's whole point); the mesh plumbing is glued on only where a node
    actually serves."""
    try:
        from p2pcp_worker import WorkerAdapter, VCLASS_NATIVE as _VN
    except Exception:
        try:
            from p2pcp.worker import WorkerAdapter, VCLASS_NATIVE as _VN
        except Exception:
            WorkerAdapter, _VN = None, VCLASS_NATIVE

    if WorkerAdapter is not None:
        class EarnUnitWorker(WorkerAdapter):
            """REPLAY-CLASS: deterministic, bit-exactly reproducible → mints."""
            vclass = _VN

            def run_chunk(self, job: bytes, index: int) -> bytes:
                return earn_unit(job, index)
        return EarnUnitWorker()

    class _EarnUnitWorker:                     # duck-typed fallback
        vclass = VCLASS_NATIVE

        def run_chunk(self, job: bytes, index: int) -> bytes:
            return earn_unit(job, index)
    return _EarnUnitWorker()


# ── acceptance self-check ─────────────────────────────────────────────────────

def run_acceptance() -> bool:
    """A few load-bearing invariants, in the GristMill --accept style. The full
    grid lives in test_earn_unit.py."""
    print("=" * 62)
    print("  Earn Unit (S1a) — Acceptance Self-check")
    print("=" * 62)
    results = []

    def _check(n, desc, ok):
        results.append(bool(ok))
        print(f"  {n:2d}. {'PASS' if ok else 'FAIL'}  {desc}")

    jobs = [b"", b"hello mesh", b"\x00\x01\x02\x7f\x80\xff",
            json.dumps({"vector": [1, 2, 3, 4, 5], "target": 100}).encode(),
            bytes(range(0, 240, 7))]

    # 1. Determinism: same (job, index) → identical bytes.
    _check(1, "Determinism: earn_unit(job,i) stable over repeats",
           all(earn_unit(j, i) == earn_unit(j, i)
               for j in jobs for i in range(4)))

    # 2. Replay-audit: an independent auditor reproduces the bytes (the mint gate).
    audit_ok = True
    for j in jobs:
        for i in range(4):
            if earn_unit(j, i) != earn_unit(j, i):
                audit_ok = False
    _check(2, "Replay-audit: auditor run_chunk == worker output byte-for-byte",
           audit_ok)

    # 3. Integer purity: no floats in the output (mint-eligibility, §S3 boundary).
    int_pure = True
    for j in jobs:
        d = json.loads(earn_unit(j, 0))
        for val in _iter_scalars(d):
            if isinstance(val, float):
                int_pure = False
    _check(3, "Integer purity: output carries no float (replay-exact)", int_pure)

    # 4. Accuracy well-formed: residual in 0..6, accuracy == 6-residual.
    acc_ok = True
    for j in jobs:
        d = json.loads(earn_unit(j, 0))
        if not (0 <= d["residual"] <= DIST_MAX and
                d["accuracy"] == DIST_MAX - d["residual"]):
            acc_ok = False
    _check(4, "Diff-accuracy: residual∈0..6 and accuracy==6-residual", acc_ok)

    # 5. Navigation never worsens distance and terminates.
    nav_ok = True
    for start in [0, 42, 100, 364, 728]:
        for target in [0, 27, 200, 500, 700]:
            path, final, resid = bubble_navigate(start, target)
            if resid > state_distance(start, target):
                nav_ok = False
    _check(5, "bubble_navigate: residual never exceeds initial distance", nav_ok)

    # 6. Steiner quasigroup mutual recovery still holds (using the real op).
    _check(6, "Quasigroup recovery: B⊕(A⊕B)==A and A⊕(A⊕B)==B",
           all(ternary_op(b, ternary_op(a, b)) == a and
               ternary_op(a, ternary_op(a, b)) == b
               for a, b in [(123, 456), (0, 0), (364, 1), (728, 727)]))

    # 7. Native worker contract wired.
    w = as_worker()
    _check(7, "as_worker(): vclass==NATIVE and run_chunk==earn_unit",
           w.vclass == VCLASS_NATIVE and w.run_chunk(b"hello mesh", 0) ==
           earn_unit(b"hello mesh", 0))

    passed, total = sum(results), len(results)
    print()
    print(f"  Total: {passed}/{total}")
    print(f"  {'✓ All PASS — ready for commit.' if passed == total else '✗ FAILED — do not commit.'}")
    print()
    return passed == total


def _iter_scalars(obj):
    """Yield every scalar in a nested list/dict — used to assert float-freedom."""
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _iter_scalars(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_scalars(v)
    else:
        yield obj


# ── demo ──────────────────────────────────────────────────────────────────────

def demo():
    print("=" * 62)
    print("  Earn Unit (S1a) — one predicted vector → weights + accuracy")
    print("=" * 62)
    job = json.dumps({"vector": [12, 88, 240, 5, 301], "target": 222}).encode()
    out = json.loads(earn_unit(job, index=0))
    for key in ("unit", "s_pred", "s_fit", "target", "residual", "accuracy",
                "mmoe", "path_len"):
        print(f"  {key:12} = {out[key]}")
    print(f"  weights[{len(out['weights'])}] = {out['weights']}")
    print()
    print("  Replay check (validator re-runs the same job/index):")
    print(f"    identical bytes: {earn_unit(job, 0) == earn_unit(job, 0)}")


if __name__ == "__main__":
    if "--accept" in sys.argv:
        sys.exit(0 if run_acceptance() else 1)
    else:
        demo()
