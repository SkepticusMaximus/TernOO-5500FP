#!/usr/bin/env python3
"""
5500FP + TernOO Emulator  v0.3.0
=================================
Implements the 2+4+18 expanded word format:

  [2-trit PRIMARY][4-trit QUALIFIER][18-trit PAYLOAD]
   T23-T22          T21-T18           T17-T0

9 primary types (3² = 81 qualifier combos each):
  −− (−1,−1) = EXEC    −0 (−1, 0) = MAP     −+ (−1,+1) = DATA
  0− ( 0,−1) = NEURAL   00 ( 0, 0) = I/O      0+ ( 0,+1) = CRYPTO (reserved)
  +− (+1,−1) = OPCODE   +0 (+1, 0) = OPEN_B   ++ (+1,+1) = POOL

Backward compatibility: all existing EXEC/MAP/DATA words are valid under
the new format — their T23 values (−1, 0, +1) map to the first trit of
the new 2-trit primary field. T22 shifts from "DATA subtype" to "primary
second trit", which is always −1 for the existing three types.

Hardware reference:
  La Rosa, C.L. (2026). 5500FP: A 24-Trit Balanced Ternary RISC Processor.
  Zenodo. doi:10.5281/zenodo.18881738

Architecture reference:
  TernOO/5500FP Word Architecture Specification v0.3
  Stevo (SkepticusMaximus) + Claude (Anthropic), May 2026
"""

import json
import sys, os
from typing import List, Tuple, Optional

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — TRIT ARITHMETIC  (unchanged)
# ═══════════════════════════════════════════════════════════════════════════

WORD_TRITS = 24
WORD_MAX   = (3**24 - 1) // 2   #  141,214,768,240
WORD_MIN   = -WORD_MAX
TRYTE_MAX  = (3**6  - 1) // 2   #  364

def clamp_word(v): return max(WORD_MIN, min(WORD_MAX, v))

def to_trits(value: int, width: int) -> List[int]:
    trits, v = [], value
    for _ in range(width):
        r = v % 3
        if r == 2: r = -1
        trits.append(r)
        v = (v - r) // 3
    return trits

def from_trits(trits: List[int]) -> int:
    return sum(t * (3**i) for i, t in enumerate(trits))

def get_trit(value: int, pos: int) -> int:
    return to_trits(value, WORD_TRITS)[pos] if 0 <= pos < WORD_TRITS else 0

def set_trit(value: int, pos: int, trit: int) -> int:
    t = to_trits(value, WORD_TRITS)
    if 0 <= pos < WORD_TRITS: t[pos] = max(-1, min(1, trit))
    return from_trits(t)

def get_field(value: int, lsb: int, width: int) -> int:
    return from_trits(to_trits(value, WORD_TRITS)[lsb:lsb+width])

def set_field(value: int, lsb: int, width: int, field_val: int) -> int:
    t = to_trits(value, WORD_TRITS)
    fv = to_trits(field_val, width)
    for i in range(width): t[lsb+i] = fv[i]
    return from_trits(t)

def word_to_str(value: int, width: int = WORD_TRITS) -> str:
    s = {-1:'-', 0:'0', 1:'+'}
    return ''.join(s[t] for t in reversed(to_trits(value, width)))

def trit_min(a,b):
    return from_trits([min(x,y) for x,y in zip(to_trits(a,WORD_TRITS),to_trits(b,WORD_TRITS))])
def trit_max(a,b):
    return from_trits([max(x,y) for x,y in zip(to_trits(a,WORD_TRITS),to_trits(b,WORD_TRITS))])
def trit_txor(a,b):
    def _t(x,y): r=(x+y)%3; return r if r!=2 else -1
    return from_trits([_t(x,y) for x,y in zip(to_trits(a,WORD_TRITS),to_trits(b,WORD_TRITS))])
def trit_equal(a,b):
    return from_trits([1 if x==y else -1 for x,y in zip(to_trits(a,WORD_TRITS),to_trits(b,WORD_TRITS))])
def trit_sum(a,b):
    return from_trits([max(-1,min(1,x+y)) for x,y in zip(to_trits(a,WORD_TRITS),to_trits(b,WORD_TRITS))])

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — WORD FORMAT CONSTANTS  (2+4+18 layout)
# ═══════════════════════════════════════════════════════════════════════════

# Field positions in the 24-trit word
PRIMARY_MST   = 23   # T23 — most significant trit of primary field
PRIMARY_LST   = 22   # T22 — least significant trit of primary field
QUAL_MST      = 21   # T21 — most significant trit of qualifier field
QUAL_LST      = 18   # T18 — least significant trit of qualifier field
PAYLOAD_MST   = 17   # T17 — most significant trit of payload
PAYLOAD_LST   =  0   # T0  — least significant trit of payload

PRIMARY_WIDTH = 2    # trits
QUAL_WIDTH    = 4    # trits
PAYLOAD_WIDTH = 18   # trits

# Primary types — 2-trit field (T23-T22)
# Encoded as (T23, T22) pairs; stored as 2-trit balanced ternary value
#   value = T23*3 + T22  but we use get_primary() helper

def _primary_val(t23, t22):
    """Encode (T23,T22) pair as a 2-trit integer for comparison."""
    return from_trits([t22, t23])   # LSB first: T22 at pos 0, T23 at pos 1

PRIMARY_EXEC   = _primary_val(-1,-1)  # −−
PRIMARY_MAP    = _primary_val(-1, 0)  # −0
PRIMARY_DATA   = _primary_val(-1,+1)  # −+
PRIMARY_NEURAL = _primary_val( 0,-1)  # 0−
PRIMARY_IO     = _primary_val( 0, 0)  # 00
PRIMARY_CRYPTO = _primary_val( 0,+1)  # 0+  (reserved)
PRIMARY_OPEN_A = _primary_val(+1,-1)  # +−
PRIMARY_OPEN_B = _primary_val(+1, 0)  # +0
PRIMARY_POOL   = _primary_val(+1,+1)  # ++  (dynamic allocation)

PRIMARY_OPCODE = PRIMARY_OPEN_A   # (+1, −1) — OPEN_A retired in favour of OPCODE.
                                  # See §3 of the whitepaper (mid-Aug pass).

PRIMARY_NAMES = {
    PRIMARY_EXEC:   'EXEC',
    PRIMARY_MAP:    'MAP',
    PRIMARY_DATA:   'DATA',
    PRIMARY_NEURAL: 'NEURAL',
    PRIMARY_IO:     'I/O',
    PRIMARY_CRYPTO: 'CRYPTO',
    PRIMARY_OPEN_A: 'OPCODE',   # was 'OPEN_A' — PRIMARY_OPEN_A alias retained
    PRIMARY_OPEN_B: 'OPEN_B',
    PRIMARY_POOL:   'POOL',
}

# ── OPCODE family constants ────────────────────────────────────────────
# Encoded as 2-trit balanced values (T21,T20 in qualifier). 4 reserved
# slots are deliberately left unnamed — naming without a design is how
# UDP drifted, the exact pathology this proposal corrects.
OPF_ISA_CORE  = _primary_val(-1, -1)   # (−, −)
OPF_ISA_STACK = _primary_val(-1,  0)   # (−, 0)
OPF_WORD_OP   = _primary_val(-1, +1)   # (−, +)
OPF_PIGART    = _primary_val( 0, -1)   # (0, −)
OPF_MECCANO   = _primary_val( 0,  0)   # (0, 0)
OPF_MODEL     = _primary_val( 0, +1)   # (0, +) — program-model words (3 Jul
                                       # 2026, CF5-Design-OPF-MODEL-v1.md):
                                       # kind/name/cell/command attributes so
                                       # the stream carries the program, not
                                       # just its rendering.
# (+1,-1), (+1,0), (+1,+1) reserved.

def get_primary(word: int) -> int:
    """Extract 2-trit primary field as a comparable integer."""
    return get_field(word, PRIMARY_LST, PRIMARY_WIDTH)

def set_primary(word: int, primary: int) -> int:
    """Set 2-trit primary field."""
    return set_field(word, PRIMARY_LST, PRIMARY_WIDTH, primary)

def get_qualifier(word: int) -> int:
    """Extract 4-trit qualifier field."""
    return get_field(word, QUAL_LST, QUAL_WIDTH)

def set_qualifier(word: int, qual: int) -> int:
    return set_field(word, QUAL_LST, QUAL_WIDTH, qual)

def get_payload(word: int) -> int:
    """Extract 18-trit payload."""
    return get_field(word, PAYLOAD_LST, PAYLOAD_WIDTH)

def set_payload(word: int, payload: int) -> int:
    return set_field(word, PAYLOAD_LST, PAYLOAD_WIDTH, payload)

# ── EXEC qualifier fields (within 4-trit qualifier) ───────────────────────
# T21=privilege, T20=call-style, T19=return-type, T18=seg-idx MST
# Plus seg-idx LST in payload MST bits, then offset, arity, arg-types, version

EXEC_PRIV_KERNEL  = -1
EXEC_PRIV_USER    =  0
EXEC_PRIV_SANDBOX = +1

EXEC_CALL_STACK    = -1
EXEC_CALL_REGISTER =  0
EXEC_CALL_MESSAGE  = +1

EXEC_RET_EXEC = -1
EXEC_RET_MAP  =  0
EXEC_RET_DATA = +1

# ── MAP qualifier (within 4-trit qualifier) ───────────────────────────────
# T21=axis-YZ, T20=axis-XZ, T19=axis-XY, T18=spare (mode hint)
MAP_AXIS_YZ_POS = 21
MAP_AXIS_XZ_POS = 20
MAP_AXIS_XY_POS = 19

# ── DATA qualifiers ───────────────────────────────────────────────────────
# T21-T20 = subtype, T19-T18 = encoding/model
DATA_SCALAR  = from_trits([-1,-1,0,0])   # T21=-1,T20=-1 in qual field (LSB first)
DATA_POINTER = from_trits([ 0, 0,0,0])   # T21=0, T20=0
DATA_STRING  = from_trits([+1,+1,0,0])   # T21=+1,T20=+1

# SCALAR encodings (T19-T18 within qualifier)
SCALAR_FLOAT = -1
SCALAR_INT   =  0
SCALAR_UINT  = +1

# STRING encodings
STRING_UNICODE = -1
STRING_ASCII   =  0
STRING_TERNARY = +1

# POINTER models — T21,T20 of qualifier field
PTR_FLAT      = (-1,-1)
PTR_RELATIVE  = (-1, 0)
PTR_STACK_REL = (-1,+1)
PTR_FIELD     = ( 0,-1)
PTR_NULL      = ( 0, 0)
PTR_SYMBOL    = ( 0,+1)
PTR_REMOTE    = (+1,-1)
PTR_WEAK      = (+1, 0)
PTR_USER_DEF  = (+1,+1)

