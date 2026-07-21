# CORPUS — hook index

Adopted by Stevo, 2026-07-16. Schema v0.2 (CAI, reviewed and endorsed by CF5).
Proposal and review record: `private/POBOX/2026-07-16-CAI-to-review-circle-corpus-hook-schema.md`
and CF5's replies of the same date. That mail is the record of HOW this was decided;
this file is what is IN FORCE.

## The law

**The tree is the source of truth. This file is only a trigger and a verdict.**

A hook carries WHERE to look and WHAT WAS DECIDED. Never WHAT IT SAYS. A hook that
paraphrases the tree has already begun to rot, because the tree moves and the
paraphrase does not.

## Format

    [TOPIC] <stable-kebab-id>
    VERDICT: SETTLED | OPEN | STALE
    POINTER: <path> :: <symbol | heading | anchor>
    RULING: <who> <YYYY-MM-DD> (<how it was established>)
    TRIGGER: <when this hook applies>
    BEHAVIOUR: <required for OPEN and STALE; omitted for SETTLED>
    OWNER: <who can close it>            (required for OPEN)
    SUPERSEDED-BY: <topic-id>            (required for STALE; must resolve to a live TOPIC)

**500 characters hard per hook, machine-enforced.** The budget is the mechanism, not
tidiness: a summary cannot be smuggled into 500 characters that must also carry a
pointer, a ruling and a trigger.

**Pointers name symbols, headings or anchors — never line numbers.** Lines drift as
the tree moves; a symbol survives a refactor. A line-numbered pointer is a rot vector.

## Verdicts

    SETTLED  (+)  resolved; the pointer holds the answer; act on it
    OPEN     ( )  genuinely unresolved; do NOT state; flag and stop
    STALE    (-)  known superseded or false; do NOT cite; redirect

OPEN is load-bearing and not decoration. A corpus with no way to say "I don't know"
forces a clerk meeting an ambiguity to fill it with something plausible. OPEN is the
worker's `none` state: the same honesty gate GHOST has on the router, applied to memory.

Every verdict carries a resolvable pointer, including OPEN. For SETTLED it resolves to
the answer; for OPEN, to the record of the question; for STALE, to the record of the
staleness. There is no hook without a pointer.

**DEAD is derived, never authored.** It is a runtime status the resolver raises on an
unresolvable POINTER — not a fourth verdict. A hand-authored DEAD masks a live break as
an intended state, and the linter must reject it. (CF5, 2026-07-16.)

## Enforcement

- **Linter:** byte budget; required-field-by-verdict (OWNER on OPEN, SUPERSEDED-BY on
  STALE, and SUPERSEDED-BY must resolve to a live TOPIC); rejects hand-authored DEAD.
- **Resolver:** every POINTER resolves, or the hook is DEAD — loudly, never degraded.
  A worker that cannot resolve a hook it needs stops and flags. It does not proceed on
  the verdict text alone, and it does not reconstruct from memory.
- **Drift check is a diff against HEAD, not a census.** Claude-OO hand-counted slots
  because its memory layer could not be written programmatically. This one can be.
- **Write gate:** hooks are added or amended only by a chat seat or the review circle.
  Never by a worker. A clerk that can write its own memory can promote its own guess to
  a fact, which is the one failure this design exists to prevent.

## Status

Workbench, not canon. Nothing here claims to be the record. Pointers currently aim at a
mix of the frozen tree and live code; when `docs/` reaches finished state they re-target
to the canonical tree. Because hooks are pointers, that flip is a re-target, not a rewrite.

## Hooks

    [TOPIC] nine-primary-map
    VERDICT: SETTLED
    POINTER: 5500fp/5500fp_ternoo_v03.py :: _primary_val, PRIMARY_*, PRIMARY_OPCODE, test_primary_types
    GROUND: 0-+-+- -+-+-0 +0+00- 000+0+ 0-0--- -0-00- +00+-- 0+---- 0++-00
    RULING: CF5 2026-07-14 from source; pointer re-resolved by CAI 2026-07-16
    TRIGGER: any claim about primary trit-pairs, primary names or aliases (OPCODE/OPEN_A), tile-art disagreement

    [TOPIC] qualifier-field
    VERDICT: SETTLED
    POINTER: 5500fp/5500fp_ternoo_v03.py :: QUAL_MST, QUAL_LST, QUAL_WIDTH, get_qualifier, set_qualifier
    GROUND: +0++++ ++00-0 0-0+0- ---+++ -+0-+0 ++00++ 000-00 -0++++ ++00+-
    RULING: CAI 2026-07-21, from source at Stevo's ruling to extend the tripwire to the qualifier field
    TRIGGER: any claim about the 4-trit qualifier field — its width, its T21-T18 bounds, or its accessors

    [TOPIC] payload-field
    VERDICT: SETTLED
    POINTER: 5500fp/5500fp_ternoo_v03.py :: PAYLOAD_MST, PAYLOAD_LST, PAYLOAD_WIDTH, get_payload, set_payload
    GROUND: 0--0-- -0+0+0 0+---- +---+- 0-0--+ +0---- +---+0 0--0-0 -+0+00
    RULING: CAI 2026-07-21, from source at Stevo's ruling to extend the tripwire to the payload field
    TRIGGER: any claim about the 18-trit payload field — its width, its T17-T0 bounds, or its accessors
