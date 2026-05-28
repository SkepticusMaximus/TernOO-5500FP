#!/usr/bin/env python3
"""
TernOO Word Inspector  v0.1.0
==============================
Interactive REPL for exploring, constructing, and inspecting TernOO words
on the 5500FP emulator. Run this for hands-on experimentation.

Usage:
    python3 ternoo_inspector.py
    python3 ternoo_inspector.py --demo        # run all demos and exit
    python3 ternoo_inspector.py --test        # run test suite and exit

Requires: 5500fp_ternoo_v02.py in the same directory.

Commands at the REPL prompt:
    help                    show this help
    demo                    run all demonstration sequences
    quit / exit / q         exit

    -- Word construction --
    exec <priv> <call> <ret> <seg> <offset>     build EXEC word
    map  <yz> <xz> <xy> <payload>               build MAP word
    int  <value>                                 build SCALAR INTEGER word
    uint <value>                                 build SCALAR UNSIGNED word
    udp  <offset> <code_seg> <data_seg>          build USER-DEF POINTER word
    null                                         build explicit NULL word
    inull <stack_id> <qual> <map_a> <map_b>      build implicit NULL word
    ptr  <model> <payload>                       build POINTER word
      models: flat relative stack_rel field symbol remote weak

    -- Inspection --
    decode <integer>         decode a raw integer as a TernOO word
    trit   <integer>         show balanced ternary representation
    fields <integer>         show all 6 x 4-trit fields of a word
    reg    <n>               show register Rn contents (after loading a program)

    -- Running programs --
    load <file.py>           load and run a Python program file in emulator context
    run  <program_name>      run a named demo program (see 'demo' for list)
    trace on|off             enable/disable instruction trace

    -- System --
    regs                     dump all non-zero registers
    reset                    reset CPU to boot state
    mem  <addr> <len>        dump memory region
    canvas                   show current canvas scene graph
"""

import sys
import os
import readline
import traceback

# ── Locate and import the emulator ───────────────────────────────────────────

def _find_emulator():
    """Find 5500fp_ternoo_v03.py in likely locations."""
    candidates = [
        os.path.join(os.path.dirname(__file__), '5500fp_ternoo_v03.py'),
        os.path.join(os.getcwd(), '5500fp_ternoo_v03.py'),
        os.path.expanduser('~/5500fp/5500fp_ternoo_v03.py'),
        os.path.expanduser('~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/5500fp_ternoo_v03.py'),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

_emu_path = _find_emulator()
if _emu_path is None:
    print("ERROR: Cannot find 5500fp_ternoo_v03.py")
    print("Place ternoo_inspector.py in the same directory as the emulator.")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(_emu_path))
from importlib.util import spec_from_file_location, module_from_spec
_spec = spec_from_file_location("emu", _emu_path)
_emu = module_from_spec(_spec)

# Suppress __main__ execution
import unittest.mock
_orig_name = "__main__"
with unittest.mock.patch.object(_emu, "__name__", "emu"):
    _spec.loader.exec_module(_emu)

# Import everything from the emulator into our namespace
from importlib import import_module
globals().update({k: getattr(_emu, k) for k in dir(_emu) if not k.startswith('__')})

# ── Global CPU instance ───────────────────────────────────────────────────────

cpu = CPU5500FP()
a   = Asm(cpu)

# ── Display helpers ───────────────────────────────────────────────────────────

BOLD   = '\033[1m'
CYAN   = '\033[36m'
GREEN  = '\033[32m'
YELLOW = '\033[33m'
RED    = '\033[31m'
BLUE   = '\033[34m'
RESET  = '\033[0m'
DIM    = '\033[2m'

def c(text, colour): return f"{colour}{text}{RESET}"
def header(text):    print(f"\n{BOLD}{CYAN}{'━'*60}{RESET}")
def subhead(text):   print(f"{BOLD}{YELLOW}  {text}{RESET}")

def print_word(w, label=""):
    """Pretty-print a TernOO word with full decode."""
    d = decode_word(w)
    trit_str = word_to_str(w)
    desc = describe_word(w)
    prefix = f"{c(label, BOLD)}: " if label else ""
    print(f"  {prefix}{c(trit_str, GREEN)}  ({w})")
    print(f"  {DIM}→ {desc}{RESET}")

def print_separator():
    print(f"  {DIM}{'─'*56}{RESET}")

# ── Demo programs ─────────────────────────────────────────────────────────────