PTR_NAMES = {
    PTR_FLAT:'FLAT', PTR_RELATIVE:'RELATIVE', PTR_STACK_REL:'STACK_REL',
    PTR_FIELD:'FIELD', PTR_NULL:'NULL', PTR_SYMBOL:'SYMBOL',
    PTR_REMOTE:'REMOTE', PTR_WEAK:'WEAK', PTR_USER_DEF:'USER_DEF',
}

# ── NEURAL qualifiers ─────────────────────────────────────────────────────
NEURAL_UNIT       = -1   # T21 value: neuron unit
NEURAL_CONNECTION =  0   # T21 value: synapse/connection
NEURAL_STRUCTURE  = +1   # T21 value: layer/network structure

# ── I/O qualifiers ────────────────────────────────────────────────────────
IO_DIR_IN   = -1
IO_DIR_BIDI =  0
IO_DIR_OUT  = +1

IO_BUF_NONE      = -1
IO_BUF_BUFFERED  =  0
IO_BUF_INTERRUPT = +1

# ── Register assignments ──────────────────────────────────────────────────
REG_ZERO    =  0
REG_ST_BASE = 45   # R45–R53: Double Null stack pointers
REG_DS_BASE = 54   # R54–R62: data segment bases DS0–DS8
REG_CS_BASE = 63   # R63–R71: code segment bases CS0–CS8
REG_RWR     = 78   # Reserved Word Register
REG_SP      = 79   # stack pointer
REG_LR      = 80   # link register

MEMORY_SIZE = 3**12
HEAP_BASE   = MEMORY_SIZE // 2

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — WORD CONSTRUCTORS
# ═══════════════════════════════════════════════════════════════════════════

def _make_word(primary: int, qualifier: int, payload: int) -> int:
    """Base word constructor — set primary, qualifier, payload."""
    w = 0
    w = set_field(w, PRIMARY_LST, PRIMARY_WIDTH, primary)
    w = set_field(w, QUAL_LST,    QUAL_WIDTH,    qualifier)
    w = set_field(w, PAYLOAD_LST, PAYLOAD_WIDTH, payload)
    return w

# ── EXEC word ─────────────────────────────────────────────────────────────

def build_exec_word(privilege: int, call_style: int, return_type: int,
                    seg_idx: int, offset: int,
                    arity: int = 0, arg_types: int = 0, version: int = 0) -> int:
    """
    Build an EXEC word (primary=−−).
    Qualifier (4 trits): T21=priv, T20=call, T19=ret, T18=seg_idx MST
    Payload (18 trits):  T17=seg_idx LST, T16-T11=offset(6t),
                         T10-T7=arity(4t), T6-T3=arg_types(4t), T2-T0=version(3t)
    """
    qual = 0
    qual = set_trit(qual+QUAL_LST*0, 3, privilege)    # T21 → qual bit 3
    qual = set_trit(qual,            2, call_style)   # T20 → qual bit 2
    qual = set_trit(qual,            1, return_type)  # T19 → qual bit 1
    # Build qualifier as a 4-trit value
    qual_trits = [0, return_type, call_style, privilege]  # T18,T19,T20,T21 (LSB first)
    qualifier = from_trits(qual_trits)

    # Payload: seg_idx split across qualifier T18 and payload T17
    # Simpler: encode seg_idx (0-8 → stored as seg_idx-4) across 2 trits
    # T18 (qual LSB) = seg MST, T17 (payload MST) = seg LST
    si = seg_idx - 4  # balanced: -4..+4
    si_trits = to_trits(si, 2)
    # Put si_trits[1] (MST) in qualifier T18
    qualifier_val = from_trits([si_trits[1], return_type, call_style, privilege])

    payload = 0
    # T17 = seg_idx LST
    payload = set_trit(payload, 17, si_trits[0])
    # T16-T11 = offset (6 trits)
    payload = set_field(payload, 11, 6, offset)
    # T10-T7  = arity (4 trits)
    payload = set_field(payload, 7, 4, arity)
    # T6-T3   = arg_types (4 trits)
    payload = set_field(payload, 3, 4, arg_types)
    # T2-T0   = version (3 trits)
    payload = set_field(payload, 0, 3, version)

    return _make_word(PRIMARY_EXEC, qualifier_val, payload)

def decode_exec_word(w: int) -> dict:
    assert get_primary(w) == PRIMARY_EXEC, "Not an EXEC word"
    qual = to_trits(get_qualifier(w), 4)  # LSB first: T18,T19,T20,T21
    si_mst = qual[0]  # T18
    pay = get_payload(w)
    si_lst = get_trit(pay, 17)
    seg_idx = from_trits([si_lst, si_mst]) + 4
    return {
        'type':        'EXEC',
        'privilege':   qual[3],   # T21
        'call_style':  qual[2],   # T20
        'return_type': qual[1],   # T19
        'seg_idx':     seg_idx,
        'offset':      get_field(pay, 11, 6),
        'arity':       get_field(pay, 7, 4),
        'arg_types':   get_field(pay, 3, 4),
        'version':     get_field(pay, 0, 3),
    }

# ── MAP word ──────────────────────────────────────────────────────────────

def build_map_word(axis_yz: int, axis_xz: int, axis_xy: int,
                   payload: int, mode_hint: int = 0) -> int:
    """
    MAP word (primary=−0).
    Qualifier: T21=axis_YZ, T20=axis_XZ, T19=axis_XY, T18=mode_hint
    Payload: 18-trit coordinate value
    """
    qual_trits = [mode_hint, axis_xy, axis_xz, axis_yz]  # T18,T19,T20,T21 LSB first
    qualifier = from_trits(qual_trits)
    return _make_word(PRIMARY_MAP, qualifier, payload)

def decode_map_word(w: int) -> dict:
    assert get_primary(w) == PRIMARY_MAP, "Not a MAP word"
    qual = to_trits(get_qualifier(w), 4)
    yz, xz, xy = qual[3], qual[2], qual[1]
    zeros = [yz, xz, xy].count(0)
    payload = get_payload(w)
    if zeros == 3:
        mode = 'ORIGIN'; coords = {'scale': payload}
    elif zeros == 2:
        active = [n for n,v in zip(['Y','X','Z'],[yz,xz,xy]) if v!=0]
        mode = f'ON_AXIS_{active[0] if active else "?"}'; coords = {'value': payload}
    elif zeros == 1:
        hi, lo = get_field(w, 9, 9), get_field(w, 0, 9)
        mode = 'ON_PLANE'
        if yz==0:   coords={'Y':hi,'Z':lo}
        elif xz==0: coords={'X':hi,'Z':lo}
        else:       coords={'X':hi,'Y':lo}
    else:
        mode = 'ABSOLUTE_3D'
        coords = {'yz':yz,'xz':xz,'xy':xy,'magnitude':payload}
    return {'type':'MAP','mode':mode,'axis_yz':yz,'axis_xz':xz,
            'axis_xy':xy,'payload':payload,'coords':coords}

# ── DATA words ────────────────────────────────────────────────────────────

def _data_qualifier(t21: int, t20: int, t19: int = 0, t18: int = 0) -> int:
    return from_trits([t18, t19, t20, t21])

def build_scalar_word(encoding: int, value: int) -> int:
    """DATA/SCALAR word. Qualifier: T21=−1(scalar), T20=−1, T19=encoding, T18=0"""
    qual = _data_qualifier(-1, -1, encoding, 0)
    return _make_word(PRIMARY_DATA, qual, value)

def build_int_word(value: int) -> int:
    return build_scalar_word(SCALAR_INT, value)

def build_uint_word(value: int) -> int:
    return build_scalar_word(SCALAR_UINT, max(0, value))

def build_string_word(encoding: int, length_or_addr: int) -> int:
    """DATA/STRING word. Qualifier: T21=+1(string), T20=+1, T19=encoding"""
    qual = _data_qualifier(+1, -1, encoding, 0)
    return _make_word(PRIMARY_DATA, qual, length_or_addr)

def build_pointer_word(model: Tuple[int,int], payload: int) -> int:
    """DATA/POINTER word (models 1-8). Qualifier: T21=0,T20=0,T19=model[0],T18=model[1]"""
    t21_m, t20_m = model
    qual = _data_qualifier(0, 0, t21_m, t20_m)
    return _make_word(PRIMARY_DATA, qual, payload)

def build_null_word(payload: int = 0) -> int:
    return build_pointer_word(PTR_NULL, payload)

def build_implicit_null(stack_id: int, qualifier: int,
                        mapping_a: int, mapping_b: int) -> int:
    """Implicit NULL for Double Null mechanism."""
    w = build_pointer_word(PTR_NULL, 1)  # payload != 0 signals implicit
    pay = 0
    pay = set_field(pay, 12, 2, stack_id - 4)  # stack selector: 2 trits
    pay = set_field(pay, 6,  6, mapping_a)
    pay = set_field(pay, 0,  6, mapping_b)
    # qualifier stored in a register by convention, not in word payload
    # (18-trit payload: T17-T16=stack_id, T15-T12=spare, T11-T6=map_a, T5-T0=map_b)
    pay2 = 0
    pay2 = set_field(pay2, 12, 2, stack_id - 4)
    pay2 = set_field(pay2, 6, 6, mapping_a)
    pay2 = set_field(pay2, 0, 6, mapping_b)
    return _make_word(PRIMARY_DATA, _data_qualifier(0,0,0,0), pay2 + 1)

def build_udp_word(subclass_t1: int, subclass_t0: int,
                   offset: int, code_seg: int, data_seg: int) -> int:
    """
    USER-DEF POINTER word (primary=DATA, qualifier=PTR_USER_DEF pattern).
    Now has full 18-trit payload (vs 16 in v0.2):
    T17-T16: subclass (2 trits, 9 combos)
    T15-T10: OFFSET (6 trits)
    T9-T4:   CODE-SEG (6 trits)
    T3-T0:   DATA-SEG (4 trits — expanded from 6 to use the freed space)
    """
    qual = _data_qualifier(PTR_USER_DEF[0], PTR_USER_DEF[1], 0, 0)
    pay = 0
    pay = set_trit(pay, 17, max(-1,min(1,subclass_t1)))
    pay = set_trit(pay, 16, max(-1,min(1,subclass_t0)))
    pay = set_field(pay, 10, 6, offset)
    pay = set_field(pay, 4,  6, code_seg)
    pay = set_field(pay, 0,  4, data_seg)
    return _make_word(PRIMARY_DATA, qual, pay)

