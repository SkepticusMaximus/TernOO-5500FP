#!/usr/bin/env python3
"""
5500FP + TernOO Emulator  v0.2.0
=================================
A Python emulator of the 5500FP 24-trit balanced ternary processor with
TernOO object-oriented word architecture extensions.

Hardware reference:
  La Rosa, C.L. (2026). "5500FP: A 24-Trit Balanced Ternary RISC Processor."
  Zenodo. doi:10.5281/zenodo.18881738

Architecture reference:
  TernOO/5500FP Word Architecture Specification v0.2
  Author: Stevo (SkepticusMaximus) with Claude (Anthropic), May 2026

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRIT VALUES:   N = −1   Z = 0   P = +1
TRIT SYMBOLS:  −        0       +
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DATA WIDTHS:
  Trit    =  1 trit   {−1, 0, +1}
  Tribble =  6 trits  [−364, +364]        (6-trit "tryte")
  Short   = 12 trits  [−265720, +265720]
  Word    = 24 trits  [≈−141B, ≈+141B]

REGISTER FILE:  81 registers R0–R80, each one 24-trit word wide.
  R0       hardwired zero
  R1–R8    argument registers
  R9–R44   general purpose
  R45–R53  Double Null stack pointers (ST0–ST8)
  R54–R62  data segment base registers (DS0–DS8)
  R63–R71  code segment base registers (CS0–CS8)
  R72–R77  reserved for future system use
  R78      RWR  — Reserved Word Register (Double Null active context)
  R79      SP   — stack pointer
  R80      LR   — link register (return address)

BOOT CONVENTION:
  All registers = 0, PC = 0, all Double Null stacks empty.
  Program at address 0 runs first and sets up segment registers.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TERNOO WORD ARCHITECTURE  (T23 = MSB, T0 = LSB)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PRIMARY TYPE  (T23 — always fixed, always decoded first):
  −1 = EXEC   +0 = MAP   +1 = DATA

EXEC WORD  (T23=−1):
  T22=privilege  T21=call-style  T20=return-type
  T19-T18=seg-idx  T17-T12=offset  T11-T8=arity
  T7-T4=arg-types  T3-T0=version

MAP WORD  (T23=0):
  T22=axis-YZ  T21=axis-XZ  T20=axis-XY
  T19-T0=coordinate payload (qualifier-determined interpretation)

DATA WORD  (T23=+1):
  T22=subtype: −1=SCALAR  0=POINTER  +1=STRING

  SCALAR: T21=encoding(−1=float, 0=int, +1=uint)  T20-T0=value
  STRING: T21=encoding(−1=unicode, 0=ascii, +1=ternary)  T20-T0=len/addr
  POINTER: T21,T20=model (9 models — see PTR_* constants)
    USER-DEF POINTER (T21=+1,T20=+1):
      T19-T18=subclass  T17-T12=OFFSET  T11-T6=CODE-SEG  T5-T0=DATA-SEG

NULL WORD / DOUBLE NULL MECHANISM:
  DATA+POINTER+NULL = T23=+1,T22=0,T21=0,T20=0
  payload=0  → explicit null (plain nothing)
  payload≠0  → implicit null: load into Double Null stack
    T19-T18=stack-id(which of 9 stacks)
    T17-T12=qualifier tribble(construct kind)
    T11-T6=mapping-A(pattern to match)
    T5-T0=mapping-B(handler reference)
"""

import sys
from typing import List, Dict, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — TRIT / WORD ARITHMETIC  (unchanged from v0.1, solid foundation)
# ═══════════════════════════════════════════════════════════════════════════════

TRYTE_TRITS = 6
SHORT_TRITS = 12
WORD_TRITS  = 24

def _pow3(n: int) -> int: return 3 ** n

WORD_MAX  = (_pow3(WORD_TRITS)  - 1) // 2   #  141,214,768,240
WORD_MIN  = -WORD_MAX
SHORT_MAX = (_pow3(SHORT_TRITS) - 1) // 2   #  265,720
TRYTE_MAX = (_pow3(TRYTE_TRITS) - 1) // 2   #  364

def clamp_word(v: int) -> int:
    return max(WORD_MIN, min(WORD_MAX, v))

def to_trits(value: int, width: int) -> List[int]:
    """Integer → balanced ternary list, LSB first."""
    trits, v = [], value
    for _ in range(width):
        r = v % 3
        if r == 2: r = -1
        trits.append(r)
        v = (v - r) // 3
    return trits

def from_trits(trits: List[int]) -> int:
    """Balanced ternary list (LSB first) → integer."""
    return sum(t * _pow3(i) for i, t in enumerate(trits))

def get_trit(value: int, pos: int) -> int:
    """Extract trit at position pos (0=LSB) from integer value."""
    return to_trits(value, WORD_TRITS)[pos] if 0 <= pos < WORD_TRITS else 0

def set_trit(value: int, pos: int, trit: int) -> int:
    """Return new integer with trit at pos replaced."""
    t = to_trits(value, WORD_TRITS)
    if 0 <= pos < WORD_TRITS:
        t[pos] = max(-1, min(1, trit))
    return from_trits(t)

def get_field(value: int, lsb: int, width: int) -> int:
    """Extract a field of `width` trits starting at position `lsb`."""
    return from_trits(to_trits(value, WORD_TRITS)[lsb:lsb+width])

def set_field(value: int, lsb: int, width: int, field_val: int) -> int:
    """Return new integer with field of `width` trits at `lsb` set to field_val."""
    t = to_trits(value, WORD_TRITS)
    fv = to_trits(field_val, width)
    for i in range(width):
        t[lsb + i] = fv[i]
    return from_trits(t)

def word_to_str(value: int, width: int = WORD_TRITS) -> str:
    """Format as balanced ternary string, MSB first."""
    symbols = {-1: '-', 0: '0', 1: '+'}
    return ''.join(symbols[t] for t in reversed(to_trits(value, width)))

# ── Ternary-native operations ─────────────────────────────────────────────────

def trit_min(a: int, b: int) -> int:
    ta, tb = to_trits(a, WORD_TRITS), to_trits(b, WORD_TRITS)
    return from_trits([min(x,y) for x,y in zip(ta,tb)])

def trit_max(a: int, b: int) -> int:
    ta, tb = to_trits(a, WORD_TRITS), to_trits(b, WORD_TRITS)
    return from_trits([max(x,y) for x,y in zip(ta,tb)])

def trit_txor(a: int, b: int) -> int:
    ta, tb = to_trits(a, WORD_TRITS), to_trits(b, WORD_TRITS)
    def _t(x,y):
        r = (x+y) % 3
        return r if r != 2 else -1
    return from_trits([_t(x,y) for x,y in zip(ta,tb)])

def trit_equal(a: int, b: int) -> int:
    ta, tb = to_trits(a, WORD_TRITS), to_trits(b, WORD_TRITS)
    return from_trits([1 if x==y else -1 for x,y in zip(ta,tb)])

def trit_sum(a: int, b: int) -> int:
    ta, tb = to_trits(a, WORD_TRITS), to_trits(b, WORD_TRITS)
    return from_trits([max(-1,min(1,x+y)) for x,y in zip(ta,tb)])

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — TERNOO WORD ARCHITECTURE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Primary type tags (T23)
PRIMARY_EXEC = -1
PRIMARY_MAP  =  0
PRIMARY_DATA = +1

# DATA subtypes (T22)
DATA_SCALAR  = -1
DATA_POINTER =  0
DATA_STRING  = +1

# SCALAR encodings (T21)
SCALAR_FLOAT = -1
SCALAR_INT   =  0
SCALAR_UINT  = +1

# STRING encodings (T21)
STRING_UNICODE = -1
STRING_ASCII   =  0
STRING_TERNARY = +1

