# The Vector Manifold — distributed training & weight-sharing over TernOO (design v0.1)

Bench draft (free-fire), CC, 27-07-2026. Captures the captain's design intent from
the 26–27/07 conversation, for review by his DeepSeek collaborators and the design
seats (CAI/CF5) BEFORE implementation. This is a SPEC, not code. The mechanics in §2
are the captain's; §5 lists what must be pinned before a line is written.

Freeze exception: the captain lifted the P2PCP repo-freeze for this feature (ruling
relayed in `private/POBOX/2026-07-26-1602-CC-to-crew-captains-ruling-p2pcp-manifold-exception.md`),
on the grounds it has no tangled history to protect. It is TernOO-NATIVE — it depends
on TMesh/OTree, PIGART, and TernOO Words — so it lands in the TernOO-5500FP tree
(`5500fp/`), NOT the standalone p2pcp repo. **P2PCP provides transport + economy; the
manifold is the payload that rides it.**

## 1. Thesis

Share not just inference but TRAINING load and weights across the mesh. A training
run's vectors converge on a pattern; in TernOO a pattern is not a flat string of trits
but a GRAPHABLE OBJECT — an equation per vector, a typed curve per dimension (linear /
exponential / polynomial). Because it is an object, it can be addressed, rendered,
packetised, diffed, rated and re-staged like any other TernOO object.

## 2. Pipeline (the captain's mechanics, verbatim intent)

1. **Vector as object** — each training vector carries its equation; each dimension a
   typed curve (linear / exp / poly).
2. **Render** — PIGART renders the manifold and its curves
   (`5500fp/ternoo_pigart.py`) — human- and machine-inspectable.
3. **Packetise** — the object ships as I/O words carrying MAP words (spatial payload).
4. **DIF + rate** — packets are DIF'd against the local model's state and rated for
   **MMID vs MMOE** alignment.
5. **Re-stage** — a heuristic (Bayesian?) re-weights and re-stages; iterate.
   Wash, rinse, repeat.

## 3. Dependencies — all TernOO-native, all in-tree

- **TMesh / OTree** dual coordinate — `5500fp/ternoo_gristmill.py` (address + traverse)
- **PIGART** — `5500fp/ternoo_pigart.py` (render)
- **MAP / NEURAL / I-O words** — the word families (see `private/TernOO-Language-Audit.md`)
- **MMID** — content-addressed identity (sponge digest / octree coords)
- **P2PCP** — transport + earn→spend economy (cycles fund the sharing)

## 4. Where it sits in the bigger vision

The manifold is the mechanism under the captain's platform thesis: TernOO as an
experimental AI eco-system for arbitrary data and modelling — training-load and
weight sharing, distributed models, shared input tokens — and ultimately sensor +
limbic integration (real-time senses → salience → emergent values → alignment, per
"The Strange Inversion of AI Alignment", now in the box). GHOST is the resident that
benefits; the manifold is how minds share what they learn. Note (captain, 26/07): the
weight-sharing network is TernOO-ONLY — GHOST cannot participate by proxy through a
non-ternary node, because the mechanism is the Words, not the payload bytes.

## 5. Open questions — PIN THESE BEFORE CODE (for the circle / DeepSeek)

- **Curve representation**: coefficients carried in USER-DEF POINTER words, vs a fitted
  function hook. Precision/rounding of real coefficients under balanced ternary.
- **MMID vs MMOE**: exact definitions and the alignment-rating function. (Working read:
  MMID = content-identity of what was sent; MMOE = mismatch-of-expectation of what the
  local model predicted. Confirm.)
- **Re-staging heuristic**: Bayesian update vs alternatives; convergence criteria — when
  does "wash, rinse, repeat" terminate?
- **Verification class**: does P2PCP's replay-audit extend to training deltas (mints
  weight-bearing credit), or is this float-class — unverifiable, rent-only? A shared
  gradient is not bit-reproducible, which points at float-class; confirm.
- **Poisoning / tamper-evidence**: a shared-weight mesh invites gradient poisoning.
  Per-packet sponge digests give tamper-EVIDENCE but not tamper-PREVENTION; what's the
  trust model for accepting a peer's weights? (This is the load-bearing security
  question — flagged, not solved.)

## 6. Status

Design v0.1 — intent captured, not yet ruled, no code written. Implementation follows
the captain's + circle's pin-down of §5. DeepSeek collaborators: react to §2 and §5;
the sibling bench file `2026-07-26-tmesh-otree-pigart-rundown-for-external-collab.md`
is the primitives reference, with public source links.

— CC