def demo_word_types():
    header("TernOO Word Type Gallery")
    print()

    subhead("EXEC words — function references with full calling contract")
    words = [
        ("user/register/DATA  CS2+14  arity=2  v1",
         build_exec_word(EXEC_PRIV_USER, EXEC_CALL_REGISTER, EXEC_RET_DATA,
                         seg_idx=2, offset=14, arity=2, version=1)),
        ("kernel/stack/EXEC   CS0+0",
         build_exec_word(EXEC_PRIV_KERNEL, EXEC_CALL_STACK, EXEC_RET_EXEC,
                         seg_idx=0, offset=0)),
        ("sandbox/message/MAP CS4+100",
         build_exec_word(EXEC_PRIV_SANDBOX, EXEC_CALL_MESSAGE, EXEC_RET_MAP,
                         seg_idx=4, offset=100, arity=1, version=3)),
    ]
    for label, w in words:
        print_word(w, label)
    print()

    subhead("MAP words — 3D octree positions")
    map_words = [
        ("ABSOLUTE_3D (+,−,+) mag=42",  build_map_word(+1,-1,+1, 42)),
        ("ON_PLANE YZ  Y=100 Z=200",    build_map_word( 0,+1,-1,  0)),
        ("ON_AXIS  X   val=847",         build_map_word(+1, 0, 0,847)),
        ("ORIGIN   scale=10",            build_map_word( 0, 0, 0, 10)),
    ]
    for label, w in map_words:
        print_word(w, label)
    print()

    subhead("SCALAR words — typed values")
    scalar_words = [
        ("INTEGER  42",      build_int_word(42)),
        ("INTEGER −42",      build_int_word(-42)),
        ("UNSIGNED 999",     build_uint_word(999)),
        ("FLOAT    3 (fp)",  build_scalar_word(SCALAR_FLOAT, 3)),
    ]
    for label, w in scalar_words:
        print_word(w, label)
    print()

    subhead("POINTER words — nine models")
    ptr_words = [
        ("FLAT     addr=847293",  build_pointer_word(PTR_FLAT,     847293)),
        ("RELATIVE off=−14",      build_pointer_word(PTR_RELATIVE, -14)),
        ("REMOTE   node=42",      build_pointer_word(PTR_REMOTE,   42)),
        ("WEAK     ref=1000",     build_pointer_word(PTR_WEAK,     1000)),
        ("SYMBOL   id=7",         build_pointer_word(PTR_SYMBOL,   7)),
        ("NULL explicit",         build_null_word(0)),
    ]
    for label, w in ptr_words:
        print_word(w, label)
    print()

    subhead("USER-DEF POINTER — self-describing object word")
    udp_variants = [
        ("base    offset=0  CS+1  DS+1",  build_udp_word( 0, 0,  0, 1, 1)),
        ("base    offset=7  CS+3  DS+12", build_udp_word( 0, 0,  7, 3,12)),
        ("sub(+,−) offset=14 CS+8 DS+8",  build_udp_word(+1,-1, 14, 8, 8)),
        ("meta(+,+) escape hatch",         build_udp_word(+1,+1,  0, 0, 0)),
    ]
    for label, w in udp_variants:
        print_word(w, label)
    print()

    subhead("NULL words — Double Null mechanism")
    null_words = [
        ("explicit null (payload=0)",  build_null_word(0)),
        ("implicit  ST3 qual=10 A=5 B=2",
         build_implicit_null(stack_id=3, qualifier=10, mapping_a=5, mapping_b=2)),
        ("implicit  ST0 qual=1  A=1 B=1",
         build_implicit_null(stack_id=0, qualifier=1,  mapping_a=1, mapping_b=1)),
    ]
    for label, w in null_words:
        print_word(w, label)
    print()


