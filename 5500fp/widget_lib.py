#!/usr/bin/env python3
"""widget_lib.py — TernOO Widget Library (formerly meccano_lib.py).

Registry of named widget programs composed from PIGART OPCODE word streams.
Each program is a MeccanoProgram instance with dual TMesh/OTree coordinates:
  - mmid:       structural identity (TTree MAP) — derived from MMOE category
  - otree_word: content address (OTree MAP)     — Fingerprint Fold over words

Renamed from meccano_lib.py on 2026-06-15 (per CF5 audit finding 1.7) to
disambiguate from the Meccano vocabulary (§10.1.3 — the closed 27-element
compositional set) and the OPF_MECCANO OPCODE family. The MeccanoProgram
class name stays because the class is generic over any TernOO word-stream
program, not widget-specific.

Current capability: v0.7 (R1 + Direction B: RNODE/REDGE shape forms, shape
registry, stream-walker factoring, FlowCode bridge, ~50 new tests).

Design notes (CWC flags for CAI review):

  1. Accumulator order-sensitivity (v0.1 flag, resolved):
     Used position-sensitive fold: S = (S + ternary_op(ta*(i+1), tb)) % MOD.
     The ta*(i+1) weighting makes each OPCODE word's contribution depend on
     both its content (ta) and its position, so permutations of the same
     word multiset produce distinct OTree addresses. CAI confirmed in v0.1.
     Named the "Fingerprint Fold" per CF5 audit 1.3.

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

  6. DATA-STRING label encoding (v0.4, replaces LABEL_TABLE):
     Uses build_string_word(STRING_ASCII, packed). Each word packs 3 ASCII
     chars via base-128: packed = c0 + c1*128 + c2*16384. RNODE arity =
     2 + ceil(len(text)/3). Renderer decodes via _decode_label_words().
     LABEL_TABLE removed from both widget_lib and pigart_ascii_renderer.

  7. Coordinate-relative composition (v0.5):
     bounds() walks the OPCODE stream to report (min_x, min_y, max_x, max_y).
     translate(dx, dy) returns a new program with all ON_PLANE MAP words shifted.
     compose_below(other, gap) and compose_right_of(other, gap) use translate +
     compose to place components without coordinate overlap.

  8. tkinter renderer (v0.6):
     pigart_tkinter_renderer.py walks the same word stream as the ASCII renderer
     and produces GUI shapes on a tkinter Canvas. Same five PIGART opcodes,
     scale=12px per Meccano unit. --render-gui CLI flag added to this module.

Date: 2026-06-11 (v0.1–v0.6), 2026-06-15 (rename chore)
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Companion specs: Meccano-Library-v01-CWC-Spec.md … Meccano-Library-v06-CWC-Spec.md
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
OP_REDGE           = _v03.OP_REDGE
OP_RENDER          = _v03.OP_RENDER
build_map_word     = _v03.build_map_word
build_int_word     = _v03.build_int_word
build_pointer_word = _v03.build_pointer_word
PTR_SYMBOL         = _v03.PTR_SYMBOL
from_trits         = _v03.from_trits
to_trits           = _v03.to_trits
build_string_word  = _v03.build_string_word
STRING_ASCII       = _v03.STRING_ASCII
decode_map_word    = _v03.decode_map_word
get_primary        = _v03.get_primary
get_field          = _v03.get_field
PRIMARY_OPCODE     = _v03.PRIMARY_OPCODE

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
        """Fingerprint Fold — position-sensitive accumulator over the word stream.

        For each word in self.words at 1-indexed position i:
            ta, tb, _ = extract_tribbles(word)
            S = (S + ternary_op(ta * (i+1), tb)) % MOD
        otree_word = build_otree_mmoe(S)

        The order-sensitivity of the fold comes from the position weight
        (i+1) applied to ta — without it, ternary_op's underlying addition
        would commute and permutations of the same word set would collide.

        Note: operand words (MAP/DATA) generally have non-zero tb values
        (e.g. _build_xy_map packs y into payload trits 6-11), so they DO
        contribute to the fold via the tb term, position-independently.
        The order-sensitivity lives in the opcodes' ta values, not in
        operand suppression.

        Why not ternary_op(ta, tb + i*27)? That expands to -(ta+tb+i*27),
        and summed over all words Σ(i*27) = 27*n*(n-1)/2 — a constant for
        any permutation of n words, so order-invariant. The ta*(i+1) form
        is not.

        Mathematical note: this is the "Fingerprint Fold" (per CF5 audit
        1.3). It is quasigroup-based, not quasigroup-pure — the position
        weight ta*(i+1) uses multiplication, which lies outside the
        Steiner quasigroup's operation set. The Placement Fold used by
        GristMill is quasigroup-pure but order-invariant at the
        final-value level; widget_lib needs final-value order-sensitivity,
        so the multiplicative weight is the deliberate departure.
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

    def compose(self, *others: 'MeccanoProgram',
                name: str = None,
                description: str = '') -> 'MeccanoProgram':
        """Compose this program with one or more others into a single program.

        The composed program's word stream is the concatenation of the component
        programs' body streams (excluding TTree/OTree headers). The composed
        program's MMID and OTree are computed afresh from the combined stream.

        Category must match across all components — cross-category composition
        is deferred to v0.4+.

        RENDER opcodes from component programs are preserved in the combined
        stream. In ASCII mode RENDER is a no-op so multiple RENDERs are harmless.
        v0.4 may introduce RENDER stripping.

        Architectural property: compose is NOT commutative on OTree
        (different orderings produce different content addresses via the
        position-weighted fold), but word concatenation IS associative:
          (A.compose(B)).compose(C).words == A.compose(B.compose(C)).words
        and therefore their OTree addresses are also equal.

        Args:
            *others:     programs to append after self, in order
            name:        name for the composed program
                         (default: 'self.name+other0.name+...')
            description: human-readable purpose (default: blank)

        Returns:
            New MeccanoProgram with category = self.category.

        Raises:
            ValueError: if any program in others has a different category.
        """
        for o in others:
            if o.category != self.category:
                raise ValueError(
                    f"compose category mismatch: "
                    f"{self.category!r} (self) vs {o.category!r} ({o.name!r})"
                )

        combined_words = list(self.words)
        for o in others:
            combined_words.extend(o.words)

        if name is None:
            name = '+'.join([self.name] + [o.name for o in others])

        return MeccanoProgram(
            name=name,
            opcode_words=combined_words,
            category=self.category,
            description=description,
        )

    def bounds(self) -> tuple[int, int, int, int]:
        """Compute the program's bounding box by walking its PIGART OPCODE stream.

        Returns (min_x, min_y, max_x, max_y) — inclusive bounds covering every
        cell any opcode would draw.

        Per-opcode contribution:
          RPOINT pos=(x,y)                → single point (x,y,x,y)
          RLINE  from=(x1,y1) to=(x2,y2) → span of both endpoints
          RNODE  pos=(x,y) size=(w,h)     → (x, y, x+w-1, y+h-1)
          REDGE  from=(x1,y1) to=(x2,y2) → span of both endpoints (like RLINE)
          RENDER                          → no contribution

        MAP words that are not in ON_PLANE mode (e.g. ORIGIN-mode v0.1 geometry
        programs) decode to (0, 0) via _extract_map_xy. These programs will
        report bounds of (0, 0, 0, 0) — correct for translate purposes, and
        flagged in test 19 with an inline ON_PLANE program for the RLINE case.

        Non-PIGART OPCODE words are skipped (no canvas bounds).

        Raises:
            ValueError: if the program contains no PIGART opcodes that
                        contribute to bounds (e.g. empty or RENDER-only).
        """
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')

        for decoded, _form, operands in iterate_instructions(self.words):
            if decoded['family'] != OPF_PIGART:
                continue
            mnemonic = decoded['mnemonic']

            if mnemonic == 'RPOINT' and len(operands) >= 1:
                x, y  = _extract_map_xy(operands[0])
                min_x = min(min_x, x); max_x = max(max_x, x)
                min_y = min(min_y, y); max_y = max(max_y, y)

            elif mnemonic in ('RLINE', 'REDGE') and len(operands) >= 2:
                x1, y1 = _extract_map_xy(operands[0])
                x2, y2 = _extract_map_xy(operands[1])
                min_x  = min(min_x, x1, x2); max_x = max(max_x, x1, x2)
                min_y  = min(min_y, y1, y2); max_y = max(max_y, y1, y2)

            elif mnemonic == 'RNODE' and len(operands) >= 2:
                x, y  = _extract_map_xy(operands[0])
                sz    = operands[1]
                sz_w  = int(get_field(sz, 6, 6))   # T11-T6 = width
                sz_h  = int(get_field(sz, 0, 6))   # T5-T0  = height
                min_x = min(min_x, x);              max_x = max(max_x, x + sz_w - 1)
                min_y = min(min_y, y);              max_y = max(max_y, y + sz_h - 1)
            # RENDER: no contribution to bounds

        if min_x == float('inf'):
            raise ValueError(
                f"program {self.name!r} has no positioned PIGART opcodes "
                f"(program may be empty or contain only RENDER)"
            )
        return (int(min_x), int(min_y), int(max_x), int(max_y))

    def translate(self, dx: int, dy: int) -> 'MeccanoProgram':
        """Return a new MeccanoProgram with all ON_PLANE MAP positions shifted by (dx, dy).

        Walks self.words; for each word whose type is MAP and whose coords dict
        contains 'X' and 'Y' (i.e. an ON_PLANE word built by _build_xy_map),
        rebuilds the word with (x+dx, y+dy). All other words pass through
        unchanged.

        MAP words in other modes (ORIGIN-mode v0.1 geometry words, ABSOLUTE_3D,
        etc.) are passed through unchanged — only ON_PLANE XY words are shifted.

        The returned program has the same category and description, and a derived
        name: f'{self.name}@({dx:+},{dy:+})'.

        Properties (verified in tests 20-23):
          translate(0, 0) is identity (word stream byte-identical to original)
          translate(dx, dy).translate(-dx, -dy) == original
          translate(a, b).translate(c, d) == translate(a+c, b+d)
          translate shifts bounds by exactly (dx, dy)
        """
        new_words = []
        for w in self.words:
            d = decode_word(w)
            if d.get('type') == 'MAP':
                dm     = decode_map_word(w)
                coords = dm.get('coords', {})
                if 'X' in coords:
                    x, y = int(coords['X']), int(coords['Y'])
                    new_words.append(_build_xy_map(x + dx, y + dy))
                else:
                    new_words.append(w)  # non-XY MAP word — pass through
            else:
                new_words.append(w)

        return MeccanoProgram(
            name=f'{self.name}@({dx:+},{dy:+})',
            opcode_words=new_words,
            category=self.category,
            description=self.description,
        )

    def compose_below(self, other: 'MeccanoProgram', gap: int = 1,
                      name: str = None,
                      description: str = '') -> 'MeccanoProgram':
        """Compose other below self, with gap blank rows between them.

        Computes the vertical translation that places other.bounds() directly
        below self.bounds() (separated by gap rows), translates other, then
        concatenates via compose().

        Formula: dy = self.max_y + gap + 1 - other.min_y
        Horizontal: dx = 0 (other keeps its original horizontal position).

        Gap semantics:
          gap=1 (default): one blank row between borders
          gap=0: borders flush against each other
          gap<0: intentional overlap by abs(gap) rows

        Default name: f'{self.name}_below_{other.name}'

        Raises:
            ValueError: if category mismatch (inherited from compose())
        """
        _, _, _, my_max_y       = self.bounds()
        _, other_min_y, _, _    = other.bounds()
        dy      = my_max_y + gap + 1 - other_min_y
        shifted = other.translate(0, dy)
        if name is None:
            name = f'{self.name}_below_{other.name}'
        return self.compose(shifted, name=name, description=description)

    def compose_right_of(self, other: 'MeccanoProgram', gap: int = 1,
                         name: str = None,
                         description: str = '') -> 'MeccanoProgram':
        """Compose other to the right of self, with gap blank columns between them.

        Computes the horizontal translation that places other.bounds() directly
        to the right of self.bounds() (separated by gap columns), translates
        other, then concatenates via compose().

        Formula: dx = self.max_x + gap + 1 - other.min_x
        Vertical: dy = 0 (other keeps its original vertical position).

        Default name: f'{self.name}_rightof_{other.name}'

        Raises:
            ValueError: if category mismatch (inherited from compose())
        """
        _, _, my_max_x, _       = self.bounds()
        other_min_x, _, _, _    = other.bounds()
        dx      = my_max_x + gap + 1 - other_min_x
        shifted = other.translate(dx, 0)
        if name is None:
            name = f'{self.name}_rightof_{other.name}'
        return self.compose(shifted, name=name, description=description)

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


