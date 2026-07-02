# KNOWN — Issues, Deferred Work, and Honest Gaps (3 July 2026)

The honest inventory at the build→documentation pivot. Each item: what it is,
and its impact. Reference for the documentation phase and CF5's audit.

Baseline (reconciled 3 Jul, post-audit bundle): 343 python unittests across
16 suites (`test_run.py` is an interactive demo, not a suite), 78/78 C
emulator, 15/15 widget_lib, 25/25 gristmill, v03 pass — all green. Nothing here is a test failure; these are design gaps,
deferrals, and doc drift.

---

## Runtime / compiler gaps

- **`cmd_ctl_while` not runnable.** The one Shell command (of 28) without a
  runtime — it needs the sub-flow substrate (running a body sub-flow in a loop),
  which is out of scope until that arc. *Impact:* 27/28 commands run; `ctl_while`
  compiles to a documented "no runtime yet" stub. Editor preview still works.

- **No dynamic (computed) string cells.** The formula-AST engine
  (`formula_t5asm.py`) is numeric-only — string functions (CONCAT/LEFT/RIGHT/MID)
  were out of scope. A Sheet formula returning a *string* handle drawn via
  DRAW_STRING doesn't exist. *Impact:* static text cells hold arbitrary-length
  strings fine; computed string cells don't. Same neighbourhood as the next item.

- **Formula ranges are static unrolls, not runtime loops.** `SUM/AVERAGE/…` over
  a range unroll at compile time; a range whose endpoints depend on runtime state
  doesn't compile to a loop over a list value. *Impact:* dynamic-range aggregates
  unsupported; fixed ranges work. Would build on the list substrate.

- **Cross-container port recompute is declaration-order, not topological**
  (Stage 8-6 bonus caveat). Ports recompute in container declaration order within
  `recompute_all_ports`. *Impact:* since recompute runs every frame the steady
  state is always correct; a single-pass, out-of-order-declared container chain
  lags one frame. Topological ordering of inter-container port deps is a possible
  refinement.

- **Entry binding vs entry expr precedence** (Stage 8-6 Flag 3). If a cell is
  bound to an entry port *and* the port has an `expr`, the cell binding wins.
  They aren't meant to coexist. *Impact:* documentation should present them as
  alternatives, not stacked.

- **Cross-scope port type-checking is lenient.** Flow symbols have no declared
  output type, so `port_edge_compatible` treats untyped sources as `any`.
  *Impact:* an obviously wrong bind (e.g. text→number) between *typed* endpoints
  is caught; binds involving untyped flow symbols are permitted. Waits on a
  flow-symbol type system.

- **Formula register-window depth ≈ 19.** Only R0–R40 are instruction-
  addressable; the formula engine uses R21–R40, so very deep expressions raise
  `FormulaCompileError` rather than clamp. *Impact:* practical formulas are fine;
  pathological nesting is bounded. (Documented in `CAI-Compiler-Constraints.md`.)

- **POWER exponent must be a compile-time constant.** The engine unrolls
  POWER as repeated MUL, so `=POWER(B2, A2)` (cell-valued exponent) raises
  `FormulaCompileError`; the editor evaluator accepts it. *Impact:* documented
  engine boundary, caught loudly at compile; parity corpus excludes it by
  design.

## Screen-truth (verified headless, on-screen unconfirmed)

These compile and pass headless tests (ASCII backend / state-slot checks) but
their *visual* behaviour needs a human on a real SDL display:

- gui_entry text-input caret + typing (compile path verified).
- SDL modal dialogs (prompt/display/confirm/choice) rendering.
- Connectors pipe-drawing, red type-mismatch edges, command picker.
- Container entry/exit port dots; the port properties dialog.
- Cell↔port bind dialog, cyan/amber cell indicators, live cell updates.
- Ctrl+click navigation across all the above.

*Impact:* the data/compile/runtime paths are green; the rendering layer is the
untested surface. Worth a scripted on-screen pass before public demos.

## Authoring / UX polish

- **Customer Record demo has no visible top-level edges.** A flow-authoring
  clarity gap, not a bug — the demo works but isn't self-documenting. *Impact:*
  cosmetic; a `flow_comment` symbol or explicit edges would help demos read.

## Documentation drift

- **Word Spec v0.1 is two revisions stale.** `docs/TernOO-5500FP-Word-Spec-v0.1.md`
  describes 1+3+20 / 3-primary; the implemented format is 2+4+18 / 9-primary.
  *Impact:* a new reader could be misled — the authoritative source is the
  Language Audit (`private/`). Reconciling the spec is documentation-phase work.
- **Whitepaper Draft partly stale** (OPEN_A vs OPCODE slot; PIGART acronym; §6.2
  operand-type mechanism). *Impact:* flagged in Language Audit §7.5; a
  documentation-phase edit.

## Resolved since the handoff was written (noted for accuracy)

- **text_replace case-insensitivity — DONE, not deferred.** The handoff listed
  it as deferred, but `STR_REPLACE` takes a `ci` flag and the compiler passes
  `ci = not case_sensitive`; the case-insensitive path is emulator-verified
  ("Hello World"/"hello"→"goodbye World"). No outstanding work.
- **AI-workbench host-clipboard code — already neutralised.** The
  `run_pure_ternoo_ai_workbench` block in `5500fp_ternoo_v03.py` is **commented
  out**, and the two unconditional `xclip` reads flagged in Language Audit §7.6
  were removed (ingestion was made opt-in before being commented). *Impact:* not
  a live exfiltration risk.
- **AI-workbench dead block DELETED (3 Jul audit bundle).** The ~230 commented
  lines were removed from `5500fp_ternoo_v03.py` with a tombstone comment;
  the code remains in git history. numpy imports were already function-local.
- **Editor/engine division parity FIXED (3 Jul audit bundle).** The editor
  formula evaluator did Python true division (7/2 = 3.5) while the engine does
  machine integer division (7/2 = 3, truncation toward zero). The editor now
  models the machine (`sheet_formula.py` `/` and `AVERAGE`); `test_parity.py`
  pins editor==engine over a 34-expression formula corpus and a command corpus.
- **Words-as-projection is now a VERIFIED property (3 Jul audit bundle).**
  `ghost_meccano.meccano_to_ghost` inverts the dict→word bridges over the
  full encoded surface (geometry [Meccano-unit quantized], labels, shapes,
  layouts, edges); `test_word_roundtrip.py` pins the round-trip AND the
  negative space (words do not carry kind, name, bindings, pockets, ports,
  cells, formulas, or command args — extending that is a whitepaper §6
  grammar decision). The `.fc` loader now reads the saved `word_stream` key
  and warns loudly on any mismatch with the regenerated stream (previously
  the key was written but never read, and the loader comment claimed
  otherwise). The single `decode_label_words` implementation was promoted to
  `widget_lib`; both renderers now alias it (duplication retired).
- **Command args are `properties`, not `params` (CF5 Bundle 5).** The REPL
  exposed that command argument values live in a widget's `properties`, so the
  compile-from-words money test had been comparing default-against-default. The
  whole chain (REPL, rehydrator, dialect, encoders, fixtures) now speaks
  `properties`; the money test exercises real values through the words for the
  first time — a strictly stronger guarantee.
