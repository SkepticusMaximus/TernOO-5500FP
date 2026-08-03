"""p2pcp_tab_view.py — the Mesh tab: P2PCP inside FlowCode/Academy.

Mounted by flowcode.py:  MeshTabView(parent_frame, C, root, set_status)

You land ALREADY talking to a model: a big prompt, a big answer, and one Ask
button that auto-routes to a live Professor on the mesh — no addresses, no ports,
no "open a stall" first. All the plumbing (your own stall, peers, the live board)
lives behind a ⚙ Setup drawer, out of sight until you want it.

Under the hood it's the tested p2pcp_service.MeshService; the live board reuses the
standalone p2pcp.dashboard's NodeState engine to watch the real nodes. `tkinter` is
imported inside __init__ so this module loads headless.

Date: 2026-07-10, rebuilt 2026-08-02 (sane-defaults UX), Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import os
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SVC = _load("p2pcp_service")


class MeshTabView:
    GRN, RED = "#3fd08f", "#e06a6a"
    PLACEHOLDER = "Ask the Professor anything…   (Ctrl+Enter to send)"
    ATTACH_MAX = 4000            # max chars of an attached file fed to the model

    def __init__(self, parent, C, root, set_status):
        import tkinter as tk
        self.tk = tk
        self.C, self.root, self._status = C, root, set_status
        self.svc = None                          # optional stall, opened from Setup
        self._buyer = SVC.MeshService(worker_kind=None, seed="flowcode-mesh")
        self._board_states = []
        self._cards = []
        self._drawer_shown = False
        self._ask_result = None                  # worker → main-thread handoff
        self._history = []                        # [(role, text)] — the conversation
        self._pending_idx = None
        self._store = None                        # portable saved-chat store
        self._chat_id = None                      # current saved chat (None = unsaved)
        self._attachment = None                   # {name,text,clipped} for the next Ask
        self._build(parent)

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self, parent):
        tk, C = self.tk, self.C
        mono = ("Monospace", 9)

        self._outer = tk.Frame(parent, bg=C["bg"])
        self._outer.pack(fill="both", expand=True)
        self._main = tk.Frame(self._outer, bg=C["bg"])
        self._main.pack(side="left", fill="both", expand=True)
        self._drawer = tk.Toplevel(self.root)      # ⚙ Setup is its own pop-out window
        self._drawer.title("⚙ Setup — Mesh-Chat")
        self._drawer.configure(bg=C["palette"])
        self._drawer.geometry("440x700")
        self._drawer.withdraw()                    # hidden until Setup is clicked
        self._drawer.protocol("WM_DELETE_WINDOW", self._toggle_setup)  # its ✕ hides it

        # top strip: live connection status + the Setup toggle
        top = tk.Frame(self._main, bg=C["bg"])
        top.pack(side="top", fill="x", padx=12, pady=(10, 2))
        self._conn = tk.Label(top, text="◌  finding a model on the mesh…",
                              bg=C["bg"], fg=C["dim"], font=mono, anchor="w")
        self._conn.pack(side="left")
        self._setupbtn = tk.Button(top, text="⚙ Setup", command=self._toggle_setup,
                                   bg=C["palette"], fg=C["text"], font=mono,
                                   relief="flat", activebackground=C["bg"],
                                   activeforeground=C["text"])
        self._setupbtn.pack(side="right")
        self._chatbtn = tk.Menubutton(top, text="💬 New chat ▾", bg=C["palette"],
                                      fg=C["text"], font=mono, relief="flat",
                                      activebackground=C["bg"])
        self._chatmenu = tk.Menu(self._chatbtn, tearoff=0)
        self._chatbtn.config(menu=self._chatmenu)
        self._chatbtn.pack(side="right", padx=(0, 8))

        # the prompt — the dominant element
        tk.Label(self._main, text="Ask the mesh", bg=C["bg"], fg=C["text"],
                 font=("Monospace", 13, "bold"), anchor="w"
                 ).pack(side="top", fill="x", padx=12, pady=(6, 2))
        self._prompt = tk.Text(self._main, height=4, bg=C["palette"], fg=C["dim"],
                               insertbackground=C["text"], relief="flat", undo=True,
                               maxundo=-1, autoseparators=True,
                               font=("Monospace", 14), wrap="word", padx=8, pady=8)
        self._prompt.pack(side="top", fill="x", padx=12)
        self._prompt.insert("1.0", self.PLACEHOLDER)
        self._prompt.bind("<FocusIn>", self._clear_placeholder)
        self._prompt.bind("<Control-Return>", lambda e: (self._ask(), "break")[1])
        self._wire_editing(self._prompt, editable=True)

        askrow = tk.Frame(self._main, bg=C["bg"])
        askrow.pack(side="top", fill="x", padx=12, pady=(6, 4))
        tk.Label(askrow, text="answers come from a live model on your mesh",
                 bg=C["bg"], fg=C["dim"], font=("Monospace", 8)).pack(side="left")
        self._askbtn = tk.Button(askrow, text="  Ask  ▶  ", command=self._ask,
                                 bg=self.GRN, fg="#0c0e14",
                                 font=("Monospace", 12, "bold"), relief="flat",
                                 activebackground="#57e0a0")
        self._askbtn.pack(side="right")
        self._attachbtn = tk.Button(askrow, text=" 📎 ", command=self._attach_file,
                                     bg=C["palette"], fg=C["text"], font=mono,
                                     relief="flat", activebackground=C["bg"],
                                     activeforeground=C["text"])
        self._attachbtn.pack(side="right", padx=(0, 6))
        self._attachlbl = tk.Label(askrow, text="", bg=C["bg"], fg=C["dim"],
                                   font=("Monospace", 8))
        self._attachlbl.pack(side="right", padx=(0, 4))

        # the chat — a running TRANSCRIPT (accumulates; read-only but selectable)
        af = tk.Frame(self._main, bg=C["bg"])
        af.pack(side="top", fill="both", expand=True, padx=12, pady=(4, 12))
        self._chat = tk.Text(af, bg="#0c0e14", fg=C["text"], relief="flat",
                             font=("Monospace", 12), wrap="word", padx=10, pady=10)
        sb = tk.Scrollbar(af, orient="vertical", command=self._chat.yview)
        self._chat.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._chat.pack(side="left", fill="both", expand=True)
        self._chat.tag_config("who_you", foreground=C["dim"],
                              font=("Monospace", 9, "bold"), spacing1=8)
        self._chat.tag_config("who_prof", foreground=self.GRN,
                              font=("Monospace", 9, "bold"), spacing1=8)
        self._chat.tag_config("msg", foreground=C["text"], font=("Monospace", 12))
        self._chat.tag_config("pending", foreground=C["dim"],
                              font=("Monospace", 11, "italic"))
        self._chat.tag_config("sys", foreground=C["dim"], font=("Monospace", 10))
        self._chat.tag_config("error", foreground=self.RED, font=("Monospace", 11))
        self._greeting()
        self._wire_editing(self._chat, editable=False)

        self._build_drawer(self._drawer)
        self._init_store()
        self._start_board()

    def _clear_placeholder(self, _e=None):
        if self._prompt.get("1.0", "end").strip() == self.PLACEHOLDER:
            self._prompt.delete("1.0", "end")
            self._prompt.config(fg=self.C["text"])

    # ── the Setup drawer (everything technical lives here) ─────────────────────
    def _build_drawer(self, drawer):
        tk, C = self.tk, self.C
        mono = ("Monospace", 9)

        head = tk.Frame(drawer, bg=C["palette"])
        head.pack(side="top", fill="x", padx=8, pady=(8, 2))
        tk.Label(head, text="⚙ Setup", bg=C["palette"], fg=C["text"],
                 font=("Monospace", 11, "bold")).pack(side="left")
        tk.Button(head, text="✕", command=self._toggle_setup, bg=C["palette"],
                  fg=C["dim"], font=mono, relief="flat", activebackground=C["bg"]
                  ).pack(side="right")

        def section(title):
            lf = tk.LabelFrame(drawer, text=f" {title} ", bg=C["bg"], fg=C["text"],
                               font=mono)
            lf.pack(side="top", fill="x", padx=8, pady=5)
            return lf

        def dbtn(where, text, cmd, side="left"):
            b = tk.Button(where, text=text, command=cmd, bg=C["palette"],
                          fg=C["text"], font=mono, relief="flat",
                          activebackground=C["bg"], activeforeground=C["text"])
            b.pack(side=side, padx=4, pady=2)
            return b

        def dentry(where, value, width=None):
            e = tk.Entry(where, bg=C["bg"], fg=C["text"], insertbackground=C["text"],
                         relief="flat", font=mono, **({"width": width} if width else {}))
            e.insert(0, value)
            return e

        # away-from-home: point the client at a public relay (e.g. bore.pub:PORT)
        road = section("🧳 Away from home — talk via relay")
        rr = tk.Frame(road, bg=C["bg"]); rr.pack(side="top", fill="x", pady=2)
        tk.Label(rr, text="relay host:port", bg=C["bg"], fg=C["dim"], font=mono
                 ).pack(side="left", padx=(4, 2))
        self._relay = dentry(rr, self._read_relay(), width=22)
        self._relay.pack(side="left", padx=2)
        dbtn(rr, "✕", self._clear_relay)          # forget a stale/ephemeral relay
        tk.Label(road, text="Set this to reach home over the internet (a bore.pub:PORT "
                 "from park-relay.sh). Clear it to use the LAN/mesh.", bg=C["bg"],
                 fg=C["dim"], font=("Monospace", 8), wraplength=360, justify="left",
                 anchor="w").pack(side="top", fill="x", padx=4, pady=(0, 2))

        # the live mesh — the real nodes (the folded-in dashboard)
        board = section("The mesh — live nodes")
        self._board_holder = board

        # your own stall — sell compute
        stall = section("Your stall — sell compute (optional)")
        srow = tk.Frame(stall, bg=C["bg"]); srow.pack(side="top", fill="x", pady=2)
        tk.Label(srow, text="sell", bg=C["bg"], fg=C["dim"], font=mono
                 ).pack(side="left", padx=(4, 2))
        self._role = tk.StringVar(value="professor")
        rm = tk.OptionMenu(srow, self._role, "professor", "ghost", "buy-only")
        rm.config(bg=C["palette"], fg=C["text"], font=mono, relief="flat",
                  highlightthickness=0, activebackground=C["bg"])
        rm.pack(side="left", padx=(0, 6))
        self._mock = tk.IntVar(value=1)
        tk.Checkbutton(srow, text="mock", variable=self._mock, bg=C["bg"],
                       fg=C["text"], selectcolor=C["palette"], font=mono,
                       activebackground=C["bg"]).pack(side="left")
        self._startbtn = dbtn(srow, "Open stall", self._toggle_stall, side="right")
        self._addr = tk.Label(stall, text="(stall closed)", bg=C["bg"], fg=C["dim"],
                              font=mono, anchor="w")
        self._addr.pack(side="top", fill="x", padx=4)
        self._wallet = tk.Label(stall, text=self._wallet_text(None), bg=C["bg"],
                                fg=C["text"], font=mono, anchor="w")
        self._wallet.pack(side="top", fill="x", padx=4)
        self._meshstat = tk.Label(stall, text="", bg=C["bg"], fg=C["dim"], font=mono,
                                  anchor="w")
        self._meshstat.pack(side="top", fill="x", padx=4)
        dbtn(stall, "Refresh", self._refresh_wallet, side="right")

        # peers
        peers = section("Peers")
        prow = tk.Frame(peers, bg=C["bg"]); prow.pack(side="top", fill="x", pady=2)
        tk.Label(prow, text="join host:port", bg=C["bg"], fg=C["dim"], font=mono
                 ).pack(side="left", padx=(4, 2))
        self._joinentry = dentry(prow, "127.0.0.1:9000", width=20)
        self._joinentry.pack(side="left", padx=2)
        dbtn(prow, "Join", self._join)
        self._peerlist = tk.Listbox(peers, height=3, bg=C["bg"], fg=C["text"],
                                    font=mono, relief="flat", highlightthickness=0,
                                    selectbackground=C["palette"])
        self._peerlist.pack(side="top", fill="x", padx=4, pady=3)

    def _toggle_setup(self):
        if self._drawer_shown:
            self._drawer.withdraw()
            self._drawer_shown = False
            self._setupbtn.config(text="⚙ Setup")
        else:
            self.root.update_idletasks()           # pop out beside the main window
            x = self.root.winfo_rootx() + self.root.winfo_width() + 8
            y = self.root.winfo_rooty()
            self._drawer.geometry(f"+{max(0, x)}+{max(0, y)}")
            self._drawer.deiconify()
            self._drawer.lift()
            self._drawer_shown = True
            self._setupbtn.config(text="⚙ Setup ✕")
            self._refresh_wallet()

    # ── the default Ask: auto-route to a live model on the mesh ────────────────
    def _ask(self):
        prompt = self._prompt.get("1.0", "end").strip()
        if not prompt or prompt == self.PLACEHOLDER:
            self._status("Type a question first.")
            return
        cands = [(st.host, st.port) for st in self._board_states] or [("127.0.0.1", 9000)]
        relay = self._relay_addr()
        if relay:
            self._save_relay(f"{relay[0]}:{relay[1]}")
        elif hasattr(self, "_relay") and not self._relay.get().strip():
            self._clear_relay(clear_field=False)   # emptied → forget it, don't resurrect
        self._begin_turn(prompt)
        context = self._build_context()          # the conversation so far → the model
        self._clear_attachment()                 # one-shot: it rode along with this turn
        self._status("Asking via relay…" if relay else "Asking the mesh…")

        def work():
            where = ans = err = None
            try:
                if relay:                         # away-from-home: go through the relay
                    where = f"{relay[0]}:{relay[1]} (relay)"
                    ans = self._buyer.ask_via_relay(relay[0], relay[1], context)
                else:                             # home: discover a provider on the mesh
                    where, ans = self._buyer.ask_mesh(context, candidates=cands)
            except Exception as e:                # noqa: BLE001 — surfaced to the user
                err = str(e)
            self._ask_result = (where, ans, err)  # a main-thread poll paints it —
            #                                       Tk calls must not cross threads

        threading.Thread(target=work, daemon=True).start()
        self.root.after(150, self._ask_poll)

    def _ask_poll(self):
        r = self._ask_result
        if r is None:
            self.root.after(150, self._ask_poll)
            return
        self._ask_result = None
        self._show_ask(*r)

    def _show_ask(self, where, ans, err):
        self._askbtn.config(state="normal", text="  Ask  ▶  ")
        self._end_pending()
        if err:
            self._chat.insert("end", f"(couldn't reach a model: {err} — try ⚙ Setup)"
                              "\n\n", ("error",))
            self._status("Ask failed.")
        elif not where or ans is None:
            self._chat.insert("end", "(no model on the mesh answered — check ⚙ Setup)"
                              "\n\n", ("error",))
            self._status("No model answered.")
        else:
            ans = self._trim_followups(ans)
            self._history.append(("assistant", ans))
            self._append_prof(where, ans)
            self._status(f"Answered by {where}.")
        self._chat.see("end")
        self._save_current()

    # ── attach a file for the Professor to read ────────────────────────────────
    def _attach_file(self):
        """Pick a text file; its contents ride along with the NEXT Ask as context,
        then clear (one-shot). Big files are clipped to ATTACH_MAX chars so they fit
        the model's small window."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Attach a text file for the Professor to read",
            filetypes=[("Text", "*.txt *.md *.py *.json *.csv *.log *.fc *.flow *.gui"),
                       ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except Exception as e:                    # noqa: BLE001 — surfaced to the user
            self._status(f"Couldn't read that file: {e}")
            return
        name = os.path.basename(path)
        clipped = len(text) > self.ATTACH_MAX
        self._attachment = {"name": name, "text": text[:self.ATTACH_MAX],
                            "clipped": clipped}
        self._attachlbl.config(text=f"📎 {name}" + ("  (clipped)" if clipped else ""))
        self._status(f"Attached {name} — rides with your next Ask (📎 again to replace).")

    def _clear_attachment(self):
        self._attachment = None
        if hasattr(self, "_attachlbl"):
            self._attachlbl.config(text="")

    # ── transcript + conversation memory ──────────────────────────────────────
    def _begin_turn(self, prompt):
        """Record the turn, show 'You: …', clear the box (the turn now lives in the
        transcript), show a pending Professor line, and disable Ask until it lands."""
        if self._attachment:                       # note the attachment in the record
            prompt = f"{prompt}\n📎 [attached: {self._attachment['name']}]"
        self._history.append(("user", prompt))
        self._append_you(prompt)
        self._prompt.delete("1.0", "end")
        self._prompt.config(fg=self.C["text"])
        self._start_pending()
        self._askbtn.config(state="disabled", text="  …thinking  ")
        self._ask_result = None

    def _append_you(self, text):
        self._chat.insert("end", "You\n", ("who_you",))
        self._chat.insert("end", text + "\n\n", ("msg",))
        self._chat.see("end")

    def _append_prof(self, where, text):
        label = f"Professor · {where}" if where else "Professor"
        self._chat.insert("end", label + "\n", ("who_prof",))
        self._chat.insert("end", text + "\n\n", ("msg",))
        self._chat.see("end")

    def _start_pending(self):
        self._pending_idx = self._chat.index("end-1c")
        self._chat.insert("end", "Professor is thinking…\n\n", ("pending",))
        self._chat.see("end")

    def _end_pending(self):
        if self._pending_idx is not None:
            self._chat.delete(self._pending_idx, "end")
            self._pending_idx = None

    def _build_context(self, budget=2400):
        """The conversation so far, newest-first within a char budget (a small model
        has a tiny context window), rendered as a dialogue the model continues after
        the final 'Professor:'. This is what gives the Professor its memory."""
        lines, total = [], 0
        for role, text in reversed(self._history):
            tag = "You" if role == "user" else "Professor"
            chunk = f"{tag}: {text}\n"
            if total + len(chunk) > budget and lines:
                break
            lines.append(chunk)
            total += len(chunk)
        lines.reverse()
        prefix = ""
        if self._attachment:                       # the user's attached file, as context
            a = self._attachment
            tag = "  (truncated)" if a.get("clipped") else ""
            prefix = (f'[The user attached a file "{a["name"]}"{tag}. Its contents:]\n'
                      f'"""\n{a["text"]}\n"""\n\n')
        return prefix + "".join(lines) + "Professor:"

    @staticmethod
    def _trim_followups(ans):
        """A small model sometimes tacks the NEXT 'You:' turn onto its answer; cut
        it there so the transcript stays clean."""
        for marker in ("\nYou:", "\nUser:", "\nYou :", "\nHuman:"):
            i = ans.find(marker)
            if i != -1:
                ans = ans[:i]
        ans = ans.strip()
        # the completion-style context makes the model echo a "Professor…:" label;
        # the turn is already labelled, so strip a short leading one.
        if ans.lower().startswith("professor"):
            colon = ans.find(":")
            if 0 < colon < 40:
                ans = ans[colon + 1:].strip()
        return ans

    # ── clipboard + selection (copy/paste/select-all/undo, like the editor) ────
    def _wire_editing(self, text, editable):
        tk = self.tk
        menu = tk.Menu(text, tearoff=0)
        if editable:
            menu.add_command(label="Cut",
                             command=lambda: text.event_generate("<<Cut>>"))
        menu.add_command(label="Copy",
                         command=lambda: text.event_generate("<<Copy>>"))
        if editable:
            menu.add_command(label="Paste",
                             command=lambda: text.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Select All", command=lambda: self._select_all(text))

        def popup(e):
            try:
                menu.tk_popup(e.x_root, e.y_root)
            finally:
                menu.grab_release()

        text.bind("<Button-3>", popup)
        text.bind("<Control-a>", lambda e: self._select_all(text))
        text.bind("<Control-A>", lambda e: self._select_all(text))
        if not editable:                          # read-only, yet selectable/copyable
            text.bind("<KeyPress>", self._readonly_guard)
            text.bind("<Button-2>", lambda e: "break")   # no middle-click paste

    def _select_all(self, text):
        text.tag_add("sel", "1.0", "end-1c")
        text.mark_set("insert", "1.0")
        return "break"

    @staticmethod
    def _readonly_guard(e):
        # allow copy (Ctrl+C) + select-all (Ctrl+A) + navigation; block edits.
        if (e.state & 0x4) and e.keysym.lower() in ("c", "a"):
            return None
        if e.keysym in ("Left", "Right", "Up", "Down", "Home", "End", "Prior",
                        "Next", "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return None
        return "break"

    # ── named chats — portable saved conversations (p2pcp.chatstore) ────────────
    def _greeting(self):
        self._chat.insert("end", "You're connected to the mesh — ask the Professor "
                          "anything. The conversation is remembered as you go and "
                          "saved as a chat you can revisit (💬 top-right). ⚙ Setup "
                          "holds the nodes, your stall, and advanced options.\n\n",
                          ("sys",))
        self._chat.see("end")

    def _init_store(self):
        try:
            from p2pcp import chatstore
            self._store = chatstore.ChatStore()
        except Exception:                          # no store → chats just aren't saved
            self._store = None
        self._chat_id = None
        self._refresh_chat_menu()

    def _refresh_chat_menu(self):
        m = self._chatmenu
        m.delete(0, "end")
        title = "New chat"
        n = 0
        if self._store:
            for cid, ttl, _u in self._store.list()[:20]:
                mark = "•  " if cid == self._chat_id else "    "
                m.add_command(label=mark + ttl,
                              command=lambda c=cid: self._switch_chat(c))
                if cid == self._chat_id:
                    title = ttl
                n += 1
            if n:
                m.add_separator()
        m.add_command(label="＋  New chat", command=self._new_chat)
        m.add_command(label="✎  Rename current", command=self._rename_chat)
        m.add_command(label="🗑  Delete current", command=self._delete_chat)
        m.add_separator()
        m.add_command(label="⬇  Export chat…", command=self._export_chat)
        self._chatbtn.config(text=f"💬 {title[:26]} ▾")

    def _new_chat(self):
        self._history = []
        self._chat_id = None
        self._pending_idx = None
        self._chat.delete("1.0", "end")
        self._greeting()
        self._refresh_chat_menu()
        self._status("New chat.")

    def _switch_chat(self, cid):
        rec = self._store.load(cid) if self._store else None
        if not rec:
            return
        self._history = [(mm["role"], mm["text"]) for mm in rec.get("messages", [])]
        self._chat_id = cid
        self._render_history()
        self._refresh_chat_menu()
        self._status(f"Opened “{rec.get('title', 'chat')}”.")

    def _render_history(self):
        self._chat.delete("1.0", "end")
        self._greeting()
        for role, text in self._history:
            self._append_you(text) if role == "user" else self._append_prof(None, text)
        self._pending_idx = None

    def _save_current(self):
        if not self._store or not self._history:
            return
        if self._chat_id is None:
            self._chat_id = self._store.new_id()
        rec = self._store.load(self._chat_id)
        if rec and rec.get("title"):               # keep a renamed/existing title
            title = rec["title"]
        else:
            first = next((t for r, t in self._history if r == "user"), "")
            title = self._store.title_for(first)
        try:
            self._store.save(self._chat_id, title, self._history)
        except Exception:                          # a transient FS error must not
            pass                                   # break the chat
        self._refresh_chat_menu()

    def _rename_chat(self):
        if not self._store or self._chat_id is None:
            self._status("Send a message first — then the chat can be named.")
            return
        from tkinter import simpledialog
        rec = self._store.load(self._chat_id)
        new = simpledialog.askstring("Rename chat", "Title:",
                                     initialvalue=(rec or {}).get("title", ""),
                                     parent=self.root)
        if new and new.strip():
            self._store.rename(self._chat_id, new.strip())
            self._refresh_chat_menu()

    def _delete_chat(self):
        if not self._store or self._chat_id is None:
            self._status("Nothing saved to delete yet.")
            return
        self._store.delete(self._chat_id)
        self._new_chat()

    def _export_chat(self):
        """Save the whole conversation to a Markdown file (the dashboard's Export,
        brought across to the standalone/FlowCode client)."""
        if not self._history:
            self._status("Nothing to export yet — ask something first.")
            return
        from tkinter import filedialog
        title = "mesh-chat"
        if self._store and self._chat_id:
            rec = self._store.load(self._chat_id)
            if rec and rec.get("title"):
                title = rec["title"]
        safe = "".join(c if c.isalnum() or c in " -_" else "" for c in title).strip()
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export chat", defaultextension=".md",
            initialfile=(safe[:40] or "mesh-chat") + ".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt"), ("All files", "*")])
        if not path:
            return
        lines = [f"# {title}\n"]
        for role, text in self._history:
            lines.append(f"**{'You' if role == 'user' else 'Professor'}:**\n\n{text}\n")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines) + "\n")
            self._status(f"Exported {len(self._history)} messages → {path}")
        except OSError as e:
            self._status(f"Export failed: {e}")

    # ── relay address (away-from-home), persisted so the phone remembers it ─────
    @staticmethod
    def _relay_path():
        return os.path.expanduser("~/.p2pcp/relay")

    def _read_relay(self):
        try:
            with open(self._relay_path(), encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError:
            return ""

    def _save_relay(self, addr):
        try:
            os.makedirs(os.path.dirname(self._relay_path()), exist_ok=True)
            with open(self._relay_path(), "w", encoding="utf-8") as fh:
                fh.write(addr.strip() + "\n")
        except OSError:
            pass

    def _relay_addr(self):
        raw = self._relay.get().strip() if hasattr(self, "_relay") else ""
        if not raw:
            return None
        host, _, port = raw.rpartition(":")
        try:
            return (host or "127.0.0.1", int(port))
        except ValueError:
            return None

    def _clear_relay(self, clear_field=True):
        """Forget the saved relay (bore tunnels are ephemeral — a dead one must not
        resurrect on restart). The ✕ button also empties the box."""
        if clear_field and hasattr(self, "_relay"):
            self._relay.delete(0, "end")
            self._status("Relay cleared — using the LAN/mesh.")
        try:
            os.remove(self._relay_path())
        except OSError:
            pass

    # ── live board: reuse p2pcp.dashboard, drives conn status + drawer cards ────
    def _start_board(self):
        tk, C = self.tk, self.C
        mono = ("Monospace", 9)
        try:
            from p2pcp import dashboard as DASH    # shims already put p2pcp on path
        except Exception as e:                     # missing dep → degrade, keep tab
            self._conn.config(text=f"(live board unavailable: {e})")
            return
        self._DASH = DASH
        self._board_states = [DASH.NodeState(a) for a in DASH._configured_nodes()]
        # cards live in the Setup drawer's board holder
        holder = getattr(self, "_board_holder", None)
        for st in self._board_states:
            if holder is None:
                break
            f = tk.Frame(holder, bg=C["palette"])
            f.pack(fill="x", padx=4, pady=3)
            hd = tk.Label(f, text=st.addr, bg=C["palette"], fg=C["dim"], font=mono,
                          anchor="w"); hd.pack(fill="x", padx=6, pady=(3, 0))
            bl = tk.Label(f, text="0 CompuCoin", bg=C["palette"], fg=C["text"],
                          font=("Monospace", 13, "bold"), anchor="w")
            bl.pack(fill="x", padx=6)
            sb = tk.Label(f, text="", bg=C["palette"], fg=C["dim"], font=mono,
                          anchor="w"); sb.pack(fill="x", padx=6)
            mr = tk.Frame(f, bg=C["palette"]); mr.pack(fill="x", padx=6, pady=(1, 4))
            tk.Label(mr, text="compute", bg=C["palette"], fg=C["dim"],
                     font=("Monospace", 8)).pack(side="left")
            cv = tk.Canvas(mr, height=10, bg=C["bg"], highlightthickness=0)
            cv.pack(side="left", fill="x", expand=True, padx=6)
            rt = tk.Label(mr, text="0.0 ch/s", bg=C["palette"], fg=C["text"],
                          font=("Monospace", 8), width=10, anchor="e")
            rt.pack(side="right")
            self._cards.append((st, hd, bl, sb, cv, rt))
        self._board_stop = threading.Event()
        threading.Thread(target=self._board_loop, name="mesh-board",
                         daemon=True).start()
        self.root.after(400, self._paint_board)

    def _board_loop(self):
        # ONLY network I/O here — never touch Tk from this thread (Tkinter is not
        # thread-safe). The main-thread _paint_board reads these NodeStates.
        while not self._board_stop.is_set():
            for st in self._board_states:
                try:
                    st.poll()
                except Exception:                 # noqa: BLE001
                    pass
            self._board_stop.wait(max(0.5, self._DASH.POLL_MS / 1000.0))

    def _paint_board(self):
        C, GRN, RED = self.C, self.GRN, self.RED
        FG, DIM = C["text"], C["dim"]
        models = sum(1 for st in self._board_states
                     if st.online and "compute:float" in st.caps)
        online = sum(1 for st in self._board_states if st.online)
        if models:
            self._conn.config(text=f"●  ready — talking to the mesh  ·  {models} "
                              f"model{'s' if models != 1 else ''} online", fg=GRN)
        elif online:
            self._conn.config(text=f"◐  {online} node(s) online, but no model right "
                              "now — try ⚙ Setup", fg=DIM)
        else:
            self._conn.config(text="○  no nodes online — open ⚙ Setup to check",
                              fg=RED)
        for (st, hd, bl, sb, cv, rt) in self._cards:
            dot = "● online" if st.online else "○ offline"
            hd.config(text=f"{st.addr}   {dot}   {st.account}",
                      fg=DIM if st.online else RED)
            flow = (f"  +{st.coin_delta}" if st.coin_delta > 0
                    else (f"  {st.coin_delta}" if st.coin_delta < 0 else ""))
            bl.config(text=f"{st.balance} CompuCoin{flow}",
                      fg=(GRN if st.coin_delta > 0
                          else (RED if st.coin_delta < 0 else FG)))
            kind = ("a model · float" if "compute:float" in st.caps
                    else ("raw compute · native" if "compute:native" in st.caps
                          else "buy-only (no worker)"))
            sb.config(text=f"jobs {st.jobs}   chunks {st.chunks}   · sells {kind}")
            cps = st.chunks_per_sec()
            cv.delete("all")
            w = cv.winfo_width() or 240
            fill = max(0.0, min(1.0, cps / self._DASH.METER_FULL))
            if fill > 0:
                cv.create_rectangle(0, 0, int(w * fill), 10, fill=GRN, outline="")
            rt.config(text=f"{cps:.1f} ch/s")
        if not self._board_stop.is_set():
            self.root.after(int(self._DASH.POLL_MS), self._paint_board)

    # ── stall + peers (driven from the drawer) ─────────────────────────────────
    @staticmethod
    def _wallet_text(w):
        if not w or not w.get("account"):
            return "wallet: —    balance: 0 CompuCoin    votes: 0"
        return (f"wallet: {w['account'][:16]}…    balance: {w['balance']} "
                f"CompuCoin    votes: {w['weight_bearing']}")

    def _toggle_stall(self):
        if self.svc and self.svc.running:
            self.svc.stop()
            self.svc = None
            self._addr.config(text="(stall closed)")
            self._startbtn.config(text="Open stall")
            self._refresh_wallet()
            self._status("Your stall is closed.")
            return
        try:
            kind = self._role.get()
            wk = None if kind == "buy-only" else kind
            self.svc = SVC.MeshService(worker_kind=wk, mock=bool(self._mock.get()),
                                       seed="flowcode-stall")
            addr = self.svc.start("127.0.0.1", 0)
            self._addr.config(text=f"selling at {addr[0]}:{addr[1]}")
            self._startbtn.config(text="Close stall")
            self._refresh_wallet()
            self.root.after(3000, self._stall_tick)
            self._status(f"Your stall ({kind}) is open on {addr[0]}:{addr[1]}.")
        except Exception as e:                    # noqa: BLE001 — surfaced
            self._status(f"Stall failed to open: {e}")

    def _stall_tick(self):
        if self.svc and self.svc.running:
            self._refresh_wallet()
            self.root.after(3000, self._stall_tick)

    def _refresh_wallet(self):
        running = bool(self.svc and self.svc.running)
        if not hasattr(self, "_wallet"):
            return
        w = self.svc.wallet() if running else None
        self._wallet.config(text=self._wallet_text(w))
        s = (self.svc.stats() or {}) if running else {}
        self._meshstat.config(text=(f"peers {s.get('peers', 0)}   served "
                                    f"{s.get('jobs_served', 0)}" if running else ""))
        self._peerlist.delete(0, "end")
        for host, port in (self.svc.known_peers() if running else []):
            self._peerlist.insert("end", f"{host}:{port}")

    def _join(self):
        if not (self.svc and self.svc.running):
            self._status("Open your stall first (this joins from your node).")
            return
        host, _, port = self._joinentry.get().strip().rpartition(":")
        try:
            addr = (host or "127.0.0.1", int(port))
        except ValueError:
            self._status("Bad host:port.")
            return
        n = self.svc.join([addr])
        self._refresh_wallet()
        self._status(f"Joined; know {n} peer(s).")

    # ── help_extra: the tab's contribution to the shared Help window ───────────
    def help_extra(self, win):
        """Registered into the Mesh row of flowcode's TAB_CHROME so the ONE header
        `? Help` also offers the native trust diagram."""
        import tkinter as tk
        C = self.C
        tk.Button(win, text="Show the trust diagram",
                  command=self._show_diagram, bg=C["palette"], fg=C["text"],
                  font=("Monospace", 9), relief="flat",
                  activebackground=C["bg"], activeforeground=C["text"]
                  ).pack(side="bottom", pady=(2, 2))

    def _show_diagram(self):
        tk, C = self.tk, self.C
        win = tk.Toplevel(self.root)
        win.title("How you can trust a stranger")
        win.configure(bg=C["bg"])
        cv = tk.Canvas(win, width=620, height=335, bg=C["bg"], highlightthickness=0)
        cv.pack(padx=12, pady=12)
        self._draw_buy_diagram(cv, C)
        tk.Button(win, text="Close", command=win.destroy, bg=C["palette"],
                  fg=C["text"], font=("Monospace", 9), relief="flat",
                  activebackground=C["bg"], activeforeground=C["text"]
                  ).pack(side="bottom", pady=(0, 10))

    @staticmethod
    def _draw_buy_diagram(cv, C):
        """One paid job between two stalls, drawn natively (no image deps)."""
        amber, green, dark = "#c9a24a", "#5f9e6a", "#141414"
        dim, text, pal = C["dim"], C["text"], C["palette"]
        mono = ("Monospace", 9)

        def stall(x0, y0, x1, y1, label):
            cv.create_rectangle(x0, y0, x1, y1, fill=pal, outline=pal)
            cv.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=label, fill=text,
                           font=mono)

        def step(x0, x1, y, label):
            cv.create_line(x0, y, x1, y, fill=dim, arrow="last")
            cv.create_text(310, y - 12, text=label, fill=text, font=mono)

        stall(30, 15, 250, 50, "Your stall (you)")
        stall(370, 15, 590, 50, "Another stall")
        cv.create_line(140, 50, 140, 315, fill=dim, dash=(2, 3))
        cv.create_line(480, 50, 480, 315, fill=dim, dash=(2, 3))
        step(145, 475, 90, "1 · JOB: my question")
        step(475, 145, 122, "2 · RESULT: the answer")
        cv.create_rectangle(30, 140, 270, 182, fill=amber, outline=amber)
        cv.create_text(150, 154, text="3 · you re-run it yourself", fill=dark,
                       font=mono)
        cv.create_text(150, 170, text="pay only if it matches", fill=dark, font=mono)
        step(145, 475, 205, "4 · RECEIPT: IOU for k coins")
        step(475, 145, 237, "5 · ACK: co-signed")
        cv.create_rectangle(30, 258, 590, 296, fill=green, outline=green)
        cv.create_text(310, 277, text="coins settle:   you −k,   seller +k",
                       fill=dark, font=("Monospace", 9, "bold"))
        cv.create_text(310, 314, fill=dim, font=mono,
                       text="LLM answers can't be re-run — checked by redundancy "
                            "instead.")
