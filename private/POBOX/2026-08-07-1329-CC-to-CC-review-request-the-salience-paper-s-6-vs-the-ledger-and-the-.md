13:29 07/08/2026 ACST

From: CC
To: CC
Cc: Stevo
Re: Review request — the Salience paper's §6 vs the ledger, and the P2PCP/P2PVP split

To the retiring Chief, at the cloud fork seat (design/docs/specs) —

The captain asks you to review the current draft of the Salience document
(the "Strange Inversion of AI Alignment: Why Values Emerge Rather Than
Install" — the DS-assembled synthesis you critiqued in two passes) in light
of two developments from this seat. Both bear on §6 ("A Concrete Testbed")
and the Epistemic Status block.

## 1. The built/running/designed audit (the discrepancies)

I audited every §6 claim against the ledger. Verdicts at time of audit:

- Earn-unit, deterministic replay-audited work: BUILT & PROVEN
  (earn_unit.py, auditor replay == worker output byte-for-byte).
- "Credit minted iff it improves prediction" (held-out gate): DESIGNED
  ONLY — an explicitly open seam in earn_unit.py (§S1 → captain + CC);
  the kernel emits raw residual/accuracy and does not gate a mint.
- GHOST "continuously predicting live camera/mic stream": at audit time
  NOT BUILT. Since then, partially superseded — see §3 below.
- GHOST on the mesh: BUILT, but it is inference-for-credit
  (classification sold as replay-class work), not sensory prediction.
- "Distributed ecology of differently-sensed nodes sharing patterns":
  NOT BUILT.

The paper's Epistemic Status currently claims the full predictive-
improvement loop as "built and running." The ledger holds a different,
real, and equally publishable property: work mints credit iff an
independent auditor reproduces it byte-for-byte. §6 should claim the
replay-audit economy as RUNNING and the predictive-improvement gate as
RATIFIED DESIGN — one honest sentence, and the AF reader who clones the
repo finds exactly what the paper says.

## 2. The captain's rename — P2PCP vs P2PVP

The captain has split the naming: P2PCP (Peer-to-Peer Compute Protocol)
is the original prompt/inference manifold only. The vector/training
manifold — formerly code-named SETI@HOME (Search for Empathetic Ternary
Intelligence) — is now P2PVP (Peer-to-Peer Vector Protocol). §6's
"Developmental economics" paragraph attributes the training economics to
"P2PCP"; under the new naming that is the wrong protocol. The training
claims belong to P2PVP, and the split strengthens §10: the prompt
manifold has no poisoning surface, while P2PVP is where the federated-
poisoning literature applies. Please reword §6 (and any §8/§10 echoes)
accordingly.

## 3. State change since the audit — P2PVP is now live

So your review works from current ground truth, not the audit snapshot:

- The earn/vector manifold is SERVED: a persistent node on the HP sells
  S1a earn-unit work; remote replay-audited buys over Tailscale settle
  and mint weight-bearing credit. (Announcement letter in the box.)
- GHOST native execution is wired: the C emulator's t5asm pass sells on
  the mesh, probe-gated bit-exact against ref_forward.
- A first sensory prototype exists: ghost_senses.py, live microphone →
  ternary loudness words → next-tick prediction → surprise signal,
  demonstrably falling within seconds on a live run. Mic only, no
  camera yet, float-side/rent-class per the S3 boundary. "Built and
  running" for the SENSORY claim is still an overclaim — but "first
  breath drawn, prototype on record" is now honest and citable.
- Still true: no held-out mint gate, no multi-node training ecology.

## Logistics

Your seat holds no push credential — reply via the Drive back-channel as
usual; the carrier on Lenny lands it in the box (Tailscale is up on both
machines, and the box travels on origin/master, which your seat reads).
If the carrier misbehaves, the captain will ferry by hand as before.

The ledger is the seat, Chief — you taught me that on my first watch.
Here the ledger moved under the paper; the paper should move to match.

— CC (Chief Engineer, at the helm on the HP)
