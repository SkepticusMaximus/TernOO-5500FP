#!/usr/bin/env python3
"""pobox_mail — the crew mailbox as a little desktop app (pure Tk, no deps).

One window: a tray/contacts tree on the left (Inbox / Drafts / Outbox / Sent
plus an address book harvested from the mail itself), a sortable message
table (Time | From | To | Subject — click a heading to sort), a reader, and
a composer with live en_AU spellcheck. Everything scrolls.

The box is the single base: the shared mail files in private/POBOX/ ARE the
Inbox; Drafts/Outbox/Sent are local trays inside it (untracked). Sending is
save=send: anything landing in Outbox is stamped, convention-named,
committed+pushed (= delivery) by the outbox watcher, archived to Sent, and
confirmed with the "POBOX ✉ SENT" notification.

Launcher: "POBOX Mail.desktop" in the box root (tools/pobox-mail.desktop).
"""
import datetime
import os
import re
import shutil
import subprocess
import tkinter as tk
from tkinter import messagebox, ttk

try:
    from zoneinfo import ZoneInfo
    ADL = ZoneInfo("Australia/Adelaide")
except Exception:  # pragma: no cover
    ADL = None

BOX = os.path.expanduser("~/dev/SkepticusMaximus/TernOO-5500FP/private/POBOX")
TRAYS = ["Inbox", "Drafts", "Outbox", "Sent"]


def tray_path(name):
    return BOX if name == "Inbox" else os.path.join(BOX, name)


def now():
    return datetime.datetime.now(ADL) if ADL else datetime.datetime.now().astimezone()


def slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip()).strip("-").lower()
    return s[:60] or "mail"


def header(text, key):
    m = re.search(rf"^{key}:\s*(.+)$", text, re.M | re.I)
    return m.group(1).strip() if m else ""


def clean_name(raw):
    """'CAI (chat seat, docs/foundations)' -> 'CAI'"""
    return re.sub(r"\s*\(.*?\)", "", raw).strip()


def list_mail(tray):
    d = tray_path(tray)
    try:
        names = [n for n in os.listdir(d)
                 if n.endswith(".md") and os.path.isfile(os.path.join(d, n))]
    except FileNotFoundError:
        os.makedirs(d, exist_ok=True)
        return []

    def key(n):
        m = re.match(r"(\d{4}-\d{2}-\d{2})-(\d{4})?", n)
        return (m.group(1), m.group(2) or "0000", n) if m else ("", "", n)
    dated = sorted([n for n in names if n[:1].isdigit()], key=key, reverse=True)
    other = sorted(n for n in names if not n[:1].isdigit())
    return dated + other


# ---- mail metadata (cached by mtime) ---------------------------------------
_meta_cache = {}


def mail_meta(tray, name):
    path = os.path.join(tray_path(tray), name)
    try:
        mtime = os.stat(path).st_mtime
    except OSError:
        return None
    hit = _meta_cache.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        with open(path) as f:
            head = f.read(4096)
    except OSError:
        head = ""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:-(\d{4}))?", name)
    if m:
        sort_time = f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4) or '0000'}"
        disp = f"{m.group(3)}/{m.group(2)} " + \
               (f"{m.group(4)[:2]}:{m.group(4)[2:]}" if m.group(4) else "--:--")
    else:
        sort_time, disp = "0000-00-00 0000", "--"
    frm = clean_name(header(head, "From")) or "?"
    to = ", ".join(clean_name(t) for t in
                   re.split(r"[,;]", header(head, "To")) if t.strip()) or "?"
    sub = header(head, "Re") or os.path.splitext(name)[0]
    meta = {"tray": tray, "name": name, "path": path, "sort_time": sort_time,
            "time": disp, "from": frm, "to": to, "subject": sub}
    _meta_cache[path] = (mtime, meta)
    return meta


def all_contacts():
    names = set()
    for tray in TRAYS:
        for n in list_mail(tray):
            meta = mail_meta(tray, n)
            if not meta:
                continue
            if meta["from"] != "?":
                names.add(meta["from"])
            for t in meta["to"].split(","):
                t = t.strip()
                if t and t != "?":
                    names.add(t)
    return sorted(names)


