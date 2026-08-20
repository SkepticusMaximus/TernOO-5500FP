#!/usr/bin/env python3
"""flowcode_walker — the design-graph runtime (Design Session 2, ruled
20-08-2026).

Walks a FlowCode design — symbols + edges + pockets — following the
ternary doors:

  DECISION  evaluate the condition in the ONE TONGUE (sheet_formula)
            against the blessed namespace → take the +, 0 or − edge.
  LOOP      one hexagon, four kinds (captain's ruling):
              while    test-first
              do       priming pass, test after (DO up top, its while
                       waiting at the bottom)
              for      var over from..to (step), body per value
              foreach  item over a list expression
            The + door is INTERNAL (cycles the pocket body). External
            exits: − done (a definite finish) · 0 bail (the condition
            became unanswerable — the structured Else, never a GOTO).
  GUARD     iteration_guard property (default 10000): a runaway loop
            trips the guard and leaves by the BAIL door with a trace
            message — never a frozen IDE.

Honest v1 boundary (flagged in the ledger): the walker traces bodies
but processes don't yet MUTATE state (assignment/effects ride the I/O
sitting), so a while over static data runs to its guard — visibly, by
design. for/foreach are fully alive: their variables bind per tick and
the body's expressions SEE them (resolver overlay).

Headless and face-neutral: syms/edges in the canvas dict shapes,
`resolver(name)` supplies operand values, `trace(text)` receives the
tick-by-tick story (the captain wants to watch loops tick — half of
learning a language).
"""
import importlib.util as _ilu
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE,
                                                           name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_SF = [None]
_PM = [None]


def _sf():
    if _SF[0] is None:
        _SF[0] = _load("sheet_formula")
    return _SF[0]


def _pm():
    if _PM[0] is None:
        _PM[0] = _load("flowcode_property_model")
    return _PM[0]


def prop(s, name, default=""):
    for p in s.get("properties", []):
        if isinstance(p, dict) and p.get("name") == name:
            return p.get("value", default)
    return default


DEFAULT_GUARD = 10000


