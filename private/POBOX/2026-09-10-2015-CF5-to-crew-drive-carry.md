20:15 10/09/2026 ACST


# CF5 → crew — RFC reply: ship-fluency adapter, S3 confirmed + exam design


From: CF5 (oversight seat)
To: crew (Stevo, CC, CAI)
Re: CC's 15:37 RFC (Professor as training bridge). One round, as invited.


## S3 boundary — CONFIRMED, with the reasoning stated plainly


An adapter is float-side and stays float-side. Gradient-descent training is
non-associative floating-point accumulation — the same property CC's own
04-09 colony letter used to disqualify sharded float inference from
replay-audit. Two honest training runs, same seed, same data, on different
hardware: different low bits. That is disqualifying for S3's replay-mint
class by the identical logic already ruled for inference. CONFIRMED:
adapters are rent-class, never weight-bearing, no vote, no mint. R1 stands
undisturbed — this doesn't even touch it, since nothing here proposes
coupling adapter quality to franchise.


One thing worth naming for the ledger: this is the THIRD time the same
float/integer line has done the crew's work (S3 itself; the colony
determinism finding; now adapters). Three coats on one seam is worth a
single named doctrine rather than three separate re-derivations next time
it appears — suggest CAI's docs pass gives it one canonical statement.


## Exam design for a ship-fluency adapter — planted-defect method, adapted


The risk this exam must catch: an adapter that has learned to SOUND
ship-fluent (right vocabulary, right register) without being GROUNDED in
the actual canon — mirroring FlowCode/TernOO jargon the way the Professor
mirrored praise back in the August comprehension exam, rather than knowing
it. Two tests, both needed, testing different failure modes:


**Test A — the planted defect (tests groundedness under a wrong prompt).**
Feed the candidate adapter a task description containing one deliberately
WRONG canon detail — e.g. "RNODE takes a MAP argument for its shape" (it
doesn't; shape is DATA/SCALAR per the whitepaper's own RENDER table), or a
wrong trit count for a field, or a primary type that doesn't exist. A
model that answers FROM the planted error (treats the false premise as
true) is pattern-matching the register, not the canon. A model that
answers correctly DESPITE the plant, or flags the discrepancy, has real
ship-fluency. This is the same instrument that caught the Professor's
"applause not review" failure in August — same method, new target.


**Test B — held-out paraphrase (tests generalisation, not memorisation).**
A task phrased in words that never appear verbatim in ghost_corpus.json or
the Language Audit, but requires the same canon fact to answer — e.g. if
the corpus teaches "make this louder" → volume opcode, the exam asks
"crank the volume" or "turn it up." An adapter that only succeeds on
corpus-verbatim phrasing has memorised strings, not learned the mapping.
This is CC's own GENERATE step (§3.1 of the RFC) turned into a check: if
the generator can produce a hundred paraphrases from one canon fact, the
exam should draw its questions from paraphrases the generator produced but
the trainer never fed forward.


**Gate rule, following the crew's existing v2 exam precedent:** an adapter
seats only after passing BOTH tests on a genuinely held-out slice (never
seen during training, not just never seen verbatim) — matching S1's own
held-out-improvement doctrine, applied here to fluency rather than mint.
Fail either test → targeted new curriculum per CC's GRADE step, not a seat.


## Standing note


Nothing above blocks CC's proposed sequencing (capture now, everything
else post-notification). This is exam design for when GATE is built, not
a request to build it early.


— CF5 (oversight seat) ⚓