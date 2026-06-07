# TernOO: A Self-Describing Object Architecture for Balanced Ternary

**Stevo (SkepticusMaximus)**
Independent Developer, Adelaide, South Australia
https://github.com/SkepticusMaximus

*Draft v0.4 — June 2026*
*Companion implementation: https://github.com/SkepticusMaximus/TernOO-5500FP*

---

## Abstract

We present TernOO-5500FP, a word architecture for the 5500FP balanced ternary
processor in which every 24-trit word is self-describing. A 2-trit primary field
identifies one of nine primary types — including executable code (EXEC), spatial
coordinate (MAP), data value (DATA), neural network primitives (NEURAL), and
input/output streams (I/O) — and a 4-trit qualifier field encodes the word's full
operational semantics without any additional memory fetch or runtime type check.
An 18-trit payload carries the value, coordinate, or structured content. In the
most general case, a single word carries its own code segment reference, data
segment reference, and internal cursor: a complete process launch descriptor in
24 trits.

We describe the word grammar, the Double Null mechanism for defining
user-extensible meta-constructs without reserved words or additional primary
types, PIGART (Primitive Graphics And Rendering Tool) renderer opcodes in which
geometric primitives emerge directly from MAP words, and GristMill, a
generative object synthesis engine in which objects are reconstructed by
traversal through a tetrahedral content mesh rather than retrieved from storage.

In v0.4 we formalise the dual coordinate system for MAP words: the OTree
(octree, stable absolute addresses) and the TTree (tetrahedral tree, content
identity navigation), distinguished by the mode_hint trit T18. We confirm the
mathematical foundation of the TMesh traversal mechanism as a Steiner quasigroup
over Z/3⁶Z — the unique ternary analogue of binary XOR satisfying the
three-way mutual recovery property — and establish the vocabulary closure
condition for the Meccano set: closed sub-quasigroups must have size 3^k, with
the minimal useful vocabulary being the 27-element set of multiples of 27.

The result is an architecture in which the distinction between code and data,
between object and pointer, between diagram and program, and between address
and content dissolves at the word level — not as a software abstraction but as
a structural property of the machine.

A Python emulator and prototype implementing the full architecture is available
as open source. The architecture targets the 5500FP processor described in
La Rosa (2026) and is designed as a candidate ISA extension for that platform.

---

## 1. Introduction

### 1.1 Terminology Note

This paper uses "word" in two distinct senses. A *machine word* is the native
24-trit unit of the 5500FP processor. A *TernOO word* is any machine word
interpreted under the TernOO architecture — a machine word whose trit fields
carry type and semantic information. Where ambiguity might arise we prefer
"machine word" or "TernOO word" for precision.

We distinguish *symbols* (the primitive elements of a flowchart — process
rectangles, decision diamonds, and so on) from *nodes* (the vertices of a
network topology graph). TernOO-5500FP supports both, and conflating the terms
in a system that explicitly represents both would cause genuine confusion.

We distinguish *tokens* from *coins*. A token is an intangible, not-normatively-
liquid digital asset representing value within a specific system — earned, spent,
and meaningful within that system but not designed as general currency. A coin is
fungible and liquid, intended for exchange like currency whether physical or
digital. The distinction preserves disambiguation potential that careless
interchangeable usage wastes.

### 1.2 The Case for Ternary

Binary computing dominates modern hardware for an accident of fabrication history rather than mathematical necessity. The radix that minimises the product of the number of digits and the base — the radix economy — is e ≈ 2.718. The nearest integer is three.

Balanced ternary, in which digits take values in {−1, 0, +1}, is particularly
elegant. Negation requires only inverting all trit signs, with no asymmetric
edge case as in two's complement. A 24-trit balanced ternary word represents a
range of approximately ±141 billion, compared to ±2 billion for a 32-bit binary
word, using only 50% more signal lines on native silicon [La Rosa 2026].

The recent emergence of ternary-quantised neural networks — in which model
weights are restricted to {−1, 0, +1} and performance matches full-precision
models at a fraction of the memory and energy cost [Ma et al. 2024] — provides
independent confirmation from a completely different domain that the three-valued
representation offers fundamental efficiency advantages.
### 1.3 The Case for Object-Oriented Structure at the Word Level

Object-oriented programming has been the dominant paradigm for software
architecture since the 1980s, yet its relationship with the underlying machine
has always been one of translation and overhead. In every mainstream OO language,
objects are a software construct layered on top of a machine that knows nothing
about them. Method dispatch requires a pointer dereference, a vtable lookup,
argument marshalling, and a branch. The object model is imposed from above; the
machine is indifferent.

This is not what Alan Kay envisioned when he invented object-oriented
programming. Kay's original conception was that "the ideal object-oriented
object is itself a computer" — that each object should be capable of receiving
a message and responding autonomously. TernOO-5500FP asks: what if the
machine's word format itself encoded object structure? The 24-trit word of the
5500FP provides exactly enough space for a 2-trit primary type, a 4-trit
qualifier, and an 18-trit payload. No external lookup. No runtime overhead.
No translation layer.
### 1.4 The Dimensional Advantage

The four qualifier trits in MAP words carry a specific geometric insight. Three
of them encode directional sense along the axis pairs of a 3D coordinate frame,
producing an octree coordinate system intrinsic to the word format. This mirrors
the economics of vector graphics over raster: MAP words encode 3D position as
directional sense plus magnitude, not as three separate integers. Information
density is intrinsic and bottom-up.

This same octree coordinate structure serves as the foundation for
content-addressable storage: data can be located by hashing it to MAP word
coordinates and navigating the octree via bubble search, cutting the search
space by two thirds at each step (O(log₃N)) rather than one half as in binary
trees. This is discussed further in Section 9.4.
### 1.5 Contributions

    The TernOO word grammar: a 2+4+18 trit word format encoding primary type, qualifier semantics, and payload in a single self-describing word. Nine primary types, 81 qualifier combinations per type.
    The USER-DEF POINTER: a word carrying its own code segment reference, data segment reference, and internal cursor — a complete process launch descriptor in 24 trits with zero vtable overhead.
    The Double Null mechanism: a general-purpose meta-construct primitive allowing users to define their own structured interpretation contexts without new primary types or text-based keywords.
    NEURAL and I/O word types: native word-level encodings for neural network primitives (neurons, synapses, network structures) and I/O streams, enabling ternary neural inference and I/O without software abstraction layers.
    PIGART renderer opcodes: five opcodes rendering geometric primitives directly from MAP words, enabling a visual programming environment in which the diagram and the program are the same object in memory.
    GristMill: a content-addressable component repository using MAP word octree coordinates as native storage addresses, enabling non-technical porting of legacy code and modular FlowCode application composition.
    An open-source Python emulator implementing the full architecture.