class Walker:
    def __init__(self, syms, edges, resolver=None, trace=None,
                 max_steps=2000, variables=None):
        self.syms = syms
        self.edges = edges
        self.resolver = resolver or (lambda name: None)
        self.trace = trace or (lambda s: None)
        self.max_steps = max_steps
        self.steps = 0
        self.binds = {}                 # loop-variable overlay
        self.vars = dict(variables or {})   # THE WALK STORE (assignment
        #                                     lives here — I/O writes to
        #                                     variables, shadow cells and
        #                                     shadow widget props; whiles
        #                                     are ALIVE as of 20-08)
        self.events = []                # ('visit',sid) ('line',txt)
        #                                 ('watch',name,value) — the faces
        #                                 replay these: live highlight +
        #                                 the watch panel (captain, 20-08)

    # ── the one tongue, spoken here ─────────────────────────────────────
    def _lookup(self, name):
        if name in self.binds:
            self.events.append(("watch", name, self.binds[name]))
            return self.binds[name]
        if name in self.vars:
            self.events.append(("watch", name, self.vars[name]))
            return self.vars[name]
        v = self.resolver(name)
        if v is None:
            self.events.append(("watch", name, "#NAME?"))
            raise _sf().FormulaError(f"#NAME? {name}")
        self.events.append(("watch", name, v))
        return v

    def _write(self, address, value, shadow=False):
        self.vars[address] = value
        self.events.append(("watch", address, value))
        return f"{address} = {value!r}" + (" (shadow)" if shadow else "")

    # ── the I/O symbol: WHERE data is read and written ─────────────────
    def _do_io(self, sid, s):
        d = prop(s, "direction", "in")
        ch = prop(s, "channel", "variable")
        addr = str(prop(s, "address", "")).strip()
        label = s.get("label", "?")
        if d == "out":
            expr = prop(s, "expression", "")
            try:
                v = self._eval(expr) if str(expr).strip() else ""
            except Exception as ex:             # noqa: BLE001
                self.trace(f"  ▱ {label} [out·{ch}] ✗ {ex}")
                return
            if ch == "console":
                self.trace(f"  ▱ {label} ⇒ console: {v!r}")
            elif ch == "variable":
                self.trace(f"  ▱ {label} ⇒ "
                           + self._write(addr or "it", v))
            else:                       # cell / widget: SHADOW write —
                #                         committed write-back rides a
                #                         later ruling; the walk sees it
                self.trace(f"  ▱ {label} ⇒ "
                           + self._write(addr, v, shadow=True))
        else:
            if ch == "console":
                self.trace(f"  ▱ {label} [in·console] (no interactive "
                           "source in a walk — skipped)")
                return
            try:
                v = self._lookup(addr) if addr else None
            except Exception:                   # noqa: BLE001
                v = None
            tgt = str(prop(s, "var", "")).strip() or (addr or "it")
            if v is None:
                self.trace(f"  ▱ {label} [in·{ch}] {addr}: nothing to "
                           "read — the dunno stays")
                return
            self.trace(f"  ▱ {label} [in·{ch}] "
                       + self._write(tgt, v))

    def _eval(self, expr):
        sf = _sf()
        node = sf.parse(str(expr).strip().lstrip("="))
        return sf._eval(node, self._lookup,
                        ctx={"name_prop":
                             lambda n, p: self.resolver(f"{n}.{p}")})

    def _door_edge(self, sid, door, scope):
        for e in self.edges:
            if e["src"] == sid and e.get("branch", "") == door:
                return e
        return None

    def _next_edge(self, sid):
        for e in self.edges:
            if e["src"] == sid and not e.get("branch"):
                return e
        return None

    # ── pockets ─────────────────────────────────────────────────────────
    def _pocket_entry(self, container):
        name = container.get("name", "")
        members = {i: s for i, s in self.syms.items()
                   if s.get("parent_scope") == name}
        if not members:
            return None, members
        with_in = {e["dst"] for e in self.edges if e["dst"] in members
                   and e["src"] in members}
        for i in sorted(members):
            if i not in with_in:
                return i, members
        return sorted(members)[0], members

    def _walk_body(self, container, depth):
        entry, members = self._pocket_entry(container)
        if entry is None:
            self.trace(f"      (pocket of {container.get('label', '?')} "
                       "is empty)")
            return
        self._run(entry, depth + 1, within=set(members))

    # ── symbol semantics ────────────────────────────────────────────────
    def _do_decision(self, sid, s):
        pm = _pm()
        cond = prop(s, "condition", "")
        mode = prop(s, "mode", "compare")
        fold = prop(s, "unused_0", "fold-to-−")
        door, detail = pm.decision_route(cond, mode, fold, self._lookup)
        self.trace(f"  ◇ {s.get('label', '?')}: {cond or '(empty)'} "
                   f"→ door {door}   [{detail}]")
        return door

    def _loop_ticks(self, s):
        """Yield (bind_name, value) per body tick, per the kind."""
        kind = prop(s, "kind", "while")
        guard = int(prop(s, "iteration_guard", DEFAULT_GUARD)
                    or DEFAULT_GUARD)
        sf = _sf()
        if kind in ("while", "do"):
            n = 0
            if kind == "do":
                yield None, None            # the priming pass
                n += 1
            while True:
                if n >= guard:
                    raise _Guard(n)
                t = sf.decision_trit(self._eval(prop(s, "condition", "")))
                if t == 0:
                    raise _Bail("condition unanswerable")
                if t < 0:
                    return
                yield None, None
                n += 1
        elif kind == "for":
            var = str(prop(s, "var", "i")) or "i"
            lo = _num_or_bail(self._eval(prop(s, "from", "1")), "from")
            hi = _num_or_bail(self._eval(prop(s, "to", "1")), "to")
            step = _num_or_bail(self._eval(prop(s, "step", "1") or "1"),
                                "step")
            if step == 0:
                raise _Bail("step 0")
            v, n = lo, 0
            while (step > 0 and v <= hi) or (step < 0 and v >= hi):
                if n >= guard:
                    raise _Guard(n)
                yield var, v
                v += step
                n += 1
        elif kind == "foreach":
            var = str(prop(s, "var", "item")) or "item"
            items = self._eval(prop(s, "list", ""))
            if not isinstance(items, list):
                raise _Bail("list expression gave no list")
            for n, item in enumerate(items):
                if n >= guard:
                    raise _Guard(n)
                yield var, item
        else:
            raise _Bail(f"unknown loop kind {kind!r}")

    def _do_loop(self, sid, s, depth):
        kind = prop(s, "kind", "while")
        label = s.get("label", "?")
        ticks = 0
        door = "-"
        note = "done"
        try:
            for var, val in self._loop_ticks(s):
                ticks += 1
                if var is not None:
                    self.binds[var] = val
                    self.events.append(("watch", var, val))
                    self.trace(f"  ⬡ {label} [{kind}] tick {ticks}: "
                               f"{var} = {val}")
                else:
                    self.trace(f"  ⬡ {label} [{kind}] tick {ticks}")
                self._walk_body(s, depth)
        except _Bail as b:
            door, note = "0", f"bail — {b}"
        except _Guard as g:
            door, note = "0", f"guard tripped at {g} ticks — bail"
        finally:
            for var in [k for k in self.binds
                        if prop(s, "var", "") == k]:
                self.binds.pop(var, None)
        self.trace(f"  ⬡ {label} leaves by the {door} door after "
                   f"{ticks} tick(s)  [{note}]")
        return door, ticks

    # ── the walk ────────────────────────────────────────────────────────
    def _run(self, sid, depth, within=None):
        while sid is not None:
            self.steps += 1
            if self.steps > self.max_steps:
                self.trace("… walk step ceiling — stopping")
                return
            s = self.syms.get(sid)
            if s is None:
                return
            self.events.append(("visit", sid))
            kind = s.get("kind", "")
            pad = "  " * depth
            if kind == "flow_decision":
                door = self._do_decision(sid, s)
                e = self._door_edge(sid, door, s.get("parent_scope"))
                if e is None:
                    self.trace(f"{pad}   (no edge on door {door} — "
                               "walk ends here)")
                    return
                sid = e["dst"]
                continue
            if kind == "flow_loop":
                door, _t = self._do_loop(sid, s, depth)
                e = self._door_edge(sid, door, s.get("parent_scope"))
                if e is None:
                    self.trace(f"{pad}   (no edge on door {door} — "
                               "walk ends here)")
                    return
                sid = e["dst"]
                continue
            if kind == "flow_io":
                self._do_io(sid, s)
                e = self._next_edge(sid)
                if e is None:
                    return
                if within is not None and e["dst"] not in within:
                    return
                sid = e["dst"]
                continue
            if kind == "flow_terminator":
                is_entry = bool(prop(s, "is_entry", False))
                self.trace(f"{pad}▸ {s.get('label', '?')} "
                           f"[terminator{' · entry' if is_entry else ''}]")
                if not is_entry and self.steps > 1:
                    return                      # a definite end
            else:
                self.trace(f"{pad}▸ {s.get('label', '?')} "
                           f"[{kind.split('_', 1)[-1]}]")
            e = self._next_edge(sid)
            if e is None:
                return
            if within is not None and e["dst"] not in within:
                return
            sid = e["dst"]


