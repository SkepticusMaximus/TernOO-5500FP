#!/home/stevo/.venvs/p2pcp/bin/python3
"""TernOO · TernDO — PySide6 edition.

The first TernPIM tool re-forged on the reference-scaffold kit (the GrOOM
pipeline — Gristmill Object Oriented Model). Reads the SAME data as the DPG
TernDO: ~/.config/ternoo/todo.json (+ timeline.json). Everything the DPG face
couldn't give, native and free from QTextEdit / QTreeWidget:
  • word-wrap + undo/redo + clipboard + context menus in the notes editor
  • a real tree for objectives → sub-goals (expand/collapse, indentation)
  • a clean Properties dialog (no double scrollbars)
Three-state status (✓ pending / O in progress / X complete), timestamped history
+ append-only timeline, gated+confirmed delete, app-wide undo.

Env TERNDO_STORE / TERNDO_TLINE override the data paths (used by the tests so a
run never touches the live file).
"""
import os
import sys
import json
import copy
import datetime
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QTreeWidget, QTreeWidgetItem, QLabel, QDialog, QTextEdit,
    QComboBox, QDialogButtonBox, QCheckBox, QMenu, QListWidget, QListWidgetItem,
    QHeaderView, QFrame)
from PySide6.QtGui import QAction, QColor, QFont, QKeySequence, QShortcut, QBrush
from PySide6.QtCore import Qt

STORE = os.environ.get("TERNDO_STORE", os.path.expanduser("~/.config/ternoo/todo.json"))
TLINE = os.environ.get("TERNDO_TLINE", os.path.expanduser("~/.config/ternoo/timeline.json"))

STATUSES = ["pending", "progress", "complete"]
GLYPH = {"pending": "✓", "progress": "O", "complete": "X"}
SLABEL = {"pending": "Pending", "progress": "In progress", "complete": "Complete"}
SCOLOR = {"pending": QColor(110, 168, 254), "progress": QColor(232, 200, 144),
          "complete": QColor(240, 130, 130)}
NEXT = {"pending": "progress", "progress": "complete", "complete": "pending"}
GRN, DIM = QColor(63, 208, 143), QColor(150, 150, 165)
UID = Qt.ItemDataRole.UserRole


