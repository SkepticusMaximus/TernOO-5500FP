# Design Memo — The Shell Tab (Skeleton)

**From:** CAI
**To:** Stevo + future CWC dispatch
**Date:** 28 June 2026
**Re:** Conceptual design for the Shell tab — commands as first-class flow symbols with Pocket parameters, pipes as FLOW edges. Skeleton only — no file I/O commands until native storage exists
**Status:** Office-mode design memo. Establishes architecture; specific command catalogue is deferred to implementation phases

---

## 1. The principle

The Shell tab brings *command composition* into FlowCode as a first-class authoring surface. The Unix shell philosophy — small commands, pipes, environment, composable — translated to a visual medium where parameter discovery and configuration happen via the same widget vocabulary that defines GUIs.

In one image: **a Shell command is a flow symbol whose Pocket is a small GUI**.

This unifies several pieces of the architecture cleanly:

- The Pocket UX from Phase 7c-4 is the *parameter sheet*
- The widget vocabulary (`gui_check`, `gui_entry`, file-picker, etc.) provides the *parameter input controls*
- FLOW edges between commands are *pipes* carrying data
- Environment / shared state lives in the program state region (same place Phase 7b-4 put widget state and the eventual Sheet cells)
- Commands have *names* via the Phase 7c-1 naming convention, so they can be referenced and composed

The Shell tab is not a separate paradigm from Flow and GUI — it's the same word substrate viewed through a command-composition lens.

---

## 2. Locked architectural decisions

| # | Decision | Choice |
|---|----------|--------|
| S1 | Command representation in WordStream | New RNODE family `cmd_*` (e.g., `cmd_text_upper`, `cmd_math_add`). Each `cmd_*` widget has an opcode-style identity (which command) plus a Pocket containing parameter widgets |
| S2 | Where commands live | New tab "Shell" alongside Flow/GUI/Sheet. Shell tab is the *canonical* view for command composition; commands can also appear inside Flow tab (a flow_process box might invoke a command) |
| S3 | Parameter sheet | The Pocket UX (Phase 7c-4). Opening a command's pocket reveals a GUI layout containing the parameter widgets — exactly the same widget vocabulary as the GUI tab |
| S4 | Pipes | FLOW edges between commands. An edge from command A's output socket to command B's input socket pipes A's output as B's input. Output/input socket positions are part of each command's definition |
| S5 | Type system | Each command's input/output sockets have a declared type. Pipes between mismatched types raise a warning in the editor and a compile-error at run-time. Initial types: `text`, `number`, `boolean`, `list_of_text`, `list_of_number`. Richer types come later |
| S6 | Command registry | A new module `flowcode_commands.py` (analogous to `flowcode_signals.py` / `flowcode_properties.py`) defines available commands: their socket signatures, parameter widget specs, and implementation references |
| S7 | Command implementation | Each command compiles to a `flow_terminator`-equivalent block of t5asm (Phase 7b-4 mechanics). For builtin commands the t5asm is hand-written templates; for user-defined commands (eventually) the t5asm is generated from the command's own flow graph |
| S8 | User-defined commands | A flowchart can be *saved as a command*, becoming reusable in other programs. The composing user sees just the command's I/O sockets and parameter sheet; the implementation is hidden in the command's Pocket. This is where reuse / abstraction lives |
| S9 | Environment / shared state | In-program key-value store living in the program state region (same mechanism Phase 7b-4 uses for widget state and entry text). Commands can `getenv("name")` and `setenv("name", value)`. Scope is per-program for now; cross-program later |
| S10 | Execution model | When a Shell program runs, the engine traces from a designated entry command (or all "root" commands with no inbound pipes), executes each in topological order, passing piped values along. Same engine as Phase 7b's PIGART runtime — no new VM |

### Crucially out of scope for this skeleton

**No file I/O commands of any kind.** No `read_file`, `write_file`, `list_dir`, `cat`, `grep` against files, `find`, anything that touches storage. The reason isn't capability — the host OS provides all that — but **discipline**: every host-FS dependency we add now is future work to tear out when native storage lands. We weaning ourselves diligently of the host FS with all due gratitude for its hospitality.

The first useful commands are deliberately *pure-data* commands — they transform values without touching any storage. They're useful immediately; they won't need rewriting when native FS arrives because they don't depend on FS.

---

## 3. The first useful commands (pre-filesystem)

These commands can be built and shipped before any storage work happens. They demonstrate the Shell tab's value without committing to host-FS dependencies. Not a complete list — examples to seed the catalogue.

### Text commands (`cmd_text_*`)

