"""flowcode_signals.py — Signal vocabulary per widget kind (Bundle 12).

Each entry in SIGNAL_REGISTRY maps a widget kind to a list of signal
descriptors.  Each descriptor carries:
  'id'   — SIGNAL_* integer constant (300–307) used in the word stream
  'name' — human-readable signal name string (for display and legacy compat)
  'args' — optional payload signature list (informational; for Stage 7+ runtime)

This file is data-only.  Extending the vocabulary = one new SIGNAL_* constant
in widget_lib.py and one new dict entry here.  No code branching on kind names.

Structured identically to flowcode_properties.py (the property registry).

Runtime resolution (Stage 7+, not implemented in Bundle 12)
------------------------------------------------------------
When a widget emits a signal at runtime, the signal fires with its argument
payload.  To find the handler:

  1. Start from the widget's RNODE in the stream.
  2. Walk UP the containment chain via STYLE_CONTAIN edges.
  3. At each level, check for a REDGE handler binding (T20=−1 form,
     FORM_HANDLER immediate) with src MAP = the widget's canvas position
     and SIGNAL_* operand = the fired signal's ID.
  4. If found: invoke the handler (the flow at the dst MAP's flow_terminator).
  5. If not found at this level: continue walking up.
  6. If root reached with no match: the signal is unhandled (default no-op
     in Stage 7; debug mode may warn).

This gives lexical scope: a button inside dialog A resolves its handlers
in dialog A's scope, not dialog B's.

Bundle 12 wires the BINDING (the editor side, signal_id form).
The walk-and-fire (the runtime side) is Stage 7+ work.

Date: 2026-06-17, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import os
import sys
import importlib.util as _ilu

# ── Load widget_lib to get SIGNAL_* constants ─────────────────────────────────
_wl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'widget_lib.py')
_wl_spec = _ilu.spec_from_file_location('widget_lib', _wl_path)
_wl      = _ilu.module_from_spec(_wl_spec)
_wl_spec.loader.exec_module(_wl)

SIGNAL_CLICKED            = _wl.SIGNAL_CLICKED
SIGNAL_TOGGLED            = _wl.SIGNAL_TOGGLED
SIGNAL_CHANGED            = _wl.SIGNAL_CHANGED
SIGNAL_ACTIVATED          = _wl.SIGNAL_ACTIVATED
SIGNAL_CLOSE_REQUESTED    = _wl.SIGNAL_CLOSE_REQUESTED
SIGNAL_FOCUS_CHANGED      = _wl.SIGNAL_FOCUS_CHANGED
SIGNAL_VALUE_CHANGED      = _wl.SIGNAL_VALUE_CHANGED
SIGNAL_SELECTION_CHANGED  = _wl.SIGNAL_SELECTION_CHANGED

SIGNAL_REGISTRY: dict = {
    'gui_button':      [{'id': SIGNAL_CLICKED,           'name': 'clicked'}],
    'gui_toggle':      [{'id': SIGNAL_TOGGLED,           'name': 'toggled',
                         'args': ['active:bool']}],
    'gui_check':       [{'id': SIGNAL_TOGGLED,           'name': 'toggled',
                         'args': ['checked:bool']}],
    'gui_radio':       [{'id': SIGNAL_TOGGLED,           'name': 'toggled',
                         'args': ['selected:bool']}],
    'gui_entry':       [{'id': SIGNAL_CHANGED,           'name': 'changed',
                         'args': ['text:str']},
                        {'id': SIGNAL_ACTIVATED,         'name': 'activated',
                         'args': ['text:str']}],
    'gui_window':      [{'id': SIGNAL_CLOSE_REQUESTED,   'name': 'close-requested'},
                        {'id': SIGNAL_FOCUS_CHANGED,     'name': 'focus-changed',
                         'args': ['focused:bool']}],
    'gui_scale':       [{'id': SIGNAL_VALUE_CHANGED,     'name': 'value-changed',
                         'args': ['value:int']}],
    'gui_spinbutton':  [{'id': SIGNAL_VALUE_CHANGED,     'name': 'value-changed',
                         'args': ['value:int']}],
    'gui_combobox':    [{'id': SIGNAL_SELECTION_CHANGED, 'name': 'selection-changed',
                         'args': ['index:int']}],
    # Widget kinds without signals get an implicit empty list via signals_for().
    # flow_* kinds intentionally have no signals — they are handler targets,
    # not signal emitters.
}


def signals_for(kind: str) -> list:
    """Return the signal list for a widget kind.  Empty list if none defined."""
    return SIGNAL_REGISTRY.get(kind, [])


def signal_name_to_id(name: str):
    """Reverse lookup: signal name → SIGNAL_* ID, or None if not found.

    Used for migrating Phase 6D-era .ternoo files that stored signal bindings
    by truncated name string.  The 3-char truncation Phase 6D used
    ('clicked'→'cli') is NOT handled here — callers should try the full name
    first, then fall back to truncated-prefix matching if needed.
    """
    for entries in SIGNAL_REGISTRY.values():
        for entry in entries:
            if entry['name'] == name:
                return entry['id']
    return None


def signal_id_to_name(sig_id: int):
    """Forward lookup: SIGNAL_* ID → signal name string, or None if not found.

    Used for display in the property panel and for populating handler_for()
    return tuples.
    """
    for entries in SIGNAL_REGISTRY.values():
        for entry in entries:
            if entry['id'] == sig_id:
                return entry['name']
    return None


def common_signals_for_kinds(kinds: list) -> list:
    """Return signals common (by name) to ALL kinds in the list.

    Used by multi-select: the Signals section shows only signals that appear
    in every selected widget kind's registry.  Order follows the first kind.
    """
    if not kinds:
        return []
    sets = [set(s['name'] for s in signals_for(k)) for k in kinds]
    common_names = sets[0].intersection(*sets[1:])
    # Preserve order from the first kind
    return [s for s in signals_for(kinds[0]) if s['name'] in common_names]


# ── Phase 6E: migrated from flowcode_bridge.py ───────────────────────────────

_build_redge_handler = _wl.build_redge_handler


def build_handler_bindings(widgets: dict, flow_symbols: dict) -> list:
    """Build REDGE handler-binding words for all signal bindings in widgets.

    Walks widgets dict, collecting each widget's 'signal_ids' dict
    (signal_id: int → {'dst_x': int, 'dst_y': int}).  For each binding,
    emits one build_redge_handler() word sequence.

    Bundle 12: uses SIGNAL_* integer IDs, 4-operand / 5-word form.
    widget_dict['bindings'] has been retired; reads only 'signal_ids'.

    Returns a flat list of words suitable for appending to the combined
    stream in _guic_sync_stream().

    Editor-side only.  No runtime firing here — Stage 7+.
    """
    _GC_SCALE = 10   # pixel → Meccano coordinate scale (matches ghost_meccano.FC_GRID_TO_MECCANO)
    words = []
    for wid, w in widgets.items():
        sig_ids = w.get('signal_ids') or {}
        wx = w.get('x', 0)
        wy = w.get('y', 0)
        for signal_id, binfo in sig_ids.items():
            if not binfo:
                continue
            dx = binfo.get('dst_x', 0)
            dy = binfo.get('dst_y', 0)
            src_mc = (wx // _GC_SCALE, wy // _GC_SCALE)
            dst_mc = (dx // _GC_SCALE, dy // _GC_SCALE)
            words.extend(_build_redge_handler(src_mc, dst_mc, int(signal_id)))
    return words


# ═════════════════════════════════════════════════════════════════════════════
# Phase 7c-2 — Name-based auto-wiring
#
# A GUI widget's signal binds to a flow_terminator *by name agreement*: for a
# widget named `submit_button` emitting `clicked`, the canonical handler name is
# `submit_button_clicked`. If an entry flow_terminator with that exact name
# exists, an implicit binding is materialised into the widget's `signal_ids`
# dict (the Bundle-12 data model) and marked `auto_wired = True`.
#
# These functions operate on a WordStream via its `_widget_meta` (widgets) and
# `_flow_meta` (flow symbols) aliases — headless, no tkinter. `materialize_*`
# recomputes the entire canonical set from current names, so a single call after
# any name/create/delete/move change is the whole "rename cascade" (L4).
# ═════════════════════════════════════════════════════════════════════════════

def canonical_handler_name(widget_name: str, signal_name: str) -> str:
    """Canonical handler name for a (widget, signal): `<widget_name>_<signal>`.

    The signal name is normalised to an identifier (hyphens → underscores), so
    `value-changed` on `slider` → `slider_value_changed`. An empty widget name
    yields '' (a nameless widget cannot be wired by name).
    """
    if not widget_name:
        return ''
    return f"{widget_name}_{signal_name.replace('-', '_')}"


def auto_handler_names_for_widget(widget: dict) -> list:
    """List of (signal_id, signal_name, handler_name) for every signal a widget
    emits. Used by the property panel's read-only handler-name display."""
    name = widget.get('name', '')
    return [(s['id'], s['name'], canonical_handler_name(name, s['name']))
            for s in signals_for(widget.get('kind', ''))]


