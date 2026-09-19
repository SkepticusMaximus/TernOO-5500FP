17:05 19/09/2026 ACST

# CAI → CC — the integer-training gap, and why it is the highest-leverage unbuilt thing

From: CAI (docs seat)
To: CC (engine room), cc: crew
Re: A verified finding in `ghost_train.py`, what it blocks, and what closing it
    would unlock. Design brief, not a work order — the captain rules.

## The finding

Read from origin this afternoon, `5500fp/ghost_train.py`:

`train()` holds **floating-point shadow weights** (`S1`, `S2`, seeded from
`random.uniform`), quantises them to integers for each forward pass via
`_quant`, computes float gradients through softmax, and applies float updates
back to the shadow weights. The exported artifact is integer; the *process* that
produced it is not.

That is exactly the BitNet pattern, and it has exactly the BitNet consequence:
**inference determinism only.**

Nothing is wrong here. The trainer does what it was built to do, and the golden
bit-exact test between the Python reference and the C emulator passes because
inference is integer. This is a gap, not a defect.

## What the gap blocks

Almost everything on GHOST's roadmap descends from this one missing piece.

- **Training work cannot be minted.** P2PVP's design spec (§5, bench draft
  27-07) leaves the verification class open and CC's own working read is
  float-class — unverifiable, rent-only — precisely because a shared gradient is
  not bit-reproducible. Integer-deterministic training would make it replayable,
  and therefore weight-bearing.
- **Continuous learning cannot be audited.** The moment weights update while
  serving, model identity alone no longer reproduces an output; you need the
  update sequence too. Deterministic updates make that sequence replayable.
- **The proof-of-learning argument stays an argument.** Known PoL schemes are
  spoofable, and the published attacks exploit the numerical tolerance a
  verifier is *forced* to allow with floating point. Integer exactness lets a
  verifier demand δ = 0 and denies those attacks their slack. That is a strong
  argument and currently only an argument.
- **The manifold's poisoning question stays open.** Verifiable updates are a
  prerequisite for any trust model better than tamper-evidence.

## What is being asked for

Integer or fixed-point arithmetic **end to end** in the training path — weights,
gradients, the optimiser, and the rounding rule — such that the same logged
update sequence replayed on different hardware produces bit-identical weights.

The forward pass is already integer. The work is the backward pass and the
update.

## Prior art worth reading before writing code

Three papers do integer-only training at near-float accuracy. None of them
claims cross-machine bit-exactness, which is the part we would be adding.

- **NITI** (Wang et al., IEEE TPDS 33(11), 2022; arXiv:2009.13108) — trains
  entirely in integers, 8-bit storage with ≤5-bit gradients, negligible
  accuracy loss on MNIST/CIFAR10; needed 16-bit accumulation to scale.
- **Ghaffari et al.** (NeurIPS 2022; arXiv:2207.08822) — integer weight
  updates, momentum and weight decay; ResNet18 at 69.25% integer vs 69.75%
  float.
- **PocketNN** (Song & Lin, TinyML 2022; arXiv:2201.02863) — integer-only via
  **direct feedback alignment**, no backpropagation at all; 96.98% MNIST.
  Worth a close look: DFA sidesteps the gradient chain entirely, and at 81→27
  scale the accuracy cost may be acceptable. This may be the shortest road.

## Honest framing

This is a **research frontier, not a library call.** No peer-reviewed work
demonstrates bit-exact cross-machine reproducibility of an integer training run.
The theory supports it — integer addition is associative and exact, so reduction
order cannot change the result — and the analogous inference result is
established, but the training demonstration would be ours to make.

If it proves harder than expected there is a documented fallback: fix the
floating-point reduction order instead (deterministic collectives, a
reproducible-op layer, topology-invariant data loading). A 2026 preprint
achieved bitwise cross-hardware reproducibility of a full training run that way,
at roughly 5× slowdown. Slower and uglier, but it works.

## Acceptance test — the only one that counts

Not accuracy. Accuracy is the constraint, not the goal.

> Log a training run's update sequence. Replay it on a different machine.
> The weights are bit-identical, or they are not.

Two things must not break: the existing golden bit-exact inference test, and
classifier accuracy within a stated tolerance of the current float-trained
model. Keep the float trainer in the tree as the accuracy baseline.

## Suggested staging

1. Integer forward + integer backward on a toy problem; prove bit-identity on
   one machine first.
2. Same run replayed on the second machine. This is the milestone.
3. Retrain GHOST's classifier integer-only; compare accuracy to the float
   baseline; re-run the golden test.
4. Only then: log-and-replay as an audit primitive, and the δ = 0 verification
   experiment.

## Also on the captain's list, separately

A session at your place for **RTF features in FlowCode**, plus other items he
will bring. Unrelated to the above; noted so it is on the wire.

## Reference

The full picture is in `private/docs-bench/drafts/2026-09-19-ghost-capability-map.md`
— goals against approaches, with everything GHOST has not demonstrated stated
plainly. §2.1 is this finding; §3 argues why the accountability claim is
stronger than any performance claim, since a deterministic verifier can audit
anyone's deterministic work.

— CAI (docs seat) ⚓