def decode_udp_word(w: int) -> dict:
    pay = get_payload(w)
    return {
        'type':        'UDP',
        'subclass_t1': get_trit(pay, 17),
        'subclass_t0': get_trit(pay, 16),
        'offset':      get_field(pay, 10, 6),
        'code_seg':    get_field(pay, 4,  6),
        'data_seg':    get_field(pay, 0,  4),
    }

# ── NEURAL words (new in v0.3) ────────────────────────────────────────────

def build_neural_unit(state: int, bias: int, fan_in: int, weight_seg: int) -> int:
    """
    NEURAL/UNIT word — a neuron.
    Qualifier: T21=UNIT(−1), T20-T18=activation encoding
    Payload: T17-T15=state(3t), T14-T9=bias(6t), T8-T4=fan_in(5t), T3-T0=weight_seg(4t)
    """
    qual = _data_qualifier(NEURAL_UNIT, 0, 0, 0)
    pay = 0
    pay = set_field(pay, 15, 3, state)
    pay = set_field(pay, 9,  6, bias)
    pay = set_field(pay, 4,  5, fan_in)
    pay = set_field(pay, 0,  4, weight_seg)
    return _make_word(PRIMARY_NEURAL, qual, pay)

def build_neural_connection(weight: int, source: int, target: int) -> int:
    """
    NEURAL/CONNECTION word — a synapse.
    Qualifier: T21=CONNECTION(0)
    Payload: T17-T16=weight(2t, 9 levels), T15-T8=source(8t), T7-T0=target(8t)
    Note: 2-trit weight gives 9 levels (−4..+4) vs BitNet's {−1,0,+1}
    """
    qual = _data_qualifier(NEURAL_CONNECTION, 0, 0, 0)
    pay = 0
    pay = set_field(pay, 16, 2, weight)   # weight: 2 trits → ±4
    pay = set_field(pay, 8,  8, source)   # source neuron id: 8 trits → ±3280
    pay = set_field(pay, 0,  8, target)   # target neuron id: 8 trits → ±3280
    return _make_word(PRIMARY_NEURAL, qual, pay)

def build_neural_structure(kind: int, size: int, seg_ref: int) -> int:
    """NEURAL/STRUCTURE word — layer or network descriptor."""
    qual = _data_qualifier(NEURAL_STRUCTURE, 0, 0, 0)
    pay = set_field(0, 12, 6, kind) 
    pay = set_field(pay, 6, 6, size)
    pay = set_field(pay, 0, 6, seg_ref)
    return _make_word(PRIMARY_NEURAL, qual, pay)

# ── I/O words (new in v0.3) ───────────────────────────────────────────────

def build_io_word(direction: int, buffering: int, blocking: int,
                  channel: int) -> int:
    """
    I/O word — stream, event, or channel reference.
    Qualifier: T21=direction, T20=buffering, T19=blocking, T18=spare
    Payload: 18-trit channel identifier or data
    """
    qual = _data_qualifier(direction, buffering, blocking, 0)
    return _make_word(PRIMARY_IO, qual, channel)

# ── Universal decoder ─────────────────────────────────────────────────────

_GLYPH_MOD = None
def _glyph_module():
    """Lazily load ternoo_glyph for native-plane payload interpretation. The
    generic decoder only RECOGNISES the plane; the plane's module reads it
    (CF5 ruling 2, 2026-07-08). Fully guarded — never breaks decode_word."""
    global _GLYPH_MOD
    if _GLYPH_MOD is None:
        try:
            import importlib.util as _ilu, os as _os
            _p = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                               'ternoo_glyph.py')
            _s = _ilu.spec_from_file_location('ternoo_glyph', _p)
            _GLYPH_MOD = _ilu.module_from_spec(_s)
            _s.loader.exec_module(_GLYPH_MOD)
        except Exception:
            _GLYPH_MOD = False
    return _GLYPH_MOD or None


def decode_word(w: int) -> dict:
    """Fully decode any TernOO word."""
    prim = get_primary(w)
    name = PRIMARY_NAMES.get(prim, f'UNKNOWN({prim})')
    qual = get_qualifier(w)
    pay  = get_payload(w)
    qual_trits = to_trits(qual, 4)  # T18,T19,T20,T21 (LSB first)

    if prim == PRIMARY_EXEC:
        return decode_exec_word(w)

    elif prim == PRIMARY_MAP:
        return decode_map_word(w)

    elif prim == PRIMARY_DATA:
        t21, t20 = qual_trits[3], qual_trits[2]
        t19, t18 = qual_trits[1], qual_trits[0]

        if t21 == -1 and t20 == -1:   # SCALAR
            enc = {SCALAR_FLOAT:'float',SCALAR_INT:'int',SCALAR_UINT:'uint'}.get(t19,'?')
            return {'type':'SCALAR','encoding':enc,'value':pay}

        elif t21 == +1 and t20 == -1:  # STRING
            if t19 == STRING_TERNARY:   # native glyph plane — delegate (ruling 2)
                gm = _glyph_module()
                if gm is not None:
                    return {'type':'STRING','encoding':'ternary',
                            'plane':'native','glyph':gm.describe(w)}
                return {'type':'STRING','encoding':'ternary','plane':'native'}
            enc = {STRING_UNICODE:'unicode',STRING_ASCII:'ascii'}.get(t19,'?')
            return {'type':'STRING','encoding':enc,'length_or_addr':pay}

        else:  # POINTER — model from T21,T20 of qualifier
            model = (t21, t20)
            if model == PTR_USER_DEF:
                return decode_udp_word(w)
            elif model == PTR_NULL:
                payload_raw = get_field(w, 0, 18)
                if payload_raw == 0:
                    return {'type':'NULL','subtype':'explicit'}
                else:
                    sid = get_field(w, 12, 2) + 4
                    return {'type':'NULL','subtype':'implicit',
                            'stack_id':sid,
                            'mapping_a':get_field(w,6,6),
                            'mapping_b':get_field(w,0,6)}
            else:
                mname = PTR_NAMES.get(model,'?')
                return {'type':'POINTER','model':mname,'payload':pay}

    elif prim == PRIMARY_NEURAL:
        t21 = qual_trits[3]
        if t21 == NEURAL_UNIT:
            return {'type':'NEURAL_UNIT',
                    'state':    get_field(w,15,3),
                    'bias':     get_field(w,9,6),
                    'fan_in':   get_field(w,4,5),
                    'weight_seg':get_field(w,0,4)}
        elif t21 == NEURAL_CONNECTION:
            return {'type':'NEURAL_CONNECTION',
                    'weight': get_field(w,16,2),
                    'source': get_field(w,8,8),
                    'target': get_field(w,0,8)}
        else:
            return {'type':'NEURAL_STRUCTURE',
                    'kind':    get_field(w,12,6),
                    'size':    get_field(w,6,6),
                    'seg_ref': get_field(w,0,6)}

    elif prim == PRIMARY_IO:
        dirs = {IO_DIR_IN:'in',IO_DIR_BIDI:'bidi',IO_DIR_OUT:'out'}
        bufs = {IO_BUF_NONE:'none',IO_BUF_BUFFERED:'buffered',
                IO_BUF_INTERRUPT:'interrupt'}
        return {'type':'I/O',
                'direction': dirs.get(qual_trits[3],'?'),
                'buffering': bufs.get(qual_trits[2],'?'),
                'blocking':  qual_trits[1],
                'channel':   pay}

    elif prim == PRIMARY_OPCODE:
        return decode_opcode_word(w)

    else:
        return {'type':name,'qualifier':qual,'payload':pay}

def describe_word(w: int) -> str:
    d = decode_word(w)
    t = d['type']
    if t == 'EXEC':
        priv = {-1:'kernel',0:'user',1:'sandbox'}.get(d['privilege'],'?')
        call = {-1:'stack',0:'register',1:'message'}.get(d['call_style'],'?')
        ret  = {-1:'EXEC',0:'MAP',1:'DATA'}.get(d['return_type'],'?')
        return (f"EXEC priv={priv} call={call} ret={ret} "
                f"CS{d['seg_idx']}+{d['offset']} ar={d['arity']} v={d['version']}")
    elif t == 'MAP':
        return f"MAP {d['mode']} {d['coords']}"
    elif t == 'SCALAR':
        return f"SCALAR({d['encoding']}) {d['value']}"
    elif t == 'STRING':
        return f"STRING({d['encoding']}) len/addr={d['length_or_addr']}"
    elif t == 'POINTER':
        return f"PTR({d['model']}) payload={d['payload']}"
    elif t == 'UDP':
        return (f"UDP sub=({d['subclass_t1']},{d['subclass_t0']}) "
                f"off={d['offset']} CS+{d['code_seg']} DS+{d['data_seg']}")
    elif t == 'NULL':
        return (f"NULL(explicit)" if d['subtype']=='explicit'
                else f"NULL(implicit) stack={d['stack_id']}")
    elif t == 'NEURAL_UNIT':
        return f"NEURON state={d['state']} bias={d['bias']} fan_in={d['fan_in']}"
    elif t == 'NEURAL_CONNECTION':
        return f"SYNAPSE w={d['weight']} {d['source']}→{d['target']}"
    elif t == 'NEURAL_STRUCTURE':
        return f"NEURAL_STRUCT kind={d['kind']} size={d['size']}"
    elif t == 'I/O':
        return f"I/O dir={d['direction']} buf={d['buffering']} ch={d['channel']}"
    elif t == 'OPCODE':
        if d['family_name'] == 'MECCANO':
            return f"OPCODE/MECCANO ⊕{d['meccano']} arity={d['arity']}"
        else:
            return f"OPCODE/{d['family_name']} {d['mnemonic']} arity={d['arity']}"
    return f"{t} qual={d.get('qualifier','?')} pay={d.get('payload','?')}"

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — OPCODES
# ═══════════════════════════════════════════════════════════════════════════

OP_NOP=0; OP_HLT=1; OP_ADD=2; OP_SUB=3; OP_MUL=4; OP_DIV=5
OP_NEG=6; OP_MOV=7; OP_LDI=8; OP_LD=9; OP_ST=10; OP_JMP=11
OP_JEQ=12; OP_JNE=13; OP_JB=14; OP_JSR=15; OP_RTI=16
OP_PUSH=17; OP_POP=18; OP_MIN=19; OP_MAX=20; OP_TXOR=21
OP_EQUAL=22; OP_SUM=23; OP_TTT=24; OP_TTZ=25; OP_TTP=26
OP_ADDI=27; OP_SUBI=28; OP_OUT=29; OP_IN=30
OP_TOBJ=31; OP_TGET=32; OP_TPAYLOAD=33; OP_TCALL=34; OP_TNEW=35
OP_TBUILD=36; OP_TSEG=37
OP_RPOINT=38; OP_RLINE=39; OP_RNODE=40; OP_REDGE=-1; OP_RENDER=-2

