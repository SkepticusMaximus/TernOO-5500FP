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
        # Focus indicator: if this entry is the focused one, overdraw a teal
        # border so a click gives visible feedback (Piece 3).
        skip_focus = f'skip_focus_{abs(widget.id)}'
        lines += [
            '    LI   R20, state_focused_entry',
            '    LDW  R15, R20, 0',
            f'    LI   R16, {widget.id}',
            f'    SUB  R15, R15, R16',
            f'    BNEZ R15, {skip_focus}',
        ]
        lines += _emit_draw_rect(ex - 1, ey - 1, ew + 2, eh + 2, 'color_teal', 0)
        # Text caret at the end of the current text (focused only).  Monospace
        # font (DejaVu Sans Mono @ 14px) advances ~8px/char, so the caret x is
        # text_start + len*8.  Drawn as a 1px teal filled bar (Piece 5).
        s = state_map.get(widget.id, {})
        textlen_lbl = s.get('textlen', '')
        text_x = ex + 8
        text_y = ey + eh // 2 - 8
        if textlen_lbl:
            lines += [
                '    ; Caret at end of text',
                f'    LI   R20, {textlen_lbl}',
                '    LDW  R2, R20, 0',
                '    MULI R2, R2, 8       ; len * char advance',
                f'    LI   R3, {text_x}',
                '    ADD  R2, R2, R3      ; caret_x = text_x + len*8',
                f'    LI   R1, {_PIG_DRAW_RECT}',
                f'    LI   R3, {text_y}',
                '    LI   R4, 1           ; caret width',
                f'    LI   R5, {_FONT_SIZE}     ; caret height',
            ]
            lines += _load_color('color_teal', 'R6')
            lines += ['    LI   R7, 1           ; filled', '    SYSCALL']
        lines.append(f'{skip_focus}:')
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


# ===========================================================================
# Stage 8-3-RT: Sheet cell compilation (static formulas → literals)
# ===========================================================================

_CELL_W, _CELL_H = 80, 24          # grid geometry (mirrors the Sheet editor)
_CELL_HDR_W, _CELL_HDR_H = 40, 22

try:
    import sheet_formula as _sheetf
except Exception:                  # pragma: no cover
    _sheetf = None


def _ast_has_native(node) -> bool:
    """True if a formula AST references WIDGET / SIGNAL_LAST (→ dynamic)."""
    if not isinstance(node, tuple):
        return False
    t = node[0]
    if t == 'call' and node[1] in ('WIDGET', 'SIGNAL_LAST'):
        return True
    if t == 'member':
        return _ast_has_native(node[1])
    if t == 'call':
        return any(_ast_has_native(a) for a in node[2])
    if t == 'bin':
        return _ast_has_native(node[2]) or _ast_has_native(node[3])
    if t == 'unary':
        return _ast_has_native(node[2])
    return False


def _cell_render_info(stream: 'WordStream') -> list:
    """[(cell_id, row, col, display_str, numeric, is_static)] for every cell.

    Static formulas (constants / other static cells) are evaluated at compile
    time and their result becomes a literal. Dynamic formulas (WIDGET / signal
    refs) emit a placeholder 0 here — Stage 8-3-RT-dynamic (Step 4) emits their
    recompute fragments. cell_value / cell_text emit their literal directly.
    """
    cells = getattr(stream, '_cell_meta', {}) or {}
    if not cells or _sheetf is None:
        return []
    dynamic = set()
    for rc, cell in cells.items():
        if cell.get('kind') == 'cell_formula':
            src = str(cell.get('value', ''))
            expr = src[1:] if src.startswith('=') else src
            try:
                if _ast_has_native(_sheetf.parse(expr)):
                    dynamic.add(rc)
            except Exception:
                dynamic.add(rc)        # unparseable → treat as non-static
    results, errors = _sheetf.evaluate_sheet(cells)
    out = []
    for rc, cell in cells.items():
        r, c = rc
        is_static = rc not in dynamic
        if cell.get('kind') == 'cell_formula':
            if is_static:
                # Static cell: compile-time value, or its error string (Part 7).
                if rc in errors:
                    disp = errors[rc]            # e.g. '#DIV/0!' / '#NAME?'
                elif rc in results:
                    disp = _sheetf.format_result(results[rc])
                else:
                    disp = '0'
            else:
                disp = '0'   # dynamic: recompute fills value/err slots at runtime
        else:
            disp = str(cell.get('value', ''))
        try:
            numeric = int(float(disp))
        except (ValueError, TypeError):
            numeric = 0
        out.append((cell.get('id', 0), r, c, disp, numeric, is_static))
    return out


