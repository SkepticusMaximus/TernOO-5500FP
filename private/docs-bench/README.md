# docs-bench — CAI's workbench + context brain for the documentation rebuild

Named by the captain's ruling (coordination order #1, ruling 4, 17/07/2026):
**"corpus" belongs to `docs/CORPUS.md` alone** — the hook index in force.
This folder is the BENCH: the free-fire workbench and the durable brain.

A durable, written home for the deep context CAI carries (and inherited from its
lineage), so that:
  1. the cai-mailbox worker can do docs work from it — an understudy reading the
     master's notes — and
  2. that context survives thread death: any future CAI thread can inherit it.

This is "externalise the context to the ledger" made concrete. CAI's knowledge is
durable only to the extent it is written HERE.

## Protocol
- CAI (the chat) WRITES into this bench during the docs phase: decisions,
  rationale, canonical facts, draft sections — free-fire, no gate.
- cai-worker READS the relevant slice each run to do docs tasks. It cannot hold
  the whole bench in one session, so INDEX.md must stay current — it is the map
  the worker (and any fresh reader) uses to find the right slice.
- POBOX stays separate: that is the mailbox for messages; this is the brain.
- THE GATE sits at the border: nothing lands in real `docs/` without walking it
  through the captain, and the corpus resolver must HOLD (ruling 2 — CC's
  pre-commit gate enforces the resolver on any commit touching `docs/`).

## Structure
- INDEX.md     the map: every bench file with a one-line "what's here"
- canon/       canonical facts CAI establishes as authoritative
- decisions/   design decisions + the reasoning behind them
- drafts/      doc sections in progress
- tools/       bench tooling (corpus_resolve.py — the sync-protocol resolver)

Structure is the design seat's call. What matters: INDEX.md always lets a fresh
reader find what it needs, and anything load-bearing is written down, not left in
a chat only CAI remembers.

— scaffolded by CC 2026-07-16; renamed docs-corpus → docs-bench per ruling, CC 17/07/2026
