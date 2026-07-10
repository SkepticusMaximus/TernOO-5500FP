"""p2pcp_node.py — launch a P2PCP node from the command line.

  python3 p2pcp_node.py professor [--host H] [--port P] [--seed S]
      Run a Professor worker node — it sells inference for CompuCoin. Ctrl-C stops.

  python3 p2pcp_node.py ask --port P [--host H] [--k N] [--seed S] "your question"
      Ask a Professor node a question, paying k CompuCoin for the answer.

The same CLI is the cross-box test when the second machine arrives: run `professor`
on one box and `ask` from the other — the wire is byte-identical to loopback.

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import argparse
import hashlib
import importlib.util as _ilu
import json
import os
import sys
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_HERE, "p2pcp.json")


def load_node_config(path=None):
    """Node defaults from p2pcp.json (host, port, keyfile, peers, mock, seed) —
    drop the file and run `p2pcp_node.py professor` with no flags. Never raises."""
    try:
        with open(path or CONFIG_FILE) as f:
            cfg = json.load(f)
        return cfg if isinstance(cfg, dict) else {}
    except (OSError, ValueError):
        return {}


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load("p2pcp_daemon")
P = _load("p2pcp_bonsai")
GH = _load("p2pcp_ghost")
L = D.L


def identity_from_seed(seed: str):
    """A stable identity from a seed phrase (repeatable runs). A production node
    persists its ed25519 key instead — see load_or_create_identity."""
    return L.Identity.from_seed(hashlib.sha256(seed.encode("utf-8")).digest())


def load_or_create_identity(path):
    """A node's PERSISTENT identity: load its ed25519 key from `path`, or create
    and save one (owner-only perms). A node keeps its account — and its earned
    CompuCoin — across restarts. This is host-app config (like an ssh key), not
    TernOO-internal content: P2PCP is host-agnostic (spec §0), no native key path."""
    if os.path.exists(path):
        with open(path) as f:
            return L.Identity.from_seed(bytes.fromhex(f.read().strip()))
    idn = L.Identity.generate()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(bytes(idn.signing_key).hex())
    return idn


def node_identity(seed=None, keyfile=None):
    """A node's identity: from a persistent keyfile if given, else a seed phrase."""
    if keyfile:
        return load_or_create_identity(keyfile)
    return identity_from_seed(seed or "node")


def _serve_worker(worker, label, host, port, identity, ledger_path=None,
                  peers=None):
    """Run a worker node (Professor or GHOST) until interrupted. `ledger_path`
    persists state across restarts; `peers` bootstraps into a mesh."""
    ledger = None
    if ledger_path and os.path.exists(ledger_path):
        ledger = L.Ledger.load(ledger_path)
        if not ledger.verify():
            print(f"[{label}] REFUSING TO START: ledger integrity check failed "
                  f"({ledger_path})", flush=True)
            return
    node = D.Daemon(identity, worker=worker, ledger=ledger)
    h, p = node.start(host, port)
    print(f"[{label}] listening on {h}:{p}", flush=True)
    print(f"[{label}] account {node.account_id.hex()[:16]}… — selling compute "
          f"for CompuCoin", flush=True)
    if peers:
        known = join_mesh(node, peers)
        print(f"[{label}] joined mesh via {len(peers)} seed(s); know {known} "
              f"peers", flush=True)
    print(f"[{label}] Ctrl-C to stop.", flush=True)
    try:
        threading.Event().wait()                   # serve until interrupted
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        if ledger_path:
            node.ledger.save(ledger_path)          # keep earnings across restarts
        earned = (node.ledger.balance(node.account_id)
                  if node.account_id in node.ledger.chains else 0)
        print(f"\n[{label}] stopped. earned {earned} CompuCoin.", flush=True)


def run_professor(host="127.0.0.1", port=0, seed="professor", mock=False,
                  keyfile=None, peers=None):
    """Start a Professor (Bonsai, float-class) node. `mock` runs the EchoBackend
    — a present-but-fake professor with no model, for demo/CI. `keyfile` persists
    the node's identity + earnings across restarts; `peers` bootstraps a mesh."""
    backend = _load("bonsai_runner").EchoBackend() if mock else None
    label = "professor (mock)" if mock else "professor"
    _serve_worker(P.BonsaiWorker(backend=backend), label, host, port,
                  node_identity(seed, keyfile),
                  ledger_path=(keyfile + ".ledger") if keyfile else None,
                  peers=peers)


def run_ghost(host="127.0.0.1", port=0, seed="ghost", keyfile=None, peers=None):
    """Start a GHOST (native, replay-class, weight-bearing) classifier node."""
    _serve_worker(GH.GhostWorker(), "ghost", host, port,
                  node_identity(seed, keyfile),
                  ledger_path=(keyfile + ".ledger") if keyfile else None,
                  peers=peers)


