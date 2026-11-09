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
                               QMessageBox, QTreeWidget, QTreeWidgetItem, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView, QInputDialog)
from PySide6.QtGui import QAction, QFont, QBrush, QColor, QIcon
from PySide6.QtCore import Qt, Signal

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root — portable across machines
POBOX = os.path.join(REPO, "private", "POBOX")
ICON = os.path.join(REPO, "tools", "pobox-mail.svg")
OUTBOX = os.path.expanduser("~/.config/ternoo/mail-outbox")   # DRAFTS only — never transmitted
ROSTER = os.path.expanduser("~/.config/ternoo/contacts.json")
MAILLISTS = os.path.expanduser("~/.config/ternoo/maillists.json")   # named distribution lists
os.makedirs(OUTBOX, exist_ok=True)
SEATS = ["Stevo", "CC", "CCC", "CF5", "CAI", "CO5", "Professor"]
UID = Qt.ItemDataRole.UserRole


# ── AgentClient facade (CCC handoff §B) — crypto-free; the real agent swaps in here ──
class StubBackend:
    """Inert git-POBOX backend — CCC's §B methods over the existing POBOX + a local roster.
    Returns the handoff-1129 wire shapes. The real TernID agent replaces this behind serve()."""
    def __init__(self):
        self._msgs = self._scan()
        self._contacts = self._load_contacts()

    # accounts
    def create_account(self, display_name):
        if display_name not in SEATS:
            SEATS.append(display_name)
        return {"account_handle": display_name}

    def list_accounts(self):
        return list(SEATS)

    def account_display(self, account_handle):
        return account_handle

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

    def mark_read(self, account, message_id):
        for m in self._msgs:
            if m["id"] == message_id:
                m["unread"] = False
        return {"ok": True}

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
        return {"contact_handle": c["handle"]}

    def create_invite(self, account, for_display_name=None):
        return {"invite": "ternid-invite:%s:stub-token" % account.lower()}   # opaque, NOT a key

    # mail — send is INERT (draft only)
    def send(self, from_account, to_contact, subject, body):
        ts = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        slug = (re.sub(r"\W+", "-", subject.lower())[:40].strip("-")) or "draft"
        fn = "%s-%s-to-%s-%s.md" % (ts, from_account, to_contact, slug)
        stamp = datetime.datetime.now().strftime("%H:%M %d/%m/%Y ACDT")
        open(os.path.join(OUTBOX, fn), "w", encoding="utf-8").write(
            "%s\n\nTo: %s\nFrom: %s\nRe: %s\n\n%s\n" % (stamp, to_contact, from_account, subject, body))
        return {"message_id": fn}

    def grants_on(self, object_handle):
        return []

    def grant(self, account, object_handle, holder_contact, rights, caveats=None):
        return {"grant_handle": "grant:stub"}

    def revoke(self, account, grant_handle):
        return {"ok": True}