def demo_trit_arithmetic():
    header("Balanced Ternary Arithmetic Demo")
    print()

    subhead("Representing integers in balanced ternary")
    print(f"  {'Value':>15}  {'Balanced ternary (24 trits, MSB first)'}")
    print(f"  {'─'*15}  {'─'*40}")
    for v in [0, 1, -1, 2, -2, 3, -3, 13, -13, 42, -42,
              100, 364, -364, 1000, WORD_MAX, WORD_MIN]:
        print(f"  {v:>15}  {word_to_str(v)}")
    print()

    subhead("Ternary-native operations on {−1, 0, +1}")
    print(f"  {'A':>5} {'B':>5}  {'MIN':>5} {'MAX':>5} {'TXOR':>5} {'EQUAL':>5} {'SUM':>5}")
    print(f"  {'─'*5} {'─'*5}  {'─'*5} {'─'*5} {'─'*5}  {'─'*5} {'─'*5}")
    for a_val, b_val in [(-1,-1),(-1,0),(-1,1),(0,0),(0,1),(1,1)]:
        mn  = from_trits([min(a_val, b_val)])
        mx  = from_trits([max(a_val, b_val)])
        tx  = from_trits([((a_val+b_val)%3) if ((a_val+b_val)%3) != 2
                          else -1])
        eq  = 1 if a_val == b_val else -1
        sm  = max(-1, min(1, a_val + b_val))
        sym = {-1:'N', 0:'Z', 1:'P'}
        print(f"  {sym[a_val]:>5} {sym[b_val]:>5}  "
              f"{sym[mn]:>5} {sym[mx]:>5} {sym[tx]:>5}  "
              f"{sym[eq]:>5} {sym[sm]:>5}")
    print()
    print(f"  {DIM}N=−1  Z=0  P=+1{RESET}")
    print()


def demo_segment_registers():
    header("Segment Register Demo")
    print()

    subhead("Setting up code segments and resolving EXEC words")
    cpu.reset()

    # Set up some code segments
    cpu.write_cs(0, 1000)
    cpu.write_cs(1, 5000)
    cpu.write_cs(2, 10000)
    cpu.write_ds(0, 2000)
    cpu.write_ds(1, 6000)

    print(f"  CS0 = {cpu.read_cs(0):8d}   DS0 = {cpu.read_ds(0):8d}")
    print(f"  CS1 = {cpu.read_cs(1):8d}   DS1 = {cpu.read_ds(1):8d}")
    print(f"  CS2 = {cpu.read_cs(2):8d}")
    print()

    ew1 = build_exec_word(EXEC_PRIV_USER, EXEC_CALL_REGISTER, EXEC_RET_DATA,
                          seg_idx=0, offset=14)
    ew2 = build_exec_word(EXEC_PRIV_KERNEL, EXEC_CALL_STACK, EXEC_RET_EXEC,
                          seg_idx=2, offset=50)
    udp = build_udp_word(0, 0, offset=7, code_seg=3, data_seg=12)

    print_word(ew1, "EXEC CS0+14")
    print(f"  {DIM}→ resolves to address: {cpu.resolve_exec(ew1)}{RESET}")
    print()
    print_word(ew2, "EXEC CS2+50")
    print(f"  {DIM}→ resolves to address: {cpu.resolve_exec(ew2)}{RESET}")
    print()
    print_word(udp, "UDP  CS0+3, DS0+12")
    print(f"  {DIM}→ code at: {cpu.resolve_udp_code(udp)}"
          f"  data at: {cpu.resolve_udp_data(udp)}{RESET}")
    print()


def demo_double_null():
    header("Double Null Mechanism Demo")
    print()

    cpu.reset()

    subhead("Building and pushing implicit NULL words")
    contexts = [
        (0, 10, 5, 2,  "FORMAT context on ST0"),
        (1, 20, 8, 3,  "LOOP context on ST1"),
        (2, 30, 1, 1,  "ERROR-HANDLER on ST2"),
        (3, 40, 7, 4,  "CHAR type on ST3"),
    ]

    for sid, qual, ma, mb, label in contexts:
        inull = build_implicit_null(stack_id=sid, qualifier=qual,
                                    mapping_a=ma, mapping_b=mb)
        cpu._handle_null(inull)
        d = decode_word(inull)
        print(f"  {c(label, YELLOW)}")
        print_word(inull)
        print(f"  {DIM}Stack {sid} depth: {len(cpu._dn_stacks[sid])}{RESET}")
        print()

    subhead("RWR holds most recent context")
    print_word(cpu.read_reg(REG_RWR), "RWR")
    print()

    subhead("Explicit NULL — plain nothing")
    enull = build_null_word(0)
    print_word(enull, "explicit NULL")
    d = decode_word(enull)
    print(f"  {DIM}subtype: {d['subtype']}{RESET}")
    print()