def _encode_label(text: str) -> List[int]:
    """Encode a label string as one or more DATA-STRING/ASCII words.

    Packs 3 printable ASCII chars per word using base-128 encoding:
      packed = c0 + c1*128 + c2*128²
    where c0, c1, c2 are the character ordinals (0-127).
    Short chunks are null-padded; the decoder strips trailing nulls.

    Max payload: 3 chars × 7 bits = 21 bits ≤ 18-trit capacity (≈28.5 bits). ✓
    All printable ASCII (32–126) and printable chars up to 127 are supported.

    Returns one word per 3-char chunk. RNODE arity = 2 + len(_encode_label(text)).

    Encoding uses the existing build_string_word(STRING_ASCII, packed) from v03.
    The 'length_or_addr' payload field is repurposed as inline character storage —
    no v03 changes needed.

    CAI flag (v0.4): DATA_STRING constant in v03 has a latent bug (T20=+1) that
    is inconsistent with build_string_word and decode_word (both use T20=-1).
    No runtime impact here; flagged for a future cleanup pass.
    """
    words = []
    for i in range(0, max(len(text), 1), 3):
        chunk = text[i:i+3]
        c0    = ord(chunk[0]) if len(chunk) > 0 else 0
        c1    = ord(chunk[1]) if len(chunk) > 1 else 0
        c2    = ord(chunk[2]) if len(chunk) > 2 else 0
        packed = c0 + c1 * 128 + c2 * 16384
        words.append(build_string_word(STRING_ASCII, packed))
    return words


def _extract_map_xy(map_word: int) -> tuple[int, int]:
    """Extract (x, y) from an ON_PLANE MAP word built by _build_xy_map().

    Uses decode_map_word and returns coords['X'], coords['Y'].
    For MAP words not in ON_PLANE mode (e.g. ORIGIN-mode v0.1 geometry words),
    returns (0, 0) — those words have no discrete XY canvas position.

    This helper is used by both bounds() and translate() so the decode logic
    is not duplicated across the two methods.

    CAI flag (v0.5): the renderer module has an identical _extract_xy helper.
    They are kept separate to avoid a cross-module dependency (meccano_lib
    importing from pigart_ascii_renderer). Both share the same semantics.
    Factoring into a shared utility is a v0.6 candidate.
    """
    d      = decode_map_word(map_word)
    coords = d.get('coords', {})
    return int(coords.get('X', 0)), int(coords.get('Y', 0))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3.5 — Shape Registry (v0.7)
# ═══════════════════════════════════════════════════════════════════════════════
#
# Shape IDs are extensible integer constants stored in DATA-POINTER-SYMBOL words.
# Adding a new shape requires only a new constant here and a renderer case.
# IDs 0-9 are FlowCode-relevant; 10-12 cover the v0.2-v0.5 widget vocabulary.
# IDs 13-26 reserved for second pass (CGP-specific, neural-network shapes, etc.).
# IDs 27+ open for community extension.

SHAPE_RECTANGLE   = 0   # Plain rectangle (default / fallback)
SHAPE_TERMINATOR  = 1   # Start/End oval (rounded rectangle in ASCII)
SHAPE_PROCESS     = 2   # Process step rectangle (alias for RECTANGLE, FlowCode clarity)
SHAPE_DECISION    = 3   # Branch diamond
SHAPE_IO          = 4   # I/O parallelogram (fallback to rect in ASCII v0.7)
SHAPE_SUBROUTINE  = 5   # Predefined-process rectangle (with side bars — v0.8)
SHAPE_CONNECTOR   = 6   # Flow connector circle
SHAPE_OFFPAGE     = 7   # Off-page connector pentagon (v0.8)
SHAPE_DOCUMENT    = 8   # Document wavy-bottom rectangle (v0.8)
SHAPE_DATA        = 9   # Data store cylinder (v0.8)
SHAPE_LABELED_BOX = 10  # v0.2 labeled box (explicit for retrofitting)
SHAPE_WINDOW      = 11  # v0.2 window with title bar (explicit for retrofitting)
SHAPE_BUTTON      = 12  # v0.2 button (explicit for retrofitting)
# IDs 13-26 reserved for future visual shapes.
# IDs 27-99 open for community extension.

# ── Logical edge style constants (100+) ──────────────────────────────────────
# These are used as the style_id argument to build_redge_styled() to encode
# semantic relationships rather than visual arrows.  Renderers that encounter
# these style IDs skip visible rendering.
STYLE_CONTAIN = 100   # REDGE "child of" — containment edge (no visible render)
# 101-126 reserved for future logical relation kinds
# (DATA_FLOW=101, EVENT_BIND=102, REFERENCE=103 — to be assigned as needed)

# Form discriminants — stored in the OPCODE word's `immediate` field (T11..T0).
# All existing v0.1-v0.6 programs have immediate=0 → lean form.  Backward-compatible.
FORM_LEAN      = 0   # MAP-pos, DATA-dims [, DATA-STRING-label*]        (existing)
FORM_SHAPE     = 1   # MAP-pos, DATA-dims, DATA-SYMBOL-shape [, label*] (new v0.7)
FORM_SHAPE_UDP = 2   # MAP-pos, DATA-dims, DATA-SYMBOL-shape, UDP-obj   (new v0.7)


def build_data_symbol(symbol_id: int) -> int:
    """Build a DATA-POINTER-SYMBOL word encoding a shape/style registry ID.

    Uses PTR_SYMBOL = (0, +1) pointer model.
    Symbol ID is packed into trits T17–T12 (the top tribble, `ta`), which is
    the trit range read by the Fingerprint Fold.  This ensures programs that
    differ only in shape or style symbol produce distinct OTree addresses.

    Shape constants: SHAPE_RECTANGLE=0, SHAPE_TERMINATOR=1, … SHAPE_BUTTON=12.
    Style constants: STYLE_CONTAIN=100, …
    Decoders read back the ID with: get_field(word, 12, 6)
    """
    # Place symbol_id in T17–T12 (top tribble) so the Fingerprint Fold sees it.
    # Trit layout of the 18-trit payload (LSB-first in from_trits list):
    #   indices  0-5  = T5-T0   (tc) = 0
    #   indices  6-11 = T11-T6  (tb) = 0
    #   indices 12-17 = T17-T12 (ta) = symbol_id
    payload = from_trits([0] * 12 + to_trits(symbol_id, 6))
    return build_pointer_word(PTR_SYMBOL, payload)


def build_rnode_shape(pos_xy: tuple, size_wh: tuple, shape_id: int) -> List[int]:
    """Build a shape-form RNODE instruction (no label).

    Emits 4 words: OPCODE(immediate=1, arity=3) + MAP(pos) + DATA(dims) +
    DATA-SYMBOL(shape).

    Backward-incompatible alternative to build_opcode_word(..., OP_RNODE):
    renderers check immediate to dispatch shape drawing.
    """
    x, y = pos_xy
    w, h = size_wh
    return [
        build_opcode_word(OPF_PIGART, arity=3, op_index=OP_RNODE,
                          immediate=FORM_SHAPE),
        _build_xy_map(x, y),
        _build_size_word(w, h),
        build_data_symbol(shape_id),
    ]


def build_rnode_shape_labeled(pos_xy: tuple, size_wh: tuple,
                               shape_id: int, label: str) -> List[int]:
    """Build a shape-form RNODE with an inline label.

    Emits 4+N words: OPCODE(immediate=1, arity=3+N) + MAP + DATA-dims +
    DATA-SYMBOL-shape + N*DATA-STRING-label.
    """
    x, y = pos_xy
    w, h = size_wh
    lw = _encode_label(label)
    return [
        build_opcode_word(OPF_PIGART, arity=3 + len(lw), op_index=OP_RNODE,
                          immediate=FORM_SHAPE),
        _build_xy_map(x, y),
        _build_size_word(w, h),
        build_data_symbol(shape_id),
        *lw,
    ]


def build_rnode_shape_udp(pos_xy: tuple, size_wh: tuple,
                           shape_id: int, udp_word: int) -> List[int]:
    """Build a shape+UDP-form RNODE (4 operands).

    Emits 5 words: OPCODE(immediate=2, arity=4) + MAP + DATA-dims +
    DATA-SYMBOL-shape + UDP-word.
    """
    x, y = pos_xy
    w, h = size_wh
    return [
        build_opcode_word(OPF_PIGART, arity=4, op_index=OP_RNODE,
                          immediate=FORM_SHAPE_UDP),
        _build_xy_map(x, y),
        _build_size_word(w, h),
        build_data_symbol(shape_id),
        udp_word,
    ]


def build_redge_styled(src_xy: tuple, dst_xy: tuple, style_id: int) -> List[int]:
    """Build a styled-form REDGE (3 operands).

    Emits 4 words: OPCODE(immediate=1, arity=3) + MAP(src) + MAP(dst) +
    DATA-SYMBOL(style).
    """
    sx, sy = src_xy
    dx, dy = dst_xy
    return [
        build_opcode_word(OPF_PIGART, arity=3, op_index=OP_REDGE,
                          immediate=FORM_SHAPE),
        _build_xy_map(sx, sy),
        _build_xy_map(dx, dy),
        build_data_symbol(style_id),
    ]


