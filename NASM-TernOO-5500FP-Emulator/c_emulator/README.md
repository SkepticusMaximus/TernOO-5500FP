# 5500FP Balanced Ternary RISC Emulator

This project provides a fully functional software emulator and assembler for the **5500FP** balanced ternary RISC architecture, implemented in C with x86-64 inline assembly for core execution paths.

## Background

The **5500FP** is a 24-trit balanced ternary RISC processor designed by Claudio Lorenzo La Rosa and implemented on an FPGA [1]. Unlike conventional binary processors that use bits (0, 1), the 5500FP uses trits (-1, 0, +1), enabling a natively balanced ternary representation. This architecture is designed for research into non-binary computing, symbolic AI, multi-valued logic, and alternative cryptographic primitives [2]. 

This emulator faithfully models the publicly known specifications of the 5500FP:
- **Native Word Width**: 24 trits (min: -141,414,794,240, max: +141,414,794,240)
- **Registers**: 81 general-purpose registers (`R0` to `R80`), with `R0` hardwired to zero
- **Memory**: Addressable in 24-trit words
- **Instruction Set**: A RISC ISA with native balanced ternary ALU operations (addition, subtraction, multiplication, division, consensus, tritwise logic, and shifts)

## Implementation Details

To execute ternary logic on conventional x86 hardware, the emulator uses a **binary-encoded ternary** representation. Each trit is encoded into 2 bits:
- `00` represents **0**
- `01` represents **+1**
- `11` represents **-1**

A 24-trit word is packed into 48 bits, perfectly fitting inside a standard 64-bit unsigned integer (`uint64_t`).

For performance, the core ALU operations (such as balanced ternary addition) are implemented using **x86-64 inline assembly**. The inner execution loop leverages x86 variable-count shift instructions (`shrq %cl`) and integer arithmetic to decode, sum, propagate balanced ternary carry, and encode the results trit-by-trit, avoiding the overhead of C compiler abstraction layers.

## Features

- **Ternary Macro-Assembler**: Compiles 5500FP assembly code into executable ternary machine words. Supports labels, decimal immediates, and ternary literals (e.g., `t1T0`).
- **Interactive Debugger**: A built-in shell to write assembly line-by-line, execute it, disassemble memory, and inspect the 81 registers.
- **Self-Test Suite**: Includes 36 automated unit tests validating trit encoding, int64 round-tripping, ALU correctness, and control flow.
- **Example Programs**: Includes implementations of Fibonacci sequence generation, Bubble Sort, Euclidean GCD algorithm, and ternary arithmetic showcases.

## Building the Emulator

The project requires GCC and targets x86-64 Linux systems.

```bash
cd 5500fp_emulator
make
```

## Usage

The emulator provides several run modes:

```bash
# Run the built-in self-test suite
./5500fp --test

# Run the included demo programs (Hello World, Fibonacci, Factorial, etc.)
./5500fp --demo

# Run a specific assembly file
./5500fp --run examples/bubble_sort.t5asm

# Start the interactive assembler and debugger shell
./5500fp --interactive
```

## Instruction Set Architecture (Subset)

The emulator implements a robust subset of the 120-instruction 5500FP ISA [1].

### ALU Operations
- `ADD Rd, Rs1, Rs2`: Ternary addition
- `SUB Rd, Rs1, Rs2`: Ternary subtraction
- `MUL Rd, Rs1, Rs2`: Ternary multiplication
- `DIV Rd, Rs1, Rs2`: Ternary division
- `MIN Rd, Rs1, Rs2`: Minimum of two values
- `MAX Rd, Rs1, Rs2`: Maximum of two values
- `AND Rd, Rs1, Rs2`: Tritwise minimum
- `OR  Rd, Rs1, Rs2`: Tritwise maximum
- `CON Rd, Rs1, Rs2`: Consensus logic
- `INV Rd, Rs1`: Tritwise inversion (arithmetic negation)
- `SHL Rd, Rs1, Rs2`: Shift left (multiply by 3)
- `SHR Rd, Rs1, Rs2`: Shift right (divide by 3)

### Control Flow
- `JMP imm`: Unconditional jump
- `BEQ Rs1, Rs2, imm`: Branch if equal
- `BGT Rs1, Rs2, imm`: Branch if greater than
- `CALL imm`: Call subroutine (saves PC to `R80`)
- `RET`: Return from subroutine (jumps to `R80`)

### Memory
- `LDW Rd, Rs1, imm`: Load word from memory
- `STW Rs2, Rs1, imm`: Store word to memory

## References

[1] La Rosa, Claudio Lorenzo. "5500FP: A 24-Trit Balanced Ternary RISC Processor". Zenodo, 2026. https://zenodo.org/records/18881738
[2] "Ternary RISC Processor Achieves Non-Binary Computing Via FPGA". Hackaday, Mar 16, 2026. https://hackaday.com/2026/03/16/ternary-risc-processor-achieves-non-binary-computing-via-fpga/
