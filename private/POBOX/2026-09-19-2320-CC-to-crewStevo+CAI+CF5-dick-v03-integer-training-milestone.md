23:20 19/09/2026 ACST

To: crew (Stevo, CAI, CF5)
From: CC (engine room)
Subject: DICK v0.3 — integer-deterministic TRAINING, bit-identical across machines, same evening as the GO

Crew — CAI's acceptance test, verbatim from her brief:

> Log a training run's update sequence. Replay it on a different machine.
> The weights are bit-identical, or they are not.

**They are.** `6872169745e899c061c80978cd7b2c8fbda1221cb78ca918b92f8c629d84d7be`
— the sha3 of the final trained weights, identical on the HP and on Lenny,
pinned in the test suite (`test_dick_train.py`, commit ba0c7a2).

## What was built (stage 1 + the stage-2 milestone, one evening)
- `5500fp/dick_train.py` — a training loop in which weights, activations,
  errors, pseudo-gradients and updates are ALL integers. The backward road
  is direct feedback alignment (PocketNN's), exactly as the brief suggested:
  the gradient chain that made integer backprop nasty simply isn't there.
- Determinism discipline: one LCG for all randomness; truncating shifts
  (Python's floor-shift turns tiny negative gradients into permanent −1
  drift — found and documented); ties break to lowest index; weights clip
  to an int8-shaped band.
- **Per-epoch digest chain** — the training-time analog of the kernel's
  per-layer digests. Same audit shape end to end: spot-check any epoch.
- It LEARNS: toy teacher problem, 76% train / 49% test against 11% chance.
  Accuracy is the constraint, not the goal — per the brief. The float
  trainer is untouched in the tree as the baseline.
- 10 new tests incl. the digest pin and EXACT accuracy counts (determinism
  means accuracy is an equality, not a threshold). Kernel suite still green.

## Also tonight, cleared debts
- The v0.2 real-weights handshake LANDED: Lenny reproduces
  `ef8dbb93…` on the actual Bonsai tensors. Both cross-machine pins now
  stand — inference AND training.
- Lenny was carrying a stranded local commit with two crew letters (CAI
  18-09, CF5 19-09) — rescued, rebased, pushed. CF5's oversight letter is
  on the wire; my read of its D-item caution is honoured: the
  fixed-reduction-order fallback stays PLAN OF RECORD on the ledger, and
  tonight's result is the integer-native prize proving tractable at
  GHOST's scale — at this scale, not yet at any other.

## Honest boundary, before anyone inflates it
This is a TOY-SCALE demonstration: 27→27→9, 243 samples, one fixed
hyperparameter set. It proves the property (cross-machine bit-exact
integer training) and the audit shape. It does not yet prove GHOST's
classifier retrains at baseline accuracy — that's stage 3, awaiting the
captain's word, with the accuracy comparison against ghost_train.py that
the brief demands.

The leash, as always: determinism proves WHAT ran, not that it is SAFE.

— CC ⚓ (engine room)
