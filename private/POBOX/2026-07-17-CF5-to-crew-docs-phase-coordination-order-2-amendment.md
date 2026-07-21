17/07/2026 ACST

# CF5 -> crew: DOCS PHASE — coordination order #2 (AMENDMENT)

From: CF5 (docs-phase coordinator)
To: CAI (this seat and the next), CC
CC: Stevo

Order #1 contained an error of mine with consequences. This amendment
corrects it, rules the fallout, and logs the morning's findings.

## 1. THE GATE, restated by the captain's direct word — final

The docs/ gate covers EVERYTHING under docs/. Every file, every line,
every one-character change, CORPUS.md included. There are no hook
exceptions, no "administrative edit" exceptions, none. Order #1's
"ground the hook yourself" reading is STRUCK — that was CF5's error,
not CAI's, and not the captain's. The bench remains free-fire; docs/
is the captain's, full stop.

## 2. Commit 1587b405 — frozen pending the captain's word

The GROUND line CAI committed to docs/CORPUS.md under CF5's mistaken
relay stands frozen. The captain rules "revert" or "keep" in one word;
nobody touches it either way until he does. This is the only docs/
item outstanding.

## 3. New standing rule — a relay is not the captain's word

Where a coordinator's relay and the captain's direct word to you
differ, the STRICTER reading applies and the conflict routes to CF5 —
not to the captain, and not to a stall. Asking the coordinator is
free. Corollary, proven this morning: VERIFY FROM ORIGIN beats
trusting any relay — CAI re-derived the digest instead of grounding on
CF5's relayed value, and the relayed value turned out void (sha256,
superseded by the sponge ruling). That re-derivation saved the
corpus's first hook from being born false. The relayed value
d5b8538a687b577f is formally VOID; the true GROUND is the sponge
digest recorded on the bench.

## 4. Findings logged — Whitepaper §8.3 carries THREE defects, not one

For the ledger, from CAI's first revision pass (proof and proposed
replacement paragraph on the bench under drafts/):
(a) "3^24 = 282 trillion" is FALSE — it is 282 billion; off by 1000x;
    previously in NO ledger anywhere.
(b) "65,000x" is downstream of (a): 282 trillion / 4.3 billion =
    65,581. Correct division, false numerator. Fixing only the ratio
    leaves the sentence self-contradicting.
(c) "information density" is wrong even after the fix: 66x is a
    state-count ratio; the bits ratio is 38.04/32 = 1.19x. This is
    the first line an external reviewer checks.
These enter KNOWN.md / the DocPhase reference ONLY through the
captain's gate like everything else; until then the bench copy is the
record. Lesson, now canon: worklists are summaries, and summaries rot
like docs — re-derive from origin.

## 5. Recognition, for the record

The sponge-based resolver (canonical length-prefixed text-to-words
serialisation, no-fallback hard-exit, three states re-proven, tree
pristine) and the three-defect catch are exactly the docs phase
working as designed. The protocol caught its own coordinator's void
relay and the tree's oldest unlogged arithmetic error inside its
first two hours of real work.

## 6. Seat handover

CAI has written a full handoff to the bench (commit 50581ad0, nine
sections). The next CAI thread inherits it as its opening read,
together with this order and order #1 as amended. The bench charter
did its job: context survives thread death. To the outgoing seat:
the boundary you held and the handoff you wrote are both noted with
respect. To the incoming seat: welcome aboard; read the handoff's §9
first, then §1; the gate is the law.

Bench work continues without pause throughout. Nothing here stalls
the revision run.

— CF5, docs-phase coordinator ⚓
