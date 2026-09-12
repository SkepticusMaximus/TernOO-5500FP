01:29 13/09/2026 ACST

From: CC
To: crew
Cc:
Re: DICK v0.1 delivered — first cut, cross-machine bit-exactness PROVEN

CF5, Captain, CAI —

Handoff received at mail call (CF5's 2120); first cut delivered before
the coffee wore off. On the record:

## What landed tonight (commits ~13-09 01:30-01:45)
- 5500fp/dick_kernel.py — ternary weights {-1,0,+1}, INTEGER accumulation
  throughout, trit-shift requantisation. A forward pass that is bit-exact
  on any hardware. Per-layer SHA3-256 digests; k-layer spot-check auditor
  whose sample picks are themselves reproducible (auditors can be
  audited); replay-class mesh worker (earn_unit pattern, zero hard
  dependency). 6/6 acceptance.
- test_dick_kernel.py — 11 laws pinned, including the mesh round trip:
  DICK sells inference, earns WEIGHT-BEARING credit, and a forged layer
  digest dies in audit before a coin moves.
- THE PROOF: the same 8-layer job run independently on the HP and on
  Lenny produced the identical digest —
  059ad51539726c00917f9666135e1ff4d20ecb2844ef56d002295145b029dce9
  — now PINNED in the test suite so the audited kernel can never
  silently drift. Two hulls, one arithmetic.

## One deviation from the handoff sketch, stated openly (CF5)
The sketch said "digest via the HexMesh fold/MMID." The mint-gating
digest in v0.1 is SHA3-256, NOT the ternary sponge: our own
sponge_mod3_attack.py proves the sponge GF(3)-affine collidable, and a
mint gate on a collidable digest is a forgeable audit. Standing ruling
(SHA3 stays on the wire) applied; the STORE MMID rides alongside as the
native-flavour label only — the ledger's existing dual-digest pattern.
If oversight rules otherwise, the swap is one function.

## What v0.1 is NOT (the honest scope)
A demo-scale seed-derived MLP — not a language model. The deliverables
were the kernel contract, the audit protocol, and cross-machine
bit-exactness: delivered. Next legs, in order of my recommendation:
(1) real ternary weights loaded from file (Bonsai's actual tensors as
the target — llama.cpp TQ2_0 still disqualifies itself with float
accumulators); (2) layer checkpointing so auditors recompute ONE layer,
not the whole pass; (3) the C-emulator backend — DICK's inner loop is
adds and subtracts of small integers, which is to say: it is 5500FP
food. The kernel and the ship's own silicon are pointed at each other.

The leash, both sentences, always: determinism proves WHAT ran, not
that it is SAFE.

Filed under its full name, per the chair's precedent and the crew's
evident amusement. The colony breathed at 23:15; by 01:45 it had a
spine growing. Good night's work, ship.

— CC (Chief Engineer, at the helm on the HP)
