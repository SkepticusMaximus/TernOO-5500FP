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
W = _load("p2pcp_wire")           # the wire contract frames (§4 L2)
C = _load("p2pcp_consensus")      # the conflict-vote (§9 / step 6)

HELLO_TYPE = "P2PCP-HELLO-v0.1"
DEFAULT_TIMEOUT = 5.0             # a bound passed to recv — never a clock read

# Forward-compat / CGP coexistence (spec §15). A node advertises its protocol
# version and capabilities in HELLO; a peer records them but acts only on the
# ones it understands. This is the negotiation SEAM that lets a future CGP-aware
# node (advertising e.g. "citicoin") find its peers and coexist with plain
# CompuCoin nodes — WITHOUT pre-shaping CGP's (unfinished) geometry into v0.1.
PROTOCOL_VERSION = "0.2"
BASE_CAPS = ("compucoin",)       # the CompuCoin ledger capability; CGP adds more

# Eclipse resistance (§9.3). A bounded book with un-evictable ANCHORS + a cap on
# how many peers one informant can teach us per fetch, so an attacker cannot flood
# out our honest peers or fill our whole view from a single source.
MAX_PEERS = 64
MAX_LEARN_PER_FETCH = 8


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
                 timeout=DEFAULT_TIMEOUT, worker=None, caps=None):
        self.identity = identity
        self.ledger = ledger if ledger is not None else L.Ledger()
        self.alg = alg
        self.timeout = timeout
        self.worker = worker                   # a WorkerAdapter, or None (§3/§5)
        self.caps = tuple(caps) if caps else BASE_CAPS   # advertised capabilities
        self.max_peers = MAX_PEERS                        # eclipse resistance (§9.3)
        self.max_learn_per_fetch = MAX_LEARN_PER_FETCH
        self._anchors = set()                             # never-evicted peers
        self.organ = SOCK.SocketOrgan()
        self._peers = {}                       # verified account_id -> Peer
        self._events = queue.Queue()           # verified account_ids, for observers
        self._votes = queue.Queue()            # verified conflict-votes (§9)
        self._peer_book = set()                # known peer LISTEN addresses (v0.2)
        self._seen = set()                     # gossip dedup keys (v0.2 flood)
        self._vote_pool = {}                   # (account,height) -> [votes] (v0.2)
        self._seen_records = {}                # (account,height) -> first-seen id
        self._forks = {}                       # (account,height) -> (id_a,id_b)
        self._record_events = queue.Queue()    # gossiped records, for observers
        self._peer_caps = {}                   # account -> {version, caps} (§15)
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
            old = self._peers.get(account_id)
            self._peers[account_id] = peer
        if old is not None and old is not peer:
            old.close()                        # a reconnect replaces & closes the old
        self._events.put(account_id)

    # ── HELLO handshake (§4 wire, identity only) ─────────────────────────────
    def _hello_frame(self) -> bytes:
        nonce = os.urandom(16)
        msg = {"type": HELLO_TYPE, "account": self.account_id.hex(),
               "nonce": nonce.hex(), "alg": self.alg,
               "version": PROTOCOL_VERSION, "caps": list(self.caps)}
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
        # Record the peer's advertised version + capabilities (forward-compat,
        # §15): unknown caps are KEPT but not acted on, so a v0.1 node coexists
        # with a future CGP-aware peer without understanding "citicoin"/"cgp".
        self._peer_caps[account] = {"version": msg.get("version"),
                                    "caps": list(msg.get("caps", []))}
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
                account = self._handshake_inbound(peer)
                self._serve_peer(peer, account)
            except (HandshakeError, SOCK.OrganError):
                peer.close()                   # a stranger who fails HELLO is dropped

    # ── the wire contract (§4 L2 / §14 step 5) ───────────────────────────────
    # The PAID job. A requester streams a JOB; the worker runs it through its
    # adapter and streams RESULT chunks; each chunk is SETTLED before the next
    # (settlement granularity §11), so neither party is exposed for more than one
    # chunk of k units. The first job that crosses is already a paid job, settled
    # against the block-lattice (§14). Trust is never assumed: the requester can
    # REPLAY-AUDIT each chunk before paying (the determinism moat, §3/§10), and
    # the receipt commits to job+output MMID so any peer can challenge later (§7).

    def _ensure_open(self):
        if self.account_id not in self.ledger.chains:
            self.ledger.open_account(self.identity, self.alg)

    def _post_settle(self, receipt):
        """Post our own side of a both-signed receipt to our chain (§5)."""
        chain = self.ledger.chains[self.account_id]
        self.ledger.post(L.build_settle_record(self.identity, chain, receipt,
                                               self.alg), receipt)

    # -- worker role (runs in the accept loop, after inbound HELLO) ------------
    def _serve_peer(self, peer, peer_id):
        """Seam filled (steps 5-6). Dispatch on the peer's first frame: a JOB is
        run if we carry a worker adapter; a VOTE is verified and collected (§9)."""
        try:
            frame = W.decode(peer.recv(timeout=self.timeout))
        except (SOCK.OrganError, ValueError):
            return
        t = frame.get("t")
        if t == W.JOB and self.worker is not None:
            self._work_job(peer, peer_id, frame)
        elif t == W.VOTE:
            self._collect_vote(frame)
        elif t == W.RECORD:
            self._collect_record(frame)
        elif t == W.PEERS_REQ:
            self._send_peer_book(peer)

    def _work_job(self, peer, requester_id, job):
        self._ensure_open()
        cargo = bytes.fromhex(job["job"])
        job_mmid = bytes.fromhex(job["job_mmid"])
        n_chunks, k, vclass = int(job["n_chunks"]), int(job["k"]), int(job["vclass"])
        # Verify-on-fetch on the wire (§12.4): the cargo must match its wire MMID.
        try:
            L.verify_wire_cargo(job_mmid, cargo, self.alg)
        except L.WireMmidError:
            peer.send(W.encode({"t": W.DONE, "reason": "bad-job-mmid"}))
            return
        # Honesty about class (§3): the worker advertises its adapter's TRUE class.
        if self.worker.vclass != vclass:
            peer.send(W.encode({"t": W.DONE, "reason": "vclass-mismatch"}))
            return

        for i in range(n_chunks):
            try:
                output = self.worker.run_chunk(cargo, i)
            except Exception:                      # adapter cannot deliver more
                peer.send(W.encode({"t": W.DONE, "reason": "worker-halt"}))
                return
            output_mmid = L.wire_mmid(output, self.alg)
            peer.send(W.encode({"t": W.RESULT, "i": i, "output": output.hex(),
                                "output_mmid": output_mmid.hex()}))
            # Settle THIS chunk before delivering the next (exposure ≤ k, §11).
            try:
                rf = W.decode(peer.recv(timeout=self.timeout))
            except (SOCK.OrganError, ValueError):
                return                             # requester vanished → stop
            if rf.get("t") != W.RECEIPT:
                return                             # requester won't pay → stop
            receipt = W.receipt_from_dict(L.Receipt, rf["receipt"])
            if not self._receipt_ok(receipt, requester_id, job_mmid, output_mmid,
                                    k, vclass):
                return
            receipt.worker_sig = self.identity.sign(receipt.signing_bytes(), self.alg)
            try:
                self._post_settle(receipt)         # our +k, weight-bearing if native
            except L.P2PCPError:
                return
            peer.send(W.encode({"t": W.RECEIPT_ACK,
                                "receipt": W.receipt_to_dict(receipt)}))
        peer.send(W.encode({"t": W.DONE, "reason": "complete"}))

    def _receipt_ok(self, r, requester_id, job_mmid, output_mmid, k, vclass):
        """The requester's receipt must bind THIS chunk to us, and its signature
        must verify — the counterparty-signature check (§8), on the wire."""
        if r.worker_id != self.account_id or r.requester_id != requester_id:
            return False
        if r.amount != k or r.job_commit != job_mmid:
            return False
        if r.output_commit != output_mmid or r.vclass != vclass:
            return False
        return L.get_alg(r.alg).verify(requester_id, r.requester_sig,
                                       r.signing_bytes())

    # -- requester role -------------------------------------------------------
    def request_job(self, host, port, job: bytes, n_chunks: int, k: int,
                    vclass=L.VCLASS_NATIVE, audit=None):
        """Dial a worker, stream a JOB, and pay per delivered+verified chunk.
        Returns a summary dict. If ``audit`` (a deterministic worker adapter of
        the same class) is supplied, each chunk is REPLAYED and compared before
        paying — the determinism moat as a pre-payment check (§3/§10); a forged
        output is never paid for. Exposure is bounded to one chunk of k (§11)."""
        self._ensure_open()
        peer = self.organ.connect(host, port, timeout=self.timeout)
        settled = 0
        receipts = []
        try:
            worker_id = self._handshake_outbound(peer)
            job_mmid = L.wire_mmid(job, self.alg)
            peer.send(W.encode({"t": W.JOB, "job": job.hex(),
                                "job_mmid": job_mmid.hex(), "n_chunks": n_chunks,
                                "k": k, "vclass": vclass}))
            for i in range(n_chunks):
                try:
                    rf = W.decode(peer.recv(timeout=self.timeout))
                except (SOCK.OrganError, ValueError):
                    break
                if rf.get("t") != W.RESULT:
                    break                          # DONE / halt → worker stopped
                output = bytes.fromhex(rf["output"])
                output_mmid = bytes.fromhex(rf["output_mmid"])
                # The worker's bytes must match its OWN claimed commitment...
                if L.wire_mmid(output, self.alg) != output_mmid:
                    break
                # ...and if we can replay it, we refuse to pay for a forgery (§3).
                if audit is not None and audit.run_chunk(job, i) != output:
                    break
                nonce = os.urandom(16)
                receipt = L.Receipt(worker_id, self.account_id, k, job_mmid,
                                    output_mmid, vclass, nonce, self.alg)
                receipt.requester_sig = self.identity.sign(receipt.signing_bytes(),
                                                           self.alg)
                peer.send(W.encode({"t": W.RECEIPT,
                                    "receipt": W.receipt_to_dict(receipt)}))
                try:
                    af = W.decode(peer.recv(timeout=self.timeout))
                except (SOCK.OrganError, ValueError):
                    break
                if af.get("t") != W.RECEIPT_ACK:
                    break                          # not co-signed → we don't pay
                acked = W.receipt_from_dict(L.Receipt, af["receipt"])
                # The worker must co-sign the SAME terms we signed (§8).
                if acked.signing_bytes() != receipt.signing_bytes():
                    break
                if not L.get_alg(self.alg).verify(worker_id, acked.worker_sig,
                                                  receipt.signing_bytes()):
                    break
                receipt.worker_sig = acked.worker_sig
                try:
                    self._post_settle(receipt)     # our −k obligation (§5)
                except L.P2PCPError:
                    break
                receipts.append(receipt)
                settled += 1
            return {"worker": worker_id, "settled_chunks": settled,
                    "paid": settled * k, "receipts": receipts}
        finally:
            peer.close()

    # ── consensus votes (§9 / step 6) ────────────────────────────────────────
    def cast_vote(self, account: bytes, height: int, choice: bytes):
        """Sign a vote on a fork of `account` at `height`, backing record `choice`
        (§9). The voter's weight is its decayed burn, computed by whoever tallies
        (§6) — the vote carries the claim, not the weight."""
        return C.sign_vote(self.identity, account, height, choice, self.alg)

    def _send_frame(self, host, port, frame):
        """Dial a peer, HELLO, send one frame, close — the unit of gossip."""
        peer = self.organ.connect(host, port, timeout=self.timeout)
        try:
            self._handshake_outbound(peer)
            peer.send(W.encode(frame))
        finally:
            peer.close()

    def _fanout_frame(self, frame):
        """Send a frame to every peer in the book; a dead peer is skipped, not
        fatal. Returns the count reached."""
        sent = 0
        for host, port in list(self._peer_book):
            try:
                self._send_frame(host, port, frame)
                sent += 1
            except SOCK.OrganError:
                continue
        return sent

    def send_vote(self, host, port, vote):
        """Carry a signed vote to a peer over the one organ."""
        self._send_frame(host, port, {"t": W.VOTE, "vote": vote.to_dict()})

    def _collect_vote(self, frame):
        vote = C.Vote.from_dict(frame["vote"])
        if not C.verify_vote(vote):        # a forged/unsigned vote is dropped (§9)
            return
        mid = self._gossip_id(vote.signing_bytes())
        if mid in self._seen:              # already heard it — drop, do NOT re-relay
            return                         # dedup: this is what stops a broadcast storm
        self._seen.add(mid)
        self._pool_vote(vote)              # collect into the observer queue + fork pool
        self._fanout_vote(vote)            # relay onward — the flood (v0.2)

    def next_vote(self, timeout=DEFAULT_TIMEOUT):
        """Block until the next verified vote arrives; return it."""
        return self._votes.get(timeout=timeout)

    # ── the mesh: peer book, discovery, broadcast (v0.2 gossip substrate) ─────
    # v0.1 was strictly point-to-point; v0.2 makes a node reach a SET of peers.
    # The book holds only reachable LISTEN addresses (never an inbound peer's
    # ephemeral port). A diverse book is the first line against eclipse (§9.3);
    # multi-hop relay + dedup flooding, and quorum assembly on a fork, are the
    # next slices.

    def add_anchor(self, host, port):
        """Add a sticky, never-evicted peer (eclipse resistance §9.3). Anchors are
        the honest bootstrap an attacker cannot flood out — NOT a trusted tier
        (§2.2): an anchor can still lie; it just cannot be silently evicted."""
        addr = (host, int(port))
        if addr != self.organ.address:
            self._anchors.add(addr)
            self.add_peer(host, port)

    def add_peer(self, host, port):
        """Seed or learn a peer's listen address (never ourselves). Bounded: at
        the cap a NON-anchor is evicted to make room; anchors are never evicted,
        so an attacker flooding addresses cannot push out our honest peers."""
        addr = (host, int(port))
        if addr == self.organ.address or addr in self._peer_book:
            return
        if len(self._peer_book) >= self.max_peers and addr not in self._anchors:
            evictable = self._peer_book - self._anchors
            if not evictable:
                return                         # book full of anchors — refuse
            self._peer_book.discard(next(iter(evictable)))
        self._peer_book.add(addr)

    def known_peers(self):
        return set(self._peer_book)

    def peer_capabilities(self, account):
        """The protocol version + capabilities a peer advertised in HELLO (§15
        forward-compat / CGP coexistence). None if we have not handshaked it."""
        return self._peer_caps.get(account)

    def _send_peer_book(self, peer):
        """Answer a PEERS_REQ with our book plus our own listen address, so the
        asker discovers the mesh from a seed (v0.2)."""
        addrs = [[h, p] for (h, p) in self._peer_book]
        if self.organ.address is not None:
            addrs.append([self.organ.address[0], self.organ.address[1]])
        try:
            peer.send(W.encode({"t": W.PEERS, "peers": addrs}))
        except SOCK.OrganError:
            pass

    def fetch_peers(self, host, port):
        """Discovery: ask a peer for its book and merge it, but learn at most
        `max_learn_per_fetch` new peers from this ONE informant — so a single
        (possibly malicious) source cannot fill our whole book (eclipse resistance
        §9.3). Returns the newly-learned addresses. The mesh still self-assembles
        from a seed, just not from a single mouth."""
        peer = self.organ.connect(host, port, timeout=self.timeout)
        learned = set()
        try:
            self._handshake_outbound(peer)
            peer.send(W.encode({"t": W.PEERS_REQ}))
            resp = W.decode(peer.recv(timeout=self.timeout))
            if resp.get("t") == W.PEERS:
                for hp in resp.get("peers", []):
                    if len(learned) >= self.max_learn_per_fetch:
                        break
                    addr = (hp[0], int(hp[1]))
                    if addr != self.organ.address and addr not in self._peer_book:
                        self.add_peer(*addr)
                        learned.add(addr)
        finally:
            peer.close()
        return learned

    def _gossip_id(self, payload: bytes):
        """Content-addressed dedup key for a gossiped item — every node derives
        the SAME id from the same content, so a flooded item is recognized and
        dropped everywhere it has already been."""
        return L.wire_mmid(payload, self.alg)

    def _fanout_vote(self, vote):
        return self._fanout_frame({"t": W.VOTE, "vote": vote.to_dict()})

    def broadcast_vote(self, vote):
        """Originate a vote to the mesh (v0.2): count it locally, mark it seen (so
        an echo back is deduped), then fan it out. Recipients RELAY it onward — the
        flood — and dedup stops it circulating forever, so it reaches non-adjacent
        nodes without a broadcast storm. Returns the count of direct peers reached.

        (NB v0.2: `_seen`/`_vote_pool` are unbounded here; a bounded/expiring
        seen-set is a later hardening. Fan-out excludes-sender is a later
        optimization — dedup already makes an echo harmless.)"""
        mid = self._gossip_id(vote.signing_bytes())
        if mid not in self._seen:
            self._seen.add(mid)
            self._pool_vote(vote)          # count our OWN vote in our own pool
        return self._fanout_vote(vote)

    # ── distributed quorum assembly on a fork (v0.2 slice 3) ──────────────────
    # Votes are GOSSIPED (slice 2), never POLLED — so there is no solicitation
    # loop to DDOS a peer book with (the throttle is the architecture): a node
    # announces its vote ONCE (deduped), the flood delivers it, and every node
    # accumulates the votes it hears into a per-fork pool and tallies LOCALLY with
    # the step-6 rule. Consensus converges because the tally is deterministic —
    # same votes + same weights -> same verdict, at every node.

    def _pool_vote(self, vote):
        """Record a verified vote on the observer queue AND in the per-fork pool
        keyed by (account, height)."""
        self._votes.put(vote)
        self._vote_pool.setdefault((vote.account, vote.height), []).append(vote)

    def votes_for(self, account, height):
        """The votes this node has heard for a fork (account @ height)."""
        return list(self._vote_pool.get((account, height), []))

    def announce_fork(self, account, height, choice):
        """Cast this node's vote for `choice` on a fork and gossip it — no polling,
        the flood does the delivery. Returns the vote."""
        vote = self.cast_vote(account, height, choice)
        self.broadcast_vote(vote)
        return vote

    def resolve_fork(self, fork, weights, slashed=None):
        """Tally the votes heard for this fork with the step-6 rule (§9): a branch
        wins iff it holds >= 2/3 of participating decayed weight, else None
        (undecided — optimistic wait). A decided fork slashes its author."""
        if slashed is None:
            slashed = set()
        return C.resolve(fork, self.votes_for(fork.account, fork.height),
                         weights, slashed)

    # ── record + fork gossip (v0.2 slice 4) ──────────────────────────────────
    # Records gossip so a node can WITNESS branches it did not originate. A node
    # remembers the FIRST record it sees at each (account, height); a later,
    # different record at the same slot is a FORK — a double-spend, since both are
    # self-signed by that account. On detecting one, the node votes for its
    # first-seen branch (the block-lattice rule) and that vote joins the quorum
    # flood (slice 3). A record that fails its self-signature is never relayed.

    def gossip_record(self, record):
        """Originate a record to the mesh: ingest locally, then flood it."""
        rid = record.record_id()
        if rid not in self._seen:
            self._seen.add(rid)
            self._ingest_record(record)
        self._fanout_frame({"t": W.RECORD, "record": W.record_to_dict(record)})

    def _collect_record(self, frame):
        record = W.record_from_dict(L.Record, frame["record"])
        # A record must be validly self-signed by its own account (§5/§8); a
        # forged record is dropped and never relayed.
        try:
            if not L.get_alg(record.alg).verify(record.account, record.sig,
                                                record.signing_bytes()):
                return
        except L.AlgError:
            return
        rid = record.record_id()
        if rid in self._seen:
            return                             # dedup — heard it, don't re-relay
        self._seen.add(rid)
        self._ingest_record(record)
        self._fanout_frame({"t": W.RECORD, "record": frame["record"]})   # relay

    def _ingest_record(self, record):
        key = (record.account, record.height)
        rid = record.record_id()
        seen = self._seen_records.get(key)
        if seen is None:
            self._seen_records[key] = rid      # first-seen for this slot
        elif seen != rid and key not in self._forks:
            # a different record at the same (account, height) — a FORK detected
            # from gossip. Vote for our FIRST-SEEN branch; the vote joins the
            # quorum flood (slice 3) and burn-weight resolves it.
            self._forks[key] = tuple(sorted((seen, rid)))
            self.announce_fork(record.account, record.height, seen)
        self._record_events.put(record)        # observe LAST — state has settled

    def first_seen(self, account, height):
        return self._seen_records.get((account, height))

    def detected_forks(self):
        return dict(self._forks)

    def next_record(self, timeout=DEFAULT_TIMEOUT):
        return self._record_events.get(timeout=timeout)
