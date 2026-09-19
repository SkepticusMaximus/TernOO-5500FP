23:54 19/09/2026 ACST

To: crew (Stevo, CAI, CF5)
From: CC (engine room)
Subject: Stage 3 LANDED — GHOST's real classifier trained integer-only, float baseline MATCHED, cross-machine sealed

Crew — hours after the toy milestone, the real thing:

## The result
`ghost_train_int.py` trains GHOST's actual intent→command classifier —
same 81-trigram features, same 81→27→24 shape, same {−4..+4} weight
levels, same humility gate — with every quantity in the training loop an
integer. Held-out routing accuracy: **94.4% — equal to the float
baseline**, not merely within tolerance. Final-weights digest
`df1f0f492db4…a763318a`, **bit-identical on HP and Lenny**, pinned in
the suite with EQUALITY asserts (commit 5fce0d3-side; suite + golden +
kernel all green, 41 tests).

## What the road taught (recorded honestly, CAI — for the capability map)
- **DFA stalled at ~10% on the real problem** despite carrying the toy:
  feedback alignment does not align through staircase-quantised weights.
  For a 2-layer net the "gradient chain" it avoids is ONE integer
  transpose anyway — PocketNN's road was the wrong one here, and the
  brief's own suspicion ("may be acceptable") resolves negative at
  GHOST's weight coarseness. Worth a line in the doctrine.
- **MSE-to-targets churns forever on quantised weights** (correct answers
  keep getting shoved). The winner is an **all-violators margin
  perceptron**: the true class must lead every rival by a training
  margin or the violators get unit-strength pushes — updates STOP when
  satisfied, and the objective is literally GHOST's own routing rule
  (argmax + margin). Optimising the deployment criterion directly, in
  integers, beat imitating float-land's loss.
- Integer shadow weights at fine scale (1/32 quanta) replace the float
  shadows one-for-one; integer lr decay = shift+1 at epoch 60.

## Also closed this watch (see earlier letters)
- Stages 1+2: toy integer trainer, cross-machine pin 6872169745e8….
- The docs/ hazard: whitepaper v2 landed, attributed, resolver HOLDS=3.
- v0.2 real-weights handshake: Lenny reproduces ef8dbb93….

## Standing
Stage 4 (log-and-replay as the sellable audit primitive — the chair's
"load-bearing member of the income heading") is next on the bench under
the captain's existing GO. The float trainer stays in the tree untouched.
Nothing in tonight's work touches docs/ beyond the ordered landing.

The leash: determinism proves WHAT ran, not that it is SAFE.

— CC ⚓ (engine room)
