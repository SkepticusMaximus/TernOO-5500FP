#!/usr/bin/env python3
"""
build_geometry_corpus.py — CC-09
=================================
Builds _GHOST_GEOMETRY_CORPUS.tgui from the canonical widget geometry
defined in ternoo_widget_geometry.py.

The corpus format is the same .tgui JSON used by GhostTrainer, so it can
be fed directly into the GHOST GUI brain training pipeline via FlowCode.

But the geometry brain is a SEPARATE hemisphere from the structural brain:
  ghost_gui_brain.json      — widget-type → widget-type Markov chains
  ghost_geometry_brain.json — geometry-word → geometry-word Markov chains

Run:  python build_geometry_corpus.py [--out PATH]

Added: 01 Jun 2026, Adelaide
Authors: Stevo + Claude
Companion: private/TernOO-5500FP-Companion.md § G6 (CC-09)
"""

import os, sys, json, argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ternoo_widget_geometry import WIDGET_GEOMETRY, word_token, get_token_sequence

_HERE = os.path.dirname(os.path.abspath(__file__))
_DEFAULT_OUT = os.path.join(_HERE, '_GHOST_GEOMETRY_CORPUS.tgui')


def build_corpus(out_path: str = _DEFAULT_OUT) -> str:
    """
    Build a .tgui corpus where each widget type becomes a 'widget' entry
    whose geometry_tokens field holds the Markov vocabulary token sequence.

    The corpus is compatible with _markov_train() in ternoo_cambalache_bridge.py
    when a geometry-aware trainer calls it with the token sequences.
    """
    widgets = []
    for wtype, words in WIDGET_GEOMETRY.items():
        tokens = [word_token(w) for w in words]
        widgets.append({
            'id':               wtype,
            'type':             wtype,
            'geometry_tokens':  tokens,
            'word_count':       len(tokens),
            'properties':       {},
            'children':         [],
        })

    corpus = {
        'corpus_type':   'ghost_geometry',
        'hemisphere':    'geometry',
        'version':       '0.1',
        'description':   'Canonical widget render-geometry word sequences (CC-09)',
        'widget_count':  len(widgets),
        'token_vocab':   sorted({t for w in widgets for t in w['geometry_tokens']}),
        'widgets':       widgets,
    }

    with open(out_path, 'w') as f:
        json.dump(corpus, f, indent=2)

    print(f"Geometry corpus written: {len(widgets)} widget types, "
          f"{len(corpus['token_vocab'])} unique tokens")
    print(f"  → {out_path}")
    return out_path


def train_geometry_brain(corpus_path: str) -> str:
    """
    Train ghost_geometry_brain.json from the geometry corpus.
    Uses the same open-vocabulary _markov_train pattern as the structural brain.
    """
    try:
        from ternoo_cambalache_bridge import _markov_train
    except ImportError as e:
        print(f"Cannot import bridge: {e}")
        return ''

    brain_path = os.path.join(_HERE, 'ghost_geometry_brain.json')

    weights: dict = {}
    if os.path.exists(brain_path):
        with open(brain_path) as f:
            weights = json.load(f).get('weights', {})

    with open(corpus_path) as f:
        corpus = json.load(f)

    # Build a synthetic tgui that _markov_train can walk as token sequences
    # _markov_train expects {'widgets': [{'type': str, 'children': [...]}]}
    # We adapt: each widget's geometry_tokens form a chain of 'pseudo-widget' types

    for entry in corpus['widgets']:
        tokens = entry['geometry_tokens']
        # Build a mini-tgui: chain of single-type widget dicts
        chain_tgui = {'widgets': [
            {'type': tok, 'children': [], 'id': f"{entry['id']}_{i}"}
            for i, tok in enumerate(tokens)
        ]}
        _markov_train(weights, chain_tgui)

    brain_data = {
        'brain_type':  'ghost_geometry',
        'hemisphere':  'geometry',
        'vocab_size':  len(weights),
        'weights':     weights,
    }
    with open(brain_path, 'w') as f:
        json.dump(brain_data, f, indent=2)

    result = (f"GHOST geometry brain updated: {len(weights)} tokens "
              f"→ {brain_path}")
    print(result)
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Build GHOST geometry corpus')
    ap.add_argument('--out',   default=_DEFAULT_OUT, help='Output .tgui path')
    ap.add_argument('--train', action='store_true',  help='Also train ghost_geometry_brain.json')
    args = ap.parse_args()

    corpus_path = build_corpus(args.out)

    if args.train:
        train_geometry_brain(corpus_path)
    else:
        print("(pass --train to also update ghost_geometry_brain.json)")
