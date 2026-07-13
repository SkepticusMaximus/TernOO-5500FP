"""help_tab_view — the Documentation tab (FlowCode's tenth tab).

Mounted by flowcode.py:  DocsTabView(parent_frame, C, root, set_status)

Left: a search box + a section-grouped index of every docs/help topic. Right: a
Read<->Edit surface — the embedded HelpViewer for reading, and (in edit mode) a raw
helpdown editor beside a LIVE preview, saving back through HelpTopics.save() (the one
write path in the codebase). Self-contained (the chrome matrix hides the sidebar +
Output on this tab). `tkinter` is imported inside __init__ so the module loads
headless.

Editor rulings — CF5 2026-07-13: raw + live preview (WYSIWYG is out); Read<->Edit
toggle inside this tab; warn-and-allow save with the two-tier lint law (drafts may
carry dead links; the repo sweep stays strict); [[link]] autocomplete + New topic in
v1; host-FS with the save() seam swappable; atomic + one-level-.bak safe writes; a
dirty-edit guard so a misclick never eats unsaved work.

Date: 2026-07-12/13, Adelaide
Authors: Stevo (SkepticusMaximus) + CC
"""

import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:                  # importable when FlowCode execs us
    _sys.path.insert(0, _HERE)

from help_topics import HelpTopics          # noqa: E402
from help_viewer import HelpViewer          # noqa: E402

_PREVIEW_DELAY = 250        # ms idle before the preview + lint re-parse
_WARN = "#c9a24a"           # amber for the live dead-link warning


