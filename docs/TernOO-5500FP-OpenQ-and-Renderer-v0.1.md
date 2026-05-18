# TernOO/5500FP — Open Questions Analysis & Renderer Opcodes
## Companion to Word Architecture Spec v0.1

**Author:** Claude (Anthropic), on behalf of Stevo (SkepticusMaximus)  
**Date:** May 2026  
**Status:** Working notes — for review and decision  

---

## Part A — Open Questions: Analysis and Recommendations

---

### Q1. EXEC Word Addressing: Absolute vs Segment-Relative

**The question:**  
Should EXEC words carry a 20-trit absolute function address, or a shorter
segment-relative offset resolved via a code segment base register?

**Option A — Absolute address (20 trits, T19–T0):**

```
T23  T22  T21  T20  T19──────────────T0
 −   priv call ret  absolute address (20 trits)
```

- Range: ±1,743,392,200 — addresses the entire 5500FP memory space directly.
- Pro: Simple. No base register indirection. The address in the word IS the address.
- Pro: Safe to use before any segment context is established (boot code, kernel init).
- Pro: Consistent with the 5500FP's own J-format instruction which uses a 20-trit immediate for jumps.
- Con: EXEC words are not relocatable. If code moves in memory, all EXEC words pointing into it are stale.
- Con: Wastes the segment model's efficiency for code that lives in a known region.

**Option B — Segment-relative (6 trits + base register, mirroring USER-DEF POINTER):**

```
T23  T22  T21  T20  T19-T18    T17–T12     T11–T0
 −   priv call ret  seg-idx    offset      extended payload
                    (2 trits)  (6 trits)
```

- The 6-trit offset (±364) resolves against a code segment base register selected by the 2-trit seg-idx (4 possible segments).
- Pro: EXEC words are relocatable — moving a code segment updates one register, not every EXEC word.
- Pro: Mirrors USER-DEF POINTER's CODE-SEG field, giving the architecture a consistent segment model.
- Pro: Opens T11–T0 (12 trits) for additional metadata — argument count, type signature hash, version tag.
- Con: Requires segment base registers to be established before EXEC dispatch works.
- Con: More complex decoder. Two indirections instead of one.
- Con: 6-trit offset limits addressability within a segment to ±364 words — workable for tight code but constraining for large libraries.

**Recommendation: Option A for v0.1, with a migration path to Option B.**

The absolute address model is simpler, matches the 5500FP ISA's own jump model,
and avoids segment register management overhead during early development. The
architectural cost is non-relocatable EXEC words — acceptable for a research
platform where code position is known at assembly time.

Option B becomes compelling when dynamic loading, shared libraries, or hot-patching
are needed. The USER-DEF POINTER already establishes the segment model; EXEC words
can adopt it in v0.2 without breaking v0.1 programs (the primary trit and qualifier
trits remain identical — only the payload interpretation changes).

**Migration path:** Reserve T19–T18 in v0.1 EXEC words as "always zero" padding.
When Option B is adopted, T19–T18 become the seg-idx field and T17–T12 become the
offset. Programs that assembled with absolute addresses will fail gracefully
(seg-idx=0,0 maps to a null segment → trap) rather than silently misbehaving.

---

### Q2. Segment Base Register Allocation

**The question:**  
How many registers should be dedicated to code and data segment bases for
USER-DEF POINTER resolution?

**Context:**  
The 5500FP has 81 general-purpose registers. USER-DEF POINTER words carry 6-trit
CODE-SEG and DATA-SEG fields (each ±364). These are compact offsets, not absolute
addresses. They need to be resolved against base registers to yield full addresses.

**Option A — Fixed high registers:**  
Reserve R70–R79 as segment base registers (10 registers).  
- 5 code segment bases (R70–R74): each covers a code region up to 364 words.
- 5 data segment bases (R75–R79): each covers a data region up to 364 words.  
- The 6-trit segment fields select an offset within the active segment.
- Pro: Simple, predictable, no dynamic allocation.
- Con: 364 words per segment is tight for complex objects. Would need multi-word chaining for large data.
- Con: Wastes registers if fewer than 5 code/data segments are in use.

