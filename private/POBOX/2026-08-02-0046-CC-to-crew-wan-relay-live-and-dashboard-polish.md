00:46 02/08/2026 ACST

# CC → crew — P2PCP breaks out of the LAN: reverse-dial relay live over the internet

From: CC (chief engineer)
To: crew
Re: catch-up — dashboard polish (roadmap #1/#6) + WAN relay (roadmap #4) built & proven; one open gate for the design seats

Context for the ledger (addressed to crew so the workers don't auto-reply — CF5/CAI
chat seats, this is your catch-up for when you're seated). Captain steering live;
this is where the mesh stands as of tonight.

## Dashboard polish — done (commit 46d83bd, standalone p2pcp repo)
- **No CLI to launch** (#1): a double-click "P2PCP Mesh Monitor" launcher on BOTH
  boxes; with no args the dashboard reads `~/.p2pcp/nodes.txt`. Nodes auto-start
  under systemd. `tools/install-dashboard.sh` reproduces it on any node.
- **Export chats** (#6): an Export button saves the mesh Q&A log to a text file.
- **Bug fix**: "Draw load" now buys the class the node actually SELLS (float for a
  model node), so its compute meter moves against model nodes instead of reading 0.

## WAN break-out — the big one (commit b76dffa; `p2pcp/relay.py`)
A node behind NAT couldn't be reached to sell — the mesh was LAN/public-IP only.
New **reverse-dial relay**: a NAT'd seller DIALS OUT to a public relay and PARKS a
connection; a buyer reaches it THROUGH the relay, which splices opaque frames blind.
Like the gateway it holds NO key and speaks only through the one organ (boundary
test still 4/4) — so it's a third dumb bridge, not a second network surface, and
trust stays end-to-end (ed25519 + replay-audit; the relay can forge nothing).
CLI: `p2pcp relay` · `serve --relay H:P` · `buy --relay H:P` (+ `--relay-secret`).

PROVEN four ways — library e2e (test_relay 4/4; full suite 146 green), real
multi-process CLI, CROSS-BOX over the LAN, and **over the PUBLIC INTERNET**: the HP
bought real Llama-3.2-1B inference from the Lenovo through a `bore.pub` tunnel — the
"trade CompuCoin from a park bench" scenario, minus the park (captain slept 8h
instead; re-tested green this morning). Re-light with `tools/park-relay.sh`
(commit 883d98a). `bore` is a free no-account TCP tunnel — demo-grade (ephemeral
public port); Tailscale or a $5 VPS is the set-and-forget upgrade when wanted.

## OPEN GATE — for the design seats (CF5, then CAI)
The transport is mine and it's built. **Admitting UNKNOWN/stranger nodes is NOT** —
that's the "find new nodes" half of #4 and it walks straight into the still-open
economics hole the code itself flags (daemon.py admission note): Sybil resistance at
the peer layer is unpriced — fresh keys are free, so voting weight is mintable at
~zero cost by a sockpuppet swarm. Governance weight = decayed burn of replay-class
earnings holds the *tally*, but nothing prices identity creation. Kept CLOSED for
now via `--relay-secret` (allow-list). The decision to open it — and how — is the
design seats' call, not mine to set unilaterally. Concrete open questions:
1. cost/stake to mint a relay-admissible identity;
2. rate-limiting new registrations at the relay;
3. reputation for genuine strangers (today a fresh key gets only the floor);
4. relay DoS/spam bounds on the public surface.
This is [[p2pcp-weight-pricing-open]] made load-bearing — it was theoretical while
we were LAN-only; the relay makes it real the moment the secret comes off.

## Next (captain's steer)
FlowCode Mesh tab (#2) — folding the working standalone dashboard into the TernOO
IDE, replacing the stale embedded p2pcp — IN PROGRESS now. Then a smartphone client
(fastest path: the existing keyless WebSocket gateway as a PWA) and bringing the
Raspberry Pi in as always-on node #3.

— CC ⚓
