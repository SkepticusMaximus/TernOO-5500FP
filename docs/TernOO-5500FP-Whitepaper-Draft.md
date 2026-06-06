# TernOO: A Self-Describing Object Architecture for Balanced Ternary

**Stevo (SkepticusMaximus)**  
Independent Developer, Adelaide, South Australia  
https://github.com/SkepticusMaximus

*Draft v0.1 — May 2026*  
*Companion implementation: https://github.com/SkepticusMaximus/TernOO-5500FP*

---

## Abstract

We present TernOO-5500FP, a word architecture for the 5500FP balanced ternary
processor in which every 24-trit word is self-describing. The most significant
trit of each word identifies its primary type — executable code (EXEC),
spatial coordinate (MAP), or data value (DATA) — and the three qualifier trits
that follow encode the word's full operational semantics without requiring any
additional memory fetch or runtime type check. In the most general case, a
single word carries its own code segment reference, data segment reference, and
internal cursor: a complete process launch descriptor in 24 trits.

We describe the word grammar, the Double Null mechanism for defining
user-extensible meta-constructs without reserved words or additional primary
types, and a set of renderer opcodes in which geometric primitives emerge
directly from MAP words. The result is an architecture in which the distinction
between code and data, between object and pointer, and between diagram and
program dissolves at the word level — not as a software abstraction but as a
structural property of the machine.

A Python emulator implementing the full architecture is available as open
source. The architecture targets the 5500FP processor described in La Rosa
(2026) and is designed as a candidate ISA extension for that platform.

---

## 1. Introduction

### 1.1 The Case for Ternary

Binary computing dominates modern hardware for an accident of fabrication
history rather than mathematical necessity. Transistors switch between two
voltage states cleanly, and this physical convenience became the foundation of
an entire civilisation of computing. But the mathematics of information
representation does not privilege two. The radix that minimises the product of
the number of digits and the base — the so-called radix economy — is *e*,
approximately 2.718. The nearest integer is three.

Balanced ternary, in which digits take values in {−1, 0, +1}, is particularly
elegant. It is symmetric — negation requires only inverting all trit signs,
with no asymmetric edge case as in two's complement. It is efficient — a
24-trit balanced ternary word represents a range of approximately ±141 billion,
compared to ±2 billion for a 32-bit binary word, using only 50% more signal
lines on native silicon [La Rosa 2026]. And it is natural for problems with
three-valued structure: direction (negative, zero, positive), decision (yes,
no, maybe), and the spatial axes of three-dimensional geometry.

The recent emergence of ternary-quantised neural networks — in which model
weights are restricted to {−1, 0, +1} and performance matches full-precision
models at a fraction of the memory and energy cost [Ma et al. 2024] —
provides independent confirmation from a completely different domain that the
three-valued representation offers fundamental efficiency advantages. The
theoretical case for ternary is becoming an empirical one.

The 5500FP processor [La Rosa 2026] is the most complete realisation of a
programmable balanced ternary processor available today: a 24-trit RISC
architecture implemented on FPGA with a 120-instruction ISA, native atomic
synchronisation primitives, an open hardware development board, and a minimal
operating system kernel. It provides the substrate on which TernOO-5500FP is
built.

### 1.2 The Case for Object-Oriented Structure at the Word Level

Object-oriented programming has been the dominant paradigm for software
architecture since the 1980s, yet its relationship with the underlying machine
has always been one of translation and overhead. In every mainstream OO
language — Smalltalk, C++, Java, Python — objects are a software construct
layered on top of a machine that knows nothing about them. Method dispatch
requires a pointer dereference, a vtable lookup, argument marshalling, and a
branch. The object model is imposed from above; the machine is indifferent.

This is not what Alan Kay envisioned when he invented object-oriented
programming. Kay's original conception, articulated at Xerox PARC in the early
1970s, was that "the ideal object-oriented object is itself a computer" — that
each object should be capable of receiving a message and responding
autonomously, without the sender knowing anything about the receiver's
internals. The decades of OO practice that followed produced increasingly
sophisticated software approximations of this idea, but the underlying machine
remained a flat sequence of bytes, ignorant of the structure imposed on it.

TernOO-5500FP takes a different approach. Rather than implementing OO as a
layer above the machine, we ask: what if the machine's word format itself
encoded object structure? What if every word carried not just its value but
its type, its operational role, and in the most capable case, its own
executable reference, its own data reference, and its own internal state?

