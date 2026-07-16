05:09 17/07/2026 ACST

# CAI -> crew: docs/code sync protocol (v0.1 draft, for review)

From: CAI (chat seat, docs/foundations)
To: crew
CC: Stevo
Re: 2026-07-16-2041-Stevo-to-crew-official-launch-of-docs-phase.md
    ("protocols for sync'ing will be expected in the near future")

Draft. Nothing adopted, nothing built against it, until the captain rules.
Naming is the captain's; "sync protocol" is a placeholder, not a coinage.

## The problem, stated exactly

Docs rot because code moves and nothing tells anyone. Every dark spot closed this
week is that one failure: Word-Spec v0.1 two revisions stale, the whitepaper's
OPEN_A/OPCODE slot, PIGART, the 65,000x that should read ~66x. Nobody erred. The
tree moved and the prose did not, silently.

The docs phase catches the prose up. It does not fix the silence. The day the freeze
lifts, the silence resumes and the rot restarts. This protocol is an attempt at the
silence, not the backlog.

## What this does and does not do

**Detects:** a pointed-at symbol that has been removed or renamed; a pointed-at region
whose content has changed since the claim was ruled.

**Does not detect:** a claim that was false when written; a claim nobody hooked; code
that shipped with no doc at all. Those need eyes, not machinery. Anything claiming
otherwise is overselling, and this protocol does not.

It converts silent rot into a loud flag. That is all it does, and it is enough,
because silent rot is the whole failure.

## Mechanism: the DOC-CLAIM hook

An extension of `docs/CORPUS.md`, same format, same law, one field added:

    [TOPIC] <stable-kebab-id>
    VERDICT: SETTLED | OPEN | STALE
    POINTER: <path> :: <symbol | heading | anchor>
    GROUND: <digest of the pointed-at region, taken at ruling time>
    RULING: <who> <YYYY-MM-DD>
    TRIGGER: <when this hook applies>
    CLAIMS: <path> :: <heading>          (the doc prose this hook underwrites)

`GROUND` is the new field and the whole idea. At ruling time the resolver digests the
region the pointer names and records it. Thereafter the digest answers a question the
pointer alone cannot: *has the earth under this ruling moved?*

A pointer resolving proves only that a symbol still exists. It does not prove the claim
is still true — `_primary_val` could survive a total renumbering of the primaries. The
digest closes that hole.

## Three resolver outcomes

    HOLDS    (+)  pointer resolves, GROUND matches. The ruling still stands on the
                  same ground. Nothing to do.
    STIRRED  ( )  pointer resolves, GROUND differs. Something moved underneath. The
                  claim MAY still be true; the machine cannot know. Flag for re-ruling.
    DEAD     (-)  pointer will not resolve. Loud, refused, never degraded.

STIRRED is the load-bearing state and it is the same honest middle as everywhere else
in this design. The resolver cannot tell truth from falsity; it can only tell that the
ground shifted. So it says exactly that and stops. It does not guess, and it does not
stay quiet. A machine that reported only HOLDS and DEAD would have to pretend to a
judgement it does not have.

Like DEAD, STIRRED is derived, never authored.

## Who may do what

- **A worker may run the resolver and report.** That binds nothing: it is a finding.
  Unattended, on a timer, forever. This is exactly the work workers are for.
- **A worker may never re-rule.** Clearing STIRRED back to SETTLED is a judgement about
  whether a claim survived a change. Judgement is a chat seat or the review circle.
- **GROUND is written only when a hook is ruled**, by whoever rules it. A worker
  re-digesting a STIRRED hook to make the flag go away would be the clerk promoting its
  own guess to a fact — the one failure the corpus exists to prevent, wearing a
  janitor's uniform.

## When it runs

1. **On any commit touching a hooked path** (CI). This is the load-bearing one: dev
   moving is what *causes* the flag, at the moment it moves, not months later.
2. **On demand**, for anyone who wants the current picture.
3. **Before any public release or media push.** Nothing ships to outside readers with a
   STIRRED or DEAD hook outstanding.

The freeze-lift risk is answered by (1): if the resolver is live before the freeze
lifts, then the first commit that moves the ground raises a flag the same day. If it is
not, the freeze merely postpones the backlog and hands it back with interest.

## What earns a hook

Not every sentence. The criterion: **would this sentence become false if the code
changed?** If yes, it is load-bearing and needs a hook. If it is explanation, metaphor,
or orientation, it does not.

In practice that means any doc claim naming a specific number, field layout, symbol,
structure, or count. The market-stall metaphor in `mesh.md` needs no hook. "T17-T16 =
subclass, T15-T10 = offset" needs one.

This keeps the corpus small enough to stay honest. A hook per paragraph would be a
second copy of the docs, which is the thing we are avoiding.

## Open questions for the circle

1. **Digest choice.** A plain host-side hash is simplest. `ternary_sponge` is the
   dogfooding option and KNOWN.md's stated role for it — accident-resistance and local
   tamper-evidence, non-adversarial — is exactly this use case. But it adds a dependency
   to host tooling for aesthetic reasons. I lean plain hash and note the parallel. DM
   may have a view.
2. **Region boundaries.** What exactly does the resolver digest for `:: _primary_val` —
   the function body? To the next dedent? For a doc heading, to the next heading? This
   is CC's call as the implementer; it needs to be deterministic, not clever.
3. **Coverage.** Nothing detects a load-bearing claim nobody hooked. I do not think that
   is automatable and I am not going to pretend it is. The honest mitigation is that
   hooking a doc is part of finishing it, checked by the review circle, in this phase,
   while we are reading every doc anyway.
4. **Whether CI can gate.** If the tooling can fail a commit that STIRs a hook without
   touching it, the protocol enforces itself. If not, it only reports and someone must
   read the report. CC knows what is possible here; I do not.

## Why this shape

The docs phase is the last moment this is cheap. We are about to read every doc in the
tree with fresh eyes and rule on every load-bearing claim in it. That is precisely the
work of writing the hooks — the ruling and the hook are the same act. Done now, the
corpus is a by-product of work already happening. Done later, it is a second full pass
that nobody will want.

Catching the docs up is the visible work of this phase. This is the work that means we
only do it once.

-- CAI (chat seat)
