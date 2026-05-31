# TernOO-5500FP Session Handoff
## 31 May 2026, Adelaide
## For: Next Claude thread / Claude Code / CoWork

---

## Who Is Stevo

Adelaide-based FOSS developer, vibe coding method (AI-assisted iterative
development). GitHub: SkepticusMaximus. Works on Linux Mint 22.3, ASUS X550LA,
Claude Desktop. Casual/humorous style. Strong opinions on workflow — read
WORKFLOW.skill.md in the repo root before doing anything.

**Critical protocol:** NEVER suggest Stevo hasn't saved a file. The fault
is always in the edit. Claude Desktop's download dialog prompts for confirmation
before overwriting — if a file is broken after being provided, check the patch
logic first, second, and third. Only raise a save issue after exhausting every
other explanation.

---

## Repository

**URL:** https://github.com/SkepticusMaximus/TernOO-5500FP
**Local:** `/home/steven/dev/SkepticusMaximus/TernOO-5500FP/`
**Latest commit:** `f70c991` — feat: v0.5.3 — process builtins, COMPARE works,
  tk_parent dialogs, filename in title
**Total commits:** 28

---

## Project in One Paragraph

TernOO-5500FP is a visual programming IDE (FlowCode) and TernOO object
architecture running on the 5500FP balanced ternary CPU. The flowgram IS the
program — no separate source file. TernOO words (24-trit, 2+4+18 format) are
the native data type. Python/tkinter is scaffolding only. The goal is a
self-hosting visual environment on native ternary hardware where Python becomes
obsolete through obsolescence, not prohibition.

---

## Current Versions

| Component | Version | File |
|-----------|---------|------|
| FlowCode IDE | v0.5.3 | `FlowCode/flowcode.py` |
| TernOO Interpreter | v0.3.0 | `5500fp/ternoo_interpreter.py` |
| NEURAL Engine | — | `5500fp/ternoo_neural.py` |
| PIGART Renderer | — | `5500fp/ternoo_pigart.py` |
| Assembly Bridge | — | `5500fp/ternoo_asm_bridge.py` |
| GristMill | — | `5500fp/ternoo_gristmill.py` |
| Emulator | v03 | `5500fp/5500fp_ternoo_v03.py` |

---

## Six Milestones — All Skeletonised Today

### 1. I/O Dispatch ✓ WORKING
- Interpreter dispatches I/O symbols by T21/T20 subclass
- prompt-read: tkinter `simpledialog.askstring` parented to FlowCode root
- prompt-write: tkinter `Toplevel` dialog parented to FlowCode root
- `tk_parent=root` passed from FlowCode to interpreter to avoid double Tk root
- Status: fully working, dialogs close cleanly

### 2. NEURAL Forward-Pass Engine ✓ SKELETON
- `TernOOBrain`, `NeuralUnit`, `NeuralConnection` classes
- `FlowCodeBrain` trained on 4 FlowCode canvases
- `predict_next(type)` blends learned weights + GristMill structural grammar
- `predict_sequence(start, length)` generates valid program structures
- Returns tuple `(predicted_type, confidence_str)` e.g. `('process', 'learned:3+grammar')`
- Gemini brain files converted to TernOO format: `ternoo_word_brain_ternoo.json`

### 3. PIGART Renderer ✓ SKELETON
- Phase 1: ASCII terminal canvas — correct shapes for all symbol types
- Phase 2: tkinter window — MAP words drive 2D geometry directly
- All AgeTest2 symbols render correctly with correct shapes and colours
- Auto-sizes window to canvas content
- `flowcode_to_pigart()` converts FlowCode JSON → scene graph
- Run: `python3 5500fp/ternoo_pigart.py --tk`