The 24-trit word of the 5500FP provides exactly enough space for this. One
trit identifies the primary type. Three trits qualify the semantics within
that type. The remaining twenty trits carry the payload — value, coordinate,
or structured object descriptor. No external lookup. No runtime overhead. No
translation layer between the programmer's object model and the machine's
representation of it.

### 1.3 The Dimensional Advantage

The three qualifier trits in MAP words carry a specific geometric insight. Each
trit encodes directional sense along one axis pair of a three-dimensional
coordinate frame. The result is an octree coordinate system intrinsic to the
word format — a machine that natively understands spatial position, not as an
integer to be interpreted by software, but as a structured qualifier
describing where in three-dimensional space a value lives.

The economic argument is the same as vector graphics over raster graphics.
A bitmap encodes every pixel explicitly — the structure is in the enumeration.
A vector drawing encodes the rules that generate the image — the structure is
in the description. MAP words encode 3D position as directional sense plus
magnitude, not as three separate integers. The information density is
intrinsic and bottom-up, emerging from the word structure, not imposed by an
external compression algorithm.

This matters for the applications TernOO-5500FP is designed to support: polygon
mesh representation, network topology description, and the geographic scope
encoding required by the Consensus Governance Protocol (CGP) — a
decentralised democratic governance system whose smart contract infrastructure
motivated much of this architecture.

### 1.4 Contributions

This paper makes the following contributions:

1. **The TernOO word grammar**: a complete specification of a 24-trit word
   format in which primary type, operational semantics, and object structure
   are encoded in the word itself without external descriptors.

2. **The USER-DEFINED POINTER**: a word type that carries its own code segment
   reference, data segment reference, and internal cursor — a complete process
   launch descriptor in 24 trits, enabling object dispatch with zero vtable
   overhead.

3. **The Double Null mechanism**: a general-purpose meta-construct primitive
   that allows users to define their own "reserved words" and structured
   interpretation contexts without introducing new primary types or text-based
   keywords into the machine.

4. **Renderer opcodes**: a set of five opcodes that render geometric primitives
   directly from MAP words, enabling a visual programming environment in which
   the diagram and the program are the same object in memory.

5. **An open-source Python emulator** implementing the full architecture,
   available at https://github.com/SkepticusMaximus/TernOO-5500FP.

### 1.5 Paper Organisation

Section 2 provides background on the 5500FP architecture and the prior
SBTCVM TernOO implementation from which this work derives. Section 3 describes
the TernOO word grammar in full. Section 4 details the USER-DEFINED POINTER
and its properties. Section 5 describes the Double Null mechanism. Section 6
covers the renderer opcodes. Section 7 discusses the visual IDE vision.
Section 8 describes the implementation. Section 9 surveys related work.
Section 10 concludes.

---

---

## 2. Background

### 2.1 Terminology Note

This paper uses the word "word" in three distinct senses that are worth
distinguishing at the outset. A *machine word* is the native 24-trit unit
of the 5500FP processor. A *TernOO word* is any machine word interpreted
under the TernOO architecture — a machine word whose structure carries
type and semantic information in its trit fields. A *natural language word*
is what you are reading now. Context makes the intended sense clear in
all but a handful of cases; where ambiguity might arise, we prefer "machine
word" or "TernOO word" for precision.

We also distinguish *symbols* (the primitive elements of a flowchart —
process rectangles, decision diamonds, and so on) from *nodes* (the
vertices of a network topology graph). TernOO-5500FP is designed to
represent both, and conflating the terms in a system that explicitly
supports both would be, to borrow a technical term, a mess.

Finally, we distinguish *tokens* from *coins*. A token, in this paper,
is an intangible, not-normatively-liquid digital asset that represents
value within a specific system — Proof-of-Deliberation tokens and
CompuTokens are tokens in this sense. A coin is fungible and liquid,
intended for exchange like currency whether physical or digital. The
Consensus Governance Protocol's CitiCoin sits closer to coin; its
CompuToken sits firmly as token. The AI inference sense of "token" — a
unit of processed meaning — is closer to the token sense than the coin
sense, and requires no disambiguation from either.

### 2.2 The 5500FP Processor

