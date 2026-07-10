# P2PCP — quickstart

P2PCP is a trustless compute mesh: strangers transact AI inference for **CompuCoin**, with
no data centre and no coordinator. This is how to run it. (Design canon:
`docs/P2PCP-v0.1-SPEC.md`.)

## Run the tests

```
cd 5500fp
python3 -m unittest test_p2pcp_ledger test_p2pcp_socket test_p2pcp_daemon \
  test_p2pcp_wire test_p2pcp_consensus test_p2pcp_gossip test_p2pcp_bonsai \
  test_p2pcp_ghost test_p2pcp_node test_sponge_mod3_attack test_network_boundary
```

## The two minds, both on the mesh

| worker | class | verified by | earns |
|---|---|---|---|
| **Professor** (Bonsai, llama.cpp) | float | redundant quorum | money (spendable, never a vote) |
| **GHOST** (native ternary MLP) | replay | bit-exact replay-audit | **weight-bearing** credit — a vote |

GHOST is deterministic integer inference, so any peer replays it and a forger is caught; that
verifiable work earns a governance vote. Float Bonsai earns rent. This is the determinism
moat made economic (§3/§10).

## The CLI (`p2pcp_node.py`)

Run a worker node (it sells compute for CompuCoin):

```
python3 p2pcp_node.py professor --port 9000            # Bonsai (needs the model)
python3 p2pcp_node.py professor --port 9000 --mock     # echo mock, no model — for demo/CI
python3 p2pcp_node.py ghost     --port 9001            # GHOST classifier (native)
```

Buy compute from a node (you pay per delivered, verified chunk):

```
python3 p2pcp_node.py ask      --port 9000 "what is balanced ternary?"
python3 p2pcp_node.py classify --port 9001 "save the file"
```

`ask` streams a prompt to a Professor (float); `classify` sends text to a GHOST node and
**replay-audits the answer itself**, paying only for work it re-derived bit-for-bit.

### Keep a node's identity + earnings across restarts

```
python3 p2pcp_node.py professor --port 9000 --mock --keyfile ~/.p2pcp/prof.key
```

The node persists its ed25519 key (owner-only) and a companion `.ledger` — restart it with the
same `--keyfile` and it keeps its account and its CompuCoin.

### Cross-box

The wire is byte-identical to loopback. Run `professor`/`ghost` on one machine and
`ask`/`classify` from another with `--host <ip>` — same CLI, real network.

## Module map

```
p2pcp_ledger.py     block-lattice ledger + TCM + consensus primitives (save/load)
p2pcp_consensus.py  fork detection + burn-weighted supermajority + slashing
p2pcp_socket.py     THE network organ (the only module that imports socket)
p2pcp_wire.py       wire frames: JOB/RESULT/RECEIPT/VOTE/RECORD/PEERS
p2pcp_daemon.py     node: keys, ledger, gossip, quorum, fork detection, eclipse
p2pcp_worker.py     WorkerAdapter interface + DeterministicWorker
p2pcp_bonsai.py     BonsaiWorker (float) — the Professor
p2pcp_ghost.py      GhostWorker (native, replay-class) — GHOST
p2pcp_node.py       the launchable CLI
sponge_mod3_attack.py   cryptanalysis gate (why SHA3 is on the wire, not the sponge)
```

## Status

v0.1 (protocol) complete; v0.2 mesh built (gossip flood, distributed quorum assembly, fork
gossip, eclipse mitigation, capability negotiation). 104 tests green on loopback. The only
substantive thing left is cross-box validation on real hardware — for which the CLI above
*is* the test.
