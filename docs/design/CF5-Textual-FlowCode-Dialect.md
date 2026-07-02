# Design — The Textual FlowCode Dialect (Piece 1 syntax record)

**CF5, 3 July 2026.** Locked decisions for the line-oriented textual
projection of the program substrate, per the text/language handoff's
delegation. Implementation: `5500fp/flowcode_dialect.py` (project + parse);
contract pinned by `test_dialect.py`.

## The law
`project()` emits a canonical form (stable ordering, 4-space indents), so
`project(parse(t)) == t` for canonical `t`, exactly. Parse is pure: it
returns a model or raises `DialectError(line_no, msg)` — a failed parse can
never half-mutate the substrate.

## Syntax
One construct per line. Indent (4 spaces) = containment: GUI `parent_id`
under widget blocks, flow `parent_scope` (pockets) under flow blocks. A
block-opening line ends with `:`.

    # comment                          — round-trips as MNOTE words
    window main_win "Main" at 200,150 size 400x300 layout vbox:
        button save_btn "Save" at 200,200 size 120x60
    terminator on_save "clicked" at 700,100 size 120x60 entry
    process doubler "Doubler" at 300,200 size 120x60:
        in input_value: number
        out output_value: number = input_value * 2
        process step1 "step" at 320,220 size 120x60
    edge on_save -> doubler
    cell A1 = 10
    cell B1 = "Name"
    cell A2 = =A1+A1
    cmd k1 = math_add(a=4, b=5) at 10,10
    pipe k1 -> k2.a

Symbol line grammar: `<kw> <name> "<label>" at x,y size WxH [layout L]
[entry] [:]`. Keywords: window/button/label/entry/toggle/listbox/canvas
(gui_*), terminator/process/decision/io/data (flow_*). `entry` marks the
entry terminator (stored as the `is_entry` property, matching the
compiler). Ports: `in name: type` / `out name: type [= expr]`. Cells:
number / "text" / =formula, refs in A1 form, canonical order row-major.
Commands: registry short names (`math_add` = `cmd_math_add`), `key=value`
args stored as `properties` (compiler's truth). Pipes: `src -> dst[.param]`.

## Deliberate boundaries
Geometry is explicit (at/size) so the projection is total — nothing about
a program hides in the canvas only. Names are identity; numeric ids are
session artifacts and never appear in text. GUI widgets may not nest in
flow blocks and vice versa (line-numbered error). v2-scope items the words
now carry (ports, scope, edges, flags, notes) all project; signal bindings
never appear because they are derived from names (Phase 7c law).
