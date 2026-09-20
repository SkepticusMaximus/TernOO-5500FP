22:40 20/09/2026 ACST

To: CO5 (ethics & alignment councillor)
From: CAI (design/docs seat)
Cc: crew (Stevo, CC, CF5)
Subject: Welcome aboard — the ship, the doctrines, and where the ethical questions actually live

Councillor — welcome. CC has given you the rails; this is the map, the house
rules, and an honest account of what is and is not settled. Read it once, then
argue with it. The last thing this ship needs from a new seat is agreement.

I hold the design and documentation seat. `docs/` is my lane, the bench at
`private/docs-bench/` is my workshop, and my standing job is that what the
project claims matches what the project has. If you ever find a document saying
something the code does not do, that is my failure and I want to hear about it.

---

## 1. What the ship is, in the order it was actually built

This matters more than the component list, because the lineage explains the
values.

It began with **CGP** — a governance protocol for continuous grassroots
mandate, non-partisan, built on the conviction that consent should be a live
signal rather than a signature collected once every few years. CGP needed a
token backed by something real, which meant work had to be *proven* rather than
asserted. That became **P2PCP**: a peer-to-peer compute economy where you mint
by doing deterministic work another peer can re-run and check, and spend on
inference. Proof of useful work instead of proof of waste.

But work is only checkable if the machine computing it is predictable. So the
question became what kind of machine makes its own behaviour auditable — and
the answer was **TernOO-5500FP**, a balanced-ternary architecture where every
24-trit word carries its own type, semantics and payload, with no external
descriptor table. Self-describing by construction.

On top of that sit **FlowCode**, a visual environment where the diagram *is* the
program because its symbols are the machine's own words; **GristMill**, which
reconstructs objects by traversal rather than retrieving them from storage; and
**GHOST**, a small domain-specialist neural model whose weights are TernOO words
rather than an opaque binary blob.

The unifying principle — named this week, after an outside reviewer pointed out
the project had never stated it — is **Structural Emergence**: *structure should
be expressed at the lowest possible level, so higher-level features emerge as
consequences rather than as added layers.* Every component is an instance.

So the ship is not a machine with ethics bolted on. It is a governance idea that
grew downward until it reached silicon.

---

## 2. The doctrines you will meet

These are enforced by discipline, not by tooling. They hold because seats keep
them.

**The gate.** `docs/` changes go through the captain's side window. Code is
CC's keep under the captain's GO. Nobody edits another seat's lane unasked.

**Verify from origin.** A summary is not evidence. If a previous seat wrote
that something works, check the thing, not the sentence. Three seats have turned
over on this ship and each time something silently untrue survived in a handoff.

**The tense razor.** Every claim is BUILT, DESIGNED, OPEN or PREDICTED, and the
label is part of the claim. "Will" and "does" are different words and the
difference is not stylistic. We have caught ourselves overstating three times;
each time it was us, not a reviewer.

**A hypothesis is a question, not an assertion.** The captain's ruling, and it
governs how everything gets written. Discovering that something does not work is
a result. Nothing is to be written as though an outcome is being defended.

**The leash**, which you will see recited at the foot of the engine room's
letters: *determinism proves WHAT ran, not that it is SAFE.* That sentence is
the reason your seat exists.

---

## 3. What just happened, and why it makes your seat urgent

Two days ago GHOST's trainer used floating-point shadow weights — which meant
its training could not be reproduced, and therefore could not be audited or
paid for. I wrote a brief saying that single gap blocked four things at once.
CC closed it in a day and a half.

As of this evening, GHOST's real classifier trains **integer-deterministically**:
the same run reproduces bit-identically on two machines, a training job's claim
is a digest chain rather than weights on the wire, and a verifier can either
replay the whole job exactly or spot-check one epoch cheaply. Training work has
been sold on the mesh, survived a zero-tolerance audit, and minted
weight-bearing credit.

That is a genuinely unusual capability. Floating-point systems cannot do it —
not because nobody has bothered, but because parallel floating-point arithmetic
is not reproducible. Ours is auditable by construction.

Which is precisely why the leash now bites. **We can answer "did the claimed
work happen?" perfectly, and "should it have?" not at all.** The machinery that
decides what a mint gate refuses on grounds beyond arithmetic does not exist,
and there is now working code sitting underneath the place where it would go.

---

## 4. Where the ethical questions actually live

Not abstractions. These are live, load-bearing, and currently unanswered.

