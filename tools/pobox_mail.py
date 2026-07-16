#!/usr/bin/env python3
"""pobox_mail — the crew mailbox as a little desktop app (pure Tk, no deps).

One window: folders pane (Inbox / Drafts / Outbox / Sent), message list,
reader, and a composer. The box is the single base: the shared mail files in
private/POBOX/ ARE the Inbox; Drafts/Outbox/Sent are local trays inside it
(untracked — never committed). Sending is still save=send: anything that
lands in Outbox is stamped, convention-named, committed+pushed (= delivery),
archived to Sent and confirmed by the watcher's "POBOX ✉ SENT" notification.

Composer extras: right-click edit menu (undo/cut/copy/paste/select-all) and
live spellcheck — misspellings tag red, right-click one for suggestions.
Backend: pyenchant (en_AU preferred) or aspell, whichever the system has;
silently absent if neither is installed.

Launcher: "POBOX Mail.desktop" in the box root (tools/pobox-mail.desktop).
"""
import datetime
import os
import re
import shutil
import subprocess
import tkinter as tk
from tkinter import messagebox

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


def list_mail(tray):
    d = tray_path(tray)
    try:
        names = [n for n in os.listdir(d)
                 if n.endswith(".md") and os.path.isfile(os.path.join(d, n))]
    except FileNotFoundError:
        os.makedirs(d, exist_ok=True)
        return []
    dated = sorted([n for n in names if n[:1].isdigit()], reverse=True)
    other = sorted(n for n in names if not n[:1].isdigit())
    return dated + other


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


# ---- shared right-click edit menu ------------------------------------------
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

        self.body = tk.Text(self, wrap="word", font=("monospace", 11), undo=True)
        self.body.pack(side="top", fill="both", expand=True, padx=10, pady=(4, 0))
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
    def __init__(self):
        super().__init__()
        self.title("POBOX Mail")
        self.geometry("1020x620")
        self.minsize(700, 420)

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
                               text="Inbox = the shared box; Outbox = save-to-send")
        self.status.pack(side="bottom", fill="x", padx=8, pady=(2, 6))

        panes = tk.PanedWindow(self, sashrelief="raised")
        panes.pack(side="top", fill="both", expand=True, padx=8)
        self.folders = tk.Listbox(panes, width=16, exportselection=False,
                                  font=("sans", 11))
        panes.add(self.folders)
        right = tk.PanedWindow(panes, orient="vertical", sashrelief="raised")
        panes.add(right)
        self.msgs = tk.Listbox(right, exportselection=False, font=("monospace", 10))
        right.add(self.msgs, height=220)
        self.reader = tk.Text(right, wrap="word", font=("monospace", 10),
                              state="disabled", bg="#fdfdfa")
        right.add(self.reader)
        attach_edit_menu(self.reader, readonly=True)

        self.folders.bind("<<ListboxSelect>>", lambda e: self.load_folder())
        self.msgs.bind("<<ListboxSelect>>", lambda e: self.load_message())
        self.current = "Inbox"
        self.refresh()
        self.folders.selection_set(0)
        self.after(4000, self._tick)

    # ---- data ---------------------------------------------------------------
    def set_status(self, text):
        self.status.config(text=text)

    def refresh(self):
        sel = self.folders.curselection()
        self.folders.delete(0, "end")
        for t in TRAYS:
            self.folders.insert("end", f"{t}  ({len(list_mail(t))})")
        if sel:
            self.folders.selection_set(sel[0])
        self.load_folder(keep=True)

    def load_folder(self, keep=False):
        sel = self.folders.curselection()
        if sel:
            self.current = TRAYS[sel[0]]
        prev = self.selected_name()
        self.msgs.delete(0, "end")
        for n in list_mail(self.current):
            self.msgs.insert("end", n)
        if keep and prev:
            names = self.msgs.get(0, "end")
            if prev in names:
                self.msgs.selection_set(names.index(prev))

    def selected_name(self):
        sel = self.msgs.curselection()
        return self.msgs.get(sel[0]) if sel else None

    def selected_path(self):
        n = self.selected_name()
        return os.path.join(tray_path(self.current), n) if n else None

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

    def _tick(self):
        self.refresh()
        self.after(4000, self._tick)

    # ---- actions --------------------------------------------------------------
    def send_draft(self):
        if self.current != "Drafts":
            self.set_status("Send draft: pick a mail in the Drafts folder first")
            return
        p = self.selected_path()
        if not p:
            self.set_status("Send draft: select a draft first")
            return
        os.makedirs(tray_path("Outbox"), exist_ok=True)
        shutil.move(p, os.path.join(tray_path("Outbox"), os.path.basename(p)))
        self.set_status(f"✉ {os.path.basename(p)} handed to the watcher — "
                        "the SENT notification will confirm")
        self.refresh()

    def delete_draft(self):
        if self.current not in ("Drafts", "Outbox"):
            self.set_status("Delete works in Drafts/Outbox only — box mail is ledger")
            return
        p = self.selected_path()
        if not p:
            return
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
        frm = header(text, "From").split("(")[0].strip() or "crew"
        sub = header(text, "Re") or os.path.basename(p)
        Composer(self, to=frm, subject=f"re: {sub}")


if __name__ == "__main__":
    os.makedirs(BOX, exist_ok=True)
    for t in TRAYS[1:]:
        os.makedirs(tray_path(t), exist_ok=True)
    MailApp().mainloop()