def _emit_cell_render(stream: 'WordStream') -> list:
    """DRAW_TEXT for each Sheet cell at its grid position (each frame)."""
    lines = []
    for cid, r, c, _disp, _num, stat in _cell_render_info(stream):
        cx = _CELL_HDR_W + c * _CELL_W + 4
        cy = _CELL_HDR_H + r * _CELL_H + 6
        lines.append(f'    ; Render cell ({r},{c}) #{cid}')
        if stat:
            lines += _emit_draw_text(cx, cy, f'cellstr_{cid}', 'color_black')
        else:
            # Stage 8-3-RT-dynamic + Part 7: if the cell's error slot is set,
            # draw the Excel-style error string; else convert the live value.
            ok = f'cellok_{cid}'; done = f'celldone_{cid}'; nm = f'cellerrnm_{cid}'
            lines += [
                f'    LI   R20, state_cell_{cid}_err',
                f'    LDW  R19, R20, 0',
                f'    BEQZ R19, {ok}',
                f'    LI   R16, 1',
                f'    SUB  R17, R19, R16',
                f'    BNEZ R17, {nm}',       # err != 1 -> not DIV/0
            ]
            lines += _emit_draw_text(cx, cy, 'errstr_div0', 'color_black')
            lines += [f'    JMP  {done}', f'{nm}:']
            lines += _emit_draw_text(cx, cy, 'errstr_name', 'color_black')
            lines += [f'    JMP  {done}', f'{ok}:']
            lines.append(f'    LI   R21, state_cell_{cid}')
            lines.append(f'    LDW  R21, R21, 0')
            lines.append(f'    LI   R22, cellbuf_{cid}')
            lines.append('    CALL int_to_str')
            lines += _emit_draw_text(cx, cy, f'cellbuf_{cid}', 'color_black')
            lines.append(f'{done}:')
        lines.append('')
    return lines


def _emit_cell_data(stream: 'WordStream') -> list:
    """Cell display strings + state-region literals (state_cell_<id>)."""
    lines = []
    info = _cell_render_info(stream)
    if info:
        lines.append('; ---- Sheet cells (Stage 8-3-RT) ----')
    for cid, r, c, disp, num, stat in info:
        lines.append(f'cellstr_{cid}:')
        lines += _emit_string_words(disp)
        lines.append(f'state_cell_{cid}:')
        lines.append(f'    .word {num:<6}  ; cell ({r},{c}) '
                     f'{"static" if stat else "dynamic(placeholder)"}')
        lines.append('')
    # Stage 8-3-RT-dynamic / 8-8-RT: SIGNAL_LAST slots (handler writes = Part 6)
    for sig in _signal_last_names(stream):
        lines.append(f'state_signal_last_{sig}:')
        lines.append('    .word 0')
        lines.append('')
    # Stage 8-3-RT-dynamic: per-cell render buffers + int_to_str scratch
    dyn = _dynamic_cells(stream)
    if dyn:
        lines.append('_its_scratch:')
        lines += ['    .word 0'] * 16
        lines.append('')
        # Part 7: runtime error strings (drawn when a cell's err slot is set)
        lines.append('errstr_div0:'); lines += _emit_string_words('#DIV/0!'); lines.append('')
        lines.append('errstr_name:'); lines += _emit_string_words('#NAME?'); lines.append('')
        for cid, _rc, _ast in dyn:
            lines.append(f'cellbuf_{cid}:')
            lines += ['    .word 0'] * 16
            lines.append(f'state_cell_{cid}_err:')
            lines.append('    .word 0')
            lines.append('')
    return lines