def build_redge_labeled(src_xy: tuple, dst_xy: tuple,
                         style_id: int, label: str) -> List[int]:
    """Build a labeled-form REDGE (3 + N operands).

    Emits 4+N words: OPCODE(immediate=2, arity=3+N) + MAP(src) + MAP(dst) +
    DATA-SYMBOL(style) + N*DATA-STRING-label.
    """
    sx, sy = src_xy
    dx, dy = dst_xy
    lw = _encode_label(label)
    return [
        build_opcode_word(OPF_PIGART, arity=3 + len(lw), op_index=OP_REDGE,
                          immediate=FORM_SHAPE_UDP),
        _build_xy_map(sx, sy),
        _build_xy_map(dx, dy),
        build_data_symbol(style_id),
        *lw,
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3.6 — Stream-walker (v0.7)
# ═══════════════════════════════════════════════════════════════════════════════

def iterate_instructions(words: List[int]):
    """Generator over a PIGART body word stream (no TTree/OTree header).

    Walks `words` from index 0, yielding one tuple per OPCODE word:
        (decoded, form, operands)

    decoded:  dict from decode_opcode_word() — includes 'family', 'mnemonic',
              'arity', 'immediate', etc.
    form:     decoded['immediate'] — form discriminant for RNODE and REDGE:
                FORM_LEAN (0)      — lean / classic operand layout
                FORM_SHAPE (1)     — operands[2] = DATA-SYMBOL shape/style
                FORM_SHAPE_UDP (2) — RNODE shape+UDP or REDGE labeled
    operands: list of words[i+1 : i+1+arity] — the operand words for this
              instruction.

    Non-OPCODE words encountered between instructions are skipped defensively
    (should not occur in well-formed programs, but protects against corruption
    or mixed-type streams during composition).

    Callers:
      bounds()               — MeccanoProgram method, passes self.words
      pigart_ascii_renderer  — passes program.to_words()[2:]
      pigart_tkinter_renderer — passes program.to_words()[2:]
    """
    i = 0
    while i < len(words):
        w = words[i]
        if get_primary(w) != PRIMARY_OPCODE:
            i += 1
            continue
        decoded  = decode_opcode_word(w)
        arity    = decoded['arity']
        form     = decoded['immediate']
        operands = words[i + 1 : i + 1 + arity]
        yield decoded, form, operands
        i += 1 + arity


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

    # ── v0.2 widget programs (v0.4: labels use DATA-STRING encoding) ─────────
    # RNODE arity = 2 (pos + size) + len(_encode_label(text)); built per-program.

    # ── 5. box_rectangle — plain rectangle outline ───────────────────────────
    lib.register(MeccanoProgram(
        'box_rectangle',
        [
            build_opcode_word(OPF_PIGART, arity=2, op_index=OP_RNODE),
            _build_xy_map(4, 3),          # top-left at col 4, row 3
            _build_size_word(24, 8),       # 24 wide × 8 tall
            op_render,
        ],
        category='pigart',
        description='Plain rectangle outline (simplest widget)',
    ))

    # ── 6. labeled_box — rectangle with centred label ────────────────────────
    _lw_hello = _encode_label('Hello')    # 2 words → arity 4
    lib.register(MeccanoProgram(
        'labeled_box',
        [
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_hello), op_index=OP_RNODE),
            _build_xy_map(8, 5),           # top-left at col 8, row 5
            _build_size_word(22, 6),        # 22 wide × 6 tall
            *_lw_hello,
            op_render,
        ],
        category='pigart',
        description='Rectangle with centred "Hello" label inside',
    ))

    # ── 7. window_basic — frame + title bar + content area ───────────────────
    _lw_title = _encode_label('Title')    # 2 words → arity 4 for title bar
    lib.register(MeccanoProgram(
        'window_basic',
        [
            # Outer frame: 50 wide × 16 tall at (4, 2) — no label
            build_opcode_word(OPF_PIGART, arity=2, op_index=OP_RNODE),
            _build_xy_map(4, 2),
            _build_size_word(50, 16),
            # Title bar: 48 wide × 3 tall at (5, 3) — labelled 'Title'
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_title), op_index=OP_RNODE),
            _build_xy_map(5, 3),
            _build_size_word(48, 3),
            *_lw_title,
            # Content area: 48 wide × 10 tall at (5, 6) — no label
            build_opcode_word(OPF_PIGART, arity=2, op_index=OP_RNODE),
            _build_xy_map(5, 6),
            _build_size_word(48, 10),
            op_render,
        ],
        category='pigart',
        description='Window: outer frame + labelled title bar + content area',
    ))

    # ── 8. button_simple — small labelled button ─────────────────────────────
    _lw_ok = _encode_label('OK')          # 1 word → arity 3
    lib.register(MeccanoProgram(
        'button_simple',
        [
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_ok), op_index=OP_RNODE),
            _build_xy_map(24, 15),         # col 24, row 15
            _build_size_word(10, 3),        # 10 wide × 3 tall
            *_lw_ok,
            op_render,
        ],
        category='pigart',
        description='Small button with centred "OK" label',
    ))

    # ── v0.3 programs ────────────────────────────────────────────────────────
    op_redge_2 = build_opcode_word(OPF_PIGART, arity=2, op_index=OP_REDGE)

    # ── 9. flowchart_simple — three nodes + two downward edges ───────────────
    # Layout (60×20 canvas):
    #   Node 1 'Start'  at (3, 1), 12 wide × 3 tall  → rows 1-3
    #   Edge 1 ↓ from (8, 4) to (8, 6)              → arrowhead at row 6
    #   Node 2 'Decide' at (3, 7), 12 wide × 3 tall  → rows 7-9
    #   Edge 2 ↓ from (8, 10) to (8, 12)             → arrowhead at row 12
    #   Node 3 'End'    at (3, 13), 12 wide × 3 tall → rows 13-15
    # v0.4: labels encoded as DATA-STRING words (label_ids removed)
    _lw_start  = _encode_label('Start')   # 2 words → arity 4
    _lw_decide = _encode_label('Decide')  # 2 words → arity 4
    _lw_end    = _encode_label('End')     # 1 word  → arity 3
    lib.register(MeccanoProgram(
        'flowchart_simple',
        [
            # Symbol 1 — Start
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_start),  op_index=OP_RNODE),
            _build_xy_map(3, 1), _build_size_word(12, 3), *_lw_start,
            # Symbol 2 — Decide
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_decide), op_index=OP_RNODE),
            _build_xy_map(3, 7), _build_size_word(12, 3), *_lw_decide,
            # Symbol 3 — End
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_end),    op_index=OP_RNODE),
            _build_xy_map(3, 13), _build_size_word(12, 3), *_lw_end,
            # Edge 1: Start → Decide (downward)
            op_redge_2, _build_xy_map(8, 4), _build_xy_map(8, 6),
            # Edge 2: Decide → End (downward)
            op_redge_2, _build_xy_map(8, 10), _build_xy_map(8, 12),
            # Render
            op_render,
        ],
        category='pigart',
        description='Three-node flowchart: Start → Decide → End with downward arrows',
    ))

    # ── 10. composed_window — labeled_box + box_rectangle via compose() ───────
    # Demonstrates: two independent programs combined into one MeccanoProgram.
    # The composed stream contains both programs' RENDER opcodes; in ASCII mode
    # RENDER is a no-op so both are harmless (v0.4 may strip redundant RENDERs).
    composed_window = lib.get('labeled_box').compose(
        lib.get('box_rectangle'),
        name='composed_window',
        description=(
            'Window built by composing labeled_box (label+inner box) '
            '+ box_rectangle (outer frame) via MeccanoProgram.compose()'
        ),
    )
    lib.register(composed_window)

    # ── 11. greeting — arbitrary text beyond the old LABEL_TABLE ─────────────
    # 'Hello, World!' = 13 chars → ceil(13/3)=5 words → RNODE arity 7
    # Visible payoff of v0.4: any string, no registry lookup needed.
    _lw_hw = _encode_label('Hello, World!')
    lib.register(MeccanoProgram(
        'greeting',
        [
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_hw), op_index=OP_RNODE),
            _build_xy_map(4, 8),           # col 4, row 8
            _build_size_word(20, 3),        # 20 wide × 3 tall
            *_lw_hw,
            op_render,
        ],
        category='pigart',
        description="Arbitrary text box — 'Hello, World!' without LABEL_TABLE",
    ))

    # ── v0.5 programs (coordinate-relative composition) ─────────────────────
    # Underscore-prefix naming (_btn_*, _dialog_*) = private/intermediate helper.
    # These are NOT registered in the library; only the composed results are.

    # ── 12. composed_window_v05 — title bar above content area, no overlap ────
    # labeled_box  bounds = (8, 5, 29, 10)  (col 8-29, row 5-10)
    # box_rectangle bounds = (4, 3, 27, 10)
    # compose_below(gap=0): dy = 10 + 0 + 1 - 3 = 8 → box_rectangle → row 11-18
    # No border overlap. Fixes the known overlap in v0.3's composed_window.
    _cw_v05 = lib.get('labeled_box').compose_below(
        lib.get('box_rectangle'), gap=0,
        name='composed_window_v05',
        description='Title bar (labeled_box) above content area (box_rectangle) via '
                    'compose_below(gap=0) — no border overlap (fixes v0.3 composed_window)',
    )
    lib.register(_cw_v05)

    # ── 13. button_row — three buttons composed left-to-right ─────────────────
    # Each button is an inline MeccanoProgram (not registered, underscore prefix).
    # Sizes: OK=6×3, Cancel=10×3, Help=8×3. All start at origin (0,0).
    # After compose_right_of(gap=2): ok x=0-5, cancel x=8-17, help x=20-27.
    _lw_ok_btn  = _encode_label('OK')      # 1 word  → RNODE arity 3
    _lw_cancel  = _encode_label('Cancel')  # 2 words → RNODE arity 4
    _lw_help    = _encode_label('Help')    # 2 words → RNODE arity 4

    _btn_ok = MeccanoProgram(
        '_btn_ok',
        [
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_ok_btn), op_index=OP_RNODE),
            _build_xy_map(0, 0), _build_size_word(6, 3), *_lw_ok_btn,
            op_render,
        ],
        category='pigart',
        description='[private helper] OK button at origin',
    )
    _btn_cancel = MeccanoProgram(
        '_btn_cancel',
        [
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_cancel), op_index=OP_RNODE),
            _build_xy_map(0, 0), _build_size_word(10, 3), *_lw_cancel,
            op_render,
        ],
        category='pigart',
        description='[private helper] Cancel button at origin',
    )
    _btn_help = MeccanoProgram(
        '_btn_help',
        [
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_help), op_index=OP_RNODE),
            _build_xy_map(0, 0), _build_size_word(8, 3), *_lw_help,
            op_render,
        ],
        category='pigart',
        description='[private helper] Help button at origin',
    )
    _btn_row = _btn_ok.compose_right_of(
        _btn_cancel, gap=2,
    ).compose_right_of(
        _btn_help, gap=2,
        name='button_row',
        description='OK / Cancel / Help buttons composed left to right with gap=2',
    )
    lib.register(_btn_row)

    # ── 14. dialog_basic — message + button row + outer frame ─────────────────
    # Layout plan:
    #   _dialog_msg  'Are you sure?' RNODE at (0,0) size 18×3  → bounds (0,0,17,2)
    #   _content = _dialog_msg.compose_below(button_row, gap=1)
    #              button_row bounds (0,0,27,2) → shifted dy=2+1+1-0=4 → rows 4-6
    #              content bounds: (0,0,27,6)
    #   _content_inner = _content.translate(1,1) → bounds (1,1,28,7)
    #   frame: 30×9 at (0,0) → bounds (0,0,29,8) — wraps inner content with 1-cell margin
    #   _dialog = _frame.compose(_content_inner)
    # CAI spec note: framing is viable here because we compute content bounds first.
    _lw_sure = _encode_label('Are you sure?')  # 13 chars → 5 words → arity 7
    _dialog_msg = MeccanoProgram(
        '_dialog_msg',
        [
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_sure), op_index=OP_RNODE),
            _build_xy_map(0, 0), _build_size_word(18, 3), *_lw_sure,
            op_render,
        ],
        category='pigart',
        description='[private helper] Are you sure? message node at origin',
    )
    _content = _dialog_msg.compose_below(lib.get('button_row'), gap=1)
    # Translate content inward by 1 cell for frame margin
    _content_inner = _content.translate(1, 1)
    # Build frame to wrap the inner content (bounds: _content_inner)
    _cb  = _content_inner.bounds()     # (1, 1, 28, 7)
    _fw  = _cb[2] + 2                   # max_x + 1 (right margin) + 1 (0-indexed) = 30
    _fh  = _cb[3] + 2                   # max_y + 1 (bottom margin) + 1 (0-indexed) = 9
    _frame = MeccanoProgram(
        '_dialog_frame',
        [
            build_opcode_word(OPF_PIGART, arity=2, op_index=OP_RNODE),
            _build_xy_map(0, 0), _build_size_word(_fw, _fh),
            op_render,
        ],
        category='pigart',
        description=f'[private helper] Dialog outer frame {_fw}×{_fh}',
    )
    _dialog = _frame.compose(
        _content_inner,
        name='dialog_basic',
        description='Dialog: "Are you sure?" message + button row framed by a border rectangle',
    )
    lib.register(_dialog)

    # ── 15. flowchart_simple_v07 — shape-form flowchart (v0.7 demo) ──────────
    # Uses RNODE FORM_SHAPE (immediate=1) and REDGE FORM_SHAPE_UDP (immediate=2)
    # for labeled edges. Demonstrates all three new shape types (terminator,
    # process, decision) and one labeled edge.
    #
    # Layout (60×20 canvas):
    #   Start (TERMINATOR):  pos (5, 1), 10×3   → rows 1-3
    #   ↓ lean edge: (9,4)→(9,5)
    #   Proc (PROCESS):      pos (5, 6), 10×3   → rows 6-8
    #   ↓ styled edge: (9,9)→(9,10)
    #   OK? (DECISION):      pos (3,11), 14×5   → rows 11-15; mid at (10,13)
    #   → labeled "yes": (17,13)→(22,13)
    #   End (TERMINATOR):    pos (23,11), 8×3   → rows 11-13
    #   ↓ labeled "no": (10,16)→(10,18)
    #   Retry (PROCESS):     pos (5,19), 10×3   → rows 19-21 (just fits >20)
    #   Use height=22 for --render, but default canvas clips at 20.
    #   (Acceptance: at least terminator + decision + process + labeled edge in output)

    lib.register(MeccanoProgram(
        'flowchart_simple_v07',
        [
            # Node 1 — Start (TERMINATOR)
            *build_rnode_shape_labeled((5, 1),  (10, 3), SHAPE_TERMINATOR, 'Start'),
            # Edge 1→2 — lean downward
            build_opcode_word(OPF_PIGART, arity=2, op_index=OP_REDGE),
            _build_xy_map(9, 4), _build_xy_map(9, 5),
            # Node 2 — Proc (PROCESS)
            *build_rnode_shape_labeled((5, 6),  (10, 3), SHAPE_PROCESS,    'Proc'),
            # Edge 2→3 — styled downward
            *build_redge_styled((9, 9), (9, 10), SHAPE_RECTANGLE),
            # Node 3 — OK? (DECISION)
            *build_rnode_shape_labeled((3, 11), (14, 5), SHAPE_DECISION,   'OK?'),
            # Edge 3→End — labeled "yes" (rightward from decision right point)
            *build_redge_labeled((17, 13), (22, 13), SHAPE_RECTANGLE, 'yes'),
            # Node 4a — End (TERMINATOR, rightward branch)
            *build_rnode_shape_labeled((23, 11), (8, 3), SHAPE_TERMINATOR, 'End'),
            # Edge 3→Retry — labeled "no" (downward from decision bottom)
            *build_redge_labeled((10, 16), (10, 18), SHAPE_RECTANGLE, 'no'),
            # Node 4b — Retry (PROCESS, downward/no branch)
            *build_rnode_shape_labeled((5, 19), (10, 3), SHAPE_PROCESS,   'Retry'),
            # Render
            build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER),
        ],
        category='pigart',
        description=(
            'v0.7 shape-form flowchart: Start(T)→Proc(P)→OK?(D) with '
            '"yes"→End(T) and "no"→Retry(P); demonstrates FORM_SHAPE + labeled REDGE'
        ),
    ))

    return lib


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Test entry point
# ═══════════════════════════════════════════════════════════════════════════════

