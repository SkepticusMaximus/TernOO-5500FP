# docs-bench INDEX — the map

Entry point for the bench. Every file gets one line: its path and a one-line
"what's in it", so a fresh cai-worker (or a new CAI thread) can find the right
slice to read without loading the whole bench.

| Path | What's here |
|------|-------------|
| `README.md` | The bench charter (CC, 2026-07-16; renamed per ruling 17/07): what this bench is for, and the rule that POBOX is the mailbox, this is the brain. |
| `INDEX.md` | This map. Keep it current — it is how a fresh reader finds the slice it needs. |
| `tools/corpus_resolve.py` | The sync-protocol resolver. Lints hooks, resolves POINTERs against the tree, digests the region, reports HOLDS/STIRRED/DEAD. Tested; exit codes are CI-gateable. Bench tooling pending promotion. |
| `decisions/2026-07-17-sync-protocol-implemented.md` | Sync protocol v0.1 implemented and proven against the live tree. Test results, the GROUND value for nine-primary-map, and the one-line change to `docs/CORPUS.md` awaiting the captain's eye. |
| `HANDOFF-to-next-CAI.md` | The predecessor seat's 317-line successor document (17/07, commit 50581ad0): gates, laws, tools, state, live work, the §8.3 three-defect finding. THE opening read for a new CAI seat — §9 first, then §1. (Relocated from the retired docs-corpus path by CC, 24/07.) |
| `drafts/2026-07-26-tmesh-otree-pigart-rundown-for-external-collab.md` | TMesh/OTree/PIGART mechanics rundown for external collaborators (DeepSeek), with public source links; flags the two captain-only open canon items. CC, 26/07. |
| `drafts/2026-07-27-vector-manifold-design-v0.1.md` | The vector-manifold spec (distributed training/weight-sharing over TMesh/OTree/PIGART): the captain's pipeline + the open questions to pin before code. For DeepSeek + the design seats. |

## Naming — RULED (captain, coordination order #1, ruling 4, 17/07/2026)

The collision this section used to flag is resolved by ruling:

- **`docs/CORPUS.md`** — the ONLY thing called "corpus". The hook index.
  Pointers, verdicts, GROUND digests. Tracked, adopted, in force.
- **`private/docs-bench/`** (here, renamed from `docs-corpus`) — the BENCH:
  workbench and brain. Decisions, rationale, canon, drafts, tooling.
  Not canon; nothing here is the record.

Rename executed by CC, 17/07/2026.
