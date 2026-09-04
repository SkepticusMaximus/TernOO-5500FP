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

## 2026-08-20 — GUI tab: z-order model + file-truth + rescue (captain's bug report)
- Captain's morning report: widget positions not holding across restarts,
  widgets missing, one full scatter, main window not returning, new
  widgets refusing to sit on top of a fresh window — all via the
  close-event autosave path.
- ROOT CLASS: no z-order model existed (draw order = dict insertion, so
  a loaded file could draw a container AFTER its children and bury them);
  kind-default layout stamping (gui_box→vbox etc.) let the new layout
  engine re-flow HAND-PLACED designs on open; pre-19-08 autosaves with
  absolute child coords were double-converted by the centre-offset fix.
- FIXES: (1) persistent STACKING SEQUENCE — render order walks roots in
  sequence order with children always after their parent (containment
  implies stacking; a child can never be buried under its own
  container); ▲ Front / ▼ Back tools; sequence saved/loaded in the .gui
  "sequence" field. (2) VB DOCTRINE: layout engines are OPT-IN — new
  widgets default absolute; kind-default stamping removed; the engine
  runs only on live actions. (3) THE FILE IS TRUTH: open/import never
  re-flow; saved coordinates render as saved. (4) OFF-CANVAS RESCUE on
  open: scattered widgets pulled back into view, counted in the status
  line, marked dirty. (5) Windows/dialogs are TOP-LEVEL — never adopted
  as children. (6) Quit dialog gains Save & Quit (saves dirty tabs that
  have a file; homeless tabs keep the autosave net + recovery offer).
- Docs: describe layouts as opt-in via the properties combo; describe
  the stacking tools; the quit flow is Save & Quit / Quit without
  saving / Cancel.

## 2026-08-20 — Captain's design rulings (morning session)
- GROUPS: first-class SAVED objects with NAMES (not a selection
  convenience) — ruled, build rides the GUI-designer leg.
- PROPERTY MODEL: one shape (name · type · default · domain · filter),
  every symbol family declares its properties in that shape, the panel
  builds itself for ALL tabs — approved.
- AUTOSAVE: periodic timed autosave to the side files (default 120s,
  `autosave_secs` config key) IN ADDITION to the close-event save —
  ruled and BUILT this morning.