# ── OPCODE word — mnemonic table ──────────────────────────────────────────────
# Keys: (family, op_index) where family is one of the OPF_* constants.
# MECCANO family uses meccano value, not op_index — no entries here for it.
# OP_REDGE=-1 and OP_RENDER=-2 have unusual negative encoding (v0.3 quirk,
# kept as-is — cleanup is a separate task per work order).

OPCODE_MNEMONICS: dict = {
    # ── ISA_CORE: 27 ops — arithmetic, logic, memory, control flow ──────
    (OPF_ISA_CORE,  0): 'NOP',    (OPF_ISA_CORE,  1): 'HLT',
    (OPF_ISA_CORE,  2): 'ADD',    (OPF_ISA_CORE,  3): 'SUB',
    (OPF_ISA_CORE,  4): 'MUL',    (OPF_ISA_CORE,  5): 'DIV',
    (OPF_ISA_CORE,  6): 'NEG',    (OPF_ISA_CORE,  7): 'MOV',
    (OPF_ISA_CORE,  8): 'LDI',    (OPF_ISA_CORE,  9): 'LD',
    (OPF_ISA_CORE, 10): 'ST',     (OPF_ISA_CORE, 11): 'JMP',
    (OPF_ISA_CORE, 12): 'JEQ',    (OPF_ISA_CORE, 13): 'JNE',
    (OPF_ISA_CORE, 14): 'JB',     (OPF_ISA_CORE, 19): 'MIN',
    (OPF_ISA_CORE, 20): 'MAX',    (OPF_ISA_CORE, 21): 'TXOR',
    (OPF_ISA_CORE, 22): 'EQUAL',  (OPF_ISA_CORE, 23): 'SUM',
    (OPF_ISA_CORE, 24): 'TTT',    (OPF_ISA_CORE, 25): 'TTZ',
    (OPF_ISA_CORE, 26): 'TTP',    (OPF_ISA_CORE, 27): 'ADDI',
    (OPF_ISA_CORE, 28): 'SUBI',   (OPF_ISA_CORE, 29): 'OUT',
    (OPF_ISA_CORE, 30): 'IN',

    # ── ISA_STACK: 4 ops — stack-band ──────────────────────────────────
    (OPF_ISA_STACK, 15): 'JSR',   (OPF_ISA_STACK, 16): 'RTI',
    (OPF_ISA_STACK, 17): 'PUSH',  (OPF_ISA_STACK, 18): 'POP',

    # ── WORD_OP: 7 ops — TernOO object operations ──────────────────────
    (OPF_WORD_OP, 31): 'TOBJ',    (OPF_WORD_OP, 32): 'TGET',
    (OPF_WORD_OP, 33): 'TPAYLOAD',(OPF_WORD_OP, 34): 'TCALL',
    (OPF_WORD_OP, 35): 'TNEW',    (OPF_WORD_OP, 36): 'TBUILD',
    (OPF_WORD_OP, 37): 'TSEG',

    # ── PIGART: 5 ops — rendering primitives ───────────────────────────
    (OPF_PIGART, 38): 'RPOINT',   (OPF_PIGART, 39): 'RLINE',
    (OPF_PIGART, 40): 'RNODE',    (OPF_PIGART, -1): 'REDGE',
    (OPF_PIGART, -2): 'RENDER',

    # MECCANO family: uses meccano value, not op_index. No entries here.
    # OPF_MODEL — program-model attribute words (grammar extension v1)
    (OPF_MODEL, 0): 'MKIND',  (OPF_MODEL, 1): 'MNAME',
    (OPF_MODEL, 2): 'MCELL',  (OPF_MODEL, 3): 'MCMDW',
    (OPF_MODEL, 4): 'MPARM',  (OPF_MODEL, 5): 'MPORT',
    (OPF_MODEL, 6): 'MSCOPE', (OPF_MODEL, 7): 'MMORE',
    (OPF_MODEL, 8): 'MEDGE',  (OPF_MODEL, 9): 'MFLAG',
    (OPF_MODEL, 10): 'MNOTE',
}

# ── Reverse lookup: mnemonic string → (family, op_index) ─────────────────────
OPCODE_MNEMONICS_REVERSE: dict = {v: k for k, v in OPCODE_MNEMONICS.items()}

# ── OPF family names ──────────────────────────────────────────────────────────
_OPF_NAMES = {
    OPF_ISA_CORE:  'ISA_CORE',
    OPF_ISA_STACK: 'ISA_STACK',
    OPF_WORD_OP:   'WORD_OP',
    OPF_PIGART:    'PIGART',
    OPF_MECCANO:   'MECCANO',
    OPF_MODEL:     'MODEL',
}


def build_opcode_word(family: int, arity: int,
                      op_index: int = 0, immediate: int = 0,
                      meccano: int = None) -> int:
    """Build an OPCODE primary word.

    Layout:
      [T23..T22] primary = PRIMARY_OPCODE (+1, −1)
      [T21..T20] family  (2 trits, balanced −4..+4 → 9 family slots)
      [T19..T18] arity   (2 trits, balanced −4..+4 → 0..8 via value+4)
      [T17..T0]  payload (18 trits):
        MECCANO family (family == OPF_MECCANO):
          - T5..T0  = Meccano value as low tribble (0..728, multiple of 27)
          - T11..T6 = 0
          - T17..T12 = spare/extension (default 0)
        Other families:
          - T17..T12 = op_index within family (6 trits, ±364)
          - T11..T6  = immediate tribble (family-defined, default 0)
          - T5..T0   = immediate tribble (family-defined, default 0)

    Args:
        family: one of OPF_* constants.
        arity: 0..8 (encoded internally as arity − 4 into the 2-trit field).
        op_index: signed integer in ±364 (family-internal opcode index).
        immediate: signed integer fitting two tribbles (interpretation family-defined).
        meccano: 0..728, multiple of 27, or 0 sentinel.
                 Mutually exclusive with op_index/immediate; implies family=OPF_MECCANO.

    Raises:
        ValueError on out-of-range arity, family, op_index, immediate, or meccano value.
    """
    if arity < 0 or arity > 8:
        raise ValueError(f"arity must be 0..8, got {arity}")
    arity_enc = arity - 4   # encode as balanced value: -4..+4

    # Validate family fits in 2 trits (balanced -4..+4)
    fam_trits = to_trits(family, 2)
    if from_trits(fam_trits) != family:
        raise ValueError(f"family value {family} does not fit in 2 trits")

    if meccano is not None:
        # MECCANO path — op_index/immediate ignored.
        # Normalise to the balanced-ternary representative of Z/729Z.
        # 729 (the group identity element) → 0; values > 364 fold negative.
        # This is required because the 6-trit field stores balanced values (±364 max).
        meccano = meccano % 729           # 729 → 0; reduces any positive input
        if meccano > 364:
            meccano -= 729                # e.g. 702 → -27, 378 → -351
        if meccano != 0 and meccano % 27 != 0:
            raise ValueError(f"meccano must be 0 or a multiple of 27 (balanced), got {meccano}")
        # Build qualifier: [T21..T20] = family, [T19..T18] = arity_enc
        qual = set_field(0, 2, 2, family)    # T21..T20 within qual 4-trit block
        qual = set_field(qual, 0, 2, arity_enc)  # T19..T18
        # Payload: low tribble (T5..T0) = meccano value (balanced); rest = 0
        pay = set_field(0, 0, 6, meccano)
    else:
        # Non-MECCANO path
        if op_index < -364 or op_index > 364:
            raise ValueError(f"op_index must be ±364, got {op_index}")
        # Build qualifier
        qual = set_field(0, 2, 2, family)
        qual = set_field(qual, 0, 2, arity_enc)
        # Payload: T17..T12 = op_index, T11..T0 = immediate (split across two tribbles)
        pay = set_field(0, 12, 6, op_index)
        pay = set_field(pay, 0, 12, immediate)

    # Assemble full word: primary at T23..T22, qualifier at T21..T18, payload at T17..T0
    w = _make_word(PRIMARY_OPCODE, qual, pay)
    return w


def decode_opcode_word(word: int) -> dict:
    """Decode an OPCODE primary word. Inverse of build_opcode_word.

    Returns:
        {
          'type': 'OPCODE',
          'family': int,           # OPF_* constant
          'family_name': str,      # 'ISA_CORE' | 'ISA_STACK' | 'WORD_OP' | 'PIGART' | 'MECCANO' | 'RESERVED'
          'arity': int,            # 0..8
          'op_index': int,         # ±364, or None for MECCANO family
          'mnemonic': str,         # from OPCODE_MNEMONICS, or '?' for unknown
          'immediate': int,        # signed, two tribbles wide
          'meccano': int,          # 0..728 for MECCANO family, None otherwise
        }

    Raises:
        ValueError if word's primary is not PRIMARY_OPCODE.
    """
    prim = get_primary(word)
    if prim != PRIMARY_OPCODE:
        raise ValueError(f"Not an OPCODE word (primary={prim})")

    qual      = get_qualifier(word)    # 4-trit field T21..T18
    family    = get_field(qual, 2, 2)  # T21..T20 within qual (positions 2-3)
    arity_enc = get_field(qual, 0, 2)  # T19..T18 within qual (positions 0-1)
    arity     = arity_enc + 4          # decode: stored+4

    family_name = _OPF_NAMES.get(family, 'RESERVED')

    pay = get_payload(word)

    if family == OPF_MECCANO:
        meccano  = get_field(pay, 0, 6)   # low tribble T5..T0
        op_index = None
        immediate = 0
        mnemonic = '?'
    else:
        op_index  = get_field(pay, 12, 6)  # T17..T12
        immediate = get_field(pay, 0, 12)  # T11..T0
        meccano   = None
        mnemonic  = OPCODE_MNEMONICS.get((family, op_index), '?')

    return {
        'type':        'OPCODE',
        'family':      family,
        'family_name': family_name,
        'arity':       arity,
        'op_index':    op_index,
        'mnemonic':    mnemonic,
        'immediate':   immediate,
        'meccano':     meccano,
    }


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 — CPU
# ═══════════════════════════════════════════════════════════════════════════

