#!/usr/bin/env python3
"""
python_bench.py — Python benchmark harness for three targets:
  1. pure_python      — plain Python, no emulation
  2. py_5500fp_emu    — 5500fp_emulator.py (Stevo's Python 5500FP emulator)
  3. py_ternoo_v03    — 5500fp_ternoo_v03.py (TernOO word-architecture emulator)

Instruction semantics (from actual source):
  JMP  addr     -> self.pc = addr              (absolute)
  JEQ  Rd,Rs,imm-> if Rd==Rs: self.pc += imm  (PC-relative, PC already past instr)
  JNE  Rd,Rs,imm-> if Rd!=Rs: self.pc += imm
  JB   Rd,Rs,imm-> if Rd<Rs:  self.pc += imm

All programs verified by smoke tests before timing.
"""

import sys, os, time, csv, importlib.util, unittest.mock

# ── Locate emulator modules ───────────────────────────────────────────────────

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'TernOO-5500FP', '5500fp')

def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)
    with unittest.mock.patch.object(mod, '__name__', name):
        spec.loader.exec_module(mod)
    return mod

emu_v01 = _load_module('emu_v01', os.path.join(REPO, '5500fp_emulator.py'))
emu_v03 = _load_module('emu_v03', os.path.join(REPO, '5500fp_ternoo_v03.py'))

REPEAT_PY_PURE = 1000
REPEAT_PY      = 5

def elapsed(fn, repeat):
    t0 = time.perf_counter()
    result = None
    for _ in range(repeat):
        result = fn()
    return time.perf_counter() - t0, result

# ─────────────────────────────────────────────────────────────────────────────
# TARGET 1: Pure Python
# ─────────────────────────────────────────────────────────────────────────────

def pure_fib30():
    # fib(30) = 832040  (0-indexed: fib(0)=0, fib(1)=1, ..., fib(30)=832040)
    a, b = 0, 1
    for _ in range(30):
        a, b = b, a + b
    return a   # 832040

def pure_fact12():
    r = 1
    for i in range(2, 13):
        r *= i
    return r   # 479001600

def pure_array_sum_1000():
    return sum(range(1, 1001))   # 500500

def pure_arith_loop_3000():
    # Fibonacci-style bounded loop: c=a+b; a=b; b=c-a (=old b)
    # This keeps values at 1 and 2 forever.
    a, b, c = 1, 2, 0
    for _ in range(3000):
        c = a + b
        a = b
        b = c - a   # = old b
    return c

# ─────────────────────────────────────────────────────────────────────────────
# Shared program builders (same ISA, same Asm API for both v01 and v03)
# ─────────────────────────────────────────────────────────────────────────────

def build_fib30(cpu_cls, asm_cls):
    """
    Iterative fib(30)=832040. Uses 29 loop iterations.
    Start: R10=0, R11=1. After 29 steps: R10=fib(29)=514229, R11=fib(30)=832040.
    Result in R11.

    addr 0: LDI R10, 0
    addr 1: LDI R11, 1
    addr 2: LDI R12, 29      # 29 iterations -> R11=fib(30)
    addr 3: JEQ R12,R0, +5   # PC after fetch=4, +5=9 -> HLT
    addr 4: ADD R13,R10,R11
    addr 5: MOV R10, R11
    addr 6: MOV R11, R13
    addr 7: SUBI R12,R12,1
    addr 8: JMP 3
    addr 9: HLT
    """
    cpu = cpu_cls()
    a = asm_cls(cpu)
    prog = [
        a.LDI(10, 0),
        a.LDI(11, 1),
        a.LDI(12, 29),
        a.JEQ(12, 0, 5),    # PC after fetch=4, +5=9
        a.ADD(13, 10, 11),
        a.MOV(10, 11),
        a.MOV(11, 13),
        a.SUBI(12, 12, 1),
        a.JMP(3),
        a.HLT(),
    ]
    cpu.load_program(prog)
    cpu.run()
    return cpu.read_reg(11)   # 832040

