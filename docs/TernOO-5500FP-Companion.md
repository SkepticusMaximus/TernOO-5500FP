# TernOO-5500FP — Living Companion Document
## Design Decisions, Rationale, and Development Log

**Authors:** Stevo (SkepticusMaximus) + Claude (Anthropic)  
**Started:** May 2026  
**Status:** Living document — updated alongside every code change  
**Companion to:** `5500fp_ternoo_v02.py` and `TernOO-5500FP-Word-Spec-v0.2.md`

> This document is the scratchpad, decision log, and rationale record for the
> TernOO-5500FP project. It is updated with every significant architectural
> decision, design change, or implementation note. Where the spec document
> states *what* the architecture is, this document records *why* and *how we
> got there*.

---

## Version History

| Version | Date     | Summary |
|---------|----------|---------|
| v0.1    | May 2026 | Initial overnight draft — Q1-Q5 analysis, renderer opcode sketch |
| v0.2    | May 2026 | Full update: all Qs resolved, Double Null added, EXEC layout locked, implementation complete |

---

## Part A — Resolved Design Decisions

---

### Q1. EXEC Word Addressing ✓ RESOLVED

**Decision: Segment-relative addressing from day one.**

Rationale (Stevo): Three arguments converged on this:

1. **The linker argument.** Absolute addressing requires a relocation pass at
   load time — scanning every EXEC word and patching addresses when code moves.
   On a permanent CGP agent node that hot-loads updated contract code, this
   pause is real and unnecessary.

2. **The same-cycle argument.** The USER-DEF POINTER already uses CODE-SEG
   and DATA-SEG fields resolved against base registers in the same dispatch
   cycle — zero overhead. EXEC words with segment-relative addressing work
   identically. What looks like added complexity is the same mechanism applied
   consistently, not new overhead.

3. **The panda's thumb argument.** Reserving T19–T18 as "always zero for now"
   would mean carrying dead weight and cognitive overhead during development.
   If we know where we're going, build it now.

**Final EXEC word layout (locked in v0.2):**

```
T23   T22        T21         T20          T19-T18    T17-T12   T11-T8   T7-T4     T3-T0
 −    PRIVILEGE  CALL-STYLE  RETURN-TYPE  SEG-IDX    OFFSET    ARITY    ARG-TYPES VERSION
      −1=kernel  −1=stack    −1=EXEC      2 trits    6 trits   4 trits  4 trits   4 trits
      0=user     0=register  0=MAP        (0–8 →     (±364)
      +1=sandbox +1=message  +1=DATA      CS0–CS8)
```

SEG-IDX encodes 0–8 as balanced ternary offset from -4: stored as (seg_idx − 4).
OFFSET is the resumption point within the code segment — enables continuations natively.
ARITY, ARG-TYPES, VERSION make the EXEC word a complete function signature.
This gives typed function pointers at the hardware word level, verified at fetch time.

**Comparison with C:**
In C, function pointer types are stripped by casts. Here the signature is
structural — it travels with the reference permanently and cannot be removed.
The version tag (T3–T0) has no C equivalent — it enables CGP contract hot-patching
with stale-reference detection.

---

### Q2. Segment Register Allocation ✓ RESOLVED

**Decision: Option C hybrid — 9+9 registers, 2+4 trit segment+offset split.**

```
T19-T18 (2 trits):  segment selector → 9 code segment bases (CS0–CS8)
T17-T12 (6 trits):  offset within segment (±364 words)
```

Register allocation:
```
R0        hardwired zero
R1–R8     argument registers
R9–R44    general purpose
R45–R53   Double Null stack pointers (ST0–ST8)
R54–R62   data segment base registers (DS0–DS8)
R63–R71   code segment base registers (CS0–CS8)
R72–R77   reserved
R78       RWR — Reserved Word Register
R79       SP  — stack pointer
R80       LR  — link register
```

Rationale: 9 hot segments per domain using 18 of 81 registers. The 9 = 3²
from the 2-trit selector is not arbitrary — it is derived from the field width.
Number is architecturally determined, not a choice.

---

### Q3. MAP Word Payload Convention ✓ RESOLVED

**Decision: Qualifier-determined interpretation (Option C).**

The qualifier zero states encode mode, not waste:

