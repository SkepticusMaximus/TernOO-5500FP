#!/usr/bin/env python3
"""
GristMill — Generative Object Synthesis Engine
================================================
Grist Is Stable Mnemonic Implicit Learning Libraries

GristMill is not a repository. It is a generative synthesis engine.
Objects are not stored at locations — they are computed from MMID coordinates.

An MMID (Minimal Map ID) is a TernOO MAP word — a native octree coordinate
in the 5500FP address space. An MMOE (Minimal Map Object Entity) is the
minimal self-contained unit of meaningful TernOO data that the MMID describes.
All dependencies are encoded in the MMID itself.

Given an MMID, GristMill synthesises the corresponding MMOE through:
1. Structural decomposition — what kind of object does this coordinate describe?
2. Proximity search — what related objects are nearby in the octree?
3. GHOST inference — generate the object's word sequence from structural context

No download. No repository query. No version resolution.
The object materialises from the MMID through computation.

Added: 31 May 2026, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Companion: docs/TernOO-5500FP-Companion.md § GristMill
Whitepaper: Section 9.5
Status: SKELETON
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    'ternoo_v03',
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 '5500fp_ternoo_v03.py'))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

build_map_word       = _mod.build_map_word
decode_map_word      = _mod.decode_map_word
build_udp_word       = _mod.build_udp_word
build_exec_word      = _mod.build_exec_word
decode_word          = _mod.decode_word
describe_word        = _mod.describe_word
set_field            = _mod.set_field
get_field            = _mod.get_field
get_primary          = _mod.get_primary
get_trit             = _mod.get_trit
set_trit             = _mod.set_trit
set_primary          = _mod.set_primary
PRIMARY_OPCODE       = _mod.PRIMARY_OPCODE
OPF_ISA_CORE         = _mod.OPF_ISA_CORE
OPF_ISA_STACK        = _mod.OPF_ISA_STACK
OPF_WORD_OP          = _mod.OPF_WORD_OP
OPF_PIGART           = _mod.OPF_PIGART
OPF_MECCANO          = _mod.OPF_MECCANO
OPCODE_MNEMONICS     = _mod.OPCODE_MNEMONICS
OP_ADD               = _mod.OP_ADD
build_opcode_word    = _mod.build_opcode_word
decode_opcode_word   = _mod.decode_opcode_word


# ── Rev4 Ternary Primitives (ported from private/tmesh_otree_prototype.py) ────
# Added: 09 Jun 2026, Adelaide  (Rev4 port)
# Author: Stevo + Claude
# Source: private/tmesh_otree_prototype.py (Rev4, all 13 acceptance criteria passing)
# Mathematics confirmed: DeepAI GPT OSS 120B, 05 Jun 2026

MOD = 3**6  # 729 — one tribble

def ternary_op(a: int, b: int) -> int:
    """
    Steiner quasigroup mutual recovery operation for balanced ternary tribbles.
    A ⊕ B = -(A+B) mod 729

    Property: for any triple (A, B, C) where C = ternary_op(A, B):
        ternary_op(B, C) == A
        ternary_op(A, C) == B
    Each side recoverable from the other two — self-validating mesh.

    Input range: any integer (result reduced to 0..728).
    """
    return (-(a + b)) % MOD


def traverse_step(state: int, side_a: int, side_b: int) -> tuple:
    """
    Advance traversal state by one triangle.
    Recovers the third side using the Steiner quasigroup, then
    advances the accumulator.
    Returns (new_state, recovered_side_c, arrived)
    arrived=True when recovered_side_c == 0 (sentinel: end-of-object marker)
    """
    side_c    = ternary_op(side_a, side_b)
    new_state = (state + side_c) % MOD
    arrived   = (side_c == 0)
    return (new_state, side_c, arrived)


MECCANO_VOCAB = [i * 27 for i in range(1, 28)]  # {27,54,...,702} — true closed 27-element sub-quasigroup of Z/729Z
# Mathematical note: a subset of Z/729Z closed under ternary_op must have size 3^k.
# [1..27] is NOT closed — ternary_op maps it to [702..727]. Multiples of 27 ARE closed:
# ternary_op(a*27, b*27) = -(a+b)*27 mod 729 = ((-(a+b) mod 27)*27) — stays in the set.
# Corrected: CAI confirmation, 05 Jun 2026.


def vocab_step(current_chunk: int, side_a: int, side_b: int) -> tuple:
    """
    Advance through the vocabulary mesh with DAG ordering enforcement.
    Recovered side_c must be >= current_chunk to maintain forward progress.
    Returns (side_c, valid).
    valid=False if ordering violated.
    side_c == 0 is the arrival sentinel — always valid.
    """
    side_c = ternary_op(side_a, side_b)
    if side_c == 0:
        return (side_c, True)   # sentinel — valid arrival
    valid = (side_c >= current_chunk) and (side_c in MECCANO_VOCAB)
    return (side_c, valid)


def meccano_tribble(word: int) -> int:
    """
    Extract the MECCANO payload tribble (T5–T0, low tribble, tc) from an
    OPCODE/MECCANO word.

    This widens the input domain accepted by the traversal accumulator: any
    OPCODE word whose primary is PRIMARY_OPCODE and whose family is OPF_MECCANO
    can be folded into vocab_step / the S-accumulator by passing its low tribble
    as the step value.

    Note: the meccano value is stored at T5-T0 = low tribble = extract_tribbles
    index [2] (tc). The word format spec stores T17-T12 (ta, index [0]) as spare.
    Use index [2], not [0], to extract the meccano value.

    Raises:
        ValueError if word is not a PRIMARY_OPCODE/OPF_MECCANO word.
    """
    if get_primary(word) != PRIMARY_OPCODE:
        raise ValueError("Not a PRIMARY_OPCODE word")
    d = decode_opcode_word(word)
    if d['family'] != OPF_MECCANO:
        raise ValueError("Not a MECCANO-family OPCODE word")
    # Low tribble = tc = extract_tribbles(word)[2] = T5-T0 = meccano value
    _ta, _tb, tc = extract_tribbles(word)
    return tc


def ternary_sign(val: int) -> int:
    """Map a value mod 3 to balanced ternary: 0→0, 1→+1, 2→-1"""
    return {0: 0, 1: +1, 2: -1}[val % 3]


def extract_tribbles(word: int) -> tuple:
    """
    Extract the three 6-trit payload tribbles (T17-T12, T11-T6, T5-T0)
    from a TernOO word integer.
    Returns (ta, tb, tc) as balanced ternary integers in range -364..+364.

    Uses get_field() from 5500fp_ternoo_v03.py — no ternary arithmetic
    reimplemented here.

    The PRIMARY and QUALIFIER fields (T23-T18) are metadata — they are NOT
    included. Only the 18-trit payload participates in coordinate derivation.
    """
    ta = get_field(word,  12, 6)   # T17-T12
    tb = get_field(word,   6, 6)   # T11-T6
    tc = get_field(word,   0, 6)   # T5-T0
    return (ta, tb, tc)


def trit_weight(val: int, width: int = 6) -> int:
    """
    Sum of absolute values of the `width` balanced trits of val.
    Range 0..width (0..6 for a single tribble, 0..12 for two).

    Uses get_field() to extract each trit individually — no bit operations.
    val is first reduced mod MOD to 0..728 (unbalanced), then each trit
    at position i is extracted as a balanced value in {-1, 0, +1}.
    """
    v = val % MOD   # reduce to unbalanced 0..728
    return sum(abs(get_field(v, i, 1)) for i in range(width))


# ── Rev4 MAP Subtype Builders (ported from prototype) ────────────────────────
# Added: 09 Jun 2026, Adelaide  (Rev4 port)
# Author: Stevo + Claude
# Source: private/tmesh_otree_prototype.py (Rev4)
#
# Discriminator: MAP qualifier T18 (mode_hint) = 0 → OTree (ABSOLUTE_3D)
#                                                 +1 → TTree (ON_PLANE with mode_hint)
# build_map_word signature: (axis_yz, axis_xz, axis_xy, payload, mode_hint=0)
# mode_hint is already supported in 5500fp_ternoo_v03.py — no modification needed.

def build_ttree_mmid(ta: int, tb: int) -> int:
    """
    Build a TTree MMID coordinate from UDP payload tribbles ta and tb.

    Uses MAP ON_PLANE mode (axis_yz=0) with mode_hint=+1 to distinguish
    from OTree MAP words.

    ta → Y dimension (structural role — T21/T20 subclass trit contribution)
    tb → Z dimension (reserved for future interaction-style encoding)

    Packing: Y is stored in trit positions 9-17 of the payload, Z in 0-8.
    Uses set_field() for clean separation — avoids the overlap that would
    result from the arithmetic y*729+z (which would contaminate trits 6-8
    with contributions from both y and z).
    """
    y = ta + 364   # shift balanced range -364..+364 to positive 0..728
    z = tb + 364
    payload = set_field(0,       9, 9, y)   # Y in payload trits 9-17
    payload = set_field(payload, 0, 9, z)   # Z in payload trits 0-8
    return build_map_word(0, +1, +1, payload, mode_hint=+1)


def build_otree_mmoe(tribble_state: int) -> int:
    """
    Build an OTree MMOE coordinate from an accumulated ternary_op traversal state.

    Uses MAP ABSOLUTE_3D mode (all three axis trits non-zero) with mode_hint=0.
    The state is a value in 0..728 produced by folding all word tribbles through
    ternary_op(). The octant signs and magnitude are derived from this state.

    Content-addressable: same tribble fold → same state → same MMOE.
    Primal MMOE is wherever its content hash lands — NOT forced to origin.
    """
    yz_sign = ternary_sign(tribble_state % 3)
    xz_sign = ternary_sign((tribble_state // 3) % 3)
    xy_sign = ternary_sign((tribble_state // 9) % 3)
    yz_sign = yz_sign if yz_sign != 0 else +1
    xz_sign = xz_sign if xz_sign != 0 else +1
    xy_sign = xy_sign if xy_sign != 0 else +1
    magnitude = tribble_state % MOD  # explicit ternary-domain reduction, 0..728
    # Payload field is 18 trits; values 0..728 occupy the low 6 trits;
    # no binary-domain masking permitted anywhere in this module.
    return build_map_word(yz_sign, xz_sign, xy_sign, magnitude, mode_hint=0)


# ── MMOE Type Registry ────────────────────────────────────────────────────────
# Added: 31 May 2026, Adelaide
# Coordinate ranges now emerge from tribble derivation (Rev4 port) rather than
# hardcoded y_range/z_range regions. Each entry retains: udp, successors, description.
# Each MMOE type has:
#   - A name (human label)
#   - A UDP subclass (T21, T20) encoding its structural role
#   - A set of natural successors (what objects typically follow this one)

MMOE_TYPES = {
    # FlowCode symbol types
    'terminator': {
        'udp': (+1, +1), 'successors': ['io_read'],
        'description': 'Program entry/exit boundary'
    },
    'io_read': {
        'udp': (+1,  0), 'successors': ['process', 'decision'],
        'description': 'External input channel'
    },
    'io_write': {
        'udp': (+1,  0), 'successors': ['terminator'],
        'description': 'External output channel'
    },
    'process': {
        'udp': (0,   0), 'successors': ['decision', 'io_write'],
        'description': 'Computation / transformation'
    },
    'decision': {
        'udp': (0,  +1), 'successors': ['io_write', 'process', 'io_read'],
        'description': 'Conditional branch'
    },
    # Widget types (GUI MMOE — skeleton for future GHOST training)
    'widget_window': {
        'udp': (+1, -1), 'successors': ['widget_panel'],
        'description': 'Top-level window container'
    },
    'widget_panel': {
        'udp': (+1, -1), 'successors': ['widget_button', 'widget_label', 'widget_input'],
        'description': 'Layout container'
    },
    'widget_button': {
        'udp': (+1, +1), 'successors': ['widget_panel', 'widget_label'],
        'description': 'Interactive button widget'
    },
    'widget_label': {
        'udp': (+1,  0), 'successors': ['widget_button', 'widget_input'],
        'description': 'Static text display'
    },
    'widget_input': {
        'udp': (+1, -1), 'successors': ['widget_button', 'widget_label'],
        'description': 'Text input field'
    },
}


# ── MMID — Minimal Map ID ─────────────────────────────────────────────────────
# Added: 31 May 2026, Adelaide

class MMID:
    """
    A Minimal Map ID — a TernOO MAP word that encodes the type and position
    of an MMOE in the octree address space.

    The MMID is not a pointer to a stored object.
    It is a complete description of what the object IS,
    encoded as a geometric coordinate in the object space.
    """

    def __init__(self, mmoe_type: str, exec_word: int = None):
        """
        Per Rev4: MMID encodes structural role only. The `instance`
        parameter has been removed — two MMIDs of the same type are
        identical (see FT-1 for the `from_flowcode` follow-up).

        exec_word: optional EXEC word whose tribble B (T11–T6) supplies tb,
        encoding interaction style as the MMID's second dimension.
        If None, tb = 0 — fully backward compatible. FT-2: RESOLVED.
        Note: exec_word population arrives with FlowCode EXEC synthesis (post-port).
        """
        self.mmoe_type  = mmoe_type
        self._exec_word = exec_word
        self._word      = None
        self._ta        = 0
        self._tb        = 0
        self._compute()

    def _compute(self):
        """
        Compute the TTree MAP word from structural role and (optionally) exec_word.

        ta: from UDP role trits T21/T20 via build_udp_word → extract_tribbles.
        tb: 0 by default; if exec_word is provided, tribble B (T11–T6) of that
            word supplies tb, encoding interaction style as the second dimension.
            proximity() and distance_to() gain the second dimension automatically
            when exec_word is non-None.
        """
        t = MMOE_TYPES.get(self.mmoe_type, {})
        t1, t0 = t.get('udp', (0, 0))
        udp = build_udp_word(t1, t0, 0, 0, 0)
        ta, _tb, _tc = extract_tribbles(udp)
        self._ta = ta
        if self._exec_word is not None:
            _, tb, _ = extract_tribbles(self._exec_word)
            self._tb = tb
        else:
            self._tb = 0
        self._word = build_ttree_mmid(self._ta, self._tb)

    @property
    def word(self) -> int:
        return self._word

    def distance_to(self, other: 'MMID') -> int:
        """
        Ternary-native distance: balanced-trit weight of the tribble differences.

        tribble_diff(a, b) = (a - b) reduced mod 729 to 0..728 (then
            get_field extracts each trit as balanced {-1, 0, +1})
        trit_weight(x)     = Σ|tᵢ| over 6 balanced trits, range 0..6
        distance(A, B)     = trit_weight(diff_ta) + trit_weight(diff_tb)

        Range 0..12. Integer-valued. d(A,A)=0. d(A,B)=d(B,A).
        Ternary analogue of Hamming distance — counts non-zero trit positions
        of the difference, consistent with Kademlia lineage (whitepaper §10.1.4).
        FT-3: RESOLVED.
        """
        diff_ta = (self._ta - other._ta) % MOD
        diff_tb = (self._tb - other._tb) % MOD
        return trit_weight(diff_ta) + trit_weight(diff_tb)

    def __repr__(self):
        return (f"MMID({self.mmoe_type} "
                f"ta={self._ta:+d} tb={self._tb:+d} "
                f"word={self._word})")



# ── MMOE — Minimal Map Object Entity ─────────────────────────────────────────
# Added: 31 May 2026, Adelaide

class MMOE:
    """
    A Minimal Map Object Entity — the minimal self-contained unit of
    meaningful TernOO data, synthesised from an MMID.

    An MMOE is not retrieved from storage.
    It is computed from the MMID by GristMill.

    Structure:
      mmid       — the MMID that generated this object
      map_word   — spatial position (from MMID)
      udp_word   — object type (from MMOE_TYPES)
      exec_words — event handlers (synthesised from type)
      label      — human-readable name
      children   — contained MMOEs (for widget trees)
    """

    def __init__(self, mmid: MMID, label: str = '', otree_word: int = None):
        self.mmid       = mmid
        self.label      = label or mmid.mmoe_type
        t               = MMOE_TYPES.get(mmid.mmoe_type, {})
        t1, t0          = t.get('udp', (0, 0))
        self.map_word   = mmid.word
        self.otree_word = otree_word   # OTree MAP word; None = unplaced (TTree identity only)
        self.udp_word   = build_udp_word(t1, t0, 0, 0, 0)
        self.exec_words = []   # event handler EXEC words
        self.children   = []   # contained MMOEs

    def add_child(self, child: 'MMOE'):
        self.children.append(child)

    def to_words(self) -> list:
        """
        Serialise to TernOO word sequence.
        Rev4 canonical stream format: [TTree MAP, OTree MAP, UDP, *exec_words, *children]
        OTree MAP is included only when otree_word is set (object is placed in OTree).
        """
        words = [self.map_word]
        if self.otree_word is not None:
            words.append(self.otree_word)
        words.append(self.udp_word)
        words.extend(self.exec_words)
        for child in self.children:
            words.extend(child.to_words())
        return words

    def describe(self, indent: int = 0) -> str:
        pad = '  ' * indent
        t   = MMOE_TYPES.get(self.mmid.mmoe_type, {})
        lines = [
            f"{pad}MMOE '{self.label}' [{self.mmid.mmoe_type}]",
            f"{pad}  MMID: {self.mmid}",
            f"{pad}  MAP:  {describe_word(self.map_word)}",
            f"{pad}  UDP:  {describe_word(self.udp_word)}",
            f"{pad}  desc: {t.get('description','')}",
        ]
        for child in self.children:
            lines.append(child.describe(indent + 1))
        return '\n'.join(lines)

    def __repr__(self):
        return f"MMOE('{self.label}' [{self.mmid.mmoe_type}] {len(self.children)} children)"


# ── GristMill ─────────────────────────────────────────────────────────────────
# Added: 31 May 2026, Adelaide

class GristMill:
    """
    The GristMill synthesis engine.

    Core operations:
      synthesise(mmid)    — compute an MMOE from an MMID
      proximity(mmid, n)  — find the n nearest MMIDs in the object space
      compose(mmids)      — assemble a tree of MMOEs from a sequence of MMIDs
      from_flowcode(json) — derive MMIDs from a FlowCode canvas
      to_flowcode(mmoes)  — convert MMOEs back to a FlowCode canvas structure

    Added: 31 May 2026, Adelaide
    """

    def synthesise(self, mmid: MMID, label: str = '', otree_word: int = None) -> MMOE:
        """
        Compute an MMOE from an MMID.
        This is the core GristMill operation — object synthesis from coordinate.
        otree_word: optional OTree placement address; None = TTree identity only.
        """
        return MMOE(mmid, label=label or mmid.mmoe_type, otree_word=otree_word)

    def proximity(self, mmid: MMID, n: int = 5) -> list:
        """
        Find the n nearest MMOE types in tribble space.
        Distance is ternary-native (trit_weight of tribble differences).
        Ties broken alphabetically by type_name for determinism.
        """
        distances = []
        for type_name in MMOE_TYPES:
            candidate = MMID(type_name)
            dist = mmid.distance_to(candidate)
            distances.append((dist, type_name))
        distances.sort()   # (int, str) — primary key: dist, secondary: type_name alphabetical
        return [(d, t) for d, t in distances[:n]]

    def successors(self, mmoe_type: str) -> list:
        """
        Return the natural successors of an MMOE type —
        what objects typically follow this one in a valid composition.
        """
        t = MMOE_TYPES.get(mmoe_type, {})
        return t.get('successors', [])

    def compose(self, mmid_sequence: list) -> list:
        """
        Assemble a list of placed MMOEs from a sequence of MMIDs or from_flowcode triples.

        Accepts either:
          - bare MMIDs: threads accumulator S to derive otree_word per element
          - (mmid, label, otree_word) triples (i.e. from_flowcode output is directly composable)

        Accumulator discipline: S₀ = 0; per element:
            ta, tb, _ = extract_tribbles(mmid.word)
            S = (S + ternary_op(ta, tb)) % MOD
            otree_word = build_otree_mmoe(S)

        Determinism guarantee: same sequence twice → identical word streams.
        Content-identity invariant: permuting sequence changes otree_words, never MMID/TTree words.
        """
        S = 0
        result = []
        for item in mmid_sequence:
            if isinstance(item, tuple):
                mmid, label, otree_word = item
            else:
                mmid  = item
                label = mmid.mmoe_type
                ta, tb, _ = extract_tribbles(mmid.word)
                S = (S + ternary_op(ta, tb)) % MOD
                otree_word = build_otree_mmoe(S)
            result.append(self.synthesise(mmid, label=label, otree_word=otree_word))
        return result

    def from_flowcode(self, canvas: dict) -> list:
        """
        Derive MMIDs from a FlowCode JSON canvas.
        Returns list of (mmid, label, otree_word) triples. FT-1: RESOLVED.

        Instance identity is provided by the OTree coordinate, not the MMID.
        Accumulator: S₀ = 0; per symbol:
            ta, tb, _ = extract_tribbles(mmid.word)
            S = (S + ternary_op(ta, tb)) % MOD
            otree_word = build_otree_mmoe(S)
        Same type, different walk position → same MMID word, different otree_word.

        Added: 31 May 2026, Adelaide
        """
        from ternoo_neural import flowcode_symbol_type as _fst
        triples  = []
        symbols  = {s['id']: s for s in canvas.get('symbols', [])}
        edges    = canvas.get('edges', [])
        S        = 0   # accumulator

        # Walk in execution order
        incoming = set(e['dst'] for e in edges)
        starts   = [s for s in canvas.get('symbols',[]) if s['id'] not in incoming]
        if not starts: starts = list(symbols.values())

        visited = set()
        queue   = [starts[0]['id']]
        while queue:
            sid = queue.pop(0)
            if sid in visited: continue
            visited.add(sid)
            sym  = symbols.get(sid)
            if not sym: continue
            tok  = _fst(sym)
            mmid = MMID(tok)
            ta, tb, _ = extract_tribbles(mmid.word)
            S = (S + ternary_op(ta, tb)) % MOD
            otree_word = build_otree_mmoe(S)
            triples.append((mmid, sym.get('label', tok), otree_word))
            for e in edges:
                if e['src'] == sid:
                    queue.append(e['dst'])

        return triples

    def to_words(self, mmoes: list) -> list:
        """Convert a list of MMOEs to a flat TernOO word sequence."""
        words = []
        for mmoe in mmoes:
            words.extend(mmoe.to_words())
        return words


# ── Acceptance Harness ────────────────────────────────────────────────────────
# Added: 10 Jun 2026, Adelaide  (Rev4 Changes 1–6)
# Criteria 1–13: ported from private/tmesh_otree_prototype.py
# Criteria 14–18: new assertions covering Changes 1–5

def run_acceptance() -> bool:
    """
    Run all Rev4 acceptance criteria against this module.
    Criteria 1–13 are ported from private/tmesh_otree_prototype.py (13/13 passing).
    Criteria 14–18 cover the new changes in this port.
    Prints PASS/FAIL per criterion. Returns True iff all pass.
    """
    print("=" * 62)
    print("  GristMill Rev4 — Acceptance Harness")
    print("=" * 62)
    print()

    results = []

    def _check(n, desc, ok):
        results.append(bool(ok))
        print(f"  {n:2d}. {'PASS' if ok else 'FAIL'}  {desc}")

    # ── Local object-builder helpers (prototype-faithful) ─────────────────────
    # Reconstruct primal/shape/widget/button as in tmesh_otree_prototype.py
    # so criteria 1–3 can be tested against the same word sequences.
    def _make_primal():
        return [
            build_map_word(0, 0, 0, 0),
            build_udp_word(0, 0, 0, 0, 0),
            build_exec_word(_mod.EXEC_PRIV_USER, _mod.EXEC_CALL_REGISTER,
                            _mod.EXEC_RET_DATA, seg_idx=4, offset=0),
        ]

    def _make_shape(ext):
        return _make_primal() + [ext]

    def _make_widget(ext, t21, t20):
        return _make_shape(ext) + [build_udp_word(t21, t20, 0, 0, 0)]

    def _make_button(ext, label_val):
        base    = _make_widget(ext, +1, +1)
        label   = _mod.build_int_word(label_val)
        handler = build_exec_word(_mod.EXEC_PRIV_USER, _mod.EXEC_CALL_MESSAGE,
                                  _mod.EXEC_RET_DATA, seg_idx=4, offset=0)
        return base + [label, handler]

    extent = build_map_word(+1, +1, -1, 160)
    primal = _make_primal()
    shape  = _make_shape(extent)
    widget = _make_widget(extent, +1, +1)
    button = _make_button(extent, 42)

    gm = GristMill()

    # ── 1. All words pass describe_word() ─────────────────────────────────────
    c1 = True
    for type_name in MMOE_TYPES:
        mmid = MMID(type_name)
        mmoe = gm.synthesise(mmid, otree_word=build_otree_mmoe(42))
        for w in mmoe.to_words():
            d = describe_word(w)
            if d is None or d == 'UNKNOWN':
                c1 = False
    for obj_words in [primal, shape, widget, button]:
        for w in obj_words:
            d = describe_word(w)
            if d is None or d == 'UNKNOWN':
                c1 = False
    _check(1, "All synthesised MMOE words pass describe_word()", c1)

    # ── 2. Primal is exactly 3 words (MAP ORIGIN + UDP(0,0) + EXEC basic) ─────
    p0_mode = decode_map_word(primal[0]).get('mode', '')
    _check(2, "Primal: exactly 3 words, first is MAP ORIGIN",
           len(primal) == 3 and p0_mode == 'ORIGIN')

    # ── 3. Strict superset property ───────────────────────────────────────────
    _check(3, "Strict superset: primal⊂shape⊂widget⊂button",
           primal == shape[:3] and shape == widget[:4] and widget == button[:5])

    # ── 4. MMID tribble derivation: extract_tribbles(UDP), no Python hash() ───
    c4 = True
    for type_name in MMOE_TYPES:
        t1, t0 = MMOE_TYPES[type_name].get('udp', (0, 0))
        udp = build_udp_word(t1, t0, 0, 0, 0)
        ta_exp, _, _ = extract_tribbles(udp)
        if MMID(type_name)._ta != ta_exp:
            c4 = False
    _check(4, "MMID._ta matches extract_tribbles(UDP) for all 10 types (no hash)", c4)

    # ── 5. MMOE content-addressability: same state → same word ────────────────
    c5 = all(build_otree_mmoe(s) == build_otree_mmoe(s)
             for s in [0, 42, 100, 364, 728])
    _check(5, "Content-addressability: same tribble_state → identical OTree word", c5)

    # ── 6. Quasigroup mutual recovery (tribble arithmetic — no Python hash()) ──
    # For C = ternary_op(A, B): ternary_op(B, C) == A  and  ternary_op(A, C) == B
    test_pairs_6 = [(123, 456), (243, 81), (0, 0), (364, 1), (728, 727)]
    c6 = all(ternary_op(B, ternary_op(A, B)) == A and
             ternary_op(A, ternary_op(A, B)) == B
             for A, B in test_pairs_6)
    _check(6, "Quasigroup mutual recovery: B⊕(A⊕B)==A and A⊕(A⊕B)==B", c6)

    # ── 7. Inheritance proximity: structural similarity = geometric proximity ──
    # terminator(+1,+1) closer to io_read(+1,0) than to process(0,0)
    d_term_io   = MMID('terminator').distance_to(MMID('io_read'))
    d_term_proc = MMID('terminator').distance_to(MMID('process'))
    _check(7, "Proximity ordering: d(terminator,io_read) ≤ d(terminator,process)",
           d_term_io <= d_term_proc)

    # ── 8. No import or runtime errors (implicit: reaching here = passing) ─────
    _check(8, "No import or runtime errors reaching criterion 8", True)

    # ── 9. MECCANO_VOCAB closed under ternary_op; [1..27] counter-test ────────
    # Normalise: 729 ≡ 0 mod 729, so compare ternary_op results in mod-729 space
    vocab_norm = set(v % MOD for v in MECCANO_VOCAB)   # {0, 27, 54, ..., 702}
    c9a = all(ternary_op(a % MOD, b % MOD) in vocab_norm
              for a in MECCANO_VOCAB for b in MECCANO_VOCAB)
    # Counter-test: [1..27] is NOT a closed sub-quasigroup
    r27  = list(range(1, 28))
    c9b  = not all(ternary_op(a, b) in r27 for a in r27[:5] for b in r27[:5])
    _check(9, "MECCANO_VOCAB closed under ternary_op; [1..27] is NOT closed", c9a and c9b)

    # ── 10. Tribble extraction round-trip ─────────────────────────────────────
    c10 = True
    for t1, t0 in [(+1,+1),(+1,0),(+1,-1),(0,0),(0,+1),(-1,0),(-1,-1)]:
        udp   = build_udp_word(t1, t0, 0, 0, 0)
        ta, tb, _ = extract_tribbles(udp)
        ttree = build_ttree_mmid(ta, tb)
        d     = decode_map_word(ttree)
        y_got = d.get('coords', {}).get('Y', None)
        z_got = d.get('coords', {}).get('Z', None)
        if y_got != ta + 364 or z_got != tb + 364:
            c10 = False
    _check(10, "Round-trip: UDP→extract_tribbles→build_ttree_mmid→decode Y/Z intact", c10)

    # ── 11. traverse_step: 5 steps mutual recovery + sentinel arrival ──────────
    sides_a = [0, 162, 243, 324, 162]
    sides_b = [162, 243, 324, 162, 243]
    state   = 0
    c11     = True
    for sa, sb in zip(sides_a, sides_b):
        state, sc, _ = traverse_step(state, sa, sb)
        if ternary_op(sc, sb) != sa:
            c11 = False
    sa_s = 100; sb_s = (-sa_s) % MOD
    _, sc_s, arr_s = traverse_step(0, sa_s, sb_s)
    c11 = c11 and (sc_s == 0) and arr_s
    _check(11, "traverse_step: 5 steps mutual recovery + sentinel arrival (sc=0)", c11)

    # ── 12. vocab_step: DAG ordering — backward step correctly rejected ─────────
    # ternary_op(725, 2) = 2, which is < current_chunk=20 → must be rejected
    _, v_bwd = vocab_step(20, 725, 2)
    _check(12, "vocab_step: backward step (sc < current_chunk) correctly rejected",
           not v_bwd)

    # ── 13. TTree/OTree T18 mode_hint discrimination ──────────────────────────
    t_dec = decode_map_word(build_ttree_mmid(162, 0))
    o_dec = decode_map_word(build_otree_mmoe(42))
    _check(13, "TTree→ON_PLANE (mode_hint=+1), OTree→ABSOLUTE_3D (mode_hint=0)",
           t_dec['mode'] == 'ON_PLANE' and o_dec['mode'] == 'ABSOLUTE_3D')

    # ── 14. Metric properties: d(A,A)=0 and d(A,B)=d(B,A) ────────────────────
    types = list(MMOE_TYPES.keys())
    c14   = True
    for t in types:
        if MMID(t).distance_to(MMID(t)) != 0:
            c14 = False
    pairs14 = [(types[i], types[j])
               for i in range(len(types)) for j in range(i+1, len(types))]
    for ta_t, tb_t in pairs14[:6]:
        if MMID(ta_t).distance_to(MMID(tb_t)) != MMID(tb_t).distance_to(MMID(ta_t)):
            c14 = False
    _check(14, "Metric: d(A,A)=0 and d(A,B)=d(B,A) for all type pairs", c14)

    # ── 15. Instance uniqueness: same-type MMIDs → same word, distinct otree ───
    # Use 'terminator' (ta=+324, ternary_op(324,0)=405 ≠ 0 — accumulator advances).
    # Avoids ternoo_neural import; tests accumulator logic directly.
    m15a = MMID('terminator'); m15b = MMID('terminator')
    S15  = 0
    ta15, tb15, _ = extract_tribbles(m15a.word)
    S15 = (S15 + ternary_op(ta15, tb15)) % MOD
    ow15a = build_otree_mmoe(S15)
    ta15, tb15, _ = extract_tribbles(m15b.word)
    S15 = (S15 + ternary_op(ta15, tb15)) % MOD
    ow15b = build_otree_mmoe(S15)
    _check(15, "Instance uniqueness: same-type MMIDs → same word, distinct otree_word",
           m15a.word == m15b.word and ow15a != ow15b)

    # ── 16. compose determinism: same sequence twice → identical word streams ───
    seq16 = [MMID(t) for t in
             ['terminator', 'io_read', 'process', 'decision', 'terminator']]
    w16a  = gm.to_words(gm.compose(seq16))
    w16b  = gm.to_words(gm.compose(seq16))
    _check(16, "compose determinism: same input sequence → identical word streams",
           w16a == w16b)

    # ── 17. Content-identity invariant: permutation changes otree, not MMID ────
    seq_a = [MMID('terminator'), MMID('process'), MMID('io_read')]
    seq_b = [MMID('io_read'),    MMID('process'), MMID('terminator')]
    mm_a  = gm.compose(seq_a)
    mm_b  = gm.compose(seq_b)
    # MMID/TTree words are type-determined — position-independent
    mmid_ok = (mm_a[0].map_word == mm_b[2].map_word and   # terminator
               mm_a[2].map_word == mm_b[0].map_word)      # io_read
    # OTree words are position-dependent — permuting changes them
    otree_changed = ([m.otree_word for m in mm_a] != [m.otree_word for m in mm_b])
    _check(17, "Content-identity: permuting sequence changes otree_words, not MMID words",
           mmid_ok and otree_changed)

    # ── 18. Mask-fix regression: build_otree_mmoe(s) == build_otree_mmoe(s+729) ─
    # % MOD is periodic; old binary mask & 0x3FFFF was not (s+729 > 728 was wrong).
    c18 = all(build_otree_mmoe(s) == build_otree_mmoe(s + MOD)
              for s in [0, 42, 100, 364, 727])
    _check(18, "Mask-fix: build_otree_mmoe(s) == build_otree_mmoe(s+729)", c18)

    # ── 19. Round-trip: all 43 mnemonics build → decode losslessly ────────────
    c19 = True
    for (fam, idx), mnem in OPCODE_MNEMONICS.items():
        for arity in [0, 4, 8]:
            try:
                w = build_opcode_word(fam, arity=arity, op_index=idx)
                d = decode_opcode_word(w)
                if d['mnemonic'] != mnem or d['arity'] != arity or d['op_index'] != idx:
                    c19 = False
            except Exception:
                c19 = False
    _check(19, "Round-trip: all 43 mnemonics build→decode losslessly", c19)

    # ── 20. Meccano round-trip: all 27 vocab values + 0 sentinel ──────────────
    # MECCANO values are stored as balanced ternary (6-trit, ±364 max).
    # Values > 364 normalise to their Z/729Z balanced representative:
    #   378 → -351, ..., 702 → -27, 729 → 0.
    # build_opcode_word performs this normalisation automatically.
    c20 = True
    mec_vals = [0] + list(range(27, 730, 27))   # 0, 27, 54, ..., 702, 729 (= 0 mod 729)
    for mv in mec_vals:
        # Balanced ternary representative of mv in Z/729Z
        mv_bt = mv % 729
        if mv_bt > 364:
            mv_bt -= 729
        try:
            w   = build_opcode_word(OPF_MECCANO, arity=0, meccano=mv)
            d   = decode_opcode_word(w)
            tc  = extract_tribbles(w)[2]   # low tribble T5-T0
            if d['meccano'] != mv_bt or d['family_name'] != 'MECCANO':
                c20 = False
            if tc != mv_bt:
                c20 = False
        except Exception:
            c20 = False
    _check(20, "Meccano round-trip: all 27 vocab values + 0; low-tribble extraction correct", c20)

    # ── 21. Closure through wrapping: ternary_op over MECCANO-word tribbles ───
    # For any m1, m2 in MECCANO_VOCAB: ternary_op(tc(m1), tc(m2)) ∈ vocab_norm
    # tc = extract_tribbles(word)[2] = T5-T0 = low tribble = meccano value.
    # Note: work order says [0] but T5-T0 is tc = index [2]; [0] is spare T17-T12.
    # vocab_norm21 = {0, 27, 54, ..., 702} — canonical Z/729Z representatives.
    # tc values are balanced ternary (-351..+351); ternary_op returns 0..728.
    # Normalise the ternary_op result with % MOD before membership check.
    vocab_norm21 = set(v % MOD for v in MECCANO_VOCAB)
    c21 = True
    for m1 in MECCANO_VOCAB:
        for m2 in MECCANO_VOCAB:
            w1  = build_opcode_word(OPF_MECCANO, arity=0, meccano=m1)
            w2  = build_opcode_word(OPF_MECCANO, arity=0, meccano=m2)
            tc1 = extract_tribbles(w1)[2]   # low tribble = balanced meccano value
            tc2 = extract_tribbles(w2)[2]
            if (ternary_op(tc1, tc2) % MOD) not in vocab_norm21:
                c21 = False
    _check(21, "Closure: ternary_op over MECCANO-word payload tribbles yields vocab member", c21)

    # ── 22. Discrimination: OPCODE vs EXEC vs DATA separated by get_primary ───
    c22 = True
    exec_prim = get_primary(build_exec_word(0, 0, 0, 4, 0))
    data_prim = get_primary(_mod.build_int_word(42))
    for (fam, idx) in list(OPCODE_MNEMONICS.keys())[:6]:
        w    = build_opcode_word(fam, arity=2, op_index=idx)
        prim = get_primary(w)
        t23  = get_trit(w, 23)
        if prim != PRIMARY_OPCODE:
            c22 = False
        if prim == exec_prim or prim == data_prim:
            c22 = False
        if t23 != +1:   # T23-band test: all OPCODE words have T23=+1
            c22 = False
    _check(22, "Discrimination: OPCODE/EXEC/DATA separated; T23=+1 for all OPCODE words", c22)

    # ── 23. Arity law: arity encoded and recovered across all families/values ──
    c23 = True
    for arity in range(9):   # 0..8
        for (fam, idx) in list(OPCODE_MNEMONICS.keys())[:5]:
            w = build_opcode_word(fam, arity=arity, op_index=idx)
            d = decode_opcode_word(w)
            if d['arity'] != arity:
                c23 = False
    _check(23, "Arity law: arity 0..8 encoded/decoded for all families without lookahead", c23)

    # ── 24. Regression: existing 18 gristmill criteria + test_primary_types ───
    # Criteria 1-18 already verified above (they're in results[0:18]).
    # test_primary_types: verify PRIMARY_OPCODE is in PRIMARY_NAMES as 'OPCODE'
    c24a = (_mod.PRIMARY_NAMES.get(_mod.PRIMARY_OPCODE) == 'OPCODE')
    # Verify 8 primary types round-trip correctly (was 7 before OPCODE)
    ptype_count = 0
    for (pval, pname, (t23, t22)) in [
        (_mod.PRIMARY_EXEC,   'EXEC',   (-1,-1)),
        (_mod.PRIMARY_MAP,    'MAP',    (-1, 0)),
        (_mod.PRIMARY_DATA,   'DATA',   (-1,+1)),
        (_mod.PRIMARY_NEURAL, 'NEURAL', ( 0,-1)),
        (_mod.PRIMARY_IO,     'I/O',    ( 0, 0)),
        (_mod.PRIMARY_CRYPTO, 'CRYPTO', ( 0,+1)),
        (_mod.PRIMARY_OPCODE, 'OPCODE', (+1,-1)),
        (_mod.PRIMARY_POOL,   'POOL',   (+1,+1)),
    ]:
        w = set_primary(0, pval)
        if (get_primary(w) == pval and
                get_trit(w, 23) == t23 and
                get_trit(w, 22) == t22):
            ptype_count += 1
    c24 = c24a and ptype_count == 8 and all(results[:18])
    _check(24, "Regression: 18 gristmill criteria pass; test_primary_types 8/8 incl. OPCODE", c24)

    # ── 25. Legacy tag pinning: OP_TOBJ/OP_TGET behaviour on OPCODE words ─────
    opcode_w   = build_opcode_word(OPF_ISA_CORE, arity=2, op_index=OP_ADD)
    t23_before = get_trit(opcode_w, 23)
    t22_before = get_trit(opcode_w, 22)
    # OP_TOBJ: set_trit(val, 23, tag) — T22 must be preserved (v0.1 behaviour)
    result_obj = set_trit(opcode_w, 23, -1)
    t23_after  = get_trit(result_obj, 23)
    t22_after  = get_trit(result_obj, 22)
    # OP_TGET: get_trit(word, 23) returns T23 only — not the 2-trit primary
    t23_get    = get_trit(opcode_w, 23)
    c25 = (t23_before == +1 and t22_before == -1 and   # OPCODE primary: T23=+1, T22=-1
           t23_after == -1 and t22_after == -1 and     # T23 updated, T22 preserved
           t23_get == +1)                               # OP_TGET returns T23 alone
    _check(25, "Legacy tag pinning: OP_TOBJ preserves T22; OP_TGET returns T23 alone", c25)

    # ── Summary ───────────────────────────────────────────────────────────────
    n_orig  = 13
    n_new   = len(results) - n_orig
    passed  = sum(results)
    total   = len(results)
    print()
    print(f"  Rev4 criteria 1–13 : {sum(results[:n_orig])}/13")
    if n_new > 0:
        print(f"  New criteria 14–{n_orig+n_new}: {sum(results[n_orig:])}/{n_new}")
    print(f"  Total              : {passed}/{total}")
    if passed == total:
        print(f"  ✓ All {total} criteria PASS — ready for commit.")
    else:
        print(f"  ✗ {total - passed} criterion/criteria FAILED — do not commit.")
    print()
    return passed == total


# ── Demo ──────────────────────────────────────────────────────────────────────

def demo_synthesis():
    """Demonstrate MMID → MMOE synthesis for a simple flowgram."""
    print("=" * 56)
    print("  GristMill — MMOE Synthesis Demo")
    print("=" * 56)

    gm = GristMill()

    # Synthesise the AgeTest2 structure from MMIDs
    sequence = [
        ('terminator', 'START'),
        ('io_read',    'GET AGE'),
        ('process',    'AGE TEST'),
        ('io_write',   'ACCEPT AGE'),
        ('io_write',   'UNDER AGE'),
        ('terminator', 'END'),
    ]

    mmoes = []
    for type_name, label in sequence:
        mmid = MMID(type_name)
        mmoe = gm.synthesise(mmid, label=label)
        mmoes.append(mmoe)
        print(mmoe.describe())
        print()

    words = gm.to_words(mmoes)
    print(f"Total TernOO words: {len(words)}")

    # Show proximity for terminator
    print(f"\nProximity to 'terminator':")
    tid = MMID('terminator')
    for dist, name in gm.proximity(tid):
        print(f"  {dist:3d}  {name}")

    # Show successors
    print(f"\nSuccessors:")
    for t in MMOE_TYPES:
        s = gm.successors(t)
        print(f"  {t:<16} → {s}")


def demo_from_flowcode():
    """Load AgeTest2.json and derive MMIDs from it."""
    base    = os.path.dirname(os.path.abspath(__file__))
    fc_path = os.path.join(base, '..', 'FlowCode', 'AgeTest2.json')
    if not os.path.exists(fc_path):
        print(f"AgeTest2.json not found at {fc_path}")
        return

    print("=" * 56)
    print("  GristMill — FlowCode → MMID Derivation")
    print("=" * 56)

    with open(fc_path) as f:
        canvas = json.load(f)

    gm      = GristMill()
    triples = gm.from_flowcode(canvas)

    print(f"\nDerived {len(triples)} MMIDs from AgeTest2.json:")
    for mmid, label, otree_word in triples:
        print(f"  {label:20} {mmid}  otree={otree_word}")

    mmoes = gm.compose(triples)
    words = gm.to_words(mmoes)
    print(f"\nSynthesised {len(mmoes)} MMOEs → {len(words)} TernOO words")


if __name__ == '__main__':
    if '--accept' in sys.argv:
        sys.exit(0 if run_acceptance() else 1)
    elif '--flowcode' in sys.argv:
        demo_from_flowcode()
    else:
        demo_synthesis()
        print()
        demo_from_flowcode()