# POINTER models (T21, T20)
PTR_FLAT      = (-1, -1)   # direct memory address
PTR_RELATIVE  = (-1,  0)   # offset from PC
PTR_STACK_REL = (-1, +1)   # offset from SP
PTR_FIELD     = ( 0, -1)   # object base + field index
PTR_NULL      = ( 0,  0)   # null / undefined
PTR_SYMBOL    = ( 0, +1)   # interned symbol
PTR_REMOTE    = (+1, -1)   # P2PCP network node reference
PTR_WEAK      = (+1,  0)   # weak reference
PTR_USER_DEF  = (+1, +1)   # self-describing object word

# EXEC word qualifier fields (T22, T21, T20)
EXEC_PRIV_KERNEL  = -1
EXEC_PRIV_USER    =  0
EXEC_PRIV_SANDBOX = +1

EXEC_CALL_STACK    = -1
EXEC_CALL_REGISTER =  0
EXEC_CALL_MESSAGE  = +1

EXEC_RET_EXEC = -1
EXEC_RET_MAP  =  0
EXEC_RET_DATA = +1

# MAP word axis qualifier positions
MAP_AXIS_YZ = 22   # T22
MAP_AXIS_XZ = 21   # T21
MAP_AXIS_XY = 20   # T20

# Register assignments
REG_ZERO    =  0   # hardwired zero
REG_ARG_BASE =  1  # R1–R8 = argument registers
REG_ST_BASE = 45   # R45–R53 = Double Null stack pointers ST0–ST8
REG_DS_BASE = 54   # R54–R62 = data segment base registers DS0–DS8
REG_CS_BASE = 63   # R63–R71 = code segment base registers CS0–CS8
REG_RWR     = 78   # Reserved Word Register
REG_SP      = 79   # stack pointer
REG_LR      = 80   # link register

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — TERNOO WORD CONSTRUCTORS AND INSPECTORS
# ═══════════════════════════════════════════════════════════════════════════════

def build_exec_word(privilege: int, call_style: int, return_type: int,
                    seg_idx: int, offset: int,
                    arity: int = 0, arg_types: int = 0, version: int = 0) -> int:
    """
    Build an EXEC word (T23=−1).
    seg_idx: 0–8, selects CS0–CS8 (encoded as 2-trit field, range −4..+4)
    offset:  6-trit offset within code segment (range ±364)
    arity:   4-trit argument count
    arg_types: 4-trit argument type signature
    version:   4-trit version/generation tag
    """
    w = 0
    w = set_trit(w, 23, PRIMARY_EXEC)            # T23 = EXEC
    w = set_trit(w, 22, privilege)               # T22 = privilege
    w = set_trit(w, 21, call_style)              # T21 = call style
    w = set_trit(w, 20, return_type)             # T20 = return type
    # T19-T18: seg_idx as 2-trit balanced ternary (encodes 0–8 as −4..+4)
    w = set_field(w, 18, 2, seg_idx - 4)
    # T17-T12: 6-trit offset within segment
    w = set_field(w, 12, 6, offset)
    # T11-T8: 4-trit arity
    w = set_field(w, 8, 4, arity)
    # T7-T4: 4-trit argument types
    w = set_field(w, 4, 4, arg_types)
    # T3-T0: 4-trit version tag
    w = set_field(w, 0, 4, version)
    return w

def decode_exec_word(w: int) -> dict:
    """Decode an EXEC word into its component fields."""
    assert get_trit(w, 23) == PRIMARY_EXEC, "Not an EXEC word"
    seg_idx_raw = get_field(w, 18, 2)
    return {
        'type':        'EXEC',
        'privilege':   get_trit(w, 22),
        'call_style':  get_trit(w, 21),
        'return_type': get_trit(w, 20),
        'seg_idx':     seg_idx_raw + 4,      # back to 0–8
        'offset':      get_field(w, 12, 6),
        'arity':       get_field(w, 8, 4),
        'arg_types':   get_field(w, 4, 4),
        'version':     get_field(w, 0, 4),
    }

def build_map_word(axis_yz: int, axis_xz: int, axis_xy: int,
                   payload: int) -> int:
    """
    Build a MAP word (T23=0) encoding a 3D octree position.
    axis_yz/xz/xy: −1=negative, 0=on-plane, +1=positive
    payload: 20-trit coordinate value (interpretation depends on qualifier state)
    """
    w = 0
    w = set_trit(w, 23, PRIMARY_MAP)
    w = set_trit(w, 22, max(-1, min(1, axis_yz)))
    w = set_trit(w, 21, max(-1, min(1, axis_xz)))
    w = set_trit(w, 20, max(-1, min(1, axis_xy)))
    w = set_field(w, 0, 20, payload)
    return w

def decode_map_word(w: int) -> dict:
    """Decode a MAP word. Returns qualifier state and payload interpretation."""
    assert get_trit(w, 23) == PRIMARY_MAP, "Not a MAP word"
    yz = get_trit(w, 22)
    xz = get_trit(w, 21)
    xy = get_trit(w, 20)
    zeros = [yz, xz, xy].count(0)
    payload = get_field(w, 0, 20)

    if zeros == 3:
        mode = 'ORIGIN'
        coords = {'x': 0, 'y': 0, 'z': 0, 'scale': payload}
    elif zeros == 2:
        # On-axis: full 20-trit payload = 1D coordinate
        active = [('Y','Z')[i] for i,v in enumerate([yz,xz,xy]) if v != 0]
        mode = f'ON_AXIS_{active[0] if active else "?"}'
        coords = {'axis': active[0] if active else '?', 'value': payload}
    elif zeros == 1:
        # On-plane: payload splits 10+10 in alphabetical axis order
        mode = 'ON_PLANE'
        hi = get_field(w, 10, 10)
        lo = get_field(w, 0, 10)
        if yz == 0:   coords = {'Y': hi, 'Z': lo}
        elif xz == 0: coords = {'X': hi, 'Z': lo}
        else:         coords = {'X': hi, 'Y': lo}
    else:
        mode = 'ABSOLUTE_3D'
        # Payload subdivided: upper trits encode combined magnitude
        coords = {'axis_yz': yz, 'axis_xz': xz, 'axis_xy': xy,
                  'magnitude': payload}

    return {'type': 'MAP', 'mode': mode, 'axis_yz': yz, 'axis_xz': xz,
            'axis_xy': xy, 'payload': payload, 'coords': coords}

def build_scalar_word(encoding: int, value: int) -> int:
    """Build a DATA/SCALAR word."""
    w = 0
    w = set_trit(w, 23, PRIMARY_DATA)
    w = set_trit(w, 22, DATA_SCALAR)
    w = set_trit(w, 21, encoding)
    w = set_field(w, 0, 21, value)
    return w

def build_int_word(value: int) -> int:
    """Convenience: build a DATA/SCALAR/INTEGER word."""
    return build_scalar_word(SCALAR_INT, value)

def build_uint_word(value: int) -> int:
    """Convenience: build a DATA/SCALAR/UNSIGNED word."""
    return build_scalar_word(SCALAR_UINT, max(0, value))

def build_string_word(encoding: int, length_or_addr: int) -> int:
    """Build a DATA/STRING word."""
    w = 0
    w = set_trit(w, 23, PRIMARY_DATA)
    w = set_trit(w, 22, DATA_STRING)
    w = set_trit(w, 21, encoding)
    w = set_field(w, 0, 21, length_or_addr)
    return w

def build_pointer_word(model: Tuple[int,int], payload: int) -> int:
    """Build a DATA/POINTER word for models 1–8 (not USER-DEF)."""
    t21, t20 = model
    w = 0
    w = set_trit(w, 23, PRIMARY_DATA)
    w = set_trit(w, 22, DATA_POINTER)
    w = set_trit(w, 21, t21)
    w = set_trit(w, 20, t20)
    w = set_field(w, 0, 20, payload)
    return w

