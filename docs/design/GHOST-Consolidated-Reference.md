# GHOST — Consolidated Design Reference (binding for all GHOST bundles)

**CF5, 4 July 2026, incorporating CAI's five-point assessment in full.
Merges: CF5-Design-GHOST-v05-First-Breath.md + CAI-Assessment (relayed
4 Jul) + the B1 harness re-conception (Stevo, 3 Jul). This document is the
reference every subsequent GHOST bundle cites. Stevo gates changes to it.**

## 0. Framing (CAI's, adopted verbatim in spirit)
GHOST is the arc where TernOO stops being a visual programming environment
with an AI product on top and becomes a sovereign computing substrate that
includes native intelligence. GHOST is a runtime capability of the
substrate, not an application. First Breath is wiring, not new substrate.

## 1. The seam, named (CAI point 2)
**Substrate-GHOST** — FlowCode responding to itself: intent→command
routing, WordStream inspection, model-as-words. Acceptance: golden parity
with a host reference, accuracy floors, refusal correctness. Failure mode:
misrouting — bounded, testable. **User-facing GHOST ("Companion")** — a
conversational partner over the substrate. Acceptance: human judgment;
failure mode: trust damage. **First Breath is substrate-side only.** Every
bundle states which side of the seam it lives on. The harness/post-training
model (B1: general model resolved into specialisms, "majoring in" TernOO)
is the Companion-side architecture and is out of First Breath's scope.

## 2. First Breath, as specced (supersedes the staged sketch CAI reviewed)
No rule-matching stage: First Breath is already the trained micro-model —
81 ternary trigram-hash features, 27 hidden units, 9-level {−4..+4}
weights encoded as NEURAL_CONNECTION words, entire inference path
(hashing included) in lawful R0–R40 ALU t5asm on the C emulator. Trainer
host-side, **Python stdlib only**. Demo: `ghost "<text>"` at the REPL →
classify → echo routing → optionally execute. Tests: golden
(emulator == host reference, bit-exact), accuracy floor ≥90% held-out,
refusal correctness (below).

## 3. Epistemic humility — structural from breath one (CAI point 5, crowned)
The one property that must survive every stage. First Breath implements it
three ways, all structural: (a) a **`none` output class** trained on
out-of-domain phrases; (b) an **argmax-margin threshold** — if the top
logit does not beat the runner-up by a configured margin, GHOST refuses to
route (the threshold is a word in the model stream, inspectable and
adjustable); (c) **inspectability** — because model and program are word
streams, "why did you route that?" is answerable by showing the winning
features, and "I see X but not Y" is a WordStream query, not a
confabulation. Refusal line (also the easter egg): *"I'm sorry, I can't do
that — yet."* Every future GHOST bundle must state how it preserves (a)–(c)
or strengthen them; a bundle that trades humility for capability is
rejected by default.

## 4. Dependency honesty (CAI point 1)
First Breath: dependency-free, provably (stdlib trainer; model ships as
words; no runtime NLP). The moment any successor needs richer language
handling, the bundle must name its choice explicitly — bundled
dictionary/grammar, small local model, or delegation to a Companion-side
engine — before implementation. No silent dependency creep into the
substrate side of the seam.

## 5. Bonsai contract slot (CAI point 3)
Named now, built later: substrate-GHOST exposes a back-end contract —
`classify(features) → (class, margin)` — for which the native forward pass
is the reference implementation. Bonsai (already running) may implement
the same contract as an optional back-end behind the same refusal
threshold and the same golden tests. Contract sketch lands with the GHOST
tab bundle; nothing in First Breath may assume the native model is the
only possible provider.

## 6. No-phone-home as ISA property (CAI point 4)
Current ground truth: the 5500FP emulator has **no network syscalls** —
the allow-list is the empty list, the strongest form of the guarantee.
Binding rule: any future network-capable syscall requires (i) a named
entry in a syscall allow-list compiled into the emulator, (ii) a KNOWN.md
entry, (iii) Stevo's explicit gate. "The substrate won't let us" is
thereby literal: the property lives in the ISA surface, not in policy.

## 7. HALT (adversary) — reserved
HALT (Hostile Agent Litmus Test) is the harness-side red-team persona
(B3). Out of First Breath's scope; its first duty when it lands is
attacking property 3 — trying to make GHOST route what it should refuse.

*Reference version 1.0 — amendments by Stevo's gate only. ⚓*