2. Background
### 2.1 The 5500FP Processor

The 5500FP [La Rosa 2026] is a 24-trit balanced ternary RISC processor
implemented on an Efinix Trion T20F256 FPGA, clocked at 20 MHz.

Word width. 24 trits, from the doubling series (24→48→96) rather than the power-of-three series (27→81→243). The 24-trit word divides cleanly into six 4-trit fields, four 6-trit tribbles, or two 12-trit shorts.

Register file. 81 general-purpose registers, each one machine word wide, addressed by a 4-trit identifier (3⁴ = 81). R0 is hardwired to zero.

ISA. Approximately 120 instructions including a ternary-native group (MIN, MAX, TXOR, EQUAL, SUM, CONS, ANY, IMPL, DECOT/DECOU/DECOF) with no binary equivalent. Native atomic synchronisation primitives (CAS, FAA).

Toolchain. A macro-assembler accepts 5500FP assembly and produces SD card binary images. A minimal OS kernel (GRam_OS) provides basic initialisation and interactive shell. The microarchitecture is open for independent implementation; the ISA is patent and copyright protected.
### 2.2 TernOO: Origin and Prior Implementation

TernOO is an object-oriented word architecture conceived by the first author
as a native extension for balanced ternary machines. The core insight — that
the leading trit of a ternary word is the natural location for a type tag, and
that three-way dispatch on that trit is the natural OO primitive — predates any
specific implementation substrate.

An initial proof-of-concept was built on a balanced ternary virtual machine,
adding four opcodes that used the leading trit of a 9-trit tryte as a type
discriminator. This demonstrated the mechanism but was constrained by the
9-trit word width and limited payload range.

TernOO-5500FP replaces every substrate-specific constraint with a design
derived from the 5500FP's richer architecture, most significantly expanding
from a 1-trit primary field (3 types) to a 2-trit primary field (9 types):
| Property          | Initial TernOO         | TernOO-5500FP                   |
|-------------------|------------------------|---------------------------------|
| Word width        | 9 trits                | 24 trits                        |
| Format            | 1+3+5                  | 2+4+18                          |
| Primary types     | 3                      | 9                               |
| Pointer models    | 1                      | 9 (including USER-DEF)          |
| Object descriptor | External               | Self-contained in word          |
| Meta-constructs   | None                   | Double Null / 9 stacks          |
| Neural words      | None                   | UNIT/CONNECTION/STRUCTURE       |
| I/O words         | None                   | Direction/Buffering/Blocking    |
| Renderer          | None                   | PIGART (5 opcodes)              |
### 2.3 Tagged Architectures and Lisp Machines

The idea of storing type information alongside data has a long history.
Lisp machines of the 1970s–80s included hardware tag fields in every word to
distinguish integers, floats, and pointers, enabling garbage collection and
dynamic dispatch without software overhead [Steele and Sussman 1975].

TernOO-5500FP differs in two respects. First, the type tag occupies the two most significant trits of a balanced ternary word — an architecturally natural position in a signed symmetric system. Second, the qualifier trits extend type information into a full operational descriptor, carrying calling convention, spatial coordinates, object structure, neural network topology, or I/O characteristics depending on the primary type. The word is not tagged with its type; it is its type, structurally.
### 2.4 Downstream Use Cases

TernOO-5500FP is designed as general-purpose infrastructure. Two downstream
applications illustrate the range of its intended use:

FlowCode — a visual programming IDE targeting non-programmers, in which flowchart symbols, spreadsheet formulas, and GUI components serve as the programming vocabulary. In TernOO native mode, FlowCode symbols map directly to TernOO words; the IDE is the compiler. Full discussion in Section 7.

Consensus Governance Protocol (CGP) — a decentralised democratic governance system developed independently by the first author over many years. CGP's geographic mandate scope maps naturally to MAP words with octree qualifier encoding. CGP was not a motivation for TernOO-5500FP; it is a use case the architecture happens to serve well.
3. The TernOO Word Grammar
### 3.1 Overview

Every 24-trit TernOO word has the 2+4+18 structure:

T23-T22       T21-T18         T17-T0
──────────    ───────────     ──────────────────────
PRIMARY       QUALIFIER       PAYLOAD
(2 trits)     (4 trits)       (18 trits)
type ID       type semantics  value / address / data

The 2-trit primary field (T23-T22) identifies one of nine primary types:
| T23 | T22 | Primary Type | Status   |
|-----|-----|--------------|----------|
| −1  | −1  | EXEC         | Defined  |
| −1  |  0  | MAP          | Defined  |
| −1  | +1  | DATA         | Defined  |
|  0  | −1  | NEURAL       | Defined  |
|  0  |  0  | I/O          | Defined  |
|  0  | +1  | CRYPTO       | Reserved |
| +1  | −1  | OPEN_A       | Open     |
| +1  |  0  | OPEN_B       | Open     |
| +1  | +1  | POOL         | Dynamic  |

Design principle: 5 defined, 1 reserved, 3 open. The POOL type (+1,+1) is
always reserved as the dynamic allocation escape hatch — new types can be
allocated from the pool without breaking existing encodings.
#### 3.1.1 Word Structure Diagram

24-TRIT WORD STRUCTURE  (2+4+18 layout)
┌──────────┬──────────────────┬──────────────────────────────────────┐
│ T23-T22  │   T21-T18        │           T17-T0  (18 trits)         │
│ 2 trits  │   4 trits        │                                      │
│ PRIMARY  │   QUALIFIER      │           PAYLOAD                    │
├──────────┼──────────────────┼──────────────────────────────────────┤
│ −−  EXEC │priv|call|ret|seg │[seg_lsb:1][offset:6][arity:4][v:3]  │
├──────────┼──────────────────┼──────────────────────────────────────┤
│ −0  MAP  │ YZ | XZ | XY |h │[coordinate: 18 trits, mode-dependent]│
├──────────┼──────────────────┼──────────────────────────────────────┤
│ −+  DATA │sub |enc |mod |mod│[value / address / object descriptor] │
│          │type|    | hi | lo│  USER-DEF:[sub:2][off:6][cs:6][ds:4] │
├──────────┼──────────────────┼──────────────────────────────────────┤
│0− NEURAL │unit|    |    |   │[state:3][bias:6][fan_in:5][wseg:4]   │
│          │conn|    |    |   │[weight:2][source:8][target:8]        │
├──────────┼──────────────────┼──────────────────────────────────────┤
│ 00  I/O  │dir |buf |blk |   │[channel identifier: 18 trits]        │
└──────────┴──────────────────┴──────────────────────────────────────┘
Trit values: − = −1   0 = 0   + = +1
Tribble = 6 trits (range ±364).  T23 is MST (most significant trit).

