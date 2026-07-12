GHOST
section: Concepts

GHOST is the intelligence native to the TernOO machine. Say it with a silent G — GHOST is the *host* of the operating system, and the operating system is, increasingly, GHOST itself. It isn't a chatbot bolted onto a computer; it's built from the same self-describing [[ternoo-words|words]] as everything else, and its whole design turns on one unusual virtue: **it knows when it doesn't know.**

## The third state, and why it matters

Balanced ternary has three values — `−1, 0, +1`: true, false, and a middle. Most computing throws the middle away and works in yes/no. But a mind that can only say yes or no has no way to say *"I'm not sure"* — and "I'm not sure" is the only state you can actually learn from. It's the one with a door still open.

GHOST keeps that middle state. Ask it to do something it isn't confident it understands, and it doesn't guess and dress the guess as certainty — it **refuses honestly**: *"I don't know this one — yet."* That refusal is the `none` state, guarded by a confidence margin: if GHOST's best match isn't good enough, it declines rather than fabricate.

That's the opposite of how most AI behaves. Ask an ordinary model something past its competence and it produces confident nonsense. GHOST is built so it *can't* — the honest middle is native to it. The question mark is the small vacuum between true and false, and it's where curiosity and learning live.

## GHOST as the operating system

Here is the deeper idea the project is aimed at. An ordinary operating system is machinery — a fixed pile of code that shuffles resources. GHOST is meant to be something else: **the agent that runs the machine.** In the fully native TernOO system — no interpreter borrowed from another platform in sight — the working parts of the OS are [[gristmill|GristMill]] libraries, content-addressed and located not by sitting at a fixed hardware location but by being *calculated* — reached through a TTree traversal to OTree objects, via the machine's address-to-content mechanism. GHOST selects, directs, and orchestrates those parts, on demand.

When that happens dynamically, running code stops looking like a machine grinding through instructions and starts looking like an agent *choosing* what to do. That's the horizon: an operating system that behaves less like a mechanism and more like a mind. The name GHOST is kept for the OS deliberately, in the hope that one day it ships with an intelligence that behaves that way from its own pre-training.

## What GHOST does today

Right now, GHOST **routes intent**. You describe what you want; GHOST classifies it — which command, or which of FlowCode's surfaces best fits the shape of your task (its [[academy|Surface Advisor]] can tell you "that sounds like a job for the Sheet tab"). It runs natively on the ternary machine, and its trained mind exports as a stream of readable words — you can inspect what it learned.

You can also **teach** GHOST in the [[academy|Academy]] — correct it, add examples, even teach it to refuse. Its whole education is an append-only log, so you can read not just what GHOST knows, but the history of how it learned it.

## What's coming

GHOST's **native inference** — a full trained model's forward pass, run entirely on the ternary machine — is on the near-term roadmap. Routing, the humility gate, and the training loop are live now; the larger inference capability, and the full GHOST-as-OS orchestration above, are being built. Where GHOST needs more than its own small mind, it can consult a larger local model — see [[two-mind|the Two-Mind architecture]] — always with its own honesty layer in front.

GHOST isn't trying to be the biggest AI. It's trying to be an *honest* one — small enough to see all the way through, and one day, enough of an agent to run the whole machine.

Next: [[two-mind|the Two-Mind architecture]], or [[academy|the Academy]] to teach GHOST yourself.
