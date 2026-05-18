#!/usr/bin/env python3
"""
5500FP Balanced Ternary RISC Processor Emulator
================================================
A Python emulator of the 5500FP 24-trit balanced ternary processor
as described in: La Rosa, Claudio Lorenzo (2026). "5500FP: A 24-Trit
Balanced Ternary RISC Processor." Zenodo. doi:10.5281/zenodo.18881738

Trit values:  N = -1,  Z = 0,  P = +1
Trit symbols: N / Z / P  (also shown as - / 0 / +)

Data widths:
  Trit   =  1 trit   range: {-1, 0, +1}
  Tryte  =  6 trits  range: [-364, +364]
  Short  = 12 trits  range: [-265720, +265720]
  Word   = 24 trits  range: [-141214768240, +141214768240]  (approx ±141B)

Register file: 81 general-purpose registers (R0..R80), each 24 trits wide.
  R0 is hardwired to zero (reads always return 0, writes are discarded).

Version: 0.1.0  (Math + Load/Store + basic control flow)
Author:  Stevo (SkepticusMaximus) with Claude (Anthropic)
"""

import sys
from typing import List, Optional

# ── Trit / Word arithmetic ────────────────────────────────────────────────────

TRIT_MIN  = -1
TRIT_MAX  =  1
TRYTE_TRITS  =  6
SHORT_TRITS  = 12
WORD_TRITS   = 24

def _pow3(n: int) -> int:
    return 3 ** n

WORD_MAX  = (_pow3(WORD_TRITS)  - 1) // 2   #  141,214,768,240
WORD_MIN  = -WORD_MAX                         # -141,214,768,240
SHORT_MAX = (_pow3(SHORT_TRITS) - 1) // 2    #  265,720
SHORT_MIN = -SHORT_MAX
TRYTE_MAX = (_pow3(TRYTE_TRITS) - 1) // 2   #  364
TRYTE_MIN = -TRYTE_MAX

def clamp_word(v: int) -> int:
    """Wrap value into balanced ternary word range (saturate at edges)."""
    if v > WORD_MAX:
        return WORD_MAX
    if v < WORD_MIN:
        return WORD_MIN
    return v

def to_trits(value: int, width: int) -> List[int]:
    """
    Convert an integer to a balanced ternary list of `width` trits.
    Least-significant trit first.
    """
    trits = []
    v = value
    for _ in range(width):
        r = v % 3
        if r == 2:
            r = -1
        trits.append(r)
        v = (v - r) // 3
    return trits

def from_trits(trits: List[int]) -> int:
    """Convert a balanced ternary list (LSB first) to an integer."""
    result = 0
    for i, t in enumerate(trits):
        result += t * (_pow3(i))
    return result

def trit_negate(trits: List[int]) -> List[int]:
    """Negate all trits — trivial in balanced ternary."""
    return [-t for t in trits]

def word_to_str(value: int, width: int = WORD_TRITS) -> str:
    """Format integer as balanced ternary string using +/0/- notation (MSB first)."""
    trits = to_trits(value, width)
    symbols = {-1: '-', 0: '0', 1: '+'}
    return ''.join(symbols[t] for t in reversed(trits))

def get_trit(value: int, position: int) -> int:
    """Extract trit at given position (0 = LSB) from integer value."""
    trits = to_trits(value, WORD_TRITS)
    if 0 <= position < len(trits):
        return trits[position]
    return 0

def set_trit(value: int, position: int, trit: int) -> int:
    """Return new integer with trit at position replaced."""
    trits = to_trits(value, WORD_TRITS)
    if 0 <= position < len(trits):
        trits[position] = max(-1, min(1, trit))
    return from_trits(trits)

# ── Ternary-native operations ─────────────────────────────────────────────────

def trit_min(a: int, b: int) -> int:
    """Trit-wise minimum (ternary AND)."""
    ta = to_trits(a, WORD_TRITS)
    tb = to_trits(b, WORD_TRITS)
    return from_trits([min(x, y) for x, y in zip(ta, tb)])

def trit_max(a: int, b: int) -> int:
    """Trit-wise maximum (ternary OR)."""
    ta = to_trits(a, WORD_TRITS)
    tb = to_trits(b, WORD_TRITS)
    return from_trits([max(x, y) for x, y in zip(ta, tb)])

def trit_txor(a: int, b: int) -> int:
    """Ternary XOR: result trit = (a+b) mod 3 in balanced form."""
    ta = to_trits(a, WORD_TRITS)
    tb = to_trits(b, WORD_TRITS)
    def _txor(x, y):
        r = (x + y) % 3
        if r == 2: r = -1
        return r
    return from_trits([_txor(x, y) for x, y in zip(ta, tb)])

def trit_equal(a: int, b: int) -> int:
    """Trit-wise equality: P if equal, N if not equal."""
    ta = to_trits(a, WORD_TRITS)
    tb = to_trits(b, WORD_TRITS)
    return from_trits([1 if x == y else -1 for x, y in zip(ta, tb)])

def trit_sum(a: int, b: int) -> int:
    """Ternary sum function: trit-wise (a+b) clamped to {-1,0,+1}."""
    ta = to_trits(a, WORD_TRITS)
    tb = to_trits(b, WORD_TRITS)
    return from_trits([max(-1, min(1, x + y)) for x, y in zip(ta, tb)])

# ── Instruction format constants ──────────────────────────────────────────────
# All fields are 4 trits wide. 24-trit word = 6 x 4-trit fields.
# Fields (MSB to LSB): F5 F4 F3 F2 F1 F0
#   F5 = opcode (or first [ext] in formats B-F)
#   Remaining fields carry registers or immediates per format.

FIELD_WIDTH = 4   # trits per field
NUM_FIELDS  = 6   # fields per 24-trit word

def decode_fields(instruction: int) -> List[int]:
    """
    Decode a 24-trit instruction into 6 x 4-trit signed fields.
    Returns [F0, F1, F2, F3, F4, F5] where F5 is MSB (opcode field).
    Each field is a signed integer in range [-40, +40] (3^4=81 values).
    """
    trits = to_trits(instruction, WORD_TRITS)
    fields = []
    for i in range(NUM_FIELDS):
        field_trits = trits[i*FIELD_WIDTH : (i+1)*FIELD_WIDTH]
        fields.append(from_trits(field_trits))
    return fields  # [F0, F1, F2, F3, F4, F5]