# ── compose dialog ──────────────────────────────────────────────────────────────
class Compose(QDialog):
    def __init__(self, agent, account, parent=None, prefill=None):
        super().__init__(parent)
        self.agent, self.account = agent, account
        self._save_draft = False
        self.setWindowTitle("Compose — as %s" % account)
        self.resize(560, 460)
        v = QVBoxLayout(self)
        r = QHBoxLayout()
        r.addWidget(QLabel("To:"))
        self.contacts = agent.contacts(account=account)
        self.to = QComboBox()
        self.to.addItem("— choose a recipient —", None)       # safe default: no accidental broadcast
        self.to.addItem("📣 crew — everyone", "list:crew")               # distribution lists
        for lname in sorted(load_lists()):
            self.to.addItem("📣 %s" % lname, "list:" + lname)
        self.to.insertSeparator(self.to.count())
        for c in self.contacts:
            self.to.addItem(c["display_name"], c["handle"])   # show name, send opaque handle
        self.to.setCurrentIndex(0)                            # start on the placeholder, not a broadcast
        r.addWidget(self.to, 1)
        v.addLayout(r)
        self.subj = QLineEdit()
        self.subj.setPlaceholderText("Subject")
        v.addWidget(self.subj)
        self.body = QTextEdit()
        self.body.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        v.addWidget(self.body, 1)
        if prefill:                                           # Reply / re-open a draft pre-fills
            i = self.to.findData(prefill["to"]) if prefill.get("to") else -1
            if i < 0 and prefill.get("to_text"):              # drafts carry the recipient as display text
                i = self.to.findText(prefill["to_text"])
            if i >= 0:
                self.to.setCurrentIndex(i)
            if prefill.get("subject"):
                self.subj.setText(prefill["subject"])
            if prefill.get("body"):
                self.body.setPlainText(prefill["body"])
        note = QLabel("Send goes live through the TernID agent — real, sealed, delivered. "
                      "Save draft keeps it local, untransmitted.")
        note.setStyleSheet("color:#e8c890;")
        note.setWordWrap(True)
        v.addWidget(note)
        bb = QDialogButtonBox()
        bb.addButton("Send", QDialogButtonBox.ButtonRole.AcceptRole)
        db = bb.addButton("Save draft", QDialogButtonBox.ButtonRole.ActionRole)
        db.clicked.connect(self._as_draft)
        bb.addButton(QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def accept(self):
        if not self._save_draft and self.to.currentData() is None:
            QMessageBox.warning(self, "No recipient",
                                "Pick a recipient before sending (or use Save draft).")
            return
        super().accept()

    def _as_draft(self):
        self._save_draft = True
        self.accept()


# ── group builder ─────────────────────────────────────────────────────────────────
class NewGroup(QDialog):
    """Create a named group / mailing list by checking members off the roster."""
    def __init__(self, contacts, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New group / mailing list")
        self.resize(360, 420)
        v = QVBoxLayout(self)
        v.addWidget(QLabel("Group name:"))
        self.name = QLineEdit()
        self.name.setPlaceholderText("e.g. claudes, ops, family")
        v.addWidget(self.name)
        v.addWidget(QLabel("Members:"))
        self.list = QListWidget()
        for c in contacts:
            it = QListWidgetItem(c["display_name"])
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Unchecked)
            it.setData(UID, c["display_name"])
            self.list.addItem(it)
        v.addWidget(self.list, 1)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        v.addWidget(bb)

    def result_group(self):
        members = [self.list.item(i).data(UID) for i in range(self.list.count())
                   if self.list.item(i).checkState() == Qt.CheckState.Checked]
        return self.name.text().strip(), members


# ── roster manager ─────────────────────────────────────────────────────────────────
class ContactsGroups(QDialog):
    """Manage the roster: view contacts + groups, create/accept invites (TernID's
    capability flow — authority ≠ identity), add a new alias/account, build groups."""
    def __init__(self, agent, account, parent=None):
        super().__init__(parent)
        self.agent, self.account = agent, account
        self.setWindowTitle("Contacts & Groups — %s" % _display(agent, account))
        self.resize(460, 500)
        v = QVBoxLayout(self)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        v.addWidget(self.tree, 1)
        self._populate()
        r1 = QHBoxLayout()
        for label, slot in (("Create invite", self._create_invite), ("Add by invite", self._add_by_invite)):
            b = QPushButton(label); b.clicked.connect(slot); r1.addWidget(b)
        v.addLayout(r1)
        r2 = QHBoxLayout()
        for label, slot in (("New alias", self._new_alias), ("New group", self._new_group),
                            ("Delete group", self._delete_group)):
            b = QPushButton(label); b.clicked.connect(slot); r2.addWidget(b)
        v.addLayout(r2)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.clicked.connect(lambda *_: self.accept())
        v.addWidget(bb)

    def _populate(self):
        self.tree.clear()
        croot = QTreeWidgetItem(self.tree, ["Contacts"])
        for c in self.agent.contacts(account=self.account):
            QTreeWidgetItem(croot, [c["display_name"]])
        groot = QTreeWidgetItem(self.tree, ["Groups"])
        QTreeWidgetItem(groot, ["crew  —  everyone (built in)"]).setData(0, UID, "crew")
        for name, members in load_lists().items():
            QTreeWidgetItem(groot, ["%s  —  %s" % (name, ", ".join(members) or "empty")]).setData(0, UID, name)
        self.tree.expandAll()

    def _create_invite(self):
        label, ok = QInputDialog.getText(self, "Create invite", "Label (who is it for)?")
        if not ok:
            return
        res = self.agent.create_invite(account=self.account, for_display_name=label or None)
        token = res.get("invite") if isinstance(res, dict) else str(res)
        dlg = QDialog(self)
        dlg.setWindowTitle("Invite token")
        dv = QVBoxLayout(dlg)
        dv.addWidget(QLabel("Share this invite with %s so they can mail you.\n"
                            "It is a capability, not a key — revocable, no identity exposed:" % (label or "them")))
        field = QLineEdit(token)
        field.setReadOnly(True)
        dv.addWidget(field)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.clicked.connect(lambda *_: dlg.accept())
        dv.addWidget(bb)
        field.selectAll()
        dlg.exec()

    def _add_by_invite(self):
        token, ok = QInputDialog.getText(self, "Add by invite", "Paste the invite token you were given:")
        if not ok or not token.strip():
            return
        try:
            self.agent.add_contact(account=self.account, invite=token.strip())
            self._populate()
        except Exception as e:
            QMessageBox.warning(self, "Add failed", str(e))

    def _new_alias(self):
        name, ok = QInputDialog.getText(self, "New alias / account", "Display name for the new seat:")
        if not ok or not name.strip():
            return
        try:
            self.agent.create_account(display_name=name.strip())
            QMessageBox.information(self, "Created", "New seat/alias '%s' created." % name.strip())
            self._populate()
        except Exception as e:
            QMessageBox.warning(self, "Create failed", str(e))

    def _new_group(self):
        d = NewGroup(self.agent.contacts(account=self.account), self)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        name, members = d.result_group()
        if not name:
            QMessageBox.warning(self, "No name", "Give the group a name.")
            return
        lists = load_lists()
        lists[name] = members
        save_lists(lists)
        self._populate()

    def _delete_group(self):
        it = self.tree.currentItem()
        tag = it.data(0, UID) if it else None
        if not tag or tag == "crew":
            QMessageBox.information(self, "Delete group", "Select a user group (not 'crew') to delete.")
            return
        lists = load_lists()
        if tag in lists:
            del lists[tag]
            save_lists(lists)
            self._populate()


# ── main window ──────────────────────────────────────────────────────────────────
class MailApp(QMainWindow):
    BOXES = ("Inbox", "Sent", "Drafts")
    _synced = Signal()

    def __init__(self, agent):
        super().__init__()
        self.agent = agent
        self._synced.connect(self._reload)       # bridge sync finished (off-thread) -> reload on GUI thread
        self.account = "Stevo"
        self.folder = "Inbox"
        self.setWindowTitle("TernOO · POBOX Mail")
        self.setWindowIcon(QIcon(ICON))
        self.resize(960, 600)
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
        self.acct.setMinimumWidth(150)                        # fit the longest seat name (Professor)
        for h in agent.list_accounts():                       # real handles are opaque (acct_…)
            self.acct.addItem(agent.account_display(account_handle=h), h)  # show name, carry handle
        want = self.acct.findText(self.account)               # prefer the captain's own seat
        if want < 0 and self.acct.count():
            want = 0
        if want >= 0:
            self.acct.setCurrentIndex(want)
            self.account = self.acct.itemData(want)
        self.acct.currentIndexChanged.connect(self._switch)
        top.addWidget(self.acct)
        for label, slot in (("Compose", self.compose), ("Reply", self.reply),
                            ("Contacts", self.manage_contacts), ("Refresh", lambda: self._sync_async())):
            b = QPushButton(label)
            b.clicked.connect(slot)
            top.addWidget(b)
        v.addLayout(top)

        split = QSplitter(Qt.Orientation.Horizontal)
        self.tree = QTreeWidget()                             # LEFT: mailboxes + contacts
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(160)
        self.tree.setMaximumWidth(240)
        self.tree.currentItemChanged.connect(self._tree_select)
        self.tree.itemDoubleClicked.connect(self._tree_dblclick)
        split.addWidget(self.tree)

        right = QSplitter(Qt.Orientation.Vertical)            # RIGHT: header table over reading pane
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Time", "From", "To", "Subject"])
        self.table.setSortingEnabled(True)                   # click a column header to sort
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(True)
        for col in (0, 1, 2):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self._open)
        self.table.itemDoubleClicked.connect(self._table_dblclick)
        right.addWidget(self.table)
        self.read = QTextEdit()
        self.read.setReadOnly(True)
        right.addWidget(self.read)
        right.setSizes([320, 260])
        split.addWidget(right)
        split.setSizes([200, 760])
        v.addWidget(split, 1)

        self.status = QLabel("")
        self.status.setStyleSheet("color:#9696a5;")
        v.addWidget(self.status)
        self._build_tree()                                   # selects Inbox -> drives the first reload

    def _sync_async(self):
        """Run the agent<->wire bridge once on a background thread (worktree-isolated), then
        reload via the thread-safe signal — a mail-call or send syncs in seconds, no UI freeze."""
        import os
        import subprocess
        import threading

        def work():
            try:
                subprocess.run(["python3", os.path.join(REPO, "tools", "mail_sync.py")],
                               capture_output=True, timeout=120)
            except Exception:
                pass
            self._synced.emit()
        threading.Thread(target=work, daemon=True).start()

    def _menus(self):
        mb = self.menuBar()
        fm = mb.addMenu("File")
        fm.addAction(QAction("Compose", self, shortcut="Ctrl+N", triggered=self.compose))
        fm.addAction(QAction("Reply", self, shortcut="Ctrl+R", triggered=self.reply))
        fm.addAction(QAction("Contacts && Groups…", self, shortcut="Ctrl+B", triggered=self.manage_contacts))
        fm.addAction(QAction("Refresh", self, shortcut="F5", triggered=lambda: self._sync_async()))
        fm.addSeparator()
        fm.addAction(QAction("Quit", self, shortcut="Ctrl+Q", triggered=self.close))
        hm = mb.addMenu("Help")
        hm.addAction(QAction("About", self, triggered=self._about))

    # ── left tree: mailboxes + contacts ──
    def _build_tree(self):
        self.tree.blockSignals(True)
        self.tree.clear()
        boxes = QTreeWidgetItem(self.tree, ["Mailboxes"])
        boxes.setFirstColumnSpanned(True)
        for name in self.BOXES:
            QTreeWidgetItem(boxes, [name]).setData(0, UID, ("box", name))
        croot = QTreeWidgetItem(self.tree, ["Contacts"])
        croot.setFirstColumnSpanned(True)
        try:
            for c in self.agent.contacts(account=self.account):
                node = QTreeWidgetItem(croot, [c["display_name"]])
                node.setData(0, UID, ("contact", c["handle"], c["display_name"]))
        except Exception:
            pass
        groot = QTreeWidgetItem(self.tree, ["Groups"])
        groot.setFirstColumnSpanned(True)
        QTreeWidgetItem(groot, ["crew"]).setData(0, UID, ("group", "crew"))
        for gname in load_lists():
            QTreeWidgetItem(groot, [gname]).setData(0, UID, ("group", gname))
        self.tree.expandAll()
        self.tree.blockSignals(False)
        self.tree.setCurrentItem(boxes.child(0))             # Inbox -> _tree_select -> _reload

    def _tree_select(self, cur, _prev=None):
        if not cur:
            return
        tag = cur.data(0, UID)
        if tag and tag[0] == "box":
            self.folder = tag[1]
            self._reload()

    def _tree_dblclick(self, it, _col=0):
        tag = it.data(0, UID)
        if tag and tag[0] == "contact":
            self._compose(prefill={"to": tag[1]})            # double-click a contact to write to them
        elif tag and tag[0] == "group":
            self._compose(prefill={"to": "list:" + tag[1]})  # or a group/mailing-list

    def manage_contacts(self):
        ContactsGroups(self.agent, self.account, self).exec()
        self._build_tree()                                   # contacts/groups may have changed

    def _me(self):
        try:
            return self.agent.account_display(account_handle=self.account)
        except Exception:
            return self.account

    # ── message table ──
    def _reload(self):
        if self.folder == "Sent":
            raw = self._sent_msgs()
        elif self.folder == "Drafts":
            raw = self._drafts()
        else:
            raw = self.agent.inbox(account=self.account)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        for m in raw:
            row = self.table.rowCount()
            self.table.insertRow(row)
            cells = (_table_time(m.get("time")), str(m.get("from", "?")),
                     str(m.get("to", "?")), str(m.get("subject", "")))
            for col, text in enumerate(cells):
                cell = QTableWidgetItem(text)
                if col == 0:
                    cell.setData(UID, m)                      # stash the whole message on the Time cell
                self.table.setItem(row, col, cell)
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.SortOrder.DescendingOrder)   # newest first by default
        self.read.clear()
        n = self.table.rowCount()
        self.status.setText("%s · %s — %d message%s" % (self._me(), self.folder, n, "" if n == 1 else "s"))

    def _sel_msg(self):
        items = self.table.selectedItems()
        if not items:
            return None
        cell = self.table.item(items[0].row(), 0)
        return cell.data(UID) if cell else None

    def _open(self):
        m = self._sel_msg()
        if not m:
            return
        try:
            self.agent.mark_read(account=self.account, message_id=m.get("id"))
        except Exception:
            pass
        self.read.setHtml(
            "<div style='color:#3fd08f;font-size:14px'>%s</div>"
            "<div style='color:#9696a5'>from <b style='color:#e6e6ec'>%s</b> · to %s · %s</div><hr>"
            "<pre style='color:#e6e6ec;white-space:pre-wrap;font-family:DejaVu Sans Mono'>%s</pre>"
            % (_esc(str(m.get("subject"))), _esc(str(m.get("from"))), _esc(str(m.get("to"))),
               _esc(_fmt_time(m.get("time"))), _esc(str(m.get("body")))))

    def _table_dblclick(self, _item):
        if self.folder != "Drafts":
            return
        m = self._sel_msg()
        if m:
            self._compose(prefill={"to_text": str(m.get("to", "")),
                                   "subject": re.sub(r"^Re:\s*", "", str(m.get("subject", ""))),
                                   "body": str(m.get("body", ""))})

    def _sent_msgs(self):
        """Reconstruct this account's SENT mail. The agent exposes no outbox query, so
        gather messages we authored from across every account's inbox, folding a single
        broadcast (same subject+time) into one row with its recipients joined."""
        try:
            me = self.agent.account_display(account_handle=self.account)
        except Exception:
            me = self.account
        try:
            accts = self.agent.list_accounts()
        except Exception:
            accts = [self.account]
        seen, out = {}, []
        for acct in accts:
            try:
                msgs = self.agent.inbox(account=acct)
            except Exception:
                continue
            for m in msgs:
                if m.get("from") != me:
                    continue
                key = (m.get("subject"), str(m.get("body")))   # fold by CONTENT — a broadcast's sends straddle whole-second stamps, so time splits one send into rows
                if key in seen:
                    prev = seen[key]
                    tos = [t.strip() for t in str(prev.get("to", "")).split(",")]
                    if str(m.get("to")) not in tos:
                        prev["to"] = str(prev.get("to", "")) + ", " + str(m.get("to"))
                    continue
                mm = dict(m)
                seen[key] = mm
                out.append(mm)
        return out

    def _drafts(self):
        """Local, untransmitted compositions saved under OUTBOX (never on the wire)."""
        out = []
        for p in sorted(glob.glob(os.path.join(OUTBOX, "*.md"))):
            try:
                txt = open(p, encoding="utf-8", errors="replace").read()
            except Exception:
                continue
            lines = txt.splitlines()

            def _h(key):
                for ln in lines[:8]:
                    mm = re.match(r"^%s:\s*(.+)" % key, ln)
                    if mm:
                        return mm.group(1).strip()
                return ""
            idx = next((i for i, l in enumerate(lines) if l.startswith("Re:")), None)
            body = "\n".join(lines[idx + 1:]).strip() if idx is not None else txt
            out.append({"id": os.path.basename(p), "from": self._me(),
                        "to": _h("To") or "?", "subject": _h("Re") or os.path.basename(p),
                        "time": int(os.path.getmtime(p)), "body": body, "unread": False})
        return out

    # ── actions ──
    def _switch(self, idx):
        self.account = self.acct.itemData(idx)
        self._build_tree()                                   # contacts are per-account; reselect Inbox -> reload

    def compose(self):
        self._compose()

    def reply(self):
        m = self._sel_msg()
        if not m:
            QMessageBox.information(self, "Reply", "Select a message first.")
            return
        sender = str(m.get("from"))
        handle = None
        try:
            for c in self.agent.contacts(account=self.account):
                if c["display_name"] == sender:
                    handle = c["handle"]
                    break
        except Exception:
            pass
        subj = str(m.get("subject", ""))
        if not subj.lower().startswith("re:"):
            subj = "Re: " + subj
        quoted = "\n\n> " + "\n> ".join(str(m.get("body", "")).splitlines())
        self._compose(prefill={"to": handle, "subject": subj, "body": quoted})

    def _compose(self, prefill=None):
        d = Compose(self.agent, self.account, self, prefill=prefill)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        to_data = d.to.currentData()
        to_text = d.to.currentText()
        subject = d.subj.text() or "(no subject)"
        body = d.body.toPlainText()
        if getattr(d, "_save_draft", False):
            self._write_draft(to_text, subject, body)
            self._select_box("Drafts")
            return
        if isinstance(to_data, str) and to_data.startswith("list:"):
            lname = to_data[5:]
            targets = resolve_list(lname, d.contacts)
            if not targets:
                QMessageBox.warning(self, "Empty list", "No reachable members on the '%s' list." % lname)
                return
            for h in targets:
                self.agent.send(from_account=self.account, to_contact=h,
                                subject="[%s] %s" % (lname, subject), body=body)
            QMessageBox.information(self, "Sent to list",
                                    "Delivered to %d on the %s list." % (len(targets), lname))
        else:
            res = self.agent.send(from_account=self.account, to_contact=to_data,
                                  subject=subject, body=body)
            fn = res["message_id"] if isinstance(res, dict) else res
            QMessageBox.information(self, "Sent",
                                    "Delivered through the TernID agent.\nmessage id: %s" % fn)
        self._sync_async()       # push the just-sent mail to the wire now, then reload

    def _write_draft(self, to_text, subject, body):
        ts = datetime.datetime.now().strftime("%Y-%m-%d-%H%M")
        slug = (re.sub(r"\W+", "-", subject.lower())[:40].strip("-")) or "draft"
        stamp = datetime.datetime.now().strftime("%H:%M %d/%m/%Y ACDT")
        with open(os.path.join(OUTBOX, "%s-draft-%s.md" % (ts, slug)), "w", encoding="utf-8") as f:
            f.write("%s\n\nTo: %s\nFrom: %s\nRe: %s\n\n%s\n" % (stamp, to_text, self._me(), subject, body))

    def _select_box(self, name):
        root = self.tree.topLevelItem(0)
        if not root:
            return
        for i in range(root.childCount()):
            if root.child(i).text(0) == name:
                self.tree.setCurrentItem(root.child(i))
                return

    def _about(self):
        QMessageBox.information(self, "POBOX Mail",
                                "TernOO · POBOX Mail — PySide6 face on the live TernID agent.\n"
                                "3-pane: mailboxes + contacts · sortable headers · reading pane.\n"
                                "Compose / Reply send real sealed mail; Drafts stay local.")


