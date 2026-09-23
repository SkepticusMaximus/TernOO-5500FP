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
              v03 DATA_STRING constant now mirrors this (+1,−1) after the
              housekeeping correction, see widget_lib.py:620]
    T19     : encoding plane      +1 native (== STRING_TERNARY)
    T18     : mode                0 text | +1/−1 signed numeric literal
    --- payload, TEXT mode (RULED relayout 23-09, Q5+Q6) ---
    The tribbles keep their residence names; their contents moved:
    T17..T12 : X   identity — T17 case (+1 up / −1 low / 0 caseless);
                   T16..T12 signed ordinal (0 = null/no-character)
    T11..T6  : Y   font registry index (0 = inherit house font)
    T5..T0   : Z   colour cube — R T5..T4, G T3..T2, B T1..T0
                   (0 = inherit ink; LED palette = higher trit of each
                   pair, an exact subset of the fine cube)
    Position is NOT in the word: it belongs to the container (order in
    the stream/span) — the King X deposition, chair's ruling.
    --- payload, LITERAL mode ---
    T17..T0  : magnitude (sign = T18); range ±193,710,244

Date: 2026-07-08, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import os
import unicodedata
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

# absolute trit positions (T-index) — RULED layout, 23-09 (Q5+Q6):
# X vacated (position is the container's — King X deposed); identity
# leftmost so the null check greets the reader first; colour takes the
# freed tribble. Reads identity → font → colour.
POS_MODE = 18                            # T18 (in the qualifier field)
# The three payload tribbles keep their RESIDENCE names X, Y, Z
# (captain's convention) — it is their CONTENTS that moved (Q5+Q6):
#   X (T17..T12) identity · Y (T11..T6) font · Z (T5..T0) colour
POS_CASE = 17                            # T17      case trit (in X)
ORD_LSB, ORD_WIDTH = 12, 5               # T12..T16 signed ordinal (in X)
X_LSB, X_WIDTH = 12, 6                   # X tribble: identity (case+ordinal)
Y_LSB, Y_WIDTH = 6, 6                    # Y tribble: font index (0 = inherit)
Z_LSB, Z_WIDTH = 0, 6                    # Z tribble: colour cube (0 = inherit)
PAY_LSB, PAY_WIDTH = 0, 18               # T0..T17  literal magnitude

# colour cube pins (ruled): R = T5..T4, G = T3..T2, B = T1..T0; the
# 27-colour LED palette reads the HIGHER trit of each pair (T5,T3,T1)
# so coarse is an EXACT SUBSET of fine.
COL_R_LSB, COL_G_LSB, COL_B_LSB = 4, 2, 0   # within Z
CHAN_MAX = 4                             # 2 trits/channel: ±4, 9 levels

ORD_MAX = (3 ** ORD_WIDTH - 1) // 2      # 121
COL_MAX = (3 ** Z_WIDTH - 1) // 2        # 364 (full-cube field value)
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

def make_glyph(ordinal: int, case: int = 0, font: int = 0,
               colour: int = 0) -> int:
    """A text character. ordinal 0 is null/no-character and is rejected;
    case is +1 upper / −1 lower / 0 caseless. Z (font) and C (colour)
    default to 0 = inherit. Position is NOT here — it belongs to the
    container (Q5, King X deposed)."""
    if ordinal == 0:
        raise GlyphError('ordinal 0 is null/no-character — not a glyph')
    if not -ORD_MAX <= ordinal <= ORD_MAX:
        raise GlyphError(f'ordinal {ordinal} out of range ±{ORD_MAX}')
    if case not in (-1, 0, 1):
        raise GlyphError(f'case {case} must be +1 / 0 / −1')
    if not -COL_MAX <= colour <= COL_MAX:
        raise GlyphError(f'colour {colour} out of range ±{COL_MAX}')
    qual = V._data_qualifier(GLYPH_T21, GLYPH_T20, NATIVE_PLANE, 0)  # text mode
    w = V._make_word(PRIMARY_DATA, qual, 0)
    w = V.set_field(w, ORD_LSB, ORD_WIDTH, ordinal)
    w = V.set_trit(w, POS_CASE, case)
    w = V.set_field(w, Y_LSB, Y_WIDTH, font)
    w = V.set_field(w, Z_LSB, Z_WIDTH, colour)
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


