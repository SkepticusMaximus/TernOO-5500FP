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

        # toolbar: role + port + mock + start/stop + address
        bar = tk.Frame(parent, bg=C["palette"])
        bar.pack(side="top", fill="x")
        tk.Label(bar, text="role", bg=C["palette"], fg=C["dim"], font=mono
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
        self._startbtn = btn(bar, "Start node", self._toggle)
        self._addr = tk.Label(bar, text="(stopped)", bg=C["palette"], fg=C["dim"],
                              font=mono)
        self._addr.pack(side="left", padx=6)

        # wallet
        wf = tk.LabelFrame(parent, text=" Wallet ", bg=C["bg"], fg=C["text"],
                           font=mono)
        wf.pack(side="top", fill="x", padx=8, pady=6)
        self._wallet = tk.Label(wf, text=self._wallet_text(None), bg=C["bg"],
                                fg=C["text"], font=mono, anchor="w", justify="left")
        self._wallet.pack(side="left", padx=6, pady=4)
        self._meshstat = tk.Label(wf, text="", bg=C["bg"], fg=C["dim"], font=mono)
        self._meshstat.pack(side="left", padx=12)
        btn(wf, "Refresh", self._refresh_wallet, side="right")

        # peers — join a node, watch the book (auto-refreshed)
        pf = tk.LabelFrame(parent, text=" Peers ", bg=C["bg"], fg=C["text"],
                           font=mono)
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
        bf = tk.LabelFrame(parent, text=" Buy compute from the mesh ", bg=C["bg"],
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
            self._addr.config(text="(stopped)")
            self._startbtn.config(text="Start node")
            self._refresh_wallet()
            self._status("Mesh node stopped.")
            return
        try:
            kind = self._role.get()
            wk = None if kind == "buy-only" else kind
            self.svc = SVC.MeshService(worker_kind=wk, mock=bool(self._mock.get()),
                                       seed="flowcode-mesh")
            addr = self.svc.start("127.0.0.1", int(self._port.get() or 0))
            self._addr.config(text=f"{addr[0]}:{addr[1]}")
            self._startbtn.config(text="Stop node")
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
