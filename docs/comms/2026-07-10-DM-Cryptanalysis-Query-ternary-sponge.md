# DM consultation — cryptanalysis of `ternary_sponge` for WIRE use (P2PCP)

**To:** DeepMind (cryptanalysis consult — the DM loop that set the sponge's original parameters, 6 Jul 2026)
**From:** Stevo (SkepticusMaximus) + CC (chief engineer)
**Date:** 2026-07-10, Adelaide
**Type:** one-shot cryptanalysis request. Attack it; tell us what (if anything) makes it wire-safe.

## 0. Why we're back

You blessed `ternary_sponge` for a **local** role: content-store addressing (MMID), sort key
among resident patterns, verify-on-fetch, accident-proof identity. `KNOWN.md` records the
caveat we agreed: **accident-resistance and local tamper-evidence YES; remote-adversarial
NO, pending external cryptanalysis.**

We are now building **P2PCP** — a public, permissionless compute mesh among mutually-
distrusting strangers. It wants a **ternary-native digest on the wire**, in two adversarial
roles the local caveat explicitly does not cover:

1. **Wire MMID** — content addressing of cargo fetched from strangers. A collision lets an
   adversary **substitute cargo** and survive verify-on-fetch.
2. **Receipt output-commitment** — a worker signs a receipt committing to `H(output)`; any
   peer audits by **replaying the job and re-hashing**. A collision lets a worker **sign for
   output it never produced** and survive the replay challenge — which would corrupt the
   proof-of-work-done that the whole economy (and the voting franchise) rests on.

Until you clear a ternary-native form, P2PCP uses **SHA3-256 for these two wire roles**
(behind an `alg` selector; the sponge keeps the local store). This request is to determine
whether — and at what parameters — the sponge can take the wire roles as `alg=1`.

**Doctrine (unchanged):** we will not deploy a home-rolled primitive against strangers
before hostile review. A "not yet / not at these parameters" is a perfectly good answer.

## 1. The construction (complete — analyze cold)

Balanced-ternary sponge over **tribble lanes** in `Z_729` (one tribble = 6 trits; `729 = 3^6`).
Built ONLY from balanced-ternary-native ops: add mod 729, multiply mod 729, lane rotation,
and the Steiner quasigroup `⊕`. No binary S-boxes, no lookup tables.

**Parameters**
```
state    = 45 lanes = 270 trits
rate     = 27 lanes = 162 trits   (absorb width)
capacity = 18 lanes = 108 trits   (~171.2 bits)
digest   =  9 lanes =  54 trits   (~85.6 bits)   ← squeezed once
rounds   = 8
```

**Primitive maps**
```
sqg(a,b)  = -(a + b) mod 729                     # Steiner quasigroup (linear)
nonlin(x) = x + 3·x^2 mod 729                    # bijection on Z_729; the ONLY nonlinearity
```

**Round constants** — nothing-up-sleeve LCG, seed 27: `x ← (41·x + 13) mod 729`, one value
per (round, lane). `rc[r][i]`.

**Permutation** `permute(state)` — 8 rounds, each:
```
1. theta (global linear diffusion):
     t = (sum of all 45 lanes) mod 729
     s[i] = (s[i] + rc[r][i] + t) mod 729         for all i
2. substitution (nonlinear):
     s[i] = nonlin(s[i])                           for all i
3. local diffusion (linear):
     s[i] = sqg(s[i], s[i-1])   = -(s[i] + s[i-1]) mod 729   (indices mod 45)
4. rotation (linear):
     rotate lanes left by k = (2·r + 7) mod 45     (stride coprime to 45)
```

**Absorb / squeeze** (`digest(words)`)
```
serialize each 24-trit word → 4 tribbles (MSB-first, order-preserved)
append pad tribble 1, then a length tribble (len mod 729), zero-pad to a multiple of rate
state = 0
for each rate-width block:  s[0..26] += block (mod 729);  state = permute(state)
return state[0..8]            # 9 lanes = the 54-trit MMID
```
(Reference implementation: `5500fp/ternary_sponge.py`, ~140 lines, and its round-trip /
bijectivity tests. We can send it verbatim.)

## 2. Threat model (wire)

A remote adversary with **offline grinding power** (say up to ~2^80 work) who wants either:
- a **collision** `H(m1) = H(m2)`, `m1 ≠ m2` — to substitute cargo, or to sign for output
  never produced; or
- a **second-preimage** of a target's committed digest.
Length-extension is not a concern (fixed-length, capacity-protected squeeze), but please
confirm. There is no secret key in these roles (pure hashing).

## 3. Our own security estimate — please confirm or destroy it

- **Collision (generic birthday on the 54-trit output):** `2^(85.6/2) ≈ 2^43`.
  **This is our headline worry:** ~43-bit collision resistance is *grindable* by a wire
  adversary. The **output length**, not the capacity, appears to be the binding constraint.
- **Capacity** is 108 trits (~171 bits), so `2^(c/2) ≈ 2^85` — ample; it does not bottleneck.
- **Hypothesis:** for the wire roles, simply **squeeze a longer digest** — e.g. 27 lanes /
  162 trits (~256-bit space → ~128-bit collision) — with capacity already sufficient, gets
  us to a conventional 128-bit collision target **without touching the permutation**. Is
  that sound, or does the permutation fail below the birthday bound (structural attacks)?

## 4. The specific questions

**Q1 — Digest length.** Confirm/correct the ~43-bit collision estimate. Is a longer squeeze
(e.g. 27 lanes) the right and sufficient fix for the wire roles, given capacity = 108 trits?

**Q2 — Is one quadratic map enough nonlinearity?** The *only* nonlinear component is
`nonlin(x) = x + 3x²`; theta, sqg, and rotation are all `Z_729`-linear. Over 8 rounds, does
the algebraic degree grow fast enough to resist algebraic / Gröbner-basis collision
engineering, or is the whole permutation effectively low-degree?

**Q3 — The mod-3 filtration (our sharpest worry).** `nonlin(x) = x + 3x² ≡ x (mod 3)` — the
substitution is the **identity on the least-significant trit**, and the linear maps are
trit-wise linear. Does the construction therefore admit an **invariant / predictable
projection** modulo 3 (or mod 9, mod 27) — i.e. does the least-significant trit-plane (or a
low-order `3^k` quotient) evolve *linearly and independently*, giving a distinguisher or a
collision path cheaper than birthday? This is the attack we would try first; please try it.

**Q4 — Diffusion & round count.** theta gives full-state diffusion in one round (any 1-lane
delta touches all lanes), and `nonlin` is a bijection. Is **8 rounds** an adequate security
margin against differential and linear cryptanalysis adapted to `Z_729`, or what round count
would you require for the wire roles? What is the differential uniformity / linearity of
`nonlin` over `Z_729`?

**Q5 — Round constants.** The `41·x + 13 mod 729` LCG has short period and obvious algebraic
structure. Does using a weak-PRNG constant schedule create exploitable symmetry (e.g.
rotational or self-similarity attacks across rounds), or is any distinct nothing-up-sleeve
schedule fine here?

**Q6 — Padding / domain separation.** Is the `1`-then-length-tribble padding injective and
free of trivial collisions for our fixed-rate use, and does it need explicit domain
separation between the two wire roles (wire-MMID vs output-commitment) to stop cross-role
confusion?

**Q7 — Bottom line.** For the wire roles against a ~2^80 adversary, is the sponge
**(a) safe as-is**, **(b) safe with a longer digest only**, **(c) safe with a longer digest
+ more rounds**, **(d) needs a stronger nonlinear layer**, or **(e) keep SHA3 on the wire —
the sponge is a local-store primitive and should stay one**? Any of these is a fine answer;
we want the honest one.

## 5. What we are NOT asking

- We are **not** asking you to design a ternary-native *signature* — ed25519 stays as
  `alg=0` for signing, indefinitely, until/unless a separate consult says otherwise. This
  request is the **digest** only.
- We are **not** asking for a blessing under time pressure. SHA3 covers the wire today; the
  sponge keeps the local store regardless of your answer. A ternary-native wire digest is a
  *want*, not a blocker.

*— Stevo + CC. One round trip; we cut nothing wire-facing on the sponge until you reply. ⚓*
