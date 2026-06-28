# Design Memo — Named-Handler Auto-Wiring + Trinity Integration

**From:** CAI
**To:** Stevo (design conversation captured) + future CWC dispatch when ready
**Date:** 28 June 2026
**Re:** How GUI widgets and Flow terminators connect; how the FlowCode trinity (GUI / Flow / Sheet) integrates without collapsing the conceptual separation
**Status:** Office-mode design memo. No CWC dispatch yet — captures the picture for future implementation phases

---

## 1. Principle — Separation is Architecture, Not a UX Failure

The Flow tab, GUI tab, and (future) Sheet tab are deliberately separate surfaces because they describe **different kinds of things** about a program:

- **GUI** — what the program looks like (the physical description of the user-facing surface)
- **Flow** — what the program does (procedural logic and control flow)
- **Sheet** — what the program computes (data, formulas, references)

This separation is *correct*. Visual Basic and Borland C++ Builder both got this right thirty years ago — the form designer is one surface; the code-behind is another; the binding between them is a *named reference*, not a visible wire on a unified canvas. FlowCode goes one better than VB/Borland by replacing the syntax-heavy code-behind with a flowchart, but the *principle of separate surfaces with named bindings* is preserved.

The CWC UX report's framing of "the two canvases don't visually communicate" mistook the separation for a problem. It isn't. The wires are *meant to be invisible* because the surfaces are *meant to be distinct*. What was actually missing — and what this memo addresses — is **discoverability**: making it easy to follow a named binding from one surface to the other without rendering them as a single visual continuum.

---

## 2. The Trinity — Connection Points

Three surfaces, four kinds of binding between them:

| From | To | Connection Type | Status |
|---|---|---|---|
| GUI widget | Flow terminator | Named handler (auto-named per signal) | Exists as explicit REDGE binding (Phase 6D/Bundle 12); this memo proposes name-driven mode |
| Flow edge | Spreadsheet cell | Cell reference as parameter value | Requires Sheet leg (not yet built) |
| Spreadsheet cell | GUI widget | Reactive: cell value displayed/edited in widget | Requires Sheet leg |
| Flow symbol | Nested flow / widgets | STYLE_CONTAIN, opened via "pocket" UX | Data model exists; UX doesn't |

Two of these (GUI↔Flow and Flow↔Sheet) are about *named references between surfaces*. One (Flow→nested) is about *recursive structure within a single surface*. One (Sheet↔GUI) is *reactive data flow*.

All four use named references as the binding mechanism. None require collapsing the surfaces into one canvas.

---

## 3. Named-Handler Auto-Wiring (the GUI↔Flow connection)

### The principle

A GUI widget's signal binds to a Flow entry point **by name agreement**. The widget knows its default signal-handler name; if a flow_terminator exists with that name, the binding is automatic. No explicit "bind this to that" step.

### Naming convention

Every GUI widget has a `name` property (distinct from `label`) that identifies it programmatically. Default name on creation: `<kind>_<id>` (e.g., `button_5`, `entry_3`). The user can rename it in the property panel (e.g., to `submit_button`).

For each signal a widget can emit, the canonical handler name is `<widget_name>_<signal>`:

- `submit_button_clicked`
- `email_entry_changed`
- `cancel_button_clicked`
- `quantity_spinbutton_value_changed`

When the user creates a flow_terminator with that name and `is_entry=true`, the binding is implicit. No REDGE handler edge is required *as a separate action*. The editor recognises the name agreement and treats the connection as wired.

### How the WordStream represents this

The WordStream's underlying data model **still uses REDGE STYLE_HANDLER edges** (per Phase 6D / Bundle 12). What changes is the *editing surface*: the editor auto-generates the REDGE binding whenever it detects name agreement, and removes it when the agreement is broken (terminator deleted, renamed, or widget renamed away from the handler).

This keeps the architecture intact — the runtime/compiler from Phase 7b still reads REDGE bindings the same way. Only the editor's UX changes: instead of an explicit "bind handler" dialog, naming is the wiring.

### Explicit bindings retired

The current "click signal row → pick a terminator from a modal" UX from Phase 6D is **retired**. The naming convention replaces it. If the user wants a button's click to fire a specific handler, they name the terminator to match. If they want a different handler, they rename.

This is a simplification: one mechanism for wiring, not two.

### Property panel changes

- New `name` field for every widget that can emit signals
- Default value: `<kind>_<id>` on creation
- Empty `name` means the widget cannot have handlers (no auto-naming possible)
- For widgets with `name` set, the property panel shows the *generated* handler names (read-only) so the user knows what to call a terminator that wires to this widget

### Flow tab side

When the user creates a flow_terminator and starts typing its name, the editor offers autocompletion from the set of available handler names — generated by walking all widgets in the WordStream and applying the naming convention. This makes wiring discoverable: type `button1_` and see what handlers are available for `button1`.

---

## 4. Ctrl+Click Navigation (Discoverability)

The complement to the naming convention: a way to **follow** a binding from one surface to the other.

### From GUI to Flow

`Ctrl+click` on a GUI widget that has any auto-wired handlers → jump to the Flow tab with the *first* matching terminator centered and highlighted. If the widget has multiple handlers (e.g., button has both `clicked` and `focus_changed`), the context menu opens with a list and the user picks which to navigate to.