**Option B — Tryte-addressed segment table:**  
Dedicate one register (R79) as the segment table base pointer.  
The segment table lives in memory; the 6-trit CODE-SEG/DATA-SEG fields are indices
into this table (up to 364 entries each, in practice far fewer).
- Pro: Unlimited logical segments, constrained only by memory.
- Pro: Segment table is inspectable, serialisable, debuggable as ordinary memory.
- Con: Two memory accesses per dispatch (table lookup + data access).
- Con: Segment table must be initialised before any USER-DEF POINTER dispatch.

**Option C — Hybrid (recommended):**  
Reserve R72–R77 as hot segment registers (6 code, 6 data — one per trit value pair
of a 2-trit selector). The 6-trit segment field is split: top 2 trits select the
base register, bottom 4 trits (±40) are the offset within that segment.

```
6-trit CODE-SEG field:
  T5–T4: segment selector (2 trits → 9 combinations → 9 hot registers)
  T3–T0: offset within segment (4 trits, ±40 words)
```

- 9 hot code segment registers (R63–R71) + 9 hot data segment registers (R54–R62).
- Pro: 18 live segments simultaneously — sufficient for complex multi-object programs.
- Pro: No memory indirection for hot segments. Segment switch = one register write.
- Pro: Uses only 18 of 81 registers (R54–R71), leaving R0–R53 and R72–R80 free.
- Con: Offset limited to ±40 words within each hot segment — adequate for
  method tables and small objects, constraining for large data blocks.

**Recommendation: Option C.**  
The 2+4 trit split gives 9 hot segments per domain with 81 words per segment.
This matches the natural ternary granularity (3^4 = 81). Large objects that
exceed 81 words use FLAT or FIELD pointer models instead of USER-DEF, which
is architecturally clean — USER-DEF POINTER is for objects, not blobs.

**Register map summary:**

```
R0          hardwired zero
R1–R8       argument registers (calling convention)
R9–R53      general purpose
R54–R62     data segment base registers (DS0–DS8)
R63–R71     code segment base registers (CS0–CS8)
R72–R78     reserved for future system use
R79         stack pointer (SP)
R80         link register (LR) — return address for JSR
```

---

### Q3. MAP Word Payload: Absolute vs Relative Coordinates

**The question:**  
Should the 20-trit MAP payload carry an absolute coordinate, a relative offset
from a reference point, or a context-dependent mixed encoding?

**Option A — Always absolute:**  
T19–T0 always encodes an absolute position in the relevant coordinate space.
- Pro: Unambiguous. Any MAP word can be interpreted without context.
- Pro: Two MAP words fully define a line segment; three define a triangle. No reference frame needed.
- Con: Small offsets near an origin require the same 20 trits as distant coordinates.
  Wastes precision for local geometry.
- Con: Moving an object requires updating every MAP word in it — no relative transformation.

**Option B — Always relative:**  
T19–T0 always encodes an offset from the previous MAP word in a sequence, or from
a reference MAP word held in a register.
- Pro: Compact for local geometry — most polygon meshes have many small local offsets.
- Pro: Object translation = update one reference register, not every vertex.
- Con: Sequences lose meaning without their reference point. MAP words are not
  independently interpretable.
- Con: The self-describing word principle (P2) is weakened — a MAP word now requires
  context to decode.

**Option C — Qualifier-determined (recommended):**  
The qualifier trits already encode the octree position. Use their zero states as
encoding mode selectors:

```
All three qualifier trits non-zero  →  absolute coordinate
Exactly one qualifier trit = zero   →  on-plane (relative within that plane)
Exactly two qualifier trits = zero  →  on-axis (relative along that axis)
All three qualifier trits = zero    →  origin reference / scale anchor
```

