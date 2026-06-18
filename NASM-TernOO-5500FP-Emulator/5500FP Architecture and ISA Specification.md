# 5500FP Architecture and ISA Specification

## Overview
The 5500FP is a 24-trit balanced ternary RISC processor.
- **Trit values:** -1 (T), 0, +1 (1)
- **Data Sizes:**
  - Tryte = 6 trits (min: -364, max: 364)
  - Short = 12 trits
  - Word = 24 trits (min: -141,414,794,240, max: 141,414,794,240)
- **Registers:** 81 general-purpose registers (R0 to R80). R0 is hardwired to 0.
- **Addressing:** 22-trit address bus (31G tryte addressable memory).
- **Encoding:** Binary-encoded ternary. We will use 2 bits per trit (00 = 0, 01 = +1, 11 = -1, 10 = unused).

## Instruction Formats
Instructions are 24 trits long. We encode them in memory using binary.
Since 3^24 = 282,429,536,481, which fits in a 64-bit integer, we can use 64-bit integers for the emulator's internal word representation, or a byte array for memory.

### RISC Formats
- **R-Type (Register-Register):**
  - Opcode: 6 trits
  - Rd: 4 trits (destination)
  - Rs1: 4 trits (source 1)
  - Rs2: 4 trits (source 2)
  - Func/Padding: 6 trits
- **I-Type (Immediate):**
  - Opcode: 6 trits
  - Rd: 4 trits
  - Rs1: 4 trits
  - Immediate: 10 trits (signed balanced ternary)
- **J-Type (Jump):**
  - Opcode: 6 trits
  - Immediate: 18 trits

## Instruction Set (Subset of 120 instructions)
### ALU Operations
- `ADD Rd, Rs1, Rs2`: Rd = Rs1 + Rs2
- `SUB Rd, Rs1, Rs2`: Rd = Rs1 - Rs2
- `MUL Rd, Rs1, Rs2`: Rd = Rs1 * Rs2
- `DIV Rd, Rs1, Rs2`: Rd = Rs1 / Rs2
- `MIN Rd, Rs1, Rs2`: Rd = min(Rs1, Rs2)
- `MAX Rd, Rs1, Rs2`: Rd = max(Rs1, Rs2)
- `INV Rd, Rs1`: Rd = -Rs1 (ternary inversion)

### Memory Operations
- `LDW Rd, Rs1, imm`: Load Word (24-trit) from mem[Rs1 + imm]
- `STW Rs2, Rs1, imm`: Store Word to mem[Rs1 + imm]

### Control Flow
- `JMP imm`: Jump to PC + imm
- `BEQ Rs1, Rs2, imm`: Branch to PC + imm if Rs1 == Rs2
- `BGT Rs1, Rs2, imm`: Branch to PC + imm if Rs1 > Rs2
- `BLT Rs1, Rs2, imm`: Branch to PC + imm if Rs1 < Rs2

## Binary Encoding of Trits
For the x86 emulator, we use a 2-bit per trit representation to allow fast bitwise operations.
- `00` -> 0
- `01` -> +1
- `11` -> -1
- `10` -> Invalid/Unused

A 24-trit word takes 48 bits, which easily fits in a standard 64-bit unsigned integer (`uint64_t`).

## Conversion Formulas
- Ternary to Binary (Int64): `val = sum(trit[i] * 3^i)`
- Int64 to Ternary: repeated division by 3, with remainder adjustment for balanced ternary.

We will write the emulator in C with inline x86 assembly for the core execution loop and ALU operations to maximize performance.
