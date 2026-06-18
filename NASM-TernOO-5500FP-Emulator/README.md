# TernOO-5500FP Emulator — Directory

This directory contains three related but independent projects for the
**5500FP balanced ternary RISC architecture**, plus the hybrid Python bridge
that wires them together for Stage 7b (PIGART native rendering).

---

## Directory layout

```
NASM-TernOO-5500FP-Emulator/
├── README.md                              (this file)
├── 5500FP Architecture and ISA Specification.md
├── _SUPERSEDED_5500FP Architecture Emulator Benchmark Report.md
├── TernOO-5500FP Benchmark Report (Revised).md
├── TernOO-5500FP — Pure x86-64 NASM Emulator.md
├── TernOO-5500FP: Strategic Assessment & Gap Analysis.md
├── Final_Summary.md
│
├── c_api.c                        hybrid bridge — C wrappers over NASM symbols
├── ternoo_bridge.py               hybrid bridge — Python ctypes layer
├── Makefile                       builds bin/libternoo.so
├── bin/
│   └── libternoo.so               built by top-level Makefile
│
├── c_emulator/                    C implementation (extracted from 5500fp_emulator.zip)
│   ├── src/                       cpu.c  assembler.c  main.c
│   ├── include/                   trit.h  isa.h  cpu.h
│   ├── examples/                  bubble_sort.t5asm  gcd.t5asm
│   ├── Makefile
│   ├── README.md
│   └── 5500fp                     pre-built binary
│
├── nasm_emulator/                 NASM implementation (extracted from ternoo_nasm.zip
│   ├── src/                       + Manus loose .asm additions)
│   │   ├── trit.asm               ternary math primitives
│   │   ├── cpu.asm                5500FP CPU core
│   │   ├── word.asm               word / string utilities
│   │   ├── main.asm               entry point + I/O
│   │   ├── assembler.asm          NASM macro-assembler (Manus)
│   │   ├── gristmill.asm          graph-walk / OTree (Manus)
│   │   └── interp.asm             FlowCode interpreter (Manus; line 344 bug—deferred)
│   ├── include/
│   │   └── ternoo.inc
│   ├── Makefile
│   ├── README.md
│   └── ternoo5500fp               pre-built binary (48 KB)
│
├── benchmarks/
│   ├── reports/                   5500FP_Revised_Benchmark_Report.md
│   ├── charts/                    *.png
│   ├── data/                      benchmark_results_all.csv
│   ├── c_emu_bench.c
│   ├── native_bench.c
│   ├── python_bench.py
│   ├── ternoo_semantic_bench.py
│   ├── analyse.py                 NOTE: hardcoded /home/ubuntu/benchmarks — fix paths before use
│   └── analyse_revised.py         NOTE: same path issue
│
└── _archive/                      original zips preserved for posterity
    ├── 5500fp_emulator.zip
    ├── ternoo_nasm.zip
    ├── 5500fp_benchmarks.zip
    └── 5500fp_revised_benchmarks.zip
```

---

## Building

### C emulator (standalone binary)

```bash
cd c_emulator
make
./5500fp --test     # 36 tests
./5500fp --demo     # Hello World / Fibonacci / Ternary / Factorial / Array Sum
```

### NASM emulator (standalone binary)

```bash
cd nasm_emulator
make
./ternoo5500fp --test
```

### Hybrid bridge shared library

Requires NASM and GCC on the host:

```bash
# From the directory root:
make                          # builds bin/libternoo.so
python3 ternoo_bridge.py      # prints R42 = 12345 + "Bridge is fully operational."
```

The top-level Makefile links `trit.asm` + `cpu.asm` (via NASM) with `c_api.c`
(via GCC -fPIC) into `bin/libternoo.so`. Both .asm files use RIP-relative
addressing throughout, so they are PIC-compatible without special NASM flags.

---

## Hybrid bridge architecture

```
Python (ternoo_bridge.py)
    |  ctypes
C wrappers (c_api.c)  -- ternoo_init / ternoo_read_reg / ternoo_write_reg ...
    |  extern declarations
NASM CPU core (cpu.asm) -- cpu_init / cpu_read_reg / cpu_write_reg ...
    |  calls
NASM math primitives (trit.asm) -- clamp_word / to_bet / from_bet ...
```

c_api.c forward-declares NASM symbols (not C emulator symbols — the two
implementations are independent and have different calling conventions).

---

## Known issues (deferred to Stage 7b)

- interp.asm line 344: Manus NASM port bug. Currently dead code (no Makefile
  target links it). Stage 7b will decide whether to fix or replace.
- analyse.py / analyse_revised.py: hardcoded /home/ubuntu/benchmarks
  paths. Fix paths locally before rerunning benchmark analysis.

---

## Background

The **5500FP** is a 24-trit balanced ternary RISC processor designed by
Claudio Lorenzo La Rosa and implemented on an FPGA. Unlike conventional binary
processors, the 5500FP uses trits (-1, 0, +1) for a natively balanced ternary
representation.

- Word width: 24 trits (range +/-141,414,794,240)
- Registers: 81 general-purpose (R0-R80; R0 hardwired to zero)
- Encoding: each trit packed into 2 bits (00=0, 01=+1, 11=-1);
  24-trit word fits in 48 bits of a uint64_t

References:
- La Rosa, Claudio Lorenzo. "5500FP: A 24-Trit Balanced Ternary RISC Processor".
  Zenodo, 2026. https://zenodo.org/records/18881738
- "Ternary RISC Processor Achieves Non-Binary Computing Via FPGA". Hackaday,
  Mar 16, 2026. https://hackaday.com/2026/03/16/ternary-risc-processor-achieves-non-binary-computing-via-fpga/
