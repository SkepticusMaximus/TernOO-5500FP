import os, sys
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import groom as G, groom_render as R
ok=True
def chk(n,c,e=""):
    global ok; ok=ok and bool(c); print(f"{'PASS' if c else 'FAIL'}  {n}  {e}")
reg,pool=G.Registry(),{}
words=R.spec("QLabel",[("text","STR","Hello TernOO"),("enabled","BOOL",True),("margin","INT",7)],reg,pool)
chk("spec word count (class + 3 pairs)", len(words)==7, f"{len(words)}")
chk("one pooled string", len(pool)==1)
sp=R.render(words,reg,pool)
chk("class round-trips", sp["class"]=="QLabel")
chk("string value exact", sp["props"]["text"]=="Hello TernOO")
chk("bool value (+1)", sp["props"]["enabled"]==1)
chk("int value", sp["props"]["margin"]==7)
from PySide6.QtWidgets import QApplication, QLineEdit
app=QApplication([])
w=R.build_qt(sp)
chk("build_qt is QLabel", type(w).__name__=="QLabel")
chk("build_qt text round-trips", w.text()=="Hello TernOO")
chk("build_qt enabled", w.isEnabled() is True)
# round-trip a REAL dissected widget's live value
le=QLineEdit(); le.setText("dissect me")
sp2=R.render(R.spec("QLineEdit",[("text","STR",le.text()),("readOnly","BOOL",le.isReadOnly())],reg,pool),reg,pool)
chk("real-widget value round-trip", R.build_qt(sp2).text()=="dissect me")
# special chars (ternary glyphs, html-ish, unicode)
s="−0+ ✓ <b> & ternary"
chk("special-char string exact", R.render(R.spec("QLabel",[("text","STR",s)],reg,pool),reg,pool)["props"]["text"]==s)
print("\n=== GROOM-RENDER:", "PASS ✅ ===" if ok else "FAIL ❌ ===")
sys.exit(0 if ok else 1)
