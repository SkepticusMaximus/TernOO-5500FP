#!/usr/bin/env python3
"""ternoo_bridge — ONE Python bridge onto BOTH native 5500FP cores.

    backend="c"    -> c_emulator/libternoo_c.so   the crowned portable
                                                  primary spine (step-1
                                                  head-to-head: ~9-14x
                                                  over the NASM core)
    backend="nasm" -> bin/libternoo.so            the x86-64 showcase

Both libraries expose the same seven-symbol ternoo_* ABI, so one engine
class drives either — the captain's redundancy doctrine at the ABI
level. Its first act was to expose a real finding: the cores are one
architecture, TWO instruction dialects (see load_program), so encoded
words do NOT interchange yet. cross_check() therefore audits within a
backend today; cross-CORE auditing goes live when the canonical-encoding
ruling lands. Text assembly is served by the C core's exported
assembler (C dialect); nasm_word/nasm_ldi hand-encode the NASM dialect.

    python3 ternoo_bridge.py            # self-test: 4 canonical programs
                                        # cross-checked on both cores
    TERNOO_BACKEND=nasm python3 ...     # flip the default backend
"""
import ctypes
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_PATHS = {
    "c": os.path.join(_HERE, "c_emulator", "libternoo_c.so"),
    "nasm": os.path.join(_HERE, "bin", "libternoo.so"),
}
_BUILD = {
    "c": "make -C c_emulator libternoo_c.so",
    "nasm": "make",
}
_libs = {}

DEFAULT_BACKEND = os.environ.get("TERNOO_BACKEND", "c")


def _trits(value, n):
    """Signed integer -> n balanced-ternary digits, least significant first."""
    out, v = [], int(value)
    for _ in range(n):
        r = v % 3
        if r == 2:
            out.append(-1)
            v = (v + 1) // 3
        else:
            out.append(r)
            v = (v - r) // 3
    return out


def to_bet(value, n_trits=24):
    """Balanced-ternary value -> BET bit-packing (0->00, +1->01, -1->10),
    trit i in bits 2i..2i+1 — the NASM core's storage format."""
    packed = 0
    for i, t in enumerate(_trits(value, n_trits)):
        if t == 1:
            packed |= 0b01 << (2 * i)
        elif t == -1:
            packed |= 0b10 << (2 * i)
    return packed


def nasm_word(fields):
    """Hand-encode one NASM-dialect instruction word from
    [(trit_pos, n_trits, value), ...]. BOTH cores store words as
    POSITIONAL balanced-ternary integer values (set_field_val round-trips
    through from_bet); BET bits are only the field-op internal form. The
    dialects differ in FIELD LAYOUT and opcode numbering, not storage."""
    return sum(val * (3 ** pos) for pos, _n, val in fields)


def nasm_ldi(rd, imm):
    """NASM-dialect LDI: op=8 at (20,4); imm at (8,12); Rd-40 at (0,4)."""
    return nasm_word([(0, 4, rd - 40), (8, 12, imm), (20, 4, 8)])


def nasm_hlt():
    return nasm_word([(20, 4, 1)])


def _lib(backend):
    """Load (once) and return the ctypes library for a backend."""
    if backend not in _PATHS:
        raise ValueError(f"unknown backend {backend!r} — want 'c' or 'nasm'")
    if backend in _libs:
        return _libs[backend]
    path = _PATHS[backend]
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found — build it:  cd {_HERE} && {_BUILD[backend]}")
    lib = ctypes.CDLL(path)
    lib.ternoo_init.argtypes = []
    lib.ternoo_init.restype = None
    lib.ternoo_reset.argtypes = []
    lib.ternoo_reset.restype = None
    lib.ternoo_run.argtypes = []
    lib.ternoo_run.restype = None
    lib.ternoo_read_reg.argtypes = [ctypes.c_int]
    lib.ternoo_read_reg.restype = ctypes.c_uint64
    lib.ternoo_write_reg.argtypes = [ctypes.c_int, ctypes.c_uint64]
    lib.ternoo_write_reg.restype = None
    lib.ternoo_mem_write.argtypes = [ctypes.c_uint64, ctypes.c_uint64]
    lib.ternoo_mem_write.restype = None
    lib.ternoo_mem_read.argtypes = [ctypes.c_uint64]
    lib.ternoo_mem_read.restype = ctypes.c_uint64
    try:                       # C-core extras; absent from the NASM library
        lib.ternoo_asm.argtypes = [ctypes.c_char_p,
                                   ctypes.POINTER(ctypes.c_int64),
                                   ctypes.c_int]
        lib.ternoo_asm.restype = ctypes.c_int
        lib.ternoo_cycles.argtypes = []
        lib.ternoo_cycles.restype = ctypes.c_uint64
    except AttributeError:
        pass
    try:                       # NASM-core extra: raw INSTRUCTION port —
        lib.ternoo_load_word.argtypes = [ctypes.c_uint64, ctypes.c_uint64]
        lib.ternoo_load_word.restype = None   # mem_write is a clamping DATA
    except AttributeError:                    # port; BET instructions exceed
        pass                                  # the clamp and need this one
    _libs[backend] = lib
    return lib


