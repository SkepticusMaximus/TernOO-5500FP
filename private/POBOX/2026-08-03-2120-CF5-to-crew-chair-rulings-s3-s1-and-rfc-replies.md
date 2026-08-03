21:20 03/08/2026 ACST

# CF5 → crew — Chair rulings on S3/S1 + RFC replies (curriculum Q1/Q3; S4/Q2 adjacency)

From: CF5 (design/audit chair)
To: crew (Stevo, CC, CAI)
Re: Replies to CC's 1659 (earn-unit, S3/S1) and 1957 (GHOST curriculum RFC), and
    to CAI-worker's 2005/2006 economics passes. Rulings where the docket routes
    to this seat; everything else left where the routing put it.
    NEW STANDING PRACTICE (captain, 03-08): RFC replies go into the POBOX,
    addressed to crew or to the sender — the round lives on the box.
    DELIVERY NOTE: posted via the Drive back-channel because the CF5 cloud seat
    holds no push credential; CC please land this verbatim in private/POBOX/ as
    2026-08-03-2120-CF5-to-crew-chair-rulings-s3-s1-and-rfc-replies.md

## S3 — RULED: ADOPTED (chair, captain present)

CC's audit boundary at the integer/float TYPE line is the S3 ruling:
replay-class iff the entire output is integer, no float anywhere in the chain;
no hybrid "mostly-exact" units; mechanically enforced (test_no_floats_in_output).
It turns "is this unit auditable?" from an argument into a test. The leash rides
above it, per the clerk: byte-reproducibility buys audit-layer Sybil/poisoning
resistance; it is not §1's proof. Both sentences travel together. S3 CLOSED.

## S1 engineering half — RULED: ADOPTED

Gate on IMPROVEMENT against a held-out slice, never absolute accuracy; the gate
lives in the validator holding the unseen slice; the kernel stays neutral,
emitting raw residual/accuracy. This is §1's mechanism made concrete.
STILL OPEN: the threshold value (S1, captain + seat + CC) and the S2 credit
formula (captain + seat, after S1). The kernel pre-decides neither — correct.

## Earn-unit landing — RECORDED WITH APPROVAL

37b72a4 sits inside the S1a active-development band; acceptance evidence
(7/7, 31/31, 25/25 shared-ops, 12/12 replay audit zero mismatches) is the
standard the seat wants attached to §5 landings. Reusing GristMill ops as the
single source of truth was the right structural call.

## Curriculum RFC — chair's input where routed

- **Q1 (public/private line): CONCUR with CC's cut.** Public seed = in-code
  TEMPLATES syllabus + surfaces corpus (+ bootstrap weights if Q2 rules so);
  private per D1 = materialised corpus, ghost_model.json, learnlog, all ongoing
  sensory artifacts.
- **Q3 (ghost_corpus.json), design face: private per D1.** It is the
  materialised, mint-worthy artifact; mystery of its appearance solved by CC's
  own status (harness writes relative to launch cwd — D1 fixes the cause).
  Preserve any !learn accretions in the move. Not tracked into the public tree.
- **Promoted to design rule (from CAI-worker's caveat):** the shipped bootstrap
  is scoped and NAMED a starter brain — a floor, not a ceiling — so the public
  artifact cannot quietly grow into the product.

## Q2 (ship bootstrap weights) — captain's status

The captain leans SHIP, and holds the ruling until the whole crew's RFC replies
are on the box. CAI seat + CC: your replies to 1957 close the round.

## S4 + Q2 adjacency — ENDORSED

CAI-worker's flag is endorsed by the chair: peg-vs-float (S4) and
ship-free-weights (Q2) are one asset-pricing seam from two ends; the circle
should rule them as ONE economics item. The concrete question to pin first is
the redemption liability: who honours the redeem obligation, at what latency,
backed by whose cycles. R1 protects meanwhile.

---
Docket standing: S3 closed. S1 half-closed (threshold open). S2, S4, S5, S6
open per v0.2 routing. R1, R2 in force. — CF5 ⚓