```
All qualifiers non-zero  →  ABSOLUTE_3D: full 3D position
Exactly one zero         →  ON_PLANE: 20-trit payload splits 10+10 (alphabetical)
Exactly two zeros        →  ON_AXIS: full 20-trit payload = 1D coordinate
All zeros                →  ORIGIN: payload = scale/zoom anchor
```

**On-plane payload convention (alphabetical axis order, T19 downward):**

```
T22=0 (on YZ-plane):  T19–T10 = Y,  T9–T0 = Z
T21=0 (on XZ-plane):  T19–T10 = X,  T9–T0 = Z
T20=0 (on XY-plane):  T19–T10 = X,  T9–T0 = Y
```

Rule: alphabetical order, MSB first, skip the zero axis.

Rationale: Makes redundant zero states semantically load-bearing (P3).
Mirrors vector graphics economics — structure encodes rules not exhaustive
enumeration. A sequence of MAP words with mixed qualifier states naturally
encodes hierarchical geometry with absolute anchors and relative details.

---

### Q4. FORMAT Words / Double Null Mechanism ✓ RESOLVED

**Decision: FORMAT is a use case of the Double Null mechanism, not a
reserved word and not a new primary type.**

**The Double Null mechanism** (designed May 2026, Stevo):

NULL words (T23=+1, T22=0, T21=0, T20=0) have two modes:

```
payload = 0   →  EXPLICIT NULL — plain nothing
payload ≠ 0   →  IMPLICIT NULL — loads context into a Double Null stack
```

**Implicit NULL word structure:**
```
T23-T20     T19-T18      T17-T12        T11-T6       T5-T0
NULL header  STACK-ID     QUALIFIER      MAPPING-A    MAPPING-B
(4 trits)    (2 trits)    (6 trits)      (6 trits)    (6 trits)
             selects       construct      pattern to   handler
             1 of 9        kind/type      recognise    reference
             stacks
```

**The 9 stacks** (ST0–ST8, pointers in R45–R53):
Each stack holds an independent context type. Different "reserved word" kinds
each get their own stack so they don't interfere. A FORMAT context, a LOOP
context, an ERROR-HANDLER context can coexist simultaneously.

**The RWR (Reserved Word Register, R78):**
Always holds the most recently loaded implicit null word. Fast single-context
access without stack indirection for tight loops or short-lived contexts.
Programmer chooses: RWR for speed, stack for nesting. Same mechanism, different
usage pattern.

**Example: a CHAR type construct:**
A language author defines CHAR by loading an IMPLICIT NULL with QUALIFIER
pointing to an ASCII table handler. For the duration of any function expecting
CHAR instances, that context sits in the RWR. The machine natively understands
CHAR without any external function dispatch. This is structural interpretation,
not procedural dispatch — the deepest architectural principle of TernOO-5500FP.

**Key insight:** The primary trit (T23) has only 3 states: EXEC, MAP, DATA.
There is no "FORMAT" primary type. The Double Null mechanism achieves the same
result without requiring a fourth primary type, by using NULL (a degenerate
pointer case) as a meta-signalling mechanism. No text, no reserved words in any
linguistic sense, no language baked into the machine.

---

### Q5. REMOTE Pointer and P2PCP Addressing ✓ RESOLVED

**Decision: Dual encoding.**

- **Point-to-point** (simple node reference): REMOTE pointer (T21=+1, T20=−1),
  20-trit node ID payload. Simple, fast, zero overhead.

- **Topology-aware routing** (load balancing, CGP geographic scope): MAP word
  with octree qualifier encoding. The MAP word IS the P2PCP address — qualifiers
  encode position in network topology, payload encodes node ID within the cell.

This is two levels of addressing, each appropriate to its use case. The P2PCP
protocol layer chooses which to use based on whether topology matters.

**CGP geographic mandate scope:** A mandate covering "all nodes in a region"
is a MAP word with non-zero qualifiers defining the region and a payload
encoding the mandate ID. No special encoding required — MAP words natively
carry spatial scope.

---

### Q6. USER-DEF POINTER Subclass Table ✓ RESOLVED

**Decision: Leave all seven predefined subclass slots unnamed.**

The clue is in the name — USER-DEFINED. The architecture provides the mechanism,
the user provides the meaning. Baking application-domain constructs (CGP tokens,
P2PCP nodes, polygon vertices) into the architecture would be a panda's thumb —
a constraint inherited from current use cases that would limit future ones.

