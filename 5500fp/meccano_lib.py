#!/usr/bin/env python3
"""
Meccano Library v0.2 — TernOO OPCODE program substrate + widget primitives
===========================================================================
Named programs composed of OPCODE word sequences.
Each program carries a dual coordinate:
  - mmid:       structural identity (TTree MAP) — derived from MMOE category
  - otree_word: content address (OTree MAP)     — position-sensitive fold over words

v0.1 ground-work: demonstrates that two programs with the same word multiset
but different execution orderings produce distinct OTree addresses while
sharing the same MMID (same structure, different content path).

v0.2 adds four DOSShell-vintage widget programs and a CLI render path via
pigart_ascii_renderer. When you run `python3 meccano_lib.py --render window_basic`
you get a text-art window on stdout — first rendered output from the Meccano substrate.

Design notes (CWC flags for CAI review):

  1. Accumulator order-sensitivity (v0.1 flag, resolved):
     Used position-sensitive fold: S = (S + ternary_op(ta*(i+1), tb)) % MOD.
     The ta*(i+1) weighting makes each OPCODE word's contribution depend on
     both its content (ta) and its position, so permutations of the same
     word multiset produce distinct OTree addresses. CAI confirmed in v0.1.

  2. MMOE_TYPES key format (v0.1 flag, resolved):
     Spec used {'subclass_t1': +1, 'subclass_t0': +1} keys; translated to
     'udp' tuples in gristmill since MMID._compute reads t.get('udp', (0,0)).

  3. Determinism semantics (v0.1 flag, resolved):
     'name' is a registry key only — does not enter mmid.word, otree_word,
     or to_words(). Two programs with the same category and words are
     word-identical regardless of name.

  4. MAP word for 2D position (v0.2, CAI flag):
     Uses ON_PLANE mode (axis_yz=1, axis_xz=1, axis_xy=0).
     payload = from_trits(to_trits(y, 9) + to_trits(x, 9))
     decode_map_word returns coords={'X': col, 'Y': row}.
     Helper: _build_xy_map(x, y).

  5. DATA word for size (v0.2, CAI flag):
     Uses DATA/SCALAR int with two-tribble packing:
       T11-T6 (tb) = width, T5-T0 (tc) = height.
     payload = from_trits(to_trits(h, 6) + to_trits(w, 6) + [0]*6)
     Renderer extracts via get_field. No new DATA subtype introduced.
     Helper: _build_size_word(width, height).

  6. DATA word for label (v0.2, CAI flag):
     Uses build_int_word(label_id). Renderer does decode_word → 'value' →
     LABEL_TABLE lookup. No conflict with existing SCALAR int semantics.

Date: 2026-06-11, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Companion specs: Meccano-Library-v01-CWC-Spec.md, Meccano-Library-v02-CWC-Spec.md
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
OP_RNODE           = _v03.OP_RNODE
OP_RENDER          = _v03.OP_RENDER
build_map_word     = _v03.build_map_word
build_int_word     = _v03.build_int_word
from_trits         = _v03.from_trits
to_trits           = _v03.to_trits

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
# SECTION 3 — Operand-building helpers (v0.2)
# ═══════════════════════════════════════════════════════════════════════════════

def _build_xy_map(x: int, y: int) -> int:
    """MAP word encoding a 2D ASCII canvas position (x=column, y=row).

    Uses ON_PLANE mode (axis_yz=1, axis_xz=1, axis_xy=0):
      payload packs x in high 9 trits (T17-T9), y in low 9 trits (T8-T0).
      decode_map_word returns mode='ON_PLANE', coords={'X': col, 'Y': row}.

    CAI flag (v0.2): ON_PLANE with xy=0 is the only existing mode that
    exposes both X and Y from a single MAP word. No new convention invented.
    """
    payload = from_trits(to_trits(y, 9) + to_trits(x, 9))
    return build_map_word(1, 1, 0, payload)


def _build_size_word(width: int, height: int) -> int:
    """DATA/SCALAR int word encoding (width, height) for RNODE operands.

    Packs two values into the payload as adjacent tribbles:
      T11-T6 (tb tribble) = width
      T5-T0  (tc tribble) = height
      T17-T12 (ta)        = 0 (unused)

    Renderer extracts via:
      width  = get_field(w, 6, 6)
      height = get_field(w, 0, 6)

    Both width and height must fit in 6 balanced trits (max ±364).
    At 60×20 default canvas they are always within range.

    CAI flag (v0.2): uses existing build_int_word with manual packing.
    No new DATA subtype introduced.
    """
    payload = from_trits(to_trits(height, 6) + to_trits(width, 6) + [0] * 6)
    return build_int_word(payload)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — Example programs
# ═══════════════════════════════════════════════════════════════════════════════

def _build_examples() -> MeccanoLibrary:
    """Build the example library: 4 v0.1 geometry programs + 4 v0.2 widget programs.

    v0.1 programs (geometry substrate demo):
        v0/v1/v2 are ORIGIN-mode MAP words — cleanly decodable but no x,y.
        triangle_method_a and _b share the same word multiset in different
        orders; position-sensitive fold yields distinct OTree addresses.

    v0.2 programs (widget primitives — renderable by pigart_ascii_renderer):
        Positions use ON_PLANE MAP words built by _build_xy_map(x, y).
        Sizes use packed DATA words built by _build_size_word(w, h).
        Labels use build_int_word(label_id), looked up in LABEL_TABLE.
        Canvas units = character columns/rows (no scaling).
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

    # ── v0.2 widget programs ─────────────────────────────────────────────────
    # Shared OPCODE words for widget programs
    op_rnode_2 = build_opcode_word(OPF_PIGART, arity=2, op_index=OP_RNODE)
    op_rnode_3 = build_opcode_word(OPF_PIGART, arity=3, op_index=OP_RNODE)

    # ── 5. box_rectangle — plain rectangle outline ───────────────────────────
    lib.register(MeccanoProgram(
        'box_rectangle',
        [
            op_rnode_2,
            _build_xy_map(4, 3),          # top-left at col 4, row 3
            _build_size_word(24, 8),       # 24 wide × 8 tall
            op_render,
        ],
        category='pigart',
        description='Plain rectangle outline (simplest widget)',
    ))

    # ── 6. labeled_box — rectangle with centred label ────────────────────────
    lib.register(MeccanoProgram(
        'labeled_box',
        [
            op_rnode_3,
            _build_xy_map(8, 5),           # top-left at col 8, row 5
            _build_size_word(22, 6),        # 22 wide × 6 tall
            build_int_word(6),              # label_id=6 → 'Hello'
            op_render,
        ],
        category='pigart',
        description='Rectangle with centred "Hello" label inside',
    ))

    # ── 7. window_basic — frame + title bar + content area ───────────────────
    lib.register(MeccanoProgram(
        'window_basic',
        [
            # Outer frame: 50 wide × 16 tall at (4, 2)
            op_rnode_2,
            _build_xy_map(4, 2),
            _build_size_word(50, 16),
            # Title bar: 48 wide × 3 tall at (5, 3), labelled 'Title'
            op_rnode_3,
            _build_xy_map(5, 3),
            _build_size_word(48, 3),
            build_int_word(1),              # label_id=1 → 'Title'
            # Content area: 48 wide × 10 tall at (5, 6)
            op_rnode_2,
            _build_xy_map(5, 6),
            _build_size_word(48, 10),
            op_render,
        ],
        category='pigart',
        description='Window: outer frame + labelled title bar + content area',
    ))

    # ── 8. button_simple — small labelled button ─────────────────────────────
    lib.register(MeccanoProgram(
        'button_simple',
        [
            op_rnode_3,
            _build_xy_map(24, 15),         # col 24, row 15
            _build_size_word(10, 3),        # 10 wide × 3 tall
            build_int_word(2),              # label_id=2 → 'OK'
            op_render,
        ],
        category='pigart',
        description='Small button with centred "OK" label',
    ))

    return lib


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Test entry point
# ═══════════════════════════════════════════════════════════════════════════════

