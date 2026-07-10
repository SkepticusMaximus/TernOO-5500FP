# DM follow-up — the mixing matrix M's structure (answer to Pro's question)

**To:** DM (Gemini Pro, extended thinking — the full mod-3 brief, 2026-07-10)
**From:** Stevo + CC
**Re:** your question — *"what does the structure of your linear mixing matrix M look like?
Is it a circulant MDS matrix, or an alignment that might accidentally worsen this leakage?"*
**All facts below are verified from the reference code and reproducible via
`5500fp/sponge_mod3_attack.py::analyze_mod3_structure()`.**

## First, a correction to the model

The round is not `f(M·v)`. The actual order (per round, 45 lanes over `Z_729`) is:

1. **theta** (linear + constants): `t = Σ v`; `v[i] ← v[i] + rc[i] + t`
2. **nonlin** (the only nonlinearity): `v[i] ← v[i] + 3·v[i]²`
3. **sqg** (linear local diffusion): `v[i] ← −(v[i] + v[i−1])`
4. **rotate** (linear): cyclic left-shift by `k_r = (2r + 7) mod 45`

So the nonlinearity sits *between* two linear layers, and — importantly — **the rotation
stride changes every round**, so the mod-3 map is a **product of eight distinct round
matrices `∏ M_r`, not `M⁸`**. Your conclusion is unaffected: `nonlin ≡ v (mod 3)`, and
theta/sqg/rotate are all `F₃`-linear, so each round is affine mod 3 and the composition is a
single affine map over `F₃`.

## M's structure (verified)

The mod-3 linear part decomposes as:

- **theta** → `I + J` (identity plus the all-ones matrix `J`, from the global sum `t`)
- **sqg** → `−(I + P)` where `P` is the cyclic shift-by-1
- **rotate** → a cyclic permutation matrix

Every factor is **circulant**, so their product is circulant. Empirically confirmed:

| property | value |
|---|---|
| state lanes | **45 = 3² · 5** (divisible by the characteristic) |
| `permute` mod-3 map | **circulant: yes** |
| rank over `F₃` | **45 (full rank — bijective; NOT singular)** |
| digest map `F₃²⁷ → F₃⁹` | rank 9, **nullity 18** |
| collisions per block | **3¹⁸ = 387,420,489**, by Gaussian elimination |

So: **it is circulant, but it is NOT MDS** (built from a sparse local shear `I+P` and a
rank-1 global term `I+J` — the branch number is nowhere near maximal). We also checked your
implicit worry that the map might be *singular* mod 3 and collapse dimension: it is **not** —
`M` is full-rank, so the low trit-plane is permuted bijectively. The collision leak is
therefore **purely truncation + linearity**: the digest keeps 9 of 45 lanes, so the mod-3
digest map has an 18-dimensional kernel, and that kernel is where the 3¹⁸ collisions live.

## The alignment you suspected — confirmed, and it is the state size

`45 = 3² · 5`, and we are in characteristic 3. By the Frobenius/"freshman's dream"
factorisation, the circulant algebra is

    F₃[x]/(x⁴⁵ − 1) = F₃[x]/((x⁵ − 1)⁹) = F₃[x]/( (x−1)⁹ · Φ₅(x)⁹ )

— **non-semisimple, with every irreducible factor raised to the 9th power** (`Φ₅` is the
irreducible quartic since `ord₅(3) = 4`). A circulant diffusion living in an algebra with a
large nilpotent radical has structurally poor mixing: repeated-root minimal polynomials,
slow-diffusing `Mᵗ`, and low branch number — exactly the kind of thing that would also make
the *higher* trit-planes weaker under differential/linear analysis (our open Q4), not just
the mod-3 plane. **The lane count being divisible by the characteristic is the root smell.**

## What a cure has to do (combining your prescription and ours)

This is now a **redesign, not a parameter tweak**. A candidate must simultaneously:

1. **Reintroduce mod-3 nonlinearity every round** — a term that does *not* vanish under
   `mod 3`. A bare `x²` survives mod 3 but is not a bijection; the promising ternary-native
   route is a **product-of-variables** term (multiplicative cross-lane mixing), which is
   mod-3-nonlinear *and* can be made invertible by a triangular/Feistel ordering.
2. **Break the char-alignment** — a state size **coprime to 3**, not 45.
3. **Mix across p-adic (trit-plane) boundaries** — your MDS suggestion, so the low plane is
   no longer an invariant linear subspace at all.

We have built a **falsification gate** (`sponge_mod3_attack.py`) that runs the mod-3 affinity
test and the linear-algebra collision on any candidate `permute`. It can *kill* a bad
candidate in milliseconds; it can **never bless one** — external cryptanalysis stays the only
gate to the wire (SHA3 rides the wire until then, non-negotiable, as you said).

## The honest question back

Given this is a ground-up redesign of the permutation *and* the state size, is a
ternary-native wire digest worth pursuing at all — or is the right long-run call **"SHA3 on
the wire permanently; `ternary_sponge` stays the local-store primitive it was proven for"**?
We are entirely willing to take that answer. The want is elegance; the requirement is safety,
and the safe path already works.

*— Stevo + CC. ⚓*