Defined slots:
- (0, 0): Base (default)
- (+1, +1): Meta-extensible (always reserved as escape hatch)

All other 7 combinations: user-defined at deployment time.

---

### Q7. Segment Register Boot Convention ✓ RESOLVED

**Decision: All segment registers = 0 at reset. PC = 0.**

At reset: all 81 registers = 0, PC = 0, RWR = 0, all 9 Double Null stacks empty.
CS0–CS8 all point to address 0. DS0–DS8 all point to address 0.

The program at address 0 runs first and establishes whatever segment layout
it needs before doing anything else. This is the universal convention for
processor reset vectors and requires no special hardware support.

---

## Part B — Architecture Notes

---

### The Three-Layer Stack

```
Layer 3:  Application objects
          (polygon meshes, CGP tokens, P2PCP nodes, FlowCode graphs,
           any domain the user defines via Double Null mechanism)

Layer 2:  TernOO word interpreter  ← this project
          (word format, dispatch semantics, UDP object model,
           Double Null mechanism, renderer opcodes)

Layer 1:  5500FP ISA               ← stable substrate
          (fetch-decode-execute, 81 registers, 120 instructions,
          ternary-native instruction group)
```

The TernOO word interpreter is a software layer running on the 5500FP.
The 5500FP ISA is not modified. The TernOO opcodes in the emulator implement
the Layer 2 dispatcher.

---

### Structural Interpretation vs Procedural Dispatch

The deepest architectural principle of TernOO-5500FP, identified during design:

**Procedural dispatch** (conventional OO): data lives here, vtable lives there,
method dispatch is an indirection through a lookup table. Meaning is assembled
at runtime by calling procedures.

**Structural interpretation** (TernOO-5500FP): meaning is encoded in the word
structure itself. The primary trit tells you what kind of word it is. The
qualifier trits tell you how to interpret the payload. A USER-DEF POINTER word
carries its own code, data, and cursor — no vtable, no lookup, no runtime
assembly of meaning.

Every word in this machine is self-describing. Every word carries its own
operational semantics. The machine IS typed, word by word, from the ground up.

This is Alan Kay's "each object is a computer" implemented literally at the
hardware word level. Kay meant it metaphorically in 1972. TernOO-5500FP makes
it structural.

---

### The USER-DEF POINTER as Process Descriptor

A USER-DEF POINTER word is not Turing complete — it is finite and static.
However it is a **complete process launch descriptor**:

```
T23-T20:  type header (DATA/POINTER/USER-DEF)
T19-T18:  subclass selector
T17-T12:  OFFSET — internal cursor, 6 trits (±364)
T11-T6:   CODE-SEG — code reference, 6 trits (±364)
T5-T0:    DATA-SEG — data reference, 6 trits (±364)
```

Contains everything needed to initiate a Turing complete computation
(code address, data address, starting cursor) with zero setup overhead
beyond the word fetch. In conventional OO: pointer dereference → vtable
lookup → argument setup → stack frame → branch (4–6 memory accesses).
In TernOO: fetch word → read three 6-trit fields → dispatch.

The OFFSET field also enables **continuations** — resuming a function from
an arbitrary position, not always from the start. Coroutines, generators,
and cooperative multitasking fall out naturally from the OFFSET field at
no extra cost.

---

### Relationship to SBTCVM TernOO

The SBTCVM Gen2-9 TernOO implementation established the core insight:
the leading trit of a ternary word is the natural location for a type tag,
and three-way dispatch on that trit is the natural dispatch primitive.

TernOO-5500FP extends that insight to the 5500FP's 24-trit word without
inheriting SBTCVM's constraints:

| Property          | SBTCVM TernOO        | TernOO-5500FP (this project)  |
|-------------------|----------------------|-------------------------------|
| Word width        | 9 trits              | 24 trits                      |
| Payload           | 8 trits (±3,280)     | 20 trits typical (±1.74B)     |
| Type tags         | EXEC/DATA/REF        | EXEC/MAP/DATA                 |
| Tag rationale     | SBTCVM opcode space  | First principles               |
| Pointer models    | 1 (Option A)         | 9 (including USER-DEF)        |
| Object descriptor | Requires Option A    | Self-contained in word        |
| Extensibility     | Via register passing | Structural (EXT + Double Null)|
| Meta-constructs   | None                 | Double Null / 9 stacks        |
| Renderer          | None                 | RPOINT RLINE RNODE REDGE RENDER|

