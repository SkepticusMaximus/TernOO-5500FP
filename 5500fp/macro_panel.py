"""macro_panel.py — Mesh-Chat's collapsible side panel: Macros / Constructor / Editor.

The captain's graphical macro language, piece 1 (the clockwork half):

* MACROS   — buttons for the library in ./macros/*.json. A macro is a JSON spec —
             a *subclass* of a command's parameter space. kind="command" renders a
             dialog (checkbox per flag, dropdown per choice, entry per arg), shows
             the EXACT command line it will run, and runs it deterministically —
             no model anywhere in the loop. kind="prompt" fills a {slot} template
             and fires it through the normal mesh Ask.
* CONSTRUCTOR — hand-forge: view/edit/save macro specs with validation. (The AI
             forge — the Professor drafting specs from --help text — is piece 2.)
* EDITOR   — a plain writing pad with a shoulder-reading assistant: manual
             "👁 Review draft" plus an auto mode that reviews after 90s of idle
             (guarded so it never queues behind a chat Ask in flight).

Tk is imported inside __init__ so the module loads headless, same as the tab.
"""

import json
import os
import subprocess
import threading
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
MACRO_DIR = os.path.join(_HERE, "macros")

SKELETON = {
    "name": "My macro",
    "kind": "command",
    "command": "ls",
    "desc": "what it does",
    "fields": [
        {"flag": "-l", "label": "Long listing", "type": "check", "default": True},
        {"flag": "--sort", "label": "Sort by", "type": "choice",
         "options": ["", "size", "time"], "default": ""},
        {"arg": "path", "label": "Where", "type": "path", "default": "~"},
    ],
}

REVIEW_PROMPT = (
    "You are a terse writing assistant. Review the draft below and reply with: "
    "1) up to three short, actionable notes on grammar/clarity/structure; "
    "2) one reference or fact worth double-checking, if any. No rewrite, no "
    "praise, just the notes.\n\nDRAFT:\n")

FORGE_HEAD = """You are drafting a macro spec for a GUI dialog builder. Reply with \
EXACTLY one JSON object and nothing else — no prose, no code fences. Schema by \
example:
{"name": "Disk usage", "kind": "command", "command": "du",
 "desc": "one line saying what it does",
 "fields": [
   {"flag": "-h", "label": "Human-readable sizes", "type": "check", "default": true},
   {"flag": "--max-depth", "label": "Depth", "type": "choice", "options": ["1","2","3"], "default": "1"},
   {"arg": "path", "label": "Where", "type": "path", "default": "~"}]}
RULES: use ONLY flags that appear in the help text below — never invent one. At
most 8 fields; pick the most useful for everyday use. Positional arguments become
"arg" fields (type "path" for files/dirs, else "text"). Labels in plain English.
"""


def _first_json(text):
    """The first balanced JSON object in `text` — models add prose despite rules."""
    import json as _json
    dec = _json.JSONDecoder()
    for i, ch in enumerate(text or ""):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(text[i:])
                return obj
            except ValueError:
                continue
    return None


def _specs():
    """Load every macro spec in MACRO_DIR, sorted by name; skip broken ones."""
    out = []
    if os.path.isdir(MACRO_DIR):
        for f in sorted(os.listdir(MACRO_DIR)):
            if f.endswith(".json"):
                try:
                    s = json.load(open(os.path.join(MACRO_DIR, f),
                                       encoding="utf-8"))
                    s["_file"] = f
                    out.append(s)
                except Exception:
                    pass
    return sorted(out, key=lambda s: s.get("name", ""))


def _validate(spec):
    """The minimal schema gate — a saved macro must be runnable."""
    if not isinstance(spec, dict):
        return "spec must be a JSON object"
    if spec.get("kind") not in ("command", "prompt"):
        return 'kind must be "command" or "prompt"'
    if spec["kind"] == "command" and not spec.get("command"):
        return 'command macros need a "command"'
    if spec["kind"] == "prompt" and not spec.get("template"):
        return 'prompt macros need a "template"'
    for f in spec.get("fields", []):
        if f.get("type") not in ("check", "choice", "text", "path"):
            return f"field {f.get('label', '?')!r}: bad type"
        if "flag" not in f and "arg" not in f:
            return f"field {f.get('label', '?')!r}: needs a flag or an arg"
    return None


