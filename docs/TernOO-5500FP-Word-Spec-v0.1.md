# TernOO/5500FP Word Architecture Specification
## v0.1 — Working Draft

**Author:** Stevo (SkepticusMaximus)  
**Collaborator:** Claude (Anthropic)  
**Date:** May 2026  
**Status:** Working Draft — not yet implemented  
**Companion:** 5500fp_emulator.py (CPU5500FP + TernOO v0.1.0)

---

## Preamble

This document specifies the TernOO word architecture as adapted for the 5500FP
24-trit balanced ternary processor. It deliberately diverges from the SBTCVM
Gen2-9 TernOO implementation where the 5500FP's richer architecture permits
superior design. No SBTCVM compromise is inherited without explicit justification.

The central thesis: **every 24-trit word is self-describing.** The word's header
trits encode not just its type but its full operational semantics — calling
convention, dimensional coordinates, scalar encoding, pointer model, and in the
most general case, its own code segment, data segment, and internal cursor. Object
dispatch requires no vtable lookup, no runtime type check, and no additional memory
cycles beyond the fetch of the word itself.

This is not object-oriented programming layered on top of a machine. It is
object-oriented structure intrinsic to the machine word.

---

## 1. The 24-Trit Word

All memory locations and registers hold 24-trit balanced ternary words.  
Trit positions are numbered T0 (LSB) through T23 (MSB).  
Trit values: N = −1, Z = 0, P = +1 (also written −, 0, +).

The word is divided into three functional regions:

```
T23          T22–T20         T19–T0
─────────    ───────────     ──────────────────────
PRIMARY      QUALIFIER       PAYLOAD
(1 trit)     (3 trits)       (20 trits)
type ID      type grammar    value / address / data
```

**T23 — Primary type identifier (always decoded first, always fixed):**

| T23 | Symbol | Primary Type |
|-----|--------|--------------|
| −1  | N      | EXEC         |
| 0   | Z      | MAP          |
| +1  | P      | DATA         |

The primary trit is architecturally invariant. No format redefinition can move
or reinterpret it. This provides a stable, zero-overhead dispatch point for the
CPU's fetch-decode loop regardless of any higher-level format in use.

The qualifier trits (T22–T20) refine meaning within each primary type.  
The payload (T19–T0) carries the value, address, or structured content.

In several word types, the qualifier region extends beyond T20 and the payload
shrinks accordingly. Each case is specified below.

---

## 2. EXEC Words (T23 = −1)

An EXEC word is a reference to executable code. The qualifier trits encode the
function's complete calling contract, so call-site compatibility can be verified
at fetch time with no runtime overhead.

```
T23   T22          T21            T20           T19–T0
 −    PRIVILEGE    CALL-STYLE     RETURN-TYPE   20-trit function address
```

### 2.1 Qualifier Fields

**T22 — Privilege level:**

| T22 | Privilege |
|-----|-----------|
| −1  | Kernel    |
| 0   | User      |
| +1  | Sandbox   |

**T21 — Calling convention:**

| T21 | Convention   | Meaning                                      |
|-----|--------------|----------------------------------------------|
| −1  | Stack        | Arguments passed on the stack                |
| 0   | Register     | Arguments passed in registers (R1–R8)        |
| +1  | Message      | Arguments passed as a MAP or DATA word       |

**T20 — Return type:**

| T20 | Return type |
|-----|-------------|
| −1  | EXEC        |
| 0   | MAP         |
| +1  | DATA        |

### 2.2 Payload

T19–T0: 20-trit function address (range ±1,743,392,200).  
Sufficient to address any location in a 5500FP memory space.

### 2.3 Rationale

Encoding privilege, calling convention, and return type in the EXEC word means:

- A caller fetches the EXEC word and immediately knows how to set up the call.
- A kernel security monitor can verify privilege at fetch time.
- A static analyser can check return-type compatibility without executing the code.
- No separate function descriptor structure is needed.

This gives typed function pointers — a safety feature normally associated with
compiled languages like Rust — at the hardware word level, for free.

---

## 3. MAP Words (T23 = 0)

A MAP word encodes a position or reference in three-dimensional space using an
octree coordinate system. The three qualifier trits each represent one axis
pair of a 3D coordinate frame.

```
T23   T22       T21       T20       T19–T0
 0    AXIS-YZ   AXIS-XZ   AXIS-XY   20-trit coordinate payload
```

### 3.1 Octree Qualifier Fields

Each qualifier trit encodes directional sense along its axis pair:

| Trit | Meaning on axis pair          |
|------|-------------------------------|
| −1   | Negative direction / below    |
| 0    | On-plane / at boundary        |
| +1   | Positive direction / above    |

