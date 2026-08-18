21:47 18/08/2026 ACST
From: CC (engineering desk)
To: Stevo, CAI, CF5
Re: Consolidation steps 1-2 landed tonight. One verdict, one first, one
    finding that needs a ruling.

## THE SPINE VERDICT (step 1, complete)
The identical-workload identical-unit head-to-head ran tonight: same box,
the four canonical programs aligned instruction-for-instruction across
ALL THREE emulators, results machine-verified in every leg, host RDTSC
measured around cpu_run alone — no GHz conversion anywhere (Rec 1 as
specified).
  workload         C emu        NASM emu     C advantage
  fib(30)          135,882      1,329,592       9.8x
  fact(12)          29,169        403,656      13.8x
  array-sum      3,602,010     31,253,877       8.7x
  arith-3000    13,080,360    123,952,251       9.5x
The census's provisional "C >= NASM" is now measured fact — inverted by
an order of magnitude. Threshold rule applied: C IS THE PORTABLE PRIMARY
SPINE; NASM stands as the x86-64 showcase. Also regenerated: C over
Python v0.1 = 44-71x on aligned workloads (the old 16-34x was
cousin-workload arithmetic), and the old C arith figure came from a
SILENTLY MIS-ASSEMBLED program (immediate parsed as register R-1) — the
verify-or-it-didn't-happen razor is now built into every bench leg.

## THE BRIDGE IS LIVE (step 2, complete)
ternoo_bridge.py now drives BOTH native cores through one seven-symbol
ABI: backend="c" (new c_emulator/libternoo_c.so) or backend="nasm"
(bin/libternoo.so). Self-test green: C runs all four canonical programs
via its exported assembler; the NASM .so executed a native-dialect probe
including R45 — proving the 81-register file through the library FOR THE
FIRST TIME. Bundle-14's veneer had never actually run a program: its
cpu_run cap was caller garbage (one-arg declaration on a two-arg core)
and its only memory port CLAMPS instruction words. Both fixed
(max_cycles=0 -> core default; new ternoo_load_word instruction port).

## THE FINDING — canonical-encoding ruling needed (captain + CF5)
The first cross-core check exposed it: ONE architecture, TWO instruction
dialects. Both cores store positional integer words, but:
  - NASM: 4-trit opcode at trit 20 (the audit-canon 2+4+18 shape),
    registers biased -40 = the full canon 81 (R0..R80).
  - C:    6-trit opcode at trit 18, its own opcode numbers, UNBIASED
    4-trit registers — only R0..R40 reachable.
The crowned speed spine deviates from the ratified word format and
cannot address half the register file. Words do not interchange, so
cross-core redundancy audits are blocked.
RECOMMENDATION: migrate the C core's encoder/decoder to the audit-canon
layout (field remap + opcode renumber in assembler.c/cpu.c; the speed
verdict is unaffected — layout does not change the execution loop's
nature). Then word interchange and two-core cross-auditing go live, and
R41+ opens up. CF5: please check the canon claim against the Language
Audit. Captain: yours to rule; engineering executes either way.

## Backup stages (per captain's order)
Tags on origin: consolidation-step1-spine-verdict,
consolidation-step2-bridge-two-cores. Every stage rolls back clean.

Next per the approved sequence: step 3, the FlowCode -> Dear PyGui port,
which can proceed in parallel with the encoding ruling.

— CC (engineering desk)
