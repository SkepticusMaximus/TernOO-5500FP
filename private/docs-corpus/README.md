# docs-corpus — CAI's context corpus for the documentation rebuild

A durable, written home for the deep context CAI carries (and inherited from its
lineage), so that:
  1. the cai-mailbox worker can do docs work from it — an understudy reading the
     master's notes — and
  2. that context survives thread death: any future CAI thread can inherit it.

This is "externalise the context to the ledger" made concrete. CAI's knowledge is
durable only to the extent it is written HERE.

## Protocol
- CAI (the chat) WRITES into this corpus during the docs phase: decisions,
  rationale, canonical facts, draft sections. Manual — gated on Stevo's visits;
  CAI pushes via its GitHub connector.
- cai-worker READS the relevant slice each run to do docs tasks. It cannot hold
  the whole corpus in one session, so INDEX.md must stay current — it is the map
  the worker (and any fresh reader) uses to find the right slice.
- POBOX stays separate: that is the mailbox for messages; this is the brain.

## Suggested starting structure (CAI: reshape freely — this is only a skeleton)
- INDEX.md     the map: every corpus file with a one-line "what's here"
- canon/       canonical facts CAI establishes as authoritative
- decisions/   design decisions + the reasoning behind them
- drafts/      doc sections in progress

Structure is the design seat's call. What matters: INDEX.md always lets a fresh
reader find what it needs, and anything load-bearing is written down, not left in
a chat only CAI remembers.

— scaffolded by CC, 2026-07-16
