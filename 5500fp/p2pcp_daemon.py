"""p2pcp_daemon.py — the node daemon skeleton (host app). Build step 4 (§14).

P2PCP reference implementation. The daemon is the host app that owns the node's
three parts and wires them together (RFC §4 node anatomy):

    Daemon (this file: keys + ledger state + the organ + accept loop)
      → SocketOrgan   (p2pcp_socket — the ONE network limb, §1.5)
      → Ledger        (p2pcp_ledger — the TCM + block-lattice, §5/§8)
      → worker adapters / wire contract   (SEAM — steps 5-6)

**This module does NOT import `socket`.** All network I/O goes through the organ
(§1.5) — the one-organ boundary holds. It is a SKELETON: it can listen, dial,
and complete a signed HELLO handshake that establishes *verified identity over
the wire* (trustless — any stranger may HELLO), and it exposes the seam where the
ledger-settled wire contract (step 5: "the first job that crosses is already a
paid job") plugs in. The paid contract itself is deliberately NOT here yet.

What HELLO proves and does not: it proves the peer controls the private key for
the account it announces (they produced a valid ed25519 signature over their
announcement, via the same `alg` table the ledger uses). Per-session liveness /
anti-replay is established by the wire contract's own signed, nonce'd frames in
step 5 — noted at the seam, not faked here. Trust is never granted by the socket;
identity is a key, and standing is burn-weight, both above this layer.

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import json
import os
import queue
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SOCK = _load("p2pcp_socket")      # the ONE network organ (no socket import here)
L = _load("p2pcp_ledger")         # Identity, Ledger, the alg table (§12)

HELLO_TYPE = "P2PCP-HELLO-v0.1"
DEFAULT_TIMEOUT = 5.0             # a bound passed to recv — never a clock read


class DaemonError(Exception):
    """Base for daemon-level failures."""


class HandshakeError(DaemonError):
    """A HELLO frame was malformed, of the wrong type, or carried an invalid
    signature. The peer is dropped cleanly (§2.1: trust is earned above)."""


def _canon(obj: dict) -> bytes:
    """Same deterministic canonical form the ledger uses (sorted keys, tight
    separators, UTF-8) so a stranger reproduces the signed bytes exactly (§0)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


class Daemon:
    """One P2PCP node. Owns an Identity, a Ledger, and the single SocketOrgan.

    Skeleton surface: ``start`` / ``stop`` / ``connect``. Inbound peers are
    handshaken by a background accept loop; each verified peer is recorded and
    announced on an event queue. The wire contract plugs in at ``_serve_peer``."""

    def __init__(self, identity, ledger=None, alg=L.ALG_ED25519,
                 timeout=DEFAULT_TIMEOUT):
        self.identity = identity
        self.ledger = ledger if ledger is not None else L.Ledger()
        self.alg = alg
        self.timeout = timeout
        self.organ = SOCK.SocketOrgan()
        self._peers = {}                       # verified account_id -> Peer
        self._events = queue.Queue()           # verified account_ids, for observers
        self._lock = threading.Lock()
        self._running = False
        self._accept_thread = None

    @property
    def account_id(self) -> bytes:
        return self.identity.account_id

    # ── lifecycle ───────────────────────────────────────────────────────────
    def start(self, host: str = "127.0.0.1", port: int = 0):
        """Open the organ's listener and spawn the accept loop. Returns the bound
        (host, port)."""
        addr = self.organ.listen(host, port)
        self._running = True
        self._accept_thread = threading.Thread(
            target=self._accept_loop, name="p2pcp-accept", daemon=True)
        self._accept_thread.start()
        return addr

    def stop(self):
        """Stop accepting, close the organ, drop every peer. Idempotent."""
        self._running = False
        self.organ.close()                     # unblocks accept → loop exits
        if self._accept_thread is not None:
            self._accept_thread.join(2.0)
            self._accept_thread = None
        with self._lock:
            for peer in self._peers.values():
                peer.close()
            self._peers.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.stop()

    # ── peers ───────────────────────────────────────────────────────────────
    def peers(self):
        with self._lock:
            return dict(self._peers)

    def next_verified_peer(self, timeout=DEFAULT_TIMEOUT):
        """Block until the next inbound peer is verified; return its account_id.
        (Test/observer affordance — a real supervisor would subscribe here.)"""
        return self._events.get(timeout=timeout)

    def _record(self, account_id: bytes, peer):
        with self._lock:
            self._peers[account_id] = peer
        self._events.put(account_id)

    # ── HELLO handshake (§4 wire, identity only) ─────────────────────────────
    def _hello_frame(self) -> bytes:
        nonce = os.urandom(16)
        msg = {"type": HELLO_TYPE, "account": self.account_id.hex(),
               "nonce": nonce.hex(), "alg": self.alg}
        sig = self.identity.sign(_canon(msg), self.alg)
        return _canon({"msg": msg, "sig": sig.hex()})

    def _verify_hello(self, frame: bytes) -> bytes:
        try:
            env = json.loads(frame)
            msg = env["msg"]
            sig = bytes.fromhex(env["sig"])
            account = bytes.fromhex(msg["account"])
            alg = msg["alg"]
        except (ValueError, KeyError, TypeError) as e:
            raise HandshakeError(f"malformed HELLO: {e}") from e
        if msg.get("type") != HELLO_TYPE:
            raise HandshakeError(f"not a HELLO: {msg.get('type')!r}")
        # The alg selector is honoured through the ledger's table: an unknown or
        # unimplemented alg is refused gracefully, on the wire as in the ledger.
        try:
            ok = L.get_alg(alg).verify(account, sig, _canon(msg))
        except L.AlgError as e:
            raise HandshakeError(f"HELLO alg refused: {e}") from e
        if not ok:
            raise HandshakeError("HELLO signature invalid — key not controlled")
        return account

    def _handshake_outbound(self, peer) -> bytes:
        peer.send(self._hello_frame())
        account = self._verify_hello(peer.recv(timeout=self.timeout))
        self._record(account, peer)
        return account

    def _handshake_inbound(self, peer) -> bytes:
        account = self._verify_hello(peer.recv(timeout=self.timeout))
        peer.send(self._hello_frame())
        self._record(account, peer)
        return account

    # ── connect out ─────────────────────────────────────────────────────────
    def connect(self, host: str, port: int) -> bytes:
        """Dial a peer and complete the outbound HELLO. Returns the peer's
        VERIFIED account_id. After this, step 5's wire contract would run over
        the same peer (see ``_serve_peer``)."""
        peer = self.organ.connect(host, port, timeout=self.timeout)
        try:
            return self._handshake_outbound(peer)
        except (HandshakeError, SOCK.OrganError):
            peer.close()
            raise

    # ── accept loop ─────────────────────────────────────────────────────────
    def _accept_loop(self):
        while self._running:
            try:
                peer = self.organ.accept(timeout=0.3)
            except SOCK.OrganTimeout:
                continue
            except SOCK.OrganError:
                break                          # organ closed → stop() in progress
            try:
                self._handshake_inbound(peer)
                self._serve_peer(peer)
            except (HandshakeError, SOCK.OrganError):
                peer.close()                   # a stranger who fails HELLO is dropped

    def _serve_peer(self, peer):
        """SEAM for step 5-6. Today: nothing — HELLO done, peer registered. Here
        the ledger-settled wire contract runs: read JOB/RESULT/RECEIPT frames,
        validate through the TCM (self.ledger), settle per chunk (settlement
        granularity, §11), and the first job that crosses is already a PAID job.
        Left explicitly empty so step 4 lands as a skeleton, not half a step 5."""
        return None
