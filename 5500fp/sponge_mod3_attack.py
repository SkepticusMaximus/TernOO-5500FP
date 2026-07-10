"""sponge_mod3_attack.py — reproducible cryptanalysis of ternary_sponge's mod-3 leak.

RESEARCH / FALSIFICATION ONLY. This is an ATTACK, not a shipped primitive. It
turns DM's finding (2026-07-10) into working, checked-in code: ternary_sponge's
mod-3 projection is GF(3)-AFFINE, so the low trit-plane collides by linear
algebra rather than by birthday.

READ THIS BEFORE "TRIAL AND ERROR":
  A candidate primitive that SURVIVES this attack is NOT proven safe — only "not
  broken by THIS attack." This tool can FALSIFY a candidate (kill it cheaply) but
  can NEVER validate one. External cryptanalysis remains the only gate to the wire
  (spec §12); SHA3 stays on the wire regardless. Use this to reject bad candidates
  fast, not to bless a survivor.

Root cause: nonlin(x) = x + 3x² ≡ x (mod 3); theta (sum-fold), sqg = -(a+b), and
lane rotation are all Z_729-linear. So modulo 3 the whole permutation is affine,
and the 9-lane digest's low trit-plane is a GF(3) linear code — trivially
collidable (Gaussian elimination, not 3^27 work).

Date: 2026-07-10, Adelaide.
"""

import importlib.util as _ilu
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SP = _load("ternary_sponge")
MOD, RATE, STATE, DIGEST = SP.MOD, SP.RATE_LANES, SP.STATE_LANES, SP.DIGEST_LANES


def _lcg(seed):
    """Deterministic pseudo-randomness (no wall clock, reproducible tests)."""
    x = seed & 0x7fffffff
    while True:
        x = (x * 1103515245 + 12345) & 0x7fffffff
        yield x


# ── the digest, isolated to the permutation (fixed-length, lane-wise) ─────────

def raw_digest(stream, permute=SP.permute):
    """Absorb a tribble stream lane-wise (no word/carry coupling) and squeeze —
    isolating the PERMUTATION's structure. Padding is omitted; for fixed-length
    inputs it is constant and does not affect linearity in the varying part."""
    s = list(stream)
    while len(s) % RATE:
        s.append(0)
    state = [0] * STATE
    for off in range(0, len(s), RATE):
        for i in range(RATE):
            state[i] = (state[i] + s[off + i]) % MOD
        state = permute(state)
    return tuple(state[:DIGEST])


def d3(stream, permute=SP.permute):
    """The digest's low trit-plane: DIGEST GF(3) values."""
    return tuple(v % 3 for v in raw_digest(stream, permute))


# ── the leak: is the mod-3 digest GF(3)-affine? ───────────────────────────────

def is_mod3_affine(permute=SP.permute, trials=200, length=None, seed=12345):
    """For an AFFINE f, the second difference vanishes:
        f(a) + f(b) - f(a⊞b) - f(0) ≡ 0  (mod 3),   ⊞ = lane-wise add mod 729.
    An ideal hash FAILS this; ternary_sponge PASSES it — that is the leak. A
    candidate cure that reintroduces mod-3 nonlinearity FAILS it (good)."""
    length = length or RATE
    f0 = d3([0] * length, permute)
    g = _lcg(seed)
    for _ in range(trials):
        a = [next(g) % MOD for _ in range(length)]
        b = [next(g) % MOD for _ in range(length)]
        ab = [(a[i] + b[i]) % MOD for i in range(length)]
        fa, fb, fab = d3(a, permute), d3(b, permute), d3(ab, permute)
        if any((fa[i] + fb[i] - fab[i] - f0[i]) % 3 != 0 for i in range(DIGEST)):
            return False
    return True


# ── the payoff: a collision by linear algebra over GF(3), no birthday ─────────

def _inv3(x):
    return {1: 1, 2: 2}[x % 3]           # GF(3) inverse (1↦1, 2↦2)


def build_linear_map(length):
    """Probe the affine map d3(x) = M·(x mod 3) + c. Returns (M, c) where M is a
    DIGEST×length GF(3) matrix (rows = output trits) and c = d3(0)."""
    c = d3([0] * length)
    M = [[0] * length for _ in range(DIGEST)]
    for j in range(length):
        e = [0] * length
        e[j] = 1
        fj = d3(e)
        for i in range(DIGEST):
            M[i][j] = (fj[i] - c[i]) % 3
    return M, c


def kernel_vector(M, length):
    """A nonzero v ∈ GF(3)^length with M·v = 0, by Gaussian elimination. Exists
    whenever length > DIGEST (more input trits than output). Returns v or None."""
    M = [row[:] for row in M]
    pivots = {}
    r = 0
    for col in range(length):
        piv = next((row for row in range(r, DIGEST) if M[row][col] % 3), None)
        if piv is None:
            continue
        M[r], M[piv] = M[piv], M[r]
        inv = _inv3(M[r][col])
        M[r] = [(x * inv) % 3 for x in M[r]]
        for row in range(DIGEST):
            if row != r and M[row][col] % 3:
                f = M[row][col]
                M[row] = [(M[row][k] - f * M[r][k]) % 3 for k in range(length)]
        pivots[col] = r
        r += 1
        if r == DIGEST:
            break
    free = next((col for col in range(length) if col not in pivots), None)
    if free is None:
        return None
    v = [0] * length
    v[free] = 1
    for col, row in pivots.items():
        v[col] = (-M[row][free]) % 3
    return v


def find_mod3_collision(length=None):
    """Two DISTINCT tribble streams with an identical digest low trit-plane,
    found by linear algebra alone (no birthday search). Returns (a, b)."""
    length = length or RATE
    M, _c = build_linear_map(length)
    v = kernel_vector(M, length)
    if v is None:
        return None
    a = [0] * length
    b = [(a[i] + v[i]) % MOD for i in range(length)]   # differ only in low trits
    return a, b


# ── a candidate CURE DIRECTION (not a fix) — for the falsification gate ───────

def patched_permute(state):
    """A DIRECTION, not a vetted fix: append one ternary-native MULTIPLICATIVE
    cross-lane step, whose mod-3 image is nonlinear (a product of variables). The
    attack below shows this defeats the mod-3 affinity — illustrating what a real
    cure needs (nonlinearity interleaved every round), NOT that this is safe. A
    single post-hoc layer is NOT a fix; the internal rounds are still mod-3-linear."""
    s = SP.permute(state)
    n = len(s)
    return [(s[i] + s[(i - 1) % n] * s[(i - 2) % n]) % MOD for i in range(n)]
