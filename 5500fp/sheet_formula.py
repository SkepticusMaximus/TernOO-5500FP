"""sheet_formula.py — Stage 8-3 formula engine for the Sheet leg.

A small, dependency-free, headless formula engine: tokenizer, recursive-descent
parser for an Excel-compatible subset, a dependency analyser, cycle detection,
and an evaluator that recomputes a whole sheet in topological order.

This is the *editor-side* evaluator (CC Day Dispatch v2, pre-approved scope
call): it satisfies the Stage 8-3 acceptance (=2+3→5, =A1+B1 updating on change,
SUM/IF/ranges, circular-dependency errors). Emitting t5asm fragments that
recompute on the PIGART render cycle is the deeper compiler-runtime integration
and is a documented follow-on.

Grammar (precedence low→high):
    expr    := compare
    compare := add ( ( '=' | '==' | '!=' | '<' | '>' | '<=' | '>=' ) add )*
    add     := mul ( ( '+' | '-' ) mul )*
    mul     := unary ( ( '*' | '/' ) unary )*
    unary   := ( '+' | '-' ) unary | primary
    primary := NUMBER | STRING | TRUE | FALSE
             | NAME '(' [ expr (',' expr)* ] ')'        (function call)
             | A1REF [ ':' A1REF ]                       (cell ref or range)
             | NAME                                      (named cell ref)
             | '(' expr ')'

Cell references: A1-style (``A1``, ``B3``, ``AA12``) and named (``cell_total``).
Builtins: SUM, AVERAGE, MIN, MAX, COUNT, IF, ABS, ROUND, AND, OR, NOT.
"""

from __future__ import annotations
import re

# ── A1 ⇄ (row, col) ──────────────────────────────────────────────────────────

_A1_RE = re.compile(r'^([A-Za-z]+)([0-9]+)$')


def col_to_index(letters: str) -> int:
    """'A'→0, 'Z'→25, 'AA'→26."""
    n = 0
    for ch in letters.upper():
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def index_to_col(idx: int) -> str:
    s = ''; idx += 1
    while idx > 0:
        idx, r = divmod(idx - 1, 26)
        s = chr(65 + r) + s
    return s


def a1_to_rc(addr: str):
    """'B3' → (2, 1) zero-based (row, col), or None if not an A1 address."""
    mobj = _A1_RE.match(addr)
    if not mobj:
        return None
    col = col_to_index(mobj.group(1))
    row = int(mobj.group(2)) - 1
    if row < 0 or col < 0:
        return None
    return (row, col)


def rc_to_a1(row: int, col: int) -> str:
    return f"{index_to_col(col)}{row + 1}"


# ── Tokenizer ────────────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(r"""
    \s*(?:
      (?P<number>\d+\.\d+|\d+)
    | (?P<string>"[^"]*")
    | (?P<op><=|>=|==|!=|[-+*/(),:<>=.])
    | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
    )