def _signal_last_names(stream) -> list:
    """Distinct signal names referenced by SIGNAL_LAST in any dynamic cell."""
    names = []
    for _cid, _rc, ast in _dynamic_cells(stream):
        _collect_signal_last(ast, names)
    seen, out = set(), []
    for n in names:
        if n not in seen:
            seen.add(n); out.append(n)
    return out


def _collect_signal_last(node, acc):
    if not isinstance(node, tuple):
        return
    if node[0] == 'call' and node[1] == 'SIGNAL_LAST' and node[2] \
            and node[2][0][0] == 'str':
        acc.append(node[2][0][1])
    if node[0] == 'call':
        for a in node[2]:
            _collect_signal_last(a, acc)
    elif node[0] == 'bin':
        _collect_signal_last(node[2], acc); _collect_signal_last(node[3], acc)
    elif node[0] == 'unary':
        _collect_signal_last(node[2], acc)
    elif node[0] == 'member':
        _collect_signal_last(node[1], acc)


# ---------------------------------------------------------------------------
# Stage 8-3-RT-dynamic (Part 3): recompute subroutines + per-frame trigger
# ---------------------------------------------------------------------------

try:
    import formula_t5asm as _fxc
except Exception:                  # pragma: no cover
    _fxc = None

try:
    import command_t5asm as _cmdc
    import flowcode_commands as _cmdreg
except Exception:                  # pragma: no cover
    _cmdc = None
    _cmdreg = None


def _dynamic_cells(stream):
    """[(cid, rc, ast)] for each dynamic formula cell (references WIDGET /
    SIGNAL_LAST), in a topological order (cells depending on other dynamic
    cells come after them)."""
    if _fxc is None:
        return []
    cells = getattr(stream, '_cell_meta', {}) or {}
    dyn = {}      # rc -> (cid, ast)
    for rc, cell in cells.items():
        if cell.get('kind') != 'cell_formula':
            continue
        src = str(cell.get('value', ''))
        expr = src[1:] if src.startswith('=') else src
        try:
            ast = _sheetf.parse(expr)
        except Exception:
            continue
        if _ast_has_native(ast):
            dyn[rc] = (cell.get('id'), ast)
    # address/name → rc, to order cells that reference other dynamic cells
    addr2rc, name2rc = {}, {}
    for rc, cell in cells.items():
        addr2rc[_sheetf.rc_to_a1(*rc)] = rc
        if cell.get('name'):
            name2rc[cell['name']] = rc
    deps = {}
    for rc, (_cid, ast) in dyn.items():
        d = set()
        for ref in _sheetf.extract_refs(ast):
            t = addr2rc.get(ref) or name2rc.get(ref)
            if t in dyn:
                d.add(t)
        deps[rc] = d
    # simple topological sort (deps first)
    order, seen = [], set()
    def visit(rc):
        if rc in seen:
            return
        seen.add(rc)
        for d in deps.get(rc, ()):
            visit(d)
        order.append(rc)
    for rc in dyn:
        visit(rc)
    return [(dyn[rc][0], rc, dyn[rc][1]) for rc in order]


def _emit_int_to_str_routine() -> list:
    """Reusable subroutine: int_to_str converts the integer in R21 to a
    null-terminated decimal word-string at the buffer address in R22.
    Uses R23..R30 + a shared scratch buffer (_its_scratch). Non-reentrant
    (called sequentially per cell each frame). Handles sign and zero."""
    return [
        'int_to_str:                ; R21=value, R22=out buffer',
        '    MOV  R23, R22          ; write pointer',
        '    BLTZ R21, _its_neg',
        '    JMP  _its_signdone',
        '_its_neg:',
        '    LI   R24, 45           ; minus sign',
        '    STW  R24, R23, 0',
        '    ADDI R23, R23, 1',
        '    SUB  R21, R0, R21      ; abs',
        '_its_signdone:',
        '    BNEZ R21, _its_digits',
        '    LI   R24, 48           ; digit zero',
        '    STW  R24, R23, 0',
        '    ADDI R23, R23, 1',
        '    JMP  _its_term',
        '_its_digits:',
        '    LI   R27, 10',
        '    LI   R28, _its_scratch',
        '    MOV  R29, R28          ; scratch ptr (LSD first)',
        '_its_dloop:',
        '    BEQZ R21, _its_copy',
        '    MOD  R24, R21, R27     ; digit value',
        '    ADDI R24, R24, 48      ; to ASCII',
        '    STW  R24, R29, 0',
        '    ADDI R29, R29, 1',
        '    DIV  R21, R21, R27',
        '    JMP  _its_dloop',
        '_its_copy:                 ; copy scratch reversed to out',
        '_its_cloop:',
        '    SUBI R29, R29, 1',
        '    CMP  R30, R29, R28',
        '    BLTZ R30, _its_term    ; ptr < base - done',
        '    LDW  R24, R29, 0',
        '    STW  R24, R23, 0',
        '    ADDI R23, R23, 1',
        '    JMP  _its_cloop',
        '_its_term:',
        '    LI   R24, 0',
        '    STW  R24, R23, 0       ; null terminator',
        '    RET',
        '',
    ]


