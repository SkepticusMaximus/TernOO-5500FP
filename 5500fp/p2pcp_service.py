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

    def __init__(self, worker_kind="professor", keyfile=None, mock=False,
                 seed="mesh-node"):
        self.worker_kind = worker_kind
        self.keyfile = keyfile
        self.mock = mock
        self.seed = seed
        self._node = None
        self._addr = None

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
        self._node = D.Daemon(identity, worker=self._make_worker(), ledger=ledger)
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
        return self._node or D.Daemon(NODE.node_identity(self.seed + "-client"))

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

    @staticmethod
    def _answer(res):
        if res["settled_chunks"] < 1:
            return None
        return res["outputs"][0].decode("utf-8", "replace")