def encode_reg(r: int) -> int:
    """Encode register number (0-80) as 4-trit signed integer."""
    # Registers 0-80 map to balanced ternary -40..+40
    return r - 40

def decode_reg(field: int) -> int:
    """Decode 4-trit field to register index (0-80)."""
    return field + 40

# ── Opcode definitions ────────────────────────────────────────────────────────
# Format A: [F5=opcode][F4=Rs4][F3=Rs3][F2=Rs2][F1=Rs1][F0=Rd]
# Format J2: [F5=opcode][F4..F3=Imm12][F1=Rs1][F0=Rd]  (Imm12 = 2 x 4-trit fields)
# We implement a representative subset for v0.1

# Opcodes are 4-trit values. We use integer keys for the dispatch table.
# Selected opcodes from the paper (approximated — full table not published):

OP_NOP   =  0   # No operation
OP_HLT   =  1   # Halt
OP_ADD   =  2   # ADD  Rd, Rs1, Rs2
OP_SUB   =  3   # SUB  Rd, Rs1, Rs2
OP_MUL   =  4   # MUL  Rd, Rs1, Rs2
OP_DIV   =  5   # DIV  Rd, Rs1, Rs2
OP_NEG   =  6   # NEG  Rd, Rs1       (negate — trivial in balanced ternary)
OP_MOV   =  7   # MOV  Rd, Rs1
OP_LDI   =  8   # LDI  Rd, Imm       (load immediate, J2 format)
OP_LD    =  9   # LD   Rd, Rs1       (load from memory[Rs1])
OP_ST    = 10   # ST   Rs1, Rs2      (store Rs1 to memory[Rs2])
OP_JMP   = 11   # JMP  Imm           (unconditional jump, J format)
OP_JEQ   = 12   # JEQ  Rs1, Rs2, Imm (jump if Rs1 == Rs2)
OP_JNE   = 13   # JNE  Rs1, Rs2, Imm (jump if Rs1 != Rs2)
OP_JB    = 14   # JB   Rs1, Rs2, Imm (jump if Rs1 < Rs2)
OP_JSR   = 15   # JSR  Imm           (jump to subroutine)
OP_RTI   = 16   # RTI                (return from subroutine)
OP_PUSH  = 17   # PUSH Rs1
OP_POP   = 18   # POP  Rd
OP_MIN   = 19   # MIN  Rd, Rs1, Rs2  (trit-wise minimum)
OP_MAX   = 20   # MAX  Rd, Rs1, Rs2  (trit-wise maximum)
OP_TXOR  = 21   # TXOR Rd, Rs1, Rs2
OP_EQUAL = 22   # EQUAL Rd, Rs1, Rs2
OP_SUM   = 23   # SUM  Rd, Rs1, Rs2
OP_TTT   = 24   # TTT  Rs1, pos, Imm  (test trit T at pos, branch if T)
OP_TTZ   = 25   # TTZ  Rs1, pos, Imm  (test trit Z at pos, branch if Z)
OP_TTP   = 26   # TTP  Rs1, pos, Imm  (test trit P at pos, branch if P)
OP_ADDI  = 27   # ADDI Rd, Rs1, Imm
OP_SUBI  = 28   # SUBI Rd, Rs1, Imm
OP_OUT   = 29   # OUT  Rs1           (write Rs1 to stdout, for debugging)
OP_IN    = 30   # IN   Rd            (read integer from stdin into Rd)

# ── TernOO opcodes ────────────────────────────────────────────────────────────
# Port of the TernOO object-oriented extension (originally for SBTCVM Gen2-9)
# to the 5500FP 24-trit architecture.
# Type tag convention (MSB trit, position 23):
#   N = -1 → Integer,  Z = 0 → Float,  P = +1 → String
# Payload: trits 0-22  (23 trits, range ±2,354,913,520)
OP_TOBJ     = 31  # TOBJ     Rd, Rs1, Rs2  — tag value in Rs1 with type in Rs2
OP_TGET     = 32  # TGET     Rd, Rs1       — get type tag of Rs1 into Rd
OP_TPAYLOAD = 33  # TPAYLOAD Rd, Rs1       — strip type tag, get payload
OP_TCALL    = 34  # TCALL    Rd,Rs1,Rs2,Rs3 — three-way dispatch on type tag of Rd
OP_TNEW     = 35  # TNEW     Rd, Rs1, Rs2  — allocate typed object on heap

TTYPE_INT   = -1  # Integer type tag
TTYPE_FLOAT =  0  # Float type tag
TTYPE_STR   =  1  # String type tag


# ── CPU ───────────────────────────────────────────────────────────────────────

MEMORY_SIZE = 3**12  # 531,441 words — modest but workable

