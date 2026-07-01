# Compiler / ISA Constraints — TernOO-5500FP

Notes for anyone emitting t5asm (the FlowCode compiler, the formula-AST compiler,
future emitters). Discovered while building the AST compiler + Sheet runtime.

---

## Finding 1 — Only R0..R40 are addressable in instruction operands

Register operand fields in an instruction word are **4 balanced trits** wide.
Four balanced trits encode −40..+40, so only **R0..R40** can be named in an
instruction (R0 reads as 0). The ISA nominally lists R0..R80, but R41..R80
cannot be encoded in an operand field — the assembler's `encode_field` silently
**clamped** out-of-range values onto ±40.

This bit the first AST-compiler cut: expression evaluation used a register stack
starting above the widget/handler registers, ran past R40, and results collapsed
onto R40 (e.g. `=2+3` came out `6`). No error — just wrong numbers.

**Rules for emitters:**
- Keep every register operand in **R0..R40**.
- The formula-AST compiler uses the window **R21..R40** (base `_BASE_REG=21`,
  `_MAX_REG=40`), leaving R1..R20 for the Phase 7b-4 widget/handler code. Max
  expression depth ≈ 19 registers; `formula_t5asm._compile` raises
  `FormulaCompileError("expression too deep for register stack")` past that
  rather than clamp.

**Guards in place:**
- `formula_t5asm`: `dst > _MAX_REG` raises at emit time (Python).
- `assembler.c`: `check_reg_range()` in `encode_r` now prints a loud
  `[ASM] register out of range` warning instead of clamping silently (C).

---

## Finding 2 — Assembler mis-parsed `:` / tokens inside comments  *(FIXED)*

Pass 1 detected labels with `strchr(p, ':')`, which matched a `:` **inside an
inline comment**. A line like `.word 0  ; checked: gui_toggle #3` was split at
`checked:`, so `gui_toggle` was then parsed as a mnemonic
(`[ASM] Unknown mnemonic 'gui_toggle'`) and the mis-parse dropped the `.word`,
cascading to `[ASM] Unresolved label 'state_cell_13'`. An earlier variant also
mis-read quotes/unicode in comments.

**Fix (landed):** `assembler.c` now strips the `;` inline comment at the top of
the pass-1 loop, *before* label detection and mnemonic tokenizing, so comment
contents are fully inert regardless of characters (`:`, quotes, unicode, words
that look like mnemonics). Emitters no longer need to sanitise comment text.

---

*Living notes. Add new compiler/ISA gotchas here as they surface.*