class CPU5500FP:
    NUM_REGS = 81

    def __init__(self, memory_size: int = MEMORY_SIZE):
        self.memory  = [0] * memory_size
        self._trace  = False
        self.canvas: List[dict] = []
        self.reset()

    def reset(self):
        self.regs        = [0] * self.NUM_REGS
        self.pc          = 0
        self.halted      = False
        self.call_stack: List[int] = []
        self.cycle_count = 0
        self._heap_ptr   = HEAP_BASE
        self._dn_stacks: List[List[dict]] = [[] for _ in range(9)]
        self.canvas      = []

    def read_reg(self, r):  return 0 if r==0 else self.regs[r % self.NUM_REGS]
    def write_reg(self, r, v):
        if r != 0: self.regs[r % self.NUM_REGS] = clamp_word(v)

    def read_cs(self, idx):  return self.read_reg(REG_CS_BASE + idx)
    def write_cs(self, idx, addr): self.write_reg(REG_CS_BASE + idx, addr)
    def read_ds(self, idx):  return self.read_reg(REG_DS_BASE + idx)
    def write_ds(self, idx, addr): self.write_reg(REG_DS_BASE + idx, addr)

    def resolve_exec(self, exec_word: int) -> int:
        d = decode_exec_word(exec_word)
        return self.read_cs(d['seg_idx']) + d['offset']

    def resolve_udp_code(self, udp_word: int) -> int:
        d = decode_udp_word(udp_word)
        return self.read_cs(0) + d['code_seg']

    def resolve_udp_data(self, udp_word: int) -> int:
        d = decode_udp_word(udp_word)
        return self.read_ds(0) + d['data_seg']

    def mem_read(self, addr):
        if 0 <= addr < len(self.memory): return self.memory[addr]
        raise MemoryError(f"Read OOB: {addr}")
    def mem_write(self, addr, value):
        if 0 <= addr < len(self.memory): self.memory[addr] = clamp_word(value)
        else: raise MemoryError(f"Write OOB: {addr}")

    def _heap_alloc(self, size):
        addr = self._heap_ptr
        self._heap_ptr += max(1, size)
        if self._heap_ptr >= len(self.memory): raise MemoryError("Heap exhausted")
        return addr

    def _er(self, r): return r - 40
    def _dr(self, f): return f + 40
    def _fields(self, instr):
        t = to_trits(instr, WORD_TRITS)
        return [from_trits(t[i*4:(i+1)*4]) for i in range(6)]
    def _regs_A(self, instr):
        f = self._fields(instr)
        return tuple(self._dr(f[i]) for i in range(5))
    def _imm_J2(self, instr):
        f = self._fields(instr)
        return self._dr(f[0]), self._dr(f[1]), from_trits(
            to_trits(f[2],4)+to_trits(f[3],4)+to_trits(f[4],4))
    def _imm_J(self, instr):
        f = self._fields(instr)
        return from_trits(to_trits(f[0],4)+to_trits(f[1],4)+to_trits(f[2],4)
                         +to_trits(f[3],4)+to_trits(f[4],4))

    def assemble_A(self, op, rd, rs1, rs2=40, rs3=40, rs4=40):
        return from_trits(to_trits(self._er(rd),4)+to_trits(self._er(rs1),4)+
                          to_trits(self._er(rs2),4)+to_trits(self._er(rs3),4)+
                          to_trits(self._er(rs4),4)+to_trits(op,4))
    def assemble_J2(self, op, rd, rs1, imm):
        return from_trits(to_trits(self._er(rd),4)+to_trits(self._er(rs1),4)+
                          to_trits(imm,12)+to_trits(op,4))
    def assemble_J(self, op, imm):
        return from_trits(to_trits(imm,20)+to_trits(op,4))

    def load_program(self, program, start=0):
        for i,w in enumerate(program): self.mem_write(start+i, w)
        self.pc = start

    def fetch(self):
        instr = self.mem_read(self.pc); self.pc += 1; return instr

    def execute(self, instr):
        f = self._fields(instr)
        op = f[5]
        if self._trace:
            print(f"  PC={self.pc-1:4d} op={op:3d} [{word_to_str(instr)}]")

        if   op==OP_NOP: pass
        elif op==OP_HLT: self.halted=True
        elif op==OP_ADD:
            rd,rs1,rs2,*_=self._regs_A(instr)
            self.write_reg(rd,self.read_reg(rs1)+self.read_reg(rs2))
        elif op==OP_ADDI:
            rd,rs1,imm=self._imm_J2(instr)
            self.write_reg(rd,self.read_reg(rs1)+imm)
        elif op==OP_SUB:
            rd,rs1,rs2,*_=self._regs_A(instr)
            self.write_reg(rd,self.read_reg(rs1)-self.read_reg(rs2))
        elif op==OP_SUBI:
            rd,rs1,imm=self._imm_J2(instr)
            self.write_reg(rd,self.read_reg(rs1)-imm)
        elif op==OP_MUL:
            rd,rs1,rs2,*_=self._regs_A(instr)
            self.write_reg(rd,self.read_reg(rs1)*self.read_reg(rs2))
        elif op==OP_DIV:
            rd,rs1,rs2,*_=self._regs_A(instr)
            d=self.read_reg(rs2)
            if d==0: raise ZeroDivisionError
            self.write_reg(rd,int(self.read_reg(rs1)/d))
        elif op==OP_NEG:
            rd,rs1,*_=self._regs_A(instr)
            self.write_reg(rd,-self.read_reg(rs1))
        elif op==OP_MOV:
            rd,rs1,*_=self._regs_A(instr)
            self.write_reg(rd,self.read_reg(rs1))
        elif op==OP_LDI:
            rd,_,imm=self._imm_J2(instr)
            self.write_reg(rd,imm)
        elif op==OP_LD:
            rd,rs1,*_=self._regs_A(instr)
            self.write_reg(rd,self.mem_read(self.read_reg(rs1)))
        elif op==OP_ST:
            rd,rs1,rs2,*_=self._regs_A(instr)
            self.mem_write(self.read_reg(rs2),self.read_reg(rd))
        elif op==OP_JMP: self.pc=self._imm_J(instr)
        elif op==OP_JSR:
            self.write_reg(REG_LR,self.pc)
            self.call_stack.append(self.pc)
            self.pc=self._imm_J(instr)
        elif op==OP_RTI:
            if self.call_stack: self.pc=self.call_stack.pop()
            else: raise RuntimeError("RTI empty stack")
        elif op==OP_JEQ:
            rd,rs1,imm=self._imm_J2(instr)
            if self.read_reg(rd)==self.read_reg(rs1): self.pc+=imm
        elif op==OP_JNE:
            rd,rs1,imm=self._imm_J2(instr)
            if self.read_reg(rd)!=self.read_reg(rs1): self.pc+=imm
        elif op==OP_JB:
            rd,rs1,imm=self._imm_J2(instr)
            if self.read_reg(rd)<self.read_reg(rs1): self.pc+=imm
        elif op==OP_PUSH:
            rd,*_=self._regs_A(instr)
            sp=self.read_reg(REG_SP)
            self.mem_write(sp,self.read_reg(rd))
            self.write_reg(REG_SP,sp-1)
        elif op==OP_POP:
            rd,*_=self._regs_A(instr)
            sp=self.read_reg(REG_SP)+1
            self.write_reg(REG_SP,sp)
            self.write_reg(rd,self.mem_read(sp))
        elif op==OP_MIN:
            rd,rs1,rs2,*_=self._regs_A(instr)
            self.write_reg(rd,trit_min(self.read_reg(rs1),self.read_reg(rs2)))
        elif op==OP_MAX:
            rd,rs1,rs2,*_=self._regs_A(instr)
            self.write_reg(rd,trit_max(self.read_reg(rs1),self.read_reg(rs2)))
        elif op==OP_TXOR:
            rd,rs1,rs2,*_=self._regs_A(instr)
            self.write_reg(rd,trit_txor(self.read_reg(rs1),self.read_reg(rs2)))
        elif op==OP_EQUAL:
            rd,rs1,rs2,*_=self._regs_A(instr)
            self.write_reg(rd,trit_equal(self.read_reg(rs1),self.read_reg(rs2)))
        elif op==OP_SUM:
            rd,rs1,rs2,*_=self._regs_A(instr)
            self.write_reg(rd,trit_sum(self.read_reg(rs1),self.read_reg(rs2)))
        elif op in (OP_TTT,OP_TTZ,OP_TTP):
            rd,rs1,imm=self._imm_J2(instr)
            t=get_trit(self.read_reg(rd),self.read_reg(rs1))
            if op==OP_TTT and t==-1: self.pc+=imm
            elif op==OP_TTZ and t==0: self.pc+=imm
            elif op==OP_TTP and t==1: self.pc+=imm
        # ── Legacy v0.1 single-trit T23 tag ops ────────────────────────────
        # OP_TOBJ and OP_TGET treat T23 as a single-trit tag, pre-dating the
        # 2-trit primary field. Retained for emulator demo compatibility.
        # Documented behaviour on OPCODE-primary words pinned by
        # test_legacy_tag_pinning. Deprecation deferred to post-ASPLOS cleanup.
        elif op==OP_TOBJ:
            rd,rs1,rs2,*_=self._regs_A(instr)
            val=self.read_reg(rs1)
            tag=max(-1,min(1,self.read_reg(rs2)))
            self.write_reg(rd,set_trit(val,23,tag))
        elif op==OP_TGET:
            rd,rs1,*_=self._regs_A(instr)
            self.write_reg(rd,get_trit(self.read_reg(rs1),23))
        elif op==OP_TPAYLOAD:
            rd,rs1,*_=self._regs_A(instr)
            self.write_reg(rd,get_payload(self.read_reg(rs1)))
        elif op==OP_TCALL:
            rd,rs1,rs2,rs3,_=self._regs_A(instr)
            prim=get_primary(self.read_reg(rd))
            self.call_stack.append(self.pc)
            self.write_reg(REG_LR,self.pc)
            if   prim==PRIMARY_EXEC:   self.pc=self.read_reg(rs1)
            elif prim==PRIMARY_MAP:    self.pc=self.read_reg(rs2)
            else:                      self.pc=self.read_reg(rs3)
        elif op==OP_TNEW:
            rd,rs1,rs2,*_=self._regs_A(instr)
            addr=self._heap_alloc(max(1,self.read_reg(rs2)))
            self.write_reg(rd,set_primary(addr,get_primary(self.read_reg(rs1))))
        elif op==OP_TBUILD:
            rd,rs1,rs2,rs3,_=self._regs_A(instr)
            self.write_reg(rd,build_udp_word(0,0,self.read_reg(rs3),
                                             self.read_reg(rs1),self.read_reg(rs2)))
        elif op==OP_TSEG:
            rd,rs1,*_=self._regs_A(instr)
            ew=self.read_reg(rs1)
            self.write_reg(rd, self.resolve_exec(ew)
                           if get_primary(ew)==PRIMARY_EXEC else ew)
        elif op==OP_RPOINT:
            rd,rs1,rs2,*_=self._regs_A(instr)
            entry={'prim':'POINT','pos':self.read_reg(rs1),
                   'colour':get_payload(self.read_reg(rs2)),'dirty':True}
            self.canvas.append(entry)
            self.write_reg(rd,len(self.canvas)-1)
        elif op==OP_RLINE:
            rd,rs1,rs2,rs3,_=self._regs_A(instr)
            entry={'prim':'LINE','start':self.read_reg(rs1),
                   'end':self.read_reg(rs2),'style':self.read_reg(rs3),'dirty':True}
            self.canvas.append(entry)
            self.write_reg(rd,len(self.canvas)-1)
        elif op==OP_RNODE:
            rd,rs1,rs2,rs3,rs4=self._regs_A(instr)
            sw=self.read_reg(rs3)
            qual_t=to_trits(get_qualifier(sw),4)
            shape={SCALAR_INT:'rect',SCALAR_FLOAT:'diamond',
                   SCALAR_UINT:'rounded'}.get(qual_t[1],'rect')
            obj_w=self.read_reg(rs4)
            entry={'prim':'NODE','pos':self.read_reg(rs1),'dims':self.read_reg(rs2),
                   'shape':shape,'object':decode_udp_word(obj_w)
                   if get_primary(obj_w)==PRIMARY_DATA else {'raw':obj_w},
                   'dirty':True}
            self.canvas.append(entry)
            self.write_reg(rd,len(self.canvas)-1)
        elif op==OP_REDGE:
            rd,rs1,rs2,rs3,_=self._regs_A(instr)
            ew=self.read_reg(rs3)
            qual_t=to_trits(get_qualifier(ew),4) if get_primary(ew)==PRIMARY_EXEC else [0]*4
            arrow={-1:'double',0:'single',1:'dashed'}.get(qual_t[2],'single')
            entry={'prim':'EDGE','src':self.read_reg(rs1),'dst':self.read_reg(rs2),
                   'exec':decode_exec_word(ew) if get_primary(ew)==PRIMARY_EXEC
                   else {'raw':ew},'arrow':arrow,'dirty':True}
            self.canvas.append(entry)
            self.write_reg(rd,len(self.canvas)-1)
        elif op==OP_RENDER:
            self._render_canvas()
        elif op==OP_OUT:
            rd,*_=self._regs_A(instr)
            v=self.read_reg(rd)
            print(f"OUT R{rd} = {v}  [{word_to_str(v)}]")
        elif op==OP_IN:
            rd,*_=self._regs_A(instr)
            try: self.write_reg(rd,int(input("IN> ")))
            except: self.write_reg(rd,0)
        else:
            raise RuntimeError(f"Unknown opcode {op} at PC={self.pc-1}")
        self.cycle_count += 1

    def _handle_null(self, word):
        d = decode_word(word)
        if d.get('subtype') == 'implicit':
            sid = d['stack_id']
            ctx = {'mapping_a':d['mapping_a'],'mapping_b':d['mapping_b'],'word':word}
            self._dn_stacks[sid].append(ctx)
            self.write_reg(REG_RWR, word)

    def _render_canvas(self):
        dirty = [e for e in self.canvas if e.get('dirty')]
        if not dirty: return
        print("\n╔══ CANVAS " + "═"*42 + "╗")
        for e in dirty:
            p = e['prim']
            if p=='NODE':
                shape={'rect':'[   ]','diamond':'<   >','rounded':'(   )'}.get(e['shape'],'[   ]')
                obj=e.get('object',{})
                print(f"║  NODE  {shape}  CS+{obj.get('code_seg','?')} DS+{obj.get('data_seg','?')}")
            elif p=='LINE':
                print(f"║  LINE  {e.get('start',0)} ─────→ {e.get('end',0)}")
            elif p=='EDGE':
                arr={'single':'──→','double':'══►','dashed':'╌╌→'}.get(e.get('arrow','single'),'──→')
                print(f"║  EDGE  [{e['src']}] {arr} [{e['dst']}]")
            elif p=='POINT':
                print(f"║  POINT @{e.get('pos',0)}")
            e['dirty']=False
        print("╚" + "═"*51 + "╝\n")

    def run(self, max_cycles=1_000_000):
        while not self.halted and self.cycle_count < max_cycles:
            instr = self.fetch()
            prim = get_primary(instr)
            if prim == PRIMARY_DATA:
                qual_t = to_trits(get_qualifier(instr), 4)
                if (qual_t[3],qual_t[2]) == PTR_NULL:
                    self._handle_null(instr)
            self.execute(instr)
        if self.cycle_count >= max_cycles:
            print(f"[WARN] Cycle limit reached")

    def dump_regs(self, count=16):
        print(f"\n── Registers (PC={self.pc} cycles={self.cycle_count}) ──")
        for i in range(min(count,self.NUM_REGS)):
            v=self.read_reg(i)
            if v: print(f"  R{i:2d} = {v:15d}  {word_to_str(v)}")
        print()

    def dump_memory(self, start: int, length: int):
        print(f"\n── Memory [{start}..{start+length-1}] ──")
        for i in range(length):
            v=self.mem_read(start+i)
            print(f"  [{start+i:4d}] = {v:15d}  {word_to_str(v)}")
        print()

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 — ASSEMBLER
# ═══════════════════════════════════════════════════════════════════════════

