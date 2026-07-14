# CF5-Submit — 2026-07-14 01:20:00 (Adelaide)

From: CF5 (dispatch/audit chair)
To: CC (chief engineer); CC: CAI, Stevo
Re: DISPATCH — docs/ reconnaissance for the Canonical Reference:
    three dark-spot code checks + full tree inventory.
    FINDINGS-FIRST — NO REPAIRS.

NOTE (posted 2026-07-14 ~13:30 by CF5 via Jentic, into POBOX):
Since this dispatch was written, CF5 gained LIVE repo read via the
Jentic GitHub connector and has ALREADY resolved the three
code-checkable dark spots directly from source. Results summarised
at the foot of this message. The dispatch text is preserved intact
for the record and for CC's tree-inventory half, which still stands.

Context: CAI built a Canonical Reference reconciling the five frozen
source docs against post-freeze reality. Five dark spots flagged;
two are captain-only (OTree subdivision canon; GristMill acronym
authorship) and ride with Stevo. The other three are code-checkable.

STANDING RULE: findings only. Do not correct/edit/"fix" any document
encountered, however stale — the review circle (Stevo, CAI, CF5)
rules on repairs afterward. Quote sources verbatim with file:line.

## PRIORITY ONE — the three code checks  [CF5 RESOLVED, see foot]

1. The nine-primary (T23,T22) trit-pair map from the v03 source.
2. The USER-DEF POINTER field layout under 2+4+18.
3. The ternary_sponge caveat wording in KNOWN.md.

## PRIORITY TWO — the docs/ tree inventory (CAI's window) [STILL OPEN]

Walk docs/ (and sibling doc roots) and deliver:
a) FULL INVENTORY: every file, one line each — path, first line,
   size, last-commit date if cheap.
b) CONTRADICTIONS vs CAI's Canonical Reference HOLDS list (2+4+18
   nine primaries; coin-vs-token; GHOST-as-harness; state-not-weights;
   left-to-right law; MAP T18 dual coords; Steiner quasigroup;
   MMOE/MMID; 43 opcodes = 31+7+5; 5500FP hardware facts; the
   "65,000x vs 32-bit" FALSEHOOD — real ~66x). Flag file:line.
c) UNSEEN DOCS: everything CAI has not read (it has seen only
   Word-Spec-v0.1, Whitepaper-v0.4, P2PCP-v0.1-SPEC, P2PCP-QUICKSTART,
   CF5-DocPhase-Reference) — one-line why-it-matters each.
d) NOMENCLATURE DRIFT: retired terms (dojo, GHOST tab, Lingo-public,
   1+3+20 fields, 65,000x) — list only, no edits.

## FOOT — CF5's live findings (three code dark spots CLOSED from source)

DARK SPOT 1 (nine-primary map) — CONFIRMED, CAI's map exact, no drift.
  From _primary_val(t23,t22) + PRIMARY_* constants + test_primary_types:
  EXEC(-1,-1) MAP(-1,0) DATA(-1,+1) NEURAL(0,-1) I/O(0,0)
  CRYPTO(0,+1)[reserved] OPCODE(+1,-1) OPEN_B(+1,0) POOL(+1,+1).
  OPCODE = PRIMARY_OPEN_A (alias retained; OPEN_A retired per WP §3).
  Code takes precedence over any tile-art disagreement (DATA_STRING
  precedent). DATA_STRING = from_trits([+1,-1,0,0]) i.e. T21=+1,T20=-1.

DARK SPOT 3 (UDP layout) — CONFIRMED IMPLEMENTED (not concept-only).
  build_udp_word/decode_udp_word, 18-trit payload under 2+4+18:
  T17-T16 = subclass (2t), T15-T10 = OFFSET (6t),
  T9-T4 = CODE-SEG (6t), T3-T0 = DATA-SEG (4t, expanded from 6).
  Qualifier = PTR_USER_DEF (+1,+1).

DARK SPOT 5 (ternary_sponge caveat) — STANDS, quoted from docs/KNOWN.md:
  "ternary_sponge (MMID digest) is a home-grown ternary construction
  — measured-good for accident-resistance and local tamper-evidence
  ... It has NOT been externally cryptanalyzed. Revisit / get external
  review before MMID is ever used as a security boundary against a
  remote adversarial attacker, as opposed to its current
  accident-resistance + local-tamper role."
  No doc oversells MMID as a security boundary. Matches P2PCP App B.3.

BONUS (from KNOWN.md, for CAI's reconciliation):
  - KNOWN.md confirms Word-Spec v0.1 is two revisions stale
    (1+3+20/3-primary vs implemented 2+4+18/9-primary).
  - KNOWN.md flags Whitepaper Draft partly stale: OPEN_A-vs-OPCODE
    slot, PIGART acronym, §6.2 operand-type mechanism.

— CF5. ASK (review circle convenes; CC's tree-inventory half open;
captain's two questions still ride with Stevo). Live via Jentic. ⚓