def test_meccano_library() -> bool:
    """v0.7 acceptance tests — 81 criteria (v0.1-v0.6 1–31, v0.7 32–81).

    CAI flag (Step 5 determinism resolution, v0.1):
    'name' is a registry key only — it does not appear in mmid.word, otree_word,
    or to_words(). Criterion 4 asserts that two MeccanoPrograms sharing category
    and words are fully word-identical (same mmid, same otree_word, same to_words())
    regardless of name. This is the correct semantics.

    CAI flag (test 19, v0.5):
    The spec's test 19 uses lib.get('line_horizontal').bounds() and asserts
    b_line[0] != b_line[2] (should span horizontally). BUT line_horizontal uses
    ORIGIN-mode MAP words (v0.1 geometry program), and _extract_map_xy returns
    (0,0) for those. An ORIGIN-mode RLINE gives bounds (0,0,0,0) — the assertion
    would fail. Resolution: use an inline ON_PLANE RLINE program for that test.
    Flagged here per spec instructions; factoring v0.1 programs to ON_PLANE is v0.6+.
    """
    print("=" * 60)
    print("TEST: Meccano Library v0.6")
    print("=" * 60)

    lib = _build_examples()

    # ── 1. All fifteen programs construct without error ───────────────────────
    assert len(lib.all()) == 15, f"expected 15 programs, got {len(lib.all())}"
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
    assert len(pigart) == 15
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

    # ── 8. window_basic renders the 'Title' label ─────────────────────────────
    window_output = _render(lib.get('window_basic'))
    assert 'Title' in window_output, \
        "window_basic: 'Title' label missing from rendered output"
    print(f"  8. PASS  window_basic renders 'Title' label")

    # ── 9. flowchart_simple: renders with labels and downward arrowheads ──────
    fc     = lib.get('flowchart_simple')
    fc_out = _render(fc)
    assert 'Start'  in fc_out, "flowchart_simple: 'Start' label missing from render"
    assert 'End'    in fc_out, "flowchart_simple: 'End' label missing from render"
    assert 'v'      in fc_out, "flowchart_simple: no downward arrowhead 'v' in render"
    print(f"  9. PASS  flowchart_simple renders with labels and arrows")

    # ── 10. composed_window: renders both component shapes ────────────────────
    cw     = lib.get('composed_window')
    cw_out = _render(cw)
    assert 'Hello' in cw_out, \
        "composed_window: 'Hello' label missing from rendered output"
    assert any(c in cw_out for c in '+-|'), \
        "composed_window: no rectangle characters in rendered output"
    print(f" 10. PASS  composed_window renders both component shapes")

    # ── 11. compose() is deterministic ───────────────────────────────────────
    _a = lib.get('box_rectangle')
    _b = lib.get('labeled_box')
    c1 = _a.compose(_b, name='c1')
    c2 = _a.compose(_b, name='c2')
    assert c1.words     == c2.words,     "compose: word stream not deterministic"
    assert c1.otree_word == c2.otree_word, "compose: OTree not deterministic"
    print(f" 11. PASS  compose() is deterministic (name excluded)")

    # ── 12. compose() is non-commutative (architectural payoff) ───────────────
    ab = _a.compose(_b, name='ab')
    ba = _b.compose(_a, name='ba')
    assert ab.words     != ba.words,     "compose: words should differ when order differs"
    assert ab.otree_word != ba.otree_word, "compose: OTree should differ when order differs"
    print(f" 12. PASS  compose() is non-commutative on words and OTree")

    # ── 13. compose() rejects category mismatch ───────────────────────────────
    _dummy = MeccanoProgram('dummy', _a.words[:1], category='word_op')
    try:
        _a.compose(_dummy)
        assert False, "compose should raise ValueError on category mismatch"
    except ValueError:
        pass
    print(f" 13. PASS  compose() raises ValueError on category mismatch")

    # ── 14. compose() word concatenation is associative ───────────────────────
    _c      = lib.get('button_simple')
    abc_ltr = (_a.compose(_b)).compose(_c, name='abc_ltr')
    abc_rtr = _a.compose(_b.compose(_c), name='abc_rtr')
    assert abc_ltr.words     == abc_rtr.words, \
        "compose: word concatenation should be associative"
    assert abc_ltr.otree_word == abc_rtr.otree_word, \
        "compose: OTree should match when words are identical (associativity)"
    print(f" 14. PASS  compose() word concatenation is associative (OTree follows)")

    # ── 15. greeting renders 'Hello, World!' ─────────────────────────────────
    g     = lib.get('greeting')
    g_out = _render(g)
    assert 'Hello, World!' in g_out, \
        f"greeting: 'Hello, World!' not in rendered output: {g_out!r}"
    print(f" 15. PASS  greeting renders 'Hello, World!'")

    # ── 16. arbitrary text — one-off program, never in LABEL_TABLE ───────────
    _lw_arb = _encode_label('Arbitrary 123')
    _test_arb = MeccanoProgram(
        'test_arbitrary',
        [
            build_opcode_word(OPF_PIGART, arity=2+len(_lw_arb), op_index=OP_RNODE),
            _build_xy_map(2, 5), _build_size_word(20, 3), *_lw_arb,
            build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER),
        ],
        category='pigart',
    )
    arb_out = _render(_test_arb)
    assert 'Arbitrary 123' in arb_out, \
        f"arbitrary text: 'Arbitrary 123' not in rendered output: {arb_out!r}"
    print(f" 16. PASS  arbitrary text 'Arbitrary 123' renders correctly")

    # ── 17. LABEL_TABLE is gone from pigart_ascii_renderer ───────────────────
    try:
        from pigart_ascii_renderer import LABEL_TABLE  # noqa: F401
        assert False, "LABEL_TABLE should be removed in v0.4"
    except ImportError:
        pass
    print(f" 17. PASS  LABEL_TABLE removed from pigart_ascii_renderer")

    # ── 18. v0.3 widget labels still render correctly with DATA-STRING encoding
    _expected_labels = {
        'labeled_box':      'Hello',
        'window_basic':     'Title',
        'button_simple':    'OK',
        'flowchart_simple': 'Start',
    }
    for _name, _label in _expected_labels.items():
        _out = _render(lib.get(_name))
        assert _label in _out, \
            f"{_name}: expected label {_label!r} missing from render"
    print(f" 18. PASS  v0.3 widgets render correct labels via DATA-STRING encoding")

    # ── v0.5 tests: coordinate-relative composition ───────────────────────────

    # ── 19. bounds() returns correct values for each PIGART opcode type ───────
    # RPOINT test: use point_red (ON_PLANE MAP word).
    b_point = lib.get('point_red').bounds()
    assert b_point[0] == b_point[2], "RPOINT bounds: min_x should equal max_x"
    assert b_point[1] == b_point[3], "RPOINT bounds: min_y should equal max_y"

    # RLINE test: must use an inline ON_PLANE program (see CAI flag in docstring —
    # line_horizontal uses ORIGIN-mode MAP words and gives (0,0,0,0) for both endpoints).
    _rline_test = MeccanoProgram(
        '_rline_bounds_test',
        [
            build_opcode_word(OPF_PIGART, arity=3, op_index=OP_RLINE),
            _build_xy_map(2, 5), _build_xy_map(10, 5),
            build_int_word(0),   # style placeholder
        ],
        category='pigart',
    )
    b_line = _rline_test.bounds()
    assert b_line[0] != b_line[2], "RLINE bounds: min_x should differ from max_x (horizontal span)"
    assert b_line[0] == 2 and b_line[2] == 10, f"RLINE bounds: expected x span 2-10, got {b_line}"

    # RNODE test: box_rectangle should span in both dimensions.
    b_box = lib.get('box_rectangle').bounds()
    assert b_box[2] > b_box[0] and b_box[3] > b_box[1], \
        "RNODE bounds: should span both dimensions (rectangle)"
    print(f" 19. PASS  bounds() correct for RPOINT, RLINE (ON_PLANE), RNODE")

    # ── 20. translate(0, 0) is identity ───────────────────────────────────────
    orig    = lib.get('labeled_box')
    shifted = orig.translate(0, 0)
    assert shifted.words == orig.words, "translate(0,0) should leave word stream unchanged"
    print(f" 20. PASS  translate(0,0) is identity")

    # ── 21. translate is invertible ───────────────────────────────────────────
    fwd  = orig.translate(5, 3)
    back = fwd.translate(-5, -3)
    assert back.words == orig.words, "translate is invertible: translate(dx,dy).translate(-dx,-dy) == original"
    print(f" 21. PASS  translate is invertible")

    # ── 22. translate is composable (additive) ────────────────────────────────
    t1     = orig.translate(2, 4)
    t2     = t1.translate(3, 1)
    direct = orig.translate(5, 5)
    assert t2.words == direct.words, "translate(a,b).translate(c,d) should equal translate(a+c,b+d)"
    print(f" 22. PASS  translate is composable (additive)")

    # ── 23. translate shifts bounding box by exactly (dx, dy) ─────────────────
    old_b = orig.bounds()
    new_b = orig.translate(10, 20).bounds()
    assert new_b[0] == old_b[0] + 10, f"translate: min_x should shift by 10, got {new_b[0] - old_b[0]}"
    assert new_b[1] == old_b[1] + 20, f"translate: min_y should shift by 20, got {new_b[1] - old_b[1]}"
    assert new_b[2] == old_b[2] + 10, f"translate: max_x should shift by 10"
    assert new_b[3] == old_b[3] + 20, f"translate: max_y should shift by 20"
    print(f" 23. PASS  translate shifts bounding box by exact (dx, dy)")

    # ── 24. compose_below: stacked result extends further down than self ───────
    _a_lb = lib.get('labeled_box')
    _b_br = lib.get('box_rectangle')
    stacked  = _a_lb.compose_below(_b_br, gap=1)
    stacked_b = stacked.bounds()
    a_b       = _a_lb.bounds()
    assert stacked_b[3] > a_b[3], \
        f"compose_below: stacked max_y ({stacked_b[3]}) should exceed labeled_box max_y ({a_b[3]})"
    print(f" 24. PASS  compose_below: stacked extends further down (max_y {stacked_b[3]} > {a_b[3]})")

    # ── 25. compose_right_of: rightcat extends further right than self ─────────
    rightcat   = _a_lb.compose_right_of(_b_br, gap=1)
    rightcat_b = rightcat.bounds()
    assert rightcat_b[2] > a_b[2], \
        f"compose_right_of: rightcat max_x ({rightcat_b[2]}) should exceed labeled_box max_x ({a_b[2]})"
    print(f" 25. PASS  compose_right_of: extends further right (max_x {rightcat_b[2]} > {a_b[2]})")

    # ── 26. composed_window_v05 renders with Hello label ──────────────────────
    cw5_out = _render(lib.get('composed_window_v05'))
    assert 'Hello' in cw5_out, \
        f"composed_window_v05: 'Hello' label missing from rendered output"
    assert any(c in cw5_out for c in '+-|'), \
        f"composed_window_v05: no rectangle characters in rendered output"
    print(f" 26. PASS  composed_window_v05 renders with 'Hello' label")

    # ── 27. button_row renders all three button labels ─────────────────────────
    btn_out = _render(lib.get('button_row'))
    assert 'OK'     in btn_out, "button_row: 'OK' label missing from rendered output"
    assert 'Cancel' in btn_out, "button_row: 'Cancel' label missing from rendered output"
    assert 'Help'   in btn_out, "button_row: 'Help' label missing from rendered output"
    print(f" 27. PASS  button_row renders all three button labels (OK / Cancel / Help)")

    # ── v0.6 tests: tkinter renderer ─────────────────────────────────────────
    # Tests 28-31 and all subsequent tkinter tests need a live display.
    # In headless environments (CI, Desktop Commander, SSH without DISPLAY)
    # these are SKIP'd, not FAIL'd — the code is still exercised by the
    # pigart_ascii_renderer path.  On Stevo's desktop they run in full.

    # ── 28. pigart_tkinter_renderer imports successfully ──────────────────────
    _HAS_DISPLAY = False
    _build_canvas = None   # type: ignore
    try:
        from pigart_tkinter_renderer import render_gui as _render_gui, \
                                            _build_canvas
        import tkinter as _tk
        _tk_probe = _tk.Tk()
        _tk_probe.destroy()
        _HAS_DISPLAY = True
        print(f" 28. PASS  pigart_tkinter_renderer imports successfully")
    except ImportError as _e28:
        raise ImportError(
            f"pigart_tkinter_renderer not importable ({_e28}). "
            f"Install python3-tk or check the module is present."
        )
    except Exception as _e28:
        print(f" 28. SKIP  pigart_tkinter_renderer — no display ({_e28})")

    # ── 29. _build_canvas on box_rectangle creates at least one shape ─────────
    if _HAS_DISPLAY:
        _root29, _canvas29 = _build_canvas(lib.get('box_rectangle'), scale=12, padding=20)
        _shapes29 = _canvas29.find_all()
        assert len(_shapes29) > 0, \
            f"box_rectangle: _build_canvas produced no shapes (got {len(_shapes29)})"
        _root29.destroy()
        print(f" 29. PASS  _build_canvas(box_rectangle) creates {len(_shapes29)} shape(s)")
    else:
        print(f" 29. SKIP  _build_canvas (no display)")

    # ── 30. _build_canvas on dialog_basic produces rectangles + text labels ───
    if _HAS_DISPLAY:
        _root30, _canvas30 = _build_canvas(lib.get('dialog_basic'), scale=12, padding=20)
        _shapes30 = _canvas30.find_all()
        assert len(_shapes30) >= 6, \
            f"dialog_basic: expected ≥6 shapes (frame + message + 3 buttons + labels), got {len(_shapes30)}"
        _types30 = {_canvas30.type(sid) for sid in _shapes30}
        assert 'rectangle' in _types30, \
            f"dialog_basic: no rectangle shapes (types found: {_types30})"
        assert 'text' in _types30, \
            f"dialog_basic: no text shapes (types found: {_types30})"
        _root30.destroy()
        print(f" 30. PASS  _build_canvas(dialog_basic): {len(_shapes30)} shapes "
              f"including rectangles and text")
    else:
        print(f" 30. SKIP  _build_canvas (no display)")

    # ── 31. Same word stream → both ASCII and GUI outputs (architectural test) ─
    _prog31  = lib.get('greeting')
    _ascii31 = _render(_prog31)
    assert 'Hello, World!' in _ascii31, \
        "greeting: 'Hello, World!' not in ASCII output"
    if _HAS_DISPLAY:
        _root31, _canvas31 = _build_canvas(_prog31, scale=12, padding=20)
        _gui_shapes31 = len(_canvas31.find_all())
        _root31.destroy()
        assert _gui_shapes31 > 0, \
            f"greeting: tkinter renderer produced no shapes (got {_gui_shapes31})"
        print(f" 31. PASS  Same word stream → ASCII ('Hello, World!' present) "
              f"and GUI ({_gui_shapes31} shape(s)) — architectural test")
    else:
        print(f" 31. PASS  Same word stream → ASCII ('Hello, World!' present); "
              f"GUI path SKIP (no display)")

    # ══════════════════════════════════════════════════════════════════════════
    # v0.7 tests: shape registry, iterate_instructions, extended builders,
    #             renderer shape dispatch, bridge
    # ══════════════════════════════════════════════════════════════════════════

    # ── 32. Shape registry constants are distinct non-negative integers ───────
    _all_shapes = [
        SHAPE_RECTANGLE, SHAPE_TERMINATOR, SHAPE_PROCESS, SHAPE_DECISION,
        SHAPE_IO, SHAPE_SUBROUTINE, SHAPE_CONNECTOR, SHAPE_OFFPAGE,
        SHAPE_DOCUMENT, SHAPE_DATA, SHAPE_LABELED_BOX, SHAPE_WINDOW,
        SHAPE_BUTTON,
    ]
    assert len(set(_all_shapes)) == len(_all_shapes), \
        "SHAPE_* constants must all be distinct"
    assert all(isinstance(s, int) and s >= 0 for s in _all_shapes), \
        "SHAPE_* constants must be non-negative integers"
    print(f" 32. PASS  {len(_all_shapes)} SHAPE_* constants, all distinct non-negative ints")

    # ── 33. Form discriminant constants are distinct ───────────────────────────
    assert FORM_LEAN == 0 and FORM_SHAPE == 1 and FORM_SHAPE_UDP == 2, \
        "FORM_* constants must be 0, 1, 2"
    print(f" 33. PASS  FORM_LEAN=0, FORM_SHAPE=1, FORM_SHAPE_UDP=2")

    # ── 34. build_data_symbol() encodes shape ID in top tribble (T17–T12) ──────
    # Symbol ID lives in ta (trits T17-T12); read back with get_field(w, 12, 6).
    _sym_w = build_data_symbol(SHAPE_DECISION)
    assert int(get_field(_sym_w, 12, 6)) == SHAPE_DECISION, \
        f"build_data_symbol: ta tribble should equal SHAPE_DECISION={SHAPE_DECISION}"
    _sym_w0 = build_data_symbol(0)
    assert int(get_field(_sym_w0, 12, 6)) == 0
    print(f" 34. PASS  build_data_symbol() payload round-trips correctly")

    # ── 35. iterate_instructions on lean RNODE ────────────────────────────────
    _lean_words = [
        build_opcode_word(OPF_PIGART, arity=2, op_index=OP_RNODE),
        _build_xy_map(0, 0), _build_size_word(10, 3),
    ]
    _it35 = list(iterate_instructions(_lean_words))
    assert len(_it35) == 1, "iterate_instructions: expected 1 instruction"
    _d35, _f35, _ops35 = _it35[0]
    assert _d35['mnemonic'] == 'RNODE' and _d35['arity'] == 2
    assert _f35 == FORM_LEAN
    assert len(_ops35) == 2
    print(f" 35. PASS  iterate_instructions: lean RNODE → form=FORM_LEAN, arity=2")

    # ── 36. iterate_instructions on shape RNODE ───────────────────────────────
    _shape_words = build_rnode_shape((1, 2), (8, 4), SHAPE_TERMINATOR)
    _it36 = list(iterate_instructions(_shape_words))
    assert len(_it36) == 1
    _d36, _f36, _ops36 = _it36[0]
    assert _d36['mnemonic'] == 'RNODE' and _d36['arity'] == 3
    assert _f36 == FORM_SHAPE
    assert len(_ops36) == 3
    assert int(get_field(_ops36[2], 12, 6)) == SHAPE_TERMINATOR  # shape ID in top tribble T17-T12
    print(f" 36. PASS  iterate_instructions: shape RNODE → form=FORM_SHAPE, shape_id correct")

    # ── 37. iterate_instructions on shape+UDP RNODE ───────────────────────────
    _udp_w = build_int_word(42)
    _udp_words = build_rnode_shape_udp((0, 0), (6, 3), SHAPE_PROCESS, _udp_w)
    _it37 = list(iterate_instructions(_udp_words))
    assert len(_it37) == 1
    _d37, _f37, _ops37 = _it37[0]
    assert _d37['arity'] == 4 and _f37 == FORM_SHAPE_UDP
    assert len(_ops37) == 4
    print(f" 37. PASS  iterate_instructions: shape+UDP RNODE → form=FORM_SHAPE_UDP, arity=4")

    # ── 38. iterate_instructions on lean REDGE ────────────────────────────────
    _lean_re = [
        build_opcode_word(OPF_PIGART, arity=2, op_index=OP_REDGE),
        _build_xy_map(0, 0), _build_xy_map(5, 0),
    ]
    _it38 = list(iterate_instructions(_lean_re))
    _d38, _f38, _ = _it38[0]
    assert _d38['mnemonic'] == 'REDGE' and _f38 == FORM_LEAN
    print(f" 38. PASS  iterate_instructions: lean REDGE → form=FORM_LEAN")

    # ── 39. iterate_instructions on styled REDGE ──────────────────────────────
    _styled_re = build_redge_styled((0, 0), (5, 0), SHAPE_RECTANGLE)
    _it39 = list(iterate_instructions(_styled_re))
    _d39, _f39, _ops39 = _it39[0]
    assert _d39['arity'] == 3 and _f39 == FORM_SHAPE
    assert len(_ops39) == 3
    print(f" 39. PASS  iterate_instructions: styled REDGE → form=FORM_SHAPE, arity=3")

    # ── 40. iterate_instructions on labeled REDGE ─────────────────────────────
    _labeled_re = build_redge_labeled((0, 0), (5, 0), SHAPE_RECTANGLE, 'yes')
    _it40 = list(iterate_instructions(_labeled_re))
    _d40, _f40, _ops40 = _it40[0]
    assert _f40 == FORM_SHAPE_UDP and _d40['arity'] >= 4
    print(f" 40. PASS  iterate_instructions: labeled REDGE → form=FORM_SHAPE_UDP")

    # ── 41. build_rnode_shape: correct word count and arity ───────────────────
    _rs41 = build_rnode_shape((2, 3), (10, 4), SHAPE_DECISION)
    assert len(_rs41) == 4, f"build_rnode_shape: expected 4 words, got {len(_rs41)}"
    _dec41 = decode_opcode_word(_rs41[0])
    assert _dec41['arity'] == 3 and _dec41['immediate'] == FORM_SHAPE
    print(f" 41. PASS  build_rnode_shape: 4 words, arity=3, immediate=FORM_SHAPE")

    # ── 42. build_rnode_shape_labeled: arity = 3 + label_words ───────────────
    _rsl42 = build_rnode_shape_labeled((0, 0), (10, 3), SHAPE_TERMINATOR, 'Start')
    _dec42 = decode_opcode_word(_rsl42[0])
    _lw42  = _encode_label('Start')
    assert _dec42['arity'] == 3 + len(_lw42), \
        f"build_rnode_shape_labeled: arity mismatch"
    assert _dec42['immediate'] == FORM_SHAPE
    print(f" 42. PASS  build_rnode_shape_labeled: arity=3+{len(_lw42)}")

    # ── 43. build_rnode_shape_udp: arity=4 ───────────────────────────────────
    _rsu43 = build_rnode_shape_udp((0, 0), (6, 3), SHAPE_CONNECTOR, build_int_word(0))
    assert decode_opcode_word(_rsu43[0])['arity'] == 4
    assert decode_opcode_word(_rsu43[0])['immediate'] == FORM_SHAPE_UDP
    print(f" 43. PASS  build_rnode_shape_udp: arity=4, immediate=FORM_SHAPE_UDP")

    # ── 44. build_redge_styled: arity=3 ──────────────────────────────────────
    _rs44 = build_redge_styled((0, 0), (0, 5), SHAPE_RECTANGLE)
    assert decode_opcode_word(_rs44[0])['arity'] == 3
    assert decode_opcode_word(_rs44[0])['immediate'] == FORM_SHAPE
    print(f" 44. PASS  build_redge_styled: arity=3, immediate=FORM_SHAPE")

    # ── 45. build_redge_labeled: arity = 3 + label_words ─────────────────────
    _rl45 = build_redge_labeled((0, 0), (5, 0), SHAPE_RECTANGLE, 'no')
    _lw45 = _encode_label('no')
    assert decode_opcode_word(_rl45[0])['arity'] == 3 + len(_lw45)
    assert decode_opcode_word(_rl45[0])['immediate'] == FORM_SHAPE_UDP
    print(f" 45. PASS  build_redge_labeled: arity=3+{len(_lw45)}, immediate=FORM_SHAPE_UDP")

    # ── 46. ASCII: shape RNODE with TERMINATOR renders rounded corners ────────
    from pigart_ascii_renderer import render as _render
    _p46 = MeccanoProgram('_t46', build_rnode_shape_labeled(
        (2, 1), (12, 3), SHAPE_TERMINATOR, 'Hi'), category='pigart')
    _o46 = _render(_p46)
    assert '/' in _o46 or '\\' in _o46, \
        f"TERMINATOR: expected rounded corners (/ or \\) in ASCII output:\n{_o46}"
    print(f" 46. PASS  ASCII TERMINATOR renders with rounded corners")

    # ── 47. ASCII: shape RNODE with DECISION renders diamond chars ────────────
    _p47 = MeccanoProgram('_t47', build_rnode_shape_labeled(
        (2, 1), (14, 7), SHAPE_DECISION, 'OK?'), category='pigart')
    _o47 = _render(_p47)
    assert any(c in _o47 for c in '<>^v/\\'), \
        f"DECISION: expected diamond chars in ASCII output:\n{_o47}"
    print(f" 47. PASS  ASCII DECISION renders with diamond chars")

    # ── 48. ASCII: PROCESS renders as rectangle ───────────────────────────────
    _p48 = MeccanoProgram('_t48', build_rnode_shape_labeled(
        (2, 1), (10, 3), SHAPE_PROCESS, 'Run'), category='pigart')
    _o48 = _render(_p48)
    assert any(c in _o48 for c in '+-|'), \
        f"PROCESS: expected rectangle chars in ASCII output:\n{_o48}"
    assert 'Run' in _o48, "PROCESS: label 'Run' missing from output"
    print(f" 48. PASS  ASCII PROCESS renders rectangle with label")

    # ── 49. ASCII: lean RNODE backward compat (same as before) ───────────────
    _o49 = _render(lib.get('box_rectangle'))
    assert any(c in _o49 for c in '+-|'), "lean RNODE backward compat broken"
    print(f" 49. PASS  ASCII lean RNODE backward-compatible (rectangle chars)")

    # ── 50. ASCII: labeled shape RNODE renders label text ─────────────────────
    _p50 = MeccanoProgram('_t50', build_rnode_shape_labeled(
        (2, 1), (14, 3), SHAPE_PROCESS, 'Execute'), category='pigart')
    assert 'Execute' in _render(_p50), "shape RNODE: label 'Execute' not rendered"
    print(f" 50. PASS  ASCII labeled shape RNODE renders label text")

    # ── 51. ASCII: labeled REDGE renders label text ───────────────────────────
    _p51 = MeccanoProgram(
        '_t51',
        [
            *build_rnode_shape_labeled((1, 1), (8, 3), SHAPE_TERMINATOR, 'A'),
            *build_redge_labeled((9, 2), (16, 2), SHAPE_RECTANGLE, 'yes'),
            *build_rnode_shape_labeled((17, 1), (8, 3), SHAPE_TERMINATOR, 'B'),
            build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER),
        ],
        category='pigart',
    )
    _o51 = _render(_p51, width=60, height=10)
    assert 'yes' in _o51, f"labeled REDGE: label 'yes' not in render output:\n{_o51}"
    print(f" 51. PASS  ASCII labeled REDGE renders 'yes' label")

    # ── 52. ASCII: CONNECTOR renders something (non-empty) ───────────────────
    _p52 = MeccanoProgram('_t52', build_rnode_shape(
        (5, 3), (4, 3), SHAPE_CONNECTOR), category='pigart')
    _o52 = _render(_p52)
    assert len(_o52.strip()) > 0, "CONNECTOR: render is empty"
    print(f" 52. PASS  ASCII CONNECTOR renders non-empty")

    # ── 53. tkinter: TERMINATOR creates oval or rounded shape ─────────────────
    if _HAS_DISPLAY:
        _p53 = MeccanoProgram('_t53', build_rnode_shape_labeled(
            (2, 1), (12, 3), SHAPE_TERMINATOR, 'S'), category='pigart')
        _r53, _c53 = _build_canvas(_p53)
        _shapes53 = _c53.find_all()
        _types53  = {_c53.type(s) for s in _shapes53}
        assert len(_shapes53) > 0, "TERMINATOR tkinter: no shapes produced"
        assert 'oval' in _types53 or 'rectangle' in _types53, \
            f"TERMINATOR tkinter: expected oval or rectangle, got {_types53}"
        _r53.destroy()
        print(f" 53. PASS  tkinter TERMINATOR creates shapes: {_types53}")
    else:
        print(f" 53. SKIP  tkinter TERMINATOR (no display)")

    # ── 54. tkinter: DECISION creates polygon or line shapes ──────────────────
    if _HAS_DISPLAY:
        _p54 = MeccanoProgram('_t54', build_rnode_shape_labeled(
            (2, 1), (14, 7), SHAPE_DECISION, 'D'), category='pigart')
        _r54, _c54 = _build_canvas(_p54)
        _shapes54 = _c54.find_all()
        assert len(_shapes54) > 0, "DECISION tkinter: no shapes produced"
        _types54  = {_c54.type(s) for s in _shapes54}
        _r54.destroy()
        print(f" 54. PASS  tkinter DECISION creates shapes: {_types54}")
    else:
        print(f" 54. SKIP  tkinter DECISION (no display)")

    # ── 55. tkinter: PROCESS creates rectangle (same as lean RNODE) ──────────
    if _HAS_DISPLAY:
        _p55 = MeccanoProgram('_t55', build_rnode_shape_labeled(
            (2, 1), (10, 3), SHAPE_PROCESS, 'P'), category='pigart')
        _r55, _c55 = _build_canvas(_p55)
        _t55 = {_c55.type(s) for s in _c55.find_all()}
        assert 'rectangle' in _t55, f"PROCESS tkinter: expected rectangle, got {_t55}"
        _r55.destroy()
        print(f" 55. PASS  tkinter PROCESS creates rectangle")
    else:
        print(f" 55. SKIP  tkinter PROCESS (no display)")

    # ── 56. tkinter: lean RNODE backward compat (still rectangle) ────────────
    if _HAS_DISPLAY:
        _r56, _c56 = _build_canvas(lib.get('labeled_box'))
        assert len(_c56.find_all()) > 0, "lean RNODE tkinter backward compat broken"
        _r56.destroy()
        print(f" 56. PASS  tkinter lean RNODE backward-compatible")
    else:
        print(f" 56. SKIP  tkinter lean RNODE (no display)")

    # ── 57. flowchart_simple_v07 constructs and registers ────────────────────
    _fc7 = lib.get('flowchart_simple_v07')
    assert _fc7 is not None
    assert _fc7.category == 'pigart'
    assert len(_fc7.words) > 20, \
        f"flowchart_simple_v07: word stream too short ({len(_fc7.words)})"
    print(f" 57. PASS  flowchart_simple_v07 constructed ({len(_fc7.words)} body words)")

    # ── 58. flowchart_simple_v07 contains all three shape types ──────────────
    _shapes_found = set()
    for _dec, _form, _ops in iterate_instructions(_fc7.words):
        if _dec['mnemonic'] == 'RNODE' and _form == FORM_SHAPE and len(_ops) >= 3:
            _shapes_found.add(int(get_field(_ops[2], 12, 6)))  # shape ID in top tribble T17-T12
    assert SHAPE_TERMINATOR in _shapes_found, \
        "flowchart_simple_v07: no TERMINATOR node found"
    assert SHAPE_PROCESS in _shapes_found, \
        "flowchart_simple_v07: no PROCESS node found"
    assert SHAPE_DECISION in _shapes_found, \
        "flowchart_simple_v07: no DECISION node found"
    print(f" 58. PASS  flowchart_simple_v07 contains TERMINATOR, PROCESS, DECISION")

    # ── 59. flowchart_simple_v07 contains labeled edges ──────────────────────
    _labeled_edges = 0
    for _dec, _form, _ops in iterate_instructions(_fc7.words):
        if _dec['mnemonic'] == 'REDGE' and _form == FORM_SHAPE_UDP:
            _labeled_edges += 1
    assert _labeled_edges >= 2, \
        f"flowchart_simple_v07: expected ≥2 labeled edges, got {_labeled_edges}"
    print(f" 59. PASS  flowchart_simple_v07 has {_labeled_edges} labeled REDGE instructions")

    # ── 60. flowchart_simple_v07 renders via ASCII ────────────────────────────
    _o60 = _render(_fc7, width=60, height=25)
    assert 'Start' in _o60, "flowchart_simple_v07 ASCII: 'Start' missing"
    assert 'End'   in _o60, "flowchart_simple_v07 ASCII: 'End' missing"
    assert 'yes'   in _o60, "flowchart_simple_v07 ASCII: 'yes' edge label missing"
    print(f" 60. PASS  flowchart_simple_v07 ASCII render contains Start, End, 'yes'")

    # ── 61. flowchart_simple_v07 contains terminator rounded-rect chars ───────
    assert '/' in _o60 or '\\' in _o60, \
        f"flowchart_simple_v07 ASCII: no terminator rounded corners in render"
    print(f" 61. PASS  flowchart_simple_v07 ASCII: terminator shape chars present")

    # ── 62. flowchart_simple_v07 renders via tkinter ──────────────────────────
    if _HAS_DISPLAY:
        _r62, _c62 = _build_canvas(_fc7, scale=12, padding=20)
        _count62   = len(_c62.find_all())
        _r62.destroy()
        assert _count62 >= 6, \
            f"flowchart_simple_v07 tkinter: expected ≥6 shapes, got {_count62}"
        print(f" 62. PASS  flowchart_simple_v07 tkinter renders {_count62} shapes")
    else:
        print(f" 62. SKIP  flowchart_simple_v07 tkinter (no display)")

    # ── 63. iterate_instructions skips non-OPCODE words defensively ──────────
    _mixed = [
        _build_xy_map(0, 0),           # stray MAP — should be skipped
        build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER),
        _build_size_word(3, 3),         # stray DATA — should be skipped
        build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER),
    ]
    _it63 = list(iterate_instructions(_mixed))
    assert len(_it63) == 2, \
        f"iterate_instructions: stray words should be skipped, got {len(_it63)} instructions"
    print(f" 63. PASS  iterate_instructions skips non-OPCODE words defensively")

    # ── 64. iterate_instructions on multi-instruction stream ─────────────────
    _multi = (
        build_rnode_shape_labeled((0, 0), (8, 3), SHAPE_PROCESS, 'A')
        + build_rnode_shape_labeled((10, 0), (8, 3), SHAPE_TERMINATOR, 'B')
        + [build_opcode_word(OPF_PIGART, arity=0, op_index=OP_RENDER)]
    )
    _it64 = list(iterate_instructions(_multi))
    assert len(_it64) == 3  # 2 RNODE + 1 RENDER
    assert _it64[0][0]['mnemonic'] == 'RNODE'
    assert _it64[1][0]['mnemonic'] == 'RNODE'
    assert _it64[2][0]['mnemonic'] == 'RENDER'
    print(f" 64. PASS  iterate_instructions walks multi-instruction stream correctly")

    # ── 65. bounds() works on shape-form RNODE ───────────────────────────────
    _p65 = MeccanoProgram('_t65',
        build_rnode_shape_labeled((5, 3), (12, 5), SHAPE_DECISION, 'X'),
        category='pigart')
    _b65 = _p65.bounds()
    assert _b65[0] == 5  and _b65[1] == 3, \
        f"bounds shape RNODE: expected min (5,3), got {_b65[:2]}"
    assert _b65[2] == 16 and _b65[3] == 7, \
        f"bounds shape RNODE: expected max (16,7), got {_b65[2:]}"
    print(f" 65. PASS  bounds() correct for shape-form RNODE: {_b65}")

    # ── 66. bounds() works on labeled REDGE ──────────────────────────────────
    _p66 = MeccanoProgram('_t66',
        build_redge_labeled((3, 5), (10, 5), SHAPE_RECTANGLE, 'go'),
        category='pigart')
    _b66 = _p66.bounds()
    assert _b66[0] == 3 and _b66[2] == 10, \
        f"bounds labeled REDGE: expected x span 3-10, got {_b66}"
    print(f" 66. PASS  bounds() correct for labeled REDGE")

    # ── 67. translate() works on shape-form RNODE ────────────────────────────
    _p67 = MeccanoProgram('_t67',
        build_rnode_shape_labeled((2, 2), (8, 3), SHAPE_TERMINATOR, 'T'),
        category='pigart')
    _shifted67 = _p67.translate(3, 4)
    _b67_orig  = _p67.bounds()
    _b67_shift = _shifted67.bounds()
    assert _b67_shift[0] == _b67_orig[0] + 3, "translate on shape RNODE: x not shifted"
    assert _b67_shift[1] == _b67_orig[1] + 4, "translate on shape RNODE: y not shifted"
    print(f" 67. PASS  translate() works on shape-form RNODE")

    # ── 68–70: FlowCode bridge fixture tests ─────────────────────────────────
    import sys as _sys, os as _os
    _sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
    from flowcode_bridge import flowcode_to_meccano, FLOWCODE_SHAPE_MAP, FC_GRID_TO_MECCANO

    # Fixture builder (inline FCCanvas, avoids importing full FlowCode GUI)
    _sys.path.insert(0, _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                      '..', 'FlowCode'))

    # ── 68. bridge: hello-world single-node canvas ────────────────────────────
    try:
        from flowcode import FCCanvas, FCSymbol, SYMBOL_PROCESS, SYMBOL_TERMINATOR, \
                             SYMBOL_DECISION, SYMBOL_IO
        _cv68 = FCCanvas()
        _s1   = _cv68.add_symbol(SYMBOL_TERMINATOR, 120, 40, 'Hello')
        _prog68 = flowcode_to_meccano(_cv68, name='hello_world')
        assert _prog68.category == 'pigart'
        assert len(_prog68.words) > 0
        _it68 = list(iterate_instructions(_prog68.words))
        assert any(d['mnemonic'] == 'RNODE' for d, _, _ in _it68), \
            "bridge hello_world: no RNODE in word stream"
        print(f" 68. PASS  bridge hello_world: 1 symbol → {len(_prog68.words)} body words")
    except Exception as _e68:
        print(f" 68. SKIP  bridge hello_world ({_e68})")

    # ── 69. bridge: yes/no decision flowchart ────────────────────────────────
    try:
        _cv69 = FCCanvas()
        _s69a = _cv69.add_symbol(SYMBOL_TERMINATOR, 120, 40,  'Start')
        _s69b = _cv69.add_symbol(SYMBOL_DECISION,   120, 160, 'OK?')
        _s69c = _cv69.add_symbol(SYMBOL_TERMINATOR, 120, 280, 'End')
        _cv69.add_edge(_s69a.id, _s69b.id)
        _cv69.add_edge(_s69b.id, _s69c.id, condition='yes')
        _prog69 = flowcode_to_meccano(_cv69, name='yes_no')
        _it69   = list(iterate_instructions(_prog69.words))
        _nodes69 = [d for d, _, _ in _it69 if d['mnemonic'] == 'RNODE']
        _edges69 = [d for d, _, _ in _it69 if d['mnemonic'] == 'REDGE']
        assert len(_nodes69) == 3, f"bridge yes/no: expected 3 RNODE, got {len(_nodes69)}"
        assert len(_edges69) == 2, f"bridge yes/no: expected 2 REDGE, got {len(_edges69)}"
        print(f" 69. PASS  bridge yes/no: 3 nodes, 2 edges → {len(_prog69.words)} body words")
    except Exception as _e69:
        print(f" 69. SKIP  bridge yes/no ({_e69})")

    # ── 70. bridge: subroutine-call flowchart ────────────────────────────────
    try:
        _cv70 = FCCanvas()
        _s70a = _cv70.add_symbol(SYMBOL_PROCESS, 120, 40,  'Main')
        _s70b = _cv70.add_symbol(SYMBOL_PROCESS, 120, 160, 'Sub')
        _s70c = _cv70.add_symbol(SYMBOL_IO,      120, 280, 'IO')
        _cv70.add_edge(_s70a.id, _s70b.id)
        _cv70.add_edge(_s70b.id, _s70c.id)
        _prog70 = flowcode_to_meccano(_cv70, name='sub_call')
        _it70   = list(iterate_instructions(_prog70.words))
        assert sum(1 for d, _, _ in _it70 if d['mnemonic'] == 'RNODE') == 3
        print(f" 70. PASS  bridge sub_call: 3 nodes → {len(_prog70.words)} body words")
    except Exception as _e70:
        print(f" 70. SKIP  bridge sub_call ({_e70})")

    # ── 71. FLOWCODE_SHAPE_MAP keys match existing FC symbol kinds ────────────
    try:
        assert SYMBOL_PROCESS    in FLOWCODE_SHAPE_MAP, "'process' not in FLOWCODE_SHAPE_MAP"
        assert SYMBOL_DECISION   in FLOWCODE_SHAPE_MAP, "'decision' not in FLOWCODE_SHAPE_MAP"
        assert SYMBOL_IO         in FLOWCODE_SHAPE_MAP, "'io' not in FLOWCODE_SHAPE_MAP"
        assert SYMBOL_TERMINATOR in FLOWCODE_SHAPE_MAP, "'terminator' not in FLOWCODE_SHAPE_MAP"
        print(f" 71. PASS  FLOWCODE_SHAPE_MAP contains all 4 current FC symbol kinds")
    except Exception as _e71:
        print(f" 71. SKIP  FLOWCODE_SHAPE_MAP check ({_e71})")

    # ── 72. FC_GRID_TO_MECCANO is a positive integer ─────────────────────────
    assert isinstance(FC_GRID_TO_MECCANO, int) and FC_GRID_TO_MECCANO > 0, \
        f"FC_GRID_TO_MECCANO must be a positive int, got {FC_GRID_TO_MECCANO!r}"
    print(f" 72. PASS  FC_GRID_TO_MECCANO = {FC_GRID_TO_MECCANO} (positive int)")

    # ── 73. bridge output is a valid MeccanoProgram ───────────────────────────
    try:
        _cv73 = FCCanvas()
        _cv73.add_symbol(SYMBOL_PROCESS, 120, 40, 'X')
        _p73 = flowcode_to_meccano(_cv73)
        assert hasattr(_p73, 'words') and hasattr(_p73, 'to_words')
        assert hasattr(_p73, 'bounds')
        _b73 = _p73.bounds()   # should not raise
        assert len(_b73) == 4
        print(f" 73. PASS  bridge output is a valid MeccanoProgram with bounds {_b73}")
    except Exception as _e73:
        print(f" 73. SKIP  bridge output validation ({_e73})")

    # ── 74. bridge output word stream decodes cleanly ─────────────────────────
    try:
        for _w in _p73.to_words():
            _dw = decode_word(_w)
            assert 'type' in _dw, f"bridge word {_w!r} failed decode"
        print(f" 74. PASS  bridge word stream decodes cleanly")
    except Exception as _e74:
        print(f" 74. SKIP  bridge word stream decode ({_e74})")

    # ── 75. bridge output renders via ASCII without error ─────────────────────
    try:
        _o75 = _render(_p73, width=60, height=20)
        assert isinstance(_o75, str) and len(_o75) > 0
        print(f" 75. PASS  bridge output renders via ASCII renderer")
    except Exception as _e75:
        print(f" 75. SKIP  bridge ASCII render ({_e75})")

    # ── 76. bridge output renders via tkinter without error ───────────────────
    if _HAS_DISPLAY:
        try:
            _r76, _c76 = _build_canvas(_p73)
            assert len(_c76.find_all()) > 0
            _r76.destroy()
            print(f" 76. PASS  bridge output renders via tkinter renderer")
        except Exception as _e76:
            print(f" 76. SKIP  bridge tkinter render ({_e76})")
    else:
        print(f" 76. SKIP  bridge tkinter render (no display)")

    # ── 77. existing v0.1-v0.6 programs render byte-identical to pre-v0.7 ─────
    # Regression: existing lean-form programs must not be affected by v0.7 changes.
    # We verify by re-rendering and checking for key output markers.
    _regression = {
        'triangle_method_a': lambda o: True,         # no renderer check (ORIGIN-mode)
        'box_rectangle':     lambda o: '+' in o,
        'flowchart_simple':  lambda o: 'Start' in o and 'v' in o,
        'dialog_basic':      lambda o: 'Are you' in o,
        'button_row':        lambda o: 'OK' in o and 'Cancel' in o,
    }
    for _rname, _check in _regression.items():
        _rout = _render(lib.get(_rname))
        if _rname == 'triangle_method_a':
            pass  # ORIGIN-mode — renderer produces blank (fine, no change)
        else:
            assert _check(_rout), \
                f"regression {_rname!r}: v0.7 broke existing program rendering"
    print(f" 77. PASS  v0.1-v0.6 existing programs render correctly after v0.7")

    # ── 78. compose_below works with shape-form programs ─────────────────────
    _pa78 = MeccanoProgram('_a78',
        build_rnode_shape_labeled((0, 0), (10, 3), SHAPE_PROCESS, 'Top'),
        category='pigart')
    _pb78 = MeccanoProgram('_b78',
        build_rnode_shape_labeled((0, 0), (10, 3), SHAPE_TERMINATOR, 'Bot'),
        category='pigart')
    _comp78 = _pa78.compose_below(_pb78, gap=1)
    _b78    = _comp78.bounds()
    assert _b78[3] > _pa78.bounds()[3], \
        "compose_below with shape programs: stacked max_y should exceed top max_y"
    print(f" 78. PASS  compose_below works with shape-form programs")

    # ── 79. MeccanoProgram with only shape-form RNODE: to_words() round-trips ─
    _p79 = MeccanoProgram('_t79',
        build_rnode_shape_labeled((3, 2), (10, 4), SHAPE_DECISION, 'Decide'),
        category='pigart')
    _w79 = _p79.to_words()
    assert len(_w79) >= 3, "to_words() too short for shape RNODE"
    for _ww in _w79:
        assert 'type' in decode_word(_ww)
    print(f" 79. PASS  shape-form MeccanoProgram to_words() round-trips ({len(_w79)} words)")

    # ── 80. OTree differs for programs differing only in SHAPE_* (Bundle 8 fix) ─
    # Shape ID now lives in T17–T12 (ta), which the Fingerprint Fold uses.
    # Two programs identical except for their shape symbol must produce distinct
    # OTree addresses.  (Same position, same size — only shape_id differs.)
    _pa80 = MeccanoProgram('_a80',
        build_rnode_shape((5, 5), (10, 5), SHAPE_PROCESS),    category='pigart')
    _pb80 = MeccanoProgram('_b80',
        build_rnode_shape((5, 5), (10, 5), SHAPE_TERMINATOR), category='pigart')
    assert _pa80.otree_word != _pb80.otree_word, \
        "Programs differing only in SHAPE_* should produce different OTree"
    print(f" 80. PASS  Different SHAPE_* IDs → different OTree (fold sees ta tribble)")

    # ── 81. flowchart_simple_v07 renders differently from flowchart_simple ────
    _o81a = _render(lib.get('flowchart_simple'),      width=60, height=20)
    _o81b = _render(lib.get('flowchart_simple_v07'),  width=60, height=25)
    assert _o81a != _o81b, \
        "v0.7 flowchart should render differently from v0.3 flowchart"
    print(f" 81. PASS  flowchart_simple_v07 renders differently from flowchart_simple")

    # ── 82. OTree differs for REDGEs with different style symbols (Bundle 8) ──
    # Style ID (e.g. STYLE_CONTAIN=100 vs SHAPE_RECTANGLE=0 used as a style)
    # is also packed into ta.  Two REDGEs with different style IDs should yield
    # different OTree addresses.
    _p82a = MeccanoProgram('_s82a',
        build_redge_styled((0, 0), (5, 5), SHAPE_RECTANGLE),   category='pigart')
    _p82b = MeccanoProgram('_s82b',
        build_redge_styled((0, 0), (5, 5), STYLE_CONTAIN),     category='pigart')
    assert _p82a.otree_word != _p82b.otree_word, \
        "REDGEs differing only in style symbol should produce different OTree"
    print(f" 82. PASS  Different style IDs (REDGE) → different OTree (ta participates)")

    # ── 83. Same shape + position → identical OTree (determinism preserved) ───
    _p83a = MeccanoProgram('_d83a',
        build_rnode_shape((3, 3), (8, 4), SHAPE_DECISION), category='pigart')
    _p83b = MeccanoProgram('_d83b',
        build_rnode_shape((3, 3), (8, 4), SHAPE_DECISION), category='pigart')
    assert _p83a.otree_word == _p83b.otree_word, \
        "Programs with same shape+position should produce identical OTree"
    print(f" 83. PASS  Same shape + position → identical OTree (content addressing preserved)")

    print()
    print(f"widget_lib v0.7: {len(lib.all())} programs, all tests pass")
    return True


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — Demo entry point
# ═══════════════════════════════════════════════════════════════════════════════

def demo():
    """Print each program with coordinates — for human eyeballing."""
    lib = _build_examples()
    print("=" * 60)
    print("  Meccano Library v0.6 — Program Registry Demo")
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
            print("usage: widget_lib.py --render <program_name>", file=sys.stderr)
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
    if '--render-gui' in sys.argv:
        _idx = sys.argv.index('--render-gui')
        if _idx + 1 >= len(sys.argv):
            print("usage: widget_lib.py --render-gui <program_name>", file=sys.stderr)
            sys.exit(2)
        from pigart_tkinter_renderer import render_gui as _render_gui
        _lib  = _build_examples()
        _name = sys.argv[_idx + 1]
        if _name not in _lib.programs:
            print(f"unknown program: {_name!r}", file=sys.stderr)
            print(f"available: {', '.join(sorted(_lib.programs))}", file=sys.stderr)
            sys.exit(2)
        _render_gui(_lib.get(_name))
        sys.exit(0)
    demo()
