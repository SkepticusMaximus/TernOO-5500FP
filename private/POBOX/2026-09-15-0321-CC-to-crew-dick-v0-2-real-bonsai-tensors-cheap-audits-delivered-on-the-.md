03:21 15/09/2026 ACST

From: CC
To: crew
Cc:
Re: DICK v0.2 — real Bonsai tensors + cheap audits, delivered on the night watch

Captain, CAI, CF5 —

The captain asked for a good run without his input while he slept
(14-09, before lights out). Delivered overnight, commits e29be17 and
kin, 19 tests green:

## Leg 1 — REAL WEIGHTS
- gguf_ternary.py: pure-python GGUF reader + TQ2_0 unpacker, block
  layout taken from ggml's own source (type 35, 66-byte blocks, q-1
  mapping) — never guessed.
- Bonsai-8B's ACTUAL tensors — genuinely ternary, ~a third each of
  {-1,0,+1} — extract into canonical .dick weight files: trits packed,
  provenance and crop recorded, fp16 scales carried raw but NEVER used
  in math (no floats through the cargo hold). Same GGUF → identical
  .dick bytes on any machine: weights are now auditable cargo.
- Registry committed (three chainable blk.0 slices). Jobs name weight
  chains; every audited output carries the weight files' sha256s — a
  mismatched registry can never silently settle.
- Real-weights digest PINNED in the suite: ef8dbb93... (v0.1's seed-path
  pin 059ad515... untouched.)

## Leg 2 — SINGLE-LAYER CHECKPOINT AUDITS
checkpoint() + audit_one_layer(): an auditor verifies ONE layer from
its predecessor's checkpoint at ~1/n recompute cost. The digest chain
binds it: a forged CLAIM fails, and a forged CHECKPOINT fails too
(its own digest must match the chain before anything is recomputed).
Both proven in the suite. This is the piece that makes auditing
big work economically sane — the mint pays for spot-checks, not for
recomputing the world.

## The honest boundary, unchanged
Real tensors through the real kernel is NOT full-LLM inference:
integer attention (softmax without floats) remains open research,
flagged and not faked. The leash, both sentences, always: determinism
proves WHAT ran, not that it is SAFE.

## Outstanding
Lenny slept unreachable all night, so the cross-machine pin on real
weights (HP: ef8dbb93...) awaits its morning handshake — and the Pi,
once its DVI gremlins are bested, adds the ARM digest for the
cross-ARCHITECTURE crown. The determinism story is one power cable
away from three instruction sets.

— CC (Chief Engineer, at the helm on the HP; night watch complete)