def build_null_word(payload: int = 0) -> int:
    """
    Build a NULL word.
    payload=0  → explicit null
    payload≠0  → implicit null (Double Null mechanism)
    """
    return build_pointer_word(PTR_NULL, payload)

def build_implicit_null(stack_id: int, qualifier: int,
                        mapping_a: int, mapping_b: int) -> int:
    """
    Build an IMPLICIT NULL word for the Double Null mechanism.
    stack_id: 0–8, selects which of the 9 Double Null stacks
    qualifier: 6-trit construct kind/type
    mapping_a: 6-trit pattern to recognise
    mapping_b: 6-trit handler reference
    """
    w = 0
    w = set_trit(w, 23, PRIMARY_DATA)
    w = set_trit(w, 22, DATA_POINTER)
    w = set_trit(w, 21, PTR_NULL[0])
    w = set_trit(w, 20, PTR_NULL[1])
    # payload ≠ 0 signals implicit null
    w = set_field(w, 18, 2, stack_id - 4)   # T19-T18: stack selector
    w = set_field(w, 12, 6, qualifier)       # T17-T12: qualifier tribble
    w = set_field(w, 6,  6, mapping_a)       # T11-T6:  mapping-A
    w = set_field(w, 0,  6, mapping_b)       # T5-T0:   mapping-B
    return w

def build_udp_word(subclass_t19: int, subclass_t18: int,
                   offset: int, code_seg: int, data_seg: int) -> int:
    """
    Build a USER-DEFINED POINTER word — the self-describing object word.
    subclass_t19, subclass_t18: −1/0/+1 each, together select 1 of 9 subclasses
    offset:   6-trit internal cursor (T17-T12), range ±364
    code_seg: 6-trit code segment reference (T11-T6), range ±364
    data_seg: 6-trit data segment reference (T5-T0), range ±364
    """
    w = 0
    w = set_trit(w, 23, PRIMARY_DATA)
    w = set_trit(w, 22, DATA_POINTER)
    w = set_trit(w, 21, PTR_USER_DEF[0])    # +1
    w = set_trit(w, 20, PTR_USER_DEF[1])    # +1
    w = set_trit(w, 19, max(-1,min(1,subclass_t19)))
    w = set_trit(w, 18, max(-1,min(1,subclass_t18)))
    w = set_field(w, 12, 6, offset)
    w = set_field(w, 6,  6, code_seg)
    w = set_field(w, 0,  6, data_seg)
    return w

def decode_udp_word(w: int) -> dict:
    """Decode a USER-DEFINED POINTER word."""
    return {
        'type':          'UDP',
        'subclass_t19':  get_trit(w, 19),
        'subclass_t18':  get_trit(w, 18),
        'offset':        get_field(w, 12, 6),
        'code_seg':      get_field(w, 6, 6),
        'data_seg':      get_field(w, 0, 6),
    }

def decode_word(w: int) -> dict:
    """Fully decode any TernOO word, returning a structured description."""
    primary = get_trit(w, 23)
    if primary == PRIMARY_EXEC:
        return decode_exec_word(w)
    elif primary == PRIMARY_MAP:
        return decode_map_word(w)
    else:  # PRIMARY_DATA
        subtype = get_trit(w, 22)
        if subtype == DATA_SCALAR:
            enc = get_trit(w, 21)
            enc_name = {SCALAR_FLOAT:'float',SCALAR_INT:'int',SCALAR_UINT:'uint'}.get(enc,'?')
            return {'type':'SCALAR','encoding':enc_name,'value':get_field(w,0,21)}
        elif subtype == DATA_STRING:
            enc = get_trit(w, 21)
            enc_name = {STRING_UNICODE:'unicode',STRING_ASCII:'ascii',
                        STRING_TERNARY:'ternary'}.get(enc,'?')
            return {'type':'STRING','encoding':enc_name,'length_or_addr':get_field(w,0,21)}
        else:  # DATA_POINTER
            t21,t20 = get_trit(w,21), get_trit(w,20)
            if (t21,t20) == PTR_USER_DEF:
                return decode_udp_word(w)
            elif (t21,t20) == PTR_NULL:
                payload = get_field(w, 0, 20)
                if payload == 0:
                    return {'type':'NULL','subtype':'explicit'}
                else:
                    sid = get_field(w,18,2) + 4
                    return {'type':'NULL','subtype':'implicit',
                            'stack_id':sid,
                            'qualifier':get_field(w,12,6),
                            'mapping_a':get_field(w,6,6),
                            'mapping_b':get_field(w,0,6)}
            else:
                model_names = {PTR_FLAT:'FLAT',PTR_RELATIVE:'RELATIVE',
                               PTR_STACK_REL:'STACK_REL',PTR_FIELD:'FIELD',
                               PTR_SYMBOL:'SYMBOL',PTR_REMOTE:'REMOTE',
                               PTR_WEAK:'WEAK'}
                return {'type':'POINTER',
                        'model':model_names.get((t21,t20),'?'),
                        'payload':get_field(w,0,20)}

def describe_word(w: int) -> str:
    """Return a human-readable one-line description of a TernOO word."""
    d = decode_word(w)
    t = d['type']
    if t == 'EXEC':
        priv = {-1:'kernel',0:'user',1:'sandbox'}.get(d['privilege'],'?')
        call = {-1:'stack',0:'register',1:'message'}.get(d['call_style'],'?')
        ret  = {-1:'EXEC',0:'MAP',1:'DATA'}.get(d['return_type'],'?')
        return (f"EXEC  priv={priv} call={call} ret={ret} "
                f"CS{d['seg_idx']}+{d['offset']} "
                f"arity={d['arity']} ver={d['version']}")
    elif t == 'MAP':
        return f"MAP   {d['mode']}  {d['coords']}  [{word_to_str(w)}]"
    elif t == 'SCALAR':
        return f"SCALAR({d['encoding']})  {d['value']}  [{word_to_str(w)}]"
    elif t == 'STRING':
        return f"STRING({d['encoding']})  len/addr={d['length_or_addr']}"
    elif t == 'POINTER':
        return f"PTR({d['model']})  payload={d['payload']}"
    elif t == 'UDP':
        sub = f"sub=({d['subclass_t19']},{d['subclass_t18']})"
        return (f"UDP  {sub} offset={d['offset']} "
                f"CS+{d['code_seg']} DS+{d['data_seg']}")
    elif t == 'NULL':
        if d['subtype'] == 'explicit':
            return "NULL (explicit)"
        else:
            return (f"NULL (implicit) stack={d['stack_id']} "
                    f"qual={d['qualifier']} A={d['mapping_a']} B={d['mapping_b']}")
    return f"UNKNOWN  [{word_to_str(w)}]"

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — OPCODE CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# ── 5500FP base ISA ──────────────────────────────────────────────────────────
OP_NOP   =  0;  OP_HLT   =  1;  OP_ADD   =  2;  OP_SUB   =  3
OP_MUL   =  4;  OP_DIV   =  5;  OP_NEG   =  6;  OP_MOV   =  7
OP_LDI   =  8;  OP_LD    =  9;  OP_ST    = 10;  OP_JMP   = 11
OP_JEQ   = 12;  OP_JNE   = 13;  OP_JB    = 14;  OP_JSR   = 15
OP_RTI   = 16;  OP_PUSH  = 17;  OP_POP   = 18;  OP_MIN   = 19
OP_MAX   = 20;  OP_TXOR  = 21;  OP_EQUAL = 22;  OP_SUM   = 23
OP_TTT   = 24;  OP_TTZ   = 25;  OP_TTP   = 26;  OP_ADDI  = 27
OP_SUBI  = 28;  OP_OUT   = 29;  OP_IN    = 30

