#!/usr/bin/env python3
"""
TernOO GHOST Widget Library Extractor
======================================
Builds an atomic widget corpus for GHOST training by querying the live
GObject introspection system — the same type registry GTK itself uses.

Every Gtk.Widget subclass becomes one atomic .tgui training file:
  one widget, all its canonical properties, all its signals, no layout noise.

This is Stage 1 GHOST vocabulary training — atoms before grammar.
The atoms produced here also become the widget palette for the FlowCode
GUI canvas tab (CC-08).

Pipeline:
  GObject type system  (gi.repository.Gtk)
        ↓
  ternoo_ghost_library.py  (this file)
        ↓
  ghost_widget_library/
    GtkButton.tgui
    GtkEntry.tgui
    GtkLabel.tgui
    ... (one per widget class)
    _GHOST_CORPUS.tgui   ← combined, for bulk training
        ↓
  python3 ternoo_ghost_library.py --train
        ↓
  ghost_gui_brain.json   ← GUI hemisphere brain (separate from flowcode_brain.json)

Usage:
  python3 ternoo_ghost_library.py              # extract + report
  python3 ternoo_ghost_library.py --train      # extract + train GHOST
  python3 ternoo_ghost_library.py --list       # list discovered widget classes
  python3 ternoo_ghost_library.py --atom GtkButton  # show one atom's .tgui

Added: 01 Jun 2026, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Companion: private/TernOO-5500FP-Companion.md § GHOST Widget Library
"""

import sys, os, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── GObject introspection ─────────────────────────────────────────────────────

def _require_gtk():
    try:
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk, GObject
        return Gtk, GObject
    except Exception as e:
        print(f"GObject introspection unavailable: {e}")
        print("Install: sudo apt install python3-gi gir1.2-gtk-3.0")
        sys.exit(1)

# ── MMOE type registry (import from bridge) ───────────────────────────────────

from ternoo_cambalache_bridge import (
    WIDGET_TYPE_MAP, widget_class_to_mmoe, canvas_to_tgui, save_tgui
)
from ternoo_gristmill import MMID, MMOE_TYPES

# ── Property type → TernOO DATA word kind ────────────────────────────────────
# GObject property fundamental types mapped to TernOO DATA semantics.

GPROP_KIND = {
    'gchararray':  'text',       # string
    'gboolean':    'trit',       # bool → ternary (-1/0/+1)
    'gint':        'scalar',     # integer
    'guint':       'scalar',
    'gfloat':      'scalar',
    'gdouble':     'scalar',
    'GdkRGBA':     'colour',
    'GdkPixbuf':   'image',
    'GtkWidget':   'ref',        # widget reference
    'GObject':     'ref',
    'GEnum':       'enum',
    'GFlags':      'flags',
}

def prop_kind(prop) -> str:
    try:
        vtype = prop.value_type.name
        for k, v in GPROP_KIND.items():
            if k in vtype:
                return v
        return 'scalar'
    except Exception:
        return 'scalar'


# ── Single widget atom extractor ──────────────────────────────────────────────

