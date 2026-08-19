#!/usr/bin/env python3
"""word_type_registry — the system-wide SECONDARY word-type index.

Captain's design, 20-08-2026 (DOCFLAG ledger, same date): for each of
the NINE primaries there are 81 qualifier-field variants (T21–T18,
four trits). This registry holds that whole 9×81 grid EXPLICITLY —
each slot either DEFINED (name · format · handler) or left OPEN — so
future secondary types (say MAP → SAT-NAV/GPS) REGISTER into a slot
instead of being hard-coded anywhere. FlowCode's property domains and
typed-I/O filters query this index; nothing implicit.

This is the DESIGN-TIME face of the Double Null mechanism (Companion
Q4): an implicit-NULL word loads {qualifier construct · pattern ·
handler} into a context stack at runtime; a registry entry records the
same triple for the designer. One day the compiler emits the former
from the latter.

Seeded strictly from v0.3 code truth (5500fp_ternoo_v03.py constants).
Where v0.3 names only PART of the quad (e.g. NEURAL's T21), the named
combinations are defined with the free trits at 0 and the rest of the
family space stays OPEN — the registry never claims more than canon.

Quad convention: (t21, t20, t19, t18), each in {-1, 0, +1} —
most-significant first, matching the audit's field reading.
"""

PRIMARIES = {
    "EXEC": -4, "MAP": -3, "DATA": -2, "NEURAL": -1, "I/O": 0,
    "CRYPTO": 1, "OPEN_A": 2, "OPEN_B": 3, "POOL": 4,
}
# DOCFLAG: v0.3 names the +2 slot OPEN_A; the Manus thread says OPCODE.
PRIMARY_NOTES = {
    "CRYPTO": "reserved primary",
    "OPEN_A": "naming under audit review (Manus thread: OPCODE)",
    "OPEN_B": "reserved primary",
    "POOL": "reserved primary",
}

TRITS = (-1, 0, 1)

OPEN = "open"
DEFINED = "defined"
RESERVED = "reserved"


def _quads():
    for a in TRITS:
        for b in TRITS:
            for c in TRITS:
                for d in TRITS:
                    yield (a, b, c, d)


def _blank_grid():
    return {q: {"status": OPEN, "name": "", "format": "", "handler": ""}
            for q in _quads()}


def _seed():
    reg = {p: _blank_grid() for p in PRIMARIES}

    def define(primary, quad, name, fmt="", handler="", status=DEFINED):
        reg[primary][quad] = {"status": status, "name": name,
                              "format": fmt, "handler": handler}

    # ── DATA (v0.3: T21,T20 pick the family; T19[,T18] the subtype) ─────
    for t19, sub in ((-1, "FLOAT"), (0, "INT"), (1, "UINT")):
        define("DATA", (-1, -1, t19, 0), f"SCALAR_{sub}",
               "18-trit scalar payload", f"scalar/{sub.lower()}")
    for t19, sub in ((-1, "UNICODE"), (0, "ASCII"), (1, "TERNARY")):
        define("DATA", (1, -1, t19, 0), f"STRING_{sub}",
               "length-or-addr payload",
               "glyph-plane" if sub == "TERNARY" else f"text/{sub.lower()}")
    PTR = {(-1, -1): "PTR_FLAT", (-1, 0): "PTR_RELATIVE",
           (-1, 1): "PTR_STACK_REL", (0, -1): "PTR_FIELD",
           (0, 0): "PTR_NULL", (0, 1): "PTR_SYMBOL",
           (1, -1): "PTR_REMOTE", (1, 0): "PTR_WEAK",
           (1, 1): "PTR_USER_DEF"}
    for (t19, t18), name in PTR.items():
        define("DATA", (0, 0, t19, t18), name, "pointer payload",
               "pointer")
    # The NULL pointer doubles as the Double Null meta-signal carrier.
    define("DATA", (0, 0, 0, 0), "PTR_NULL / DOUBLE-NULL",
           "payload 0 = explicit null; ≠0 = implicit null "
           "(stack-id · construct · mapping-A · mapping-B)",
           "double-null", status=RESERVED)

    # ── EXEC (v0.3: T21 priv · T20 call · T19 ret) ──────────────────────
    PRIV = {-1: "KERNEL", 0: "USER", 1: "SANDBOX"}
    CALL = {-1: "STACK", 0: "REGISTER", 1: "MESSAGE"}
    RET = {-1: "EXEC", 0: "MAP", 1: "DATA"}
    for p, pn in PRIV.items():
        for c, cn in CALL.items():
            for r, rn in RET.items():
                define("EXEC", (p, c, r, 0),
                       f"EXEC {pn}·{cn}·ret-{rn}",
                       "segment-relative code address", "exec")

    # ── NEURAL (v0.3: T21 unit/connection/structure) ────────────────────
    for t21, name in ((-1, "NEURAL_UNIT"), (0, "NEURAL_CONNECTION"),
                      (1, "NEURAL_STRUCTURE")):
        define("NEURAL", (t21, 0, 0, 0), name,
               "weight·source·target packing" if t21 == 0 else "",
               "ghost-brain" if t21 == 0 else "neural")

    # ── I/O (v0.3: T21 direction · T20 buffering) ───────────────────────
    DIR = {-1: "IN", 0: "BIDI", 1: "OUT"}
    BUF = {-1: "UNBUFFERED", 0: "BUFFERED", 1: "INTERRUPT"}
    for d, dn in DIR.items():
        for b, bn in BUF.items():
            define("I/O", (d, b, 0, 0), f"IO_{dn}_{bn}",
                   "channel/address payload", "io")

    # ── MAP (v0.3 marks axis-plane trit positions; enumeration rides
    #        the audit — the family stays open rather than over-claimed).
    # CRYPTO / OPEN_A / OPEN_B / POOL: reserved primaries, all 81 open.
    return reg


