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
        btn(bar, " ?  Help ", self._show_help, side="right")

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

    # ── help: the market-stall walkthrough (native canvas, no image deps) ──────
    def _show_help(self):
        tk, C = self.tk, self.C
        mono = ("Monospace", 9)
        win = tk.Toplevel(self.root)
        win.title("Mesh tab — your stall on the CompuCoin market")
        win.configure(bg=C["bg"])

        tk.Label(win, text="Welcome to your stall on the CompuCoin market",
                 bg=C["bg"], fg=C["text"], font=("Monospace", 12, "bold"),
                 anchor="w").pack(side="top", fill="x", padx=12, pady=(12, 2))

        prose = "\n\n".join([
            "Here's the whole idea in one breath: your computer can do small AI "
            "jobs for other people and get paid in CompuCoin (think of it as "
            "tokens — fair money), and you can pay other people's computers to do "
            "jobs for you. No company sits in the middle taking a cut or holding "
            "your money. It's just stalls at a fair, trading with each other "
            "directly.",

            "If every number on the tab reads 0, nothing's wrong — it only means "
            "nobody has wandered over to your stall yet.",

            "Opening up takes about ten seconds: pick what you'd like to sell in "
            "the 'sell' box and click 'Open stall'. That's the whole ceremony. "
            "Everything else has a sensible default you can happily ignore until "
            "you get curious.",

            "What can I sell?  (the 'sell' box)\n"
            "A 'professor' is a chatty AI that answers questions, a bit like a "
            "little ChatGPT. A 'ghost' is a quick sorter that files a scrap of "
            "text into the right category. Or pick 'buy-only' if you don't fancy "
            "selling anything and just want to shop.",

            "Leave 'mock' ticked to begin with. It means 'pretend professor' — it "
            "lets you play with the whole tab without first downloading a big AI "
            "model. Untick it later, once you have the real model set up.",

            "What on earth is a 'port'?  (honestly, don't worry about it)\n"
            "A port is just a numbered door on your computer that other computers "
            "knock on to find you. Leave the box at 0 and the program quietly "
            "picks a free door for you. Once your stall is open, the address shown "
            "up top (something like 127.0.0.1:45461) is where visitors knock — and "
            "'127.0.0.1' is simply computer-speak for 'this very machine'.",

            "Your takings  (the wallet strip)\n"
            "'Account' is your name-badge at the fair (a long code, but it's "
            "yours). 'Balance' is the CompuCoin you've earned. 'Votes' is your say "
            "in how the market is run — you earn it by doing honest work that "
            "anyone can double-check. 'Peers' counts the other stalls you've met, "
            "and 'served' counts the jobs you've done for others.",

            "Meeting the other stalls  (the 'Other stalls' box)\n"
            "Type another stall's address, hit 'Join', and your stall strolls "
            "over, says hello, and they swap little black books of "
            "who-else-they-know. From one neighbour you slowly get introduced to "
            "the whole fair.",

            "Buying something  (the 'Buy from another stall' box)\n"
            "Type a stall's address, write your question, and press 'Ask' or "
            "'Classify'. Or press one of the '(mesh)' buttons and let the fair "
            "find a willing seller for you — it'll even skip any stalls that have "
            "packed up and gone home.",

            "And here's the part that makes all this safe with total strangers — "
            "see the picture below. When you buy a job, your own computer quietly "
            "redoes the work itself and checks the answer matches before a single "
            "coin leaves your wallet. So you never have to trust anyone: try to "
            "fob someone off with a dud, and you simply don't get paid.",
        ])
        # prose on the left, the picture on the right — a landscape window that
        # fits a laptop screen without the Close button sliding under the taskbar.
        tk.Button(win, text="Close", command=win.destroy, bg=C["palette"],
                  fg=C["text"], font=mono, relief="flat", activebackground=C["bg"],
                  activeforeground=C["text"]).pack(side="bottom", pady=(4, 12))

        mid = tk.Frame(win, bg=C["bg"])
        mid.pack(side="top", fill="both", expand=True, padx=12, pady=4)

        left = tk.Frame(mid, bg=C["bg"])
        left.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(left)
        sb.pack(side="right", fill="y")
        txt = tk.Text(left, height=17, width=54, bg=C["bg"], fg=C["text"],
                      relief="flat", font=mono, wrap="word", padx=6, pady=4,
                      spacing3=6, yscrollcommand=sb.set)
        txt.insert("1.0", prose)
        txt.config(state="disabled")
        txt.pack(side="left", fill="both", expand=True)
        sb.config(command=txt.yview)

        right = tk.Frame(mid, bg=C["bg"])
        right.pack(side="left", fill="y", padx=(14, 0))
        tk.Label(right, text="The clever bit — how you can trust a stranger:",
                 bg=C["bg"], fg=C["dim"], font=mono, anchor="w"
                 ).pack(side="top", fill="x", pady=(2, 4))
        cv = tk.Canvas(right, width=620, height=335, bg=C["bg"],
                       highlightthickness=0)
        cv.pack(side="top")
        self._draw_buy_diagram(cv, C)

        tk.Button(win, text="Close", command=win.destroy, bg=C["palette"],
                  fg=C["text"], font=mono, relief="flat", activebackground=C["bg"],
                  activeforeground=C["text"]).pack(side="bottom", pady=(0, 10))

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
