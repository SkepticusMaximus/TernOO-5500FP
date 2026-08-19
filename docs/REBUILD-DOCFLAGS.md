# REBUILD DOCFLAGS — the documentation debt ledger

**Purpose (captain's order, 19-08-2026):** every doc-impacting shift made
during the DPG rebuild gets a line here AS IT HAPPENS, so the Documentation
tab port (deliberately LAST) and CAI's docs phase reconcile against a
ledger, not against memory. The comprehensive CAI handoff at the end of the
rebuild is written FROM this file.

Convention: code comments may carry `DOCFLAG:` markers; every marker gets a
line here. Newest at the bottom. Format: date · area · the shift · doc(s)
affected.

---

- 18-08 · architecture · **Both-faces doctrine**: flowcode.py (Tk) remains
  the working surface while flowcode_dpg.py + per-tab organ modules
  (flowcode_dpg_flow/gui/sheet…) grow to parity; organs REUSE flowcode.py's
  module-level classes headless (FCCanvas, brain, interpreter, compiler,
  sheet_formula) — one source of truth, no copies.
  → whitepaper architecture section, CAI-Shell-Tab-Skeleton note, README.
- 18-08 · benchmarks · reproducible from clean clone; workloads aligned +
  result-verified across all three emulators; **C-over-Python now 44–71×
  aligned** (old 16–34× was cousin workloads); NASM ~10–16× stands; "13–25×"
  Manus figure retired. → whitepaper performance section.
- 18-08 · spine · **C emulator = portable primary spine** (~9–14× over NASM,
  same unit/box); NASM = x86-64 showcase. → whitepaper, AE appendix.
- 18-08 · bridge · ternoo_bridge.py drives BOTH cores (backend="c"/"nasm");
  libternoo_c.so + Makefile target; NASM .so veneer bugs fixed
  (max_cycles, ternoo_load_word raw port). → P2PCP/AE docs mentioning the
  bridge.
- 18-08 · **ENCODING DIALECT FINDING** (ruling pending): C core = Manus
  clean-room format (6-trit opcode @18, unbiased regs R0..R40); NASM =
  faithful port of the house v0.1 6-field×4-trit format (op @20–23, biased
  regs, all 81). Canon two-level reading proposed (raw 6×4 ISA + 2+4+18
  OPCODE-word wrapper). POBOX letters 2026-08-18-2147 + 2026-08-19-1007.
  → Language Audit cross-check (CF5), whitepaper ISA section.
- 19-08 · naming · v0.3 code names the +− primary **OPEN_A** while the Manus
  thread's list says **OPCODE** in that region — naming discrepancy for the
  audit/ruling to settle. → Language Audit.
- 19-08 · GUI persistence · Tk `properties` are dicts {'name','value'};
  the DPG GUI organ briefly wrote [name, value] pairs (fixed; legacy pairs
  still read). Files saved by the DPG face in that window may carry pairs.
  → file-format policy doc if pairs ever surface.
- 19-08 · files · new config/state files: ~/.config/ternoo-flowcode-dpg.json
  (+ autosave.flow / autosave.gui rescue files, recovery-on-launch flow).
  → user-facing docs / help.
- 19-08 · UX doctrine · WYSIWYG widget-face renderer (one vocabulary,
  palette + canvas); **fixed-size chrome** rule (titlebars/scrollbars/row
  pitch don't scale with widget size — content does); stand-in until the
  CC-09 RNODE geometry organ renders canon shapes. → design docs, CC-09.
- 19-08 · Flow tab · DPG Flow executes via the SAME organs as Tk
  (interpreter walk, Stage-6 compile → C engine SDL); Load→EMU targets the
  NATIVE C core (Tk loads the Python CPU) — a capability DIFFERENCE between
  faces. Pocket scopes not yet ported in DPG. → Stage-6/7c docs.
- 19-08 · CLAUDE.md · tab list stale (says five tabs; canon is ten) and the
  word-format bracket "(T23 / T22–T19 / T18–T0)" is misleading (canon:
  T23–T22 · T21–T18 · T17–T0) — captain's own file, captain's hand.
- 19-08 · Sheet tab (DPG v1) · grid + formula bar editing, recalc via the
  shared sheet_formula module, number formats, names; regions/free cells
  are RENDERED + PRESERVED but not yet creatable/editable in DPG; no
  canvas zoom yet. → Stage-8 memo as-built notes.
- 19-08 · Connectors tab (DPG v1) · command tiles + typed pipes via the
  shared flowcode_commands registry; one-pipe-per-input replace semantics,
  red mismatch pipes (compile = hard gate) — Tk parity. NOT yet: REPL
  capture-to-pipeline, pocket interiors; no partial extension (.shell
  reserved, unemitted) so saves are .fc only. → Stage-9 docs as-built.
- 19-08 · Flow pocket scopes (DPG) · full 7c-4/-4b port: scope-local
  render+placement, 📦 top-right drill-in, breadcrumb bar (MainFlow › …),
  Esc up, cross-scope edges refused unless bound to a named port, Ports…
  editor (entry/exit lists on containers), scopes+ports round-trip .fc/.flow.
  Flow tab now has NO unported items. → 7c-4 docs as-built.
- 19-08 · Mesh-Chat tab (DPG) · IN-PANE conversation mount: the organ
  imports the standalone client AS A LIBRARY (its buyer, candidates,
  ChatStore, context builder — UI stays behind __main__), so tab + pane +
  standalone all share one core and one saved-chat store. The workshop
  (macros/forge/editor) remains standalone-only, via the Full-client
  button. Minimap now leashed to the Flow tab only. → client docs.
- 19-08 · Shell tab (DPG) · the REPL engine REUSED whole (flowcode_repl.Repl
  — registry pipelines executing on the C emulator via the shared compile
  path, fs commands, run file.t5asm) + registry browser + Capture→Connectors
  (text and visual faces of one pipeline). Native t5asm console restored —
  its tab branch had been silently swallowed by an earlier patch (regression
  window ~12:00–13:10 19-08, caught by review). Tk's staged-pipeline (Lingo
  three-pane) builder NOT yet ported. → Stage-9/DocPhase B2 notes.
- 19-08 · TEXT SERVICE (captain's standing order) · flowcode_dpg_clip.py:
  one clipboard layer app-wide (xclip/xsel → Tk read → DPG mirror + rescue
  file), Ctrl-sync making in-field Ctrl+C/X/V system-true, and a context-
  menu framework registered on every text surface (editor, shell REPL in/
  out, native console, sheet formula/name/GRID cells, mesh prompt/log).
  Sheet gains spreadsheet manners: click-and-TYPE (key-mapped; DPG has no
  char handler), F2 edits, Del clears. Text tab gains Ctrl+Z/Y ring undo.
  RULE GOING FORWARD: no new text surface ships without CLIP menus.
  → user-facing docs / help.