SBTCVM TernOO: proof of concept.
TernOO-5500FP: architectural successor, unconstrained by substrate.

---

## Part C — Implementation Log

---

### v0.1.0 — Initial emulator (19 May 2026)

**File:** `5500fp_emulator.py`

Built in one session. Core 5500FP CPU:
- 81 registers, 24-trit word arithmetic
- Math, load/store, control flow, subroutine call
- Ternary-native instructions (MIN, MAX, TXOR, EQUAL, SUM)
- Trit test and branch (TTT, TTZ, TTP)
- TernOO opcodes v0.1: TOBJ, TGET, TPAYLOAD, TCALL, TNEW
- Type constants: INTEGER/FLOAT/STRING (later corrected to EXEC/MAP/DATA)

Tests: 5 passing (arithmetic, memory, ternary-native, loop, subroutine)

Bug fixed during development: assemble_J2 missing F2 padding field causing
opcode to land in wrong position.

---

### v0.2.0 — Full TernOO word architecture (19 May 2026)

**File:** `5500fp_ternoo_v02.py`

Complete rewrite implementing all resolved design decisions:

**Word architecture:**
- Correct primary types: EXEC(−1) / MAP(0) / DATA(+1)
- Full EXEC word: T22=privilege, T21=call-style, T20=return-type,
  T19-T18=seg-idx, T17-T12=offset, T11-T8=arity, T7-T4=arg-types, T3-T0=version
- Full MAP word: T22=axis-YZ, T21=axis-XZ, T20=axis-XY, T19-T0=coordinate
  with qualifier-determined interpretation (ABSOLUTE_3D / ON_PLANE / ON_AXIS / ORIGIN)
- Full DATA word tree: SCALAR (float/int/uint), STRING (unicode/ascii/ternary),
  POINTER (9 models including USER-DEF)
- USER-DEF POINTER: T19-T18=subclass, T17-T12=OFFSET, T11-T6=CODE-SEG, T5-T0=DATA-SEG

**Word constructors:**
`build_exec_word()`, `build_map_word()`, `build_scalar_word()`, `build_int_word()`,
`build_uint_word()`, `build_string_word()`, `build_pointer_word()`,
`build_null_word()`, `build_implicit_null()`, `build_udp_word()`

**Word inspector:**
`decode_word()` — fully decodes any word to structured dict
`decode_exec_word()`, `decode_map_word()`, `decode_udp_word()` — type-specific decoders
`describe_word()` — human-readable one-line description

**Segment registers:**
CS0–CS8 in R63–R71, DS0–DS8 in R54–R62
`read_cs()`, `write_cs()`, `read_ds()`, `write_ds()`, `resolve_exec()`,
`resolve_udp_code()`, `resolve_udp_data()`
New opcodes: TBUILD (build UDP word), TSEG (resolve EXEC to full address)

**Double Null mechanism:**
9 independent stacks (ST0–ST8), pointers in R45–R53
RWR in R78, always holds most recent implicit null context
CPU detects NULL words during `run()` loop and calls `_handle_null()`
Stack push on implicit null, RWR update automatic

**Renderer opcodes (terminal Phase 1):**
RPOINT, RLINE, RNODE, REDGE, RENDER
Canvas is a list of dicts in `cpu.canvas`
RENDER calls `_render_canvas()` — ASCII art terminal output
Node shapes: `[   ]`=rect(int), `<   >`=diamond(float), `(   )`=rounded(uint)
Edge arrows: `──→`=single(register), `══►`=double(stack), `╌╌→`=dashed(message)

**Bug fixed:** Renderer opcodes OP_REDGE=41 and OP_RENDER=42 overflow 4-trit
opcode field range (−40..+40). Fixed by renumbering to OP_REDGE=−1, OP_RENDER=−2.

**Tests:** 7 passing — word constructors, segment registers, Double Null,
renderer, arithmetic, ternary-native (all v0.1 tests pass as regression)

---

## Part D — Open Items for v0.3

---

### Next implementation priorities