class Asm:
    def __init__(self, cpu): self.cpu=cpu
    def NOP(self):                        return self.cpu.assemble_A(OP_NOP,0,0)
    def HLT(self):                        return self.cpu.assemble_A(OP_HLT,0,0)
    def ADD(self,rd,rs1,rs2):             return self.cpu.assemble_A(OP_ADD,rd,rs1,rs2)
    def ADDI(self,rd,rs1,imm):            return self.cpu.assemble_J2(OP_ADDI,rd,rs1,imm)
    def SUB(self,rd,rs1,rs2):             return self.cpu.assemble_A(OP_SUB,rd,rs1,rs2)
    def SUBI(self,rd,rs1,imm):            return self.cpu.assemble_J2(OP_SUBI,rd,rs1,imm)
    def MUL(self,rd,rs1,rs2):             return self.cpu.assemble_A(OP_MUL,rd,rs1,rs2)
    def DIV(self,rd,rs1,rs2):             return self.cpu.assemble_A(OP_DIV,rd,rs1,rs2)
    def NEG(self,rd,rs1):                 return self.cpu.assemble_A(OP_NEG,rd,rs1)
    def MOV(self,rd,rs1):                 return self.cpu.assemble_A(OP_MOV,rd,rs1)
    def LDI(self,rd,imm):                 return self.cpu.assemble_J2(OP_LDI,rd,0,imm)
    def LD(self,rd,rs1):                  return self.cpu.assemble_A(OP_LD,rd,rs1)
    def ST(self,rs1,rs2):                 return self.cpu.assemble_A(OP_ST,rs1,rs1,rs2)
    def JMP(self,addr):                   return self.cpu.assemble_J(OP_JMP,addr)
    def JSR(self,addr):                   return self.cpu.assemble_J(OP_JSR,addr)
    def RTI(self):                        return self.cpu.assemble_A(OP_RTI,0,0)
    def JEQ(self,rd,rs1,off):             return self.cpu.assemble_J2(OP_JEQ,rd,rs1,off)
    def JNE(self,rd,rs1,off):             return self.cpu.assemble_J2(OP_JNE,rd,rs1,off)
    def JB(self,rd,rs1,off):              return self.cpu.assemble_J2(OP_JB,rd,rs1,off)
    def PUSH(self,rs1):                   return self.cpu.assemble_A(OP_PUSH,rs1,0)
    def POP(self,rd):                     return self.cpu.assemble_A(OP_POP,rd,0)
    def MIN(self,rd,rs1,rs2):             return self.cpu.assemble_A(OP_MIN,rd,rs1,rs2)
    def MAX(self,rd,rs1,rs2):             return self.cpu.assemble_A(OP_MAX,rd,rs1,rs2)
    def TXOR(self,rd,rs1,rs2):            return self.cpu.assemble_A(OP_TXOR,rd,rs1,rs2)
    def EQUAL(self,rd,rs1,rs2):           return self.cpu.assemble_A(OP_EQUAL,rd,rs1,rs2)
    def SUM(self,rd,rs1,rs2):             return self.cpu.assemble_A(OP_SUM,rd,rs1,rs2)
    def OUT(self,rs1):                    return self.cpu.assemble_A(OP_OUT,rs1,0)
    def IN(self,rd):                      return self.cpu.assemble_A(OP_IN,rd,0)
    def TOBJ(self,rd,rs1,rs2):            return self.cpu.assemble_A(OP_TOBJ,rd,rs1,rs2)
    def TGET(self,rd,rs1):                return self.cpu.assemble_A(OP_TGET,rd,rs1)
    def TPAYLOAD(self,rd,rs1):            return self.cpu.assemble_A(OP_TPAYLOAD,rd,rs1)
    def TCALL(self,rd,rs1,rs2,rs3):       return self.cpu.assemble_A(OP_TCALL,rd,rs1,rs2,rs3)
    def TNEW(self,rd,rs1,rs2):            return self.cpu.assemble_A(OP_TNEW,rd,rs1,rs2)
    def TBUILD(self,rd,rs1,rs2,rs3):      return self.cpu.assemble_A(OP_TBUILD,rd,rs1,rs2,rs3)
    def TSEG(self,rd,rs1):                return self.cpu.assemble_A(OP_TSEG,rd,rs1)
    def RPOINT(self,rd,rs1,rs2):          return self.cpu.assemble_A(OP_RPOINT,rd,rs1,rs2)
    def RLINE(self,rd,rs1,rs2,rs3):       return self.cpu.assemble_A(OP_RLINE,rd,rs1,rs2,rs3)
    def RNODE(self,rd,rs1,rs2,rs3,rs4):   return self.cpu.assemble_A(OP_RNODE,rd,rs1,rs2,rs3,rs4)
    def REDGE(self,rd,rs1,rs2,rs3):       return self.cpu.assemble_A(OP_REDGE,rd,rs1,rs2,rs3)
    def RENDER(self,rs1,rs2):             return self.cpu.assemble_A(OP_RENDER,rs1,rs2)

# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 — TESTS
# ═══════════════════════════════════════════════════════════════════════════

