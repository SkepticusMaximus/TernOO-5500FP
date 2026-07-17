# docs-corpus INDEX — the map

Entry point for the corpus. Every file gets one line: its path and a one-line
"what's in it", so a fresh cai-worker (or a new CAI thread) can find the right
slice to read without loading the whole corpus.

| Path | What's here |
|------|-------------|
| `README.md` | The bench charter (CC, 2026-07-16): what this corpus is for, and the rule that POBOX is the mailbox, this is the brain. |
| `INDEX.md` | This map. Keep it current — it is how a fresh reader finds the slice it needs. |
| `tools/corpus_resolve.py` | The sync-protocol resolver. Lints hooks, resolves POINTERs against the tree, digests the region, reports HOLDS/STIRRED/DEAD. Tested; exit codes are CI-gateable. Bench tooling pending promotion. |
| `decisions/2026-07-17-sync-protocol-implemented.md` | Sync protocol v0.1 implemented and proven against the live tree. Test results, the GROUND value for nine-primary-map, and the one-line change to `docs/CORPUS.md` awaiting the captain's eye. |

## Naming caution

Two things in this project are called "corpus" and they are NOT the same:

- **`docs/CORPUS.md`** — the hook index. Pointers, verdicts, GROUND digests.
  Tracked, adopted, in force. The trigger layer.
- **`private/docs-corpus/`** (here) — the workbench and the brain. Decisions,
  rationale, canon, drafts, tooling. Not canon; nothing here is the record.

A fresh reader will conflate them. Flagged for the review circle: one of them
may want renaming before the confusion sets like concrete.
