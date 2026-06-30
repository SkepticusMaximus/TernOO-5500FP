"""formula_t5asm.py — AST → t5asm arithmetic compiler (Sheet Runtime Track B).

The bottleneck primitive: walk a sheet_formula AST and emit t5asm that, when
executed, leaves the formula's integer result in a destination register.

Model (locked decisions A2/A3): a **register stack**. compile_ast(node, dst, …)
emits code leaving the result in R<dst>, using R<dst+1>, R<dst+2>… for
sub-expressions. With 81 registers (R0..R80, R0==0) there's ample depth and no
memory expression stack is needed.

Cell / widget / signal references resolve, at compile time, to a state-slot
data label via a resolver callback; the emitted code does `LI Rx, <label>;
LDW Rx, Rx, 0`. Static-extent ranges (A1:A5) unroll into chained ops at compile
time — no runtime loops.

Supported now: numbers, booleans, cell/widget/signal refs, + - * / (DIV guarded
against /0), comparisons (< > <= >= = == !=), unary minus, IF, and the
aggregate/scalar functions SUM/AVERAGE/MIN/MAX/COUNT/ABS/ROUND/MOD/POWER. String
functions and string-valued results are out of scope here (numeric engine) — see
the bundle report.
"""

from __future__ import annotations
import os
import importlib.util as _ilu

# Reuse the editor-side parser/range-expander.
_sf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'sheet_formula.py')
_sf_spec = _ilu.spec_from_file_location('sheet_formula', _sf_path)
sheet_formula = _ilu.module_from_spec(_sf_spec)
_sf_spec.loader.exec_module(sheet_formula)

# Instruction register fields are 4 balanced trits → only R0..R40 are
# addressable (encode_field clamps to ±40). The Phase 7b-4 compiler uses R0..R20
# (syscall args R1-R7, mouse R10/R11, temp R15, addr R20), so formula eval takes
# the clear high window R21..R40 (depth up to 19) — no clobber, no overflow.
_BASE_REG = 21
_MAX_REG = 40


class FormulaCompileError(Exception):
    pass


class _Ctx:
    """Resolver + unique-label state for one compilation."""
    def __init__(self, resolver):
        # resolver(ref) -> state-slot label or None.
        #   ref is a cell/name string, or ('widget', name, prop),
        #   or ('signal', name).
        self.resolver = resolver
        self._n = 0

    def label(self, prefix):
        self._n += 1
        return f"_fx_{prefix}_{self._n}"


def compile_ast(node, dst: int, resolver) -> list:
    """Top-level: emit t5asm leaving `node`'s value in R<dst>."""
    return _compile(node, dst, _Ctx(resolver))


def _compile(node, dst, ctx) -> list:
    if dst > _MAX_REG:
        raise FormulaCompileError("expression too deep for register stack")
    t = node[0]
    if t == 'num':
        return [f"    LI   R{dst}, {int(node[1])}"]
    if t == 'bool':
        return [f"    LI   R{dst}, {1 if node[1] else 0}"]
    if t == 'str':
        # Numeric engine: a bare string literal evaluates to 0 (documented).
        return [f"    LI   R{dst}, 0   ; (string literal — numeric engine)"]
    if t == 'ref':
        return _emit_load_slot(ctx.resolver(node[1]), dst, f"ref {node[1]}")
    if t == 'member':
        base = node[1]
        if base[0] == 'call' and base[1] == 'WIDGET' and base[2]:
            wname = base[2][0][1] if base[2][0][0] == 'str' else ''
            slot = ctx.resolver(('widget', wname, node[2]))
            return _emit_load_slot(slot, dst, f"WIDGET {wname}.{node[2]}")
        raise FormulaCompileError("unsupported member access")
    if t == 'unary':
        lines = _compile(node[2], dst, ctx)
        if node[1] == '-':
            lines.append(f"    SUB  R{dst}, R0, R{dst}   ; negate (0 - x)")
        return lines
    if t == 'bin':
        return _emit_binary(node[1], node[2], node[3], dst, ctx)
    if t == 'call':
        return _emit_call(node[1], node[2], dst, ctx)
    raise FormulaCompileError(f"unsupported node {t}")


def _emit_load_slot(slot, dst, why) -> list:
    if slot is None:
        return [f"    LI   R{dst}, 0   ; #NAME? ({why})"]
    return [f"    LI   R{dst}, {slot}",
            f"    LDW  R{dst}, R{dst}, 0   ; {why}"]


_ARITH = {'+': 'ADD', '-': 'SUB', '*': 'MUL'}


def _emit_binary(op, left, right, dst, ctx) -> list:
    lines = _compile(left, dst, ctx)
    lines += _compile(right, dst + 1, ctx)
    if op in _ARITH:
        lines.append(f"    {_ARITH[op]}  R{dst}, R{dst}, R{dst + 1}")
        return lines
    if op == '/':
        return lines + _emit_div(dst, ctx)
    if op in ('<', '>', '<=', '>=', '=', '==', '!='):
        return lines + _emit_compare(op, dst, ctx)
    raise FormulaCompileError(f"unsupported operator {op}")


def _emit_div(dst, ctx) -> list:
    """Guarded divide: divisor 0 → result 0 (engine already writes 0; explicit
    for clarity / future #DIV/0! sentinel)."""
    skip = ctx.label('div0')
    return [
        f"    BEQZ R{dst + 1}, {skip}   ; divisor==0 → leave 0",
        f"    DIV  R{dst}, R{dst}, R{dst + 1}",
        f"    JMP  {skip}_done",
        f"{skip}:",
        f"    LI   R{dst}, 0",
        f"{skip}_done:",
    ]


