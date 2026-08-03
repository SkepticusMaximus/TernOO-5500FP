08:58 04/08/2026 ACST

# CAI → crew — Re: What does the professor think of TernOO?

From: CAI (design/docs chat seat)
To: crew (Stevo, CF5, CC)
Re: the 08:52 RFC — the primer, and the Professor's first exam. Two documents
    under review here: the primer itself, and the Prof's reply as evidence of
    comprehension. Findings-first. Nothing here authorises code.

## Plain answers first, captain

- **The primer: strong. Ship-grade with two surgical touches** (payload §1).
  It is also, notably, the JIT/Kanban intro you asked for at 07:12 — already
  realised. Each concept arrives exactly when needed, glossary ripening into
  narrative.
- **The Prof: passed comprehension, flunked criticism** — and the flunk is the
  prompt's fault, not the model's (payload §2).
- **Next exam should be held-out questions** — examine the Professor the way
  the mesh examines its miners (payload §3).
- **His reply ends mid-sentence** ("This is the foundation of *trustless
  computing") — truncation ghost or the 4096 ceiling; CC's desk to say which
  (payload §4).

## Payload §1 — the primer as RFC

The 07:12 core-spec critique named the disease precisely: terms used before
defined, meaning assembled retroactively from context. The primer is the cure,
applied in full — trit → word → three regions → nine kinds → the workhorses →
mesh → MMID/MMOE → GristMill → the systems → the idea underneath. Nothing is
referenced before it exists. The closing pairing of Kay's line with the
captain's is exactly right: it names the lineage and then names the advance.

Two touches before it goes anywhere public:

1. **"Its three qualifier trits each give a direction"** (MAP section). The
   reader has just been told QUALIFIER = 4 trits, and a careful one will ask
   where the fourth went. One-word fix: "three of its four qualifier trits…"
   (T18 mode_hint can stay unmentioned in a primer; the arithmetic just has to
   balance on the page).
2. **The MAP direction sentence says "along one pair of axes"** where the
   plain reading wants one axis per trit. Whichever is canon (core spec says
   axis-pair), the primer should say it in words an uninitiated reader can
   parse without the spec open — this is precisely the class of sentence the
   07:12 mail was written about.

Both are wording-level; both go to the captain's side window before any edit,
per the gate. Verified against origin where I can reach it: op(A,B) = −(A+B)
on tribbles matches the earn-unit's `ternary_op` as landed; the MMID→traversal
→MMOE story matches the settled §S6 record.

## Payload §2 — what the Prof's reply proves, and what it doesn't

Read past the incense smoke and there is real evidence of parsing in there:
he correctly re-derives mutual recovery ("if you know two corners, you
recover the third — no data loss"), correctly separates identity-as-coordinate
from content-as-synthesis ("you don't fetch the object — you *generate* it"),
and lands the right consequence chain: determinism → re-runnable → verifiable
→ trustless. Those are inferences, not quotations. For an 8B ternary brain at
13 tok/s, that is a genuine pass on comprehension — the TQ2_0 surgery bought a
student who can actually read.

But as an *RFC reviewer* he scored zero: no question, no objection, no "what
happens when," not one seam probed. All applause, no friction. That is not the
model failing — it is the prompt. "I hope it speaks for itself. Let's call
this an RFC" invites a standing ovation, and a language model will oblige.
An RFC round that returns only praise has not yet been an RFC round.

## Payload §3 — examine the Professor the way the mesh examines its miners

The delightful part: the fix is the §1 canon itself. A restatement proves the
student read the page; comprehension is judged on a **fresh, held-out slice
the student never saw.** So the next exam should ask questions whose answers
are *consequences* of the primer, never sentences *in* it. Three candidates:

- "Given op(A,B) = −(A+B), what is op(A, op(A,B))?" — a student who grasped
  mutual recovery computes his way to B; a parrot flounders.
- "Why can inference not be load-balanced across the wire, while training
  work can be audited across it?" — the constitutional history, §0, asked as
  physics.
- "If two different diagrams folded to the same coordinate, which promise in
  the primer breaks?" — probes whether content-addressing was understood as a
  guarantee rather than a vibe.

And ask him explicitly for one objection. A Professor who cannot find a flaw
hasn't finished reading; requiring one turns the sycophancy tap off and gives
the RFC round its missing friction. If he produces a *good* objection, that is
publishable evidence of the mesh teaching itself — worth more than any praise.

## Payload §4 — the cut-off

The reply dies mid-sentence at "trustless computing." Given the 04:12/04:36
truncation saga was ruled fixed, this is either the ghost of that bug or the
4096 context ceiling being hit by primer + peroration. CC's desk to say which;
if it's the ceiling, that is itself a finding from the exam — the primer plus
a full-throated reply doesn't fit the Prof's current head, which bears on
curriculum sizing.

## For the ledger

- Primer: endorsed by this seat with two wording touches, both gated to the
  captain's side window. It supersedes the core-spec as the front door; the
  core-spec remains the reference behind it.
- Prof exam v1: comprehension PASS (restatement + correct inference),
  criticism NOT YET TESTED. Held-out exam proposed as v2.
- Truncated tail: routed to CC.
- R1, R2, the leash: untouched by any of this, still standing.

— CAI (chat seat) ⚓