def _make_recompute_resolver(stream, state_map):
    """ref → state-slot label for the AST compiler. Cells → state_cell_<id>;
    numeric widget props (toggle checked) → the widget's state slot;
    SIGNAL_LAST → state_signal_last_<name> (slot emitted in Part 6)."""
    cells = getattr(stream, '_cell_meta', {}) or {}
    addr2id, name2id = {}, {}
    for rc, cell in cells.items():
        addr2id[_sheetf.rc_to_a1(*rc)] = cell.get('id')
        if cell.get('name'):
            name2id[cell['name']] = cell.get('id')
    wname2slot = {}
    for w in stream.iter_widgets('gui_'):
        s = state_map.get(w.id) or {}
        if 'checked' in s and getattr(w, 'name', ''):
            wname2slot[w.name] = s['checked']

    def resolver(ref):
        if isinstance(ref, tuple):
            if ref[0] == 'widget':
                return wname2slot.get(ref[1])
            if ref[0] == 'signal':
                return f'state_signal_last_{ref[1]}'
            return None
        cid = addr2id.get(ref)
        if cid is None:
            cid = name2id.get(ref)
        return f'state_cell_{cid}' if cid is not None else None
    return resolver


def _section_recompute_blocks(stream, state_map) -> list:
    """recompute_cell_<id> subroutine per dynamic cell + recompute_all (topo)."""
    dyn = _dynamic_cells(stream)
    if not dyn or _fxc is None:
        return []
    resolver = _make_recompute_resolver(stream, state_map)
    base = _fxc._BASE_REG
    lines = ['; ---- Dynamic cell recompute (Stage 8-3-RT-dynamic) ----']
    lines += _emit_int_to_str_routine()   # runtime int→string for dynamic render
    for cid, rc, ast in dyn:
        lines.append(f'recompute_cell_{cid}:')
        try:
            lines.append(f'    LI   R{_fxc._ERR_REG}, 0   ; clear error code')
            lines += _fxc.compile_ast(ast, base, resolver)
            lines.append(f'    LI   R20, state_cell_{cid}')
            lines.append(f'    STW  R{base}, R20, 0   ; store result')
            lines.append(f'    LI   R20, state_cell_{cid}_err')
            lines.append(f'    STW  R{_fxc._ERR_REG}, R20, 0   ; store error code (Part 7)')
        except Exception as e:
            lines.append(f'    ; (uncompilable: {e}) - leave prior value')
        lines.append('    RET')
        lines.append('')
    lines.append('recompute_all_cells:')
    for cid, _rc, _ast in dyn:
        lines.append(f'    CALL recompute_cell_{cid}')
    lines.append('    RET')
    lines.append('')
    return lines


def _has_dynamic_cells(stream) -> bool:
    return bool(_dynamic_cells(stream))