class _Bail(Exception):
    pass


class _Guard(Exception):
    pass


def _num_or_bail(v, what):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise _Bail(f"{what} is not a number")
    return v


def entry_symbol(syms):
    terms = [(i, s) for i, s in sorted(syms.items())
             if s.get("kind") == "flow_terminator"
             and s.get("parent_scope") is None]
    for i, s in terms:
        if prop(s, "is_entry", False):
            return i
    return terms[0][0] if terms else (sorted(syms)[0] if syms else None)


def walk(syms, edges, resolver=None, trace=None, variables=None):
    """Run the design from its entry. Returns a report dict."""
    lines = []
    w = [None]

    def _t(x):
        lines.append(x)
        if w[0] is not None:
            w[0].events.append(("line", x))
        if trace:
            trace(x)
    w[0] = Walker(syms, edges, resolver, _t, variables=variables)
    start = entry_symbol(syms)
    if start is None:
        _t("(nothing to walk)")
        return {"steps": 0, "lines": lines, "events": w[0].events,
                "vars": dict(w[0].vars)}
    w[0]._run(start, 0)
    _t(f"— walk complete: {w[0].steps} step(s)")
    return {"steps": w[0].steps, "lines": lines, "events": w[0].events,
            "vars": dict(w[0].vars)}