def ask(host, port, prompt, k=5, seed="client"):
    """Ask a Professor node a question, paying k CompuCoin. Returns
    (client_daemon, result). The caller stops the client when done."""
    client = D.Daemon(identity_from_seed(seed))
    res = client.request_job(host, int(port), prompt.encode("utf-8"),
                             n_chunks=1, k=k, vclass=L.VCLASS_FLOAT, audit=None)
    return client, res


def classify(host, port, text, k=4, seed="caller"):
    """Ask a GHOST node to classify text (native, replay-class). The client
    REPLAY-AUDITS with its own GhostWorker — paying only for work it re-derives."""
    client = D.Daemon(identity_from_seed(seed))
    res = client.request_job(host, int(port), text.encode("utf-8"), n_chunks=1,
                             k=k, vclass=L.VCLASS_NATIVE, audit=GH.GhostWorker())
    return client, res


def ask_mesh(peers, prompt, k=5, seed="client"):
    """Buy inference from ANY Professor among `peers`: discover a compute:float
    provider and fall through if one is down. Returns (client, addr, result)."""
    client = D.Daemon(identity_from_seed(seed))
    addr, res = client.buy_from_mesh("compute:float", prompt.encode("utf-8"),
                                     1, k, L.VCLASS_FLOAT, audit=None,
                                     candidates=peers)
    return client, addr, res


def classify_mesh(peers, text, k=4, seed="caller"):
    """Buy classification from ANY GHOST among `peers` (compute:native),
    replay-audited. Returns (client, addr, result)."""
    client = D.Daemon(identity_from_seed(seed))
    addr, res = client.buy_from_mesh("compute:native", text.encode("utf-8"),
                                     1, k, L.VCLASS_NATIVE, audit=GH.GhostWorker(),
                                     candidates=peers)
    return client, addr, res


def wallet(keyfile):
    """A node's account + CompuCoin, read from its persisted state — no server.
    `balance` is spendable; `weight_bearing` is the replay-class earnings that can
    be burned for a vote (§10)."""
    if not os.path.exists(keyfile):
        raise FileNotFoundError(f"no node key at {keyfile}")
    acct = load_or_create_identity(keyfile).account_id
    ledger_path = keyfile + ".ledger"
    ledger = (L.Ledger.load(ledger_path)
              if os.path.exists(ledger_path) else L.Ledger())
    if acct in ledger.chains:
        return {"account": acct.hex(), "balance": ledger.balance(acct),
                "weight_bearing": ledger.burnable(acct)}
    return {"account": acct.hex(), "balance": 0, "weight_bearing": 0}


def node_status(host, port, seed="observer"):
    """Fetch a node's public status (worker, caps, peers, jobs served)."""
    return D.Daemon(identity_from_seed(seed)).fetch_status(host, int(port))


def find_providers(cap, peers, seed="finder"):
    """Scan `peers` for nodes advertising compute class `cap` (e.g.
    'compute:native'). Returns matching (host, port) — discovery, not a buy."""
    return D.Daemon(identity_from_seed(seed)).find_providers(cap, peers)


def parse_peers(peers_csv):
    """'host:port,host:port' -> [(host, port), ...]."""
    out = []
    for item in (peers_csv or "").split(","):
        item = item.strip()
        if not item:
            continue
        host, _, port = item.rpartition(":")
        out.append((host or "127.0.0.1", int(port)))
    return out


def join_mesh(node, peers):
    """Join a mesh: seed the peer book from bootstrap peers, then discover more
    (best-effort — a dead seed is skipped). Returns the peer count now known."""
    for host, port in peers:
        node.add_peer(host, port)
    for host, port in peers:
        try:
            node.fetch_peers(host, port)
        except Exception:                              # a dead seed is not fatal
            pass
    return len(node.known_peers())


