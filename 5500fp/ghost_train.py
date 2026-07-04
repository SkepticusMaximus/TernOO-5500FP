#!/usr/bin/env python3
"""ghost_train.py — GHOST First Breath trainer (host-side, stdlib only).

Trains the intent→command micro-model and exports it three ways:
  * ghost_model.json          — quantized weights + metadata (the artifact)
  * NEURAL_CONNECTION words   — the model AS a TernOO word stream
  * (consumed by gen_ghost_t5asm.py to emit the native forward pass)

Architecture (GHOST-Consolidated-Reference §2):
  features : text → char-trigram hash → 81 ternary values in {−1,0,+1}
  hidden   : 27 units, integer MAC + ReLU
  output   : one logit per routable command + a `none` class
  weights  : 9-level {−4..+4} (v0.3 NEURAL encoding)

Training: float shadow weights, straight-through 9-level quantization,
plain SGD, deterministic seed.  The exported `ref_forward` is THE golden
reference the emulator must match bit-exactly (integer math only).

Epistemic humility is structural here (Reference §3): the `none` class is
trained on out-of-domain phrases, and routing requires the winning logit to
beat the runner-up by MARGIN.

Date: 2026-07-04, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import json
import math
import random

# ── model shape ──────────────────────────────────────────────────────────────
NFEAT = 81          # 3^4, and the register count — the poetry is free
NHID = 27
MARGIN = 3          # required argmax lead before GHOST will route
WLEVELS = 4         # weights clamp to {−4..+4}

# ── routable classes (substrate-side; io_*/ctl_* excluded from v0.5) ─────────
CLASSES = ['none',
           'cmd_text_upper', 'cmd_text_lower', 'cmd_text_trim',
           'cmd_text_length', 'cmd_text_replace', 'cmd_text_split',
           'cmd_text_join', 'cmd_math_add', 'cmd_math_subtract',
           'cmd_math_multiply', 'cmd_math_divide', 'cmd_math_mod',
           'cmd_math_round', 'cmd_math_abs', 'cmd_math_power',
           'cmd_list_count', 'cmd_list_first', 'cmd_list_last',
           'cmd_list_reverse', 'cmd_list_sort', 'cmd_list_unique',
           'cmd_env_set', 'cmd_env_get']

# ── corpus templates ─────────────────────────────────────────────────────────
TEMPLATES = {
 'cmd_text_upper':   ['make {} loud', 'uppercase {}', 'shout {}',
                      'capitalize all of {}', 'make {} upper case',
                      'convert {} to caps', 'yell {}', 'all caps {}'],
 'cmd_text_lower':   ['lowercase {}', 'make {} quiet', 'make {} lower case',
                      'convert {} to small letters', 'whisper {}',
                      'no caps in {}', 'decapitalize {}'],
 'cmd_text_trim':    ['trim {}', 'strip spaces from {}',
                      'remove whitespace around {}', 'tidy the edges of {}',
                      'clean up spaces in {}'],
 'cmd_text_length':  ['how long is {}', 'length of {}', 'count characters in {}',
                      'how many letters in {}', 'measure {}',
                      'character count of {}'],
 'cmd_text_replace': ['replace foo with bar in {}', 'swap words in {}',
                      'substitute text in {}', 'change every foo in {}',
                      'find and replace in {}'],
 'cmd_text_split':   ['split {} by commas', 'break {} into pieces',
                      'cut {} apart', 'divide {} at each comma',
                      'tokenize {}'],
 'cmd_text_join':    ['join the pieces of {}', 'glue {} together',
                      'combine parts of {} with commas',
                      'concatenate the items of {}', 'merge list {} into text'],
 'cmd_math_add':     ['add {} and {}', 'sum of {} and {}', 'what is {} plus {}',
                      'total of {} and {}', '{} plus {}', 'add them up'],
 'cmd_math_subtract':['subtract {} from {}', '{} minus {}',
                      'difference between {} and {}', 'take {} away from {}'],
 'cmd_math_multiply':['multiply {} by {}', '{} times {}', 'product of {} and {}',
                      'what is {} multiplied by {}'],
 'cmd_math_divide':  ['divide {} by {}', '{} divided by {}',
                      'split {} into {} parts', 'quotient of {} and {}'],
 'cmd_math_mod':     ['remainder of {} divided by {}', '{} modulo {}',
                      'what is left over from {} by {}', 'mod of {} and {}'],
 'cmd_math_round':   ['round {}', 'round off {}', 'nearest whole number to {}',
                      'round {} to an integer'],
 'cmd_math_abs':     ['absolute value of {}', 'make {} positive',
                      'magnitude of {}', 'abs of {}', 'drop the sign of {}'],
 'cmd_math_power':   ['{} to the power of {}', 'raise {} to {}',
                      '{} squared', '{} cubed', 'exponent {} of {}'],
 'cmd_list_count':   ['how many items in {}', 'count the list {}',
                      'number of elements in {}', 'size of list {}'],
 'cmd_list_first':   ['first item of {}', 'head of {}', 'start of list {}',
                      'give me the first element of {}'],
 'cmd_list_last':    ['last item of {}', 'tail end of {}', 'final element of {}',
                      'end of list {}'],
 'cmd_list_reverse': ['reverse {}', 'flip the list {}', 'backwards order of {}',
                      'invert the order of {}'],
 'cmd_list_sort':    ['sort {}', 'order the list {}', 'arrange {} in order',
                      'alphabetize {}', 'sort {} ascending',
                      'sort my {} list', 'put the {} list in order',
                      'sort the shopping list', 'order these items'],
 'cmd_list_unique':  ['unique items of {}', 'remove duplicates from {}',
                      'dedupe {}', 'distinct elements of {}'],
 'cmd_env_set':      ['set variable {} to {}', 'remember {} as {}',
                      'store {} in {}', 'save value {} as {}',
                      'let {} equal {}'],
 'cmd_env_get':      ['what is variable {}', 'recall {}', 'get the value of {}',
                      'read variable {}', 'fetch {}'],
 'none':             ['open the pod bay doors', 'what is the weather today',
                      'sing me a song', 'order a pizza', 'who won the football',
                      'tell me a joke about llamas', 'paint the fence',
                      'where are my keys', 'play some music',
                      'book a flight to mars', 'walk the dog',
                      'what time is it in london', 'nobody expects this',
                      'bring me a shrubbery'],
}

FILLERS = ['this text', 'the message', 'my string', 'that line', 'the words',
           'the numbers', 'the list', 'these values', 'seven', 'twelve',
           'the answer', 'x', 'my data', 'the file contents', 'everything']


# ── features (MUST stay trivially portable to t5asm) ─────────────────────────
def features(text: str):
    """81 ternary features from character trigrams.  Integer-only, and the
    exact algorithm gen_ghost_t5asm.py re-emits in assembly."""
    f = [0] * NFEAT
    b = [ord(c) % 128 for c in text.lower()]
    for i in range(len(b) - 2):
        c0, c1, c2 = b[i], b[i + 1], b[i + 2]
        slot = (c0 * 7 + c1 * 31 + c2 * 131) % NFEAT
        sign = 1 if ((c0 * 17 + c1 * 13 + c2 * 11) % 2) == 0 else -1
        f[slot] += sign
    return [1 if v > 0 else (-1 if v < 0 else 0) for v in f]


# ── quantized integer forward — THE golden reference ─────────────────────────
def ref_forward(text: str, W1, W2):
    """Integer forward pass: (class_index, margin, logits).  The emulator's
    output must equal this bit-for-bit."""
    f = features(text)
    h = []
    for j in range(NHID):
        acc = 0
        for i in range(NFEAT):
            if f[i]:
                acc += f[i] * W1[i][j]
        h.append(acc if acc > 0 else 0)          # ReLU
    logits = []
    for k in range(len(CLASSES)):
        acc = 0
        for j in range(NHID):
            if h[j]:
                acc += h[j] * W2[j][k]
        logits.append(acc)
    order = sorted(range(len(logits)), key=lambda k: -logits[k])
    best, second = order[0], order[1]
    return best, logits[best] - logits[second], logits


def route(text: str, W1, W2):
    """Apply the humility gate: below MARGIN, GHOST refuses (→ none)."""
    cls, margin, _ = ref_forward(text, W1, W2)
    if margin < MARGIN or CLASSES[cls] == 'none':
        return 'none', margin
    return CLASSES[cls], margin


# ── training ─────────────────────────────────────────────────────────────────
def _quant(w):
    q = int(round(w))
    return WLEVELS if q > WLEVELS else (-WLEVELS if q < -WLEVELS else q)


def build_corpus(seed=27):
    rng = random.Random(seed)
    rows = []
    for cls_idx, cls in enumerate(CLASSES):
        for t in TEMPLATES[cls]:
            n = t.count('{}')
            for _ in range(9):
                args = [rng.choice(FILLERS) for _ in range(n)]
                rows.append((t.format(*args), cls_idx))
    rng.shuffle(rows)
    cut = max(1, len(rows) // 6)
    return rows[cut:], rows[:cut]          # train, held-out


def train(seed=27, epochs=70, lr=0.05):
    rng = random.Random(seed)
    S1 = [[rng.uniform(-1, 1) for _ in range(NHID)] for _ in range(NFEAT)]
    S2 = [[rng.uniform(-1, 1) for _ in range(len(CLASSES))]
          for _ in range(NHID)]
    train_rows, held = build_corpus(seed)
    feats = {t: features(t) for t, _ in train_rows + held}
    for ep in range(epochs):
        lr_t = lr * (1.0 - ep / (epochs * 1.3))
        rng.shuffle(train_rows)
        for text, y in train_rows:
            f = feats[text]
            W1 = [[_quant(w) for w in row] for row in S1]
            W2 = [[_quant(w) for w in row] for row in S2]
            pre = [sum(f[i] * W1[i][j] for i in range(NFEAT) if f[i])
                   for j in range(NHID)]
            h = [p if p > 0 else 0 for p in pre]
            logits = [sum(h[j] * W2[j][k] for j in range(NHID) if h[j])
                      for k in range(len(CLASSES))]
            m = max(logits)
            exps = [math.exp((l - m) / 8.0) for l in logits]
            Z = sum(exps)
            probs = [e / Z for e in exps]
            dlog = [probs[k] - (1.0 if k == y else 0.0)
                    for k in range(len(CLASSES))]
            for j in range(NHID):
                if h[j]:
                    for k in range(len(CLASSES)):
                        S2[j][k] -= lr_t * dlog[k] * h[j] * 0.05
            dh = [sum(dlog[k] * W2[j][k] for k in range(len(CLASSES)))
                  if pre[j] > 0 else 0.0 for j in range(NHID)]
            for i in range(NFEAT):
                if f[i]:
                    for j in range(NHID):
                        if dh[j]:
                            S1[i][j] -= lr_t * dh[j] * f[i]
    W1 = [[_quant(w) for w in row] for row in S1]
    W2 = [[_quant(w) for w in row] for row in S2]
    return W1, W2, held


def accuracy(rows, W1, W2):
    ok = 0
    for text, y in rows:
        got, _m = route(text, W1, W2)
        want = CLASSES[y]
        if got == want or (want == 'none' and got == 'none'):
            ok += 1
    return ok / len(rows)


def export(W1, W2, path='ghost_model.json'):
    json.dump({'nfeat': NFEAT, 'nhid': NHID, 'classes': CLASSES,
               'margin': MARGIN, 'W1': W1, 'W2': W2}, open(path, 'w'))
    return path


def export_neural_words(W1, W2):
    """The model AS TernOO words: one NEURAL_CONNECTION word per weight,
    payload = (layer, src, dst, value) packed small-endian in trits via the
    v0.3 builder.  Inspectability is the point (Reference §3c)."""
    import importlib.util as u, os
    here = os.path.dirname(os.path.abspath(__file__))
    s = u.spec_from_file_location('v03', os.path.join(here,
                                                      '5500fp_ternoo_v03.py'))
    v = u.module_from_spec(s); s.loader.exec_module(v)
    words = []
    for layer, W in ((0, W1), (1, W2)):
        for i, row in enumerate(W):
            for j, val in enumerate(row):
                if val == 0:
                    continue                     # sparse: zero = no synapse
                # source/target carry (layer, index) packed small; weight is
                # the 9-level value — the v0.3 NEURAL_CONNECTION contract.
                words.append(v.build_neural_connection(
                    val, layer * 100 + (i % 100), j))
    return words


if __name__ == '__main__':
    W1, W2, held = train()
    acc = accuracy(held, W1, W2)
    print(f"held-out routing accuracy: {acc:.1%} ({len(held)} phrases)")
    print(f"model: {export(W1, W2)}")
    demo = ['make this loud', 'add 4 and 5', 'sort my shopping list',
            'open the pod bay doors', 'reverse the polarity']
    for d in demo:
        cls, m = route(d, W1, W2)
        print(f"  ghost {d!r:38s} → {cls}  (margin {m})")