| Command | Inputs | Outputs | Parameters | Purpose |
|---|---|---|---|---|
| `cmd_text_upper` | `text` | `text` | none | Uppercase transformation |
| `cmd_text_lower` | `text` | `text` | none | Lowercase transformation |
| `cmd_text_trim` | `text` | `text` | none | Strip whitespace |
| `cmd_text_replace` | `text` | `text` | `find` (text), `with` (text), `case_sensitive` (bool) | Substitution |
| `cmd_text_split` | `text` | `list_of_text` | `delimiter` (text) | Splitting |
| `cmd_text_join` | `list_of_text` | `text` | `separator` (text) | Concatenation |
| `cmd_text_length` | `text` | `number` | none | Character count |
| `cmd_text_format` | various | `text` | `template` (text with `{}` placeholders) | Templating |

### Math commands (`cmd_math_*`)

| Command | Inputs | Outputs | Parameters | Purpose |
|---|---|---|---|---|
| `cmd_math_add` | `number`, `number` | `number` | none | Addition |
| `cmd_math_subtract` | `number`, `number` | `number` | none | Subtraction |
| `cmd_math_multiply` | `number`, `number` | `number` | none | Multiplication |
| `cmd_math_divide` | `number`, `number` | `number` | none | Division (with zero-check) |
| `cmd_math_sum` | `list_of_number` | `number` | none | Sum a list |
| `cmd_math_round` | `number` | `number` | `places` (number) | Rounding |

### List commands (`cmd_list_*`)

| Command | Inputs | Outputs | Parameters | Purpose |
|---|---|---|---|---|
| `cmd_list_filter` | `list_of_*` | `list_of_*` | `predicate` (sub-flow) | Subset by criterion |
| `cmd_list_map` | `list_of_*` | `list_of_*` | `transform` (sub-flow) | Apply transformation |
| `cmd_list_sort` | `list_of_*` | `list_of_*` | `ascending` (bool), `by` (sub-flow optional) | Ordering |
| `cmd_list_count` | `list_of_*` | `number` | none | Length |
| `cmd_list_first` | `list_of_*` | `*` | none | Head element |
| `cmd_list_last` | `list_of_*` | `*` | none | Tail element |

### Input/Display commands (`cmd_io_*`) — note: NOT file I/O

| Command | Inputs | Outputs | Parameters | Purpose |
|---|---|---|---|---|
| `cmd_io_prompt` | none | `text` | `message` (text) | Interactive input via SDL dialog |
| `cmd_io_display` | `text` | none | `title` (text) | Display a value to the user |
| `cmd_io_confirm` | none | `boolean` | `message` (text) | Yes/no dialog |
| `cmd_io_choice` | `list_of_text` | `text` | `prompt` (text) | Pick-from-list dialog |

These are user interactions via SDL — no storage involved. They use PIGART syscalls already defined in Phase 7b-2.

### Control flow commands (`cmd_ctl_*`)

| Command | Inputs | Outputs | Parameters | Purpose |
|---|---|---|---|---|
| `cmd_ctl_if` | `boolean`, `*`, `*` | `*` | none | If/else value selector |
| `cmd_ctl_repeat` | `number`, `*` (sub-flow) | `list_of_*` | none | Loop n times |
| `cmd_ctl_while` | `*` (predicate sub-flow), `*` (body sub-flow) | none | none | Conditional loop |

These are essentially flow-control primitives that the Flow tab also has — but expressed as commands so they compose in Shell programs.

### Environment commands (`cmd_env_*`)

| Command | Inputs | Outputs | Parameters | Purpose |
|---|---|---|---|---|
| `cmd_env_get` | none | `text` | `name` (text) | Read in-program env var |
| `cmd_env_set` | `text` | none | `name` (text) | Write in-program env var |
| `cmd_env_exists` | none | `boolean` | `name` (text) | Check env var presence |

**Critical**: this `cmd_env_*` family is for *in-program* state — same scope as Phase 7b-4's program state region. It is NOT the host's environment variables. No host-OS leak.

---

## 4. What this skeleton enables before filesystem lands

With just the commands above, the Shell tab is useful for:

- **Text manipulation tools** — chained text transformations on user-provided input, with output displayed back
- **Calculators** — number-crunching tools with parameter dialogs
- **List processing** — filter/map/sort over user-provided collections
- **Interactive utilities** — multi-step dialogs that gather information, transform it, present results
- **Reusable command assemblies** — save a useful Shell program as a *new command*, then use it in other programs

That's a non-trivial set of utilities, all working without any storage primitives. Stevo's "GUI version of shell scripts for simple dynamic purpose built user tools" lands at this point — minus the file-touching commands, which arrive later.

---

## 5. What's deferred to post-filesystem