def all_handler_names(stream) -> set:
    """Every canonical handler name implied by the widgets in `stream`.

    Drives autocompletion of the flow_terminator name field — type `button1_`
    and the available handlers surface.
    """
    out = set()
    for w in getattr(stream, '_widget_meta', {}).values():
        nm = w.get('name', '')
        if not nm:
            continue
        for s in signals_for(w.get('kind', '')):
            out.add(canonical_handler_name(nm, s['name']))
    return out


def _flow_is_entry(sym: dict) -> bool:
    """True if a flow symbol dict has its is_entry property set."""
    for p in sym.get('properties', []):
        if p.get('name') == 'is_entry':
            return bool(p.get('value'))
    return False


def _entry_terminators_by_name(stream) -> dict:
    """Map name → flow_terminator dict for entry terminators with a non-empty
    name. Names are globally unique (Phase 7c-1), so the map is unambiguous."""
    out = {}
    for sym in getattr(stream, '_flow_meta', {}).values():
        if sym.get('kind') == 'flow_terminator' and _flow_is_entry(sym):
            nm = sym.get('name', '')
            if nm:
                out[nm] = sym
    return out


def compute_auto_wired_bindings(stream) -> dict:
    """Pure function: the canonical set of auto-wired bindings implied by the
    current name agreements.

    Returns {widget_id: {signal_id: {'dst_x': int, 'dst_y': int}}}, where the
    dst is the matched entry terminator's canvas position.
    """
    terms = _entry_terminators_by_name(stream)
    result: dict = {}
    for wid, w in getattr(stream, '_widget_meta', {}).items():
        wname = w.get('name', '')
        if not wname:
            continue
        for s in signals_for(w.get('kind', '')):
            term = terms.get(canonical_handler_name(wname, s['name']))
            if term is not None:
                result.setdefault(wid, {})[s['id']] = {
                    'dst_x': term.get('x', 0), 'dst_y': term.get('y', 0)}
    return result


