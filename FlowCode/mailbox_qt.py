#!/home/stevo/.venvs/p2pcp/bin/python3
"""TernOO · POBOX Mail — PySide6 reference face (list item g1).

Built against CCC's crypto-free AgentClient facade (handoff 2026-10-10-1107). The
UI only ever handles display names + opaque handles — never a key, hash, grant id,
signature or ciphertext (CCC's golden rule).

Backend NOW = an inert git-POBOX stub: reads private/POBOX/*.md as mail, keeps a
local contacts roster, and `send()` writes a DRAFT to a local outbox — it never
transmits, commits, pushes, or touches the watched POBOX outbox. The real TernID
agent swaps in behind this same facade later, with zero UI change.
"""
import os
import re
import sys
import glob
import json
import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QListWidget, QListWidgetItem, QTextEdit, QLabel, QComboBox,
                               QPushButton, QDialog, QLineEdit, QDialogButtonBox, QSplitter,
                               QMessageBox)
from PySide6.QtGui import QAction, QFont, QBrush, QColor
from PySide6.QtCore import Qt

REPO = "/home/stevo/dev/SkepticusMaximus/TernOO-5500FP"
POBOX = os.path.join(REPO, "private", "POBOX")
OUTBOX = os.path.expanduser("~/.config/ternoo/mail-outbox")   # DRAFTS only — never transmitted
ROSTER = os.path.expanduser("~/.config/ternoo/contacts.json")
os.makedirs(OUTBOX, exist_ok=True)
SEATS = ["Stevo", "CC", "CCC", "CF5", "CAI", "CO5", "Professor"]
UID = Qt.ItemDataRole.UserRole


