The Connectors tab
section: The tabs

Connectors is where the pieces of a program are joined together **by name** — so a point in one place can hand off to a point somewhere else, without a long arrow trailing across the whole canvas.

## Why name your connections

As a program grows, joining everything with visible arrows gets tangled fast. Naming solves it: you give a point a name here, a matching name there, and the two link up by that name — the way you'd label both ends of a cable "line 3" instead of trying to trace the wire through a crowded room by eye.

This is also how the separate parts of a program come together. A [[flow|flow]] can hand a value to a [[sheet|sheet]]; a [[gui|button]] can start a flow; a result can travel back to a label — all through named connections. Connectors is the tab where that wiring lives, keeping it legible as the program gets bigger.

## Working across scopes

Programs are organised into self-contained pieces — pockets, each with its own inner workings. A pocket can expose named entry and exit points on its edge: from outside you use those named points, and the tangle inside stays hidden until you choose to look. You drill into a pocket to see how it works; you connect to it by its named ports. That's what lets a program grow into nested parts without the wiring turning into a thicket.

## Getting started

Name a point where one piece finishes, name a point where the next should begin, and connect them by those names. As your program grows into pockets, the named ports keep everything joined and readable.

## Where to go next

- The pieces being connected: [[flow|Flow]], [[sheet|Sheet]], [[gui|GUI]].
- How a whole program fits together: [[welcome|the overview]].