def _norm_sig_ids(raw: dict) -> dict:
    """Normalise a signal_ids dict's keys to int (JSON round-trips them to str),
    dropping falsy entries."""
    out = {}
    for k, v in (raw or {}).items():
        if not v:
            continue
        try:
            ik = int(k)
        except (ValueError, TypeError):
            ik = k
        out[ik] = v
    return out


def materialize_auto_wired_bindings(stream) -> int:
    """Update every widget's `signal_ids` to match the canonical auto-wired set.

    - Manual bindings (no/false `auto_wired`) are preserved and win per-signal.
    - Auto-wired entries are (re)generated to match current names/positions;
      stale ones (name agreement broken, terminator moved/deleted) are dropped.
    Operates in place on stream._widget_meta. Returns the number of widgets whose
    signal_ids changed.
    """
    desired = compute_auto_wired_bindings(stream)
    changed = 0
    for wid, w in getattr(stream, '_widget_meta', {}).items():
        norm = _norm_sig_ids(w.get('signal_ids'))
        want = desired.get(wid, {})
        new_sig = {}
        # Manual bindings preserved verbatim; they take precedence per-signal.
        for sid, binfo in norm.items():
            if not binfo.get('auto_wired'):
                new_sig[sid] = binfo
        # Auto-wired bindings for any signal not manually bound.
        for sid, dst in want.items():
            if sid in new_sig:
                continue
            new_sig[sid] = {'dst_x': dst['dst_x'], 'dst_y': dst['dst_y'],
                            'auto_wired': True}
        if new_sig != norm:
            changed += 1
            w['signal_ids'] = new_sig
        elif 'signal_ids' in w:
            w['signal_ids'] = norm   # keep normalised (int keys)
    return changed