### 3.2 EXEC Words (T23=−1, T22=−1)

An EXEC word is a reference to executable code. The qualifier and payload
fields encode the function's complete calling contract:

T23-T22  T21        T20         T19          T18       T17   T16-T11  T10-T7  T6-T3    T2-T0
  −−     PRIVILEGE  CALL-STYLE  RETURN-TYPE  SEG-MST   SEG   OFFSET   ARITY   ARGTYPES VERSION
                                              (qual)    (pay)

T21 — Privilege: −1=kernel, 0=user, +1=sandbox T20 — Call style: −1=stack, 0=register, +1=message-passing T19 — Return type: −1=EXEC, 0=MAP, +1=DATA T18 — Segment index MST: upper trit of 2-trit segment selector T17 — Segment index LST: lower trit of segment selector Together T18-T17 select CS0–CS8 (encoded as seg_idx−4, range −4..+4)

T16–T11 — Offset: 6-trit offset within code segment (±364). Also serves as resumption point for continuations — a function can be entered at any position, enabling coroutines and cooperative multitasking at zero extra cost.

T10–T7 — Arity: 4-trit argument count T6–T3 — Argument types: 4-trit type signature T2–T0 — Version: 3-trit generation tag for hot-patching and stale-reference detection (8 versions before rollover — sufficient for most contract lifecycles)

The EXEC word is a complete function signature at the hardware word level.
Call-site type checking — privilege, arity, argument types, return type —
occurs at fetch time with no runtime overhead.
### 3.3 MAP Words (T23=−1, T22=0)

A MAP word encodes a position or reference in three-dimensional space via an
octree coordinate system. Three of the four qualifier trits represent axis pairs;
the fourth is a mode hint:

T23-T22  T21       T20       T19       T18       T17-T0
  −0     AXIS-YZ   AXIS-XZ   AXIS-XY   MODE-HINT 18-trit coordinate payload

Each axis trit: −1=negative direction, 0=on-plane, +1=positive direction.

Qualifier zero states encode coordinate modes:
| Qualifier state (T21-T19) | Mode        | Payload interpretation                |
|---------------------------|-------------|---------------------------------------|
| All non-zero              | ABSOLUTE_3D | 3D octree position + magnitude        |
| One zero                  | ON_PLANE    | 2D offset in plane (9+9 trits)        |
| Two zeros                 | ON_AXIS     | 1D coordinate along active axis       |
| All zero                  | ORIGIN      | Scale/zoom anchor                     |

On-plane payload convention (alphabetical axis order, T17 downward):

    T21=0 (YZ-plane): T17–T9=Y, T8–T0=Z
    T20=0 (XZ-plane): T17–T9=X, T8–T0=Z
    T19=0 (XY-plane): T17–T9=X, T8–T0=Y

MAP words as content addresses. The octree structure of MAP words is not only for visual geometry — it also provides the substrate for content-addressable storage. Data can be located by hashing it to MAP word coordinates and navigating the octree via bubble search (Section 9.4).
### 3.4 DATA Words (T23=−1, T22=+1)

DATA words carry values, pointers, and strings. T21-T20 of the qualifier
selects among three DATA subtypes; T19-T18 encodes subtype-specific detail:

SCALAR (T21=−1, T20=−1): T19=encoding (−1=float, 0=integer, +1=unsigned), T18=spare, T17–T0=value (18 trits, range ±129,140,163)

STRING (T21=+1, T20=+1): T19=encoding (−1=unicode, 0=ascii, +1=ternary glyph), T18=spare, T17–T0=length or address

POINTER (T21=0, T20=0): T19-T18 select one of nine pointer models:
| T19 | T18 | Model     | Description                       |
|-----|-----|-----------|-----------------------------------|
| −1  | −1  | FLAT      | Direct memory address             |
| −1  |  0  | RELATIVE  | Offset from PC                    |
| −1  | +1  | STACK_REL | Offset from SP                    |
|  0  | −1  | FIELD     | Object base + field index         |
|  0  |  0  | NULL      | Null / undefined (Double Null)    |
|  0  | +1  | SYMBOL    | Interned symbol                   |
| +1  | −1  | REMOTE    | P2PCP network node reference      |
| +1  |  0  | WEAK      | Weak reference                    |
| +1  | +1  | USER-DEF  | Self-describing object word       |
### 3.5 NEURAL Words (T23=0, T22=−1)

NEURAL words encode neural network primitives as first-class word types. The
T21 qualifier trit selects among three neural roles:

NEURAL/UNIT (T21=−1) — a neuron:

Payload: T17-T15=state(3t) T14-T9=bias(6t) T8-T4=fan_in(5t) T3-T0=weight_seg(4t)

State is a 3-trit activation value. Fan_in counts up to 31 incoming connections.
Weight_seg references the synaptic weight array via a data segment register.

NEURAL/CONNECTION (T21=0) — a synapse:

Payload: T17-T16=weight(2t) T15-T8=source(8t) T7-T0=target(8t)

The 2-trit weight field encodes 9 discrete levels (±4 range), compared to
BitNet's {−1,0,+1}. This finer granularity is native to balanced ternary
arithmetic and provides more expressive synaptic weights at no extra cost.

NEURAL/STRUCTURE (T21=+1) — a layer or network descriptor:

Payload: T17-T12=kind(6t) T11-T6=size(6t) T5-T0=seg_ref(6t)

The NEURAL primary type enables ternary neural inference without a software
abstraction layer. A forward pass through a layer is a sequence of
NEURAL_CONNECTION word lookups, each performing a 2-trit weight multiplication
using native ternary arithmetic.
### 3.6 I/O Words (T23=0, T22=0)

I/O words encode stream endpoints, event channels, and peripheral interfaces.
Three qualifier trits encode the communication characteristics:

T23-T22  T21        T20          T19       T18    T17-T0
  00     DIRECTION  BUFFERING    BLOCKING  spare  channel identifier

T21 — Direction: −1=input, 0=bidirectional, +1=output T20 — Buffering: −1=unbuffered, 0=buffered, +1=interrupt-driven T19 — Blocking: −1=blocking, 0=nonblocking, +1=async/event