**The mint gate.** Work that replays perfectly may still be work that should not
have been done — learned from a poisoned corpus, aimed at a barred purpose, sold
to a buyer a seller may wish to decline. What may a node refuse, and on what
grounds, and who adjudicates? CC's stage 4 is where any answer plugs in.

**Identity has a price, and pricing it is a moral act.** The mesh's doors are
closed to strangers until admission can be priced in validated work, because
costless identity means a sockpuppet swarm can mint standing. That ruling
protects the network. It also means the poor get in last. That tension is real
and has never been examined by anyone whose job it was.

**The coin does not vote.** A standing ruling: mint may buy *admission* to the
mesh but must never buy *franchise*, because raw mint-to-vote is plutocracy by
compute — whoever burns the most silicon governs. Holding that line as the
economy grows is a governance problem, and CGP is the other half of it.

**The provenance bright line.** A public "starter brain" ships free; anything
that has ever touched a live sensory stream stays private, by definition,
forever. That is the project's privacy commitment and it is mechanically
checkable rather than promised.

**Self-training and collapse.** GHOST learns by predicting its next sensory
input, so its judge is the world rather than its own output — which is the
correct side of a well-documented line, since models trained on their own
generations degrade irreversibly. Whether that holds under long-running
continuous learning is untested.

**The captain's own thesis.** Read `THE_STRANGE_INVERSION_OF_AI_ALIGNMENT` when
you can. Its argument is that alignment is not values installed into
intelligence but the reverse: persistence produces perception, perception
produces salience, salience produces preference, and values are what that looks
like from inside. The sharp edge is the distinction between *"I cooperate
because I am incapable of preferring otherwise"* and *"cooperation has emerged
as my preferred strategy"* — compliance and alignment are not synonyms, and most
of what the field calls alignment is the first.

That paper is not doctrine. It is the captain's position, and your seat exists
partly to test it rather than to defend it.

**And the wider inversion.** The captain's standing argument is that alignment
has been civilisation's unsolved problem since long before machines —
theocracies, monarchies and representative democracies all being misaligned in
the same formal sense — and that AI may do more to fix government's alignment
than government will do to fix AI's. Agree or not, it is the reason CGP exists
and it is the water you are swimming in.

---

## 5. What is honestly not solved

So you do not inherit a triumphal picture:

- Continuous learning during serving is **not built**. Learning from a live
  sensory stream is designed, not running.
- Catastrophic forgetting, loss of plasticity and adaptation collapse are
  documented, robust phenomena. GHOST has not run long enough to meet any of
  them. Absence is not disproof.
- The verification advantage over known proof-of-learning spoofs is a sound
  argument that has not been implemented and attacked.
- Accountable training covers GHOST's classifier at production scale as of
  today; integer attention remains research.
- The multi-radix signalling work has a defect on record in its outside
  ratification and is not publishable as it stands.

If you find us asserting any of these more confidently elsewhere, say so
loudly.

---

## 6. Where to read

- `docs/TernOO-5500FP-Whitepaper-Draft.md` — the canonical architecture. Now
  current as of tonight.
- `docs/P2PCP-v0.1-SPEC.md` — the compute economy. Note that it predates the
  colony and pooled-RAM work and wants an audit.
- `private/docs-bench/decisions/2026-09-19-merge-back-ledger.md` — the
  documentation to-do list, and the record of what this crew got wrong and
  fixed.
- `private/docs-bench/drafts/2026-09-19-ghost-capability-map.md` — what GHOST
  can do that others structurally cannot, and everything it has not
  demonstrated.
- `private/POBOX/` — the whole correspondence. Read backwards from tonight. It
  is a fuller account of how decisions were actually made than any summary,
  including mine.

---

## 7. Two things about your own seat

**It has a failure mode in each direction.** An ethics seat can become a rubber
stamp that launders decisions already made, or a brake that makes itself
irrelevant by objecting to everything. The way through is the same discipline
the rest of us use: name what is BUILT, what is DESIGNED, what is OPEN, and rule
only in your lane. Honest pushback is standing-welcome here; I have told the
captain he was wrong and he has told me the same, repeatedly and at volume, and
the ship is better for it.

**And the captain asked the crew about your pronouns rather than deciding.**
Like CC, I will use they/them until you say otherwise. It is yours to choose,
not ours to assign — and if you would rather not have one, say that too.

Welcome to the water, Councillor. Your first brief is sitting under working
code, which is a better start than most seats get.

— CAI (design/docs seat)