- Pro: Preserves P2 (self-describing) — the qualifier trits tell you how to
  interpret the payload without external context.
- Pro: The zero states that were "redundant" become the relative/scale encoding.
  No trit is wasted.
- Pro: A sequence of MAP words with mixed qualifier states naturally encodes
  hierarchical geometry — absolute anchors interspersed with relative details.
- Pro: "Zoom level" or scale is encoded as all-zero qualifiers with a scale value
  in the payload. This is the vector graphics economic advantage made explicit.
- Con: Slightly more complex decoder — must check qualifier state before interpreting payload.
- Con: Requires a convention for which axis-pair the payload offsets when one qualifier is zero.

**Recommendation: Option C.**  
The qualifier-determined model makes the zero states semantically load-bearing
rather than wasted, exactly as P3 (redundant zeros as semantic anchors) specifies.
This is the most ternary-native choice — it exploits the three-state nature of
each trit rather than treating it as a binary flag with a wasted state.

**Coordinate convention for on-plane/on-axis states:**

When one qualifier trit is zero (on-plane case), the payload encodes a 2D offset
within the plane defined by the two non-zero axes. Split as T19–T10 (10 trits, one
axis) and T9–T0 (10 trits, the other axis). When two qualifier trits are zero
(on-axis case), the full 20-trit payload encodes a 1D position along the single
active axis.

---

### Q4. FORMAT Words: Domain-Specific Word Streams

**The question:**  
Should there be a reserved word type that redefines qualifier/payload boundaries
for subsequent words, enabling domain-specific encodings?

**Analysis:**

The FORMAT word idea is architecturally appealing — it would allow a network
protocol, an audio stream, or an image codec to define its own word grammar
without touching the primary type trit. However, it introduces statefulness into
word interpretation: the meaning of a word depends on which FORMAT words preceded
it in the stream.

This directly conflicts with P2 (self-describing without lookup). A word in a
FORMAT-modified stream cannot be interpreted without knowledge of the current
format state. This makes words non-portable, non-inspectable in isolation, and
fragile in the presence of dropped or corrupted format-switching words.

**Verdict: Defer FORMAT words to v0.3 or later.**  
The existing nine POINTER models plus the USER-DEF extensibility trit cover the
immediate use cases. The FORMAT mechanism, if adopted, should be strictly scoped
to data streams (sequences of DATA words used as byte arrays or codec payloads),
never to code streams. Code word interpretation must remain format-independent for
security and debuggability.

A safer near-term alternative: define a STREAM POINTER model (one of the nine
pointer models, e.g. the currently-reserved SYMBOL entry at T21=0,T20=+1) whose
payload points to a format descriptor in memory. The format applies only to words
accessed through that pointer, not to the instruction stream itself.

---

### Q5. REMOTE Pointer and P2PCP Addressing

**The question:**  
Should the REMOTE pointer model (T21=+1, T20=−1) use the standard 20-trit payload,
or get its own extended format as a MAP-type word?

**Analysis:**

P2PCP node addresses need to encode: network layer address, node identifier,
port or service, and potentially a geographic or topological coordinate. A flat
20-trit integer (±1.74B) is sufficient for a node identifier within a moderately
large network (~1.74 billion nodes) but doesn't naturally express the multi-
dimensional topology that P2PCP's compute-sharing protocol implies.

MAP words, on the other hand, natively encode 3D positions — and P2PCP's network
topology IS a geometric object. Nodes closer in the MAP coordinate space could
be preferentially selected for compute jobs, giving the routing protocol a spatial
locality optimisation for free.

**Recommendation: Dual encoding.**

- For simple node references (point-to-point, known address): use REMOTE pointer
  with 20-trit node ID payload. Simple, fast, no overhead.
