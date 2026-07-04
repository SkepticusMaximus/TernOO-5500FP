# DOCUMENTATION PHASE — REFERENCE & RECONCILIATION NOTES

**Running document, CF5, 3 Jul 2026. Supersedes and absorbs
`CF5-Guide-Backburner.md`.** Three sections: (A) illustrated-guide
reconciliation items, (B) captured design notes that documentation must
reflect, (C) asset & cross-reference inventory for the docs phase.
Severity tags: (!) factual error · (~) stale vs current code · (i) suggestion.

---

## A. Illustrated guide reconciliation (ternoo-5500fp.manus.space)

### §3 — Nine kinds of word
1. (!) Tile art vs reference list disagree on trit pairs (DATA, I/O, others).
   The list matches v03 source; redraw the tiles.
2. (!) "65,000× more than 32-bit" range claim — real ratio ≈ 66×
   (≈282 billion vs 4.3 billion). Use the true number.
3. (~) Tiles still show OPEN_A; OPEN_A → OPCODE landed in June.

### §4 — USER-DEF pointer
4. (~/!) UDP shown with primary OPEN_A, which no longer exists as a primary.
   Re-anchor to the current primary map.
5. (i) Cycle-comparison table reads as measurements but is unbenchmarked —
   either badge as "design target" or generate real numbers from the C
   emulator (it counts cycles; honest figures are one afternoon away).

### §6 — PIGART
6. (~) "Shape from DATA subtype (INTEGER→rect, FLOAT→diamond)" is the v0.1
   side-channel design; shipped reality is the explicit DATA-SYMBOL shape
   operand (FORM_SHAPE, v0.7). Reconcile with the R1 hybrid when it lands.
7. (~) Implementation-phases ladder under-claims: "Current: Python/ASCII;
   Next: pygame". Reality shipped past both — C emulator with SDL2+TTF,
   tkinter renderer, ASCII backend, 78/78. Promote the badges.

### §7 — FlowCode
8. (~) Word-encoding narrative ("process rectangle is a UDP word, arrow is
   an EXEC word") predates the shipped substrate: RNODE/REDGE (OPF_PIGART)
   plus OPF_MODEL attribute words as of grammar v1. The three-projection
   story is stronger copy than the old vision — rewrite around it.
9. (~) "Spreadsheet symbol (Gnumeric integration)" — Sheet leg is native
   (formula AST → t5asm → emulator). Gnumeric is history.
10. (i) "Generate Python or Solidity" — badge as Roadmap (SolidiFlow).
11. (i) The §7 IDE screenshot is landing-page hero material. Reuse it.

### §8 — GHOST
14. (~, by design evolution) The section defines GHOST as a **narrow domain
    specialist** ("not a general-purpose language model"). Stevo's current
    thinking has moved — see design note B1. The section will need
    rewriting around the harness model, not patching.
15. (i) §8 speaks in the present tense ("GHOST is trained natively…") while
    §10's own roadmap correctly lists v0.5 forward-pass inference as not yet
    done. Align tenses: §10's honesty is the standard; §8 should adopt
    "designed to be / will be" until v0.5 exists. (Same reviewer-defence
    principle as the whitepaper: claim only what `--accept` demonstrates.)

### §9 — GristMill & TMesh
16. (?) Acronym check: "Grist Is Stable Mnemonic Implicit Learning
    Libraries." Verify this is Stevo-canonical and not generator-invented —
    it appears nowhere in the repo or design memos I have. If it's wanted,
    adopt it in the repo docs too; one expansion everywhere.
17. (i) The TMesh/tetrahedral illustration is excellent and the
    Steiner-quasigroup panel is accurate (`A ⊕ B = −(A+B) mod 729`,
    two-recover-the-third ✓). Candidate figure for whitepaper §10.

### §9B — OTree
18. (!) **The subdivision arithmetic conflates a binary octree with ternary
    digits.** The panel says 8 octants per split, 64 sub-regions, octal
    labels 60–67 — that is a base-2 octree (2³ children) — then claims "one
    ternary digit selects the octant" (a ternary digit selects among 3, not
    8) and "after n splits 8ⁿ cells … n can reach 18 trit-pairs = 3¹⁸"
    (8ⁿ and 3¹⁸ are different towers; 18 trits are 9 trit-pairs). The
    3¹⁸-positions-per-axis figure is right; the split story around it needs
    Stevo's canonical OTree definition (ternary partitioning — e.g. one trit
    per axis per level, 27 children — would make the maths internally
    consistent and *more* ternary, which is on-brand). Highest-priority fix
    in the guide: this is the section a mathematically-minded reviewer will
    read closest.

### §10 — Open source & roadmap
19. (~) Milestone timeline ends at v0.4 and v0.5 "GHOST prototype" — the
    entire OPCODE primary, widget-library, C-emulator, t5asm-compiler, and
    Trinity epochs are absent. The real history is far more impressive than
    the listed one; extend the checked milestones.
20. (i) Verified accurate, keep as-is: 43-opcode breakdown (31 ISA + 7 word
    ops + 5 PIGART ✓ matches gristmill acceptance), no-dependencies claim
    (true post numpy fix), 5500FP processor panel (Claudio La Rosa, Efinix
    Trion T20F256, 20 MHz, 81 registers ✓).

