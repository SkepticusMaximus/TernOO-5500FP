#!/usr/bin/env python3
"""pobox_new_mail — the captain's little compose window (pure Tk, no deps).

Double-click "New Mail" in ~/POBOX: a small mail-composer opens with
From / To / Cc / Subject fields and a body area. [Send] writes the stamped,
convention-named file straight into ~/POBOX/Outbox — where the outbox
watcher picks it up, commits+pushes (= delivery), archives to ~/POBOX/Sent
and fires the "POBOX ✉ SENT" notification. [Save draft] parks it in
~/POBOX/Drafts instead (drag to Outbox later to send).

The script itself never touches git — delivery is the watcher's job.
"""
import datetime
import os
import re
import tkinter as tk
from tkinter import messagebox

try:
    from zoneinfo import ZoneInfo
    ADL = ZoneInfo("Australia/Adelaide")
except Exception:  # pragma: no cover — the box runs Adelaide time anyway
    ADL = None

BASE = os.path.expanduser("~/POBOX")
OUTBOX = os.path.join(BASE, "Outbox")
DRAFTS = os.path.join(BASE, "Drafts")


def now():
    return datetime.datetime.now(ADL) if ADL else datetime.datetime.now().astimezone()


def slug(s):
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s.strip()).strip("-").lower()
    return s[:60] or "mail"


class Composer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("New POBOX mail")
        self.geometry("760x560")
        self.minsize(520, 360)

        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=(10, 4))
        self.vars = {}
        for i, (label, default) in enumerate(
                [("From", "Stevo"), ("To", ""), ("Cc", ""), ("Subject", "")]):
            tk.Label(top, text=label + ":", anchor="e", width=8)\
                .grid(row=i, column=0, sticky="e", pady=2)
            v = tk.StringVar(value=default)
            self.vars[label] = v
            tk.Entry(top, textvariable=v)\
                .grid(row=i, column=1, sticky="ew", pady=2)
        tk.Label(top, text="crew: CC, CF5, CAI, Stevo, crew  (commas for several)",
                 fg="#777").grid(row=1, column=2, sticky="w", padx=8)
        top.columnconfigure(1, weight=1)

        self.body = tk.Text(self, wrap="word", font=("monospace", 11), undo=True)
        self.body.pack(fill="both", expand=True, padx=10, pady=(4, 0))

        btns = tk.Frame(self)
        btns.pack(fill="x", padx=10, pady=8)
        tk.Button(btns, text="Send  ✉", command=self.send, width=10)\
            .pack(side="right")
        tk.Button(btns, text="Save draft", command=self.save_draft)\
            .pack(side="right", padx=8)
        tk.Label(btns, fg="#777",
                 text="Send drops it in the Outbox — the watcher posts it and "
                      "notifies; copy lands in Sent.").pack(side="left")

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        top.grid_slaves(row=1, column=1)[0].focus_set()   # cursor in To:

    # ---- mail assembly ----------------------------------------------------
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
        body = self.body.get("1.0", "end").rstrip()
        return head + body + f"\n\n— {frm}\n", frm, to, sub

    def filename(self, dt, frm, to, sub):
        to_part = "+".join(t.strip() for t in re.split(r"[,;]", to) if t.strip())
        return f"{dt.strftime('%Y-%m-%d-%H%M')}-{frm}-to-{to_part}-{slug(sub)}.md"

    # ---- buttons ----------------------------------------------------------
    def send(self):
        if not self.vars["To"].get().strip():
            messagebox.showwarning("No addressee", "Fill in To: (e.g. CC, CF5)")
            return
        if not self.vars["Subject"].get().strip():
            messagebox.showwarning("No subject", "Fill in Subject:")
            return
        if not self.body.get("1.0", "end").strip():
            if not messagebox.askyesno("Empty body", "Body is empty — send anyway?"):
                return
        dt = now()
        text, frm, to, sub = self.compose_text(dt)
        os.makedirs(OUTBOX, exist_ok=True)
        with open(os.path.join(OUTBOX, self.filename(dt, frm, to, sub)), "w") as f:
            f.write(text)
        self.destroy()      # watcher takes it from here; SENT notification follows

    def save_draft(self):
        dt = now()
        text, frm, to, sub = self.compose_text(dt)
        os.makedirs(DRAFTS, exist_ok=True)
        name = f"DRAFT-{slug(sub) if sub.strip() else 'untitled'}.md"
        with open(os.path.join(DRAFTS, name), "w") as f:
            f.write(text)
        messagebox.showinfo("Draft saved",
                            f"~/POBOX/Drafts/{name}\n\nDrag it into Outbox to send.")
        self.destroy()

    def on_close(self):
        if self.body.get("1.0", "end").strip() or self.vars["Subject"].get().strip():
            if not messagebox.askyesno("Discard?", "Discard this mail?"):
                return
        self.destroy()


if __name__ == "__main__":
    Composer().mainloop()