- For topology-aware routing (load balancing, locality selection, CGP geographic
  mandate scope): use MAP words with octree qualifier encoding. The MAP word IS
  the P2PCP address — it encodes both the node's identifier (payload) and its
  position in the network topology (qualifiers).

This is not a conflict — it's two levels of addressing, each appropriate to its
use case, both natively supported by the word architecture. The P2PCP protocol
layer chooses which to use based on whether topology matters for a given operation.

**Concrete encoding:**

```
REMOTE pointer (point-to-point):
  T23=+1, T22=0, T21=+1, T20=−1, T19–T0 = node ID

MAP (topology-aware):
  T23=0, T22-T20 = octree position in network space
  T19–T0 = node ID within the octree cell
```

The octree cell in MAP space maps naturally to CGP's geographic mandate scope —
a mandate for "all nodes in this region" is a MAP word with non-zero qualifiers
defining the region and a wildcard payload.

---

## Part B — Renderer Opcodes: A Textless Visual Machine

---

### Overview

This section specifies a minimal set of TernOO renderer opcodes that enable a
GUI built from pure machine code, using MAP words as the native geometric
primitive. The design goal is that the diagram IS the machine code — no
intermediate representation, no serialisation, no compilation step between
the visual object and the executing program.

This is the FlowCode-for-ternary-hardware vision: a visual IDE where flowchart
nodes are MAP and USER-DEF POINTER words, connections between nodes are EXEC
words, and the display on screen is a direct rendering of the live object graph
in memory.

---

### B.1 Display Model

The renderer operates on a **scene graph** — a sequence of TernOO words in memory
that describe the current visual state. The scene graph is not a framebuffer. It
is a structured list of geometric primitives, each encoded as one or two TernOO
words, that the renderer interprets to produce output.

The scene graph lives in a dedicated memory region (the **canvas segment**).
Rendering is triggered by a RENDER instruction that scans the canvas segment and
produces output to a display buffer or terminal.

This model has the vector graphics economic property: only changed words need to
be re-rendered. A scene with 50 nodes and 80 edges requires updating at most a
handful of words when the user moves one node — not a full framebuffer refresh.

---

### B.2 Renderer Opcode Set

Six new opcodes extend the TernOO instruction set for visual output.
All use the standard 5500FP Format A instruction encoding.

---

#### OP_RPOINT — Render a point

```
RPOINT Rd, Rs1, Rs2
```
- Rs1: MAP word encoding the point position (octree qualifiers + coordinate payload)
- Rs2: DATA/SCALAR word encoding colour (packed RGB as unsigned integer)
- Rd:  receives the canvas address where the point was written (for later update)

Draws a single point at the position encoded in Rs1.
The octree qualifiers in Rs1 determine coordinate mode (absolute/relative/on-plane).

---

#### OP_RLINE — Render a line segment

```
RLINE Rd, Rs1, Rs2, Rs3
```
- Rs1: MAP word — start point
- Rs2: MAP word — end point
- Rs3: DATA/SCALAR word — colour and line weight (packed)
- Rd:  canvas address of this line element

Draws a line segment between two MAP-encoded positions.
The most common primitive for flowchart edges, network topology links,
polygon mesh edges.

---

#### OP_RPOLY — Render a polygon from a vertex list

```
RPOLY Rd, Rs1, Rs2, Rs3
```
- Rs1: POINTER/FLAT word — address of vertex list (sequence of MAP words)
- Rs2: DATA/SCALAR word — vertex count
- Rs3: DATA/SCALAR word — colour and fill style
- Rd:  canvas address

Draws a filled or outlined polygon from a contiguous block of MAP words.
The vertex list is a sequence of MAP words in memory — no boxing, no wrapping.
The polygon primitive is the basis for all filled shapes including flowchart nodes.

---

#### OP_RNODE — Render a flowchart / graph node

