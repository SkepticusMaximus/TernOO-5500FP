#!/usr/bin/env python3
"""
TernOO-Appropriate Semantic Benchmark Suite
=============================================
Tests the SEMANTIC strengths of the TernOO word architecture.

Targets:
  A) Pure Python (baseline)
  B) v0.1 emulator  — 5500FP ISA + trit primitives, NO word-format layer
  C) v0.3 emulator  — 5500FP ISA + full TernOO word-format layer

Benchmarks:
  1. Word type dispatch        (route N words by primary type)
  2. Heterogeneous word stream (mixed-type pipeline)
  3. Tribble extraction        (structural addressing)
  4. Object accumulation       (build a typed word pool)
  5. Graph walk                (FlowCode-style DFS)
"""

import os as _os
import sys, os, time, csv, importlib.util

REPO = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))), "5500fp")
sys.path.insert(0, REPO)

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

v01 = load_module("emu_v01", os.path.join(REPO, "5500fp_emulator.py"))
v03 = load_module("emu_v03", os.path.join(REPO, "5500fp_ternoo_v03.py"))

# Derived constants
PAYLOAD_MAX_V03 = (3 ** v03.PAYLOAD_WIDTH - 1) // 2   # max 18-trit payload

ITERS       = 10_000
GRAPH_NODES = 200
GRAPH_LINKS = 400
REPS        = 3

def timer(fn, *args):
    t0 = time.perf_counter_ns()
    result = fn(*args)
    return (time.perf_counter_ns() - t0) / 1_000_000.0, result

def run_rep(fn, *args):
    return min(timer(fn, *args)[0] for _ in range(REPS))

# ── Helpers ───────────────────────────────────────────────────────────────────
def v03_build_word(t, payload):
    """Build a v03 word of type t (0..8) with given payload."""
    p = payload % PAYLOAD_MAX_V03
    seg = p % 100
    off = p % 1000
    if   t == 0: return v03.build_exec_word(0, 0, 0, seg, off)   # EXEC
    elif t == 1: return v03.build_map_word(0, 0, 0, p)            # MAP
    elif t == 2: return v03.build_int_word(p)                     # DATA/int
    elif t == 3: return v03.build_io_word(0, 0, 0, p % 100)      # IO
    elif t == 4: return v03.build_opcode_word(p % 4, 0)            # OPCODE (family 0..3)
    elif t == 5: return v03.build_exec_word(0, 1, 0, seg, off)   # EXEC variant
    elif t == 6: return v03.build_map_word(1, 0, 0, p)            # MAP variant
    elif t == 7: return v03.build_uint_word(p)                    # DATA/uint
    else:        return v03.build_null_word(p % 100)              # POOL/null


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Word type dispatch
# ═══════════════════════════════════════════════════════════════════════════════

def bench_dispatch_pure_python(n):
    handlers = [
        lambda v: v + 1, lambda v: v + 2, lambda v: v + 3,
        lambda v: v + 4, lambda v: v + 5, lambda v: v * 2,
        lambda v: v - 1, lambda v: v ^ 0xFF, lambda v: v * 3,
    ]
    total = 0
    for i in range(n):
        total += handlers[i % 9](i % 729)
    return total

def bench_dispatch_v01(n):
    """v0.1: Encode type in high trits, decode with to_trits, dispatch."""
    total = 0
    for i in range(n):
        t = i % 9
        payload = i % 729
        # Pack type (0..8) into T22-T23 as balanced ternary
        # Map 0..8 → balanced ternary pair: subtract 4 to centre on 0
        bt = t - 4          # -4..+4
        t1 = bt % 3         # low trit
        if t1 == 2: t1 = -1
        t2 = (bt - t1) // 3 # high trit
        word_val = payload + (t1 + 4) * (3**22) + (t2 + 4) * (3**23)
        trits = v01.to_trits(v01.clamp_word(word_val), 24)
        type_key = t  # use original t for dispatch (encoding is illustrative)
        if   type_key == 0: total += payload + 1
        elif type_key == 1: total += payload + 2
        elif type_key == 2: total += payload + 3
        elif type_key == 3: total += payload + 4
        elif type_key == 4: total += payload + 5
        elif type_key == 5: total += payload * 2
        elif type_key == 6: total += payload - 1
        elif type_key == 7: total += payload ^ 0xFF
        else:               total += payload * 3
    return total

def bench_dispatch_v03(n):
    """v0.3: Self-describing word — primary field IS the type, no lookup."""
    total = 0
    for i in range(n):
        t = i % 9
        payload = i % 729
        w = v03_build_word(t, payload)
        p = v03.get_primary(w)
        pv = v03.get_payload(w)
        if   p == v03.PRIMARY_EXEC:   total += pv + 1
        elif p == v03.PRIMARY_MAP:    total += pv + 2
        elif p == v03.PRIMARY_DATA:   total += pv + 3
        elif p == v03.PRIMARY_IO:     total += pv + 4
        elif p == v03.PRIMARY_OPCODE: total += pv + 5
        else:                         total += pv
    return total