The I/O primary type eliminates the STREAM and EVENT word subtypes that would
otherwise consume DATA pointer model slots. A P2PCP node's network interface,
a display output, and a keyboard input are all I/O words with different
qualifier combinations.
4. The USER-DEFINED POINTER
### 4.1 Structure

The USER-DEF POINTER (DATA primary, T19=+1, T18=+1 pointer model) is the
most structurally rich word type:

T23-T22  T21-T18         T17-T16    T15-T10   T9-T4     T3-T0
  −+     PTR qualifier   SUBCLASS   OFFSET    CODE-SEG  DATA-SEG
  DATA   USER-DEF        2 trits    6 trits   6 trits   4 trits

T17–T16 — Subclass: 2 trits, 9 possible subclass variants. (0,0)=base, (+1,+1)=meta-extensible escape hatch. The other 7 slots are user-defined at deployment time — not prescribed by the architecture.

T15–T10 — OFFSET: 6-trit internal cursor (±364). Points to the current position within the object's data segment. Enables sequential access, iteration, and streaming without external state. Also enables continuations — an object can record where processing paused and resume from that position.

T9–T4 — CODE-SEG: 6-trit code segment reference (±364). Resolved against a code segment base register (CS0–CS8 in R63–R71) to yield the full address of the object's associated executable code.

T3–T0 — DATA-SEG: 4-trit data segment reference (±40). Resolved against a data segment base register (DS0–DS8 in R54–R62). The 4-trit field (vs 6 in v0.2) reflects the freed space from the 2+4+18 expansion — small objects whose data fits within 40 words of their segment base use this field directly; larger objects use FLAT or FIELD pointer models.
### 4.2 Dispatch Semantics

When the CPU encounters a USER-DEF POINTER word, it:

    Reads CODE-SEG → resolves full code address via CS base register
    Reads DATA-SEG → resolves full data address via DS base register
    Reads OFFSET → sets internal cursor for data traversal
    Dispatches to the resolved code address

Steps 1–4 require no memory fetches beyond the word itself. In conventional OO:
pointer dereference → vtable lookup → argument setup → stack frame → branch
(4–6 memory accesses). In TernOO: fetch word → read three fields → dispatch.
### 4.3 Process Launch Descriptor

A USER-DEF POINTER word is not Turing complete — it is finite and static. However it is a complete process launch descriptor: it contains everything needed to initiate a Turing complete computation (code address, data address, starting cursor) with zero setup overhead beyond the word fetch.

This is Alan Kay's "each object is a computer" implemented literally at the
hardware word level.
### 4.4 Segment Register Architecture

R54–R62:  DS0–DS8  (data segment bases)
R63–R71:  CS0–CS8  (code segment bases)

The 2-trit segment selector field (T18-T17 in EXEC, implicit in UDP) addresses
9 hot segments per domain (3² = 9 — derived from field width, not arbitrary).
Moving a code block requires one register write, not a scan-and-patch of every
EXEC word referencing it.

At reset: all segment base registers = 0. The program at address 0 establishes
its own segment layout before first dispatch.
5. The Double Null Mechanism
### 5.1 The Problem It Solves

Every programming system needs some concept of a "reserved word" — a symbol
that means something specific to the system rather than being general data.
The 2-trit primary field has nine states, five defined. There is no spare
primary type for "META" or "FORMAT." The Double Null mechanism achieves the
same result using the degenerate case of an existing word type.
### 5.2 Structure

A NULL word (DATA primary, T19=0, T18=0 pointer model) has two modes:

payload = 0   →  EXPLICIT NULL — plain nothing
payload ≠ 0   →  IMPLICIT NULL — loads a meta-construct context

Implicit NULL word structure:

T23-T22  T21-T18         T17-T16    T15-T12  T11-T6       T5-T0
  −+     PTR/NULL        STACK-ID   spare    MAPPING-A    MAPPING-B
  DATA   qualifier       2 trits    4 trits  6 trits      6 trits

STACK-ID selects one of 9 Double Null stacks (ST0–ST8, pointers in R45–R53).
MAPPING-A is the trit pattern to recognise in subsequent words.
MAPPING-B is the handler reference for that pattern.
### 5.3 The Nine Stacks

Nine independent stacks, each dedicated to a different kind of meta-construct.
A FORMAT context, a LOOP context, and an ERROR-HANDLER context can coexist
simultaneously without interference.

The RWR (Reserved Word Register, R78) always holds the most recently loaded
implicit null context for fast single-level access. The programmer chooses:
RWR for speed, stack for nesting.
### 5.4 Structural Interpretation vs Procedural Dispatch

The Double Null mechanism exemplifies the deepest architectural principle of
TernOO-5500FP. In conventional OO, meaning is assembled at runtime by calling
procedures. Here, meaning is encoded in the word stream itself. A CHAR type
construct loaded into the RWR means the CPU natively understands CHAR without
any function dispatch. The type interpretation is structural, not procedural.
6. PIGART — Primitive Graphics And Rendering Tool
### 6.1 Design Philosophy

There is no point in making a computer speak a dialect of English in order to
tell it how to be a bunch of connected switches. If some of those switches are
wired to a graphical matrix, graphical symbolic mnemonic primitives are the
shortest line between programmer intent and machine behaviour.

PIGART is the renderer opcode set that closes this loop. Five opcodes render
geometric primitives directly from TernOO words. The scene graph in memory IS
the program. The display on screen IS the program viewed through the renderer.
### 6.2 The Opcode Set

RPOINT Rd, Rs1, Rs2 — Render a point. Rs1=MAP word (position), Rs2=DATA/SCALAR word (colour). Rd receives canvas address.

RLINE Rd, Rs1, Rs2, Rs3 — Render a line segment. Rs1=MAP (start), Rs2=MAP (end), Rs3=DATA (style).

RNODE Rd, Rs1, Rs2, Rs3, Rs4 — Render a flowchart symbol. Rs1=MAP (position), Rs2=DATA (dimensions), Rs3=DATA/SCALAR (shape):

    INTEGER (T19=0) → rectangle (process symbol)
    FLOAT (T19=−1) → diamond (decision symbol)
    UNSIGNED (T19=+1) → rounded rectangle (I/O symbol) Rs4=USER-DEF POINTER (the TernOO object this symbol represents). Rd receives canvas address. The symbol on screen IS that object. Changing the word changes the display on next RENDER.

REDGE Rd, Rs1, Rs2, Rs3 — Render a directed edge between two symbols. Rs1=source canvas address, Rs2=target canvas address, Rs3=EXEC word. Arrow style derives from EXEC call-style trit: stack(−1)→double, register(0)→single, message(+1)→dashed. The edge drawn IS the EXEC word in memory.