HEAP_BASE   = MEMORY_SIZE // 2  # heap starts at midpoint of memory
class CPU5500FP:
    """
    5500FP balanced ternary RISC processor emulator.
    
    Registers:
      R0  = hardwired zero
      R1..R79 = general purpose
      R80 = stack pointer (SP) by convention
    
    Special registers (not in the general file):
      PC  = program counter (word address)
      PSW = program status word (condition flags)
    
    Memory:
      Word-addressed. Each location holds one 24-trit word.
    """

    NUM_REGS = 81

    def __init__(self, memory_size: int = MEMORY_SIZE):
        self.regs   = [0] * self.NUM_REGS   # R0..R80
        self.pc     = 0                      # program counter
        self.psw    = 0                      # program status word
        self.memory = [0] * memory_size      # word-addressed memory
        self.halted = False
        self.call_stack: List[int] = []      # return address stack
        self.cycle_count = 0
        self._trace = False                  # enable instruction trace
        self._heap_ptr = HEAP_BASE           # bump allocator pointer

    def reset(self):
        self.regs    = [0] * self.NUM_REGS
        self.pc      = 0
        self.psw     = 0
        self.halted  = False
        self.call_stack = []
        self.cycle_count = 0
        self._heap_ptr = HEAP_BASE

    def _heap_alloc(self, size: int) -> int:
        """Bump allocator — returns base address of allocated block."""
        size = max(1, size)
        addr = self._heap_ptr
        self._heap_ptr += size
        if self._heap_ptr >= len(self.memory):
            raise MemoryError("Heap exhausted")
        return addr

    # ── Register access ───────────────────────────────────────────────────────

    def read_reg(self, r: int) -> int:
        if r == 0:
            return 0  # R0 hardwired to zero
        return self.regs[r % self.NUM_REGS]

    def write_reg(self, r: int, value: int):
        if r == 0:
            return  # R0 writes discarded
        self.regs[r % self.NUM_REGS] = clamp_word(value)

    # ── Memory access ─────────────────────────────────────────────────────────

    def mem_read(self, addr: int) -> int:
        if 0 <= addr < len(self.memory):
            return self.memory[addr]
        raise MemoryError(f"Read out of bounds: address {addr}")

    def mem_write(self, addr: int, value: int):
        if 0 <= addr < len(self.memory):
            self.memory[addr] = clamp_word(value)
        else:
            raise MemoryError(f"Write out of bounds: address {addr}")

    # ── Instruction fetch ─────────────────────────────────────────────────────

    def fetch(self) -> int:
        instr = self.mem_read(self.pc)
        self.pc += 1
        return instr

    # ── Decode helpers ────────────────────────────────────────────────────────

    def _fields(self, instr: int):
        """Return (F0, F1, F2, F3, F4, F5) for instruction."""
        f = decode_fields(instr)
        return f[0], f[1], f[2], f[3], f[4], f[5]

    def _regs_A(self, instr: int):
        """Format A: opcode=F5, Rs4=F4, Rs3=F3, Rs2=F2, Rs1=F1, Rd=F0"""
        f0, f1, f2, f3, f4, f5 = self._fields(instr)
        rd  = decode_reg(f0)
        rs1 = decode_reg(f1)
        rs2 = decode_reg(f2)
        rs3 = decode_reg(f3)
        rs4 = decode_reg(f4)
        return rd, rs1, rs2, rs3, rs4

    def _imm_J2(self, instr: int):
        """Format J2: opcode=F5, Imm12=F4:F3, Rs1=F1, Rd=F0"""
        f0, f1, f2, f3, f4, f5 = self._fields(instr)
        rd   = decode_reg(f0)
        rs1  = decode_reg(f1)
        # Imm12: combine F3 and F4 as a 12-trit immediate
        imm_trits = to_trits(f3, FIELD_WIDTH) + to_trits(f4, FIELD_WIDTH)
        imm  = from_trits(imm_trits)
        return rd, rs1, imm

    def _imm_J(self, instr: int):
        """Format J: opcode=F5, Imm20=F4:F3:F2:F1:F0 (5 x 4-trit fields)"""
        f0, f1, f2, f3, f4, f5 = self._fields(instr)
        imm_trits = (to_trits(f0, FIELD_WIDTH) + to_trits(f1, FIELD_WIDTH) +
                     to_trits(f2, FIELD_WIDTH) + to_trits(f3, FIELD_WIDTH) +
                     to_trits(f4, FIELD_WIDTH))
        return from_trits(imm_trits)

    # ── Opcode dispatch ───────────────────────────────────────────────────────

    def execute(self, instr: int):
        """Decode and execute one instruction."""
        f = decode_fields(instr)
        # Extract raw opcode field (F5, MSB field) as a 4-trit signed int
        # Map it to an opcode integer for dispatch
        # In a real ISA the opcode field itself is ternary-encoded;
        # here we use a simplified direct mapping for the prototype.
        opcode_raw = f[5]  # signed 4-trit value in [-40, +40]
        # We map the opcode_raw directly to our OP_ constants
        # (In a full implementation this would use the paper's exact encoding)
        op = opcode_raw  # opcode stored directly

        if self._trace:
            print(f"  PC={self.pc-1:4d}  op={op:3d}  "
                  f"instr={word_to_str(instr)}  "
                  f"fields={f}")

        # ── No-op / Halt ─────────────────────────────────────────────────────
        if op == OP_NOP:
            pass

        elif op == OP_HLT:
            self.halted = True
            if self._trace:
                print("  HALTED")

        # ── Arithmetic ───────────────────────────────────────────────────────
        elif op == OP_ADD:
            rd, rs1, rs2, *_ = self._regs_A(instr)
            self.write_reg(rd, self.read_reg(rs1) + self.read_reg(rs2))

        elif op == OP_ADDI:
            rd, rs1, imm = self._imm_J2(instr)
            self.write_reg(rd, self.read_reg(rs1) + imm)

        elif op == OP_SUB:
            rd, rs1, rs2, *_ = self._regs_A(instr)
            self.write_reg(rd, self.read_reg(rs1) - self.read_reg(rs2))

        elif op == OP_SUBI:
            rd, rs1, imm = self._imm_J2(instr)
            self.write_reg(rd, self.read_reg(rs1) - imm)

        elif op == OP_MUL:
            rd, rs1, rs2, *_ = self._regs_A(instr)
            self.write_reg(rd, self.read_reg(rs1) * self.read_reg(rs2))

        elif op == OP_DIV:
            rd, rs1, rs2, *_ = self._regs_A(instr)
            divisor = self.read_reg(rs2)
            if divisor == 0:
                raise ZeroDivisionError("DIV by zero")
            self.write_reg(rd, int(self.read_reg(rs1) / divisor))

        elif op == OP_NEG:
            rd, rs1, *_ = self._regs_A(instr)
            self.write_reg(rd, -self.read_reg(rs1))

        elif op == OP_MOV:
            rd, rs1, *_ = self._regs_A(instr)
            self.write_reg(rd, self.read_reg(rs1))

        # ── Immediate load ───────────────────────────────────────────────────
        elif op == OP_LDI:
            rd, _, imm = self._imm_J2(instr)
            self.write_reg(rd, imm)

        # ── Memory ───────────────────────────────────────────────────────────
        elif op == OP_LD:
            rd, rs1, *_ = self._regs_A(instr)
            addr = self.read_reg(rs1)
            self.write_reg(rd, self.mem_read(addr))

        elif op == OP_ST:
            rd, rs1, rs2, *_ = self._regs_A(instr)
            # ST Rs1, Rs2 — store value in Rs1 to address in Rs2
            self.mem_write(self.read_reg(rs2), self.read_reg(rs1))

        # ── Control flow ─────────────────────────────────────────────────────
        elif op == OP_JMP:
            self.pc = self._imm_J(instr)

        elif op == OP_JSR:
            self.call_stack.append(self.pc)
            self.pc = self._imm_J(instr)

        elif op == OP_RTI:
            if self.call_stack:
                self.pc = self.call_stack.pop()
            else:
                raise RuntimeError("RTI with empty call stack")

        elif op == OP_JEQ:
            rd, rs1, imm = self._imm_J2(instr)
            if self.read_reg(rd) == self.read_reg(rs1):
                self.pc += imm

        elif op == OP_JNE:
            rd, rs1, imm = self._imm_J2(instr)
            if self.read_reg(rd) != self.read_reg(rs1):
                self.pc += imm

        elif op == OP_JB:
            rd, rs1, imm = self._imm_J2(instr)
            if self.read_reg(rd) < self.read_reg(rs1):
                self.pc += imm

        # ── Stack ────────────────────────────────────────────────────────────
        elif op == OP_PUSH:
            rd, *_ = self._regs_A(instr)
            sp = self.read_reg(80)
            self.mem_write(sp, self.read_reg(rd))
            self.write_reg(80, sp - 1)

        elif op == OP_POP:
            rd, *_ = self._regs_A(instr)
            sp = self.read_reg(80) + 1
            self.write_reg(80, sp)
            self.write_reg(rd, self.mem_read(sp))

        # ── Ternary-native ───────────────────────────────────────────────────
        elif op == OP_MIN:
            rd, rs1, rs2, *_ = self._regs_A(instr)
            self.write_reg(rd, trit_min(self.read_reg(rs1), self.read_reg(rs2)))

        elif op == OP_MAX:
            rd, rs1, rs2, *_ = self._regs_A(instr)
            self.write_reg(rd, trit_max(self.read_reg(rs1), self.read_reg(rs2)))

        elif op == OP_TXOR:
            rd, rs1, rs2, *_ = self._regs_A(instr)
            self.write_reg(rd, trit_txor(self.read_reg(rs1), self.read_reg(rs2)))

        elif op == OP_EQUAL:
            rd, rs1, rs2, *_ = self._regs_A(instr)
            self.write_reg(rd, trit_equal(self.read_reg(rs1), self.read_reg(rs2)))

        elif op == OP_SUM:
            rd, rs1, rs2, *_ = self._regs_A(instr)
            self.write_reg(rd, trit_sum(self.read_reg(rs1), self.read_reg(rs2)))

        # ── Trit test and branch ─────────────────────────────────────────────
        elif op in (OP_TTT, OP_TTZ, OP_TTP):
            # TTx Rs1, pos, offset — test trit at position pos
            rd, rs1, imm = self._imm_J2(instr)
            pos = self.read_reg(rs1)   # position from register
            t = get_trit(self.read_reg(rd), pos)
            if   op == OP_TTT and t == -1: self.pc += imm
            elif op == OP_TTZ and t ==  0: self.pc += imm
            elif op == OP_TTP and t ==  1: self.pc += imm

        # ── TernOO object-oriented extensions ────────────────────────────────
        # Type tag lives in trit 23 (MSB of 24-trit word).
        # Payload is trits 0-22 (23 trits).
        # Type tags: N(-1)=Integer, Z(0)=Float, P(+1)=String, NP=Reference
        elif op == OP_TOBJ:
            # TOBJ Rd, Rs1, type_tag
            # Tag the value in Rs1 with type_tag, store in Rd.
            # Clears MSB trit then sets it to type_tag.
            rd, rs1, rs2, *_ = self._regs_A(instr)
            val      = self.read_reg(rs1)
            tag      = self.read_reg(rs2)   # -1=Int, 0=Float, 1=String
            tag      = max(-1, min(1, tag))
            payload  = set_trit(val, WORD_TRITS - 1, 0)   # clear MSB
            tagged   = set_trit(payload, WORD_TRITS - 1, tag)
            self.write_reg(rd, tagged)

        elif op == OP_TGET:
            # TGET Rd, Rs1
            # Extract type tag from Rs1 (MSB trit) into Rd.
            rd, rs1, *_ = self._regs_A(instr)
            tag = get_trit(self.read_reg(rs1), WORD_TRITS - 1)
            self.write_reg(rd, tag)

        elif op == OP_TPAYLOAD:
            # TPAYLOAD Rd, Rs1
            # Extract payload (trits 0-22) from a tagged object, strip type tag.
            rd, rs1, *_ = self._regs_A(instr)
            val     = self.read_reg(rs1)
            cleared = set_trit(val, WORD_TRITS - 1, 0)   # zero the MSB trit
            self.write_reg(rd, cleared)

        elif op == OP_TCALL:
            # TCALL Rs1, addr_N, addr_Z, addr_P
            # Three-way dispatch on type tag of Rs1:
            #   tag=N(-1) → jump to address in Rs2
            #   tag=Z(0)  → jump to address in Rs3
            #   tag=P(+1) → jump to address in Rs4
            # Uses the 5500FP's native three-way trit dispatch.
            rd, rs1, rs2, rs3, rs4 = self._regs_A(instr)
            tag = get_trit(self.read_reg(rd), WORD_TRITS - 1)
            self.call_stack.append(self.pc)
            if   tag == -1: self.pc = self.read_reg(rs1)
            elif tag ==  0: self.pc = self.read_reg(rs2)
            elif tag ==  1: self.pc = self.read_reg(rs3)

        elif op == OP_TNEW:
            # TNEW Rd, type_tag, size
            # Allocate `size` words on the heap, tag the base address, store in Rd.
            # Heap grows upward from HEAP_BASE.
            rd, rs1, rs2, *_ = self._regs_A(instr)
            tag  = self.read_reg(rs1)
            size = self.read_reg(rs2)
            addr = self._heap_alloc(size)
            tagged_addr = set_trit(addr, WORD_TRITS - 1, max(-1, min(1, tag)))
            self.write_reg(rd, tagged_addr)

        # ── I/O (debug) ───────────────────────────────────────────────────────
        elif op == OP_OUT:
            rd, *_ = self._regs_A(instr)
            val = self.read_reg(rd)
            print(f"OUT R{rd} = {val}  [{word_to_str(val, WORD_TRITS)}]")

        elif op == OP_IN:
            rd, *_ = self._regs_A(instr)
            try:
                val = int(input("IN> "))
                self.write_reg(rd, val)
            except (ValueError, EOFError):
                self.write_reg(rd, 0)

        else:
            raise RuntimeError(f"Unknown opcode {op} at PC={self.pc-1}")

        self.cycle_count += 1

    # ── Run ───────────────────────────────────────────────────────────────────

    def run(self, max_cycles: int = 1_000_000):
        """Run until HLT or max_cycles reached."""
        while not self.halted and self.cycle_count < max_cycles:
            instr = self.fetch()
            self.execute(instr)
        if self.cycle_count >= max_cycles:
            print(f"[WARNING] Reached cycle limit ({max_cycles})")

    # ── Assembler helpers ─────────────────────────────────────────────────────

    def assemble_A(self, op: int, rd: int, rs1: int,
                   rs2: int = 40, rs3: int = 40, rs4: int = 40) -> int:
        """
        Build a Format A instruction word.
        Register numbers 0-80 are encoded as balanced ternary fields
        by shifting: field = reg - 40  (so R0=−40, R40=0, R80=+40)
        """
        trits = (to_trits(encode_reg(rd),  FIELD_WIDTH) +
                 to_trits(encode_reg(rs1), FIELD_WIDTH) +
                 to_trits(encode_reg(rs2), FIELD_WIDTH) +
                 to_trits(encode_reg(rs3), FIELD_WIDTH) +
                 to_trits(encode_reg(rs4), FIELD_WIDTH) +
                 to_trits(op,         FIELD_WIDTH))
        return from_trits(trits)

    def assemble_J2(self, op: int, rd: int, rs1: int, imm: int) -> int:
        """Build a Format J2 instruction word.
        Layout: F0=Rd, F1=Rs1, F2=unused(0), F3:F4=Imm12, F5=OpCode
        """
        imm_trits = to_trits(imm, FIELD_WIDTH * 2)  # 8 trits = 2 fields (F3, F4)
        trits = (to_trits(encode_reg(rd),  FIELD_WIDTH) +   # F0
                 to_trits(encode_reg(rs1), FIELD_WIDTH) +   # F1
                 to_trits(0,               FIELD_WIDTH) +   # F2 unused
                 imm_trits                              +   # F3, F4
                 to_trits(op,         FIELD_WIDTH))    # F5 opcode
        return from_trits(trits)

    def assemble_J(self, op: int, imm: int) -> int:
        """Build a Format J instruction word (20-trit immediate)."""
        imm_trits = to_trits(imm, FIELD_WIDTH * 5)  # 20 trits
        trits = imm_trits + to_trits(op, FIELD_WIDTH)
        return from_trits(trits)

    def load_program(self, program: List[int], start: int = 0):
        """Load a list of instruction words into memory."""
        for i, word in enumerate(program):
            self.mem_write(start + i, word)
        self.pc = start

    # ── Debug / inspection ────────────────────────────────────────────────────

    def dump_regs(self, count: int = 16):
        """Print first `count` registers."""
        print(f"\n── Registers (PC={self.pc}, cycles={self.cycle_count}) ──")
        for i in range(min(count, self.NUM_REGS)):
            v = self.read_reg(i)
            if v != 0:
                print(f"  R{i:2d} = {v:15d}  {word_to_str(v)}")
        print()

    def dump_memory(self, start: int, length: int):
        """Print memory contents."""
        print(f"\n── Memory [{start}..{start+length-1}] ──")
        for i in range(length):
            v = self.mem_read(start + i)
            print(f"  [{start+i:4d}] = {v:15d}  {word_to_str(v)}")
        print()