# ── AgentClient facade (CCC handoff §B) — crypto-free; the real agent swaps in here ──
class AgentClient:
    def __init__(self):
        self._msgs = self._scan()
        self._contacts = self._load_contacts()

    # accounts
    def list_accounts(self):
        return list(SEATS)

    def account_display(self, handle):
        return handle

    # POBOX scan / parse
    def _scan(self):
        out = []
        for path in sorted(glob.glob(os.path.join(POBOX, "*.md"))):
            try:
                txt = open(path, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            out.append(self._parse(os.path.basename(path), txt))
        return out

    def _parse(self, fname, txt):
        lines = txt.splitlines()
        stamp = lines[0].strip() if lines else fname[:15]

        def hdr(key):
            for ln in lines[:12]:
                mm = re.match(r"^%s:\s*(.+)" % key, ln)
                if mm:
                    return mm.group(1).strip()
            return ""

        frm = re.sub(r"\s*\(.*\)", "", hdr("From")) or self._fn(fname, r"\d{4}-\d{2}-\d{2}(?:-\d{4})?-(.+?)-to-")
        to = hdr("To") or self._fn(fname, r"-to-(.+?)-")
        subj = hdr("Re") or fname.rsplit(".", 1)[0]
        body = txt
        idx = next((i for i, l in enumerate(lines) if l.startswith("Re:")), None)
        if idx is not None:
            body = "\n".join(lines[idx + 1:]).strip()
        return {"id": fname, "from": frm or "?", "to": to or "?", "subject": subj,
                "time": stamp, "body": body, "unread": False}

    def _fn(self, f, pat):
        m = re.search(pat, f)
        return m.group(1) if m else ""

    @staticmethod
    def _match(to, account):
        toks = [t for t in re.split(r"[^A-Za-z0-9]+", to) if t]
        if any(t.lower().startswith("crew") for t in toks):
            return True
        return account in toks

    def inbox(self, account):
        return [m for m in self._msgs if self._match(m["to"], account)]

    def mark_read(self, account, mid):
        for m in self._msgs:
            if m["id"] == mid:
                m["unread"] = False

    # contacts (the roster)
    def _load_contacts(self):
        try:
            return json.load(open(ROSTER))
        except Exception:
            c = [{"handle": "contact:" + s.lower(), "display_name": s} for s in SEATS]
            json.dump(c, open(ROSTER, "w"), indent=1)
            return c

    def contacts(self, account):
        return self._contacts

    def add_contact(self, account, invite):
        name = (invite or "").strip() or "New contact"
        c = {"handle": "contact:" + re.sub(r"\W+", "", name).lower(), "display_name": name}
        self._contacts.append(c)
        json.dump(self._contacts, open(ROSTER, "w"), indent=1)
        return c["handle"]

    def create_invite(self, account, for_name=None):
        return "ternid-invite:%s:%s" % (account.lower(), "stub-token")   # opaque, NOT a key

    # mail — send is INERT (draft only)
    def send(self, from_account, to_contact, subject, body):
        ts = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        slug = (re.sub(r"\W+", "-", subject.lower())[:40].strip("-")) or "draft"
        fn = "%s-%s-to-%s-%s.md" % (ts, from_account, to_contact, slug)
        stamp = datetime.datetime.now().strftime("%H:%M %d/%m/%Y ACDT")
        open(os.path.join(OUTBOX, fn), "w", encoding="utf-8").write(
            "%s\n\nTo: %s\nFrom: %s\nRe: %s\n\n%s\n" % (stamp, to_contact, from_account, subject, body))
        return fn

    def grants_on(self, object_handle):
        return []


# ── compose dialog ──────────────────────────────────────────────────────────────
class Compose(QDialog):
    def __init__(self, agent, account, parent=None):
        super().__init__(parent)
        self.agent, self.account = agent, account
        self.setWindowTitle("Compose — as %s" % account)
        self.resize(560, 460)
        v = QVBoxLayout(self)
        r = QHBoxLayout()
        r.addWidget(QLabel("To:"))
        self.to = QComboBox()
        for c in agent.contacts(account):
            self.to.addItem(c["display_name"])
        r.addWidget(self.to, 1)
        v.addLayout(r)
        self.subj = QLineEdit()
        self.subj.setPlaceholderText("Subject")
        v.addWidget(self.subj)
        self.body = QTextEdit()
        self.body.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        v.addWidget(self.body, 1)
        note = QLabel("Draft only — saved to your outbox, not transmitted "
                      "(sending is the TernID agent's job, pending).")
        note.setStyleSheet("color:#e8c890;")
        note.setWordWrap(True)
        v.addWidget(note)
        bb = QDialogButtonBox()
        bb.addButton("Save draft", QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton(QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)


# ── main window ──────────────────────────────────────────────────────────────────
class MailApp(QMainWindow):
    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self.account = "Stevo"
        self.setWindowTitle("TernOO · POBOX Mail")
        self.resize(820, 560)
        self._menus()
        central = QWidget()
        self.setCentralWidget(central)
        v = QVBoxLayout(central)
        v.setContentsMargins(8, 6, 8, 8)
        top = QHBoxLayout()
        hdr = QLabel("TernOO · POBOX Mail")
        hdr.setStyleSheet("color:#3fd08f;font-size:16px;")
        top.addWidget(hdr)
        top.addStretch(1)
        top.addWidget(QLabel("Account:"))
        self.acct = QComboBox()
        self.acct.addItems(agent.list_accounts())
        self.acct.setCurrentText(self.account)
        self.acct.currentTextChanged.connect(self._switch)
        top.addWidget(self.acct)
        cb = QPushButton("Compose")
        cb.clicked.connect(self.compose)
        top.addWidget(cb)
        ct = QPushButton("Contacts")
        ct.clicked.connect(self.show_contacts)
        top.addWidget(ct)
        v.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.list = QListWidget()
        self.list.setMinimumWidth(300)
        self.list.currentItemChanged.connect(self._open)
        split.addWidget(self.list)
        self.read = QTextEdit()
        self.read.setReadOnly(True)
        split.addWidget(self.read)
        split.setSizes([320, 500])
        v.addWidget(split, 1)
        self.status = QLabel("")
        self.status.setStyleSheet("color:#9696a5;")
        v.addWidget(self.status)
        self._reload()

    def _menus(self):
        mb = self.menuBar()
        fm = mb.addMenu("File")
        fm.addAction(QAction("Compose", self, shortcut="Ctrl+N", triggered=self.compose))
        fm.addSeparator()
        fm.addAction(QAction("Quit", self, shortcut="Ctrl+Q", triggered=self.close))
        hm = mb.addMenu("Help")
        hm.addAction(QAction("About", self, triggered=self._about))

    def _switch(self, acct):
        self.account = acct
        self._reload()

    def _reload(self):
        self.list.clear()
        msgs = sorted(self.agent.inbox(self.account), key=lambda m: m["time"], reverse=True)
        for m in msgs:
            it = QListWidgetItem("%s\n%s   ·   %s" % (m["subject"][:60], m["from"], m["time"]))
            it.setData(UID, m)
            self.list.addItem(it)
        self.read.clear()
        self.status.setText("%s — %d messages   ·   outbox: %s"
                            % (self.account, len(msgs), OUTBOX))

    def _open(self, cur, _prev=None):
        if not cur:
            return
        m = cur.data(UID)
        self.agent.mark_read(self.account, m["id"])
        self.read.setHtml(
            "<div style='color:#3fd08f;font-size:14px'>%s</div>"
            "<div style='color:#9696a5'>from <b style='color:#e6e6ec'>%s</b> · to %s · %s</div><hr>"
            "<pre style='color:#e6e6ec;white-space:pre-wrap;font-family:DejaVu Sans Mono'>%s</pre>"
            % (_esc(m["subject"]), _esc(m["from"]), _esc(m["to"]), _esc(m["time"]), _esc(m["body"])))

    def compose(self):
        d = Compose(self.agent, self.account, self)
        if d.exec() == QDialog.DialogCode.Accepted:
            fn = self.agent.send(self.account, d.to.currentText(),
                                 d.subj.text() or "(no subject)", d.body.toPlainText())
            QMessageBox.information(self, "Draft saved",
                                    "Saved to outbox (NOT transmitted):\n%s\n\n%s"
                                    % (fn, OUTBOX))

    def show_contacts(self):
        names = ", ".join(c["display_name"] for c in self.agent.contacts(self.account))
        QMessageBox.information(self, "Contacts (the roster)",
                                names + "\n\n(Add-contact uses an opaque invite token — no keys.)")

    def _about(self):
        QMessageBox.information(self, "POBOX Mail",
                                "TernOO POBOX Mail — PySide6 reference face (g1).\n"
                                "Crypto-free AgentClient facade (CCC handoff 1107).\n"
                                "Inert git-POBOX backend; the real TernID agent swaps in behind it.")


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


DARK = ("QWidget{background:#1a1f2b;color:#e6e6ec;}"
        "QListWidget,QTextEdit,QLineEdit,QComboBox{background:#15151f;border:1px solid #3a3a52;}"
        "QListWidget::item:selected{background:#2e466e;}"
        "QPushButton{background:#2e466e;border:1px solid #5a82be;border-radius:4px;padding:3px 10px;}"
        "QMenuBar,QMenu{background:#1e2431;} QMenu::item:selected{background:#2e466e;}")


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK)
    w = MailApp(AgentClient())
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