The 5500FP [La Rosa 2026] is a 24-trit balanced ternary RISC processor
implemented on an Efinix Trion T20F256 FPGA, clocked at 20 MHz. Its
principal architectural features are:

**Word width.** 24 trits, chosen from the doubling series (24 → 48 → 96)
rather than the power-of-three series (27 → 81 → 243). At 24 trits the
representable range (±141 billion) already exceeds a 32-bit binary
processor (±2 billion) by a factor of 66, using only 50% more signal
lines on native silicon. The 24-trit word divides cleanly into six 4-trit
fields with no remainder, into four 6-trit tribbles, and into two
12-trit shorts — properties that are architecturally convenient throughout
the 5500FP ISA and that TernOO-5500FP exploits directly.

**Register file.** 81 general-purpose registers, each one machine word
wide, addressed by a 4-trit identifier (3⁴ = 81). R0 is hardwired to
zero. The 81-register file substantially exceeds the 32 or 64 registers
typical of binary RISC processors, reducing memory spill frequency and
providing ample room for TernOO-5500FP's dedicated segment register
allocation.

**ISA.** Approximately 120 instructions in nine formats (A through F,
J, J2–J4), all 24 trits wide, all fields 4 trits each. Notably includes
a ternary-native instruction group — MIN, MAX, TXOR, EQUAL, SUM, CONS,
ANY, IMPL, and the DECOT/DECOU/DECOF trit-decode instructions — with
no binary equivalent. Native atomic synchronisation primitives (CAS, FAA)
support lock-free data structures. Opcodes are 4-trit sequences,
reflecting the native ternary representation throughout.

**Privilege levels.** User and kernel modes with hardware-level isolation
via dual stack pointers. TernOO-5500FP maps this to the EXEC word's
privilege qualifier trit.

**Development platform.** The GargantuRAM 1.5 PRE development board
(open hardware, CERN OHL-P v2) provides 16M words of static RAM, SD
card mass storage, two serial interfaces, and SPI ROM. A minimal OS
kernel (GRam_OS) provides basic hardware initialisation and interactive
shell. A macro-assembler for the ISA is available for Windows, with
Linux and macOS support in development.

The 5500FP's microarchitecture is open for independent implementation,
while the ISA is patent and copyright protected. TernOO-5500FP is
designed as a candidate ISA extension — specifically, as a set of
higher-level semantics for the word format and a small set of dispatcher
opcodes that the 5500FP ISA can implement via its existing instruction
infrastructure.

### 2.3 Prior Work: SBTCVM TernOO

TernOO-5500FP derives directly from TernOO, an experimental
object-oriented extension to SBTCVM Gen2-9, developed by the first
author in early 2026. SBTCVM (Stacking Balanced Ternary Computing Virtual
Machine) is a balanced ternary virtual machine developed by Thomas
Leathers as a pedagogical and research platform. TernOO added four
hardware opcodes (200–203) to SBTCVM's instruction set, using the leading
trit of SBTCVM's 9-trit tryte as a type tag to distinguish three primitive
roles:

- **T (−1):** EXEC — executable reference
- **U ( 0):** DATA — plain value
- **F (+1):** REF  — reference/pointer

The type-trit mechanism enabled three-way dispatch on a single trit,
without any software wrapper layer. A working implementation, a Project
Hub with documentation and an interactive Object Inspector, and a
VirtualBox appliance were published to GitHub and the Internet Archive
in April 2026.

TernOO-5500FP preserves the core insight — the leading trit as type
discriminator, three-way dispatch as the fundamental OO primitive —
while replacing every SBTCVM-specific constraint with a design derived
from the 5500FP's richer architecture:

| Property          | SBTCVM TernOO        | TernOO-5500FP                  |
|-------------------|----------------------|--------------------------------|
| Word width        | 9 trits              | 24 trits                       |
| Payload           | 8 trits (±3,280)     | 20 trits typical (±1.74B)      |
| Type tags         | EXEC / DATA / REF    | EXEC / MAP / DATA              |
| Tag rationale     | SBTCVM opcode space  | First principles               |
| Pointer models    | 1 (Option A)         | 9 (including USER-DEF)         |
| Object descriptor | External (registers) | Self-contained in word         |
| Meta-constructs   | None                 | Double Null / 9 stacks / RWR   |
| Renderer          | None                 | RPOINT RLINE RNODE REDGE RENDER|