_REG = _seed()


# ── the query API (property domains speak this) ─────────────────────────────
def primaries():
    return dict(PRIMARIES)


def slots(primary):
    """The full 81-slot grid for one primary (quad -> entry)."""
    return {q: dict(e) for q, e in _REG[primary].items()}


def lookup(primary, quad):
    return dict(_REG[primary][tuple(quad)])


def defined(primary=None):
    """[(primary, quad, entry)] for every non-open slot."""
    prims = [primary] if primary else list(PRIMARIES)
    out = []
    for p in prims:
        for q, e in _REG[p].items():
            if e["status"] != OPEN:
                out.append((p, q, dict(e)))
    return out


def register(primary, quad, name, fmt="", handler=""):
    """Fill an OPEN slot — the explicit, system-wide registration the
    captain specified. Refuses to trample a defined/reserved slot."""
    e = _REG[primary][tuple(quad)]
    if e["status"] != OPEN:
        raise ValueError(f"slot {primary}{tuple(quad)} is {e['status']}: "
                         f"{e['name']!r}")
    e.update(status=DEFINED, name=name, format=fmt, handler=handler)
    return dict(e)


def query(pattern):
    """Domain-query syntax for the property model: 'registry:DATA.*'
    → all defined DATA entries; 'registry:*' → everything defined;
    'registry:DATA.STRING_*' → name-prefixed."""
    body = pattern.split(":", 1)[1] if ":" in pattern else pattern
    prim, _, name_pat = body.partition(".")
    out = []
    for p, q, e in defined(None if prim in ("*", "") else prim):
        if name_pat in ("", "*") or \
                e["name"].startswith(name_pat.rstrip("*")):
            out.append((p, q, e))
    return out


def stats():
    per = {p: sum(1 for e in g.values() if e["status"] != OPEN)
           for p, g in _REG.items()}
    return {"primaries": len(_REG), "slots": 81 * len(_REG),
            "defined": sum(per.values()), "per_primary": per}


def _selftest():
    s = stats()
    assert s["primaries"] == 9 and s["slots"] == 729
    assert all(len(g) == 81 for g in _REG.values())
    assert lookup("DATA", (1, -1, 1, 0))["name"] == "STRING_TERNARY"
    assert lookup("DATA", (0, 0, 0, 0))["status"] == RESERVED
    assert len(query("registry:DATA.STRING_*")) == 3
    assert s["per_primary"]["EXEC"] == 27
    assert s["per_primary"]["I/O"] == 9
    assert s["per_primary"]["CRYPTO"] == 0          # honestly open
    r = register("MAP", (1, 1, 1, 1), "SATNAV_GPS_DEMO", "lat·lon·alt",
                 "satnav")
    assert r["status"] == DEFINED
    try:
        register("MAP", (1, 1, 1, 1), "TRAMPLE")
        raise AssertionError("re-registration must refuse")
    except ValueError:
        pass
    _REG["MAP"][(1, 1, 1, 1)] = {"status": OPEN, "name": "", "format": "",
                                 "handler": ""}
    return s


if __name__ == "__main__":
    print(_selftest())
