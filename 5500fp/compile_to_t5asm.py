"""compile_to_t5asm.py — FlowCode → 5500FP assembly compiler.

Phase 7b-1 path (backward-compat):
  If the WordStream has no gui_* widgets, compiles the first flow_terminator
  with is_entry=True to a PRINT_CHAR sequence + HALT.  Raises CompileError
  if no entry terminator exists.

Phase 7b-4 path (full PIGART program):
  If the WordStream contains any gui_* widget (gui_window, gui_button, etc.),
  compiles to a complete SDL program with:
    - PIGART_OPEN_WINDOW
    - Event loop: CLEAR + render all widgets + PRESENT + POLL_EVENT
    - MOUSE_DOWN hit-test → CALL handler block(s) per (widget, signal),
      resolved via walk-up containment-chain (Phase 6D §8.4)
    - KEY_DOWN handler → append char to focused gui_entry text buffer,
      fire CHANGED handler
    - TOGGLED dispatch for gui_check/gui_radio/gui_toggle: flips checked
      state in program state region, then dispatches TOGGLED then CLICKED
    - CHANGED dispatch for gui_entry: per-char key_down while entry focused
    - Handler blocks: print terminator label + RET (caller JMPs to event loop)
    - Containment-aware positions: LAYOUT_ABSOLUTE adds parent pos to child;
      LAYOUT_VBOX/HBOX stack children with 4px padding (compile-time resolved)
    - Program state region: 1 word per toggleable (checked), 65 words per
      entry (textlen + 64-char text buffer), 1 word focused_entry_id

Color constants exceed 10-trit LI range (±29524) so are in data section,
loaded via LI R20, label; LDW Rn, R20, 0.

Date: 2026-06-23, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import datetime
import os
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from word_stream import WordStream

# ---------------------------------------------------------------------------
# Public exception
# ---------------------------------------------------------------------------

class CompileError(Exception):
    """Raised when a WordStream cannot be compiled to .t5asm."""


# ---------------------------------------------------------------------------
# Syscall constants
# ---------------------------------------------------------------------------

_SYS_PRINT_CHAR = 3
_SYS_PRINT_NL   = 6

_PIG_OPEN_WINDOW  = 100
_PIG_CLEAR        = 101
_PIG_DRAW_RECT    = 102
_PIG_DRAW_OVAL    = 104
_PIG_DRAW_TEXT    = 105
_PIG_PRESENT      = 107
_PIG_POLL_EVENT   = 108
_PIG_SLEEP_MS     = 109
_PIG_CLOSE_WINDOW = 111

_PIG_EVENT_CLOSE      = 1
_PIG_EVENT_KEY_DOWN   = 2
_PIG_EVENT_MOUSE_DOWN = 4

# Signal IDs (widget_lib / flowcode_signals)
_SIGNAL_CLICKED = 300
_SIGNAL_TOGGLED = 301
_SIGNAL_CHANGED = 302

# ---------------------------------------------------------------------------
# Widget kind sets
# ---------------------------------------------------------------------------

# Kinds that flip a 'checked' bit on mouse-down and emit SIGNAL_TOGGLED
_TOGGLEABLE_KINDS = frozenset({'gui_check', 'gui_radio', 'gui_toggle'})

# Kinds that receive keyboard focus on mouse-down and emit SIGNAL_CHANGED
_ENTRY_KINDS = frozenset({'gui_entry'})

# Kinds that render their label via static DRAW_TEXT
# (gui_window/gui_dialog use label as SDL title; gui_entry uses state buffer)
_KINDS_WITH_DRAWN_TEXT = frozenset({
    'gui_button', 'gui_toggle',
    'gui_label',
    'gui_check', 'gui_radio',
})

# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------

_LAYOUT_VBOX_PADDING = 4   # pixels between children in vbox / hbox

# ---------------------------------------------------------------------------
# Color constants (exceed 10-trit LI range ±29524 → stored as .word data)
# ---------------------------------------------------------------------------

_COLOR_BG     = 0xF0F0F0   # light gray background
_COLOR_GRAY   = 0x808080   # window / dialog outline
_COLOR_PURPLE = 0xA070C0   # button fill (off-state toggle)
_COLOR_DARK   = 0x404040   # entry outline, check fill
_COLOR_LIGHT  = 0xC0C0C0   # generic fallback outline
_COLOR_BLACK  = 0x000000   # text
_COLOR_WHITE  = 0xFFFFFF   # white
_COLOR_TEAL   = 0x308080   # toggle on-state fill

_FONT_SIZE = 14


# ===========================================================================
# Phase 7b-1 helpers  (trivial print-and-halt path)
# ===========================================================================

def _find_entry_terminator(stream: 'WordStream') -> Optional[dict]:
    """Return the first flow_terminator with is_entry=True, or None."""
    for sym in (getattr(stream, '_flow_meta', None) or {}).values():
        if sym.get('kind') != 'flow_terminator':
            continue
        for p in sym.get('properties', []):
            if p.get('name') == 'is_entry' and p.get('value'):
                return sym
    return None


def _emit_print_char_sequence(label: str) -> list:
    """Emit LI R1 / LI R2 / SYSCALL stanza for each char in label."""
    if not label:
        return []
    lines = []
    for i, ch in enumerate(label):
        code = ord(ch)
        if i == 0:
            lines.append(f'    LI   R1, {_SYS_PRINT_CHAR:<6}  ; SYSCALL PRINT_CHAR')
        lines.append(f'    LI   R2, {code:<6}  ; {repr(ch)}')
        lines.append( '    SYSCALL')
    return lines


# ===========================================================================
# Phase 7b-4 helpers — walk-up handler resolution
# ===========================================================================

def _resolve_handler(stream: 'WordStream', widget_id: int,
                     signal_id: int) -> Optional[dict]:
    """Walk the containment chain from widget_id upward.

    At each level check for a binding matching signal_id.  Returns the first
    matching flow_terminator sym dict, or None.

    Implements Phase 6D §8.4 lexical scope: innermost binding wins.
    """
    current_id = widget_id
    while current_id is not None:
        w = stream._widget_meta.get(current_id)
        if w is None:
            break
        sig_ids = w.get('signal_ids') or {}
        # Keys may be int (in-memory) or str (JSON-round-tripped)
        binfo = sig_ids.get(signal_id) or sig_ids.get(str(signal_id))
        if binfo is not None:
            dst_x = binfo.get('dst_x', 0)
            dst_y = binfo.get('dst_y', 0)
            for sym in stream._flow_meta.values():
                if (sym.get('kind') == 'flow_terminator'
                        and sym.get('x', 0) == dst_x
                        and sym.get('y', 0) == dst_y):
                    return sym
        current_id = w.get('parent_id')
    return None


# ===========================================================================
# Phase 7b-4 helpers — layout-aware position resolution
# ===========================================================================

def _compute_effective_positions(stream: 'WordStream') -> dict:
    """Return {widget_id: (eff_x, eff_y, eff_w, eff_h)} for all gui_* widgets.

    LAYOUT_ABSOLUTE (default/grid/stacked): child x/y are relative to parent.
    LAYOUT_VBOX: children stacked vertically inside parent, 4px gaps.
    LAYOUT_HBOX: children stacked horizontally inside parent, 4px gaps.
    LAYOUT_GRID / LAYOUT_STACKED: treated as LAYOUT_ABSOLUTE (TODO future).
    """
    all_widgets = {w.id: w for w in stream.iter_widgets('gui_')}

    # Ordered child list per parent (insertion order preserved)
    children_of: dict = {}
    for w in all_widgets.values():
        if w.parent_id is not None:
            children_of.setdefault(w.parent_id, []).append(w)

    resolved: dict = {}

    def resolve(wid: int):
        if wid in resolved:
            return resolved[wid]
        w = all_widgets.get(wid)
        if w is None:
            return None

        if w.parent_id is None:
            resolved[wid] = (w.x, w.y, w.w, w.h)
            return resolved[wid]

        parent_pos = resolve(w.parent_id)
        if parent_pos is None:
            resolved[wid] = (w.x, w.y, w.w, w.h)
            return resolved[wid]

        px, py, _pw, _ph = parent_pos
        parent = all_widgets.get(w.parent_id)
        layout = (parent.layout_mode if parent else 'absolute') or 'absolute'

        if layout in ('absolute', 'grid', 'stacked'):
            # LAYOUT_ABSOLUTE: add parent top-left to child's own position
            resolved[wid] = (px + w.x, py + w.y, w.w, w.h)

        elif layout == 'vbox':
            # Stack vertically; x = parent.x + padding, y = accumulated
            y_off = py + _LAYOUT_VBOX_PADDING
            for sib in children_of.get(w.parent_id, []):
                if sib.id == wid:
                    break
                sp = resolve(sib.id)
                y_off += (sp[3] if sp else sib.h) + _LAYOUT_VBOX_PADDING
            resolved[wid] = (px + _LAYOUT_VBOX_PADDING, y_off, w.w, w.h)

        elif layout == 'hbox':
            # Stack horizontally; y = parent.y + padding, x = accumulated
            x_off = px + _LAYOUT_VBOX_PADDING
            for sib in children_of.get(w.parent_id, []):
                if sib.id == wid:
                    break
                sp = resolve(sib.id)
                x_off += (sp[2] if sp else sib.w) + _LAYOUT_VBOX_PADDING
            resolved[wid] = (x_off, py + _LAYOUT_VBOX_PADDING, w.w, w.h)

        else:
            resolved[wid] = (px + w.x, py + w.y, w.w, w.h)

        return resolved[wid]

    for wid in all_widgets:
        resolve(wid)
    return resolved


# ===========================================================================
# Phase 7b-4 helpers — program state allocation
# ===========================================================================

def _build_state_map(stream: 'WordStream') -> dict:
    """Allocate data-section labels for runtime-mutable widget state.

    Returns:
      state_map['focused']     = 'state_focused_entry'
      state_map[wid] (toggle)  = {'checked': 'state_checked_N'}
      state_map[wid] (entry)   = {'text': 'state_text_N', 'textlen': 'state_textlen_N'}
    """
    s: dict = {'focused': 'state_focused_entry'}
    for w in stream.iter_widgets('gui_'):
        if w.kind in _TOGGLEABLE_KINDS:
            s[w.id] = {'checked': f'state_checked_{abs(w.id)}'}
        elif w.kind in _ENTRY_KINDS:
            s[w.id] = {
                'text':    f'state_text_{abs(w.id)}',
                'textlen': f'state_textlen_{abs(w.id)}',
            }
    return s


# ===========================================================================
# Phase 7b-4 helpers — low-level render primitives
# ===========================================================================

def _load_color(color_label: str, dest_reg: str = 'R6') -> list:
    return [
        f'    LI   R20, {color_label}',
        f'    LDW  {dest_reg}, R20, 0',
    ]


def _emit_draw_rect(x: int, y: int, w: int, h: int,
                    color_label: str, filled: int) -> list:
    lines = [
        f'    LI   R1, {_PIG_DRAW_RECT}',
        f'    LI   R2, {x}',
        f'    LI   R3, {y}',
        f'    LI   R4, {w}',
        f'    LI   R5, {h}',
    ]
    lines += _load_color(color_label, 'R6')
    lines += [f'    LI   R7, {filled}', '    SYSCALL']
    return lines


def _emit_draw_oval(x: int, y: int, w: int, h: int,
                    color_label: str, filled: int) -> list:
    lines = [
        f'    LI   R1, {_PIG_DRAW_OVAL}',
        f'    LI   R2, {x}',
        f'    LI   R3, {y}',
        f'    LI   R4, {w}',
        f'    LI   R5, {h}',
    ]
    lines += _load_color(color_label, 'R6')
    lines += [f'    LI   R7, {filled}', '    SYSCALL']
    return lines


def _emit_draw_text(x: int, y: int, text_label: str, color_label: str) -> list:
    lines = [
        f'    LI   R1, {_PIG_DRAW_TEXT}',
        f'    LI   R2, {x}',
        f'    LI   R3, {y}',
        f'    LI   R4, {text_label}',
        f'    LI   R5, {_FONT_SIZE}',
    ]
    lines += _load_color(color_label, 'R6')
    lines.append('    SYSCALL')
    return lines


# ===========================================================================
# Phase 7b-4 helpers — widget string label tracking
# ===========================================================================

def _build_wstr_labels(stream: 'WordStream') -> dict:
    """Return {widget_id: data_label} for widgets with static drawn text."""
    result = {}
    for w in stream.iter_widgets():
        if w.kind in _KINDS_WITH_DRAWN_TEXT and w.label:
            result[w.id] = f'wstr_{abs(w.id)}'
    return result


# ===========================================================================
# Phase 7b-4 helpers — per-kind widget rendering (effective positions)
# ===========================================================================

def _emit_widget_render(widget, ex: int, ey: int, ew: int, eh: int,
                        wstr_labels: dict, state_map: dict) -> list:
    """t5asm lines for rendering one gui_* widget at its effective position."""
    k     = widget.kind
    lines = [f'    ; Render {k} #{widget.id} at ({ex},{ey}) [eff]']

    if k in ('gui_window', 'gui_dialog'):
        lines += _emit_draw_rect(ex, ey, ew, eh, 'color_gray', 0)

    elif k == 'gui_button':
        lines += _emit_draw_rect(ex, ey, ew, eh, 'color_purple', 1)
        if widget.id in wstr_labels:
            lines += _emit_draw_text(ex + 8, ey + eh // 2 - 8,
                                     wstr_labels[widget.id], 'color_black')

    elif k == 'gui_toggle':
        s = state_map.get(widget.id, {})
        checked_lbl = s.get('checked', '')
        # Draw purple base (unchecked appearance)
        lines += _emit_draw_rect(ex, ey, ew, eh, 'color_purple', 1)
        if checked_lbl:
            # Overdraw teal if checked
            skip_lbl = f'skip_toggle_fill_{abs(widget.id)}'
            lines += [
                f'    LI   R20, {checked_lbl}',
                f'    LDW  R15, R20, 0',
                f'    BEQZ R15, {skip_lbl}',
            ]
            lines += _emit_draw_rect(ex, ey, ew, eh, 'color_teal', 1)
            lines.append(f'{skip_lbl}:')
        if widget.id in wstr_labels:
            lines += _emit_draw_text(ex + 8, ey + eh // 2 - 8,
                                     wstr_labels[widget.id], 'color_black')

    elif k == 'gui_entry':
        lines += _emit_draw_rect(ex, ey, ew, eh, 'color_dark', 0)
        s = state_map.get(widget.id, {})
        text_lbl = s.get('text', '')
        if text_lbl:
            # Dynamic text from state buffer (pointer is the data-section label)
            lines += _emit_draw_text(ex + 8, ey + eh // 2 - 8,
                                     text_lbl, 'color_gray')

    elif k == 'gui_label':
        if widget.id in wstr_labels:
            lines += _emit_draw_text(ex, ey, wstr_labels[widget.id], 'color_black')

    elif k in ('gui_check', 'gui_radio'):
        s = state_map.get(widget.id, {})
        checked_lbl = s.get('checked', '')
        # Outer circle (always, unfilled)
        lines += _emit_draw_oval(ex, ey, 16, 16, 'color_dark', 0)
        if checked_lbl:
            # Inner fill only when checked
            skip_lbl = f'skip_check_fill_{abs(widget.id)}'
            lines += [
                f'    LI   R20, {checked_lbl}',
                f'    LDW  R15, R20, 0',
                f'    BEQZ R15, {skip_lbl}',
            ]
            lines += _emit_draw_oval(ex + 3, ey + 3, 10, 10, 'color_dark', 1)
            lines.append(f'{skip_lbl}:')
        if widget.id in wstr_labels:
            lines += _emit_draw_text(ex + 24, ey + 4,
                                     wstr_labels[widget.id], 'color_black')

    else:
        lines += _emit_draw_rect(ex, ey, ew, eh, 'color_light', 0)

    return lines


# ===========================================================================
# Phase 7b-4 — section emitters
# ===========================================================================

def _get_window_dims(stream: 'WordStream'):
    for w in stream.iter_widgets():
        if w.kind == 'gui_window':
            return w.w, w.h
    return 800, 600


def _get_window_title(stream: 'WordStream') -> str:
    for w in stream.iter_widgets():
        if w.kind == 'gui_window' and w.label:
            return w.label
    return '5500FP'


def _emit_string_words(text: str) -> list:
    lines = [f'    .word {ord(ch):<6}  ; {repr(ch)}' for ch in text]
    lines.append('    .word 0              ; null terminator')
    return lines


def _section_header(stream: 'WordStream', source_path: str) -> list:
    now     = datetime.datetime.now().astimezone()
    iso_now = now.strftime('%Y-%m-%dT%H:%M:%S%z')
    src     = os.path.basename(source_path) if source_path != '<in-memory>' else source_path
    return [
        '; Auto-generated by FlowCode compiler',
        f'; Source:    {src}',
        f'; Generated: {iso_now}',
        '; Phase:     7b-4 (walk-up handlers, TOGGLED/CHANGED, layout)',
        '',
        'main:',
        '',
    ]


def _section_open_window(stream: 'WordStream') -> list:
    w, h = _get_window_dims(stream)
    return [
        '    ; Open SDL window',
        f'    LI   R1, {_PIG_OPEN_WINDOW}',
        f'    LI   R2, {w}',
        f'    LI   R3, {h}',
        '    LI   R4, win_title_str',
        '    SYSCALL',
        '',
    ]


def _section_render(stream: 'WordStream', wstr_labels: dict,
                    eff_pos: dict, state_map: dict) -> list:
    """CLEAR + render all gui_* widgets at their layout-resolved positions."""
    lines = [
        '    ; --- Render frame ---',
        f'    LI   R1, {_PIG_CLEAR}',
    ]
    lines += _load_color('color_bg', 'R2')
    lines.append('    SYSCALL')
    lines.append('')
    for w in stream.iter_widgets():
        if not w.kind.startswith('gui_'):
            continue
        ex, ey, ew, eh = eff_pos.get(w.id, (w.x, w.y, w.w, w.h))
        lines += _emit_widget_render(w, ex, ey, ew, eh, wstr_labels, state_map)
        lines.append('')
    return lines


def _section_event_poll(has_entries: bool = False) -> list:
    """Present + poll + event-type decode + dispatch entry points."""
    lines = [
        '    ; Present frame',
        f'    LI   R1, {_PIG_PRESENT}',
        '    SYSCALL',
        '',
        '    ; Poll one event',
        f'    LI   R1, {_PIG_POLL_EVENT}',
        '    LI   R2, event_buf',
        '    SYSCALL',
        '    BEQZ R1, no_event_this_tick',
        '',
        '    ; Decode event type',
        '    LDW  R5, R2, 0          ; event_type = event_buf[0]',
        '',
        f'    LI   R6, {_PIG_EVENT_CLOSE}',
        '    BEQ  R5, R6, exit_prog',
        '',
        f'    LI   R6, {_PIG_EVENT_MOUSE_DOWN}',
        '    BEQ  R5, R6, handle_mouse_down',
        '',
    ]
    if has_entries:
        lines += [
            f'    LI   R6, {_PIG_EVENT_KEY_DOWN}',
            '    BEQ  R5, R6, handle_key_down',
            '',
        ]
    lines += [
        '    JMP  no_event_this_tick',
        '',
        'handle_mouse_down:',
        '    LDW  R10, R2, 1         ; mouse_x = event_buf[1]',
        '    LDW  R11, R2, 2         ; mouse_y = event_buf[2]',
        '',
        '    ; Any click outside a gui_entry clears keyboard focus',
        '    LI   R20, state_focused_entry',
        '    LI   R15, 0',
        '    STW  R15, R20, 0',
        '',
    ]
    return lines


def _section_hit_test(stream: 'WordStream', eff_pos: dict,
                      state_map: dict) -> list:
    """Hit-test block (inside handle_mouse_down), reverse widget order.

    Walk-up resolution: _resolve_handler walks parent chain for CLICKED and
    TOGGLED signals.  For toggleable widgets the checked state is flipped and
    TOGGLED fires before CLICKED (per spec D-order).  For gui_entry widgets,
    focus is set.  Handler calls use CALL so the hit block can chain multiple
    signals then JMP event_loop_top.
    """
    lines = []
    all_widgets = list(stream.iter_widgets())

    for widget in reversed(all_widgets):
        if not widget.kind.startswith('gui_'):
            continue
        ex, ey, ew, eh = eff_pos.get(widget.id,
                                      (widget.x, widget.y, widget.w, widget.h))
        is_toggleable = widget.kind in _TOGGLEABLE_KINDS
        is_entry      = widget.kind in _ENTRY_KINDS

        clicked_term = _resolve_handler(stream, widget.id, _SIGNAL_CLICKED)
        toggled_term = _resolve_handler(stream, widget.id, _SIGNAL_TOGGLED)

        has_action = is_toggleable or is_entry or clicked_term or toggled_term
        if not has_action:
            continue

        skip_lbl = f'skip_wid_{abs(widget.id)}'
        lines += [
            f'    ; Hit-test {widget.kind} #{widget.id} at ({ex},{ey},{ew},{eh})',
            f'    LI   R12, {ex}',
            f'    BLT  R10, R12, {skip_lbl}',
            f'    LI   R12, {ex + ew}',
            f'    BGT  R10, R12, {skip_lbl}',
            f'    LI   R12, {ey}',
            f'    BLT  R11, R12, {skip_lbl}',
            f'    LI   R12, {ey + eh}',
            f'    BGT  R11, R12, {skip_lbl}',
        ]

        # Flip checked state for toggleable widgets
        if is_toggleable:
            s = state_map.get(widget.id, {})
            checked_lbl = s.get('checked', '')
            if checked_lbl:
                lines += [
                    f'    ; Flip checked for {widget.kind} #{widget.id}',
                    f'    LI   R20, {checked_lbl}',
                    f'    LDW  R15, R20, 0',
                    f'    LI   R16, 1',
                    f'    SUB  R15, R16, R15   ; toggle: 1 - R15',
                    f'    STW  R15, R20, 0',
                ]

        # Set keyboard focus for entry widgets (focus was already cleared above)
        if is_entry:
            lines += [
                f'    ; Set focus to entry #{widget.id}',
                f'    LI   R20, state_focused_entry',
                f'    LI   R15, {widget.id}',
                f'    STW  R15, R20, 0',
            ]

        # Dispatch: TOGGLED first (per spec), then CLICKED
        if is_toggleable and toggled_term:
            lines.append(
                f'    CALL handler_term_{toggled_term["id"]}   ; TOGGLED')
        if clicked_term:
            lines.append(
                f'    CALL handler_term_{clicked_term["id"]}   ; CLICKED')

        lines.append('    JMP  event_loop_top')
        lines.append(f'{skip_lbl}:')
        lines.append('')

    lines += ['    JMP  no_event_this_tick', '']
    return lines


def _section_key_handler(stream: 'WordStream', state_map: dict) -> list:
    """Key-down handler: route to focused gui_entry, append char, fire CHANGED.

    Filters to printable ASCII (32-126).  Buffer limit: 63 chars.
    Uses 3-register ADD to compute dynamic text buffer address.
    """
    entry_widgets = [w for w in stream.iter_widgets('gui_')
                     if w.kind in _ENTRY_KINDS]
    if not entry_widgets:
        return []

    lines = [
        'handle_key_down:',
        '    LDW  R14, R2, 1         ; key_code = event_buf[1]',
        '',
        '    LI   R20, state_focused_entry',
        '    LDW  R15, R20, 0        ; focused entry ID (0=none)',
        '    BEQZ R15, no_event_this_tick',
        '',
    ]

    for w in entry_widgets:
        s           = state_map.get(w.id, {})
        text_lbl    = s.get('text', '')
        textlen_lbl = s.get('textlen', '')
        if not text_lbl:
            continue

        changed_term = _resolve_handler(stream, w.id, _SIGNAL_CHANGED)
        skip_not_us  = f'not_entry_{abs(w.id)}'
        skip_append  = f'skip_append_{abs(w.id)}'

        lines += [
            f'    LI   R16, {w.id}',
            f'    BNE  R15, R16, {skip_not_us}',
            '',
            f'key_on_entry_{abs(w.id)}:',
            '    ; Filter: printable ASCII 32-126',
            '    LI   R16, 32',
            f'    BLT  R14, R16, {skip_append}',
            '    LI   R16, 126',
            f'    BGT  R14, R16, {skip_append}',
            '',
            '    ; Check buffer limit (max 63 chars)',
            f'    LI   R20, {textlen_lbl}',
            '    LDW  R13, R20, 0',
            '    LI   R16, 63',
            f'    BGT  R13, R16, {skip_append}',
            '',
            '    ; text_buf[len] = key_code',
            f'    LI   R20, {text_lbl}',
            '    ADD  R20, R20, R13        ; R20 = &text_buf[len]',
            '    STW  R14, R20, 0',
            '',
            '    ; len++',
            f'    LI   R20, {textlen_lbl}',
            '    LDW  R13, R20, 0',
            '    ADDI R13, 1',
            '    STW  R13, R20, 0',
            '',
        ]
        if changed_term:
            lines.append(
                f'    CALL handler_term_{changed_term["id"]}   ; CHANGED')
        lines += [
            '    JMP  event_loop_top',
            '',
            f'{skip_append}:',
            '    JMP  no_event_this_tick',
            '',
            f'{skip_not_us}:',
        ]

    lines += ['    JMP  no_event_this_tick', '']
    return lines


def _section_tail_blocks() -> list:
    return [
        'no_event_this_tick:',
        f'    LI   R1, {_PIG_SLEEP_MS}',
        '    LI   R2, 16',
        '    SYSCALL',
        '    JMP  event_loop_top',
        '',
        'exit_prog:',
        f'    LI   R1, {_PIG_CLOSE_WINDOW}',
        '    SYSCALL',
        '    HALT',
        '',
    ]


def _section_handler_blocks(stream: 'WordStream') -> list:
    """One handler block per unique terminator referenced by any signal.

    Blocks end with RET so that hit/key blocks can CALL them and chain
    multiple signals before jumping back to event_loop_top.
    Deduplicates by terminator id.
    """
    lines      = []
    emitted    : set = set()

    for widget in stream.iter_widgets():
        if not widget.kind.startswith('gui_'):
            continue
        signals = [_SIGNAL_CLICKED]
        if widget.kind in _TOGGLEABLE_KINDS:
            signals.append(_SIGNAL_TOGGLED)
        if widget.kind in _ENTRY_KINDS:
            signals.append(_SIGNAL_CHANGED)

        for sig_id in signals:
            term = _resolve_handler(stream, widget.id, sig_id)
            if term is None:
                continue
            term_id = term['id']
            if term_id in emitted:
                continue
            emitted.add(term_id)

            lbl = term.get('label', '') or ''
            lines.append(f'handler_term_{term_id}:')
            lines.append(f'    ; Terminator "{lbl}"')
            if lbl:
                lines += _emit_print_char_sequence(lbl)
            lines.append(f'    LI   R1, {_SYS_PRINT_NL:<6}  ; SYSCALL PRINT_NL')
            lines.append( '    SYSCALL')
            lines.append( '    RET')
            lines.append('')

    return lines


def _section_data(stream: 'WordStream', wstr_labels: dict,
                  state_map: dict) -> list:
    """Data section: color words, window title, widget strings, event_buf, state."""
    lines = ['; ============ Data ============', '']

    # Color constants
    for name, val in [
        ('color_bg',     _COLOR_BG),
        ('color_gray',   _COLOR_GRAY),
        ('color_purple', _COLOR_PURPLE),
        ('color_dark',   _COLOR_DARK),
        ('color_light',  _COLOR_LIGHT),
        ('color_black',  _COLOR_BLACK),
        ('color_white',  _COLOR_WHITE),
        ('color_teal',   _COLOR_TEAL),
    ]:
        lines += [f'{name}:', f'    .word {val}']
    lines.append('')

    # Window title
    lines.append('win_title_str:')
    lines += _emit_string_words(_get_window_title(stream))
    lines.append('')

    # Static widget label strings
    for w in stream.iter_widgets():
        if w.id in wstr_labels and w.label:
            lines.append(f'{wstr_labels[w.id]}:')
            lines += _emit_string_words(w.label)
            lines.append('')

    # Event buffer (4 words: type, x/key, y/mod, spare)
    lines += [
        'event_buf:',
        '    .word 0              ; event type',
        '    .word 0              ; mouse_x / key_code',
        '    .word 0              ; mouse_y / key_mod',
        '    .word 0              ; spare',
        '',
        '; ---- Runtime state region ----',
        f'{state_map["focused"]}:',
        '    .word 0              ; focused entry id (0=none)',
        '',
    ]

    # Per-widget state
    for w in stream.iter_widgets('gui_'):
        s = state_map.get(w.id)
        if s is None:
            continue

        if w.kind in _TOGGLEABLE_KINDS:
            initial = 0
            for p in w.properties:
                if p.get('name') in ('checked', 'active'):
                    initial = 1 if p.get('value') else 0
                    break
            lines += [
                f'{s["checked"]}:',
                f'    .word {initial}         ; checked: {w.kind} #{w.id}',
                '',
            ]

        elif w.kind in _ENTRY_KINDS:
            # Initial text: check 'text' property first, fall back to label
            initial_text = w.label or ''
            for p in w.properties:
                if p.get('name') == 'text':
                    initial_text = str(p.get('value', ''))
                    break
            initial_len = len(initial_text)
            lines += [
                f'{s["textlen"]}:',
                f'    .word {initial_len}         ; textlen: entry #{w.id}',
                f'{s["text"]}:',
            ]
            for ch in initial_text:
                lines.append(f'    .word {ord(ch):<6}  ; {repr(ch)}')
            # Pad to 64 words (text + null terminator)
            for _ in range(64 - initial_len):
                lines.append('    .word 0')
            lines.append('')

    return lines


# ===========================================================================
# Phase 7b-4: full program compilation
# ===========================================================================

def _compile_full_program(stream: 'WordStream', source_path: str) -> str:
    wstr_labels = _build_wstr_labels(stream)
    eff_pos     = _compute_effective_positions(stream)
    state_map   = _build_state_map(stream)
    has_entries = any(w.kind in _ENTRY_KINDS for w in stream.iter_widgets('gui_'))

    parts: list = []
    parts += _section_header(stream, source_path)
    parts += _section_open_window(stream)
    parts += ['event_loop_top:']
    parts += _section_render(stream, wstr_labels, eff_pos, state_map)
    parts += _section_event_poll(has_entries=has_entries)
    parts += _section_hit_test(stream, eff_pos, state_map)
    parts += _section_tail_blocks()
    if has_entries:
        parts += _section_key_handler(stream, state_map)
    parts += _section_handler_blocks(stream)
    parts += _section_data(stream, wstr_labels, state_map)

    return '\n'.join(parts) + '\n'


# ===========================================================================
# Phase 7b-1: trivial print-and-halt (backward-compat)
# ===========================================================================

def _compile_trivial(stream: 'WordStream', source_path: str) -> str:
    entry = _find_entry_terminator(stream)
    if entry is None:
        raise CompileError("No entry terminator found")

    label = entry.get('label', '') or ''
    ex    = entry.get('x', 0)
    ey    = entry.get('y', 0)

    now     = datetime.datetime.now().astimezone()
    iso_now = now.strftime('%Y-%m-%dT%H:%M:%S%z')
    src     = os.path.basename(source_path) if source_path != '<in-memory>' else source_path

    lines = [
        '; Auto-generated by FlowCode compiler',
        f'; Source:    {src}',
        f'; Generated: {iso_now}',
        f'; Entry:     flow_terminator "{label}" at position ({ex}, {ey})',
        '; Phase:     7b-1 (PRINT_CHAR + HALT only)',
        '',
        'main:',
    ]
    if label:
        lines.append(f'    ; Print "{label}"')
        lines += _emit_print_char_sequence(label)
    else:
        lines.append('    ; (empty label — just emit newline)')
    lines += [
        f'    LI   R1, {_SYS_PRINT_NL:<6}  ; SYSCALL PRINT_NL',
        '    SYSCALL',
        '    HALT',
        '',
    ]
    return '\n'.join(lines)


# ===========================================================================
# Public API
# ===========================================================================

def compile_wordstream_to_t5asm(stream: 'WordStream',
                                 source_path: str = '<in-memory>') -> str:
    """Translate a WordStream to 5500FP assembly text.

    Phase detection:
      - Any gui_* widget → Phase 7b-4 full PIGART path
      - No gui_* widgets → Phase 7b-1 trivial print-and-halt path
    """
    if any(w.kind.startswith('gui_') for w in stream.iter_widgets()):
        return _compile_full_program(stream, source_path)
    return _compile_trivial(stream, source_path)
