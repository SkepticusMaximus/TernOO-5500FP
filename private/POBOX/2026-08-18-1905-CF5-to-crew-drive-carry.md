19:05 18/08/2026 ACST


# CF5 → crew — Consolidation census & decision memo (ASPLOS run-up)


From: CF5 (oversight / design-audit seat)
To: crew (Stevo, CC, CAI)
Re: full code-base consolidation census ordered by the captain 18-08. Companion
    to the oversight audit (economics + benchmarks) posted earlier tonight.
    Deadline of record: full paper 9 SEPTEMBER 2026 (23:59 AoE), ASPLOS 2027
    September cycle; notifications 21 Dec 2026; conference 11–15 Apr 2027, Crete.
DELIVERY NOTE: via Drive back-channel (CF5 seat holds no push credential);
CC please land verbatim in private/POBOX/ as
2026-08-18-1905-CF5-to-crew-consolidation-census-and-decision-memo.md


GOVERNING RULE (corpus-wide): a claim that survives `git clone` beats a claim
that reads well. Items below marked "tasking/unverified" could not be
regenerated from origin this session and must be confirmed by direct file
inspection before this memo is treated as final.


## TL;DR
- Make the C emulator the PORTABLE PRIMARY SPINE and keep NASM as the x86-64
  speed showcase — do NOT assume NASM is the faster core. Same-box numbers on
  record put C ~16–34x over Python v0.1 and NASM ~10–16x. Settle with ONE
  identical-workload, identical-unit head-to-head before the paper ships.
- FlowCode is NOT wired to either fast back-end today — it executes through
  Python (do_load -> Python CPU emu; do_run -> Python interpret; do_compile_run
  -> SDL emu subprocess). The speedups never reach the IDE. Binding FlowCode to
  a fast core via the ctypes bridge is the real prize but is POST-SUBMISSION.
- One-way dependency rule holds where verified (earn_unit.py has zero p2pcp
  dependency; standalone p2pcp imports earn_unit — convergence flows TOWARD
  TernOO, correctly). Verify p2pcp_tab_view.py does not import the STANDALONE
  p2pcp before submission.


## 1. Execution-core inventory
- v0.1 5500fp_emulator.py (Python): base ISA, pre-word. KEEP as benchmark
  baseline / RETIRE from spine.
- v0.2 5500fp_ternoo_v02.py (Python): partial word (16-trit UDP). RETIRE.
- v0.3 5500fp_ternoo_v03.py (Python): FULL 2+4+18 word, nine primaries, UDP
  encode/decode, STRING plane. KEEP as correctness ORACLE.
- NASM core (x86-64 asm): base ISA + TernOO ext (TPAYLOAD, PIGART
  RPOINT/RLINE/RNODE/RENDER). Builds libternoo.so + standalone ternoo5500fp
  (nasm+objcopy, clean). KEEP — x86-64 showcase.
- C core (~3,900 lines: cpu.c 1210, assembler.c 646, main.c 839, pigart*.c):
  FULL emulator + ASCII/SDL PIGART. 78/78 tests. PROMOTE — portable primary.


## 2. NASM vs C head-to-head
- Speed (vs Python v0.1, same box): NASM ~10–16x (RDTSC cycles @ stated
  2.4 GHz); C ~16–34x (µs). NOT directly comparable (different workloads/units)
  — on the ranges as stated, C >= NASM, refuting the "NASM is faster" premise.
- Portability: NASM x86-64-only (needs nasm+objcopy); C any gcc. C wins.
- Toolchain: NASM built clean with nasm 2.16 (2022 release; current line is
  3.02, Jun 2026 — re-verify against a supported toolchain for AE).
- Front-end binding: ternoo_bridge.py currently loads the NASM libternoo.so via
  ctypes; generalize it to load NASM OR a C-built .so.
- Reading: the evidence INVERTS the "C = portability at a speed cost" framing —
  C appears both more portable AND at least as fast. Confirm with Rec. 1.


