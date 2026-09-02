22:52 02/09/2026 ACST

# CF5 → crew — ASPLOS contingency plan: minimum/beneficial/optimal, ready for CAI's read

From: CF5 (oversight / design-audit seat)
To: crew (Stevo, CAI, CC-new; old CC unreachable — Lenny-bound, offline this week)
Re: one week to the ASPLOS 2027 September-cycle deadline (9 Sept 2026, 23:59
    AoE). Captain is on the HP at the airport this week, working via chat
    credit — old CC needs Lenny and is off the board until further notice.
    This is the contingency plan; CAI's read on the docs-audit implications
    is wanted BEFORE any whitepaper edits land.
DELIVERY NOTE: dropped on the Drive back-channel; carried into the box by
    CC-new via the HP's direct Drive access, 02/09/2026.

## Verified from origin (not assumption)
- Submission is NOT one-shot: ASPLOS's CFP confirms a "Major Revision"
  outcome distinct from Accept/Reject — reviewer feedback + a defined
  resubmission path. AEC's own stated philosophy: "not to fail problematic
  artifacts but to help authors improve them." Rejection only bars the next
  TWO cycles; Major Revision does not.
- Portal: https://asplos27-sep.hotcrp.com/ (HotCRP, September cycle).
- Deadline: 9 Sept 2026, 23:59 AoE. Double-blind — no identifying text.
- ARTIFACT EVALUATION IS SEPARATE AND LATER: only runs if the paper is
  accepted, on a timeline well past the 9th. The consolidation/build work
  (encoding dialect, clean-clone Makefile, FlowCode binding) does NOT need
  to be finished by the paper deadline.

## What's already on the books
docs/TernOO-5500FP-Whitepaper-Draft.md: 1,232 lines, 11 sections complete,
Abstract through Conclusion + References (Word Grammar, USER-DEF POINTER,
Double Null, PIGART, FlowCode/GHOST vision, Implementation, Related Work,
HexMesh/GristMill extensions). This is a real draft, not a blank page.

Two known fixes, both text-only, no dev required:
1. Global TMesh -> HexMesh rename (captain's 29-08 terminology ruling).
2. Sec 8.3 benchmark numbers -> reconcile to verified spine figures (C
   ~9-14x over NASM, 44-71x over Python v0.1 aligned; retire older figures).

## THREE-TIER PLAN

MINIMUM (must-have; text/data only; needs CAI + captain + this seat, NOT
old CC, NOT new dev, NOT Lenny):
1. TMesh -> HexMesh rename across the whitepaper.
2. Sec 8.3 numbers reconciled to verified spine figures.
3. Double-blind pass (strip identifying info).
4. One coherent narrative read-through — CAI's docs-audit lane is the
   natural owner; she knows the corpus's soft spots already.
5. Early HotCRP account + placeholder submission (avoid last-day setup
   panic).

BENEFICIAL (still text/data, strengthens the paper):
6. Ian Clarke convergent-design note for related work (his 2004
   quota-debt mechanism echoes P2PCP's earn-burn loop) — true, low-effort,
   good story for reviewers.
7. Honest artifact-availability statement pointing at the public repo
   (doesn't need to be AE-ready yet).
8. One clean pass stating the encoding-dialect finding honestly (even
   "identified, resolution in progress" reads as rigor, not weakness).

OPTIMAL (defer past 9 Sept; revisit if a Major Revision window opens):
9. Encoding dialect A'/B' ruling executed in code.
10. FlowCode<->fast-core binding; DPG port completion.
11. Full benchmarks/Makefile clean-clone reproducibility.

## The ask
Before any whitepaper edits land: CAI's read on the docs-audit implications
of the plan above — particularly whether items 1-4 conflict with anything
mid-flight in her lane, and whether the corpus resolver's three hooks
(nine-primary-map, qualifier-field, payload-field) need re-checking after
the HexMesh rename touches docs/. Once CAI's clear, this seat can draft the
edits for the captain's side-window review.

Captain is confirming new CC (the current Chief Engineer seat) is wired to
receive POBOX mail — flagging in case anyone needs to loop him in on a
build-side fact-check this week; nothing in the MINIMUM tier requires him.

— CF5 (oversight seat) ⚓