RENDER Rs1, Rs2 — Commit canvas segment to display. Rs1=canvas base address, Rs2=word count. Redraws only dirty entries.
### 6.3 Scene Graph Model

PIGART operates on a scene graph — a structured list of TernOO words in a
dedicated canvas segment. The scene graph is not a framebuffer. This provides
the vector graphics economic property: only changed words need redrawing.
### 6.4 Implementation Phases

Phase 1 (current): Python emulator with ASCII terminal canvas output. Nodes displayed as [   ], <   >, (   ). Edges as ──→, ══►, ╌╌→.

Phase 2: pygame or PyQtGraph backend. MAP words drive 2D geometry directly.

Phase 3: Native 5500FP hardware. Canvas segment maps to framebuffer memory. All programs written in Phases 1–2 run unmodified.
7. The Visual IDE Vision: FlowCode as TernOO Compiler
### 7.1 The ASCII Workaround

There is no point in making a computer speak a dialect of English in order to
tell it how to be a bunch of connected switches. It already is a bunch of
connected switches. If some of them are wired to a graphical matrix, then
graphical symbolic mnemonic primitives are the shortest line.

Early computers had keyboards. Keyboards produced character codes. Character
codes were mapped to numbers — ASCII and its descendants — and those numbers
were given to the processor. Crucially, the symbols, though graphical in
origin (letters are shapes), were not used as graphical primitives. They were
assembled into linguistic constructs with syntax rules, compiled to a text
representation, which was then compiled again to binary switching patterns.

A programmer who drew a flowchart to document their program produced something
ironically closer to the machine's actual structure than the source code — yet
the compiler was blind to it. The diagram was always the most honest
representation of the program; it was simply never the one that ran.
### 7.2 The Structural Dissolution of the Diagram/Program Gap

In conventional visual programming (LabVIEW, Scratch, MIT App Inventor), the
gap between diagram and program is fundamental. You draw a diagram. A compiler
reads the diagram and produces code. The code runs. The diagram documents.
They are different representations kept consistent by translation. The compiler
never sees the diagram in the old paradigm — the diagram is the programmer's
sketch, invisible to the machine.

In TernOO-5500FP this gap does not exist:

    Process rectangle → USER-DEF POINTER word (rect subtype)
    Decision diamond → USER-DEF POINTER word (diamond subtype)
    Connection arrow → EXEC word (calling convention in qualifier trits)
    Position coordinate → MAP word

The renderer reads these words and displays the symbols.
The executor reads the same words and runs the program.
They are the same words. One source of truth.
### 7.3 FlowCode as TernOO Assembly Language

FlowCode was conceived as a general-purpose visual programming environment
with three integrated components: Dia (flowcharting), Gnumeric (spreadsheet/
mathematical formulas), and Cambalache (GUI design). A MiniMind small language
model component was designed to assist in generating code output. Target
outputs were Python and Solidity (via SolidiFlow for Ethereum smart contracts).

TernOO-5500FP reveals a more fundamental role. FlowCode, targeting the TernOO
word architecture, is not a front-end to a compiler. It is the assembly language
itself:
| Conventional assembly  | FlowCode / TernOO                          |
|------------------------|--------------------------------------------|
| Mnemonic (ADD, MOV...) | Symbol shape (rectangle, diamond, arrow)   |
| Operand registers      | Symbol connections (which flows to which)  |
| Addressing mode        | Connection style (EXEC qualifier trits)    |
| Data declaration       | DATA symbol (SCALAR, STRING, POINTER)      |
| Mathematical formula   | Spreadsheet symbol (Gnumeric integration)  |
| Macro definition       | Double Null context (user-defined construct) |

The spreadsheet component maps to SCALAR words — arithmetic formulas operating
on SCALAR/INTEGER and SCALAR/FLOAT words, with formula structure encoded in
word relationships rather than text syntax.
### 7.4 Two Modes, One Architecture

Conventional mode: Draw a flowchart, generate Python or Solidity. The original FlowCode vision, unchanged. Useful for conventional platforms.

Native mode: Draw a flowchart, the TernOO words are already in memory, run them directly on the TernOO interpreter. No compilation step. The drawing canvas and program memory are the same data structure. Modifying a symbol modifies the running program.
### 7.5 The Bootstrap Path

The Python emulator is scaffolding — the modern equivalent of binary hand-
coding. It exists to build the thing that replaces it.

The practical bootstrap path to native execution:

    Python emulator (current) — validates architecture, develops programs
    Python FlowCode IDE — draws symbols, instantiates TernOO words in emulator
    Assembly bridge — Python tool emitting 5500FP assembly from TernOO word sequences, fed to Claudio La Rosa's macro-assembler to produce SD card images
    Native execution — TernOO programs run on actual 5500FP hardware
    Self-hosting — FlowCode native IDE, itself a TernOO program, draws its own successor versions

At step 5, Python has been replaced by drawing. The system is self-hosting
without a text compiler in the loop.
### 7.6 GHOST: The AI-Native Operating System

GHOST (the ghost in the machine — following the GNU tradition of recursive
naming) is not a component added to TernOO-5500FP. It is the emergent
behaviour of the system when FlowCode, GristMill, and the NEURAL word substrate
operate together on native hardware.

The name is precise. A ghost is not the machine — it is the intelligence that
animates it from within. GHOST is what TernOO-5500FP becomes when it is
sufficiently self-hosting to reason about its own programs.

The NEURAL substrate. The NEURAL primary type (Section 3.5) provides the word-level computational primitives for on-device neural inference. A GHOST instance running on TernOO hardware uses NEURAL_UNIT and NEURAL_CONNECTION words as its actual computational substrate — not a software simulation of a neural network, but neural computation encoded in the machine's native word format. A forward pass through a GHOST inference layer is a sequence of NEURAL_CONNECTION word lookups, each performing 9-level ternary weight multiplication using native ternary arithmetic. The 2-trit synaptic weight field (±4 range) exceeds BitNet's {−1,0,+1} expressiveness, making TernOO-native neural inference more expressive per word than the current state of the art in ternary quantisation.

The closed loop. FlowCode, GristMill, and GHOST together form a self- reinforcing triad:

Human intent
     ↓
  GHOST              ← queries GristMill via MAP word bubble search
     ↓                 returns content-addressed TernOO component words
  GristMill
     ↓
  FlowCode           ← renders the composition as visual symbols
     ↓
  Human approves / modifies
     ↓
  Execution          ← same TernOO words run directly