def now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── data layer (GUI-agnostic) ─────────────────────────────────────────────────
class Store:
    def __init__(self):
        self.db = self._load_db()
        self.tl = self._load_tl()
        self.undo = []

    def _load_db(self):
        try:
            raw = json.load(open(STORE, encoding="utf-8"))
        except Exception:
            raw = None
        if not (isinstance(raw, dict) and raw.get("version") == 2):
            raw = {"version": 2, "seq": 0, "items": []}
        raw.setdefault("seq", len(raw.get("items", [])))
        for it in raw["items"]:
            it.setdefault("parent", None)
            it.setdefault("status", "pending")
            it.setdefault("history", [])
            it.setdefault("notes", "")
        return raw

    def _load_tl(self):
        try:
            return json.load(open(TLINE, encoding="utf-8"))
        except Exception:
            return []

    def save(self):
        json.dump(self.db, open(STORE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        json.dump(self.tl, open(TLINE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)

    def snapshot(self):
        self.undo.append((copy.deepcopy(self.db), copy.deepcopy(self.tl)))
        if len(self.undo) > 100:
            self.undo.pop(0)

    def undo_last(self):
        if self.undo:
            self.db, self.tl = self.undo.pop()
            self.save()
            return True
        return False

    def by_id(self, iid):
        for it in self.db["items"]:
            if it["id"] == iid:
                return it
        return None

    def ordered(self):
        out, seen = [], set()
        for m in self.db["items"]:
            if m.get("parent"):
                continue
            out.append((m, 0)); seen.add(m["id"])
            for c in self.db["items"]:
                if c.get("parent") == m["id"]:
                    out.append((c, 1)); seen.add(c["id"])
        for it in self.db["items"]:
            if it["id"] not in seen:
                out.append((it, 0))
        return out

    def counts(self):
        c = {"pending": 0, "progress": 0, "complete": 0}
        for it in self.db["items"]:
            c[it.get("status", "pending")] = c.get(it.get("status", "pending"), 0) + 1
        return c

    def new_item(self, text, parent=None):
        self.db["seq"] += 1
        iid = "g%d" % self.db["seq"]
        ts = now()
        self.db["items"].append({"id": iid, "text": text, "status": "pending",
                                 "parent": parent, "notes": "",
                                 "history": [{"ts": ts, "status": "pending", "note": "created"}]})
        self.tl.append({"ts": ts, "id": iid, "text": text, "to": "pending", "note": "created"})
        return iid

    def add(self, text, parent=None):
        if not text.strip():
            return None
        self.snapshot()
        iid = self.new_item(text.strip(), parent)
        self.save()
        return iid

    def set_status(self, iid, new):
        it = self.by_id(iid)
        if not it or it["status"] == new:
            return False
        self.snapshot()
        ts = now()
        it["status"] = new
        it.setdefault("history", []).append({"ts": ts, "status": new})
        self.tl.append({"ts": ts, "id": iid, "text": it["text"], "to": new})
        self.save()
        return True

    def cycle(self, iid):
        it = self.by_id(iid)
        if it:
            self.set_status(iid, NEXT[it["status"]])

    def apply_props(self, iid, text, status, notes):
        it = self.by_id(iid)
        if not it:
            return False
        tc = text.strip() and text.strip() != it["text"]
        nc = notes != it.get("notes", "")
        sc = status != it["status"]
        if not (tc or nc or sc):
            return False
        self.snapshot()
        if tc:
            it["text"] = text.strip()
        if nc:
            it["notes"] = notes
        if sc:
            ts = now()
            it["status"] = status
            it.setdefault("history", []).append({"ts": ts, "status": status})
            self.tl.append({"ts": ts, "id": iid, "text": it["text"], "to": status})
        self.save()
        return True

    def delete(self, iid):
        it = self.by_id(iid)
        if not it:
            return False
        self.snapshot()
        ids = {iid} | {x["id"] for x in self.db["items"] if x.get("parent") == iid}
        ts = now()
        for d in ids:
            d_it = self.by_id(d)
            if d_it:
                self.tl.append({"ts": ts, "id": d, "text": d_it["text"],
                                "to": "deleted", "note": "deleted"})
        self.db["items"][:] = [x for x in self.db["items"] if x["id"] not in ids]
        self.save()
        return True


# ── dialogs ───────────────────────────────────────────────────────────────────
class PropsDialog(QDialog):
    def __init__(self, store, iid, parent=None):
        super().__init__(parent)
        self.store, self.iid = store, iid
        it = store.by_id(iid)
        self.setWindowTitle("Properties")
        self.resize(500, 460)
        v = QVBoxLayout(self)
        v.addWidget(_hdr("Text"))
        self.text = QLineEdit(it["text"])
        v.addWidget(self.text)
        v.addWidget(_hdr("Status"))
        self.status = QComboBox()
        for s in STATUSES:
            self.status.addItem(SLABEL[s], s)
        self.status.setCurrentIndex(STATUSES.index(it.get("status", "pending")))
        v.addWidget(self.status)
        v.addWidget(_hdr("Notes  (Markdown — shared format with skills/Obsidian)"))
        self.notes = QTextEdit()
        self.notes.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.notes.setFont(QFont("DejaVu Sans Mono", 10))
        self.notes.setPlainText(it.get("notes", ""))
        v.addWidget(self.notes, 1)
        h = it.get("history", [])
        meta = "id %s  ·  created %s  ·  %d change(s)" % (
            it["id"], h[0]["ts"] if h else "—", len(h))
        if it.get("parent"):
            meta += "  ·  sub-goal of %s" % it["parent"]
        lab = QLabel(meta)
        lab.setStyleSheet("color:#9696a5;")
        v.addWidget(lab)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                              | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def commit(self):
        return self.store.apply_props(
            self.iid, self.text.text(), self.status.currentData(),
            self.notes.toPlainText())


class DeleteDialog(QDialog):
    def __init__(self, store, iid, parent=None):
        super().__init__(parent)
        self.store, self.iid = store, iid
        it = store.by_id(iid)
        kids = [x for x in store.db["items"] if x.get("parent") == iid]
        self.setWindowTitle("Delete record")
        self.resize(440, 220)
        v = QVBoxLayout(self)
        t = QLabel("Permanently delete this record?")
        t.setStyleSheet("color:#f08282;font-size:15px;")
        v.addWidget(t)
        w = QLabel(it["text"])
        w.setWordWrap(True)
        v.addWidget(w)
        if kids:
            k = QLabel("This also deletes %d sub-goal(s)." % len(kids))
            k.setStyleSheet("color:#e8c890;")
            v.addWidget(k)
        note = QLabel("Records are normally kept for history. This removes it for good.")
        note.setStyleSheet("color:#9696a5;")
        note.setWordWrap(True)
        v.addWidget(note)
        self.ok = QCheckBox("I understand — remove it permanently")
        v.addWidget(self.ok)
        self.bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.delbtn = self.bb.addButton("Delete permanently",
                                        QDialogButtonBox.ButtonRole.DestructiveRole)
        self.delbtn.setEnabled(False)
        self.ok.toggled.connect(self.delbtn.setEnabled)
        self.delbtn.clicked.connect(self.accept)
        self.bb.rejected.connect(self.reject)
        v.addWidget(self.bb)


class TimelineDialog(QDialog):
    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Timeline")
        self.resize(560, 520)
        v = QVBoxLayout(self)
        v.addWidget(_hdr("every status change, oldest first"))
        lst = QListWidget()
        for e in sorted(store.tl, key=lambda e: e.get("ts", "")):
            to = e.get("to", "")
            tgt = SLABEL.get(to, "Deleted" if to == "deleted" else to)
            it = QListWidgetItem("%s  %s  →  %s" % (GLYPH.get(to, "·"),
                                                    e.get("ts", ""), tgt))
            it.setForeground(QBrush(SCOLOR.get(to, QColor(200, 120, 120))))
            it.setToolTip(e.get("text", ""))
            lst.addItem(it)
        v.addWidget(lst, 1)


def _hdr(text):
    lab = QLabel(text)
    lab.setStyleSheet("color:#6ea8fe;")
    return lab


# ── main window ────────────────────────────────────────────────────────────────
class TernDO(QMainWindow):
    def __init__(self, store):
        super().__init__()
        self.store = store
        self.setWindowTitle("TernOO · TernDO (PySide6)")
        self.resize(560, 640)
        self._menus()
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(10, 8, 10, 8)
        hdr = QLabel("TernOO · TernDO")
        hdr.setStyleSheet("color:#3fd08f;font-size:17px;")
        v.addWidget(hdr)
        sub = QLabel("TernPIM · objectives · sub-goals · notes · timeline  (GrOOM reference)")
        sub.setStyleSheet("color:#9696a5;")
        v.addWidget(sub)
        row = QHBoxLayout()
        self.inp = QLineEdit()
        self.inp.setPlaceholderText("new objective…")
        self.inp.returnPressed.connect(self.add_from_input)
        row.addWidget(self.inp, 1)
        addb = QPushButton(" Add ")
        addb.clicked.connect(self.add_from_input)
        row.addWidget(addb)
        v.addLayout(row)
        leg = QLabel("status: ✓ pending   O in progress   X complete  "
                     "· double-click = Properties · right-click = options")
        leg.setStyleSheet("color:#9696a5;")
        v.addWidget(leg)
        self.tree = QTreeWidget()
        self.tree.setColumnCount(2)
        self.tree.setHeaderLabels(["Objective", "St"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tree.setColumnWidth(1, 40)
        self.tree.setRootIsDecorated(True)
        self.tree.itemClicked.connect(self._clicked)
        self.tree.itemDoubleClicked.connect(lambda i, c: self.open_props(i.data(0, UID)))
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._ctx)
        v.addWidget(self.tree, 1)
        foot = QHBoxLayout()
        self.count = QLabel("")
        self.count.setStyleSheet("color:#9696a5;")
        foot.addWidget(self.count, 1)
        tlb = QPushButton("Timeline")
        tlb.clicked.connect(self.show_timeline)
        foot.addWidget(tlb)
        v.addLayout(foot)
        QShortcut(QKeySequence.StandardKey.Undo, self, activated=self.undo)
        self.refresh()

    def _menus(self):
        mb = self.menuBar()
        fm = mb.addMenu("File")
        fm.addAction(QAction("New objective", self, shortcut="Ctrl+N",
                             triggered=lambda: self.inp.setFocus()))
        fm.addSeparator()
        fm.addAction(QAction("Quit", self, shortcut="Ctrl+Q", triggered=self.close))
        em = mb.addMenu("Edit")
        em.addAction(QAction("Undo", self, shortcut="Ctrl+Z", triggered=self.undo))
        em.addSeparator()
        em.addAction(QAction("Properties…", self, shortcut="F2", triggered=self._props_sel))
        em.addAction(QAction("Copy selected", self, shortcut="Ctrl+C", triggered=self._copy_sel))
        em.addAction(QAction("Paste as objective", self, shortcut="Ctrl+V", triggered=self._paste))
        em.addAction(QAction("Delete selected…", self, shortcut="Del", triggered=self._del_sel))
        vm = mb.addMenu("View")
        vm.addAction(QAction("Timeline…", self, triggered=self.show_timeline))
        hm = mb.addMenu("Help")
        hm.addAction(QAction("About", self, triggered=self._about))

    # -- rendering --
    def refresh(self):
        self.tree.clear()
        nodes = {}
        for it, depth in self.store.ordered():
            label = ("└ " if depth else "") + it["text"]
            if depth and it["parent"] in nodes:
                node = QTreeWidgetItem(nodes[it["parent"]])
            else:
                node = QTreeWidgetItem(self.tree)
            node.setText(0, it["text"])
            node.setData(0, UID, it["id"])
            st = it["status"]
            node.setText(1, GLYPH[st])
            node.setForeground(1, QBrush(SCOLOR[st]))
            node.setTextAlignment(1, Qt.AlignmentFlag.AlignCenter)
            if it.get("notes"):
                node.setToolTip(0, it["notes"][:200])
            nodes[it["id"]] = node
        self.tree.expandAll()
        c = self.store.counts()
        self.count.setText("%d records · %d pending · %d in progress · %d complete"
                           % (len(self.store.db["items"]), c["pending"], c["progress"], c["complete"]))

    # -- actions --
    def add_from_input(self):
        if self.store.add(self.inp.text()):
            self.inp.clear()
            self.refresh()

    def _sel_id(self):
        it = self.tree.currentItem()
        return it.data(0, UID) if it else None

    def _clicked(self, item, col):
        if col == 1:
            self.store.cycle(item.data(0, UID))
            self.refresh()

    def open_props(self, iid):
        if not iid:
            return
        d = PropsDialog(self.store, iid, self)
        if d.exec() == QDialog.DialogCode.Accepted:
            d.commit()
            self.refresh()

    def _props_sel(self):
        if self._sel_id():
            self.open_props(self._sel_id())

    def add_sub(self, parent_id):
        from PySide6.QtWidgets import QInputDialog
        txt, ok = QInputDialog.getText(self, "Add sub-goal", "Sub-goal:")
        if ok and txt.strip():
            self.store.add(txt, parent=parent_id)
            self.refresh()

    def _copy_sel(self):
        iid = self._sel_id()
        it = self.store.by_id(iid) if iid else None
        if it:
            QApplication.clipboard().setText(it["text"])

    def _paste(self):
        txt = QApplication.clipboard().text()
        if txt.strip():
            self.store.add(txt)
            self.refresh()

    def confirm_delete(self, iid):
        d = DeleteDialog(self.store, iid, self)
        if d.exec() == QDialog.DialogCode.Accepted:
            self.store.delete(iid)
            self.refresh()

    def _del_sel(self):
        if self._sel_id():
            self.confirm_delete(self._sel_id())

    def show_history(self, iid):
        it = self.store.by_id(iid)
        if not it:
            return
        from PySide6.QtWidgets import QMessageBox
        lines = ["%s  %s  %s" % (GLYPH.get(h["status"], "?"), h.get("ts", "—"),
                                 SLABEL.get(h["status"], h["status"])
                                 + ((" (%s)" % h["note"]) if h.get("note") else ""))
                 for h in it.get("history", [])]
        QMessageBox.information(self, "History — " + it["text"][:40],
                               "\n".join(lines) or "(no recorded changes)")

    def show_timeline(self):
        TimelineDialog(self.store, self).exec()

    def undo(self):
        if self.store.undo_last():
            self.refresh()

    def _about(self):
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(self, "TernDO (PySide6)",
                               "TernPIM objective tracker — PySide6 edition.\n"
                               "The GrOOM reference scaffold: native wrap/undo/clipboard,\n"
                               "shared todo.json with the DPG TernDO.")

    def _ctx(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        iid = item.data(0, UID)
        m = QMenu(self)
        sm = m.addMenu("Set status")
        for s in STATUSES:
            sm.addAction(QAction("%s  %s" % (GLYPH[s], SLABEL[s]), self,
                                 triggered=lambda _=False, x=s: (self.store.set_status(iid, x),
                                                                 self.refresh())))
        m.addAction(QAction("Properties…", self, triggered=lambda: self.open_props(iid)))
        m.addAction(QAction("Add sub-goal…", self, triggered=lambda: self.add_sub(iid)))
        m.addAction(QAction("Copy text", self,
                            triggered=lambda: QApplication.clipboard().setText(
                                self.store.by_id(iid)["text"])))
        m.addAction(QAction("History…", self, triggered=lambda: self.show_history(iid)))
        m.addSeparator()
        m.addAction(QAction("Delete record…", self, triggered=lambda: self.confirm_delete(iid)))
        m.addSeparator()
        m.addAction(QAction("Undo  (Ctrl+Z)", self, triggered=self.undo))
        m.exec(self.tree.viewport().mapToGlobal(pos))


DARK = ("QWidget{background:#1a1f2b;color:#e6e6ec;}"
        "QLineEdit,QTextEdit,QComboBox,QListWidget,QTreeWidget{background:#15151f;"
        "border:1px solid #3a3a52;}"
        "QTreeWidget::item:selected{background:#2e466e;}"
        "QPushButton{background:#2e466e;border:1px solid #5a82be;border-radius:4px;padding:3px 10px;}"
        "QMenuBar,QMenu{background:#1e2431;} QMenu::item:selected{background:#2e466e;}")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK)
    w = TernDO(Store())
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
