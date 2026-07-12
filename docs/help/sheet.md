The Sheet tab
section: Tabs

Sheet is a spreadsheet surface — a grid of cells with formulas — and if you've used a spreadsheet before, the basics will feel familiar. What's different is what the grid is connected to.

## Familiar on the surface

Type values into cells, write formulas that reference other cells, and the grid recalculates the way you'd expect. Arithmetic, comparisons, the common functions — they work the way a spreadsheet should.

## Different underneath

A TernOO formula isn't interpreted by a spreadsheet engine off to the side — it compiles down to the native machine and runs there, so a formula and a program are ultimately the same kind of thing. The grid is a *view* of computation, not a separate application.

That's why the Sheet tab can do something an ordinary spreadsheet can't: **cells can bind to your program's logic.** A cell can drive a [[flow|flow]], or a flow's result can land in a cell. The spreadsheet becomes a live surface over your program rather than a static table beside it.

## Getting started

Start as you would anywhere — put values in cells, write a formula. When you want a cell to do more than calculate, connect it to a flow through the binding mechanism, and the grid and the logic move together.

Next: [[gui|GUI]] for on-screen controls, or [[flow|Flow]] for the logic cells can drive.
