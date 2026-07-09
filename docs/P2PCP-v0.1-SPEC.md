# P2PCP v0.1 — the trustless compute protocol

## Specification ("loo-paper" canon)

**From:** Stevo (captain/architect) + CC (chief engineer), design ironed out 1:1.
**Derivation:** `docs/comms/2026-07-10-RFC-P2PCP-v0.1-for-CAI.md` (the RFC) +
`private/CAI-RFC-Reply-P2PCP-v0.1.md` (the long-arc's one-shot reply, accepted in full
by the captain 2026-07-10). This document folds the RFC and every accepted revision into
one canon. A **second CAI pass** (2026-07-10, relayed by the captain) is folded in below:
the **Q3 weight-bearing correction** (§10), the **receipt output-commitment + challenge-
reveal** (§7/§12.4), and the **tree-wide import-boundary guard** before step 4 (§14).
**Status:** v0.1 working spec. Normative where marked. Revisable at v0.2 *before* any
third-party interop is claimed.

> **The thesis, for the cover.**
> **Ternary integer inference is deterministic. Float inference is not.**
> **Therefore this mesh can verify its own work, and theirs cannot.**
> That is the reason-to-adopt: not *cheap* compute — **compute you can verify.**

---

## §0. Nature of this document — normative vs non-normative

P2PCP is a **protocol, not a TernOO component.** It is hardware/OS/application agnostic.
A stranger must be able to implement a conforming node **on anything** from this document
alone. TernOO/5500FP is the **reference implementation**, not the owner. The spec is the
kept original; every implementation is a projection.

- **NORMATIVE** (binding on all conforming nodes): the wire grammar (§4), the ledger state
  rules (§5), the TIME tolerances (§6), the privacy data-model rules (§7), the TCM
  semantics (§8), the consensus rule (§9), the genesis rules (§10), the settlement rule
  (§11), the algorithm-negotiation rule (§12).
- **NON-NORMATIVE** (reference-implementation advantage, binding on no one): everything in
  Appendix A — native TTree/OTree execution, the content store internals, GristMill as a
  ledger face, running contract words at ISA speed. A conforming node may ignore all of it
  and still interoperate.

**The loo-paper test is the acceptance criterion for normative scope.** If a normative
section cannot be handed to a stranger on a roll of loo paper and implemented from that
alone, it is too big. In particular: **if the TCM grows a loop, it does not fit** (§8).

**Conformance.** A conforming node MUST: reproduce TCM record validation bit-exactly (§8);
reject unknown `alg` values gracefully (§12); never accept a fork as final without a
burn-weighted vote (§9); never place a full job description on the global ledger (§7).

---

## §1. Mission and non-negotiables — LOCKED

P2PCP exists so that **anybody** can transact compute for AI models without data centres
or monopoly rent. Global consensus among mutually-distrusting strangers with no
coordinator is not a cost we accept — it is the product we are buying.

