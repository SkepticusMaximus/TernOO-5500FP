# Sync protocol v0.1 — implemented and proven

Date: 2026-07-17
Author: CAI (chat seat)
Authorised by: Stevo, directly ("go ahead and implement that"), 2026-07-17 ~05:50 ACST
Proposal: `private/POBOX/2026-07-17-0509-CAI-to-crew-sync-protocol-draft.md`

## What was built

`private/docs-corpus/tools/corpus_resolve.py` — stdlib only, 351 lines.

Reads a corpus file, lints every hook against the schema, resolves each POINTER
against the tree, digests the pointed-at region, compares to GROUND, reports.

    HOLDS    (+)  pointer resolves, GROUND matches
    STIRRED  ( )  pointer resolves, GROUND differs — re-rule
    DEAD     (-)  pointer will not resolve

Exit: 0 all hold; 1 STIRRED/DEAD/UNGROUNDED present; 2 lint failure.
That answers open question 4 from the proposal in the affirmative: **CI can gate.**
A commit that stirs a hook without touching it fails the run with a non-zero exit.

## Proven, not asserted

Run against the live tree, all three states demonstrated:

- HOLDS on the untouched tree — exit 0.
- STIRRED after a verified mutation to `PRIMARY_POOL`: `d5b8538a687b577f -> 68018ca17a7a3d77`, exit 1.
- DEAD after renaming `_primary_val`: "symbol(s) not found", exit 1.
- HOLDS again after restore. Source tree left pristine (`git status` clean).

Two real defects were caught during the build, both worth recording:

1. **The schema template parsed as a hook.** The example in CORPUS.md's header is
   structurally identical to a real hook; a machine cannot tell the example from
   the instance. Fixed by parsing only under the `## Hooks` heading. The lesson
   generalises: any format that documents itself in its own syntax needs a
   section boundary, not cleverness, to separate specimen from subject.

2. **A test that lied.** The first STIRRED test reported HOLDS. The tool was
   right; the test was broken — `sed` silently matched nothing (the real source
   reads `_primary_val(+1,+1)`, the pattern had `(+1, +1)`) and `sed` exits 0 on
   no-match, so the fallback never fired. The mutation never landed. This nearly
   caused a correct tool to be "fixed". It is exactly the failure the protocol
   exists to catch — a silent no-op wearing the face of a pass — and it caught
   the author first. Every mutation in the final test asserts that the file
   actually changed before drawing any conclusion.

## Decisions taken while building

- **Digest: sha256, truncated to 16 hex (64 bits).** Plain host-side hash, not
  `ternary_sponge`. This is accident-detection on the host, non-adversarial;
  64 bits is ample and it adds no dependency. The sponge parallel is noted in the
  proposal and remains the circle's to rule. I lean plain hash.
- **Normalisation: line endings and trailing whitespace only.** Nothing cleverer.
  Indentation and blank lines are content. A whitespace-only edit will STIR a
  hook — a false positive, never a false negative. That asymmetry is deliberate:
  this tool may cry wolf, but it may never stay quiet.
- **GROUND required for SETTLED; optional for OPEN and STALE.** The risk lives
  where a claim asserts a fact. Open for the circle.
- **`--ground` flag prints the current digest** for a human ruling a hook. Noted
  in its own help text that a worker must never use it to clear a flag.

## Awaiting the captain's eye

One line to add to `docs/CORPUS.md`, completing the existing hook:

    GROUND: d5b8538a687b577f

That digest was computed by resolving the pointer against `master` — the same
resolution CF5 made from source and I re-made independently. With it, the hook
is complete under the protocol and the corpus lints clean. Without it, the hook
is UNGROUNDED and the resolver says so, loudly, which is the correct behaviour
and is what it currently reports.

Not applied: `docs/` edits go past Stevo first. It is a one-line change.
