The Two-Mind architecture
section: Concepts

TernOO can run two very different AIs, and the interesting part is how they relate: **they cooperate without merging.**

## Two minds, two jobs

- **GHOST** is small, fast, and fully inspectable. Its weights are readable words; its reasoning runs natively on the ternary machine; its refusals are honest. Its virtue is *provable honesty*. It stays small on purpose — the moment you grow it, you lose the ability to see all the way through it.
- **The Professor** (a larger local model — the ternary "Bonsai" model) is big and capable. It can do things GHOST can't. Its virtue is *capability*.

The temptation is to fuse them into one bigger, smarter thing. TernOO deliberately doesn't. Instead they talk through a **contract** — GHOST out front as the honest face, the Professor behind it as consulted horsepower.

## How they cooperate

When GHOST is confident, it just answers — natively, quickly, honestly. When GHOST hits its [[ghost|`none` state]] — "this is beyond me" — it can *ask the Professor*. But the Professor's answer doesn't reach you unfiltered: it comes back **through GHOST's honesty layer**. GHOST never becomes a dumb pass-through. If the big model is confidently wrong, the small honest one is still the last word.

This is the project's deepest discipline applied to minds: **keep the original.** GHOST stays GHOST; the Professor stays the Professor; neither dissolves into the other. The small mind keeps the conscience; the big mind lends the power; and because both speak the same ternary number system, nothing is lost in translation between them.

## Why the Professor is quarantined

The Professor is a genuinely capable model, so it's treated with appropriate care. It runs as a **local subprocess** — a program on your own machine, spoken to through a direct pipe, with **no network socket anywhere in the path.** It cannot phone home because there is nothing in the design to phone home *with*. When you talk to the Professor directly (through the Academy's [[academy|Backstage Panel]]), you're talking to your model, on your machine, and it never leaves the box.

That "no network, ever" rule is the one guarantee that never bends — the same sovereignty promise that runs through all of TernOO.

## The state of it

The pieces are arriving in order. GHOST's routing, humility gate, and training are live. The delegation contract to the Professor is built, consent-gated (GHOST asks before it consults). The Professor requires the larger model to be present on your machine, and degrades gracefully when it isn't. Some of the deeper cooperation — and the honest evaluation of what the big model returns — is still being refined; the system is upfront about which parts are live and which are coming.

Two minds. One honest, one powerful, neither pretending to be the other.

Next: [[academy|the Academy]], where you meet both, or back to [[ghost|GHOST]].
