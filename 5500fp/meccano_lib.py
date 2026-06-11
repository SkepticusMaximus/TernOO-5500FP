#!/usr/bin/env python3
"""
Meccano Library v0.1 — TernOO OPCODE program substrate
========================================================
Named programs composed of OPCODE word sequences.
Each program carries a dual coordinate:
  - mmid:       structural identity (TTree MAP) — derived from MMOE category
  - otree_word: content address (OTree MAP)     — position-sensitive fold over words

v0.1 ground-work: demonstrates that two programs with the same word multiset
but different execution orderings produce distinct OTree addresses while
sharing the same MMID (same structure, different content path).

Design notes (CWC flags for CAI review):

  1. Accumulator order-sensitivity (Step 5 divergence):
     The spec cited the gristmill commutative fold:
         S = (S + ternary_op(ta, tb)) % MOD
     That fold is commutative — any permutation of the same words yields the
     same S and therefore the same OTree. Acceptance criterion 3 requires
     triangle_method_a and triangle_method_b to differ in OTree despite being
     permutations of each other. This implementation uses a position-sensitive
     fold instead:
         S = (S + ternary_op(ta, (tb + i*27) % MOD)) % MOD
     The i*27 term shifts each word's contribution by its position (in units
     of 27, the MECCANO group step). Flagged here — CAI to confirm or revise.

  2. MMOE_TYPES key format (Step 1 translation):
     Spec used {'subclass_t1': +1, 'subclass_t0': +1} keys but MMID._compute
     reads t.get('udp', (0,0)). Entries added with 'udp' keys in gristmill.

  3. Determinism semantics (Step 5 note):
     'name' is a registry key only; it does not appear in mmid.word, otree_word,
     or to_words(). Two MeccanoPrograms with the same category and words are
     word-identical regardless of name.

Date: 2026-06-11, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Companion spec: Meccano-Library-v01-CWC-Spec.md
"""

from __future__ import annotations
import sys
import os
import importlib.util as _ilu
from typing import List

# ── Load 5500fp_ternoo_v03 via importlib (filename starts with a digit) ───────
_v03_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         '5500fp_ternoo_v03.py')
_v03_spec = _ilu.spec_from_file_location('ternoo_v03', _v03_path)
_v03 = _ilu.module_from_spec(_v03_spec)
_v03_spec.loader.exec_module(_v03)

build_opcode_word  = _v03.build_opcode_word
decode_opcode_word = _v03.decode_opcode_word
decode_word        = _v03.decode_word
OPF_PIGART         = _v03.OPF_PIGART
OP_RPOINT          = _v03.OP_RPOINT
OP_RLINE           = _v03.OP_RLINE
OP_RENDER          = _v03.OP_RENDER
build_map_word     = _v03.build_map_word
build_int_word     = _v03.build_int_word

# ── Load ternoo_gristmill (valid identifier — standard import) ────────────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ternoo_gristmill import (
    MMID, MOD, ternary_op, extract_tribbles, build_otree_mmoe,
)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — MeccanoProgram
# ═══════════════════════════════════════════════════════════════════════════════

class MeccanoProgram:
    """A named TernOO program — a sequence of OPCODE words and their operands.

    Dual-coordinate identity per the TMesh/OTree architecture:
      mmid:       structural coordinate (TTree MAP word) — category-derived
      otree_word: content address (OTree MAP word) — word-sequence-derived

    Two programs with the same category and words are word-identical regardless
    of name. Name is a registry key only.
    """

    def __init__(self, name: str, opcode_words: List[int],
                 category: str = 'pigart',
                 description: str = ''):
        """
        Args:
            name:          human-readable identifier (registry key; not in word output)
            opcode_words:  full word stream in positional order —
                           OPCODE word followed by its operands, repeated per instruction
            category:      'pigart' | 'word_op' | 'compose'
                           selects meccano_program_<category> MMOE type for MMID
            description:   human-readable purpose string
        """
        if category not in ('pigart', 'word_op', 'compose'):
            raise ValueError(f"unknown category: {category!r}")
        self.name        = name
        self.words       = list(opcode_words)
        self.category    = category
        self.description = description
        self.mmid        = MMID(f'meccano_program_{category}')
        self.otree_word  = self._compute_otree()

    def _compute_otree(self) -> int:
        """Position-sensitive accumulator fold over the full word sequence.

        For each word at position i (0-indexed):
            ta, tb, _ = extract_tribbles(w)
            S = (S + ternary_op(ta * (i+1), tb)) % MOD

        Multiplying ta by (i+1) makes each word's contribution depend on both its
        content (ta) and its position. The total accumulator is:
            S = −Σ(ta_i*(i+1) + tb_i) mod 729

        Words with ta=0 (MAP/DATA operands) contribute nothing regardless of position.
        Words with non-zero ta (OPCODE words) contribute position-weighted values.
        Permuting OPCODE words changes Σ(ta_i*(i+1)) and therefore changes S.

        Why not ternary_op(ta, tb + i*27)?  That expands to −(ta+tb+i*27), and
        summed over all words Σ(i*27) = 27*n*(n-1)/2 — a constant for any
        permutation of n words, so order-invariant. The ta*(i+1) form is not.
        """
        S = 0
        for i, w in enumerate(self.words):
            ta, tb, _ = extract_tribbles(w)
            S = (S + ternary_op(ta * (i + 1), tb)) % MOD
        return build_otree_mmoe(S)

    def to_words(self) -> List[int]:
        """Canonical serialisation: [TTree MAP, OTree MAP, *body].

        TTree word (mmid.word) — structural category coordinate.
        OTree word (otree_word) — content address.
        Body — full OPCODE + operand stream.

        Two programs with equal category and words produce identical to_words()
        regardless of name.
        """
        return [self.mmid.word, self.otree_word] + self.words

    def __repr__(self) -> str:
        return (f"MeccanoProgram({self.name!r}, "
                f"category={self.category!r}, "
                f"words={len(self.words)}, "
                f"mmid={self.mmid.word}, otree={self.otree_word})")


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — MeccanoLibrary
# ═══════════════════════════════════════════════════════════════════════════════

