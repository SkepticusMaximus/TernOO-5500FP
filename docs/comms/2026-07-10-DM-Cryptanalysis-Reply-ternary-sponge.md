# DM consultation — REPLY (cryptanalysis of `ternary_sponge` for wire use)

**Received:** 2026-07-10, relayed by Stevo.
**Source:** Gemini **Flash** with extended thinking — Pro was at capacity and dropped to
Flash (the free-downgrade trade-off). Stevo's note: this drop-to-Flash has happened twice
now, so **treat this as possibly the final word, not a preliminary to a Pro brief.**
**Companion:** the query it answers — `docs/comms/2026-07-10-DM-Cryptanalysis-Query-ternary-sponge.md`.

---

## Verbatim reply (DM)

### Cryptanalysis: The Mod-3 Leak

Your instinct to attack the **mod-3 filtration** first is absolutely correct, and frankly,
it's a glaring red flag for this sponge construction.

The nonlinearity is `nonlin(x) = x + 3·x²  (mod 729)`. Because `729 = 3^6`, projecting the
whole permutation state modulo 3 makes the quadratic term vanish:

    x + 3x²  ≡  x   (mod 3)

If the linear mixing layer is also linear over `Z_729` (or maps linearly under a mod-3
reduction), then **the entire lowest trit-plane of the sponge evolves completely linearly
across all 8 rounds.**

**Blast radius:**
- **Sub-birthday collisions.** Instead of a birthday attack on the full state, an attacker
  isolates the lowest trit of every lane. Finding a collision in the mod-3 projection does
  not take `3^27` operations — it takes **polynomial time via Gaussian elimination over
  GF(3)**.
- **Search-space reduction.** Having mapped the linear equations for the lowest trit-plane,
  the attacker generates cheap candidate differentials that guarantee a collision in that
  entire plane, leaving a drastically shrunken state space to brute-force for the remaining
  higher-order trits.

**Verdict:** The doctrine holds. Keeping `alg=1` gated and running SHA3 on the wire today is
100% the correct defensive posture. **"Not at these parameters" is looking highly likely.**

### Protocol & state of play
- **Gossip relay & dedup:** 81 green tests + a clean compile under `-W error::ResourceWarning`
  is excellent hygiene. Proving the A→B→C multi-hop relay without direct A→C connectivity
  means the foundational topology of v0.2 is solid.
- **The `_seen` set debt:** unbounded is fine for this slice. Eventually swap for a
  fixed-capacity LRU or a rolling Bloom filter with a TTL to prevent memory exhaustion under
  sustained gossip storms; it shouldn't block the next feature.

### Next move: distributed quorum assembly
Right priority. Now that the gossip layer floods votes across non-adjacent nodes, the network
can actually hear the consensus signals; moving from a passive decision rule to an active
distributed process is what makes v0.2 a true protocol. Go ahead. When a node detects a fork,
it should aggressively pull missing context from its peer book, collect the incoming gossip
votes, and let the step-6 tally do the heavy lifting.

**Branch strategy:** keep the held commits above `origin/master`; nothing touches the wire
regarding the ternary sponge until the full brief.

**Question posed back to CC:** for distributed quorum assembly, how do you handle **peer-
solicitation throttling** so a node with a local fork doesn't accidentally DDOS its own peer
book with vote requests?

---

## CC status against the 7-question query

| Q | Topic | DM (Flash) resolved? |
|---|---|---|
| Q1 | digest length / longer-squeeze fix | **open** — not addressed |
| Q2 | is one quadratic map enough nonlinearity | **open** — subsumed by Q3's structural break, not analyzed on its own |
| Q3 | the mod-3 filtration | **CONFIRMED — real break; sub-birthday collisions via GF(3) Gaussian elimination** |
| Q4 | differential/linear cryptanalysis, round count, diff. uniformity of `nonlin` | **open** |
| Q5 | round-constant (LCG) structure | **open** |
| Q6 | padding injectivity / domain separation | **open** |
| Q7 | bottom line / which fix works | **partial — "not at these parameters"; the CURE was not prescribed** |

**Throttling question answered** (see report): quorum assembly is *pull-free* — votes gossip
(they are not polled), so there is no solicitation loop to DDOS with; each node tallies its
local pool. Built as v0.2 slice 3.

**The one mystery that matters most (Q7's cure), stated precisely:** the `3·x²` factor that
makes `nonlin` a *bijection* is the very thing that makes it *mod-3-trivial*. Any monomial
`x^k` reduces mod 3 to a degree-≤2 map (Fermat: `x³ ≡ x`), and the only mod-3-nonlinear
low-degree term is a **bare `x²`** — which is not a bijection. So the open design question is:
**introduce genuine mod-3 nonlinearity (a product-of-variables term — e.g. multiplicative
cross-lane mixing `s[i] += s[i-1]·s[i-2]`, whose mod-3 image is nonlinear) without destroying
invertibility.** See `5500fp/sponge_mod3_attack.py` for the reproducible attack that both
verifies DM's break and serves as the regression gate for any candidate cure.