def extract_widget_atom(gtk_class_name: str, Gtk, GObject) -> dict:
    """
    Extract the complete atomic definition of one GTK widget class.

    Returns a .tgui-compatible dict with exactly one symbol — the atom.
    Properties and signals are encoded as sub-records in the symbol,
    ready for GHOST to learn as the widget's intrinsic vocabulary.
    """
    # Resolve the class
    cls = getattr(Gtk, gtk_class_name, None)
    if cls is None:
        return None

    # Parent class name
    try:
        parent_name = cls.__mro__[1].__name__ if len(cls.__mro__) > 1 else ''
    except Exception:
        parent_name = ''

    # Is it a container?
    try:
        is_container = issubclass(cls, Gtk.Container)
    except Exception:
        is_container = False

    # Properties
    properties = []
    try:
        for prop in GObject.list_properties(cls):
            # Skip inherited-from-GObject noise; keep widget-relevant props
            owner = prop.owner_type.name if hasattr(prop, 'owner_type') else ''
            if owner and not owner.startswith('Gtk') and owner not in ('GtkWidget',):
                # Still include it — all props are vocabulary
                pass
            properties.append({
                'name':    prop.name,
                'kind':    prop_kind(prop),
                'owner':   owner,
                'blurb':   prop.blurb or '',
            })
    except Exception:
        pass

    # Signals
    signals = []
    try:
        for sig_name in GObject.signal_list_names(cls):
            signals.append({
                'name':    sig_name,
                'handler': f'on_{gtk_class_name.lower()}_{sig_name.replace("-","_")}',
            })
    except Exception:
        pass

    # MMOE type
    mmoe_type = widget_class_to_mmoe(gtk_class_name)
    if mmoe_type == 'gui_unknown':
        # Infer from parent if possible
        if parent_name:
            mmoe_type = widget_class_to_mmoe(parent_name)

    # Compute MMID for this atom
    mmid = MMID(mmoe_type, instance=hash(gtk_class_name) & 0xFFFF)

    # Build the single-symbol .tgui
    symbol = {
        'id':          0,
        'kind':        mmoe_type,
        'label':       gtk_class_name,
        'gtk_class':   gtk_class_name,
        'parent_class':parent_name,
        'is_container':is_container,
        'x':           0,
        'y':           0,
        'depth':       0,
        'mmid_y':      mmid._y,
        'mmid_z':      mmid._z,
        'properties':  properties,
        'signals':     signals,
    }

    return {
        'tgui_version': '0.1',
        'source_file':  f'{gtk_class_name}.atom',
        'source_type':  'gir_atom',
        'symbols':      [symbol],
        'edges':        [],
        'sequence':     [0],
        'tgui_meta': {
            'widget_count':    1,
            'edge_count':      0,
            'mmoe_types_used': [mmoe_type],
            'property_count':  len(properties),
            'signal_count':    len(signals),
            'is_container':    is_container,
        },
    }


# ── Full library extraction ───────────────────────────────────────────────────