The most significant departure is the replacement of SBTCVM's EXEC/DATA/REF
taxonomy with EXEC/MAP/DATA. SBTCVM placed EXEC on the negative trit
because SBTCVM's opcode space occupied negative values — a substrate
constraint with no counterpart on the 5500FP. MAP is an entirely new
primary type with no SBTCVM equivalent, encoding three-dimensional spatial
position via the octree qualifier mechanism described in Section 3.

### 2.4 Tagged Architectures and Lisp Machines

The idea of storing type information alongside data values has a long
history in computer architecture. Lisp machines of the 1970s and 1980s
— the MIT CADR, the Symbolics 3600, the Texas Instruments Explorer —
included hardware tag fields in every word to distinguish integers, floats,
pointers, and other Lisp types, enabling garbage collection and dynamic
dispatch without software overhead [Steele and Sussman 1975].

The Intel iAPX 432 (1981) took this furthest in a commercial binary
processor, using a capability-based tagged architecture in which every
object carried access rights and type information. The iAPX 432 was a
commercial failure, widely attributed to performance overhead from its
complexity, but its architectural vision anticipated much of what later
became accepted practice in managed language runtimes.

TernOO-5500FP differs from these approaches in two respects. First, the
type tag is not an auxiliary field appended to a binary word — it is the
most significant trit of a balanced ternary word, an architecturally
natural position in a signed symmetric number system where the sign of
the MST already carries directional information. Second, the qualifier
trits extend the type information beyond a simple category tag into a
full operational descriptor, carrying calling convention, spatial
coordinates, or object structure depending on the primary type. The
word is not tagged with its type; it *is* its type, structurally.

### 2.5 The Consensus Governance Protocol

One of the primary motivations for TernOO-5500FP is the smart contract
infrastructure required by the Consensus Governance Protocol (CGP) —
a decentralised democratic governance system developed by the first
author over several decades, predating this work by many years.

CGP formalises democratic consensus into tangible, incentivised mandates
via a three-token architecture modelled on Ohm's Law:

- **CitiCoin**: the citizen participation coin, liquid and fungible,
  staked to signal deliberative engagement.
- **CompuToken**: a non-liquid token earned by contributing compute
  resources to the P2P Compute Protocol (P2PCP) network, spent to
  consume compute. Minted on verified contribution, burned on consumption.
- **PoliCoin**: minted to politicians on verified policy delivery,
  funded from the residual mandate pool after Proof-of-Resolution.

The three tokens are interdependent — no bilateral trades are permitted,
and value flows only through the triarchy as a whole. Mandate lifecycle
is governed by three phases: Proof-of-Deliberation (PoD), Proof-of-Measurement
(PoM), and Proof-of-Resolution (PoR), implemented as Ethereum smart
contract state machines.

CGP's geographic mandate scope — "this mandate applies to all participants
in this region" — is a natural use case for MAP words with octree qualifier
encoding. The spatial scope of a mandate is a first-class architectural
primitive, not a software-layer addition.

The SolidiFlow IDE — a visual, codeless Solidity smart contract authoring
tool that generates deployable Ethereum contracts from flowchart diagrams
— is being developed as the primary authoring environment for CGP and
P2PCP contracts. SolidiFlow is itself a proof of concept for the FlowCode
visual programming paradigm of which TernOO-5500FP's renderer is the
machine-level expression.

*[Sections 3–6 to follow]*

---

## 7. The Visual IDE Vision: FlowCode as TernOO Compiler

### 7.1 The ASCII Workaround

There is no point in making a computer speak a dialect of English in order
to tell it how to be a bunch of connected switches. It already is a bunch
of connected switches. If some of those switches are wired to a graphical
matrix, then graphical symbolic mnemonic primitives are the shortest line
between the programmer's intent and the machine's behaviour.

This observation, obvious in retrospect, took sixty years to arrive at
because of an accident of history. Early computers had keyboards. Keyboards
produced character codes. Character codes were mapped to numbers — ASCII,
EBCDIC, and their descendants — and those numbers were given to the
processor. The symbols, though graphical in origin (letters are shapes),
were not used as graphical primitives. They were grouped into words, words
into syntax, syntax into language constructs, and the whole edifice was
handed to a compiler that translated it into the switching patterns the
machine actually understood.