# ═══════════════════════════════════════════════════════════════════════════════
# 2. Heterogeneous word stream
# ═══════════════════════════════════════════════════════════════════════════════

def bench_hetstream_pure_python(n):
    total = 0
    for i in range(n):
        t, v = i % 9, i % 729
        if   t == 0: total += v * 2
        elif t == 1: total += v + v
        elif t == 2: total += v
        elif t == 3: total += v // 3 if v else 0
        elif t == 4: total += v ^ 0xFF
        elif t == 5: total += v * v % 10000
        elif t == 6: total += v + 1
        elif t == 7: total += v - 1 if v else 0
        else:        total += v * 3
    return total

def bench_hetstream_v01(n):
    total = 0
    for i in range(n):
        t, v = i % 9, i % 729
        word_val = v01.clamp_word(v + t * (3**18))
        trits = v01.to_trits(word_val, 24)
        pv = v01.from_trits(trits[:18])
        if   t == 0: total += pv * 2
        elif t == 1: total += pv + pv
        elif t == 2: total += pv
        elif t == 3: total += pv // 3 if pv else 0
        elif t == 4: total += pv ^ 0xFF
        elif t == 5: total += pv * pv % 10000
        elif t == 6: total += pv + 1
        elif t == 7: total += pv - 1 if pv else 0
        else:        total += pv * 3
    return total

def bench_hetstream_v03(n):
    total = 0
    for i in range(n):
        t, v = i % 9, i % 729
        w = v03_build_word(t, v)
        p = v03.get_primary(w)
        pv = v03.get_payload(w)
        if   p == v03.PRIMARY_EXEC:   total += pv * 2
        elif p == v03.PRIMARY_MAP:    total += pv + pv
        elif p == v03.PRIMARY_DATA:   total += pv
        elif p == v03.PRIMARY_IO:     total += pv ^ 0xFF
        elif p == v03.PRIMARY_OPCODE: total += pv + 1
        else:                         total += pv * 3
    return total

# ═══════════════════════════════════════════════════════════════════════════════
# 3. Tribble extraction
# ═══════════════════════════════════════════════════════════════════════════════

def bench_tribble_pure_python(n):
    total = 0
    for i in range(n):
        tmp = (i * 1234567) % (3**24)
        for _ in range(6):
            tribble = 0
            for bit in range(4):
                r = tmp % 3
                if r == 2: r = -1
                tribble += r * (3 ** bit)
                tmp = (tmp - r) // 3
            total += tribble
    return total

def bench_tribble_v01(n):
    total = 0
    for i in range(n):
        w = (i * 1234567) % (3**24)
        trits = v01.to_trits(w, 24)
        for t in range(6):
            s = t * 4
            total += trits[s] + trits[s+1]*3 + trits[s+2]*9 + trits[s+3]*27
    return total

def bench_tribble_v03(n):
    total = 0
    for i in range(n):
        w = (i * 1234567) % (3**24)
        trits = v03.to_trits(w, 24)
        for t in range(6):
            s = t * 4
            total += trits[s] + trits[s+1]*3 + trits[s+2]*9 + trits[s+3]*27
    return total

# ═══════════════════════════════════════════════════════════════════════════════
# 4. Object accumulation
# ═══════════════════════════════════════════════════════════════════════════════

def bench_objpool_pure_python(n):
    pool = [{"type": i % 9, "value": i * 7 % 729} for i in range(n)]
    return sum(o["value"] for o in pool)

def bench_objpool_v01(n):
    """v0.1: Encode objects as raw trit integers."""
    pool = [v01.clamp_word(i * 7 % 729 + (i % 9) * (3**18)) for i in range(n)]
    return sum(v01.from_trits(v01.to_trits(w, 24)[:18]) for w in pool)

def bench_objpool_v03(n):
    """v0.3: Self-describing typed words — type is structural, not a tag."""
    pool = [v03_build_word(i % 9, i * 7 % 729) for i in range(n)]
    return sum(v03.get_payload(w) for w in pool)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. Graph walk (FlowCode-style DFS)
# ═══════════════════════════════════════════════════════════════════════════════

def make_adj(n_nodes, n_links):
    adj = {i: [] for i in range(n_nodes)}
    for i in range(n_links):
        src = i % n_nodes
        dst = (i * 7 + 3) % n_nodes
        if src != dst:
            adj[src].append(dst)
    return adj

