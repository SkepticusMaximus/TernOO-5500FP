"""p2pcp_tab_view.py — the Mesh tab: P2PCP inside FlowCode/Academy.

Mounted by flowcode.py:  MeshTabView(parent_frame, C, root, set_status)

A thin panel over p2pcp_service.MeshService (all logic is tested there, no screen
needed): start a worker node, watch your CompuCoin wallet, and BUY compute from
strangers — sell and buy AI compute from the GUI. `tkinter` is imported inside
__init__ so this module loads headless (only instantiation needs a display).

Date: 2026-07-10, Adelaide
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
    def __init__(self, parent, C, root, set_status):
        import tkinter as tk
        self.tk = tk
        self.C, self.root, self._status = C, root, set_status
        self.svc = None
        self._build(parent)

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self, parent):
        tk, C = self.tk, self.C
        mono = ("Monospace", 9)

        def btn(where, text, cmd, side="left"):
            b = tk.Button(where, text=text, command=cmd, bg=C["palette"],
                          fg=C["text"], font=mono, relief="flat",
                          activebackground=C["bg"], activeforeground=C["text"])
            b.pack(side=side, padx=6, pady=2)
            return b

        def entry(where, value, width=None):
            e = tk.Entry(where, bg=C["bg"], fg=C["text"], insertbackground=C["text"],
                         relief="flat", font=mono,
                         **({"width": width} if width else {}))
            e.insert(0, value)
            return e

        # the guiding metaphor: a stall on the CompuCoin market
        tk.Label(parent,
                 text="  The CompuCoin market — your stall on the mesh:  sell "
                      "compute to strangers, buy it from them, no middleman.  ",
                 bg=C["palette"], fg=C["dim"], font=mono, anchor="w"
                 ).pack(side="top", fill="x")

        # The standalone dashboard, folded in: a live board of the REAL running
        # nodes (wallets, what each sells, a compute meter), polled off-thread.
        self._build_market_board(parent)

        # toolbar: what you sell + port + mock + open/close + address + help
        bar = tk.Frame(parent, bg=C["palette"])
        bar.pack(side="top", fill="x")
        tk.Label(bar, text="sell", bg=C["palette"], fg=C["dim"], font=mono
                 ).pack(side="left", padx=(6, 2))
        self._role = tk.StringVar(value="professor")
        rm = tk.OptionMenu(bar, self._role, "professor", "ghost", "buy-only")
        rm.config(bg=C["palette"], fg=C["text"], font=mono, relief="flat",
                  highlightthickness=0, activebackground=C["bg"])
        rm.pack(side="left", padx=(0, 8))
        tk.Label(bar, text="port", bg=C["palette"], fg=C["dim"], font=mono
                 ).pack(side="left")
        self._port = entry(bar, "0", width=6)
        self._port.pack(side="left", padx=(2, 8))
        self._mock = tk.IntVar(value=1)
        tk.Checkbutton(bar, text="mock", variable=self._mock, bg=C["palette"],
                       fg=C["text"], selectcolor=C["bg"], font=mono,
                       activebackground=C["palette"]).pack(side="left")
        self._startbtn = btn(bar, "Open stall", self._toggle)
        self._addr = tk.Label(bar, text="(stall closed)", bg=C["palette"],
                              fg=C["dim"], font=mono)
        self._addr.pack(side="left", padx=6)
        # No local "? Help" here — the tab's single Help affordance lives in the
        # shared header strip (TAB_CHROME). flowcode registers help_extra() so that
        # header ? Help still offers the trust diagram. (Chrome-contract, 2026-07-12.)

        # wallet
        wf = tk.LabelFrame(parent, text=" Your takings (wallet) ", bg=C["bg"],
                           fg=C["text"], font=mono)
        wf.pack(side="top", fill="x", padx=8, pady=6)
        self._wallet = tk.Label(wf, text=self._wallet_text(None), bg=C["bg"],
                                fg=C["text"], font=mono, anchor="w", justify="left")
        self._wallet.pack(side="left", padx=6, pady=4)
        self._meshstat = tk.Label(wf, text="", bg=C["bg"], fg=C["dim"], font=mono)
        self._meshstat.pack(side="left", padx=12)
        btn(wf, "Refresh", self._refresh_wallet, side="right")

        # peers — join a node, watch the book (auto-refreshed)
        pf = tk.LabelFrame(parent, text=" Other stalls (peers) ", bg=C["bg"],
                           fg=C["text"], font=mono)
        pf.pack(side="top", fill="x", padx=8, pady=6)
        prow = tk.Frame(pf, bg=C["bg"])
        prow.pack(side="top", fill="x", pady=2)
        tk.Label(prow, text="join host:port", bg=C["bg"], fg=C["dim"], font=mono
                 ).pack(side="left", padx=(6, 2))
        self._joinentry = entry(prow, "127.0.0.1:9000", width=22)
        self._joinentry.pack(side="left", padx=2)
        btn(prow, "Join", self._join)
        self._peerlist = tk.Listbox(pf, height=4, bg=C["bg"], fg=C["text"],
                                    font=mono, relief="flat", highlightthickness=0,
                                    selectbackground=C["palette"])
        self._peerlist.pack(side="top", fill="x", padx=6, pady=4)

        # buy compute
        bf = tk.LabelFrame(parent, text=" Buy from another stall ", bg=C["bg"],
                           fg=C["text"], font=mono)
        bf.pack(side="top", fill="both", expand=True, padx=8, pady=6)
        row = tk.Frame(bf, bg=C["bg"])
        row.pack(side="top", fill="x", pady=4)
        tk.Label(row, text="node host:port", bg=C["bg"], fg=C["dim"], font=mono
                 ).pack(side="left", padx=(6, 2))
        self._target = entry(row, "127.0.0.1:9000", width=22)
        self._target.pack(side="left", padx=2)
        self._prompt = entry(bf, "what is balanced ternary?")
        self._prompt.pack(side="top", fill="x", padx=6, pady=4)
        brow = tk.Frame(bf, bg=C["bg"])
        brow.pack(side="top", fill="x")
        btn(brow, "Ask (Professor)", lambda: self._buy("ask"))
        btn(brow, "Classify (GHOST)", lambda: self._buy("classify"))
        btn(brow, "Ask (mesh)", lambda: self._buy_mesh("ask"))
        btn(brow, "Classify (mesh)", lambda: self._buy_mesh("classify"))
        self._result = tk.Text(bf, height=6, bg=C["bg"], fg=C["text"],
                               insertbackground=C["text"], relief="flat",
                               font=mono, wrap="word")
        self._result.pack(side="top", fill="both", expand=True, padx=6, pady=4)

    # ── live market board: the standalone dashboard, folded in ─────────────────
    # Reuses p2pcp.dashboard's NodeState/rate engine verbatim to poll the REAL
    # running nodes (from ~/.p2pcp/nodes.txt) and paint per-node cards — wallet,
    # what each sells, and a chunks/sec compute meter. Polling runs OFF the GUI
    # thread so a slow or absent node never freezes the IDE; the paint is marshalled
    # back onto the Tk thread via root.after(0). This is the dashboard the captain
    # watched work, now inside the Mesh tab and themed with the shared C palette.
    def _build_market_board(self, parent):
        tk, C = self.tk, self.C
        mono = ("Monospace", 9)
        try:
            from p2pcp import dashboard as DASH     # shims already put p2pcp on path
        except Exception as e:                      # missing dep → degrade, keep tab
            tk.Label(parent, text=f"  (live board unavailable: {e})  ", bg=C["bg"],
                     fg=C["dim"], font=mono).pack(side="top", fill="x", padx=8)
            return
        self._DASH = DASH
        self._GRN, self._RED = "#3fd08f", "#e06a6a"
        self._board_states = [DASH.NodeState(a) for a in DASH._configured_nodes()]
        board = tk.LabelFrame(parent, text=" Live mesh — the real nodes ",
                              bg=C["bg"], fg=C["text"], font=mono)
        board.pack(side="top", fill="x", padx=8, pady=6)
        self._cards = []
        for st in self._board_states:
            f = tk.Frame(board, bg=C["palette"])
            f.pack(fill="x", padx=6, pady=3)
            head = tk.Label(f, text=st.addr, bg=C["palette"], fg=C["dim"],
                            font=mono, anchor="w")
            head.pack(fill="x", padx=6, pady=(3, 0))
            bal = tk.Label(f, text="0 CompuCoin", bg=C["palette"], fg=C["text"],
                           font=("Monospace", 14, "bold"), anchor="w")
            bal.pack(fill="x", padx=6)
            sub = tk.Label(f, text="", bg=C["palette"], fg=C["dim"], font=mono,
                           anchor="w")
            sub.pack(fill="x", padx=6)
            mrow = tk.Frame(f, bg=C["palette"])
            mrow.pack(fill="x", padx=6, pady=(1, 4))
            tk.Label(mrow, text="compute", bg=C["palette"], fg=C["dim"],
                     font=("Monospace", 8)).pack(side="left")
            cv = tk.Canvas(mrow, height=10, bg=C["bg"], highlightthickness=0)
            cv.pack(side="left", fill="x", expand=True, padx=6)
            rate = tk.Label(mrow, text="0.0 ch/s", bg=C["palette"], fg=C["text"],
                            font=("Monospace", 8), width=10, anchor="e")
            rate.pack(side="right")
            self._cards.append((st, head, bal, sub, cv, rate))
        self._board_stop = threading.Event()
        threading.Thread(target=self._board_loop, name="mesh-board",
                         daemon=True).start()
        self.root.after(400, self._paint_board)     # main-thread paint loop

    def _board_loop(self):
        # ONLY network I/O here — never touch Tk from this thread (Tkinter is not
        # thread-safe; cross-thread .after() silently fails to dispatch). The
        # main-thread _paint_board reads these NodeStates and repaints on its own
        # cadence, so a slow/absent node blocks only this thread, never the IDE.
        while not self._board_stop.is_set():
            for st in self._board_states:
                try:
                    st.poll()                       # STATUS over the wire, OFF the GUI thread
                except Exception:                   # noqa: BLE001 — never kill the loop
                    pass
            self._board_stop.wait(max(0.5, self._DASH.POLL_MS / 1000.0))

    def _paint_board(self):
        GRN, RED, FG, DIM = self._GRN, self._RED, self.C["text"], self.C["dim"]
        for (st, head, bal, sub, cv, rate) in self._cards:
            dot = "● online" if st.online else "○ offline"
            head.config(text=f"{st.addr}    {dot}    {st.account}",
                        fg=DIM if st.online else RED)
            flow = (f"  +{st.coin_delta}" if st.coin_delta > 0
                    else (f"  {st.coin_delta}" if st.coin_delta < 0 else ""))
            bal.config(text=f"{st.balance} CompuCoin{flow}",
                       fg=(GRN if st.coin_delta > 0
                           else (RED if st.coin_delta < 0 else FG)))
            kind = ("a model · float" if "compute:float" in st.caps
                    else ("raw compute · native" if "compute:native" in st.caps
                          else "buy-only (no worker)"))
            sub.config(text=f"jobs {st.jobs}   chunks {st.chunks}   · sells {kind}")
            cps = st.chunks_per_sec()
            cv.delete("all")
            w = cv.winfo_width() or 260
            fill = max(0.0, min(1.0, cps / self._DASH.METER_FULL))
            if fill > 0:
                cv.create_rectangle(0, 0, int(w * fill), 10, fill=GRN, outline="")
            rate.config(text=f"{cps:.1f} ch/s")
        if not self._board_stop.is_set():
            self.root.after(int(self._DASH.POLL_MS), self._paint_board)  # reschedule (GUI thread)

    # ── actions (delegate to the tested MeshService) ──────────────────────────
    @staticmethod
    def _wallet_text(w):
        if not w or not w.get("account"):
            return "account: —    balance: 0 CompuCoin    votes: 0"
        return (f"account: {w['account'][:16]}…    balance: {w['balance']} "
                f"CompuCoin    votes: {w['weight_bearing']}")

    def _toggle(self):
        if self.svc and self.svc.running:
            self.svc.stop()
            self.svc = None
            self._addr.config(text="(stall closed)")
            self._startbtn.config(text="Open stall")
            self._refresh_wallet()
            self._status("Mesh node stopped.")
            return
        try:
            kind = self._role.get()
            wk = None if kind == "buy-only" else kind
            self.svc = SVC.MeshService(worker_kind=wk, mock=bool(self._mock.get()),
                                       seed="flowcode-mesh")
            addr = self.svc.start("127.0.0.1", int(self._port.get() or 0))
            self._addr.config(text=f"open at {addr[0]}:{addr[1]}")
            self._startbtn.config(text="Close stall")
            self._refresh_wallet()
            self.root.after(3000, self._tick)           # live auto-refresh
            self._status(f"Mesh node ({kind}) on {addr[0]}:{addr[1]}.")
        except Exception as e:                          # noqa: BLE001 — surfaced
            self._status(f"Mesh start failed: {e}")

    def _tick(self):
        if self.svc and self.svc.running:
            self._refresh_wallet()
            self.root.after(3000, self._tick)

    def _refresh_wallet(self):
        running = bool(self.svc and self.svc.running)
        w = self.svc.wallet() if running else None
        self._wallet.config(text=self._wallet_text(w))
        s = (self.svc.stats() or {}) if running else {}
        self._meshstat.config(
            text=(f"peers: {s.get('peers', 0)}    served: {s.get('jobs_served', 0)}"
                  if running else ""))
        self._peerlist.delete(0, "end")                # live peer book
        for host, port in (self.svc.known_peers() if running else []):
            self._peerlist.insert("end", f"{host}:{port}")

    def _join(self):
        if not (self.svc and self.svc.running):
            self._status("Start a node first.")
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

    def _buy_mesh(self, kind):
        """Buy from ANY provider on the mesh — discover + fall through, no target
        typed. Shows which node served."""
        if not (self.svc and self.svc.running):
            self._status("Start a node first.")
            return
        text = self._prompt.get()
        self._result.delete("1.0", "end")
        self._result.insert("end", "(discovering a provider…)")
        self._status(f"Buying {kind} from the mesh…")

        def work():
            err = where = ans = None
            try:
                where, ans = (self.svc.ask_mesh(text) if kind == "ask"
                              else self.svc.classify_mesh(text))
            except Exception as e:                      # noqa: BLE001 — surfaced
                err = str(e)
            self.root.after(0, lambda: self._show_mesh(where, ans, err))

        threading.Thread(target=work, daemon=True).start()

    def _show_mesh(self, where, ans, err):
        self._result.delete("1.0", "end")
        if err:
            self._result.insert("end", f"error: {err}")
            self._status("Mesh buy failed.")
        elif not where or ans is None:
            self._result.insert("end", "(no provider on the mesh settled)")
            self._status("No mesh provider settled.")
        else:
            self._result.insert("end", f"{ans}\n\n— served by {where}")
            self._refresh_wallet()
            self._status(f"Bought from {where}.")

    def _buy(self, kind):
        if not (self.svc and self.svc.running):
            self._status("Start a node first.")
            return
        host, _, port = self._target.get().strip().rpartition(":")
        try:
            host, port = (host or "127.0.0.1"), int(port)
        except ValueError:
            self._status("Bad host:port.")
            return
        text = self._prompt.get()
        self._result.delete("1.0", "end")
        self._result.insert("end", "(working…)")
        self._status(f"Buying {kind} from {host}:{port}…")

        def work():
            err = None
            try:
                ans = (self.svc.ask(host, port, text) if kind == "ask"
                       else self.svc.classify(host, port, text))
            except Exception as e:                      # noqa: BLE001 — surfaced
                ans, err = None, str(e)
            self.root.after(0, lambda: self._show(ans, err))

        threading.Thread(target=work, daemon=True).start()

    def _show(self, ans, err):
        self._result.delete("1.0", "end")
        if err:
            self._result.insert("end", f"error: {err}")
            self._status("Buy failed.")
        elif ans is None:
            self._result.insert("end",
                                "(no result — node offline, refused, or audit failed)")
            self._status("No result settled.")
        else:
            self._result.insert("end", ans)
            self._refresh_wallet()
            self._status("Bought — wallet updated.")

    # ── help_extra: the tab's contribution to the shared Help window ───────────
    def help_extra(self, win):
        """Registered into the Mesh row of flowcode's TAB_CHROME so the ONE header
        `? Help` (which opens the shared helpdown viewer at the 'mesh' topic) also
        offers the native trust diagram. The buy-handshake diagram stays a native
        canvas — rendering it inside helpdown is Pass 2. Signature is `(win)` to
        match open_help_window's `extra(win)` contract."""
        import tkinter as tk
        C = self.C
        tk.Button(win, text="Show the trust diagram",
                  command=self._show_diagram, bg=C["palette"], fg=C["text"],
                  font=("Monospace", 9), relief="flat",
                  activebackground=C["bg"], activeforeground=C["text"]
                  ).pack(side="bottom", pady=(2, 2))

    def _show_diagram(self):
        """Pop the buy-handshake diagram on its own native canvas."""
        tk, C = self.tk, self.C
        win = tk.Toplevel(self.root)
        win.title("How you can trust a stranger")
        win.configure(bg=C["bg"])
        cv = tk.Canvas(win, width=620, height=335, bg=C["bg"],
                       highlightthickness=0)
        cv.pack(padx=12, pady=12)
        self._draw_buy_diagram(cv, C)
        tk.Button(win, text="Close", command=win.destroy, bg=C["palette"],
                  fg=C["text"], font=("Monospace", 9), relief="flat",
                  activebackground=C["bg"], activeforeground=C["text"]
                  ).pack(side="bottom", pady=(0, 10))

    # ── the native buy-handshake diagram (kept for the ? Help window) ──────────
    @staticmethod
    def _draw_buy_diagram(cv, C):
        """One paid job between two stalls, drawn natively (no SVG/image deps)."""
        amber, green, dark = "#c9a24a", "#5f9e6a", "#141414"
        dim, text, pal = C["dim"], C["text"], C["palette"]
        mono = ("Monospace", 9)

        def stall(x0, y0, x1, y1, label):
            cv.create_rectangle(x0, y0, x1, y1, fill=pal, outline=pal)
            cv.create_text((x0 + x1) / 2, (y0 + y1) / 2, text=label, fill=text,
                           font=mono)

        def step(x0, x1, y, label):                    # arrow + its label
            cv.create_line(x0, y, x1, y, fill=dim, arrow="last")
            cv.create_text(310, y - 12, text=label, fill=text, font=mono)

        stall(30, 15, 250, 50, "Your stall (you)")
        stall(370, 15, 590, 50, "Another stall")
        cv.create_line(140, 50, 140, 315, fill=dim, dash=(2, 3))     # lifelines
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