# ── Assembler convenience shortcuts ──────────────────────────────────────────

class Asm:
    """
    Convenience assembler helper.
    Usage:
        cpu = CPU5500FP()
        a = Asm(cpu)
        program = [
            a.LDI(1, 42),        # R1 = 42
            a.LDI(2, 10),        # R2 = 10
            a.ADD(3, 1, 2),      # R3 = R1 + R2
            a.OUT(3),            # print R3
            a.HLT(),
        ]
        cpu.load_program(program)
        cpu.run()
    """
    def __init__(self, cpu: CPU5500FP):
        self.cpu = cpu

    def NOP(self)                        -> int: return self.cpu.assemble_A(OP_NOP,  0, 0)
    def HLT(self)                        -> int: return self.cpu.assemble_A(OP_HLT,  0, 0)
    def ADD(self, rd, rs1, rs2)          -> int: return self.cpu.assemble_A(OP_ADD,  rd, rs1, rs2)
    def ADDI(self, rd, rs1, imm)         -> int: return self.cpu.assemble_J2(OP_ADDI, rd, rs1, imm)
    def SUB(self, rd, rs1, rs2)          -> int: return self.cpu.assemble_A(OP_SUB,  rd, rs1, rs2)
    def SUBI(self, rd, rs1, imm)         -> int: return self.cpu.assemble_J2(OP_SUBI, rd, rs1, imm)
    def MUL(self, rd, rs1, rs2)          -> int: return self.cpu.assemble_A(OP_MUL,  rd, rs1, rs2)
    def DIV(self, rd, rs1, rs2)          -> int: return self.cpu.assemble_A(OP_DIV,  rd, rs1, rs2)
    def NEG(self, rd, rs1)               -> int: return self.cpu.assemble_A(OP_NEG,  rd, rs1)
    def MOV(self, rd, rs1)               -> int: return self.cpu.assemble_A(OP_MOV,  rd, rs1)
    def LDI(self, rd, imm)               -> int: return self.cpu.assemble_J2(OP_LDI, rd, 0, imm)
    def LD(self, rd, rs1)                -> int: return self.cpu.assemble_A(OP_LD,   rd, rs1)
    def ST(self, rs1, rs2)               -> int: return self.cpu.assemble_A(OP_ST,   rs1, rs1, rs2)
    def JMP(self, addr)                  -> int: return self.cpu.assemble_J(OP_JMP,  addr)
    def JSR(self, addr)                  -> int: return self.cpu.assemble_J(OP_JSR,  addr)
    def RTI(self)                        -> int: return self.cpu.assemble_A(OP_RTI,  0, 0)
    def JEQ(self, rd, rs1, offset)       -> int: return self.cpu.assemble_J2(OP_JEQ, rd, rs1, offset)
    def JNE(self, rd, rs1, offset)       -> int: return self.cpu.assemble_J2(OP_JNE, rd, rs1, offset)
    def JB(self, rd, rs1, offset)        -> int: return self.cpu.assemble_J2(OP_JB,  rd, rs1, offset)
    def PUSH(self, rs1)                  -> int: return self.cpu.assemble_A(OP_PUSH, rs1, 0)
    def POP(self, rd)                    -> int: return self.cpu.assemble_A(OP_POP,  rd, 0)
    def MIN(self, rd, rs1, rs2)          -> int: return self.cpu.assemble_A(OP_MIN,  rd, rs1, rs2)
    def MAX(self, rd, rs1, rs2)          -> int: return self.cpu.assemble_A(OP_MAX,  rd, rs1, rs2)
    def TXOR(self, rd, rs1, rs2)         -> int: return self.cpu.assemble_A(OP_TXOR, rd, rs1, rs2)
    def EQUAL(self, rd, rs1, rs2)        -> int: return self.cpu.assemble_A(OP_EQUAL,rd, rs1, rs2)
    def SUM(self, rd, rs1, rs2)          -> int: return self.cpu.assemble_A(OP_SUM,  rd, rs1, rs2)
    def OUT(self, rs1)                   -> int: return self.cpu.assemble_A(OP_OUT,  rs1, 0)
    def IN(self, rd)                     -> int: return self.cpu.assemble_A(OP_IN,   rd, 0)
    # ── TernOO ───────────────────────────────────────────────────────────────
    def TOBJ(self, rd, rs1, rs2)         -> int: return self.cpu.assemble_A(OP_TOBJ,     rd, rs1, rs2)
    def TGET(self, rd, rs1)              -> int: return self.cpu.assemble_A(OP_TGET,     rd, rs1)
    def TPAYLOAD(self, rd, rs1)          -> int: return self.cpu.assemble_A(OP_TPAYLOAD, rd, rs1)
    def TCALL(self, rd, rs1, rs2, rs3)   -> int: return self.cpu.assemble_A(OP_TCALL,    rd, rs1, rs2, rs3)
    def TNEW(self, rd, rs1, rs2)         -> int: return self.cpu.assemble_A(OP_TNEW,     rd, rs1, rs2)


