"""flowcode_lingo_translate.py — the Translator projection engine.

One shared traversal of the program model yields semantic events; one small
renderer per dialect turns the event stream into pseudocode.  Projections
from the substrate, not translations between languages: same words, five
mental models.  Per the handoff: recognizable to programmers of that
flavor, pseudocode not executable, lossy at style level, faithful at
semantic level.

    render(model, 'python' | 'java' | 'vb' | 'c' | 'flowcode') -> str

Adding a dialect = one new ~100-line renderer class.

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import importlib.util as _ilu
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_dialect = _load('flowcode_dialect')

DIALECTS = ('flowcode', 'python', 'java', 'vb', 'c')


# ═══════════════════════════════════════════════════════════════════════════
# Traversal → semantic events
# ═══════════════════════════════════════════════════════════════════════════

def _props(ent):
    return {p.get('name'): p.get('value') for p in (ent.get('properties') or [])}


def events(model: dict):
    """Yield (event, payload) tuples in stable program order."""
    widgets = dict(model.get('widgets') or {})
    flows = dict(model.get('flows') or {})
    cells = dict(model.get('cells') or {})
    cmds = dict(model.get('cmds') or {})

    def _order(d):
        return sorted(d, key=lambda i: (not isinstance(i, int),
                                        i if isinstance(i, int) else str(i)))

    # GUI
    kids = {}
    for i, w in widgets.items():
        kids.setdefault(w.get('parent_id'), []).append(i)
    for v in kids.values():
        v.sort(key=lambda i: (not isinstance(i, int),
                              i if isinstance(i, int) else str(i)))

    def _walk_widget(i, depth):
        w = widgets[i]
        yield ('widget', {'depth': depth, 'kind': w.get('kind', ''),
                          'name': w.get('name') or f'w{i}',
                          'label': w.get('label', ''),
                          'layout': w.get('layout_mode', 'absolute'),
                          'container': bool(kids.get(i))})
        for k in kids.get(i, []):
            yield from _walk_widget(k, depth + 1)
        if kids.get(i):
            yield ('widget_end', {'depth': depth,
                                  'name': w.get('name') or f'w{i}'})

    for i in kids.get(None, []):
        yield from _walk_widget(i, 0)

    # Flow: handlers (entry terminators) then containers/processes
    name_to_fid = {f.get('name'): i for i, f in flows.items()
                   if f.get('name')}
    fkids = {}
    for i, f in flows.items():
        fkids.setdefault(name_to_fid.get(f.get('parent_scope')),
                         []).append(i)
    for v in fkids.values():
        v.sort(key=lambda i: (not isinstance(i, int),
                              i if isinstance(i, int) else str(i)))

    def _walk_flow(i, depth):
        f = flows[i]
        is_entry = bool(_props(f).get('is_entry')) or f.get('is_entry')
        ev = {'depth': depth, 'kind': f.get('kind', ''),
              'name': f.get('name') or f'f{i}',
              'label': f.get('label', ''), 'is_entry': is_entry,
              'entry_points': f.get('entry_points') or [],
              'exit_points': f.get('exit_points') or [],
              'container': bool(fkids.get(i))}
        yield ('flow', ev)
        for p in ev['entry_points']:
            yield ('port_in', {'depth': depth + 1, **p})
        for p in ev['exit_points']:
            yield ('port_out', {'depth': depth + 1, **p})
        for k in fkids.get(i, []):
            yield from _walk_flow(k, depth + 1)
        if fkids.get(i) or ev['entry_points'] or ev['exit_points']:
            yield ('flow_end', {'depth': depth, 'name': ev['name']})

    for i in fkids.get(None, []):
        yield from _walk_flow(i, 0)

    for e in (model.get('flow_edges') or []):
        nm = {i: f.get('name') or str(i) for i, f in flows.items()}
        yield ('edge', {'src': nm.get(e.get('src'), e.get('src')),
                        'dst': nm.get(e.get('dst'), e.get('dst'))})

    import sheet_formula as _sf
    for rc in sorted(cells):
        c = cells[rc]
        yield ('cell', {'ref': _sf.rc_to_a1(*rc), 'kind': c.get('kind'),
                        'value': c.get('value')})

    cname = {i: (c.get('name') or f'c{i}') for i, c in cmds.items()}
    for i in _order(cmds):
        c = cmds[i]
        kind = c.get('kind', '')
        yield ('cmd', {'name': cname[i],
                       'op': kind[4:] if kind.startswith('cmd_') else kind,
                       'args': _props(c) or dict(c.get('params') or {})})
    for e in (model.get('cmd_edges') or []):
        yield ('pipe', {'src': cname.get(e.get('src'), e.get('src')),
                        'dst': cname.get(e.get('dst'), e.get('dst')),
                        'param': e.get('dst_param')})


# ═══════════════════════════════════════════════════════════════════════════
# Renderers
# ═══════════════════════════════════════════════════════════════════════════

def _sq(v):
    return repr(v) if isinstance(v, str) else str(v)


class _Py:
    IND = '    '
    def render(self, evs):
        o = ['# Python-flavored projection of the TernOO word substrate']
        for ev, p in evs:
            d = self.IND * p.get('depth', 0)
            if ev == 'widget':
                kw = p['kind'].replace('gui_', '')
                if p['container']:
                    o.append(f"{d}with ui.{kw}({p['name']!r}, "
                             f"label={p['label']!r}, layout={p['layout']!r}):")
                else:
                    o.append(f"{d}{p['name']} = ui.{kw}(label={p['label']!r})")
            elif ev == 'flow':
                if p['is_entry']:
                    o.append(f"{d}def {p['name']}():   # entry handler "
                             f"({p['label']!r})")
                elif p['container'] or p['entry_points'] or p['exit_points']:
                    o.append(f"{d}def {p['name']}("
                             + ', '.join(pt['name']
                                         for pt in p['entry_points'])
                             + f"):   # {p['kind'].replace('flow_', '')}")
                else:
                    o.append(f"{d}{p['name']}()   # "
                             f"{p['kind'].replace('flow_', '')} "
                             f"{p['label']!r}")
            elif ev == 'port_out':
                d2 = self.IND * p['depth']
                o.append(f"{d2}return {p.get('expr', p['name'])}"
                         f"   # -> {p['name']}: {p['type']}")
            elif ev == 'edge':
                o.append(f"{p['src']}()  # then")
                o.append(f"{p['dst']}()")
            elif ev == 'cell':
                o.append(f"sheet[{p['ref']!r}] = "
                         + (p['value'][1:] if p['kind'] == 'cell_formula'
                            else _sq(p['value'])))
            elif ev == 'cmd':
                args = ', '.join(f"{k}={_sq(v)}"
                                 for k, v in sorted(p['args'].items()))
                o.append(f"{p['name']} = shell.{p['op']}({args})")
            elif ev == 'pipe':
                o.append(f"{p['dst']}.{p['param'] or 'input'} = {p['src']}")
        return '\n'.join(o) + '\n'


class _CStyle:
    """Shared brace-language machinery for Java and C."""
    IND = '    '
    HEAD, FN, CALL_SUFFIX = '//', 'void', ';'
    def render(self, evs):
        o = [f'{self.HEAD} {self.NAME}-flavored projection of the TernOO '
             f'word substrate']
        opens = []
        for ev, p in evs:
            d = self.IND * (p.get('depth', 0) + len(self.PREOPEN(p)))
            for pre in self.PREOPEN(p):
                pass
            if ev == 'widget':
                kw = p['kind'].replace('gui_', '')
                if p['container']:
                    o.append(self.IND * p['depth'] +
                             f"{self.FN} {p['name']}() {{  "
                             f"{self.HEAD} {kw} \"{p['label']}\" "
                             f"layout={p['layout']}")
                else:
                    o.append(self.IND * p['depth'] +
                             f"ui_{kw}({_c(p['name'])}, \"{p['label']}\")"
                             f"{self.CALL_SUFFIX}")
            elif ev == 'widget_end' or ev == 'flow_end':
                o.append(self.IND * p['depth'] + '}')
            elif ev == 'flow':
                params = ', '.join(f"{self.TY(pt['type'])} {pt['name']}"
                                   for pt in p['entry_points'])
                ret = (self.TY(p['exit_points'][0]['type'])
                       if p['exit_points'] else self.FN)
                if p['is_entry']:
                    o.append(self.IND * p['depth'] +
                             f"{self.FN} {p['name']}() {{  "
                             f"{self.HEAD} entry \"{p['label']}\"")
                    o.append(self.IND * (p['depth'] + 1) +
                             f"{self.HEAD} ...")
                    o.append(self.IND * p['depth'] + '}')
                elif p['container'] or p['entry_points'] or p['exit_points']:
                    o.append(self.IND * p['depth'] +
                             f"{ret} {p['name']}({params}) {{")
                else:
                    o.append(self.IND * p['depth'] +
                             f"{p['name']}(){self.CALL_SUFFIX}  "
                             f"{self.HEAD} {p['label']}")
            elif ev == 'port_out':
                o.append(self.IND * p['depth'] +
                         f"return {p.get('expr', p['name'])}"
                         f"{self.CALL_SUFFIX}")
            elif ev == 'edge':
                o.append(f"{p['src']}(){self.CALL_SUFFIX} "
                         f"{p['dst']}(){self.CALL_SUFFIX}")
            elif ev == 'cell':
                v = (p['value'][1:] if p['kind'] == 'cell_formula'
                     else _cq(p['value']))
                o.append(f"sheet_set(\"{p['ref']}\", {v})"
                         f"{self.CALL_SUFFIX}")
            elif ev == 'cmd':
                args = ', '.join(_cq(v) for _, v in sorted(p['args'].items()))
                o.append(f"{self.VAR} {p['name']} = "
                         f"{p['op']}({args}){self.CALL_SUFFIX}")
            elif ev == 'pipe':
                o.append(f"{self.HEAD} pipe: {p['src']} -> "
                         f"{p['dst']}.{p['param'] or 'in'}")
        return '\n'.join(o) + '\n'
    def PREOPEN(self, p):
        return ()
    def TY(self, t):
        return {'number': 'int', 'text': 'String',
                'boolean': 'boolean'}.get(t, t)


def _c(s):
    return f'"{s}"'


def _cq(v):
    return f'"{v}"' if isinstance(v, str) else str(v)


class _Java(_CStyle):
    NAME, VAR = 'Java', 'var'


class _C(_CStyle):
    NAME, VAR = 'C', 'int'
    def TY(self, t):
        return {'number': 'int', 'text': 'const char*',
                'boolean': 'bool'}.get(t, t)


class _VB:
    IND = '    '
    def render(self, evs):
        o = ["' VB-flavored projection of the TernOO word substrate"]
        for ev, p in evs:
            d = self.IND * p.get('depth', 0)
            if ev == 'widget':
                kw = p['kind'].replace('gui_', '').capitalize()
                if p['container']:
                    o.append(f"{d}Begin {kw} {p['name']}   "
                             f"' \"{p['label']}\" Layout={p['layout']}")
                else:
                    o.append(f"{d}Dim {p['name']} As New {kw}"
                             f"(\"{p['label']}\")")
            elif ev == 'widget_end':
                o.append(f"{d}End {p['name']}")
            elif ev == 'flow':
                if p['is_entry']:
                    o.append(f"{d}Sub {p['name']}()   "
                             f"' entry \"{p['label']}\"")
                elif p['container'] or p['entry_points'] or p['exit_points']:
                    params = ', '.join(
                        f"{pt['name']} As {self.TY(pt['type'])}"
                        for pt in p['entry_points'])
                    if p['exit_points']:
                        o.append(f"{d}Function {p['name']}({params}) As "
                                 f"{self.TY(p['exit_points'][0]['type'])}")
                    else:
                        o.append(f"{d}Sub {p['name']}({params})")
                else:
                    o.append(f"{d}Call {p['name']}()   ' {p['label']}")
            elif ev == 'port_out':
                o.append(f"{d}Return {p.get('expr', p['name'])}")
            elif ev == 'flow_end':
                o.append(f"{d}End Sub")
            elif ev == 'edge':
                o.append(f"Call {p['src']}() : Call {p['dst']}()")
            elif ev == 'cell':
                v = (p['value'][1:] if p['kind'] == 'cell_formula'
                     else _cq(p['value']))
                o.append(f"Sheet(\"{p['ref']}\") = {v}")
            elif ev == 'cmd':
                args = ', '.join(f"{k}:={_cq(v)}"
                                 for k, v in sorted(p['args'].items()))
                o.append(f"Dim {p['name']} = Shell.{p['op']}({args})")
            elif ev == 'pipe':
                o.append(f"' pipe: {p['src']} -> {p['dst']}."
                         f"{p['param'] or 'in'}")
        return '\n'.join(o) + '\n'
    def TY(self, t):
        return {'number': 'Integer', 'text': 'String',
                'boolean': 'Boolean'}.get(t, t)


class _FlowCode:
    def render_model(self, model):
        return _dialect.project(model)


def render(model: dict, dialect: str) -> str:
    """model → pseudocode in the named dialect."""
    if dialect == 'flowcode':
        return _dialect.project(model)
    evs = list(events(model))
    r = {'python': _Py, 'java': _Java, 'vb': _VB, 'c': _C}.get(dialect)
    if r is None:
        raise ValueError(f"unknown dialect {dialect!r}; "
                         f"one of {DIALECTS}")
    return r().render(evs)
