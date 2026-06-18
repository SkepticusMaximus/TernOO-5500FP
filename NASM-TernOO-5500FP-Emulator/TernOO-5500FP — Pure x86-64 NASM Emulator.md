# TernOO-5500FP — Pure x86-64 NASM Emulator

A complete, bare-metal x86-64 NASM assembly port of the **TernOO-5500FP** balanced
ternary computer architecture. No C, no compiler, no runtime library — only NASM
assembly and Linux system calls.

---

## Architecture Overview

The emulator implements the full three-layer TernOO-5500FP stack in hand-written
x86-64 assembly:

| Layer | Module | Description |
|---|---|---|
| **Trit primitives** | `src/trit.asm` | Binary-encoded ternary (BET) encoding, field extract/insert, trit-wise ALU |
| **5500FP ISA** | `src/cpu.asm` | 81 registers, 24-trit words, 37 opcodes, fetch/execute loop, stack, heap |
| **TernOO word format** | `src/word.asm` | 2+4+18 trit word layout, 9 primary types, word constructors and descriptors |
| **Entry / tests / bench** | `src/main.asm` | `_start`, test suite, benchmark harness, demo programs |

### Binary-Encoded Ternary (BET)

Each trit is stored as **2 bits** in a 64-bit integer:

| Trit value | BET bits |
|---|---|
| 0 | `00` |
| +1 | `01` |
| −1 | `10` |

A 24-trit word occupies 48 bits and fits entirely in a single `rax` register.
The encoding is dense, branch-free, and maps directly onto x86 bitwise operations.

### 5500FP Instruction Format

```
  T23..T20   T19..T16   T15..T12   T11..T8    T7..T4     T3..T0
  ┌────────┬──────────┬──────────┬──────────┬──────────┬────────┐
  │ opcode │  F4/imm  │  F3/imm  │  F2/imm  │   Rs1    │   Rd   │
  └────────┴──────────┴──────────┴──────────┴──────────┴────────┘
  Field 5    Field 4    Field 3    Field 2    Field 1    Field 0
  (4 trits)  (4 trits)  (4 trits)  (4 trits)  (4 trits)  (4 trits)
```

- **Format A** (register): `[Rd][Rs1][Rs2][Rs3][Rs4][op]`
- **Format J2** (register + immediate): `[Rd][Rs1][imm:12t][op]`
- **Format J** (jump): `[imm:20t][op]`

Registers are encoded as `field_value + 40` (balanced ternary offset), giving
81 registers (R0–R80) with R0 hardwired to zero.

### TernOO Word Format

```
  T23..T22   T21..T18   T17..T0
  ┌─────────┬──────────┬────────────────────┐
  │ primary │ qualifier│      payload        │
  │ (2 trit)│ (4 trit) │    (18 trits)       │
  └─────────┴──────────┴────────────────────┘
```

Nine primary types (encoded in 2 trits, balanced ternary −1..+1 × −1..+1):

| Primary | Value | Meaning |
|---|---|---|
| `EXEC` | −4 | Executable word: privilege, call style, return type, segment, offset |
| `MAP` | −3 | Structural map: type, qualifier, address/length |
| `DATA` | 0 | Data word: scalar, pointer, null |
| `NEURAL` | +1 | Neural unit or connection weight |
| `IO` | +2 | I/O descriptor |
| `CRYPTO` | +3 | Cryptographic primitive |
| `OPCODE` | +4 | Inline opcode word |
| `OPEN_B` | −1 | Open/bracket structural word |
| `POOL` | −2 | Memory pool descriptor |

---

## Building

```bash
# Prerequisites: nasm, ld (binutils)
sudo apt-get install nasm binutils

cd ternoo_nasm
make
```

The build produces a single statically-linked ELF64 binary: `./ternoo5500fp`.

---

## Usage

```bash
./ternoo5500fp [--test] [--bench] [--demo]
```

With no arguments, all three modes run in sequence.

### `--test` — Self-test suite

Runs 33 unit tests covering every layer:

```
=== Self-Test Suite ===
  [PASS] to_bet(+1, 1) = 01b
  [PASS] from_bet(01b, 1) = +1
  ...
  [PASS] cpu Fibonacci(10)=55
  [PASS] cpu Factorial(5)=120
Tests: 33 / 33 passed
```

### `--bench` — RDTSC benchmark

Measures raw x86 CPU cycles for four workloads:

```
=== Benchmark ===
  Fibonacci(25)     : 1,036,890 cycles (RDTSC)
  Factorial(10)     :   262,504 cycles (RDTSC)
  Arith loop (3000) : 61,420,544 cycles (RDTSC)
  TernOO word build : 126,008,902 cycles (RDTSC)
```

### `--demo` — Demo programs

```
-- Fibonacci(15) --
  fib(15) = 987
  PC=10  cycles=188

-- Factorial(8) --
  fact(8) = 40320

-- TernOO Word Dispatch Demo --
  Built word: EXEC  payload=...
  Built word: DATA  payload=...
  Built word: MAP   payload=...
  TernOO word dispatch: OK

-- PIGART Canvas Demo --
╔══ CANVAS ══
  POINT @100
  LINE  200 --> 300
╚═══
```

---

