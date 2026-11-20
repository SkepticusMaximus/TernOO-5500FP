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
import bisect
import datetime
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QListWidget, QListWidgetItem, QTextEdit, QLabel, QComboBox,
                               QPushButton, QDialog, QLineEdit, QDialogButtonBox, QSplitter,
                               QMessageBox, QTreeWidget, QTreeWidgetItem, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView, QInputDialog,
                               QCompleter, QCheckBox, QFormLayout, QColorDialog, QSystemTrayIcon)
from PySide6.QtGui import (QAction, QFont, QBrush, QColor, QIcon, QShortcut, QKeySequence,
                           QTextCursor, QSyntaxHighlighter, QTextCharFormat, QTextBlockFormat,
                           QTextListFormat)
from PySide6.QtCore import Qt, Signal, QStringListModel, QTimer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root — portable across machines
POBOX = os.path.join(REPO, "private", "POBOX")
ICON = os.path.join(REPO, "tools", "pobox-mail.svg")
OUTBOX = os.path.expanduser("~/.config/ternoo/mail-outbox")   # DRAFTS only — never transmitted
ROSTER = os.path.expanduser("~/.config/ternoo/contacts.json")
MAILLISTS = os.path.expanduser("~/.config/ternoo/maillists.json")   # named distribution lists
os.makedirs(OUTBOX, exist_ok=True)
SEATS = ["Stevo", "CC", "CCC", "CF5", "CAI", "CO5", "Professor"]
UID = Qt.ItemDataRole.UserRole
SORT_ROLE = int(Qt.ItemDataRole.UserRole) + 1                  # epoch stashed for chronological sort
SETTINGS = os.path.expanduser("~/.config/ternoo/mail-settings.json")

# date-format presets (label shown in Settings -> strftime pattern). Default = Australian 12h.
DATE_FORMATS = [
    ("Day/Month/Year · 12h    31/12/2026 2:05 PM", "%d/%m/%Y %-I:%M %p"),
    ("Day/Month/Year · 24h    31/12/2026 14:05", "%d/%m/%Y %H:%M"),
    ("Day-Month-Year · 12h    31-12-2026 2:05 PM", "%d-%m-%Y %-I:%M %p"),
    ("Day Mon Year · 12h      31 Dec 2026 2:05 PM", "%d %b %Y %-I:%M %p"),
    ("Year-Month-Day · 24h    2026-12-31 14:05", "%Y-%m-%d %H:%M"),
    ("Month/Day/Year · 12h    12/31/2026 2:05 PM", "%m/%d/%Y %-I:%M %p"),
]
DEFAULT_DATE_FMT = DATE_FORMATS[0][1]                          # Australian 12h (captain's preference)


def load_settings():
    try:
        return json.load(open(SETTINGS))
    except Exception:
        return {}


def save_settings(s):
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    json.dump(s, open(SETTINGS, "w"), indent=1)


def date_fmt():
    return load_settings().get("date_format", DEFAULT_DATE_FMT)


# reading-pane font size (g92), seal-recipient confirmation (g96), signature (g94)
FONT_SIZES = [("Small — 10", 10), ("Medium — 12 (default)", 12), ("Large — 14", 14), ("Extra large — 17", 17)]
DEFAULT_FONT_PT = 12


def reading_pt():
    return int(load_settings().get("reading_pt", DEFAULT_FONT_PT))


def seal_confirm():
    return load_settings().get("seal_confirm", True)         # default ON (hermetic safety)


def signature():
    return load_settings().get("signature", "")


def auto_read():
    return bool(load_settings().get("auto_read", False))      # g93: default manual


def sync_min():
    return int(load_settings().get("sync_min", 1))            # g95: minutes; 0 = manual only


def notify_on():
    return bool(load_settings().get("notify", True))          # g95: desktop toast on new mail


class _TimeItem(QTableWidgetItem):
    """A Date cell that sorts by the epoch stashed in SORT_ROLE, not by its shown text — so
    DD/MM/YYYY (or any format) still sorts newest-to-oldest correctly."""
    def __lt__(self, other):
        return (self.data(SORT_ROLE) or 0) < (other.data(SORT_ROLE) or 0)


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


# ── g70: spell-check — dependency-free (system word lists + difflib suggestions) ────
PERSONAL_DICT = os.path.expanduser("~/.config/ternoo/mail-dict.txt")
_DICT = None
# ship-vocabulary so our own words don't squiggle; the user grows their own via "Add to dictionary"
_TERNOO_WORDS = {
    "ternoo", "ternid", "ternauth", "ternip", "tmail", "pobox", "flowcode", "terndo",
    "gristmill", "cc", "ccc", "cf5", "cai", "co5", "huey", "lenny", "colibri", "trit",
    "trits", "markdown", "rclone", "systemd", "tailscale", "repo", "config", "wifi", "async",
}


def _load_dict():
    """Union of the system word list + the en_AU/en_US hunspell dictionaries (so Aussie
    spellings pass) + the user's personal additions. Built once, cached."""
    global _DICT
    if _DICT is not None:
        return _DICT
    words = set()
    try:
        with open("/usr/share/dict/words", encoding="utf-8", errors="ignore") as f:
            for line in f:
                words.add(line.strip().lower())
    except Exception:
        pass
    for path in ("/usr/share/hunspell/en_AU.dic", "/usr/share/hunspell/en_US.dic"):
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                next(f, None)                                  # first line is the entry count
                for line in f:
                    words.add(line.split("/")[0].strip().lower())   # drop affix flags
        except Exception:
            pass
    try:
        with open(PERSONAL_DICT, encoding="utf-8") as f:
            for line in f:
                words.add(line.strip().lower())
    except Exception:
        pass
    words |= _TERNOO_WORDS
    words.discard("")
    _DICT = words
    return words