def build_fact12(cpu_cls, asm_cls):
    """
    Iterative factorial(12)=479001600. Result in R11.

    addr 0: LDI R10, 12
    addr 1: LDI R11, 1
    addr 2: JEQ R10,R0, +3   # PC after fetch=3, +3=6 -> HLT
    addr 3: MUL R11,R11,R10
    addr 4: SUBI R10,R10,1
    addr 5: JMP 2
    addr 6: HLT
    """
    cpu = cpu_cls()
    a = asm_cls(cpu)
    prog = [
        a.LDI(10, 12),
        a.LDI(11, 1),
        a.JEQ(10, 0, 3),
        a.MUL(11, 11, 10),
        a.SUBI(10, 10, 1),
        a.JMP(2),
        a.HLT(),
    ]
    cpu.load_program(prog)
    cpu.run()
    return cpu.read_reg(11)   # 479001600

def build_array_sum_1000(cpu_cls, asm_cls):
    """
    Sum integers 1..1000 directly (no memory store needed).
    Use a counting loop: sum += i, i++, until i > 1000.
    Result in R3 = 500500.

    addr 0: LDI R3, 0        # sum = 0
    addr 1: LDI R4, 1        # i = 1
    addr 2: LDI R5, 1001     # limit = 1001
    addr 3: JEQ R4,R5, +3    # PC(4)+3=7 -> HLT
    addr 4: ADD R3, R3, R4   # sum += i
    addr 5: ADDI R4, R4, 1   # i++
    addr 6: JMP 3
    addr 7: HLT
    """
    cpu = cpu_cls()
    a = asm_cls(cpu)
    prog = [
        a.LDI(3, 0),
        a.LDI(4, 1),
        a.LDI(5, 1001),
        a.JEQ(4, 5, 3),
        a.ADD(3, 3, 4),
        a.ADDI(4, 4, 1),
        a.JMP(3),
        a.HLT(),
    ]
    cpu.load_program(prog)
    cpu.run()
    return cpu.read_reg(3)   # 500500

def build_arith_loop_3000(cpu_cls, asm_cls):
    """
    Arithmetic loop 3000 iterations: Fibonacci-style bounded ADD+SUB loop.
    3000 fits in v01's 8-trit immediate range (max 3280).
    c = a+b; a = b; b = c-a (keeps values at 1 and 2 forever).
    Result in R12.

    addr 0: LDI R10, 1
    addr 1: LDI R11, 2
    addr 2: LDI R12, 0
    addr 3: LDI R13, 3000
    addr 4: JEQ R13,R0, +5   # PC after fetch=5, +5=10 -> HLT
    addr 5: ADD R12,R10,R11  # c = a+b
    addr 6: MOV R10, R11     # a = b
    addr 7: SUB R11,R12,R10  # b = c-a (= old b)
    addr 8: SUBI R13,R13,1
    addr 9: JMP 4
    addr10: HLT
    """
    cpu = cpu_cls()
    a = asm_cls(cpu)
    prog = [
        a.LDI(10, 1),
        a.LDI(11, 2),
        a.LDI(12, 0),
        a.LDI(13, 3000),
        a.JEQ(13, 0, 5),    # PC after fetch=5, +5=10 -> HLT
        a.ADD(12, 10, 11),
        a.MOV(10, 11),
        a.SUB(11, 12, 10),
        a.SUBI(13, 13, 1),
        a.JMP(4),
        a.HLT(),
    ]
    cpu.load_program(prog)
    cpu.run()
    return cpu.read_reg(12)

# ─────────────────────────────────────────────────────────────────────────────
# Emulator wrappers
# ─────────────────────────────────────────────────────────────────────────────

def v01_fib30():           return build_fib30(emu_v01.CPU5500FP,         emu_v01.Asm)
def v01_fact12():          return build_fact12(emu_v01.CPU5500FP,        emu_v01.Asm)
def v01_array_sum_1000():  return build_array_sum_1000(emu_v01.CPU5500FP,emu_v01.Asm)
def v01_arith_loop_3000(): return build_arith_loop_3000(emu_v01.CPU5500FP,emu_v01.Asm)

