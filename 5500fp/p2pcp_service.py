"""p2pcp_service.py — the bridge between P2PCP and the GUI (FlowCode/Academy).

A stateful mesh service the GUI panel sits thinly on top of: start a worker node
in the background, check the wallet, join a mesh, and buy compute from strangers.
Fully testable WITHOUT a screen — the GUI panel only wires buttons to these
methods, so all the logic is covered here.

One operator node BOTH sells (its worker serves inbound jobs) and buys (ask /
classify go out) under one identity and one wallet.

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load("p2pcp_daemon")
L = D.L
P = _load("p2pcp_bonsai")
GH = _load("p2pcp_ghost")
NODE = _load("p2pcp_node")


class MeshService:
    """The operator's mesh node, wrapped for the GUI. ``worker_kind`` is
    ``"professor"`` (Bonsai, float), ``"ghost"`` (native), or ``None`` (buy-only).
    ``keyfile`` persists identity + earnings; ``mock`` uses the echo professor."""

    # A model can take tens of seconds to answer (float inference); the buy client
    # must wait that long or it hangs up mid-answer and reports "no result" — the
    # bug behind an Ask that silently fails against a real Professor.
    MODEL_TIMEOUT = 240.0

    def __init__(self, worker_kind="professor", keyfile=None, mock=False,
                 seed="mesh-node", timeout=None):
        self.worker_kind = worker_kind
        self.keyfile = keyfile
        self.mock = mock
        self.seed = seed
        self.timeout = self.MODEL_TIMEOUT if timeout is None else timeout
        self._node = None
        self._addr = None
        self._buy_client = None

    # ── lifecycle ────────────────────────────────────────────────────────────
    def _make_worker(self):
        if self.worker_kind == "professor":
            backend = _load("bonsai_runner").EchoBackend() if self.mock else None
            return P.BonsaiWorker(backend=backend)
        if self.worker_kind == "ghost":
            return GH.GhostWorker()
        return None                                    # buy-only node

    def start(self, host="127.0.0.1", port=0):
        identity = NODE.node_identity(self.seed, self.keyfile)
        ledger = None
        if self.keyfile and os.path.exists(self.keyfile + ".ledger"):
            ledger = L.Ledger.load(self.keyfile + ".ledger")
            if not ledger.verify():                    # never run on tampered state
                raise ValueError("persisted ledger failed integrity check")
        self._node = D.Daemon(identity, worker=self._make_worker(), ledger=ledger,
                              timeout=self.timeout)
        self._addr = self._node.start(host, port)
        return self._addr

    def stop(self):
        if self._node is not None:
            self._node.stop()
            if self.keyfile:
                self._node.ledger.save(self.keyfile + ".ledger")
            self._node = None

    @property
    def running(self):
        return self._node is not None

    @property
    def address(self):
        return self._addr

    # ── mesh ─────────────────────────────────────────────────────────────────
    def join(self, peers):
        """Bootstrap into a mesh from [(host, port), ...]; return peers known."""
        return NODE.join_mesh(self._node, peers) if self._node else 0

    def known_peers(self):
        return sorted(self._node.known_peers()) if self._node else []

    def stats(self):
        """This node's own metrics (jobs served, peers, wallet)."""
        return self._node.stats() if self._node else None

    def peer_status(self, host, port):
        """A remote node's public status."""
        return self._client().fetch_status(host, int(port))

    # ── wallet ───────────────────────────────────────────────────────────────
    def wallet(self):
        if self._node is None:
            return {"account": None, "balance": 0, "weight_bearing": 0}
        acct, led = self._node.account_id, self._node.ledger
        here = acct in led.chains
        return {"account": acct.hex(),
                "balance": led.balance(acct) if here else 0,
                "weight_bearing": led.burnable(acct) if here else 0}

    # ── buy compute ──────────────────────────────────────────────────────────
    def _client(self):
        if self._node is not None:                 # a running stall buys under its wallet
            return self._node
        if self._buy_client is None:               # else a stable, model-patient buy client
            self._buy_client = D.Daemon(NODE.node_identity(self.seed + "-client"),
                                        timeout=self.timeout)
        return self._buy_client

    def ask(self, host, port, prompt, k=5):
        """Buy inference from a Professor node (float). Returns the answer, or None."""
        res = self._client().request_job(host, int(port), prompt.encode("utf-8"),
                                         n_chunks=1, k=k, vclass=L.VCLASS_FLOAT,
                                         audit=None)
        return self._answer(res)

    def classify(self, host, port, text, k=4):
        """Buy classification from a GHOST node, replay-audited. Returns class, or None."""
        res = self._client().request_job(host, int(port), text.encode("utf-8"),
                                         n_chunks=1, k=k, vclass=L.VCLASS_NATIVE,
                                         audit=GH.GhostWorker())
        return self._answer(res)

    def ask_mesh(self, prompt, k=5, candidates=None):
        """Buy inference from ANY Professor on the mesh: discover a compute:float
        provider and fall through if one is down. `candidates=None` scans the
        node's known peers. Returns (host:port, answer) or (None, None)."""
        addr, res = self._client().buy_from_mesh(
            "compute:float", prompt.encode("utf-8"), 1, k, L.VCLASS_FLOAT,
            audit=None, candidates=candidates)
        return self._located(addr, res)

    def classify_mesh(self, text, k=4, candidates=None):
        """Buy classification from ANY GHOST on the mesh (compute:native),
        replay-audited. Returns (host:port, class) or (None, None)."""
        addr, res = self._client().buy_from_mesh(
            "compute:native", text.encode("utf-8"), 1, k, L.VCLASS_NATIVE,
            audit=GH.GhostWorker(), candidates=candidates)
        return self._located(addr, res)

    @classmethod
    def _located(cls, addr, res):
        if not addr:
            return None, None
        return f"{addr[0]}:{addr[1]}", cls._answer(res)

    @staticmethod
    def _answer(res):
        if res["settled_chunks"] < 1:
            return None
        return res["outputs"][0].decode("utf-8", "replace")