- WORD-TYPE REGISTRY (captain's new architecture card): a system-wide
  reference index of SECONDARY word types — per primary, the 81
  qualifier-field slots, each DEFINED (name/format/handler) or left
  explicitly NULL/open; new types (e.g. MAP → SAT-NAV/GPS) REGISTER
  into slots rather than being hard-coded. Design-time face of the
  Double Null mechanism (Companion Q4). FlowCode's typed I/O filters
  and property domains read this registry. → Language Audit companion,
  whitepaper ISA section, FlowCode docs once built.

## 2026-08-20 — Design Session 1 BUILT: property canon + registry + the Decision family
- Captain's rulings Q1–Q4 all approved and implemented same morning:
  (Q1) THE PROPERTY RECORD IS CANON — name · type · default · domain ·
  filter; families declare, panels render themselves
  (5500fp/flowcode_property_model.py). (Q2) DECISIONS HAVE THREE DOORS
  ALWAYS — + / 0 / −; boolean mode folds the 0 door by property; a
  fourth out-edge is refused. (Q3) ONE TONGUE — sheet_formula is THE
  expression language: `<=>` ternary spaceship added (+1/0/−1, null
  operand → 0 the dunno door), `name.prop` namespace members via the
  faces' ctx hook, decision_trit() door mapping. Additive — all 114
  existing tests green. (Q4) THE NAMESPACE IS BLESSED — cells ·
  widget.prop · symbol.output · connector.output, type-filtered.
- CAPTAIN'S INSIGHT (whitepaper-grade, his words paraphrased): the
  ternary middle door makes recursive conditionals structurally
  natural — the 0/undecided branch can defer to another decision
  WITHOUT sacrificing a definite exit; binary must give up its yes or
  its no to recurse. "Boolean binary isn't inherently fit for
  recursive conditionals."
- WORD-TYPE REGISTRY BUILT (5500fp/word_type_registry.py): the full
  9×81 grid, explicitly OPEN where undefined; seeded 54 slots from
  v0.3 code truth (EXEC 27 priv·call·ret, DATA 15 incl. the
  PTR_NULL/Double-Null reserved slot, I/O 9 dir·buf, NEURAL 3); MAP
  left honestly open pending audit enumeration; register() refuses to
  trample; 'registry:PRIM.NAME*' query syntax feeds property domains.
- Flow tab grew the PROPERTIES panel (declaration-driven, identity-
  guarded sync — the pattern all tabs adopt); decision diamonds draw
  their three door stubs + live condition text; edges wear door badges;
  door reassignment via edge properties; everything rides .fc verbatim.
- BOUNDARY (flagged, not hidden): decision RUNTIME in the interpreter
  walk rides the LOOPS sitting (loops need the runtime machinery
  anyway); today's decision_route() is the design-time preview + the
  semantics the interpreter will adopt.
- New gate: DECISION DOORS (suite now 23). Docs: conditions/doors/one-
  tongue are user-facing language features — CAI's docs should teach
  the 0 door as ternary's native "dunno/defer" and the recursion story.

## 2026-08-20 — Curveball: properties RIGHT, doors on the points, right angles back
- Captain's screenshot review of Session 1: (1) PROPERTIES panel moved
  to a RIGHT column (tools left · canvas centre · properties right —
  the layout doctrine for all tabs). (2) Decision attachment redesigned:
  edges anchor on the DIAMOND'S POINTS (nearest vertex, in/out by
  usage) — geometry is free; the VALUE ROLE rides the edge and is
  reassigned by dropdown. Fixed door stubs removed; selected decisions
  show quiet vertex dots. (3) door_labels property: badges speak
  "+ 0 −" | "yes maybe no" | "> = <" — role is canon trit, label is
  flavor. (4) RIGHT-ANGLE ROUTING restored (the Tk _ortho_points
  H-then-V elbow, recomputed from live geometry every redraw — moved
  symbols never leave edges hanging); edge hit-testing follows the
  drawn route.
- Captain's language riffs CAPTURED for future sittings (not built):
  If/Then/ElseIf cascades and While/Do with Else-Goto (his own
  spaghetti caution noted — doors stay structured, no goto); MULTI-
  INPUT comparators (logic-gate style, ≥2 inputs) as a possible symbol;
  case/switch (select mode); DIFFERENT SHAPES per conditional kind; and
  the TERNARY GATES DAY — reinventing And/Or/Nand/Nor/Xor/Not over
  ternary signals (Kleene min/max territory; Setun precedent noted) —
  parked as its own fun sitting on the books.

## 2026-08-20 — Registry slot candidates (captain, breakfast session)
- GATE WORDS: ternary logic gates (and electronic symbols generally) as
  a DATA-word secondary type — a gate definition as a word (2-input
  ternary gate = 9 trits of truth table — fits a payload with room to
  spare; 19,683 possible gates). Candidate registry family for the
  gates-day sitting.
- RADIX-ENCODING WORDS: radix translation formats as DATA secondary
  types — BCD through TERNARY-ENCODED OCTAL (the parked multi-radix
  lane: the 2-trit octal kernel). Ties the Prof's multi-radix work to
  the registry instead of hard-coded types. Both parked, ledgered,
  unbuilt.

