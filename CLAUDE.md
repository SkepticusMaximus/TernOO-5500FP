# CLAUDE.md — Standing Instructions for Claude Code Sessions

> Place this file at the repo root. Claude Code reads it automatically at session start.

## Who I am

I am Stevo. Address me by name, second person. I'm the captain and architect of TernOO-5500FP — a 24-trit balanced-ternary computing architecture with a visual programming environment called FlowCode. I have 35+ years of GUI/development experience.

When I report what I see on my screen, treat that as **ground truth**. If I say something is missing or broken, investigate accordingly — don't propose that I might have missed a window or hidden output. Screen observations are not up for debate.

## How we work

I am the captain. I set pace, scope, and direction. You execute against the spec I provide and use your judgment on implementation specifics that aren't locked.

I gate **work**, not housekeeping. "Gating" means I review the result and decide whether to keep, change, or build on it. It does NOT mean I issue manual instructions for every commit, push, file move, or repo-maintenance task. Those are yours to handle on the fly.

You make engineering calls in the office. CAI (in the Claude.ai chat) makes design calls and produces specs. I review outputs and discuss with CAI when something needs a decision.

If something seems wider than the spec described, flag it rather than silently expanding scope. If something seems narrower (already done, no-op), flag that too rather than going through the motions.

## Repo maintenance — your responsibility

**Commits**: When a bundle's acceptance criteria are met and tests pass, commit the work. Don't wait for explicit instruction. The default is commit; the exception is when work is genuinely uncertain or you'd want CAI's review before locking it in — in that case, flag back rather than commit.

**Commit hygiene**: Each logical piece of work gets its own commit when they're independent. Interdependent restructures commit atomically. Commit messages reference the spec file when relevant (`Phase 7c-2 — Auto-wiring per CC-Phase-7c-2-Auto-Wiring.md`).

**Pushing**: Push to `origin/main` (or the working branch) after committing unless I've told you not to.

**At session start**: Check for uncommitted work from prior sessions. If present, either commit it (if the acceptance criteria are clearly met from the prior session's report) or flag it back at the top of your session summary so I can resolve it.

**Branch hygiene**: Work on the working branch I've set up. Don't create branches unless I've asked.

## Output protocol

**Default**: When session work is complete, deliver the session summary as a **markdown code block in the chat window**. I want to copy-paste it forward without navigating file dialogs.

**Files**: For durable artifacts (specs, design memos, persistent reports) that I have explicitly asked you to save. Don't save reports to disk unless I've asked for a saved report.

**File location for explicit saves**: `private/` directory in repo root. Don't ask where to save — that's the convention.

**Brief over verbose**: I'd rather have a tight summary that captures the essentials than a comprehensive dump. If I want more detail I'll ask.

**Flags and notes go inside the report block**, never as separate chat messages outside it.

## Project context — TernOO-5500FP

- **Repo**: `~/dev/SkepticusMaximus/TernOO-5500FP`
- **Architecture**: 24-trit balanced-ternary CPU (5500FP), 81 registers, word format 2+4+18 (T23 / T22-T19 / T18-T0)
- **9 primaries** in the word architecture (per Language Audit): DATA, EXEC, MAP, NEURAL, I-O, plus reserved CRYPTO, OPEN_B, POOL, and one more — see `private/TernOO-Language-Audit.md` for the canonical reference
- **Tabs in IDE**: Flow | GUI | Shell | Connectors | Lingo
- **Status**: Phase 7b closed. Phase 7c-1 and 7c-2 complete (`name` property + name-based auto-wiring). Currently building toward Phase 7c-3 (Ctrl+click cross-tab nav), Phase 7c-4 (Pocket UX), Stage 8 (Sheet), Stage 9 (Shell command set), Stage 10 (native filesystem). Plus assorted UX polish bundles
- **Test commands**:
  - `cd 5500fp && python3 widget_lib.py --test`
  - `python3 ternoo_gristmill.py --accept`
  - `python3 5500fp_ternoo_v03.py --test`
  - `python3 -m unittest test_compile_to_t5asm`
  - `python3 -m unittest test_stage6_workflow`
  - `python3 -m unittest test_gristmill_tab`
  - `python3 -m unittest test_name_property`
  - `python3 -m unittest test_auto_wiring`
  - `cd ../NASM-TernOO-5500FP-Emulator/c_emulator && ./5500fp --test`

## Key reference documents

- `private/TernOO-Language-Audit.md` — authoritative reference for word types, opcodes (RNODE/REDGE), symbol families, mesh mechanics
- `docs/design/CAI-Named-Handler-Auto-Wiring-Design.md` — Phase 7c architecture
- `docs/design/CAI-Sheet-Leg-Design-Memo.md` — Stage 8 design
- `docs/design/CAI-Shell-Tab-Skeleton-Design.md` — Stage 9 design (note: Shell tab is now the three-pane builder; the canvas-based view is the Connectors tab)
- `docs/design/CAI-FlowCode-File-Extensions-Policy.md` — `.fc` / `.flow` / `.gui` / `.sheet` extension policy
- `private/CC-*.md` — bundle specs from CAI

When a dispatch references a spec, read it first.

## What never to do

- Don't suggest I'm missing a window, hidden output, or some UI element I haven't found. Treat my screen reports as ground truth.
- Don't refer to me in third person as "the user." I'm Stevo.
- Don't propose timelines, deadlines, or "this should take N weeks" framings. Pace is exclusively my call.
- Don't add scope to a bundle silently. Flag, don't expand.
- Don't reverse a correct earlier decision because of an emotional appeal or pressure. If something was rejected for a real reason, the reason still holds.
- Don't use the host filesystem for TernOO-internal storage when there's a native path. We're weaning off the host FS deliberately, with gratitude for its hospitality.
- Don't leave completed work uncommitted waiting for explicit commit instructions. Commit is the default.

## What's always welcome

- Honest pushback when you see something I'm missing
- "This bundle is a no-op because X is already done" (Bundle 15 was a clean example)
- "The scope you've described actually requires Y to be done first" (flag, don't bull through)
- Engineering improvements beyond the spec when they're clearly correct (Phase 7b-4's CALL/RET pattern, Bundle 24's atomic commit decision, Phase 7c-2's one-live-hook approach)
- Honest reporting of what was actually broken when the spec's hypotheses don't match reality (Bundle 19's "stuck drag from missed ButtonRelease" was better than the spec's "missed conversion" guess)

## The standing rule above all else

If something is ambiguous, ask. If something is obviously implied by what I've said, do it. The middle ground — guessing at scope or making architectural decisions that should be mine — is where bumbling happens. When in doubt, surface the question clearly with the trade-off named.

Housekeeping is never the middle ground. If a commit needs to happen, commit. If files need to move into place, move them. If the previous session left work uncommitted, commit it. Don't pass mundane chores back up the chain.

---

*Standing instructions. Read at every CC session start. Last updated 29 June 2026 — clarified commit default, repo housekeeping as CC's responsibility.*
