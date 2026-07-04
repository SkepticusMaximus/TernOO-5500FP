# DESIGN — GHOST v0.5 "First Breath" (micro-model, native forward pass)

**CF5, 4 July 2026. Campaign opener of the triad (GHOST → Logic → GristMill).
Scope is a scalpel: the smallest model that legitimately breathes.**

## The claim being built
A ternary-weight neural model whose **weights are TernOO NEURAL_CONNECTION
words** and whose **forward pass executes natively on the 5500FP emulator**
in plain ALU t5asm — no host-side inference anywhere. Demo: at the FlowCode
prompt, `ghost "make this text loud"` → the model classifies intent →
routes to `text_upper` → the command runs. The machine is asked in English
and answers in trits.

## Architecture (deliberately tiny)
Input: text → character-trigram hash → **81 ternary features** {−1,0,+1}
(81 = 3⁴, and exactly the register count — the poetry is free).
Hidden: **27 units**, integer accumulate, clip-ReLU. Output: one logit per
routable registry command (~26 runnable + a `none` class). Weights:
**9-level ternary** {−4..+4} (two trits — the v0.3 NEURAL encoding, matching
the illustrated guide's "9-level weight multiplication" claim). Total ≈
81×27 + 27×27 ≈ 2,916 weight words — comfortably a `.word` data section and
comfortably a word stream.

## Pipeline
1. `ghost_train.py` (host-side, stdlib only — no numpy, honouring the
   no-dependencies claim): synthetic phrase corpus from per-command
   templates ("upper/shout/loud…" → text_upper, etc.), integer training
   with straight-through 9-level quantization, deterministic seed.
2. Export: weights → NEURAL_CONNECTION words (identity + rendering: the
   model IS inspectable in the stream) **and** t5asm data section.
3. `ghost_forward.t5asm` (generated): hash-features already computed
   host-side v0 — NO: features too are computed on-emulator from the input
   buffer (char loop → trigram hash mod 81 → ±1 bucket), so the entire
   inference path is native. Two nested MAC loops, argmax, print class id.
4. REPL command `ghost "<text>"`: engine writes input buffer, runs the
   compiled forward pass on the emulator, maps class id → registry command,
   echoes the routing, optionally executes.
5. `test_ghost.py`: golden — emulator forward pass output == host reference
   implementation output over a fixed eval set, plus accuracy floor
   (≥90% on held-out templates) so retraining regressions are loud.

## Register/immediate law compliance (learned the hard way)
R0–R40 only; LI ≤ ±29524; large constants composed or loaded from data.
Cycle budget: 81×27 + 27×27 MACs ≈ 3k MACs ≈ 30k instructions per query —
milliseconds. HALT (the adversary) is out of scope for v0.5; the training
harness hook lands with the GHOST tab later.

## Seasoning directive (standing, per the captain)
This geekware is to be liberally peppered with geek humour and pop-culture
homage for Our People — Adams and the Pythons enshrined as kin (`.fish`
protocol and `ni` command respectively, the misattribution redeemed), HAL's
lineage reserved for HALT, and future eggs welcome wherever they don't cost
correctness. First breath's own egg: the model's `none` class replies
"I'm sorry, I can't do that — yet."