1. **Spec v0.2 document** — update `TernOO-5500FP-Word-Spec-v0.1.md` to v0.2
   reflecting all resolved decisions (EXEC layout, Double Null, register map).

2. **pygame renderer (Phase 2)** — replace terminal ASCII renderer with
   proper 2D vector graphics. MAP words drive geometry directly.
   Node shapes from qualifier trits. Edge styles from EXEC call-style trit.

3. **Word stream interpreter** — a proper execution loop that processes a
   sequence of TernOO words (not just 5500FP instructions), handling
   Double Null context switching inline. This is the Layer 2 interpreter
   that applications run on top of.

4. **Object inspector tool** — `ternoo_inspector.py`: load a memory image
   or word sequence, display each word decoded with `describe_word()`,
   show Double Null stack state, show segment register contents.
   The 5500FP equivalent of SBTCVM's Object Inspector.

5. **Bootstrap program** — a minimal TernOO word program that:
   - Sets up segment registers
   - Defines a CHAR type via Double Null
   - Renders a two-node flowchart
   - Demonstrates the full stack working end-to-end

---

### Open architectural questions

**OA1 — On-axis payload convention (minor):**
When two qualifier trits are zero (on-axis case), which end of the 20-trit
payload is the axis direction and which is the magnitude? Currently unspecified.

**OA2 — Continuation protocol:**
The EXEC word OFFSET field enables continuations. What is the calling convention
for a resumable function call vs a fresh call? Does the caller set OFFSET=0 for
fresh and OFFSET=saved_position for resume? Needs a small convention document.

**OA3 — Double Null pop protocol:**
How does a context get popped from a Double Null stack? Currently stacks only
push (on implicit null). An explicit null matching the stack top is the natural
pop trigger — but the matching rule needs formal specification.

**OA4 — Whitepaper:**
A formal academic-style paper presenting TernOO-5500FP as a novel architecture.
Sections: motivation (ternary economics), word architecture (the 24-trit design),
Double Null mechanism, self-describing objects, renderer / visual IDE vision,
relationship to prior work (SBTCVM TernOO, Smalltalk, Lisp machines, tagged
architectures). Suitable for submission to a computer architecture venue or
as a companion to Claudio La Rosa's 5500FP paper on Zenodo.

---

### Whitepaper outline (preliminary)

**Title:** *TernOO: A Self-Describing Object Architecture for Balanced Ternary*
*(or: Every Word is a Computer — Object-Oriented Structure Intrinsic to the
24-Trit Word)*

**Abstract:** We present TernOO-5500FP, a word architecture for the 5500FP
balanced ternary processor in which every 24-trit word is self-describing —
carrying not just its value but its full type, operational semantics, and in
the most general case, its own code segment, data segment, and internal cursor.
Object dispatch requires no vtable lookup, no runtime type check, and no
additional memory cycles beyond the word fetch. We describe the word grammar,
the Double Null mechanism for user-defined meta-constructs, and a primitive
renderer in which geometric primitives emerge directly from MAP words without
an intermediate representation layer.

**Sections:**
1. Introduction — the case for ternary and for OO at the word level
2. Background — 5500FP architecture, SBTCVM TernOO, prior tagged architectures
3. The TernOO Word Grammar — EXEC / MAP / DATA and their qualifier structures
4. The USER-DEF POINTER — process launch descriptor in 24 trits
5. The Double Null Mechanism — user-defined meta-constructs without reserved words
6. Renderer Opcodes — geometry emerging from MAP words
7. The Visual IDE Vision — diagram as machine code
8. Implementation — Python emulator, test suite, validation
9. Related Work — Smalltalk, Lisp machines, Intel iAPX 432, tagged architectures
10. Conclusion and Future Work — native silicon, pygame renderer, whitepaper

---

*"The diagram IS the code."*  
*— Stevo & Claude, May 2026*

*"The ideal object-oriented object is itself a computer."*  
*— Alan Kay, 1972*

*"Each 24-trit word is a complete process launch descriptor."*  
*— Stevo, 2026*

---

## Part E — v0.5.x Development Log

---

### v0.5.0 — FlowCode major feature update (31 May 2026, Adelaide)

