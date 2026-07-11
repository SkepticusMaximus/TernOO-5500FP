"""help_tab_view — the Documentation tab (FlowCode's tenth tab).

Mounted by flowcode.py:  DocsTabView(parent_frame, C, root, set_status)

Left: a search box + a section-grouped index of every docs/help topic. Right: the
embedded HelpViewer. Self-contained (the chrome matrix hides the sidebar + Output on
this tab). `tkinter` is imported inside __init__ so the module loads headless.

Date: 2026-07-12, Adelaide
Authors: Stevo (SkepticusMaximus) + CC
"""

from help_topics import HelpTopics
from help_viewer import HelpViewer


class DocsTabView:
    def __init__(self, parent, C, root, set_status=None):
        import tkinter as tk
        self.tk = tk
        self.C, self.root = C, root
        self._status = set_status or (lambda _m: None)
        self.topics = HelpTopics()
        self._rows = []            # listbox row index -> topic_id (or None header)
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
                                selectbackground=C["palette"],
                                activestyle="none")
        self._list.pack(side="top", fill="both", expand=True, padx=6, pady=(0, 6))
        self._list.bind("<<ListboxSelect>>", lambda _e: self._on_pick())

        right = tk.Frame(parent, bg=C["bg"])
        right.pack(side="left", fill="both", expand=True)
        self.viewer = HelpViewer(right, C, self.topics, on_status=self._status)

    # ── index + search ─────────────────────────────────────────────────────────
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
        first = next((tid for _text, tid in rows if tid), None)
        if first:
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
        if tid:
            self.viewer.show(tid)
