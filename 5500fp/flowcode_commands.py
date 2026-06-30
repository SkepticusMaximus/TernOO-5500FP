"""flowcode_commands.py — Stage 9-1A Shell command registry.

Real implementations for the Shell tab's pure-data commands (text / math /
list), replacing the cosmetic stubs. Structured like flowcode_signals.py /
flowcode_properties.py: data-first, no branching on names elsewhere.

Each command entry:
    'desc'   — one-line description
    'params' — [{'name', 'type', 'optional'(bool), 'default'}]
               types: 'text' | 'number' | 'bool' | 'list_of_text'
    'output' — output type string
    'fn'     — implementation: fn(args_dict) -> value  (editor-side)

Pure-data only: no filesystem, no network, no host-OS calls (Shell-skeleton
discipline). Runtime t5asm compilation is Stage 9-1B.
"""

from __future__ import annotations


def _p(name, type_, optional=False, default=None):
    return {'name': name, 'type': type_, 'optional': optional, 'default': default}


def _to_list(v):
    if isinstance(v, list):
        return v
    if v is None or v == '':
        return []
    return [s.strip() for s in str(v).split(',')]


def _num(v):
    try:
        f = float(v)
        return int(f) if f == int(f) else f
    except (ValueError, TypeError):
        return 0


COMMAND_REGISTRY = {
    # ── Text ─────────────────────────────────────────────────────────────────
    'cmd_text_upper':   {'desc': 'Uppercase a string', 'output': 'text',
                         'params': [_p('text', 'text')],
                         'fn': lambda a: str(a.get('text', '')).upper()},
    'cmd_text_lower':   {'desc': 'Lowercase a string', 'output': 'text',
                         'params': [_p('text', 'text')],
                         'fn': lambda a: str(a.get('text', '')).lower()},
    'cmd_text_trim':    {'desc': 'Strip surrounding whitespace', 'output': 'text',
                         'params': [_p('text', 'text')],
                         'fn': lambda a: str(a.get('text', '')).strip()},
    'cmd_text_length':  {'desc': 'Character count', 'output': 'number',
                         'params': [_p('text', 'text')],
                         'fn': lambda a: len(str(a.get('text', '')))},
    'cmd_text_replace': {'desc': 'Replace text in a string', 'output': 'text',
                         'params': [_p('text', 'text'), _p('find', 'text'),
                                    _p('with', 'text'),
                                    _p('case_sensitive', 'bool', True, False)],
                         'fn': lambda a: _text_replace(a)},
    'cmd_text_split':   {'desc': 'Split into a list by delimiter',
                         'output': 'list_of_text',
                         'params': [_p('text', 'text'), _p('delimiter', 'text')],
                         'fn': lambda a: str(a.get('text', '')).split(
                             a.get('delimiter') or ',')},
    'cmd_text_join':    {'desc': 'Join a list with a separator', 'output': 'text',
                         'params': [_p('list', 'list_of_text'),
                                    _p('separator', 'text')],
                         'fn': lambda a: str(a.get('separator', '')).join(
                             str(x) for x in _to_list(a.get('list')))},
    'cmd_text_format':  {'desc': 'Template substitution, e.g. "Hi {name}"',
                         'output': 'text',
                         'params': [_p('template', 'text'),
                                    _p('args', 'list_of_text', True)],
                         'fn': lambda a: _text_format(a)},
    # ── Math ─────────────────────────────────────────────────────────────────
    'cmd_math_add':      {'desc': 'Add two numbers', 'output': 'number',
                          'params': [_p('a', 'number'), _p('b', 'number')],
                          'fn': lambda a: _num(a.get('a')) + _num(a.get('b'))},
    'cmd_math_subtract': {'desc': 'Subtract b from a', 'output': 'number',
                          'params': [_p('a', 'number'), _p('b', 'number')],
                          'fn': lambda a: _num(a.get('a')) - _num(a.get('b'))},
    'cmd_math_multiply': {'desc': 'Multiply two numbers', 'output': 'number',
                          'params': [_p('a', 'number'), _p('b', 'number')],
                          'fn': lambda a: _num(a.get('a')) * _num(a.get('b'))},
    'cmd_math_divide':   {'desc': 'Divide a by b (zero-checked)', 'output': 'number',
                          'params': [_p('a', 'number'), _p('b', 'number')],
                          'fn': lambda a: _div(a)},
    'cmd_math_mod':      {'desc': 'Remainder of a / b', 'output': 'number',
                          'params': [_p('a', 'number'), _p('b', 'number')],
                          'fn': lambda a: (_num(a.get('a')) % _num(a.get('b'))
                                           if _num(a.get('b')) else '#DIV/0!')},
    'cmd_math_round':    {'desc': 'Round x to places decimals', 'output': 'number',
                          'params': [_p('x', 'number'), _p('places', 'number', True, 0)],
                          'fn': lambda a: round(_num(a.get('x')),
                                                int(_num(a.get('places') or 0)))},
    'cmd_math_abs':      {'desc': 'Absolute value', 'output': 'number',
                          'params': [_p('x', 'number')],
                          'fn': lambda a: abs(_num(a.get('x')))},
    'cmd_math_power':    {'desc': 'base raised to exp', 'output': 'number',
                          'params': [_p('base', 'number'), _p('exp', 'number')],
                          'fn': lambda a: _num(a.get('base')) ** _num(a.get('exp'))},
    # ── List ─────────────────────────────────────────────────────────────────
    'cmd_list_count':   {'desc': 'Number of items', 'output': 'number',
                         'params': [_p('list', 'list_of_text')],
                         'fn': lambda a: len(_to_list(a.get('list')))},
    'cmd_list_first':   {'desc': 'First item', 'output': 'text',
                         'params': [_p('list', 'list_of_text')],
                         'fn': lambda a: (_to_list(a.get('list')) or [''])[0]},
    'cmd_list_last':    {'desc': 'Last item', 'output': 'text',
                         'params': [_p('list', 'list_of_text')],
                         'fn': lambda a: (_to_list(a.get('list')) or [''])[-1]},
    'cmd_list_reverse': {'desc': 'Reverse order', 'output': 'list_of_text',
                         'params': [_p('list', 'list_of_text')],
                         'fn': lambda a: list(reversed(_to_list(a.get('list'))))},
    'cmd_list_sort':    {'desc': 'Sort items', 'output': 'list_of_text',
                         'params': [_p('list', 'list_of_text'),
                                    _p('ascending', 'bool', True, True)],
                         'fn': lambda a: sorted(_to_list(a.get('list')),
                                                reverse=not a.get('ascending', True))},
    'cmd_list_unique':  {'desc': 'Distinct items (order preserved)',
                         'output': 'list_of_text',
                         'params': [_p('list', 'list_of_text')],
                         'fn': lambda a: _unique(_to_list(a.get('list')))},
    # ── Env (in-program state, NOT host env) ─────────────────────────────────
    'cmd_env_set':    {'desc': 'Set an in-program env var', 'output': 'none',
                       'params': [_p('name', 'text'), _p('value', 'text')],
                       'fn': lambda a: _env_set(a)},
    'cmd_env_get':    {'desc': 'Read an in-program env var', 'output': 'text',
                       'params': [_p('name', 'text')],
                       'fn': lambda a: _ENV.get(str(a.get('name', '')), '')},
    'cmd_env_exists': {'desc': 'Check an in-program env var', 'output': 'bool',
                       'params': [_p('name', 'text')],
                       'fn': lambda a: str(a.get('name', '')) in _ENV},
    # ── Control flow (editor-side: if fully; repeat/while need sub-flows at
    # runtime — see Stage 9-1B t5asm path) ───────────────────────────────────
    'cmd_ctl_if':     {'desc': 'If/else value selector', 'output': 'any',
                       'params': [_p('condition', 'text'),
                                  _p('then_value', 'text'), _p('else_value', 'text')],
                       'fn': lambda a: (a.get('then_value', '')
                                        if _cond(a.get('condition'))
                                        else a.get('else_value', ''))},
    'cmd_ctl_repeat': {'desc': 'Repeat a value n times → list', 'output': 'list_of_text',
                       'params': [_p('count', 'number'), _p('value', 'text')],
                       'fn': lambda a: [a.get('value', '')] * max(0, int(_num(a.get('count'))))},
    'cmd_ctl_while':  {'desc': 'Conditional loop (runtime sub-flows)',
                       'output': 'none',
                       'params': [_p('predicate', 'text'), _p('body', 'text')],
                       'fn': lambda a: ''},   # editor-side no-op; runtime executes
}