def demo_renderer():
    header("PIGART Renderer Demo — Flowchart Scene Graph")
    print()

    cpu.reset()
    cpu.write_cs(0, 100)
    cpu.write_ds(0, 200)

    a_asm = Asm(cpu)

    # Build a three-symbol flowchart: START → PROCESS → DECISION
    start_pos  = build_map_word(0, 0, 0, 50)    # origin-relative, coord=50
    proc_pos   = build_map_word(0, 0, 0, 200)
    dec_pos    = build_map_word(0, 0, 0, 350)

    dims       = build_int_word(80)
    start_obj  = build_udp_word(0, 0, offset=0, code_seg=0, data_seg=0)
    proc_obj   = build_udp_word(0, 0, offset=0, code_seg=1, data_seg=1)
    dec_obj    = build_udp_word(0, 0, offset=0, code_seg=2, data_seg=2)

    start_style = build_scalar_word(SCALAR_UINT,  0)  # rounded rectangle
    proc_style  = build_scalar_word(SCALAR_INT,   0)  # rectangle
    dec_style   = build_scalar_word(SCALAR_FLOAT, 0)  # diamond

    flow_exec   = build_exec_word(EXEC_PRIV_USER, EXEC_CALL_REGISTER,
                                  EXEC_RET_DATA, seg_idx=0, offset=5)
    cond_exec   = build_exec_word(EXEC_PRIV_USER, EXEC_CALL_MESSAGE,
                                  EXEC_RET_DATA, seg_idx=0, offset=6)

    # Load into registers
    cpu.write_reg(1,  start_pos);  cpu.write_reg(2,  dims)
    cpu.write_reg(3,  start_style);cpu.write_reg(4,  start_obj)
    cpu.write_reg(5,  proc_pos);   cpu.write_reg(6,  proc_style)
    cpu.write_reg(7,  proc_obj);   cpu.write_reg(8,  dec_pos)
    cpu.write_reg(9,  dec_style);  cpu.write_reg(10, dec_obj)
    cpu.write_reg(11, flow_exec);  cpu.write_reg(12, cond_exec)

    prog = [
        a_asm.RNODE(20, 1,  2, 3,  4),   # START symbol → canvas[0]
        a_asm.RNODE(21, 5,  2, 6,  7),   # PROCESS symbol → canvas[1]
        a_asm.RNODE(22, 8,  2, 9, 10),   # DECISION symbol → canvas[2]
        a_asm.REDGE(23, 20, 21, 11),      # START→PROCESS via flow_exec
        a_asm.REDGE(24, 21, 22, 12),      # PROCESS→DECISION via cond_exec
        a_asm.RENDER(20, 5),
        a_asm.HLT(),
    ]
    cpu.load_program(prog)
    cpu.run()

    subhead("Canvas scene graph (5 entries):")
    for i, entry in enumerate(cpu.canvas):
        p = entry['prim']
        if p == 'NODE':
            shape = {'rect':'[PROCESS]','diamond':'<DECISION>',
                     'rounded':'(START/END)'}.get(entry['shape'], entry['shape'])
            obj = entry.get('object', {})
            print(f"  canvas[{i}]  NODE  {shape}  "
                  f"CS+{obj.get('code_seg','?')} DS+{obj.get('data_seg','?')}")
        elif p == 'EDGE':
            arr = {'single':'──→','double':'══►','dashed':'╌╌→'}.get(
                entry.get('arrow','single'), '──→')
            ex = entry.get('exec', {})
            print(f"  canvas[{i}]  EDGE  [{entry['src']}] {arr} [{entry['dst']}]  "
                  f"EXEC priv={ex.get('privilege','?')} call={ex.get('call_style','?')}")
    print()
    subhead("Same data rendered as ASCII art:")
    # Re-dirty all entries for display
    for e in cpu.canvas: e['dirty'] = True
    cpu._render_canvas()


