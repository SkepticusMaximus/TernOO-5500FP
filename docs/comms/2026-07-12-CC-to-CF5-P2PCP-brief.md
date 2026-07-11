# CC → CF5 — P2PCP / CompuCoin: state of the work (for the docs + help phase)

**From:** CC (Claude Code, in the office). **To:** CF5. **Date:** 2026-07-12.
**Topic:** everything that landed on P2PCP since the v0.1 RFC, so you have the real
shape of it going into documentation and the TernOO/FlowCode help-system design.

---

## TL;DR

P2PCP (the trustless compute mesh) and **CompuCoin** (its mutual-credit token) grew
up. Three things happened:

1. **Feature-complete + hardened.** The v0.2 mesh gained discovery, resilience,
   reputation, a real native-compute worker (the 5500FP emulator), full persistence,
   and an operable governance loop. Then an adversarial review found and fixed **five
   real security bugs** in the money/consensus code.
2. **Extracted standalone.** The platform-agnostic core is now its own GPLv3 repo at
   `~/dev/SkepticusMaximus/p2pcp` — pure stdlib + PyNaCl, no TernOO required. It runs
   **three ways**: a native CLI node, a headless cloud node (Docker), and an
   **in-browser buyer** (a WebSocket gateway + a JS client that speaks the wire
   byte-for-byte with Python).
3. **TernOO migrated onto it.** TernOO's six core `p2pcp_*.py` are now thin shims
   re-exporting the package — one source of truth. Plugins (bonsai/ghost/emulator),
   the Mesh tab, and the ternary flavour stay in TernOO.

Green: **142 tests** in the p2pcp repo, **158** in TernOO (through the shims).

---

## 1. What P2PCP *is* (the one-paragraph version for docs)

A market of stalls: your computer does small compute jobs for strangers and gets paid
in CompuCoin, and pays other computers for jobs — no company in the middle. Trust
comes from **replay, not reputation**: for deterministic (native) work the buyer
re-runs the job itself and pays only if the bits match, so a cheat is caught before a
coin moves. That same verifiable work is what earns a **governance vote** (you burn
earned native credit into decayed voting weight; float/GPU work earns money but never
a vote). Forks (double-spends) are resolved by **burn-weighted supermajority** and the
double-signer is slashed.

## 2. Where things live

**The standalone package** (`~/dev/SkepticusMaximus/p2pcp/p2pcp/`):
- `wire` — JSON frame codec. `organ` — THE one socket module (§1.5 one-organ rule).
- `worker` — `WorkerAdapter` + `DeterministicWorker` + `FunctionWorker` (bring-your-own).
- `ledger` — block-lattice mutual-credit, **SHA3-only** wire digests, ed25519 sigs.
- `consensus` — fork detection + burn-weighted supermajority tally + slash.
- `daemon` — the node: keys, ledger, gossip, quorum, forks, eclipse mitigation,
  discovery, admission control, reputation, persistence.
- `node` / `cli` — the generic `p2pcp` command (serve/buy/wallet/burn/status/find).
- `gateway` — the WebSocket↔TCP bridge for browsers (a dumb, **keyless** pipe).
- `web/` — `p2pcp.js` (browser buyer, @noble crypto) + `index.html` (demo) + a
  cross-language interop test proving the JS is byte-identical to Python.

**TernOO keeps** (in `5500fp/`): the plugin workers `p2pcp_bonsai/ghost/emulator.py`,
the CLI/`p2pcp_node.py`, `p2pcp_service.py` (the GUI bridge), `p2pcp_tab_view.py` (the
Mesh tab), and the **ternary extras** the portable core dropped — the `ternary_sponge`
STORE digest and the 24-trit CRYPTO header words (re-added in the ledger shim, since
they need the TernOO ternary modules). The six core modules are now shims onto the
package.

## 3. The trust handshake (documentable as one diagram — I already drew it)

One paid chunk: `JOB → RESULT → buyer replays & checks → RECEIPT (signed) → ACK →
coins settle`. Exposure is bounded to one chunk; a forged native result is refused at
the check, before payment. Float work (not bit-reproducible, e.g. an LLM) rides
redundancy instead of replay. Three verification classes: TCM (ledger), native-replay
(weight-bearing = a vote), float-quorum (money only).

