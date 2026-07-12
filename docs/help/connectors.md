The Connectors tab
section: Tabs

Connectors is where the pieces of a program are wired together **by name** — so a step in one place can hand off to a step somewhere else without a tangle of long arrows crossing the whole canvas.

## Why named connections

As a program grows, connecting everything with visible arrows gets messy fast. Connectors let you give a point a **name** — a named exit here, a named entry there — and the two link up by that name. It's the difference between running a physical wire across a crowded room and just labelling both ends "line 3."

These named points work across **scopes** — the self-contained pockets a program is organized into. A pocket can expose named entry and exit points on its edge, hiding its inner detail while still connecting cleanly to the rest of the program. You drill into a pocket to see how it works; from outside, you just use its named ports.

## Getting started

Name an exit point where a piece of logic finishes, name an entry point where another should begin, and connect them by those names. As your program grows into nested pockets, the named ports keep the wiring legible instead of letting it sprawl.

Next: [[flow|Flow]], where the logic being connected is drawn.
