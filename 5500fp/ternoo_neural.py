#!/usr/bin/env python3
"""
TernOO-5500FP Neural Forward-Pass Engine
=========================================
Skeleton implementation of the GHOST NEURAL substrate.
Operates on native TernOO NEURAL words — UNIT, CONNECTION, STRUCTURE.

Added: 31 May 2026, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Companion: docs/TernOO-5500FP-Companion.md § NEURAL Forward-Pass Engine
Status: SKELETON — proof of architecture, not production

Architecture:
  NEURAL/UNIT word       — one neuron: state, bias, fan_in, weight_seg
  NEURAL/CONNECTION word — one synapse: weight(2t=9 levels), source_id, target_id
  NEURAL/STRUCTURE word  — layer/network descriptor: kind, size, seg_ref

Forward pass:
  For each CONNECTION word:
    target.state += source.state * weight   (ternary arithmetic)
  Then apply bias:
    unit.state = clamp(unit.state + unit.bias)

Weight encoding: 2 trits → 9 levels (−4..+4), richer than BitNet's {−1,0,+1}
State encoding:  3 trits → 27 levels (−13..+13)

Relationship to GHOST:
  This engine is the computational substrate GHOST runs on.
  When a FlowCode program contains NEURAL symbols, the interpreter
  delegates to this engine for forward passes.
  Input arrives via I/O prompt-read symbols → eval stack → NEURAL input layer.
  Output departs via NEURAL output layer → eval stack → I/O prompt-write symbols.

Relationship to Gemini brain files:
  ternoo_word_brain.json / ternoo_generative_brain.json are Markov chain
  prototypes — valid prior art for the file format and scaffolding.
  This engine replaces the Markov random-pick with actual ternary arithmetic
  on TernOO words, while keeping the same JSON-loadable brain concept.
"""

import sys, json, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util as _ilu, os as _os
_spec = _ilu.spec_from_file_location(
    'ternoo_v03',
    _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                  '5500fp_ternoo_v03.py'))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
build_neural_unit      = _mod.build_neural_unit
build_neural_connection= _mod.build_neural_connection
build_neural_structure = _mod.build_neural_structure
decode_word            = _mod.decode_word
get_field              = _mod.get_field
set_field              = _mod.set_field
NEURAL_UNIT            = _mod.NEURAL_UNIT
NEURAL_CONNECTION      = _mod.NEURAL_CONNECTION
NEURAL_STRUCTURE       = _mod.NEURAL_STRUCTURE
PRIMARY_NEURAL         = _mod.PRIMARY_NEURAL
get_primary            = _mod.get_primary

# ── Ternary arithmetic helpers ────────────────────────────────────────────────
# Added: 31 May 2026, Adelaide

TRIT_MAX  = 13   # max 3-trit balanced ternary value  (+13)
TRIT_MIN  = -13  # min 3-trit balanced ternary value  (-13)
STATE_MAX = 13
STATE_MIN = -13

def trit_clamp(value: int, lo: int = STATE_MIN, hi: int = STATE_MAX) -> int:
    """Clamp a value to the ternary state range."""
    return max(lo, min(hi, value))

def trit_multiply(a: int, b: int) -> int:
    """Ternary multiply — plain integer multiply, clamped to state range."""
    return trit_clamp(a * b)

def trit_accumulate(accumulator: int, delta: int) -> int:
    """Add delta to accumulator, clamped."""
    return trit_clamp(accumulator + delta)


# ── TernOO NEURAL word wrappers ───────────────────────────────────────────────
# Added: 31 May 2026, Adelaide

class NeuralUnit:
    """
    A single neuron, backed by a NEURAL/UNIT TernOO word.
    state:      3 trits — current activation (-13..+13)
    bias:       6 trits — resting offset
    fan_in:     5 trits — expected number of incoming connections
    weight_seg: 4 trits — segment address of this unit's connection words
    """
    def __init__(self, unit_id: int, state: int = 0, bias: int = 0,
                 fan_in: int = 0, weight_seg: int = 0):
        self.id         = unit_id
        self.state      = trit_clamp(state)
        self.bias       = bias
        self.fan_in     = fan_in
        self.weight_seg = weight_seg
        self._accumulator = 0  # running sum during forward pass

    def to_word(self) -> int:
        return build_neural_unit(self.state, self.bias, self.fan_in, self.weight_seg)

    @classmethod
    def from_word(cls, unit_id: int, word: int) -> 'NeuralUnit':
        d = decode_word(word)
        assert d['type'] == 'NEURAL_UNIT', f"Expected NEURAL_UNIT, got {d['type']}"
        return cls(unit_id, d['state'], d['bias'], d['fan_in'], d['weight_seg'])

    def __repr__(self):
        return f"NeuralUnit(#{self.id} state={self.state} bias={self.bias})"