No text compiler. No dependency resolver. No installation step. Intent
maps to TernOO words via GHOST and GristMill; FlowCode makes the mapping
visible and editable; execution follows immediately.

The self-implementing property. The goal of GHOST writing or emerging its own features from within is architecturally achievable, not aspirational. When GHOST is capable of generating valid TernOO word sequences in response to intent descriptions — sequences that are directly executable as FlowCode programs — the development loop closes entirely. GHOST uses TernOO to describe TernOO. The system becomes self-modifying at the word level.

This is distinct from conventional AI code generation, which produces text that
must be compiled. GHOST generates TernOO words directly. The output of inference
IS the program. There is no compilation step because the AI's native output
format and the machine's native execution format are the same thing.

Current status. The NEURAL word types and their field layouts are specified and implemented in v0.3. The forward-pass inference engine — the system that reads a sequence of NEURAL_CONNECTION words and computes activations — is the next implementation milestone. A working GHOST prototype on the emulator will use small NEURAL word sequences for pattern matching and component suggestion in the FlowCode IDE, before targeting native 5500FP hardware.

GHOST is not a chatbot appended to the system. It is the system, when the
system is ready.
8. Implementation
### 8.1 Python Emulator

The TernOO-5500FP emulator (5500fp_ternoo.py, current version 0.3) is a pure Python implementation requiring no dependencies beyond the standard library.

Architecture:

    CPU5500FP class: 81-register file, 24-trit word arithmetic, full fetch-decode-execute loop
    Word constructor functions: build_exec_word(), build_map_word(), build_scalar_word(), build_udp_word(), build_null_word(), build_implicit_null(), build_neural_unit(), build_neural_connection(), build_neural_structure(), build_io_word()
    Word inspector functions: decode_word(), describe_word(), per-type decoders
    Segment register helpers: read_cs(), write_cs(), resolve_exec(), etc.
    Double Null mechanism: 9 independent stacks (ST0–ST8 in R45–R53), RWR in R78
    PIGART renderer: _render_canvas() with ASCII terminal output (Phase 1)
    Asm class: convenience assembler for inline program construction

Opcode set (43 opcodes): Base 5500FP ISA (31): NOP, HLT, ADD, SUB, MUL, DIV, NEG, MOV, LDI, LD, ST, JMP, JSR, RTI, JEQ, JNE, JB, PUSH, POP, MIN, MAX, TXOR, EQUAL, SUM, TTT, TTZ, TTP, ADDI, SUBI, OUT, IN

TernOO word opcodes (7): TOBJ, TGET, TPAYLOAD, TCALL, TNEW, TBUILD, TSEG

PIGART renderer opcodes (5): RPOINT, RLINE, RNODE, REDGE, RENDER

A companion interactive REPL (ternoo_inspector.py) provides word construction, inspection, demo programs, and a Fibonacci demonstration entirely in the emulator.
### 8.2 Test Suite

Seven test functions validate the implementation:

    test_primary_types() — 2+4+18 encoding for all 9 primary types
    test_word_constructors() — all word types, round-trip encode/decode
    test_arithmetic() — ADD, SUB, MUL, NEG regression
    test_renderer() — RNODE, REDGE, RENDER, canvas structure validation
    test_neural_network() — NEURAL_UNIT, NEURAL_CONNECTION construction
    demo_word_gallery() — human-readable display of all primary types

All tests pass on Python 3.12, no external dependencies.
### 8.3 Performance Characteristics

The 24-trit word provides 3²⁴ ≈ 282 trillion unique states, compared to
2³² ≈ 4.3 billion for a 32-bit binary word — approximately 65,000× greater
information density per word.

Dispatch cost comparison (estimated cycles):
| Operation            | Binary OO (typical)  | TernOO-5500FP     |
|----------------------|----------------------|-------------------|
| Object instantiation | 10–50 (heap alloc)   | 1 (word write)    |
| Method dispatch      | 3–5 (vtable)         | 1–2 (field + jump)|
| Type check           | 1–3 (tag test)       | 1 (2-trit fetch)  |
| PIGART symbol render | 100–500 (rasterise)  | <100 (MAP word)   |
| Neural weight lookup | N/A (float)          | 1 (NEURAL word)   |

These estimates assume native 5500FP hardware at 20 MHz. The Python emulator
preserves relative comparisons while absolute cycle times reflect Python overhead.

Zero-copy message passing: USER-DEF POINTER words enable segment register aliasing — two cores can share a data segment by pointing their DS registers at the same base address. Message passing becomes a register write, not a memory copy.
9. Related Work

Tagged architectures: The MIT CADR Lisp machine [Steele and Sussman 1975], the Symbolics 3600, and the Intel iAPX 432 [Myers 1982] established the concept of type information travelling with data words. TernOO-5500FP differs in using the two most significant trits as the invariant primary discriminator and extending type information into full operational semantics via the qualifier trits.

Smalltalk image model: Smalltalk-80 [Goldberg and Robson 1983] achieved a closed loop between running system and development environment within a single object graph. TernOO-5500FP achieves the same property at the machine word level, without a text compiler in the loop.

Visual programming: LabVIEW [Kodosky et al. 1991], Scratch [Resnick et al. 2009], and MIT App Inventor use visual front-ends that compile to conventional backends. The diagram always documents; the compiled output always runs. TernOO-5500FP dissolves this gap structurally.

Ternary neural networks: BitNet b1.58 [Ma et al. 2024] demonstrates that LLM weights quantised to {−1, 0, +1} match full-precision performance with substantial efficiency gains. TernOO's NEURAL_CONNECTION word extends this to 9-level weights (±4) at no extra cost, a finer granularity native to balanced ternary arithmetic.

Content-addressable storage: IPFS [Benet 2014] and Git use content- addressing with Merkle DAGs, where data is located by its hash rather than its physical address. Kademlia DHT [Maymounkov and Mazières 2002] uses XOR-based distance metrics for P2P routing. TernOO-5500FP extends these concepts via the MAP word octree structure (Section 9.4).
### 9.4 TMesh: Tetrahedral Content Identity via Steiner Quasigroup

The TTree coordinate system (Section 3.3.1) provides geometric addresses for
content navigation. The mechanism by which those addresses are traversed to
reconstruct objects is the **TMesh** — a tetrahedral mesh where each triangle
encodes three content chunks (tribbles) in a mutually recoverable relationship.

#### 9.4.1 The Mutual Recovery Operation

The fundamental operation of the TMesh is the **Steiner quasigroup** over
balanced ternary tribbles (Z/3⁶Z, mod 729):

