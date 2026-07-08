"""ternoo_glyph.py — the native glyph plane (register v0.3, S1-S6 + O1 ruled).

A character IS a word. Within DATA/STRING, encoding-plane T19 = +1 (native,
== the existing STRING_TERNARY) selects the native glyph plane, additive
beside the ascii/unicode planes (hospitable doctrine). This module is the
single source of truth for that plane's payload; the generic decode_word only
recognises the plane and delegates here (CF5 ruling 2, 2026-07-08).

LEFT-TO-RIGHT NON-COMMUTATIVE CONTEXT SENSITIVITY (register S1, the founding
law): a defining trit may condition the semantics of trits to its RIGHT, never
its left, and no payload VALUE is ever a hidden mode switch. Here: T19 (plane)
conditions the payload; T18 (mode) further qualifies it. Ordinary hierarchical
typing — not a sentinel.

Word layout (ratified trit map, R4 2026-07-08):
    T23 T22 : primary            DATA          (−1,+1)
    T21 T20 : subtype            STRING        (+1,−1)   [working canon; the
              DATA_STRING=(+1,+1) constant in v03 is a KNOWN latent bug —
              left untouched this build, see widget_lib.py:620]
    T19     : encoding plane      +1 native (== STRING_TERNARY)
    T18     : mode                0 text | +1/−1 signed numeric literal
    --- payload, TEXT mode ---
    T17..T12 : X   assigned place in the containing list (produce-order in v1)
    T11..T6  : Y   T11 case (+1 up / −1 low / 0 caseless); T10..T6 signed
                   ordinal (0 = null/no-character); Y is also the index into
                   the font's ordered glyph array (O1)
    T5..T0   : Z   font registry index (0 = house font in v1)
    --- payload, LITERAL mode ---
    T17..T0  : magnitude (sign = T18); range ±193,710,244

Date: 2026-07-08, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import os
import importlib.util as _ilu

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


V = _load('5500fp_ternoo_v03')

# ── build on v03's REAL constants (never re-declare the trits) ───────────────
PRIMARY_DATA = V.PRIMARY_DATA
NATIVE_PLANE = V.STRING_TERNARY          # +1 — the native glyph plane
GLYPH_T21, GLYPH_T20 = +1, -1            # STRING subtype, ratified working canon

# absolute trit positions (T-index)
POS_MODE = 18                            # T18 (in the qualifier field)
Z_LSB, Z_WIDTH = 0, 6                    # T0..T5   font index
ORD_LSB, ORD_WIDTH = 6, 5               # T6..T10  signed ordinal
POS_CASE = 11                            # T11      case trit
X_LSB, X_WIDTH = 12, 6                   # T12..T17 position
PAY_LSB, PAY_WIDTH = 0, 18               # T0..T17  literal magnitude

ORD_MAX = (3 ** ORD_WIDTH - 1) // 2      # 121
X_MAX = (3 ** X_WIDTH - 1) // 2          # 364
LIT_MAX = (3 ** PAY_WIDTH - 1) // 2      # 193,710,244


class GlyphError(ValueError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# Plane / mode predicates
# ═══════════════════════════════════════════════════════════════════════════

def is_glyph_plane(word: int) -> bool:
    """A DATA/STRING word in the native plane (T19 = +1)."""
    prim = V.get_field(word, V.PRIMARY_LST, V.PRIMARY_WIDTH)
    if prim != PRIMARY_DATA:
        return False
    return (V.get_trit(word, 21) == GLYPH_T21
            and V.get_trit(word, 20) == GLYPH_T20
            and V.get_trit(word, 19) == NATIVE_PLANE)


def is_literal(word: int) -> bool:
    """A native-plane numeric literal (T18 != 0)."""
    return is_glyph_plane(word) and V.get_trit(word, POS_MODE) != 0


def _require_text(word: int):
    if not is_glyph_plane(word):
        raise GlyphError('not a native glyph-plane word')
    if V.get_trit(word, POS_MODE) != 0:
        raise GlyphError('literal word has no character identity — project '
                         'via literal_to_digit_words()')


# ═══════════════════════════════════════════════════════════════════════════
# Text-character words
# ═══════════════════════════════════════════════════════════════════════════

def make_glyph(ordinal: int, case: int = 0, position: int = 0,
               font: int = 0) -> int:
    """A text character. ordinal 0 is null/no-character and is rejected; case
    is +1 upper / −1 lower / 0 caseless. X (position) and Z (font) default to
    their v1-trivial values and are meaningful fields, not padding (O1)."""
    if ordinal == 0:
        raise GlyphError('ordinal 0 is null/no-character — not a glyph')
    if not -ORD_MAX <= ordinal <= ORD_MAX:
        raise GlyphError(f'ordinal {ordinal} out of range ±{ORD_MAX}')
    if case not in (-1, 0, 1):
        raise GlyphError(f'case {case} must be +1 / 0 / −1')
    if not -X_MAX <= position <= X_MAX:
        raise GlyphError(f'position {position} out of range ±{X_MAX} (O2)')
    qual = V._data_qualifier(GLYPH_T21, GLYPH_T20, NATIVE_PLANE, 0)  # text mode
    w = V._make_word(PRIMARY_DATA, qual, 0)
    w = V.set_field(w, ORD_LSB, ORD_WIDTH, ordinal)
    w = V.set_trit(w, POS_CASE, case)
    w = V.set_field(w, X_LSB, X_WIDTH, position)
    w = V.set_field(w, Z_LSB, Z_WIDTH, font)
    return w


def parse_glyph(word: int):
    """(ordinal, case). Raises on a literal (the renderer must project first)."""
    _require_text(word)
    return get_ordinal(word), get_case(word)


def get_ordinal(word: int) -> int:
    _require_text(word)
    return V.get_field(word, ORD_LSB, ORD_WIDTH)


def get_case(word: int) -> int:
    _require_text(word)
    return V.get_trit(word, POS_CASE)


def get_position(word: int) -> int:
    _require_text(word)
    return V.get_field(word, X_LSB, X_WIDTH)


def get_font(word: int) -> int:
    _require_text(word)
    return V.get_field(word, Z_LSB, Z_WIDTH)


def set_position(word: int, position: int) -> int:
    _require_text(word)
    if not -X_MAX <= position <= X_MAX:
        raise GlyphError(f'position {position} out of range ±{X_MAX} (O2)')
    return V.set_field(word, X_LSB, X_WIDTH, position)


# ── case ops as trit WRITES (never arithmetic — S-law) ──────────────────────
def to_upper(word: int) -> int:
    _require_text(word)
    return V.set_trit(word, POS_CASE, +1)


def to_lower(word: int) -> int:
    _require_text(word)
    return V.set_trit(word, POS_CASE, -1)


def to_caseless(word: int) -> int:
    _require_text(word)
    return V.set_trit(word, POS_CASE, 0)


fold_case = to_caseless          # fold = zero the case trit


def same_identity(a: int, b: int) -> bool:
    """Compare Y only (case + ordinal). Names its masking (X/Z ignored)."""
    _require_text(a); _require_text(b)
    return V.get_field(a, ORD_LSB, ORD_WIDTH + 1) == \
        V.get_field(b, ORD_LSB, ORD_WIDTH + 1)


def same_folded(a: int, b: int) -> bool:
    """Case-insensitive: fold both, compare Y (i.e. compare ordinal)."""
    return get_ordinal(a) == get_ordinal(b)


# ═══════════════════════════════════════════════════════════════════════════
# Numeric literals (never touch the renderer)
# ═══════════════════════════════════════════════════════════════════════════

def make_literal(value: int) -> int:
    """A native-plane signed numeric literal. Sign in T18, magnitude in the
    18-trit payload; raises on overflow (S4 range, no silent truncation)."""
    mag = abs(value)
    if mag > LIT_MAX:
        raise GlyphError(f'literal {value} out of range ±{LIT_MAX}')
    sign = -1 if value < 0 else +1               # 0 → +1, magnitude 0
    qual = V._data_qualifier(GLYPH_T21, GLYPH_T20, NATIVE_PLANE, sign)
    w = V._make_word(PRIMARY_DATA, qual, 0)
    return V.set_field(w, PAY_LSB, PAY_WIDTH, mag)


def literal_value(word: int) -> int:
    if not is_literal(word):
        raise GlyphError('not a native-plane literal')
    sign = V.get_trit(word, POS_MODE)
    return sign * V.get_field(word, PAY_LSB, PAY_WIDTH)


def literal_to_digit_words(value: int) -> list:
    """S4 projection: a literal → the glyph words that DISPLAY it (leading
    hyphen for negatives, then digit-characters), X assigned in produce order."""
    words = []
    if value < 0:
        words.append(make_glyph(ORDINAL['-']))
    for ch in str(abs(value)):
        words.append(make_glyph(ORDINAL[ch]))     # digit chars, ordinals 28..37
    return _assign_positions(words)


# ═══════════════════════════════════════════════════════════════════════════
# Provisional ordinal table (house DEFAULT font/map convention — NOT a decree;
# revisable under open item O4. Data, not architecture.)
# ═══════════════════════════════════════════════════════════════════════════

ORDINAL = {}
for _i, _ch in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ', start=1):
    ORDINAL[_ch] = _i                     # A=1 .. Z=26 (case via the case trit)
ORDINAL[' '] = 27
for _d in range(10):
    ORDINAL[str(_d)] = 28 + _d            # digit characters '0'..'9' = 28..37
ORDINAL.update({                          # negative band: punctuation & marks
    '.': -1, ',': -2, ':': -3, ';': -4, '!': -5, '?': -6,
    '⸮': -7,                              # answer mark
    # -8 idea mark (⸮?) — founding resident by captain's history
    '~': -9,                              # placeholder mark — founding resident
    '-': -10, "'": -11, '"': -12, '(': -13, ')': -14,
})
ANSWER_ORD, IDEA_ORD, PLACEHOLDER_ORD = -7, -8, -9

# reverse: ordinal → representative character (upper-case for letters)
_FROM_ORDINAL = {}
for _ch, _o in ORDINAL.items():
    _FROM_ORDINAL.setdefault(_o, _ch)
_FROM_ORDINAL[IDEA_ORD] = '⸮?'


def _assign_positions(words: list) -> list:
    return [set_position(w, i) for i, w in enumerate(words)]


def text_to_words(text: str, strict: bool = True) -> list:
    """Projection utility for interop (NOT the kept original). strict=True
    (default): an unknown character is a loud error — anything that PERSISTS
    uses strict. strict=False (renderer path): unknown → the ~ placeholder."""
    words = []
    for ch in text:
        if 'A' <= ch <= 'Z':
            words.append(make_glyph(ORDINAL[ch], +1))
        elif 'a' <= ch <= 'z':
            words.append(make_glyph(ORDINAL[ch.upper()], -1))
        elif ch in ORDINAL:
            words.append(make_glyph(ORDINAL[ch], 0))
        elif not strict:
            words.append(make_glyph(PLACEHOLDER_ORD, 0))
        else:
            raise GlyphError(f'no glyph for {ch!r} (strict); '
                             f'use strict=False for the ~ placeholder')
    return _assign_positions(words)


def words_to_text(words: list) -> str:
    out = []
    for w in words:
        o, case = parse_glyph(w)
        ch = _FROM_ORDINAL.get(o)
        if ch is None:
            raise GlyphError(f'ordinal {o} has no character in the house table')
        if 'A' <= ch <= 'Z' and case == -1:
            ch = ch.lower()
        out.append(ch)
    return ''.join(out)


def describe(word: int) -> dict:
    """Single source of truth for a native-plane word's payload — what the
    generic decode_word delegates to (CF5 ruling 2). Never raises."""
    if is_literal(word):
        return {'mode': 'literal', 'value': literal_value(word)}
    try:
        ordinal, case = parse_glyph(word)
    except GlyphError:
        return {'mode': '?'}
    try:
        char = words_to_text([word])
    except GlyphError:
        char = None
    return {'mode': 'text', 'ordinal': ordinal, 'case': case,
            'position': get_position(word), 'font': get_font(word),
            'char': char}
