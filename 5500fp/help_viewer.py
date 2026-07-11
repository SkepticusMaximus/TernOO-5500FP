"""help_viewer — a reusable Tk viewer for helpdown topics.

Walks parse_topic() output into a read-only Text widget with tags (h1/h2/bullet/
para/bold/code/link), clickable [[links]], back/forward history, and a title bar.
Dead links (target has no topic file) render grey with a 'topic not found' status.
`tkinter` is imported inside __init__ so this module loads headless.

Used by the Documentation tab (embedded) and by every tab's `? Help` button (as a
pop-up Toplevel — see open_help_window).

Date: 2026-07-12, Adelaide
Authors: Stevo (SkepticusMaximus) + CF5 (helpdown core) + CC (viewer)
"""

import os as _os
import sys as _sys

_HERE = _os.path.dirname(_os.path.abspath(__file__))
if _HERE not in _sys.path:                  # importable when FlowCode execs us
    _sys.path.insert(0, _HERE)

import helpdown                             # noqa: E402

LINK_FG = "#5aa0e0"        # a readable blue in both light/dark host themes


class HelpViewer:
    """A help pane over a HelpTopics store. `on_status(msg)` is optional."""

    def __init__(self, parent, C, topics, on_status=None):
        import tkinter as tk
        self.tk = tk
        self.C, self.topics = C, topics
        self._status = on_status or (lambda _m: None)
        self._history, self._pos = [], -1
        self._link_seq = 0
        self._build(parent)

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self, parent):
        tk, C = self.tk, self.C
        mono = ("Monospace", 9)

        bar = tk.Frame(parent, bg=C["palette"])
        bar.pack(side="top", fill="x")

        def nav(text, cmd):
            b = tk.Button(bar, text=text, command=cmd, bg=C["palette"],
                          fg=C["text"], font=mono, relief="flat",
                          activebackground=C["bg"], activeforeground=C["text"])
            b.pack(side="left", padx=2, pady=2)
            return b

        self._backbtn = nav("◀ Back", self.back)
        self._fwdbtn = nav("Forward ▶", self.forward)
        self._title = tk.Label(bar, text="", bg=C["palette"], fg=C["text"],
                               font=("Monospace", 10, "bold"))
        self._title.pack(side="left", padx=10)

        self._text = tk.Text(parent, bg=C["bg"], fg=C["text"], relief="flat",
                             font=mono, wrap="word", padx=12, pady=8,
                             insertwidth=0, highlightthickness=0, cursor="arrow")
        self._text.pack(side="top", fill="both", expand=True)

        t = self._text
        t.tag_configure("h1", font=("Monospace", 14, "bold"), spacing1=8,
                        spacing3=4)
        t.tag_configure("h2", font=("Monospace", 11, "bold"), spacing1=6,
                        spacing3=3)
        t.tag_configure("para", spacing3=6)
        t.tag_configure("bullet", lmargin1=18, lmargin2=30, spacing3=2)
        t.tag_configure("bold", font=("Monospace", 9, "bold"))
        t.tag_configure("code", font=("Monospace", 9), background=C["palette"])
        t.tag_configure("link", foreground=LINK_FG, underline=True)
        t.tag_configure("deadlink", foreground=C["dim"], underline=True)
        self._refresh_nav()

    # ── navigation ────────────────────────────────────────────────────────────
    def show(self, topic_id):
        """Navigate to a topic, pushing it onto history (truncating any forward)."""
        del self._history[self._pos + 1:]
        self._history.append(topic_id)
        self._pos = len(self._history) - 1
        self._render(topic_id)

    def back(self):
        if self._pos > 0:
            self._pos -= 1
            self._render(self._history[self._pos])

    def forward(self):
        if self._pos < len(self._history) - 1:
            self._pos += 1
            self._render(self._history[self._pos])

    def _refresh_nav(self):
        self._backbtn.config(state=("normal" if self._pos > 0 else "disabled"))
        self._fwdbtn.config(state=("normal" if self._pos < len(self._history) - 1
                                   else "disabled"))

    # ── rendering ─────────────────────────────────────────────────────────────
    def _render(self, topic_id):
        t = self._text
        t.config(state="normal")
        t.delete("1.0", "end")
        topic = self.topics.topic(topic_id)
        if topic is None:
            self._title.config(text=topic_id)
            t.insert("end", "This topic hasn't been written yet.\n\n", ("para",))
            t.insert("end", f"(missing: {topic_id})\n", ("code",))
            t.config(state="disabled")
            self._refresh_nav()
            return
        self._title.config(text=topic["title"])
        for block in topic["blocks"]:
            kind = block["kind"]
            if kind == helpdown.BULLET:
                t.insert("end", "•  ", ("bullet",))
            self._insert_spans(block["spans"], kind)
            t.insert("end", "\n", (kind,))
            if kind in (helpdown.PARA, helpdown.H1, helpdown.H2):
                t.insert("end", "\n")
        t.config(state="disabled")
        self._refresh_nav()

    def _insert_spans(self, spans, block_kind):
        t = self._text
        for span in spans:
            if span["link"]:
                self._insert_link(span["text"], span["link"])
            else:
                style = {helpdown.BOLD: "bold", helpdown.CODE: "code"}.get(
                    span["style"])
                tags = (block_kind,) + ((style,) if style else ())
                t.insert("end", span["text"], tags)

    def _insert_link(self, label, target):
        t = self._text
        self._link_seq += 1
        tag = f"lnk{self._link_seq}"
        topic_id = target.split("#", 1)[0]        # #anchors are v1-optional
        dead = not self.topics.exists(topic_id)
        t.tag_configure(tag)
        t.insert("end", label, ("link" if not dead else "deadlink", tag))
        if dead:
            t.tag_bind(tag, "<Button-1>",
                       lambda _e, tid=topic_id: self._status(
                           f"Help topic not found: {tid}"))
            t.tag_bind(tag, "<Enter>", lambda _e, tid=topic_id: self._status(
                f"(dead link — no topic '{tid}')"))
        else:
            t.tag_bind(tag, "<Button-1>",
                       lambda _e, tid=topic_id: self.show(tid))
            t.tag_bind(tag, "<Enter>",
                       lambda _e: t.config(cursor="hand2"))
            t.tag_bind(tag, "<Leave>", lambda _e: t.config(cursor="arrow"))


