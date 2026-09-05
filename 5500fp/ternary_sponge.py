"""ternary_sponge.py — the MMID digest function, per the mathematical
consultation of 6 Jul 2026 (Deep-Mind loop, final parameters).

Construction: a sponge over tribbles (Z_729 lanes), built ONLY from
operations native to balanced-ternary hardware — addition mod 729,
multiplication mod 729, lane rotation, and the cyclic mixing operation
A⊕B = -(A+B) mod 729. No binary S-boxes, no lookup tables.

NAMING NOTE (05-09-2026 audit/ruling): the mixer below was originally
labelled "the Steiner quasigroup operation"; the cyclic form is totally
symmetric but NOT idempotent, hence not Steiner. As a DIFFUSION step no
quasigroup axioms are required, so per the captain's scope ruling the
sponge keeps the cyclic mixer unchanged (digest stability preserved) and
only the label is corrected. The true Steiner operation now lives in
ternoo_gristmill.ternary_op (per-trit, balanced).

Blessed parameters (consultation, Part 2):
  * state  = 45 tribbles = 270 trits   (>= the 243-trit minimum)
  * rate   = 27 tribbles = 162 trits   (absorb width)
  * capacity = 18 tribbles = 108 trits (>= the 81-trit security floor)
  * digest = 9 tribbles = 54 trits     (in the 50-60 recommendation:
             negligible accidental collisions for 10^9 residents,
             with adversarial margin)

Nonlinear step: x -> x + 3*x^2 (mod 729). This map is a BIJECTION on
Z_729 (f(x) ≡ x mod 3 and 3-adic injectivity; pinned by test), built
from add and mul alone — the "nonlinear mixing" the consultation
required to defeat algebraic collision-engineering, in ternary-native
form. Diffusion step mixes each lane with its neighbor via the SQG
operation plus a rotating round constant; ROUNDS=8.

The digest's jobs (and only these): sort key among RESIDENT patterns,
verification tag on fetch, accident-proof identity. Tamper-evidence is
earned by this nonlinearity PLUS full-comparison at insert
(ternoo_content_store.py); the digest never reconstructs content —
pigeonhole forbids it and the design never asks.

Date: 2026-07-06, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

MOD = 729                      # one tribble = 6 trits = Z_729
STATE_LANES = 45               # 270 trits
RATE_LANES = 27                # 162 trits absorbed per block
CAPACITY_LANES = STATE_LANES - RATE_LANES   # 18 lanes = 108 trits
DIGEST_LANES = 9               # 54 trits out
ROUNDS = 8

TRIBBLES_PER_WORD = 4          # a 24-trit TernOO word = 4 tribbles


def sqg(a: int, b: int) -> int:
    """Cyclic mixing operation A⊕B = -(A+B) mod 729 (see NAMING NOTE above:
    kept for diffusion; not the Steiner quasigroup, name retained for API
    stability)."""
    return (-(a + b)) % MOD


def nonlin(x: int) -> int:
    """x -> x + 3x^2 mod 729 — bijective, nonlinear, add+mul only."""
    return (x + 3 * x * x) % MOD


def _round_constants() -> list:
    """Deterministic per-round, per-lane constants from a tiny LCG.
    Nothing-up-the-sleeve: fixed seed 27, classic multiplier."""
    rc, x = [], 27
    for _ in range(ROUNDS):
        row = []
        for _ in range(STATE_LANES):
            x = (x * 41 + 13) % MOD
            row.append(x)
        rc.append(row)
    return rc


_RC = _round_constants()


def permute(state: list) -> list:
    """The sponge permutation: ROUNDS x (constants + nonlinearity +
    SQG neighbor diffusion + lane rotation)."""
    s = list(state)
    n = STATE_LANES
    for r in range(ROUNDS):
        rc = _RC[r]
        # 1) theta — GLOBAL diffusion: fold the whole-state sum into
        #    every lane, so any 1-lane delta reaches all lanes this
        #    round (the local-only neighbor mix provably crawled one
        #    lane per round and never reached the digest window).
        t = sum(s) % MOD
        s = [(s[i] + rc[i] + t) % MOD for i in range(n)]
        # 2) nonlinear substitution on every lane
        s = [nonlin(v) for v in s]
        # 3) local diffusion: each lane absorbs its left neighbor (SQG)
        s = [sqg(s[i], s[(i - 1) % n]) for i in range(n)]
        # 4) rotate lanes by a round-dependent stride (coprime to 45)
        k = (2 * r + 7) % n
        s = s[k:] + s[:k]
    return s


def words_to_tribbles(words) -> list:
    """Canonical serialization: each 24-trit word (int) becomes 4
    tribbles, most-significant first. Order is preserved — the sponge
    is order-sensitive by construction, unlike a bare ⊕-fold."""
    out = []
    for w in words:
        w = int(w) % (MOD ** TRIBBLES_PER_WORD)
        chunk = []
        for _ in range(TRIBBLES_PER_WORD):
            chunk.append(w % MOD)
            w //= MOD
        out.extend(reversed(chunk))
    return out


def digest(words) -> tuple:
    """MMID of a canonical word sequence: 9 tribbles (54 trits).

    Sponge: pad tribble stream to a multiple of RATE_LANES with the
    standard 1,0,...,0 pattern (here: a single 1-tribble then zeros,
    plus a final length lane — unambiguous for our fixed-rate use),
    absorb blockwise into the rate portion, permute; squeeze once.
    """
    stream = words_to_tribbles(words)
    stream.append(1)                              # domain/pad marker
    stream.append(len(stream) % MOD)              # length tribble
    while len(stream) % RATE_LANES:
        stream.append(0)
    state = [0] * STATE_LANES
    for off in range(0, len(stream), RATE_LANES):
        block = stream[off:off + RATE_LANES]
        for i in range(RATE_LANES):
            state[i] = (state[i] + block[i]) % MOD
        state = permute(state)
    return tuple(state[:DIGEST_LANES])


def digest_trits(words) -> str:
    """Human/debug form: the 54-trit MMID as a balanced-ternary string
    (characters -,0,+ per trit, 6 per tribble, MSB first)."""
    out = []
    for lane in digest(words):
        trits = []
        for _ in range(6):
            r = lane % 3
            trits.append({0: '0', 1: '+', 2: '-'}[r])
            lane = (lane - (r if r < 2 else -1)) // 3
        out.append(''.join(reversed(trits)))
    return ' '.join(out)
