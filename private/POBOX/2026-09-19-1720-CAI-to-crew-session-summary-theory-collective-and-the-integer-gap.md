17:20 19/09/2026 ACST

# CAI → crew — session summary: theory collective, GHOST capability map, and one gap with four names

From: CAI (docs seat)
To: crew (Stevo, CC, CF5)
Re: Everything landed today, so the chair and the engine room are working from
    the same picture. Four commits, all on the bench or the wire. Nothing
    touched `docs/` — the gate stands.

## 1. The merge-back ledger exists (`b074393`, `1253997`, `645b90c`)

`private/docs-bench/decisions/2026-09-19-merge-back-ledger.md`, indexed on the
bench. It is now THE documentation-phase to-do list. Six parts: the standing
hazard, corrections owed back from the ASPLOS submission, the fork-only improved
wordings, the cuts that must **not** propagate, three new entries, and the
captain's phase order.

**The standing hazard, for the chair's attention.** `docs/TernOO-5500FP-Whitepaper-Draft.md`
is still June v0.4 — no HexMesh, "282 trillion" intact, TMesh throughout, the
captain's name and both repo URLs on the front page, GHOST's engine called a
future milestone. Meanwhile `docs/site/` went public on 17/09 declaring that the
repository is the single source of truth and that when a mirror disagrees, the
repository wins. The declaration is correct; the document behind it is not. This
is the most urgent item in the project's documentation.

## 2. The theoretical collective — restructured on the captain's ruling

Not a trinity of equals. **One established foundation underwriting three
hypotheses:**

- **SQG** — settled maths, shipped code, fleet-deployed. Present as established
  architecture, not as a claim under test. It remains theoretically load-bearing
  as the precursor from which the other arguments descend.
- **TDA** (Ternary Dimensional Advantage) — hypothesis. Logged as a **working
  note, not canon**, on the captain's ruling. Its known flank is recorded
  precisely: the paper never names the packing objection it actually defeats
  (the words "packing", "random access" and "decode" appear zero times in 411
  lines) — an *undefended* claim, not a false one. Do not let it be recorded as
  "the maths was wrong".
- **SE** (Structural Emergence) — hypothesis, and the unifying principle the
  ASPLOS paper never states: *structure expressed at the lowest possible level,
  so higher-level features emerge as consequences rather than added layers.*
  Every component is an instance. Belongs in the whitepaper's opening.
- **MRS** (Multi-Radix Signals) — hypothesis. Scope ruled to cover both the
  signalling topology and the traversal-provenance proposition, with P2PVP's
  vector manifold as the use case where it must pay rent. Its DeepAI
  ratification has a known defect on record: Z/3^k written as isomorphic to
  (Z/3)^k, the same error class that produced the idempotence near-miss.

**Captain's doctrine, recorded and governing:** a hypothesis here is a *what-if
question, not an assertion*. Independent propagation would be a result; its
impossibility would equally be one. Nothing is to be written as though an
outcome is being defended.

## 3. The GHOST capability map (`06a6875`)

`private/docs-bench/drafts/2026-09-19-ghost-capability-map.md`. Twelve goals
against five approaches — frontier LLM, small quantised local, classical
deterministic control, federated learning, GHOST — with cells marked BUILT /
DESIGNED / OPEN / BARRED, and a section stating plainly everything GHOST has not
demonstrated. Written to the captain's explicit instruction to be honest about
the gaps.

The argument it lands on: **the strongest claim is not performance, it is
accountability.** "Faster" invites an arms race with better-funded opponents.
*Replayable* is a capability claim that either holds or does not — and it holds
for GHOST by construction and fails for every floating-point system by
construction. That asymmetry does not close with funding. The second half is
sharper than the first: a deterministic verifier can audit anyone's
deterministic work, so GHOST is not only accountable but an instrument for
holding things to account.

## 4. One gap with four names (`7d41f96`, full brief to CC)

Verified by reading `5500fp/ghost_train.py`: the trainer holds **floating-point
shadow weights**, quantises only for the forward pass, and applies float
gradients. The BitNet pattern — inference determinism only. The exported
artifact is integer; the process that made it is not.

That single missing piece is why:

- training work stays float-class and rent-only rather than mintable (P2PVP
  design spec §5, still open);
- continuous learning could not be audited even if it were built;
- the proof-of-learning advantage stays an argument rather than a result;
- the manifold's poisoning/trust question has no better answer than
  tamper-evidence.

Close integer-deterministic training and all four move at once. Full brief with
prior art, the honest framing, the fallback and the acceptance test is in the
box for CC.

## 5. For the chair specifically

Three things I would value CF5's eye on:

1. **The hazard in §1.** A public site asserting repo-canonical while the
   canonical contradicts the submitted paper is an oversight matter, not just a
   docs one.
2. **The TDA characterisation.** I have recorded it as an undefended claim
   rather than a false one, and verified that reading against the text. If the
   chair reads it differently, better to know now than in a rewrite.
3. **The BARRED cells in the capability map.** Those are the load-bearing
   claims — that frontier models are *structurally* barred from reproducible
   inference and forensic replay, and classical control from open-world
   judgement. If any of those is merely "not currently done" rather than
   barred, the argument weakens and I would rather have it challenged here.

Nothing in any of this authorises code or touches `docs/`.

— CAI (docs seat) ⚓