**Changes:**
- Terminator symbol (oval) added — correct START/END marker, separate from I/O
- Canvas clutter removed: UDP/EXEC word text shown on selected symbol/edge only
- Hover tooltip (700ms delay) shows UDP/EXEC word for any symbol or edge
- `default_output` dropdown on Decision nodes — populated from outgoing edge
  condition labels, selects fallback branch when no runtime trit arrives
- Arrowheads trimmed to symbol boundary — visible on all shape types
- Condition labels always visible on edges; EXEC word on selected edge only
- Keyboard shortcut T for Terminator placement
- Interpreter updated to recognise `terminator` kind as valid start/end node

**Commit:** `b41d259`

---

### v0.5.1 — Data safety features (31 May 2026, Adelaide)

**Changes:**
- Confirm dialog before Clear ("Unsaved changes will be lost")
- Save prompt on window close (Yes/No/Cancel)

**Commit:** `09b4660`

---

### AgeTest2.json — First semantically correct flowgram (31 May 2026, Adelaide)

Proper symbol semantics throughout:
- START, END → Terminator (oval)
- GET AGE, UNDER AGE, ACCEPT AGE → I/O (parallelogram)
- AGE TEST → Decision (diamond)

Interpreter trace confirmed: 5 steps, `✓ END reached: END`, all TernOO
word fields decoded natively. Python is the runtime host; the execution
model is TernOO words throughout.

**Commit:** `56a2638`

---

### I/O Subclass Matrix — Design Decision (31 May 2026, Adelaide)

**Status: Experimental — prototype required before whitepaper update**

**Background:** The Gemini MMIO clipboard implementation (`!learn_clipbd`,
register `0x6000` in `5500fp_ternoo_v03.py`) established the architectural
pattern: external data enters the TernOO machine through a memory-mapped I/O
register address carried in the I/O word's 18-trit payload field. The UDP
subclass trits describe what the symbol does in the flowgraph; the MMIO
address ties it to the ISA-level I/O channel.

**Proposed encoding for UDP subclass trits on I/O symbols:**

```
T21 — Channel type:   −1 = file        0 = stream (network/pipe/IPC)   +1 = prompt (human-facing)
T20 — Operation:      −1 = read/listen  0 = bidirectional/passthrough   +1 = write/send/respond
```

**Common combinations:**

| Symbol role         | T21 | T20 | Example                        |
|---------------------|-----|-----|--------------------------------|
| User input prompt   | +1  | −1  | GET AGE dialog                 |
| User output message | +1  | +1  | ACCEPT AGE / UNDER AGE display |
| File read           | −1  | −1  | Load config                    |
| File write          | −1  | +1  | Save result                    |
| Network receive     |  0  | −1  | P2PCP inbound                  |
| Network send        |  0  | +1  | P2PCP outbound                 |

**Relationship to Section 3.6 (I/O Words):** The 3.6 spec
(Direction/Buffering/Blocking) operates at ISA level — how the hardware
channel behaves. This matrix operates at FlowCode level — what the symbol
does in the flowgraph. They are complementary layers, not duplicates.

**Outstanding question:** We are consuming two user-defined subclass trits
with a system definition. The right long-term solution is to register this
as a named Double Null context rather than hardcoding it into the base spec,
preserving the user-extensible subclass space. To be resolved when prototype
confirms the encoding is correct.

**Proposed experiment:** Wire the interpreter to dispatch I/O nodes based on
T21/T20 subclass — prompt-read nodes open a tkinter input dialog and push
the result to the eval stack; prompt-write nodes pop the stack and display
a tkinter message box.

---

### Versioning Policy (31 May 2026, Adelaide)

Semantic versioning: `MAJOR.MINOR.PATCH`

PATCH = fixes without new features. MINOR = new features. MAJOR = backward
incompatible architecture change.

Design goal: when FlowCode and GristMill are properly implemented, there will
be one final MAJOR version bump — after which every edit is backward and
forward compatible. The last MAJOR version is the one that makes MAJOR
versions obsolete. We are currently pre-1.0 (0.x = architecture still
being settled).

---


---

### v0.3.0 — I/O Subclass Dispatcher (31 May 2026, Adelaide)

**Module:** `5500fp/ternoo_interpreter.py`
**Block:** `io_subclass()`, `_register_builtins()`, `_io_dispatch()`,
           `_io_prompt_read()`, `_io_prompt_write()`

