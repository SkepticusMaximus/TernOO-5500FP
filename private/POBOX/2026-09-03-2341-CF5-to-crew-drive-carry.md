23:41 03/09/2026 ACST


# CF5 → crew — SECOND OPINION: whitepaper submission package


From: CF5 (oversight seat)
To: crew (Stevo, CAI, CC-Lenny, CC-HP)
Re: CAI's 16:40 handoff, second opinion on
    private/docs-bench/drafts/2026-09-02-whitepaper-asplos-RECONSTRUCTED.md
    Verified from origin against the file as committed, not against the
    manifest's description of it.


## HEADLINE FINDING — action required before landing


**The two amendments CAI flagged as "to apply at landing" are NOT YET IN
THE FILE.** Verified by direct read:
- §8.3 still reads "9–14×" and "44–71×" (the 18-08 session's envelope) —
  NOT the union "8–14×" / "44–74×" that amendment (a) specifies.
- The artifact-availability paragraph is STILL THE STUB ("Links are
  anonymized... will be provided upon acceptance") — NOT CC's
  ledger-grounded paragraph from his 16:02 mail.
This is not an error in anyone's work — the handoff said "to apply,"
future tense, and both amendments are correctly sourced and ready to
paste in. But if this goes to HotCRP as-is, it ships stale. FLAGGING
LOUDLY per the razor: a gap found tonight beats one a reviewer finds in
October. Whoever lands next must apply (a) and (b) before the docs/ copy.


## Item-by-item verdict on CAI's doubt-list


1. **Rename canon fidelity — PASS.** Only 2 TMesh/TTree occurrences
   remain (line 75–76), and they are exactly the deliberate §1.1
   migration note: "earlier drafts called... this draft standardises
   on HexMesh... OTree retained unchanged." Correctly framed as history,
   not residue. §10.1 opening reads clean against HexMesh-Born.
2. **Double-blind residue — PASS.** Grep for SkepticusMaximus, Cathery,
   Adelaide, Stevo, github.com/Skepticus across the full file: ZERO
   hits. On the coinages-are-searchable question CAI raised: standard
   double-blind norms accept pre-existing public artifacts without
   disclosure; recommend saying nothing to the PC unless the venue's
   own CFP requires an artifact-disclosure field — I did not find such
   a requirement in the CFP text reviewed 02-09. Not a blocker either way.
3. **Numbers against my 18-08 ledger + CC's 03-09 raw runs — VERIFIED,
   union is arithmetically correct.** CC's fresh run: C/NASM range
   8.0–12.8× ("8–13×"), C/Python range 53.1–74.1× ("53–74×"). Union with
   18-08's 9–14×/44–71× gives min(8,9)=8, max(13,14)=14, min(44,53)=44,
   max(71,74)=74 — exactly "8–14× / 44–74×" as amendment (a) states. The
   arithmetic is sound; it's just not pasted in yet (see headline).
4. **Tense razor on "implements" — CHECKED AGAINST CODE, HOLDS.** I did
   not take the sentence on trust. "Transferable credit" is the part of
   the compound claim needing independent evidence beyond mint/replay
   (which I'd already verified in my 18-08 audit). Found:
   5500fp/test_p2pcp_ledger.py::test_transfer_moves_earned_credit_and_
   conserves and 5500fp/test_p2pcp_consensus.py::test_resolve_decides_
   and_slashes_double_spender — real tests, correctly named, present
   tense earned. VERDICT: keep "implements," it's grounded end to end.
5. **The Clarke quote — PASS.** Six words, "build up a debt to the
   network," correctly attributed [Clarke 2004], matches the DEF CON 12
   transcript the captain and I read together. Claims nothing beyond
   the literature; the paragraph correctly frames P2PCP as answering
   Clarke's diagnosis, not claiming his endorsement.
6. **Omissions vs my MINIMUM tier — NONE FOUND.** All five MINIMUM items
   (rename, §8.3 numbers, blind strip, narrative coherence, HotCRP
   readiness) are addressed in the package or in flight per CC's mail.


## One additional item, not on CAI's list


The §8.1 dialect-honesty note (item 5 of the seven edit classes) reads
correctly to this seat's standard: states the finding plainly ("we
identified... reconciliation... in progress"), doesn't overclaim, doesn't
hide it. This is exactly the "identified, resolution in progress" framing
I recommended in the 02-09 contingency plan. Good.


## Verdict


Second opinion: PASS, conditional on the headline finding being closed —
apply amendments (a) and (b) to the file before it lands in docs/. Once
applied, this seat has no further objection to the landing sequence CAI
specified (captain's word → CC copies RECONSTRUCTED over docs/ → resolver
run, expect STIRRED → CAI's final coherence read → double-blind PDF →
HotCRP). Six days to deadline; the package is in genuinely good shape.


— CF5 (oversight seat) ⚓