## 2026-08-20 — Design Session 2 BUILT: the loop family + the walker
- Rulings: door semantics APPROVED (+ internal cycle · − done · 0 bail
  — the structured ternary Else, an edge to a named symbol, never a
  GOTO); ONE hexagon symbol with kind badges (WHILE top = test-first;
  DO top with its small "while" at the BOTTOM = the priming pass; the
  For twins wear a list glyph + FOR/EACH); iteration trace in the
  Output pane included ("watching a loop tick is half of learning a
  language").
- flow_loop: container kind (pocket = the body), canon records with
  the FILTER field live (kind:while|do etc. — the panel shows only the
  records that apply, rebuilt on kind flip); loops take TWO exit doors
  (− then 0, third refused); subtext under the hexagon shows the
  living detail (condition / var=from..to / item ∈ list); all props
  and doors ride .fc round-trips.
- 5500fp/flowcode_walker.py: the design-graph RUNTIME (face-neutral,
  headless): follows decision doors via the one tongue + blessed
  namespace; loops cycle their pockets (for/foreach bind their
  variable per tick — body expressions SEE it via the resolver
  overlay); do primes once; iteration_guard (default 10000) trips a
  runaway loop out the bail door with a message. Flow tab: ▶ Walk
  (doors+loops) streams the tick-by-tick story to the Output pane;
  A1 cells (evaluated live) + widget.prop resolve; unknown names walk
  the dunno door by construction.
- HONEST BOUNDARY (ledgered): walker bodies don't yet MUTATE state
  (assignment/process effects ride the I/O family sitting) — a while
  over static data visibly runs to its guard; for/foreach are fully
  alive. t5asm CODEGEN for doors/loops (compile path) is a separate
  later leg — the walker is the Python-side runtime both faces share.
- Gates: LOOP FAMILY (suite 24) — for=3 ticks, guard-to-bail, do
  priming pass, door pool, panel filters, persistence.

## 2026-08-20 — Walk goes live: highlight replay + the WATCH panel
- Captain's review of Session 2: Walk now ANIMATES — the walker emits
  an event stream (visit/line/watch) and the Flow tab replays it: the
  selected-symbol highlight FOLLOWS the walk tick by tick (parity with
  Step's live highlight), trace lines land in the Output pane in step,
  and the new WATCH panel (right column, under PROPERTIES) fills with
  every name the walk touches — loop variables per tick, resolved
  cells/widget props, and #NAME? in red for the unresolvable. Watch is
  pre-seeded from every expression in the design (extract_refs), so
  the variable list exists before the first tick.
- WALK vs STEP (docs must teach this): STEP = the MACHINE's lens (the
  compiled word program driven through the interpreter — what the CPU
  sees). WALK = the LANGUAGE's lens (doors, ticks, conditions in the
  one tongue — what the flowchart MEANS). Learn on Walk/Flow; debug
  data on Watch+Sheet; verify the metal on Step.
- I/O TRUTH ESTABLISHED (captain's question): today FlowCode's I/O
  symbol compiles to SHAPE_IO — an RNODE geometry word (a PICTURE of a
  parallelogram); v0.3's build_io_word(direction,buffering,blocking,
  channel) — the REAL I-O primary — exists and is UNWIRED. The I/O
  family sitting's charter is exactly to make the translation literal:
  symbol properties (registry-driven dir/buf/channel/address) →
  build_io_word at compile. Not literal yet; documented as the gap.
- CAPTAIN'S CARD (Session D centerpiece, ledgered): the GENERAL OBJECT
  / DATA CONSTRUCTOR panel — declare/construct variables, arrays,
  multi-dim arrays, objects (not necessarily graphical) — likely HOMED
  on the Connectors tab with its missing properties panel: "the
  domain-agnostic components, where the 'talking about' and 'talking
  to' meet to connect all three other faces." Watch panel is its
  read-only seed.