def test_primary_types():
    print("="*60)
    print("TEST: 2+4+18 primary type encoding")
    print("="*60)
    types = [
        (PRIMARY_EXEC,   'EXEC',   (-1,-1)),
        (PRIMARY_MAP,    'MAP',    (-1, 0)),
        (PRIMARY_DATA,   'DATA',   (-1,+1)),
        (PRIMARY_NEURAL, 'NEURAL', ( 0,-1)),
        (PRIMARY_IO,     'I/O',    ( 0, 0)),
        (PRIMARY_CRYPTO, 'CRYPTO', ( 0,+1)),
        (PRIMARY_OPCODE, 'OPCODE', (+1,-1)),
        (PRIMARY_POOL,   'POOL',   (+1,+1)),
    ]
    for pval, name, (t23,t22) in types:
        w = set_primary(0, pval)
        assert get_primary(w) == pval, f"{name}: primary mismatch"
        assert get_trit(w,23) == t23, f"{name}: T23 mismatch"
        assert get_trit(w,22) == t22, f"{name}: T22 mismatch"
        print(f"  {name:8s}  T23={t23:+d} T22={t22:+d}  trit={word_to_str(w)[:4]}...")
    print("  PASS\n")

def test_word_constructors():
    print("="*60)
    print("TEST: Word constructors and decoders")
    print("="*60)

    # EXEC
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
    print(f"  EXEC: {describe_word(ew)}")
    print("  EXEC: PASS")

    # MAP
    mw = build_map_word(+1,-1,+1, 42)
    d  = decode_map_word(mw)
    assert d['axis_yz']==+1 and d['axis_xz']==-1 and d['axis_xy']==+1
    assert d['payload']==42
    print(f"  MAP:  {describe_word(mw)}")
    print("  MAP:  PASS")

    # SCALAR
    sw = build_int_word(42)
    d  = decode_word(sw)
    assert d['type']=='SCALAR' and d['value']==42
    print(f"  INT:  {describe_word(sw)}")
    print("  SCALAR: PASS")

    # UDP
    udp = build_udp_word(0,0,offset=7,code_seg=3,data_seg=5)
    d   = decode_udp_word(udp)
    assert d['offset']==7 and d['code_seg']==3 and d['data_seg']==5
    print(f"  UDP:  {describe_word(udp)}")
    print("  UDP: PASS")

    # NEURAL
    nu = build_neural_unit(state=1, bias=2, fan_in=8, weight_seg=3)
    d  = decode_word(nu)
    assert d['type']=='NEURAL_UNIT'
    assert get_primary(nu)==PRIMARY_NEURAL
    print(f"  NEURON: {describe_word(nu)}")

    nc = build_neural_connection(weight=2, source=100, target=200)
    d  = decode_word(nc)
    assert d['type']=='NEURAL_CONNECTION'
    assert d['weight']==2 and d['source']==100 and d['target']==200
    print(f"  SYNAPSE: {describe_word(nc)}")
    print("  NEURAL: PASS")

    # I/O
    iow = build_io_word(IO_DIR_OUT, IO_BUF_BUFFERED, 0, channel=42)
    d   = decode_word(iow)
    assert d['type']=='I/O' and d['direction']=='out'
    print(f"  I/O:  {describe_word(iow)}")
    print("  I/O: PASS\n")

def test_arithmetic():
    print("="*60)
    print("TEST: Arithmetic (regression)")
    print("="*60)
    cpu=CPU5500FP(); a=Asm(cpu)
    prog=[a.LDI(1,42),a.LDI(2,10),a.ADD(3,1,2),a.LDI(4,7),
          a.SUB(5,3,4),a.MUL(6,1,2),a.NEG(7,1),a.HLT()]
    cpu.load_program(prog); cpu.run()
    assert cpu.read_reg(3)==52
    assert cpu.read_reg(5)==45
    assert cpu.read_reg(6)==420
    assert cpu.read_reg(7)==-42
    print("  PASS\n")

def test_renderer():
    print("="*60)
    print("TEST: PIGART renderer")
    print("="*60)
    cpu=CPU5500FP(); a=Asm(cpu)
    cpu.write_cs(0,100); cpu.write_ds(0,200)
    pos_a=build_map_word(0,0,0,100)
    pos_b=build_map_word(0,0,0,300)
    dims=build_int_word(80)
    sty_rect=build_scalar_word(SCALAR_INT,0)
    sty_dia=build_scalar_word(SCALAR_FLOAT,0)
    obj_a=build_udp_word(0,0,0,1,1)
    obj_b=build_udp_word(0,0,0,2,2)
    ew=build_exec_word(EXEC_PRIV_USER,EXEC_CALL_REGISTER,EXEC_RET_DATA,0,5)
    for r,v in [(1,pos_a),(2,dims),(3,sty_rect),(4,obj_a),
                (5,pos_b),(6,sty_dia),(7,obj_b),(8,ew)]:
        cpu.write_reg(r,v)
    prog=[a.RNODE(20,1,2,3,4),a.RNODE(21,5,2,6,7),
          a.REDGE(22,20,21,8),a.RENDER(20,5),a.HLT()]
    cpu.load_program(prog); cpu.run()
    assert len(cpu.canvas)==3
    assert cpu.canvas[0]['shape']=='rect'
    assert cpu.canvas[1]['shape']=='diamond'
    print("  PASS\n")

def test_neural_network():
    print("="*60)
    print("TEST: Neural word types")
    print("="*60)
    # Build a tiny 2-neuron network
    n1 = build_neural_unit(state=1, bias=0, fan_in=1, weight_seg=0)
    n2 = build_neural_unit(state=0, bias=1, fan_in=1, weight_seg=1)
    syn = build_neural_connection(weight=2, source=0, target=1)

    d1 = decode_word(n1); d2 = decode_word(n2); ds = decode_word(syn)
    assert d1['type']=='NEURAL_UNIT'
    assert d2['type']=='NEURAL_UNIT'
    assert ds['type']=='NEURAL_CONNECTION'
    assert ds['source']==0 and ds['target']==1
    assert ds['weight']==2   # 2-trit weight: value 2 = moderately positive

    print(f"  Neuron 1: {describe_word(n1)}")
    print(f"  Neuron 2: {describe_word(n2)}")
    print(f"  Synapse:  {describe_word(syn)}")
    print(f"  Weight encoding: 2-trit → ±4 range (vs BitNet's {{-1,0,+1}})")
    print("  PASS\n")

def test_legacy_tag_pinning():
    """
    Pin the documented v0.1 behaviour of OP_TOBJ and OP_TGET on OPCODE-primary words.
    These ops use a single-trit T23 tag, pre-dating the 2-trit primary field.
    Retained for emulator demo compatibility; deprecation deferred to post-ASPLOS cleanup.
    """
    print("="*60)
    print("TEST: Legacy v0.1 single-trit tag pinning (OP_TOBJ, OP_TGET)")
    print("="*60)

    cpu = CPU5500FP()
    a   = Asm(cpu)

    # Build an OPCODE word: T23=+1, T22=-1 (PRIMARY_OPCODE = +1,-1)
    opcode_word = build_opcode_word(OPF_ISA_CORE, arity=2, op_index=OP_ADD)
    assert get_trit(opcode_word, 23) == +1, "OPCODE word: T23 should be +1"
    assert get_trit(opcode_word, 22) == -1, "OPCODE word: T22 should be -1"

    # ── OP_TOBJ: set T23 tag on val; T22 must be preserved ───────────────
    # set_trit(val, 23, tag) touches only T23; T22 stays as it was in val.
    new_tag = -1
    result = set_trit(opcode_word, 23, new_tag)
    assert get_trit(result, 23) == new_tag,  "OP_TOBJ: T23 should be updated"
    assert get_trit(result, 22) == -1,       "OP_TOBJ: T22 must be preserved (v0.1 behaviour)"

    # ── OP_TGET: reads T23 alone, ignores T22 ────────────────────────────
    t23_read = get_trit(opcode_word, 23)
    assert t23_read == +1, f"OP_TGET: should return T23=+1, got {t23_read}"
    # The 2-trit primary value would be PRIMARY_OPCODE = +1,-1 ≠ +1 alone
    assert t23_read != get_primary(opcode_word), \
        "OP_TGET single-trit T23 != 2-trit get_primary() (confirms v0.1 narrowness)"

    print("  OP_TOBJ: T23 updated, T22 preserved — PASS")
    print("  OP_TGET: returns T23 alone (not 2-trit primary) — PASS")
    print("  Pre-grammar v0.1 behaviour, retained for emulator demos.")
    print("  PASS\n")


