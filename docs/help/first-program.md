Your first program
section: Start here

Let's make something and watch it run. This won't take long, and by the end you'll have done the thing that everything else builds on — turned an idea into a working program and seen TernOO carry it out. No prior experience needed. If you get stuck, every step here links to a page that explains it more fully.

We'll build the smallest complete thing there is: a program that takes a word and shouts it back in capitals. Small, yes — but it's a *whole* program, start to finish, and the shape of it is the shape of everything bigger.

## Step 1 — Open the canvas

Go to the [[flow|Flow]] tab. This is the drawing board where programs are built as flowcharts — boxes for the things that happen, arrows for the order they happen in. A blank canvas is exactly the right place to be right now.

## Step 2 — Mark where it starts and ends

Every program needs a beginning and an end. From the palette on the left, place a **Terminator** (the oval) near the top for the start, and another lower down for the end. Between them is where the work will go. If flowcharts are new to you, the short version is: you're about to describe a journey from *start* to *finish*, one step at a time.

## Step 3 — Lay out the three steps in the middle

Between start and end, place three symbols in a row. The labels aren't decoration — TernOO reads them, so what you write on a box is what the box does:

- An **I/O** step (the parallelogram), labelled something like *ask for a word*. This is where the program pauses and waits for you to type.
- A **Process** step (the rectangle), labelled **shout** (or *uppercase*, or *capitals*). This is the heart of the program: TernOO recognises those words and turns whatever reaches this step into capital letters.
- A second **I/O** step, labelled *show the result*. This is where the program hands the answer back.

That a box labelled *shout* really shouts is the self-describing-word idea (see [[ternoo-words|What is a TernOO word]]) working in miniature — the word on the box says what the box does.

## Step 4 — Connect the dots

Draw arrows so the path runs cleanly: start → ask → shout → show → end. The arrows are the program's story: *begin, take a word, shout it, show it, stop.* When the path is unbroken from start to finish, your program is complete. That's genuinely all a program is — a path through a set of steps.

## Step 5 — Run it

Press **Run**. TernOO walks the path you drew, and the active step lights up as it goes. When it reaches your *ask* step it pauses and asks for a word — type one and press OK. It shouts your word into capitals and hands it straight back, and the output area shows you the result and the trace of how it got there.

That's it. **You made a thing do a thing.** It ran on a ternary machine, driven by words that describe themselves, following a path you drew with your own hands. Small program — but everything you'd build from here uses these exact moves: place steps, connect them, run, watch.

## What just happened, underneath

The flowchart you drew wasn't a *picture of* a program — it *was* the program. Each box you placed became a self-describing [[ternoo-words|TernOO word]]; the arrows became words too. When you pressed Run, TernOO read those words directly. There was no hidden text version underneath translating your drawing into "real code" — the drawing was the real code. (If you're curious, the [[flow|Flow]] tab can show you the actual words your flowchart became.)

## Where to go next

- **Do more with it.** Try adding a second step — count the letters, or reverse the word — and running again. Chaining steps is how programs grow.
- **See it another way.** Open [[babble-fish|Babble-Fish]] and look at the same program written in a familiar programming language. Same program, different view.
- **Let the assistant help.** In the [[shell|Shell]], type `ghost` followed by a plain-English description of what you want, and [[ghost|GHOST]] will point you at the right tool for the job.
- **Understand the foundation.** If you skipped it, [[ternoo-words|What is a TernOO word]] explains why the drawing *was* the program.

You've done the hardest part already — the first one. Everything from here is just more of the same, arranged into bigger and better things.
