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
- 19-08 · TED (Text tab) + native glyph plane · editor gains find/replace,
  live counts, Ctrl+Z/Y; the NATIVE GLYPH PLANE pane encodes text as XYZ
  glyph words per the CAPTURED park-session design (private/DeepAI-Consult-
  Glyph-Word-Brief.md) — the "undocumented" charmap work was documented
  there all along. FORMATIVE assumptions marked in-app: tribble order
  X-high/Z-low, space=caseless 27, digits 30–39, punct 40+, Z=0. Rulings
  Q1–Q6 requested from CF5 (POBOX). v0.3's STRING_TERNARY (+1 @T19) is the
  ruled hook this plugs into. → glyph-plane canon doc (CF5 charter).
- 19-08 · glyph plane · CF5 recovery (POBOX 1956): the XYZ FRAME IS
  RATIFIED CANON (Ted builds on real canon); foundational law recovered:
  LEFT-TO-RIGHT NON-COMMUTATIVE CONTEXT SENSITIVITY (a defining trit may
  condition trits to its right, never vice versa); chalk voice (Professor)
  / ink voice (GHOST) canon; house font 51+ glyphs (⸮ and ~ founding
  residents). The SIX formative points remain the CAPTAIN'S to rule (or
  the recovered park transcript's). DeepAI brief now COMMITTED (it was
  on disk but untracked — invisible to crew seats). Y-field wording
  variance between the recovery ("identity tag + font index") and the
  brief ("case trit + ordinal"; font in Z) — transcript to settle.
  → glyph canon doc.

## 2026-08-19 — Babble-Fish tab live on the DPG face
- `FlowCode/flowcode_dpg_babble.py`: the Babble-Fish organ. Both Tk views
  ported: VOCABULARY (reuses `gristmill_tab_view.build_vocabulary_data` +
  `build_program_data` — the pure no-tkinter builders — for the static
  registry [Opcodes/Shapes/Styles/Layouts/Signals] and the live Program
  tree) and TRANSLATOR (reuses `flowcode_lingo_translate.render` +
  `flowcode_dialect.project`; live model assembled exactly like Tk's
  `_dialect_model` from the Flow/GUI/Sheet/Connectors organs).
- Translator layout differs from Tk deliberately: left pane is ALWAYS the
  canonical FlowCode dialect, right pane the picked tongue (Python/Java/
  VB/C) — the split view is the default, not a toggle. Doc screenshots of
  the Lingo tab should use the DPG layout when the handoff is written.
- Word spans in the vocabulary Program tree read as "(dump the stream on
  Flow to map)" when no stream has been built — the DPG face has no
  always-live WordStream subscription yet (Tk subscribes on_stream_change).
  Flag for the parity ledger, not user-facing docs.

## 2026-08-19 — Academy tab live on the DPG face
- `FlowCode/flowcode_dpg_academy.py`: the classroom organ. ALL engines
  reused untouched: ghost_harness (router/!learn/train/majors/.chat IO),
  ghost_bonsai (BonsaiProcess + consent ceremony + consistency gate),
  ghost_tab_view's pure presenters + frozen art-contract constants,
  ternoo_glyph (house font codec + O4 ledger), glyph_canvas pure layout.
- NEW DpgGlyphSurface: chalk/ink voices re-rendered on a drawlist from
  glyph_canvas.plan_layout plans; same deterministic jitter recipe
  (line*1009+ox) so chalk never shimmers. DIFFERENCE vs Tk: curved
  strokes draw as raw polylines (no spline smoothing in drawlists) —
  doc screenshots of board writing should come from whichever face ships
  them consistently. Panes are fixed-height (no Tk relative reflow).
- Backstage is a FLOATING panel on the DPG face (Tk: in-tab 30% column).
  Same corridor rules hold by construction: never touches harness.turns,
  teaching refused, own log files.
- Satellites ported: Curriculum, Brain scan (NEURAL_CONNECTION words),
  Chars (house-font specimen to the board), ASCII/Unicode→glyph-string
  Translate window (both voices + O4 unknown reporting).
- Bonsai discovery is SKIPPED under SMOKE (gates never launch a model
  subprocess); CLICK-PATH sweep now also excludes "Train" buttons — a
  swept real training thread killed at app exit could truncate the
  node-private brain file.

## 2026-08-19 — Mesh-Chat tab: full client IN-PANE (captain's ruling)
- Stevo's review: the conversation-only pane + "Full client" launcher
  button was "inconsistent, tacked on, an arbitrary extra step". Ruling:
  the tab IS the client, built into the parent interface.
- `flowcode_dpg_mesh.py` rebuilt: it now constructs the STANDALONE'S OWN
  tag layout in-pane (workshop: Macros/Forge/Editor+reviews; chat column
  with attach/saved-chat management/export) and delegates every action to
  mesh_chat_dpg's module functions — zero forked logic. Draggable seams
  (panel/ask-box/notes) reused and persisted to the SHARED client config.
- The launcher button is GONE. Not wired from the standalone: its global
  zoom/clipboard/right-click layers (FlowCode's shell + CLIP own those),
  menu-bar chrome, and the "FlowCode taste" node demo (this IS FlowCode).
- Docs implication: Mesh-Chat tab docs should show the full in-pane
  client; the standalone remains for solo use (Prof's box) — same
  codebase, same chats, same macros, two mounts.

## 2026-08-19 — GUI tab leftovers: layout engine, signals panel, Import
- LAYOUT ENGINE live: hbox/vbox/grid/stacked place children in real time
  (drop into a container, resize it, or switch layout_mode — children
  flow). Same arithmetic as Tk guic_apply_layout, absolute-coord port.
  Stacked places ALL pages on the content area (Tk draws only the first)
  — visually equivalent, ledger-noted.
- CROSS-FACE FIDELITY FIX: parented widgets now save/load as CENTRE-
  OFFSETS from the parent centre (the Tk schema convention). Before
  this, nested designs saved by the DPG face opened scattered in Tk and
  vice versa. .gui files saved by the DPG face BEFORE 19-08 with nested
  children carry absolute child coords and will shift once on re-open.
- Phase 7c-2 Signals → handlers panel ported (read-only, naming IS the
  wiring): per-signal canonical handler name + state (manual / ✓ wired /
  named-not-entry / unwired). Wired-state honours the dump-time entry
  synthesis rule (first terminator when none explicit) — kinder than
  Tk's strict is_entry check and truthful to what compile does.
- Import into GUI... (File menu): merge another .gui/.fc — fresh ids,
  parent links remapped, roots nudged +30, layouts re-flowed.
- Children order inside containers is id-order (the organ keeps no
  child_order map yet) — Tk preserves insertion order. Parity note.
- REMAINING GUI parity item (unchanged): RNODE widget geometry
  rendering; the parametric WYSIWYG faces carry the standard meanwhile.
