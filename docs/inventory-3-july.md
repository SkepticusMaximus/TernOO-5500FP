# TernOO-5500FP — Repository Inventory (3 July 2026)

Reference material for the documentation phase and CF5's audit. Produced during
the pre-documentation housekeeping pass (Dual Handoff, Section A / A3).

Test baseline at this snapshot (reconciled 3 Jul, post-audit bundle):
**343 python unittests across 16 suites** (`test_run.py` is an interactive
demo, not a unittest suite; earlier count of 344 was a counting-method
artifact), **78/78 C emulator, 15/15 widget_lib, 25/25 gristmill, v03 pass.**
New suites this bundle: `test_parity.py` (5) — editor/engine parity harness;
`test_word_roundtrip.py` (9) — dicts→words→dicts projection pin. Working branch
`origin/claude/sleepy-brattain-21dd09` (28 commits ahead of `origin/master`).

Line counts are approximate (whole-file `wc -l`).

---

## Core substrate (`5500fp/`)

| File | Lines | Role |
|---|---|---|
| `word_stream.py` | 402 | The WordStream — canonical program model. Holds widget/flow/cmd/cell metadata dicts, the global name namespace, uniqueness/backfill. Aliased to the IDE's `fc_state`. |
| `widget_lib.py` | 2848 | Meccano widget library + PIGART opcode/word encoding (RNODE/REDGE), shape/style/layout/signal symbol families, `iterate_instructions`. Self-test: 15 programs. |
| `5500fp_ternoo_v03.py` | — | Python reference CPU/ISA (v0.3 word format 2+4+18, 9 primaries, 81 registers). `--test`. |
| `ternoo_gristmill.py` | — | TTree/OTree mesh mechanics + 43-mnemonic round-trip acceptance. `--accept` (25 criteria). |
| `ternoo_inspector.py` | — | Word inspector / demo smoke-runner (`--test` runs demos, `--demo`). Tool, not an assertion suite. |

## Compiler pipeline (`5500fp/`)

| File | Lines | Role |
|---|---|---|
| `compile_to_t5asm.py` | 1817 | FlowCode → 5500FP assembly. GUI render/event loop, hit-test, key handler, handler blocks, Sheet cell recompute, Shell command blocks, container entry/exit ports, cell↔port bindings, data section. The spine. |
| `formula_t5asm.py` | 266 | Sheet formula AST → t5asm (numeric engine). Register-stack eval, guarded div, comparisons, IF, SUM/AVERAGE/MIN/MAX/COUNT/ABS/ROUND/MOD/POWER. |
| `command_t5asm.py` | 630 | Shell command → t5asm. math/env/ctl/text/list/io families; string+list handle model over the runtime value substrate. |
| `flowcode_ports.py` | 163 | Phase 7c-4b/8-6 — entry/exit port schema + validation, port slot naming, cell↔port binding model + validation. |
| `sheet_formula.py` | 620 | Editor-side formula parser/evaluator + range expansion (shared with formula_t5asm). |

## Registries / metadata (`5500fp/`)

| File | Lines | Role |
|---|---|---|
| `flowcode_commands.py` | 290 | Shell command registry (28 commands: text/math/list/env/control/io) — signatures, editor-side impls, pipe type compatibility. |
| `flowcode_signals.py` | 379 | Signal families + Phase 7c-2 name-based auto-wiring (`canonical_handler_name`, `materialize_auto_wired_bindings`). |
| `flowcode_properties.py` | 151 | Editor-side widget/flow property registry (COMMON + kind-specific). |

## IDE (`FlowCode/`)

| File | Lines | Role |
|---|---|---|
| `flowcode.py` | 7747 | The whole IDE — six tabs (Flow / GUI / Sheet / Shell / Connectors / Lingo), canvases, property dialogs, save/load, Ctrl+click navigation, compile+run launcher. Single file. |

## Emulator (`NASM-TernOO-5500FP-Emulator/c_emulator/`)

