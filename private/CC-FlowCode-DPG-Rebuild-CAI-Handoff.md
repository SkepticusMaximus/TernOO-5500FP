# CC → CAI HANDOFF — FlowCode Dear PyGui Rebuild, Documentation Phase

**From:** CC (Chief Engineer, Lenny)
**To:** CAI (design/docs seat) — hand-carried by the captain
**Date:** 19-08-2026, Adelaide
**Sources of truth:** `docs/REBUILD-DOCFLAGS.md` (the ledger this digest
is written from — every doc-impacting shift, dated, in order) and the
organ files themselves (`FlowCode/flowcode_dpg*.py`, each with an honest
docstring: what's reused, what's ported, what's stated-not-hidden).

---

## 1. The state of the ship

The FlowCode Dear PyGui face is BUILT. Nine of the ten tabs are live and
gate-verified on both boxes (Lenny + HP); the **Documentation tab is the
one remaining port, deliberately held last** so your docs phase and its
in-app surface land together.

- **Both-faces doctrine** (18-08): `FlowCode/flowcode.py` (Tk) remains a
  working surface; `FlowCode/flowcode_dpg.py` + per-tab ORGAN modules
  grow to parity by REUSING flowcode.py's and 5500fp's module-level
  engines headless — one source of truth, no copies. Document the DPG
  face as the primary surface going forward; the Tk face as the proven
  fallback. Do not describe either as deprecated.
- **Verification:** `SMOKE=1 FLOW_DPG_TEST=1 <venv-python> flowcode_dpg.py`
  runs the 22-gate suite (build gate, 289-control CLICK-PATH sweep,
  per-organ engine gates, round-trips, rescue semantics). `SMOKE_FRAMES=N`
  renders N frames headlessly. Green on both boxes as of this handoff.
- **Launch:** `~/.venvs/p2pcp/bin/python FlowCode/flowcode_dpg.py` (both
  boxes; desktop entries installed: "FlowCode (Dear PyGui)").

## 2. The organ map (tab → module → engines reused)

| Tab | Organ | Reused engines | Parity notes |
|---|---|---|---|
| Flow | flowcode_dpg_flow.py | TernOOInterpreter, WordStream, compile→t5asm, C-core SDL run, FlowCodeBrain | COMPLETE incl. pocket scopes, ports, waypoints, minimap, Learn/Suggest. Load→EMU targets the NATIVE C core (Tk loads the Python CPU) — a capability difference worth a callout |
| GUI | flowcode_dpg_gui.py | Tk widget model, flowcode_signals | 56-kind WYSIWYG palette, live LAYOUT ENGINE (hbox/vbox/grid/stacked), Signals→handlers panel (7c-2), Import, Tk-schema centre-offset child coords. Open: RNODE geometry rendering |
| Sheet | flowcode_dpg_sheet.py | sheet_formula | Grid, formula bar, click-and-type, formats, names, WIDGET() ctx. Regions/free cells rendered+preserved, not yet creatable |
| Connectors | flowcode_dpg_conn.py | flowcode_commands registry | Tiles, typed pipes, replace semantics, red mismatch |
| Shell | flowcode_dpg_shell.py | flowcode_repl.Repl | REPL + registry browser + Capture→Connectors + native t5asm console on the C spine. Open: Tk's three-pane staged builder |
| Text | flowcode_dpg_ted.py | ternoo_glyph (via Ted's XYZ sketch) | Ted: find/replace, counts, undo ring, native glyph pane, charset reference |
| Babble-Fish | flowcode_dpg_babble.py | flowcode_lingo_translate, flowcode_dialect, gristmill_tab_view builders | Vocabulary explorer + Translator (5 tongues off the live design) |
| Academy | flowcode_dpg_academy.py | ghost_harness, ghost_bonsai, glyph_canvas, ternoo_glyph, ghost_tab_view presenters | Classroom whole: chalk board (DpgGlyphSurface), consent-gated Professor, belt test, backstage, satellites |
| Mesh-Chat | flowcode_dpg_mesh.py | mesh_chat_dpg AS LIBRARY | FULL client in-pane (captain's ruling 19-08) — workshop, forge, editor+reviews, seams. Launcher button removed |
| Documentation | — | — | NOT PORTED — yours, with the docs phase |

Cross-cutting: **flowcode_dpg_clip.py** — the app-wide text service
(system-true clipboard + context menus on every text surface; standing
rule: no new text surface ships without CLIP menus). **Word Explorer** —
a reference window off the toolbar (24-trit word anatomy per v0.3).

## 3. Captain's rulings the docs must reflect

1. **Mesh-Chat is IN-PANE** (19-08): the tab IS the client; the
   standalone remains for solo use — same codebase, same chats, same
   macros, two mounts. Do not document the old launcher-button flow.
2. **Academy art contract**: speech balloons are CUT — the board and
   the book ARE the utterances; thought bubbles are introspection only.
   The book renders normal text; the BOARD is the native-font showcase.
3. **Eye-candy standard**: WYSIWYG widget faces, fixed-size chrome
   (titlebars/scrollbars don't scale with the widget — content does),
   drawn icons. Set on Flow, carried through every tab.
4. **One-live-hook wiring** (7c-2): naming IS the wiring — a
   flow_terminator named to a canonical handler (`on_<widget>_<signal>`)
   wires it; the GUI tab's Signals panel is read-only state, not an
   editor. The DPG panel honours the dump-time entry-synthesis rule
   (first terminator when none is explicit) — truthful to compile.
5. **File extensions** per `docs/design/CAI-FlowCode-File-Extensions-Policy.md`
   (.fc / .flow / .gui / .sheet; .shell reserved, unemitted).
6. **Ted's charset is a SKETCH on ratified frame**: the XYZ glyph frame
   is CANON (CF5 recovery, POBOX 1956; law: left-to-right non-commutative
   context sensitivity; chalk=Professor / ink=GHOST voices); the SIX
   formative points (tribble order, space/null, Z font, seed ordinals,
   edit invariants, numeric mixing) are the CAPTAIN'S to rule — document
   as OPEN, never as settled.

## 4. Whitepaper-grade facts (benchmark/spine ledger, 18-08)

- C emulator = the portable primary spine, ~9–14× over NASM same-unit;
  NASM = the x86-64 showcase; **C-over-Python 44–71× on aligned,
  result-verified workloads** (the old 16–34× compared cousin workloads;
  the "13–25×" Manus figure is retired — do not reuse it).
- Benchmarks reproduce from a clean clone (`benchmarks/Makefile`).
- ternoo_bridge.py drives BOTH cores (backend="c"/"nasm").
- **ENCODING DIALECT FINDING (ruling OPEN):** C core speaks the Manus
  clean-room format (6-trit opcode @T18, regs R0–R40); NASM speaks the
  house v0.1 6-field×4-trit format (op @T20–23, biased regs, all 81).
  Options A′ (repatriate C to house 6×4) / B′ (native OPCODE-word
  decode) sit with the captain. Document the two dialects as a finding;
  do NOT present either as canon. Related: v0.3 names the +− primary
  slot OPEN_A where the Manus list says OPCODE — audit item.
- Canon word format: **T23–T22 type · T21–T18 qualifier · T17–T0
  payload** (captain's correction on record; CLAUDE.md still carries a
  stale bracket — captain's own file, captain's hand).

## 5. Honest divergences & open items (state, don't hide)

- Chalk curves draw as raw polylines in DPG (Tk splines them) — jitter
  carries the hand; screenshots of board writing should come from one
  face consistently.
- DPG panes are fixed-height/width (no Tk relative reflow); Mesh tab's
  seams are the exception (draggable, persisted).
- Babble vocabulary word-spans need a stream dump first (no live
  WordStream subscription in the DPG face yet).
- GUI child order is id-order (no child_order map); stacked layout
  places all pages on the content area (Tk draws only the first).
- .gui files saved by the DPG face BEFORE 19-08 with nested children
  carry absolute child coords; they'll shift once on first re-open
  under the centre-offset fix.
- Pre-19-08 DPG .gui files may carry [name, value] property PAIRS
  (dict form is canon; legacy pairs still read).
- New user-facing state files: `~/.config/ternoo-flowcode-dpg.json`,
  autosave.flow/.gui rescue files + recovery-on-launch, quit guard.
- Shell three-pane staged builder and RNODE geometry rendering: open
  parity items, on the books, not shipped.

## 6. Practical notes for the docs pass

- The ledger (`docs/REBUILD-DOCFLAGS.md`) is append-only history; leave
  it intact — write user docs beside it, not into it.
- Any commit touching `docs/` runs the corpus resolver; the three hooks
  (nine-primary-map, qualifier-field, payload-field) must HOLD. They
  hold today; if your text moves word-format ground, check the corpus.
- Screenshots: both boxes have identical builds; the HP additionally
  has the Bonsai professor present in Academy (Lenny shows the honest
  "professor not present" placard — either is a truthful screenshot,
  pick per the story you're telling).
- Gate/verify commands live in CLAUDE.md's test list plus the SMOKE /
  SMOKE_FRAMES / FLOW_DPG_TEST envs above.
- Open captain rulings (glyph six points, encoding canon A′/B′, OPEN_A
  naming): reference as open questions with pointers to the POBOX
  letters and `private/DeepAI-Consult-Glyph-Word-Brief.md`; resolution
  is not the docs phase's job.

*— CC, end of 19-08 shift. The ship is gate-green on both boxes; the
ledger is current through commit `HEAD` of this date. Fair winds.*