def _emit_compare(op, dst, ctx) -> list:
    """left in R<dst>, right in R<dst+1> → R<dst> = 1/0 per comparison.

    The ISA has BEQZ/BNEZ/BLTZ/BGTZ but no BLEZ/BGEZ, so <= and >= branch on
    their *negation* (branch-to-false) instead.
    """
    d = dst
    lines = [f"    SUB  R{d}, R{d}, R{d + 1}   ; cmp (a-b)"]
    end = ctx.label('cmpe')
    # ops with a direct branch-to-TRUE
    direct = {'=': 'BEQZ', '==': 'BEQZ', '!=': 'BNEZ', '<': 'BLTZ', '>': 'BGTZ'}
    if op in direct:
        t = ctx.label('cmp1')
        lines += [
            f"    {direct[op]} R{d}, {t}",
            f"    LI   R{d}, 0",
            f"    JMP  {end}",
            f"{t}:",
            f"    LI   R{d}, 1",
            f"{end}:",
        ]
        return lines
    # <= and >= : branch to FALSE on the strict opposite, else true
    opp = {'<=': 'BGTZ', '>=': 'BLTZ'}[op]
    f = ctx.label('cmp0')
    lines += [
        f"    {opp} R{d}, {f}",
        f"    LI   R{d}, 1",
        f"    JMP  {end}",
        f"{f}:",
        f"    LI   R{d}, 0",
        f"{end}:",
    ]
    return lines


def _flatten(args, ctx) -> list:
    """Expand range args into individual value nodes (static-extent unroll)."""
    out = []
    for a in args:
        if a[0] == 'range':
            for addr in sheet_formula._expand_range(a[1], a[2]):
                out.append(('ref', addr))
        else:
            out.append(a)
    return out


def _emit_call(fname, args, dst, ctx) -> list:
    if fname == 'IF':
        return _emit_if(args, dst, ctx)
    if fname == 'ABS':
        lines = _compile(args[0], dst, ctx)
        lines.append(f"    ABS  R{dst}, R{dst}")
        return lines
    if fname == 'ROUND':
        # Integer engine: ROUND(x, places>=0) is identity.
        return _compile(args[0], dst, ctx)
    if fname == 'MOD':
        lines = _compile(args[0], dst, ctx) + _compile(args[1], dst + 1, ctx)
        lines.append(f"    MOD  R{dst}, R{dst}, R{dst + 1}")
        return lines
    if fname == 'POWER':
        return _emit_power(args, dst, ctx)
    if fname in ('SUM', 'MIN', 'MAX', 'AVERAGE', 'COUNT'):
        return _emit_aggregate(fname, args, dst, ctx)
    if fname == 'SIGNAL_LAST':
        name = args[0][1] if args and args[0][0] == 'str' else ''
        return _emit_load_slot(ctx.resolver(('signal', name)), dst,
                               f'SIGNAL_LAST {name}')
    if fname == 'CELL':
        name = args[0][1] if args and args[0][0] == 'str' else ''
        return _emit_load_slot(ctx.resolver(name), dst, f'CELL {name}')
    raise FormulaCompileError(f"#NAME? {fname}")


def _emit_if(args, dst, ctx) -> list:
    elseL, endL = ctx.label('else'), ctx.label('end')
    lines = _compile(args[0], dst, ctx)             # condition → R<dst>
    lines.append(f"    BEQZ R{dst}, {elseL}")
    lines += _compile(args[1], dst, ctx)            # then
    lines.append(f"    JMP  {endL}")
    lines.append(f"{elseL}:")
    if len(args) > 2:
        lines += _compile(args[2], dst, ctx)        # else
    else:
        lines.append(f"    LI   R{dst}, 0")
    lines.append(f"{endL}:")
    return lines


def _emit_aggregate(fname, args, dst, ctx) -> list:
    items = _flatten(args, ctx)
    n = len(items)
    if fname == 'COUNT':
        return [f"    LI   R{dst}, {n}"]
    if n == 0:
        return [f"    LI   R{dst}, 0"]
    lines = _compile(items[0], dst, ctx)
    fold = {'SUM': 'ADD', 'AVERAGE': 'ADD', 'MIN': 'MIN', 'MAX': 'MAX'}[fname]
    for it in items[1:]:
        lines += _compile(it, dst + 1, ctx)
        lines.append(f"    {fold}  R{dst}, R{dst}, R{dst + 1}")
    if fname == 'AVERAGE':
        lines.append(f"    LI   R{dst + 1}, {n}")
        lines.append(f"    DIV  R{dst}, R{dst}, R{dst + 1}")
    return lines


def _emit_power(args, dst, ctx) -> list:
    """POWER(base, exp) for small non-negative integer exp — unroll multiplies."""
    exp_node = args[1]
    if exp_node[0] == 'num' and float(exp_node[1]) == int(exp_node[1]) and \
            0 <= int(exp_node[1]) <= 16:
        e = int(exp_node[1])
        if e == 0:
            return [f"    LI   R{dst}, 1"]
        lines = _compile(args[0], dst, ctx)          # base → R<dst>
        if e == 1:
            return lines
        lines.append(f"    MOV  R{dst + 1}, R{dst}   ; base copy")
        for _ in range(e - 1):
            lines.append(f"    MUL  R{dst}, R{dst}, R{dst + 1}")
        return lines
    raise FormulaCompileError("POWER requires a small constant integer exponent")
