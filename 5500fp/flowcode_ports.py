"""flowcode_ports.py — Phase 7c-4b named entry/exit points on container symbols.

Data-first, like flowcode_signals.py / flowcode_commands.py. A container flow
symbol (flow_process / flow_subroutine — one that has a pocket) may expose:

  entry_points — inputs the interior receives from the parent scope
  exit_points  — outputs the interior sends to the parent scope

Each port is a dict:  {'name': str, 'type': str, 'description': str}

Ports are the ONLY cross-scope communication mechanism; direct edges across
pocket boundaries stay forbidden (Phase 7c-4 L3). Outer scope binds to a
container's ports *by name* (Phase 7c-1/2 naming); the interior references them
by name too. At compile time each port becomes a state slot (Phase 7c-4b P5):

  entry -> state_entry_<container>_<port>
  exit  -> state_exit_<container>_<port>

Names are unique within a container's port namespace (an entry and an exit
cannot share a name).
"""

from __future__ import annotations

# Type vocabulary — same as pipes / commands (Phase 9-2). Extendable later.
PORT_TYPES = ('text', 'number', 'boolean', 'list_of_text', 'list_of_number')

# Container kinds that may own ports (mirror of flowcode._FC_CONTAINER_KINDS).
CONTAINER_KINDS = frozenset({'flow_process', 'flow_subroutine'})


def is_container(kind: str) -> bool:
    return kind in CONTAINER_KINDS


def make_port(name: str, type_: str = 'number', description: str = '',
              expr: str = '') -> dict:
    """A normalised port dict. `expr` (exit ports only) is the interior
    computation — a formula over entry-port names, e.g. "input_value * 2"."""
    p = {'name': str(name).strip(),
         'type': type_ if type_ in PORT_TYPES else 'number',
         'description': str(description)}
    if expr:
        p['expr'] = str(expr)
    return p


def _value_class(type_str: str) -> str:
    t = (type_str or '').lower()
    if t in ('number', 'boolean', 'bool'):
        return 'num'
    if t == 'text':
        return 'text'
    if t.startswith('list'):
        return 'list'
    return 'any'


def port_edge_compatible(src_type: str, port_type: str) -> bool:
    """True if a source of `src_type` can bind to a port of `port_type`."""
    sc, pc = _value_class(src_type), _value_class(port_type)
    return 'any' in (sc, pc) or sc == pc


def entry_points(sym: dict) -> list:
    return sym.get('entry_points') or []


def exit_points(sym: dict) -> list:
    return sym.get('exit_points') or []


def port_names(sym: dict) -> set:
    """All entry + exit port names in a container's namespace."""
    return ({p.get('name') for p in entry_points(sym)}
            | {p.get('name') for p in exit_points(sym)})


def find_port(sym: dict, name: str):
    """Return ('entry'|'exit', port_dict) for `name`, or (None, None)."""
    for p in entry_points(sym):
        if p.get('name') == name:
            return 'entry', p
    for p in exit_points(sym):
        if p.get('name') == name:
            return 'exit', p
    return None, None


def validate_new_port(sym: dict, name: str, type_: str, exclude: dict = None):
    """Validate adding/editing a port on `sym`. Returns (ok: bool, msg: str).

    `exclude` is the port dict being edited (so it doesn't clash with itself).
    """
    name = str(name).strip()
    if not name:
        return False, 'Port name cannot be empty'
    if not name.replace('_', '').isalnum():
        return False, 'Port name must be alphanumeric / underscores'
    if type_ not in PORT_TYPES:
        return False, f'Unknown type {type_!r}'
    for p in entry_points(sym) + exit_points(sym):
        if p is exclude:
            continue
        if p.get('name') == name:
            return False, f'Port name {name!r} already used in this container'
    return True, ''


# --- Compile-time slot naming (Phase 7c-4b P5) ----------------------------

def _sanitize(s: str) -> str:
    return ''.join(c if (c.isalnum() or c == '_') else '_' for c in str(s)) or 'x'


def entry_slot(container_name: str, port_name: str) -> str:
    return f'state_entry_{_sanitize(container_name)}_{_sanitize(port_name)}'


def exit_slot(container_name: str, port_name: str) -> str:
    return f'state_exit_{_sanitize(container_name)}_{_sanitize(port_name)}'


# --- Stage 8-6: cell ↔ port bindings --------------------------------------
#
# A Sheet cell may be bound to one container port instead of holding a formula.
# The binding is a dict {container_name, port_name, direction} stored on the
# cell as `bound_to_port`. direction 'entry' -> the cell drives the entry port;
# 'exit' -> the cell reflects the exit port. Mutually exclusive with a formula.

def make_cell_binding(container_name: str, port_name: str, direction: str) -> dict:
    return {'container_name': str(container_name),
            'port_name': str(port_name),
            'direction': 'entry' if direction == 'entry' else 'exit'}


def cell_bound_port(cell: dict):
    """The cell's port binding dict, or None."""
    b = cell.get('bound_to_port')
    return b if (isinstance(b, dict) and b.get('container_name')
                 and b.get('port_name')) else None


def cell_has_formula(cell: dict) -> bool:
    return (cell.get('kind') == 'cell_formula'
            or str(cell.get('value', '')).startswith('='))


def validate_cell_binding(cell: dict, container_sym: dict, port_name: str,
                          direction: str):
    """Validate binding `cell` to container_sym.<port_name> as `direction`.
    Returns (ok, msg). A cell bound to a port must not also be a formula, and
    the port must exist in the requested direction on the container."""
    if container_sym is None:
        return False, 'Container not found'
    if cell_has_formula(cell):
        return False, ('Cell has a formula — clear it before binding to a port '
                       '(a cell is a value, a formula, or a port binding)')
    ports = (entry_points(container_sym) if direction == 'entry'
             else exit_points(container_sym))
    if port_name not in {p.get('name') for p in ports}:
        return False, f'No {direction} port {port_name!r} on that container'
    return True, ''