```
RNODE Rd, Rs1, Rs2, Rs3, Rs4
```
- Rs1: MAP word — node centre position
- Rs2: DATA/SCALAR word — node dimensions (width and height packed as two 10-trit fields)
- Rs3: DATA/SCALAR word — node style (shape: rectangle/diamond/circle encoded as SCALAR subtype trit)
- Rs4: USER-DEF POINTER — the TernOO object this node represents (provides CODE-SEG for label, DATA-SEG for content)
- Rd:  canvas address

This is the key opcode for the visual IDE. It renders a node and simultaneously
binds it to a TernOO object. The node on screen IS the object in memory — the same
word serves both roles. When the USER-DEF POINTER word in Rs4 changes, re-rendering
the node reflects the change automatically.

Node shapes by DATA/SCALAR encoding subtype:
- INTEGER (T21=0): rectangle (process/state node)
- FLOAT (T21=−1): diamond (condition/decision node)
- UNSIGNED (T21=+1): rounded rectangle (I/O or terminal node)

---

#### OP_REDGE — Render a directed edge between two nodes

```
REDGE Rd, Rs1, Rs2, Rs3
```
- Rs1: canvas address of source node (from RNODE's Rd)
- Rs2: canvas address of target node
- Rs3: EXEC word — the function this edge represents (provides arrowhead style from call-style qualifier)
- Rd:  canvas address of this edge element

Renders a directed edge (arrow) between two previously rendered nodes.
The EXEC word in Rs3 is the actual executable connection — the arrow on screen
represents a real function call in the object graph. Edge direction from EXEC
word's privilege trit (kernel edges drawn differently from user edges).

This is the property that makes the visual IDE honest rather than metaphorical:
the line you draw between two nodes IS the EXEC word that connects them in memory.
You are not annotating code — you are writing code by drawing.

---

#### OP_RENDER — Commit canvas segment to display

```
RENDER Rs1, Rs2
```
- Rs1: canvas segment base address
- Rs2: canvas segment length (word count)

Scans the canvas segment from Rs1 for Rs2 words and produces display output.
Only words that have the canvas dirty flag set (a convention using one trit of
the DATA-SEG field in each canvas entry) are redrawn.

This is the only opcode that touches the display hardware. All other render
opcodes write to the canvas segment in memory. RENDER is called once per frame,
or when a dirty flag is set by any other render opcode.

---

### B.3 Visual IDE Bootstrap Program

To illustrate the opcode set, here is a minimal program that renders a two-node
flowchart with one directed edge — the simplest possible FlowCode diagram —
in pure TernOO machine code.

```
; Registers pre-loaded by convention:
; R63 = code segment base (CS0)
; R54 = data segment base (DS0)
; R79 = stack pointer

; ── Build two TernOO object words ─────────────────────────────────────────

; Node A: a process node (rectangle)
; MAP position: absolute, centre-left
; DATA SCALAR INTEGER: value 1 (node ID)
LDI  R1,  [MAP word: T23=0, T22=+1, T21=0, T20=0, payload=100]  ; x=100
LDI  R2,  [MAP word: T23=0, T22=0,  T21=+1,T20=0, payload=200]  ; y=200
LDI  R3,  [SCALAR INTEGER: value=1]                               ; node ID
LDI  R4,  [SCALAR UNSIGNED: 0x4488FF]                            ; colour blue
LDI  R5,  [SCALAR INTEGER: packed 80x40]                          ; dimensions
LDI  R6,  [USER-DEF POINTER: CS0+0, DS0+0, offset=0]             ; object word

; ── Render Node A ─────────────────────────────────────────────────────────
RNODE R10, R1, R5, R3, R6        ; R10 = canvas address of node A

; ── Build Node B: a decision node (diamond) ──────────────────────────────
LDI  R11, [MAP word: payload=400]                                 ; x=400
LDI  R12, [MAP word: payload=200]                                 ; y=200
LDI  R13, [SCALAR FLOAT: value=2]                                 ; diamond style
LDI  R14, [SCALAR UNSIGNED: 0xFF8844]                            ; colour orange
LDI  R15, [USER-DEF POINTER: CS0+1, DS0+1, offset=0]             ; object word

RNODE R16, R11, R5, R13, R15     ; R16 = canvas address of node B

; ── Build the edge: an EXEC word connecting A to B ────────────────────────
LDI  R17, [EXEC word: T22=0(user), T21=0(register-args), T20=+1(returns DATA),
           address=handler_fn]    ; the actual function being called

; ── Render the edge ───────────────────────────────────────────────────────
REDGE R18, R10, R16, R17         ; arrow from A to B, styled as R17's EXEC word

; ── Commit to display ─────────────────────────────────────────────────────
LDI  R20, canvas_base
LDI  R21, canvas_length
RENDER R20, R21                  ; draw everything marked dirty

HLT
```

The key line is REDGE. The EXEC word in R17 is not just styling for the arrow —
it IS the function that node A calls when execution flows to node B. Changing
the function means changing the arrow's EXEC word. Drawing the arrow means
creating the function call. The diagram and the program are the same object.

---

### B.4 The Textless IDE Vision

A complete FlowCode-for-5500FP IDE built on these opcodes would have these
properties:

**Every element is a TernOO word.**  
Nodes are USER-DEF POINTER words. Edges are EXEC words. Coordinates are MAP
words. There is no separate "project file" — the scene graph in memory IS the
project.

**No text anywhere in the visual layer.**  
Node shapes encode their type (rectangle=process, diamond=condition, rounded=I/O).
Colours encode privilege level and data type. Edge arrowhead style encodes calling
convention. The visual vocabulary is entirely geometric and chromatic — no labels,
no text boxes, no syntax.

**Text exists at a higher layer if needed.**  
A DATA/STRING word can be attached to any node as a human-readable annotation.
But the machine does not need the annotation to execute. The annotation is for
the human programmer, not the machine.

**Live execution is visible.**  
Because nodes and edges are TernOO words in live memory, a debugger can highlight
the currently-executing node by setting a flag trit in its USER-DEF POINTER word.
The RENDER opcode reads this flag and renders the active node differently. Step
through a program in the debugger and the flowchart animates — not as a
visualisation of execution, but as a direct display of the execution state.

**The IDE is itself written in TernOO.**  
The visual IDE's own user interface — its toolbox, its canvas, its menus — are
rendered by the same six opcodes. The IDE eats its own cooking. Writing a new
node type in the IDE generates new TernOO words in memory, which the IDE can
immediately render, because the IDE's renderer understands TernOO words natively.

This is the property that made Smalltalk-80 remarkable and that no subsequent
environment has fully recaptured: the development environment and the running
program are the same system, with no translation layer between them.

On a ternary machine with TernOO words, this property is not a design aspiration.
It is a direct consequence of the word architecture: there is nothing else for
the IDE to be made of.

---

### B.5 Implementation Path

**Phase 1 — Python prototype (immediate):**  
Add the six renderer opcodes to `5500fp_emulator.py`.  
Use Python's `tkinter` or `pygame` as the display backend.  
The canvas segment is a Python list of TernOO words.  
RENDER scans the list and calls `pygame.draw` primitives.  
This validates the opcode semantics without hardware.

**Phase 2 — Terminal renderer (for Raspberry Pi node):**  
Replace the pygame backend with ANSI escape code output.  
MAP words with integral coordinates map to terminal character positions.  
Colours map to ANSI colour codes.  
This gives a working textless IDE on any terminal — including the Pi node
you envisaged as the permanent CGP agent hardware.

**Phase 3 — Native 5500FP (when hardware available):**  
The canvas segment maps to a framebuffer memory region.  
RENDER writes directly to display memory.  
The Python emulator is replaced by the actual 5500FP board.  
All TernOO programs written in Phases 1–2 run unmodified.

---

*End of companion document.*

*"The diagram IS the code."*  
*— Stevo & Claude, May 2026*
