# Design Memo Index — TernOO-5500FP

Annotated index of every design memo, for the documentation phase. See
`README.md` for the recommended reading order and the memos' role (canonical
source of *what was decided and why*; code is canonical for *what's built*).

**Currency legend:** **Current** = decisions still hold and match the code ·
**Implemented** = design landed in code (memo remains the rationale of record) ·
**Living** = continuously updated · **Superseded/Historical** = kept for context.

| File | Summary | Date | Currency |
|---|---|---|---|
| `README.md` | Reading order + role of the memos (canonical intent vs canonical build). | — | **Current** |
| `CAI-Named-Handler-Auto-Wiring-Design.md` | How GUI widgets and Flow terminators connect by *name agreement* (not visual wires); the foundation of the whole Phase 7c arc, incl. Ctrl+click navigation. | 28 Jun 2026 | **Implemented** (7c-1 → 7c-4b all landed). Architectural intent still authoritative. |
| `CAI-Sheet-Leg-Design-Memo.md` | The Sheet leg of the Trinity — spreadsheet as a canonical computation surface (Stage 8). Supersedes the earlier exploratory `CAI-Spreadsheet-Leg-Design-Sketch.md`. | 28 Jun 2026 | **Implemented** (Sheet formulas run; Stage 8-6 cell↔port binding landed). Current. |
| `CAI-Shell-Tab-Skeleton-Design.md` | The Shell tab — commands as flow symbols with Pockets, pipes as FLOW edges (Stage 9). Command catalogue deferred to implementation (now realized: 27/28 runnable). | 28 Jun 2026 | **Implemented** (commands compile + run; typed pipes on Connectors). Current, with the "no host FS" discipline still in force. |
| `CAI-FlowCode-File-Extensions-Policy.md` | `.fc` / `.flow` / `.gui` / `.sheet` extension policy. Decision-locked. | 28 Jun 2026 | **Current** (policy; `.fc` is the composite design format in use). |
| `CAI-Compiler-Constraints.md` | Living log of compiler/ISA gotchas discovered while building. Finding 1: only R0–R40 are instruction-addressable. Finding 2: assembler inline-comment mis-parse (FIXED). Finding 3: single-R80 hazard → return-address stack (FIXED). | ongoing | **Living** — append new gotchas here. Current. |

## Referenced-but-not-in-this-folder

- `CAI-Spreadsheet-Leg-Design-Sketch.md` — the exploratory precursor to the Sheet
  memo. **Superseded** by `CAI-Sheet-Leg-Design-Memo.md`; not tracked here (if a
  copy exists it is historical only).
- `TernOO-Language-Audit.md` (in gitignored `private/`) — the authoritative
  word/opcode/ISA catalogue. Cited first in the reading order; §7.7 documents the
  return-address mechanism. **Current** (local-only reference).

## Notes for the documentation phase

- All five architectural memos are **28 June 2026** office-mode memos that have
  since been implemented across the last week's bundles. They remain accurate as
  *intent*; where the built behaviour extended or refined the memo (e.g. the
  Shell command catalogue, the expr-driven interior semantics of entry/exit
  ports), the code + `docs/KNOWN.md` are the up-to-date detail.
- Stale-doc risk to watch (per the README's own warning): the **Word Spec v0.1**
  (`docs/TernOO-5500FP-Word-Spec-v0.1.md`) is two revisions behind the
  implemented 2+4+18 / 9-primary format — flagged in the Language Audit, not yet
  reconciled. See `docs/KNOWN.md`.