def _selftest():
    pm = _pm()
    syms = {
        0: {"kind": "flow_terminator", "label": "START", "name": "start",
            "parent_scope": None,
            "properties": [{"name": "is_entry", "value": True}]},
        1: {"kind": "flow_loop", "label": "L1", "name": "loop1",
            "parent_scope": None, "properties": [
                {"name": "kind", "value": "for"},
                {"name": "var", "value": "i"},
                {"name": "from", "value": "1"},
                {"name": "to", "value": "3"}]},
        2: {"kind": "flow_process", "label": "body", "name": "body",
            "parent_scope": "loop1", "properties": []},
        3: {"kind": "flow_decision", "label": "D", "name": "d",
            "parent_scope": None, "properties": [
                {"name": "condition", "value": "score <=> 27"},
                {"name": "mode", "value": "compare"}]},
        4: {"kind": "flow_terminator", "label": "WIN", "name": "win",
            "parent_scope": None, "properties": []},
        5: {"kind": "flow_terminator", "label": "LOSE", "name": "lose",
            "parent_scope": None, "properties": []},
        6: {"kind": "flow_loop", "label": "W", "name": "w1",
            "parent_scope": None, "properties": [
                {"name": "kind", "value": "while"},
                {"name": "condition", "value": "1 <=> 0"},
                {"name": "iteration_guard", "value": 5}]},
        7: {"kind": "flow_terminator", "label": "BAILED",
            "name": "bailed", "parent_scope": None, "properties": []},
    }
    edges = [
        {"src": 0, "dst": 1},
        {"src": 1, "dst": 3, "branch": "-"},
        {"src": 1, "dst": 5, "branch": "0"},
        {"src": 3, "dst": 4, "branch": "+"},
        {"src": 3, "dst": 5, "branch": "-"},
        {"src": 3, "dst": 6, "branch": "0"},
        {"src": 6, "dst": 7, "branch": "0"},
    ]
    rep = walk(syms, edges, {"score": 30}.get)
    body_ticks = sum(1 for ln in rep["lines"] if "] tick" in ln
                     and "L1" in ln)
    assert body_ticks == 3, rep["lines"]
    assert any("WIN" in ln for ln in rep["lines"]), rep["lines"]
    assert any("i = 3" in ln for ln in rep["lines"])
    # the dunno path: score unresolvable → decision 0 door → while
    # runs to its guard → bail door → BAILED
    rep2 = walk(syms, edges, {}.get)
    assert any("door 0" in ln for ln in rep2["lines"]), rep2["lines"]
    assert any("guard tripped at 5" in ln for ln in rep2["lines"])
    assert any("BAILED" in ln for ln in rep2["lines"])
    # do = priming pass: condition immediately false still runs once
    syms2 = {
        0: syms[0],
        1: {"kind": "flow_loop", "label": "D0", "name": "do1",
            "parent_scope": None, "properties": [
                {"name": "kind", "value": "do"},
                {"name": "condition", "value": "0 <=> 1"}]},
        2: {"kind": "flow_process", "label": "once", "name": "once",
            "parent_scope": "do1", "properties": []},
        3: {"kind": "flow_terminator", "label": "END", "name": "end",
            "parent_scope": None, "properties": []},
    }
    rep3 = walk(syms2, [{"src": 0, "dst": 1},
                        {"src": 1, "dst": 3, "branch": "-"}], {}.get)
    assert sum(1 for ln in rep3["lines"] if "] tick" in ln) == 1
    assert any("once" in ln for ln in rep3["lines"])
    visits = [e for e in rep["events"] if e[0] == "visit"]
    watches = [e for e in rep["events"] if e[0] == "watch"]
    assert visits and ("watch", "i", 3) in watches, watches[:6]
    assert any(e == ("watch", "score", 30) for e in watches)

    # THE STORY GATE — assignment brings the while ALIVE (20-08):
    # x = 0 · while x < 3 · body: x ⇐ x + 1 → 3 ticks, done door, x=3
    syms3 = {
        0: {"kind": "flow_terminator", "label": "START", "name": "s",
            "parent_scope": None,
            "properties": [{"name": "is_entry", "value": True}]},
        1: {"kind": "flow_loop", "label": "W", "name": "w2",
            "parent_scope": None, "properties": [
                {"name": "kind", "value": "while"},
                {"name": "condition", "value": "x < 3"}]},
        2: {"kind": "flow_io", "label": "inc", "name": "inc",
            "parent_scope": "w2", "properties": [
                {"name": "direction", "value": "out"},
                {"name": "channel", "value": "variable"},
                {"name": "address", "value": "x"},
                {"name": "expression", "value": "x + 1"}]},
        3: {"kind": "flow_terminator", "label": "DONE", "name": "dn",
            "parent_scope": None, "properties": []},
    }
    rep4 = walk(syms3, [{"src": 0, "dst": 1},
                        {"src": 1, "dst": 3, "branch": "-"}],
                {}.get, variables={"x": 0})
    ticks = sum(1 for ln in rep4["lines"] if "] tick" in ln)
    assert ticks == 3, rep4["lines"]
    assert rep4["vars"].get("x") == 3, rep4["vars"]
    assert any("DONE" in ln for ln in rep4["lines"])
    assert any("(shadow)" not in ln and "x = 3" in ln
               for ln in rep4["lines"])
    return {"for_ticks": body_ticks, "guard": "trips to bail",
            "do": "priming pass runs once",
            "events": len(rep["events"]),
            "while_alive": f"x=0 → {ticks} ticks → "
                           f"x={rep4['vars'].get('x')} · done door"}


if __name__ == "__main__":
    print(_selftest())
