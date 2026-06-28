# Design Memos — TernOO-5500FP / FlowCode

Architectural design memos for the project. Each captures decisions, locked design space, and the rationale behind them. They are *living* references — updated as the project evolves — and are the canonical source of architectural intent. Code is the canonical source of *what's built*; these memos are the canonical source of *what was decided and why*.

Memos should be committed to the repo and updated when decisions change. Don't let them go stale — that's the documentation drift that caused the Word Spec v0.1 problem.

## Reading order for new readers

If you're new to the project (or returning after a break), read in this order:

1. **TernOO-Language-Audit.md** (`private/`) — Authoritative catalogue of language constructs. Word types, opcodes (RNODE/REDGE), symbol families, mesh mechanics. Start here for "what is TernOO actually."

2. **CAI-Named-Handler-Auto-Wiring-Design.md** — How GUI widgets and Flow terminators connect (by name agreement, not visual wires). Foundational for Phase 7c work.

3. **CAI-Sheet-Leg-Design-Memo.md** — The third leg of the FlowCode trinity. Spreadsheet as canonical computation surface. Stage 8.

4. **CAI-Shell-Tab-Skeleton-Design.md** — Command composition as a fourth surface. Builds on Sheet + Pocket UX. Stage 9.

5. **CAI-FlowCode-File-Extensions-Policy.md** — `.fc` / `.flow` / `.gui` / `.sheet` extensions and what each contains.

## What's in each memo

### CAI-Named-Handler-Auto-Wiring-Design.md
Phase 7c. The principle that GUI / Flow / Sheet / Shell are *separate surfaces* connected by *named references*, not unified canvases. Borland VB/C++ Builder precedent. Pocket UX for nested scopes. Implementation phases 7c-1 through 7c-4.

### CAI-Sheet-Leg-Design-Memo.md
Stage 8. Cells as `cell_*` RNODE family. Hybrid formula evaluation (compile-time static + runtime dynamic). Excel-compatible syntax with TernOO-native extensions. Non-Turing-complete by design. Ten implementation phases 8-1 through 8-10.

### CAI-Shell-Tab-Skeleton-Design.md
Stage 9. Commands as `cmd_*` RNODE family. Pipes as typed FLOW edges. Parameter sheets via Pocket UX. **Hard discipline: no file I/O commands until native filesystem exists.** First useful commands are pure-data (text, math, list, dialogs, control flow). Seven phases 9-0 through 9-6.

### CAI-FlowCode-File-Extensions-Policy.md
File extension policy. `.fc` canonical, partial saves for subsystem-only files, `.ternoo` deprecation with backward compat. Implemented as Bundle 20.

### CLAUDE.md (repo root, not in this directory)
Standing instructions for Claude Code sessions. Output protocol, addressing conventions, screen-reports-as-ground-truth, project context, key reference documents.

## Status as of 28 June 2026

- Phase 7b: complete (native PIGART rendering, FlowCode→t5asm pipeline)
- Phase 7c-1: complete (name property)
- Phase 7c-2 through 7c-4: pending
- Stage 8: not started
- Stage 9: not started
- Stage 10 (native filesystem): conceptual, no memo yet

When Stage 10 (filesystem) is ready for design work, a new memo joins this directory.

---

*Last updated: 28 June 2026*