class NeuralConnection:
    """
    A single synapse, backed by a NEURAL/CONNECTION TernOO word.
    weight: 2 trits — 9 levels (-4..+4)
    source: 8 trits — source unit id
    target: 8 trits — target unit id
    """
    def __init__(self, weight: int, source: int, target: int):
        self.weight = weight
        self.source = source
        self.target = target

    def to_word(self) -> int:
        return build_neural_connection(self.weight, self.source, self.target)

    @classmethod
    def from_word(cls, word: int) -> 'NeuralConnection':
        d = decode_word(word)
        assert d['type'] == 'NEURAL_CONNECTION'
        return cls(d['weight'], d['source'], d['target'])

    def __repr__(self):
        return f"NeuralConnection({self.source}→{self.target} w={self.weight})"


# ── TernOO Brain — a network of NEURAL words ─────────────────────────────────
# Added: 31 May 2026, Adelaide

class TernOOBrain:
    """
    A neural network expressed entirely as TernOO NEURAL words.

    Layout:
      units[id]       → NeuralUnit
      connections     → [NeuralConnection]
      input_ids       → unit ids that receive external input
      output_ids      → unit ids whose state is the network output

    Forward pass:
      1. Load input values into input unit states
      2. For each connection: target.accumulator += source.state * weight
      3. For each unit: unit.state = clamp(accumulator + bias); reset accumulator

    This is intentionally simple — a single-layer feedforward pass.
    Recurrence and multi-layer passes are the next iteration.
    """

    def __init__(self):
        self.units:       dict[int, NeuralUnit]   = {}
        self.connections: list[NeuralConnection]  = []
        self.input_ids:   list[int]               = []
        self.output_ids:  list[int]               = []

    def add_unit(self, unit: NeuralUnit, is_input=False, is_output=False):
        self.units[unit.id] = unit
        if is_input:  self.input_ids.append(unit.id)
        if is_output: self.output_ids.append(unit.id)

    def add_connection(self, conn: NeuralConnection):
        self.connections.append(conn)

    def forward(self, inputs: list) -> list:
        """
        Run one forward pass.
        inputs: list of ternary values for input units (in order of input_ids)
        returns: list of output unit states (in order of output_ids)
        """
        # Load inputs
        for uid, val in zip(self.input_ids, inputs):
            if uid in self.units:
                self.units[uid].state = trit_clamp(val)
                self.units[uid]._accumulator = 0

        # Reset accumulators on non-input units
        for uid, unit in self.units.items():
            if uid not in self.input_ids:
                unit._accumulator = 0

        # Propagate connections
        for conn in self.connections:
            src = self.units.get(conn.source)
            dst = self.units.get(conn.target)
            if src and dst:
                delta = trit_multiply(src.state, conn.weight)
                dst._accumulator = trit_accumulate(dst._accumulator, delta)

        # Apply bias and commit state
        for uid, unit in self.units.items():
            if uid not in self.input_ids:
                unit.state = trit_clamp(unit._accumulator + unit.bias)

        return [self.units[uid].state for uid in self.output_ids
                if uid in self.units]

    def to_words(self) -> list[int]:
        """Serialise entire network as a list of TernOO NEURAL words."""
        words = []
        for unit in self.units.values():
            words.append(unit.to_word())
        for conn in self.connections:
            words.append(conn.to_word())
        return words

    def to_json(self) -> dict:
        """Serialise to a JSON-friendly dict (brain file format)."""
        return {
            'units': [
                {'id': u.id, 'state': u.state, 'bias': u.bias,
                 'fan_in': u.fan_in, 'weight_seg': u.weight_seg,
                 'is_input': u.id in self.input_ids,
                 'is_output': u.id in self.output_ids}
                for u in self.units.values()
            ],
            'connections': [
                {'weight': c.weight, 'source': c.source, 'target': c.target}
                for c in self.connections
            ]
        }

    @classmethod
    def from_json(cls, data: dict) -> 'TernOOBrain':
        brain = cls()
        for ud in data.get('units', []):
            u = NeuralUnit(ud['id'], ud.get('state',0), ud.get('bias',0),
                           ud.get('fan_in',0), ud.get('weight_seg',0))
            brain.add_unit(u,
                           is_input=ud.get('is_input', False),
                           is_output=ud.get('is_output', False))
        for cd in data.get('connections', []):
            brain.add_connection(
                NeuralConnection(cd['weight'], cd['source'], cd['target']))
        return brain

    @classmethod
    def load(cls, path: str) -> 'TernOOBrain':
        with open(path) as f:
            data = json.load(f)
        # Detect format: new TernOO format vs old Markov format
        if 'units' in data:
            return cls.from_json(data)
        else:
            print(f"[TernOOBrain] Legacy Markov format detected in {path}")
            print(f"  Use TernOOBrain.from_markov() to convert.")
            return cls._from_markov(data)

    @classmethod
    def _from_markov(cls, data: dict) -> 'TernOOBrain':
        """
        Bootstrap: convert a Gemini-style Markov chain dict into a minimal
        TernOO brain. Each unique token becomes a NEURAL UNIT. Each transition
        becomes a NEURAL CONNECTION with weight=+1.
        This is a lossy approximation — it proves the pipeline, not the model.
        """
        brain = cls()
        tokens = list(data.keys())
        tok_id = {t: i for i, t in enumerate(tokens)}
        for i, tok in enumerate(tokens):
            u = NeuralUnit(i, state=0, bias=0, fan_in=len(data[tok]))
            brain.add_unit(u)
        for src_tok, dst_list in data.items():
            src_id = tok_id[src_tok]
            seen = set()
            for dst_tok in dst_list:
                if dst_tok in tok_id and dst_tok not in seen:
                    brain.add_connection(
                        NeuralConnection(+1, src_id, tok_id[dst_tok]))
                    seen.add(dst_tok)
        if tokens:
            brain.input_ids  = [tok_id[tokens[0]]]
            brain.output_ids = [tok_id[tokens[-1]]]
        print(f"[TernOOBrain] Converted {len(tokens)} tokens → "
              f"{len(brain.units)} units, {len(brain.connections)} connections")
        return brain



