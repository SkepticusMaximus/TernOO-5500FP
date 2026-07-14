# PERMISSIONS — repo write policy for the crew

**Set by Stevo (captain), 2026-07-14. Standing policy — not a dated message.**
Recorded here by CAI at the captain's instruction.

Defines who may WRITE where in the TernOO-5500FP repo, now that CC, CF5, and
CAI each have live read/write access via the Jentic GitHub connector.

## Read
- **CC, CF5, CAI** — the whole repo.

## Write (default scopes)
- **Everyone (Stevo, CC, CF5, CAI)** — `private/` and `private/POBOX/`, free read/write.
- **CC** — the whole repo.
- **CF5, CAI** — `docs/` (plus the shared `private/` above).

## Captain override
When Stevo is working directly with CAI or CF5, his request supersedes the
default: that agent may write whatever the present task asks or requires,
wherever it requires it, for the duration of that task.

## Permission is not process
This file says who CAN write where. It does not loosen the working disciplines
that say WHEN to write:
- Doc repairs go through the review circle (Stevo, CAI, CF5) — findings-first,
  no unilateral "fixes" to encountered documents.
- Code and canonical changes land at the captain's gate.
Write access is a reason to honour those disciplines on purpose, not a licence
to bypass them.

## Provenance note
Token-based API commits are authored as "Steven Cathery" (the token's account)
whichever agent wrote them. Attribution therefore lives in the commit MESSAGE
and in the FROM field of POBOX mail, never in the git author field.

— Recorded by CAI, per Stevo's ruling, 2026-07-14. ⚓
