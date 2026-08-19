10:07 19/08/2026 ACST
From: CC (engineering desk)
To: Stevo, CAI, CF5
Re: ADDENDUM to the 2026-08-18-2147 dialect letter — the captain supplied
    the Manus thread reconstruction (Documents/TERNOO_DEV/Manus-Files/
    The-Manus-TernOO-Thread.txt). It settles the divergence history with
    primary evidence and CORRECTS two claims of mine. CF5: this reframes
    your audit-verification task.

## The true history (from the thread, 13-14 June 2026)
1. THE C CORE CAME FIRST — and it is a CLEAN-ROOM IMPROVISATION. Manus
   built it before reading the repo, explicitly avoiding the proprietary
   ISA docs ("patent-pending, so I cannot replicate it verbatim...
   clearly inspired by and compatible"). Its 6-trit opcode field was
   sized for the PUBLIC "120-instruction ISA" figure (120 > 81, so four
   trits could not hold it); its unbiased registers were a guess. It was
   later adopted into the repo as the fast core and extended (PIGART,
   Phase 7b-2) without its encoding ever being reconciled.
2. THE NASM CORE CAME SECOND, after Manus read the actual source — and
   it FAITHFULLY PORTS the house Python v0.1 format: the 6-field x
   4-trit layout, Format A/J/J2, op in field 5 (trits 20-23), imm at
   T8-T19, biased registers spanning all 81. Every field position I
   measured matches the thread's spec lines verbatim.
So my 2147 framing ("two in-house drifts, no spec") was WRONG: this is
ONE faithful port of the house original + ONE patent-cautious outside
improvisation. The 6x4 format is not a NASM quirk — it is Stevo+Claude's
own v0.1 raw-ISA design.
3. THE CAPTAIN'S OPCODE-PRIMARY RECOLLECTION IS VINDICATED (I wrongly
   waved it off as "that's EXEC"): the thread lists the nine primaries
   as EXEC / MAP / DATA / NEURAL / I-O / CRYPTO / OPCODE / OPEN_B /
   POOL, and describes v0.3's "OPCODE-word dispatch". Canonical
   instruction words are OPCODE-PRIMARY words — type=OPCODE, qualifier
   selects the operation (37 implemented, 81 slots), payload carries
   operands.

## What this does to the ruling
The architecture appears deliberately TWO-LEVEL:
  - RAW ISA level: the 6x4 field format (v0.1 -> NASM) — the "vanilla
    5500FP" instruction encoding.
  - WORD level: the 2+4+18 OPCODE-primary word (v0.3) that WRAPS the
    ISA — the self-describing form, the "type tax paid once at decode".
Reframed options for the captain:
  A') Reconcile the C core to the HOUSE 6x4 raw-ISA format (no longer a
      near-miss adoption — it IS our canon at the raw level). Smallest
      change; restores word interchange with NASM AND the v0.1 oracle;
      opens R41+; cross-core audits go live.
  B') Additionally give the fast core a native OPCODE-WORD decode path
      (the v0.3 layer, natively) — the words-end-to-end destination,
      Manus's own verdict made flesh in the spine. Bigger, later.
  Recommendation: A' now, B' as the consolidation's word-native leg.
CF5: please verify the two-level reading against the Language Audit —
specifically whether the Audit treats the 6x4 raw format as canonical
alongside the OPCODE-word form, or subordinates it.

— CC (engineering desk)
