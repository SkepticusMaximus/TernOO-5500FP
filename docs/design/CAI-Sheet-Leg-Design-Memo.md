# Design Memo — The Sheet Leg of the FlowCode Trinity

**From:** CAI
**To:** Stevo + future CWC dispatch
**Date:** 28 June 2026
**Re:** Spreadsheet tab as third surface of the FlowCode trinity. Cells as first-class TernOO words, hybrid formula evaluation, name-based binding, grid-primary UX
**Status:** Office-mode design memo. Decision-locked across most of the design space. Supersedes the earlier exploratory sketch (CAI-Spreadsheet-Leg-Design-Sketch.md). Implementation arc as Stage 8

---

## 1. The principle

The Sheet leg completes the FlowCode trinity:

- **GUI** says *what the program looks like*
- **Flow** says *what the program does*
- **Sheet** says *what the program computes*

Each leg is a *separate authoring surface* with its own canonical content type, all backed by the same WordStream substrate. The Sheet leg fills a gap that's been visible since the trinity was first conceived: without it, programs that compute anything have nowhere natural to express the math, and the Flow leg ends up reaching for awkward expressions inside flow boxes.

Spreadsheets are the universally-understood notation for "data plus formulas." Borrowing that notation (rather than inventing one) maximizes familiarity for users and minimizes invention cost for the project.

The Sheet leg is the *substrate that gives the other legs something computable to bind to*.

---

## 2. Locked decisions

### Core data model

| # | Decision | Choice |
|---|----------|--------|
| Sh1 | Cell representation in WordStream | New RNODE family `cell_*`. Each cell is one RNODE with kind such as `cell_value`, `cell_formula`, `cell_text`. Reuses existing RNODE machinery — opcode, MAP for position, DATA for content. No new opcodes invented |
| Sh2 | Cell coordinate model | Cells live at grid positions (row, column) in the default Sheet view. Internally each cell's MAP word encodes (col, row) — grid coordinates, not pixel positions. The Sheet UX maps grid coords to screen coords like a normal spreadsheet |
| Sh3 | Cell kinds | `cell_value` (holds a literal — number, text, boolean, etc.), `cell_formula` (holds an expression that evaluates to a value), `cell_text` (holds plain text — labels, headers, comments) |
| Sh4 | Cell content | A cell's content (literal value or formula string) lives in the cell's data operands. For `cell_formula`, the formula is encoded as a sequence of DATA-STRING words containing the formula source text. The compiler parses this at compile-time |
| Sh5 | Cell typing | Cells are *dynamically typed* — a cell's value type is determined by its content (literal type or formula's evaluated type). Type checking happens at compile-time for static formulas; at runtime for dynamic |

### Cell references and formulas

| # | Decision | Choice |
|---|----------|--------|
| Sh6 | Formula syntax | **Excel-compatible** as primary dialect. `=A1+B1`, `=SUM(C1:C10)`, `=IF(A1>0, "pos", "neg")`. Familiar to anyone who's used a spreadsheet |
| Sh7 | TernOO-native function extensions | New functions for accessing widget state and flow signals: `WIDGET("name").property`, `SIGNAL_LAST("name")`, `CELL("name")` — name-based references using Phase 7c-1 naming convention |
| Sh8 | Cell address syntax | Two valid forms: `A1`-style (Excel-compatible, default for in-formula references) AND `cell_<id>` (Phase 7c-1 naming, used when a cell has been explicitly renamed). The cell-id form is preferred for cross-subsystem references (widgets and flows reference cells by name, not by A1 address) |
| Sh9 | Formula evaluation strategy | **Hybrid**: static formulas (referencing only constants and other static cells) evaluate at compile-time and emit constants into t5asm. Dynamic formulas (referencing widget state, signal values, runtime cells) emit small fragments of t5asm that recompute when dependencies change. Engine sees only literal values or compiled fragments — no formula interpreter needed at runtime |
| Sh10 | Circular dependency handling | Compile-time detection. Circular dependencies produce a compile-error in the IDE before run. No runtime circular evaluation (no iterative recalc) |
| Sh11 | Recalculation model | Dependency graph maintained at compile-time. When a dynamic cell's dependency changes (widget state changes, signal fires, dependent cell recomputes), only affected cells recompute on the next frame. Same per-frame model as Phase 7b-4's render cycle — no separate recalc engine needed |

### Sheet UX