""", re.VERBOSE)


class FormulaError(Exception):
    """Raised on parse or evaluation failure (surfaces as a cell error)."""


def tokenize(expr: str):
    toks = []
    pos = 0
    while pos < len(expr):
        if expr[pos].isspace():
            pos += 1
            continue
        m = _TOKEN_RE.match(expr, pos)
        if not m or m.end() == pos:
            raise FormulaError(f"bad character at {pos!r} in {expr!r}")
        pos = m.end()
        kind = m.lastgroup
        val = m.group(kind)
        toks.append((kind, val))
    toks.append(('end', ''))
    return toks


# ── AST nodes (tuples) ───────────────────────────────────────────────────────
#   ('num', value) ('str', value) ('bool', value)
#   ('ref', 'A1' or name) ('range', startaddr, endaddr)
#   ('bin', op, left, right) ('unary', op, operand) ('call', fname, [args])

class _Parser:
    def __init__(self, toks):
        self.toks = toks
        self.i = 0

    def peek(self):
        return self.toks[self.i]

    def next(self):
        t = self.toks[self.i]; self.i += 1; return t

    def expect(self, val):
        k, v = self.next()
        if v != val:
            raise FormulaError(f"expected {val!r}, got {v!r}")

    def parse(self):
        node = self.parse_compare()
        if self.peek()[0] != 'end':
            raise FormulaError(f"unexpected {self.peek()[1]!r}")
        return node

    def parse_compare(self):
        node = self.parse_add()
        while self.peek()[1] in ('=', '==', '!=', '<', '>', '<=', '>='):
            op = self.next()[1]
            node = ('bin', op, node, self.parse_add())
        return node

    def parse_add(self):
        node = self.parse_mul()
        while self.peek()[1] in ('+', '-'):
            op = self.next()[1]
            node = ('bin', op, node, self.parse_mul())
        return node

    def parse_mul(self):
        node = self.parse_unary()
        while self.peek()[1] in ('*', '/'):
            op = self.next()[1]
            node = ('bin', op, node, self.parse_unary())
        return node

    def parse_unary(self):
        if self.peek()[1] in ('+', '-'):
            op = self.next()[1]
            return ('unary', op, self.parse_unary())
        return self.parse_primary()

    def parse_primary(self):
        node = self._parse_atom()
        # Stage 8-8: member access, e.g. WIDGET("x").label
        while self.peek()[1] == '.':
            self.next()
            k, v = self.next()
            if k != 'name':
                raise FormulaError(f"expected property name after '.', got {v!r}")
            node = ('member', node, v)
        return node

    def _parse_atom(self):
        kind, val = self.peek()
        if kind == 'number':
            self.next()
            return ('num', float(val) if '.' in val else int(val))
        if kind == 'string':
            self.next()
            return ('str', val[1:-1])
        if val == '(':
            self.next()
            node = self.parse_compare()
            self.expect(')')
            return node
        if kind == 'name':
            self.next()
            up = val.upper()
            if up in ('TRUE', 'FALSE'):
                return ('bool', up == 'TRUE')
            if self.peek()[1] == '(':            # function call
                self.next()
                args = []
                if self.peek()[1] != ')':
                    args.append(self.parse_compare())
                    while self.peek()[1] == ',':
                        self.next(); args.append(self.parse_compare())
                self.expect(')')
                return ('call', up, args)
            if a1_to_rc(val) is not None:         # A1 ref, maybe a range
                if self.peek()[1] == ':':
                    self.next()
                    k2, v2 = self.next()
                    if a1_to_rc(v2) is None:
                        raise FormulaError(f"bad range end {v2!r}")
                    return ('range', val, v2)
                return ('ref', val)
            return ('ref', val)                   # named cell reference
        raise FormulaError(f"unexpected token {val!r}")


def parse(expr: str):
    """Parse a formula expression (without the leading '=') into an AST."""
    return _Parser(tokenize(expr)).parse()


# ── Dependency extraction ────────────────────────────────────────────────────

def extract_refs(node):
    """Set of reference tokens (A1 strings and names) a formula AST depends on.
    Ranges are expanded to their constituent A1 cells."""
    out = set()
    t = node[0]
    if t == 'ref':
        out.add(node[1])
    elif t == 'range':
        for a in _expand_range(node[1], node[2]):
            out.add(a)
    elif t == 'bin':
        out |= extract_refs(node[2]); out |= extract_refs(node[3])
    elif t == 'unary':
        out |= extract_refs(node[2])
    elif t == 'call':
        for a in node[2]:
            out |= extract_refs(a)
    return out


def _expand_range(a, b):
    ra = a1_to_rc(a); rb = a1_to_rc(b)
    if ra is None or rb is None:
        return []
    (r0, c0), (r1, c1) = ra, rb
    out = []
    for r in range(min(r0, r1), max(r0, r1) + 1):
        for c in range(min(c0, c1), max(c0, c1) + 1):
            out.append(rc_to_a1(r, c))
    return out


# ── Evaluation ───────────────────────────────────────────────────────────────

def _num(v):
    if isinstance(v, bool):
        return 1 if v else 0
    if isinstance(v, (int, float)):
        return v
    if isinstance(v, str):
        try:
            return int(v)
        except ValueError:
            try:
                return float(v)
            except ValueError:
                return 0
    return 0


def _eval(node, lookup, ctx=None):
    t = node[0]
    if t == 'num':  return node[1]
    if t == 'str':  return node[1]
    if t == 'bool': return node[1]
    if t == 'ref':  return lookup(node[1])
    if t == 'range':
        return [lookup(a) for a in _expand_range(node[1], node[2])]
    if t == 'member':
        # Stage 8-8: WIDGET("name").property
        base = node[1]
        if base[0] == 'call' and base[1] == 'WIDGET':
            wname = _eval(base[2][0], lookup, ctx) if base[2] else ''
            if ctx and ctx.get('widget_prop'):
                v = ctx['widget_prop'](str(wname), node[2])
                if v is None:
                    raise FormulaError(f"#NAME? {wname}")
                return v
            raise FormulaError(f"#NAME? {wname}")
        raise FormulaError("#ERROR!")
    if t == 'unary':
        v = _num(_eval(node[2], lookup, ctx))
        return -v if node[1] == '-' else v
    if t == 'bin':
        op = node[1]
        a = _eval(node[2], lookup, ctx); b = _eval(node[3], lookup, ctx)
        if op in ('=', '=='): return a == b
        if op == '!=': return a != b
        if op == '<':  return _num(a) < _num(b)
        if op == '>':  return _num(a) > _num(b)
        if op == '<=': return _num(a) <= _num(b)
        if op == '>=': return _num(a) >= _num(b)
        x, y = _num(a), _num(b)
        if op == '+': return x + y
        if op == '-': return x - y
        if op == '*': return x * y
        if op == '/':
            if y == 0:
                raise FormulaError("#DIV/0!")
            # Machine semantics: the 5500FP DIV truncates toward zero
            # (C integer division). The editor preview models the machine,
            # so 7/2 == 3 and -7/2 == -3 here, exactly as at runtime.
            return int(x / y)
    if t == 'call':
        return _eval_call(node[1], node[2], lookup, ctx)
    raise FormulaError("bad node")


def _flat_nums(args, lookup, ctx=None):
    out = []
    for a in args:
        v = _eval(a, lookup, ctx)
        if isinstance(v, list):
            out.extend(_num(x) for x in v)
        else:
            out.append(_num(v))
    return out


def _eval_call(fname, args, lookup, ctx=None):
    if fname == 'SUM':     return sum(_flat_nums(args, lookup, ctx))
    if fname == 'AVERAGE':
        nums = _flat_nums(args, lookup, ctx)
        # Machine semantics: engine folds with ADD then divides with DIV
        # (truncation toward zero), so AVERAGE(7,2) == 4, not 4.5.
        return int(sum(nums) / len(nums)) if nums else 0
    if fname == 'MIN':     return min(_flat_nums(args, lookup, ctx) or [0])
    if fname == 'MAX':     return max(_flat_nums(args, lookup, ctx) or [0])
    if fname == 'COUNT':   return len(_flat_nums(args, lookup, ctx))
    if fname == 'ABS':     return abs(_num(_eval(args[0], lookup, ctx)))
    if fname == 'ROUND':
        v = _num(_eval(args[0], lookup, ctx))
        nd = int(_num(_eval(args[1], lookup, ctx))) if len(args) > 1 else 0
        return round(v, nd)
    if fname == 'IF':
        cond = _eval(args[0], lookup, ctx)
        cond = bool(cond) if not isinstance(cond, (int, float)) else _num(cond) != 0
        return _eval(args[1], lookup, ctx) if cond else (
            _eval(args[2], lookup, ctx) if len(args) > 2 else False)
    if fname == 'NOT':
        v = _eval(args[0], lookup, ctx)
        return not (bool(v) if not isinstance(v, (int, float)) else _num(v) != 0)
    if fname == 'AND':
        return all(_truthy(_eval(a, lookup, ctx)) for a in args)
    if fname == 'OR':
        return any(_truthy(_eval(a, lookup, ctx)) for a in args)
    # ── Stage 8-8: TernOO-native functions (all dynamic) ─────────────────────
    if fname == 'CELL':
        name = str(_eval(args[0], lookup, ctx)) if args else ''
        return lookup(name)
    if fname == 'SIGNAL_LAST':
        name = str(_eval(args[0], lookup, ctx)) if args else ''
        if ctx and ctx.get('signal_last'):
            return ctx['signal_last'](name)
        return 0          # no signal has fired (editor / never-fired)
    if fname == 'WIDGET':
        # Bare WIDGET("x") with no .property is not directly usable.
        raise FormulaError("#ERROR! WIDGET needs .property")
    # ── Stage 8-10: extended math ────────────────────────────────────────────
    if fname == 'MOD':
        b = _num(_eval(args[1], lookup, ctx))
        if b == 0:
            raise FormulaError("#DIV/0!")
        return _num(_eval(args[0], lookup, ctx)) % b
    if fname == 'POWER':
        return _num(_eval(args[0], lookup, ctx)) ** _num(_eval(args[1], lookup, ctx))
    if fname == 'SQRT':
        v = _num(_eval(args[0], lookup, ctx))
        if v < 0:
            raise FormulaError("#NUM!")
        return v ** 0.5
    if fname == 'INT':
        import math as _m
        return _m.floor(_num(_eval(args[0], lookup, ctx)))
    # ── Stage 8-10: string functions ─────────────────────────────────────────
    if fname == 'CONCAT':
        return ''.join(str(_eval(a, lookup, ctx)) for a in args)
    if fname == 'LEN':
        return len(str(_eval(args[0], lookup, ctx)))
    if fname == 'UPPER':
        return str(_eval(args[0], lookup, ctx)).upper()
    if fname == 'LOWER':
        return str(_eval(args[0], lookup, ctx)).lower()
    if fname == 'TRIM':
        return str(_eval(args[0], lookup, ctx)).strip()
    if fname == 'LEFT':
        s = str(_eval(args[0], lookup, ctx))
        n = int(_num(_eval(args[1], lookup, ctx))) if len(args) > 1 else 1
        return s[:n]
    if fname == 'RIGHT':
        s = str(_eval(args[0], lookup, ctx))
        n = int(_num(_eval(args[1], lookup, ctx))) if len(args) > 1 else 1
        return s[-n:] if n > 0 else ''
    if fname == 'MID':
        s = str(_eval(args[0], lookup, ctx))
        start = int(_num(_eval(args[1], lookup, ctx)))
        length = int(_num(_eval(args[2], lookup, ctx)))
        return s[start - 1:start - 1 + length]
    # ── Stage 8-10: date functions (numeric days since 1970-01-01) ───────────
    if fname == 'TODAY' or fname == 'NOW':
        return _date_to_days(_dt.date.today())
    if fname == 'DATE':
        y = int(_num(_eval(args[0], lookup, ctx)))
        mo = int(_num(_eval(args[1], lookup, ctx)))
        d = int(_num(_eval(args[2], lookup, ctx)))
        return _date_to_days(_dt.date(y, mo, d))
    if fname == 'YEAR':
        return _days_to_date(_num(_eval(args[0], lookup, ctx))).year
    if fname == 'MONTH':
        return _days_to_date(_num(_eval(args[0], lookup, ctx))).month
    if fname == 'DAY':
        return _days_to_date(_num(_eval(args[0], lookup, ctx))).day
    if fname == 'DATEDIF':
        a = int(_num(_eval(args[0], lookup, ctx)))
        b = int(_num(_eval(args[1], lookup, ctx)))
        unit = str(_eval(args[2], lookup, ctx)).upper() if len(args) > 2 else 'D'
        d0, d1 = _days_to_date(a), _days_to_date(b)
        if unit == 'D': return b - a
        if unit == 'Y': return d1.year - d0.year
        if unit == 'M': return (d1.year - d0.year) * 12 + (d1.month - d0.month)
        return b - a
    # ── Stage 8-10: lookup functions ─────────────────────────────────────────
    if fname in ('VLOOKUP', 'HLOOKUP'):
        key = _eval(args[0], lookup, ctx)
        if args[1][0] != 'range':
            raise FormulaError("#REF!")
        grid = _range_grid(args[1], lookup)
        idx = int(_num(_eval(args[2], lookup, ctx)))
        if fname == 'HLOOKUP':
            grid = [list(r) for r in zip(*grid)]   # transpose → search by row 0
        for row in grid:
            if str(row[0]) == str(key) or row[0] == key:
                if idx < 1 or idx > len(row):
                    raise FormulaError("#REF!")
                return row[idx - 1]
        raise FormulaError("#N/A")
    if fname == 'INDEX':
        if args[0][0] != 'range':
            raise FormulaError("#REF!")
        grid = _range_grid(args[0], lookup)
        ri = int(_num(_eval(args[1], lookup, ctx)))
        ci = int(_num(_eval(args[2], lookup, ctx))) if len(args) > 2 else 1
        if ri < 1 or ri > len(grid) or ci < 1 or ci > len(grid[0]):
            raise FormulaError("#REF!")
        return grid[ri - 1][ci - 1]
    if fname == 'MATCH':
        key = _eval(args[0], lookup, ctx)
        if args[1][0] != 'range':
            raise FormulaError("#REF!")
        flat = [v for row in _range_grid(args[1], lookup) for v in row]
        for i, v in enumerate(flat):
            if str(v) == str(key) or v == key:
                return i + 1
        raise FormulaError("#N/A")
    raise FormulaError(f"#NAME? {fname}")


def _truthy(v):
    return bool(v) if not isinstance(v, (int, float)) else _num(v) != 0


# ── Stage 8-10 helpers: dates (days since 1970-01-01) + 2D ranges ────────────

import datetime as _dt
_EPOCH = _dt.date(1970, 1, 1)


def _days_to_date(n):
    return _EPOCH + _dt.timedelta(days=int(n))


def _date_to_days(d):
    return (d - _EPOCH).days


def _range_grid(node, lookup):
    """('range', a, b) → 2D list of values (row-major)."""
    ra = a1_to_rc(node[1]); rb = a1_to_rc(node[2])
    r0, c0 = ra; r1, c1 = rb
    r0, r1 = min(r0, r1), max(r0, r1)
    c0, c1 = min(c0, c1), max(c0, c1)
    return [[lookup(rc_to_a1(r, c)) for c in range(c0, c1 + 1)]
            for r in range(r0, r1 + 1)]


# ── Whole-sheet evaluation ───────────────────────────────────────────────────

def evaluate_sheet(cells, ctx=None):
    """Evaluate every cell in a sheet.

    `cells`: dict {(row, col): {'kind', 'value', 'name'(optional)}}.
    `ctx`:   optional {'widget_prop': fn(name, prop), 'signal_last': fn(name)}
             for the Stage 8-8 native functions (WIDGET/SIGNAL_LAST).
    Returns (results, errors):
      results: {(row, col): evaluated python value}
      errors:  {(row, col): error string, e.g. '#CYCLE!', '#NAME?'}
    Static and dynamic formulas are evaluated the same way here (editor-side);
    cycles are detected and reported per the design memo (Sh10).
    """
    # Build address → (row,col) maps (A1 and named).
    addr_rc = {}
    name_rc = {}
    for (r, c), cell in cells.items():
        addr_rc[rc_to_a1(r, c)] = (r, c)
        nm = cell.get('name')
        if nm:
            name_rc[nm] = (r, c)

    def ref_to_rc(ref):
        if ref in addr_rc:
            return addr_rc[ref]
        if ref in name_rc:
            return name_rc[ref]
        rc = a1_to_rc(ref)
        return rc   # may point at an empty cell (treated as 0/'')

    asts = {}
    deps = {}
    for (r, c), cell in cells.items():
        if cell.get('kind') == 'cell_formula':
            src = str(cell.get('value', ''))
            expr = src[1:] if src.startswith('=') else src
            try:
                ast = parse(expr)
                asts[(r, c)] = ast
                d = set()
                for ref in extract_refs(ast):
                    rc = ref_to_rc(ref)
                    if rc is not None:
                        d.add(rc)
                deps[(r, c)] = d
            except FormulaError:
                asts[(r, c)] = None
                deps[(r, c)] = set()

    results = {}
    errors = {}

    # Cycle detection + topological evaluation via DFS with colouring.
    WHITE, GREY, BLACK = 0, 1, 2
    color = {}

    def literal_value(rc):
        cell = cells.get(rc)
        if cell is None:
            return 0
        kind = cell.get('kind')
        val = cell.get('value', '')
        if kind == 'cell_value':
            s = str(val).strip()
            if s.lower() == 'true':  return True
            if s.lower() == 'false': return False
            return _num(s)
        if kind == 'cell_text':
            return str(val)
        return val

    def visit(rc):
        if color.get(rc) == BLACK:
            return results.get(rc, literal_value(rc))
        if color.get(rc) == GREY:
            raise _Cycle(rc)
        cell = cells.get(rc)
        if cell is None or cell.get('kind') != 'cell_formula':
            results[rc] = literal_value(rc)
            color[rc] = BLACK
            return results[rc]
        color[rc] = GREY
        ast = asts.get(rc)
        if ast is None:
            errors[rc] = '#ERROR!'
            results[rc] = '#ERROR!'
            color[rc] = BLACK
            return 0

        def lookup(ref):
            tgt = ref_to_rc(ref)
            if tgt is None:
                raise FormulaError(f"#NAME? {ref}")
            return visit(tgt)
        try:
            val = _eval(ast, lookup, ctx)
            results[rc] = val
        except _Cycle:
            raise
        except FormulaError as fe:
            msg = str(fe)
            errors[rc] = msg if msg.startswith('#') else '#ERROR!'
            results[rc] = errors[rc]
        color[rc] = BLACK
        return results.get(rc, 0)

    for rc in list(cells.keys()):
        try:
            if color.get(rc) != BLACK:
                visit(rc)
        except _Cycle as cyc:
            # Mark every formula cell still in the cycle's component.
            errors[cyc.rc] = '#CYCLE!'
            results[cyc.rc] = '#CYCLE!'
            color[cyc.rc] = BLACK
            # Reset greys so remaining cells can still evaluate.
            for k in list(color.keys()):
                if color[k] == GREY:
                    errors.setdefault(k, '#CYCLE!')
                    results[k] = '#CYCLE!'
                    color[k] = BLACK
    return results, errors


class _Cycle(Exception):
    def __init__(self, rc):
        self.rc = rc


def format_result(v):
    """Render an evaluated value for display in a cell."""
    if isinstance(v, bool):
        return 'TRUE' if v else 'FALSE'
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)