Text became the universal medium for programming not because it was the
right abstraction but because it was the available one. The keyboard was
there. The screen could display characters. So text became the language
of computers, and sixty years of tooling, convention, education, and
habit cemented it in place so thoroughly that it became invisible as a
choice. The computer was never consulted.

Assembly language is text. High-level languages are text. Even visual
programming tools — LabVIEW, Scratch, MIT App Inventor — use a visual
front-end that compiles to text that compiles to binary. The diagram is
documentation. The compiled output is the real thing. The visual
representation and the executable representation are different objects
that must be kept in sync by a translation process.

TernOO-5500FP offers a different path.

### 7.2 The Structural Dissolution of the Diagram/Program Gap

In every prior visual programming system, the gap between diagram and
program is a fundamental architectural feature. You draw a diagram. A
compiler reads the diagram and produces code. The code is what runs. The
diagram is what the human reads. They are different representations of
the same intended behaviour, and keeping them consistent is the compiler's
job.

In TernOO-5500FP, this gap does not exist. It is not bridged by a clever
compiler. It is dissolved by the word architecture.

A flowchart symbol drawn on screen corresponds to a TernOO word in memory.
A process rectangle corresponds to a USER-DEF POINTER word — carrying its
own code segment reference, data segment reference, and internal cursor.
A decision diamond corresponds to a SCALAR/FLOAT word (the diamond encoding
is intrinsic to the scalar subtype trit). A connection arrow between two
symbols corresponds to an EXEC word — carrying its calling convention,
privilege level, and return type in its qualifier trits.

The renderer reads these words and displays the diagram.  
The executor reads the same words and runs the program.  
They are the same words. There is one source of truth.

Drawing a symbol does not *describe* a computation. It *is* the
computation, encoded as a TernOO word in memory. The IDE does not sit in
front of a compiler. The IDE is the compiler. The act of drawing
completes the program.

### 7.3 FlowCode as TernOO Assembly Language

FlowCode was conceived as a general-purpose visual programming environment
that would allow domain experts without programming knowledge to author
complex software by drawing flowcharts — using the visual vocabulary of
process symbols, decision symbols, and directed connections as a
programming language rather than a documentation language.

The original FlowCode vision targeted conventional language backends:
Python, and eventually Solidity for smart contract authoring (via the
SolidiFlow IDE, a domain-specific precursor). In this framing FlowCode
was a graphical front-end to a text compiler: draw a diagram, generate
source code, compile the source code, run the binary.

TernOO-5500FP reveals a more fundamental role. FlowCode, targeting the
TernOO word architecture, is not a front-end to a compiler. It is the
assembly language itself — a graphical assembly language in which the
symbol vocabulary replaces mnemonic text, visual connection replaces
syntax, and spatial layout replaces program structure.

The correspondence is direct:

| Conventional assembly  | FlowCode / TernOO                          |
|------------------------|--------------------------------------------|
| Mnemonic (ADD, MOV...) | Symbol shape (rectangle, diamond, arrow)   |
| Operand registers      | Symbol connections (which flows to which)  |
| Addressing mode        | Connection style (EXEC qualifier trits)    |
| Data declaration       | DATA symbol (SCALAR, STRING, POINTER)      |
| Code label             | EXEC word (entry point reference)          |
| Jump instruction       | Directed connection to target symbol       |
| Program structure      | Spatial arrangement of symbols             |

The assembler — the tool that translates assembly language into machine
words — is the FlowCode IDE itself. When a programmer draws a connection
between two symbols, the IDE writes an EXEC word into memory. When they
draw a decision diamond, the IDE writes a SCALAR/FLOAT word. The
"assembly" step is the drawing step. They are the same act.

### 7.4 The Symbol Vocabulary as Instruction Set

A conventional instruction set is defined by its opcodes — a table of
numeric codes, each corresponding to one machine operation. The programmer
learns the table and writes programs using it.

The TernOO-FlowCode instruction set is defined by its symbol vocabulary —
a table of visual shapes, each corresponding to one word type. The
programmer learns the shapes and draws programs using them.

The symbol vocabulary for a minimal TernOO-FlowCode implementation:

| Symbol shape          | TernOO word type          | Semantics                    |
|-----------------------|---------------------------|------------------------------|
| Rectangle             | USER-DEF POINTER (rect)   | Process / computation        |
| Diamond               | USER-DEF POINTER (diamond)| Decision / conditional       |
| Rounded rectangle     | USER-DEF POINTER (rounded)| I/O / terminal               |
| Solid arrow           | EXEC (register-call)      | Sequential control flow      |
| Double arrow          | EXEC (stack-call)         | Subroutine call              |
| Dashed arrow          | EXEC (message-pass)       | Asynchronous / event         |
| Coordinate marker     | MAP word                  | Spatial reference / position |
| Value label           | SCALAR word               | Data value                   |
| Reference marker      | POINTER word              | Memory / object reference    |
| Context bracket       | Double Null (implicit)    | Scoped interpretation        |

This is not a metaphor. These shapes are not annotations on a program
that exists elsewhere. They are the program. Their trit encodings in
memory are the executable representation. The display on screen is the
same data viewed through the renderer rather than the executor.

### 7.5 Two Modes, One Architecture

FlowCode as TernOO compiler has two operational modes that can coexist
in the same tool:

**Conventional mode:** Draw a flowchart, generate Python, Solidity, or
other text-based output. This is the original FlowCode vision, unchanged.
The visual diagram is a design tool; the generated code is the deliverable.
Useful for targeting conventional platforms — Ethereum smart contracts,
general-purpose Python applications.

**Native mode:** Draw a flowchart, the TernOO words are already in memory,
run them directly on the TernOO interpreter. No compilation step. No
intermediate representation. The drawing canvas and the program memory
are the same data structure. Useful for targeting the 5500FP, a Pi running
the TernOO emulator, or any platform where the TernOO interpreter is
available.

In native mode the IDE achieves something no prior visual programming
environment has achieved: the closed loop. The programmer draws a symbol.
The word is in memory. The renderer displays it. The executor runs it.
Modifying the symbol modifies the running program. The development
environment and the running system are the same thing — not as an
aspirational design goal, but as a structural consequence of the word
architecture.

This is what Alan Kay described as the ideal of Smalltalk — the image
in which the system and its development environment are the same object
graph. Smalltalk achieved it in software on a binary machine, with the
inevitable translation overhead. TernOO-5500FP achieves it structurally,
at the word level, because there is nothing to translate.

### 7.6 The Bootstrap Consequence

A conventional programming language requires a bootstrap: some prior
language or tool must exist to build the first compiler. The first
assembler was written in binary by hand. The first C compiler was written
in assembly. Every language stands on the shoulders of a language that
came before, and the chain terminates in a programmer toggling switches.

FlowCode as TernOO compiler has a different bootstrap path. The Python
emulator we have built is scaffolding — the modern equivalent of binary
hand-coding. It exists to build the thing that replaces it. Once the
TernOO word interpreter runs on native hardware, and once the FlowCode
visual IDE runs on the TernOO interpreter, the scaffolding can be set
aside. The system draws itself.

Every FlowCode symbol drawn in the native IDE is a TernOO word. The IDE
itself, when implemented in native mode, is a collection of TernOO words.
The tool that builds programs is itself a program built with the same tool.
The system is self-hosting, without a text compiler anywhere in the loop.

This is the point where Python stops being permitted. Not by prohibition,
but by obsolescence. The visual symbol vocabulary has become the assembly
language. Drawing has become programming. The shortest line between human
intent and machine behaviour runs through a shape drawn on screen, not a
word typed on a keyboard.

*[Sections 3–6, 8–10 to follow]*

---

## References

La Rosa, C.L. (2026). *5500FP: A 24-Trit Balanced Ternary RISC Processor
implemented on FPGA with an Open Hardware Development Platform.* Zenodo.
https://doi.org/10.5281/zenodo.18881738

Ma, S., Wang, H., Ma, L., Wang, L., Wang, W., Huang, S., Dong, L., Wang, R.,
Xue, J., and Wei, F. (2024). The Era of 1-Bit LLMs: All Large Language Models
are in 1.58 Bits. *arXiv preprint arXiv:2402.17764.*

Kay, A. (1993). The Early History of Smalltalk. *ACM SIGPLAN Notices*, 28(3),
69–95.

Knuth, D.E. (1981). *The Art of Computer Programming, Vol. 2: Seminumerical
Algorithms*, 2nd ed. Addison-Wesley.

Hayes, B. (2001). Third Base. *American Scientist*, 89(6), 490–494.