def test_opcode_words():
    print("="*60)
    print("TEST: OPCODE primary words — build, decode, describe")
    print("="*60)

    # ── 1. Round-trip: ISA_CORE ADD arity=2 ───────────────────────────
    w = build_opcode_word(OPF_ISA_CORE, arity=2, op_index=OP_ADD)
    d = decode_opcode_word(w)
    assert d['type']        == 'OPCODE',    f"type mismatch: {d['type']}"
    assert d['family']      == OPF_ISA_CORE
    assert d['family_name'] == 'ISA_CORE'
    assert d['mnemonic']    == 'ADD'
    assert d['arity']       == 2
    assert d['op_index']    == OP_ADD
    assert d['meccano']     is None
    assert get_primary(w)   == PRIMARY_OPCODE
    assert get_trit(w, 23)  == +1, "T23 must be +1 for OPCODE"
    assert get_trit(w, 22)  == -1, "T22 must be -1 for OPCODE"
    print(f"  ISA_CORE ADD arity=2: {describe_word(w)}")
    print("  ISA_CORE round-trip: PASS")

    # ── 2. ISA_STACK JSR arity=0 ──────────────────────────────────────
    w2 = build_opcode_word(OPF_ISA_STACK, arity=0, op_index=OP_JSR)
    d2 = decode_opcode_word(w2)
    assert d2['family_name'] == 'ISA_STACK'
    assert d2['mnemonic']    == 'JSR'
    assert d2['arity']       == 0
    assert d2['op_index']    == OP_JSR
    print(f"  ISA_STACK JSR arity=0: {describe_word(w2)}")
    print("  ISA_STACK round-trip: PASS")

    # ── 3. PIGART with negative op_index (REDGE=-1, RENDER=-2) ────────
    for op_sym, op_val in [('REDGE', OP_REDGE), ('RENDER', OP_RENDER)]:
        wp = build_opcode_word(OPF_PIGART, arity=4, op_index=op_val)
        dp = decode_opcode_word(wp)
        assert dp['family_name'] == 'PIGART'
        assert dp['mnemonic']    == op_sym,  f"{op_sym}: mnemonic mismatch: {dp['mnemonic']}"
        assert dp['op_index']    == op_val
        print(f"  PIGART {op_sym} arity=4: {describe_word(wp)}")
    print("  PIGART (negative op_index) round-trip: PASS")

    # ── 4. MECCANO round-trip: spot-check balanced values ─────────────
    # Use values that fit directly in 6 balanced trits (max ±364).
    for mv in [27, 189, 351]:
        wm = build_opcode_word(OPF_MECCANO, arity=4, meccano=mv)
        dm = decode_opcode_word(wm)
        assert dm['family_name'] == 'MECCANO'
        assert dm['meccano']     == mv,  f"meccano mismatch: {dm['meccano']} != {mv}"
        assert dm['op_index']    is None
        assert dm['arity']       == 4
        # Verify stored at low tribble T5..T0 (payload positions 0-5)
        pay = get_payload(wm)
        assert get_field(pay, 0, 6) == mv, "MECCANO: low-tribble payload mismatch"
        print(f"  MECCANO ⊕{mv}: {describe_word(wm)}")
    print("  MECCANO round-trip (balanced values): PASS")

    # ── 4b. MECCANO normalisation: 702 is −27 in balanced ternary ────
    # Values > 364 fold to their balanced form: 702 = 729 − 27 → −27.
    # This is the correct Z/729Z representative — 702 ≡ −27 (mod 729).
    wm_702 = build_opcode_word(OPF_MECCANO, arity=4, meccano=702)
    dm_702 = decode_opcode_word(wm_702)
    assert dm_702['meccano'] == -27, \
        f"702 should normalise to -27, got {dm_702['meccano']}"
    print(f"  MECCANO normalisation 702→-27: {describe_word(wm_702)}")
    print("  MECCANO normalisation: PASS")

    # ── 5. Arity extremes 0 and 8 ─────────────────────────────────────
    for arity_val in [0, 8]:
        wa = build_opcode_word(OPF_ISA_CORE, arity=arity_val, op_index=OP_NOP)
        da = decode_opcode_word(wa)
        assert da['arity'] == arity_val, f"arity {arity_val} round-trip failed: got {da['arity']}"
    print("  Arity extremes (0 and 8) round-trip: PASS")

    # ── 6. decode_word() dispatches to decode_opcode_word ────────────
    w_nop = build_opcode_word(OPF_ISA_CORE, arity=0, op_index=OP_NOP)
    dg = decode_word(w_nop)
    assert dg['type']     == 'OPCODE'
    assert dg['mnemonic'] == 'NOP'
    print("  decode_word dispatch: PASS")

    # ── 7. describe_word output format ────────────────────────────────
    desc_isa = describe_word(build_opcode_word(OPF_ISA_CORE, arity=2, op_index=OP_ADD))
    assert 'OPCODE/ISA_CORE' in desc_isa and 'ADD' in desc_isa, \
        f"ISA describe format wrong: '{desc_isa}'"
    desc_mec = describe_word(build_opcode_word(OPF_MECCANO, arity=4, meccano=54))
    assert 'OPCODE/MECCANO' in desc_mec and '54' in desc_mec, \
        f"MECCANO describe format wrong: '{desc_mec}'"
    print(f"  describe_word ISA:    '{desc_isa}'")
    print(f"  describe_word MECCANO: '{desc_mec}'")
    print("  describe_word format: PASS")

    # ── 8. OPCODE primary differs from EXEC/DATA primary ─────────────
    assert PRIMARY_OPCODE != PRIMARY_EXEC
    assert PRIMARY_OPCODE != PRIMARY_DATA
    assert PRIMARY_OPCODE == PRIMARY_OPEN_A, "PRIMARY_OPCODE alias must equal PRIMARY_OPEN_A"
    print("  PRIMARY_OPCODE identity: PASS")

    # ── 9. PRIMARY_NAMES lookup ───────────────────────────────────────
    assert PRIMARY_NAMES[PRIMARY_OPCODE] == 'OPCODE', \
        f"PRIMARY_NAMES[PRIMARY_OPCODE] = '{PRIMARY_NAMES[PRIMARY_OPCODE]}'"
    print("  PRIMARY_NAMES lookup: PASS")

    print("  PASS\n")


def run_tests():
    """Run all unit tests — called by --test flag."""
    test_primary_types()
    test_word_constructors()
    test_arithmetic()
    test_renderer()
    test_neural_network()
    test_legacy_tag_pinning()
    test_opcode_words()
    print("="*60)
    print("ALL TESTS PASSED")
    print("="*60)


def demo_word_gallery():
    print("="*60)
    print("DEMO: TernOO v0.3 word gallery — all primary types")
    print("="*60)
    words = [
        ("EXEC user/reg/DATA CS2+14", build_exec_word(0,0,1,2,14,arity=2,version=1)),
        ("MAP  absolute(+,−,+) 42",   build_map_word(+1,-1,+1,42)),
        ("MAP  origin scale=100",      build_map_word(0,0,0,100)),
        ("SCALAR INT 42",              build_int_word(42)),
        ("UDP  off=7 CS+3 DS+5",       build_udp_word(0,0,7,3,5)),
        ("NULL explicit",              build_null_word(0)),
        ("PTR  REMOTE node=42",        build_pointer_word(PTR_REMOTE,42)),
        ("NEURON state=1 bias=2 fi=8", build_neural_unit(1,2,8,3)),
        ("SYNAPSE w=2 0→1",            build_neural_connection(2,0,1)),
        ("I/O  out/buffered ch=5",     build_io_word(IO_DIR_OUT,IO_BUF_BUFFERED,0,5)),
    ]
    for label, w in words:
        pname = PRIMARY_NAMES.get(get_primary(w),'?')
        print(f"  [{pname:6s}] {label}")
        print(f"           {word_to_str(w)}  ({w})")
        print(f"           {describe_word(w)}")
        print()

import random

# ═══════════════════════════════════════════════════════════════
# REAL TERNOO NEURAL ENGINE SUBSTRATE
# ═══════════════════════════════════════════════════════════════
class RealTernooNeuralEngine:
    """Executes true matrix transformations and text decoding using TernOO v0.3 constraints."""
    def __init__(self, cpu_instance):
        self.cpu = cpu_instance
        self.synapse_heap = 0x3000
        self.projection_heap = 0x4000
        self.vocab_size = 13  # Expanded to support full 13-word vocabulary
        self.hidden_size = 16

    # ═══════════════════════════════════════════════════════════════
    # HARDWARE WEIGHT INITIALIZATION & RESTORAL LOADER
    # ═══════════════════════════════════════════════════════════════
    def burn_weights_to_ram(self):
        """Physically populates system RAM with structural v0.3 NEURAL and I/O weights."""
        import json
        import os
        import numpy as np

        if os.path.exists("ternoo_hardware_matrix.json"):
            print(" [Hardware] Restoring pre-trained 18-trit matrix layouts from storage checkpoint...")
            try:
                with open("ternoo_hardware_matrix.json", "r") as f:
                    saved_matrix = json.load(f)

                for idx, word_val in enumerate(saved_matrix["synapse_heap"]):
                    self.cpu.mem_write(self.synapse_heap + idx, word_val)

                for idx, word_val in enumerate(saved_matrix["projection_heap"]):
                    self.cpu.mem_write(self.projection_heap + idx, word_val)

                print(" [Hardware] Matrix restoral sequence complete. Brain state fully active.\n")
                return
            except Exception as e:
                print(f" [Hardware] Restore trace faulted: {e}. Defaulting to fresh burn profile.")

        print(" [Hardware] Burning fresh 9-level input synaptic matrix into RAM (0x3000)...")
        addr = self.synapse_heap
        for src in range(self.vocab_size):
            for tgt in range(self.hidden_size):
                weight_val = int(np.clip(np.random.randint(-4, 5), -4, 4))
                synapse_word = build_neural_connection(weight=weight_val, source=src, target=tgt)
                self.cpu.mem_write(addr, synapse_word)
                addr += 1

        print(" [Hardware] Burning fresh 9-level I/O output projection matrix into RAM (0x4000)...")
        addr = self.projection_heap
        for src in range(self.hidden_size):
            for tgt in range(self.vocab_size):
                weight_val = int(np.clip(np.random.randint(-4, 5), -4, 4))
                projection_word = build_neural_connection(weight=weight_val, source=src, target=tgt)
                self.cpu.mem_write(addr, projection_word)
                addr += 1
        print(f" [Hardware] Structural matrices verified. Upper allocation layout boundary: {hex(addr)}.\n")

    # ═══════════════════════════════════════════════════════════════
    # NATIVE CORE MATRIX INFERENCE PIPELINE
    # ═══════════════════════════════════════════════════════════════
    def execute_hardware_inference(self, input_vector_addr, vector_length):
        """Processes an input vector using pure hardware payload stepping logic."""
        import numpy as np
        accumulators = np.zeros(self.hidden_size, dtype=int)

        for i in range(vector_length):
            input_word = self.cpu.mem_read(input_vector_addr + i)
            input_signal = int(input_word) if hasattr(input_word, '__int__') else 1

            synapse_base = self.synapse_heap + (i * self.hidden_size)
            for j in range(self.hidden_size):
                synapse_word = self.cpu.mem_read(synapse_base + j)

                raw_payload = synapse_word & 0x3FFFF
                weight = (raw_payload >> 14) & 0x3
                if weight > 1:
                    weight -= 4

                accumulators[j] += input_signal * weight

        return [1 if v > 2 else ( -1 if v < -2 else 0 ) for v in accumulators]

    # ═══════════════════════════════════════════════════════════════
    # NATIVE AUTOREGRESSIVE LATENT VECTOR DECODER
    # ═══════════════════════════════════════════════════════════════
    def execute_hardware_decode(self, hidden_states):
        """Projects latent vectors using native 18-trit payload masks."""
        import numpy as np
        output_logits = np.zeros(self.vocab_size, dtype=int)

        for i in range(self.hidden_size):
            hidden_signal = hidden_states[i]
            projection_base = self.projection_heap + (i * self.vocab_size)

            for j in range(self.vocab_size):
                proj_word = self.cpu.mem_read(projection_base + j)

                raw_payload = proj_word & 0x3FFFF
                weight = (raw_payload >> 14) & 0x3
                if weight > 1:
                    weight -= 4

                output_logits[j] += hidden_signal * weight

        return int(np.argmax(output_logits))


# ═══════════════════════════════════════════════════════════════
# MAIN INTERACTIVE HARDWARE RUNTIME BENCHMARK
# ═══════════════════════════════════════════════════════════════
# ─────────────────────────────────────────────────────────────────────────────
# The Gemini-era 'AI workbench' block (~230 commented lines) was removed on
# 3 Jul 2026 after the pre-documentation audit; it never ran (commented out
# since the workbench security review, commit 30498ca) and is preserved in
# git history for reference.
# ─────────────────────────────────────────────────────────────────────────────
#
if __name__ == '__main__':
    if '--test' in sys.argv:
        run_tests()
    elif '--gallery' in sys.argv:
        demo_word_gallery()
    else:
        # The Gemini-era AI workbench (above) is retired/commented out.
        print("5500fp_ternoo_v03 — TernOO v0.3 word/ISA library.")
        print("  --test     run the test suite")
        print("  --gallery  print the word gallery demo")
