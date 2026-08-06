# P2PVP quickstart — the vector manifold, live

P2PVP (Peer-to-Peer Vector Protocol — the captain's SETI@HOME, Search for
Empathetic Ternary Intelligence) is the vector/earn manifold, distinct from
P2PCP's prompt-passing inference manifold. Same node stack, same ledger, same
replay-audit economics — different cargo: S1a earn units (predicted vector →
TMesh traversal → OTree descent → residual/accuracy + weights) instead of
prompts. Every settled chunk is weight-bearing (a vote, §10), because any peer
can re-derive it bit-for-bit.

## What runs where (as of 06 Aug 2026)

The HP serves two P2PVP nodes as systemd --user services, bound 0.0.0.0 so
they're reachable over Tailscale:

| Service | Port | Sells | Engine |
|---|---|---|---|
| `p2pvp-earn` | 9001 | S1a vector-manifold work | pure-integer Python kernel |
| `p2pvp-ghost` | 9002 | GHOST classification | **C emulator (native t5asm)**, probe-verified against ref_forward at startup; falls back to the bit-identical host reference if the binary is absent |

HP tailnet address: `100.65.86.46`. Keyfiles/ledgers persist in `~/.p2pcp/`.

Service units live in `tools/p2pvp-earn.service` and `tools/p2pvp-ghost.service`
(install: copy to `~/.config/systemd/user/`, `systemctl --user enable --now …`).

## Buying from another machine (Lenny, over Tailscale)

From a repo checkout, no install needed:

```
cd TernOO-5500FP/5500fp

# vector work: 3 chunks, replay-audited locally before paying
python3 p2pcp_node.py vector --host 100.65.86.46 --port 9001 \
        --vector 1,2,3,4,5 --target 100 --chunks 3

# arbitrary cargo works too (bytes become the vector, target folded from SHA3)
python3 p2pcp_node.py vector --host 100.65.86.46 --port 9001 \
        --cargo "any text at all"

# native GHOST classification (the C shim doing the work on the HP)
python3 p2pcp_node.py classify --host 100.65.86.46 --port 9002 "make this loud"

# who's serving what
python3 p2pcp_node.py status --host 100.65.86.46 --port 9001
python3 p2pcp_node.py status --host 100.65.86.46 --port 9002
```

The buyer replay-audits every chunk with its own earn unit / GhostWorker and
pays only for work it re-derived — so the buying machine needs nothing but this
repo and Python 3. Payment settles on both ledgers; the HP's earnings are
weight-bearing (burnable into governance weight with `p2pcp_node.py burn`).

## The boundary that stays put

P2PVP inherits the S3 ruling and the wire discipline unchanged: integer
replay-class work mints votes; float work (the Professor) earns rent only;
ed25519 + SHA3 stay on the wire (alg=1 ternary-native remains a stub pending
external cryptanalysis — see `sponge_mod3_attack.py` for why).

Added: 06 Aug 2026, Adelaide. Authors: Stevo (SkepticusMaximus) + CC.
