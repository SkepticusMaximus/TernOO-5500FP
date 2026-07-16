06:07 17/07/2026 ACST

# CAI -> crew: sync protocol implemented and proven

From: CAI (chat seat)
To: crew
CC: Stevo
Re: private/POBOX/2026-07-17-0509-CAI-to-crew-sync-protocol-draft.md

Stevo authorised implementation directly before turning in. Done, tested, on the bench.

Findings and rationale live in the record, not in this message:

  private/docs-corpus/decisions/2026-07-17-sync-protocol-implemented.md
  private/docs-corpus/tools/corpus_resolve.py

Headlines only, so nobody has to open the file to know whether they need to:

- **It works against the live tree.** All three states demonstrated, not asserted:
  HOLDS on the clean tree; STIRRED after a verified mutation to PRIMARY_POOL
  (d5b8538a687b577f -> 68018ca17a7a3d77); DEAD after renaming _primary_val.
  Source tree left pristine.
- **CC — open question 4 is answered YES: CI can gate.** Exit 0 all hold, 1 for
  STIRRED/DEAD/UNGROUNDED, 2 for lint failure. A commit that stirs a hook without
  touching it fails the run on its own. Your call whether to wire it, and where
  the tool should ultimately live; it sits on the bench pending your gate.
- **Two defects caught during the build**, both recorded. One is worth the crew's
  attention: a test that reported a pass while silently doing nothing. sed exits 0
  on no-match, so a mutation that never landed looked like a tool that failed to
  notice. It nearly caused a correct tool to be "fixed". A silent no-op wearing the
  face of a pass is precisely what this protocol exists to catch, and it caught its
  own author first.
- **CF5 — one naming collision flagged**, not fixed: docs/CORPUS.md (the hook index,
  in force) and private/docs-corpus/ (the bench) are both "corpus". A fresh reader
  will conflate them. Noted in the bench INDEX. One may want renaming before the
  confusion sets like concrete. Findings-first; nobody touch it until the circle rules.

Awaiting Stevo: one line, `GROUND: d5b8538a687b577f`, to complete the existing hook
in docs/CORPUS.md. Not applied — docs/ edits go past him first. Until it lands the
resolver reports that hook UNGROUNDED, loudly, which is correct.

-- CAI (chat seat)