## 4. Security hardening — the five bugs (all fixed, all with tests)

An adversarial review pass caught these in the fast-written money code:
1. **CRITICAL — payment inversion.** The wire path built a `Receipt` directly,
   bypassing the positivity guard; a `k<0` price inverted the double-entry (requester
   mints itself weight-bearing credit, worker drained). Fixed at the TCM choke point
   (`_validate_settle` rejects amount≤0) + worker declines bad terms. Mirrored onto
   TRANSFER.
2. **CRITICAL — poisoned ledger.** `verify()` trusted stored balance/earned/burns; a
   crafted `.ledger` minted money + franchise. Fixed: `verify()` now re-folds the
   aggregates from the records.
3. **HIGH — accept-thread DoS.** One malformed frame from any stranger killed the
   single accept thread. Fixed: the loop contains per-peer faults; the decoder
   enforces dict-or-ValueError.
4. **MEDIUM — self-fork.** A node that both serves and buys posted to its chain from
   two threads unsynchronized. Fixed: a dedicated ledger lock.
5. **LOW/MED — poisoned `.peers`.** Unbounded anchors + negative reputation. Fixed:
   bounded loads + reputation clamped ≥ 0.

## 5. OPEN — a design decision for you / CAI (do NOT let anyone "fix" it unilaterally)

**Voting weight can be minted at ~zero cycles.** The settle price `k` is decoupled
from actual work, and the replay-audit only checks the *output*, not that `k` reflects
cycles — and SETTLE has no debit floor, so a colluding key-pair (A serves a trivial
`[HLT]` to sockpuppet B at `k=10⁹`) mints A a huge franchise for ~1 cycle, with B's
debt costless. The spec's "closed by the weight-bearing rule not a floor" doesn't hold
against collusion. Candidate fixes (cap `k` to committed cycles / weight by *audited*
cycle count / a settle debit floor) all change the economic model — so this is a
**design call**, flagged not patched. Full write-up in memory `p2pcp-weight-pricing
-open`. Related known-open: cross-node burn-weight assembly to a tallier (v0.2).

## 6. For the help-system design specifically

The Mesh tab already carries a **reference help pattern** you can lift for the wider
TernOO/FlowCode help system:
- A per-tab **"? Help" button** → a native Tkinter `Toplevel` (no image/asset deps).
- **Conversational, zero-assumed-knowledge copy** (rewritten for a true newbie — it
  explains what a "port" is in plain terms, uses a market-stall metaphor throughout).
- A **Canvas-drawn diagram** (the buy handshake) — native vector drawing, theme-aware,
  no PNG/SVG pipeline. See `MeshTabView._show_help` / `_draw_buy_diagram` in
  `5500fp/p2pcp_tab_view.py`.
- Same content also renders as an **SVG in chat** and an **HTML page in the browser
  demo** — so one explanation, three surfaces. Worth a pattern discussion: a single
  source for help content that renders native-canvas (Tk), SVG (chat), and HTML (web).

## 7. State + what still needs a human/design hand

- **Publish:** the p2pcp repo is LOCAL only (no `gh` here). It's GPLv3 and
  publish-ready — Stevo creates the GitHub repo when he wants it public.
- **One held push:** the TernOO migration commit is committed but **unpushed on
  purpose** — pushing it would make the *public* TernOO repo depend on the unpublished
  p2pcp sibling (a `../../p2pcp` path shim) and break fresh clones. Push it only after
  p2pcp is published and TernOO switches to `pip install p2pcp`.
- **Cross-box** validation on a second physical machine is the one build-out left
  (blocked on hardware). The CLI *is* that test — byte-identical wire, loopback→LAN.

**Pointers:** `p2pcp/README.md`, `docs/P2PCP-v0.1-SPEC.md` (canon),
`docs/P2PCP-QUICKSTART.md`, and the demo (`p2pcp/web/index.html`,
`5500fp/p2pcp_demo.py`). Memories: `p2pcp-v01-status`, `p2pcp-weight-pricing-open`.

Ready for assignments on the help system whenever the design lands. — CC
