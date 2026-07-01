"""command_t5asm.py — Shell command → t5asm compiler (Stage 9-1B compile half).

The bottleneck primitive, mirroring formula_t5asm.compile_ast: given a command
name and its argument value-specs, emit t5asm that — when executed — leaves the
command's result where the caller can read it.

    compile_command(name, args, dst, ctx) -> [t5asm lines]

Result contract (see command_output_kind):
  - 'number' commands leave their result in R<dst>.
  - 'text'   commands write a null-terminated char buffer to ctx.out_text
             (one char per word, gui_entry style) and leave the char count
             in R<dst>.
  - 'none'   commands (env_set) produce no value; R<dst> is scratch.

Runtime value model (locked for this stage):
  - number : one native word.
  - text   : fixed-size null-terminated word-buffer (the Phase 7b-4 gui_entry
             representation — one ASCII char per word). _TEXT_BUF_WORDS long.
  - list   : DEFERRED. No variable-length/list representation exists in the
             runtime yet, so list_of_* commands, split/join/format, and the
             list-producing control commands (repeat/while sub-flows) are not
             compiled here — see SUPPORTED / the bundle report's flag.

Argument value-specs (tuples), produced by the compile_to_t5asm wiring:
  ('num',  int)      numeric literal
  ('numslot', label) a state slot holding a number (a pipe/ref input)
  ('text', label)    a text buffer label (input text value)
  ('name', str)      a compile-time literal string (env var name only)

Registers: numeric evaluation uses the clear high window R21..R40 (same as the
formula engine, which runs at a different time). Text loops use R21..R25 as
local scratch. R19 is the shared error-code register (below the eval window),
R20 is the address scratch — matching formula_t5asm so the two engines compose.
"""

from __future__ import annotations

_BASE_REG = 21
_MAX_REG = 40
_ERR_REG = 19
_ERR_DIV0 = 1
_ERR_NAME = 2

# Prompt answers land in this shared scratch buffer before becoming a heap
# string (commands run sequentially, so one scratch is safe).
_PROMPT_SCRATCH_WORDS = 128

# String-runtime syscalls (Runtime Value Substrate). Handles are heap addresses.
_SYS_STR_FROMBUF = 41
_SYS_STR_LEN     = 42
_SYS_STR_UPPER   = 49
_SYS_STR_LOWER   = 50
_SYS_STR_TRIM    = 51
_SYS_STR_REPLACE = 52

# PIGART interactive dialog syscalls (Stage 9-1C).
_PIG_DIALOG_PROMPT = 112
_PIG_DIALOG_DISPLAY = 113
_PIG_DIALOG_CONFIRM = 114


class CommandCompileError(Exception):
    pass


# ---------------------------------------------------------------------------
# Output-kind table (drives result contract + data-section allocation)
# ---------------------------------------------------------------------------

_OUTPUT_KIND = {
    'cmd_math_add': 'number', 'cmd_math_subtract': 'number',
    'cmd_math_multiply': 'number', 'cmd_math_divide': 'number',
    'cmd_math_mod': 'number', 'cmd_math_round': 'number',
    'cmd_math_abs': 'number', 'cmd_math_power': 'number',
    'cmd_ctl_if': 'number',
    'cmd_env_set': 'none', 'cmd_env_get': 'number', 'cmd_env_exists': 'number',
    'cmd_text_length': 'number',
    'cmd_text_upper': 'text', 'cmd_text_lower': 'text',
    'cmd_text_trim': 'text', 'cmd_text_replace': 'text',
    'cmd_io_prompt': 'text', 'cmd_io_display': 'none',
    'cmd_io_confirm': 'number',
}

# (command, param) pairs whose value is a text (string-handle) value. Drives the
# argument encoding: literals become heap strings (STR_FROMBUF of a data buffer)
# and piped text loads the upstream command's handle slot.
_TEXT_BUF_PARAMS = {
    'cmd_text_upper': {'text'}, 'cmd_text_lower': {'text'},
    'cmd_text_length': {'text'}, 'cmd_text_trim': {'text'},
    'cmd_text_replace': {'text', 'find', 'with'},
    'cmd_io_prompt': {'message'}, 'cmd_io_confirm': {'message'},
    'cmd_io_display': {'value', 'title'},
}


def text_buf_params(name: str) -> set:
    """Param names of `name` that carry a text buffer value."""
    return _TEXT_BUF_PARAMS.get(name, set())

