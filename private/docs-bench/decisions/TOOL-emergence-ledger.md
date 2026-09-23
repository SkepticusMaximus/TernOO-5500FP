# TOOL Emergence Ledger — semantics discovered by building, not designed

Per the north-star brief (§3 "extract, don't design") and the captain's
23-09 order: every trit of development is the prototype from which
TOOL's semantics EMERGE. This ledger records each place a specimen
needed to say something the words could not yet say. Bench-bound;
these entries are TOOL's raw semantic vocabulary, not work items.

| # | Discovered while building | The semantic the specimen needed |
|---|---------------------------|----------------------------------|
| 1 | Colour picker (23-09) | A walk must write a widget PROPERTY, not only its label — "name.prop" as an assignment TARGET, symmetric with reading it. |
| 2 | Colour picker (23-09) | A control's value must be READABLE in expressions as `name.value` — the resolver knows geometry/label/props; value is a peer. |
| 3 | (anticipated: file dialog) | A composite must RETURN a value to its caller — the dialog-result semantic: a span-of-spans with an exit port carrying a word. |
| 4 | (anticipated: font explorer) | A list widget populated from a QUERY (the font registry) — data-source binding, not hand-authored items. |
| 5 | Colour picker (23-09) | LIVE face state must flow into the resolver before each walk — the design-at-rest is not the program's state. (Landed: drive syncs values pre-walk.) |
| 6 | Colour picker (23-09) | OPEN: `name.value` inside arithmetic returns None through the walker's member-expression path — swatch paints ''. Suspect: sheet_formula 'member' node evaluation for bare-name.prop vs WIDGET("x").prop. Next watch's first dig. |
