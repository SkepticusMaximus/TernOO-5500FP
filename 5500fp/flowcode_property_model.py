#!/usr/bin/env python3
"""flowcode_property_model — the CANON property record (ruled 20-08).

Captain's ruling: every property, on every symbol, in every tab, is ONE
record —

    name    · what it's called
    type    · expression | choice | text | number | trit | ref | list
    default · what it starts as
    domain  · where values come from (choice list, 'registry:...' query,
              'names:...' namespace query — resolved by providers)
    filter  · what narrows the domain (data-type compatibility)

Symbol families DECLARE their properties in this shape; panels build
themselves from the declarations. Face-neutral and headless: the DPG
organs and (later) the Tk face both read it; domain resolution takes a
`providers` dict so the module never imports UI.

First customer (ruled): the DECISION family — three ports always
(+ / 0 / −), a condition speaking the ONE TONGUE (sheet_formula), and
the unused-0 folding choice for boolean mode. The captain's recursion
insight rides the 0 port: the middle door can defer to another
decision without sacrificing a definite exit — structurally beyond
binary conditionals.
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
_REG = [None]


def _sf():
    if _SF[0] is None:
        _SF[0] = _load("sheet_formula")
    return _SF[0]


def _reg():
    if _REG[0] is None:
        _REG[0] = _load("word_type_registry")
    return _REG[0]


def record(name, type_, default="", domain=None, filter_=None, label=""):
    return {"name": name, "type": type_, "default": default,
            "domain": domain, "filter": filter_,
            "label": label or name.replace("_", " ")}


# ── the declarations (families grow here as legs land) ──────────────────────
DECLARATIONS = {
    "flow_decision": [
        record("condition", "expression", "",
               label="condition (one tongue)"),
        record("mode", "choice", "compare",
               domain=["compare", "boolean"],
               label="mode"),
        record("unused_0", "choice", "fold-to-−",
               domain=["fold-to-−", "fold-to-+", "refuse"],
               label="unused 0 (boolean mode)"),
    ],
    "flow_process": [
        record("note", "text", "", label="note"),
    ],
    "flow_subroutine": [
        record("note", "text", "", label="note"),
    ],
    "flow_terminator": [
        record("is_entry", "trit", 0,
               label="is entry (+1 yes · 0 auto · −1 no)"),
    ],
    # flow_io: channel/address family rides the I/O design sitting —
    # declared here the moment it's ruled, panel picks it up for free.
    "flow_io": [
        record("note", "text", "", label="note"),
    ],
}

BRANCHES = ("+", "0", "-")          # the three doors, always


def declarations_for(kind):
    return [dict(r) for r in DECLARATIONS.get(kind, [])]


# ── domain resolution ───────────────────────────────────────────────────────
def resolve_domain(domain, providers=None):
    """A domain is: a literal list · 'registry:<primary>.<name*>' ·
    'names:<kind>' (resolved by the caller's providers dict, e.g.
    providers['names'](kind) -> [str])."""
    if domain is None:
        return None
    if isinstance(domain, (list, tuple)):
        return list(domain)
    if isinstance(domain, str) and domain.startswith("registry:"):
        return [e["name"] for _p, _q, e in _reg().query(domain)]
    if isinstance(domain, str) and domain.startswith("names:"):
        p = (providers or {}).get("names")
        return list(p(domain.split(":", 1)[1])) if p else []
    return None


def validate(rec, value, providers=None):
    """(ok, message). Expressions parse in the ONE TONGUE; choices must
    sit in their resolved domain; trits are −1/0/+1."""
    t = rec["type"]
    if t == "expression":
        v = str(value).strip()
        if not v:
            return True, "empty (always 0-door)"
        try:
            _sf().parse(v.lstrip("="))
            return True, "✓ parses"
        except Exception as e:                  # noqa: BLE001
            return False, f"✗ {e}"
    if t == "choice":
        dom = resolve_domain(rec["domain"], providers) or []
        return (value in dom,
                "✓" if value in dom else f"✗ not in {dom}")
    if t == "trit":
        try:
            return int(value) in (-1, 0, 1), "trit"
        except (TypeError, ValueError):
            return False, "✗ not a trit"
    if t == "number":
        try:
            float(value)
            return True, "number"
        except (TypeError, ValueError):
            return False, "✗ not a number"
    return True, ""                             # text/ref/list: free-form


def decision_route(condition, mode, unused_0, resolver):
    """Design-time preview + (later) runtime semantics of the ruled
    Decision: evaluate the condition in the one tongue and pick a door.
    `resolver(name)` supplies operand values (the blessed namespace).
    Returns ('+' | '0' | '-', detail)."""
    sf = _sf()
    v = str(condition or "").strip().lstrip("=")
    if not v:
        return "0", "empty condition → the dunno door"
    try:
        node = sf.parse(v)
        result = sf._eval(node, resolver, ctx=None)
    except Exception as e:                      # noqa: BLE001
        return "0", f"error → 0 ({e})"
    t = sf.decision_trit(result)
    door = {1: "+", 0: "0", -1: "-"}[t]
    if mode == "boolean" and door == "0":
        door = {"fold-to-−": "-", "fold-to-+": "+",
                "refuse": "0"}.get(unused_0, "-")
        return door, f"boolean 0-fold → {door}"
    return door, f"{result!r} → {door}"


def _selftest():
    recs = declarations_for("flow_decision")
    assert [r["name"] for r in recs] == ["condition", "mode", "unused_0"]
    ok, msg = validate(recs[0], "a <=> b")
    assert ok, msg
    ok, msg = validate(recs[0], "1 +* 2")
    assert not ok
    ok, _ = validate(recs[1], "compare")
    assert ok
    ok, _ = validate(recs[1], "quantum")
    assert not ok
    dom = resolve_domain("registry:DATA.STRING_*")
    assert len(dom) == 3 and "STRING_TERNARY" in dom
    env = {"a": 7, "b": 3, "x": 3}
    door, _d = decision_route("a <=> b", "compare", "fold-to-−",
                              env.__getitem__)
    assert door == "+"
    door, _d = decision_route("b <=> a", "compare", "fold-to-−",
                              env.__getitem__)
    assert door == "-"
    door, _d = decision_route("x <=> b", "compare", "fold-to-−",
                              env.__getitem__)
    assert door == "0", "the dunno door, $100 to the captain"
    door, _d = decision_route("a = 99", "boolean", "fold-to-−",
                              env.__getitem__)
    assert door == "-"
    door, _d = decision_route("", "compare", "fold-to-−", env.__getitem__)
    assert door == "0"
    return {"families": len(DECLARATIONS), "doors": BRANCHES,
            "registry_domain": len(dom)}


if __name__ == "__main__":
    print(_selftest())