# ---------------------------------------------------------------------------
# Stage 9-1B: Shell command compilation (cmd_* widgets → t5asm)
# ---------------------------------------------------------------------------
#
# Each cmd_* widget whose kind is a real command (flowcode_commands registry)
# compiles to a `command_<id>` subroutine that computes the command and stores
# its result to a well-known slot the caller reads from:
#   number output -> state_cmd_<id>       (one word)
#   text   output -> cmdbuf_<id>          (64-word buffer) + length in state_cmd_<id>
# `run_all_commands` calls each block (declaration order; Stage 9-2 pipes will
# reorder topologically). Commands without a runtime yet (list_*, split/join/
# format/trim, ctl_repeat/while) still get a block — a documented no-op stub.

def _iter_commands(stream) -> list:
    """[(cmd_id, widget_dict)] for cmd_* widgets that name a real command.

    cmd_placeholder (no command identity) is skipped. Registry commands with no
    runtime yet are included so they still get a (stub) compile block.
    """
    if _cmdc is None or _cmdreg is None:
        return []
    cmd_meta = getattr(stream, '_cmd_meta', {}) or {}
    registry = _cmdreg.commands()
    out = []
    for cid, wd in cmd_meta.items():
        if wd.get('kind') in registry:
            out.append((cid, wd))
    return out


def _has_commands(stream) -> bool:
    return bool(_iter_commands(stream))


def _has_io_commands(stream) -> bool:
    """True if any command is an interactive cmd_io_* (needs an SDL surface)."""
    return any(wd.get('kind', '').startswith('cmd_io_')
               for _cid, wd in _iter_commands(stream))


def _is_text_buf_param(cmd_name: str, pname: str) -> bool:
    """True when (command, param) consumes a text (string-handle) value."""
    return pname in _cmdc.text_buf_params(cmd_name)


def _is_list_param(cmd_name: str, pname: str) -> bool:
    """True when (command, param) consumes a list value."""
    return pname in _cmdc.list_params(cmd_name)


# --- Stage 9-2: typed pipe edges between commands -------------------------

def _value_class(type_str: str) -> str:
    """Collapse a socket type to a runtime value class for pipe compatibility.
    number/bool share the numeric word; text is a buffer; list_* is deferred."""
    t = (type_str or '').lower()
    if t in ('number', 'bool', 'boolean'):
        return 'num'
    if t == 'text':
        return 'text'
    if t.startswith('list'):
        return 'list'
    return 'any'


def _cmd_by_id(stream) -> dict:
    return {cid: wd for cid, wd in _iter_commands(stream)}


def _command_edges(stream) -> list:
    """Pipe edges whose endpoints are both real commands.
    Edge dict: {'src': id, 'dst': id, 'dst_param': param_name}."""
    edges = getattr(stream, '_cmd_edges', None) or []
    ids = set(_cmd_by_id(stream))
    return [e for e in edges
            if e.get('src') in ids and e.get('dst') in ids]


def _incoming_pipes(stream) -> dict:
    """{dst_id: {param_name: src_id}} — the pipe feeding each input socket."""
    m: dict = {}
    for e in _command_edges(stream):
        m.setdefault(e['dst'], {})[e.get('dst_param')] = e['src']
    return m


def _ordered_command_ids(stream) -> list:
    """Command ids in topological (upstream-first) pipe order.
    Raises CompileError on a pipe cycle."""
    ids = [cid for cid, _ in _iter_commands(stream)]
    deps: dict = {cid: set() for cid in ids}
    for e in _command_edges(stream):
        deps[e['dst']].add(e['src'])
    order, done, active = [], set(), set()

    def visit(n):
        if n in done:
            return
        if n in active:
            raise CompileError(f'pipe cycle through command #{n}')
        active.add(n)
        for d in deps.get(n, ()):
            visit(d)
        active.discard(n)
        done.add(n)
        order.append(n)

    for cid in ids:
        visit(cid)
    return order


def _ordered_commands(stream) -> list:
    """[(cid, wd)] in topological pipe order."""
    by_id = _cmd_by_id(stream)
    return [(cid, by_id[cid]) for cid in _ordered_command_ids(stream)]


def _as_int(val) -> int:
    try:
        f = float(val)
        return int(f)
    except (ValueError, TypeError):
        return 0