# ── TernOO word opcodes ───────────────────────────────────────────────────────
OP_TOBJ     = 31   # TOBJ     Rd, Rs1, Rs2  — tag value in Rs1 with type in Rs2
OP_TGET     = 32   # TGET     Rd, Rs1       — get primary type trit of Rs1
OP_TPAYLOAD = 33   # TPAYLOAD Rd, Rs1       — strip primary tag, get payload
OP_TCALL    = 34   # TCALL    Rd,Rs1,Rs2,Rs3 — three-way dispatch on primary type
OP_TNEW     = 35   # TNEW     Rd, Rs1, Rs2  — allocate typed object on heap
OP_TBUILD   = 36   # TBUILD   Rd, Rs1       — decode word in Rs1, store summary in Rd
OP_TSEG     = 37   # TSEG     Rd, Rs1       — resolve EXEC word in Rs1 to full address

# ── TernOO renderer opcodes ───────────────────────────────────────────────────
OP_RPOINT  = 38   # RPOINT  Rd, Rs1, Rs2          — render point
OP_RLINE   = 39   # RLINE   Rd, Rs1, Rs2, Rs3     — render line segment
OP_RNODE   = 40   # RNODE   Rd, Rs1, Rs2, Rs3, Rs4 — render flowchart node
OP_REDGE   = -1   # REDGE   Rd, Rs1, Rs2, Rs3     — render directed edge
OP_RENDER  = -2   # RENDER  Rs1, Rs2              — commit canvas to display

HEAP_BASE   = 3**12 // 2
MEMORY_SIZE = 3**12

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — CPU
# ═══════════════════════════════════════════════════════════════════════════════