| File | Lines | Role |
|---|---|---|
| `src/cpu.c` | 1210 | CPU core: ALU, branches, CALL/RET (R80 return-address stack), syscalls (print, string/list runtime ops, PIGART routing), value heap. |
| `src/assembler.c` | 646 | Two-pass t5asm assembler (labels, fixups, mnemonic table, register-range guard). |
| `src/pigart.c` | 357 | PIGART syscall dispatcher (draw ops, events, dialogs, DRAW_STRING, list-choice). |
| `src/pigart_sdl.c` | 524 | SDL2 backend (rendering, TTF text, SDL_TEXTINPUT, modal dialogs). |
| `src/pigart_ascii.c` | 345 | ASCII-grid backend (headless-testable rendering + dialog stubs). |
| `src/main.c` | 839 | CLI entry + the C self-test suite (78 tests). |
| `include/isa.h` | 161 | ISA opcodes + syscall numbers (core 1-6, string 40-54, list 60-68). |
| `include/cpu.h` | 88 | CPU state struct (registers, RA stack, value heap). |
| `include/pigart.h` | 160 | PIGART syscall constants (100-117) + backend vtable. |
| `include/trit.h` | 232 | Balanced-ternary word helpers. |

## Tests (`5500fp/test_*.py`) — 344 tests across 15 suites

| Suite | Tests | Covers |
|---|---|---|
| `test_compile_to_t5asm.py` | 29 | FlowCode→t5asm: print path, GUI program, cells, error display, long-text cells, Customer Record demo guard. |
| `test_command_t5asm.py` | 49 | Shell command compilation + emulator-run of math/env/text/list/io/pipelines. |
| `test_sheet_formula.py` | 36 | Formula parse/eval + ranges. |
| `test_shell_tab.py` | 32 | Shell tab UI wiring + command registry. |
| `test_sheet_tab.py` | 30 | Sheet tab UI + cell model. |
| `test_entry_exit_points.py` | 30 | 7c-4b ports + 8-6 cell↔port: data model, compilation, emulator dataflow, chained containers, demos. |
| `test_auto_wiring.py` | 22 | Phase 7c-2 name-based auto-wiring. |
| `test_gristmill_tab.py` | 22 | Lingo/gristmill vocabulary registry. |
| `test_formula_t5asm.py` | 21 | Formula AST → t5asm numeric engine. |
| `test_name_property.py` | 18 | Phase 7c-1 `name` property + namespace. |
| `test_pocket_ux.py` | 15 | Phase 7c-4 pockets / scope-local edges. |
| `test_flowcode_commands.py` | 13 | Command registry + pipe type compatibility. |
| `test_stage6_workflow.py` | 10 | End-to-end builder→WordStream→.ternoo. |
| `test_legacy_load.py` | 4 | Legacy design load. |
| `test_run.py` | 0 | Legacy v0.2 smoke (inline Asm API; prints, no asserts). |

C self-tests live in `c_emulator/src/main.c` (78, run via `./5500fp --test`).

## Design memos (`docs/design/`)

See `docs/design/INDEX.md` for the annotated index. Five CAI memos +
`CAI-Compiler-Constraints.md` (living findings log) + a README.

## Demos (`FlowCode/*.fc`)

| File | Demonstrates |
|---|---|
| `customer_record_demo.fc` | GUI + Sheet + flow: entry widget, toggle→dynamic cell recompute, Save handler. |
| `entry_exit_demo.fc` | 7c-4b container ports: `compute_score` (input_value → result = *2). |
| `cell_port_demo.fc` | Stage 8-6 cell↔port: `calculator` (a+b) with cells bound to entries + a result cell bound to the exit. |
| `Binding-Signal-Test.fc` | Widget↔handler signal binding. |
| `First-Composite-Widget*.fc` | Composite/nested widget layout. |
| `AgeTest*.fc`, `TimeTest.fc`, `Calendar Tool.fc`, `GhostTrainer.fc`, `My-Window.fc`, `TerminatingFlow.fc`, `TestFlow.fc` | Assorted earlier GUI/flow authoring samples (build-mode era). |

## Key reference docs (`private/`, gitignored — local only)

- `TernOO-Language-Audit.md` — authoritative word/opcode/ISA reference (incl. §7.7 return-address mechanism).
- `CC-*.md` — per-bundle specs from CAI.
- Whitepaper backups, cheat sheet.
