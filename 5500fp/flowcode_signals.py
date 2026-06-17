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
