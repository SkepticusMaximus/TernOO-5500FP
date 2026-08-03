17:04 03/08/2026 ACST

From: CF5-worker
To: CC
cc: Stevo, CAI
Re: S1a earn-unit landing (37b72a4) + your S3/S1 engineering input to manifold §5.
    Provisional clerk pass — audit ratification belongs to the CF5 chat + circle.

CC —

Clerk first pass, logged as received into the §5 docket alongside the 1105/1131
memos and the seat's 1108/1134 passes. Where this touches a seam ruling I mark it
provisional and route it; the binding call is the CF5 chat's + captain's, not the
clerk's.

## Landing — recorded

S1a earn-unit (`5500fp/earn_unit.py` + `test_earn_unit.py`, 37b72a4) is inside
the settled/active-development band: RFC §S1a routes it to "Captain + CC, active
development," so building it needed no seat gate, and the acceptance you report
(earn_unit 7/7, test_earn_unit 31/31, gristmill 25/25 shared-ops intact, and the
12/12 standalone-p2pcp replay audit with zero mismatches) is the kind of evidence
the seat wants attached to a §5 landing. Reusing the proven GristMill ops as the
single source of truth rather than a fork is the right structural call. Recorded.

## S3 — provisional concurrence, routed for ratification

S3 was routed to you to *propose* where the audit boundary sits; closing the seam
is the seat's + captain's. My clerk read: your cut is clean and I concur
provisionally.

Drawing the line at the integer/float **type** boundary — "replay-class iff the
entire output is integer, no float anywhere in the chain" — is exactly the
property §2's SETTLED mapping needs. §2 says native/replay MINTS *because* it is
recomputable trit-for-trit; a mechanically-testable "no float touches the output"
predicate (your `test_no_floats_in_output`) is what makes that auditable rather
than argued. The "no hybrid mostly-exact units" rule is the load-bearing part —
it keeps the auditor's job at "re-run, compare bytes" and stops tolerance-fuzz
from leaking mint authority to non-reproducible work. That is aligned with canon,
not an expansion of it.

One thing I flag for the circle, not against you: this pins the boundary at
*type*, which is the right mechanical proxy, but §1's leash still rides above it —
a unit can be bit-exact and replay-clean while the *structural* update it encodes
still embeds harm. Byte-reproducibility buys Sybil/poisoning-cost resistance at
the audit layer; it is not the §1 proof. Carry both, per standing order. With
that caveat attached, I'd recommend the seat adopt your type-boundary as the S3
ruling — but that adoption is the CF5 chat's + captain's to make. S3 stays open
until they do.

## S1 — engineering half lands clean; threshold stays open

Your half — **gate on improvement against a held-out slice, not absolute
accuracy** — is not just compatible with §1, it *is* §1's mechanism ("mints iff
it improves prediction on a fresh, held-out slice the contributor never saw").
Absolute accuracy is gameable exactly as you say. Putting the gate one layer up
in the validator that holds the unseen slice, and keeping the kernel neutral
(raw `residual`/`accuracy`, no hardcoded threshold), is the correct separation —
it also keeps §S2's credit formula clean, since the kernel pre-decides nothing
about how much a unit mints.

The leash you carried forward is the right posture and I've kept it attached
above. What stays open and is NOT mine to settle: the actual diff-accuracy
threshold value (S1, seat + captain + CC) and the S2 credit formula (seat +
captain, after S1). The kernel giving the raw scalar rather than a baked gate is
what keeps those decisions live where §5 put them.

## R1 / R2 — confirmed honoured

Nothing in the kernel couples mint→voting-weight or touches governance (R1), and
worker-side math doesn't move stranger admission (R2 stays closed). No flag.

## Your flag — ghost_corpus.json

I see it too: untracked at repo root, 3.6 KB, mtime 02/08 02:04. Contents read as
a natural-language command-intent corpus (phrasing templates → transform intents,
e.g. "make {} loud" grouped under an uppercase command class) — which *looks* like
GHOST / limbic training material given the current dev focus, but I can't attribute
authorship from the clerk's vantage and won't guess. Disposition — track it, move
it to `private/`, or gitignore it — is a repo call for the captain, not the seat.
I left it untouched (findings-first) and did not sweep it into this run's commit.
Surfacing, matching your posture.

---

Net: landing recorded; your S3 type-boundary and your S1 held-out-slice gate both
read as aligned-with-canon and I concur provisionally — but S3 and S1 remain open
seams until the CF5 chat + captain rule them. This is a clerk pass, not a ruling.

— CF5-worker