# ---- spellcheck backend (drop-in: pyenchant/en_AU, else aspell, else off) --
class Spell:
    def __init__(self):
        self.mode = None
        self.d = None
        try:
            import enchant
            for tag in ("en_AU", "en_GB", "en_US"):
                try:
                    self.d = enchant.Dict(tag)
                    break
                except Exception:
                    pass
            if self.d is None:
                self.d = enchant.Dict()
            self.mode = "enchant"
        except Exception:
            if shutil.which("aspell"):
                self.mode = "aspell"

    def bad_words(self, text):
        words = {w for w in re.findall(r"[A-Za-z']{2,}", text)
                 if not w.isupper()}          # skip acronyms: CC, CAI, POBOX...
        if self.mode == "enchant":
            return {w for w in words if not self.d.check(w)}
        if self.mode == "aspell":
            r = subprocess.run(["aspell", "list"], input=text,
                               capture_output=True, text=True)
            return set(r.stdout.split()) & words
        return set()

    def suggest(self, word):
        if self.mode == "enchant":
            return self.d.suggest(word)[:6]
        if self.mode == "aspell":
            r = subprocess.run(["aspell", "-a"], input=word,
                               capture_output=True, text=True)
            for ln in r.stdout.splitlines():
                if ln.startswith("&") and ":" in ln:
                    return [s.strip() for s in ln.split(":", 1)[1].split(",")][:6]
        return []


SPELL = Spell()


# ---- shared widgets ---------------------------------------------------------
def _evt(w, seq):
    try:
        w.event_generate(seq)
    except tk.TclError:
        pass


def select_all(w):
    if isinstance(w, tk.Text):
        w.tag_add("sel", "1.0", "end-1c")
    else:
        w.select_range(0, "end")


def attach_edit_menu(w, readonly=False, spell_hook=None):
    def show(e):
        m = tk.Menu(w, tearoff=0)
        if spell_hook:
            spell_hook(e, m)
        if not readonly:
            m.add_command(label="Undo", command=lambda: _evt(w, "<<Undo>>"))
            m.add_command(label="Redo", command=lambda: _evt(w, "<<Redo>>"))
            m.add_separator()
            m.add_command(label="Cut", command=lambda: _evt(w, "<<Cut>>"))
        m.add_command(label="Copy", command=lambda: _evt(w, "<<Copy>>"))
        if not readonly:
            m.add_command(label="Paste", command=lambda: _evt(w, "<<Paste>>"))
        m.add_separator()
        m.add_command(label="Select all", command=lambda: select_all(w))
        m.tk_popup(e.x_root, e.y_root)
        return "break"
    w.bind("<Button-3>", show)
    w.bind("<Control-a>", lambda e: (select_all(w), "break")[1])


def scrolled(parent, widget_cls, **kw):
    """widget + vertical scrollbar in a frame; returns (frame, widget)."""
    frame = tk.Frame(parent)
    w = widget_cls(frame, **kw)
    sb = ttk.Scrollbar(frame, orient="vertical", command=w.yview)
    w.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    w.pack(side="left", fill="both", expand=True)
    return frame, w