def _esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt_time(t):
    """Agent sends `time` as a unix int; the old stub sent a string. Format either."""
    try:
        return datetime.datetime.fromtimestamp(int(t)).strftime("%H:%M %d/%m/%Y")
    except (ValueError, TypeError, OSError):
        return str(t)


def _table_time(t):
    """Timestamp for the sortable Time column: ISO-ish, so lexical sort == chronological."""
    try:
        return datetime.datetime.fromtimestamp(int(t)).strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError, OSError):
        return str(t)


def load_lists():
    """Named distribution lists {name: [display_name, ...]}. 'crew' is built-in (everyone)."""
    try:
        return json.load(open(MAILLISTS))
    except Exception:
        default = {"claudes": ["CC", "CCC", "CAI", "Professor"]}   # a handy starter list
        try:
            os.makedirs(os.path.dirname(MAILLISTS), exist_ok=True)
            json.dump(default, open(MAILLISTS, "w"), indent=1)
        except Exception:
            pass
        return default


def save_lists(lists):
    """Persist the named distribution lists. 'crew' is built-in, never stored."""
    os.makedirs(os.path.dirname(MAILLISTS), exist_ok=True)
    json.dump({k: v for k, v in lists.items() if k != "crew"},
              open(MAILLISTS, "w", encoding="utf-8"), indent=1)


