# Design Memo — FlowCode File Extension Policy

**From:** CAI
**To:** Stevo + future CWC dispatch
**Date:** 28 June 2026
**Re:** Rename .ternoo → .fc, introduce partial-save formats (.flow, .gui, .sheet), define load/import semantics, deprecate .ternoo with backward compatibility
**Status:** Office-mode design memo. Decision-locked. Ready for CWC implementation as Phase 7c-0 or similar lead-in bundle

---

## 1. The naming clarification

**TernOO** is the machine architecture: a 24-trit balanced-ternary CPU (the 5500FP), the word-format substrate, the OPCODE/EXEC/MAP/DATA/NEURAL/I-O grammar, the TTree/OTree mesh, the GristMill content-addressing infrastructure. It's the *target environment*.

**FlowCode** is the *visual programming language* used to author programs for that environment. A FlowCode program consists of a GUI design, a flowchart describing procedural logic, a spreadsheet expressing computation (when Sheet lands), and (eventually) shell-style command compositions. Files saved by the FlowCode IDE contain FlowCode programs, not "TernOO."

The current `.ternoo` extension confuses the two — it names the file after the substrate rather than the language. This memo corrects that.

The architectural payoff of dissolving the high-level/low-level distinction (TernOO's core design ambition) doesn't mean files containing FlowCode source should be named after the machine. The substrate is uniform; what the user *authors* is FlowCode programs. Files are FlowCode source.

---

## 2. Locked decisions

### 2.1 Extensions

| Extension | Meaning | Contains | Status |
|---|---|---|---|
| **`.fc`** | Canonical complete FlowCode program | Full WordStream — all GUI widgets, flow symbols, sheet cells (when Sheet exists), and bindings between them | **The default. New canonical extension** |
| **`.flow`** | Flow-only partial save | flow_* symbols, flow edges, flow scope/containment relationships | Partial save format |
| **`.gui`** | GUI-only partial save | gui_* widgets, layout relationships (STYLE_CONTAIN), widget properties | Partial save format |
| **`.sheet`** | Sheet-only partial save (when Sheet exists) | cell_* RNODEs, cell-to-cell references | Partial save format, awaits Stage 8 |
| **`.shell`** | Shell-only partial save (eventually) | command_* RNODEs and pipe edges | Reserved; awaits Stage 9 |
| **`.ternoo`** | Legacy | Same WordStream content as .fc | **Deprecated.** Loadable; auto-converts to .fc on next save |

### 2.2 What "partial" means

A partial-save file contains *only the WordStream words that belong to the named subsystem*, plus enough header information to identify which subsystem. Specifically:

- `.gui` contains: every RNODE word whose `kind` starts with `gui_`, every REDGE word whose semantics relate to GUI (STYLE_CONTAIN edges between GUI widgets, but NOT STYLE_HANDLER edges that bind to flow targets that aren't in this file)
- `.flow` contains: every RNODE word whose `kind` starts with `flow_`, every REDGE word that's a flow edge
- `.sheet` (future): every RNODE word whose `kind` starts with `cell_`, plus cell-to-cell reference edges
- `.fc`: everything

Cross-subsystem bindings (e.g., a STYLE_HANDLER from a GUI button to a flow terminator) are by definition not preserved in partial saves — they only exist in the complete file.

### 2.3 Load vs. Import semantics

Two distinct operations:

**Load** (existing behavior, applies to any extension):
- Replaces the current WordStream entirely with the file's contents
- Warns if there are unsaved changes
- After load, the IDE shows only what was in the file

**Import** (new):
- *Merges* the file's contents into the current WordStream
- Used to combine a `.gui` design with a `.flow` (load one, import the other), or to bring a reusable component into a working program
- ID collision handling: imported widgets/symbols get re-assigned IDs to avoid collision; cross-references within the imported content are renumbered to match
- Cross-subsystem bindings re-establish where name agreement permits (Phase 7c named-handler convention — a button named `submit_button` in the imported .gui will re-bind to a `submit_button_clicked` terminator already in the current .flow)

### 2.4 Save vs. Save As

**Save** (existing behavior):
- If the current file is `.fc`: writes the full WordStream
- If the current file is `.flow`, `.gui`, `.sheet`: writes only the relevant subset of the current WordStream and *warns* if the user has added content outside that subset

**Save As**:
- Lets the user pick any extension
- If choosing a partial extension and the WordStream has content outside that subset, a dialog appears:

```
┌─────────────────────────────────────────────────────────┐
│  Save as .gui?                                          │
│                                                         │
│  Your program contains flowchart symbols and bindings   │
│  that won't be saved in a .gui file.                    │
│                                                         │
│  The GUI design will be preserved, but the procedural   │
│  logic and any handler bindings will be lost from this  │
│  save.                                                  │
│                                                         │
│  [ Save as .fc instead ]  [ Save anyway ]  [ Cancel ]   │
└─────────────────────────────────────────────────────────┘
```

This honors the user's intent (they asked for .gui) while preventing accidental data loss.

### 2.5 Backward compatibility (.ternoo)

- `.ternoo` files continue to load — the file content is the WordStream serialization, which doesn't change
- On first Save after loading a `.ternoo` file, the IDE prompts:

```
┌─────────────────────────────────────────────────────────┐
│  This file uses the legacy .ternoo extension.           │
│  Save as .fc (the new default)?                         │
│                                                         │
│  [ Save as .fc ]  [ Keep .ternoo ]  [ Cancel ]          │
└─────────────────────────────────────────────────────────┘
```

The user can keep the legacy extension if they want; the file content is identical either way.

After some interval (a future bundle's decision), `.ternoo` could become a hard-deprecation. For now, soft-deprecation is sufficient.

### 2.6 File format stays the same

**No change to the file format itself.** Files contain serialized WordStream content (the existing format). The extension simply tells the IDE what subset to expect, and the save/load logic filters accordingly. A `.gui` file is structurally a WordStream that happens to contain only `gui_*` widgets.

This means:
- No migration scripts needed for the file format
- Existing `.ternoo` files work as `.fc` files immediately (only the extension differs from the new default)
- Implementation is purely IDE-side: file-dialog extension filters, content-filter on save, header detection on load

### 2.7 The .fcx compiled-executable question (deferred)

Whether FlowCode programs should also be saveable in a *compiled* form (analogous to `.py` vs `.pyc`) is a real question but is **out of scope for this memo**. Reasons:

- The current model (compile at run-time from source `.fc`) works fine for development
- Compiled artifacts only matter for *distribution* of FlowCode programs to non-developers — which isn't yet a use case
- Once GristMill-the-real-thing exists, compiled artifacts may be addressed differently (content-addressed by their OTree fingerprint rather than by extension)

Flagged for revisit when distribution becomes a concern.

---

## 3. Implementation scope

A single CWC bundle, modest scope:

1. Add file-dialog extension filters: `.fc` (FlowCode Program), `.flow` (Flow-only), `.gui` (GUI-only), `.ternoo` (legacy)
2. Default save extension: `.fc` for new files
3. Implement content-subset filtering in the save path (when extension is partial)
4. Implement the partial-save warning dialog
5. Implement the legacy-conversion prompt for `.ternoo` files
6. Add Import (separate from Load) menu item or sidebar action; implement ID-collision-handled merge
7. Update IDE titlebar and any "current file" references to use the new extension naturally
8. Any tests that reference `.ternoo` files in fixtures should continue working (load path still handles it)
9. The `button_click_demo.ternoo` fixture from Phase 7b-3 — leave as-is to verify backward compat keeps working

**Out of scope for this bundle:**
- `.sheet` and `.shell` extensions (just reserve, don't implement save filters yet)
- `.fcx` compiled format
- Hard-deprecation of `.ternoo`
- Migration of example fixtures (let them migrate organically on next save)

---

## 4. Acceptance criteria

1. New FlowCode programs save as `.fc` by default
2. `.flow`, `.gui` partial saves work with appropriate warning dialogs
3. Existing `.ternoo` files load correctly and prompt for conversion on save
4. Import-merge functions, creating no ID collisions
5. The example demo (`button_click_demo.ternoo` or successor) still works
6. All existing tests pass (58/58 across suites)
7. File-dialog filters show all supported extensions when opening; default to `.fc` when saving new content

---

## 5. The native block device / content-addressed storage horizon

This memo handles the file extensions question on the *host filesystem* — Linux Mint's ext4, etc. That's the current reality.

The longer arc is **TernOO-native storage**, weaning off the host filesystem entirely:

- A block-device abstraction in TernOO words
- A filesystem layer (FAT-like initially, content-addressed when GristMill-the-real-thing exists)
- I/O primary actually exercised (currently dormant per audit §1.6 and §7.3)
- File operations as TernOO opcodes, not host-OS syscalls

When that arc lands, the file extensions defined here remain meaningful — they just identify *what's in the content-addressed block* rather than *what's on the host's filesystem*. The extension is a content type marker, not a path-suffix convention. Same logic, different substrate.

So this memo's decisions are *forward-compatible* with the native storage future. The work isn't throwaway scaffolding; it's the right naming convention for both host-FS and native-FS eras.

---

## 6. Open questions (flagged, not blocking)

1. **The `.fcs` / `.fcx` distinction** — source vs. compiled. Deferred until distribution is a real use case
2. **Import-merge ID-collision strategy details** — keep imported IDs unless they conflict, then renumber? Or always renumber on import? CWC's call during implementation
3. **Multi-file FlowCode programs** — can a `.fc` file reference content in another `.fc` file? Not for now; everything in one file. May become useful when GristMill-the-real-thing introduces content-addressed references
4. **Subsystem prefixes vs. extensions** — could use `.fc.gui` instead of `.gui`. Probably no, `.gui` is cleaner. Locking the shorter form

---

*Memo prepared: 28 June 2026, Adelaide*