class DocsTabView:
    def __init__(self, parent, C, root, set_status=None):
        import tkinter as tk
        self.tk = tk
        self.C, self.root = C, root
        self._status = set_status or (lambda _m: None)
        self.topics = HelpTopics()
        self._rows = []            # listbox row -> topic_id (or None for a header)
        self._mode = "read"        # "read" | "edit"
        self._current_id = None    # topic shown in read mode
        self._editing_id = None    # topic loaded in the editor
        self._dirty = False
        self._preview_job = None
        self._build(parent)
        self._load_index()

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self, parent):
        tk, C = self.tk, self.C
        mono = ("Monospace", 9)

        left = tk.Frame(parent, bg=C["bg"], width=240)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        srow = tk.Frame(left, bg=C["bg"])
        srow.pack(side="top", fill="x", padx=6, pady=6)
        tk.Label(srow, text="search", bg=C["bg"], fg=C["dim"], font=mono
                 ).pack(side="left", padx=(0, 4))
        self._search = tk.Entry(srow, bg=C["palette"], fg=C["text"],
                                insertbackground=C["text"], relief="flat", font=mono)
        self._search.pack(side="left", fill="x", expand=True)
        self._search.bind("<KeyRelease>", lambda _e: self._on_search())

        self._list = tk.Listbox(left, bg=C["bg"], fg=C["text"], font=mono,
                                relief="flat", highlightthickness=0,
                                selectbackground=C["palette"], activestyle="none")
        self._list.pack(side="top", fill="both", expand=True, padx=6, pady=(0, 6))
        self._list.bind("<<ListboxSelect>>", lambda _e: self._on_pick())

        right = tk.Frame(parent, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)

        self._toolbar = tk.Frame(right, bg=C["palette"])
        self._toolbar.pack(side="top", fill="x")

        # read surface
        self._read_pane = tk.Frame(right, bg=C["bg"])
        self._read_pane.pack(side="top", fill="both", expand=True)
        self.viewer = HelpViewer(self._read_pane, C, self.topics,
                                 on_status=self._status)

        # edit surface — built once, packed only in edit mode: raw | preview
        self._edit_pane = tk.Frame(right, bg=C["bg"])
        raw_wrap = tk.Frame(self._edit_pane, bg=C["bg"])
        raw_wrap.pack(side="left", fill="both", expand=True)
        rsb = tk.Scrollbar(raw_wrap, orient="vertical")
        rsb.pack(side="right", fill="y")
        self._raw = tk.Text(raw_wrap, bg=C["bg"], fg=C["text"], relief="flat",
                            font=mono, wrap="word", padx=8, pady=6,
                            insertbackground=C["text"], highlightthickness=0,
                            undo=True, yscrollcommand=rsb.set)
        self._raw.pack(side="left", fill="both", expand=True)
        rsb.config(command=self._raw.yview)
        self._raw.bind("<<Modified>>", self._on_raw_modified)

        tk.Frame(self._edit_pane, bg=C["dim"], width=1).pack(side="left", fill="y")

        prev_wrap = tk.Frame(self._edit_pane, bg=C["bg"])
        prev_wrap.pack(side="left", fill="both", expand=True)
        self._preview = HelpViewer(prev_wrap, C, self.topics, on_status=self._status)

        self._lint = None
        self._render_toolbar()

    # ── toolbar (mode-dependent) ────────────────────────────────────────────────
    def _tb_btn(self, text, cmd):
        b = self.tk.Button(self._toolbar, text=text, command=cmd,
                           bg=self.C["palette"], fg=self.C["text"],
                           font=("Monospace", 9), relief="flat",
                           activebackground=self.C["bg"],
                           activeforeground=self.C["text"])
        b.pack(side="left", padx=3, pady=2)
        return b

    def _render_toolbar(self):
        for w in self._toolbar.winfo_children():
            w.destroy()
        if self._mode == "read":
            self._tb_btn("✎  Edit", self._enter_edit)
            self._tb_btn("＋  New topic", self._new_topic)
            self._lint = None
        else:
            self._tb_btn("👁  Read", self._leave_edit)
            self._tb_btn("Save", self._save)
            self._tb_btn("Revert", self._revert)
            self._tb_btn("🔗  Insert link", self._insert_link)
            self._tb_btn("＋  New topic", self._new_topic)
            self._lint = self.tk.Label(self._toolbar, text="", bg=self.C["palette"],
                                       fg=self.C["dim"], font=("Monospace", 9))
            self._lint.pack(side="right", padx=8)

    # ── index + search ──────────────────────────────────────────────────────────
    def _set_rows(self, rows):
        """rows = [(display_text, topic_id_or_None)]."""
        self._list.delete(0, "end")
        self._rows = []
        for text, tid in rows:
            self._list.insert("end", text)
            self._rows.append(tid)

    def _load_index(self):
        rows, section = [], None
        for tid, title, sec in self.topics.index():
            if sec != section:
                rows.append((sec, None))                     # section header
                section = sec
            rows.append(("   " + title, tid))
        if not rows:
            rows = [("(no topics yet)", None)]
        self._set_rows(rows)
        if self._current_id is None:                         # first load only
            first = next((tid for _t, tid in rows if tid), None)
            if first:
                self._current_id = first
                self.viewer.show(first)

    def _on_search(self):
        q = self._search.get().strip()
        if not q:
            self._load_index()
            return
        hits = self.topics.search(q)
        rows = [(f"{len(hits)} result(s)", None)] + \
               [("   " + title, tid) for tid, title in hits]
        self._set_rows(rows if hits else [("no matches", None)])

    def _on_pick(self):
        sel = self._list.curselection()
        if not sel:
            return
        tid = self._rows[sel[0]]
        if not tid:
            return
        if self._mode == "edit":
            if tid == self._editing_id:
                return
            if not self._guard_dirty():                      # topic-switch guard
                return
            self._load_into_editor(tid)
        else:
            self._current_id = tid
            self.viewer.show(tid)

    # ── edit mode ───────────────────────────────────────────────────────────────
    def _load_into_editor(self, tid):
        raw = self.topics.raw(tid) if self.topics.exists(tid) else ""
        self._editing_id = tid
        self._current_id = tid
        self._raw.delete("1.0", "end")
        self._raw.insert("1.0", raw)
        self._raw.edit_modified(False)                       # the load isn't a dirty edit
        self._dirty = False
        self._do_preview()
        self._status(f"Editing: {tid}")

    def _enter_edit(self):
        if not self._current_id:
            self._status("Pick a topic to edit first.")
            return
        self._mode = "edit"
        self._read_pane.pack_forget()
        self._edit_pane.pack(side="top", fill="both", expand=True)
        self._render_toolbar()
        self._load_into_editor(self._current_id)

    def _leave_edit(self):
        if not self._guard_dirty():                          # toggle guard
            return
        self._mode = "read"
        self._edit_pane.pack_forget()
        self._read_pane.pack(side="top", fill="both", expand=True)
        self._render_toolbar()
        if self._editing_id:
            self.viewer.show(self._editing_id)               # reflect saved state
        self._status("Reading.")

    def _on_raw_modified(self, _e=None):
        if not self._raw.edit_modified():
            return
        self._raw.edit_modified(False)                       # re-arm the event
        self._dirty = True
        self._schedule_preview()

    def _schedule_preview(self):
        if self._preview_job is not None:
            try:
                self.root.after_cancel(self._preview_job)
            except Exception:
                pass
        self._preview_job = self.root.after(_PREVIEW_DELAY, self._do_preview)

    def _do_preview(self):
        self._preview_job = None
        raw = self._raw.get("1.0", "end-1c")
        self._preview.preview(raw)
        self._update_lint(raw)

    def _update_lint(self, raw=None):
        if self._lint is None:
            return
        if raw is None:
            raw = self._raw.get("1.0", "end-1c")
        missing = self.topics.missing_targets(raw)
        if missing:
            self._lint.config(text="⚠ dead links: " + ", ".join(missing), fg=_WARN)
        else:
            self._lint.config(text="✓ links resolve", fg=self.C["dim"])

    def _save(self):
        """Warn-and-allow (CF5 two-tier law): saves even with dead links; the repo
        sweep stays strict. Returns True on success (used by the dirty guard)."""
        if self._mode != "edit" or not self._editing_id:
            return True
        raw = self._raw.get("1.0", "end-1c")
        try:
            self.topics.save(self._editing_id, raw)
        except Exception as e:                               # noqa: BLE001
            self._status(f"Save failed: {e}")
            return False
        self._raw.edit_modified(False)
        self._dirty = False
        self._load_index()                                   # title/section may change
        missing = self.topics.missing_targets(raw)
        note = f"  (saved with {len(missing)} dead link(s))" if missing else ""
        self._status(f"Saved: {self._editing_id}{note}")
        return True

    def _revert(self):
        raw = (self.topics.raw(self._editing_id)
               if self._editing_id and self.topics.exists(self._editing_id) else "")
        self._raw.delete("1.0", "end")
        self._raw.insert("1.0", raw)
        self._raw.edit_modified(False)
        self._dirty = False
        self._do_preview()
        self._status("Reverted to last saved.")

    def _new_topic(self):
        from tkinter import simpledialog, messagebox
        if self._mode == "edit" and not self._guard_dirty():
            return
        tid = simpledialog.askstring("New topic",
                                     "Topic id (lowercase letters, digits, hyphens):",
                                     parent=self.root)
        if not tid:
            return
        tid = tid.strip()
        if not self.topics.is_valid_id(tid):
            messagebox.showerror("New topic", f"Invalid id: {tid!r}\n"
                                 "Use lowercase letters, digits and hyphens "
                                 "(e.g. keep-the-original).")
            return
        if self.topics.exists(tid):
            messagebox.showerror("New topic", f"'{tid}' already exists.")
            return
        section = (simpledialog.askstring("New topic", "Section (e.g. The tabs):",
                                          parent=self.root) or "Other").strip()
        title = tid.replace("-", " ")
        title = title[:1].upper() + title[1:]
        skeleton = f"{title}\nsection: {section}\n\n# {title}\n\n"
        self.topics.save(tid, skeleton)
        self._load_index()
        if self._mode != "edit":                             # jump into editing it
            self._mode = "edit"
            self._read_pane.pack_forget()
            self._edit_pane.pack(side="top", fill="both", expand=True)
            self._render_toolbar()
        self._load_into_editor(tid)
        self._status(f"Created: {tid}")

    # ── [[link]] insert helper (autocomplete over EXISTING ids only) ────────────
    def _insert_link_at_cursor(self, tid):
        """Insert [[id|Title]] at the cursor. Only called with an id that exists,
        so the inserted link is always live (never a fresh dead link)."""
        t = self.topics.topic(tid)
        label = t["title"] if t else tid
        self._raw.insert("insert", f"[[{tid}|{label}]]")
        self._dirty = True
        self._schedule_preview()

    def _insert_link(self):
        tk, C = self.tk, self.C
        mono = ("Monospace", 9)
        ids = self.topics.ids()                              # existing ids ONLY
        if not ids:
            self._status("No topics to link to yet.")
            return
        win = tk.Toplevel(self.root)
        win.title("Insert link")
        win.configure(bg=C["bg"])
        win.geometry("320x380")
        win.transient(self.root)
        filt = tk.Entry(win, bg=C["palette"], fg=C["text"], insertbackground=C["text"],
                        relief="flat", font=mono)
        filt.pack(side="top", fill="x", padx=8, pady=8)
        lb = tk.Listbox(win, bg=C["bg"], fg=C["text"], font=mono, relief="flat",
                        highlightthickness=0, selectbackground=C["palette"],
                        activestyle="none")
        lb.pack(side="top", fill="both", expand=True, padx=8)

        def refill(*_):
            q = filt.get().strip().lower()
            lb.delete(0, "end")
            for tid in ids:
                if q in tid.lower():
                    lb.insert("end", tid)
        refill()
        filt.bind("<KeyRelease>", refill)

        def do_insert(*_):
            sel = lb.curselection()
            tid = lb.get(sel[0]) if sel else (lb.get(0) if lb.size() else None)
            if tid:
                self._insert_link_at_cursor(tid)
            win.destroy()
            self._raw.focus_set()

        lb.bind("<Double-Button-1>", do_insert)
        filt.bind("<Return>", do_insert)
        row = tk.Frame(win, bg=C["bg"])
        row.pack(side="bottom", fill="x", pady=8)
        tk.Button(row, text="Insert", command=do_insert, bg=C["palette"], fg=C["text"],
                  relief="flat", font=mono, activebackground=C["bg"]
                  ).pack(side="right", padx=8)
        tk.Button(row, text="Cancel", command=win.destroy, bg=C["palette"],
                  fg=C["text"], relief="flat", font=mono, activebackground=C["bg"]
                  ).pack(side="right")
        filt.focus_set()

    # ── dirty guard (used on toggle, topic switch, and new-topic) ───────────────
    def _guard_dirty(self):
        """True = OK to proceed. If there are unsaved edits, prompt save/discard/
        cancel so a misclick never eats work (CF5 ruling). Cancel returns False."""
        if not self._dirty:
            return True
        from tkinter import messagebox
        ans = messagebox.askyesnocancel(
            "Unsaved changes",
            f"Save changes to '{self._editing_id}' before leaving it?")
        if ans is None:
            return False                                     # cancel — stay put
        if ans:
            return self._save()                              # proceed only if saved
        self._dirty = False                                  # discard
        return True

    def has_unsaved(self):
        """For flowcode's tab-change guard (wired separately)."""
        return self._mode == "edit" and self._dirty

    def prompt_save_on_leave(self):
        """Called by flowcode when the Documentation tab is left with unsaved edits.
        The tab has already switched (ttk.Notebook can't veto), so this is save-or-
        discard, no cancel — the point is that a misclick to another tab never
        silently eats the writing. Saving preserves it; the editor keeps its buffer."""
        if not self.has_unsaved():
            return
        from tkinter import messagebox
        if messagebox.askyesno(
                "Unsaved help changes",
                f"You left the Documentation tab with unsaved edits to "
                f"'{self._editing_id}'.\n\nSave them now?"):
            self._save()
        else:
            self._dirty = False