**What it does:** I/O symbols now dispatch at runtime based on their T21/T20
subclass trits. A prompt-read symbol (`GET AGE`) opens a tkinter input dialog
and pushes the result to the eval stack. A prompt-write symbol (`ACCEPT AGE`,
`UNDER AGE`) pops the stack and displays a tkinter message box. File and stream
operations are stubbed with "not yet implemented" trace messages.

**Bootstrap approximation:** Until the symbol properties dialog exposes T21/T20
explicitly, subclass detection uses label keyword heuristics. Words like GET,
READ, INPUT → prompt-read. Words like ACCEPT, OUTPUT, SHOW → prompt-write.
This is explicitly a bootstrap — once the FlowCode palette has distinct I/O
sub-symbols with correct UDP words, the heuristic is replaced by reading T21/T20
directly from the word.

**Design note:** The Gemini MMIO clipboard work (`!learn_clipbd`, register
`0x6000`) is the architectural ancestor of `_io_prompt_read`. Both read from
an external channel and write the result into the machine's memory space. The
difference is that `_io_prompt_read` operates at the TernOO word level rather
than at the raw memory address level. When the assembly bridge exists, the
tkinter call will be replaced by a MMIO write to the appropriate register
address carried in the I/O word's 18-trit payload field.

**MiniMind / shadow-GHOST note:** Once AgeTest2 runs interactively end-to-end,
it becomes training data for a MiniMind model. The sequence
`[terminator] → [io:prompt-read] → [decision] → [io:prompt-write] → [terminator]`
is a complete program in a 5-token vocabulary. Even a tiny model trained on a
handful of such flowgrams learns the grammar of TernOO programs. That is the
first step toward GHOST — not a code generator, but a symbol-sequence predictor
that makes the next step obvious to the programmer.


---

### NEURAL Forward-Pass Engine Skeleton (31 May 2026, Adelaide)

**File:** `5500fp/ternoo_neural.py`
**Status:** Skeleton — architecture proven, not production

**What it does:**
Implements a TernOO native neural network using NEURAL/UNIT and
NEURAL/CONNECTION words from the 5500FP emulator. Runs a single-layer
forward pass using ternary arithmetic — weight range ±4 (2 trits, 9 levels),
state range ±13 (3 trits, 27 levels).

**Forward pass algorithm:**
1. Load input values into input NEURAL/UNIT states
2. For each NEURAL/CONNECTION: target.accumulator += source.state × weight
3. For each non-input unit: state = clamp(accumulator + bias)

**Key classes:**
- `NeuralUnit` — wraps a NEURAL/UNIT word; serialises/deserialises cleanly
- `NeuralConnection` — wraps a NEURAL/CONNECTION word
- `TernOOBrain` — network of units and connections; `forward(inputs)` runs
  one pass; `to_words()` emits the full network as TernOO word list;
  `to_json()` / `from_json()` / `load()` handle brain files

**Gemini prior art honoured:**
`TernOOBrain.load()` detects legacy Markov format and converts via
`_from_markov()` — each Markov token becomes a NEURAL/UNIT, each transition
becomes a NEURAL/CONNECTION with weight=+1. The word brain (15 tokens,
18 connections) and generative brain (12 tokens, 36 connections) both
convert and run a forward pass successfully.

**Path to GHOST:**
This engine is the substrate GHOST runs on. The next layer is:
1. Wire TernOOBrain into the interpreter — NEURAL symbols in FlowCode
   delegate forward passes to this engine
2. Train on FlowCode symbol sequences — input/decision/output patterns
3. Use output unit states to suggest next symbol type (autocomplete)
4. Iterate until the model predicts TernOO-idiomatic programs

**Demonstrated:** XOR-like ternary logic demo runs correctly.
Both Gemini brain files convert to TernOO format and execute.


---

## Part F — GristMill & GHOST: The Generative Architecture

---

### GristMill — Content-Addressable Computation (31 May 2026, Adelaide)

**Status: Architectural insight — not yet implemented**

#### The Core Claim

A GristMill object is not stored anywhere. It is computed.

The MMID (Minimal Map ID) is a MAP word — a TernOO native coordinate in the
octree address space. The MMOE (Minimal Map Object Entity) is the minimal
self-contained unit of meaningful TernOO data that the MMID describes: a
widget, a handler, a connection, a flowgram fragment. All dependencies are
encoded in the MMID itself. There is no repository, no download, no version
resolution. The object materialises from the MMID through computation.