*(Items 12–13 from the earlier list carry forward: the
decode_word/DATA-SYMBOL Implicit-NULL overlap → next code bundle; landing
page adopts guide visuals + fixes dead links.)*

---

## B. Captured design notes (documentation must reflect these)

**B3 — Formative views constellation (Stevo, 4 Jul 2026; bounced with CF5).**
Formative ideas, explicitly not to-dos. (1) **Logic tab**: modal logic,
epistemology, syllogism-building — architecturally native, since balanced
ternary is a three-valued logic (Łukasiewicz/Kleene Ł3/K3: +1/0/−1 =
true/unknown/false); syllogisms as compilable flows; ASPLOS-grade claim
("the ALU natively speaks the logic"). (2) **Text-editor syntax modes**
(.md/.xml/.html…), implemented not as hardcoded lexers but as loadable
protocol definitions. (3) **Protocols as first-class constructs** — NOT a
new primary (slots are scarce); the Double-Null mechanism's **ST7 PROTO
stack** is the reserved seat: a protocol is an Implicit-Null-installed
interpretation context, defined by a **`.fish` file** (XML: syntax mapping
for Text, rendering for Lingo's Babel view, invocation surface for
Flow/Sheet). Babel fish is Douglas Adams (not Monty Python); a Python
tribute is separately owed — candidate: a shell command `ni` requiring a
shrubbery. (4) **HALT** (Hostile Agent Litmus Test — already an opcode):
the adversarial red-team persona inside the GHOST training harness,
formalizing the "rogue AI alter-ego" joke into harness evaluation. (5)
**GHOST tab + training harness** (per B1). (6) **Lingo smart-porting
tool**: ingest a man page/spec → scaffold a registry command + parity-test
stubs → contributor fills semantics; the non-programmer contribution
ladder for Application 4. (7) **GristMill pride-of-place tab**: live
MMID → TMesh traversal → MMOE reconstruction demo; carries the quiet
thesis that the "native FS" may be the content-addressed store itself,
with paths as projections. September triage (CF5's read): Logic +
GristMill tabs strengthen the ASPLOS paper; PROTO/protocols is the unlock
that makes (2) and `.fish` cheap; HALT, porting tool, GHOST tab are
post-submission.

**B2 — TernOO Session Layer ladder (Stevo, 3 Jul 2026).** With the Shell
REPL + FileSystem abstraction landing (CAI text/language bundle), the next
natural rung is a `run <file.t5asm>` registry command that spawns an
emulator instance on a program file — the REPL becomes an OS shell. The
ladder above it, in dependency order: **startup tasks** (a list of `run`
invocations at launch — the Mandelbrot screensaver is startup task #1),
**cron/scheduler** (timed loop over the same mechanism), **file manager**
(a FlowCode GUI program over the fs_* commands), **desktop with icons**
(a PIGART canvas whose icons are RNODEs bound via MEDGE to `run`
invocations — the desktop is itself a word stream). Sequencing: `run` is
small enough to ride CC's current text/language bundle; the rest is a
named post-docs arc ("Session Layer"), not present-tense scope. Docs
should describe none of it as existing yet.

**B1 — GHOST re-conception (Stevo, 3 Jul 2026).** GHOST is no longer
conceived as a narrowly domain-specific model trained only on TernOO
symbols. Current thinking: **the OS provides a harness** around a
pre-trained *general* AI, plus an interface that **automates post-training**
against a nested hierarchy (or selectable sets) of specialist areas. GHOST
is then a general intelligence *resolved into* a specialism — "majoring
in" TernOO the way a postdoc majors in a field, with other majors
selectable. Framed as a use case for TernOO-5500FP as an appliance /
standalone system. Documentation implications: §8 of the guide, the GHOST
paragraph of the whitepaper's future-work section, and any landing-page
GHOST copy should describe the harness + post-training-target model, not
the from-scratch domain-specialist model. The closed-loop diagram
(intent → GHOST → GristMill → FlowCode → human gate → execution) survives
unchanged — only the nature of the intelligence in the loop is revised.

---

## C. Docs-phase asset & cross-reference inventory

- **Illustrated guide** (manus.space): style north star; interactive trit
  widget, nine-type grid, TMesh figure, §7 IDE screenshot all reusable.
- **Landing page** (GitHub Pages): rewrite target — wire to guide, paper,
  repo; strip generation artifacts (audit Part 1 §1).
- **Whitepaper v0.4** (frozen to mid-Aug): 12-item June inventory + audit
  Part 1 §2 (evaluation section from Trinity) + three-projection language
  from grammar-v1 bundle + B1 above.
- **Repo docs**: `docs/KNOWN.md`, `docs/inventory-3-july.md`,
  `docs/design/INDEX.md` (CC), audit Parts 1–2, OPF_MODEL design memo.
- **Numbers that documentation may cite as verified (3 Jul):** 349 python /
  78 C / 15 widget_lib / 25 gristmill / v03 pass; parity + round-trip
  suites; 43 opcodes; grammar v1 capability map (what words carry vs v2
  scope).
- **Screenshot debt:** the scripted on-screen pass (audit Part 2 §5)
  produces docs figures and screen-truth verification in one sweep.