# ── Test programs ─────────────────────────────────────────────────────────────


def demo_trit_display():
    """Demo: show balanced ternary representation of various values."""
    print("=" * 60)
    print("DEMO: Balanced ternary representation")
    print("=" * 60)
    values = [0, 1, -1, 2, -2, 13, -13, 42, -42, 100, 364, -364,
              WORD_MAX, WORD_MIN]
    for v in values:
        print(f"  {v:20d}  {word_to_str(v)}")
    print()

def test_basic_arithmetic():
    """Test: R3 = 42 + 10 = 52, R4 = R3 - 7 = 45, R5 = R3 * R4"""
    print("=" * 60)
    print("TEST: Basic arithmetic")
    print("=" * 60)
    cpu = CPU5500FP()
    a   = Asm(cpu)

    program = [
        a.LDI(1, 42),        # R1 = 42
        a.LDI(2, 10),        # R2 = 10
        a.ADD(3, 1, 2),      # R3 = R1 + R2 = 52
        a.LDI(4, 7),         # R4 = 7
        a.SUB(5, 3, 4),      # R5 = R3 - R4 = 45
        a.MUL(6, 1, 2),      # R6 = R1 * R2 = 420
        a.NEG(7, 1),         # R7 = -R1 = -42
        a.OUT(3),
        a.OUT(5),
        a.OUT(6),
        a.OUT(7),
        a.HLT(),
    ]
    cpu.load_program(program)
    cpu.run()
    cpu.dump_regs(10)
    assert cpu.read_reg(3) == 52,  f"Expected 52, got {cpu.read_reg(3)}"
    assert cpu.read_reg(5) == 45,  f"Expected 45, got {cpu.read_reg(5)}"
    assert cpu.read_reg(6) == 420, f"Expected 420, got {cpu.read_reg(6)}"
    assert cpu.read_reg(7) == -42, f"Expected -42, got {cpu.read_reg(7)}"
    print("PASS\n")