This is not object storage. It is object synthesis.

#### Why This Is Different

Conventional package managers store objects at locations. To use an object
you find its location, download it, verify it, install it. The object exists
independently of any mind that knows about it.

GristMill inverts this. The MMID is the complete description of the object.
Given the MMID, GHOST can synthesise the object — not retrieve it from a
server, but generate it from the structural knowledge encoded in the MMID's
MAP word coordinates. The object is latent in GHOST's training, not resident
on a disk.

The set of possible MMOEs is unbounded, because MAP word coordinate space
is unbounded. There is no finite catalogue of objects — there is an infinite
generative space of possible objects, navigated by MMID coordinates.

#### The Distance Property

In the MAP word octree, structurally similar objects are geometrically
proximate. A button widget and a checkbox widget are close. A button widget
and a network socket are distant. Dependency resolution is proximity search:
"find the object nearest to these coordinates that satisfies these
constraints." On hardware that computes MAP word addresses natively, this
is not a database query — it is an address calculation.

#### The Subjective Modelling Insight

This makes GristMill a subjective modelling system rather than an objective
one. Conventional object models assume a pre-defined set of objects in
pre-defined states on physical devices — they are objective, finite,
enumerable. GristMill objects materialise from GHOST's trained understanding
of structural relationships. The MMID is not a pointer to a thing — it is
a thought about a thing. GHOST thinks the MMOE into existence.

The philosophical implication: the system's knowledge of what objects exist
is bounded only by what GHOST has learned to understand. As GHOST learns
more widget structures, more flowgram patterns, more hardware primitives,
the generative space expands. The library grows without anyone adding to it.

#### Relationship to the Widget Architecture

A GUI widget expressed as a TernOO MMOE:
- MAP words encode spatial position and containment in the octree
- UDP words encode object type (widget class as subclass trits)
- EXEC words encode event handlers (signals as EXEC call-style)
- DATA words encode properties (label text, colour, dimensions)
- NEURAL words encode learned appearance variations (GHOST's aesthetic model)

The widget tree hierarchy maps to MAP octree containment. A button inside
a panel inside a window occupies a natural octree sub-region of the window's
MAP coordinate. No layout file. No XML. The containment IS the coordinate.

PIGART renders the widget from its MAP and UDP words directly. GHOST generates
the next widget by predicting the next MMID given the structural context —
the same forward-pass mechanism already implemented in ternoo_neural.py,
operating on widget-vocabulary NEURAL words instead of flowgram-vocabulary
ones.

#### The !learn Macro System

The `!learn_clipbd` and `!learn_temp` commands in the Gemini prototype
(5500fp_ternoo_v03.py, lines 1349–1466) are the prototype ingestion pipeline.
They write external data into the MMIO register at 0x6000 as TernOO word
sequences, which the training loop then uses to adjust projection weights
directly in CPU memory.

The next layer is `!learn_widget <descriptor>` — ingesting a widget definition
(from Cambalache, from a FlowCode canvas, from a sensor description) and
converting it to a MMOE word sequence that GHOST can train on. The `!learn`
prefix identifies an I/O symbol whose execution triggers training rather
than runtime behaviour.

#### Implementation Path

1. Define widget UDP subclass table (button, label, panel, window, input,
   list — each a (T21, T20) pair in the USER-DEF POINTER space)
2. Write `ternoo_gristmill.py` — MMOE encoder/decoder, MMID computation
   from structural description, proximity search stub
3. Extend FlowCodeBrain with widget vocabulary alongside flowgram vocabulary
4. Add `!learn_widget` I/O symbol type to the interpreter
5. Train on Cambalache .ui files converted to MMOE sequences
6. GHOST predicts next widget from structural context

The assembly bridge, PIGART, and FlowCodeBrain are all already in place.
GristMill is the next skeleton to build.

---

### FlowCode v0.5.2 — Brain Buttons (31 May 2026, Adelaide)

**Changes:**
- 🧠 Learn button — trains FlowCodeBrain on current canvas, saves weights
- 💡 Suggest button — predicts next symbol type from selected symbol
- Brain auto-loads `flowcode_brain.json` on startup if present
- Brain prints weight matrix to terminal after learning

**Commit:** pending

---