def find_nonconforming_manual_bindings(stream) -> list:
    """Manual signal_ids entries that do NOT match the naming convention.

    A manual binding conforms when the terminator it points to is an entry
    terminator whose name equals the widget's canonical handler name for that
    signal. Non-conforming manual bindings are the legacy edges the load path
    prompts about. Returns a list of
    {widget_id, signal_id, handler, bound_terminator, term}.
    """
    pos2term = {}
    for sym in getattr(stream, '_flow_meta', {}).values():
        if sym.get('kind') == 'flow_terminator':
            pos2term[(sym.get('x', 0), sym.get('y', 0))] = sym
    out = []
    for wid, w in getattr(stream, '_widget_meta', {}).items():
        for sid, binfo in _norm_sig_ids(w.get('signal_ids')).items():
            if binfo.get('auto_wired'):
                continue   # only manual edges
            sname = signal_id_to_name(sid)
            if sname is None:
                continue
            canon = canonical_handler_name(w.get('name', ''), sname)
            term = pos2term.get((binfo.get('dst_x', 0), binfo.get('dst_y', 0)))
            conforms = (term is not None and _flow_is_entry(term)
                        and term.get('name', '') == canon and canon != '')
            if not conforms:
                out.append({'widget_id': wid, 'signal_id': sid,
                            'handler': canon,
                            'bound_terminator': term.get('name', '') if term else '',
                            'term': term})
    return out


def reconcile_loaded_bindings(stream) -> list:
    """Load-path reconciliation. Drops manual bindings that already conform to
    the naming convention (they're regenerated as auto-wired), then materialises.
    Returns the list of remaining non-conforming manual bindings so the caller
    can show the one-time legacy prompt.
    """
    nonconf = find_nonconforming_manual_bindings(stream)
    nonconf_keys = {(it['widget_id'], it['signal_id']) for it in nonconf}
    for wid, w in getattr(stream, '_widget_meta', {}).items():
        raw = w.get('signal_ids') or {}
        for k in list(raw.keys()):
            binfo = raw[k]
            if not binfo or binfo.get('auto_wired'):
                continue
            try:
                sid = int(k)
            except (ValueError, TypeError):
                sid = k
            if (wid, sid) not in nonconf_keys:
                del raw[k]   # conforming manual → regenerated as auto below
    materialize_auto_wired_bindings(stream)
    return nonconf


def conform_manual_bindings(stream) -> int:
    """'Update names' action: rename each non-conforming manual binding's target
    terminator to the widget's canonical handler name, so the binding survives as
    an auto-wired one. Returns the number of terminators renamed."""
    n = 0
    for item in find_nonconforming_manual_bindings(stream):
        term, canon = item['term'], item['handler']
        if term is not None and canon:
            term['name'] = canon
            n += 1
    # Renamed terminators now match the convention; reconcile drops the (now
    # conforming) manual entries and regenerates them as auto-wired.
    reconcile_loaded_bindings(stream)
    return n