| # | Decision | Choice |
|---|----------|--------|
| Sh12 | Tab structure | New tab "Sheet" alongside Flow/GUI/(Shell). Same WordStream backing; same edit primitive (`WordStreamEdit`) |
| Sh13 | Default view | Grid view, like Excel/LibreOffice. Rows numbered 1..N, columns A..Z (then AA..AZ etc.). Cell at (row, col) clickable, editable in place, formula bar at top of view |
| Sh14 | Free-form regions | Designated regions of the canvas where cells can be placed at arbitrary positions (not grid-snapped). For use cases that don't fit grids — named formula groups, charts in future, etc. Marked visually with a region boundary. Cells outside any region snap to grid |
| Sh15 | Cell formatting | Per-cell formatting: number format (decimal places, currency, percentage), text format (alignment, font weight), background/foreground color. Stored as properties on the cell RNODE |
| Sh16 | Headers | Row 1 (or any row, by convention) can be designated header — cells render differently (bold, locked from formula references via name). User can hide header behavior if not wanted |
| Sh17 | Multi-sheet | **Out of scope for Stage 8 initial.** One sheet per program. Multi-sheet workbooks can come later via per-sheet RNODE namespacing |

### Binding to other legs

| # | Decision | Choice |
|---|----------|--------|
| Sh18 | Widget↔cell binding | Name-based, per Phase 7c-1 convention. A widget has a `bind_value_to` property naming a cell; the widget's displayed/editable value comes from that cell, and changes write back. Bidirectional by default; an explicit `read_only=true` flag prevents writes |
| Sh19 | Flow↔cell binding | Via Pocket UX (Phase 7c-4). A flow symbol's pocket can include cell-reference inputs (read from cell) and cell-target outputs (write to cell). This is *how data flows between procedural steps and computed values* |
| Sh20 | Shell↔cell binding | Same as Flow — Shell commands can take cell references as parameter inputs. A command processes the cell's current value; pipes can write computed results back to other cells |
| Sh21 | Cell↔cell reactivity | Cell A referencing cell B means changes to B trigger A's recomputation. Standard spreadsheet semantics |

### Scope and constraints

| # | Decision | Choice |
|---|----------|--------|
| Sh22 | Computational completeness | Sheet is *not* Turing-complete. No loops, no recursion, no while. The Flow leg provides procedural completeness; Sheet provides functional/reactive computation. Keeping Sheet non-Turing-complete prevents non-terminating recalcs and matches user expectations |
| Sh23 | Cell types | `number` (real, internally ternary), `text` (UTF-8 string), `boolean`, `widget_ref` (a reference to a widget — Phase 7c naming-convention name), `signal_ref` (a reference to a flow signal — same naming). Richer types as needed; types 5+ can be added later without breaking |
| Sh24 | Number type | Real numbers represented as native TernOO words. Precision limited by word size — initially treating cells as integers; floating-point cell support deferred to a polish phase |
| Sh25 | String type | UTF-8 strings stored as sequences of DATA-STRING words (existing convention from Phase 7b widget labels). Length limited by word count; multi-word strings supported |

---

## 3. The first useful Sheet capabilities (what Stage 8 phases deliver)

Without leaving the existing architecture, Sheet enables several real use cases:

### Use case 1: Form calculator

A GUI tab dialog with inputs for variables. A Sheet tab with cells that compute results from those inputs. Cells bound to display widgets in the GUI. User changes an input → cells recompute → display updates.

Example: A loan calculator. GUI inputs for principal, rate, term. Sheet cells compute monthly payment, total interest, payoff schedule. GUI displays bind to result cells.

### Use case 2: Data transformation pipeline

User provides input data (via GUI or pasted into cells). Sheet cells process — sums, averages, filters, transformations. Results display or feed into Flow procedural steps.

Example: A simple budget tracker. Input cells for expenses by category. Formula cells compute totals, percentages, overage flags. Flow tab triggers (when category exceeds budget) bound to result cells.

### Use case 3: Configuration tables

A Sheet of named cells acts as a configuration store. Flow steps and GUI widgets read from these cells. Easier than threading individual constants through the program.

Example: Display preferences (theme colors, font sizes) as a Sheet. GUI widgets bind their `color`, `font_size` properties to those cells. User changes a cell → entire program's appearance updates.

### Use case 4: Lookup tables

A Sheet of value mappings (input → output). Flow steps use VLOOKUP-style functions to translate.

Example: A unit converter. Sheet table of conversion factors. Flow step takes a value + source unit + target unit, looks up the factor, computes the result.

These use cases are real and useful. Each is achievable in Stage 8's planned phases.

---

## 4. Integration with the architecture

### With Phase 7c (named-handler auto-wiring)

- Cells get names per the 7c-1 convention (`cell_<id>` default, user-renameable to e.g. `monthly_payment`)
- Widget↔cell binding is name-based per 7c-2
- Ctrl+click navigation per 7c-3 jumps from a widget to the cell it's bound to, and vice versa
- The Pocket UX from 7c-4 is how cells appear in flow contexts

### With Shell tab (Stage 9)

- Shell commands can take cell-references as parameters (e.g., `cmd_math_sum` over a range of cells)
- Shell commands can write outputs back to cells via the same name-based reference
- The Pocket-as-parameter-sheet pattern unifies Shell commands and Sheet cells visually

### With Flow tab

- Flow process boxes can read from cells (input parameters) and write to cells (output values) via their pockets
- Decision boxes can use cell values in their conditions
- Sub-flows compose with cell parameters cleanly

### With GUI tab