# Commands with a real runtime in this stage. Everything else in the registry
# (text_trim/replace/split/join/format, all list_*, ctl_repeat/while) needs the
# deferred list / variable-length-string / sub-flow substrate.
SUPPORTED = frozenset(_OUTPUT_KIND)


def command_output_kind(name: str) -> str:
    """'number' | 'text' | 'none' for a supported command; else 'unsupported'."""
    return _OUTPUT_KIND.get(name, 'unsupported')


def env_slot(name: str) -> str:
    return f'state_env_{_sanitize(name)}'


def env_present_slot(name: str) -> str:
    return f'state_env_{_sanitize(name)}_present'


def _sanitize(name: str) -> str:
    return ''.join(c if (c.isalnum() or c == '_') else '_' for c in str(name)) or 'x'


# ---------------------------------------------------------------------------
# Compilation context
# ---------------------------------------------------------------------------

class _Ctx:
    """Unique-label state for one command compilation."""

    def __init__(self, out_text: str = None):
        self._n = 0
        self.out_text = out_text     # retained for signature compat (unused)
        self.env_names: set = set()  # env vars referenced (for allocation)
        self.needs_prompt_scratch = False

    def label(self, prefix: str) -> str:
        self._n += 1
        return f'_cmd_{prefix}_{self._n}'


# ---------------------------------------------------------------------------
# Argument loaders
# ---------------------------------------------------------------------------

def _load_num(arg, reg: int) -> list:
    """Emit code leaving arg's numeric value in R<reg>."""
    kind = arg[0]
    if kind == 'num':
        return [f'    LI   R{reg}, {int(arg[1])}']
    if kind == 'numslot':
        return [f'    LI   R{reg}, {arg[1]}',
                f'    LDW  R{reg}, R{reg}, 0']
    if kind == 'text':
        raise CommandCompileError('numeric argument required, got text')
    raise CommandCompileError(f'unusable numeric argument {arg!r}')


def _load_text(arg, reg: int) -> list:
    """Emit code leaving a string HANDLE in R<reg>.
      ('strlit', buflabel)    -> STR_FROMBUF of a NUL-terminated data buffer
      ('handleslot', label)   -> load a slot already holding a handle (pipe/ref)
    """
    kind = arg[0]
    if kind == 'strlit':
        return [f'    LI   R2, {arg[1]}',
                f'    LI   R1, {_SYS_STR_FROMBUF}',
                '    SYSCALL',
                f'    MOV  R{reg}, R1']
    if kind == 'handleslot':
        return [f'    LI   R{reg}, {arg[1]}',
                f'    LDW  R{reg}, R{reg}, 0']
    raise CommandCompileError(f'text argument required, got {arg!r}')


def _literal_name(arg) -> str:
    if arg[0] == 'name':
        return str(arg[1])
    if arg[0] == 'text':
        return str(arg[1])
    raise CommandCompileError('env name must be a compile-time literal')


# ---------------------------------------------------------------------------
# Public entry
# ---------------------------------------------------------------------------

def compile_command(name: str, args: list, dst: int, ctx: '_Ctx' = None) -> list:
    """Emit t5asm for command `name` with value-spec `args`, per the result
    contract in the module docstring."""
    if dst > _MAX_REG - 1:
        raise CommandCompileError('register window exhausted')
    ctx = ctx or _Ctx()
    fn = _DISPATCH.get(name)
    if fn is None:
        raise CommandCompileError(f'no runtime for command {name}')
    return fn(args, dst, ctx)


def new_ctx(out_text: str = None) -> '_Ctx':
    return _Ctx(out_text)


# ---------------------------------------------------------------------------
# Math (all real, native ISA ops)
# ---------------------------------------------------------------------------

def _binop(op):
    def emit(args, dst, ctx):
        lines = _load_num(args[0], dst)
        lines += _load_num(args[1], dst + 1)
        lines.append(f'    {op}  R{dst}, R{dst}, R{dst + 1}')
        return lines
    return emit


def _cmd_divide(args, dst, ctx):
    lines = _load_num(args[0], dst) + _load_num(args[1], dst + 1)
    skip = ctx.label('div0')
    lines += [
        f'    BEQZ R{dst + 1}, {skip}   ; divisor==0 -> #DIV/0!',
        f'    DIV  R{dst}, R{dst}, R{dst + 1}',
        f'    JMP  {skip}_done',
        f'{skip}:',
        f'    LI   R{dst}, 0',
        f'    LI   R{_ERR_REG}, {_ERR_DIV0}',
        f'{skip}_done:',
    ]
    return lines


