"""compile_to_t5asm.py — FlowCode → 5500FP assembly compiler.

Phase 7b-1 path (backward-compat):
  If the WordStream has no gui_* widgets, compiles the first flow_terminator
  with is_entry=True to a PRINT_CHAR sequence + HALT.  Raises CompileError
  if no entry terminator exists.

Phase 7b-3 path (full PIGART program):
  If the WordStream contains any gui_* widget (gui_window, gui_button, etc.),
  compiles to a complete SDL program with:
    - PIGART_OPEN_WINDOW
    - Event loop: CLEAR + render all widgets + PRESENT + POLL_EVENT
    - MOUSE_DOWN hit-test → jump to handler block per (widget, SIGNAL_CLICKED)
    - Handler blocks: print terminator label, JMP back to event loop
    - Data section: .word color constants, .word-per-char strings, event_buf

  Color constants are stored in the data section (all exceed the 10-trit LI
  immediate range of ±29524) and loaded via LI+LDW.

Syscall conventions (from c_emulator/include/isa.h):
  SYS_PRINT_CHAR = 3   — R1=3, R2=char_code, SYSCALL
  SYS_PRINT_NL   = 6   — R1=6, SYSCALL

PIGART syscalls (from c_emulator/include/pigart.h):
  PIGART_OPEN_WINDOW   = 100  — R2=w, R3=h, R4=title_ptr
  PIGART_CLEAR         = 101  — R2=color
  PIGART_DRAW_RECT     = 102  — R2=x, R3=y, R4=w, R5=h, R6=color, R7=filled
  PIGART_DRAW_OVAL     = 104  — R2=x, R3=y, R4=w, R5=h, R6=color, R7=filled
  PIGART_DRAW_TEXT     = 105  — R2=x, R3=y, R4=text_ptr, R5=size, R6=color
  PIGART_PRESENT       = 107
  PIGART_POLL_EVENT    = 108  — R2=event_buf_ptr → writes 4 words; R1=count
  PIGART_SLEEP_MS      = 109  — R2=ms
  PIGART_CLOSE_WINDOW  = 111

Date: 2026-06-22, Adelaide
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
# Shared syscall constants
# ---------------------------------------------------------------------------

_SYS_PRINT_CHAR = 3
_SYS_PRINT_NL   = 6

# ---------------------------------------------------------------------------
# PIGART syscall constants
# ---------------------------------------------------------------------------

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
_PIG_EVENT_MOUSE_DOWN = 4

# SIGNAL_CLICKED from flowcode_signals.SIGNAL_CLICKED (= widget_lib.SIGNAL_CLICKED)
_SIGNAL_CLICKED = 300

# ---------------------------------------------------------------------------
# Color constants (all exceed 10-trit LI range ±29524 — stored as .word data)
# ---------------------------------------------------------------------------

_COLOR_BG     = 0xF0F0F0  # 15790320 — light gray background
_COLOR_GRAY   = 0x808080  # 8421504  — window / dialog outline
_COLOR_PURPLE = 0xA070C0  # 10514624 — button fill
_COLOR_DARK   = 0x404040  # 4210752  — entry outline
_COLOR_LIGHT  = 0xC0C0C0  # 12632256 — generic fallback outline
_COLOR_BLACK  = 0x000000  # 0        — text
_COLOR_WHITE  = 0xFFFFFF  # 16777215 — white

_FONT_SIZE = 14  # default DRAW_TEXT pixel size

# Widget kinds that render their label via DRAW_TEXT.
# gui_window / gui_dialog use the label as the SDL window title (OPEN_WINDOW),
# not as on-canvas text — so they are excluded here.
_KINDS_WITH_DRAWN_TEXT = frozenset({
    'gui_button', 'gui_toggle',
    'gui_entry',
    'gui_label',
    'gui_check', 'gui_radio',
})


# ---------------------------------------------------------------------------
# Phase 7b-1 helpers (trivial print-and-halt path)
# ---------------------------------------------------------------------------

def _find_entry_terminator(stream: 'WordStream') -> Optional[dict]:
    """Return the first flow_terminator with is_entry=True, or None.

    Iterates stream._flow_meta in insertion order (Python 3.7+ dict).
    """
    flow_meta = getattr(stream, '_flow_meta', None) or {}
    for sym in flow_meta.values():
        if sym.get('kind') != 'flow_terminator':
            continue
        is_entry = False
        for p in sym.get('properties', []):
            if p.get('name') == 'is_entry':
                is_entry = bool(p.get('value', False))
                break
        if is_entry:
            return sym
    return None


def _emit_print_char_sequence(label: str) -> list:
    """Emit the PRINT_CHAR stanza for label (may be empty).

    Pattern:
        LI   R1, 3          ; SYSCALL PRINT_CHAR  ← set once
        LI   R2, <code>     ; '<ch>'
        SYSCALL
        LI   R2, <code>     ; '<ch>'              ← subsequent chars: R2 only
        SYSCALL
        ...
    """
    lines = []
    if not label:
        return lines

    chars = list(label)
    first   = chars[0]
    code    = ord(first)
    ch_repr = repr(first)
    lines.append(f'    LI   R1, {_SYS_PRINT_CHAR:<6}  ; SYSCALL PRINT_CHAR')
    lines.append(f'    LI   R2, {code:<6}  ; {ch_repr}')
    lines.append( '    SYSCALL')
    for ch in chars[1:]:
        code    = ord(ch)
        ch_repr = repr(ch)
        lines.append(f'    LI   R2, {code:<6}  ; {ch_repr}')
        lines.append( '    SYSCALL')
    return lines


# ---------------------------------------------------------------------------
# Phase 7b-3 helpers — low-level render primitives
# ---------------------------------------------------------------------------

def _load_color(color_label: str, dest_reg: str = 'R6') -> list:
    """Emit: LI R20, color_label; LDW dest_reg, R20, 0  (R20 = temp)."""
    return [
        f'    LI   R20, {color_label}',
        f'    LDW  {dest_reg}, R20, 0',
    ]


def _emit_draw_rect(x: int, y: int, w: int, h: int,
                    color_label: str, filled: int) -> list:
    """Emit PIGART_DRAW_RECT sequence (R2=x R3=y R4=w R5=h R6=color R7=filled)."""
    lines = [
        f'    LI   R1, {_PIG_DRAW_RECT}',
        f'    LI   R2, {x}',
        f'    LI   R3, {y}',
        f'    LI   R4, {w}',
        f'    LI   R5, {h}',
    ]
    lines += _load_color(color_label, 'R6')
    lines += [
        f'    LI   R7, {filled}',
        '    SYSCALL',
    ]
    return lines


def _emit_draw_oval(x: int, y: int, w: int, h: int,
                    color_label: str, filled: int) -> list:
    """Emit PIGART_DRAW_OVAL sequence (R2=x R3=y R4=w R5=h R6=color R7=filled)."""
    lines = [
        f'    LI   R1, {_PIG_DRAW_OVAL}',
        f'    LI   R2, {x}',
        f'    LI   R3, {y}',
        f'    LI   R4, {w}',
        f'    LI   R5, {h}',
    ]
    lines += _load_color(color_label, 'R6')
    lines += [
        f'    LI   R7, {filled}',
        '    SYSCALL',
    ]
    return lines


def _emit_draw_text(x: int, y: int, text_label: str, color_label: str) -> list:
    """Emit PIGART_DRAW_TEXT sequence (R2=x R3=y R4=ptr R5=size R6=color)."""
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


# ---------------------------------------------------------------------------
# Phase 7b-3 helpers — widget string label tracking
# ---------------------------------------------------------------------------

def _build_wstr_labels(stream: 'WordStream') -> dict:
    """Return {widget_id: data_label} for widgets that render their label via DRAW_TEXT.

    Excludes gui_window/gui_dialog — their label is the SDL window title
    (passed to OPEN_WINDOW), not rendered on the canvas.
    """
    result = {}
    for widget in stream.iter_widgets():
        if widget.kind in _KINDS_WITH_DRAWN_TEXT and widget.label:
            result[widget.id] = f'wstr_{abs(widget.id)}'
    return result


# ---------------------------------------------------------------------------
# Phase 7b-3 helpers — per-kind widget rendering
# ---------------------------------------------------------------------------

def _emit_widget_render(widget, wstr_labels: dict) -> list:
    """Return t5asm lines for rendering a single gui_* widget."""
    k     = widget.kind
    lines = [f'    ; Render {k} #{widget.id} at ({widget.x},{widget.y})']

    if k in ('gui_window', 'gui_dialog'):
        lines += _emit_draw_rect(widget.x, widget.y, widget.w, widget.h,
                                 'color_gray', 0)

    elif k in ('gui_button', 'gui_toggle'):
        lines += _emit_draw_rect(widget.x, widget.y, widget.w, widget.h,
                                 'color_purple', 1)
        if widget.label and widget.id in wstr_labels:
            tx = widget.x + 8
            ty = widget.y + widget.h // 2 - 8
            lines += _emit_draw_text(tx, ty, wstr_labels[widget.id], 'color_black')

    elif k == 'gui_entry':
        lines += _emit_draw_rect(widget.x, widget.y, widget.w, widget.h,
                                 'color_dark', 0)
        if widget.label and widget.id in wstr_labels:
            tx = widget.x + 8
            ty = widget.y + widget.h // 2 - 8
            lines += _emit_draw_text(tx, ty, wstr_labels[widget.id], 'color_gray')

    elif k == 'gui_label':
        if widget.label and widget.id in wstr_labels:
            lines += _emit_draw_text(widget.x, widget.y,
                                     wstr_labels[widget.id], 'color_black')

    elif k in ('gui_check', 'gui_radio'):
        # Small filled oval + label to the right
        lines += _emit_draw_oval(widget.x, widget.y, 16, 16, 'color_dark', 1)
        if widget.label and widget.id in wstr_labels:
            lines += _emit_draw_text(widget.x + 24, widget.y + 4,
                                     wstr_labels[widget.id], 'color_black')

    else:
        # Fallback: outlined rect for any unhandled kind
        lines += _emit_draw_rect(widget.x, widget.y, widget.w, widget.h,
                                 'color_light', 0)

    return lines


# ---------------------------------------------------------------------------
# Phase 7b-3 helpers — section emitters
# ---------------------------------------------------------------------------

def _get_window_dims(stream: 'WordStream'):
    """Return (width, height) from first gui_window, or default (800, 600)."""
    for widget in stream.iter_widgets():
        if widget.kind == 'gui_window':
            return widget.w, widget.h
    return 800, 600


def _get_window_title(stream: 'WordStream') -> str:
    """Return title from first gui_window label, or default."""
    for widget in stream.iter_widgets():
        if widget.kind == 'gui_window' and widget.label:
            return widget.label
    return '5500FP'


def _emit_string_words(text: str) -> list:
    """Emit .word per char + null terminator for a C-style string."""
    lines = []
    for ch in text:
        lines.append(f'    .word {ord(ch):<6}  ; {repr(ch)}')
    lines.append('    .word 0              ; null terminator')
    return lines


def _section_header(stream: 'WordStream', source_path: str) -> list:
    now      = datetime.datetime.now().astimezone()
    iso_now  = now.strftime('%Y-%m-%dT%H:%M:%S%z')
    src_name = (os.path.basename(source_path)
                if source_path != '<in-memory>' else source_path)
    return [
        '; Auto-generated by FlowCode compiler',
        f'; Source:    {src_name}',
        f'; Generated: {iso_now}',
        '; Phase:     7b-3 (PIGART SDL window + event loop)',
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


def _section_render(stream: 'WordStream', wstr_labels: dict) -> list:
    """CLEAR + draw all gui_* widgets in stream order."""
    lines = ['    ; --- Render frame ---']
    lines.append(f'    LI   R1, {_PIG_CLEAR}')
    lines += _load_color('color_bg', 'R2')
    lines.append('    SYSCALL')
    lines.append('')
    for widget in stream.iter_widgets():
        if not widget.kind.startswith('gui_'):
            continue
        lines += _emit_widget_render(widget, wstr_labels)
        lines.append('')
    return lines


def _section_event_poll() -> list:
    """Present + poll + event-type decode + dispatch branches."""
    return [
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
        '    ; Close event → exit',
        f'    LI   R6, {_PIG_EVENT_CLOSE}',
        '    BEQ  R5, R6, exit_prog',
        '',
        '    ; Mouse-down → hit-test',
        f'    LI   R6, {_PIG_EVENT_MOUSE_DOWN}',
        '    BEQ  R5, R6, handle_mouse_down',
        '',
        '    ; All other events: ignore',
        '    JMP  no_event_this_tick',
        '',
        'handle_mouse_down:',
        '    LDW  R10, R2, 1         ; mouse_x = event_buf[1]',
        '    LDW  R11, R2, 2         ; mouse_y = event_buf[2]',
        '',
    ]


def _section_hit_test(stream: 'WordStream') -> list:
    """Hit-test block (inside handle_mouse_down) in reverse widget order.

    Reverse iteration = last drawn = topmost widget first.
    Falls through to JMP no_event_this_tick if no widget hit.
    """
    lines = []
    all_widgets = list(stream.iter_widgets())
    for widget in reversed(all_widgets):
        if not widget.kind.startswith('gui_'):
            continue
        term = stream.find_terminator_for(widget.id, _SIGNAL_CLICKED)
        if term is None:
            continue
        term_id       = term['id']
        skip_lbl      = f'skip_wid_{abs(widget.id)}'
        handler_lbl   = f'handler_term_{term_id}'
        lines += [
            f'    ; Hit-test {widget.kind} #{widget.id} → {handler_lbl}',
            f'    LI   R12, {widget.x}',
            f'    BLT  R10, R12, {skip_lbl}',
            f'    LI   R12, {widget.x + widget.w}',
            f'    BGT  R10, R12, {skip_lbl}',
            f'    LI   R12, {widget.y}',
            f'    BLT  R11, R12, {skip_lbl}',
            f'    LI   R12, {widget.y + widget.h}',
            f'    BGT  R11, R12, {skip_lbl}',
            f'    JMP  {handler_lbl}',
            f'{skip_lbl}:',
            '',
        ]
    # No widget hit (or no bindings) → back to idle
    lines += ['    JMP  no_event_this_tick', '']
    return lines


def _section_tail_blocks() -> list:
    """no_event_this_tick and exit_prog blocks."""
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
    """One labeled block per unique handler terminator.

    Deduplicates by terminator id: two widgets bound to the same terminator
    emit two hit-test entries but a single handler block.
    """
    lines = []
    emitted_ids: set = set()

    for widget in stream.iter_widgets():
        if not widget.kind.startswith('gui_'):
            continue
        term = stream.find_terminator_for(widget.id, _SIGNAL_CLICKED)
        if term is None:
            continue
        term_id = term['id']
        if term_id in emitted_ids:
            continue
        emitted_ids.add(term_id)

        lbl         = term.get('label', '') or ''
        handler_lbl = f'handler_term_{term_id}'

        lines.append(f'{handler_lbl}:')
        lines.append(f'    ; Entry terminator "{lbl}"')
        if lbl:
            lines += _emit_print_char_sequence(lbl)
        lines.append(f'    LI   R1, {_SYS_PRINT_NL:<6}  ; SYSCALL PRINT_NL')
        lines.append( '    SYSCALL')
        lines.append( '    JMP  event_loop_top')
        lines.append('')

    return lines


def _section_data(stream: 'WordStream', wstr_labels: dict) -> list:
    """Data section: color .word constants, window title, widget strings, event_buf."""
    lines = ['; ============ Data ============', '']

    # Color constants (all > LI range; stored as .word)
    for name, val in [
        ('color_bg',     _COLOR_BG),
        ('color_gray',   _COLOR_GRAY),
        ('color_purple', _COLOR_PURPLE),
        ('color_dark',   _COLOR_DARK),
        ('color_light',  _COLOR_LIGHT),
        ('color_black',  _COLOR_BLACK),
        ('color_white',  _COLOR_WHITE),
    ]:
        lines.append(f'{name}:')
        lines.append(f'    .word {val}')
    lines.append('')

    # Window title string
    title = _get_window_title(stream)
    lines.append('win_title_str:')
    lines += _emit_string_words(title)
    lines.append('')

    # Widget label strings (only widgets with non-empty label that need text)
    for widget in stream.iter_widgets():
        if widget.id in wstr_labels and widget.label:
            lines.append(f'{wstr_labels[widget.id]}:')
            lines += _emit_string_words(widget.label)
            lines.append('')

    # Event buffer (4 words: type, mouse_x, mouse_y, spare)
    lines += [
        'event_buf:',
        '    .word 0              ; event type',
        '    .word 0              ; mouse x',
        '    .word 0              ; mouse y',
        '    .word 0              ; spare',
        '',
    ]
    return lines


# ---------------------------------------------------------------------------
# Phase 7b-3: full program compilation
# ---------------------------------------------------------------------------

def _compile_full_program(stream: 'WordStream', source_path: str) -> str:
    """Compile WordStream with gui_* widgets to a complete PIGART program."""
    wstr_labels = _build_wstr_labels(stream)

    parts: list = []
    parts += _section_header(stream, source_path)
    parts += _section_open_window(stream)
    parts += ['event_loop_top:']
    parts += _section_render(stream, wstr_labels)
    parts += _section_event_poll()
    parts += _section_hit_test(stream)
    parts += _section_tail_blocks()
    parts += _section_handler_blocks(stream)
    parts += _section_data(stream, wstr_labels)

    return '\n'.join(parts) + '\n'


# ---------------------------------------------------------------------------
# Phase 7b-1: trivial print-and-halt compilation (backward-compat)
# ---------------------------------------------------------------------------

def _compile_trivial(stream: 'WordStream', source_path: str) -> str:
    """Phase 7b-1 trivial path: print entry terminator label + HALT."""
    entry = _find_entry_terminator(stream)
    if entry is None:
        raise CompileError("No entry terminator found")

    label = entry.get('label', '') or ''
    ex    = entry.get('x', 0)
    ey    = entry.get('y', 0)

    now      = datetime.datetime.now().astimezone()
    iso_now  = now.strftime('%Y-%m-%dT%H:%M:%S%z')
    src_name = (os.path.basename(source_path)
                if source_path != '<in-memory>' else source_path)

    lines = [
        '; Auto-generated by FlowCode compiler',
        f'; Source:    {src_name}',
        f'; Generated: {iso_now}',
        f'; Entry:     flow_terminator "{label}" at position ({ex}, {ey})',
        '; Phase:     7b-1 (PRINT_CHAR + HALT only)',
        '',
        'main:',
    ]

    if label:
        lines.append(f'    ; Print "{label}"')
        lines.extend(_emit_print_char_sequence(label))
    else:
        lines.append('    ; (empty label — just emit newline)')

    lines.append(f'    LI   R1, {_SYS_PRINT_NL:<6}  ; SYSCALL PRINT_NL')
    lines.append( '    SYSCALL')
    lines.append( '    HALT')
    lines.append('')   # trailing newline

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compile_wordstream_to_t5asm(stream: 'WordStream',
                                 source_path: str = '<in-memory>') -> str:
    """Translate a WordStream to 5500FP assembly text.

    Phase detection:
      - Any gui_* widget in stream._widget_meta → Phase 7b-3 full PIGART path
      - No gui_* widgets → Phase 7b-1 trivial print-and-halt path

    Args:
        stream:      the canonical WordStream (must have _flow_meta and/or
                     _widget_meta set).
        source_path: path to the .ternoo file (used in header comment only).

    Returns:
        t5asm text ready to write to a .t5asm file.

    Raises:
        CompileError: (Phase 7b-1 path only) if no entry terminator exists.
    """
    gui_widgets = [w for w in stream.iter_widgets()
                   if w.kind.startswith('gui_')]
    if gui_widgets:
        return _compile_full_program(stream, source_path)
    return _compile_trivial(stream, source_path)
