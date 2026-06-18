#!/usr/bin/env python3
"""flowcode_properties.py — GHOST Canvas property registry (TernOO v0.7 Bundle 7)

Maps widget kinds to their editable properties.  Used by the GHOST Canvas
right-side property panel to build per-kind editor widgets.

Property kinds:
  string  — single-line text entry; commit on Enter or focus-loss
  int     — numeric spinbox; commit on Enter, focus-loss, or each spin click
  choice  — dropdown of enumerated options; commit on selection
  bool    — checkbox; commit on toggle

COMMON_PROPERTIES always present regardless of kind.
WIDGET_PROPERTIES adds kind-specific props (written to the widget's
  'properties' list as {"name": str, "value": any}).
COMMON_PROPERTIES entries write to the widget's top-level dict field.

Date: 2026-06-16, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Spec: CWC-Bundle-7-Stages-4-5.md §2.4
"""

from __future__ import annotations

COMMON_PROPERTIES: list[dict] = [
    {'name': 'x',     'kind': 'int',    'section': 'Geometry'},
    {'name': 'y',     'kind': 'int',    'section': 'Geometry'},
    {'name': 'w',     'kind': 'int',    'section': 'Geometry', 'min': 20},
    {'name': 'h',     'kind': 'int',    'section': 'Geometry', 'min': 20},
    {'name': 'label', 'kind': 'string', 'section': 'Appearance'},
]

_LAYOUT_OPTIONS = ['absolute', 'hbox', 'vbox', 'grid', 'stacked']
_LAYOUT_PROP = {'name': 'layout_mode', 'kind': 'choice', 'section': 'Container',
                'options': _LAYOUT_OPTIONS}

WIDGET_PROPERTIES: dict[str, list[dict]] = {
    'gui_window': [
        {'name': 'title', 'kind': 'string', 'section': 'Appearance'},
        _LAYOUT_PROP,
    ],
    'gui_dialog': [
        {'name': 'title', 'kind': 'string', 'section': 'Appearance'},
        {'name': 'modal', 'kind': 'bool',   'section': 'Appearance'},
        _LAYOUT_PROP,
    ],
    'gui_box':      [_LAYOUT_PROP],
    'gui_grid':     [_LAYOUT_PROP],
    'gui_frame':    [_LAYOUT_PROP],
    'gui_notebook': [_LAYOUT_PROP],
    'gui_button':   [],
    'gui_entry':    [{'name': 'placeholder', 'kind': 'string', 'section': 'Appearance'}],
    'gui_label':    [],
    'gui_check':    [{'name': 'checked',  'kind': 'bool', 'section': 'State'}],
    'gui_toggle':   [{'name': 'active',   'kind': 'bool', 'section': 'State'}],
    'gui_radio':    [{'name': 'selected', 'kind': 'bool', 'section': 'State'}],
    'gui_progress': [{'name': 'value', 'kind': 'int', 'section': 'State',
                      'min': 0, 'max': 100}],
    'gui_scale':    [{'name': 'value', 'kind': 'int', 'section': 'State'},
                     {'name': 'min',   'kind': 'int', 'section': 'State'},
                     {'name': 'max',   'kind': 'int', 'section': 'State'}],
    'gui_spinbutton': [{'name': 'value', 'kind': 'int', 'section': 'State'}],
}


# ── Phase 6C: FlowCode tab symbol properties ─────────────────────────────────
# Flow symbols share COMMON_PROPERTIES (x, y, w, h, label) and gain
# kind-specific properties listed below.  The 'is_entry' flag on
# flow_terminator designates a flow-entry point; Phase 6D's handler-binding
# picker consumes it.  The 'condition' string on flow_decision captures the
# branch predicate expression.
WIDGET_PROPERTIES.update({
    'flow_terminator': [
        {'name': 'is_entry', 'kind': 'bool',   'section': 'Flow'},
    ],
    'flow_process':    [],
    'flow_decision':   [
        {'name': 'condition', 'kind': 'string', 'section': 'Flow'},
    ],
    'flow_io':         [],
    'flow_subroutine': [
        {'name': 'target',    'kind': 'string', 'section': 'Flow'},
    ],
    'flow_connector':  [],
})


def properties_for(kind: str) -> list[dict]:
    """Merged property list (COMMON + kind-specific) for a widget kind.

    Kinds not in WIDGET_PROPERTIES receive COMMON_PROPERTIES only.
    """
    return COMMON_PROPERTIES + WIDGET_PROPERTIES.get(kind, [])


def common_properties_for_kinds(kinds: list[str]) -> list[dict]:
    """Return properties present in ALL listed kinds (intersection).

    Used for multi-select property panel: only show props shared by every
    selected widget kind.

    Equality is by property 'name' only — if name matches, the first
    kind's property descriptor is used.
    """
    if not kinds:
        return []
    sets = [properties_for(k) for k in kinds]
    base_names = {p['name'] for p in sets[0]}
    for s in sets[1:]:
        base_names &= {p['name'] for p in s}
    # Return in the order they appear in the first kind's list
    return [p for p in sets[0] if p['name'] in base_names]