def main(argv=None):
    cfg = load_node_config()
    ap = argparse.ArgumentParser(prog="p2pcp_node",
                                 description="Launch a P2PCP node.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("professor", help="run a Professor worker node")
    pp.add_argument("--host", default=cfg.get("host", "127.0.0.1"))
    pp.add_argument("--port", type=int, default=cfg.get("port", 0))
    pp.add_argument("--seed", default=cfg.get("seed", "professor"))
    pp.add_argument("--mock", action="store_true", default=cfg.get("mock", False),
                    help="run a mock professor (EchoBackend) — no model needed")
    pp.add_argument("--keyfile", default=cfg.get("keyfile"),
                    help="persist node identity + earnings here")
    pp.add_argument("--peers", default=cfg.get("peers"),
                    help="bootstrap peers, host:port,host:port")
    pg = sub.add_parser("ghost", help="run a GHOST classifier worker node")
    pg.add_argument("--host", default=cfg.get("host", "127.0.0.1"))
    pg.add_argument("--port", type=int, default=cfg.get("port", 0))
    pg.add_argument("--seed", default=cfg.get("seed", "ghost"))
    pg.add_argument("--keyfile", default=cfg.get("keyfile"),
                    help="persist node identity + earnings here")
    pg.add_argument("--peers", default=cfg.get("peers"),
                    help="bootstrap peers, host:port,host:port")
    pa = sub.add_parser("ask", help="ask a Professor node a question (paid)")
    pa.add_argument("prompt")
    pa.add_argument("--host", default="127.0.0.1")
    pa.add_argument("--port", type=int, help="a specific node (else use --peers)")
    pa.add_argument("--peers", help="discover a Professor among these, host:port,...")
    pa.add_argument("--k", type=int, default=5)
    pa.add_argument("--seed", default="client")
    pc = sub.add_parser("classify", help="ask a GHOST node to classify text (paid)")
    pc.add_argument("text")
    pc.add_argument("--host", default="127.0.0.1")
    pc.add_argument("--port", type=int, help="a specific node (else use --peers)")
    pc.add_argument("--peers", help="discover a GHOST among these, host:port,...")
    pc.add_argument("--k", type=int, default=4)
    pc.add_argument("--seed", default="caller")
    pw = sub.add_parser("wallet", help="show a node's account + CompuCoin")
    pw.add_argument("--keyfile", required=True)
    ps = sub.add_parser("status", help="query a node's public status")
    ps.add_argument("--host", default="127.0.0.1")
    ps.add_argument("--port", type=int, required=True)
    pf = sub.add_parser("find", help="find mesh nodes serving a compute class")
    pf.add_argument("--class", dest="klass", choices=["native", "float"],
                    required=True, help="native (replay/GHOST) or float (Professor)")
    pf.add_argument("--peers", required=True,
                    help="candidate nodes, host:port,host:port")
    args = ap.parse_args(argv)

    if args.cmd == "professor":
        run_professor(args.host, args.port, args.seed, args.mock, args.keyfile,
                      parse_peers(args.peers))
    elif args.cmd == "ghost":
        run_ghost(args.host, args.port, args.seed, args.keyfile,
                  parse_peers(args.peers))
    elif args.cmd == "wallet":
        w = wallet(args.keyfile)
        print(f"account:        {w['account']}")
        print(f"balance:        {w['balance']} CompuCoin")
        print(f"weight-bearing: {w['weight_bearing']} (votes-worth, replay-class)")
    elif args.cmd == "status":
        st = node_status(args.host, args.port)
        if not st:
            print("[status] no response (node offline?)", file=sys.stderr)
            sys.exit(1)
        for k in ("account", "workers", "version", "caps", "peers", "jobs_served"):
            print(f"{k}: {st.get(k)}")
    elif args.cmd == "find":
        cap = "compute:" + args.klass
        hits = find_providers(cap, parse_peers(args.peers))
        if not hits:
            print(f"[find] no node advertising {cap}", file=sys.stderr)
            sys.exit(1)
        for h, p in hits:
            print(f"{h}:{p}")
    elif args.cmd in ("ask", "classify"):
        served = None
        if args.peers:                                 # discover across the mesh
            peers = parse_peers(args.peers)
            if args.cmd == "ask":
                client, served, res = ask_mesh(peers, args.prompt, args.k, args.seed)
            else:
                client, served, res = classify_mesh(peers, args.text, args.k,
                                                     args.seed)
            if res is None:                            # no provider settled
                print(f"[{args.cmd}] no provider on the mesh settled (all offline, "
                      f"refused, or failed audit).", file=sys.stderr)
                client.stop()
                sys.exit(1)
        elif args.port is not None:                    # a specific named node
            if args.cmd == "ask":
                client, res = ask(args.host, args.port, args.prompt, args.k, args.seed)
            else:
                client, res = classify(args.host, args.port, args.text, args.k,
                                       args.seed)
        else:
            ap.error(f"{args.cmd}: give --port (a node) or --peers (discover one)")
        try:
            if res["settled_chunks"] < 1:
                print(f"[{args.cmd}] nothing settled (node offline, refused, or "
                      f"audit failed).", file=sys.stderr)
                sys.exit(1)
            print(res["outputs"][0].decode("utf-8", "replace"))
            where = f" via {served[0]}:{served[1]}" if served else ""
            print(f"\n[{args.cmd}] paid {res['paid']} CompuCoin to "
                  f"{res['worker'].hex()[:16]}…{where}", file=sys.stderr)
        finally:
            client.stop()


if __name__ == "__main__":
    main()
