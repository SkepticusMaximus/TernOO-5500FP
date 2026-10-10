"""GrOOM — Gristmill Object Oriented Model (core).

Grinds a reference-kit (PySide6) widget's retained object model into TernOO
24-trit balanced-ternary words — the native substrate for TernUI.

A GrOOM object/class is expressed in words (2 trit PRIMARY · 4 trit QUALIFIER(role)
· 18 trit PAYLOAD):
    identity  = CRYPTO · IDENTITY · serial      (the TernID handle — the spine)
    class     = I/O    · CLASS    · class-id
    parent    = MAP    · PARENT   · super-class-id   (the inheritance edge)
    property  = DATA   · PROP     · prop-id
    value     = DATA   · VALUE    · value
    of-class  = MAP    · CONTENT  · class-id

The word layer is pure Python (no Qt). Only `dissect()` touches a live widget's
metaObject — and that can run off-screen. This is the first real turn of the mill:
reference object model -> words -> (later) TernUI.
"""

# ── the 9 primaries (T23,T22) ─────────────────────────────────────────────────
PRIMARY = {"EXEC": (-1, -1), "MAP": (-1, 0), "DATA": (-1, 1),
           "NEURAL": (0, -1), "IO": (0, 0), "CRYPTO": (0, 1),
           "OPCODE": (1, -1), "OPEN_B": (1, 0), "POOL": (1, 1)}
PRIMARY_INV = {v: k for k, v in PRIMARY.items()}

# GrOOM word roles, carried in the 4-trit qualifier (81 slots; we use a handful)
ROLE = {"CLASS": 0, "PARENT": 1, "PROP": 2, "VALUE": 3,
        "IDENTITY": 4, "CHILD": 5, "CONTENT": 6}
ROLE_INV = {v: k for k, v in ROLE.items()}

GLY = {-1: "−", 0: "0", 1: "+"}


# ── balanced-ternary word pack/unpack (24 trits = 2 + 4 + 18) ─────────────────
def int_to_bt(n, width):
    """int -> `width` balanced trits, MSB first."""
    ts = [0] * width
    for i in range(width):
        r = n % 3
        n //= 3
        if r == 2:
            r = -1
            n += 1
        ts[i] = r
    return ts[::-1]


def bt_to_int(trits):
    """balanced trits (MSB first) -> int."""
    n = 0
    for t in trits:
        n = n * 3 + t
    return n


def pack(primary, role, payload):
    """Compose a 24-trit GrOOM word (returned as its signed-int value)."""
    return bt_to_int(list(PRIMARY[primary]) + int_to_bt(role, 4) + int_to_bt(payload, 18))


def unpack(word):
    ts = int_to_bt(word, 24)
    return (PRIMARY_INV[(ts[0], ts[1])], ROLE_INV.get(bt_to_int(ts[2:6]), bt_to_int(ts[2:6])),
            bt_to_int(ts[6:24]))


def glyphs(word):
    return "".join(GLY[t] for t in int_to_bt(word, 24))


# ── stable id registry ─────────────────────────────────────────────────────────
class Registry:
    def __init__(self):
        self.classes, self.props = {}, {}
        self.classes_inv, self.props_inv = {}, {}
        self._c, self._p = 0, 0

    def class_id(self, name):
        if name not in self.classes:
            self._c += 1
            self.classes[name] = self._c
            self.classes_inv[self._c] = name
        return self.classes[name]

    def prop_id(self, name):
        if name not in self.props:
            self._p += 1
            self.props[name] = self._p
            self.props_inv[self._p] = name
        return self.props[name]

    def class_name(self, cid):
        return self.classes_inv.get(cid)

    def prop_name(self, pid):
        return self.props_inv.get(pid)


# ── the mill: grind a widget's object model into GrOOM words ───────────────────
def ancestry(widget):
    chain, m = [], widget.metaObject()
    while m:
        chain.append(m.className())
        m = m.superClass()
    return chain


def prop_names(widget):
    mo = widget.metaObject()
    return [mo.property(i).name() for i in range(mo.propertyCount())]


def dissect(widget, reg):
    """Reference widget -> GrOOM class model. Returns {class, ancestry, props, words}."""
    chain = ancestry(widget)
    words = []
    for i, cname in enumerate(chain):
        words.append(("CLASS %s" % cname, pack("IO", ROLE["CLASS"], reg.class_id(cname))))
        if i + 1 < len(chain):
            parent = chain[i + 1]
            words.append(("PARENT %s->%s" % (cname, parent),
                          pack("MAP", ROLE["PARENT"], reg.class_id(parent))))
    props = prop_names(widget)
    for pn in props:
        words.append(("PROP %s" % pn, pack("DATA", ROLE["PROP"], reg.prop_id(pn))))
    return {"class": chain[0], "ancestry": chain, "props": props, "words": words}


def groom_object(widget, reg, identity_serial):
    """A GrOOM *instance*: a TernID identity bound to a dissected class."""
    model = dissect(widget, reg)
    words = [("IDENTITY #%d" % identity_serial,
              pack("CRYPTO", ROLE["IDENTITY"], identity_serial)),
             ("OF-CLASS %s" % model["class"],
              pack("MAP", ROLE["CONTENT"], reg.class_id(model["class"])))]
    return {"class": model["class"], "identity": identity_serial,
            "instance_words": words, "model": model}


def to_words(groom_obj):
    """Flatten a GrOOM object to the list of raw 24-trit word values."""
    out = [w for _, w in groom_obj["instance_words"]]
    out += [w for _, w in groom_obj["model"]["words"]]
    return out


# ── demo (off-screen) ──────────────────────────────────────────────────────────
def _demo():
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication, QTextEdit, QTreeWidget
    _ = QApplication([])
    reg = Registry()
    for w in (QTextEdit(), QTreeWidget()):
        g = groom_object(w, reg, reg.class_id(w.metaObject().className()))
        print("\n=== GrOOM object: %s  (identity #%d) ===" % (g["class"], g["identity"]))
        for label, word in g["instance_words"]:
            print("  %-26s %s  (%s)" % (label, glyphs(word), ",".join(map(str, unpack(word)))))
        print("  ancestry: " + " -> ".join(g["model"]["ancestry"]))
        print("  %d property-words; first 3:" % len(g["model"]["props"]))
        for label, word in g["model"]["words"][len(g["model"]["ancestry"]) * 2 - 1:][:3]:
            print("    %-22s %s" % (label, glyphs(word)))
        print("  total words to represent this object: %d" % len(to_words(g)))


if __name__ == "__main__":
    _demo()