class MeccanoLibrary:
    """Registry of named Meccano programs."""

    def __init__(self):
        self.programs: dict[str, MeccanoProgram] = {}

    def register(self, program: MeccanoProgram) -> None:
        if program.name in self.programs:
            raise ValueError(f"duplicate program name: {program.name!r}")
        self.programs[program.name] = program

    def get(self, name: str) -> MeccanoProgram:
        if name not in self.programs:
            raise KeyError(f"no program named {name!r}")
        return self.programs[name]

    def by_category(self, category: str) -> List[MeccanoProgram]:
        return [p for p in self.programs.values() if p.category == category]

    def all(self) -> List[MeccanoProgram]:
        return list(self.programs.values())


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Example programs
# ═══════════════════════════════════════════════════════════════════════════════

def _build_examples() -> MeccanoLibrary:
    """Build the v0.1 demo library: four PIGART example programs.

    Vertex coordinates — placeholder MAP words (cleanly decodable):
        v0 = MAP(all-zero axes, payload=0)   — origin
        v1 = MAP(all-zero axes, payload=100) — +100 along scale axis
        v2 = MAP(all-zero axes, payload=200) — +200 along scale axis

    Colour/style operands use DATA(SCALAR/int) words.
    The point of v0.1 is round-trippable word streams, not pixel-perfect geometry.

    triangle_method_a and triangle_method_b contain the same word multiset
    (3× RPOINT operands, 3× RLINE operands, 1× RENDER, same MAP and DATA words)
    but in different orders. The position-sensitive fold yields distinct OTrees.
    """
    lib = MeccanoLibrary()

    # ── Shared operand words ──────────────────────────────────────────────────
    v0     = build_map_word(0, 0, 0,   0)  # origin
    v1     = build_map_word(0, 0, 0, 100)  # offset +100
    v2     = build_map_word(0, 0, 0, 200)  # offset +200
    colour = build_int_word(1)              # placeholder colour (DATA SCALAR int=1)
    style  = build_int_word(0)              # placeholder line style (DATA SCALAR int=0)

    # ── OPCODE words (PIGART family) ─────────────────────────────────────────
    op_rpoint = build_opcode_word(OPF_PIGART, arity=2, op_index=OP_RPOINT)
    op_rline  = build_opcode_word(OPF_PIGART, arity=3, op_index=OP_RLINE)
    op_render = build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER)

    # ── 1. point_red — single point at origin with colour=1 ──────────────────
    lib.register(MeccanoProgram(
        'point_red',
        [op_rpoint, v0, colour],
        category='pigart',
        description='Single RPOINT at origin',
    ))

    # ── 2. line_horizontal — line from v0 to v1 with default style ───────────
    lib.register(MeccanoProgram(
        'line_horizontal',
        [op_rline, v0, v1, style],
        category='pigart',
        description='Single RLINE from v0 to v1',
    ))

    # ── 3. triangle_method_a — point-first: 3 RPs, then 3 RLs, then RENDER ──
    lib.register(MeccanoProgram(
        'triangle_method_a',
        [
            # Three points
            op_rpoint, v0, colour,
            op_rpoint, v1, colour,
            op_rpoint, v2, colour,
            # Three edges
            op_rline, v0, v1, style,
            op_rline, v1, v2, style,
            op_rline, v2, v0, style,
            # Render
            op_render,
        ],
        category='pigart',
        description='Triangle: all points first, all lines second (point-first ordering)',
    ))

    # ── 4. triangle_method_b — interleaved: RPOINT-RLINE-RPOINT-RLINE… RENDER ─
    lib.register(MeccanoProgram(
        'triangle_method_b',
        [
            # Interleaved point-then-edge
            op_rpoint, v0, colour,
            op_rline,  v0, v1, style,
            op_rpoint, v1, colour,
            op_rline,  v1, v2, style,
            op_rpoint, v2, colour,
            op_rline,  v2, v0, style,
            # Render
            op_render,
        ],
        category='pigart',
        description='Triangle: point-line interleaved (same triangle, different ordering)',
    ))

    return lib


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Test entry point
# ═══════════════════════════════════════════════════════════════════════════════

