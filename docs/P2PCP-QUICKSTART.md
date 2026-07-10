# P2PCP — quickstart

P2PCP is a trustless compute mesh: strangers transact AI inference and native
compute for **CompuCoin**, with no data centre and no coordinator. This is how to
run it. (Design canon: `docs/P2PCP-v0.1-SPEC.md`.)

## See the whole thing in one command

```
cd 5500fp
python3 p2pcp_demo.py
```

Spins up a Professor + a GHOST + a 5500FP-emulator worker and a client on
loopback, joins them into one mesh, runs one paid transaction of **each**
verification class, then a native worker **burns earned credit into a governance
vote** — printing discovery and every wallet. No model, no config, no second box.

## Run the tests

```
cd 5500fp
python3 run_p2pcp_tests.py          # every P2PCP suite, one command + summary
```

Or invoke the fourteen suites directly with `python3 -m unittest test_p2pcp_ledger
test_p2pcp_socket … test_network_boundary` if you want to pick a subset.

## The workers, all on the mesh

| worker | class | verified by | earns |
|---|---|---|---|
| **Professor** (Bonsai, llama.cpp) | float | redundant quorum | money (spendable, never a vote) |
| **GHOST** (native ternary MLP) | replay | bit-exact replay-audit | **weight-bearing** credit — a vote |
| **5500FP emulator** (native ternary CPU) | replay | bit-exact replay-audit | **weight-bearing** credit — a vote |

Native workers run deterministic integer/ternary compute, so any peer replays the
work and a forger is caught before a coin is paid; that verifiable work earns a
governance vote. Float Bonsai earns rent. This is the determinism moat made
economic (§3/§10). Any callable can join too — wrap it with
`p2pcp_worker.FunctionWorker(fn)` and declare its class honestly.

## The CLI (`p2pcp_node.py`)

**Sell** compute (a worker node — it earns CompuCoin):

```
python3 p2pcp_node.py professor --port 9000            # Bonsai (needs the model)
python3 p2pcp_node.py professor --port 9000 --mock     # echo mock, no model — demo/CI
python3 p2pcp_node.py ghost     --port 9001            # GHOST classifier (native)
python3 p2pcp_node.py emulator  --port 9002            # 5500FP native compute
```

**Buy** compute (you pay per delivered, verified chunk):

```
python3 p2pcp_node.py ask      --port 9000 "what is balanced ternary?"
python3 p2pcp_node.py classify --port 9001 "save the file"
python3 p2pcp_node.py compute  --port 9002 --demo --chunks 3   # R3 = R1 + 100 over 0,1,2
```

`ask` streams a prompt to a Professor (float). `classify` sends text to a GHOST
node and **replay-audits the answer itself**. `compute` submits a 5500FP program
(`--demo`, or `--program-file prog.json` where prog is `{program:[words], in:R,
out:[R]}`) and replay-audits every result — paying only for work it re-derived
bit-for-bit.

### Discover instead of naming a node

Nodes advertise which class they serve, so you can find one instead of hard-coding
a port:

```
python3 p2pcp_node.py find    --class native --peers 127.0.0.1:9001,127.0.0.1:9002
python3 p2pcp_node.py ask      --peers 127.0.0.1:9000,127.0.0.1:9003 "…"   # picks a Professor
python3 p2pcp_node.py classify --peers 127.0.0.1:9001,127.0.0.1:9002 "…"   # picks a GHOST
python3 p2pcp_node.py status  --port 9000                                  # a node's public status
```

`ask`/`classify` with `--peers` discover a provider for the class and fall through
if one is down — the mesh as a utility you ask, not a node you name.

### Keep identity, earnings, and mesh state across restarts

```
python3 p2pcp_node.py professor --port 9000 --mock --keyfile ~/.p2pcp/prof.key
```

The node persists its ed25519 key (owner-only), a companion `.ledger` (account +
CompuCoin), and a `.ledger.peers` node-state file (known peers, anchors, and
earned reputation). Restart with the same `--keyfile` and it keeps its money, its
mesh view, and who has paid it — rejoining the mesh instantly. A tampered ledger
is refused on start.

### Fairness under load

A worker reveals a chunk before it's paid, so admission control bounds a deadbeat's
free ride (§9.1): a peer may hold only a few unsettled chunks before it's cut off,
while a paying customer *earns* a higher in-flight cap through reputation. Dead
peers are pruned from the book; anchors never are (§9.3).

### Cross-box

The wire is byte-identical to loopback. Run `professor`/`ghost`/`emulator` on one
machine and `ask`/`classify`/`compute` from another with `--host <ip>` — same CLI,
real network.

## In the GUI (FlowCode → Mesh tab)

The **Mesh** tab is P2PCP inside FlowCode/Academy: pick a role, Start a node, watch
your CompuCoin wallet and the live peer book, Join peers, and buy compute — from a
named node or from the mesh (discover + fall through). All logic lives in the
tested `p2pcp_service.MeshService`.

## Module map

```
p2pcp_ledger.py     block-lattice ledger + TCM + consensus primitives (save/load)
p2pcp_consensus.py  fork detection + burn-weighted supermajority + slashing
p2pcp_socket.py     THE network organ (the only module that imports socket)
p2pcp_wire.py       wire frames: JOB/RESULT/RECEIPT/VOTE/RECORD/PEERS/STATUS
p2pcp_daemon.py     node: keys, ledger, gossip, quorum, forks, eclipse, discovery,
                    admission control, reputation, peer-book health + persistence
p2pcp_worker.py     WorkerAdapter + DeterministicWorker + FunctionWorker
p2pcp_bonsai.py     BonsaiWorker (float) — the Professor
p2pcp_ghost.py      GhostWorker (native, replay-class) — GHOST
p2pcp_emulator.py   EmulatorWorker (native, replay-class) — the 5500FP itself
p2pcp_node.py       the launchable CLI
p2pcp_service.py    MeshService — the GUI bridge (fully testable, no screen)
p2pcp_tab_view.py   the FlowCode Mesh tab
p2pcp_demo.py       the whole mesh in one command
sponge_mod3_attack.py   cryptanalysis gate (why SHA3 is on the wire, not the sponge)
```

## Status

v0.1 (protocol) complete; v0.2 mesh built (gossip flood, distributed quorum
assembly, fork gossip, eclipse mitigation, capability negotiation). Since then:
capability discovery, buy-from-mesh with fall-through, admission control +
reputation, dial retry, dead-peer pruning, peer-book + reputation persistence, the
5500FP emulator as real native compute, and the FlowCode Mesh tab. 142 tests green
on loopback. The one substantive thing left is cross-box validation on real
hardware — for which the CLI above *is* the test.