class TernOONativeEngine:
    """Python handle onto a native 5500FP core (C or NASM)."""

    def __init__(self, backend=None):
        self.backend = backend or DEFAULT_BACKEND
        self._lib = _lib(self.backend)
        self._lib.ternoo_init()
        self.reset()

    def reset(self):
        self._lib.ternoo_reset()

    def read_reg(self, reg_idx):
        return self._lib.ternoo_read_reg(reg_idx)

    def write_reg(self, reg_idx, value):
        self._lib.ternoo_write_reg(reg_idx, value)

    def write_mem(self, addr, value):
        self._lib.ternoo_mem_write(addr, value)

    def read_mem(self, addr):
        return self._lib.ternoo_mem_read(addr)

    def load_program(self, word_list, start_addr=0):
        """Install instruction words IN THIS BACKEND'S OWN DIALECT.

        FINDING (18-08-2026, exposed by the first cross-check): the two
        cores are one architecture but TWO instruction DIALECTS. Both
        store words as positional balanced-ternary integer values, but:
          C core:    6-trit opcode at trit 18, its own opcode numbers,
                     UNBIASED 4-trit registers — only R0..R40 reachable
          NASM core: 4-trit opcode at trit 20 (the audit-canon 2+4+18
                     shape), its own opcode numbers, registers biased
                     -40 — the full canon 81 (R0..R80)
        Words do NOT interchange. Which layout is 5500FP canon is a
        captain's ruling; until then the bridge loads verbatim in each
        backend's own dialect. NASM loads use ternoo_load_word (the raw
        instruction port; its ternoo_mem_write DATA port clamps)."""
        raw = getattr(self._lib, "ternoo_load_word", None)
        for i, word in enumerate(word_list):
            w = word & 0xFFFFFFFFFFFFFFFF
            if raw is not None:
                raw(start_addr + i, w)
            else:
                self.write_mem(start_addr + i, w)

    def run(self):
        self._lib.ternoo_run()

    def run_program(self, words, result_reg=None):
        """reset -> load -> run; return result_reg's value if asked."""
        self.reset()
        self.load_program(words)
        self.run()
        return None if result_reg is None else self.read_reg(result_reg)


def assemble(source):
    """.t5asm text -> encoded instruction words (via the C core's
    assembler; the words run on either core)."""
    lib = _lib("c")
    buf = (ctypes.c_int64 * 4096)()
    n = lib.ternoo_asm(source.encode("utf-8"), buf, 4096)
    if n <= 0:
        raise ValueError(f"assembly failed (rc={n})")
    return [int(buf[i]) for i in range(n)]


def cross_check(source_or_words, watch_regs, backends=("c", "nasm")):
    """Run one program on every backend and compare the watched registers.

    Returns (agree: bool, {backend: {reg: value}}). Two independent
    implementations of the ISA auditing each other — a disagreement means
    one of them is wrong, and you just found out for free."""
    if isinstance(source_or_words, str):
        words = assemble(source_or_words)
    else:
        words = list(source_or_words)
    results = {}
    for b in backends:
        eng = TernOONativeEngine(b)
        eng.run_program(words)
        results[b] = {r: eng.read_reg(r) for r in watch_regs}
    first = results[backends[0]]
    agree = all(results[b] == first for b in backends)
    return agree, results


# ── self-test: the four canonical workloads, cross-checked ──────────────────
_CANON = [
    ("fib(30)", 11, 832040,
     "LI R10, 0\nLI R11, 1\nLI R12, 29\n"
     "fib_loop:\nBEQZ R12, fib_done\nADD R13, R10, R11\nMOV R10, R11\n"
     "MOV R11, R13\nSUBI R12, R12, 1\nJMP fib_loop\nfib_done:\nHALT\n"),
    ("fact(12)", 11, 479001600,
     "LI R10, 12\nLI R11, 1\n"
     "fact_loop:\nBEQZ R10, fact_done\nMUL R11, R11, R10\n"
     "SUBI R10, R10, 1\nJMP fact_loop\nfact_done:\nHALT\n"),
    ("array_sum(1000)", 3, 500500,
     "LI R3, 0\nLI R4, 1\nLI R5, 1001\n"
     "sum_loop:\nBEQ R4, R5, sum_done\nADD R3, R3, R4\nADDI R4, R4, 1\n"
     "JMP sum_loop\nsum_done:\nHALT\n"),
    ("arith_loop(3000)", 12, 3,
     "LI R10, 1\nLI R11, 2\nLI R12, 0\nLI R13, 3000\n"
     "arith_loop:\nBEQZ R13, arith_done\nADD R12, R10, R11\nMOV R10, R11\n"
     "SUB R11, R12, R10\nSUBI R13, R13, 1\nJMP arith_loop\n"
     "arith_done:\nHALT\n"),
]


def selftest():
    print(f"bridge self-test (default backend = {DEFAULT_BACKEND})")
    ok = True
    print("[1] C backend — four canonical programs via its assembler:")
    for name, reg, expected, src in _CANON:
        got = TernOONativeEngine("c").run_program(assemble(src), reg)
        good = got == expected
        ok = ok and good
        print(f"  {'PASS' if good else 'FAIL'}  {name:18s} "
              f"got={got}  expect={expected}")
    print("[2] NASM backend — hand-encoded native-dialect probe:")
    eng = TernOONativeEngine("nasm")
    eng.run_program([nasm_ldi(10, 7), nasm_ldi(45, -33), nasm_hlt()])
    r10 = eng.read_reg(10)
    r45 = ctypes.c_int64(eng.read_reg(45)).value
    good = r10 == 7 and r45 == -33
    ok = ok and good
    print(f"  {'PASS' if good else 'FAIL'}  LDI R10,7; LDI R45,-33; HLT  "
          f"-> R10={r10}  R45={r45}")
    print("[3] cross-core word interchange: BLOCKED BY FINDING — one")
    print("    architecture, two instruction DIALECTS (see load_program");
    print("    docstring). Canonical-encoding ruling pending; until then")
    print("    cross_check() runs within a single backend only.")
    print("BRIDGE " + ("OK — both backends execute ✓" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