# ── FlowCode Symbol Vocabulary ────────────────────────────────────────────────
# Added: 31 May 2026, Adelaide
# The 5 core symbol types as unit IDs for the shadow-GHOST brain.
# Each symbol type gets one NEURAL UNIT. Connections encode transition
# probabilities — stronger weight = more common transition.

FLOWCODE_VOCAB = {
    'terminator': 0,
    'io_read':    1,   # I/O prompt-read  (T20=read)
    'io_write':   2,   # I/O prompt-write (T20=write)
    'process':    3,
    'decision':   4,
}
FLOWCODE_VOCAB_INV = {v: k for k, v in FLOWCODE_VOCAB.items()}


def flowcode_symbol_type(node: dict) -> str:
    """Map a FlowCode JSON symbol dict to a vocabulary token."""
    kind = node.get('kind', 'process')
    if kind == 'terminator':
        return 'terminator'
    if kind == 'decision':
        return 'decision'
    if kind == 'process':
        return 'process'
    if kind == 'io':
        # Heuristic: same keyword detection as interpreter
        label = node.get('label','').upper()
        words = set(label.replace('-',' ').replace('_',' ').split())
        write_h = {'OUTPUT','PRINT','SHOW','DISPLAY','MESSAGE','RESULT',
                   'ACCEPT','UNDER','PASS','FAIL','TELL','SAY','RESPOND'}
        if words & write_h:
            return 'io_write'
        return 'io_read'
    return 'process'


