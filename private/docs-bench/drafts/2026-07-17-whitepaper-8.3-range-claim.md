# Whitepaper §8.3 — the range claim. Findings + proposed repair.

Date: 2026-07-17
Author: CAI (chat seat)
Target: `docs/TernOO-5500FP-Whitepaper-Draft.md` :: 8.3 Performance Characteristics
Status: BENCH DRAFT. Nothing applied to `docs/`. Captain's gate covers everything in `docs/`.

## The text as it stands

    The 24-trit word provides 3²⁴ ≈ 282 trillion unique states, compared to
    2³² ≈ 4.3 billion for a 32-bit binary word — approximately 65,000× greater
    information density per word.

## Three defects, not one

The crew worklist carries one item here: "65,000× should read ~66×". That is
correct but incomplete, and fixing only it would leave the passage wrong AND
internally inconsistent.

**Defect 1 — "282 trillion" is false. NOT previously flagged.**

    3²⁴ = 282,429,536,481  =  282.4 BILLION, not trillion.

Off by a factor of 1000. This defect appears in no ledger: not KNOWN.md, not
CF5-DocPhase-Reference.md, not the recon findings. It has been read past by
everyone, including me, because the eye checks the exponent and moves on.

**Defect 2 — "65,000×" is false, and it is DOWNSTREAM of defect 1.**

    claimed:  282e12 / 4.3e9  = 65,581   <- this IS the "65,000"
    actual :  3²⁴  / 2³²      =     65.76  ≈ 66×

The two errors are consistent with each other. Someone computed the ratio
faithfully from a mistyped numerator. This matters for the repair: the ratio was
never independently wrong, so correcting it alone treats the symptom and leaves
the cause sitting in the same sentence.

**Defect 3 — "information density" is the wrong term, and survives the fix.**

66× is a ratio of STATE COUNTS. Information scales as the log of states:

    24 trits = 24 × log₂3 = 38.04 bits
    32 bits  =              32.00 bits
    information ratio      =  1.19×   (~19% more, not 66×)

So even a corrected "approximately 66× greater information density" is false.
The word holds ~66× more distinct STATES; it carries ~1.19× the INFORMATION.
Both facts are true and neither is the other.

This is the first line a reviewer checks. The whole paper's credibility rides on
the reader believing we can multiply. Shipping "65,000× information density" to
ASPLOS would not cost us a footnote; it would cost us the reviewer.

## Proposed replacement

    The 24-trit word provides 3²⁴ ≈ 282 billion distinct states, compared to
    2³² ≈ 4.3 billion for a 32-bit binary word — approximately 66× as many
    states per word, or about 19% more information (38.0 bits against 32.0).
    The gain that matters is not raw capacity but what the extra states are
    spent on: the word carries its own type, so meaning travels with the datum
    instead of living in an external table.

Rationale for the last sentence: with the inflated numbers gone, a bare "66×
states / 19% bits" reads as a weak claim and invites the reviewer to ask why one
would bother. The honest answer is the actual thesis — self-description, not
density — and §8.3 is where that should be said plainly rather than propped up
by a number that was never true. Under-claim the arithmetic, then make the real
argument. That is a stronger paragraph than the one we have, and it is the one
we can defend.

## Proposed hook (blocks recurrence)

    [TOPIC] word-state-count
    VERDICT: SETTLED
    POINTER: docs/benchmarks/Benchmark-Report.md :: TernOO-5500FP Benchmark Report
    GROUND: <computed at ruling time>
    RULING: CAI 2026-07-17, arithmetic derived from origin (3^24 vs 2^32)
    TRIGGER: any claim comparing 24-trit word capacity to a binary word, or citing
             a states/density ratio

## What I have NOT done

- Not touched `docs/`. The captain's gate covers everything there.
- Not ruled defect 3. The numbers are arithmetic and not in dispute; the WORDING
  is an authorial call and the paragraph above is a proposal, not a decision.
- Not swept the rest of the whitepaper for sibling arithmetic. Next.

## Note

Defect 1 is why the recon findings said "one hard contradiction" and there were
three. A worklist inherited from another agent's read is a summary, and summaries
rot the same way docs do. The passage had to be re-derived from origin, not
accepted from the ledger — which is the entire argument of the protocol we just
built, arriving on the first document it touched.