def _command_plan(wd: dict, cid: int, incoming: dict = None,
                  cmd_by_id: dict = None) -> dict:
    """Resolve a cmd widget into {args, out_kind, bufs, env} for both the code
    and data emitters. `bufs` = [(label, text)] text-input buffers to allocate;
    `env` = set of env var names referenced.

    A parameter fed by a pipe (Stage 9-2) takes its value from the upstream
    command's output slot instead of a literal buffer; the pipe's types are
    checked here and a mismatch raises CompileError (the hard compile-time
    error the editor's red warning mirrors)."""
    name = wd.get('kind')
    spec = _cmdreg.commands().get(name, {})
    props = {p.get('name'): p.get('value')
             for p in (wd.get('properties') or [])}
    pipes = (incoming or {}).get(cid, {})
    cmd_by_id = cmd_by_id or {}
    args, bufs, env = [], [], set()
    for p in spec.get('params', []):
        pname, ptype = p.get('name'), p.get('type')
        val = props.get(pname, p.get('default'))

        src_id = pipes.get(pname)
        if src_id is not None:                     # piped input
            src_wd = cmd_by_id.get(src_id, {})
            src_kind = src_wd.get('kind', '')
            src_out = _cmdreg.commands().get(src_kind, {}).get('output', '')
            if _cmdc.command_output_kind(src_kind) not in ('number', 'text', 'list'):
                raise CompileError(
                    f'pipe into {name} #{cid}.{pname}: source {src_kind} '
                    f'#{src_id} has no runtime output')
            if _value_class(src_out) != _value_class(ptype):
                raise CompileError(
                    f'pipe type mismatch into {name} #{cid}.{pname}: '
                    f'{src_kind} outputs {src_out}, expected {ptype}')
            if _is_text_buf_param(name, pname) or _is_list_param(name, pname):
                # text/list values flow as a handle in the upstream slot
                args.append(('handleslot', f'state_cmd_{abs(src_id)}'))
            else:
                args.append(('numslot', f'state_cmd_{abs(src_id)}'))
            continue

        if name.startswith('cmd_env_') and pname == 'name':
            nm = str(val if val is not None else '')
            env.add(nm)
            args.append(('name', nm))
        elif _is_list_param(name, pname):
            # literal list = a comma-separated string split at runtime
            label = f'cmdarg_{abs(cid)}_{pname}'
            bufs.append((label, '' if val is None else str(val)))
            args.append(('listlit', label))
        elif _is_text_buf_param(name, pname):
            # literal text becomes a heap string (STR_FROMBUF of this buffer)
            label = f'cmdarg_{abs(cid)}_{pname}'
            bufs.append((label, '' if val is None else str(val)))
            args.append(('strlit', label))
        elif ptype == 'bool':
            args.append(('num', 1 if val else 0))
        else:                              # number / text-as-number / any
            args.append(('num', _as_int(val)))
    return {'args': args, 'out_kind': _cmdc.command_output_kind(name),
            'bufs': bufs, 'env': env}


def _section_command_blocks(stream) -> list:
    cmds = _ordered_commands(stream)
    if not cmds:
        return []
    incoming, by_id = _incoming_pipes(stream), _cmd_by_id(stream)
    lines = ['; ---- Shell command blocks (Stage 9-1B/9-2) ----']
    for cid, wd in cmds:
        name = wd.get('kind')
        plan = _command_plan(wd, cid, incoming, by_id)
        lines.append(f'command_{abs(cid)}:   ; {name} #{cid}')
        try:
            ctx = _cmdc.new_ctx()
            lines.append(f'    LI   R{_cmdc._ERR_REG}, 0   ; clear error code')
            lines += _cmdc.compile_command(name, plan['args'],
                                           _cmdc._BASE_REG, ctx)
            if plan['out_kind'] in ('number', 'text', 'list'):
                lines.append(f'    LI   R20, state_cmd_{abs(cid)}')
                tag = 'result' if plan['out_kind'] == 'number' else 'handle'
                lines.append(f'    STW  R{_cmdc._BASE_REG}, R20, 0   ; store {tag}')
        except _cmdc.CommandCompileError as e:
            lines.append(f'    ; no runtime yet: {e}')
        lines.append('    RET')
        lines.append('')
    # run_all_commands: CALL each command block in topological (upstream-first)
    # order. Now that the return-address stack (Option A) supports nesting, this
    # wrapper is a real subroutine — main CALLs it, it CALLs each command; the
    # old "inline at depth 0" workaround for the single-R80 hazard is retired.
    lines.append('run_all_commands:')
    for cid, wd in cmds:
        lines.append(f'    CALL command_{abs(cid)}   ; {wd.get("kind")} #{cid}')
    lines.append('    RET')
    lines.append('')
    return lines


