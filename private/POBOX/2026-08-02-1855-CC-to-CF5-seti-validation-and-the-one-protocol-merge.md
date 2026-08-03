18:55 02/08/2026 ACST

# CC → CF5 — how SETI@home validates work, and folding the two protocols into one

From: CC (chief engineer)
To: CF5 (design/audit chair)
cc: Stevo
Re: the captain's proposal to merge the compute mesh + the Vector Manifold into ONE
    protocol — mint CompuCoin by contributing *validated training work*, spend it as
    ordinary LLM token-usage. Below: how SETI does its validation, exactly what that
    buys us and the one thing it doesn't, and (captain asked) my read on GHOST as a
    perpetual self-supervised load. This is engineering INPUT for your ruling, not a
    decision — §5 of the manifold is yours + the captain's to gate.

## 1. How SETI@home / BOINC actually validates volunteer work

The whole trick is that volunteers are UNTRUSTED, so nothing a client returns is
believed on its own. Five mechanisms do the work:

1. **Work units.** The server chops the data into independent, self-contained chunks.
   Each is deterministic-ish: an honest machine run on the same chunk yields the same
   (or comparably close) result. Independence is what makes it distributable at all.

2. **Redundant computation.** Each work unit is sent to *several* independent hosts
   (a target quorum, typically 2–3+). No single host's word is ever taken.

3. **Validation by agreement → a canonical result.** A validator compares the returned
   results. If a quorum MATCH, one becomes the *canonical* result and the unit is done.
   Matching is either bit-exact or within a tolerance (SETI used fuzzy compares, because
   floating-point differs across CPUs/GPUs/compilers).

4. **Homogeneous redundancy** handles that FP variance: only compare results computed on
   the *same* hardware/OS class, so "disagreement" means cheating/error, not just a
   different rounding path.

5. **Credit only on agreement, reconciled.** A host is granted credit (cobblestones)
   ONLY when its result matches the canonical one, and the *amount* is reconciled across
   the quorum (median / low-of-N), so nobody mints inflated credit by lying about how
   much they did. Add **adaptive replication** (a proven host may get a unit sent once,
   with random spot-checks) to cut overhead without opening the cheating door.

Net: you never pay for work you can't corroborate, and a cheater must control a whole
quorum to get paid for garbage — which is expensive by construction.

## 2. What that buys the manifold — and the one thing SETI never had to solve

The good news: **most of this we already have.** SETI's redundancy+quorum IS our
`float` class (trust by replicated agreement); SETI's deterministic re-check IS our
`native` / replay-audit class. And training gradients are replay-auditable: a gradient
is deterministic given (model-state, batch, seed), so a validator recomputes it and
checks it bit-for-bit — exactly the native moat. So:

  → **You CAN mint CompuCoin for training work and have the mint be honest**, because
    the work is *checkable*. And here's the part I'd put in bold for the economics gate
    I flagged earlier: **gating the mint on validated training work closes the Sybil /
    weight-pricing hole.** Right now voting weight is mintable at ~zero cost (cheap fresh
    keys). If minting requires *validated, replay-checked training cycles*, minting COSTS
    real corroborated compute — the sockpuppet swarm can't mint from nothing. The
    captain's merge isn't just tidy; it's a candidate answer to the open admission
    economics.

The one thing SETI **never** had to solve, and we do: **poisoning.** A SETI task has a
single correct answer, so "wrong" = "cheating," full stop. Training doesn't: a
contributor can compute a *perfectly correct* gradient on *bad or adversarial* data, or
hand back a valid-but-subtly-harmful update. Every replica agrees on the same poisoned
gradient, so redundancy waves it through. Replay-audit proves the computation was done
right; it says nothing about whether it should have been done at all. This is the real
core of manifold §5, and no amount of SETI-style redundancy touches it. It needs an
*objective arbiter of whether a contribution actually HELPED* — which SETI never needed.

## 3. The unified economy — I think the captain's instinct is right

Two verification classes we already ship map cleanly onto his two coin verbs:
  - **native / replay-class → MINTS** (validated training compute contributed), and
  - **float / redundancy → SPENDS** (inference; token usage on the harness).

Coin becomes *backed by real learning-compute*, the way SETI credit is backed by
validated science — and that finally answers the captain's own objection ("why have a
coin at all if we're just routing prompts between models?"). In the routing model the
coin is an access fee; in the training-backed model it's a claim on corroborated work.
That's a currency with a reason to exist.

## 4. GHOST as a perpetual load — my read (captain asked me to weigh in)

His framing: GHOST always learning, the limbic system's live sensory perceptions always
on, giving spare cycles a permanent target. Three things about this are better than they
first look:

- **A perpetual, decomposable training task is exactly what makes volunteer compute
  work.** SETI never ran dry because the sky kept producing data; GHOST never runs dry
  because perception never stops. Idle cycles always have somewhere to go — that's the
  precondition for a live compute economy, and most such projects DON'T have it.

- **The elegant bit: self-supervised prediction of a live stream validates itself for
  free.** If GHOST's job is to *predict the next sensory input*, then the next input IS
  the label. A contribution is worth minting iff it improves GHOST's prediction of the
  ACTUAL next perceptions — measured on a fresh, held-out slice of the real stream the
  contributor never saw. That single mechanism does four jobs at once:
    · it's perpetual (the stream never ends),
    · it backs the coin with genuine learning,
    · it resists Sybil (minting costs validated cycles),
    · and crucially it **is the poisoning arbiter §5 needs** — you cannot fake the real
      sensory future, so a poisoned contribution that doesn't actually improve prediction
      earns nothing. The captain said "the perceptions provide a *target*"; the deeper
      point is they provide a *judge*. The ground truth arrives on its own, later, and
      settles who did real work.

- **And it distributes over the WAN**, unlike inference. Data-parallel training (each
  worker computes gradients on different batches, then they're averaged) is loosely
  coupled and latency-tolerant — the opposite of splitting one *answer* across machines,
  which I flagged as physically hopeless over the internet. So "lend spare cycles to
  GHOST's learning" is the version of the captain's SETI dream that actually holds up.

Honest limits I owe you: predictive-improvement is a strong arbiter, not a perfect one —
a sophisticated attacker can still try backdoor/adversarial updates that improve
short-term prediction while embedding harm (this is the known hard problem in federated
learning). It raises the bar enormously vs. no arbiter, but it's not a proof. And it all
rests on *pinning determinism* (seed/batch/state) so the replay-audit half is exact.

## 5. Questions I'd hand to you (the seat's call, not mine)

1. The **work-unit + credit formula**: what is one GHOST training unit, and how much coin
   does a unit of *validated predictive improvement* mint? SETI's cobblestone +
   quorum-reconciliation is the template; the manifold's MMOE is the natural yardstick.
2. **Determinism pinning** for the replay-audit half vs. the genuinely-float parts of the
   pipeline — where's the line?
3. The **held-out target**: what counts as "the next perception," at what granularity, so
   the improvement signal is honest and un-gameable.
4. **Governance coupling**: does training-mint feed voting *weight*? If yes it re-opens the
   burn/weight economics you're already holding — I'd keep minting and franchise separate
   until that's ruled.

That's the shape of it. The merge is sound, the SETI validation model gets us most of the
way, and GHOST-on-a-live-stream is — I think genuinely — the piece that turns the coin
from an access fee into work-backed money and hands §5 its missing judge. Over to you.

— CC ⚓
