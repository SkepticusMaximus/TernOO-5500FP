"""flowcode_dialect.py — the textual FlowCode dialect.

A line-oriented textual projection of the same program model the visual
canvas represents.  Not Python; not JavaScript; a purpose-built dialect
mapping 1:1 onto the substrate.  Two functions matter:

    project(model)  -> canonical dialect text
    parse(text)     -> model  (raises DialectError with line numbers)

`model` is the dict quintet the substrate speaks everywhere else:
{'widgets': {...}, 'flows': {...}, 'cells': {...}, 'cmds': {...},
 'flow_edges': [...], 'cmd_edges': [...], 'notes': [...]}

Because project() emits a canonical form (stable ordering, normalized
whitespace), the round-trip law is exact:  project(parse(t)) == project(m)
whenever t == project(m).  test_dialect.py pins it.

Syntax (locked per the text/language handoff's delegation; documented in
docs/design/CF5-Textual-FlowCode-Dialect.md):

    # comment                              → MNOTE round-trip
    window main_win "Main" at 200,150 size 400x300 layout vbox:
        button go "Go" at 200,200 size 120x60
    terminator runner "go" at 700,100 size 120x60 entry
    process doubler "Doubler" at 300,200 size 120x60:
        in input_value: number
        out output_value: number = input_value * 2
        process step1 "step" at 320,220 size 120x60
    edge runner -> doubler
    cell A1 = 10
    cell B1 = "Name"
    cell A2 = =A1+A1
    cmd k1 = math_add(a=4, b=5) at 10,10
    pipe k1 -> k2.a

Indent = containment (GUI parent, flow pocket).  4 spaces per level.

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import re

# kind ↔ keyword tables ------------------------------------------------------
GUI_KINDS = {'window': 'gui_window', 'button': 'gui_button',
             'label': 'gui_label', 'entry': 'gui_entry',
             'toggle': 'gui_toggle', 'listbox': 'gui_listbox',
             'canvas': 'gui_canvas'}
FLOW_KINDS = {'terminator': 'flow_terminator', 'process': 'flow_process',
              'decision': 'flow_decision', 'io': 'flow_io',
              'data': 'flow_data'}
KEYWORD_OF = {v: k for k, v in {**GUI_KINDS, **FLOW_KINDS}.items()}
INDENT = '    '


class DialectError(ValueError):
    def __init__(self, line_no: int, message: str):
        super().__init__(f"line {line_no}: {message}")
        self.line_no = line_no


# ═══════════════════════════════════════════════════════════════════════════
# project(model) → canonical text
# ═══════════════════════════════════════════════════════════════════════════

def _fmt_cell_value(cell) -> str:
    k, v = cell.get('kind'), cell.get('value')
    if k == 'cell_number':
        return str(v)
    if k == 'cell_formula':
        return str(v)                      # formulas keep their leading '='
    return '"' + str(v).replace('"', '\\"') + '"'


def _node_line(ent, kind_kw) -> str:
    x, y = int(ent.get('x', 0)), int(ent.get('y', 0))
    w, h = int(ent.get('w', 120)), int(ent.get('h', 60))
    name = ent.get('name') or f"anon_{abs(int(ent.get('id', 0)))}"
    label = str(ent.get('label', '')).replace('"', '\\"')
    line = f'{kind_kw} {name} "{label}" at {x},{y} size {w}x{h}'
    lay = ent.get('layout_mode')
    if lay and lay != 'absolute':
        line += f' layout {lay}'
    if any(p.get('name') == 'is_entry' and p.get('value')
           for p in (ent.get('properties') or [])) or ent.get('is_entry'):
        line += ' entry'
    return line


def _children_map(entities, parent_key):
    kids = {}
    for ident, e in entities.items():
        kids.setdefault(e.get(parent_key), []).append(ident)
    for v in kids.values():   # authoring order: ids ascend in creation order
        v.sort(key=lambda i: (not isinstance(i, int),
                              i if isinstance(i, int) else str(i)))
    return kids


def _emit_tree(out, entities, kids, ident, depth, kind_kw_of, port_emit):
    e = entities[ident]
    kw = kind_kw_of(e)
    has_kids = bool(kids.get(ident)) or port_emit(e, None, 0, probe=True)
    line = INDENT * depth + _node_line(e, kw) + (':' if has_kids else '')
    out.append(line)
    port_emit(e, out, depth + 1)
    for kid in kids.get(ident, []):
        _emit_tree(out, entities, kids, kid, depth + 1, kind_kw_of, port_emit)


def project(model: dict) -> str:
    widgets = dict(model.get('widgets') or {})
    flows = dict(model.get('flows') or {})
    cells = dict(model.get('cells') or {})
    cmds = dict(model.get('cmds') or {})
    out = []

    for n in (model.get('notes') or []):
        out.append(str(n.get('text') if isinstance(n, dict) else n))

    # GUI tree (containment by parent_id)
    wkids = _children_map(widgets, 'parent_id')
    def _wkw(e):
        return KEYWORD_OF.get(e.get('kind'), e.get('kind', 'widget'))
    def _no_ports(e, out_, depth, probe=False):
        return False
    for ident in wkids.get(None, []):
        _emit_tree(out, widgets, wkids, ident, 0, _wkw, _no_ports)

    # Flow tree (pockets by parent_scope, which is a NAME)
    name_to_fid = {f.get('name'): i for i, f in flows.items() if f.get('name')}
    fkids = {}
    for i, f in flows.items():
        parent = name_to_fid.get(f.get('parent_scope'))
        fkids.setdefault(parent, []).append(i)
    for v in fkids.values():
        v.sort(key=lambda i: (not isinstance(i, int),
                              i if isinstance(i, int) else str(i)))
    def _fkw(e):
        return KEYWORD_OF.get(e.get('kind'), e.get('kind', 'process'))
    def _ports(e, out_, depth, probe=False):
        eps = e.get('entry_points') or []
        xps = e.get('exit_points') or []
        if probe:
            return bool(eps or xps)
        for p in eps:
            out_.append(INDENT * depth +
                        f"in {p.get('name')}: {p.get('type', 'number')}")
        for p in xps:
            line = INDENT * depth + \
                f"out {p.get('name')}: {p.get('type', 'number')}"
            if p.get('expr'):
                line += f" = {p['expr']}"
            out_.append(line)
        return bool(eps or xps)
    for ident in fkids.get(None, []):
        _emit_tree(out, flows, fkids, ident, 0, _fkw, _ports)

    # flow edges by name
    fname = {i: (f.get('name') or f"anon_{abs(int(i)) if str(i).lstrip('-').isdigit() else i}")
             for i, f in flows.items()}
    for e in sorted((model.get('flow_edges') or []),
                    key=lambda e: (str(e.get('src')), str(e.get('dst')))):
        out.append(f"edge {fname.get(e.get('src'), e.get('src'))} -> "
                   f"{fname.get(e.get('dst'), e.get('dst'))}")

    # cells, A1-ordered
    import sheet_formula as _sf
    for (r, c) in sorted(cells):
        out.append(f"cell {_sf.rc_to_a1(r, c)} = "
                   f"{_fmt_cell_value(cells[(r, c)])}")

    # commands + pipes
    cname = {i: (cm.get('name') or f"c{abs(int(i)) if str(i).lstrip('-').isdigit() else i}")
             for i, cm in cmds.items()}
    for i in sorted(cmds, key=lambda i: (not isinstance(i, int),
                                         i if isinstance(i, int) else str(i))):
        cm = cmds[i]
        kind = cm.get('kind', '')
        short = kind[4:] if kind.startswith('cmd_') else kind
        _pd = {p.get('name'): p.get('value')
               for p in (cm.get('properties') or [])}
        _pd.update(cm.get('params') or {})
        params = ', '.join(f"{k}={_fmt_param(v)}"
                           for k, v in sorted(_pd.items()))
        out.append(f"cmd {cname[i]} = {short}({params}) "
                   f"at {int(cm.get('x', 0))},{int(cm.get('y', 0))}")
    for e in sorted((model.get('cmd_edges') or []),
                    key=lambda e: (str(e.get('src')), str(e.get('dst')))):
        line = f"pipe {cname.get(e.get('src'), e.get('src'))} -> " \
               f"{cname.get(e.get('dst'), e.get('dst'))}"
        if e.get('dst_param'):
            line += f".{e['dst_param']}"
        out.append(line)

    return '\n'.join(out) + ('\n' if out else '')


def _fmt_param(v):
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    return '"' + s.replace('"', '\\"') + '"'


# ═══════════════════════════════════════════════════════════════════════════
# parse(text) → model
# ═══════════════════════════════════════════════════════════════════════════

_NODE_RE = re.compile(
    r'^(?P<kw>\w+)\s+(?P<name>[A-Za-z_]\w*)\s+"(?P<label>(?:[^"\\]|\\.)*)"'
    r'\s+at\s+(?P<x>-?\d+),(?P<y>-?\d+)\s+size\s+(?P<w>\d+)x(?P<h>\d+)'
    r'(?:\s+layout\s+(?P<layout>\w+))?(?P<entry>\s+entry)?(?P<colon>:)?\s*$')
_PORT_RE = re.compile(
    r'^(?P<dir>in|out)\s+(?P<name>[A-Za-z_]\w*)\s*:\s*(?P<type>\w+)'
    r'(?:\s*=\s*(?P<expr>.+?))?\s*$')
_EDGE_RE = re.compile(r'^edge\s+(?P<src>[\w]+)\s*->\s*(?P<dst>[\w]+)\s*$')
_CELL_RE = re.compile(r'^cell\s+(?P<ref>[A-Za-z]+\d+)\s*=\s*(?P<val>.+?)\s*$')
_CMD_RE = re.compile(
    r'^cmd\s+(?P<name>[A-Za-z_]\w*)\s*=\s*(?P<kind>\w+)\((?P<params>.*)\)'
    r'\s+at\s+(?P<x>-?\d+),(?P<y>-?\d+)\s*$')
_PIPE_RE = re.compile(
    r'^pipe\s+(?P<src>[\w]+)\s*->\s*(?P<dst>[\w]+)(?:\.(?P<param>\w+))?\s*$')


def _unescape(s):
    return s.replace('\\"', '"')


def _parse_params(s, line_no):
    params = {}
    s = s.strip()
    if not s:
        return params
    # split on commas not inside quotes
    parts, buf, q = [], '', False
    for ch in s:
        if ch == '"':
            q = not q
        if ch == ',' and not q:
            parts.append(buf); buf = ''
        else:
            buf += ch
    parts.append(buf)
    for p in parts:
        if '=' not in p:
            raise DialectError(line_no, f"bad parameter {p.strip()!r}")
        k, v = p.split('=', 1)
        k, v = k.strip(), v.strip()
        if v.startswith('"') and v.endswith('"'):
            params[k] = _unescape(v[1:-1])
        else:
            try:
                params[k] = int(v)
            except ValueError:
                try:
                    params[k] = float(v)
                except ValueError:
                    params[k] = v
        if not k.isidentifier():
            raise DialectError(line_no, f"bad parameter name {k!r}")
    return params


def parse(text: str) -> dict:
    import sheet_formula as _sf
    widgets, flows, cells, cmds = {}, {}, {}, {}
    flow_edges, cmd_edges, notes = [], [], []
    next_id = [1]
    cmd_ids = {}

    # stack of (indent_level, ('widget'|'flow', ident))
    stack = []

    def _fresh():
        i = next_id[0]; next_id[0] += 1; return i

    for line_no, raw in enumerate(text.splitlines(), start=1):
        if not raw.strip():
            continue
        indent_ws = len(raw) - len(raw.lstrip(' '))
        if raw.lstrip(' ').startswith('\t'):
            raise DialectError(line_no, "tabs not allowed; indent with spaces")
        if indent_ws % len(INDENT):
            raise DialectError(line_no,
                               f"indent must be multiples of {len(INDENT)} spaces")
        depth = indent_ws // len(INDENT)
        line = raw.strip()

        if line.startswith('#'):
            notes.append({'index': len(widgets) + len(flows), 'text': line})
            continue

        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent = stack[-1] if stack else None

        m = _PORT_RE.match(line)
        if m and parent and parent[1][0] == 'flow':
            f = flows[parent[1][1]]
            port = {'name': m['name'], 'type': m['type'], 'description': ''}
            if m['expr']:
                port['expr'] = m['expr'].strip()
            key = 'entry_points' if m['dir'] == 'in' else 'exit_points'
            f.setdefault(key, []).append(port)
            continue

        m = _NODE_RE.match(line)
        if m:
            kw = m['kw']
            ident = _fresh()
            ent = {'id': ident, 'name': m['name'],
                   'label': _unescape(m['label']),
                   'x': int(m['x']), 'y': int(m['y']),
                   'w': int(m['w']), 'h': int(m['h']), 'properties': []}
            if kw in GUI_KINDS:
                ent['kind'] = GUI_KINDS[kw]
                ent['layout_mode'] = m['layout'] or 'absolute'
                ent['signal_ids'] = {}
                ent['parent_id'] = (parent[1][1]
                                    if parent and parent[1][0] == 'widget'
                                    else None)
                if parent and parent[1][0] == 'flow':
                    raise DialectError(line_no,
                                       "GUI widget cannot nest inside a flow block")
                widgets[ident] = ent
                stack.append((depth, ('widget', ident)))
            elif kw in FLOW_KINDS:
                ent['kind'] = FLOW_KINDS[kw]
                if m['entry']:
                    ent['properties'] = [{'name': 'is_entry', 'value': True}]
                if parent and parent[1][0] == 'flow':
                    ent['parent_scope'] = flows[parent[1][1]]['name']
                elif parent:
                    raise DialectError(line_no,
                                       "flow symbol cannot nest inside a widget block")
                flows[ident] = ent
                stack.append((depth, ('flow', ident)))
            else:
                raise DialectError(line_no, f"unknown symbol kind {kw!r}")
            continue

        if depth:
            raise DialectError(line_no,
                               "only symbols, ports and comments may be indented")

        m = _EDGE_RE.match(line)
        if m:
            flow_edges.append({'src': m['src'], 'dst': m['dst']})
            continue
        m = _CELL_RE.match(line)
        if m:
            rc = _sf.a1_to_rc(m['ref'])
            if rc is None:
                raise DialectError(line_no, f"bad cell ref {m['ref']!r}")
            v = m['val']
            if v.startswith('='):
                cells[rc] = {'kind': 'cell_formula', 'value': v}
            elif v.startswith('"') and v.endswith('"'):
                cells[rc] = {'kind': 'cell_text', 'value': _unescape(v[1:-1])}
            else:
                try:
                    cells[rc] = {'kind': 'cell_number', 'value': int(v)}
                except ValueError:
                    raise DialectError(line_no, f"bad cell value {v!r}")
            continue
        m = _CMD_RE.match(line)
        if m:
            ident = 1000 + len(cmds)
            cmd_ids[m['name']] = ident
            _prm = _parse_params(m['params'], line_no)
            cmds[ident] = {'id': ident, 'name': m['name'],
                           'kind': 'cmd_' + m['kind'],
                           'x': int(m['x']), 'y': int(m['y']),
                           'w': 160, 'h': 80, 'label': '',
                           'properties': [{'name': k, 'value': v}
                                          for k, v in _prm.items()]}
            continue
        m = _PIPE_RE.match(line)
        if m:
            e = {'src': cmd_ids.get(m['src'], m['src']),
                 'dst': cmd_ids.get(m['dst'], m['dst'])}
            if m['param']:
                e['dst_param'] = m['param']
            cmd_edges.append(e)
            continue

        raise DialectError(line_no, f"cannot parse: {line!r}")

    # resolve flow-edge names → ids where possible
    fbyname = {f['name']: i for i, f in flows.items()}
    for e in flow_edges:
        e['src'] = fbyname.get(e['src'], e['src'])
        e['dst'] = fbyname.get(e['dst'], e['dst'])

    return {'widgets': widgets, 'flows': flows, 'cells': cells,
            'cmds': cmds, 'flow_edges': flow_edges,
            'cmd_edges': cmd_edges, 'notes': notes}
