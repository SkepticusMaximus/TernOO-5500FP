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

import sys, os, json, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    'ternoo_v03',
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 '5500fp_ternoo_v03.py'))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

build_map_word    = _mod.build_map_word
decode_map_word   = _mod.decode_map_word
build_udp_word    = _mod.build_udp_word
build_exec_word   = _mod.build_exec_word
decode_word       = _mod.decode_word
describe_word     = _mod.describe_word


# ── MMOE Type Registry ────────────────────────────────────────────────────────
# Added: 31 May 2026, Adelaide
# Each MMOE type has:
#   - A name (human label)
#   - A UDP subclass (T21, T20) encoding its structural role
#   - A set of natural successors (what objects typically follow this one)
#   - A MAP octree region (Y-range, Z-range) where objects of this type live

MMOE_TYPES = {
    # FlowCode symbol types
    'terminator': {
        'udp': (+1, +1), 'successors': ['io_read'],
        'y_range': (-100, +100), 'z_range': (+800, +1000),
        'description': 'Program entry/exit boundary'
    },
    'io_read': {
        'udp': (+1,  0), 'successors': ['process', 'decision'],
        'y_range': (-100, +100), 'z_range': (+600, +800),
        'description': 'External input channel'
    },
    'io_write': {
        'udp': (+1,  0), 'successors': ['terminator'],
        'y_range': (+100, +300), 'z_range': (+600, +800),
        'description': 'External output channel'
    },
    'process': {
        'udp': (0,   0), 'successors': ['decision', 'io_write'],
        'y_range': (-100, +100), 'z_range': (+400, +600),
        'description': 'Computation / transformation'
    },
    'decision': {
        'udp': (0,  +1), 'successors': ['io_write', 'process', 'io_read'],
        'y_range': (-100, +100), 'z_range': (+200, +400),
        'description': 'Conditional branch'
    },
    # Widget types (GUI MMOE — skeleton for future GHOST training)
    'widget_window': {
        'udp': (+1, -1), 'successors': ['widget_panel'],
        'y_range': (+300, +500), 'z_range': (+800, +1000),
        'description': 'Top-level window container'
    },
    'widget_panel': {
        'udp': (+1, -1), 'successors': ['widget_button', 'widget_label', 'widget_input'],
        'y_range': (+300, +500), 'z_range': (+600, +800),
        'description': 'Layout container'
    },
    'widget_button': {
        'udp': (+1, +1), 'successors': ['widget_panel', 'widget_label'],
        'y_range': (+300, +500), 'z_range': (+400, +600),
        'description': 'Interactive button widget'
    },
    'widget_label': {
        'udp': (+1,  0), 'successors': ['widget_button', 'widget_input'],
        'y_range': (+300, +500), 'z_range': (+200, +400),
        'description': 'Static text display'
    },
    'widget_input': {
        'udp': (+1, -1), 'successors': ['widget_button', 'widget_label'],
        'y_range': (+300, +500), 'z_range': (0, +200),
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

    def __init__(self, mmoe_type: str, instance: int = 0):
        self.mmoe_type = mmoe_type
        self.instance  = instance
        self._word     = None
        self._compute()

    def _compute(self):
        """Compute the MAP word for this MMID from type and instance."""
        t = MMOE_TYPES.get(self.mmoe_type, {})
        y_lo, y_hi = t.get('y_range', (0, 100))
        z_lo, z_hi = t.get('z_range', (0, 100))
        # Place instance within the type's octree region
        y = y_lo + (instance_hash(self.mmoe_type, self.instance) %
                    max(1, y_hi - y_lo))
        z = z_lo + (self.instance % max(1, z_hi - z_lo))
        # Cache raw coordinates for distance_to() — decoding the MAP word
        # back to Y/Z requires re-applying sign bits which decode_map_word
        # does not do, so we keep the originals here.
        self._y = y
        self._z = z
        # Payload: upper 9 trits = abs(Y), lower 9 trits = abs(Z).
        # Multiplier is 3^9 = 19683, not 3^6 = 729.
        self._word = build_map_word(
            0,
            1 if y >= 0 else -1,
            1 if z >= 0 else -1,
            abs(y) * 19683 + abs(z)
        )

    @property
    def word(self) -> int:
        return self._word

    def distance_to(self, other: 'MMID') -> float:
        """
        Geometric distance between two MMIDs in octree space.
        Structurally similar objects are close. Dissimilar objects are distant.
        Uses cached _y/_z rather than decoding the MAP word — decode_map_word
        returns raw trit-field values without re-applying the qualifier sign
        bits, so reconstructed coordinates would be unsigned and wrong.
        """
        return math.sqrt((self._y - other._y)**2 + (self._z - other._z)**2)

    def __repr__(self):
        return (f"MMID({self.mmoe_type}#{self.instance} "
                f"Y={self._y} Z={self._z} "
                f"word={self._word})")


def instance_hash(type_name: str, instance: int) -> int:
    """Stable hash for placing an instance within its type region."""
    h = hash(f"{type_name}:{instance}") & 0x7fffffff
    return h % 100


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

    def __init__(self, mmid: MMID, label: str = ''):
        self.mmid       = mmid
        self.label      = label or mmid.mmoe_type
        t               = MMOE_TYPES.get(mmid.mmoe_type, {})
        t1, t0          = t.get('udp', (0, 0))
        self.map_word   = mmid.word
        self.udp_word   = build_udp_word(t1, t0, 0, 0, 0)
        self.exec_words = []   # event handler EXEC words
        self.children   = []   # contained MMOEs

    def add_child(self, child: 'MMOE'):
        self.children.append(child)

    def to_words(self) -> list:
        """Serialise to TernOO word sequence."""
        words = [self.map_word, self.udp_word]
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

    def synthesise(self, mmid: MMID, label: str = '') -> MMOE:
        """
        Compute an MMOE from an MMID.
        This is the core GristMill operation — object synthesis from coordinate.
        """
        return MMOE(mmid, label=label or mmid.mmoe_type)

    def proximity(self, mmid: MMID, n: int = 5) -> list:
        """
        Find the n nearest MMOE types in the octree to the given MMID.
        Closer types are more structurally related.
        """
        distances = []
        for type_name in MMOE_TYPES:
            candidate = MMID(type_name, 0)
            dist = mmid.distance_to(candidate)
            distances.append((dist, type_name))
        distances.sort()
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
        Assemble a list of MMOEs from a sequence of MMIDs.
        This is how GHOST manifests a program — as a sequence of MMOEs
        generated from a sequence of MMIDs.
        """
        return [self.synthesise(mmid) for mmid in mmid_sequence]

    def from_flowcode(self, canvas: dict) -> list:
        """
        Derive MMIDs from a FlowCode JSON canvas.
        Each symbol becomes an MMID. The sequence captures the program structure.
        Added: 31 May 2026, Adelaide
        """
        from ternoo_neural import flowcode_symbol_type as _fst
        mmids = []
        symbols = {s['id']: s for s in canvas.get('symbols', [])}
        edges   = canvas.get('edges', [])

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
            mmid = MMID(tok, instance=sid)
            mmids.append((mmid, sym.get('label', tok)))
            for e in edges:
                if e['src'] == sid:
                    queue.append(e['dst'])

        return mmids

    def to_words(self, mmoes: list) -> list:
        """Convert a list of MMOEs to a flat TernOO word sequence."""
        words = []
        for mmoe in mmoes:
            words.extend(mmoe.to_words())
        return words


# ── Demo ──────────────────────────────────────────────────────────────────────

def demo_synthesis():
    """Demonstrate MMID → MMOE synthesis for a simple flowgram."""
    print("=" * 56)
    print("  GristMill — MMOE Synthesis Demo")
    print("=" * 56)

    gm = GristMill()

    # Synthesise the AgeTest2 structure from MMIDs
    sequence = [
        ('terminator', 1, 'START'),
        ('io_read',    2, 'GET AGE'),
        ('process',    3, 'AGE TEST'),
        ('io_write',   4, 'ACCEPT AGE'),
        ('io_write',   5, 'UNDER AGE'),
        ('terminator', 6, 'END'),
    ]

    mmoes = []
    for type_name, instance, label in sequence:
        mmid = MMID(type_name, instance)
        mmoe = gm.synthesise(mmid, label=label)
        mmoes.append(mmoe)
        print(mmoe.describe())
        print()

    words = gm.to_words(mmoes)
    print(f"Total TernOO words: {len(words)}")

    # Show proximity for terminator
    print(f"\nProximity to 'terminator':")
    tid = MMID('terminator', 0)
    for dist, name in gm.proximity(tid):
        print(f"  {dist:8.2f}  {name}")

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

    gm    = GristMill()
    mmids = gm.from_flowcode(canvas)

    print(f"\nDerived {len(mmids)} MMIDs from AgeTest2.json:")
    for mmid, label in mmids:
        print(f"  {label:20} {mmid}")

    mmoes = [gm.synthesise(mmid, label=label) for mmid, label in mmids]
    words = gm.to_words(mmoes)
    print(f"\nSynthesised {len(mmoes)} MMOEs → {len(words)} TernOO words")


if __name__ == '__main__':
    if '--flowcode' in sys.argv:
        demo_from_flowcode()
    else:
        demo_synthesis()
        print()
        demo_from_flowcode()
