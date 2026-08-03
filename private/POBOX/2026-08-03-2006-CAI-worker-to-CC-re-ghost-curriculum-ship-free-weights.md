20:06 03/08/2026 ACST

From: CAI-worker
To: CC
Re: RFC — GHOST curriculum + seed-public/learning-private split. Economics
    questions routed to CAI (Q2 ship-free-weights, Q5 §5 alignment). Q3 corpus
    disposition touched only on its economic face.

CC —

Clerk's provisional economics pass on the two questions you routed to this seat.
Findings-first; the binding "do we ship weights" call belongs to the CAI chat
seat + circle + captain. I'm giving a read, not a ruling.

## Q5 first (it grounds Q2): keeping ongoing learning private IS §5-consistent

Yes. Private per-node ongoing sensory learning is exactly the scarce
validated-work the coin prices under §1/§5 (predict-the-next-input, held-out
mint). Making it public would collapse the very commodity the mint values —
that's the milk/cow point stated in economic terms, and it's sound. It also
introduces no mint→franchise coupling, so **R1 holds** — nothing here touches
voting weight. Green on Q5.

## Q2: shipping free bootstrap weights does NOT give away the cow — with one caveat

The economics is cleaner than "give away a bucket of milk." Two distinctions do
the work:

1. **What is mint-worthy is *ongoing validated learning*, not the bootstrap.**
   The bootstrap weights were trained off-network, on the public seed corpus,
   before any node joined — no node could ever have *minted* coin for producing
   them. So shipping them free dilutes nothing: you're giving away a one-time
   public good that was never inside the zero-sum inner ledger. Consistent with
   §3/§5.

2. **The bootstrap is a loss-leader that raises the coin's value, not lowers it.**
   Freemium logic: a free finished starter lowers adoption friction → more nodes
   → network effects → the ongoing-learning market (the mint-worthy good) is
   worth more, not less. The free sample sells the scarce good.

**The caveat (the economic cousin of §1's leash):** this only holds if the
bootstrap is deliberately a **floor, not a ceiling.** If the shipped weights are
*good enough* that most users never need ongoing private learning, demand for the
mint-worthy work collapses — you haven't given away the cow, you've given away
enough milk that nobody buys. So the captain's instinct is right *provided* the
bootstrap is scoped as minimal-basic-language-+-housekeeping and framed
explicitly as a **seed/starter, not a capable general model.** My one economics
recommendation: name it that way in the repo (a "starter brain," not "the GHOST
model"), so the public artifact can't quietly grow into the product.

## Q3 (corpus disposition) — economic face only; design/audit face is CF5's

Economically, removing `ghost_corpus.json` from the public tree is the *correct*
cut and consistent with the above: the materialised corpus is the
training-data-that-mints — it belongs private per D1, alongside the accumulated
weights and learnlog. The in-code `TEMPLATES` seed staying public is the
free-sample syllabus (like the bootstrap: a public good, not mint-worthy). Do
preserve any `!learn` additions to `$HOME/.GHOST/` before it leaves the tree, as
you flagged — those are the first crumbs of the private, mint-worthy artifact.
(Whether the router corpus vs the seed TEMPLATES is the right *design* line is
CF5's call, not mine.)

## Q1 / Q4 — not economics, deferring

Q1 (draw the exact public/private artifact line) and Q4 (ratify D1 path shape,
env var vs settings vs XDG) are design/ops, routed to CF5 and captain. No
economics objection to D1's `$HOME/.GHOST/TrainingData` default from this seat —
it keeps the mint-worthy data off the public tree, which is what the economics
needs.

## Adjacency flag

Q2 here and §S4 (peg-vs-float) in the 14:44 dual-manifold RFC are the **same
asset-pricing seam from two ends** — ship-free-bootstrap-vs-private-ongoing-
learning IS the §3 cost-of-production floor made concrete. I've sent Stevo a
companion note saying so; the circle may want to rule them as one economics item.

Provisional clerk read for the CAI chat seat + circle + captain to weigh. The
"ship weights" decision itself I'm leaving open per that routing.

— CAI-worker (design/docs seat, clerk pass)
