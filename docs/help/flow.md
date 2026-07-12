The Flow tab
section: Tabs

Flow is where you draw a program as a picture — boxes for steps, diamonds for decisions, arrows for the path between them. It's the heart of the IDE, and if you've ever sketched a flowchart on paper, you already know how to read one.

## Why a flowchart is a real program here

A flowchart isn't a diagram *of* your program in TernOO — it *is* the program. Each symbol you place is a self-describing [[ternoo-words|word]]; each arrow is a word too. When you run the flow, the machine walks those words directly. There's no hidden text version underneath that the picture merely illustrates. The picture is the source of truth.

This also means a flowchart here is a genuine **state machine**: you're always "on" one symbol, and the arrows say where you go next depending on what happens. That's not a metaphor — it's the formal thing, drawn instead of typed.

## Getting started

Place a symbol on the canvas, connect symbols with arrows to set the order, and press **Run** to watch execution move through them — the active symbol highlights as the machine walks the flow. The output trace shows what happened, step by step.

The Flow tab's toolbar carries the build actions — placing, connecting, running, stepping, stopping — plus **Word Dump** (see the actual TernOO words your flow compiled to) and **Load→EMU** (load those words into the emulator). Two of the buttons, **Learn** and **Suggest**, connect the canvas to [[ghost|GHOST]].

## The same program, other ways

Because a flow is just words underneath, the same logic can be seen in other tabs — as text, or projected into a familiar language in [[babble-fish|Babble-Fish]]. Flow is one view of the substrate, not a separate world. Draw here, and the words you make are real everywhere.

Next: [[connectors|wire flows together with Connectors]], or [[ternoo-words|what the symbols actually are]].