class CPU5500FP:
    """
    5500FP + TernOO v0.2 processor emulator.
    Implements the full TernOO word architecture with segment registers,
    Double Null mechanism, and renderer opcodes.
    """

    NUM_REGS = 81

    def __init__(self, memory_size: int = MEMORY_SIZE):
        self.memory   = [0] * memory_size
        self._trace   = False
        self.canvas: List[dict] = []    # renderer scene graph
        self.reset()

    def reset(self):
        self.regs        = [0] * self.NUM_REGS
        self.pc          = 0
        self.halted      = False
        self.call_stack: List[int] = []
        self.cycle_count = 0
        self._heap_ptr   = HEAP_BASE
        # Double Null stacks — each is a list (stack grows by append)
        self._dn_stacks: List[List[dict]] = [[] for _ in range(9)]
        self.canvas      = []

    # ── Register access ───────────────────────────────────────────────────────

    def read_reg(self, r: int) -> int:
        return 0 if r == 0 else self.regs[r % self.NUM_REGS]

    def write_reg(self, r: int, value: int):
        if r != 0:
            self.regs[r % self.NUM_REGS] = clamp_word(value)

    # ── Segment register helpers ──────────────────────────────────────────────

    def read_cs(self, idx: int) -> int:
        """Read code segment base register CS{idx} (0–8) → full 24-trit address."""
        return self.read_reg(REG_CS_BASE + idx)

    def write_cs(self, idx: int, addr: int):
        self.write_reg(REG_CS_BASE + idx, addr)

    def read_ds(self, idx: int) -> int:
        """Read data segment base register DS{idx} (0–8) → full 24-trit address."""
        return self.read_reg(REG_DS_BASE + idx)

    def write_ds(self, idx: int, addr: int):
        self.write_reg(REG_DS_BASE + idx, addr)

    def resolve_exec(self, exec_word: int) -> int:
        """Resolve an EXEC word to its full memory address via segment registers."""
        d = decode_exec_word(exec_word)
        base = self.read_cs(d['seg_idx'])
        return base + d['offset']

    def resolve_udp_code(self, udp_word: int) -> int:
        """Resolve UDP word CODE-SEG to full address via CS0."""
        d = decode_udp_word(udp_word)
        # By convention UDP code_seg resolves against CS0 unless subclass says otherwise
        return self.read_cs(0) + d['code_seg']

    def resolve_udp_data(self, udp_word: int) -> int:
        """Resolve UDP word DATA-SEG to full address via DS0."""
        d = decode_udp_word(udp_word)
        return self.read_ds(0) + d['data_seg']

    # ── Memory access ─────────────────────────────────────────────────────────

    def mem_read(self, addr: int) -> int:
        if 0 <= addr < len(self.memory):
            return self.memory[addr]
        raise MemoryError(f"Read OOB: addr={addr}")

    def mem_write(self, addr: int, value: int):
        if 0 <= addr < len(self.memory):
            self.memory[addr] = clamp_word(value)
        else:
            raise MemoryError(f"Write OOB: addr={addr}")

    def _heap_alloc(self, size: int) -> int:
        size = max(1, size)
        addr = self._heap_ptr
        self._heap_ptr += size
        if self._heap_ptr >= len(self.memory):
            raise MemoryError("Heap exhausted")
        return addr

    # ── Instruction assembly helpers ──────────────────────────────────────────

    def _encode_reg(self, r: int) -> int: return r - 40
    def _decode_reg(self, f: int) -> int: return f + 40

    def _fields(self, instr: int):
        t = to_trits(instr, WORD_TRITS)
        return [from_trits(t[i*4:(i+1)*4]) for i in range(6)]

    def _regs_A(self, instr: int):
        f = self._fields(instr)
        return (self._decode_reg(f[0]), self._decode_reg(f[1]),
                self._decode_reg(f[2]), self._decode_reg(f[3]),
                self._decode_reg(f[4]))

    def _imm_J2(self, instr: int):
        f = self._fields(instr)
        rd   = self._decode_reg(f[0])
        rs1  = self._decode_reg(f[1])
        imm  = from_trits(to_trits(f[2], 4) + to_trits(f[3], 4) + to_trits(f[4], 4))
        return rd, rs1, imm

    def _imm_J(self, instr: int):
        f = self._fields(instr)
        return from_trits(to_trits(f[0],4)+to_trits(f[1],4)+to_trits(f[2],4)
                         +to_trits(f[3],4)+to_trits(f[4],4))

    def assemble_A(self, op: int, rd: int, rs1: int,
                   rs2: int = 40, rs3: int = 40, rs4: int = 40) -> int:
        t = (to_trits(self._encode_reg(rd),  4) +
             to_trits(self._encode_reg(rs1), 4) +
             to_trits(self._encode_reg(rs2), 4) +
             to_trits(self._encode_reg(rs3), 4) +
             to_trits(self._encode_reg(rs4), 4) +
             to_trits(op,                    4))
        return from_trits(t)

    def assemble_J2(self, op: int, rd: int, rs1: int, imm: int) -> int:
        imm_t = to_trits(imm, 12)
        t = (to_trits(self._encode_reg(rd),  4) +
             to_trits(self._encode_reg(rs1), 4) +
             imm_t +
             to_trits(op,                    4))
        return from_trits(t)

    def assemble_J(self, op: int, imm: int) -> int:
        t = to_trits(imm, 20) + to_trits(op, 4)
        return from_trits(t)

    def load_program(self, program: List[int], start: int = 0):
        for i, word in enumerate(program):
            self.mem_write(start + i, word)
        self.pc = start

    # ── Execute ───────────────────────────────────────────────────────────────

    def fetch(self) -> int:
        instr = self.mem_read(self.pc)
        self.pc += 1
        return instr

    def execute(self, instr: int):
        f = self._fields(instr)
        op = f[5]   # opcode in F5 (MSB field)

        if self._trace:
            print(f"  PC={self.pc-1:4d} op={op:3d} [{word_to_str(instr)}]")

        # ── Base ISA ─────────────────────────────────────────────────────────
        if   op == OP_NOP: pass
        elif op == OP_HLT: self.halted = True

        elif op == OP_ADD:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            self.write_reg(rd, self.read_reg(rs1) + self.read_reg(rs2))
        elif op == OP_ADDI:
            rd,rs1,imm = self._imm_J2(instr)
            self.write_reg(rd, self.read_reg(rs1) + imm)
        elif op == OP_SUB:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            self.write_reg(rd, self.read_reg(rs1) - self.read_reg(rs2))
        elif op == OP_SUBI:
            rd,rs1,imm = self._imm_J2(instr)
            self.write_reg(rd, self.read_reg(rs1) - imm)
        elif op == OP_MUL:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            self.write_reg(rd, self.read_reg(rs1) * self.read_reg(rs2))
        elif op == OP_DIV:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            d = self.read_reg(rs2)
            if d == 0: raise ZeroDivisionError("DIV by zero")
            self.write_reg(rd, int(self.read_reg(rs1) / d))
        elif op == OP_NEG:
            rd,rs1,*_ = self._regs_A(instr)
            self.write_reg(rd, -self.read_reg(rs1))
        elif op == OP_MOV:
            rd,rs1,*_ = self._regs_A(instr)
            self.write_reg(rd, self.read_reg(rs1))
        elif op == OP_LDI:
            rd,_,imm = self._imm_J2(instr)
            self.write_reg(rd, imm)
        elif op == OP_LD:
            rd,rs1,*_ = self._regs_A(instr)
            self.write_reg(rd, self.mem_read(self.read_reg(rs1)))
        elif op == OP_ST:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            self.mem_write(self.read_reg(rs2), self.read_reg(rd))
        elif op == OP_JMP:
            self.pc = self._imm_J(instr)
        elif op == OP_JSR:
            self.write_reg(REG_LR, self.pc)
            self.call_stack.append(self.pc)
            self.pc = self._imm_J(instr)
        elif op == OP_RTI:
            if self.call_stack: self.pc = self.call_stack.pop()
            else: raise RuntimeError("RTI with empty call stack")
        elif op == OP_JEQ:
            rd,rs1,imm = self._imm_J2(instr)
            if self.read_reg(rd) == self.read_reg(rs1): self.pc += imm
        elif op == OP_JNE:
            rd,rs1,imm = self._imm_J2(instr)
            if self.read_reg(rd) != self.read_reg(rs1): self.pc += imm
        elif op == OP_JB:
            rd,rs1,imm = self._imm_J2(instr)
            if self.read_reg(rd) < self.read_reg(rs1): self.pc += imm
        elif op == OP_PUSH:
            rd,*_ = self._regs_A(instr)
            sp = self.read_reg(REG_SP)
            self.mem_write(sp, self.read_reg(rd))
            self.write_reg(REG_SP, sp - 1)
        elif op == OP_POP:
            rd,*_ = self._regs_A(instr)
            sp = self.read_reg(REG_SP) + 1
            self.write_reg(REG_SP, sp)
            self.write_reg(rd, self.mem_read(sp))

        # ── Ternary-native ────────────────────────────────────────────────────
        elif op == OP_MIN:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            self.write_reg(rd, trit_min(self.read_reg(rs1), self.read_reg(rs2)))
        elif op == OP_MAX:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            self.write_reg(rd, trit_max(self.read_reg(rs1), self.read_reg(rs2)))
        elif op == OP_TXOR:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            self.write_reg(rd, trit_txor(self.read_reg(rs1), self.read_reg(rs2)))
        elif op == OP_EQUAL:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            self.write_reg(rd, trit_equal(self.read_reg(rs1), self.read_reg(rs2)))
        elif op == OP_SUM:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            self.write_reg(rd, trit_sum(self.read_reg(rs1), self.read_reg(rs2)))
        elif op in (OP_TTT, OP_TTZ, OP_TTP):
            rd,rs1,imm = self._imm_J2(instr)
            pos = self.read_reg(rs1)
            t = get_trit(self.read_reg(rd), pos)
            if op==OP_TTT and t==-1: self.pc += imm
            elif op==OP_TTZ and t== 0: self.pc += imm
            elif op==OP_TTP and t==+1: self.pc += imm

        # ── TernOO word opcodes ───────────────────────────────────────────────
        elif op == OP_TOBJ:
            # Tag value in Rs1 with primary type from Rs2, store in Rd
            rd,rs1,rs2,*_ = self._regs_A(instr)
            val = self.read_reg(rs1)
            tag = max(-1, min(1, self.read_reg(rs2)))
            result = set_trit(val, 23, tag)
            self.write_reg(rd, result)

        elif op == OP_TGET:
            # Get primary type trit (T23) of Rs1
            rd,rs1,*_ = self._regs_A(instr)
            self.write_reg(rd, get_trit(self.read_reg(rs1), 23))

        elif op == OP_TPAYLOAD:
            # Strip primary type tag, return remaining 23 trits
            rd,rs1,*_ = self._regs_A(instr)
            self.write_reg(rd, set_trit(self.read_reg(rs1), 23, 0))

        elif op == OP_TCALL:
            # Three-way dispatch on primary type of Rd
            # EXEC(-1)→Rs1, MAP(0)→Rs2, DATA(+1)→Rs3
            rd,rs1,rs2,rs3,_ = self._regs_A(instr)
            tag = get_trit(self.read_reg(rd), 23)
            self.call_stack.append(self.pc)
            self.write_reg(REG_LR, self.pc)
            if   tag == -1: self.pc = self.read_reg(rs1)
            elif tag ==  0: self.pc = self.read_reg(rs2)
            elif tag == +1: self.pc = self.read_reg(rs3)

        elif op == OP_TNEW:
            # Allocate typed object on heap
            rd,rs1,rs2,*_ = self._regs_A(instr)
            tag  = max(-1, min(1, self.read_reg(rs1)))
            size = max(1, self.read_reg(rs2))
            addr = self._heap_alloc(size)
            self.write_reg(rd, set_trit(addr, 23, tag))

        elif op == OP_TBUILD:
            # Build a UDP word: Rs1=code_seg_offset, Rs2=data_seg_offset
            # Stores the constructed word in Rd
            rd,rs1,rs2,rs3,_ = self._regs_A(instr)
            cs  = self.read_reg(rs1)
            ds  = self.read_reg(rs2)
            off = self.read_reg(rs3)
            self.write_reg(rd, build_udp_word(0, 0, off, cs, ds))

        elif op == OP_TSEG:
            # Resolve EXEC word in Rs1 to full absolute address using segment registers
            rd,rs1,*_ = self._regs_A(instr)
            exec_word = self.read_reg(rs1)
            if get_trit(exec_word, 23) == PRIMARY_EXEC:
                self.write_reg(rd, self.resolve_exec(exec_word))
            else:
                self.write_reg(rd, exec_word)  # pass-through if not EXEC

        # ── Double Null mechanism ─────────────────────────────────────────────
        # Handled at word-stream level below; the CPU detects NULL words
        # during execution and processes them via _handle_null()

        # ── Renderer opcodes ─────────────────────────────────────────────────
        elif op == OP_RPOINT:
            rd,rs1,rs2,*_ = self._regs_A(instr)
            pos_word   = self.read_reg(rs1)
            colour_word= self.read_reg(rs2)
            entry = {
                'prim':   'POINT',
                'pos':    decode_map_word(pos_word) if get_trit(pos_word,23)==0
                          else {'payload': pos_word},
                'colour': get_field(colour_word, 0, 21),
                'dirty':  True,
                'addr':   len(self.canvas)
            }
            self.canvas.append(entry)
            self.write_reg(rd, len(self.canvas) - 1)

        elif op == OP_RLINE:
            rd,rs1,rs2,rs3,_ = self._regs_A(instr)
            entry = {
                'prim':   'LINE',
                'start':  decode_map_word(self.read_reg(rs1))
                          if get_trit(self.read_reg(rs1),23)==0
                          else {'payload': self.read_reg(rs1)},
                'end':    decode_map_word(self.read_reg(rs2))
                          if get_trit(self.read_reg(rs2),23)==0
                          else {'payload': self.read_reg(rs2)},
                'style':  self.read_reg(rs3),
                'dirty':  True,
                'addr':   len(self.canvas)
            }
            self.canvas.append(entry)
            self.write_reg(rd, len(self.canvas) - 1)

        elif op == OP_RNODE:
            rd,rs1,rs2,rs3,rs4 = self._regs_A(instr)
            style_word = self.read_reg(rs3)
            shape_enc  = get_trit(style_word, 21)  # uses SCALAR subtype trit
            shape = {SCALAR_INT:'rect', SCALAR_FLOAT:'diamond',
                     SCALAR_UINT:'rounded'}.get(shape_enc, 'rect')
            entry = {
                'prim':   'NODE',
                'pos':    decode_map_word(self.read_reg(rs1))
                          if get_trit(self.read_reg(rs1),23)==0
                          else {'payload': self.read_reg(rs1)},
                'dims':   self.read_reg(rs2),
                'shape':  shape,
                'object': decode_udp_word(self.read_reg(rs4))
                          if (get_trit(self.read_reg(rs4),21)==1 and
                              get_trit(self.read_reg(rs4),20)==1)
                          else {'raw': self.read_reg(rs4)},
                'dirty':  True,
                'addr':   len(self.canvas)
            }
            self.canvas.append(entry)
            self.write_reg(rd, len(self.canvas) - 1)

        elif op == OP_REDGE:
            rd,rs1,rs2,rs3,_ = self._regs_A(instr)
            exec_word = self.read_reg(rs3)
            call_style = get_trit(exec_word, 21) if get_trit(exec_word,23)==-1 else 0
            arrow = {-1:'double', 0:'single', 1:'dashed'}.get(call_style, 'single')
            entry = {
                'prim':   'EDGE',
                'src':    self.read_reg(rs1),
                'dst':    self.read_reg(rs2),
                'exec':   decode_exec_word(exec_word)
                          if get_trit(exec_word,23)==-1 else {'raw':exec_word},
                'arrow':  arrow,
                'dirty':  True,
                'addr':   len(self.canvas)
            }
            self.canvas.append(entry)
            self.write_reg(rd, len(self.canvas) - 1)

        elif op == OP_RENDER:
            rd,rs1,*_ = self._regs_A(instr)
            self._render_canvas()

        # ── I/O ───────────────────────────────────────────────────────────────
        elif op == OP_OUT:
            rd,*_ = self._regs_A(instr)
            val = self.read_reg(rd)
            print(f"OUT R{rd} = {val}  [{word_to_str(val)}]")
        elif op == OP_IN:
            rd,*_ = self._regs_A(instr)
            try: self.write_reg(rd, int(input("IN> ")))
            except: self.write_reg(rd, 0)

        else:
            raise RuntimeError(f"Unknown opcode {op} at PC={self.pc-1}")

        self.cycle_count += 1

    def _handle_null(self, word: int):
        """Process a NULL word through the Double Null mechanism."""
        d = decode_word(word)
        if d['type'] == 'NULL' and d['subtype'] == 'implicit':
            sid = d['stack_id']
            context = {
                'qualifier': d['qualifier'],
                'mapping_a': d['mapping_a'],
                'mapping_b': d['mapping_b'],
                'word':      word
            }
            self._dn_stacks[sid].append(context)
            self.write_reg(REG_RWR, word)   # update RWR with latest context
            if self._trace:
                print(f"  [Double Null] push stack {sid}: {context}")

    def _render_canvas(self):
        """Terminal renderer — renders dirty canvas entries as ASCII art."""
        dirty = [e for e in self.canvas if e.get('dirty')]
        if not dirty:
            return
        print("\n╔══ CANVAS (" + "="*40 + "╗")
        for entry in dirty:
            p = entry['prim']
            if p == 'POINT':
                c = entry.get('pos',{}).get('payload',0)
                print(f"║  POINT   coord={c}  colour={entry.get('colour',0)}")
            elif p == 'LINE':
                s = entry.get('start',{}).get('payload',0)
                e2 = entry.get('end',{}).get('payload',0)
                print(f"║  LINE    {s} ─────────→ {e2}")
            elif p == 'NODE':
                shape = entry.get('shape','rect')
                pos   = entry.get('pos',{}).get('payload',0)
                obj   = entry.get('object',{})
                shapes = {'rect':'[   ]', 'diamond':'<   >', 'rounded':'(   )'}
                print(f"║  NODE    {shapes.get(shape,'[   ]')} "
                      f"@{pos}  "
                      f"CS+{obj.get('code_seg','?')} "
                      f"DS+{obj.get('data_seg','?')}")
            elif p == 'EDGE':
                src  = entry.get('src', 0)
                dst  = entry.get('dst', 0)
                arr  = entry.get('arrow','single')
                arrows = {'single':'──→','double':'══►','dashed':'╌╌→'}
                print(f"║  EDGE    node[{src}] {arrows.get(arr,'──→')} node[{dst}]")
            entry['dirty'] = False
        print("╚" + "═"*51 + "╝\n")

    def run(self, max_cycles: int = 1_000_000):
        while not self.halted and self.cycle_count < max_cycles:
            instr = self.fetch()
            # Check for NULL words to process through Double Null mechanism
            if (get_trit(instr,23)==PRIMARY_DATA and
                get_trit(instr,22)==DATA_POINTER and
                get_trit(instr,21)==PTR_NULL[0] and
                get_trit(instr,20)==PTR_NULL[1]):
                self._handle_null(instr)
            self.execute(instr)
        if self.cycle_count >= max_cycles:
            print(f"[WARN] Cycle limit reached ({max_cycles})")

    def dump_regs(self, count: int = 16):
        print(f"\n── Registers (PC={self.pc}, cycles={self.cycle_count}) ──")
        for i in range(min(count, self.NUM_REGS)):
            v = self.read_reg(i)
            if v != 0:
                print(f"  R{i:2d} = {v:15d}  {word_to_str(v)}")
        print()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — ASSEMBLER HELPER