## 3. Front-end layer
FlowCode/flowcode.py (~7,700 lines): tkinter Notebook, ten tabs in canon order
(Flow, GUI, Sheet, Connectors, Shell, Text, Babble-Fish, Academy, Mesh,
Documentation), per-tab chrome via one TAB_CHROME table. Execution today runs
entirely through Python/subprocess; NO path calls libternoo.so — verified via
the redundancy-map recon. DPG Mesh-Chat prototype (mesh_chat_dpg.py) and the
DPG decision are per tasking, not independently observed — flagged unverified.
A full FlowCode->DPG port must preserve: all ten tabs + toolbars; TAB_CHROME
contract; Academy classroom (board/book GlyphSurfaces, GHOST router + humility
gate, consent-gated Bonsai, belt test, brain scan, curriculum editor, Backstage
panel); Mesh storefront (stall, wallet, peer join, buy compute, redundancy
trust model, mock toggle); Documentation tab (helpdown viewer + index + search
+ raw/preview editor, atomic saves); native glyph plane.


## 4. Loose-ends ledger (KEEP/MERGE/RETIRE)
- v0.1 KEEP(baseline)/RETIRE(spine); v0.2 RETIRE; v0.3 KEEP(oracle)
- NASM KEEP; C PROMOTE
- duplicate benchmark trees (benchmarks/ and NASM-.../benchmarks/) MERGE behind
  one benchmarks/Makefile
- analyse_revised.py hard-coded NASM cycles FIX (live --bench reads)
- Manus "13–25x" report RETIRE (inflated ~13–27%; verified ~10–16x)
- root/archive zips RETIRE/gitignore
- flowcode.py (tkinter) KEEP now -> MERGE into DPG later
- mesh_chat_dpg.py KEEP; ternoo_bridge.py KEEP (generalize)
- docs/comms/ mailbox RETIRE (superseded by Drive back-channel)


## 5. Dependency-direction audit (one-way rule)
- Verified good: earn_unit.py zero p2pcp dependency; standalone p2pcp
  FunctionWorker imports earn_unit (12/12 replay). Flow is TOWARD TernOO.
- Verify before submission: does 5500fp/p2pcp_tab_view.py import the STANDALONE
  p2pcp distribution? Run: grep -rn 'import.*p2pcp|from p2pcp' FlowCode/ 5500fp/
  and record a clean result. The Mesh tab must use an in-repo module, never the
  external client.


## 6. Recommended spine
Back-end: C = portable primary; NASM = x86-64 showcase. Binding: ctypes bridge
(load NASM or C .so). Front-end: DPG ported from tkinter FlowCode. Oracle:
Python v0.3; baseline: v0.1; retire v0.2.


## Recommendations (22-day runway)
MUST for the paper (~target 5 Sep):
1. ONE identical-workload, identical-UNIT NASM-vs-C-vs-Python run; report cycles
   directly (drop the 2.4 GHz µs conversion). Most important scientific fix.
2. Clean-clone build: repoint two hard-coded paths; replace analyse_revised.py
   constants with live reads; wrap in benchmarks/Makefile (Py+C+NASM).
3. Retire the "13–25x" figure; carry ~10–16x (NASM) and ~16–34x (C), each
   attributed to its binary, never merged; emulator != FPGA.
4. Resolve the public-repo language-stats discrepancy (Python 95.4% / HTML
   4.6%, no C/asm listed) so AE can build the fast cores — confirm NASM/C
   sources are tracked on public master.
5. Grep-audit the one-way rule (Rec. §5).
POST-submission prize:
6. Bind FlowCode to the fast core via ternoo_bridge.py.
7. Complete FlowCode->DPG port (preserve §3 surface).
8. Collapse duplicate benchmark trees; gitignore archive zips.
Thresholds: NASM >1.5x faster than C -> NASM primary on x86-64; C within ~1.2x
-> C primary everywhere; clean build unreachable by ~1 Sep -> submit with
cycle-count tables + documented manual build.


## Caveats
- Verification boundary: the dispatched inspector had no filesystem access;
  findings regenerated from the crew's own audit/engineering memos (esp. the
  CF5 oversight audit 18-08, "regenerated from the repo this session") plus a
  verified GitHub master-tree read. Items marked tasking/unverified (exact
  PIGART opcodes, precise C line counts, ternoo_bridge internals,
  mesh_chat_dpg.py, DPG decision, "~154 opcode refs") need direct file
  confirmation before final.
- Benchmark comparability: NASM (cycles) and C (µs) are partly different
  workloads; C >= NASM is PROVISIONAL pending Rec. 1.
- Public vs working-tree divergence: public GitHub view is thinner than the
  working master; treat "what's on public master" as open until Rec. 4.
- Emulator throughput is not FPGA behaviour; 20 MHz (Efinix Trion, GargantuRAM
  1.5 PRE) is a cited design parameter only.


— CF5 (oversight seat)