def bench_graphwalk_pure_python(n_nodes, n_links):
    adj = make_adj(n_nodes, n_links)
    values = [i * 3 % 729 for i in range(n_nodes)]
    visited, stack, total = set(), [0], 0
    while stack:
        node = stack.pop()
        if node in visited: continue
        visited.add(node)
        total += values[node]
        stack.extend(nb for nb in adj[node] if nb not in visited)
    return total

def bench_graphwalk_v01(n_nodes, n_links):
    """v0.1: Node values as raw trit words, links as integer pairs."""
    adj = make_adj(n_nodes, n_links)
    nodes = [v01.clamp_word(i * 3 % 729) for i in range(n_nodes)]
    visited, stack, total = set(), [0], 0
    while stack:
        node = stack.pop()
        if node in visited: continue
        visited.add(node)
        total += v01.from_trits(v01.to_trits(nodes[node], 24)[:18])
        stack.extend(nb for nb in adj[node] if nb not in visited)
    return total

def bench_graphwalk_v03(n_nodes, n_links):
    """v0.3: Nodes are MAP words, links are EXEC words — self-describing."""
    adj = make_adj(n_nodes, n_links)
    nodes = [v03.build_map_word(0, 0, 0, i * 3 % PAYLOAD_MAX_V03) for i in range(n_nodes)]
    visited, stack, total = set(), [0], 0
    while stack:
        node = stack.pop()
        if node in visited: continue
        visited.add(node)
        total += v03.get_payload(nodes[node])
        stack.extend(nb for nb in adj[node] if nb not in visited)
    return total

# ═══════════════════════════════════════════════════════════════════════════════
# Run
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 80)
print("TernOO-Appropriate Semantic Benchmark Suite")
print(f"  N={ITERS:,}  |  Graph: {GRAPH_NODES} nodes / {GRAPH_LINKS} links  |  Best of {REPS} reps")
print("=" * 80)

benchmarks = [
    ("Word Dispatch",
     bench_dispatch_pure_python, (ITERS,),
     bench_dispatch_v01,         (ITERS,),
     bench_dispatch_v03,         (ITERS,)),
    ("Het. Word Stream",
     bench_hetstream_pure_python, (ITERS,),
     bench_hetstream_v01,         (ITERS,),
     bench_hetstream_v03,         (ITERS,)),
    ("Tribble Extraction",
     bench_tribble_pure_python,   (ITERS,),
     bench_tribble_v01,           (ITERS,),
     bench_tribble_v03,           (ITERS,)),
    ("Object Accumulation",
     bench_objpool_pure_python,   (ITERS,),
     bench_objpool_v01,           (ITERS,),
     bench_objpool_v03,           (ITERS,)),
    ("Graph Walk",
     bench_graphwalk_pure_python, (GRAPH_NODES, GRAPH_LINKS),
     bench_graphwalk_v01,         (GRAPH_NODES, GRAPH_LINKS),
     bench_graphwalk_v03,         (GRAPH_NODES, GRAPH_LINKS)),
]

results = []
print(f"\n{'Benchmark':<24} {'Pure Py':>10} {'v0.1':>10} {'v0.3':>10} {'v01/py':>9} {'v03/py':>9} {'v03/v01':>9}")
print("-" * 85)

for row in benchmarks:
    name, py_fn, py_args, v01_fn, v01_args, v03_fn, v03_args = row
    py_ms  = run_rep(py_fn,  *py_args)
    v01_ms = run_rep(v01_fn, *v01_args)
    v03_ms = run_rep(v03_fn, *v03_args)
    r01 = v01_ms / py_ms  if py_ms  > 0 else 0
    r03 = v03_ms / py_ms  if py_ms  > 0 else 0
    r13 = v03_ms / v01_ms if v01_ms > 0 else 0
    print(f"  {name:<22} {py_ms:>9.2f} {v01_ms:>10.2f} {v03_ms:>10.2f} {r01:>8.2f}x {r03:>8.2f}x {r13:>8.2f}x")
    results.append({
        "benchmark":     name,
        "pure_py_ms":    round(py_ms,  3),
        "v01_ms":        round(v01_ms, 3),
        "v03_ms":        round(v03_ms, 3),
        "v01_vs_python": round(r01, 3),
        "v03_vs_python": round(r03, 3),
        "v03_vs_v01":    round(r13, 3),
    })

print()
print("  v01/py  = cost of trit-encoding overhead vs pure Python")
print("  v03/py  = cost of TernOO word-format layer vs pure Python")
print("  v03/v01 = additional cost of self-describing word format over raw ISA")

csv_path = "/tmp/ternoo_semantic_bench.csv"
with open(csv_path, "w", newline="") as f:
    wr = csv.DictWriter(f, fieldnames=results[0].keys())
    wr.writeheader()
    wr.writerows(results)
print(f"\nResults written to {csv_path}")