def demo_full_program():
    header("Full Program Demo — Fibonacci Sequence")
    print()
    subhead("Computing first 8 Fibonacci numbers, storing in memory")

    cpu.reset()
    a_fib = Asm(cpu)

    # Fibonacci: R1=a=0, R2=b=1, R3=loop count, R4=temp, R5=mem addr
    prog = [
        # Setup
        a_fib.LDI(1, 0),         # R1 = a = 0
        a_fib.LDI(2, 1),         # R2 = b = 1
        a_fib.LDI(3, 8),         # R3 = count = 8
        a_fib.LDI(5, 400),       # R5 = mem base addr
        # Store first two
        a_fib.ST(1, 5),          # mem[400] = 0
        a_fib.ADDI(5, 5, 1),
        a_fib.ST(2, 5),          # mem[401] = 1
        a_fib.ADDI(5, 5, 1),
        a_fib.LDI(3, 6),         # 6 more to compute
        # Loop (addr 8):
        a_fib.ADD(4, 1, 2),      # R4 = a + b
        a_fib.MOV(1, 2),         # a = b
        a_fib.MOV(2, 4),         # b = a+b
        a_fib.ST(4, 5),          # mem[addr] = new value
        a_fib.ADDI(5, 5, 1),     # addr++
        a_fib.SUBI(3, 3, 1),     # count--
        a_fib.JNE(3, 0, -7),     # if count != 0, loop back
        a_fib.HLT(),
    ]
    cpu.load_program(prog)
    cpu.run()

    print(f"  Fibonacci sequence (stored at addresses 400–407):")
    vals = [cpu.mem_read(400 + i) for i in range(8)]
    print(f"  {vals}")
    print(f"  {[word_to_str(v, 8) for v in vals[:4]]}  (first 4, 8-trit view)")
    print()
    print(f"  CPU cycles used: {cpu.cycle_count}")
    print()

    subhead("Now wrapping results as SCALAR INTEGER TernOO words")
    for i, v in enumerate(vals):
        w = build_int_word(v)
        print(f"  fib({i}) = {v:3d}  →  {describe_word(w)}")
    print()


# ── Command parser ─────────────────────────────────────────────────────────────

MODEL_MAP = {
    'flat': PTR_FLAT, 'relative': PTR_RELATIVE, 'stack_rel': PTR_STACK_REL,
    'field': PTR_FIELD, 'null': PTR_NULL, 'symbol': PTR_SYMBOL,
    'remote': PTR_REMOTE, 'weak': PTR_WEAK, 'user': PTR_USER_DEF,
}

def parse_int(s):
    """Parse integer, accepting decimal, 0x hex, 0b binary, 0t ternary."""
    s = s.strip()
    if s.startswith('0t'):
        # Ternary literal: 0t+-0+- → from +/−/0 notation
        trits = [{'+':-1,'0':0,'-':1}.get(c, 0)  # note: MSB first so reversed
                 for c in reversed(s[2:])]
        return from_trits(trits)
    return int(s, 0)

