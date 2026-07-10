#!/usr/bin/env python3
"""p2pcp_demo.py — the whole P2PCP mesh in one command.

Spins up three worker nodes and a client on loopback, joins them into one mesh,
and runs one paid transaction of EACH verification class (§3):

  ① ask a Professor      — float-class: earns money, never a vote (llama-style)
  ② classify via GHOST   — native-class: replay-audited, weight-bearing
  ③ compute on the 5500FP — native-class: bit-exact ternary, weight-bearing

Then prints every node's wallet. It doubles as a smoke test: ``run_demo()``
returns the results and asserts each class settled. No model, no network config,
no second box — just ``python3 p2pcp_demo.py``.

Run:  cd 5500fp && python3 p2pcp_demo.py
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
N = _load("p2pcp_node")
P = _load("p2pcp_bonsai")
GH = _load("p2pcp_ghost")
EM = _load("p2pcp_emulator")
B = _load("bonsai_runner")
L = D.L


def _wallet(node):
    acct = node.account_id
    here = acct in node.ledger.chains
    return {"balance": node.ledger.balance(acct) if here else 0,
            "weight_bearing": node.ledger.burnable(acct) if here else 0}


def run_demo(verbose=True):
    """Run the full three-class mesh session; return a results dict. Asserts each
    class settled so this is also a smoke test."""
    def say(*a):
        if verbose:
            print(*a)

    def rule():
        say("─" * 62)

    prof = D.Daemon(N.identity_from_seed("demo-professor"),
                    worker=P.BonsaiWorker(backend=B.EchoBackend()))
    ghost = D.Daemon(N.identity_from_seed("demo-ghost"), worker=GH.GhostWorker())
    emu = D.Daemon(N.identity_from_seed("demo-emulator"),
                   worker=EM.EmulatorWorker())
    p_addr, g_addr, e_addr = prof.start(), ghost.start(), emu.start()
    client = D.Daemon(N.identity_from_seed("demo-client"))
    for a in (p_addr, g_addr, e_addr):                 # the client joins the mesh
        client.add_peer(*a)

    out = {}
    try:
        rule()
        say("P2PCP mesh — 3 workers + 1 client on loopback")
        rule()
        say(f"  Professor (float)   @ {p_addr[0]}:{p_addr[1]}  {sorted(prof.caps)}")
        say(f"  GHOST (native)      @ {g_addr[0]}:{g_addr[1]}  {sorted(ghost.caps)}")
        say(f"  Emulator (native)   @ {e_addr[0]}:{e_addr[1]}  {sorted(emu.caps)}")

        rule()
        say("Discovery — find_providers over the client's peer book:")
        floats = client.find_providers("compute:float")
        natives = client.find_providers("compute:native")
        say(f"  compute:float  -> {floats}")
        say(f"  compute:native -> {natives}")
        out["discovery"] = {"float": floats, "native": natives}

        rule()
        say("① ask a Professor  (float — money, never a vote)")
        where, ares = client.buy_from_mesh(
            "compute:float", b"what is balanced ternary?", 1, 5, L.VCLASS_FLOAT,
            audit=None, candidates=[p_addr])
        answer = ares["outputs"][0].decode("utf-8", "replace")
        say(f"   served by {where[0]}:{where[1]}")
        say(f"   answer: {answer[:56]}…")
        out["ask"] = {"served_by": where, "answer": answer}

        rule()
        say("② classify via GHOST  (native — replay-audited, a vote)")
        gres = client.request_job(g_addr[0], g_addr[1], b"save the file", 1, 3,
                                  vclass=L.VCLASS_NATIVE, audit=GH.GhostWorker())
        say(f"   class: {gres['outputs'][0].decode('utf-8', 'replace')}")
        out["classify"] = {"settled": gres["settled_chunks"],
                           "class": gres["outputs"][0]}

        rule()
        say("③ compute on the 5500FP  (native — bit-exact ternary, a vote)")
        prog, in_reg, out_regs = EM.demo_program()
        job = EM.program_job(prog, in_reg, out_regs)
        eres = client.request_job(e_addr[0], e_addr[1], job, 3, 2,
                                  vclass=L.VCLASS_NATIVE, audit=EM.EmulatorWorker())
        vals = [o.decode("utf-8", "replace") for o in eres["outputs"]]
        say(f"   R3 = R1 + 100 over inputs 0,1,2  ->  {vals}")
        out["compute"] = {"settled": eres["settled_chunks"], "outputs": vals}

        rule()
        say("④ governance: a native worker burns earned credit into a vote")
        weight_before = ghost.my_weight()
        ghost.burn_for_weight(2)                        # GHOST burns 2 of its earned 3
        weight_after = ghost.my_weight()
        say(f"   GHOST earned native credit, burns 2  ->  voting weight "
            f"{weight_after:.3f}  (float rent could never — §10)")
        out["governance"] = {"weight_before": weight_before,
                             "weight_after": weight_after}

        rule()
        say("Wallets after the session:")
        wallets = {}
        for name, node in (("Professor", prof), ("GHOST", ghost),
                           ("Emulator", emu), ("Client", client)):
            w = _wallet(node)
            wallets[name] = w
            say(f"  {name:10s} balance {w['balance']:+3d} CompuCoin   "
                f"weight-bearing {w['weight_bearing']}")
        out["wallets"] = wallets
        rule()

        # Smoke assertions: every class settled, native earned votes, float did not.
        assert ares["settled_chunks"] == 1, "professor did not settle"
        assert gres["settled_chunks"] == 1, "ghost did not settle"
        assert eres["settled_chunks"] == 3, "emulator did not settle"
        assert wallets["Professor"]["weight_bearing"] == 0, "float minted a vote"
        assert wallets["Emulator"]["weight_bearing"] == 6, "emulator native not a vote"
        # GHOST burned 2 of its 3 earned credit → 1 burnable left, positive weight.
        assert wallets["GHOST"]["weight_bearing"] == 1, "ghost burn not reflected"
        assert weight_before == 0.0 and weight_after > 0.0, "burn did not enfranchise"
        say("✓ three classes settled; native minted votes, float did not; and "
            "earned credit burned into a governance vote.")
        return out
    finally:
        for node in (prof, ghost, emu, client):
            node.stop()


if __name__ == "__main__":
    run_demo(verbose=True)