def help_button(parent, root, C, topics, topic_id, text="?  Help", **pack):
    """A ready-to-pack `? Help` button for a tab's local toolbar: opens the shared
    viewer at `topic_id`. `topics` may be a HelpTopics or a zero-arg factory (so a
    tab can defer building the store). Any pack() kwargs are applied."""
    import tkinter as tk

    def _open():
        tp = topics() if callable(topics) else topics
        open_help_window(root, C, tp, topic_id)

    b = tk.Button(parent, text=text, command=_open, bg=C["palette"], fg=C["text"],
                  font=("Monospace", 9), relief="flat", activebackground=C["bg"],
                  activeforeground=C["text"])
    if pack:
        b.pack(**pack)
    return b


def open_help_window(root, C, topics, topic_id, geometry="720x560", extra=None):
    """Pop a standalone Help window showing `topic_id` — the target of a tab's
    `? Help` button. `extra(win)` is an optional callback to add a control row
    (e.g. a tab-specific 'Show diagram' button) between the viewer and Close.
    Returns the Toplevel."""
    import tkinter as tk
    win = tk.Toplevel(root)
    win.title("FlowCode Help")
    win.configure(bg=C["bg"])
    win.geometry(geometry)
    tk.Button(win, text="Close", command=win.destroy, bg=C["palette"],
              fg=C["text"], font=("Monospace", 9), relief="flat",
              activebackground=C["bg"], activeforeground=C["text"]
              ).pack(side="bottom", pady=(0, 8))
    if extra is not None:
        extra(win)                              # packed bottom, above Close
    viewer = HelpViewer(win, C, topics)         # fills the rest (top)
    viewer.show(topic_id)
    return win