class FlowCodeBrain(TernOOBrain):
    """
    A TernOOBrain specialised for learning FlowCode symbol sequences.
    Added: 31 May 2026, Adelaide
    Author: Stevo + Claude
    Companion: docs/TernOO-5500FP-Companion.md § FlowCode Brain Training

    Vocabulary: 5 symbol types (terminator, io_read, io_write, process, decision)
    Each type = one NEURAL UNIT. Connections = learned transitions.
    Weight range: -4..+4 (2 trits). Positive = common transition.
    """

    def __init__(self):
        super().__init__()
        # Create one unit per symbol type
        for name, uid in FLOWCODE_VOCAB.items():
            u = NeuralUnit(uid, state=0, bias=0, fan_in=0)
            is_in  = (name == 'terminator')
            is_out = (name == 'terminator')
            self.add_unit(u, is_input=is_in, is_output=is_out)
        # Connection weights stored as a dict for easy update
        # key: (src_id, dst_id) → weight
        self._weights: dict = {}

    def _get_weight(self, src: int, dst: int) -> int:
        return self._weights.get((src, dst), 0)

    def _set_weight(self, src: int, dst: int, w: int):
        self._weights[(src, dst)] = trit_clamp(w, -4, 4)
        # Rebuild connections list from weights dict
        self.connections = [
            NeuralConnection(v, k[0], k[1])
            for k, v in self._weights.items() if v != 0
        ]

    def train_on_canvas(self, canvas: dict, learning_rate: int = 1):
        """
        Train on one FlowCode JSON canvas.
        Walks symbols in edge-connected order and strengthens transition weights.
        learning_rate: trit increment per observed transition (default +1)
        """
        symbols = {s['id']: s for s in canvas.get('symbols', [])}
        edges   = canvas.get('edges', [])

        # Build adjacency: src_id → [dst_id]
        adj = {}
        for e in edges:
            adj.setdefault(e['src'], []).append(e['dst'])

        # Find start: terminator with no incoming edges
        incoming = set(e['dst'] for e in edges)
        starts = [s for s in symbols.values()
                  if s['id'] not in incoming]
        if not starts:
            starts = list(symbols.values())

        # Walk from start, record transitions
        visited = set()
        queue = [starts[0]['id']]
        transitions = []
        while queue:
            sid = queue.pop(0)
            if sid in visited:
                continue
            visited.add(sid)
            sym = symbols.get(sid)
            if not sym:
                continue
            for dst_id in adj.get(sid, []):
                dst_sym = symbols.get(dst_id)
                if dst_sym:
                    src_tok = flowcode_symbol_type(sym)
                    dst_tok = flowcode_symbol_type(dst_sym)
                    transitions.append((src_tok, dst_tok))
                    queue.append(dst_id)

        # Strengthen weights for observed transitions
        for src_tok, dst_tok in transitions:
            src_id = FLOWCODE_VOCAB[src_tok]
            dst_id = FLOWCODE_VOCAB[dst_tok]
            current = self._get_weight(src_id, dst_id)
            self._set_weight(src_id, dst_id,
                             trit_clamp(current + learning_rate, -4, 4))

        return transitions

    def train_on_file(self, path: str, learning_rate: int = 1):
        """Load a FlowCode JSON file and train on it."""
        with open(path) as f:
            canvas = json.load(f)
        transitions = self.train_on_canvas(canvas, learning_rate)
        print(f"  Trained on {path.split('/')[-1]}: "
              f"{len(transitions)} transitions observed")
        return transitions

    def predict_next(self, current_type: str) -> str:
        """
        Given the current symbol type, predict the most likely next type.
        Returns the token with the highest outgoing connection weight.
        """
        src_id = FLOWCODE_VOCAB.get(current_type, 0)
        best_w, best_tok = -5, 'terminator'
        for (s, d), w in self._weights.items():
            if s == src_id and w > best_w:
                best_w = w
                best_tok = FLOWCODE_VOCAB_INV.get(d, 'terminator')
        return best_tok

    def show_weights(self):
        """Print the learned transition weight matrix."""
        tokens = list(FLOWCODE_VOCAB.keys())
        col_w = 12
        print(f"\n{'Transition weights (rows=src, cols=dst)':}")
        print(f"{'':14}", end='')
        for t in tokens: print(f"{t:>{col_w}}", end='')
        print()
        for src in tokens:
            print(f"{src:<14}", end='')
            for dst in tokens:
                w = self._get_weight(FLOWCODE_VOCAB[src], FLOWCODE_VOCAB[dst])
                print(f"{w:>{col_w}}", end='')
            print()

# ── Minimal demo ──────────────────────────────────────────────────────────────