def extract_library(output_dir: str = None) -> dict:
    """
    Enumerate all Gtk.Widget subclasses via GObject introspection,
    extract one atom per class, save individual .tgui files, and
    build a combined _GHOST_CORPUS.tgui for bulk training.

    Returns a summary dict.
    """
    Gtk, GObject = _require_gtk()

    if output_dir is None:
        output_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'GHOST', 'GUI')
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("  TernOO GHOST Widget Library Extractor")
    print("=" * 60)
    print(f"  Output: {os.path.abspath(output_dir)}")
    print()

    # Discover all Gtk.Widget subclasses
    widget_classes = []
    for name in sorted(dir(Gtk)):
        if not name.startswith('Gtk') and not name[0].isupper():
            continue
        try:
            cls = getattr(Gtk, name)
            if (isinstance(cls, type) and
                issubclass(cls, Gtk.Widget) and
                cls is not Gtk.Widget):
                widget_classes.append(name)
        except Exception:
            pass

    print(f"  Discovered {len(widget_classes)} widget classes")
    print()

    atoms        = []
    corpus_syms  = []
    corpus_edges = []
    next_corpus_id = 0
    by_mmoe      = {}
    skipped      = []

    for name in widget_classes:
        atom = extract_widget_atom(name, Gtk, GObject)
        if atom is None:
            skipped.append(name)
            continue

        # Save individual atom file
        atom_path = os.path.join(output_dir, f'{name}.tgui')
        save_tgui(atom, atom_path)

        # Accumulate corpus
        sym = dict(atom['symbols'][0])
        sym['id'] = next_corpus_id
        corpus_syms.append(sym)

        mmoe = atom['tgui_meta']['mmoe_types_used'][0]
        by_mmoe.setdefault(mmoe, []).append(name)

        atoms.append({
            'name':     name,
            'mmoe':     mmoe,
            'props':    atom['tgui_meta']['property_count'],
            'signals':  atom['tgui_meta']['signal_count'],
            'container':atom['tgui_meta']['is_container'],
        })
        next_corpus_id += 1

    # Build corpus edges: connect atoms of the same MMOE type in sequence
    # (teaches GHOST that similar widget classes are interchangeable siblings)
    for mmoe_type, names in by_mmoe.items():
        ids = [i for i, a in enumerate(atoms) if a['mmoe'] == mmoe_type]
        for i in range(len(ids) - 1):
            corpus_edges.append({
                'src': ids[i], 'dst': ids[i+1],
                'privilege': 0, 'call_style': 0,
                'return_type': 1, 'seg_idx': 0,
                'offset': 0, 'waypoints': [], 'condition': ''
            })

    # Also add cross-type successor edges from MMOE_TYPES registry
    mmoe_id_map = {}
    for i, a in enumerate(atoms):
        mmoe_id_map.setdefault(a['mmoe'], i)   # first representative

    for mmoe_type in by_mmoe:
        t = MMOE_TYPES.get(mmoe_type, {})
        for succ in t.get('successors', []):
            if mmoe_type in mmoe_id_map and succ in mmoe_id_map:
                corpus_edges.append({
                    'src': mmoe_id_map[mmoe_type],
                    'dst': mmoe_id_map[succ],
                    'privilege': 0, 'call_style': 0,
                    'return_type': 1, 'seg_idx': 0,
                    'offset': 0, 'waypoints': [], 'condition': ''
                })

    # Save combined corpus
    corpus = {
        'tgui_version': '0.1',
        'source_file':  '_GHOST_CORPUS',
        'source_type':  'gir_library',
        'symbols':      corpus_syms,
        'edges':        corpus_edges,
        'sequence':     list(range(len(corpus_syms))),
        'tgui_meta': {
            'widget_count':    len(corpus_syms),
            'edge_count':      len(corpus_edges),
            'mmoe_types_used': sorted(by_mmoe.keys()),
            'atom_count':      len(atoms),
        },
    }
    corpus_path = os.path.join(output_dir, '_GHOST_CORPUS.tgui')
    save_tgui(corpus, corpus_path)

    # Report
    print(f"\n  {'Class':<30} {'MMOE type':<22} {'Props':>5} {'Sigs':>5} {'Ctr':>4}")
    print(f"  {'-'*30} {'-'*22} {'-'*5} {'-'*5} {'-'*4}")
    for a in atoms:
        print(f"  {a['name']:<30} {a['mmoe']:<22} "
              f"{a['props']:>5} {a['signals']:>5} "
              f"{'yes' if a['container'] else '':>4}")

    print(f"\n  {len(atoms)} atoms extracted → {output_dir}/")
    print(f"  Combined corpus → _GHOST_CORPUS.tgui "
          f"({len(corpus_edges)} edges)")
    if skipped:
        print(f"  Skipped: {skipped}")

    return {
        'atoms':       atoms,
        'by_mmoe':     by_mmoe,
        'output_dir':  os.path.abspath(output_dir),
        'corpus_path': corpus_path,
        'count':       len(atoms),
    }


# ── GHOST GUI brain training ──────────────────────────────────────────────────