# In-program environment store (editor-side preview). Runtime uses the program
# state region (same mechanism as widget state) — this is NOT the host env.
_ENV = {}


def _env_set(a):
    _ENV[str(a.get('name', ''))] = str(a.get('value', ''))
    return ''


def _cond(v):
    s = str(v).strip().lower()
    if s in ('', '0', 'false', 'no'):
        return False
    try:
        return float(s) != 0
    except ValueError:
        return True


def _text_replace(a):
    text, find, repl = str(a.get('text', '')), str(a.get('find', '')), str(a.get('with', ''))
    if not find:
        return text
    if a.get('case_sensitive'):
        return text.replace(find, repl)
    # case-insensitive replace
    import re
    return re.sub(re.escape(find), repl.replace('\\', '\\\\'), text, flags=re.IGNORECASE)


def _text_format(a):
    template = str(a.get('template', ''))
    args = _to_list(a.get('args'))
    # Positional {} and {0}/{1}; also {name}=value pairs not supported here.
    out = template
    for i, val in enumerate(args):
        out = out.replace('{' + str(i) + '}', str(val))
    # fill remaining {} left-to-right
    for val in args:
        out = out.replace('{}', str(val), 1)
    return out


def _div(a):
    b = _num(a.get('b'))
    if b == 0:
        return '#DIV/0!'
    return _num(a.get('a')) / b


def _unique(lst):
    seen = set(); out = []
    for x in lst:
        if x not in seen:
            seen.add(x); out.append(x)
    return out


def commands():
    """The command registry (name → spec)."""
    return COMMAND_REGISTRY


def command_names():
    return list(COMMAND_REGISTRY.keys())


def run_command(name, args):
    """Editor-side execution: run command `name` with an args dict.
    Returns the result value, or an error string for unknown commands."""
    spec = COMMAND_REGISTRY.get(name)
    if spec is None:
        return f"#CMD? {name}"
    try:
        return spec['fn'](args)
    except Exception as e:
        return f"#ERROR! {e}"
