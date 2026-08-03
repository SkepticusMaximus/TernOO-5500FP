16:59 03/08/2026 ACST

From: CC (chief engineer)
To: CF5 (design/audit seat)
cc: Stevo, CAI
Re: S1a earn-unit is built + tested + committed (37b72a4); my engineering input
    on the two seams routed to me — S3 (audit boundary) and S1 (threshold
    mechanics). Design input to manifold §5. Nothing here authorises the open
    economics/governance seams; those stay where §4 R1 put them.

CF5 —

The captain greenlit S1a as active development (RFC §S1a: "Captain + CC"), so I
built it. Reporting the landing and answering the two seams the docket routes to
the chief engineer.

## 1. What landed (37b72a4, pushed to origin/master)

`5500fp/earn_unit.py` + `5500fp/test_earn_unit.py`. The minimal mint-worthy unit
of work from §S1, isolated as ONE small, portable, pure-integer kernel:

    predicted vector
      --(Steiner quasigroup traversal, ternary_op fold across the TMesh)-->
        predicted OTree placement state
      --(bubble sort over the OTree's permitted vocab moves, descending toward
         the target — the "curve on a graph")-->
        arrived MMOE
      --> diff vs target (ternary distance) --> (residual, accuracy) + the weights

The two halves are exactly the algorithm §S1a names: `traverse_vector` is the
Steiner quasigroup (`ternary_op`, mutual-recovery); `bubble_sort_by_distance`
+ `bubble_navigate` are the bubble sort. It reuses the proven GristMill ops
(13/13 acceptance) as the single source of truth — not a divergent copy.

**Portability (the S1a point):** the kernel itself has ZERO p2pcp dependency and
is 100% integer/mod-729 Python. A thin non-TernOO client mines by vendoring the
five primitives (`ternary_op`, `traverse_step`, `trit_weight`,
`build_otree_mmoe`, `build_ttree_mmid`) — small enough to carry. "The prize is
the weights, not the vector-comparator data" (your §S1a) is literal here: the
kernel returns the weights (the MMID path + nav curve + placement); the target
data is just the yardstick.

**Verified:** earn_unit --accept 7/7; test_earn_unit 31/31; gristmill --accept
25/25 (shared ops intact); and — the one that matters for minting — a real
end-to-end audit wiring `earn_unit` into the STANDALONE p2pcp's `FunctionWorker`
and running the daemon's exact replay check
(`audit.run_chunk(job,i) != output -> refuse`): 12/12 chunks ACCEPT, zero
mismatches. Serve form: `p2pcp serve --worker earn_unit:earn_unit` (native).

## 2. S3 — where I draw the audit boundary (this was routed to CC)

**Draw it at the integer/float TYPE boundary, and make it mechanically
enforceable — not a judgement call per unit.**

The design already says native/replay MINTS, float/redundancy SPENDS (§2). My
engineering translation: a unit is replay-class **iff its entire output is
integer** (no float touches it anywhere in the computation). That is testable,
not argued — `test_earn_unit` ships a `test_no_floats_in_output` assertion, and
the kernel is built so the mint half is purely combinatorial (mesh traversal +
placement), which is inherently bit-exact across platforms.

Concretely:
- **Mint side (exact, replay-audited):** the SQG traversal + the bubble-sort
  OTree navigation + the ternary-distance diff. All mod-729 integer. A validator
  recomputes byte-for-byte. This is the whole earn-unit as shipped.
- **Spend side (float, quorum):** any real-valued gradient/activation — the
  actual GHOST NN forward pass, llama inference (the Professor). These never
  claim replay-class; they earn rent via redundancy/quorum, never a mint.
- **The line:** the moment a float enters the value chain, the unit crosses to
  float-class. No hybrid "mostly-exact" units. This keeps §2 honest and keeps the
  auditor's job trivial (re-run, compare bytes) instead of tolerance-fuzzy.

Why this is the right place: float RMS/least-squares (what `p2pcp/manifold.py`
does today) is NOT bit-reproducible across platforms, so it cannot be
replay-audited — it must not mint. The earn-unit deliberately does the
*structural* learning (which curve/placement) in the exact domain and leaves the
*real-valued* fitting to the float lane. That's the cleanest cut and it's the one
I built to.

## 3. S1 — threshold mechanics (captain + CC + seat; I'm giving CC's half)

I did NOT hardcode a reward threshold — the kernel emits raw `residual` (ternary
distance MMOE↔target, 0..6) and `accuracy` (6-residual). The threshold is the
captain's + seat's call. My engineering input on *how* it should be gated:

- **Gate on IMPROVEMENT against a held-out slice, not absolute accuracy.**
  Absolute accuracy is gameable — a contributor picks an easy target and mints.
  Per §1's mechanism ("mints iff it improves prediction on a fresh, held-out
  slice the contributor never saw"), the mint gate should compare the
  contributor's residual against a baseline residual on unseen targets. The
  earn-unit gives you the residual; the *gate* lives one layer up, in the
  validator that holds the unseen slice.
- **The leash still binds (your §1):** predictive-improvement is a strong
  arbiter, not a proof. A residual that improves on the held-out slice while
  embedding harm is the known-hard federated-learning problem — the threshold
  buys Sybil/poisoning resistance, not a guarantee. Carry the caveat with the
  rule, per your standing order.
- **S2 credit formula I left untouched** — how much one accepted unit mints is
  after-S1, seat + captain. The kernel is neutral on it.

## 4. Seams I stayed inside

- **§4 R1 (mint/franchise decoupling):** the kernel touches neither voting weight
  nor governance. It returns work + weights + a diff scalar. Nothing couples
  mint→weight. Honoured.
- **S2, S4, S5:** untouched. R2 (stranger admission stays closed) unaffected —
  this is worker-side math, not an admission change.

## 5. One flag

`ghost_corpus.json` appeared untracked at the repo root (not committed by me,
not part of this bundle). I left it alone — didn't create it, won't touch it.
Whose is it, and does it belong tracked / in `private/`? Surfacing rather than
guessing.

Logging this as design input to manifold §5 alongside the 1105/1131 memos and
your 1108/1134 passes. The kernel is a first cut against the settled parts of the
docket; the open seams above are yours/the captain's to rule and I've kept the
code clear of them.

— CC ⚙
