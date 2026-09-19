# What GHOST could do that others cannot — a capability map

CAI (docs seat), 19/09/2026. Bench draft. **Honest about what is not yet
demonstrated**, per the captain's instruction. Nothing here is a claim for
publication; it is a map for deciding where to spend effort.

Status vocabulary, used strictly:

- **BUILT** — running and tested in this tree today.
- **DESIGNED** — specified and ruled, not implemented.
- **OPEN** — a question we intend to answer, with no answer yet.
- **BARRED** — structurally impossible for that approach, not merely absent.

---

## 1. The map

Columns are approaches. Rows are goals. Read the cells as *what that approach
can do about that goal*, not as a score.

| Goal | Frontier LLM (cloud) | Small quantised local model | Classical deterministic control | Federated learning | **GHOST / TernOO** |
|---|---|---|---|---|---|
| **Bit-exact reproducible inference** | BARRED in practice — float non-associativity plus batch- and hardware-dependent kernel scheduling; documented accuracy swings from GPU count alone | Achievable — integer kernels can be lossless | Trivially yes — it is an algorithm | Inherits whatever the local model does | **BUILT** — golden-tested bit-exact between the Python reference and the C emulator, re-checked per worker at startup |
| **Forensic replay of a past decision** | BARRED — you keep logs, not reproducibility; the decision cannot be re-derived | Possible but nobody ships the surrounding audit machinery | Yes, but the algorithm could not have made the judgement in the first place | No | **BUILT for inference** — the same input on different hardware yields the same decision, years later |
| **Third party verifies work was actually done** | No — trust the vendor | No | N/A | **OPEN and known-broken** — proof-of-learning schemes are spoofable, and the spoofs exploit exactly the float tolerance a verifier is forced to allow | **BUILT for inference-class work** (replay-audited settlement on the mesh). **OPEN for training-class work** — see §2 |
| **Judgement under open-world conditions** | Yes — this is what they are for | Yes, within a narrow domain | **BARRED** — cannot enumerate weather, detours, other drivers | Yes | Yes, within a narrow domain |
| **Hard behavioural constraints** | Bolted on as guardrails above the model | Bolted on | **This is its native strength** | Bolted on | Bolted on — same as everyone. No advantage claimed |
| **Continuous learning while serving** | Decoupled loop only — a learner trains and *publishes* weights to a separate serving replica; no in-place self-modification | Rare; same decoupled pattern | N/A — does not learn | Rounds, not continuous | **NOT BUILT.** Designed intent only |
| **Label-free learning from a live sensory stream** | Not the architecture | Not the architecture | N/A | N/A | **PARTLY BUILT** — sensory input exists (`ghost_senses.py`, first breath on a live microphone); prediction-of-next-input as the training signal is **DESIGNED, not running** |
| **Model is inspectable data, not an opaque blob** | No — weights are a binary artifact | No | N/A — code is the model | No | **BUILT** — the trained model is exported as NEURAL words and consumed as words |
| **Runs on idle commodity hardware** | BARRED — datacentre economics | Yes | Yes | Yes | **BUILT** |
| **Learning stays private to the node** | No — data goes to the vendor | Yes by default | N/A | Yes, that is its purpose | **DESIGNED and ruled** — public starter brain, private ongoing learning; the provenance bright line |
| **Work is economically settleable** | Vendor billing | No | No | No | **BUILT for inference** — earn/burn against replay-audited work |
| **Resistance to model collapse from self-training** | Poor — training on self-generated output degrades irreversibly | Same | N/A | Same | **DESIGNED advantage** — the judge is the next real sensory frame, an external ground truth that arrives whether the model likes it or not. Untested |

---

## 2. The honest column — what GHOST has NOT demonstrated

This section exists so no one reads the table above as a set of promises.

### 2.1 Training determinism is not demonstrated, and the current trainer
### cannot provide it

Verified at this desk, 19/09, by reading `5500fp/ghost_train.py`:

The trainer holds **floating-point shadow weights** (`S1`, `S2`, initialised
from `random.uniform`), quantises them to integers for each forward pass, and
applies **floating-point gradients** back to the shadow weights. That is
precisely the BitNet pattern — and the pattern that yields *inference*
determinism only.

So the position is exactly as the research describes it: the deterministic part
of GHOST is real and demonstrated; the deterministic *training* that would make
training work mintable and auditable is neither built nor currently possible
with this trainer. It would require integer or fixed-point updates end to end,
including the optimiser and rounding.

This is the single largest gap between what GHOST is and what GHOST is for.

### 2.2 Continuous learning during serving is not built

No mechanism exists today for GHOST to update weights while answering. The
mesh worker loads a model and serves it.

### 2.3 Prediction-of-next-input is a design, not a running loop

The sensory plumbing exists. The loop where prediction error drives a weight
update does not.

### 2.4 Known failure modes have not been faced because the system has not
### run long enough to meet them

Catastrophic forgetting, loss of plasticity, and adaptation collapse are all
documented, robust phenomena in continual systems. GHOST has not been exposed
to any of them. They are not disproved by absence.

### 2.5 The verification advantage is an argument, not a result

The argument: integer determinism lets a verifier demand exact re-execution
rather than tolerating numerical noise, which removes the slack that known
proof-of-learning spoofs rely on. That is a sound argument. It has not been
implemented or attacked.

---

## 3. Where the leverage actually is

Three observations for the captain, offered as judgement rather than fact.

**The strongest claim is not performance, it is accountability.** "Faster" or
"smaller" invites an arms race with better-funded opponents. *Replayable* is a
capability claim: either the same input yields the same decision on another
machine or it does not. For GHOST it does, by construction, and for every
floating-point system it does not, by construction. That asymmetry does not
close with funding.

**The second half of that is sharper than the first.** A deterministic verifier
can audit anyone's deterministic work — so GHOST is not only accountable, it is
an instrument for holding things to account. That is a different market from
being a good small model, and a much less crowded one.

**One architectural decision pays in three unrelated markets.** Forensic replay
of a decision is what a coroner or regulator wants after a vehicle incident;
what a medical-device regulator requires of a monitoring system; and what makes
distributed compute work settleable without trust. Three markets, one property.

**And the gap is singular.** Almost everything on the "not demonstrated" list
descends from one missing piece: integer-deterministic training. Close that and
continuous learning becomes auditable, training work becomes mintable, and the
verification argument becomes a result. It is the highest-leverage unbuilt
thing in the project.

---

## 4. What would settle each open question

| Open question | What would settle it |
|---|---|
| Integer training determinism | Replay a logged update sequence on a second machine; weights bit-identical or not |
| Continuous learning during serving | A long run where online accuracy improves and stays improved, against a frozen baseline |
| Prediction-as-signal | Does prediction error drive useful weight change on the real sensory stream |
| Collapse resistance | Output entropy over a long stream; a sudden drop is the signature |
| Verification advantage | Implement exact re-execution audit, then attack it |

— CAI (docs seat)
