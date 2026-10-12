#!/home/stevo/.venvs/p2pcp/bin/python3
"""Tests for GrOOM core — word round-trips + the dissector (off-screen Qt)."""
import os
import sys
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import groom as G

ok = True
def chk(n, c, extra=""):
    global ok; ok = ok and bool(c); print(f"{'PASS' if c else 'FAIL'}  {n}  {extra}")

# balanced-ternary round-trip, incl. the 24-trit extremes
lim = (3 ** 24 - 1) // 2
chk("bt round-trip (incl ±max 24-trit)",
    all(G.bt_to_int(G.int_to_bt(n, 24)) == n for n in [0, 1, -1, 12345, -12345, lim, -lim]))

# pack/unpack across all primaries × roles × payload extremes
pl_lim = (3 ** 18 - 1) // 2
good = True
for primary in G.PRIMARY:
    for role in G.ROLE.values():
        for payload in [0, 1, -1, 42, -42, 1000, -1000, pl_lim, -pl_lim]:
            p, r, pl = G.unpack(G.pack(primary, role, payload))
            if not (p == primary and r == G.ROLE_INV[role] and pl == payload):
                good = False
chk("pack/unpack round-trip (9 primaries × 7 roles × 9 payloads)", good)

# field placement
chk("CLASS word = IO·CLASS·id", G.unpack(G.pack("IO", G.ROLE["CLASS"], 7)) == ("IO", "CLASS", 7))
chk("IDENTITY word = CRYPTO·IDENTITY·id",
    G.unpack(G.pack("CRYPTO", G.ROLE["IDENTITY"], 99)) == ("CRYPTO", "IDENTITY", 99))
chk("PARENT word = MAP·PARENT·id", G.unpack(G.pack("MAP", G.ROLE["PARENT"], 3)) == ("MAP", "PARENT", 3))

# the mill
from PySide6.QtWidgets import QApplication, QTextEdit, QTreeWidget
app = QApplication([])
reg = G.Registry()
m = G.dissect(QTextEdit(), reg)
chk("dissect class", m["class"] == "QTextEdit")
chk("ancestry ends at QObject", m["ancestry"][-1] == "QObject", " -> ".join(m["ancestry"]))
chk("props > 80", len(m["props"]) > 80, f"{len(m['props'])}")

parent_w = [w for (lbl, w) in m["words"] if lbl.startswith("PARENT")]
class_w = [w for (lbl, w) in m["words"] if lbl.startswith("CLASS")]
prop_w = [w for (lbl, w) in m["words"] if lbl.startswith("PROP")]
chk("parent edges == ancestry-1", len(parent_w) == len(m["ancestry"]) - 1)
chk("parent words all MAP·PARENT",
    all(G.unpack(w)[:2] == ("MAP", "PARENT") for w in parent_w))
chk("class words all IO·CLASS",
    all(G.unpack(w)[:2] == ("IO", "CLASS") for w in class_w))
chk("prop words all DATA·PROP and count matches",
    len(prop_w) == len(m["props"]) and all(G.unpack(w)[:2] == ("DATA", "PROP") for w in prop_w))

g = G.groom_object(QTreeWidget(), reg, 123)
chk("instance identity = CRYPTO·IDENTITY·123",
    G.unpack(g["instance_words"][0][1]) == ("CRYPTO", "IDENTITY", 123))
chk("to_words flattens object", len(G.to_words(g)) > 100, f"{len(G.to_words(g))} words")

print("\n=== GROOM:", "PASS ✅ ===" if ok else "FAIL ❌ ===")
sys.exit(0 if ok else 1)
