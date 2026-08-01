"""p2pcp_tab_view.py — the Mesh tab: P2PCP inside FlowCode/Academy.

Mounted by flowcode.py:  MeshTabView(parent_frame, C, root, set_status)

You land ALREADY talking to a model: a big prompt, a big answer, and one Ask
button that auto-routes to a live Professor on the mesh — no addresses, no ports,
no "open a stall" first. All the plumbing (which node, your own stall, peers,
GHOST classify) lives behind a ⚙ Setup drawer, out of sight until you want it.

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
        self._build(parent)

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self, parent):
        tk, C = self.tk, self.C
        mono = ("Monospace", 9)

        self._outer = tk.Frame(parent, bg=C["bg"])
        self._outer.pack(fill="both", expand=True)
        self._main = tk.Frame(self._outer, bg=C["bg"])
        self._main.pack(side="left", fill="both", expand=True)
        self._drawer = tk.Frame(self._outer, bg=C["palette"], width=400)  # hidden

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

        # the prompt — the dominant element
        tk.Label(self._main, text="Ask the mesh", bg=C["bg"], fg=C["text"],
                 font=("Monospace", 13, "bold"), anchor="w"
                 ).pack(side="top", fill="x", padx=12, pady=(6, 2))
        self._prompt = tk.Text(self._main, height=4, bg=C["palette"], fg=C["dim"],
                               insertbackground=C["text"], relief="flat",
                               font=("Monospace", 14), wrap="word", padx=8, pady=8)
        self._prompt.pack(side="top", fill="x", padx=12)
        self._prompt.insert("1.0", self.PLACEHOLDER)
        self._prompt.bind("<FocusIn>", self._clear_placeholder)
        self._prompt.bind("<Control-Return>", lambda e: (self._ask(), "break")[1])

        askrow = tk.Frame(self._main, bg=C["bg"])
        askrow.pack(side="top", fill="x", padx=12, pady=(6, 4))
        tk.Label(askrow, text="answers come from a live model on your mesh",
                 bg=C["bg"], fg=C["dim"], font=("Monospace", 8)).pack(side="left")
        self._askbtn = tk.Button(askrow, text="  Ask  ▶  ", command=self._ask,
                                 bg=self.GRN, fg="#0c0e14",
                                 font=("Monospace", 12, "bold"), relief="flat",
                                 activebackground="#57e0a0")
        self._askbtn.pack(side="right")

        # the answer — dominant, fills the rest
        af = tk.Frame(self._main, bg=C["bg"])
        af.pack(side="top", fill="both", expand=True, padx=12, pady=(4, 12))
        self._answer = tk.Text(af, bg="#0c0e14", fg=C["text"], relief="flat",
                               font=("Monospace", 12), wrap="word", padx=10,
                               pady=10, state="disabled")
        sb = tk.Scrollbar(af, orient="vertical", command=self._answer.yview)
        self._answer.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self._answer.pack(side="left", fill="both", expand=True)
        self._set_answer("Type a question above and press Ask — you're already "
                         "connected to the mesh. ⚙ Setup (top-right) has the nodes, "
                         "your own stall, and advanced options.", C["dim"])

        self._build_drawer(self._drawer)
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

        # advanced: talk to a specific node / classify with GHOST
        adv = section("Advanced — a specific node")
        arow = tk.Frame(adv, bg=C["bg"]); arow.pack(side="top", fill="x", pady=2)
        tk.Label(arow, text="node host:port", bg=C["bg"], fg=C["dim"], font=mono
                 ).pack(side="left", padx=(4, 2))
        self._target = dentry(arow, "127.0.0.1:9000", width=20)
        self._target.pack(side="left", padx=2)
        brow = tk.Frame(adv, bg=C["bg"]); brow.pack(side="top", fill="x")
        dbtn(brow, "Ask this node", lambda: self._buy_direct("ask"))
        dbtn(brow, "Classify (GHOST)", lambda: self._buy_direct("classify"))

    def _toggle_setup(self):
        if self._drawer_shown:
            self._drawer.pack_forget()
            self._drawer_shown = False
            self._setupbtn.config(text="⚙ Setup")
        else:
            self._drawer.pack(side="right", fill="y")
            self._drawer.pack_propagate(False)
            self._drawer_shown = True
            self._setupbtn.config(text="⚙ Setup ✕")
            self._refresh_wallet()

    # ── the default Ask: auto-route to a live model on the mesh ────────────────
    def _ask(self):
        prompt = self._prompt.get("1.0", "end").strip()
        if not prompt or prompt == self.PLACEHOLDER:
            self._status("Type a question first.")
            return
        cands = [(st.host, st.port) for st in self._board_states]
        if not cands:
            cands = [("127.0.0.1", 9000)]
        self._askbtn.config(state="disabled", text="  …thinking  ")
        self._set_answer("…asking a model on the mesh (a Professor can take a few "
                         "seconds)…", self.C["dim"])
        self._status("Asking the mesh…")

        self._ask_result = None

        def work():
            where = ans = err = None
            try:
                where, ans = self._buyer.ask_mesh(prompt, candidates=cands)
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
        if err:
            self._set_answer(f"Couldn't reach a model: {err}\n\nOpen ⚙ Setup to "
                             "check the mesh nodes.", self.RED)
            self._status("Ask failed.")
        elif not where or ans is None:
            self._set_answer("No model on the mesh answered just now. Open ⚙ Setup "
                             "to see which nodes are online.", self.C["dim"])
            self._status("No model answered.")
        else:
            self._set_answer(ans, self.C["text"])
            self._append_answer(f"\n\n— answered by {where}", self.C["dim"])
            self._status(f"Answered by {where}.")

    def _set_answer(self, text, color=None):
        self._answer.config(state="normal")
        self._answer.delete("1.0", "end")
        self._answer.insert("1.0", text)
        self._answer.config(state="disabled", fg=color or self.C["text"])

    def _append_answer(self, text, color=None):
        self._answer.config(state="normal")
        self._answer.insert("end", text)
        self._answer.config(state="disabled")

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

    # ── advanced: talk to a specific node (from the drawer) ────────────────────
    def _buy_direct(self, kind):
        host, _, port = self._target.get().strip().rpartition(":")
        try:
            host, port = (host or "127.0.0.1"), int(port)
        except ValueError:
            self._status("Bad host:port.")
            return
        text = self._prompt.get("1.0", "end").strip()
        if not text or text == self.PLACEHOLDER:
            self._status("Type a question first.")
            return
        self._askbtn.config(state="disabled", text="  …thinking  ")
        self._set_answer(f"…asking {host}:{port}…", self.C["dim"])
        self._ask_result = None

        def work():
            err = None
            try:
                ans = (self._buyer.ask(host, port, text) if kind == "ask"
                       else self._buyer.classify(host, port, text))
            except Exception as e:                # noqa: BLE001 — surfaced
                ans, err = None, str(e)
            self._ask_result = (f"{host}:{port}", ans, err)

        threading.Thread(target=work, daemon=True).start()
        self.root.after(150, self._ask_poll)

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