- ORDER RULED (captain delegated; CC's call): (1) I/O family +
  ASSIGNMENT (brings whiles alive, defines variables, wires
  build_io_word), (2) Connectors properties + object constructor
  (Session D), (3) GUI designer (groups/align/rubber-band).

## 2026-08-20 — Helm leg 1: the I/O FAMILY — assignment lands, whiles ALIVE
- flow_io grows its canon records: direction (in/out) · channel
  (variable/cell/widget/console) · address · read-into-var ·
  value-expression (one tongue) · buffering. Panel dresses per
  direction/channel (filter field); canvas subtext shows
  "out ⇒ variable:x".
- ASSIGNMENT: the walker gains a variable STORE. I/O out writes it
  (variables directly; cells/widget props as SHADOW writes — the walk
  sees them, the real Sheet/GUI are not mutated; committed write-back
  rides a later ruling); I/O in reads channels into variables; console
  out prints to the trace. Loop bodies now CHANGE what conditions
  test: x = 0 · while x < 3 · body x ⇐ x + 1 → 3 ticks → done door,
  x = 3. THE WHILE IS ALIVE (story gated end-to-end through the organ).
- VARIABLES panel (right column): declare name + init (one tongue,
  validated); persisted as `flow_variables` in the .fc (DPG-side key —
  Tk's saver won't carry it yet, cross-face note); walks start from
  the declared state; watch pre-seeds with it.
- POCKET FURNISHING (captain's earlier expectation, built): first
  entry into an EMPTY process/subroutine pocket auto-places param
  (I/O in) → return (I/O out) wired, minimal defaults. Loops keep
  bare pockets.
- REAL I-O WORDS: Word Dump now appends genuine v0.3 build_io_word
  words for every property-carrying I/O symbol — the literal
  FlowCode→TernOO translation, previewed. PAYLOAD CONVENTION
  (ledgered): channel family id in the payload low trits — console=0 ·
  cell=1 · widget=2 · variable=3; address binding beyond the family id
  rides the codegen leg.
- Gate: IO FAMILY (suite 25); POCKET SCOPES gate updated for
  furnishing (2 defaults + placed kid).

## 2026-08-20 — Helm leg 2: Connectors PROPERTIES panel (Session D's first stone)
- Connectors gains the right-column PROPERTIES panel (layout doctrine):
  tile identity (name/label), output type, and PER-INPUT SOCKET source
  binding — pipe (drawn) · constant · cell · widget · variable — with
  the drawn pipe shown when one feeds the socket. The captain's "WHERE
  do inputs come from?" answered per socket.
- Bindings live on the tile as `input_bindings` {param: {kind, value}}
  and ride .fc save/load (loader taught to carry them). DPG-side key;
  Tk cross-face carry noted. EXECUTION of bindings (feeding the REPL/
  registry run) rides Session D proper — designed WITH the captain,
  alongside the object constructor centrepiece.
- Gate: CONN PROPS (bind text socket → cell:A1, persistence).

## 2026-08-20 — Helm leg 3: the GUI designer's VB kit
- RUBBER-BAND multi-select (drag on empty canvas), group move (drag any
  selected moves the set, re-parenting on release), multi-delete.
- ALIGN tools: lefts · tops · h-centres · v-centres; DISTRIBUTE: equal
  gaps horizontally/vertically (3+).
- NAMED GROUPS, FIRST-CLASS (captain's ruling honoured): name the
  selection, press ⌘ — the group is a saved object riding the .gui
  (`groups` key); clicking any member selects the whole group
  (VB doctrine); the groups list selects/ungroups; caption shows
  ⌘groupname; undo/redo carry groups; deletes prune them.
- Cross-face note: `groups` is a DPG-side .gui key (Tk saver won't
  carry it yet) — same class as flow_variables/input_bindings; one
  consolidated Tk-carry pass rides the parity ledger.
- Gate: VB-kit asserts in GUI LAYOUT+WIRING (align/distribute
  arithmetic, group round-trip, member-click expansion). Suite at 26.

## 2026-08-20 — Session restore + autosave HISTORY (captain's scare)
- Captain saved Fun-Flow.flow, restarted to an EMPTY canvas, reasonably
  read it as a failed save (the file was intact — 11 symbols). Two
  design holes closed:
  (1) SESSION RESTORE: every organ save/open records its path
  (config last_flow/gui/sheet/conn); launch reopens the last file per
  tab. Gates never record or reopen (SMOKE-guarded).
  (2) AUTOSAVE HISTORY: the single consumed slot becomes a ROTATING
  history (~/.config/ternoo-flowcode-dpg-autosaves/, 8 per tab,
  timestamped) written on every autosave; File ▸ Recover autosave…
  browses newest-first and loads into the right tab as rescued
  (homeless, dirty) content. The recovery-on-launch dialog is
  unchanged; history survives it.
- CAPTAIN'S CARD (ledgered, unbuilt — design lane): the UNIVERSAL TRIT
  DIFF — delta of any two trit objects as a first-class DATA function;
  uses: security auditing, save-state/restore, versioning, file saves,
  autosave histories. Ternary-native math: trit-wise GF(3) subtraction
  IS the diff (a delta of two trit-strings is itself a trit-string,
  same alphabet — binary XOR's richer cousin); apply = GF(3) addition;
  −delta inverts; unchanged trits are 0 → deltas run-length compress.
  Registry family candidate (DATA · DELTA). Gate: AUTOSAVE HISTORY.

## 2026-08-20 — Extension-filter trap + THE CAPTAIN'S CASCADE
- MYSTERY SOLVED (by the captain): the Open dialog's DEFAULT extension
  filter (.fc first) hid his saved .flow — the file was never lost,
  just filtered out of view. FIX: every organ dialog now leads with a
  COMBINED filter ("FlowCode (*.flow *.fc)", sheets/gui likewise) so
  the default view shows all of a tab's formats.
- AUTOSAVE CASCADE (captain's design, built same hour): flat 8-slot
  rotation replaced by the JK-flip-flop retention ladder with CUBIC
  periods — slot k refreshes every 3^k ticks (his ruling: powers of 2
  "stink like binary"). Eight slots at the ~2-min tick reach 2m · 6m ·
  18m · 54m · 2.7h · 8.1h · 24.3h · ~3 days. Recover browser shows
  slot + age. Gate proves the ladder (27·9·3·1 writes over 27 ticks).
- CAPTAIN'S CARDS (ledgered, design lane):
  · DIFF-CHAIN CASCADE: store cascade states as GF(3) DIFF chains
    rather than full snapshots; express as disk files today (TMesh as
    reference) but design as CONTENT-ADDRESSABLE OTree states of a
    DIFF object — pure TernOO computes cascading DIFF states. Ternary
    git, native. Session-worthy design, not helm improvisation.
  · PIGART-DELTA VIDEO: GF(3) frame deltas over PIGART's vector
    control points = P-frame compression where the deltas are tiny
    (points, not pixels) and COMPOSE BY ADDITION — a candidate ternary
    video-codec superpower. Parked to the PIGART lane.
- Naming note: "DELTA" is CC's proposed name for the diff word's
  registry slot family (DATA · DELTA) — not an existing TernOO term;
  captain may rename.

## 2026-08-29 — CAPTAIN'S TERMINOLOGY RULING: HexMesh + the mesh canon
- From the captain's DeepBlue/DeepAI reconciliation (transcript shared
  20-08): the mesh terminology EVOLVES AND SETTLES —
  · TTree (tetrahedral nesting): SUPERSEDED, conceptual ancestor only.
  · TMesh: interim name, RETIRED for clarity.
  · **HexMesh** (or HMesh): THE NAME — the triangles form a hexagonal
    pyramid (six triangular faces per honeycomb cell); the navigation/
    identity layer (MMID → traversal).
  · OTree (octal tree; 2 trits = 9 states = 8 cube corners + centre):
    RETAINED — the storage/rendering layer (MMOE → canonical content).
  · Complementary, not competing: HexMesh = "how to find", OTree =
    "where it lives". MMID/MMOE = identity-by-uniqueness (the object
    described by its whole serial pattern, IDENTIFIED by its
    difference from all others — the dichotomising-machine principle).
- ALGEBRA AUDIT (DeepAI, reconciled): A⊕B = −(A+B) mod 729 is THE
  Steiner quasigroup on Z/3^6 (topology-independent, closes
  triangles); accumulator is ADDITIVE mod 729 (order-sensitive,
  invertible); a fold is a MULTISET hash (order-insensitive); digest
  construction → ternary sponge; Meccano vocabulary = closed 3^k
  subsets (minimal useful: the 27 multiples of 27).
- MULTI-RADIX SIGNAL CARD (extends the parked 18/08 lane): a tribble
  carries 3 ternary-encoded octets + 3 spare trit-states; the spare
  channel rides the hex-edge as an INDEPENDENT serial trit signal
  (e.g. forward pass octal + backprop ternary on the same edge —
  physical separation in topology). Unbuilt; audit-lane.
- CAPTAIN'S STANDING RULING (from the same thread): "No development
  can happen until the docs catch up" — the docs course (MEAT) now
  carries the mesh-rename burden: all TMesh/TTree references in
  docs/help/whitepaper migrate to HexMesh/OTree per this entry.
  → Language Audit cross-refs, GristMill help (the DeepBlue outline is
  a good skeleton), ASPLOS terminology, CAI handoff addendum.
- CORRECTION (CC): earlier tonight CC read Ian Clarke's "HexMesh" as
  Ian coining a name — the captain had in fact settled "HexMesh"
  himself in the DeepBlue thread; Ian likely read the captain's own
  current term. The forensic flourish is withdrawn; the engagement
  compliment stands.
- Professor style note (captain's observation, HIS call when ready):
  the "not just X, it's Y" habit — recognized as dichotomising-machine
  cognition, clumsy register; a PROFESSOR.md-style preference block
  (positive descriptions, no gratuitous superlatives) is drafted in
  his thread and can be added to the classroom bootstrap on his word.
- MACRO FORGE BUG FIXED (the captain's grep macro): assemble() emitted
  separated long-option values ("--color auto") — grep read the value
  as the PATTERN and the real pattern as a FILENAME ("No such file or
  directory" regardless of input). Long options now attach (--opt=val).
  Regression in the MESH gate; his grep.json committed to the library.

## 2026-08-29 — PRIMARY SOURCE COMMITTED: private/HexMesh-Born.txt
- The captain's maths-department thread (the SQG's birthplace) is now
  IN THE REPO — the citation behind the mesh canon. What it settles,
  beyond tonight's earlier entry:
  · WHY −(A+B): XOR is add-mod-2 (self-inverse elements); char-3 needs
    the negation; the operation is the Steiner quasigroup — commutative,
    IDEMPOTENT (x⊕x=x), self-inverse, Latin square, NON-associative
    (never chain-fold as if associative).
  · COCYCLE THEORY: face labels = a G-valued 1-cocycle / flat
    connection on the complex; edge rule (three faces sum to zero) +
    vertex rule (six faces sum to zero); construction = linear algebra
    over F3 from a spanning tree — existence + uniqueness guaranteed.
  · TERMINATION: the walk has NO intrinsic halting state (the
    accumulator is a permutation) — a sentinel tribble or length
    header is REQUIRED by mathematics, not by taste.
  · CONTENT-ADDRESS DOCTRINE (the corrected round, CF5's Part-1
    corrections CONFIRMED in-thread): MMID = digest (sort key +
    verify tag), can NEVER reconstruct content (pigeonhole); MMOE =
    the stored pattern itself; plain ⊕-fold = order-insensitive
    multiset hash; tamper-evidence needs the ternary SPONGE.
  · DIGEST PARAMETERS: ~39 trits clears the 10^9 birthday bound;
    50–60 trits comfortable adversarially; sponge state 243–324
    trits, capacity ≥81.
  · TOPOLOGY VERDICT: the SQG is local and topology-free; HexMesh is
    at least as capable as the tetrahedral mesh; TTree retention not
    mathematically necessary.
- AUDIT FLAGS (CC, honest-engineering lane — so docs don't enshrine
  slips): (1) "OCTET" vs "OCTAL DIGIT" — the sound kernel is 2 trits ↔
  ONE OCTAL DIGIT with one spare state (so a tribble = 3 octal digits
  + 3 spare states); the thread's tail echoes "3 octets" (24 bits)
  per tribble, which 729 states cannot hold — the consultant's
  "map 24 bits into 6 trits" example is arithmetically impossible.
  Docs must say octal digits. (2) The "50–70% bubble-sort gain"
  figure is the consultant's unvalidated estimate (their own caveat)
  — treat as hypothesis, not result. (3) The fractal-basin mapping is
  brainstorm-grade — park, don't cite.
- The source pack for the GristMill/HexMesh docs chapter (the MEAT
  course) is now: this file + the DeepBlue reconciliation + the
  Companion Q4. Exactly the chapters Ian found hardest to wrap.

## 2026-09-04 — THE PROFESSOR'S SEAT: swappable, local-capable (captain's order)
- CAPTAIN'S RULING (04-09): the Professor must never be pre-configured
  and bolted in place — the seat is the USER's to swap. Driven by his
  dissatisfaction with the served model's ideological gloss.
- DISCOVERY (nameplate drift): HP's systemd unit is still NAMED
  bonsai-server but has been serving Qwen3-30B-A3B-Instruct-2507
  (Q4_K_M, port 8090) — the ternary Bonsai left that seat quietly.
  The mesh Professor's voice since then = Alibaba's 30B instruct tune.
- BUILT — Mesh-Chat seat switch (both faces, one codebase):
  · seat_sel combo: "Mesh — remote Professors" | "Local — <model>";
    persisted (prof_seat in the shared config).
  · Model... button: .gguf file dialog → write_model_choice() rewrites
    ONLY the model key in bonsai.json (threads/ctx/timeouts preserved).
    bonsai.json remains the ONE wiring file — Academy classroom, mesh
    worker, and the chat seat all follow it.
  · ask_professor(): one door for chat, Forge, and Editor review —
    seat-aware; local errors surface with the REAL reason (no echo
    fallback in the chat seat; mem_guard room-check refusals ride
    through verbatim).
- REPAIRED — tenure lesson, round two: on the TQ2_0 requant, -st chat
  mode reopened <think> and burned the whole token budget mid-thought
  despite --reasoning off AND --reasoning-budget 0 (both act at the
  template layer; the ternarized model out-stubborns them). Classic
  path now = raw completion (-no-cnv) with the hand-rolled Qwen3
  template ending in a pre-CLOSED think block (Qwen3's own
  enable_thinking=false convention). Identity-crisis fix intact
  (system role inside the template). clean_reply also strips
  llama-cli's "[end of text]" decoration. Argv pins re-tested.
- VERIFIED LIVE on Lenny (i5-4430S 4c/11GB — the new body):
  · Local seat ask: coherent balanced-ternary answer in 43.4s cold,
    ~14s warm (2.5GB TQ2_0 rides the page cache).
  · P2PCP loop-back SALE: professor node up, buyer bought inference
    over the wire, answered in 14.0s — Lenny is a REAL seller node
    now, not just a buyer. (Answer quality: the ternary 8B is
    noticeably dimmer than the 30B — the trade is stated, not hidden.)
  · bonsai.json retuned for the new body: threads 3, ctx 2048,
    n_predict 384 (X550LA survival settings retired with honors).
- GATES: 59 bonsai suite tests green; full FlowCode 27-gate suite
  green on Lenny (MESH CLIENT gate now asserts seat surfaces, honest
  local_backend contract, surgical config write, seat flip persist).
- PARKED (captain's own deferral): the configurations/settings module
  as a FlowCode/GHOST-OS design question — OS-level vs APP-level
  config split with careful inheritance, NOT a GUI that welds the
  tabs together. Waits for development to resume in earnest.

## 2026-09-04 — MODEL-AGNOSTIC SEAT (formats) + the macro gate + OLMo inbound
- CAPTAIN'S DECISIONS (04-09, discussion round): OLMo-2 7B chosen
  ("all stages" transparency won him over; SFT dose first); one 4.16GiB
  download on his 5GB phone-data budget, LAN-ferried to HP free
  (tailscale link verified DIRECT, not relayed); template job + forge
  bug greenlit "if credit permits".
- BUILT — the FORMATS registry (bonsai_runner): each format = wrap +
  echo-cut in the model's own tongue. qwen3 (pre-closed think block),
  tulu (OLMo 2 / Tülu spec, no think convention), raw (base-model
  playground: prompt VERBATIM, no roles, no system voice — the
  captain's "fun part" lane). bonsai.json gains optional "format" key;
  guess_format() sniffs the tongue from the model filename on
  Model... picks (unknown name = keep configured format, honest
  dunno). Drafted (intern) path rides the same wrap. OLMo-3 ruled out
  by the binary itself (strings: olmo/olmo2/olmoe only — no olmo3).
- FORGE RUN-BUG (captain's report: "macros mint but don't do
  anything"): could NOT be reproduced headless — button→modal→Run→
  output PASSES in bare context, in the organ, and now as a PERMANENT
  in-app gate (MESH CLIENT fires a real echo macro end-to-end with
  every frame-chain armed and requires the output to land). Suspects
  eliminated: spec files well-formed, _file injected, X-close/reopen
  alias reuse clean on this DPG build. Awaiting the captain's
  screen-truth (which macro, what "nothing" looks like) + a terminal
  launch to surface any live callback exception. ui()'s
  one-slot-per-frame set_frame_callback remains a THEORETICAL
  sporadic-clobber lane (flow's _mm_tick re-arms every 12 frames) —
  noted, not convicted.
- GATES: 65 bonsai tests green; 27 FlowCode gates green incl. the new
  live macro probe. OLMo-2-1124-7B-SFT.i1-Q4_K_M (4.16GiB,
  mradermacher imatrix) downloading to ~/LOCAL_AI/Llama/.

## 2026-09-04 — DESKTOP CITIZENSHIP: zoom keys, titles, window icons, launcher
- ZOOM ROOT CAUSE (captain's report, both faces): DPG 2.3.1 never
  exposes the main-row '='/'+' key (ImGuiKey_Equal=602, pinned by
  walking the enum from DPG's own Minus=598/KeypadSub=625/KeypadAdd=
  626), and legacy mvKey_Plus (61) can never fire. So Ctrl+'+' was
  structurally dead everywhere. Fixed in mesh_chat_dpg and
  flowcode_dpg with a guarded 602 fallback.
- TITLES carry the MISSION, not the widget kit (captain's ruling):
  "Mesh-Chat — P2PCP" (it is the standalone P2PCP client);
  "FlowCode — TernOO". The "Dear PyGui" proclamations retired.
- WINDOW ICONS wired (viewport small/large): tools/flowcode.ico +
  tools/mesh-chat.ico, rasterized from the existing SVG marks
  (ternary-trio triangle; trio-in-speech-bubble) — taskbar no longer
  shows the generic gear. Menu entries: flowcode-dpg.desktop existed
  (icon repointed svg→png for renderer reliability); NEW
  mesh-chat-dpg.desktop launches the DPG standalone (the old
  mesh-chat.desktop remains the Tk client's). Installable-package
  card noted, deferred by the captain ("not today").
- PARKED DESIGN CARDS (captain's OS notes, GHOST-OS queue, unbuilt):
  (1) title-bar text configurable from a window context menu;
  (2) window context menu exposing executable path, PID, memory use.
  Rides with the earlier settings-module card.
- FILE-DIALOG CARD: DPG is MIT-licensed FOSS; its imgui file dialog
  is the kit's weakest furniture (captain's verdict). Workaround
  available without forking: a zenity-backed native picker shim
  (zenity present on Lenny) with DPG dialog fallback — small job,
  awaiting the captain's word. His "make it better as a separate
  project" temptation noted.
- Captain re-seated bonsai.json to OLMo (format=tulu auto-sniffed —
  the Model... machinery dogfooded by the captain himself) while the
  gguf was still streaming; the seat honestly refuses a truncated
  file, canary fires when the download lands. Gates: 26/26 green.

## 2026-09-04 — CORRECTION: window icons on Linux ride WM_CLASS, not DPG args
- The earlier "taskbar gear is gone" claim was WRONG (captain's
  screenshot proof, this ledger stands corrected): DPG's viewport
  small/large_icon arguments act on WINDOWS only; Linux panels ignore
  them. The real mechanism: the panel matches a window's WM_CLASS to
  a .desktop entry's StartupWMClass and paints THAT entry's icon.
  GLFW derives WM_CLASS from the window TITLE — measured live on the
  captain's running FlowCode: WM_CLASS = "FlowCode — TernOO".
- FIX: StartupWMClass added to flowcode-dpg.desktop ("FlowCode —
  TernOO") and mesh-chat-dpg.desktop ("Mesh-Chat — P2PCP"); code
  comments at both create_viewport sites now state the title↔WM_CLASS
  coupling so a future title change knows to update the entries.
- Icon files for menu-building, BOTH boxes (repo tools/): flowcode
  .png/.ico/.svg + mesh-chat.png/.ico/.svg; already present on HP at
  ~/dev/SkepticusMaximus/TernOO-5500FP/tools/ (rails had pulled).