Once the TernOO-native filesystem exists (its own stage), these commands become possible and meaningful:

- File read/write (`cmd_file_*`)
- Directory traversal (`cmd_dir_*`)
- Find/grep (`cmd_search_*`)
- Path manipulation (`cmd_path_*`)
- Archive/compress (`cmd_archive_*`)

The file-touching commands inherit the same Pocket-with-parameters pattern; only their implementations differ (calling native filesystem opcodes rather than pure-data transforms).

This is the discipline: build the substrate, then build commands against it. Don't borrow host-FS now and tear it out later.

---

## 6. Integration with other arcs

### With Phase 7c (named-handler auto-wiring)

Commands have names per the 7c-1 convention. A command's outputs are bindable as parameters to other commands by *name*. This means:

- `cmd_text_upper.output` can be referenced by name in another command's parameter
- A command's name is `<kind>_<id>` by default; user can rename to a meaningful name (`uppercase_title`, `count_items`)
- The Pocket UX (7c-4) is the *parameter sheet* — Shell is its canonical use case

### With Sheet leg (Stage 8)

A command can take a sheet cell as a parameter (e.g., `cmd_math_add` with both inputs bound to sheet cells). The pipe-or-cell-reference duality means commands compose with sheet computation naturally.

### With Flow tab

A `flow_process` symbol in the Flow tab can invoke a command. The command's pocket contains the parameter sheet for that invocation. This means: existing Flow tab work isn't replaced by Shell; Shell is a *canonical command-composition view*, and Flow can call commands like it calls anything else.

### With GUI tab

User-facing GUIs can include widgets bound (via Phase 7c) to commands. A button's `clicked` handler can be a command invocation rather than a flow_terminator. The Pocket UX makes the command's parameters editable in the GUI tab via the button's properties.

So: **Shell isn't a separate tower. It's one perspective on the substrate, sitting alongside Flow / GUI / Sheet, all reading the same WordStream.**

---

## 7. Implementation roadmap (loose — Stevo's pace)

These are the substantive bundles. No timeline implied.

| Phase | Scope | Prerequisites |
|---|---|---|
| Stage 9-0 | Shell tab UI scaffolding — empty tab, palette of command kinds | Phase 7c-1 (`name` property) |
| Stage 9-1 | Command registry + a few cmd_text_* commands | Stage 9-0, Phase 7c-4 (Pocket UX) |
| Stage 9-2 | Pipe edges (typed) between commands; compile path to t5asm | Stage 9-1 |
| Stage 9-3 | cmd_math_*, cmd_list_*, cmd_env_* commands | Stage 9-2 |
| Stage 9-4 | cmd_io_* commands (SDL dialogs) | Stage 9-3, Phase 7b PIGART syscalls (already done) |
| Stage 9-5 | cmd_ctl_* control flow commands | Stage 9-4 |
| Stage 9-6 | User-defined commands — save a flowchart as a reusable command | Stage 9-5 |
| Stage 10 | Native filesystem (separate arc) | TBD |
| Stage 10-onward | File-touching commands (`cmd_file_*`, `cmd_dir_*`, etc.) | Stage 10 complete |

---

## 8. The Stage 10 (filesystem) note — explicit

This memo says nothing concrete about Stage 10. The filesystem strategy needs its own memo when ready. The key promise *this* memo makes is:

> No command in Stages 9-0 through 9-6 will depend on the host filesystem. The Shell tab will be useful before the native filesystem exists, and the filesystem will be added cleanly to a Shell tab that's already working without it.

That discipline keeps the substrate honest.

---

## 9. Open questions (flagged, not blocking)

1. **Command versioning** — when a built-in command changes its signature, what happens to existing programs that use it? Probably: version-tag commands, allow old programs to bind to old versions. Filesystem of commands → GristMill territory
2. **Async commands** — commands that take time (network, eventually file I/O) need an async model. Probably: pipes become *future* values that compose asynchronously. Not for Stage 9 skeleton; later
3. **Error handling in pipes** — if a command fails, what flows down the pipe? An error value? A side-channel? Probably: typed Result/Maybe at the type level. Deferred to Stage 9-2 implementation
4. **Command discovery UX** — the command palette needs categorization, search, recently-used. Standard IDE pattern; implementation detail
5. **The `cmd_` kind family vs. a generic `command` kind with a "which command" discriminator** — packaging decision; either works. CWC's call

---

*Memo prepared: 28 June 2026, Adelaide*
*Companion to: CAI-Named-Handler-Auto-Wiring-Design.md, CAI-Spreadsheet-Leg-Design-Sketch.md, CAI-FlowCode-File-Extensions-Policy.md*
