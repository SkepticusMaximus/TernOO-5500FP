#!/usr/bin/env python3
"""
test_earn_unit.py — acceptance grid for the S1a earn unit (earn_unit.py)
========================================================================

The earn unit is the mesh's minimal mint-worthy work (§S1/§S1a). For it to be
MINT-eligible (REPLAY-CLASS, §2) it must be bit-exactly reproducible: a validator
re-running ``earn_unit(job, index)`` gets identical bytes. These tests pin that
property (the mint gate) plus the two halves of the algorithm — the Steiner
quasigroup traversal and the bubble sort — and the native worker contract.

Run:  cd 5500fp && python3 -m unittest test_earn_unit

Added: 03 Aug 2026, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import earn_unit as E
from earn_unit import (
    earn_unit, bubble_sort_by_distance, bubble_navigate, traverse_vector,
    state_distance, decode_job, as_worker, VCLASS_NATIVE, DIST_MAX,
)
from ternoo_gristmill import MOD, MECCANO_VOCAB, ternary_op


# A spread of job cargoes: empty, text, raw bytes with high/low values, a JSON
# job, and a long deterministic byte run.
JOBS = [
    b"",
    b"hello mesh",
    b"\x00\x01\x02\x7f\x80\xff",
    json.dumps({"vector": [1, 2, 3, 4, 5], "target": 100}).encode(),
    json.dumps({"vector": [364, -364, 0, 728, -1], "target": 0}).encode(),
    bytes(range(0, 240, 7)),
    b"the quick brown fox" * 5,
]


class TestDeterminismAndReplayAudit(unittest.TestCase):
    """The mint gate: bit-exact reproducibility across independent runs."""

    def test_same_job_index_identical_bytes(self):
        for j in JOBS:
            for i in range(6):
                self.assertEqual(earn_unit(j, i), earn_unit(j, i),
                                 f"non-deterministic for job={j!r} index={i}")

    def test_replay_audit_matches(self):
        # Mirror the daemon's audit: a second, independent invocation stands in
        # for the auditor's run_chunk. Any mismatch would refuse the mint.
        worker = as_worker()
        auditor = as_worker()
        for j in JOBS:
            for i in range(4):
                self.assertEqual(worker.run_chunk(j, i), auditor.run_chunk(j, i))

    def test_output_is_bytes(self):
        for j in JOBS:
            self.assertIsInstance(earn_unit(j, 0), (bytes, bytearray))

    def test_output_is_canonical_json(self):
        # Canonical: sorted keys, no spaces — so it is byte-stable everywhere.
        for j in JOBS:
            raw = earn_unit(j, 0)
            self.assertEqual(raw, json.dumps(json.loads(raw), sort_keys=True,
                                             separators=(",", ":")).encode())


class TestIntegerPurity(unittest.TestCase):
    """No floats anywhere → replay-exact across platforms (the §S3 boundary)."""

    def _scalars(self, obj):
        if isinstance(obj, dict):
            for v in obj.values():
                yield from self._scalars(v)
        elif isinstance(obj, list):
            for v in obj:
                yield from self._scalars(v)
        else:
            yield obj

    def test_no_floats_in_output(self):
        for j in JOBS:
            d = json.loads(earn_unit(j, 0))
            for val in self._scalars(d):
                self.assertNotIsInstance(val, float,
                                         f"float leaked into output for {j!r}")

    def test_key_fields_are_ints(self):
        for j in JOBS:
            d = json.loads(earn_unit(j, 0))
            for key in ("s_pred", "s_fit", "target", "residual", "accuracy",
                        "mmoe", "target_mmoe", "path_len", "index"):
                self.assertIsInstance(d[key], int, f"{key} not int for {j!r}")


class TestDiffAccuracy(unittest.TestCase):
    """The yardstick the mesh will price a mint on (§S1)."""

    def test_residual_range(self):
        for j in JOBS:
            d = json.loads(earn_unit(j, 0))
            self.assertGreaterEqual(d["residual"], 0)
            self.assertLessEqual(d["residual"], DIST_MAX)

    def test_accuracy_complements_residual(self):
        for j in JOBS:
            d = json.loads(earn_unit(j, 0))
            self.assertEqual(d["accuracy"], DIST_MAX - d["residual"])

    def test_residual_equals_recomputed_distance(self):
        # residual must equal the ternary distance between the resolved fit state
        # and the target — the diff-for-accuracy, recomputed independently.
        for j in JOBS:
            d = json.loads(earn_unit(j, 0))
            self.assertEqual(d["residual"],
                             state_distance(d["s_fit"], d["target"]))


class TestStateDistance(unittest.TestCase):
    """The ternary metric behind the diff."""

    def test_identity_is_zero(self):
        for s in [0, 1, 42, 364, 728]:
            self.assertEqual(state_distance(s, s), 0)

    def test_symmetric(self):
        pairs = [(0, 27), (42, 700), (100, 500), (364, 1), (728, 0)]
        for a, b in pairs:
            self.assertEqual(state_distance(a, b), state_distance(b, a))

    def test_range_0_to_6(self):
        for a in range(0, MOD, 37):
            for b in range(0, MOD, 53):
                self.assertGreaterEqual(state_distance(a, b), 0)
                self.assertLessEqual(state_distance(a, b), DIST_MAX)


class TestBubbleSort(unittest.TestCase):
    """The bubble-sort half of the algorithm."""

    def test_orders_nearest_first(self):
        target = 222
        cands = [0, 27, 54, 700, 500, 222, 111, 333, 729 - 1]
        ordered = bubble_sort_by_distance(cands, target)
        keys = [(state_distance(c, target), c) for c in ordered]
        self.assertEqual(keys, sorted(keys), "not ordered nearest-first")

    def test_matches_reference_sort(self):
        # A bubble sort with the same total-order key must equal Python's sort.
        target = 351
        cands = list(range(0, MOD, 29))
        ordered = bubble_sort_by_distance(cands, target)
        ref = sorted(cands, key=lambda c: (state_distance(c, target), c))
        self.assertEqual(ordered, ref)

    def test_is_a_permutation(self):
        target = 100
        cands = [5, 5, 900, 12, 12, 0]     # includes duplicates
        ordered = bubble_sort_by_distance(cands, target)
        self.assertEqual(sorted(ordered), sorted(cands))

    def test_stable_total_order_is_deterministic(self):
        target = 400
        cands = list(range(0, MOD, 11))
        self.assertEqual(bubble_sort_by_distance(cands, target),
                         bubble_sort_by_distance(cands, target))


class TestBubbleNavigate(unittest.TestCase):
    """The constrained OTree descent (the curve on a graph)."""

    def test_never_worsens_distance(self):
        for start in range(0, MOD, 41):
            for target in range(0, MOD, 47):
                _path, final, resid = bubble_navigate(start, target)
                self.assertLessEqual(resid, state_distance(start, target))
                self.assertEqual(resid, state_distance(final, target))

    def test_terminates_and_is_deterministic(self):
        for start in [0, 42, 364, 728]:
            for target in [0, 27, 222, 700]:
                a = bubble_navigate(start, target)
                b = bubble_navigate(start, target)
                self.assertEqual(a, b)

    def test_moves_are_vocab_steps(self):
        # Every step lands on a state reachable by a single ±vocab move from the
        # previous — the mesh only permits sub-quasigroup moves.
        vocab = set(MECCANO_VOCAB)
        start, target = 42, 500
        path, _final, _resid = bubble_navigate(start, target)
        prev = start % MOD
        for nxt in path:
            deltas = {(nxt - prev) % MOD, (prev - nxt) % MOD}
            self.assertTrue(deltas & vocab,
                            f"step {prev}->{nxt} is not a single vocab move")
            prev = nxt

    def test_zero_distance_start_is_noop(self):
        path, final, resid = bubble_navigate(222, 222)
        self.assertEqual(resid, 0)
        self.assertEqual(final, 222)
        self.assertEqual(path, [])


class TestTraverseVector(unittest.TestCase):
    """The Steiner-quasigroup half."""

    def test_deterministic(self):
        vec = [12, 88, 240, 5, 301, 7]
        self.assertEqual(traverse_vector(vec), traverse_vector(vec))

    def test_state_in_range(self):
        for vec in ([1], [1, 2], list(range(20)), [364, -364, 728]):
            S, mmid_path, states = traverse_vector(vec)
            self.assertTrue(0 <= S < MOD)
            for s in states:
                self.assertTrue(0 <= s < MOD)

    def test_arrival_sentinel_stops_fold(self):
        # a paired with -a gives ternary_op(a,-a) = 0 → arrival on the first step.
        S, mmid_path, states = traverse_vector([100, -100, 5, 5, 5, 5])
        self.assertEqual(len(states), 1)      # stopped at the sentinel
        self.assertEqual(len(mmid_path), 1)


class TestWorkerContract(unittest.TestCase):
    """Plugging into the mesh as a REPLAY-CLASS (mintable) worker."""

    def test_vclass_is_native(self):
        self.assertEqual(as_worker().vclass, VCLASS_NATIVE)

    def test_run_chunk_matches_kernel(self):
        w = as_worker()
        for j in JOBS:
            for i in range(3):
                self.assertEqual(w.run_chunk(j, i), earn_unit(j, i))

    def test_index_changes_output_deterministically(self):
        # Distinct chunk indices are distinct units, but each is still stable.
        j = b"hello mesh"
        outs = [earn_unit(j, i) for i in range(6)]
        self.assertGreater(len(set(outs)), 1, "index had no effect")
        self.assertEqual(outs, [earn_unit(j, i) for i in range(6)])


class TestJobCodec(unittest.TestCase):
    """Deterministic decode of both JSON and raw-cargo jobs."""

    def test_json_job_roundtrip(self):
        job = json.dumps({"vector": [1, 2, 3], "target": 55}).encode()
        vec, target = decode_job(job, 0)
        self.assertEqual(vec, [1, 2, 3])
        self.assertEqual(target, 55)

    def test_index_offsets_target(self):
        job = json.dumps({"vector": [1], "target": 10}).encode()
        _v0, t0 = decode_job(job, 0)
        _v1, t1 = decode_job(job, 1)
        self.assertEqual(t0, 10)
        self.assertEqual(t1, 11)

    def test_raw_bytes_job_is_deterministic(self):
        self.assertEqual(decode_job(b"\x01\x02\x03", 2),
                         decode_job(b"\x01\x02\x03", 2))

    def test_empty_job_is_handled(self):
        vec, target = decode_job(b"", 0)
        self.assertEqual(vec, [0])
        self.assertTrue(0 <= target < MOD)


class TestSelfCheck(unittest.TestCase):
    def test_run_acceptance_passes(self):
        self.assertTrue(E.run_acceptance())


if __name__ == "__main__":
    unittest.main(verbosity=2)