def test_memory():
    """Test: store to memory and load back."""
    print("=" * 60)
    print("TEST: Memory store/load")
    print("=" * 60)
    cpu = CPU5500FP()
    a   = Asm(cpu)

    program = [
        a.LDI(1, 999),       # R1 = 999 (value to store)
        a.LDI(2, 200),       # R2 = 200 (address)
        a.ST(1, 2),          # memory[200] = R1
        a.LDI(3, 0),         # R3 = 0 (clear)
        a.LD(3, 2),          # R3 = memory[200]
        a.OUT(3),
        a.HLT(),
    ]
    cpu.load_program(program)
    cpu.run()
    assert cpu.read_reg(3) == 999, f"Expected 999, got {cpu.read_reg(3)}"
    print("PASS\n")


def test_ternary_native():
    """Test ternary-native instructions."""
    print("=" * 60)
    print("TEST: Ternary-native instructions")
    print("=" * 60)
    cpu = CPU5500FP()
    a   = Asm(cpu)

    # Use small values whose trit structure is easy to verify
    # 1 in balanced ternary = +0000...  (trit 0 = +1, rest = 0)
    # -1 in balanced ternary = -0000... (trit 0 = -1, rest = 0)
    program = [
        a.LDI(1,  1),        # R1 = +1
        a.LDI(2, -1),        # R2 = -1
        a.MIN(3, 1, 2),      # R3 = trit-min(+1, -1) = -1
        a.MAX(4, 1, 2),      # R4 = trit-max(+1, -1) = +1
        a.TXOR(5, 1, 2),     # R5 = trit-xor(+1, -1) = 0
        a.NEG(6, 1),         # R6 = -1 (trivial ternary negation)
        a.OUT(3),
        a.OUT(4),
        a.OUT(5),
        a.OUT(6),
        a.HLT(),
    ]
    cpu.load_program(program)
    cpu.run()
    assert cpu.read_reg(3) == -1, f"MIN: Expected -1, got {cpu.read_reg(3)}"
    assert cpu.read_reg(4) ==  1, f"MAX: Expected +1, got {cpu.read_reg(4)}"
    assert cpu.read_reg(5) ==  0, f"TXOR: Expected 0, got {cpu.read_reg(5)}"
    assert cpu.read_reg(6) == -1, f"NEG: Expected -1, got {cpu.read_reg(6)}"
    print("PASS\n")