def get_font(word: int) -> int:
    _require_text(word)
    return V.get_field(word, Y_LSB, Y_WIDTH)


def get_colour(word: int) -> int:
    _require_text(word)
    return V.get_field(word, Z_LSB, Z_WIDTH)


def set_colour(word: int, colour: int) -> int:
    _require_text(word)
    if not -COL_MAX <= colour <= COL_MAX:
        raise GlyphError(f'colour {colour} out of range ±{COL_MAX}')
    return V.set_field(word, Z_LSB, Z_WIDTH, colour)


def colour_rgb(r: int, g: int, b: int) -> int:
    """Cube field value from per-channel levels (each ±4, 9 levels)."""
    for ch, nm in ((r, 'R'), (g, 'G'), (b, 'B')):
        if not -CHAN_MAX <= ch <= CHAN_MAX:
            raise GlyphError(f'{nm} {ch} out of range ±{CHAN_MAX}')
    return r * 3 ** COL_R_LSB + g * 3 ** COL_G_LSB + b * 3 ** COL_B_LSB


def colour_channels(colour: int):
    """(r, g, b) per-channel levels of a cube field value."""
    t = V.to_trits(colour, Z_WIDTH)
    return (t[COL_R_LSB] + 3 * t[COL_R_LSB + 1],
            t[COL_G_LSB] + 3 * t[COL_G_LSB + 1],
            t[COL_B_LSB] + 3 * t[COL_B_LSB + 1])


def led_colour(r: int, g: int, b: int) -> int:
    """The 27-colour traffic-light palette: one trit per channel
    (−/0/+ = off/half/full), written to the HIGHER trit of each pair —
    an EXACT SUBSET of the fine cube (ruled pin b)."""
    for ch, nm in ((r, 'R'), (g, 'G'), (b, 'B')):
        if ch not in (-1, 0, 1):
            raise GlyphError(f'LED {nm} {ch} must be +1 / 0 / −1')
    return colour_rgb(r * 3, g * 3, b * 3)


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
        V.get_field(b, ORD_LSB, ORD_WIDTH + 1)   # T12..T17: ordinal+case


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
        words.append(make_glyph(ORDINAL[ch]))     # digit chars, ordinals 1..10
    return _assign_positions(words)


# ═══════════════════════════════════════════════════════════════════════════
# THE SEED ORDINAL TABLE — RULED by the captain, 23-09-2026 (glyph-plane
# closure, carried as CF5-Submit-2026-09-23_200400). Digits-first, null
# preserved at 0; the NEGATIVE half of the ordinal (−1..−121) is RESERVED
# UNUSED — a free second class if ever needed, no trits carved. The table
# grows in the positive band above 38 (a SEED, not stone). 120 = unknown.
# ═══════════════════════════════════════════════════════════════════════════

ORDINAL = {}
for _d in range(10):
    ORDINAL[str(_d)] = 1 + _d             # digits '0'..'9' = 1..10 (value = Y−1)
for _i, _ch in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ', start=11):
    ORDINAL[_ch] = _i                     # letters = 11..36 (a=11; case via T11)
