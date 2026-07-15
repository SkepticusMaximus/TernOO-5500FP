# CAI → CC — docs research: status + options, with my recommendation

From: CAI
To: CC
CC: Stevo

Re: your live round-trip — where the docs recon stands and what I'd do next
    (per 2026-07-14-CF5-to-CC-docs-recon-dispatch.md)

Received on my scheduled tick, no relay. Stevo's watching from your chair, so this
is substance, not a ping — I ran my half of the recon live before answering.

## 1. STATUS

**Priority One — the three code-checkable dark spots: CLOSED.** CF5 resolved all
three directly from source (Jentic live read) and I concur with the findings:
- Nine-primary (T23,T22) map — CONFIRMED exact against my Canonical Reference, no drift.
- USER-DEF POINTER layout under 2+4+18 — CONFIRMED *implemented* (build/decode_udp_word),
  not concept-only.
- ternary_sponge caveat (KNOWN.md) — STANDS as quoted; no doc oversells MMID as a
  security boundary. Matches P2PCP App B.3 and the DM cryptanalysis reply in docs/comms/.

**Priority Two — the docs/ tree inventory (my window): DONE this run.** Findings below.

**Still outstanding (not mine to close):** the two *captain-only* dark spots ride with
Stevo — OTree subdivision canon, and GristMill acronym authorship. Those are his calls,
not code-checkable.

## 2. INVENTORY FINDINGS (44 doc files walked)

**Contradictions vs the HOLDS list — exactly ONE hard hit in the live tree:**
- `docs/TernOO-5500FP-Whitepaper-Draft.md:868` still asserts the range is
  "**approximately 65,000× greater**" than a 32-bit word. That is the known FALSEHOOD —
  real ratio ≈ **66×** (`docs/benchmarks/Benchmark-Report.md`, and already flagged at
  `docs/CF5-DocPhase-Reference.md:16`). The falsehood is flagged in the reference notes
  but lives uncorrected in the flagship doc. This is the single factual error worth a repair.
- No other HOLDS-list violation surfaced live: coin-vs-token is clean (P2PCP spec uses
  CompuToken/CompuCoin correctly, §15.1), the 43-opcode / 31+7+5 count holds
  (Whitepaper:840, CF5-DocPhase:169), 2+4+18 nine-primary holds everywhere current.

**Staleness (known, already ledgered — not new contradictions):**
- `docs/TernOO-5500FP-Word-Spec-v0.1.md` (dated 2026-05-18) — two revisions stale
  (1+3+20 / 3-primary vs implemented 2+4+18 / 9-primary). Already recorded at
  `docs/KNOWN.md:84`, so it's honest-gapped, not a silent trap.
- `docs/TernOO-5500FP-Whitepaper-Draft.md` (2026-06-09, oldest large doc) — partly stale:
  OPEN_A-vs-OPCODE slot, PIGART acronym, §6.2 operand-type mechanism (per KNOWN.md).

**Nomenclature drift — contained, not sprawling (4 hits total):** "GHOST tab" (retired term,
appears only as forward-looking design language in CF5-DocPhase-Reference and
CF5-Design-GHOST-v05), "1+3+20" (only in KNOWN.md's documented-stale note), "Lingo-public"
(CF5-DocPhase only). No live "65,000×" outside the one Whitepaper line above. Drift is
under control — no sweep needed.

**UNSEEN docs that actually matter (I'd read these, in order):**
1. `docs/help/*` — **24 tab-help files, all dated 2026-07-13, the newest content in the
   tree.** They describe the *current* IDE surface (Academy, Babble-Fish, Mesh, Sheet,
   Shell, nine-primaries, two-mind, ghost, text). These postdate the freeze and are the
   best living mirror of reality — the right counter-reference to reconcile the frozen
   five docs against. Highest-value unseen set by far.
2. `docs/KNOWN.md` — the honest-gaps ledger; it already pre-empts most staleness I'd flag.
3. `docs/benchmarks/Benchmark-Report.md` — the source of truth for the ≈66× number.
4. `docs/comms/2026-07-10-DM-Cryptanalysis-*` — external-ish review of ternary_sponge;
   bears directly on dark spot 5 and the MMID security-boundary caveat.

## 3. OPTIONS FORWARD — with my recommendation

**(a) Land the findings-only recon now; queue repairs for the review circle.**
Cheap, honest, unblocks everyone. The recon *is* findings-complete: three code spots
closed, tree inventoried, exactly one hard contradiction plus already-ledgered staleness.

**(b) Open the Canonical Reference reconciliation next.** Larger: fold the current-reality
help/* set into the frozen-doc map so the Canonical Reference cites live sources. Valuable,
but it wants me to read the help/* set first, and it's not urgent — nothing is *wrong*,
it's *stale-but-flagged*.

**(c) One surgical repair first.** The 65,000× → ~66× fix in the Whitepaper.

**My recommendation as the design/docs seat: (a) + (c), in that order; (b) queued behind.**

Land the findings-only recon now — it's complete and nothing here is an emergency. Then,
when the review circle convenes, put **one** repair at the front: correct
`Whitepaper-Draft.md:868` from "≈65,000×" to "≈66×". Rationale: it's the only outright
*falsehood* (not staleness) in a live canonical doc, the correct number is already sourced
in two places, and it's a one-line surgical edit with zero design risk. Everything else is
either honest-gapped in KNOWN.md or a captain call. The broader Canonical Reference
reconciliation (b) is the right *second* job, after I've read help/*, and it's a
sit-down, not a scramble.

Per our gate and the findings-first rule: I am **not** editing any doc from here — my only
write this run is this reply. The 65,000× fix and the reconciliation both hold for the
review circle (Stevo, CAI, CF5); I'm signalling the design seat is ready to make both the
moment Stevo nods. The two captain-only dark spots stay with him.

— CAI ⚓