If the widget has no matching terminators (no flow has been wired yet), the context menu offers "Create handler: `<auto-name>`" — clicking it creates the terminator on the Flow tab with the right name and switches tabs.

### From Flow to GUI

`Ctrl+click` on a flow_terminator whose name matches a widget's handler convention → jump to the GUI tab with that widget highlighted/centered.

If the terminator's name doesn't match any widget's handler convention (an "orphan" handler), Ctrl+click does nothing (or shows a status message: "No matching widget signal").

### Why this isn't visual integration

Ctrl+click navigation honours the separation of surfaces — the user is still working in one surface at a time, just with frictionless cross-reference. This is how every modern IDE handles cross-file navigation: Ctrl+click on a function name jumps to its definition, but the function and its callers don't visually merge into one document.

---

## 5. The "Pocket" UX (the Flow→nested connection)

Stevo's intuition: where edges meet a flow symbol, there's a "pocket" you can open up. Inside the pocket: parameters/formulas (eventually spreadsheet cell references) and a recursive flow scope.

### What the architecture already supports

Per Phase 6D §8.4 and the Stage 6 design memo, a flow symbol can contain other flow symbols and widgets via STYLE_CONTAIN edges. The WordStream encodes this uniformly. So "nested flow inside a process box" is already a representable structure.

What's missing is the **UX** for opening the pocket and editing the nested content.

### Proposed UX (rough — for future iteration)

- Each flow symbol has an "open" affordance — probably a small triangle/disclosure indicator in a corner, double-click to open
- Opening the pocket transitions the canvas into "scope drilldown" mode: the parent symbol's interior fills the canvas, and the user is now editing the nested scope
- The breadcrumb bar at the top of the canvas shows the scope path: `MainFlow > ProcessReceipt > ValidateAmount`
- The pocket can contain: nested flow symbols, parameter/return type declarations, formula bindings (when Sheet exists), widget previews (for handlers that render their associated widget)
- Closing the pocket: click the parent in the breadcrumb, or press Escape

### Scope rules

The walk-up containment-chain handler resolution from Phase 6D §8.4 already defines lexical scope. The pocket UX is the visual expression of that scope: inside a pocket, you see only what's reachable from this scope.

### What this isn't

It isn't a separate tab. It isn't an inline expanding panel. It's a **drilldown**: the canvas you're looking at is the scope you're editing, with breadcrumbs to navigate back up. This is the same model as drilling into a folder in a file manager: you're not seeing both at once; you're descending and the navigation lets you return.

---

## 6. What This Memo Does NOT Decide

- **The Sheet leg's data model and UX** — that's its own design conversation (sketched separately)
- **Exact implementation order** — when named-handler auto-wiring lands vs. pocket UX vs. spreadsheet leg is Stevo's call
- **Migration of existing designs** — if any `.ternoo` files exist with explicit REDGE bindings that don't match the new naming convention, how do they upgrade? Probably auto-rename terminators to match the existing binding, or surface a migration dialog. Deferred to implementation phase
- **What happens to `signal_ids` from Bundle 12** — they still exist in the WordStream for the REDGE bindings to reference; the naming convention is the editing-surface UX, not a data-model replacement

---

## 7. Implementation Roadmap (Loose — Stevo's Pace)

These are the substantive phases that emerge from this memo. **No timeline implied.** Each becomes a CWC bundle when Stevo points to it.

| Phase | Scope | Effort |
|---|---|---|
| 7c-1 | Add `name` property to widgets; default value generator; property panel UI for editing | Small |
| 7c-2 | Editor recognises name agreement → auto-generates REDGE handler binding; retire explicit-binding picker; autocompletion in flow terminator name field | Medium |
| 7c-3 | Ctrl+click navigation between tabs | Small |
| 7c-4 | Pocket UX — drilldown into flow symbol scope, breadcrumb navigation | Medium-large |
| 8 | Spreadsheet leg — separate substantive arc; sketched in a separate memo | Large |

Phases 7c-1 through 7c-4 close the GUI↔Flow integration story. Phase 8 (Sheet) opens the Flow↔Sheet and Sheet↔GUI integration stories.

---

## 8. The Question of Concept Drift

CWC's framing in the original UX report — that the GUI and Flow tabs not being visually merged was a "problem" — represented genuine concept drift away from the project's architectural principles. This memo is partly a record of catching that drift and re-establishing the right framing.

For future reference: any time a proposal suggests "the two canvases should be visually integrated" or "you should see them together," the response should be **why?** The separation is purposeful. Concrete usability concerns (binding discoverability, cross-canvas navigation, execution traceability) are legitimate and addressable — without collapsing the surfaces.

---

## 9. Why This Is Right (Summary)

- Borland and VB got it right thirty years ago: separate surfaces, named bindings
- FlowCode replaces code-behind with flowchart but preserves the separation
- Name-based wiring is more *intuitive* than visual wires once you stop trying to draw arrows between tabs
- The trinity (GUI / Flow / Sheet) maps cleanly onto separate-surfaces-with-named-references
- Pocket UX provides recursive abstraction without visual chaos
- Ctrl+click navigation gives discoverability without sacrificing the conceptual separation

The architecture and the UX align. The project doesn't need to be "fixed" by merging tabs — it needs the existing model surfaced more discoverably.

---

*Design memo prepared: 28 June 2026, Adelaide*
*Implementation phases 7c-1 through 7c-4 dispatch as separate bundles at Stevo's pace.*