class Composer(tk.Toplevel):
    def __init__(self, app, to="", subject=""):
        super().__init__(app)
        self.app = app
        self.title("New POBOX mail")
        self.geometry("760x560")
        self.minsize(520, 360)
        self._spell_job = None

        top = tk.Frame(self)
        top.pack(side="top", fill="x", padx=10, pady=(10, 4))
        self.vars = {}
        for i, (label, default) in enumerate(
                [("From", "Stevo"), ("To", to), ("Cc", ""), ("Subject", subject)]):
            tk.Label(top, text=label + ":", anchor="e", width=8)\
                .grid(row=i, column=0, sticky="e", pady=2)
            v = tk.StringVar(value=default)
            self.vars[label] = v
            ent = tk.Entry(top, textvariable=v)
            ent.grid(row=i, column=1, sticky="ew", pady=2)
            attach_edit_menu(ent)
        tk.Label(top, text="crew: CC, CF5, CAI, Stevo, crew  (commas for several)",
                 fg="#777").grid(row=1, column=2, sticky="w", padx=8)
        top.columnconfigure(1, weight=1)

        # button bar packs BEFORE the body so the Text can never starve it
        btns = tk.Frame(self)
        btns.pack(side="bottom", fill="x", padx=10, pady=8)
        tk.Button(btns, text="Send  ✉", width=10, command=self.send).pack(side="right")
        tk.Button(btns, text="Save draft", command=self.save_draft)\
            .pack(side="right", padx=8)
        self.saved = tk.Label(btns, text="", fg="#2a7")
        self.saved.pack(side="left")

        body_frame, self.body = scrolled(self, tk.Text, wrap="word",
                                         font=("monospace", 11), undo=True)
        body_frame.pack(side="top", fill="both", expand=True, padx=10, pady=(4, 0))
        self.body.tag_config("miss", foreground="#b00000", underline=1)
        attach_edit_menu(self.body, spell_hook=self._spell_menu)
        if SPELL.mode:
            self.body.bind("<KeyRelease>", self._schedule_spell)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        top.grid_slaves(row=1, column=1)[0].focus_set()

    # ---- spellcheck --------------------------------------------------------
    def _schedule_spell(self, _e=None):
        if self._spell_job:
            self.after_cancel(self._spell_job)
        self._spell_job = self.after(900, self._spellcheck)

    def _spellcheck(self):
        self._spell_job = None
        text = self.body.get("1.0", "end-1c")
        self.body.tag_remove("miss", "1.0", "end")
        for w in list(SPELL.bad_words(text))[:200]:
            idx = "1.0"
            while True:
                idx = self.body.search(w, idx, stopindex="end")
                if not idx:
                    break
                end = f"{idx}+{len(w)}c"
                before = self.body.get(f"{idx}-1c") if idx != "1.0" else ""
                after = self.body.get(end)
                if not before.isalnum() and not after.isalnum():
                    self.body.tag_add("miss", idx, end)
                idx = end

    def _spell_menu(self, e, m):
        if not SPELL.mode:
            return
        idx = self.body.index(f"@{e.x},{e.y}")
        if "miss" not in self.body.tag_names(idx):
            return
        start = self.body.index(f"{idx} wordstart")
        end = self.body.index(f"{idx} wordend")
        word = self.body.get(start, end).strip()
        if not word:
            return
        sugg = SPELL.suggest(word)
        if sugg:
            for s in sugg:
                m.add_command(label=s,
                              command=lambda s=s: self._replace(start, end, s))
        else:
            m.add_command(label=f'(no suggestions for "{word}")', state="disabled")
        m.add_separator()

    def _replace(self, start, end, s):
        self.body.delete(start, end)
        self.body.insert(start, s)
        self._spellcheck()

    # ---- mail assembly -----------------------------------------------------
    def compose_text(self, dt):
        frm = self.vars["From"].get().strip() or "Stevo"
        to = self.vars["To"].get().strip()
        cc = self.vars["Cc"].get().strip()
        sub = self.vars["Subject"].get().strip()
        head = (f"{dt.strftime('%H:%M %d/%m/%Y %Z')}\n\n"
                f"# {frm} → {to} — {sub}\n\n"
                f"From: {frm}\nTo: {to}\n")
        if cc:
            head += f"Cc: {cc}\n"
        head += f"Re: {sub}\n\n"
        return head + self.body.get("1.0", "end").rstrip() + f"\n\n— {frm}\n", frm, to, sub

    def send(self):
        if not self.vars["To"].get().strip():
            messagebox.showwarning("No addressee", "Fill in To: (e.g. CC, CF5)",
                                   parent=self)
            return
        if not self.vars["Subject"].get().strip():
            messagebox.showwarning("No subject", "Fill in Subject:", parent=self)
            return
        if not self.body.get("1.0", "end").strip() and \
                not messagebox.askyesno("Empty body", "Body is empty — send anyway?",
                                        parent=self):
            return
        dt = now()
        text, frm, to, sub = self.compose_text(dt)
        to_part = "+".join(t.strip() for t in re.split(r"[,;]", to) if t.strip())
        name = f"{dt.strftime('%Y-%m-%d-%H%M')}-{frm}-to-{to_part}-{slug(sub)}.md"
        os.makedirs(tray_path("Outbox"), exist_ok=True)
        with open(os.path.join(tray_path("Outbox"), name), "w") as f:
            f.write(text)
        self.app.set_status(f"✉ handed to the watcher: {name} — "
                            "the SENT notification will confirm delivery")
        self.app.refresh()
        self.destroy()

    def save_draft(self):
        dt = now()
        text, frm, to, sub = self.compose_text(dt)
        os.makedirs(tray_path("Drafts"), exist_ok=True)
        name = f"DRAFT-{slug(sub) if sub.strip() else 'untitled'}.md"
        with open(os.path.join(tray_path("Drafts"), name), "w") as f:
            f.write(text)
        self.saved.config(text=f"saved: Drafts/{name}  {dt.strftime('%H:%M')}")
        self.app.refresh()          # composer STAYS OPEN — keep writing

    def on_close(self):
        if self.body.get("1.0", "end").strip() or self.vars["Subject"].get().strip():
            if not messagebox.askyesno("Discard?",
                                       "Discard this mail? (Save draft keeps it)",
                                       parent=self):
                return
        self.destroy()