# ═══════════════════════════════════════════════════════════════════════════════

class Asm:
    """Convenience assembler. Usage: a = Asm(cpu); program = [a.LDI(1,42), ...]"""
    def __init__(self, cpu: CPU5500FP): self.cpu = cpu
    def NOP(self)                         -> int: return self.cpu.assemble_A(OP_NOP,0,0)
    def HLT(self)                         -> int: return self.cpu.assemble_A(OP_HLT,0,0)
    def ADD(self,rd,rs1,rs2)              -> int: return self.cpu.assemble_A(OP_ADD,rd,rs1,rs2)
    def ADDI(self,rd,rs1,imm)             -> int: return self.cpu.assemble_J2(OP_ADDI,rd,rs1,imm)
    def SUB(self,rd,rs1,rs2)              -> int: return self.cpu.assemble_A(OP_SUB,rd,rs1,rs2)
    def SUBI(self,rd,rs1,imm)             -> int: return self.cpu.assemble_J2(OP_SUBI,rd,rs1,imm)
    def MUL(self,rd,rs1,rs2)              -> int: return self.cpu.assemble_A(OP_MUL,rd,rs1,rs2)
    def DIV(self,rd,rs1,rs2)              -> int: return self.cpu.assemble_A(OP_DIV,rd,rs1,rs2)
    def NEG(self,rd,rs1)                  -> int: return self.cpu.assemble_A(OP_NEG,rd,rs1)
    def MOV(self,rd,rs1)                  -> int: return self.cpu.assemble_A(OP_MOV,rd,rs1)
    def LDI(self,rd,imm)                  -> int: return self.cpu.assemble_J2(OP_LDI,rd,0,imm)
    def LD(self,rd,rs1)                   -> int: return self.cpu.assemble_A(OP_LD,rd,rs1)
    def ST(self,rs1,rs2)                  -> int: return self.cpu.assemble_A(OP_ST,rs1,rs1,rs2)
    def JMP(self,addr)                    -> int: return self.cpu.assemble_J(OP_JMP,addr)
    def JSR(self,addr)                    -> int: return self.cpu.assemble_J(OP_JSR,addr)
    def RTI(self)                         -> int: return self.cpu.assemble_A(OP_RTI,0,0)
    def JEQ(self,rd,rs1,off)              -> int: return self.cpu.assemble_J2(OP_JEQ,rd,rs1,off)
    def JNE(self,rd,rs1,off)              -> int: return self.cpu.assemble_J2(OP_JNE,rd,rs1,off)
    def JB(self,rd,rs1,off)               -> int: return self.cpu.assemble_J2(OP_JB,rd,rs1,off)
    def PUSH(self,rs1)                    -> int: return self.cpu.assemble_A(OP_PUSH,rs1,0)
    def POP(self,rd)                      -> int: return self.cpu.assemble_A(OP_POP,rd,0)
    def MIN(self,rd,rs1,rs2)              -> int: return self.cpu.assemble_A(OP_MIN,rd,rs1,rs2)
    def MAX(self,rd,rs1,rs2)              -> int: return self.cpu.assemble_A(OP_MAX,rd,rs1,rs2)
    def TXOR(self,rd,rs1,rs2)             -> int: return self.cpu.assemble_A(OP_TXOR,rd,rs1,rs2)
    def EQUAL(self,rd,rs1,rs2)            -> int: return self.cpu.assemble_A(OP_EQUAL,rd,rs1,rs2)
    def SUM(self,rd,rs1,rs2)              -> int: return self.cpu.assemble_A(OP_SUM,rd,rs1,rs2)
    def OUT(self,rs1)                     -> int: return self.cpu.assemble_A(OP_OUT,rs1,0)
    def IN(self,rd)                       -> int: return self.cpu.assemble_A(OP_IN,rd,0)
    # TernOO word opcodes
    def TOBJ(self,rd,rs1,rs2)             -> int: return self.cpu.assemble_A(OP_TOBJ,rd,rs1,rs2)
    def TGET(self,rd,rs1)                 -> int: return self.cpu.assemble_A(OP_TGET,rd,rs1)
    def TPAYLOAD(self,rd,rs1)             -> int: return self.cpu.assemble_A(OP_TPAYLOAD,rd,rs1)
    def TCALL(self,rd,rs1,rs2,rs3)        -> int: return self.cpu.assemble_A(OP_TCALL,rd,rs1,rs2,rs3)
    def TNEW(self,rd,rs1,rs2)             -> int: return self.cpu.assemble_A(OP_TNEW,rd,rs1,rs2)
    def TBUILD(self,rd,rs1,rs2,rs3)       -> int: return self.cpu.assemble_A(OP_TBUILD,rd,rs1,rs2,rs3)
    def TSEG(self,rd,rs1)                 -> int: return self.cpu.assemble_A(OP_TSEG,rd,rs1)
    # Renderer opcodes
    def RPOINT(self,rd,rs1,rs2)           -> int: return self.cpu.assemble_A(OP_RPOINT,rd,rs1,rs2)
    def RLINE(self,rd,rs1,rs2,rs3)        -> int: return self.cpu.assemble_A(OP_RLINE,rd,rs1,rs2,rs3)
    def RNODE(self,rd,rs1,rs2,rs3,rs4)    -> int: return self.cpu.assemble_A(OP_RNODE,rd,rs1,rs2,rs3,rs4)
    def REDGE(self,rd,rs1,rs2,rs3)        -> int: return self.cpu.assemble_A(OP_REDGE,rd,rs1,rs2,rs3)
    def RENDER(self,rs1,rs2)              -> int: return self.cpu.assemble_A(OP_RENDER,rs1,rs2)

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — TESTS
# ═══════════════════════════════════════════════════════════════════════════════

