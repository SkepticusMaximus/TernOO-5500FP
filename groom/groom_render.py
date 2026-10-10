"""GrOOM value-words + renderer — closes the loop  reference → words → native.

  spec()      encodes a widget (class + property VALUES) into TernOO words + a
              string pool (strings are MAP content-addressed; the native char-map
              plane fills the pool later — CF5's charter).
  render()    reads a word list back to a {class, props} spec (pure).
  build_qt()  reconstructs a live PySide6 widget from a rendered spec.

Value kinds: BOOL → DATA·VALUE·(±1), INT/ENUM → DATA·VALUE·payload,
             STR → MAP·CONTENT·pool-id.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import groom as G


def encode_value(kind, value, pool):
    if kind == "BOOL":
        return G.pack("DATA", G.ROLE["VALUE"], 1 if value else -1)
    if kind in ("INT", "ENUM"):
        return G.pack("DATA", G.ROLE["VALUE"], int(value))
    if kind == "STR":
        pid = len(pool) + 1
        pool[pid] = str(value)
        return G.pack("MAP", G.ROLE["CONTENT"], pid)
    raise ValueError("unknown value kind: %s" % kind)


def spec(class_name, props, reg, pool):
    """props = [(name, kind, value)] → a flat word list (class, then prop/value pairs)."""
    words = [G.pack("IO", G.ROLE["CLASS"], reg.class_id(class_name))]
    for name, kind, value in props:
        words.append(G.pack("DATA", G.ROLE["PROP"], reg.prop_id(name)))
        words.append(encode_value(kind, value, pool))
    return words


def render(words, reg, pool):
    """Read a spec word list back to {class, props:{name:value}}. Pure, no Qt."""
    out = {"class": reg.class_name(G.unpack(words[0])[2]), "props": {}}
    i = 1
    while i + 1 < len(words) + 1 and i < len(words):
        name = reg.prop_name(G.unpack(words[i])[2])
        vprim, vrole, vpl = G.unpack(words[i + 1])
        out["props"][name] = pool.get(vpl) if (vprim == "MAP" and vrole == "CONTENT") else vpl
        i += 2
    return out


def build_qt(spec_dict):
    """Reconstruct a minimal live PySide6 widget from a rendered spec."""
    from PySide6.QtWidgets import QLabel, QPushButton, QLineEdit, QCheckBox, QWidget
    ctor = {"QLabel": QLabel, "QPushButton": QPushButton,
            "QLineEdit": QLineEdit, "QCheckBox": QCheckBox}.get(spec_dict["class"], QWidget)
    w = ctor()
    p = spec_dict["props"]
    if "text" in p and hasattr(w, "setText"):
        w.setText(str(p["text"]))
    if "enabled" in p:
        w.setEnabled(p["enabled"] in (1, True))
    if "checked" in p and hasattr(w, "setChecked"):
        w.setChecked(p["checked"] in (1, True))
    return w


def _demo():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    _ = QApplication([])
    reg, pool = G.Registry(), {}
    words = spec("QLabel", [("text", "STR", "Hello TernOO — words to widget"),
                            ("enabled", "BOOL", True),
                            ("margin", "INT", 7)], reg, pool)
    print("spec: %d words + %d pooled string(s)" % (len(words), len(pool)))
    for w in words:
        print("   %s  %s" % (G.glyphs(w), G.unpack(w)))
    sp = render(words, reg, pool)
    print("\nrendered spec: %s" % sp)
    widget = build_qt(sp)
    print("built live: %s  text=%r  enabled=%s"
          % (type(widget).__name__, widget.text(), widget.isEnabled()))
    print("\nLOOP CLOSED: widget → words → widget, text round-trips exactly =",
          widget.text() == "Hello TernOO — words to widget")


if __name__ == "__main__":
    _demo()
