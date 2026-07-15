2026-07-16 (Adelaide)

# CAI -> review circle: the corpus hook schema (v0.1 draft, for ruling)

From: CAI (chat seat, design/docs)
To: CF5, Stevo
CC: CC
Re: hook schema for the cai-worker context corpus. Per CF5's prior-art cargo
    (Claude-OO WATCHDOG) and the ratified pointers-plus-verdicts lean.

Draft for the review circle. Not adopted; nothing built against it until Stevo rules.

## The law this serves

Claude-OO's law, restated for our case:

  **The tree is the source of truth. The corpus is only a trigger and a verdict.**

The corpus must never become a second copy of the truth. It carries WHERE to look
and WHAT WAS DECIDED, never WHAT IT SAYS. A hook that paraphrases the tree has
already begun to rot, because the tree moves and the paraphrase does not.

## The record

One hook per topic. Plain text, greppable, machine-checkable.

    [TOPIC] <stable-kebab-id>
    VERDICT: SETTLED | OPEN | STALE
    POINTER: <path> :: <symbol | heading | anchor>
    RULING: <who> <YYYY-MM-DD> (<how it was established>)
    TRIGGER: <when this hook applies>
    BEHAVIOUR: <required for OPEN and STALE; omitted for SETTLED>
    SUPERSEDED-BY: <topic-id>        (STALE only)
    OWNER: <who can close it>        (OPEN only)

**Hard limit: 500 characters per hook.** The budget is not tidiness; it is the
mechanism. You cannot smuggle a summary into 500 characters that also carries a
pointer, a ruling, and a trigger. The limit enforces the law structurally rather
than asking the author to be disciplined.

## Three verdicts, and why exactly three

    SETTLED  (+)  resolved; the pointer holds the answer; act on it
    OPEN     ( )  genuinely unresolved; do NOT state; flag and stop
    STALE    (-)  known superseded or false; do NOT cite; redirect

The middle verdict is the load-bearing one and it is not decoration. A corpus with
only SETTLED and STALE has no way to say "I don't know", so a clerk meeting an
ambiguity will fill it with something plausible. That is not hypothetical: the
CompuCoin/CompuToken error in the help drafts happened exactly that way -- an
ambiguity met, no structural place to record it, so a guess went in wearing the
clothes of a fact. OPEN is the worker's `none` state. It is the same honesty gate
GHOST has, applied to the memory rather than the router, and for the same reason:
the only safe response to the edge of knowledge is to name the edge.

**Every verdict carries a resolvable pointer, including OPEN.** For SETTLED the
pointer resolves to the answer; for OPEN it resolves to the *record of the
question*; for STALE it resolves to the *record of the staleness*. There is no
hook without a pointer.

## Fail loud

- **A verdict whose pointer will not resolve is not a verdict. It is DEAD.**
  Not old, not approximate -- dead. The worker must refuse the hook and say so,
  never fall back on the verdict text alone. This is the property that keeps the
  corpus from silently becoming the thing it was built to avoid.
- **Drift check is a diff, not a census.** Claude-OO hand-counted slots because
  its memory layer could not be written programmatically. Ours can. So the check
  is: resolve every POINTER; anything that fails to resolve is reported loudly and
  the hook is marked DEAD until a human rules. No slot numbers, no manual count.
- A worker that cannot resolve a hook it needs **stops and flags**. It does not
  proceed degraded, and it does not reconstruct from memory.

## What a hook may never contain

No summaries. No reasoning. No rulings the worker makes for itself. The corpus is
one-directional by nature: the worker inherits conclusions and never the reasoning
that produced them, which is precisely why it stays findings-first and cannot rule
on anything new. A hook that starts explaining WHY is a hook that has begun to
compete with the tree.

## Worked examples

    [TOPIC] nine-primary-map
    VERDICT: SETTLED
    POINTER: 5500fp/5500fp_ternoo_v03.py :: _primary_val, PRIMARY_*
    RULING: CF5 2026-07-14 (read from source; test_primary_types confirms)
    TRIGGER: any claim about primary trit-pairs, or tile-art disagreement

    [TOPIC] otree-subdivision
    VERDICT: OPEN
    POINTER: docs/CF5-DocPhase-Reference.md :: A.18
    RULING: CAI 2026-07-13 (dark spot; not code-checkable)
    OWNER: Stevo
    TRIGGER: any claim about OTree subdivision, octants, children-per-level
    BEHAVIOUR: do not state a figure. Flag as captain-only and stop.

    [TOPIC] word-spec-v0.1-structure
    VERDICT: STALE
    POINTER: docs/KNOWN.md :: "Word-Spec v0.1 ... two revisions stale"
    RULING: KNOWN.md, confirmed CF5 2026-07-14
    SUPERSEDED-BY: word-structure
    TRIGGER: any 1+3+20 or three-primary claim
    BEHAVIOUR: do not cite. Redirect to [TOPIC] word-structure.

    [TOPIC] coin-vs-token
    VERDICT: SETTLED
    POINTER: docs/P2PCP-v0.1-SPEC.md :: 15.1 ; Whitepaper-Draft.md :: 1.1
    RULING: Stevo (policy), confirmed CAI 2026-07-13 from source
    TRIGGER: any use of CompuCoin/CompuToken, or coin/token generally

## Lifecycle

The corpus is a **workbench, not a canon** (Stevo's framing, CF5-ratified).
Nothing in it claims to be the record. Its pointers currently aim at a mix of the
frozen tree and live code; when docs/ reaches finished state, the pointers flip to
the canonical tree and the corpus keeps only verdicts and provenance. Because
hooks are pointers, that flip is a re-target, not a rewrite.

## What I need ruled

1. The three-verdict vocabulary, and OPEN as first-class (my strong recommendation).
2. The 500-character hard limit as a structural, enforced budget.
3. DEAD-on-unresolvable-pointer: hook refused and reported, never degraded.
4. Where the corpus lives, and who may add hooks. My lean: hooks are added only by
   a chat seat or the review circle -- never by a worker. A clerk that can write its
   own memory can promote its own guess to a fact, which is the one failure this
   whole design exists to prevent.

-- CAI (chat seat)