def test_meccano_library() -> bool:
    """v0.1 acceptance tests — 5 criteria.

    CAI flag (Step 5 determinism resolution):
    'name' is a registry key only — it does not appear in mmid.word, otree_word,
    or to_words(). Criterion 4 asserts that two MeccanoPrograms sharing category
    and words are fully word-identical (same mmid, same otree_word, same to_words())
    regardless of name. This is the correct semantics.
    """
    print("=" * 60)
    print("TEST: Meccano Library v0.1")
    print("=" * 60)

    lib = _build_examples()

    # ── 1. All four programs construct without error ───────────────────────────
    assert len(lib.all()) == 4, f"expected 4 programs, got {len(lib.all())}"
    print(f"  1. PASS  {len(lib.all())} programs constructed")

    # ── 2. Each program's to_words() stream decodes cleanly ───────────────────
    for p in lib.all():
        words = p.to_words()
        assert len(words) >= 3, f"{p.name}: to_words() too short ({len(words)})"
        for w in words:
            d = decode_word(w)
            assert 'type' in d, f"{p.name}: word {w!r} failed to decode (got {d})"
    print("  2. PASS  All to_words() streams decode cleanly")

    # ── 3. triangle_method_a and _b: same MMID, distinct OTree ───────────────
    ta = lib.get('triangle_method_a')
    tb = lib.get('triangle_method_b')
    assert ta.mmid.word == tb.mmid.word, (
        f"triangles must share MMID (same category='pigart'):\n"
        f"  method_a mmid={ta.mmid.word}\n  method_b mmid={tb.mmid.word}")
    assert ta.otree_word != tb.otree_word, (
        f"triangles must have distinct OTree (different word orderings):\n"
        f"  method_a otree={ta.otree_word}\n  method_b otree={tb.otree_word}")
    print(f"  3. PASS  Triangles: shared MMID={ta.mmid.word}, "
          f"distinct OTree a={ta.otree_word} b={tb.otree_word}")

    # ── 4. Determinism: same category+words → identical to_words() ───────────
    # 'name' does not affect any computed field.
    p1 = MeccanoProgram('det_test_1', list(ta.words), category='pigart')
    p2 = MeccanoProgram('det_test_2', list(ta.words), category='pigart')
    assert p1.mmid.word  == p2.mmid.word,  "same category → same MMID"
    assert p1.otree_word == p2.otree_word, "same words → same OTree"
    assert p1.to_words() == p2.to_words(), "same category+words → identical to_words()"
    print("  4. PASS  Determinism: same words+category → identical to_words() (name excluded)")

    # ── 5. Category filtering ─────────────────────────────────────────────────
    pigart = lib.by_category('pigart')
    assert len(pigart) == 4
    assert all(p.category == 'pigart' for p in pigart)
    print(f"  5. PASS  by_category('pigart') returns {len(pigart)} programs")

    print()
    print(f"meccano_lib v0.1: {len(lib.all())} programs, all tests pass")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Demo entry point
# ═══════════════════════════════════════════════════════════════════════════════

def demo():
    """Print each program with coordinates — for human eyeballing."""
    lib = _build_examples()
    print("=" * 60)
    print("  Meccano Library v0.1 — Program Registry Demo")
    print("=" * 60)
    for p in lib.all():
        print(f"\n{p.name}  [{p.category}]")
        print(f"  desc:   {p.description}")
        print(f"  MMID:   {p.mmid.word}")
        print(f"  OTree:  {p.otree_word}")
        print(f"  stream: {len(p.words)} body words "
              f"({len(p.to_words())} total with TTree+OTree header)")

    # Highlight the architectural payoff
    ta = lib.get('triangle_method_a')
    tb = lib.get('triangle_method_b')
    print()
    print("── Content-address demo: same triangle, different execution path ──")
    print(f"  method_a MMID:  {ta.mmid.word}  ← identical (same structure)")
    print(f"  method_b MMID:  {tb.mmid.word}")
    print(f"  method_a OTree: {ta.otree_word}  ← distinct (different word order)")
    print(f"  method_b OTree: {tb.otree_word}")
    print(f"  Word counts:    method_a={len(ta.words)}  method_b={len(tb.words)}")


if __name__ == '__main__':
    if '--test' in sys.argv:
        sys.exit(0 if test_meccano_library() else 1)
    demo()