def test_meccano_library() -> bool:
    """v0.2 acceptance tests — 8 criteria (v0.1 criteria 1–5, v0.2 criteria 6–8).

    CAI flag (Step 5 determinism resolution, v0.1):
    'name' is a registry key only — it does not appear in mmid.word, otree_word,
    or to_words(). Criterion 4 asserts that two MeccanoPrograms sharing category
    and words are fully word-identical (same mmid, same otree_word, same to_words())
    regardless of name. This is the correct semantics.
    """
    print("=" * 60)
    print("TEST: Meccano Library v0.2")
    print("=" * 60)

    lib = _build_examples()

    # ── 1. All eight programs construct without error ──────────────────────────
    assert len(lib.all()) == 8, f"expected 8 programs, got {len(lib.all())}"
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
    assert len(pigart) == 8
    assert all(p.category == 'pigart' for p in pigart)
    print(f"  5. PASS  by_category('pigart') returns {len(pigart)} programs")

    # ── 6. All four widget programs are present and construct cleanly ──────────
    widget_names = ('box_rectangle', 'labeled_box', 'window_basic', 'button_simple')
    for name in widget_names:
        assert name in lib.programs, f"missing widget program: {name!r}"
        p = lib.get(name)
        # to_words() must be decodable
        for w in p.to_words():
            d = decode_word(w)
            assert 'type' in d, f"{name}: word {w!r} failed decode"
    print(f"  6. PASS  All 4 widget programs present and decode cleanly")

    # ── 7. Each widget program renders without error and produces rectangle chars
    from pigart_ascii_renderer import render as _render
    for name in widget_names:
        output = _render(lib.get(name))
        assert isinstance(output, str) and len(output) > 0, \
            f"{name}: render() returned empty output"
        assert any(c in output for c in '+-|'), \
            f"{name}: rendered output contains no rectangle characters: {output!r}"
    print(f"  7. PASS  All 4 widget programs render without error (rectangle chars present)")

    # ── 8. window_basic renders at least one label from LABEL_TABLE ───────────
    from pigart_ascii_renderer import LABEL_TABLE as _LABEL_TABLE
    window_output = _render(lib.get('window_basic'))
    assert any(lbl in window_output for lbl in _LABEL_TABLE.values() if lbl), \
        "window_basic: no LABEL_TABLE entry found in rendered output"
    print(f"  8. PASS  window_basic renders at least one label")

    print()
    print(f"meccano_lib v0.2: {len(lib.all())} programs, all tests pass")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Demo entry point
# ═══════════════════════════════════════════════════════════════════════════════

def demo():
    """Print each program with coordinates — for human eyeballing."""
    lib = _build_examples()
    print("=" * 60)
    print("  Meccano Library v0.2 — Program Registry Demo")
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
    if '--render' in sys.argv:
        _idx = sys.argv.index('--render')
        if _idx + 1 >= len(sys.argv):
            print("usage: meccano_lib.py --render <program_name>", file=sys.stderr)
            sys.exit(2)
        from pigart_ascii_renderer import render as _render
        _lib  = _build_examples()
        _name = sys.argv[_idx + 1]
        if _name not in _lib.programs:
            print(f"unknown program: {_name!r}", file=sys.stderr)
            print(f"available: {', '.join(sorted(_lib.programs))}", file=sys.stderr)
            sys.exit(2)
        print(_render(_lib.get(_name)))
        sys.exit(0)
    demo()