def v03_fib30():           return build_fib30(emu_v03.CPU5500FP,         emu_v03.Asm)
def v03_fact12():          return build_fact12(emu_v03.CPU5500FP,        emu_v03.Asm)
def v03_array_sum_1000():  return build_array_sum_1000(emu_v03.CPU5500FP,emu_v03.Asm)
def v03_arith_loop_3000(): return build_arith_loop_3000(emu_v03.CPU5500FP,emu_v03.Asm)

# ─────────────────────────────────────────────────────────────────────────────
# Smoke test
# ─────────────────────────────────────────────────────────────────────────────

def smoke_test():
    print("Smoke testing...", file=sys.stderr)
    arith_ref = pure_arith_loop_3000()
    checks = [
        ('pure_fib30',           pure_fib30,           832040),
        ('pure_fact12',          pure_fact12,           479001600),
        ('pure_array_sum_1000',  pure_array_sum_1000,   500500),
        ('pure_arith_loop_3000', pure_arith_loop_3000,  arith_ref),
        ('v01_fib30',            v01_fib30,             832040),
        ('v01_fact12',           v01_fact12,            479001600),
        ('v01_array_sum_1000',   v01_array_sum_1000,    500500),
        ('v01_arith_loop_3000',  v01_arith_loop_3000,   arith_ref),
        ('v03_fib30',            v03_fib30,             832040),
        ('v03_fact12',           v03_fact12,            479001600),
        ('v03_array_sum_1000',   v03_array_sum_1000,    500500),
        ('v03_arith_loop_3000',  v03_arith_loop_3000,   arith_ref),
    ]
    all_ok = True
    for name, fn, expected in checks:
        try:
            got = fn()
            ok = got == expected
            status = "OK" if ok else f"FAIL (got {got}, expected {expected})"
            if not ok: all_ok = False
        except Exception as e:
            status = f"ERROR: {e}"
            all_ok = False
        print(f"  {name}: {status}", file=sys.stderr)
    if not all_ok:
        print("Smoke test FAILED — aborting.", file=sys.stderr)
        sys.exit(1)
    print("All smoke tests passed.", file=sys.stderr)

# ─────────────────────────────────────────────────────────────────────────────
# Runner
# ─────────────────────────────────────────────────────────────────────────────

BENCHMARKS = [
    ('pure_python',   'fibonacci_30',       pure_fib30,             REPEAT_PY_PURE),
    ('pure_python',   'factorial_12',       pure_fact12,            REPEAT_PY_PURE),
    ('pure_python',   'array_sum_1000',     pure_array_sum_1000,    REPEAT_PY_PURE),
    ('pure_python',   'arith_loop_3000',    pure_arith_loop_3000,   REPEAT_PY_PURE),

    ('py_5500fp_emu', 'fibonacci_30',       v01_fib30,              REPEAT_PY),
    ('py_5500fp_emu', 'factorial_12',       v01_fact12,             REPEAT_PY),
    ('py_5500fp_emu', 'array_sum_1000',     v01_array_sum_1000,     REPEAT_PY),
    ('py_5500fp_emu', 'arith_loop_3000',    v01_arith_loop_3000,    REPEAT_PY),

    ('py_ternoo_v03', 'fibonacci_30',       v03_fib30,              REPEAT_PY),
    ('py_ternoo_v03', 'factorial_12',       v03_fact12,             REPEAT_PY),
    ('py_ternoo_v03', 'array_sum_1000',     v03_array_sum_1000,     REPEAT_PY),
    ('py_ternoo_v03', 'arith_loop_3000',    v03_arith_loop_3000,    REPEAT_PY),
]

def main():
    smoke_test()
    writer = csv.writer(sys.stdout)
    writer.writerow(['target','workload','iterations','total_sec','avg_us','result','emu_cycles'])
    for target, workload, fn, repeat in BENCHMARKS:
        sys.stderr.write(f"  Timing {target}/{workload} x{repeat}...\n")
        sys.stderr.flush()
        total, result = elapsed(fn, repeat)
        avg_us = total / repeat * 1e6
        writer.writerow([target, workload, repeat,
                         f'{total:.9f}', f'{avg_us:.3f}',
                         result, 'N/A'])
        sys.stdout.flush()

if __name__ == '__main__':
    main()