def run_command(line):
    """Parse and execute one inspector command. Returns False to quit."""
    parts = line.strip().split()
    if not parts:
        return True
    cmd = parts[0].lower()
    args = parts[1:]

    try:
        if cmd in ('quit', 'exit', 'q'):
            return False

        elif cmd == 'help':
            print(__doc__)

        elif cmd == 'demo':
            demo_word_types()
            demo_trit_arithmetic()
            demo_segment_registers()
            demo_double_null()
            demo_renderer()
            demo_full_program()

        elif cmd == 'exec':
            if len(args) < 5:
                print("  Usage: exec <priv:−1/0/1> <call:−1/0/1> <ret:−1/0/1>"
                      " <seg:0-8> <offset>")
                return True
            priv, call, ret = int(args[0]), int(args[1]), int(args[2])
            seg, off = int(args[3]), int(args[4])
            arity = int(args[5]) if len(args) > 5 else 0
            ver   = int(args[6]) if len(args) > 6 else 0
            w = build_exec_word(priv, call, ret, seg, off, arity=arity, version=ver)
            print_word(w, "EXEC")

        elif cmd == 'map':
            if len(args) < 4:
                print("  Usage: map <yz:−1/0/1> <xz:−1/0/1> <xy:−1/0/1> <payload>")
                return True
            yz, xz, xy = int(args[0]), int(args[1]), int(args[2])
            payload = parse_int(args[3])
            w = build_map_word(yz, xz, xy, payload)
            print_word(w, "MAP")

        elif cmd == 'int':
            if not args: print("  Usage: int <value>"); return True
            w = build_int_word(parse_int(args[0]))
            print_word(w, "INTEGER")

        elif cmd == 'uint':
            if not args: print("  Usage: uint <value>"); return True
            w = build_uint_word(parse_int(args[0]))
            print_word(w, "UNSIGNED")

        elif cmd == 'udp':
            if len(args) < 3:
                print("  Usage: udp <offset> <code_seg> <data_seg>")
                return True
            off, cs, ds = int(args[0]), int(args[1]), int(args[2])
            w = build_udp_word(0, 0, off, cs, ds)
            print_word(w, "UDP")

        elif cmd == 'null':
            w = build_null_word(0)
            print_word(w, "NULL")

        elif cmd == 'inull':
            if len(args) < 4:
                print("  Usage: inull <stack_id:0-8> <qualifier> <mapping_a> <mapping_b>")
                return True
            w = build_implicit_null(int(args[0]), int(args[1]),
                                    int(args[2]), int(args[3]))
            print_word(w, "IMPLICIT NULL")

        elif cmd == 'ptr':
            if len(args) < 2:
                print("  Usage: ptr <model> <payload>")
                print("  Models:", ', '.join(MODEL_MAP.keys()))
                return True
            model = MODEL_MAP.get(args[0].lower())
            if model is None:
                print(f"  Unknown model '{args[0]}'. Models: {list(MODEL_MAP.keys())}")
                return True
            w = build_pointer_word(model, parse_int(args[1]))
            print_word(w, f"PTR({args[0].upper()})")

        elif cmd == 'decode':
            if not args: print("  Usage: decode <integer>"); return True
            w = parse_int(args[0])
            print_word(w, "decoded")

        elif cmd == 'trit':
            if not args: print("  Usage: trit <integer>"); return True
            v = parse_int(args[0])
            for width in [8, 12, 24]:
                print(f"  {width:2d}-trit: {word_to_str(v, width)}")
            print(f"  decimal: {v}")
            print(f"  trits (LSB first): {to_trits(v, 24)}")

        elif cmd == 'fields':
            if not args: print("  Usage: fields <integer>"); return True
            w = parse_int(args[0])
            f = [from_trits(to_trits(w, 24)[i*4:(i+1)*4]) for i in range(6)]
            print(f"  Word: {word_to_str(w)}")
            print(f"  F5(op)={f[5]:4d}  F4={f[4]:4d}  F3={f[3]:4d}"
                  f"  F2={f[2]:4d}  F1={f[1]:4d}  F0={f[0]:4d}")

        elif cmd == 'regs':
            cpu.dump_regs(81)

        elif cmd == 'reset':
            cpu.reset()
            print("  CPU reset.")

        elif cmd == 'mem':
            if len(args) < 2:
                print("  Usage: mem <addr> <length>")
                return True
            cpu.dump_memory(int(args[0]), int(args[1]))

        elif cmd == 'canvas':
            if not cpu.canvas:
                print("  Canvas is empty. Run a renderer demo first.")
            else:
                print(f"  Canvas: {len(cpu.canvas)} entries")
                for i, e in enumerate(cpu.canvas):
                    print(f"  [{i}] {e['prim']}  dirty={e['dirty']}")

        elif cmd == 'trace':
            if args and args[0].lower() == 'on':
                cpu._trace = True
                print("  Trace ON")
            else:
                cpu._trace = False
                print("  Trace OFF")

        elif cmd == 'run':
            name = args[0].lower() if args else ''
            demos = {
                'words':   demo_word_types,
                'trit':    demo_trit_arithmetic,
                'segs':    demo_segment_registers,
                'null':    demo_double_null,
                'render':  demo_renderer,
                'fib':     demo_full_program,
            }
            if name in demos:
                demos[name]()
            else:
                print(f"  Available: {list(demos.keys())}")

        else:
            print(f"  Unknown command: '{cmd}'.  Type 'help' for command list.")

    except Exception as e:
        print(f"  {RED}Error: {e}{RESET}")
        if '--verbose' in sys.argv:
            traceback.print_exc()

    return True


# ── REPL ───────────────────────────────────────────────────────────────────────

BANNER = f"""
{BOLD}{CYAN}TernOO Word Inspector  v0.1.0{RESET}
{DIM}5500FP balanced ternary processor — interactive exploration REPL{RESET}
{DIM}Emulator: {_emu_path}{RESET}

Type {c('demo', YELLOW)} to run all demonstrations.
Type {c('help', YELLOW)} for the full command reference.
Type {c('quit', YELLOW)} to exit.
"""

def main():
    if '--test' in sys.argv:
        # Run all demos as a smoke test
        demo_word_types()
        demo_trit_arithmetic()
        demo_segment_registers()
        demo_double_null()
        demo_renderer()
        demo_full_program()
        print(f"{GREEN}All demos completed successfully.{RESET}")
        return

    if '--demo' in sys.argv:
        demo_word_types()
        demo_trit_arithmetic()
        demo_segment_registers()
        demo_double_null()
        demo_renderer()
        demo_full_program()
        return

    print(BANNER)

    while True:
        try:
            line = input(f"{CYAN}ternoo>{RESET} ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not run_command(line):
            break

    print(f"{DIM}Goodbye.{RESET}")


if __name__ == '__main__':
    main()