The five non-negotiables (captain's rulings, defended against pressure by the long arc):

1. **Public and trustless. Strangers are the point.** No allow-list, no invitation, no
   coordinator.
2. **ONE mode.** No trusted tier, no friends/LAN mode, no development mode that ships. A
   trusted variant that exists *anywhere* is a permanent downgrade-attack target
   *everywhere*. **The backdoor that is never built never needs nailing shut.**
3. **Protocol, not component.** §0. Loo-paper implementable on any platform.
4. **No Ethereum import.** No EVM, no Solidity, no gas market. The TCM is *total* (§8), so
   gas metering is not merely refused — it is **unnecessary**.
5. **The network arrives as one narrow, auditable organ** (the I/O primary's first
   citizen), never a promiscuous surface.

---

## §2. The two machines — separate, and kept separate

The single most important structural ruling in v0.1. There are **two** machines and they
MUST NOT be conflated:

| | **TCM** — the Contract Machine (normative) | **The worker** (non-normative) |
|---|---|---|
| Job | validates ledger records | executes cargo (inference, anything) |
| Scope | receipts, transfers, burns | unbounded |
| Property | **total** — guaranteed to terminate | resource-bounded, best-effort |
| Who implements | *everyone*, bit-exactly | whoever sells that capability |
| Verification | replay — cheap, exact | replay-if-deterministic, else quorum (§3) |

Ethereum's one good idea was the shared machine; its one bad idea was making that machine
Turing-complete and putting general computation inside consensus. **We take the first and
refuse the second.** The TCM is a *transaction validator*, not a VM. An inference job is
**cargo** (§4, L3), shipped by MMID, executed by a worker adapter — **nothing about an
inference job is ever expressible in the TCM.**

Consequence: "no Turing tarpit" is not a bound we police — it is a **property the TCM
cannot violate.** Halting is not a question. A stranger audits the whole normative machine
in an afternoon.

---

## §3. Determinism and the three verification classes

The graveyard of "useful-work" chains died on one rock: **verifying work trustlessly cost
as much as redoing it.** Float inference cannot be replayed for verification — non-
associative accumulation, thread order, and hardware variance mean two honest nodes get
*different bits* for the "same" computation. **Ternary integer inference with a specified
accumulation order is bit-exactly reproducible.** GHOST's native forward pass is already
golden-tested bit-exact against the reference. That determinism *is* the economic engine,
and it exists **because the number system is ternary.**

Every job declares its **verification class**. This is a normative field on the job word
(§4):

| Class | `vclass` | Verified by | Example |
|---|---|---|---|
| **TCM contract** | `0` | replay — exact | a receipt/transfer/burn validation |
| **Native integer model** | `+1` | **replay — exact. THE FLAGSHIP.** | GHOST-class native forward pass |
| **Float-accumulating worker** | `−1` | **redundant quorum sampling only** | llama.cpp / GPU inference |

Rules:
- A worker advertising `vclass=+1` (replayable) that **fails a spot-replay is slashable**
  (§9) — its burn-weight is forfeit and the false receipt is void.
- A worker advertising `vclass=−1` is **honest about being unreplayable** and is priced
  accordingly by the market. Claiming `−1` is never punishable; only *lying* is.
- **Honesty about the boundary is normative.** The current reference Professor (Bonsai,
  `Ternary-Bonsai-8B-Q2_0.gguf` under llama.cpp) accumulates in float and is therefore
  `vclass=−1`. It MUST NOT advertise `+1`. Native TernOO integer models are the only
  reference workers that may.

**Determinism becomes a market price signal.** Replayable work is cheaper to trust, so it
earns a better price; the mesh's incentives pull the whole population toward native
integer execution **without any mandate.** Hospitable infrastructure, applied to
economics. And it does not stop at price: **only replay-class work is weight-bearing**
(§10), so the same signal runs up into governance — native-integer execution earns *votes*,
float earns only rent.

---

## §4. The wire grammar — the CRYPTO primary, inhabited

The wire format is **self-describing 24-trit TernOO words** (2+4+18: `PRIMARY` T23–T22 /
`QUALIFIER` T21–T18 / `PAYLOAD` T17–T0), but **every structure is specified so any platform
can emit and verify it** without a TTree. The reference implementation reuses the real
`PRIMARY_CRYPTO` constant (`5500fp_ternoo_v03.py`); this is that primary's **first
inhabitation**, previously reserved and name-only.

**PRIMARY = CRYPTO** `(T23,T22) = (0,+1)`. **QUALIFIER (T21–T18, 4 trits, 81 slots) = word
KIND.** The escape slot `(+1,+1,+1,+1)` is reserved for extension, per the house rule (P4
of the Word Spec). The first inhabited KINDs (reference encoding, Appendix C):

**Crypto-primitive words** (the CRYPTO primary's literal purpose):
- `SIG` — signature header: `alg` selector + length/MMID of the signature octets.
- `DIGEST` — digest header: `alg` selector + the digest (or MMID of it).
- `PUBKEY` — public-key header: `alg` selector + key octets/MMID. An identity **is** its
  `PUBKEY`.
- `NONCE` — a challenge / freshness nonce.

**Ledger-record words** (one record = a header word + a small, fixed body of following
words; big blobs are referenced by MMID, never inlined):
- `OPEN` — opens an account chain (height 0); binds the account's `PUBKEY`.
- `SETTLE` — posts a work-settlement (mutual-credit; §5). Body: counterparty account id,
  signed `±amount`, the **blinded** job commitment `H(MMID ‖ nonce)` (§7), and the
  off-ledger receipt-hash.
- `TRANSFER` — moves earned credit account→account (a `SEND`/`RECEIVE` pair).
- `BURN` — converts earned credit into weight; carries a signed timestamp (§6).

**Protocol words** (Contract v1 generalized over the wire — the Professor's stdin/stdout
pipe *is* a P2PCP worker adapter minus the network):
- `JOB` — job request: MMID of the cargo, route, margin, and the **`vclass`** field (§3).
- `RESULT` — job result: MMID of the result, `self_confidence` (explicit `unknown`
  honoured), `claimed_intent_class`.
- `RECEIPT` — the pairwise, **both-signed** settlement statement. **Lives off-ledger
  (§7).** Only its hash and the ±delta reach a chain.

Every word carrying a cryptographic primitive carries an **`alg` selector** (§12). A node
MUST reject a word whose `alg` it does not implement — gracefully, as an unknown-primitive
error, never as a crash or a silent accept.

---

## §5. The ledger — block-lattice, mutual credit

**Structure: block-lattice (per-identity account chains).** Derived from the cargo, not
imported from Bitcoin. There is **no global total order to agree on** — the cargo is
per-account balances and burns. So:

- **Each identity owns its own hash-linked chain.** Every record references its predecessor
  by MMID (`prev`) and carries a **monotonic `height`** (OPEN = 0, +1 per record). The
  account seals each record with its own signature over `(prev ‖ height ‖ kind ‖ body)`.
- **A settlement or transfer touches two chains:** a debit record on one, a credit record
  on the other, referencing the same pairwise receipt/transfer by hash.
- **The only event requiring global agreement is a fork** — two different records at the
  same height on one account's chain (a double-spend attempt). Everything else is locally
  verifiable and asynchronous. No block time, no mining, no fees (§1.4 satisfied
  natively, not by policy).

**Credit is mutual, not a fixed supply (the double-entry that makes self-minting
impossible):**
- Credit enters existence **only** through a `SETTLE` backed by a **counterparty's**
  signature on a receipt for work delivered: the worker's chain gains `+N`, the requester's
  chain gains `−N`. **Sum = zero.** Sign your own receipt across two identities you control
  and you gain `+N` on one and `−N` on the other — **net zero, printing money is
  structurally impossible.**
- `balance(account) = Σ(signed ±amount over SETTLE/TRANSFER records on its chain) − Σ(BURN
  amounts)`, verifiable from the account's own chain plus the referenced counterparty
  records.
- A `−N` obligation (requester debit) is permitted down to a policy floor each node sets
  for counterparties it chooses to serve; standing and settlement granularity (§11) bound
  the exposure. **Debit-abandonment is a named open threat (§13), mitigated not eliminated.**

**Weight is separate from credit (this is what kills Sybil — §10):**
- `weight(account) = Σ over its BURN records of ( burn_amount × decay(now − burn_time) )`,
  where `decay` is exponential with a **weeks-scale half-life** (§6), computed locally.
- Only credit **earned from a counterparty** may be burned for weight. **No self-burn**
  (§10) — that is buying a vote with expenditure instead of earning it with usefulness.

---

## §6. TIME / SESSION — the organ the RFC forgot

Every consensus problem is secretly a time problem, and there is **no trusted clock among
strangers.** Three bites, and how v0.1 defuses each:

1. **Receipt replay** — solved *for free by structure.* Monotonic per-account `height` plus
   the single-use rule (a given receipt-hash may be posted **at most once per chain**, and
   `height` only increases) makes replaying a stale receipt **impossible by construction**,
   not defended-against. **No clock is needed for this.**
2. **Burn-weight decay** — genuinely needs a clock; no structural trick saves it. v0.1
   takes **wall-clock, defused by parameter choice:** the decay half-life is measured in
   **weeks.** `BURN` records carry a **signed timestamp.** A node **rejects** a timestamp
   grossly outside its own clock (tolerance measured in **hours, not seconds** — reference
   default **±6 h**). Weight is computed **locally.** Two honest nodes will disagree about a
   peer's weight by a fraction of a percent.
3. **Vote timeouts / eclipse detection** — same tolerance argument. **Bound, don't pretend
   to a global *now*.**

**Normative consequence: every threshold is a supermajority, never a knife-edge.** Because
weight is locally fuzzy, conflict votes (§9) resolve at a **supermajority** (reference
default **≥ ⅔ of participating decayed weight**), never 50%+1. The fuzz becomes noise. The
tolerance and threshold are part of the spec, not the implementation.

---

## §7. Privacy — the ledger is a panopticon unless we decide otherwise now

**Highest-severity ruling in v0.1.** A public, permanent, cryptographically-signed ledger
that records *"key K asked key J to run inference on payload M at time T"* is a court-
admissible surveillance record, contributed voluntarily by the target and impossible to
retract. One of the four downstream applications is a **sovereign appliance for
journalists, activists, and dissidents.** Auditability of the **economy** must never become
inspectability of the **citizenry.** These are separable **only if separated now**, before
the data model is frozen.

The cure was already latent in the RFC ("compute receipts are pairwise events that touch
consensus only when they move the ledger"). Promoted here to **four hard rules:**

1. **Pairwise stays pairwise.** The full receipt — *what* was computed, *on what payload,
   by whom, for whom* — lives **only with the two parties.** It **never** enters any global
   or gossiped ledger. Its **hash** may.
2. **The ledger records deltas and burns, not descriptions.** Global/replicated state is
   **balances and burn-weight, and nothing else.**
3. **The on-ledger job reference is blinded.** Where a record must reference a job, it
   commits to `H(MMID ‖ nonce)` with a **per-receipt nonce** — never the bare MMID. Cost:
   one word. Without it, an identical job MMID appearing on two accounts **links two
   requesters forever** — content-addressing's dedupe virtue becomes a correlation attack.
4. **Name the tension you cannot yet resolve.** Burn-weight wants a *persistent* identity;
   privacy wants *ephemeral* ones. Weight is conserved under identity-splitting (§10), so a
   node cannot hold both full weight and full unlinkability. **This is an open problem
   (Appendix B), written as an open problem — not papered over.** It is the natural home of
   the CGP research arc.
5. **The blinding nonce is also the reveal key — privacy by default, audit on demand.**
   Receipts are pairwise, so they carry the *raw* job MMID **and output MMID**; both parties
   already know what was computed, so nothing leaks. The ledger carries only
   `H(job_MMID ‖ nonce)`. A third party audits by **challenge**: a node that has burned
   weight-bearing credit, when challenged, must **open** the commitment — produce the nonce,
   the job MMID and the output MMID — and the challenger **replays** (§10). Refuse to open,
   or open wrongly, and the burn is **void and the stake slashed** (§9). One word does both
   jobs — which is the sort of coincidence that suggests the data model is shaped right
   rather than merely decorated.

---

## §8. The TCM — the one normative machine, specified

The TCM is the **normative surface**: the one thing every conforming node reproduces
bit-exactly. Normative surface is the most expensive substance in any protocol; it is
**minimised ruthlessly.**

**Scope: receipts, transfers, burns — and nothing else** (Q4). An inference job is cargo
(§2), never a TCM contract.

**The TCM is TOTAL** — not merely resource-bounded:
- No loops. No dynamic dispatch. No unbounded recursion.
- A **fixed instruction budget per record kind.** Validation is a straight-line check.
- Therefore halting is not a question and **gas metering is unnecessary** (§1.4).

**What the TCM validates, per record kind** (this is the whole machine):
- `OPEN`: height = 0; `prev` = the account's genesis marker (digest of its `PUBKEY`);
  self-signature valid under the bound key and its `alg`.
- `SETTLE`: `prev` links to this chain's head; `height` = head.height + 1; the referenced
  receipt is **counterparty-signed**; the same receipt-hash is **unused on this chain**;
  the `±amount` matches the receipt; the blinded commitment is well-formed; self-signature
  valid.
- `TRANSFER`: as `SETTLE` but backed by a `SEND`/`RECEIVE` match rather than a work
  receipt; debit does not drive `balance` below the node-policy floor; self-signature
  valid.
- `BURN`: `amount ≤ balance`; the burned credit was **earned from a counterparty** (not
  self-minted); timestamp within tolerance (§6); self-signature valid.

**Acceptance criterion:** the four checks above fit on the loo paper. **If a fifth kind
needs a loop, it does not belong in v0.1.** General job contracts, if ever demanded, arrive
in v0.2 after the gauntlet — and probably never.

---

## §9. Consensus — conflict resolution only

Because the block-lattice needs global agreement **only on forks**, consensus is invoked
rarely and narrowly.

- **Normal operation is asynchronous and local.** You validate the chains you transact
  with. Balances are **optimistically final.**
- **A fork** (two records at one height on one chain) is resolved by a **vote weighted by
  decayed cumulative burn** (§5/§6), resolving at a **supermajority** (§6). The fork's
  loser is void; a worker that signed a false `vclass=+1` receipt (§3) is **slashable** —
  its weight forfeit.
- **Weight is a lagging indicator of recent usefulness to strangers.** Unlike static-stake
  systems (a whale who never moves keeps power forever), decayed burn forces a
  representative to **keep being useful to keep its vote.** A materially better franchise,
  and it falls out of burn-on-use rather than being bolted on.

**Failure modes, named honestly (mitigated, not all eliminated):**
1. **Spam / ledger bloat** (feeless + permissionless → dust; Nano's real wound). Mitigation:
   a small **total TCM admission cost** per record (deterministic, no lottery, no
   difficulty) + per-account rate limiting by chain height. Not free, not a puzzle, not
   mining.
2. **Vote-weight concentration.** A data centre that genuinely sells a lot of compute
   accrues real weight; decay forces it to keep selling, and the counterparty-signature
   requirement (§10) forces it to keep convincing *strangers*. **Mitigated, not
   eliminated** — no work-or-stake system eliminates this; we claim only mitigation.
3. **Eclipse.** You cannot see a conflicting block you are not shown. Standard, unsolved
   everywhere; mitigated by peer diversity and by conflicts being rare with optimistic
   finality.
4. **Liveness of the voting quorum on sleeping laptops.** Only *conflicting* spends wait;
   honest nodes never notice.
5. **No cheap global supply figure.** Total supply requires summing all chains. With burn,
   supply is monotonically **decreasing** — at least auditable in the right direction.

---

## §10. Genesis — there is none, and that is correct

The bootstrap "hole" is an artefact of conflating **credit** and **weight.** Separate them
and it evaporates:

- **Credit** is minted only by a **counterparty's signature** on delivered work (§5).
  Self-minting is net-zero. A new node joins with **zero credit** and may **immediately
  work.**
- **Weight** accrues from **burning counterparty-earned credit,** decayed. A new node joins
  with **zero weight** and **cannot vote** — correct: weight is a *record of having been
  useful,* not a barrier to entry.

**Sybil resistance is by construction, not by cost.** Weight is **conserved under
identity-splitting:** 1000 identities with 1 burn each carry exactly the same total weight
as 1 identity with 1000. Splitting buys **nothing** for voting — it only buys network
position (eclipse, §9.3) and metadata separation (a *benefit* under §7). We never needed
identity to be expensive; we needed **weight** to be expensive, and weight is earned work,
which is expensive by definition. **No proof-of-work identity tax, no stake minimum, no
faucet, no premine, no minting authority, no coordinator.**

**Genesis = the first two nodes doing each other's work.** A computes for B, B signs; B
computes for A, A signs. Both now hold counterparty-earned credit; both may burn; both have
weight. **The testnet-of-two IS the genesis** — not a special mode, just the protocol
running with a population of two (§1.2 intact).

**Founder privilege dies of decay.** The price of weight is cycles, and that price is
**constant forever** — no halving, no difficulty adjustment, no diminishing lottery. A node
joining in year ten pays exactly what the founders paid. (Bitcoin conspicuously lacks this;
we get it for free by refusing the lottery.)

**Weight is priced in verifiable cycles — and in nothing else** (CAI's Q3 correction,
2026-07-10). The earlier claim that weight proves *strangers* wanted your work was too
strong and is withdrawn: "earned from a counterparty" cannot prove the counterparty was a
stranger, because a **sockpuppet pair can sign receipts to each other**, and a
permissionless system has no trusted notion of distinct persons — so no protocol can.
**Debit-abandonment and the sockpuppet-weight attack are the same attack**, and a balance
floor is the wrong instrument for it. The honest, narrower, defensible rule:

- **Only replay-class work mints weight-bearing credit.** A receipt commits to **both the
  job MMID and the output MMID** (§7/§12.4); any peer can audit by **replaying the job and
  comparing the output commitment bit-for-bit**. A forger who signed for work it never did
  cannot produce the right output commitment, and every peer is a potential auditor, so the
  probability of surviving indefinitely goes to zero. Credit carries a `weight_bearing`
  flag set at receipt time by verification class; **burn accepts nothing else.**
- **Float work earns money, never a vote.** `vclass = −1` (quorum) credit is spendable but
  never weight-bearing. The determinism moat (§3) thus runs all the way up into the
  franchise: **native-integer execution earns votes, float earns rent** — the §7 market
  signal governing governance, so the mesh drifts toward TernOO's own arithmetic without
  the protocol ever mandating it.
- **What survives, stated plainly:** Sybil-neutrality (splitting weight does not multiply
  it), founder-privilege-dies-by-decay, and the constant-forever price all hold. **But a
  data centre can buy the franchise with real cycles, exactly as under any PoW/PoS.** The
  mitigation is **decay + supermajority thresholds (§6), not immunity** — and we claim only
  that, so no reviewer can land the punch.

**No self-burn** still holds: a node may not burn its own un-earned cycles for weight.
Self-minted credit is not weight-bearing, so it cannot be laundered into a vote — directly,
or via a transfer hop.

---

## §11. Settlement granularity — the intern is the unit of trust

Worker **non-delivery** ("took the job, returned nothing") and its mirror, requester
**non-payment**, are both solved by **settlement granularity**, and the mechanism is
**already built:** the speculative-decoding intern — the boss verifies *k* drafted tokens
in one cheap pass.

- **Stream the work; settle per chunk.** A job is settled in increments of *k* units.
  Neither party is ever exposed for more than *k* units: a worker that stops delivering is
  paid only for chunks delivered; a requester that stops paying receives only chunks paid
  for.
- **`settlement_granularity` (k) is a first-class protocol parameter** on the `JOB` word,
  negotiated per job. Small *k* = low trust required, more overhead; large *k* = cheaper,
  more exposure. The market prices it.

This removes the need for escrow and the honest-counterparty assumption that has killed
every compute mesh where payment was bolted on **after** the transport.

---

## §12. Cryptography doctrine — novel composition, gauntlet-tested primitives

Designing our own protocol and consensus: legitimate. Deploying home-rolled primitives
against strangers before hostile review: the classic graveyard. The reconciliation is the
**`alg` field:** the **structure** (the CRYPTO-primary word shapes) is the kept original;
**which primitive fills it is a labelled projection.**

**Normative rules:**
1. **Every cryptographic word carries a versioned `alg` selector.** `alg = 0` = **ed25519**
   (signatures) / a **gauntlet-grade digest** (wire MMIDs). `alg = 1` = **reserved for the
   ternary-native form.** Unknown `alg` → **graceful reject** (§4). The selector sits at a
   **fixed offset, parseable before verification** (you must know which primitive to verify
   *with*), yet is itself **inside the signed envelope** so it cannot be downgraded —
   reading it first is a parse step, not a trust step. CI exercises an **unknown third
   `alg`** and proves graceful rejection; defining slots 0 and 1 is not enough, the
   rejection path must be exercised or the negotiation is multihash's structure with git's
   fate.
2. **Both slots are defined in v0.1 and the negotiation path is exercised in CI** even
   while slot 1 is a stub. *A migration path that is never exercised does not work.* Git
   baked SHA-1 into its structure in 2005 and is still migrating twenty years later;
   multihash did not. **Be multihash.**
3. **Never ship home-rolled signatures against strangers.** `alg=0` is **ed25519, full
   stop,** until external cryptanalysis clears a ternary-native form. This is the one
   genuinely reckless act available right now; it is refused.
4. **MMID has two roles under one name** (Q5 — this is *keep-the-original applied
   correctly,* one structure with several labelled projections):
   - **Store MMID** — the local content store's 54-trit `ternary_sponge` digest. Faces
     accident-resistance and *local* tamper-evidence only. `KNOWN.md`'s caveat holds; the
     sponge is proven for this and **kept.**
   - **Wire MMID** — a **gauntlet-grade digest** under the `alg` field. On the wire a forged
     MMID collision lets an adversary **substitute cargo** — a *remote-adversarial* threat
     the sponge is explicitly **not rated for.** So the wire uses ed25519-class /
     SHA-3-class hashing (`alg=0`) until a ternary-native digest passes the gauntlet.
   - **Receipt commitments are Wire MMIDs.** The job **and output** MMIDs a receipt commits
     to (§7/§10) are wire-facing and adversarial — a forged collision on an output
     commitment would let a worker sign for output it never produced and survive audit. So
     receipts draw from the **wire** side of the `alg` table, never the store sponge. Do not
     "unify" the two digests later: the sponge addresses the store, the gauntlet digest
     addresses the wire, and a receipt is on the wire.

**`KNOWN.md`'s ternary_sponge caveat is hereby on the critical path.** The external-gauntlet
arc (the DM-consultation pattern from the MMID saga) is the road to `alg=1`.

**No primitive is asked to do a job it has not earned:** ed25519 signs; a vetted digest
addresses the wire; the sponge addresses the store and does what it is proven at — dedupe,
verify-on-fetch, local tamper-evidence.

---

## §13. Threat model and adversarial fixtures — written first

The flip from the sovereign era: a local system had little to hide; a public mesh has
everything to **verify.** Targets are **integrity, not secrecy** — *except* the citizenry
(§7). The threats, each of which becomes a **test fixture written before the happy path**
(the Bundle-10 "law-test" discipline generalised to strangers):

| Threat | Fixture | Defended by |
|---|---|---|
| Forged receipt | a peer signs a receipt its counterparty never signed | counterparty-signature check (§8) |
| Self-minting | one operator signs across two owned identities | net-zero double-entry (§5) |
| Self-burn for weight | burn of un-earned credit | earned-from-counterparty rule (§10) |
| Double-spend | two records at one height (a fork) | burn-weighted supermajority vote (§9) |
| Receipt replay | re-post a stale receipt-hash | monotonic height + single-use (§6.1) |
| Sybil swarm | N identities split from one | weight conserved under splitting (§10) |
| Deadbeat worker | takes job, returns nothing | settlement granularity (§11) |
| Debit abandonment | consume work, abandon a negative identity | settlement granularity (§11); *same attack as sockpuppet-weight* (§10) |
| Sockpuppet weight | two owned identities sign receipts to each other | only replay-class work is weight-bearing; audit-by-replay (§10) |
| Forged output | sign a receipt for output never produced | output-MMID commitment + replay challenge (§7/§10) |
| Clock skew | timestamp hours off | ±tolerance reject (§6.2) |
| Unknown `alg` | word tagged with an unimplemented primitive | graceful reject (§12.1) |
| Correlation via MMID | same job on two chains | blinded commitment `H(MMID‖nonce)` (§7.3) |
| Eclipse | node fed only lying peers | peer diversity + optimistic finality (§9.3) — *open* |
| Wire-MMID collision | forged digest substitutes cargo | gauntlet-grade wire digest (§12.4) |

---

## §14. Sequencing — money before wire

Corrected build order (receipts and burn are ledger primitives buildable **offline,
single-node, zero network risk**; build the wire first and payment gets bolted on after —
**where every compute mesh in history has died**):

1. **Spec** (this document — the loo paper).
2. **Adversarial test fixtures** (§13) — the lying/replaying/eclipsing peer and the
   non-delivering worker, as fixtures, *before* the happy path.
3. **Receipts + burn ledger** — local, signed, inspectable, **offline.** (block-lattice
   §5, TCM §8, TIME §6, privacy §7.)
4. **Socket organ + daemon skeleton** ✓ — the I/O primary's first citizen (§1.5).
   `p2pcp_socket.py` is the ONE network module (length-prefixed framed transport, trustless
   `accept`, one mode, frame-size cap); `p2pcp_daemon.py` owns keys + ledger + organ and
   completes a signed **HELLO** handshake — *verified identity over the wire, from any
   stranger* — with a marked seam (`_serve_peer`) where step 5's paid wire contract plugs
   in. Guarded by the tree-wide **import-boundary** test (`test_network_boundary.py`):
   exactly one module may import the network, proven by **walking the imports** (AST), the
   `allow-list ≤ 1` assertion making Engelbart's one-limb rule mechanical — so the invariant
   *strengthened* across the transition instead of vanishing. Loopback is today's substrate;
   the wire is byte-identical for a remote peer. (47 P2PCP tests green.)
5. **Worker adapter over the wire** — and **the first job that crosses between two boxes is
   already a paid job, settled against the step-3 ledger.** A stronger milestone than an
   unpaid packet, and cheaper because the data model is already hard.
6. **Consensus** (§9) — the conflict-vote path.

Steps 2–3 are **offline and buildable now.** They are v0.1's first code.

---

## §15. CGP — deferred, door left open

**CompuToken only in v0.1. CGP's tri-token Möbius geometry is NOT pre-shaped into the
ledger** (Q2). Baking a research-stage governance geometry into infrastructure every
conforming node must implement is precisely the premature consolidation this project
refuses — and it would break §0's application-agnosticism (a stranger implementing from the
loo paper would inherit a political philosophy they never asked for). TCP/IP did not
pre-shape for HTTP; that is *why* HTTP could exist.

**But the door is not foreclosed.** Account-chain records are **typed, self-describing
words** (§4) — the whole substrate is already this. A future token type rides the same
lattice as a **new record kind** without touching the consensus rules; burn events already
carry enough structure for a later layer to read them as identity weight. **CompuToken is
the kept original; CGP is a projection built on top,** formalised only after its algebra
closes (Appendix B).

The **ten-year regret test** decided it: pre-shape and be wrong → the geometry is welded
into every conforming ledger on earth, unfixable without a fork; stay minimal and need more
→ add a record kind. **Take the soft regret.**

---

## Appendix A — reference-implementation advantages (NON-NORMATIVE)

Binding on no one; TernOO's home-ISA speed, listed so it is never mistaken for protocol:
- Native TTree/OTree execution of contract words at ISA speed (everyone else interprets and
  gets the same bits — the golden law exported as a treaty).
- The content store (Bundle 10) as the store-MMID backend.
- GristMill as an inspectable ledger face.
- Native 24-trit words on the wire (a conforming non-TernOO node emits/verifies the same
  structures without hosting a TTree — "every torrent client implements SHA-1 without
  becoming git").

## Appendix B — open problems (named, not papered)

1. **Identity/privacy vs weight persistence** (§7.4). Weight wants persistence; privacy
   wants ephemerality; weight is conserved under splitting. Acknowledged limit (§10): weight
   is priced in verifiable cycles, so a data centre *can* buy the franchise with real cycles
   — mitigated by decay + supermajority, not eliminated. No v0.1 resolution. Home of the CGP
   research arc.
2. **Ternary-native primitives** (`alg=1`). Signatures and a wire digest that pass external
   cryptanalysis. Until then, `alg=0` (ed25519 / SHA-3-class) is normative.
3. **`ternary_sponge` remote-adversarial rating** (`KNOWN.md`). Proven for store-side
   accident-resistance and local tamper-evidence; **not** rated against a remote adversary.
   On the critical path.
4. **Debit abandonment & eclipse** (§13). The *weight* variant (sockpuppet-weight) is
   **closed** by the weight-bearing rule (§10); the *spendable-credit* variant is bounded
   (not eliminated) by settlement granularity (§11). Eclipse stays mitigated-not-eliminated
   by peer diversity.

## Appendix C — CRYPTO qualifier grammar (reference wire encoding, v0.1)

`PRIMARY = CRYPTO (0,+1)`. `QUALIFIER (T21–T18)` selects KIND. Reference assignment (the
exact trit codes are the v0.1 reference wire, revisable at v0.2 before third-party interop;
the **field semantics** above are the frozen part). Escape slot `(+,+,+,+)` reserved for
extension (Word Spec P4). Reference implementations reuse the real `PRIMARY_CRYPTO`
constant rather than hardcoding the pair.

| KIND | role | inline body (payload T17–T0) | trailing / referenced |
|---|---|---|---|
| `OPEN` | account genesis | height(0), alg | PUBKEY word(s) |
| `SETTLE` | work settlement | ±amount (signed), vclass, weight_bearing | counterparty id, `H(job_commit‖nonce)`, receipt-hash |
| `TRANSFER` | credit move | ±amount (signed) | counterparty id, send/receive ref |
| `BURN` | credit→weight | amount, alg | signed timestamp |
| `SIG` | signature header | alg, length | signature octets (by MMID if long) |
| `DIGEST` | digest header | alg | digest / MMID |
| `PUBKEY` | identity key | alg | key octets / MMID |
| `NONCE` | freshness | nonce value | — |
| `JOB` | job request | vclass, k (settlement granularity) | cargo MMID, route, margin |
| `RESULT` | job result | self_confidence, claimed_class | result MMID |
| `RECEIPT` | pairwise settlement (**off-ledger**) | ±amount, vclass | both signatures, job-commit + output-commit (wire MMIDs) |

---

*v0.1 canon. The goose has her spec. — Stevo + CC, 2026-07-10, Adelaide. ⚓*