def _spell_ok(word):
    d = _load_dict()
    lw = word.lower().strip("'")
    if not lw or lw in d:
        return True
    if word.isupper() or any(c.isdigit() for c in word):       # acronyms, codes
        return True
    if lw.endswith("'s") and lw[:-2] in d:                      # possessive
        return True
    # inflection leniency: the hunspell .dic ships base words, not every inflected form, so
    # "prioritising"/"organised"/"colours" would wrongly squiggle. Accept if a known base remains.
    for suf, repl in (("ings", "e"), ("ing", "e"), ("ing", ""), ("ed", "e"), ("ed", ""),
                      ("es", ""), ("s", ""), ("ly", ""), ("ers", ""), ("er", ""), ("est", ""),
                      ("ations", "e"), ("ation", "e")):
        if lw.endswith(suf) and len(lw) - len(suf) >= 3 and (lw[:-len(suf)] + repl) in d:
            return True
    return False


def _spell_suggest(word, n=6):
    import difflib
    d = _load_dict()
    lw = word.lower()
    cand = [w for w in d if w[:1] == lw[:1] and abs(len(w) - len(lw)) <= 2]   # prefilter -> fast
    sugg = difflib.get_close_matches(lw, cand or list(d), n=n, cutoff=0.6)
    # adjacent-transposition typos (teh->the) score low in difflib; surface them first
    for i in range(len(lw) - 1):
        sw = lw[:i] + lw[i + 1] + lw[i] + lw[i + 2:]
        if sw != lw and sw in d and sw not in sugg:
            sugg.insert(0, sw)
    return sugg[:n]


def _add_personal(word):
    try:
        os.makedirs(os.path.dirname(PERSONAL_DICT), exist_ok=True)
        with open(PERSONAL_DICT, "a", encoding="utf-8") as f:
            f.write(word.lower() + "\n")
        _load_dict().add(word.lower())
    except Exception:
        pass


# ── autocomplete: frequency-ranked PIM dictionary + user pins + whole-string fuzzy ──────────
# Dictionary built by tools/build_pim_dict.py (Norvig counts ∩ local clean dict, PIM-boosted,
# log-normalized popularity). Ranking blends popularity with similarity (the captain's spec).
_FREQ = None                                                   # {word: popularity 0..1}
_FREQ_SORTED = None                                            # sorted keys for prefix bisect
PINS_FILE = os.path.expanduser("~/.config/ternoo/mail-pins.txt")
_PINS = None


def _freq():
    global _FREQ
    if _FREQ is None:
        _FREQ = {}
        try:
            path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pim_words.tsv")
            for line in open(path, encoding="utf-8"):
                parts = line.rstrip("\n").split("\t")
                if len(parts) >= 2:
                    _FREQ[parts[0]] = float(parts[1])
        except Exception:
            pass
        if not _FREQ:                                          # fallback: hand-seeded common_words.txt
            try:
                p2 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "common_words.txt")
                seed = [l.strip().lower() for l in open(p2, encoding="utf-8") if l.strip()]
                n = len(seed) or 1
                _FREQ = {w: 1 - i / n for i, w in enumerate(seed)}
            except Exception:
                pass
    return _FREQ


def _freq_sorted():
    global _FREQ_SORTED
    if _FREQ_SORTED is None:
        _FREQ_SORTED = sorted(_freq())
    return _FREQ_SORTED


def _pins():
    """User-pinned words (right-click → Pin to predictions): always offered, top precedence."""
    global _PINS
    if _PINS is None:
        try:
            _PINS = [l.strip() for l in open(PINS_FILE, encoding="utf-8") if l.strip()]
        except Exception:
            _PINS = []
    return _PINS


def _add_pin(word):
    """Pin a word to the TOP of predictions and whitelist it (offered + never squiggled)."""
    w = word.strip()
    if not w:
        return
    pins = _pins()
    if w.lower() not in [p.lower() for p in pins]:
        pins.insert(0, w)                                      # newest pin = highest precedence
        try:
            os.makedirs(os.path.dirname(PINS_FILE), exist_ok=True)
            with open(PINS_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(pins) + "\n")
        except Exception:
            pass
    _add_personal(w)                                           # whitelist for the spell-checker too


def _rank_completions(prefix, names, limit=8):
    """Ranked predictions: user pins → contacts/@-mentions → frequency-ranked words (by
    popularity) → whole-string similarity fallback for typo'd words (blend 0.7·sim + 0.3·pop)."""
    p = prefix.lower()
    out, seen = [], set()

    def add(w):
        lw = w.lower()
        if lw not in seen and lw != p:
            seen.add(lw)
            out.append(w)

    if p.startswith("@"):                                       # @-mentions only
        for n in names:
            if n.lower().startswith(p):
                add(n)
        return out[:limit]
    for w in _pins():                                          # 1. user pins — highest precedence
        if w.lower().startswith(p):
            add(w)
    for n in names:                                            # 2. contacts
        if not n.startswith("@") and n.lower().startswith(p):
            add(n)
    freq = _freq()                                             # 3. frequency-ranked, popularity desc
    fs = _freq_sorted()
    lo = bisect.bisect_left(fs, p)
    hi = bisect.bisect_left(fs, p + "￿")
    for w in sorted(fs[lo:hi], key=lambda x: -freq.get(x, 0)):
        add(w)
    if len(out) < limit and len(p) >= 3:                       # 4. whole-string similarity (typos)
        import difflib
        pool = list(freq.keys())[:8000] + [n for n in names if not n.startswith("@")]
        cand = difflib.get_close_matches(p, pool, n=limit * 2, cutoff=0.6)
        cand.sort(key=lambda w: -(difflib.SequenceMatcher(None, p, w).ratio() * 0.7
                                  + freq.get(w.lower(), 0) * 0.3))
        for w in cand:
            add(w)
    return out[:limit]


