#!/home/stevo/.venvs/p2pcp/bin/python3
"""Headless + OFF-SCREEN proof for terndo_qt.py. Tests on a COPY of the live data
(never touches ~/.config/ternoo/todo.json) and grabs PNGs without a live window."""
import os
import sys
import shutil
import tempfile
import importlib.util

LIVE = os.path.expanduser("~/.config/ternoo/todo.json")
LIVE_TL = os.path.expanduser("~/.config/ternoo/timeline.json")
tmp = tempfile.mkdtemp()
store = os.path.join(tmp, "todo.json")
tline = os.path.join(tmp, "timeline.json")
shutil.copy(LIVE, store)
if os.path.exists(LIVE_TL):
    shutil.copy(LIVE_TL, tline)
os.environ["TERNDO_STORE"] = store
os.environ["TERNDO_TLINE"] = tline
os.environ["QT_QPA_PLATFORM"] = "offscreen"          # no live desktop, ever

SHOT = "/tmp/claude-1000/-home-stevo-dev-SkepticusMaximus-TernOO-5500FP/" \
       "e5549637-5d5b-494c-a9d3-eb3eed6c7080/scratchpad/widgetkit/"

spec = importlib.util.spec_from_file_location(
    "terndo_qt", "/home/stevo/dev/SkepticusMaximus/TernOO-5500FP/FlowCode/terndo_qt.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

ok = True
def chk(n, c, extra=""):
    global ok; ok = ok and bool(c); print(f"{'PASS' if c else 'FAIL'}  {n}  {extra}")

app = M.QApplication([])
app.setStyleSheet(M.DARK)
st = M.Store()
n0 = len(st.db["items"])
chk("loaded live-copy data", n0 >= 1, f"{n0} records")
w = M.TernDO(st)
w.resize(560, 640)
chk("window builds", w.tree.topLevelItemCount() >= 1,
    f"{w.tree.topLevelItemCount()} top-level items")

st.add("HEADLESS-QT objective")
w.refresh()
chk("add", len(st.db["items"]) == n0 + 1)

first = st.db["items"][0]["id"]
tl0 = len(st.tl)
st.cycle(first)
chk("cycle -> progress", st.by_id(first)["status"] == "progress")
chk("status change timelined", len(st.tl) == tl0 + 1)

st.apply_props(first, "renamed via props", "complete", "qt notes here")
it = st.by_id(first)
chk("props: text+status+notes atomic",
    it["text"] == "renamed via props" and it["status"] == "complete"
    and it["notes"] == "qt notes here")
st.undo_last()
chk("undo reverts props", st.by_id(first)["text"] != "renamed via props")

tgt = st.db["items"][-1]["id"]
before = len(st.db["items"])
st.delete(tgt)
chk("delete", len(st.db["items"]) == before - 1)
st.undo_last()
chk("undo restores deleted", len(st.db["items"]) == before
    and any(x["id"] == tgt for x in st.db["items"]))

# dialogs build (no exec — would block)
pd = M.PropsDialog(st, first, w)
chk("Properties dialog builds",
    pd.text.text() != "" and pd.notes is not None and pd.status.count() == 3)
dd = M.DeleteDialog(st, first, w)
chk("gated delete: button disabled until checked", dd.delbtn.isEnabled() is False)
dd.ok.setChecked(True)
chk("gated delete: enables on check", dd.delbtn.isEnabled() is True)
td = M.TimelineDialog(st, w)
chk("Timeline dialog builds", td is not None)

# OFF-SCREEN grabs (render to pixmap, no window shown)
w.show(); app.processEvents()
main_png = SHOT + "qt_terndo_main.png"
w.grab().save(main_png)
pd.show(); app.processEvents()
props_png = SHOT + "qt_terndo_props.png"
pd.grab().save(props_png)
chk("grabbed main PNG", os.path.getsize(main_png) > 2000, main_png)
chk("grabbed props PNG", os.path.getsize(props_png) > 2000, props_png)

# confirm the LIVE file is untouched
import json
live_n = len(json.load(open(LIVE))["items"])
chk("LIVE todo.json untouched", live_n == n0, f"live has {live_n}")

print("\n=== TERNDO-QT:", "PASS ✅ ===" if ok else "FAIL ❌ ===")
sys.exit(0 if ok else 1)