def test_loop():
    """Test: count from 1 to 5 using a loop."""
    print("=" * 60)
    print("TEST: Loop (count 1 to 5)")
    print("=" * 60)
    cpu = CPU5500FP()
    a   = Asm(cpu)

    # R1 = counter, R2 = limit=5
    # Loop: OUT R1, R1++, if R1 != R2+1 jump back
    program = [
        a.LDI(1, 1),         # addr 0: R1 = 1 (counter)
        a.LDI(2, 6),         # addr 1: R2 = 6 (stop when R1 == R2)
        # loop start at addr 2:
        a.OUT(1),            # addr 2: print R1
        a.ADDI(1, 1, 1),     # addr 3: R1 = R1 + 1
        a.JNE(1, 2, -3),     # addr 4: if R1 != R2 jump back 3 (to addr 2)
        a.HLT(),             # addr 5
    ]
    cpu.load_program(program)
    cpu.run()
    assert cpu.read_reg(1) == 6, f"Expected counter=6, got {cpu.read_reg(1)}"
    print("PASS\n")


def test_subroutine():
    """Test JSR/RTI subroutine call."""
    print("=" * 60)
    print("TEST: Subroutine call (JSR/RTI)")
    print("=" * 60)
    cpu = CPU5500FP()
    a   = Asm(cpu)

    # Main: call double(5), result in R2
    # double: R2 = R1 * 2
    program = [
        a.LDI(1, 5),         # addr 0: R1 = 5
        a.JSR(3),            # addr 1: call subroutine at addr 3
        a.HLT(),             # addr 2: halt
        # subroutine at addr 3:
        a.MUL(2, 1, 1),      # addr 3: R2 = R1 * R1  (squaring, simpler test)
        a.RTI(),             # addr 4: return
    ]
    cpu.load_program(program)
    cpu.run()
    assert cpu.read_reg(2) == 25, f"Expected 25, got {cpu.read_reg(2)}"
    print("PASS\n")


def test_ternoo():
    """Test TernOO object-oriented extension opcodes."""
    print("=" * 60)
    print("TEST: TernOO opcodes (TOBJ, TGET, TPAYLOAD, TCALL, TNEW)")
    print("=" * 60)
    cpu = CPU5500FP()
    a   = Asm(cpu)

    # ── TOBJ / TGET / TPAYLOAD ────────────────────────────────────────────────
    # Tag the value 42 as Integer (tag=-1), then retrieve tag and payload.

    # Load type tag constants into registers
    cpu.write_reg(20, TTYPE_INT)    # R20 = -1 (Integer tag)
    cpu.write_reg(21, TTYPE_FLOAT)  # R21 =  0 (Float tag)
    cpu.write_reg(22, TTYPE_STR)    # R22 = +1 (String tag)

    program = [
        # Tag 42 as Integer
        a.LDI(1, 42),           # R1 = 42
        a.TOBJ(2, 1, 20),       # R2 = tagged(42, INT)
        a.TGET(3, 2),           # R3 = type tag of R2 → should be -1
        a.TPAYLOAD(4, 2),       # R4 = payload of R2 → should be 42

        # Tag 100 as String
        a.LDI(5, 100),          # R5 = 100
        a.TOBJ(6, 5, 22),       # R6 = tagged(100, STR)
        a.TGET(7, 6),           # R7 = type tag → should be +1
        a.TPAYLOAD(8, 6),       # R8 = payload → should be 100

        # Tag 0 as Float
        a.LDI(9, 77),           # R9 = 77
        a.TOBJ(10, 9, 21),      # R10 = tagged(77, FLOAT)
        a.TGET(11, 10),         # R11 = type tag → should be 0

        a.HLT(),
    ]
    cpu.load_program(program)
    cpu.run()

    assert cpu.read_reg(3) == TTYPE_INT,   f"TGET INT:   expected {TTYPE_INT},   got {cpu.read_reg(3)}"
    assert cpu.read_reg(4) == 42,          f"TPAYLOAD:  expected 42, got {cpu.read_reg(4)}"
    assert cpu.read_reg(7) == TTYPE_STR,   f"TGET STR:   expected {TTYPE_STR},   got {cpu.read_reg(7)}"
    assert cpu.read_reg(8) == 100,         f"TPAYLOAD:  expected 100, got {cpu.read_reg(8)}"
    assert cpu.read_reg(11) == TTYPE_FLOAT,f"TGET FLOAT: expected {TTYPE_FLOAT}, got {cpu.read_reg(11)}"
    print("  TOBJ / TGET / TPAYLOAD: PASS")

    # ── TCALL three-way dispatch ──────────────────────────────────────────────
    # Tag a value, then dispatch to three different handlers based on type.
    # Each handler writes a distinct result to R30, then halts.

    cpu2 = CPU5500FP()
    a2   = Asm(cpu2)
    cpu2.write_reg(20, TTYPE_INT)
    cpu2.write_reg(21, TTYPE_FLOAT)
    cpu2.write_reg(22, TTYPE_STR)

    # Addresses: handler_int=6, handler_float=9, handler_str=12
    prog2 = [
        a2.LDI(1, 99),          # addr 0: R1 = 99
        a2.TOBJ(2, 1, 22),      # addr 1: tag as String
        a2.LDI(10, 6),          # addr 2: R10 = addr of int handler
        a2.LDI(11, 9),          # addr 3: R11 = addr of float handler
        a2.LDI(12, 12),         # addr 4: R12 = addr of str handler
        a2.TCALL(2, 10, 11, 12),# addr 5: dispatch on type of R2
        # (TCALL pushes return addr; handlers halt instead of RTI for simplicity)
        # handler_int at addr 6:
        a2.LDI(30, -1),         # addr 6: R30 = -1 (int handler marker)
        a2.HLT(),               # addr 7
        a2.NOP(),               # addr 8: padding
        # handler_float at addr 9:
        a2.LDI(30, 0),          # addr 9: R30 = 0 (float handler marker)
        a2.HLT(),               # addr 10
        a2.NOP(),               # addr 11: padding
        # handler_str at addr 12:
        a2.LDI(30, 1),          # addr 12: R30 = 1 (str handler marker)
        a2.HLT(),               # addr 13
    ]
    cpu2.load_program(prog2)
    cpu2.run()
    assert cpu2.read_reg(30) == 1, f"TCALL: expected str handler (1), got {cpu2.read_reg(30)}"
    print("  TCALL three-way dispatch: PASS")

    # ── TNEW heap allocation ──────────────────────────────────────────────────
    cpu3 = CPU5500FP()
    a3   = Asm(cpu3)
    cpu3.write_reg(20, TTYPE_INT)

    prog3 = [
        a3.LDI(1, 4),           # R1 = 4 (allocate 4 words)
        a3.TNEW(2, 20, 1),      # R2 = tagged heap address (Integer, size 4)
        a3.TGET(3, 2),          # R3 = type tag of heap ptr → should be -1
        a3.HLT(),
    ]
    cpu3.load_program(prog3)
    cpu3.run()
    assert cpu3.read_reg(3) == TTYPE_INT, f"TNEW tag: expected {TTYPE_INT}, got {cpu3.read_reg(3)}"
    heap_addr = cpu3.read_reg(2)
    payload_addr = set_trit(heap_addr, WORD_TRITS - 1, 0)
    assert payload_addr == HEAP_BASE, f"TNEW addr: expected {HEAP_BASE}, got {payload_addr}"
    print("  TNEW heap allocation: PASS")

    # ── Pretty-print a tagged object ──────────────────────────────────────────
    print()
    print("  Tagged object display:")
    type_names = {TTYPE_INT: "Integer", TTYPE_FLOAT: "Float", TTYPE_STR: "String"}
    for tag, name in type_names.items():
        val = 42
        trits = to_trits(val, WORD_TRITS)
        trits[WORD_TRITS - 1] = tag
        tagged = from_trits(trits)
        recovered_tag = get_trit(tagged, WORD_TRITS - 1)
        recovered_payload = set_trit(tagged, WORD_TRITS - 1, 0)
        print(f"    {name:8s}  raw={tagged:15d}  "
              f"trit={word_to_str(tagged)}  "
              f"tag={recovered_tag:+d}  payload={recovered_payload}")
    print()
    print("TEST: TernOO PASS\n")