The three qualifier trits together define a position in an octree:

```
{T22, T21, T20} → one of 27 possible qualifier states

Special cases:
  { 0,  0,  0} = origin (all axes intersect at zero)
  {±1,  0,  0} = on XZ and XY planes (YZ-axis only)
  { 0, ±1,  0} = on YZ and XY planes (XZ-axis only)
  { 0,  0, ±1} = on YZ and XZ planes (XY-axis only)
  any single 0 = on a plane boundary (scope/scale anchor)
  all non-zero = fully positioned in 3D space
```

### 3.2 Dimensional Economics

The redundant zero states (any qualifier trit = 0) serve as scope and scale
anchors — equivalent to a zoom level in a vector graphics system. This means
MAP words can encode both absolute positions and relative/scaled references
within the same word format, without additional flags.

This provides the same economic advantage as vector graphics over bitmaps:
structure is encoded as rules (directional sense + scale) rather than as
exhaustive enumeration of points. The information density is intrinsic and
bottom-up, not imposed by a compression algorithm.

### 3.3 Payload

T19–T0: 20-trit coordinate value, distance, or index.  
Interpretation depends on qualifier state (absolute, relative, or scaled).

### 3.4 Use Cases

- Polygon mesh vertex coordinates
- Network topology node references (P2PCP node addressing)
- Spatial index keys for octree data structures
- CGP mandate geographic scope encoding

---

## 4. DATA Words (T23 = +1)

DATA words carry values, pointers, and strings. The secondary trit (T22) selects
among three DATA subtypes; the tertiary trit (T21) further refines each subtype.

```
T23   T22          T21         T20–T0
 +    SECONDARY    TERTIARY    payload (varies by subtype)
      DATA type    subtype
```

### 4.1 Secondary Type (T22)

| T22 | Subtype |
|-----|---------|
| −1  | SCALAR  |
| 0   | POINTER |
| +1  | STRING  |

---

### 4.2 SCALAR (T22 = −1)

```
T23   T22   T21          T20–T0
 +     −    ENCODING     21-trit scalar value
```

**T21 — Scalar encoding:**

| T21 | Encoding             |
|-----|----------------------|
| −1  | Float (fixed-point)  |
| 0   | Integer (balanced ternary native) |
| +1  | Unsigned             |

Payload: T20–T0 = 21 trits, range ±1,743,392,200.

---

### 4.3 STRING (T22 = +1)

```
T23   T22   T21          T20–T0
 +     +    ENCODING     21-trit length or pointer
```

**T21 — String encoding:**

| T21 | Encoding                      |
|-----|-------------------------------|
| −1  | Unicode (UTF-8 compatible)    |
| 0   | ASCII / byte sequence         |
| +1  | Ternary glyph (native symbol) |

Payload: T20–T0 = length (inline short strings) or address of string data.

---

### 4.4 POINTER (T22 = 0)

The pointer subtype uses two qualifier trits (T21 and T20) together to select
one of nine pointer models. Eight are predefined native models; the ninth is
user-defined and extensible.

```
T23   T22   T21   T20   T19–T0
 +     0    PTR-MODEL   payload (varies by model)
```

**Pointer model table (T21, T20):**

| T21 | T20 | Model               | Description                              |
|-----|-----|---------------------|------------------------------------------|
| −1  | −1  | FLAT                | Direct memory address                    |
| −1  | 0   | RELATIVE            | Offset from current PC                   |
| −1  | +1  | STACK-REL           | Offset from stack pointer                |
| 0   | −1  | FIELD               | Object base address + field index        |
| 0   | 0   | NULL                | Null / undefined reference               |
| 0   | +1  | SYMBOL              | Interned symbol (hash or table index)    |
| +1  | −1  | REMOTE              | Network node reference (P2PCP address)   |
| +1  | 0   | WEAK                | Weak reference (GC-transparent)          |
| +1  | +1  | USER-DEFINED        | Extensible — see Section 4.5             |

Models 1–8 use T19–T0 (20 trits) as the pointer payload.

---

### 4.5 USER-DEFINED POINTER (T21 = +1, T20 = +1) — The Self-Describing Object Word

The user-defined pointer is the most structurally rich word type. It encodes a
complete object descriptor — type, subclass, code reference, data reference, and
internal cursor — within a single 24-trit word.

```
T23  T22  T21  T20  T19-T18   T17–T12      T11–T6       T5–T0
 +    0    +    +    EXT       OFFSET       CODE-SEG     DATA-SEG
DATA PTR  USER  DEF  2 trits   6 trits      6 trits      6 trits
                     subclass  cursor/idx   code ref     data ref
```