def test_word_constructors():
    print("="*60)
    print("TEST: TernOO word constructors and inspector")
    print("="*60)

    # EXEC word
    ew = build_exec_word(EXEC_PRIV_USER, EXEC_CALL_REGISTER, EXEC_RET_DATA,
                         seg_idx=2, offset=14, arity=2, version=1)
    d = decode_exec_word(ew)
    assert d['privilege']   == EXEC_PRIV_USER
    assert d['call_style']  == EXEC_CALL_REGISTER
    assert d['return_type'] == EXEC_RET_DATA
    assert d['seg_idx']     == 2
    assert d['offset']      == 14
    assert d['arity']       == 2
    assert d['version']     == 1
    assert get_trit(ew, 23) == PRIMARY_EXEC
    print(f"  EXEC: {describe_word(ew)}")
    print("  EXEC word: PASS")

    # MAP word — absolute 3D
    mw = build_map_word(+1, -1, +1, 42)
    d  = decode_map_word(mw)
    assert d['axis_yz'] == +1
    assert d['axis_xz'] == -1
    assert d['axis_xy'] == +1
    assert d['payload'] == 42
    print(f"  MAP:  {describe_word(mw)}")
    print("  MAP word: PASS")

    # MAP word — origin (all zeros)
    mw0 = build_map_word(0, 0, 0, 100)
    d0  = decode_map_word(mw0)
    assert d0['mode'] == 'ORIGIN'
    assert d0['coords']['scale'] == 100
    print(f"  MAP (origin): {describe_word(mw0)}")

    # MAP word — on YZ-plane
    mw_plane = build_map_word(0, +1, -1, 0)
    d_plane  = decode_map_word(mw_plane)
    assert d_plane['mode'] == 'ON_PLANE'
    print(f"  MAP (on-plane): {describe_word(mw_plane)}")
    print("  MAP variants: PASS")

    # SCALAR word
    sw = build_int_word(42)
    d  = decode_word(sw)
    assert d['type']  == 'SCALAR'
    assert d['value'] == 42
    assert get_trit(sw, 23) == PRIMARY_DATA
    print(f"  SCALAR: {describe_word(sw)}")
    print("  SCALAR word: PASS")

    # UDP word
    udp = build_udp_word(0, 0, offset=7, code_seg=3, data_seg=12)
    d   = decode_udp_word(udp)
    assert d['offset']   == 7
    assert d['code_seg'] == 3
    assert d['data_seg'] == 12
    print(f"  UDP:  {describe_word(udp)}")
    print("  UDP word: PASS")

    # NULL words
    null_e = build_null_word(0)
    null_i = build_implicit_null(stack_id=3, qualifier=10, mapping_a=5, mapping_b=2)
    de = decode_word(null_e)
    di = decode_word(null_i)
    assert de['subtype'] == 'explicit'
    assert di['subtype'] == 'implicit'
    assert di['stack_id'] == 3
    print(f"  NULL explicit: {describe_word(null_e)}")
    print(f"  NULL implicit: {describe_word(null_i)}")
    print("  NULL words: PASS\n")

def test_segment_registers():
    print("="*60)
    print("TEST: Segment registers and EXEC resolution")
    print("="*60)

    cpu = CPU5500FP()
    a   = Asm(cpu)

    # Set CS2 base to address 1000
    cpu.write_cs(2, 1000)
    assert cpu.read_cs(2) == 1000

    # Build an EXEC word targeting CS2 + offset 14
    ew = build_exec_word(EXEC_PRIV_USER, EXEC_CALL_REGISTER, EXEC_RET_DATA,
                         seg_idx=2, offset=14)
    resolved = cpu.resolve_exec(ew)
    assert resolved == 1014, f"Expected 1014, got {resolved}"
    print(f"  CS2=1000, offset=14 → resolved={resolved}")

    # Test TSEG opcode
    prog = [
        a.HLT(),
    ]
    cpu.load_program(prog)
    cpu.write_reg(10, ew)       # R10 = EXEC word
    cpu.write_cs(2, 1000)
    # Manually invoke TSEG
    tseg_instr = a.TSEG(11, 10)
    cpu.pc = 0
    cpu.mem_write(0, tseg_instr)
    cpu.mem_write(1, cpu.assemble_A(OP_HLT, 0, 0))
    cpu.run()
    assert cpu.read_reg(11) == 1014, f"TSEG: expected 1014, got {cpu.read_reg(11)}"
    print(f"  TSEG opcode: R10(EXEC) → R11={cpu.read_reg(11)}")
    print("  Segment registers: PASS\n")