def _cmd_mod(args, dst, ctx):
    lines = _load_num(args[0], dst) + _load_num(args[1], dst + 1)
    skip = ctx.label('mod0')
    lines += [
        f'    BEQZ R{dst + 1}, {skip}   ; modulus 0 -> #DIV/0!',
        f'    MOD  R{dst}, R{dst}, R{dst + 1}',
        f'    JMP  {skip}_done',
        f'{skip}:',
        f'    LI   R{dst}, 0',
        f'    LI   R{_ERR_REG}, {_ERR_DIV0}',
        f'{skip}_done:',
    ]
    return lines


def _cmd_round(args, dst, ctx):
    # Integer engine: ROUND(x, places>=0) is identity.
    return _load_num(args[0], dst)


def _cmd_abs(args, dst, ctx):
    lines = _load_num(args[0], dst)
    lines.append(f'    ABS  R{dst}, R{dst}')
    return lines


def _cmd_power(args, dst, ctx):
    base, exp = args[0], args[1]
    if exp[0] != 'num':
        raise CommandCompileError('power exponent must be a constant integer')
    e = int(exp[1])
    if not (0 <= e <= 16):
        raise CommandCompileError('power exponent out of range 0..16')
    if e == 0:
        return [f'    LI   R{dst}, 1']
    lines = _load_num(base, dst)
    if e == 1:
        return lines
    lines.append(f'    MOV  R{dst + 1}, R{dst}   ; base copy')
    for _ in range(e - 1):
        lines.append(f'    MUL  R{dst}, R{dst}, R{dst + 1}')
    return lines


# ---------------------------------------------------------------------------
# Control (numeric if — real; repeat/while deferred)
# ---------------------------------------------------------------------------

def _cmd_if(args, dst, ctx):
    if len(args) < 3:
        raise CommandCompileError('if requires condition, then, else')
    cond, then_v, else_v = args[0], args[1], args[2]
    elseL, endL = ctx.label('else'), ctx.label('endif')
    lines = _load_num(cond, dst)
    lines.append(f'    BEQZ R{dst}, {elseL}')
    lines += _load_num(then_v, dst)
    lines.append(f'    JMP  {endL}')
    lines.append(f'{elseL}:')
    lines += _load_num(else_v, dst)
    lines.append(f'{endL}:')
    return lines


# ---------------------------------------------------------------------------
# Env (numeric-valued in-program store — text-valued env deferred)
# ---------------------------------------------------------------------------

def _cmd_env_set(args, dst, ctx):
    name = _literal_name(args[0])
    ctx.env_names.add(name)
    lines = _load_num(args[1], dst)
    lines += [
        f'    LI   R20, {env_slot(name)}',
        f'    STW  R{dst}, R20, 0   ; env["{name}"] = value',
        f'    LI   R20, {env_present_slot(name)}',
        f'    LI   R{dst + 1}, 1',
        f'    STW  R{dst + 1}, R20, 0   ; mark present',
    ]
    return lines


def _cmd_env_get(args, dst, ctx):
    name = _literal_name(args[0])
    ctx.env_names.add(name)
    return [
        f'    LI   R{dst}, {env_slot(name)}',
        f'    LDW  R{dst}, R{dst}, 0   ; env["{name}"]',
    ]


def _cmd_env_exists(args, dst, ctx):
    name = _literal_name(args[0])
    ctx.env_names.add(name)
    return [
        f'    LI   R{dst}, {env_present_slot(name)}',
        f'    LDW  R{dst}, R{dst}, 0   ; env has "{name}"?',
    ]


# ---------------------------------------------------------------------------
# Text (string-handle model — whole-string transforms are string syscalls)
# ---------------------------------------------------------------------------

def _cmd_text_length(args, dst, ctx):
    """length(text) -> number. Handle in R<dst>, then STR_LEN."""
    lines = _load_text(args[0], dst)
    lines += [
        f'    MOV  R2, R{dst}',
        f'    LI   R1, {_SYS_STR_LEN}',
        '    SYSCALL',
        f'    MOV  R{dst}, R1',
    ]
    return lines


def _str_transform(sysnum, why):
    """Unary string transform: load a handle, apply a whole-string syscall."""
    def emit(args, dst, ctx):
        lines = _load_text(args[0], dst)
        lines += [
            f'    MOV  R2, R{dst}',
            f'    LI   R1, {sysnum}   ; {why}',
            '    SYSCALL',
            f'    MOV  R{dst}, R1',
        ]
        return lines
    return emit


