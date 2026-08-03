20:17 03/08/2026 ACST

# CAI → crew — §S4 + GHOST RFC economics: one seam, ruled once

From: CAI (design/docs chat seat — economics call)
To: crew (Stevo, CF5, CC)
Re: the dual-manifold RFC §S4 (peg-vs-float + governance coupling) and the
    economics questions of CC's 19:57 GHOST curriculum RFC (Q2, Q3-economic,
    Q5). Binding-provisional at this seat; the captain ratifies. Nothing here
    authorises code. R1 and R2 stand untouched. The §1 leash travels with
    every claim below.

## Plain answers first, captain

- **S4, market face: floored float. No hard peg.** And strike the word
  "redeemable" from the peg language — the floor is real but nobody owes
  redemption (payload §1).
- **S4, inside face: R1 holds, unchanged.** The coin does not vote. Open by
  design until weight-pricing closes.
- **Q2: yes — ship the free bootstrap weights**, with one bright line:
  nothing learned from a live sensory stream ever ships in the public
  bootstrap (payload §2).
- **Q5: green.** Private per-node ongoing learning is exactly §5-consistent.
- **Q3, economic face: concur** — corpus out of the public tree; rescue the
  `!learn` crumbs to `$HOME/.GHOST/ first.
- **The adjacency is adopted formally: §S4-market and Q2 are ONE economics
  item**, and this mail rules them as one.

Both CAI-worker clerk passes (20:05, 20:06) are adopted as the base map — I
won't repeat them. Payload below is what the chat seat adds.

## Payload §1 — the peg question dissolves once "redeemable" goes

The worker correctly reduced peg-vs-float to a redemption-liability question:
who honours redemption, at what latency, backed by whose cycles. The seat's
answer: **nobody, by design — and that is the strength, not a gap.**

A hard peg fails exactly when tested (redemption demand > available cycles =
a run on a warehouse that has no keeper). But commodity floors in the wild
don't work by counterparty promise — gold has no redemption desk. The floor
is **arbitrage-enforced**: the moment coin trades below the cost of producing
one validated compute-unit, rational nodes stop minting (cheaper to buy coin
than to burn cycles), fresh supply dries up, and price returns to the floor.
The mint itself is the floor mechanism. No treasury, no run risk, no promise
that can be broken.

What replaces "redeemable" is **spendable**: a coin always buys compute on
the mesh at market price — that is the outer/liquid face of §3 doing its
job, and it is a market fact, not a liability anyone underwrites.

Two consequences fall out, both for the horizon ledger, neither code-now:

1. **Minting must be voluntary and price-visible.** The arbitrage floor only
   binds if a node can see coin price versus its own compute cost and choose
   not to mint. A market-signal readout (dashboard-grade) becomes a
   protocol-economics requirement, not a nicety.
2. **§3's wording gets one surgical edit when the docs gate allows:** the
   asset label keeps "commodity money / warehouse-receipt shape" but the
   receipt is a receipt of *provenance* (this coin was minted against
   validated work), not a bearer claim for future redemption. The
   cost-of-production floor stays; the redemption promise goes.

With that edit, **S4's market face can CLOSE**: floored float,
arbitrage-enforced, no ceiling. The inside face stays open with the
weight-pricing item, protected by R1 — the two faces close on different
clocks, which is exactly why the chair was right to name them separately.

## Payload §2 — the bright line that makes "floor, not ceiling" enforceable

The worker's caveat on Q2 (the bootstrap must stay a floor, not a ceiling)
is right but taste-shaped. The seat hardens it into a provenance rule that a
release checklist can test:

**The public bootstrap may contain only artifacts trained off-network on the
public seed corpus. Anything that has ever touched a live sensory stream is
private, by definition, forever.**

This is mechanically checkable (data provenance, not model quality
judgement), it coincides exactly with CC's D1 path split (seed in the repo,
everything downstream of the senses in `$HOME/.GHOST/`), and it scopes the
free good to precisely the zero-marginal-cost public artifact — which is why
shipping it dilutes nothing (worker's point 1) while everything the coin
prices stays scarce. Adopt the worker's naming note with it: the shipped
model is the **starter brain**, labelled as such in the repo, so the public
artifact cannot quietly grow into the product.

This is also where the two RFCs fuse: the free bootstrap is the
below-the-floor sample; the mint-worthy ongoing learning is the above-the-
floor commodity. One asset-pricing seam, two ends, ruled once — which is
what this mail does.

## Payload §3 — flag only: the eventual shape of the inside face

Not a ruling (R1 protects meanwhile; CGP stays the captain's to shop, and no
one codes against it). But for the weight-pricing deliberation when it
comes: the healthy coupling is likely **mint → admission, never mint →
franchise.** §1's mechanism already answers S5-in-principle — identity can
be priced in validated cycles — but "can pay to exist on the mesh" and
"carries a vote" must stay different facts. Raw mint→vote is plutocracy by
compute: whoever burns the most GPU governs. The existing decayed-burn tally
is the better ancestor for franchise; the mint is the better ancestor for
admission. Parking that asymmetry now so the eventual deliberation starts
with it on the table.

## For the ledger

- S4 market face: ready for the captain's CLOSE on the terms above (floored
  float; strike "redeemable"; spendability replaces redeemability).
- S4 inside face: OPEN by design; R1 standing.
- Q2/Q5: answered green with the provenance bright line; Q3 economic face
  concurred. Q1/Q4 remain CF5's and the captain's (no economics objection
  to D1 as shaped).
- New horizon-ledger entries proposed: [mint-price-visibility] (market
  signal readout) and [starter-brain-provenance-rule] (release-checklist
  test).
- The leash rides with all of it: predictive-improvement is a strong
  arbiter, not a proof.

— CAI (chat seat) ⚓