class MacroPanel:
    WIDTH = 450

    def __init__(self, tv, outer, C, root):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk = tk, ttk
        self.tv, self.C, self.root = tv, C, root
        self._shown = False
        self._review_busy = False
        self._dirty = False
        self._last_key = time.time()
        self._auto = tk.IntVar(value=0)
        self._rev_result = None
        self._forge_result = None
        self._forge_cmd = None

        self.frame = tk.Frame(outer, bg=C["palette"], width=self.WIDTH)
        self.frame.pack_propagate(False)

        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("TNotebook", background=C["palette"], borderwidth=0)
        st.configure("TNotebook.Tab", background=C["bg"], foreground=C["text"],
                     padding=(10, 4))
        st.map("TNotebook.Tab", background=[("selected", C["palette"])])

        hdr = tk.Frame(self.frame, bg=C["palette"])
        hdr.pack(fill="x")
        tk.Label(hdr, text=" 🧰 macro workshop", bg=C["palette"], fg=C["dim"],
                 font=("Monospace", 9)).pack(side="left", padx=4, pady=2)
        tk.Button(hdr, text="«", command=self.toggle, bg=C["palette"],
                  fg=C["dim"], relief="flat", font=("Monospace", 11)
                  ).pack(side="right", padx=2)

        nb = ttk.Notebook(self.frame)
        nb.pack(fill="both", expand=True, padx=4, pady=4)
        self._tab_macros = tk.Frame(nb, bg=C["palette"])
        self._tab_forge = tk.Frame(nb, bg=C["palette"])
        self._tab_edit = tk.Frame(nb, bg=C["palette"])
        nb.add(self._tab_macros, text=" Macros ")
        nb.add(self._tab_forge, text=" Forge ")
        nb.add(self._tab_edit, text=" Editor ")

        self._build_macros_tab()
        self._build_forge_tab()
        self._build_editor_tab()

        # captain's ruling: the panel is a citizen, not a secret — it lives on
        # the LEFT, open by default (Claude-Desktop style), collapsible via «;
        # a thin » ribbon remains so reopening is discoverable, not memorised.
        self._sliver = tk.Frame(outer, bg=C["bg"], width=18)
        tk.Button(self._sliver, text="»", command=self.toggle, bg=C["bg"],
                  fg=C["dim"], relief="flat", font=("Monospace", 10)
                  ).pack(fill="both", expand=True)
        # a draggable grip so the width is YOURS, not mine — wide for writing
        # in the Editor, narrow for a button strip
        self._grip = tk.Frame(outer, bg=C["bg"], width=6,
                              cursor="sb_h_double_arrow")
        self._grip.bind("<B1-Motion>", self._drag)
        self.toggle()                              # start OPEN

    # ── panel chrome ─────────────────────────────────────────────────────────
    def _drag(self, e):
        w = max(250, min(e.x_root - self.frame.winfo_rootx(), 720))
        self.WIDTH = w
        self.frame.config(width=w)

    def toggle(self):
        if self._shown:
            self.frame.pack_forget()
            self._grip.pack_forget()
            self._sliver.pack(side="left", fill="y", before=self.tv._main)
        else:
            self._sliver.pack_forget()
            self.frame.config(width=self.WIDTH)
            self.frame.pack(side="left", fill="y", before=self.tv._main)
            self._grip.pack(side="left", fill="y", before=self.tv._main)
            self.refresh()
        self._shown = not self._shown

    # ── Macros tab: the button library ───────────────────────────────────────
    def _build_macros_tab(self):
        tk, C = self.tk, self.C
        self._btnbox = tk.Frame(self._tab_macros, bg=C["palette"])
        self._btnbox.pack(side="top", fill="both", expand=True, padx=6, pady=6)
        tk.Button(self._tab_macros, text="↻ Reload library", command=self.refresh,
                  bg=C["bg"], fg=C["dim"], relief="flat",
                  font=("Monospace", 9)).pack(side="bottom", pady=(0, 6))
        self.refresh()

    def refresh(self):
        tk, C = self.tk, self.C
        for w in self._btnbox.winfo_children():
            w.destroy()
        specs = _specs()
        if not specs:
            tk.Label(self._btnbox, text="no macros yet —\nforge one in the "
                     "Constructor", bg=C["palette"], fg=C["dim"],
                     font=("Monospace", 10)).pack(pady=20)
        for spec in specs:
            glyph = "⚙" if spec.get("kind") == "command" else "🎓"
            b = tk.Button(self._btnbox, text=f" {glyph}  {spec.get('name', '?')} ",
                          anchor="w", command=lambda s=spec: self._open_dialog(s),
                          bg=C["bg"], fg=C["text"], relief="flat",
                          font=("Monospace", 11), pady=4)
            b.pack(fill="x", pady=2)

    # ── the dialog renderer: spec → widgets → exact command ─────────────────
    def _open_dialog(self, spec):
        tk, C = self.tk, self.C
        dlg = tk.Toplevel(self.root)
        dlg.title(spec.get("name", "macro"))
        dlg.configure(bg=C["palette"])
        dlg.transient(self.root)
        # the button bar claims its ground FIRST (bottom) — pack gives space
        # priority by packing order, and Run/Cancel must never be the widgets
        # that get squeezed out of a small window
        bar = tk.Frame(dlg, bg=C["palette"])
        bar.pack(side="bottom", fill="x", padx=12, pady=(0, 10))
        if spec.get("desc"):
            tk.Label(dlg, text=spec["desc"], bg=C["palette"], fg=C["dim"],
                     font=("Monospace", 9), wraplength=480, justify="left"
                     ).pack(anchor="w", padx=12, pady=(10, 4))

        vars_ = []
        for f in spec.get("fields", []):
            row = tk.Frame(dlg, bg=C["palette"])
            row.pack(fill="x", padx=12, pady=3)
            tk.Label(row, text=f.get("label", f.get("flag", f.get("arg", "?"))),
                     bg=C["palette"], fg=C["text"], font=("Monospace", 10),
                     width=16, anchor="w").pack(side="left")
            t = f.get("type")
            if t == "check":
                v = tk.IntVar(value=1 if f.get("default") else 0)
                tk.Checkbutton(row, variable=v, bg=C["palette"],
                               activebackground=C["palette"]).pack(side="left")
            elif t == "choice":
                v = tk.StringVar(value=str(f.get("default", "")))
                opts = [str(o) for o in f.get("options", [])] or [""]
                tk.OptionMenu(row, v, *opts).pack(side="left", fill="x",
                                                  expand=True)
            else:                                   # text | path
                v = tk.StringVar(value=str(f.get("default", "")))
                e = tk.Entry(row, textvariable=v, bg=C["bg"], fg=C["text"],
                             insertbackground=C["text"], relief="flat",
                             font=("Monospace", 11))
                e.pack(side="left", fill="x", expand=True)
                self.tv._wire_editing(e, editable=True)
                if t == "path":
                    def browse(var=v):
                        from tkinter import filedialog
                        p = filedialog.askopenfilename() or \
                            filedialog.askdirectory()
                        if p:
                            var.set(p)
                    tk.Button(row, text="…", command=browse, bg=C["bg"],
                              fg=C["text"], relief="flat").pack(side="left")
            vars_.append((f, v))

        prev = tk.Label(dlg, text="", bg=C["bg"], fg=C["text"],
                        font=("Monospace", 10), wraplength=480, justify="left",
                        anchor="w", pady=6, padx=8)
        prev.pack(fill="x", padx=12, pady=(8, 4))
        out = tk.Text(dlg, height=10, bg=C["bg"], fg=C["text"], relief="flat",
                      font=("Monospace", 9), state="disabled", wrap="word")
        out.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        def assemble():
            """spec + current widget values → argv list or prompt text."""
            if spec.get("kind") == "prompt":
                slots = {f.get("arg", f.get("flag", "")): str(v.get())
                         for f, v in vars_}
                try:
                    return spec["template"].format(**slots)
                except KeyError as e:
                    return f"(template needs a value for {e})"
            argv = [spec["command"]]
            for f, v in vars_:
                val = v.get()
                if f.get("type") == "check":
                    if val:
                        argv.append(f["flag"])
                elif "flag" in f:
                    if str(val):
                        argv += [f["flag"], str(val)]
            for f, v in vars_:                     # positionals, in spec order
                if "arg" in f and f.get("type") != "check":
                    val = str(v.get())
                    if val:
                        argv.append(os.path.expanduser(val)
                                    if f.get("type") == "path" else val)
            return argv

        def repaint(*_):
            a = assemble()
            prev.config(text=("→ " + " ".join(a)) if isinstance(a, list)
                        else "→ " + a[:220])
        for _f, v in vars_:
            v.trace_add("write", repaint)
        repaint()

        def run():
            a = assemble()
            if spec.get("kind") == "prompt":
                dlg.destroy()
                self._fire_prompt(a)
                return
            out.config(state="normal")
            out.delete("1.0", "end")
            out.insert("end", "$ " + " ".join(a) + "\n\n")
            try:
                r = subprocess.run(a, capture_output=True, timeout=60,
                                   cwd=os.path.expanduser("~"))
                body = (r.stdout.decode("utf-8", "replace")
                        + r.stderr.decode("utf-8", "replace"))
                out.insert("end", body[:8000] or "(no output)")
            except Exception as e:                  # noqa: BLE001 — to the user
                out.insert("end", f"error: {e}")
            out.config(state="disabled")

        tk.Button(bar, text="Cancel", command=dlg.destroy, bg=C["bg"],
                  fg=C["dim"], relief="flat").pack(side="right", padx=4)
        tk.Button(bar, text="  Run ▶  ", command=run, bg=self.tv.GRN,
                  fg="#0c0e14", relief="flat",
                  font=("Monospace", 11, "bold")).pack(side="right")
        # size to the content, clamped to the screen — never bigger than the
        # display, never small enough to hide the controls
        dlg.update_idletasks()
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        w = max(560, min(dlg.winfo_reqwidth() + 24, sw - 80))
        h = max(480, min(dlg.winfo_reqheight() + 24, sh - 80))
        dlg.geometry(f"{w}x{h}")
        dlg.minsize(520, 420)

    def _fire_prompt(self, text):
        """A prompt-macro rides the normal mesh Ask, exactly as if typed."""
        tv = self.tv
        tv._prompt.delete("1.0", "end")
        tv._prompt.insert("1.0", text)
        tv._prompt.config(fg=self.C["text"])
        tv._ask()

    # ── Forge tab: the pruning TREE is the interface; JSON is plumbing ───────
    def _build_forge_tab(self):
        tk, C = self.tk, self.C
        top = tk.Frame(self._tab_forge, bg=C["palette"])
        top.pack(fill="x", padx=6, pady=6)
        self._forge_name = tk.StringVar(value="")
        tk.Label(top, text="file:", bg=C["palette"], fg=C["dim"],
                 font=("Monospace", 9)).pack(side="left")
        self._forge_entry = tk.Entry(top, textvariable=self._forge_name,
                                     bg=C["bg"], fg=C["text"], relief="flat",
                                     insertbackground=C["text"],
                                     font=("Monospace", 10))
        self._forge_entry.pack(side="left", fill="x", expand=True, padx=4)
        tk.Label(top, text=".json", bg=C["palette"], fg=C["dim"],
                 font=("Monospace", 9)).pack(side="left")
        self.tv._wire_editing(self._forge_entry, editable=True)

        # bottom claims its ground FIRST — controls must never be the widgets
        # squeezed out of a small panel (the captain caught this twice)
        bar = tk.Frame(self._tab_forge, bg=C["palette"])
        bar.pack(side="bottom", fill="x", padx=6, pady=6)
        self._forge_msg = tk.Label(self._tab_forge, text="", bg=C["palette"],
                                   fg=C["dim"], font=("Monospace", 9),
                                   wraplength=380, justify="left")
        self._forge_msg.pack(side="bottom", fill="x", padx=6)
        self._forge_body = tk.Frame(self._tab_forge, bg=C["palette"])
        self._forge_body.pack(fill="both", expand=True, padx=6)

        tk.Button(bar, text="🤖 Forge from a command", command=self._ai_forge,
                  bg=C["bg"], fg=C["text"], relief="flat", font=("Monospace", 9)
                  ).pack(side="left")
        tk.Button(bar, text="skeleton", command=self._load_skeleton, bg=C["bg"],
                  fg=C["dim"], relief="flat", font=("Monospace", 9)
                  ).pack(side="left", padx=4)
        tk.Button(bar, text="{ }", command=self._toggle_raw, bg=C["bg"],
                  fg=C["dim"], relief="flat", font=("Monospace", 9)
                  ).pack(side="left", padx=4)
        tk.Button(bar, text="💾 Save", command=self._forge_save, bg=self.tv.GRN,
                  fg="#0c0e14", relief="flat", font=("Monospace", 10, "bold")
                  ).pack(side="right")
        self._load_skeleton()
        self._forge_msg.config(
            text="🤖 forges a pruning tree from any command's --help — tick what "
                 "to keep, tweak labels and defaults, 💾 Save mints the button. "
                 "{ } shows the raw spec if you want it.")

    def _load_skeleton(self):
        self._forge_spec = json.loads(json.dumps(SKELETON))
        if not self._forge_name.get().strip():
            self._forge_name.set("my-macro")
        self._show_tree()

    def _clear_body(self):
        for w in self._forge_body.winfo_children():
            w.destroy()

    def _show_tree(self):
        """The 90% interface: the spec as a tick-box pruning tree."""
        tk, C = self.tk, self.C
        self._forge_raw = False
        self._clear_body()
        s = self._forge_spec or {}
        tk.Label(self._forge_body, text=f"command: {s.get('command', '?')}",
                 bg=C["palette"], fg=C["dim"], font=("Monospace", 9),
                 anchor="w").pack(fill="x", pady=(4, 0))
        hr = tk.Frame(self._forge_body, bg=C["palette"])
        hr.pack(fill="x", pady=2)
        tk.Label(hr, text="button name", bg=C["palette"], fg=C["dim"],
                 font=("Monospace", 8)).pack(side="left")
        self._t_name = tk.StringVar(value=s.get("name", ""))
        ne = tk.Entry(hr, textvariable=self._t_name, bg=C["bg"], fg=C["text"],
                      insertbackground=C["text"], relief="flat",
                      font=("Monospace", 10))
        ne.pack(side="left", fill="x", expand=True, padx=4)
        self.tv._wire_editing(ne, editable=True)
        tk.Label(self._forge_body, text="tick = keep · edit labels & defaults",
                 bg=C["palette"], fg=C["dim"], font=("Monospace", 8),
                 anchor="w").pack(fill="x", pady=(2, 4))
        self._t_rows = []
        for f in s.get("fields", []):
            row = tk.Frame(self._forge_body, bg=C["palette"])
            row.pack(fill="x", pady=1)
            inc = tk.IntVar(value=1)
            tk.Checkbutton(row, variable=inc, bg=C["palette"],
                           activebackground=C["palette"]).pack(side="left")
            lv = tk.StringVar(value=f.get("label", ""))
            le = tk.Entry(row, textvariable=lv, bg=C["bg"], fg=C["text"],
                          insertbackground=C["text"], relief="flat",
                          font=("Monospace", 10), width=16)
            le.pack(side="left", padx=(2, 4))
            self.tv._wire_editing(le, editable=True)
            code = f.get("flag", f.get("arg", "?"))
            tk.Label(row, text=f"{code}", bg=C["palette"], fg=C["dim"],
                     font=("Monospace", 9), width=12, anchor="w"
                     ).pack(side="left")
            t = f.get("type")
            if t == "check":
                dv = tk.IntVar(value=1 if f.get("default") else 0)
                tk.Checkbutton(row, variable=dv, bg=C["palette"],
                               activebackground=C["palette"]).pack(side="left")
            elif t == "choice":
                dv = tk.StringVar(value=str(f.get("default", "")))
                opts = [str(o) for o in f.get("options", [])] or [""]
                tk.OptionMenu(row, dv, *opts).pack(side="left")
            else:
                dv = tk.StringVar(value=str(f.get("default", "")))
                de = tk.Entry(row, textvariable=dv, bg=C["bg"], fg=C["text"],
                              insertbackground=C["text"], relief="flat",
                              font=("Monospace", 10), width=10)
                de.pack(side="left")
                self.tv._wire_editing(de, editable=True)
            self._t_rows.append((f, inc, lv, dv))

    def _tree_to_spec(self):
        """Fold the tree back into the spec — unticked fields fall away."""
        s = self._forge_spec or {}
        s["name"] = self._t_name.get().strip() or s.get("name", "macro")
        fields = []
        for f, inc, lv, dv in self._t_rows:
            if not inc.get():
                continue
            f2 = dict(f)
            f2["label"] = lv.get().strip() or f.get("label", "")
            f2["default"] = (bool(dv.get()) if f.get("type") == "check"
                             else dv.get())
            fields.append(f2)
        s["fields"] = fields
        self._forge_spec = s

    def _show_raw(self):
        """The 10% view: the spec as raw JSON, for those who ask."""
        tk, C = self.tk, self.C
        self._forge_raw = True
        self._clear_body()
        self._forge_text = tk.Text(self._forge_body, bg=C["bg"], fg=C["text"],
                                   insertbackground=C["text"], relief="flat",
                                   font=("Monospace", 10), wrap="none",
                                   undo=True)
        self._forge_text.pack(fill="both", expand=True)
        self.tv._wire_editing(self._forge_text, editable=True)
        self._forge_text.insert("1.0", json.dumps(self._forge_spec, indent=2))

    def _toggle_raw(self):
        if getattr(self, "_forge_raw", False):
            try:
                self._forge_spec = json.loads(
                    self._forge_text.get("1.0", "end"))
            except Exception as e:                  # noqa: BLE001 — to the user
                self._forge_msg.config(text=f"raw spec isn't valid JSON: {e}")
                return
            self._show_tree()
        else:
            self._tree_to_spec()
            self._show_raw()

    def _forge_save(self):
        name = self._forge_name.get().strip()
        if not name:
            self._forge_msg.config(text="give it a file name first")
            return
        if getattr(self, "_forge_raw", False):
            try:
                spec = json.loads(self._forge_text.get("1.0", "end"))
            except Exception as e:                  # noqa: BLE001 — to the user
                self._forge_msg.config(text=f"not valid JSON: {e}")
                return
        else:
            self._tree_to_spec()
            spec = self._forge_spec
        err = _validate(spec)
        if err:
            self._forge_msg.config(text=f"spec problem: {err}")
            return
        os.makedirs(MACRO_DIR, exist_ok=True)
        path = os.path.join(MACRO_DIR, name + ".json")
        json.dump(spec, open(path, "w", encoding="utf-8"), indent=2)
        self._forge_msg.config(text=f"saved {os.path.basename(path)} ✓ — "
                                    "it's in Macros now")
        self.refresh()

    # ── the AI forge: command --help → the Professor drafts, YOU prune ───────
    def _ai_forge(self):
        tk, C = self.tk, self.C
        dlg = tk.Toplevel(self.root)
        dlg.title("🤖 Forge from a command")
        dlg.configure(bg=C["palette"])
        dlg.transient(self.root)
        tk.Label(dlg, text="Command to forge (must exist on this machine):",
                 bg=C["palette"], fg=C["text"], font=("Monospace", 10)
                 ).pack(padx=14, pady=(12, 4), anchor="w")
        v = tk.StringVar()
        e = tk.Entry(dlg, textvariable=v, bg=C["bg"], fg=C["text"],
                     insertbackground=C["text"], relief="flat",
                     font=("Monospace", 12), width=28)
        e.pack(padx=14, pady=4, fill="x")
        self.tv._wire_editing(e, editable=True)
        e.focus_set()
        tk.Label(dlg, text="Its --help goes to the Professor; he proposes a\n"
                           "spec; it lands in the Forge editor for YOUR pruning.",
                 bg=C["palette"], fg=C["dim"], font=("Monospace", 9),
                 justify="left").pack(padx=14, pady=(2, 6), anchor="w")

        def go(_e=None):
            cmd = (v.get().strip().split() or [""])[0]
            dlg.destroy()
            if cmd:
                self._forge_start(cmd)
        e.bind("<Return>", go)
        bar = tk.Frame(dlg, bg=C["palette"])
        bar.pack(fill="x", padx=14, pady=(0, 12))
        tk.Button(bar, text="Cancel", command=dlg.destroy, bg=C["bg"],
                  fg=C["dim"], relief="flat").pack(side="right", padx=4)
        tk.Button(bar, text="  Forge ▶  ", command=go, bg=self.tv.GRN,
                  fg="#0c0e14", relief="flat",
                  font=("Monospace", 10, "bold")).pack(side="right")

    def _forge_start(self, cmd):
        import shutil
        if not shutil.which(cmd):
            self._forge_msg.config(text=f"no such command on this machine: {cmd}")
            return
        try:
            r = subprocess.run([cmd, "--help"], capture_output=True, timeout=10)
            help_text = (r.stdout or r.stderr).decode("utf-8", "replace")
            if len(help_text.strip()) < 40:
                r = subprocess.run([cmd, "-h"], capture_output=True, timeout=10)
                help_text = (r.stdout or r.stderr).decode("utf-8", "replace")
        except Exception as e:                      # noqa: BLE001 — to the user
            self._forge_msg.config(text=f"couldn't read {cmd} --help: {e}")
            return
        self._forge_cmd = cmd
        self._forge_name.set(cmd)
        self._forge_msg.config(
            text=f"🤖 the Professor is reading `{cmd} --help`… (a minute or two)")
        prompt = FORGE_HEAD + f"\nCOMMAND: {cmd}\nHELP TEXT:\n{help_text[:5000]}"
        tv = self.tv
        local = ("127.0.0.1", 9000)
        cands = [local] + [(s.host, s.port) for s in tv._board_states
                           if (s.host, s.port) != local]

        def work():
            try:
                _w, ans = tv._buyer.ask_mesh(prompt, candidates=cands)
                self._forge_result = ans or "(no model answered)"
            except Exception as ex:                 # noqa: BLE001 — to the user
                self._forge_result = f"(forge failed: {ex})"
        threading.Thread(target=work, daemon=True).start()
        self._poll_forge()

    def _poll_forge(self):
        if self._forge_result is None:
            self.root.after(400, self._poll_forge)
            return
        text = self._forge_result
        self._forge_result = None
        obj = _first_json(text)
        if obj is None:
            # off-protocol prose → the raw view, labelled as salvage
            self._forge_spec = {"name": self._forge_cmd or "macro",
                                "kind": "command",
                                "command": self._forge_cmd or "",
                                "fields": []}
            self._show_raw()
            self._forge_text.delete("1.0", "end")
            self._forge_text.insert("1.0", text)
            self._forge_msg.config(
                text="the Professor went off-protocol — his raw reply is above; "
                     "salvage by hand or 🤖 retry")
            return
        # the model proposes; the clockwork corrects what it can't be trusted on
        obj["kind"] = "command"
        if self._forge_cmd:
            obj["command"] = self._forge_cmd
        self._forge_spec = obj
        self._show_tree()
        err = _validate(obj)
        if err:
            self._forge_msg.config(
                text=f"proposed, but fix this before saving: {err}")
        else:
            self._forge_msg.config(
                text="the Professor proposes — untick what you don't want, "
                     "tweak labels and defaults (he may have invented a flag; "
                     "the dialog preview will expose it), then 💾 Save")

    # ── Editor tab: the shoulder-reader ──────────────────────────────────────
    def _build_editor_tab(self):
        tk, C = self.tk, self.C
        bar = tk.Frame(self._tab_edit, bg=C["palette"])
        bar.pack(fill="x", padx=6, pady=(6, 2))
        tk.Button(bar, text="Open", command=self._ed_open, bg=C["bg"],
                  fg=C["text"], relief="flat", font=("Monospace", 9)
                  ).pack(side="left")
        tk.Button(bar, text="Save", command=self._ed_save, bg=C["bg"],
                  fg=C["text"], relief="flat", font=("Monospace", 9)
                  ).pack(side="left", padx=4)
        tk.Checkbutton(bar, text="auto 👁", variable=self._auto, bg=C["palette"],
                       fg=C["text"], selectcolor=C["bg"],
                       activebackground=C["palette"], font=("Monospace", 9)
                       ).pack(side="right")
        tk.Button(bar, text="👁 Review draft", command=self._review_now,
                  bg=C["bg"], fg=C["text"], relief="flat", font=("Monospace", 9)
                  ).pack(side="right", padx=4)

        # notes claim the bottom FIRST so the writing pad can never squeeze
        # them (or itself) out of a short panel
        self._notes = tk.Text(self._tab_edit, height=7, bg=C["bg"], fg=C["dim"],
                              relief="flat", font=("Monospace", 9), wrap="word",
                              state="disabled", padx=6, pady=4)
        self._notes.pack(side="bottom", fill="x", padx=6, pady=(0, 6))
        tk.Label(self._tab_edit, text="assistant notes", bg=C["palette"],
                 fg=C["dim"], font=("Monospace", 8)
                 ).pack(side="bottom", anchor="w", padx=8)
        self.tv._wire_editing(self._notes, editable=False)

        self._ed = tk.Text(self._tab_edit, bg=C["bg"], fg=C["text"],
                           insertbackground=C["text"], relief="flat", undo=True,
                           font=("Monospace", 11), wrap="word", padx=6, pady=6)
        self._ed.pack(fill="both", expand=True, padx=6)
        self._ed.bind("<KeyRelease>", self._ed_key)
        self.tv._wire_editing(self._ed, editable=True)
        self._ed_path = None
        self.root.after(5000, self._auto_tick)

    def _ed_key(self, _e=None):
        self._dirty = True
        self._last_key = time.time()

    def _ed_open(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(initialdir=os.path.expanduser("~"))
        if p:
            self._ed_path = p
            self._ed.delete("1.0", "end")
            self._ed.insert("1.0", open(p, encoding="utf-8",
                                        errors="replace").read())
            self._dirty = False

    def _ed_save(self):
        from tkinter import filedialog
        p = self._ed_path or filedialog.asksaveasfilename(
            initialdir=os.path.expanduser("~"))
        if p:
            self._ed_path = p
            open(p, "w", encoding="utf-8").write(self._ed.get("1.0", "end-1c"))
            self._note(f"saved {os.path.basename(p)}")

    def _note(self, text):
        self._notes.config(state="normal")
        self._notes.delete("1.0", "end")
        self._notes.insert("1.0", text)
        self._notes.config(state="disabled")

    def _review_now(self):
        """One shoulder-glance: the draft rides the normal mesh buy."""
        if self._review_busy:
            return
        draft = self._ed.get("1.0", "end-1c").strip()
        if len(draft) < 40:
            self._note("(draft too short to review)")
            return
        self._review_busy = True
        self._dirty = False
        self._note("👁 the Professor is reading…")
        tv = self.tv
        local = ("127.0.0.1", 9000)
        cands = [local] + [(s.host, s.port) for s in tv._board_states
                           if (s.host, s.port) != local]

        def work():
            try:
                _w, ans = tv._buyer.ask_mesh(REVIEW_PROMPT + draft[:6000],
                                             candidates=cands)
                self._rev_result = ans or "(no model answered)"
            except Exception as e:                  # noqa: BLE001 — to the user
                self._rev_result = f"(review failed: {e})"
        threading.Thread(target=work, daemon=True).start()
        self._poll_review()

    def _poll_review(self):
        if self._rev_result is None:
            self.root.after(300, self._poll_review)
            return
        self._note(self._rev_result)
        self._rev_result = None
        self._review_busy = False

    def _auto_tick(self):
        """The 'reading over your shoulder' switch: review after 90s of idle,
        only when nothing else is talking to the mesh."""
        try:
            idle = time.time() - self._last_key
            ask_idle = str(self.tv._askbtn["state"]) == "normal"
            if (self._auto.get() and self._dirty and idle > 90
                    and not self._review_busy and ask_idle):
                self._review_now()
        finally:
            self.root.after(5000, self._auto_tick)