def train_ghost_gui_brain(corpus_path: str = None, library_dir: str = None):
    """
    Train the GUI hemisphere brain (ghost_gui_brain.json) on the atomic
    widget corpus. Completely separate from flowcode_brain.json.

    Stage 1: individual atoms (vocabulary)
    Stage 2: combined corpus with successor edges (grammar seeds)
    """
    from ternoo_neural import FlowCodeBrain

    brain_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        'ghost_gui_brain.json')

    brain = FlowCodeBrain()

    # Load existing GUI brain if present (never touches flowcode_brain.json)
    if os.path.exists(brain_path):
        with open(brain_path) as f:
            data = json.load(f)
        brain.weights = data.get('weights', {})
        print(f"  Loaded existing GUI brain: {brain_path}")
    else:
        print(f"  Creating new GUI brain: {brain_path}")

    # Stage 1: train on every individual atom file
    if library_dir is None:
        library_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'GHOST', 'GUI')

    atom_count = 0
    if os.path.isdir(library_dir):
        for fname in sorted(os.listdir(library_dir)):
            if fname.endswith('.tgui') and not fname.startswith('_'):
                path = os.path.join(library_dir, fname)
                with open(path) as f:
                    tgui = json.load(f)
                brain.train_on_flowcode(tgui)
                atom_count += 1

    print(f"  Stage 1 complete: {atom_count} widget atoms")

    # Stage 2: train on combined corpus (successor grammar)
    if corpus_path and os.path.exists(corpus_path):
        with open(corpus_path) as f:
            corpus = json.load(f)
        brain.train_on_flowcode(corpus)
        print(f"  Stage 2 complete: corpus grammar")

    # Save — to ghost_gui_brain.json, never flowcode_brain.json
    brain.save(brain_path)
    print(f"\n  GUI brain saved: {brain_path}")
    print(f"  flowcode_brain.json untouched ✓")

    # Show learned transitions
    print(f"\n  Top GUI transitions learned:")
    print(f"  {'From':<22} → {'To':<22} {'Weight':>6}")
    print(f"  {'-'*22}   {'-'*22} {'-'*6}")
    rows = []
    for src, dsts in brain.weights.items():
        for dst, w in dsts.items():
            if w > 0:
                rows.append((src, dst, w))
    rows.sort(key=lambda x: -x[2])
    for src, dst, w in rows[:20]:
        print(f"  {src:<22} → {dst:<22} {w:>6}")


# ── Single atom preview ───────────────────────────────────────────────────────

def show_atom(gtk_class_name: str):
    """Print the full atom definition for one widget class."""
    Gtk, GObject = _require_gtk()
    atom = extract_widget_atom(gtk_class_name, Gtk, GObject)
    if atom is None:
        print(f"Widget class not found: {gtk_class_name}")
        return
    sym = atom['symbols'][0]
    print(f"\n{'='*60}")
    print(f"  {gtk_class_name}  [{sym['mmoe_type'] if 'mmoe_type' in sym else sym['kind']}]")
    print(f"  Parent: {sym['parent_class']}  Container: {sym['is_container']}")
    print(f"  MMID: Y={sym['mmid_y']}  Z={sym['mmid_z']}")
    print(f"\n  Properties ({len(sym['properties'])}):")
    for p in sym['properties']:
        print(f"    {p['name']:<35} [{p['kind']}]  {p['blurb'][:40]}")
    print(f"\n  Signals ({len(sym['signals'])}):")
    for s in sym['signals']:
        print(f"    {s['name']}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':

    if '--list' in sys.argv:
        Gtk, GObject = _require_gtk()
        names = []
        for name in sorted(dir(Gtk)):
            try:
                cls = getattr(Gtk, name)
                if isinstance(cls, type) and issubclass(cls, Gtk.Widget) and cls is not Gtk.Widget:
                    mmoe = widget_class_to_mmoe(name)
                    names.append((name, mmoe))
            except Exception:
                pass
        print(f"\n{'Class':<32} {'MMOE type'}")
        print(f"{'-'*32} {'-'*24}")
        for name, mmoe in names:
            print(f"{name:<32} {mmoe}")
        print(f"\n{len(names)} widget classes")

    elif '--atom' in sys.argv:
        idx = sys.argv.index('--atom')
        if idx + 1 < len(sys.argv):
            show_atom(sys.argv[idx + 1])
        else:
            print("Usage: --atom GtkButton")

    elif '--train' in sys.argv:
        result = extract_library()
        print(f"\n{'='*60}")
        print("  Training GHOST GUI brain...")
        print(f"{'='*60}")
        train_ghost_gui_brain(corpus_path=result['corpus_path'],
                              library_dir=result['output_dir'])

    else:
        # Default: extract only, no training
        result = extract_library()
        print(f"\n  Run with --train to feed GHOST.")
        print(f"  Run with --atom GtkButton to inspect one atom.")
        print(f"  Run with --list to see all classes and their MMOE types.")