def test_ternoo_dispatch_demo():
    """
    Demo: a polymorphic 'describe' operation that prints different
    output depending on the type tag of its argument.
    Shows TernOO's three-way dispatch in action.
    """
    print("=" * 60)
    print("DEMO: TernOO polymorphic dispatch")
    print("=" * 60)

    cpu = CPU5500FP()
    a   = Asm(cpu)
    cpu.write_reg(20, TTYPE_INT)
    cpu.write_reg(21, TTYPE_FLOAT)
    cpu.write_reg(22, TTYPE_STR)

    # We'll call describe() three times with different types.
    # describe() is at address 20.
    # It reads R1 (the object), dispatches on type, outputs result.
    # int_handler=30, float_handler=33, str_handler=36

    prog = [
        # Call 1: Integer 42
        a.LDI(1, 42),           # 0
        a.TOBJ(1, 1, 20),       # 1: tag R1 as Integer
        a.LDI(10, 30),          # 2: int handler addr
        a.LDI(11, 33),          # 3: float handler addr
        a.LDI(12, 36),          # 4: str handler addr
        a.JSR(20),              # 5: call describe
        # Call 2: Float 77
        a.LDI(1, 77),           # 6
        a.TOBJ(1, 1, 21),       # 7: tag as Float
        a.JSR(20),              # 8: call describe
        # Call 3: String 99
        a.LDI(1, 99),           # 9
        a.TOBJ(1, 1, 22),       # 10: tag as String
        a.JSR(20),              # 11: call describe
        a.HLT(),                # 12

        # Padding to addr 20
        a.NOP(), a.NOP(), a.NOP(), a.NOP(), a.NOP(),  # 13-17
        a.NOP(), a.NOP(),                              # 18-19

        # describe() at addr 20:
        a.TCALL(1, 10, 11, 12), # 20: dispatch on type of R1

        # Padding to addr 30
        a.NOP(), a.NOP(), a.NOP(), a.NOP(), a.NOP(),  # 21-25
        a.NOP(), a.NOP(), a.NOP(), a.NOP(),            # 26-29

        # int_handler at addr 30:
        a.TPAYLOAD(2, 1),       # 30: R2 = payload
        a.OUT(2),               # 31: print it
        a.RTI(),                # 32: return

        # float_handler at addr 33:
        a.TPAYLOAD(2, 1),       # 33
        a.OUT(2),               # 34
        a.RTI(),                # 35

        # str_handler at addr 36:
        a.TPAYLOAD(2, 1),       # 36
        a.OUT(2),               # 37
        a.RTI(),                # 38
    ]
    cpu.load_program(prog)

    type_labels = {TTYPE_INT: "Integer", TTYPE_FLOAT: "Float", TTYPE_STR: "String"}
    print("  Polymorphic describe() output:")

    # Patch OUT to show type label
    original_execute = cpu.execute
    call_count = [0]
    type_seq = [TTYPE_INT, TTYPE_FLOAT, TTYPE_STR]

    cpu.run()
    print("\nDEMO: TernOO dispatch complete\n")
    """Demo: show balanced ternary representation of various values."""
    print("=" * 60)
    print("DEMO: Balanced ternary representation")
    print("=" * 60)
    values = [0, 1, -1, 2, -2, 13, -13, 42, -42, 100, 364, -364,
              WORD_MAX, WORD_MIN]
    for v in values:
        print(f"  {v:20d}  {word_to_str(v)}")
    print()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo_trit_display()
    test_basic_arithmetic()
    test_memory()
    test_ternary_native()
    test_loop()
    test_subroutine()
    test_ternoo()
    test_ternoo_dispatch_demo()
    print("All tests passed.")
    print(f"\n5500FP + TernOO emulator v0.1.0 ready.")
    print("Import CPU5500FP, Asm, TTYPE_INT/FLOAT/STR from this module.")