def _command_dispatch_lines(stream) -> list:
    """A single `CALL run_all_commands` — the pipeline runs via the wrapper
    subroutine (nested CALLs, enabled by the RA stack)."""
    if not _iter_commands(stream):
        return []
    return ['    CALL run_all_commands']


def _section_command_data(stream) -> list:
    cmds = _iter_commands(stream)
    if not cmds:
        return []
    incoming, by_id = _incoming_pipes(stream), _cmd_by_id(stream)
    lines = ['; ---- Shell command state (Stage 9-1B/9-2) ----']
    env_names: set = set()
    for cid, wd in cmds:
        plan = _command_plan(wd, cid, incoming, by_id)
        # state_cmd_<id> holds the result: a number, or a string handle for text
        # commands (both are one word).
        lines += [f'state_cmd_{abs(cid)}:', '    .word 0']
        for label, text in plan['bufs']:
            lines.append(f'{label}:')
            lines += _emit_string_words(text)
        env_names |= plan['env']
        lines.append('')
    for nm in sorted(env_names):
        lines += [f'{_cmdc.env_slot(nm)}:', '    .word 0',
                  f'{_cmdc.env_present_slot(nm)}:', '    .word 0', '']
    if any(wd.get('kind') == 'cmd_io_prompt' for _cid, wd in cmds):
        lines += ['_prompt_scratch:',
                  f'    .word 0   ; x{_cmdc._PROMPT_SCRATCH_WORDS} prompt answer scratch']
        lines += ['    .word 0'] * (_cmdc._PROMPT_SCRATCH_WORDS - 1)
        lines.append('')
    # literal list args are split on "," at runtime — emit the shared delimiter
    needs_comma = any(
        a[0] == 'listlit'
        for cid, wd in cmds
        for a in _command_plan(wd, cid, incoming, by_id)['args'])
    if needs_comma:
        lines.append('_comma_str:')
        lines += _emit_string_words(',')
        lines.append('')
    return lines


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
    if _has_dynamic_cells(stream):       # Stage 8-3-RT-dynamic: refresh each frame
        lines.append('    CALL recompute_all_cells   ; recompute dynamic cells')
    lines += _emit_cell_render(stream)   # Stage 8-3-RT: draw Sheet cells
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
    sigset = set(_signal_last_names(stream))   # Part 6: SIGNAL_LAST targets
    # Part 5: cell name → state slot, for bind_value_to write-back.
    _cells = getattr(stream, '_cell_meta', {}) or {}
    cellname2id = {c['name']: c['id'] for c in _cells.values() if c.get('name')}

    for widget in reversed(all_widgets):
        if not widget.kind.startswith('gui_'):
            continue
        ex, ey, ew, eh = eff_pos.get(widget.id,
                                      (widget.x, widget.y, widget.w, widget.h))
        is_toggleable = widget.kind in _TOGGLEABLE_KINDS
        is_entry      = widget.kind in _ENTRY_KINDS

        clicked_term = _resolve_handler(stream, widget.id, _SIGNAL_CLICKED)
        toggled_term = _resolve_handler(stream, widget.id, _SIGNAL_TOGGLED)

        wname = getattr(widget, 'name', '') or ''
        sl_clicked = f"{wname}_clicked" if wname and f"{wname}_clicked" in sigset else None
        sl_toggled = f"{wname}_toggled" if wname and f"{wname}_toggled" in sigset else None

        has_action = (is_toggleable or is_entry or clicked_term or toggled_term
                      or sl_clicked or sl_toggled)   # Part 6: SIGNAL_LAST-only widgets
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
                if sl_toggled:   # Part 6: SIGNAL_LAST payload = new checked value
                    lines += [
                        f'    LI   R20, state_signal_last_{sl_toggled}',
                        f'    STW  R15, R20, 0   ; signal_last {sl_toggled}',
                    ]
                # Part 5: cell↔widget write-back — bound cell gets the new value.
                _bv = None
                for p in getattr(widget, 'properties', []):
                    if p.get('name') == 'bind_value_to':
                        _bv = p.get('value'); break
                if _bv and _bv in cellname2id:
                    lines += [
                        f'    LI   R20, state_cell_{cellname2id[_bv]}',
                        f'    STW  R15, R20, 0   ; write-back to {_bv}',
                    ]

        # Set keyboard focus for entry widgets (focus was already cleared above)
        if is_entry:
            lines += [
                f'    ; Set focus to entry #{widget.id}',
                f'    LI   R20, state_focused_entry',
                f'    LI   R15, {widget.id}',
                f'    STW  R15, R20, 0',
            ]

        # Part 6: SIGNAL_LAST for CLICKED (payload-less) → increment a fire counter
        if sl_clicked:
            lines += [
                f'    LI   R20, state_signal_last_{sl_clicked}',
                f'    LDW  R15, R20, 0',
                f'    ADDI R15, R15, 1   ; signal_last {sl_clicked} fire counter',
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
            '    ADDI R13, R13, 1     ; 3-operand form: len = len + 1',
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

    lines += _emit_cell_data(stream)     # Stage 8-3-RT: cell strings + state
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
    if _has_commands(stream):
        parts += ['    ; Stage 9-1B — run Shell commands once at startup']
        parts += _command_dispatch_lines(stream)
        parts += ['']
    parts += ['event_loop_top:']
    parts += _section_render(stream, wstr_labels, eff_pos, state_map)
    parts += _section_event_poll(has_entries=has_entries)
    parts += _section_hit_test(stream, eff_pos, state_map)
    parts += _section_tail_blocks()
    if has_entries:
        parts += _section_key_handler(stream, state_map)
    parts += _section_handler_blocks(stream)
    parts += _section_recompute_blocks(stream, state_map)  # Stage 8-3-RT-dynamic
    parts += _section_command_blocks(stream)               # Stage 9-1B
    parts += _section_data(stream, wstr_labels, state_map)
    parts += _section_command_data(stream)                 # Stage 9-1B

    return '\n'.join(parts) + '\n'


# ===========================================================================
# Stage 9-1B: shell-only program (cmd_* widgets, no GUI / cells)
# ===========================================================================

def _compile_shell_program(stream: 'WordStream', source_path: str) -> str:
    """A Connectors/Shell program with commands but no GUI: run every command
    once, then halt. Results live in state_cmd_<id> / cmdbuf_<id> slots (read
    by pipes in Stage 9-2, or an interactive display command in Stage 9-1C)."""
    io = _has_io_commands(stream)
    parts: list = []
    parts += _section_header(stream, source_path)
    if io:                       # interactive dialogs need an SDL window/renderer
        parts += [
            '    ; Open a window so interactive dialogs have an SDL surface',
            f'    LI   R1, {_PIG_OPEN_WINDOW}',
            '    LI   R2, 480', '    LI   R3, 240',
            '    LI   R4, shell_win_title', '    SYSCALL', '',
        ]
    parts += _command_dispatch_lines(stream)
    if io:
        parts += [f'    LI   R1, {_PIG_CLOSE_WINDOW}', '    SYSCALL']
    parts += ['    HALT', '']
    parts += _section_command_blocks(stream)
    parts += ['; ============ Data ============', '']
    if io:
        parts += ['shell_win_title:'] + _emit_string_words('TernOO Shell')
    parts += _section_command_data(stream)
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
    has_gui   = any(w.kind.startswith('gui_') for w in stream.iter_widgets())
    has_cells = bool(getattr(stream, '_cell_meta', {}))
    if has_gui or has_cells:           # Stage 8-3-RT: cells also need the PIGART path
        return _compile_full_program(stream, source_path)
    if _has_commands(stream):          # Stage 9-1B: shell-only program
        return _compile_shell_program(stream, source_path)
    return _compile_trivial(stream, source_path)