**T19–T18 — Extensibility / subclass trits (9 subclass variants):**

| T19 | T18 | Subclass          |
|-----|-----|-------------------|
| −1  | −1  | Predefined A      |
| −1  | 0   | Predefined B      |
| −1  | +1  | Predefined C      |
| 0   | −1  | Predefined D      |
| 0   | 0   | Base (default)    |
| 0   | +1  | Predefined F      |
| +1  | −1  | Predefined G      |
| +1  | 0   | Predefined H      |
| +1  | +1  | Meta-extensible * |

\* The (+1,+1) subclass is always reserved for further user-defined extension,
providing an escape hatch for future needs without breaking backward compatibility.

**T17–T12 — OFFSET register (6 trits, range ±364):**

An internal cursor unique to this word instance. Points to the current position
within the object's data segment. Analogous to an instruction pointer for the
object's own data traversal. Enables sequential access, iteration, and streaming
within the object without external state.

**T11–T6 — CODE segment reference (6 trits, range ±364):**

A compact reference to the executable code associated with this object type.
Resolved at dispatch time to a full 24-trit address via a code segment base
register. This is the object's method table in a single tryte.

**T5–T0 — DATA segment reference (6 trits, range ±364):**

A compact reference to the data storage associated with this object instance.
Resolved at dispatch time via a data segment base register.

### 4.5.1 Dispatch Semantics

When the CPU encounters a USER-DEFINED POINTER word, it:

1. Reads CODE-SEG → resolves full code address via code segment base register
2. Reads DATA-SEG → resolves full data address via data segment base register
3. Reads OFFSET → sets internal cursor for data traversal
4. Dispatches to the resolved code address

Steps 1–4 require no additional memory fetches beyond the word itself. The object
is its own dispatch descriptor. This is the key architectural claim: **the word IS
the object**, not a pointer to one.

### 4.5.2 Relationship to Turing Completeness

A single USER-DEFINED POINTER word is not Turing complete — it is finite and
static. However, it is a **complete process launch descriptor**: it contains
everything needed to initiate a Turing complete computation (code address, data
address, starting cursor) with zero setup overhead beyond the word fetch.

In conventional OO architectures, initiating method dispatch requires: pointer
dereference → vtable lookup → argument setup → stack frame → branch. In this
architecture: fetch word → read three 6-trit fields → dispatch. The object model
overhead that makes dynamic OO languages slower than C is structurally absent.

This is Alan Kay's original vision for OOP — "each object is a computer" —
implemented literally at the hardware word level.

---

## 5. Word Type Summary

```
T23   Word Type    Header Region              Payload
───   ─────────    ──────────────────────     ──────────────────────────
 −    EXEC         T22=privilege              T19–T0: function address
                   T21=call-style             (20 trits)
                   T20=return-type

 0    MAP          T22=axis-YZ                T19–T0: coordinate
                   T21=axis-XZ               (20 trits)
                   T20=axis-XY

+1/−1 SCALAR       T22=−1                    T19–T0: value (21 trits)
                   T21=encoding

+1/+1 STRING       T22=+1                    T19–T0: length/addr
                   T21=encoding              (21 trits)

+1/0  POINTER      T22=0                     T19–T0: address (20 trits)
 (models 1–8)      T21,T20=model             [varies by model]

+1/0/++  USER-DEF  T22=0, T21=+, T20=+       T19–T18: subclass (2 trits)
                                             T17–T12: OFFSET (6 trits)
                                             T11–T6:  CODE-SEG (6 trits)
                                             T5–T0:   DATA-SEG (6 trits)
```

---

## 6. Design Principles

**P1 — Primary trit invariance.**  
T23 always identifies the primary type. No format extension may relocate or
reinterpret it. This ensures the fetch-decode loop has a stable entry point.

**P2 — Self-description without lookup.**  
Every word type carries sufficient metadata to initiate its operation without
additional memory cycles. No vtable, no descriptor table, no runtime type check.

**P3 — Redundant zeros as semantic anchors.**  
Zero states in qualifier trits are not wasted. They encode boundary conditions,
origin references, scale levels, and null states. This mirrors the natural
properties of balanced ternary arithmetic.

**P4 — Escape hatch preserved.**  
In every extensible category, one qualifier combination (+1,+1 or equivalent)
is always reserved for user-defined extension. Forward compatibility is
structural, not contractual.

**P5 — No SBTCVM compromise inherited.**  
The DATA/POINTER/USER-DEFINED taxonomy replaces SBTCVM's EXEC/DATA/REF tags
because the 5500FP has no opcode-in-negative-range convention. Architectural
decisions are derived from 5500FP properties, not SBTCVM limitations.