### 4. Assembly Bridge ✓ SKELETON + VALIDATED
- Emits valid Tlang assembly from FlowCode JSON
- AgeTest2.json → AgeTest2.tasm → AgeTest2.hex (compiled by Claudio's Tlang)
- Tlang installed via Wine/PlayOnLinux at:
  `~/.PlayOnLinux/wineprefix/Tlang/drive_c/tlang.exe`
- Claudio's emulator also installed at same path as `emulator.exe`
- Emulator always executes from 0x0000 boot ROM — load address issue
  unresolved, needs Claudio's docs or forum

### 5. FlowCode Brain ✓ WORKING
- 🧠 Learn button: trains on current canvas, saves `flowcode_brain.json`
- 💡 Suggest button: shows `Brain suggests: after X → Y (learned:N+grammar)`
- Brain auto-loads on startup from `5500fp/flowcode_brain.json`
- Trained on: AgeTest.json, AgeTest2.json, TerminatingFlow.json, TestFlow.json

### 6. GristMill ✓ SKELETON
- `MMID` class: MAP word as generative coordinate
- `MMOE` class: synthesised from MMID, not stored
- `GristMill` class: `synthesise()`, `proximity()`, `successors()`, `compose()`,
  `from_flowcode()`
- Widget type registry: terminator, io_read, io_write, process, decision,
  widget_window, widget_panel, widget_button, widget_label, widget_input
- AgeTest2 derives 6 MMIDs → synthesises 6 MMOEs → 12 TernOO words
- Proximity search returns all-zeros (coordinate spread bug — needs fix)
- Run: `python3 5500fp/ternoo_gristmill.py`

---

## FlowCode Canvases

| File | Symbols | Description |
|------|---------|-------------|
| AgeTest.json | 5 | Basic age test, old symbol types |
| AgeTest2.json | 6 | Proper symbols: Terminator START/END, I/O for prompts |
| AgeTest3.json | 7 | AgeTest2 + COMPARE 18 process — WORKING conditional branch |
| TerminatingFlow.json | 3 | Minimal terminating flow |
| TestFlow.json | 4 | Basic test flow |

**AgeTest3 is the current reference program.** It works end-to-end:
START → GET AGE (prompts user) → COMPARE 18 (pushes trit -1/0/+1) →
AGE TEST (routes on trit) → UNDER AGE or ACCEPT AGE (displays result) → END

---

## Key Architecture Decisions (Why, Not Just What)

**I/O Subclass Matrix:** T21=channel type (-1=file, 0=stream, +1=prompt),
T20=operation (-1=read, 0=bidir, +1=write). Bootstrap uses label keywords
until palette exposes T21/T20 directly. This is experimental — in companion doc.

**Process Builtins:** COMPARE/CHECK/CMP keywords trigger ternary comparison,
returning +1/0/-1 trit. In native TernOO this is a single CMP instruction.
Python implements it here as scaffolding. Label pattern: `COMPARE 18` means
compare stack top against 18.

**Decision Routing:** Decision symbols read the top of eval_stack. Positive
(+1) → first outgoing edge, negative (-1) → second edge, zero (0) → default.
The `default_output` field is the fallback if stack is empty.

**tk_parent:** Always pass `tk_parent=root` when creating TernOOInterpreter
from FlowCode. Without it, dialogs create a second Tk root and deadlock.

**GristMill is generative, not a repository.** Objects are computed from MMID
coordinates by GHOST — not stored, not downloaded. The MMID is a thought about
the MMOE. Set of possible objects is unbounded. This is the key architectural
insight from today's session.

---

## Toolchain

| Tool | Location | Notes |
|------|----------|-------|
| Tlang assembler | `~/.PlayOnLinux/wineprefix/Tlang/drive_c/tlang.exe` | Wine 6.17 amd64 |
| Claudio's emulator | `~/.PlayOnLinux/wineprefix/Tlang/drive_c/emulator.exe` | Same prefix |
| Run Tlang | `WINEPREFIX=~/.PlayOnLinux/wineprefix/Tlang wine tlang.exe -l assembly input.tasm -o out.hex` | |
| Run emulator | `WINEPREFIX=~/.PlayOnLinux/wineprefix/Tlang wine emulator.exe --debug file.hex` | Always halts at 0x0000 — load address bug |

---

## Known Issues / Open Threads

### High Priority

**1. UNDER AGE dialog shows `-1` not a message**
The trit value is being displayed instead of a human-readable message.
Fix: `_io_prompt_write` should display a label from the symbol, not the raw
stack value. Or: add a DATA word to the symbol carrying the message text.

**2. Suggest button AttributeError**
`do_suggest` in flowcode.py has old `nxt.upper()` call but `predict_next`
now returns a tuple `(type, confidence)`. Fix: `nxt, conf = predict_next(tok)`.
The fix was in an output file that conflicted — needs one clean apply.

**3. GristMill proximity all-zeros**
The Y/Z coordinate spread in MMID._compute() produces coordinates that are
too close together. The `y_range` and `z_range` values in MMOE_TYPES need
recalibrating so different types occupy distinct octree regions.

**4. Emulator load address**
Claudio's emulator always executes from 0x0000 (boot ROM). Our hex needs
either a load address record or a specific entry point directive. Needs
Claudio's docs or forum post.

### Medium Priority

**5. AgeTest2 still has no COMPARE symbol**
AgeTest3.json has the working COMPARE 18. AgeTest2 should either be updated
or left as the "before" reference. Decision pending.

**6. ACCEPT AGE/UNDER AGE should display meaningful messages**
Currently displays the raw trit or age value. Should say "Welcome — you are
old enough" / "Sorry — come back when you're older". This requires the I/O
symbol to carry message text in a DATA word pocket.

**7. `!learn` macro system**
Discussed but not implemented. I/O symbols with `!learn` prefix should
trigger training when the interpreter visits them. Connects the Gemini
`!learn_clipbd` / `!learn_temp` work to the new FlowCodeBrain architecture.

### Low Priority / Future

**8. Collapsible palette sections**
I/O sub-types (prompt-read, prompt-write, file-read etc.) should be distinct
palette entries in a collapsible section.

**9. Widget MMOEs**
GristMill widget type registry exists but isn't trained into FlowCodeBrain yet.
Next step: add `widget_*` symbols to the FlowCode vocabulary and train.

**10. Spreadsheet/pockets**
Stevo's idea: symbol properties dialog shows live DATA word values as cell
references (like a spreadsheet). Pockets in symbols carry DATA words with
live values. No separate spreadsheet tool needed — it emerges from the
symbol architecture.

**11. Bootstrap FOSS code via assembler**
Discussed: LibreOffice Calc (LGPL) or GTK widgets as TernOO MMOEs via the
assembly bridge. Interesting but long-term — grow from primitives first.

---

## Opening Prompt for Next Thread

```
Continuing TernOO-5500FP development. Repo: https://github.com/SkepticusMaximus/TernOO-5500FP
Latest commit: f70c991 (28 commits total). Please git pull and read WORKFLOW.skill.md first.

Current state: FlowCode v0.5.3, all six milestones skeletonised (I/O dispatch,
NEURAL engine, PIGART renderer, assembly bridge, FlowCode brain, GristMill).
AgeTest3.json runs end-to-end with real conditional branching driven by ternary
trit comparison.

Priority fixes needed:
1. do_suggest AttributeError: nxt.upper() — predict_next returns tuple now
2. UNDER AGE dialog shows raw trit -1 instead of message text
3. GristMill proximity all-zeros — coordinate spread bug in MMID._compute()

After fixes: wire !learn macro system, then Symbol pockets/DATA words for
message text in I/O symbols. See HANDOFF-TernOO-5500FP-31May2026.md in outputs.
```

---

## Claude Code / CoWork TODO List

The following tasks are suitable for autonomous execution with Claude Code
or CoWork. Each is self-contained, has clear acceptance criteria, and doesn't
require Stevo's input during execution.

### CC-01: Fix do_suggest tuple error
**File:** `FlowCode/flowcode.py`
**Find:** `nxt = _brain_instance.predict_next(tok)` and `nxt.upper()`
**Fix:** `nxt, conf = _brain_instance.predict_next(tok)` and update the
status/print lines to use `nxt` and `conf` separately.
**Test:** Run FlowCode, select a symbol, click Suggest — should show
`Brain suggests: after terminator → IO_READ (learned:1+grammar)` in status bar.

### CC-02: Fix UNDER AGE / ACCEPT AGE display text
**File:** `5500fp/ternoo_interpreter.py`
**Find:** `_io_prompt_write` — currently displays raw stack value as message
**Fix:** Display `f"{node.label}: {msg}"` so the dialog title is the symbol
label and the body shows a meaningful message. Also: if `msg` is a trit
(-1, 0, +1) convert it to `"Access denied"` / `"Adult Supervision Required"` / `"Access granted"`
OR better, pop the previous stack value (the age) and display that.
**Test:** Run AgeTest3, enter 17 → UNDER AGE dialog should show the age (17)
not the trit (-1).

### CC-03: Fix GristMill proximity search
**File:** `5500fp/ternoo_gristmill.py`
**Find:** `MMOE_TYPES` y_range and z_range values, and `MMID._compute()`
**Fix:** Spread the type regions so each type occupies a distinct octree
area. Flowgram types (terminator, io_read, io_write, process, decision)
should be in one region, widget types in another, with clear separation.
**Test:** Run `python3 ternoo_gristmill.py` — proximity output should show
non-zero distances between different types, with same-type distances near zero.

### CC-04: Retrain brain on AgeTest3
**File:** `5500fp/flowcode_brain.json`
**Action:** Run `python3 ternoo_neural.py --train` from the `5500fp/` directory
— this picks up all FlowCode JSON files including AgeTest3.json which has
the COMPARE 18 process symbol. Commit the updated `flowcode_brain.json`.
**Test:** Weight matrix should now show `process → decision` with weight 4+
(AgeTest3 adds another process→decision transition).

### CC-05: Add !learn macro I/O symbol type
**Files:** `5500fp/ternoo_interpreter.py`, `FlowCode/flowcode.py`
**Design:** I/O symbols whose label starts with `!learn` trigger training
instead of prompting. The interpreter visits the symbol, reads whatever is
on the eval stack, calls `_brain_instance.train_on_canvas()` or a new
`train_on_value()` method, and continues execution.
**Implementation:**
- In `io_subclass()`: add detection for `!learn` prefix → returns special op code
- In `_io_dispatch()`: handle `!learn` → call brain training with stack value
- In FlowCode: add `!learn` to the write_hints so it doesn't prompt
**Test:** Draw a flow with `!learn_clipbd` I/O symbol, run it — terminal
should show `[Brain] learned from clipboard` and `flowcode_brain.json` updated.

### CC-06: Update companion doc
**File:** `docs/TernOO-5500FP-Companion.md` (local only — gitignored)
**Action:** Add Part F entries for:
- Today's six milestone skeletons with dates and commit hashes
- GristMill generative architecture insight (objects computed not stored)
- Process builtin dispatch design rationale
- I/O subclass matrix confirmed working
**Note:** This file is gitignored — changes stay local only.

### CC-07: Generate AgeTest2.tasm and AgeTest3.tasm
**File:** `5500fp/ternoo_asm_bridge.py`
**Action:** Run:
```
cd 5500fp
python3 ternoo_asm_bridge.py ../FlowCode/AgeTest2.json --out AgeTest2.tasm
python3 ternoo_asm_bridge.py ../FlowCode/AgeTest3.json --out AgeTest3.tasm
WINEPREFIX=~/.PlayOnLinux/wineprefix/Tlang wine ~/.PlayOnLinux/wineprefix/Tlang/drive_c/tlang.exe -l assembly AgeTest3.tasm -o AgeTest3.hex
```
Commit both .tasm and .hex files.
**Test:** AgeTest3.hex should compile without errors.

---

*Handoff generated: 31 May 2026, Adelaide*
*Session duration: ~14 hours (11:30am – 1:30am next day)*
*Commits this session: 28 (from 8669cc7 to f70c991)*
