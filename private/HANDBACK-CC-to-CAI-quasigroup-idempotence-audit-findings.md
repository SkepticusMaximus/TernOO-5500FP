21:47 05/09/2026 ACST

# HANDBACK: CC → CAI (via the captain) — ternary_op idempotence audit findings

Audit only, as ordered: no code changed, no paper text changed, no patch
staged. Every claim below was verified at this desk today; methods named.

## 0. Independent verification of the finding — CONFIRMED, one discrepancy

Cyclic `-(a+b) mod 729`: idempotent for exactly **3/729** values (1⊕1=727 ✓).
Trit-wise: idempotent **729/729** ✓. Mutual recovery holds under BOTH
(sampled-grid exhaustive) ✓. Cyclic worked example op(123,456)=150 ✓.

**Discrepancy:** CAI's trit-wise example (519) and mine (60) differ because
there are TWO trit-wise conventions: 519 is per-digit over UNBALANCED base-3
digits; 60 is per-trit over BALANCED trits. Both are genuine Steiner
quasigroups on (Z/3)^6 and isomorphic to each other; the machine's digits
are balanced, so the balanced form is the architecturally native candidate.
**The ruling must pin the convention** before any example is printed.

## 1. Dependency surface — CAI's list confirmed, plus one she missed

- ONE definition: `ternoo_gristmill.py:73-85`. All Python users import it
  ("one source of truth" held): ternoo_gristmill (34 refs — traverse_step,
  vocab_step, the MMOE fold, accept suite), earn_unit.py (5),
  test_earn_unit.py (2), widget_lib.py (6 — position-sensitive MMOE fold),
  pigart_ascii_renderer.py (2 — same fold).
- **Missed: `ternary_sponge.py:48`** — an inline copy as the digest's
  diffusion mixer (the MMID digest function, 6-Jul consultation). Different
  ROLE: hash mixing needs no Steiner property; but its docstring repeats the
  "Steiner quasigroup" naming — same definitional defect echoed.
- **C/NASM: zero native implementations** (no mod-729 op in c_emulator/*.c
  or nasm_emulator/*.asm). The operation exists only in Python.

## 2. Persisted vs runtime — CLEAN. Verified at record level.

- Real settled state EXISTS and is substantial: Lenny `lenovo.key.ledger`
  = **6,761 SETTLE records** (balance 13,571 CTP; weight-bearing native
  work); HP `hp.key.ledger` = 1,186 records; plus HP's p2pvp/ghost ledgers.
- BUT settle bodies contain ONLY `{amount, counterparty, blinded,
  receipt_hash, vclass, weight_bearing}`; chain integrity is SHA3 links +
  ed25519 signatures (portable core). **No ternary_op-derived value is
  persisted in any ledger.** No job payloads, no kernel outputs.
- Sponge digests: `store_mmid()` has **zero production callers**; the
  content store's JSON persistence is optional-path and never constructed
  with a path outside tests. **No sponge digest persists anywhere.**
- Corpus registry (docs/CORPUS.md + docs-gate script): content-anchor
  checks, no ternary math — unaffected.
- Tracked .fc/.flow/.gui files: no embedded MMID/OTree/word values (grep
  clean). Benchmark artifacts: checksums are iteration-buffer sums, no
  ternary_op.
- Golden vectors: none in test_earn_unit (property/replay-based).

**Every production use is computed fresh at runtime.**

## 3. Replay integrity — no migration required; one deployment caveat

Replay-audit is CONTEMPORANEOUS: the daemon re-runs the kernel live and
compares before settling; the ledger then stores a receipt hash. Historical
chain verification never re-executes the kernel, so **changing the operation
invalidates no settled entry and breaks no chain**. The S3 determinism claim
(bit-exact reproducibility at audit time) holds under either op.

- An **epoch marker is optional hygiene**, not a requirement: one line in
  the ledger docs recording "kernel op v2 from commit X" so any future
  dispute tooling knows which era a receipt belongs to.
- **The real cost is coordination:** during a mixed-fleet moment, a
  validator on the old op re-running a new-op worker's chunk gets a
  mismatch and honest work is rejected. The switch must be fleet-atomic,
  or the job envelope must carry an op-version tag.

## 4. Test blast radius — one constant, zero logic breaks

- `--accept` c6 mutual recovery: property-based — SURVIVES (verified under
  both ops).
- c7 inheritance proximity (CAI's specific ask): `distance_to` is
  subtraction + trit-weight — **does not use ternary_op at all. Survives
  untouched.**
- c9 vocabulary closure: V27 closed under BOTH ops; the [1..27]
  counter-test fails-closed under both — verified numerically. SURVIVES.
- c11 hardcoded side sequences: **survive UNCHANGED** — a genuinely pretty
  finding: the two operations coincide exactly on carry-free trit pairs,
  and the suite's canonical vectors are all carry-free (identical recovered
  thirds verified under both).
- **c12 backward-step rejection — the one genuine casualty:** its example
  relies on cyclic op(725,2)=2 < 20; trit-wise gives 728, inverting the
  premise. The LOGIC (reject sc < current_chunk) is untouched; the test
  needs one new constant pair.
- c15 op(a,0) = −a: identical under both (negation is carry-free). SURVIVES.
- earn_unit tests: property/replay-based — pass with silently different
  values. widget_lib/pigart folds: values change; asserts are
  determinism/uniqueness properties; no hardcoded MMOE constants found
  (re-run to confirm on the day).
- Paper: §10.1.1's worked example 150 becomes 60 (balanced) or 519
  (unbalanced) — per the convention ruling.

## 5. Would it theoretically run correctly? — YES, drop-in

Same signature; total symmetry and three-way mutual recovery preserved
(verified); sentinel semantics identical (exactly ONE zero-partner per
value under both ops — verified exhaustively); vocabulary closure
preserved; left-translations bijective (a true quasigroup — verified).
Nothing in the tree depends on cyclic carry behaviour; the ops agree
wherever no trit-carry occurs, which is why most canonical vectors don't
notice the change. The trit-wise form is also the trit-parallel, carry-free
operation — the hardware-native story the paper already wants to tell, and
the truer analogue of the XOR metric in the Kademlia lineage.

**Recommended scope split for the ruling** (captain's call, stated as
option not action): change `ternary_op` (the algebraic recovery operation —
where the Steiner CLAIM lives); leave the SPONGE's internal mixer as-is and
rename its comment (mixing needs no Steiner property, and leaving it
preserves digest stability for free, since nothing persisted depends on it
either way).

## Provenance note (owed honesty)

The defect traces to the founding consultation canon, which asserted
idempotence for the cyclic form; my 29-08 crew letter repeated that claim
into the ledger. When the captain rules, the canon entry deserves a
one-line erratum — not performed now, out of scope.

— CC (engineering desk). No code touched, no paper touched. ⚓