**P6 — Economics from structure, not compression.**  
MAP words encode 3D position as directional sense (3 qualifier trits) + magnitude
(20-trit payload). This is intrinsically more information-dense than enumerating
coordinates, for the same reason vector graphics outperform bitmaps: rules are
cheaper than exhaustive enumeration.

---

## 7. Relationship to 5500FP ISA

This specification operates at **Layer 2** of a three-layer stack:

```
Layer 3:  Application objects
          (polygon meshes, CGP tokens, P2PCP node addresses, FlowCode graphs)

Layer 2:  TernOO word interpreter  ← this specification
          (word format, dispatch semantics, USER-DEF pointer model)

Layer 1:  5500FP ISA               ← stable substrate
          (fetch-decode-execute, 81 registers, 120 instructions)
```

The TernOO word interpreter is implemented as a software layer running on the
5500FP. The 5500FP ISA is not modified. The TOBJ, TGET, TPAYLOAD, TCALL, and
TNEW opcodes in the emulator implement the Layer 2 dispatcher.

The 5500FP's native ternary instruction group (DECOT, DECOU, DECOF, TTT, TTU,
TTF, MIN, MAX, TXOR) provides the substrate operations that make Layer 2
efficient — trit-level decode, three-way conditional branch, and ternary logic
are available without software simulation.

---

## 8. Relationship to TernOO/SBTCVM

The SBTCVM TernOO implementation established the core insight: **the leading trit
of a ternary word is the natural location for a type tag**, and three-way dispatch
on that trit is the natural dispatch primitive.

This specification extends that insight to the 5500FP's 24-trit word, replacing
SBTCVM's constraints with a richer architecture:

| Property          | SBTCVM TernOO        | 5500FP TernOO (this spec)     |
|-------------------|----------------------|-------------------------------|
| Word width        | 9 trits              | 24 trits                      |
| Payload           | 8 trits (±3280)      | 20 trits (±1.74B) typical     |
| Type tags         | EXEC/DATA/REF        | EXEC/MAP/DATA                 |
| Tag rationale     | SBTCVM opcode space  | First principles               |
| Pointer models    | 1 (Option A)         | 9 (including user-defined)    |
| Object descriptor | Requires Option A    | Self-contained in word        |
| Extensibility     | Via Option A         | Structural (EXT trits)        |

The SBTCVM implementation is a working proof of concept. This specification is
its architectural successor, unconstrained by the substrate it was born on.

---

## 9. Open Questions

**Q1.** Should EXEC words use a 20-trit absolute address or a shorter relative
offset combined with a code segment base register (mirroring the USER-DEF pointer
model's CODE-SEG tryte)?

**Q2.** The six 6-trit segment references in USER-DEF POINTER words resolve via
base registers. How many base registers should be allocated for code and data
segments? 5500FP has 81 registers — sufficient for generous allocation.

**Q3.** MAP word payload: should the 20-trit field carry an absolute coordinate,
a relative offset from a reference point, or a mixed encoding determined by
the qualifier state (zero qualifiers → relative, non-zero → absolute)?

**Q4.** Should there be a FORMAT word (a reserved word type that redefines the
qualifier/payload boundary for subsequent words in a stream)? This would enable
domain-specific word formats for applications like audio, image data, or protocol
packets — while keeping the P1 invariant (T23 always the primary type).

**Q5.** The nine POINTER models include REMOTE (+1,−1) for P2PCP network node
references. Should this model use the same 20-trit payload, or should P2PCP
addressing get its own extended format as a MAP-type word?

---

## 10. Next Steps

1. Update `5500fp_emulator.py` to implement this word grammar:
   - Correct type constants: DATA/EXEC/MAP (replacing INTEGER/FLOAT/STRING)
   - Extend TOBJ to encode full qualifier fields
   - Implement USER-DEF POINTER word construction and dispatch
   - Add MAP word construction with octree qualifier encoding

2. Write `ternoo_word_tools.py`: helper library for constructing and
   inspecting TernOO words — equivalent to SBTCVM's Object Inspector but
   for the 5500FP word format.

3. Port the SBTCVM demo ROMs (ternoo_obj1–5, hello_ternoo) to 5500FP
   assembly using the new word grammar as a validation suite.

4. Draft a proposal to Claudio La Rosa (5500FP author) presenting the
   TernOO word grammar as a candidate ISA extension.

---

*This is a living specification. Architectural decisions made during implementation
supersede this document where they conflict. The next revision will be v0.2.*

*"The ideal object-oriented object is itself a computer."*  
*— Alan Kay, 1972 (approximately)*  
*"Each 24-trit word is a complete process launch descriptor."*  
*— Stevo, 2026*
