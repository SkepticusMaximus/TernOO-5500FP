# TernOO-5500FP — Development Workflow Skill
## Claude + Stevo Collaboration Protocol

**Created:** 31 May 2026, Adelaide
**Authors:** Stevo (SkepticusMaximus) + Claude (Anthropic)
**Scope:** All TernOO-5500FP development sessions

---

## Core Workflow Rules

### Git & Commits
- Never assume a push has happened without seeing terminal output confirming it
- Always provide commit commands in a code block — Stevo pastes and runs them
- Always read terminal output carefully before responding to it
- Stevo provides push confirmation; Claude tracks version numbers
- No git clutter — don't suggest intermediate commits for work-in-progress

### Code Generation
- Always build from the committed git base, never from previous session outputs
- Verify with syntax check and feature grep before presenting any file
- Each functional block gets a header comment: date (friendly format), author, purpose
- Timestamps format: `31 May 2026, Adelaide`

### Companion Doc
- Every code block addition gets a mirrored entry in the companion doc
- Same timestamp, same block name, brief design rationale
- The companion is the *why*, the code is the *what*

### Questions
- Don't barrage — one question at a time, pick the most important
- More research is better than more questions

---

## Versioning

Semantic versioning: `MAJOR.MINOR.PATCH`

- **PATCH** — fixes that don't add features (e.g. confirm-on-clear: 0.5.0 → 0.5.1)
- **MINOR** — new features added (e.g. Terminator symbol: 0.4.x → 0.5.0)
- **MAJOR** — architecture breaks backward compatibility (rare; we are in 0.x)

Design goal: when FlowCode and GristMill are properly implemented, there will
be one final MAJOR version bump — after which every edit is backward and forward
compatible. The last MAJOR version is the one that makes MAJOR versions obsolete.

We are currently at **v0.5.1** (FlowCode IDE) and **v0.2.2** (interpreter).

---

## Prior Art Policy

Work from other AI sessions (Gemini, previous Claude instances) is treated as
prior art, not waste. Before dismissing or replacing any existing code, read it
and understand what architectural problem it was solving. The Gemini MMIO
clipboard implementation (0x6000 register, `!learn_clipbd`) directly informed
the I/O subclass matrix design. That's how it should work.

---

## I/O Architecture (Current Working Model — 31 May 2026)

Two orthogonal axes for the UDP subclass trits on I/O symbols:

```
T21 — Channel type:   −1 = file        0 = stream (network/pipe/IPC)   +1 = prompt (human-facing)
T20 — Operation:      −1 = read/listen  0 = bidirectional/passthrough   +1 = write/send/respond
```

Status: experimental — held in companion doc until prototype validates it.
The Gemini MMIO clipboard work at 0x6000 is the reference prototype for
`(+1, −1)` prompt-read behaviour.

---

## Module Block Header Format

Every new code block should open with:

```python
# ── [BLOCK NAME] ──────────────────────────────────────────────────────────────
# Added: 31 May 2026, Adelaide
# Author: Stevo + Claude
# Purpose: [one line]
# Companion: docs/TernOO-5500FP-Companion.md § [section name]
```