class SpellHighlighter(QSyntaxHighlighter):
    """Red wavy underline under words the dictionary doesn't know."""
    def __init__(self, doc):
        super().__init__(doc)
        self._fmt = QTextCharFormat()
        # WaveUnderline relies on the paint engine and silently doesn't render on some X11
        # setups (the captain's). A solid underline + a subtle red wash CAN'T fail to show.
        self._fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        self._fmt.setUnderlineColor(QColor("#ff5a4a"))
        self._fmt.setBackground(QColor("#4e2626"))

    def highlightBlock(self, text):
        for mo in re.finditer(r"[A-Za-z][A-Za-z']*", text):
            w = mo.group()
            if len(w) > 2 and not _spell_ok(w):
                self.setFormat(mo.start(), len(w), self._fmt)


class SpellTextEdit(QTextEdit):
    """QTextEdit with live spell-check (red squiggles + right-click corrections) AND
    autocomplete — a popup of dictionary words + contact / @-mention names after 3+ letters,
    dismissed by typing past it or pressing Esc."""
    def __init__(self, parent=None, words=None):
        super().__init__(parent)
        self._hl = SpellHighlighter(self.document())
        self._names = sorted(words) if words else []           # contact + @-mention vocabulary
        self._cmodel = QStringListModel([], self)               # refilled per keystroke, pre-ranked
        self._completer = QCompleter(self._cmodel, self)
        self._completer.setWidget(self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setModelSorting(QCompleter.ModelSorting.UnsortedModel)   # keep OUR ranking
        self._completer.setMaxVisibleItems(8)
        self._completer.activated.connect(self._insert_completion)

    def _completion_prefix(self):
        """The word being typed, including a leading @ (so @-mentions complete)."""
        cur = self.textCursor()
        block = cur.block().text()
        col = cur.positionInBlock()
        start = col
        while start > 0 and (block[start - 1].isalnum() or block[start - 1] in "@_'"):
            start -= 1
        return block[start:col]

    def _insert_completion(self, completion):
        cur = self.textCursor()
        prefix = self._completion_prefix()
        cur.movePosition(QTextCursor.MoveOperation.Left, QTextCursor.MoveMode.KeepAnchor, len(prefix))
        cur.insertText(completion)
        self.setTextCursor(cur)

    def keyPressEvent(self, e):
        c = self._completer
        if c.popup().isVisible() and e.key() in (Qt.Key.Key_Enter, Qt.Key.Key_Return,
                                                 Qt.Key.Key_Escape, Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            e.ignore()                                           # let the popup take Enter/Tab/Esc
            return
        super().keyPressEvent(e)
        prefix = self._completion_prefix()
        last = e.text()[-1] if e.text() else ""
        if len(prefix.lstrip("@")) < 2 or (last and not last.isalnum() and last not in "@_'"):
            c.popup().hide()
            return
        ranked = _rank_completions(prefix, self._names)         # common words first, blue > blubber
        if not ranked:
            c.popup().hide()
            return
        self._cmodel.setStringList(ranked)
        c.setCompletionPrefix(prefix)
        c.popup().setCurrentIndex(c.completionModel().index(0, 0))
        rect = self.cursorRect()
        rect.setWidth(c.popup().sizeHintForColumn(0) + c.popup().verticalScrollBar().sizeHint().width())
        c.complete(rect)

    def contextMenuEvent(self, event):
        menu = self.createStandardContextMenu()
        cur = self.cursorForPosition(event.pos())
        cur.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cur.selectedText()
        if word:
            first = menu.actions()[0] if menu.actions() else None
            if not _spell_ok(word):                            # corrections for a misspelled word
                for s in _spell_suggest(word):
                    a = QAction(s, menu)
                    a.triggered.connect(lambda _=False, w=s, c=QTextCursor(cur): c.insertText(w))
                    menu.insertAction(first, a)
                addw = QAction('Add "%s" to dictionary' % word, menu)
                addw.triggered.connect(lambda _=False, w=word: (_add_personal(w), self._hl.rehighlight()))
                menu.insertAction(first, addw)
            pin = QAction('Pin "%s" to predictions' % word, menu)   # user-prioritise, any word
            pin.triggered.connect(lambda _=False, w=word: (_add_pin(w), self._hl.rehighlight()))
            menu.insertAction(first, pin)
            menu.insertSeparator(first)
        menu.exec(event.globalPos())


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
        fmt = QHBoxLayout()                                   # g62: markdown compose helpers
        fmt.setSpacing(4)
        for lbl, tip, fn in (("B", "Bold  (Ctrl+B)", self._md_bold),
                             ("I", "Italic  (Ctrl+I)", self._md_italic),
                             ("H", "Heading", self._md_heading),
                             ("•", "Bullet", self._md_bullet),
                             ("</>", "Code", self._md_code)):
            b = QPushButton(lbl)
            b.setToolTip(tip)
            b.setMaximumWidth(48 if len(lbl) > 1 else 30)
            b.clicked.connect(fn)
            fmt.addWidget(b)
        fmt.addStretch(1)
        hint = QLabel("live formatting · sent as markdown")
        hint.setStyleSheet("color:#6f6f82;font-size:11px;")
        fmt.addWidget(hint)
        v.addLayout(fmt)
        nm = [c["display_name"] for c in self.contacts]         # autocomplete name vocabulary
        grp = list(load_lists().keys()) + ["crew"]
        names = nm + grp + ["@" + n for n in nm + grp]
        self.body = SpellTextEdit(words=names)                 # g70 spell-check + ranked autocomplete
        self.body.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        v.addWidget(self.body, 1)
        QShortcut(QKeySequence("Ctrl+B"), self.body).activated.connect(self._md_bold)
        QShortcut(QKeySequence("Ctrl+I"), self.body).activated.connect(self._md_italic)
        if prefill:                                           # Reply / re-open a draft pre-fills
            i = self.to.findData(prefill["to"]) if prefill.get("to") else -1
            if i < 0 and prefill.get("to_text"):              # drafts carry the recipient as display text
                i = self.to.findText(prefill["to_text"])
            if i >= 0:
                self.to.setCurrentIndex(i)
            if prefill.get("subject"):
                self.subj.setText(prefill["subject"])
            if prefill.get("body"):
                self.body.setMarkdown(prefill["body"])        # show replies/drafts rendered, not raw
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

    # ── g62 WYSIWYG: real rich-text formatting; the wire still gets clean markdown ──────
    # Compose shows true bold/italic/headings (toggled on the selection, or on what you type
    # next). On Send/Save the body is exported via document().toMarkdown(), so **bold**, *italic*,
    # `code`, ## headings and - bullets all come out as plain markdown the reader renders back.
    def _md_bold(self):
        normal = QFont.Weight.Normal
        self.body.setFontWeight(normal if self.body.fontWeight() > normal else QFont.Weight.Bold)
        self.body.setFocus()

    def _md_italic(self):
        self.body.setFontItalic(not self.body.fontItalic())
        self.body.setFocus()

    def _md_code(self):
        cur = self.body.textCursor()
        on = cur.charFormat().fontFixedPitch()
        f = QTextCharFormat()
        f.setFontFixedPitch(not on)
        f.setFontFamilies(["DejaVu Sans Mono"] if not on else [self.body.font().family()])
        if cur.hasSelection():
            cur.mergeCharFormat(f)
        self.body.mergeCurrentCharFormat(f)
        self.body.setFocus()

    def _md_heading(self):
        cur = self.body.textCursor()
        if cur.hasSelection():
            # Only the SELECTED line becomes a heading — split it out of its block so it
            # doesn't heading the whole body (the captain's finesse, 17-11).
            txt = cur.selectedText().replace(" ", " ").replace(" ", " ").strip()
            if not txt:
                self.body.setFocus()
                return
            cur.removeSelectedText()
            if cur.positionInBlock() != 0:                     # start the heading on its own line
                cur.insertBlock()
            hb = QTextBlockFormat()
            hb.setHeadingLevel(2)                              # toMarkdown -> "## "
            cur.setBlockFormat(hb)
            hf = QTextCharFormat()
            hf.setFontWeight(QFont.Weight.Bold)
            hf.setProperty(QTextCharFormat.Property.FontSizeAdjustment, 2)
            cur.insertText(txt, hf)
            cur.insertBlock(QTextBlockFormat(), QTextCharFormat())   # normal block after, so typing continues plain
            self.body.setTextCursor(cur)
        else:
            # No selection: toggle heading on the current line/block.
            is_head = cur.blockFormat().headingLevel() > 0
            hb = QTextBlockFormat()
            hb.setHeadingLevel(0 if is_head else 2)
            cur.mergeBlockFormat(hb)
            line = QTextCursor(cur)
            line.select(QTextCursor.SelectionType.BlockUnderCursor)
            hf = QTextCharFormat()
            hf.setFontWeight(QFont.Weight.Normal if is_head else QFont.Weight.Bold)
            hf.setProperty(QTextCharFormat.Property.FontSizeAdjustment, 0 if is_head else 2)
            line.mergeCharFormat(hf)
        self.body.setFocus()

    def _md_bullet(self):
        self.body.textCursor().createList(QTextListFormat.Style.ListDisc)
        self.body.setFocus()


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
        self._hdr = hdr
        hdr.setStyleSheet("color:%s;font-size:16px;" % theme_colors()["accent"])
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
                            ("→ To-Do", self.make_todo), ("Trust sender", self.trust_sender),
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
        self.table.setHorizontalHeaderLabels(["Date", "From", "To", "Subject"])
        self.table.setSortingEnabled(True)                   # click a column header to sort
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        hh = self.table.horizontalHeader()
        hh.setStretchLastSection(True)
        self._loading = False
        hh.sortIndicatorChanged.connect(self._save_sort)     # g97: remember the user's chosen sort
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
        self.status.setStyleSheet("color:%s;" % theme_colors()["muted"])
        v.addWidget(self.status)
        # g93 read-state (local; hermetic mail has no server read flag) + g95 auto-sync + notify
        self._read = set(self._load_read())
        self._seen_ids = set()
        self._tray = QSystemTrayIcon(QIcon(ICON), self)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self._tray.show()
        self._synctimer = QTimer(self)
        self._synctimer.timeout.connect(self._sync_async)
        self._apply_sync_timer()
        self._build_tree()                                   # selects Inbox -> drives the first reload

    # ── g95 auto-sync + g93 read-state helpers ──
    READ_STATE = os.path.expanduser("~/.config/ternoo/mail-read.json")

    def _apply_sync_timer(self):
        m = sync_min()
        self._synctimer.start(m * 60000) if m > 0 else self._synctimer.stop()

    def _load_read(self):
        try:
            return json.load(open(self.READ_STATE))
        except Exception:
            return []

    def _save_read(self):
        try:
            json.dump(sorted(self._read), open(self.READ_STATE, "w"))
        except Exception:
            pass

    def _mark_read(self, mid, read=True):
        """g93: local read-state. Updates the store and re-styles the selected row (no full reload)."""
        if not mid:
            return
        self._read.add(mid) if read else self._read.discard(mid)
        self._save_read()
        items = self.table.selectedItems()
        if items:
            f = QFont()
            f.setBold(not read)
            for col in range(4):
                it = self.table.item(items[0].row(), col)
                if it:
                    it.setFont(f)

    def _toggle_read(self):
        m = self._sel_msg()
        if m and not m.get("sent"):
            self._mark_read(m.get("id"), m.get("id") not in self._read)

    def _sync_async(self):
        """Run the agent<->wire bridge once on a background thread (worktree-isolated), then
        reload via the thread-safe signal — a mail-call or send syncs in seconds, no UI freeze."""
        import os
        import subprocess
        import threading

        def work():
            try:
                if hasattr(self.agent, "wire"):           # hermetic: push our sealed pool, pull others'
                    self.agent.wire.sync(push=True)       # in-process; NO plaintext bridge
                else:
                    subprocess.run(["python3", os.path.join(REPO, "tools", "mail_sync.py")],
                                   capture_output=True, timeout=120)
            except Exception:
                pass
            self._synced.emit()
        threading.Thread(target=work, daemon=True).start()

    def _settings(self):
        """Settings dialog — date format, reading-pane text size, signature, seal-confirm."""
        d = QDialog(self)
        d.setWindowTitle("Tmail — Settings")
        form = QFormLayout(d)
        datef = QComboBox()
        datef.addItems([lbl for lbl, _ in DATE_FORMATS])
        datef.setCurrentIndex(next((i for i, (_, f) in enumerate(DATE_FORMATS) if f == date_fmt()), 0))
        form.addRow("Date / time format:", datef)
        fontf = QComboBox()
        fontf.addItems([lbl for lbl, _ in FONT_SIZES])
        fontf.setCurrentIndex(next((i for i, (_, pt) in enumerate(FONT_SIZES) if pt == reading_pt()), 1))
        form.addRow("Reading-pane text size:", fontf)
        sealc = QCheckBox("Confirm recipients before sealing each letter")
        sealc.setChecked(bool(seal_confirm()))
        form.addRow("Security:", sealc)
        sigf = QLineEdit(signature())
        sigf.setPlaceholderText("appended to new letters after a '-- ' line")
        form.addRow("Signature:", sigf)

        # ── Appearance (g91): theme preset + per-element custom colours via Qt's picker ──
        from PySide6.QtGui import QColor
        s0 = load_settings()
        themef = QComboBox()
        themef.addItems(list(THEMES.keys()))
        themef.setCurrentText(s0.get("theme_name", DEFAULT_THEME))
        form.addRow("Theme:", themef)
        custom = dict(s0.get("theme_custom", {}) or {})
        btns = {}

        def _cur(key):
            return custom.get(key) or THEMES[themef.currentText()].get(key)

        def _paint():
            for k, b in btns.items():
                b.setStyleSheet("background:%s;border:1px solid #888;border-radius:3px;" % _cur(k))

        def _mkpick(key):
            def pick():
                col = QColorDialog.getColor(QColor(_cur(key)), d, "Pick the %s colour" % key)
                if col.isValid():
                    custom[key] = col.name()
                    _paint()
            return pick

        row = QHBoxLayout()
        for label, key in COLOR_KEYS:
            b = QPushButton()
            b.setFixedSize(34, 22)
            b.clicked.connect(_mkpick(key))
            btns[key] = b
            row.addWidget(QLabel(label))
            row.addWidget(b)
        themef.currentTextChanged.connect(lambda _=None: (custom.clear(), _paint()))
        _paint()
        cw = QWidget()
        cw.setLayout(row)
        form.addRow("Custom colours:", cw)

        # ── g93 mark-as-read · g95 auto-sync + notifications ──
        autoread = QCheckBox("Mark a message read automatically when I open it")
        autoread.setChecked(bool(s0.get("auto_read", False)))
        form.addRow("Mark as read:", autoread)
        syncf = QComboBox()
        syncf.addItems(["Manual only", "Every 1 min", "Every 3 min", "Every 5 min"])
        syncf.setCurrentIndex({0: 0, 1: 1, 3: 2, 5: 3}.get(int(s0.get("sync_min", 1)), 1))
        form.addRow("Auto-sync the wire:", syncf)
        notifyf = QCheckBox("Desktop notification when new mail arrives")
        notifyf.setChecked(bool(s0.get("notify", True)))
        form.addRow("Notifications:", notifyf)

        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(d.accept)
        bb.rejected.connect(d.reject)
        form.addRow(bb)
        if d.exec() != QDialog.DialogCode.Accepted:
            return
        s = load_settings()
        s["date_format"] = dict(DATE_FORMATS).get(datef.currentText(), DEFAULT_DATE_FMT)
        s["reading_pt"] = dict(FONT_SIZES).get(fontf.currentText(), DEFAULT_FONT_PT)
        s["seal_confirm"] = sealc.isChecked()
        s["signature"] = sigf.text().strip()
        s["theme_name"] = themef.currentText()
        s["theme_custom"] = custom
        s["auto_read"] = autoread.isChecked()
        s["sync_min"] = [0, 1, 3, 5][syncf.currentIndex()]
        s["notify"] = notifyf.isChecked()
        save_settings(s)
        apply_theme(QApplication.instance())                  # re-skin the whole app live
        self._hdr.setStyleSheet("color:%s;font-size:16px;" % theme_colors()["accent"])
        self._apply_sync_timer()                              # g95: adjust the auto-sync cadence
        self._reload()                                        # re-render the table + reading pane

    def _save_sort(self, col, order):
        """g97: persist the user's chosen sort column + direction (skip while we restore it)."""
        if getattr(self, "_loading", False):
            return
        s = load_settings()
        s["sort_col"], s["sort_order"] = int(col), int(getattr(order, "value", order))
        save_settings(s)

    def _names_for(self, handles, contacts):
        by = {c["handle"]: c["display_name"] for c in contacts}
        return [by.get(h, str(h)) for h in handles]

    def _confirm_seal(self, names):
        """Hermetic safety: before sealing, show EXACTLY who will be able to open this letter —
        because once sealed, no one else ever can, by design."""
        who = ", ".join(names) if names else "(no one)"
        r = QMessageBox.question(
            self, "Seal this letter?",
            "This letter will be hermetically sealed.\n\nOnly these can ever open it:\n  %s\n\n"
            "No one else — not the wire, not another seat, not even the captain — can read it.\n\nSend?"
            % who,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        return r == QMessageBox.StandardButton.Yes

    def _menus(self):
        mb = self.menuBar()
        fm = mb.addMenu("File")
        fm.addAction(QAction("Compose", self, shortcut="Ctrl+N", triggered=self.compose))
        fm.addAction(QAction("Reply", self, shortcut="Ctrl+R", triggered=self.reply))
        fm.addAction(QAction("Make To-Do from message", self, shortcut="Ctrl+T", triggered=self.make_todo))
        fm.addAction(QAction("Toggle read / unread", self, shortcut="Ctrl+U", triggered=self._toggle_read))
        fm.addAction(QAction("Contacts && Groups…", self, shortcut="Ctrl+B", triggered=self.manage_contacts))
        fm.addAction(QAction("Refresh", self, shortcut="F5", triggered=lambda: self._sync_async()))
        fm.addSeparator()
        fm.addAction(QAction("Settings…", self, shortcut="Ctrl+,", triggered=self._settings))
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
        bold = QFont()
        bold.setBold(True)
        for m in raw:
            row = self.table.rowCount()
            self.table.insertRow(row)
            unread = self.folder == "Inbox" and not m.get("sent") and m.get("id") not in self._read
            tcell = _TimeItem(_table_time(m.get("time")))
            tcell.setData(SORT_ROLE, _epoch(m.get("time")))   # the real chronological sort key
            tcell.setData(UID, m)                             # stash the whole message on the Date cell
            self.table.setItem(row, 0, tcell)
            for col, text in ((1, str(m.get("from", "?"))), (2, str(m.get("to", "?"))),
                              (3, str(m.get("subject", "")))):
                self.table.setItem(row, col, QTableWidgetItem(text))
            if unread:                                        # g93: unread letters are bold
                for col in range(4):
                    self.table.item(row, col).setFont(bold)
        self.table.setSortingEnabled(True)
        s = load_settings()                                     # g97: restore the saved sort
        self._loading = True
        self.table.sortItems(int(s.get("sort_col", 0)), Qt.SortOrder(int(s.get("sort_order", 1))))
        self._loading = False
        if self.folder == "Inbox":                             # g95: notify on genuinely new mail
            cur = {m.get("id") for m in raw if not m.get("sent")}
            new = cur - self._seen_ids
            if new and self._seen_ids and notify_on() and self._tray.isSystemTrayAvailable():
                self._tray.showMessage("TernOO · POBOX Mail",
                                       "%d new sealed letter%s" % (len(new), "" if len(new) == 1 else "s"),
                                       QSystemTrayIcon.MessageIcon.Information, 5000)
            self._seen_ids = cur
        self.read.clear()
        n = self.table.rowCount()
        base = "%s · %s — %d message%s" % (self._me(), self.folder, n, "" if n == 1 else "s")
        al = self.agent.alarms() if hasattr(self.agent, "alarms") else []   # M2/H3 tripwires
        if al:
            self.status.setText("⚠ " + " · ".join(al))
            self.status.setStyleSheet("color:#ffb0b0;font-weight:bold;")
        else:
            self.status.setText(base)
            self.status.setStyleSheet("")

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
        if auto_read() and not m.get("sent"):                 # g93: auto-mark read on open (if enabled)
            self._mark_read(m.get("id"), True)
        c = theme_colors()                                    # g91: reading pane follows the theme
        fp = str(m.get("fingerprint") or "")
        fpline = " <span style='color:%s'>· %s</span>" % (c["link"], _esc(fp)) if fp else ""
        # H3: a sender whose name isn't pinned to this key gets a loud warning, never silent trust.
        warn = ("" if m.get("verified", True) or m.get("sent") else
                "<div style='background:#5a1e1e;color:#ffd0d0;padding:5px 9px;border-radius:4px;margin:4px 0'>"
                "⚠ UNVERIFIED SENDER — this display name is <b>not pinned</b> to this key "
                "(fingerprint %s). If the sender gave you this exact fingerprint out of band, "
                "click <b>Trust sender</b> to pin it.</div>" % _esc(fp))
        self.read.setStyleSheet("font-size:%dpt" % reading_pt())   # g92: reading-pane text size
        self.read.setHtml(
            "<div style='color:%s;font-size:14px'>%s</div>"
            "<div style='color:%s'>from <b style='color:%s'>%s</b>%s · to %s · %s</div>%s<hr>"
            "<div style='color:%s;white-space:pre-wrap;font-family:DejaVu Sans Mono'>%s</div>"
            % (c["accent"], _esc(str(m.get("subject"))), c["muted"], c["text"], _esc(str(m.get("from"))),
               fpline, _esc(str(m.get("to"))), _esc(_fmt_time(m.get("time"))), warn,
               c["text"], _md_body(str(m.get("body")))))

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

    def make_todo(self):
        """g85 Mail → To-Do: turn the selected message into a tracked TernDO task. Appends via the
        merge-safe board helper (TernDO folds external appends in, so this never clobbers the list)."""
        m = self._sel_msg()
        if not m:
            QMessageBox.information(self, "Make To-Do", "Select a message first.")
            return
        subject = str(m.get("subject") or "(no subject)").strip()
        frm, when = str(m.get("from") or "?"), _fmt_time(m.get("time"))
        snippet = " ".join(str(m.get("body") or "").split())[:200]
        default = subject[3:].strip() if subject.lower().startswith("re:") else subject
        title, ok = QInputDialog.getText(self, "Make To-Do", "Task title:",
                                         QLineEdit.EchoMode.Normal, default)
        if not ok or not title.strip():
            return
        notes = "From %s · %s%s" % (frm, when, ("\n" + snippet) if snippet else "")
        try:
            sys.path.insert(0, os.path.join(REPO, "tools"))
            from terndo_board import add_task
            tid = add_task(title.strip(), notes=notes, area="mail",
                           origin="from mail: %s" % subject[:60])
        except Exception as e:
            QMessageBox.warning(self, "Make To-Do", "Couldn't add the task:\n%s" % e)
            return
        QMessageBox.information(self, "Added to TernDO", "Task %s created:\n%s" % (tid, title.strip()))

    def trust_sender(self):
        """H3: confirm a sender's fingerprint out of band, then pin it so the warning clears."""
        if not hasattr(self.agent, "pin"):
            QMessageBox.information(self, "Trust sender", "Only available on the hermetic mailbox.")
            return
        m = self._sel_msg()
        if not m:
            QMessageBox.information(self, "Trust sender", "Select a message first.")
            return
        if m.get("verified") or m.get("sent") or m.get("legacy"):
            QMessageBox.information(self, "Trust sender",
                                    "This sender is already verified (or it's your own / ported mail).")
            return
        who, aid, fp = str(m.get("from")), m.get("from_aid"), str(m.get("fingerprint") or "")
        if not aid:
            QMessageBox.warning(self, "Trust sender", "No key to pin for this message.")
            return
        r = QMessageBox.question(
            self, "Confirm this fingerprint",
            "Pin \"%s\" to this key?\n\n    fingerprint:   %s\n\n"
            "Only confirm if %s gave you THIS EXACT fingerprint through a channel you already "
            "trust — a chat, a call, on paper — NOT through the mail itself." % (who, fp, who),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel)
        if r != QMessageBox.StandardButton.Yes:
            return
        try:
            self.agent.pin(who, aid)
        except Exception as e:
            QMessageBox.warning(self, "Trust sender", "Couldn't pin: %s" % e)
            return
        QMessageBox.information(self, "Trusted", "%s is now pinned and verified." % who)
        self._reload()

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
        body = d.body.document().toMarkdown().strip()         # WYSIWYG -> clean markdown on the wire
        if getattr(d, "_save_draft", False):
            self._write_draft(to_text, subject, body)
            self._select_box("Drafts")
            return
        if signature():                                       # g94: signature on sent mail (not drafts)
            body = body + "\n\n-- \n" + signature()
        if isinstance(to_data, str) and to_data.startswith("list:"):
            lname = to_data[5:]
            targets = resolve_list(lname, d.contacts)
            subj_out = "[%s] %s" % (lname, subject)
            if not targets:
                QMessageBox.warning(self, "Empty list", "No reachable members on the '%s' list." % lname)
                return
        else:
            targets, subj_out = [to_data], subject

        if hasattr(self.agent, "send_group"):             # hermetic: ONE seal to all, after confirming
            names = self._names_for(targets, d.contacts)
            if seal_confirm() and not self._confirm_seal(names):   # g96: confirm is toggleable
                return
            res = self.agent.send_group(from_account=self.account, to_contacts=targets,
                                        subject=subj_out, body=body)
            sealed = ", ".join(res.get("recipients", names)) if isinstance(res, dict) else ", ".join(names)
            QMessageBox.information(self, "Sealed & sent",
                                    "Sealed so ONLY these can ever open it:\n%s" % sealed)
        else:                                             # stub / legacy agent: per-recipient
            for h in targets:
                self.agent.send(from_account=self.account, to_contact=h, subject=subj_out, body=body)
            QMessageBox.information(self, "Sent", "Delivered to %d recipient%s."
                                    % (len(targets), "" if len(targets) == 1 else "s"))
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
    # L2 (CF5 re-audit): escape quotes too, so a crafted URL can't add attributes inside a link
    return ((s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#39;"))


def _md_body(text):
    """Render the common markdown the compose helpers emit — **bold**, *italic*, `code`,
    # headings, [links](url), bare URLs, - bullets — into inline HTML, WITHOUT touching line
    breaks, alignment, or `---` rules (those stay verbatim; the reading pane keeps
    white-space:pre-wrap). Deliberately NOT a full markdown parser: it must never mangle a
    plain-text letter (a `---` separator, an aligned column, a stray `*`), only light up
    real markup. Proven on real mail shapes (g62)."""
    c = theme_colors()                                        # g91: markdown colours follow the theme
    code, head, link = c["border"], c["accent"], c["link"]
    t = _esc(text)
    t = re.sub(r'`([^`\n]+)`', r"<code style='background:%s;padding:0 3px;border-radius:3px'>\1</code>" % code, t)
    t = re.sub(r'(?m)^(\s{0,3})###\s+(.+)$', r"\1<b style='color:%s'>\2</b>" % head, t)
    t = re.sub(r'(?m)^(\s{0,3})##\s+(.+)$', r"\1<b style='color:%s;font-size:15px'>\2</b>" % head, t)
    t = re.sub(r'(?m)^(\s{0,3})#\s+(.+)$', r"\1<b style='color:%s;font-size:17px'>\2</b>" % head, t)
    t = re.sub(r'\*\*(\S(?:.*?\S)?)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<!\w)\*(?!\s)(.+?)(?<!\s)\*(?!\w)', r'<i>\1</i>', t)
    t = re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)', r"<a href='\2' style='color:%s'>\1</a>" % link, t)
    # bare URLs — but NOT ones already inside an href (exclude a preceding ' " > = /)
    t = re.sub(r"(?<![\"'>=/])(https?://[^\s<]+)", r"<a href='\1' style='color:%s'>\1</a>" % link, t)
    t = re.sub(r'(?m)^(\s*)[-*]\s+', r'\1• ', t)
    return t


def _epoch(t):
    """Best-effort unix epoch for SORTING. An int stays an int; a known stamp string is parsed;
    anything undated -> 0 (sinks to the bottom). This is why the date column sorts chronologically
    no matter which display format the user picks."""
    if isinstance(t, (int, float)):
        return int(t)
    s = re.sub(r"\s+[A-Z]{2,5}$", "", str(t or "").strip())   # drop a trailing " ACST"/" ACDT"
    if s.isdigit():
        return int(s)
    for f in ("%H:%M %d/%m/%Y", "%d/%m/%Y %H:%M", "%d-%m-%Y %H:%M",
              "%Y-%m-%d %H:%M", "%Y-%m-%d-%H%M", "%d %b %Y %H:%M", "%m/%d/%Y %I:%M %p"):
        try:
            return int(datetime.datetime.strptime(s, f).timestamp())
        except ValueError:
            pass
    return 0


def _fmt_time(t):
    """Human date/time in the user's chosen format — used by both the table and the reading pane."""
    e = _epoch(t)
    return datetime.datetime.fromtimestamp(e).strftime(date_fmt()) if e else ""


_table_time = _fmt_time                                        # same display; the sort key is the epoch


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


# ── Appearance (g91): curated themes + per-element custom colours via Qt's native picker ──
THEMES = {
    "TernOO Dark":   dict(bg="#1a1f2b", surface="#15151f", text="#e6e6ec", muted="#9696a5",
                          accent="#3fd08f", sel="#2e466e", border="#3a3a52", link="#79b8ff"),
    "Paper (Light)": dict(bg="#f3f3ee", surface="#ffffff", text="#20232a", muted="#6b6f7a",
                          accent="#1f9d6b", sel="#d2e4ff", border="#d4d4dd", link="#1a66cc"),
    "Midnight":      dict(bg="#0d1017", surface="#151a24", text="#dbe2ee", muted="#7a8498",
                          accent="#6ea8fe", sel="#213a5c", border="#283040", link="#8fb8ff"),
    "Dusk":          dict(bg="#272230", surface="#322a3b", text="#ece6ef", muted="#a596aa",
                          accent="#e2a862", sel="#463a52", border="#463c52", link="#e2a862"),
    "Solar":         dict(bg="#002b36", surface="#073642", text="#eee8d5", muted="#93a1a1",
                          accent="#2aa198", sel="#0a4a56", border="#0f4b58", link="#268bd2"),
    "High Contrast": dict(bg="#000000", surface="#0b0b0b", text="#ffffff", muted="#c8c8c8",
                          accent="#ffd400", sel="#004a99", border="#555555", link="#66ccff"),
}
DEFAULT_THEME = "TernOO Dark"
COLOR_KEYS = [("Background", "bg"), ("Text", "text"), ("Accent", "accent"), ("Links", "link")]


def theme_colors():
    """Active palette: the chosen preset, with any per-element custom overrides on top."""
    s = load_settings()
    c = dict(THEMES.get(s.get("theme_name", DEFAULT_THEME), THEMES[DEFAULT_THEME]))
    c.update(s.get("theme_custom", {}) or {})
    return c


def build_qss(c):
    """A full flat/modern stylesheet from the active palette, with a subtle accent hover."""
    return ("QWidget{background:%(bg)s;color:%(text)s;}"
            "QListWidget,QTextEdit,QLineEdit,QComboBox,QTableWidget,QTreeWidget"
            "{background:%(surface)s;border:1px solid %(border)s;border-radius:4px;}"
            "QListWidget::item:selected,QTableWidget::item:selected,QTreeWidget::item:selected"
            "{background:%(sel)s;color:%(text)s;}"
            "QHeaderView::section{background:%(bg)s;color:%(muted)s;border:none;"
            "border-bottom:1px solid %(border)s;padding:4px;}"
            "QPushButton{background:%(sel)s;border:1px solid %(accent)s;border-radius:5px;padding:4px 12px;}"
            "QPushButton:hover{background:%(accent)s;color:%(bg)s;}"
            "QPushButton:pressed{background:%(border)s;}"
            "QMenuBar{background:%(bg)s;} QMenu{background:%(surface)s;border:1px solid %(border)s;}"
            "QMenu::item:selected,QMenuBar::item:selected{background:%(sel)s;}"
            "QScrollBar:vertical{background:%(bg)s;width:11px;margin:0;}"
            "QScrollBar::handle:vertical{background:%(border)s;border-radius:5px;min-height:24px;}"
            "QScrollBar::add-line,QScrollBar::sub-line{height:0;}" % c)


def apply_theme(app):
    app.setStyleSheet(build_qss(theme_colors()))


HERMETIC_KEY = os.environ.get("TERNOO_KEY", os.path.expanduser("~/.config/ternoo/keys/seat.key"))
HERMETIC_WIRE = os.environ.get("TERNOO_WIRE", os.path.expanduser("~/.local/state/ternoo/wire"))


def _hermetic_agent():
    """Load THIS seat's keyholder (passphrase-unlocked if wrapped) and point Tmail at the sealed
    wire. The backend seals every outgoing letter and opens only what this key can — there is no
    admin, no shared keystore, no plaintext. This is the real mail system (CF5 spec §11)."""
    sys.path.insert(0, os.path.join(REPO, "tools"))
    from release_manifest import verify as _verify_release   # M3: don't unlock a key for untrusted code
    ok, detail = _verify_release()
    if not ok:
        QMessageBox.critical(None, "Mail code not trusted",
                             "The mail code does not match the release you signed:\n\n%s\n\n"
                             "Refusing to unlock your key. Review the change and re-sign "
                             "(python3 tools/release_manifest.py sign), or restore the signed version."
                             % detail)
        sys.exit(1)
    from keyholder import Keyholder
    from hermetic_mailbox import HermeticMailbox
    try:
        kh = Keyholder.load(HERMETIC_KEY)                 # unwrapped key (cloud/other seats)
    except Exception:
        pw, ok = QInputDialog.getText(None, "Unlock mailbox",
                                      "Passphrase for your hermetic key:",
                                      QLineEdit.EchoMode.Password)
        if not ok:
            sys.exit(0)
        kh = Keyholder.load(HERMETIC_KEY, passphrase=pw)  # captain's passphrase-wrapped key (D3)
    return HermeticMailbox(kh, HERMETIC_WIRE)


def make_agent():
    """Backend selection, most-secure first:
      1. HERMETIC — this seat's sealed mailbox, when its key file exists (the real system).
      2. the old TernID agent over IPC (TERNID_AGENT_SOCK) — legacy, being retired.
      3. the inert in-process git-POBOX stub — demo only."""
    if os.path.exists(HERMETIC_KEY):
        try:
            return _hermetic_agent()
        except SystemExit:
            raise
        except Exception as e:
            QMessageBox.critical(None, "Mailbox locked",
                                 "Couldn't unlock the hermetic mailbox:\n%s" % e)
            sys.exit(1)
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
    apply_theme(app)
    w = MailApp(make_agent())
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
