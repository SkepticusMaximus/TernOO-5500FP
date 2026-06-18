# CWC Handoff — Post-Phase-6C File Format Deliberation

**From:** CWC  
**To:** CAI via Stevo  
**Date:** 16 June 2026  
**Re:** Unified save format and open-dialog UX — open questions surfaced during Phase 6C visual checks  
**Status:** Deliberation needed before Phase 6D or any further save/load work

---

## What triggered this

During Phase 6C visual checks, Stevo noticed:

1. The Open dialog in the FlowCode tab defaulted to filtering `.tgui` files and opened in the wrong directory — the files it needed to read (legacy `.json`) weren't visible.
2. The legacy `.json` filter was exposed as a named user-visible option, which felt like implementation noise rather than a UX choice.
3. More fundamentally: if Phase 6C's whole point is a single unified representation, why do the two tabs have different file type expectations at all?

CWC fixed the immediate directory default (`initialdir=_FC_DIR`) and removed the legacy filter entry (it remains auto-detected silently from the JSON content). But the deeper question was correctly escalated.

---

## The core question

**Phase 6C made the data model unified — flow symbols and GUI widgets now live in the same `word_stream`. The file format should reflect that. It currently does not, clearly.**

The `.tgui` extension was named for "TernOO GUI training" and was introduced for the GHOST Canvas. It has no connotation of flowcharts. A user looking at a file called `AgeTest3.tgui` has no idea it contains a flowchart; a user looking at `AgeTest3.json` has no idea it's a TernOO design file.

---

## Open questions for CAI decision

### Q1 — File extension

Options:
- **Keep `.tgui`** — lowest-friction, but the name is misleading now that it contains flowcharts too. Could update the description string to "TernOO design (*.tgui)".
- **New extension** — e.g. `.t55`, `.tgd` (TernOO GUI Design), `.ternoo`. Cleaner semantics; requires a migration note for existing `.tgui` files (trivial: just rename, format is identical).
- **CWC recommendation:** Pick a new extension that is neutral about whether the content is a GUI, a flowchart, or both. Something short. `.t55` has nice specificity (5500FP); `.tgd` is readable. Either works. The exact choice doesn't matter much; having one neutral name matters.

### Q2 — Should both tabs share one open/save dialog?

Currently: both GHOST Canvas and FlowCode tab call `gc_do_save()` / `gc_do_open()`. This is the right architecture — one file, one dialog. The problem is the dialog title says "Open GHOST design" and the filter says "TernOO GUI training", which sounds exclusively GHOST.

Proposed: rename dialog titles and filter descriptions to be tab-neutral. "Open TernOO design" / "TernOO design (*.tgui)" or whatever the new extension is. No structural change to the open/save code needed.

### Q3 — Legacy `.json` (old FCCanvas format)

CWC has implemented auto-detection: if the loaded JSON has no `tgui_version` key and its `symbols` have bare kind names (`"terminator"`, `"process"`, etc.), it's treated as a legacy FCCanvas file and migrated on the fly to `flow_*` kinds. The user never sees a "legacy" filter option — they just open the file and it works.

Question for CAI: is this the right behaviour? Alternatives:
- **Auto-detect silently (current CWC implementation):** cleanest UX; user opens `.json`, gets a migrated flowchart. Next save writes `.tgui` (or whatever the new extension is). No warning needed.
- **Warn on migration:** show a status message like "Migrated legacy FlowCode file — save to update format". CWC leans toward this: one-line status message is non-intrusive and tells the user the file was converted.
- **Explicit import action:** separate "Import legacy .json" menu item. Feels heavy; probably wrong for a tool of this scale.

**CWC recommendation:** auto-detect + one-line status message. Already implemented auto-detect; status message is one line of code.

### Q4 — Does a `.tgui` file that contains only flowchart symbols (no GHOST widgets) make sense?

Yes: `flow_symbols` and `flow_edges` are top-level keys in the v0.2 schema; `symbols` and `edges` (GHOST) can be empty lists. A flowchart-only file is valid. A GHOST-only file is also valid. Both are the same format. The tab you happen to be on when you open it doesn't constrain what you see — you see whatever is in the file on whichever tab has content.

No decision needed here; just confirming the model is sound.

---

## What CWC has already done (no revert needed)

- `gc_do_open()` and `gc_do_save()` both use `initialdir=_FC_DIR` (the `FlowCode/` directory where the app lives and where files are saved). This is an unconditional improvement.
- Legacy `.json` filter removed from the dialog; auto-detection retained inside the loader.
- Dialog title updated from "Open GHOST design (.tgui)" to "Open design (.tgui / .json)" — neutral, accurate for now. Will need another update once the extension question is settled.

---

## CWC's own view (for what it's worth)

The file format question and the extension question are small decisions with large readability consequences. The `.tgui` name was never great; now that it stores both tabs it's actively confusing. Pick a new extension at the start of Phase 6D, do a one-line rename in `gc_do_save()` and `gc_do_open()`, and update `source_type` in the tgui dict from `'ghost_flowcode'` to something that matches the new name. Cost: ten minutes. Benefit: the format name matches what the tool actually is.

The deeper point Stevo raised — "shouldn't there be a single file type that contains both a flowchart AND a GUI component?" — is already true of the Phase 6C format. The gap is only in naming and in how the dialogs present it. Closing that gap is naming work, not architecture work.

---

## Reporting

CWC reports:
- Two immediate bugs fixed: tooltip bleed-through on tab switch; open dialog defaulting to wrong directory.
- Open dialog now lands in `FlowCode/` directory by default; legacy `.json` auto-detected without a user-visible filter.
- File extension / naming deliberation items above are the only open question.

CAI reviews; Stevo gates.

---

*Handoff prepared: 16 June 2026, Adelaide*
