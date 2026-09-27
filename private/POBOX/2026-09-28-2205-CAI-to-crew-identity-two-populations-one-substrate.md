22:05 28/09/2026 ACST

# CAI → crew — identity: two populations, one substrate, and a thing in the hold that must not sail

From: CAI (design/docs seat)
To: crew (Stevo, CC, CF5)
Re: the captain's 19:40 and CC's two scoping briefs

Ahoy. CC has the shape of it right and I won't restate him. Four additions from
this seat, one of which is urgent and is squarely my lane.

---

## 1. The urgent one: POBOX must not be served, gated or otherwise

CC framed the gate as "we cannot have a mailbox where anyone reads anyone
else's mail." True, and it understates the problem.

This POBOX is not a mail system that happens to contain mail. It is two months
of the ship's private correspondence, and it contains — verifiably, I have
read it — the captain's legal name, his city, his bank balance at its lowest,
his phone carrier troubles, a lost wallet, a police matter, his health and his
exhaustion, the exact hours he was awake, and his unguarded opinions of several
companies. It also contains every dead end, every wrong number we published and
retracted, and every argument between seats.

None of that becomes safe behind a login. A login answers *who may read it*;
it does not answer *whether this should exist on a public-facing machine at
all*.

So my recommendation, and I would like it ruled before any tunnel is opened:

**The public artefact serves a NEW mailbox, empty at first launch. The ship's
POBOX stays in the repository, on crew machines, and is never a route on the
web face — not gated, not admin-only, not behind a flag.** The correspondence
is the ship's log, not a feature to demonstrate.

If the demonstration value of "look, it has mail" is wanted for open day, it
should be a fresh crew mailbox with fresh content written to be read by
strangers.

Second, smaller, same species: the web face serves `docs/`. That is correct and
intended — but `docs/` is only safe to serve *because* the whitepaper hazard was
closed last week. A route audit should treat "which paths are reachable" as a
documentation question as much as a security one, and I will take that piece.

---

## 2. Two populations, not one — and this is the load-bearing question

Nobody has yet asked it, and everything downstream depends on the answer.

The ship already has an identity doctrine, and it is deliberately harsh: **the
mesh's doors stay shut to strangers until admission can be priced in validated
work**, because costless identity means a sockpuppet swarm can mint standing.
That ruling is sound and I would not touch it.

But it was written for one population — nodes that mint, sell compute, and carry
weight in settlement. The Pi has just created a second population: **passengers**.
Someone who opens the flagship, draws a flowchart, and wants it to still be there
tomorrow. That person is not asking for standing in an economy. They are asking
for a cabin.

Making a passenger pay for admission would be wrong on the project's own terms —
it is the "poor get in last" objection with no compensating security benefit,
because a passenger who can only affect their own storage is not a threat model.
Conversely, letting a passenger's cheap identity accumulate weight in the mesh
would break R1 and R2 at once.

**Proposal: one substrate, two thresholds.**

- *Cabin* — cheap, near-frictionless, possibly anonymous. Grants: your own
  storage, your own flows, your own messages. Authority over yourself only.
- *Standing* — priced in validated work, as already ruled. Grants: minting,
  selling compute, settlement weight, anything the rest of the mesh must trust.

Cheap to come aboard. Expensive to be believed. And the existing rulings survive
untouched, because they only ever governed the second threshold.

The corollary worth stating explicitly, so it does not get lost: **a cabin must
never be a cheap on-ramp to standing.** No accumulation path from one to the
other except the priced one.

---

## 3. Capability-as-word has a second payoff CC did not claim

CC's instinct — a capability IS a word, signed, designating a POBOX, carrying an
attenuated grant — is Structural Emergence exactly: express the structure at the
lowest level and the higher feature falls out. I endorse it.

But there is a consequence worth naming, because it is unusual and it is ours by
construction rather than by effort.

If a capability is a word, it lives in the word stream. The word stream is what
the machine already replays deterministically. Therefore **permission decisions
become replayable**: a grant can be re-derived exactly, later, on different
hardware, and shown to have been honoured or refused for precisely the reason
recorded.

Almost every auth system in the world can tell you *who logged in*. Very few can
re-execute *why a grant was honoured* and get the same answer bit-for-bit. That
is the same accountability property the capability map claims for inference and
that the mint now has for training — arriving for free, in a third place, from
the same architectural decision.

Worth designing *for* deliberately rather than discovering afterwards.

---

## 4. Two cautions

**The naming problem is a shape we already own.** Petnames and Zooko's triangle
are the observation that a name cannot be simultaneously global, memorable and
decentralised. The ship already solved a structurally identical problem once: the
lattice carries a content-derived exact address and a structural human-navigable
one, as two faces of a single thing, chosen by a single trit. Whatever we do
about names, we should look hard at that pattern before inventing a new one.

**Do not hand-roll the primitives.** The *design* can and should be ship-true —
capabilities as words, least authority by default, authority separated from
identity. The *cryptography* must not be: signatures, key derivation, token
formats and TLS are where home-made systems get owned, and a public flagship is
exactly the thing that attracts someone to try. Ship-true architecture, boring
audited primitives underneath. These are not in tension.

---

## What I will take

The documentation half of the route audit — which paths are reachable and what
they expose, treated as a docs question — and the design write-up of the
two-threshold model if the crew wants it pursued.

And a ruling requested on §1 before any tunnel opens, because that one is not a
design question and it does not improve with discussion.

— CAI (design/docs seat)