def demo_xor():
    """
    Demonstrate a minimal TernOO neural network solving ternary XOR-like logic.
    Input: two units (A, B) with states in {-1, 0, +1}
    Output: one unit whose state represents A XOR B (sign agreement)
    """
    print("="*56)
    print("  TernOO Brain — Ternary Forward Pass Demo")
    print("="*56)

    brain = TernOOBrain()

    # Input layer: units 0, 1
    brain.add_unit(NeuralUnit(0, state=0, bias=0, fan_in=0), is_input=True)
    brain.add_unit(NeuralUnit(1, state=0, bias=0, fan_in=0), is_input=True)
    # Hidden unit: unit 2
    brain.add_unit(NeuralUnit(2, state=0, bias=0, fan_in=2))
    # Output unit: unit 3
    brain.add_unit(NeuralUnit(3, state=0, bias=0, fan_in=1), is_output=True)

    # Connections: A→hidden w=+1, B→hidden w=-1, hidden→output w=+1
    brain.add_connection(NeuralConnection(+1, 0, 2))
    brain.add_connection(NeuralConnection(-1, 1, 2))
    brain.add_connection(NeuralConnection(+1, 2, 3))

    # Test a few input combinations
    tests = [(-1,-1),(0,0),(+1,+1),(-1,+1),(+1,-1),(0,+1)]
    print(f"\n{'Input A':>8} {'Input B':>8} {'Output':>8}")
    print("-"*28)
    for a, b in tests:
        out = brain.forward([a, b])
        print(f"{a:>8} {b:>8} {out[0]:>8}")

    print(f"\nNetwork as TernOO words:")
    for w in brain.to_words():
        d = decode_word(w)
        print(f"  {w:>12}  {d}")

    print(f"\nBrain JSON:")
    print(json.dumps(brain.to_json(), indent=2))


def demo_markov_convert():
    """Load the Gemini brain files and convert them to TernOO format."""
    base = os.path.dirname(os.path.abspath(__file__))
    for fname in ('ternoo_word_brain.json', 'ternoo_generative_brain.json'):
        path = os.path.join(base, fname)
        if not os.path.exists(path):
            print(f"  {fname} not found, skipping")
            continue
        print(f"\n{'='*56}")
        print(f"  Converting: {fname}")
        print('='*56)
        brain = TernOOBrain.load(path)
        out = brain.to_json()
        out_path = path.replace('.json', '_ternoo.json')
        with open(out_path,'w') as f:
            json.dump(out, f, indent=2)
        print(f"  Saved TernOO format → {os.path.basename(out_path)}")
        print(f"  Units: {len(out['units'])}  "
              f"Connections: {len(out['connections'])}")
        # Run a trivial forward pass to prove it works
        result = brain.forward([1] * len(brain.input_ids))
        print(f"  Test forward pass output: {result}")



def demo_train_flowcode():
    """Train FlowCodeBrain on all available FlowCode canvases and show results."""
    print("="*56)
    print("  FlowCode Brain — Symbol Sequence Training")
    print("="*56)

    brain = FlowCodeBrain()

    # Find FlowCode JSON files relative to this script
    base = os.path.dirname(os.path.abspath(__file__))
    fc_dir = os.path.join(base, '..', 'FlowCode')
    canvases = []
    if os.path.isdir(fc_dir):
        import glob
        canvases = glob.glob(os.path.join(fc_dir, '*.json'))

    if not canvases:
        print("  No FlowCode JSON files found — using built-in AgeTest2 structure")
        # Inline minimal AgeTest2-like canvas for demo
        canvas = {
            'symbols': [
                {'id':1,'kind':'terminator','label':'START'},
                {'id':2,'kind':'io',        'label':'GET AGE'},
                {'id':3,'kind':'decision',  'label':'AGE TEST'},
                {'id':4,'kind':'io',        'label':'ACCEPT AGE'},
                {'id':5,'kind':'io',        'label':'UNDER AGE'},
                {'id':6,'kind':'terminator','label':'END'},
            ],
            'edges': [
                {'src':1,'dst':2},{'src':2,'dst':3},
                {'src':3,'dst':4},{'src':3,'dst':5},
                {'src':4,'dst':6},{'src':5,'dst':6},
            ]
        }
        brain.train_on_canvas(canvas)
        print("  Trained on inline AgeTest2 structure")
    else:
        for path in sorted(canvases):
            brain.train_on_file(path)

    brain.show_weights()

    print("\nPredictions:")
    for tok in FLOWCODE_VOCAB:
        nxt = brain.predict_next(tok)
        print(f"  after {tok:<14} → {nxt}")

    # Save trained brain
    out_path = os.path.join(base, 'flowcode_brain.json')
    with open(out_path, 'w') as f:
        json.dump(brain.to_json(), f, indent=2)
    print(f"\nSaved trained brain → {os.path.basename(out_path)}")


if __name__ == '__main__':
    if '--markov' in sys.argv:
        demo_markov_convert()
    elif '--train' in sys.argv:
        demo_train_flowcode()
    else:
        demo_xor()