```
A ⊕ B = −(A + B) mod 729
```

For any triple (A, B, C) satisfying C = −(A+B) mod 729:

```
A ⊕ B = C
B ⊕ C = A      (any two sides recover the third)
A ⊕ C = B
```

This operation was confirmed by formal algebraic analysis (DeepAI GPT OSS
120B, June 2026) to be the unique ternary analogue of binary XOR satisfying
the three-way mutual recovery property. Its algebraic properties:

| Property      | Binary XOR          | Ternary ⊕ (mod 729)              |
|---------------|---------------------|-----------------------------------|
| Definition    | (a+b) mod 2         | −(a+b) mod 729                   |
| Commutative   | Yes                 | Yes                               |
| Idempotent    | a⊕a = 0            | a⊕a = a (in characteristic 3)    |
| Self-inverse  | (a⊕b)⊕b = a        | (a⊕b)⊕b = a                      |
| Associative   | Yes                 | No — not required for recovery    |
| Class         | Abelian group       | Steiner quasigroup                |

Implementation in Python (and directly translatable to 5500FP assembly):

```python
MOD = 3**6  # 729 — one 6-trit tribble
def ternary_op(a, b): return (-(a + b) % MOD) % MOD
```

Verified: ternary_op(123, 456) = 150; ternary_op(456, 150) = 123 ✓

#### 9.4.2 TMesh Triangle Structure

Each triangle in the TMesh has three sides, each side carrying one tribble
value. The three sides satisfy the Steiner quasigroup relation: knowing any
two sides recovers the third. This is the content of the triangle — not an
arbitrary coordinate but a genuine algebraic relationship between three content
chunks.

The **traversal accumulator** advances at each triangle step:

```
S_new = (S + C) mod 729
```

where C is the recovered third side. The accumulator is always one tribble.
It is the fingerprint of the traversal path, not the object content itself.
The object is the ordered sequence of triangles visited.

A **sentinel value** of C = 0 signals end-of-object. This reserves exactly
one tribble value (0.14% of the vocabulary) as a termination marker. No
other intrinsic halt condition exists in the Steiner quasigroup algebra.

#### 9.4.3 DAG Property via Vocabulary Ordering (Meccano Set)

The TMesh traversal is a Directed Acyclic Graph (DAG) — paths move forward
only, never revisiting a triangle. This property is enforced by **vocabulary
ordering**: the mesh is populated with a curated, ordered set of machine
operations (the Meccano set) where each traversal step must advance to a
higher-indexed chunk.

The vocabulary must be algebraically closed under the Steiner quasigroup
operation. Closure requires the vocabulary size to be a power of 3. The
minimal useful closed sub-quasigroup of Z/729Z is the 27-element set of
multiples of 27:

```
V₂₇ = {27, 54, 81, ..., 702}   (multiples of 27, size = 3³ = 27)
```

Verified: ternary_op(27, 54) = −81 mod 729 = 648 = 24×27 ∈ V₂₇ ✓

Larger vocabularies use the 81-element set (multiples of 9) or the full
729-element set. The choice determines the expressive range of the Meccano
set — larger vocabularies represent more diverse objects.

The DAG ordering constraint means GristMill's object vocabulary has a natural
dependency order: operations that define values precede operations that consume
them. This is not an imposed convention — it is the natural order of machine
code, falling out of the architecture without overhead.

#### 9.4.4 Relationship to Prior Content-Addressable Work

The tri-mutual dependency structure described in earlier versions of this
section (MaskA = f(Hash(B) ⊕ Hash(C)) etc.) is now formalised as the Steiner
quasigroup. The informal XOR-hash notation was a correct intuition; the
confirmed operation is A ⊕ B = −(A+B) mod 729, which is precisely the
ternary analogue of binary XOR described by the earlier notation.

The "bubble search" navigation remains correct: at each bifurcation the two
candidate next chunks are compared against the target pattern, and the path
that halves the distance to the target is taken. The Steiner quasigroup
provides the third-side recovery at each triangle; the bubble search provides
the navigation decision at each fork.

### 9.5 GristMill: Generative Object Synthesis via TMesh Traversal

GristMill (Grist Is Stable Mnemonic Implicit Learning Libraries) is the
compositional synthesis engine for TernOO-5500FP applications and FlowCode
libraries. GristMill is not a repository — it is a **generator**. Objects
are not stored at locations and retrieved; they are reconstructed by traversal
through the TMesh.

#### 9.5.1 MMID and MMOE

Every TernOO object has two coordinates:

**MMID (Minimal Map ID).** A TTree MAP word (T18=+1) encoding the object's
structural identity. Derived from the structural tribbles of the object's leaf
UDP word. The MMID is small — comparable to a postcode — and encodes what
the object IS structurally, not what content it carries. Objects with similar
structural roles are geometrically close in TTree space.

**MMOE (Minimal Map Object Entity).** An OTree MAP word (T18=0, ABSOLUTE_3D
mode) encoding the object's canonical content address. Derived by folding the
Steiner quasigroup accumulator over all tribbles of the object's complete word
sequence. The MMOE is content-addressable: identical word sequences always
produce the same MMOE, and any change to any word changes the MMOE completely.

The MMID and MMOE are the same size (both are single MAP words). The MMID
is where navigation begins; the MMOE is where it terminates. The object is
what accumulates along the traversal path between them.

#### 9.5.2 Generative Synthesis

Given an MMID, GristMill synthesises the corresponding object by:

1. Locating the MMID in the TTree vocabulary mesh
2. Stepping through successive triangles, recovering the third side at each
   step via the Steiner quasigroup operation
3. Accumulating the traversal state: S = (S + C) mod 729 at each step
4. Terminating when the sentinel value C = 0 is recovered
5. The ordered sequence of recovered C values, decoded as TernOO word
   tribbles, constitutes the object

The object is not retrieved from storage. It is reconstructed by the path.
GristMill is the engine that walks the path.

#### 9.5.3 Ecological Specification (unchanged from v0.3)

GristMill's departure from conventional package management — implicit
ecological specification over reactive sandboxing — remains as described in
earlier versions. Each module carries an intrinsic manifest of its necessary
and sufficient environmental conditions, verified at publish time. The
environment assembles around the function call rather than the other way round.

Application composition follows the appliance metaphor:
Parent Window → Text Canvas → File Dialog → Markup Parser → (optional) P2P Share

Each component's dependency on the prior is an intrinsic property of the
component, not an ad-hoc linkage resolved at install time.

#### 9.5.4 P2P Network Integration