- Widget properties bind to cells (the existing widget property panel gains a "bind to cell" affordance)
- Cell values populate widgets reactively
- Widget edits write back to cells reactively

### With GHOST

- A trained GHOST model can scaffold Sheet programs from text prompts: "I want a budget tracker with monthly categories and overage warnings" → GHOST generates the Sheet structure + binds GUI widgets
- The Sheet corpus (existing spreadsheets generally, not specifically TernOO ones) is large enough that even a small GHOST model trained on spreadsheet patterns is plausibly useful
- This is exactly the *domain-specific scaffolding* GHOST is meant for

### With GristMill-the-real-thing (eventually)

- Cells are RNODEs, so they're content-addressable
- A useful Sheet (or a named formula) becomes a *shareable artifact* via OTree content addressing
- A library of reusable Sheets (template loan calculators, common math tables, etc.) becomes discoverable via GristMill the same way other code packages do

---

## 5. Implementation roadmap (Stage 8, loose phases — Stevo's pace)

| Phase | Scope | Prerequisites |
|---|---|---|
| 8-1 | Sheet tab UI scaffolding — empty tab, basic grid, cell editing, navigation | Phase 7c-1 (`name` property foundation) |
| 8-2 | `cell_value` and `cell_text` RNODE encoding + serialization | 8-1 |
| 8-3 | `cell_formula` encoding + formula parser + compile-time evaluation (static formulas) | 8-2 |
| 8-4 | Runtime evaluation path for dynamic formulas (cell-to-cell, cell-from-widget) | 8-3, Phase 7c-2 (name-based binding) |
| 8-5 | Cell↔widget binding (name-based) | 8-4 |
| 8-6 | Cell↔flow binding (via pockets) | 8-5, Phase 7c-4 (Pocket UX) |
| 8-7 | Cell formatting (number, text, color) | 8-6 |
| 8-8 | TernOO-native function extensions (WIDGET, SIGNAL_LAST, CELL) | 8-7 |
| 8-9 | Free-form cell regions | 8-8 |
| 8-10 | Polish, lookup functions (VLOOKUP, INDEX/MATCH), date functions if needed | 8-9 |

Each phase is its own bundle. Order matters because each builds on the previous. Multi-sheet support, charts, and external data import/export are all post-Stage-8.

---

## 6. What stays open (genuine forks)

Decisions I'm *not* locking in this memo:

1. **Exact in-place edit UX** — does clicking a cell open an inline editor (Excel default), or does it focus a formula bar at top of view (LibreOffice default), or both? Implementation choice for Phase 8-1
2. **Number precision** — initial integer-only; when do we add floating-point? Probably 8-7 (formatting) or later
3. **Range operations** — `A1:A10` ranges in formulas. Probably yes; whether they're internalized as cell collections or expanded at compile-time is an implementation detail
4. **Whether DATA-STRING formula encoding wastes too much space** — formulas as text strings take many words. If this becomes a problem, a tokenized representation might be needed. Empirical; cross when bridged
5. **Format-cell dialog vs. property-panel** — where does cell formatting UI live? Aesthetic call, not architectural

These are implementation specifics, not design questions. Phase-by-phase decisions.

---

## 7. What this memo doesn't decide

- **Charts and visualizations** — substantial sub-system; deferred to post-Stage-8
- **Macros / scripting in cells** — partly handled by the TernOO-native functions; full macro language would be Turing-complete (against Sh22). Probably never; the Flow leg handles procedural needs
- **Data import/export** — CSV at minimum, JSON, possibly XLSX. Deferred until Stage 8 core is stable; depends on filesystem (so likely Stage 10+)
- **Performance at large sheet sizes** — current architecture is fine for hundreds of cells. Thousands+ may need optimization. Cross when bridged

---

## 8. Why this completes the trinity

The earlier sketch concluded the Sheet leg was "structurally required for the FlowCode trinity to be complete." With this memo locked, the architecture has:

- **GUI** (existing) — visual surface for user interaction
- **Flow** (existing) — procedural surface for control logic
- **Sheet** (this memo) — functional surface for computation
- **(Shell, eventually)** — command-composition surface, builds on all three

All four surfaces share:
- One WordStream substrate
- One naming convention (Phase 7c)
- One edit primitive (`WordStreamEdit`)
- One compilation path (extending `compile_to_t5asm.py`)
- One Pocket UX for cross-surface bindings
- One eventual content-addressable store (GristMill-the-real-thing)

That's coherent architecture. The Sheet leg isn't a new tower — it's the missing third surface, slotting in cleanly because the architecture was designed with it in mind from the start.

---

*Memo prepared: 28 June 2026, Adelaide*
*Supersedes: CAI-Spreadsheet-Leg-Design-Sketch.md (28 June 2026, earlier)*
*Companion to: CAI-Named-Handler-Auto-Wiring-Design.md, CAI-Shell-Tab-Skeleton-Design.md, CAI-FlowCode-File-Extensions-Policy.md*