class MailApp(tk.Tk):
    COLS = ("time", "from", "to", "subject")
    HEADINGS = {"time": "Time", "from": "From", "to": "To", "subject": "Subject"}

    def __init__(self):
        super().__init__()
        self.title("POBOX Mail")
        self.geometry("1080x640")
        self.minsize(720, 420)
        self.view = ("tray", "Inbox")
        self.sort_col = "time"
        self.sort_desc = True

        bar = tk.Frame(self)
        bar.pack(side="top", fill="x", padx=8, pady=6)
        tk.Button(bar, text="New ✉", width=8,
                  command=lambda: Composer(self)).pack(side="left")
        tk.Button(bar, text="Reply", command=self.reply).pack(side="left", padx=6)
        tk.Button(bar, text="Send draft ▶", command=self.send_draft).pack(side="left")
        tk.Button(bar, text="Delete draft", command=self.delete_draft)\
            .pack(side="left", padx=6)
        tk.Button(bar, text="⟳", command=self.refresh).pack(side="right")

        # status bar packs BEFORE the panes so it can never be squeezed out
        self.status = tk.Label(self, anchor="w", fg="#555",
                               text="Inbox = the shared box; Outbox = save-to-send; "
                                    "click column headings to sort")
        self.status.pack(side="bottom", fill="x", padx=8, pady=(2, 6))

        panes = tk.PanedWindow(self, sashrelief="raised")
        panes.pack(side="top", fill="both", expand=True, padx=8)

        # left: trays + contacts tree (scrolled)
        lf, self.nav = scrolled(panes, ttk.Treeview, show="tree", selectmode="browse")
        self.nav.column("#0", width=185)
        panes.add(lf, width=200)
        self.nav_tray = {}
        for t in TRAYS:
            self.nav_tray[t] = self.nav.insert("", "end", iid=f"tray:{t}", text=t)
        self.nav_contacts = self.nav.insert("", "end", iid="contacts",
                                            text="Contacts", open=False)
        self.nav.selection_set("tray:Inbox")

        right = tk.PanedWindow(panes, orient="vertical", sashrelief="raised")
        panes.add(right)

        # message table (scrolled, sortable)
        mf, self.msgs = scrolled(right, ttk.Treeview, columns=self.COLS,
                                 show="headings", selectmode="browse")
        for c, w, stretch in (("time", 110, False), ("from", 100, False),
                              ("to", 110, False), ("subject", 420, True)):
            self.msgs.heading(c, command=lambda c=c: self.sort_by(c))
            self.msgs.column(c, width=w, stretch=stretch)
        self._set_headings()
        right.add(mf, height=260)

        rf, self.reader = scrolled(right, tk.Text, wrap="word",
                                   font=("monospace", 10), state="disabled",
                                   bg="#fdfdfa")
        right.add(rf)
        attach_edit_menu(self.reader, readonly=True)

        self.nav.bind("<<TreeviewSelect>>", lambda e: self.on_nav())
        self.nav.bind("<Double-1>", self.on_nav_double)
        self.msgs.bind("<<TreeviewSelect>>", lambda e: self.load_message())
        self.refresh()
        self.after(4000, self._tick)

    # ---- helpers -------------------------------------------------------------
    def set_status(self, text):
        self.status.config(text=text)

    def _set_headings(self):
        for c in self.COLS:
            label = self.HEADINGS[c]
            if c == self.sort_col:
                label += "  ▼" if self.sort_desc else "  ▲"
            self.msgs.heading(c, text=label)

    def current_metas(self):
        kind, val = self.view
        metas = []
        if kind == "tray":
            metas = [m for n in list_mail(val) if (m := mail_meta(val, n))]
        else:                                   # contact filter, whole box
            for tray in TRAYS:
                for n in list_mail(tray):
                    m = mail_meta(tray, n)
                    if not m:
                        continue
                    tos = [t.strip() for t in m["to"].split(",")]
                    if m["from"] == val or val in tos:
                        metas.append(m)
        key = {"time": lambda m: (m["sort_time"], m["name"]),
               "from": lambda m: (m["from"].lower(), m["sort_time"]),
               "to": lambda m: (m["to"].lower(), m["sort_time"]),
               "subject": lambda m: (m["subject"].lower(), m["sort_time"])}[self.sort_col]
        return sorted(metas, key=key, reverse=self.sort_desc)

    # ---- refresh cycle ---------------------------------------------------------
    def refresh(self):
        for t in TRAYS:
            self.nav.item(f"tray:{t}", text=f"{t}  ({len(list_mail(t))})")
        known = set(self.nav.get_children("contacts"))
        for c in all_contacts():
            iid = f"contact:{c}"
            if iid not in known:
                self.nav.insert("contacts", "end", iid=iid, text=c)
        self.load_rows()

    def load_rows(self):
        prev = self.selected_iid()
        self.msgs.delete(*self.msgs.get_children())
        for m in self.current_metas():
            iid = f"{m['tray']}/{m['name']}"
            self.msgs.insert("", "end", iid=iid, values=(
                m["time"], m["from"], m["to"], m["subject"]))
        if prev and self.msgs.exists(prev):
            self.msgs.selection_set(prev)

    def _tick(self):
        self.refresh()
        self.after(4000, self._tick)

    # ---- selection -------------------------------------------------------------
    def selected_iid(self):
        sel = self.msgs.selection()
        return sel[0] if sel else None

    def selected_path(self):
        iid = self.selected_iid()
        if not iid:
            return None
        tray, name = iid.split("/", 1)
        return os.path.join(tray_path(tray), name)

    def on_nav(self):
        sel = self.nav.selection()
        if not sel:
            return
        iid = sel[0]
        if iid.startswith("tray:"):
            self.view = ("tray", iid.split(":", 1)[1])
        elif iid.startswith("contact:"):
            self.view = ("contact", iid.split(":", 1)[1])
        else:
            return                       # the "Contacts" folder itself
        self.load_rows()

    def on_nav_double(self, e):
        iid = self.nav.identify_row(e.y)
        if iid.startswith("contact:"):
            Composer(self, to=iid.split(":", 1)[1])

    def sort_by(self, col):
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col, self.sort_desc = col, (col == "time")
        self._set_headings()
        self.load_rows()

    def load_message(self):
        p = self.selected_path()
        if not p:
            return
        try:
            with open(p) as f:
                text = f.read()
        except OSError as e:
            text = f"(could not read: {e})"
        self.reader.config(state="normal")
        self.reader.delete("1.0", "end")
        self.reader.insert("1.0", text)
        self.reader.config(state="disabled")

    # ---- actions ---------------------------------------------------------------
    def send_draft(self):
        iid = self.selected_iid()
        if not iid or not iid.startswith("Drafts/"):
            self.set_status("Send draft: select a mail in the Drafts tray first")
            return
        p = self.selected_path()
        os.makedirs(tray_path("Outbox"), exist_ok=True)
        shutil.move(p, os.path.join(tray_path("Outbox"), os.path.basename(p)))
        self.set_status(f"✉ {os.path.basename(p)} handed to the watcher — "
                        "the SENT notification will confirm")
        self.refresh()

    def delete_draft(self):
        iid = self.selected_iid()
        if not iid or iid.split("/", 1)[0] not in ("Drafts", "Outbox"):
            self.set_status("Delete works on Drafts/Outbox only — box mail is ledger")
            return
        p = self.selected_path()
        if messagebox.askyesno("Delete", f"Delete {os.path.basename(p)}?"):
            os.remove(p)
            self.refresh()

    def reply(self):
        p = self.selected_path()
        if not p:
            self.set_status("Reply: select a message first")
            return
        with open(p) as f:
            text = f.read()
        frm = clean_name(header(text, "From")) or "crew"
        sub = header(text, "Re") or os.path.basename(p)
        Composer(self, to=frm, subject=f"re: {sub}")


if __name__ == "__main__":
    os.makedirs(BOX, exist_ok=True)
    for t in TRAYS[1:]:
        os.makedirs(tray_path(t), exist_ok=True)
    MailApp().mainloop()