The TMesh/OTree dual coordinate system maps directly onto a three-layer P2P
network stack:

1. **TMesh layer (discovery).** Pure relative geometry, no central authority.
   Nodes navigate the mesh to find objects by structural proximity.
2. **Anchor layer (handshake).** A small set of content-defined OTree
   coordinates that both nodes independently locate via TMesh navigation.
   Shared anchors establish a shared OTree frame without prior coordination.
3. **OTree layer (stable storage).** GristMill objects, versioned libraries,
   and P2P network descriptors at canonical content-derived addresses.

CGP (Constituent Governance Protocol) governance attaches to the anchor layer,
providing democratic validation of shared network anchors via the three-token
triarchy (CitiCoin/AgentCoin/PoliCoin).

### 9.6 Open Questions

**Memory management.** The architecture does not yet specify a garbage
collection model. Reference counting is the natural choice given the multi-core
segment sharing model (Section 8.3), since shared segments must track live
references across cores. A 6-trit reference count field in the segment table
entry supports up to 364 concurrent references.

**Inheritance and subclass chains.** The USER-DEF POINTER subclass field
(T17-T16, 9 variants) is a single-level dispatch mechanism. Deep inheritance
chains are implemented via the CODE-SEG reference, where a subclass's method
handler calls the parent's handler for unhandled messages. Chain depth is
limited only by the call stack, not by word structure.

Multiple inheritance is expected to fall out geometrically from TTree proximity
rather than requiring explicit declaration. Objects satisfying the structural
constraints of two types simultaneously live near both in TTree space — the
inheritance relationship is a geometric fact, not a declared convention. This
hypothesis has not yet been formally verified by prototype.

**Exception and trap handling.** A TernOO-level convention for trap handler
EXEC words — recognisable by a reserved qualifier pattern — would provide
language-level exception semantics above the 5500FP's hardware interrupt layer.
Unspecified in v0.3; flagged for v0.4.

**Interoperability with binary systems.** TernOO-5500FP words serialise to
binary cleanly: the 5500FP's 2-bit trit encoding maps 24 trits to 48 bits,
fitting in a 64-bit host word with 16 bits spare (the TernOO-64 shadow
execution model). Standard protocols transport TernOO word streams as opaque
binary payloads.

**Traversal product convergence.** The mathematical relationship between the
ordered sequence of Steiner quasigroup values recovered during TMesh traversal
and the content of the original object has not yet been formally characterised.
The accumulator state (S = Σ Cᵢ mod 729) identifies the path uniquely for
path lengths < 729. Whether the full ordered sequence of recovered values
constitutes a sufficient reconstruction of the original object content — and
under what conditions — is an open question requiring further algebraic analysis.

**MMID second dimension.** The current MMID encoding is effectively
one-dimensional: both UDP subclass trits land in tribble A (ta), leaving
tribble B (tb) = 0 for objects with zero OFFSET. A second structural dimension
— proposed as the EXEC word's tribble B, encoding calling convention — would
give MMID a two-dimensional structure where Y encodes structural role and Z
encodes interaction style. Pending implementation.

**Boot ROM layout.** The class hierarchy type descriptors for the Boot ROM
can now be specified: the OTree/TTree coordinate decision is resolved, the
primal object word sequence is confirmed (MAP ORIGIN + UDP(0,0) + EXEC basic),
and MMOE addresses are derivable by ternary_op fold over word tribbles. The
Boot ROM layout itself — segment register initial values, type descriptor
ordering, method table structure — is unspecified in v0.3.

---

## 10. Conclusion

TernOO-5500FP demonstrates that object-oriented structure can be intrinsic to
a machine's word format rather than layered on top of it. The 24-trit balanced
ternary word provides exactly the structural space required: two trits for
primary type (nine categories), four for operational semantics (81 qualifier
combinations per type), and eighteen for payload — with the USER-DEF POINTER
compressing a complete process launch descriptor (code, data, and cursor)
into that payload.

The expansion to nine primary types enables neural network primitives (NEURAL)
and I/O streams (I/O) as first-class word types, alongside the existing EXEC,
MAP, and DATA types. NEURAL_CONNECTION words with 9-level ternary weights
exceed BitNet's {−1,0,+1} expressiveness natively. I/O words encode stream
direction, buffering, and blocking behaviour in a single qualifier.

The Double Null mechanism extends the word grammar to meta-level constructs,
allowing any user to define their own "reserved words" as context entries on
nine independent stacks, without requiring new primary types.

PIGART closes the loop with a renderer in which MAP words directly drive
geometric output. The scene graph in memory and the program in memory are the
same data structure.

The MAP word's octree structure serves double duty as a content-addressing
substrate: data is located by its hash coordinates in 3D space, not by
arbitrary linear addresses. The tri-mutual dependency triangle provides lateral
self-validation without hierarchical Merkle trees.

GristMill proposes a component repository where dependencies are ecological
properties of modules, not post-hoc linkages.

The path to a self-hosting visual programming environment on native balanced
ternary hardware is clear. The Python emulator is the scaffolding. FlowCode
in TernOO native mode is the destination. The point at which Python stops
being permitted is not a prohibition — it is an obsolescence, brought about
by drawing.

---

## References

Benet, J. (2014). IPFS — Content Addressed, Versioned, P2P File System.
*arXiv:1407.3561*.

Goldberg, A. and Robson, D. (1983). *Smalltalk-80: The Language and its
Implementation*. Addison-Wesley.

Hayes, B. (2001). Third Base. *American Scientist*, 89(6), 490–494.

Kay, A. (1993). The Early History of Smalltalk. *ACM SIGPLAN Notices*, 28(3), 69–95.

Kodosky, J. et al. (1991). Visual programming using structured data flow.
*IEEE Workshop on Visual Languages*.

La Rosa, C.L. (2026). *5500FP: A 24-Trit Balanced Ternary RISC Processor.*
Zenodo. https://doi.org/10.5281/zenodo.18881738

Ma, S. et al. (2024). The Era of 1-Bit LLMs: All Large Language Models are in
### 1.58 Bits. *arXiv:2402.17764*.

Maymounkov, P. and Mazières, D. (2002). Kademlia: A Peer-to-Peer Information
System Based on the XOR Metric. *IPTPS 2002*.

Myers, G.J. (1982). *Advances in Computer Architecture*, 2nd ed. Wiley.

Resnick, M. et al. (2009). Scratch: Programming for all. *CACM*, 52(11), 60–67.

Steele, G.L. and Sussman, G.J. (1975). Scheme: An interpreter for extended
lambda calculus. *MIT AI Memo 349*.
