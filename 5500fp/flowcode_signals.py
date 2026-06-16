"""flowcode_signals.py — Signal vocabulary per widget kind (Phase 6D).

Each entry in SIGNAL_REGISTRY maps a widget kind to a list of signal
descriptors.  Each descriptor has at minimum 'name'.  The optional 'args'
field describes the signal's payload signature (informational — not enforced
at edit time; for runtime use in Stage 7+).

This file is data-only.  Extending the vocabulary = adding a dict entry.
No code branching on kind names anywhere in this module.

Structured identically to flowcode_properties.py (the property registry).

Runtime resolution (Stage 7+, not implemented in Phase 6D)
-----------------------------------------------------------
When a widget emits a signal at runtime, the signal fires with its argument
payload.  To find the handler:

  1. Start from the widget's RNODE in the stream.
  2. Walk UP the containment chain via STYLE_CONTAIN edges.
  3. At each level, check for a REDGE handler binding (T20=−1 form,
     FORM_HANDLER immediate) with src MAP = the widget's canvas position
     and signal name operand = the fired signal name.
  4. If found: invoke the handler (the flow at the dst MAP's flow_terminator).
  5. If not found at this level: continue walking up.
  6. If root reached with no match: the signal is unhandled (default no-op
     in Stage 7; debug mode may warn).

This gives lexical scope: a button inside dialog A resolves its handlers
in dialog A's scope, not dialog B's.

Phase 6D wires the BINDING (the editor side).  The walk-and-fire (the
runtime side) is Stage 7+ work.

Date: 2026-06-17, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

SIGNAL_REGISTRY: dict = {
    'gui_button':      [{'name': 'clicked'}],
    'gui_toggle':      [{'name': 'toggled',           'args': ['active:bool']}],
    'gui_check':       [{'name': 'toggled',           'args': ['checked:bool']}],
    'gui_radio':       [{'name': 'toggled',           'args': ['selected:bool']}],
    'gui_entry':       [{'name': 'changed',           'args': ['text:str']},
                        {'name': 'activated',         'args': ['text:str']}],
    'gui_window':      [{'name': 'close-requested'},
                        {'name': 'focus-changed',     'args': ['focused:bool']}],
    'gui_scale':       [{'name': 'value-changed',     'args': ['value:int']}],
    'gui_spinbutton':  [{'name': 'value-changed',     'args': ['value:int']}],
    'gui_combobox':    [{'name': 'selection-changed', 'args': ['index:int']}],
    # Widget kinds without signals get an implicit empty list via signals_for().
    # flow_* kinds intentionally have no signals — they are handler targets,
    # not signal emitters.
}


def signals_for(kind: str) -> list:
    """Return the signal list for a widget kind.  Empty list if none defined."""
    return SIGNAL_REGISTRY.get(kind, [])


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