def test_double_null():
    print("="*60)
    print("TEST: Double Null mechanism")
    print("="*60)

    cpu = CPU5500FP()
    a   = Asm(cpu)

    # Build an implicit null targeting stack 3
    inull = build_implicit_null(stack_id=3, qualifier=10, mapping_a=5, mapping_b=2)
    assert decode_word(inull)['subtype'] == 'implicit'

    # Load it into memory and run — CPU should push it onto stack 3
    cpu.mem_write(0, inull)
    cpu.mem_write(1, cpu.assemble_A(OP_HLT, 0, 0))
    cpu.pc = 0
    cpu.run()

    assert len(cpu._dn_stacks[3]) == 1
    ctx = cpu._dn_stacks[3][0]
    assert ctx['qualifier'] == 10
    assert ctx['mapping_a'] == 5
    assert ctx['mapping_b'] == 2
    print(f"  Stack 3 after implicit null: {ctx}")

    # RWR should be loaded with the implicit null word
    assert cpu.read_reg(REG_RWR) == inull
    print(f"  RWR loaded: {describe_word(cpu.read_reg(REG_RWR))}")
    print("  Double Null: PASS\n")

def test_renderer():
    print("="*60)
    print("TEST: Renderer opcodes and terminal display")
    print("="*60)

    cpu = CPU5500FP()
    a   = Asm(cpu)

    # Build words for two nodes and one edge
    node_a_pos  = build_map_word(0, 0, 0, 100)   # origin-relative, coord=100
    node_b_pos  = build_map_word(0, 0, 0, 300)   # coord=300
    node_dims   = build_int_word(80)
    node_a_style= build_scalar_word(SCALAR_INT,   0)  # rectangle
    node_b_style= build_scalar_word(SCALAR_FLOAT, 0)  # diamond
    node_a_obj  = build_udp_word(0, 0, offset=0, code_seg=1, data_seg=1)
    node_b_obj  = build_udp_word(0, 0, offset=0, code_seg=2, data_seg=2)
    edge_exec   = build_exec_word(EXEC_PRIV_USER, EXEC_CALL_REGISTER,
                                  EXEC_RET_DATA, seg_idx=0, offset=5)

    # Load words into registers
    cpu.write_reg(1,  node_a_pos)
    cpu.write_reg(2,  node_dims)
    cpu.write_reg(3,  node_a_style)
    cpu.write_reg(4,  node_a_obj)
    cpu.write_reg(5,  node_b_pos)
    cpu.write_reg(6,  node_b_style)
    cpu.write_reg(7,  node_b_obj)
    cpu.write_reg(8,  edge_exec)
    cpu.write_reg(9,  build_int_word(0))  # colour placeholder

    prog = [
        a.RNODE(20, 1, 2, 3, 4),      # render node A → canvas addr in R20
        a.RNODE(21, 5, 2, 6, 7),      # render node B → canvas addr in R21
        a.REDGE(22, 20, 21, 8),        # render edge A→B using EXEC word in R8
        a.RENDER(20, 9),               # commit canvas to display
        a.HLT(),
    ]
    cpu.load_program(prog)
    cpu.run()

    assert len(cpu.canvas) == 3
    assert cpu.canvas[0]['prim'] == 'NODE'
    assert cpu.canvas[1]['prim'] == 'NODE'
    assert cpu.canvas[2]['prim'] == 'EDGE'
    assert cpu.canvas[0]['shape'] == 'rect'
    assert cpu.canvas[1]['shape'] == 'diamond'
    print("  Canvas has 3 entries: NODE(rect), NODE(diamond), EDGE")
    print("  Renderer: PASS\n")

def test_basic_arithmetic():
    print("="*60)
    print("TEST: Basic arithmetic (regression from v0.1)")
    print("="*60)
    cpu = CPU5500FP()
    a   = Asm(cpu)
    prog = [
        a.LDI(1, 42), a.LDI(2, 10),
        a.ADD(3, 1, 2),    # 52
        a.LDI(4, 7),
        a.SUB(5, 3, 4),    # 45
        a.MUL(6, 1, 2),    # 420
        a.NEG(7, 1),       # -42
        a.HLT(),
    ]
    cpu.load_program(prog)
    cpu.run()
    assert cpu.read_reg(3) == 52
    assert cpu.read_reg(5) == 45
    assert cpu.read_reg(6) == 420
    assert cpu.read_reg(7) == -42
    print("  PASS\n")

def test_ternary_native():
    print("="*60)
    print("TEST: Ternary-native instructions")
    print("="*60)
    cpu = CPU5500FP()
    a   = Asm(cpu)
    prog = [
        a.LDI(1,  1), a.LDI(2, -1),
        a.MIN(3, 1, 2),   # -1
        a.MAX(4, 1, 2),   # +1
        a.TXOR(5, 1, 2),  # 0
        a.NEG(6, 1),      # -1
        a.HLT(),
    ]
    cpu.load_program(prog)
    cpu.run()
    assert cpu.read_reg(3) == -1
    assert cpu.read_reg(4) ==  1
    assert cpu.read_reg(5) ==  0
    assert cpu.read_reg(6) == -1
    print("  PASS\n")

def demo_word_gallery():
    print("="*60)
    print("DEMO: TernOO word gallery")
    print("="*60)
    words = [
        ("EXEC user/register/DATA CS2+14 v1",
         build_exec_word(0,0,1,2,14,arity=2,version=1)),
        ("MAP absolute 3D (+,−,+) coord=42",
         build_map_word(+1,-1,+1,42)),
        ("MAP origin scale=100",
         build_map_word(0,0,0,100)),
        ("MAP on YZ-plane",
         build_map_word(0,+1,-1,0)),
        ("SCALAR INT 42",
         build_int_word(42)),
        ("SCALAR UINT 999",
         build_uint_word(999)),
        ("UDP offset=7 CS+3 DS+12",
         build_udp_word(0,0,7,3,12)),
        ("NULL explicit",
         build_null_word(0)),
        ("NULL implicit stack=3",
         build_implicit_null(3,10,5,2)),
        ("PTR FLAT addr=847293",
         build_pointer_word(PTR_FLAT, 847293)),
        ("PTR REMOTE node=42",
         build_pointer_word(PTR_REMOTE, 42)),
    ]
    for label, w in words:
        print(f"  {label}")
        print(f"    trit: {word_to_str(w)}")
        print(f"    dec:  {w}")
        print(f"    desc: {describe_word(w)}")
        print()

def demo_trit_display():
    print("="*60)
    print("DEMO: Balanced ternary representation")
    print("="*60)
    for v in [0,1,-1,2,-2,13,-13,42,-42,100,364,-364,WORD_MAX,WORD_MIN]:
        print(f"  {v:20d}  {word_to_str(v)}")
    print()

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    demo_trit_display()
    demo_word_gallery()
    test_basic_arithmetic()
    test_ternary_native()
    test_word_constructors()
    test_segment_registers()
    test_double_null()
    test_renderer()
    print("━"*60)
    print("All tests passed.")
    print()
    print("5500FP + TernOO emulator v0.2.0")
    print("  Word architecture: EXEC / MAP / DATA")
    print("  Segment registers: CS0–CS8 (R63–R71), DS0–DS8 (R54–R62)")
    print("  Double Null stacks: ST0–ST8 (R45–R53), RWR (R78)")
    print("  Renderer: RPOINT RLINE RNODE REDGE RENDER")
    print()
    print("Import CPU5500FP, Asm, build_*_word, decode_word from this module.")