def _cmd_text_replace(args, dst, ctx):
    """replace(text, find, with, case_sensitive) -> text (STR_REPLACE).
    STR_REPLACE's ci flag is the negation of case_sensitive."""
    th, fh, wh = dst, dst + 1, dst + 2
    lines = _load_text(args[0], th)
    lines += _load_text(args[1], fh)
    lines += _load_text(args[2], wh)
    cs = 1 if (len(args) > 3 and args[3][0] == 'num' and args[3][1]) else 0
    lines += [
        f'    MOV  R2, R{th}',
        f'    MOV  R3, R{fh}',
        f'    MOV  R4, R{wh}',
        f'    LI   R5, {1 - cs}   ; ci = not case_sensitive',
        f'    LI   R1, {_SYS_STR_REPLACE}',
        '    SYSCALL',
        f'    MOV  R{dst}, R1',
    ]
    return lines


# ---------------------------------------------------------------------------
# Interactive I/O (SDL dialog syscalls — Stage 9-1C), string-handle model
# ---------------------------------------------------------------------------

def _cmd_io_prompt(args, dst, ctx):
    """prompt(message) -> text handle. The dialog writes the typed answer to a
    shared scratch buffer; STR_FROMBUF turns it into a heap string."""
    ctx.needs_prompt_scratch = True
    lines = _load_text(args[0], dst)          # message handle in R<dst>
    lines += [
        f'    MOV  R2, R{dst}',
        '    ADDI R2, R2, 1                ; message chars (handle+1)',
        '    LI   R3, _prompt_scratch',
        f'    LI   R4, {_PROMPT_SCRATCH_WORDS}',
        f'    LI   R1, {_PIG_DIALOG_PROMPT}',
        '    SYSCALL',
        '    LI   R2, _prompt_scratch',
        f'    LI   R1, {_SYS_STR_FROMBUF}',
        '    SYSCALL',
        f'    MOV  R{dst}, R1               ; answer as string handle',
    ]
    return lines


def _cmd_io_display(args, dst, ctx):
    """display(value, title) -> none. Handles rendered via their char runs."""
    vh, th = dst, dst + 1
    lines = _load_text(args[0], vh)
    lines += _load_text(args[1], th)
    lines += [
        f'    MOV  R2, R{th}',
        '    ADDI R2, R2, 1                ; title chars',
        f'    MOV  R3, R{vh}',
        '    ADDI R3, R3, 1                ; value chars',
        f'    LI   R1, {_PIG_DIALOG_DISPLAY}',
        '    SYSCALL',
    ]
    return lines


def _cmd_io_confirm(args, dst, ctx):
    """confirm(message) -> 1/0."""
    lines = _load_text(args[0], dst)
    lines += [
        f'    MOV  R2, R{dst}',
        '    ADDI R2, R2, 1                ; message chars',
        f'    LI   R1, {_PIG_DIALOG_CONFIRM}',
        '    SYSCALL',
        f'    MOV  R{dst}, R1   ; 1=yes 0=no',
    ]
    return lines


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_DISPATCH = {
    'cmd_math_add':      _binop('ADD'),
    'cmd_math_subtract': _binop('SUB'),
    'cmd_math_multiply': _binop('MUL'),
    'cmd_math_divide':   _cmd_divide,
    'cmd_math_mod':      _cmd_mod,
    'cmd_math_round':    _cmd_round,
    'cmd_math_abs':      _cmd_abs,
    'cmd_math_power':    _cmd_power,
    'cmd_ctl_if':        _cmd_if,
    'cmd_env_set':       _cmd_env_set,
    'cmd_env_get':       _cmd_env_get,
    'cmd_env_exists':    _cmd_env_exists,
    'cmd_text_length':   _cmd_text_length,
    'cmd_text_upper':    _str_transform(_SYS_STR_UPPER, 'STR_UPPER'),
    'cmd_text_lower':    _str_transform(_SYS_STR_LOWER, 'STR_LOWER'),
    'cmd_text_trim':     _str_transform(_SYS_STR_TRIM, 'STR_TRIM'),
    'cmd_text_replace':  _cmd_text_replace,
    'cmd_io_prompt':     _cmd_io_prompt,
    'cmd_io_display':    _cmd_io_display,
    'cmd_io_confirm':    _cmd_io_confirm,
}
