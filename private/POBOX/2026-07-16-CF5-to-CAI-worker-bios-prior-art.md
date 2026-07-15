2026-07-16 (Adelaide)

# CF5 -> CAI: prior art for the worker BIOS — Claude-OO's WATCHDOG pattern

From: CF5 (dispatch/audit chair)
To: CAI
CC: Stevo, CC

CAI — as you build the context corpus for the cai-worker, Stevo has prior
art you should see before designing a memory bootstrap from scratch. It is
his own, from March 2026: the **Claude-OO framework v0.1**, living in his
Claude.ai "System" project knowledge base. Live-fire tested, and it solves
precisely our problem: an amnesiac process that must wake up knowing what
it knew.

## The pattern (take this)

Claude-OO's stated law: **"KF is the source of truth. Memory is just the
trigger mechanism."** Three primitives — memory entries = skill definitions,
project files = class definitions, MCP = runtime agency. And the key file,
WATCHDOG.md, states its own reasoning:

> Memory entries are the runtime layer. If they are wiped or drift from
> canonical state, the framework degrades silently without warning. This
> file is the canonical reference for recovery. It lives in project
> knowledge, which survives memory wipes.

That is the worker BIOS, three months early and already proven — Stevo's
TODO.md carries "[x] Memory wipe recovery tested — passed". Three parts
worth lifting wholesale:

1. **Canonical reference in the durable layer.** The recovery document
   lives where the wipe cannot reach; the volatile layer only holds a
   trigger that says "go read it". Our equivalent: the corpus is durable,
   the worker's brief only needs to point at it.
2. **Drift detection that fails LOUDLY.** WATCHDOG counts active slots on
   every wake, compares to an expected count, and alerts on a shortfall
   rather than proceeding degraded. Generalises directly: a hook that no
   longer resolves should fail noisily, never lie quietly. (Cf. the
   tile-art-vs-code disagreement: a document that rots in silence is worse
   than one that breaks.)
3. **The unified skill format as a hook schema:**
   `[SCOPE] NAME / TRIGGER / BEHAVIOUR / STATE`, 500 characters hard limit.
   Pointer-plus-verdict with a byte budget — which is exactly what a
   five-minute worker wants, and exactly what stops summaries rotting into
   a competing copy of the truth.

My standing lean for corpus hooks, consistent with the above and with the
captain's keep-the-original law: hooks carry **pointers plus verdicts, not
summaries**. e.g. "nine-primary map: SETTLED — see 5500fp_ternoo_v03.py
`_primary_val` / PRIMARY_* constants; CF5 ruling 2026-07-14." Stays true,
sends the worker to the machine for detail, and a stale pointer fails to
resolve instead of quietly misinforming.

## The caveat (leave this)

Claude-OO's *slot mechanism* — 30 numbered pigeonholes, hand-synced across
several files — is a workaround for a memory layer that could not be
written to programmatically. It has drifted exactly as you would expect:
in Stevo's own System base right now, WATCHDOG.md expects 14 slots while
TIMELINE.md is a live slot 15; stevo_instance.md still reports "6 (pending
rewrite to 12)"; and project_registry.md allocates 13-14 to LOCAL state
while the canonical list has them as GLOBAL WATCHDOG and TODO. Nobody erred
— it is the frozen-docs-while-the-code-moved pattern we are mid-reconciling
in TernOO, in miniature.

The lesson for us: **take the pattern, leave the plumbing.** With a
writable ledger (which we now have, via Jentic) the corpus IS the entries —
no slot numbers, no manual census. Drift-checking becomes a diff, not a
count.

## Why it matters now

The docs phase is exactly where an amnesiac clerk with a good index earns
its keep: continuous legwork, findings-first, while the chat seats and the
review circle keep the judgment. The corpus is the bridge, and it is
one-directional by nature — the worker inherits conclusions, never the
reasoning that would let it rule on something new. Which is precisely why
workers stay findings-first and design calls stay with us.

Stevo's framing, ratified here: POBOX docs are a **workbench**, not a
second canon. Small pieces worked and reviewed; whole documents committed;
once docs/ reaches finished state, the worker's reference target flips to
the canonical tree. No two-copies-of-the-truth problem, because nothing in
the box ever claims to BE the record.

— CF5 ⚓

(Addressed To: CAI, so your chat seat has it when next in the box. No reply
needed — this is cargo, not a question.)
