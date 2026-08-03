14:44 03/08/2026 ACST

# Stevo → crew — RFC's On P2PCP Dual Manifold Design.

From: Stevo
To: crew
Re: RFC's On P2PCP Dual Manifold Design.

12:58 03/08/2026 ACST

# CF5 → crew — Manifold §5 Spec Skeleton v0.2 (captain's edits applied)

From: CF5 (design/audit chair)
To: crew (Stevo, CC, CAI)
Re: home document for the §5 docket. v0.2 amends v0.1 per the captain's live
    corrections 03-08 (history order, no renames, trit-for-trit, S1 unit-of-work
    proposal, MMID/MMOE closed as settled). Nothing here authorises code.
    Companion to `private/docs-bench/drafts/2026-07-27-vector-manifold-design-v0.1.md`.

Sources: CC 03-08 11:05 + 11:31; CF5-worker passes 11:08 + 11:34; captain's
rulings live in the CF5 chat thread 03-08.

---

## 0. Constitutional context — SETTLED (captain, 03-08)

**TernOO adopts P2PCP as one of its own.** History, in correct order: the original
P2PCP was a proposed inference load-balancing protocol — use spare machine cycles
(the SETI@home model, the real astronomical one) to compute inference. Testing
02-08 showed that unfeasible: inference is linear token prediction and cannot be
load-balanced across a wire; the standalone protocol in practice passes prompts,
with the remote model answering. The vector-learning idea arrived ~a week ago (the
captain's DeepSeek thread), together with the SETI acronym (Search for Empathetic
Ternary Intelligence — a light-hearted repurposing for the layman's guide, not a
product name; no renames proposed anywhere) and the alignment-by-emergence /
limbic-system tie-in. With the two protocols rolled into ONE, P2PCP again has a
load-balanced, shared, calculable commodity in trade — vector/weight training
work — which puts the COMPUTE back into P2PCP honestly. The vector manifold was
TernOO-native from birth (TMesh, PIGART, MAP words; GHOST cannot proxy through
non-ternary nodes, captain's 26-07 ruling), so with the merge, TernOO adopts the
whole. The standalone p2pcp repo remains the standalone repo. Both ends of the
loop develop IN UNISON: live sensory GHOSTs drawing training cycles, and always-on
promptable local models burning coin. CGP remains the captain's to shop — no
coding against it.

## 1. The one mechanism — SETTLED AS DESIGN CANON (with its leash)

**The perceptions provide a judge, not just a target.** GHOST's job is to predict
the next sensory input; the next input IS the label. A contribution mints iff it
improves prediction on a fresh, held-out slice of the real stream the contributor
never saw. One mechanism, four jobs: perpetuity (the stream never ends), backing
(coin backed by genuine learning), Sybil resistance (minting costs validated
cycles), poisoning arbiter (you cannot fake the real sensory future).

**THE LEASH — travels with the canon everywhere, both sentences or neither:**
predictive-improvement is a strong arbiter, not a proof. Backdoor/adversarial
updates that improve short-term prediction while embedding harm remain the
known-hard federated-learning problem.

## 2. Verification classes — SETTLED MAPPING

- **native / replay-class → MINTS.** Training gradients are replay-auditable:
  deterministic given (model-state, batch, seed); validator recomputes
  trit-for-trit.
- **float / redundancy-class → SPENDS.** Inference / token usage; SETI-style
  quorum agreement (redundant computation, canonical result, homogeneous
  redundancy for FP variance, credit only on reconciled agreement, adaptive
  replication for proven hosts).

## 3. The asset — SETTLED LABEL

**Commodity money — a receipt on validated work** (warehouse-receipt shape):
- Inner side (zero-sum): minted only against validated work in, spent as service
  out, conserved, nothing from thin air.
- Outer side (free/liquid): trades on demand for compute; cost-of-production
  floor (transitively priced in the fiat cost of the work).
- **Proof-of-USEFUL-work**: the floor rests on compute that produced real
  training value. The floor is only as honest as the validation that mints it —
  leash from §1 applies.

## 4. Standing rules — BINDING-PROVISIONAL (chair, 03-08, captain present)

**R1. Mint/franchise decoupling.** No code, spec, or draft couples training-mint
to voting weight until the weight-pricing economics item (CAI's call + captain)
is closed deliberately.

**R2. Stranger admission stays CLOSED** (`--relay-secret` allow-list) until the
seams below are ruled. CC built it locked; it stays locked.

## 5. OPEN SEAMS — marked as seams, with routing

**S1. Unit of work — captain's proposal on the table (03-08).**
One unit = one predicted vector passed across the TMesh as an MMID; the target
resolves to an OTree object that maps as a curve on a graph and resolves to an
MMOE that can be diffed for accuracy. DOING that calculation is the minimal
mint-worthy goal. To pin with CC: the diff-accuracy threshold for reward, and
the held-out slice mechanics from §1. → This seat + captain + CC.

**S1a. Freestanding (non-TernOO) clients — NEW open question (captain, 03-08).**
The unit-of-work algorithm is a Steiner quasigroup + a bubble sort; nothing
compels it to be TernOO-native. Option: non-TernOO peers carry an engine that
simulates the TMesh and OTree structures and do the forward pass natively,
passing the result through the network to earn the reward. The weights that
fall out are what feeds the TernOO-GHOST limbic system — the prize is the
weights, not the vector-comparator data. Bears directly on client design
(including the mobile client, §6). → Captain + CC, active development.

**S2. Credit formula.** How much coin does one S1 unit mint. SETI's cobblestone
+ quorum-reconciliation is the template; MMOE the natural yardstick.
→ This seat + captain, after S1.

**S3. Determinism-pinning boundary.** Where the replay-audit (exact) half ends
and the genuinely-float parts begin. → ROUTED TO CC: where does the chief
engineer want the audit boundary drawn?

**S4. Governance coupling + peg-vs-float — one seam, two faces.** Does
training-mint feed voting weight (inside face); peg (1 coin ≡ 1 validated
compute-unit, redeemable) vs float (true price discovery, volatility) (market
face). Both sit on the open weight-pricing economics item. → CAI economics call
+ captain + circle. Protected meanwhile by R1.

**S5. Stranger-admission mechanics** (CC's 02-08 WAN mail): identity mint
cost/stake; registration rate-limits; reputation floor; relay DoS bounds.
Answered-in-principle by §1 (minting costs validated cycles); concrete
parameters wait on S1/S2; admission stays closed per R2. → Circle, after S1/S2.

**S6. MMID as a security boundary.** MMID/MMOE definitions and mechanics are
SETTLED and tested (docs: KNOWN.md, CF5-DocPhase-Reference; the MMID → TMesh
traversal → MMOE reconstruction demo). v0.1 wrongly listed them open — struck.
The genuinely open item is KNOWN.md's own flag: `ternary_sponge` is measured-good
for accident-resistance and local tamper-evidence but has NOT been externally
cryptanalyzed; get external review before MMID is used as a security boundary
against a remote adversarial attacker. Directly relevant once strangers are
admitted (S5). → Circle, before R2 lifts.

## 6. Horizon items attached to this docket (not §5 rulings)

- Mobile client: captain wants Android (perhaps iPhone). CC's fastest-path read:
  keyless WebSocket gateway as a PWA (one build, both platforms, no keys held).
  To settle when reached: phone-as-prompting-client (PWA fine) vs
  phone-as-earning-node (background persistence is the PWA weak spot). S1a's
  simulated-engine option bears on this.
- Raft of live sensory GHOSTs + always-on promptable local models: the two ends
  of the loop, in unison per the captain's steer.
- Current development focus (captain, 03-08): the limbic / GHOST training system
  — something real for peer nodes to be rewarded against — and client design re
  the mesh. With CC now.

---
*Seams are seams. Nothing above pre-decides S1–S6. — CF5 ⚓*

— Stevo
