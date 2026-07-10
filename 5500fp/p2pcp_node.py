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
import os
import sys
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load("p2pcp_daemon")
P = _load("p2pcp_bonsai")
L = D.L


def identity_from_seed(seed: str):
    """A stable identity from a seed phrase (repeatable runs). A production node
    would persist its ed25519 key; this derives one deterministically."""
    return L.Identity.from_seed(hashlib.sha256(seed.encode("utf-8")).digest())


def run_professor(host="127.0.0.1", port=0, seed="professor", mock=False):
    """Start a Professor node and serve inference until interrupted. `mock` runs
    the EchoBackend — a present-but-fake professor with no model, for demo/CI."""
    backend = _load("bonsai_runner").EchoBackend() if mock else None
    prof = D.Daemon(identity_from_seed(seed),
                    worker=P.BonsaiWorker(backend=backend))
    h, p = prof.start(host, port)
    tag = " (mock)" if mock else ""
    print(f"[professor] listening on {h}:{p}{tag}", flush=True)
    print(f"[professor] account {prof.account_id.hex()[:16]}… — selling inference "
          f"for CompuCoin", flush=True)
    print("[professor] Ctrl-C to stop.", flush=True)
    try:
        threading.Event().wait()                   # serve until interrupted
    except KeyboardInterrupt:
        pass
    finally:
        prof.stop()
        earned = (prof.ledger.balance(prof.account_id)
                  if prof.account_id in prof.ledger.chains else 0)
        print(f"\n[professor] stopped. earned {earned} CompuCoin.", flush=True)


def ask(host, port, prompt, k=5, seed="client"):
    """Ask a Professor node a question, paying k CompuCoin. Returns
    (client_daemon, result). The caller stops the client when done."""
    client = D.Daemon(identity_from_seed(seed))
    res = client.request_job(host, int(port), prompt.encode("utf-8"),
                             n_chunks=1, k=k, vclass=L.VCLASS_FLOAT, audit=None)
    return client, res


def main(argv=None):
    ap = argparse.ArgumentParser(prog="p2pcp_node",
                                 description="Launch a P2PCP node.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pp = sub.add_parser("professor", help="run a Professor worker node")
    pp.add_argument("--host", default="127.0.0.1")
    pp.add_argument("--port", type=int, default=0)
    pp.add_argument("--seed", default="professor")
    pp.add_argument("--mock", action="store_true",
                    help="run a mock professor (EchoBackend) — no model needed")
    pa = sub.add_parser("ask", help="ask a Professor node a question (paid)")
    pa.add_argument("prompt")
    pa.add_argument("--host", default="127.0.0.1")
    pa.add_argument("--port", type=int, required=True)
    pa.add_argument("--k", type=int, default=5)
    pa.add_argument("--seed", default="client")
    args = ap.parse_args(argv)

    if args.cmd == "professor":
        run_professor(args.host, args.port, args.seed, args.mock)
    elif args.cmd == "ask":
        client, res = ask(args.host, args.port, args.prompt, args.k, args.seed)
        try:
            if res["settled_chunks"] < 1:
                print("[ask] no answer settled (professor offline or refused).",
                      file=sys.stderr)
                sys.exit(1)
            print(res["outputs"][0].decode("utf-8", "replace"))
            print(f"\n[ask] paid {res['paid']} CompuCoin to "
                  f"{res['worker'].hex()[:16]}…", file=sys.stderr)
        finally:
            client.stop()


if __name__ == "__main__":
    main()