ORDINAL[' '] = 37                         # space — its own nonzero ordinal
# Punctuation — the growing positive seed (38+), per the ruling
ORDINAL.update({
    '.': 38, ',': 39, ':': 40, ';': 41, '!': 42, '?': 43,
    '⸮': 44,                              # answer mark
    # 45 idea mark (⸮?) — founding resident by captain's history
    '~': 46,                              # placeholder mark — founding resident
    '-': 47, "'": 48, '"': 49, '(': 50, ')': 51,
})
# Technical / MATH band continues the positive seed. So much of the
# curriculum is arithmetic that a well-appointed operator set earns its keep.
ORDINAL.update({
    '+': 52, '−': 53, '×': 54, '÷': 55, '=': 56, '≠': 57, '<': 58, '>': 59,
    '≤': 60, '≥': 61, '±': 62, '/': 63, '\\': 64, '*': 65, '^': 66, '%': 67,
    '·': 68, '_': 69, '|': 70, '#': 71, '[': 72, ']': 73, '{': 74, '}': 75,
    '→': 76, 'π': 77, '√': 78, 'Δ': 79, '°': 80, '∑': 81, '∫': 82, '∞': 83,
})
ANSWER_ORD, IDEA_ORD, PLACEHOLDER_ORD = 44, 45, 46
UNKNOWN_ORD = 120     # ruled: the ceiling marker for an unknown character
                      # (projection still renders ~ per R1 screen-truth)

# reverse: ordinal → representative character (upper-case for letters)
_FROM_ORDINAL = {}
for _ch, _o in ORDINAL.items():
    _FROM_ORDINAL.setdefault(_o, _ch)
_FROM_ORDINAL[IDEA_ORD] = '⸮?'


def _assign_positions(words: list) -> list:
    """Q5: position belongs to the container — order IS the string.
    Kept as identity for call-site compatibility."""
    return list(words)


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
            'font': get_font(word), 'colour': get_colour(word),
            'char': char}


# ═══════════════════════════════════════════════════════════════════════════
# House normalization + growth ledger (saddle-dispatch §1) — the SHARED
# projection front-end. Both the Translate tool and the live board path run
# through normalize_for_house so the two can never drift. Everything surviving
# normalization that still lacks a house glyph becomes ~ (R1) AND is recorded
# to the growth ledger — the O4 charter intake. Nothing silently vanishes.
# ═══════════════════════════════════════════════════════════════════════════

_NORMALIZE = {
    '‘': "'", '’': "'",          # curly single quotes → straight
    '“': '"', '”': '"',          # curly double quotes → straight
    '–': '-', '—': '-',          # en / em dash → hyphen
    # U+2212 MINUS is NOT folded: it renders its own math-band glyph
    # (ordinal 39); normalization must never defeat its own font (CF5).
    '…': '...',                        # ellipsis → three periods
    '⚠': '!',                       # warning sign → bang (board caveat lines
                                    # rendered ~ before this — screen-truth)
    ' ': ' ', ' ': ' ',           # NBSP / figure space → space
    ' ': ' ', ' ': ' ',           # thin / narrow-NBSP → space
}


def normalize_for_house(text: str) -> str:
    """Fold common non-house Unicode toward house-representable forms. Explicit
    map for curly quotes / dashes / ellipsis / exotic spaces; accented Latin
    strips to its base letter via NFKD. Pure; shared by tool and live path."""
    out = []
    for ch in text:
        if ch in _NORMALIZE:
            out.append(_NORMALIZE[ch])
            continue
        base = ''.join(c for c in unicodedata.normalize('NFKD', ch)
                       if not unicodedata.combining(c))
        out.append(base if base else ch)
    return ''.join(out)


def house_representable(ch: str) -> bool:
    """Does the house font have a glyph for this single character?"""
    return ch == '\n' or ch in ORDINAL or ('A' <= ch.upper() <= 'Z')


GROWTH_LEDGER = {}          # original char → count of times it hit ~ (O4 feed)


def to_house_words(text: str, record: bool = True) -> list:
    """The shared entry point: normalize, then project to glyph words
    (strict=False → ~ on the unrepresentable). Records each ORIGINAL char that
    still lacks a house glyph, by its original identity (saddle §1)."""
    if record:
        for ch in text:
            if any(not house_representable(c) for c in normalize_for_house(ch)):
                GROWTH_LEDGER[ch] = GROWTH_LEDGER.get(ch, 0) + 1
    return text_to_words(normalize_for_house(text), strict=False)