## Instruction Set Reference

### Arithmetic

| Mnemonic | Format | Operation |
|---|---|---|
| `ADD Rd, Rs1, Rs2` | A | `Rd = clamp(Rs1 + Rs2)` |
| `ADDI Rd, Rs1, imm` | J2 | `Rd = clamp(Rs1 + imm)` |
| `SUB Rd, Rs1, Rs2` | A | `Rd = clamp(Rs1 - Rs2)` |
| `SUBI Rd, Rs1, imm` | J2 | `Rd = clamp(Rs1 - imm)` |
| `MUL Rd, Rs1, Rs2` | A | `Rd = clamp(Rs1 × Rs2)` |
| `DIV Rd, Rs1, Rs2` | A | `Rd = Rs1 ÷ Rs2` (Rs2≠0) |
| `NEG Rd, Rs1` | A | `Rd = -Rs1` |

### Logic (trit-wise)

| Mnemonic | Operation |
|---|---|
| `MIN Rd, Rs1, Rs2` | Per-trit minimum |
| `MAX Rd, Rs1, Rs2` | Per-trit maximum |
| `TXOR Rd, Rs1, Rs2` | Ternary XOR (cyclic sum mod 3) |
| `EQ Rd, Rs1, Rs2` | Per-trit equality (+1 if equal, −1 if not) |
| `TSUM Rd, Rs1, Rs2` | Saturating trit sum |

### Data movement

| Mnemonic | Operation |
|---|---|
| `LDI Rd, imm` | Load 12-trit immediate |
| `MOV Rd, Rs1` | Register copy |
| `LD Rd, Rs1` | Load from memory[Rs1] |
| `ST Rd, Rs2` | Store Rd to memory[Rs2] |
| `PUSH Rd` | Push to stack |
| `POP Rd` | Pop from stack |

### Control flow

| Mnemonic | Operation |
|---|---|
| `JMP addr` | Unconditional jump |
| `JSR addr` | Jump to subroutine (push return addr) |
| `RTI` | Return from subroutine |
| `JEQ Rd, Rs1, offset` | Jump if Rd == Rs1 (relative) |
| `JNE Rd, Rs1, offset` | Jump if Rd ≠ Rs1 (relative) |
| `JB Rd, Rs1, offset` | Jump if Rd < Rs1 (relative) |
| `HLT` | Halt |

### TernOO object model

| Mnemonic | Operation |
|---|---|
| `TOBJ Rd, Rs1, Rs2` | Create object at heap addr Rs1 with type Rs2 |
| `TGET Rd, Rs1` | Get object type from handle Rs1 |
| `TCALL Rd, Rs1, Rs2` | Call method Rs2 on object Rs1 |
| `TNEW Rd, Rs1` | Allocate new object of type Rs1 |
| `TSEG Rd, Rs1, Rs2` | Segment operation |

### PIGART rendering

| Mnemonic | Operation |
|---|---|
| `RPOINT Rd, pos, colour` | Record canvas point |
| `RLINE Rd, src, end, colour` | Record canvas line |
| `RNODE Rd, pos, dims, shape, obj` | Record canvas node |
| `REDGE Rd, src, dst, style` | Record canvas edge |
| `RENDER` | Flush canvas to output |

---

## Project Structure

```
ternoo_nasm/
├── Makefile
├── README.md
├── include/
│   └── ternoo.inc          # Shared constants, macros, struct offsets
└── src/
    ├── trit.asm             # BET primitives
    ├── cpu.asm              # 5500FP ISA core
    ├── word.asm             # TernOO word format layer
    └── main.asm             # Entry point, tests, benchmarks, demos
```

---

## Relationship to Python Reference Implementation

This NASM port is a faithful translation of the Python reference implementation
at [github.com/SkepticusMaximus/TernOO-5500FP](https://github.com/SkepticusMaximus/TernOO-5500FP).
The Python emulator (`5500fp_ternoo_v03.py`) served as the ground truth for all
opcode semantics, word format constants, and object model behaviour.

The key architectural decisions that differ from the Python version:

1. **No Python overhead**: every trit operation is a direct x86 bitwise instruction.
2. **Register-resident words**: a 24-trit word fits in a single 64-bit register.
3. **Flat memory model**: the 81-register file and memory array are contiguous
   heap allocations, accessed via pointer arithmetic with no dictionary lookups.
4. **Inline field decode**: `get_field_val` / `set_field_val` are tight loops of
   `shr`, `and`, and `imul` — no Python list comprehensions.

---

## Benchmark Context

The RDTSC cycle counts above are for the **emulated ternary ISA running on x86**.
Each emulated instruction requires approximately 40–80 x86 instructions (field
decode, dispatch, register read/write, clamp). The TernOO word-build benchmark
includes three `word_build_*` calls per iteration, each performing a full
primary/qualifier/payload encode.

For comparison against the Python reference implementation, see the separate
benchmark report in `../benchmarks/5500FP_Benchmark_Report.md`.

---

## Licence

This implementation is released under the MIT Licence.
The TernOO-5500FP architecture is the work of the contributors to
[github.com/SkepticusMaximus/TernOO-5500FP](https://github.com/SkepticusMaximus/TernOO-5500FP).