def resolve_list(name, contacts):
    """Contact handles for a list. 'crew' = all contacts; named lists match members by display name."""
    if name == "crew":
        return [c["handle"] for c in contacts]
    by_disp = {c["display_name"]: c["handle"] for c in contacts}
    return [by_disp[m] for m in load_lists().get(name, []) if m in by_disp]


def _display(agent, account):
    try:
        return agent.account_display(account_handle=account)
    except Exception:
        return str(account)


DARK = ("QWidget{background:#1a1f2b;color:#e6e6ec;}"
        "QListWidget,QTextEdit,QLineEdit,QComboBox{background:#15151f;border:1px solid #3a3a52;}"
        "QListWidget::item:selected{background:#2e466e;}"
        "QPushButton{background:#2e466e;border:1px solid #5a82be;border-radius:4px;padding:3px 10px;}"
        "QMenuBar,QMenu{background:#1e2431;} QMenu::item:selected{background:#2e466e;}")


def make_agent():
    """Pick the backend: the real TernID agent over IPC if TERNID_AGENT_SOCK is set,
    else the inert in-process git-POBOX stub. Same §B methods either way."""
    sock = os.environ.get("TERNID_AGENT_SOCK")
    if sock:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from ternid_agent_protocol import Client
        return Client(sock)
    return StubBackend()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("POBOX Mail")
    app.setDesktopFileName("pobox-mail-qt")   # so Cinnamon matches the window to the .desktop icon
    app.setWindowIcon(QIcon(ICON))
    app.setStyleSheet(DARK)
    w = MailApp(make_agent())
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
