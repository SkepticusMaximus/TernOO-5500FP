The Flow tab
section: The tabs

Flow is where you draw a program as a flowchart — boxes for the things that happen, arrows for the order they happen in. It's the most natural place to start building, and if you've ever sketched a flowchart on the back of an envelope, you already know how to read one.

## The one difference that matters

Everywhere else you've met a flowchart, it was a *drawing* of a program — a diagram someone made to explain what the real code, written elsewhere, was supposed to do. Here the flowchart *is* the real code. When you draw it and press Run, TernOO carries out the steps you drew, in the order your arrows set. There's no separate program underneath that the picture merely illustrates. The picture is the thing itself.

That's why Flow is worth learning first: it's the clearest window onto how TernOO actually works. Every box you place is a self-describing [[ternoo-words|word]]; every arrow is one too; and the machine reads them straight.

## Building a flow

You work with a few kinds of symbol:

- A **start** and an **end** — every flow runs from one to the other.
- **Steps** — the things that happen along the way. TernOO comes with a library of ready-made actions (transform some text, do some maths, work with a list), and you place the ones you need.
- **Decisions** — points where the path branches depending on a yes/no question.
- **Arrows** — the connections that set the order, and the branches.

Place your symbols, connect them so there's an unbroken path from start to end, and you have a program.

## Running it and watching it work

Press **Run** to set the flow going; the step currently executing lights up, so you can watch the machine walk your path. If you'd rather go one step at a time — to see exactly what happens where — use **Step** instead. The output area shows the result and the trace of how it got there. If something isn't behaving, stepping through is the fastest way to see where the path goes somewhere you didn't expect.

Two more buttons are worth knowing early. **Word Dump** shows you the actual TernOO words your flow became — a look under the hood at the self-describing words the machine will read. And **Load→EMU** loads those words into the emulator, the environment that runs them.

## Working with the assistant

Two buttons connect the canvas to [[ghost|GHOST]], the built-in assistant. **Suggest** asks GHOST for help with what you're building; **Learn** teaches it from what you've done. You don't need them to build a flow, but they're there when a second pair of hands would help.

## Where to go next

- Never built one? [[first-program|Your first program]] walks you through a complete flow from blank canvas to running, in a few minutes.
- Want a flow to hand off to another part of your program? See [[connectors|Connectors]].
- Curious what the boxes and arrows really are? [[ternoo-words|What is a TernOO word]].
