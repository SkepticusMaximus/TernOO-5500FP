#!/usr/bin/env python3
"""
FlowCode  v0.1.0
================
Visual programming IDE for TernOO-5500FP.
Draw flowchart symbols → generates TernOO words → loads into emulator.

This is the proof-of-concept that closes the loop:
  Draw a symbol → TernOO word in memory → emulator can run it.

Usage:
    python3 flowcode.py              # open the visual canvas
    python3 flowcode.py --headless   # run logic tests without GUI

Requires:
    5500fp_ternoo.py (or 5500fp_ternoo_v03.py) in the same directory.
    tkinter (ships with Python on Linux Mint: sudo apt install python3-tk)

Controls:
    R  — place a Process rectangle at cursor position
    D  — place a Decision diamond at cursor position
    I  — place an I/O rounded-rectangle at cursor position
    E  — start/finish drawing a connection (click source then target)
    Del — delete selected symbol
    W  — print TernOO word dump to terminal
    L  — load program into emulator and run
    Ctrl+S — save canvas to JSON
    Ctrl+O — load canvas from JSON

Symbol → TernOO word mapping:
    Rectangle (Process)      → USER-DEF POINTER, subclass base (0,0)
    Diamond (Decision)       → USER-DEF POINTER, subclass (0,+1) 
    Rounded rect (I/O)       → USER-DEF POINTER, subclass (+1,0)
    Connection arrow         → EXEC word (register call, user privilege)
    Symbol position          → MAP word (octree coordinate from canvas position)
"""

import sys
import os
import json
import math
from typing import List, Dict, Optional, Tuple

# ── Locate emulator ──────────────────────────────────────────────────────────

def _find_emulator():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '5500fp_ternoo.py'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '5500fp_ternoo_v03.py'),
        os.path.join(os.getcwd(), '5500fp_ternoo.py'),
        os.path.join(os.getcwd(), '5500fp_ternoo_v03.py'),
        os.path.expanduser('~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/5500fp_ternoo.py'),
        os.path.expanduser('~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/5500fp_ternoo_v03.py'),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

_emu_path = _find_emulator()
if _emu_path is None:
    print("ERROR: Cannot find 5500fp_ternoo.py")
    sys.exit(1)

from importlib.util import spec_from_file_location, module_from_spec
_spec = spec_from_file_location("emu", _emu_path)
_emu  = module_from_spec(_spec)
import unittest.mock
with unittest.mock.patch.object(_emu, "__name__", "emu"):
    _spec.loader.exec_module(_emu)

globals().update({k: getattr(_emu, k) for k in dir(_emu) if not k.startswith('__')})

# ── FlowCode data model ───────────────────────────────────────────────────────

SYMBOL_PROCESS  = 'process'    # rectangle  → UDP subclass (0,0)
SYMBOL_DECISION = 'decision'   # diamond    → UDP subclass (0,+1)
SYMBOL_IO       = 'io'         # rounded    → UDP subclass (+1,0)

SYMBOL_SUBCLASS = {
    SYMBOL_PROCESS:  (0,  0),
    SYMBOL_DECISION: (0, +1),
    SYMBOL_IO:       (+1, 0),
}

SYMBOL_W = 120   # default symbol width  (canvas pixels)
SYMBOL_H =  60   # default symbol height

class FCSymbol:
    """A FlowCode visual symbol — one TernOO USER-DEF POINTER word."""

    _next_id = 1

    def __init__(self, kind: str, x: int, y: int,
                 label: str = "", code_seg: int = 0, data_seg: int = 0):
        self.id       = FCSymbol._next_id
        FCSymbol._next_id += 1
        self.kind     = kind      # SYMBOL_PROCESS / DECISION / IO
        self.x        = x         # canvas centre x
        self.y        = y         # canvas centre y
        self.label    = label or f"{kind[0].upper()}{self.id}"
        self.code_seg = code_seg  # CODE-SEG tribble
        self.data_seg = data_seg  # DATA-SEG nibble
        self.offset   = 0         # internal cursor

    def to_map_word(self) -> int:
        """
        Encode canvas position as a MAP word.
        Canvas (0,0)=top-left.  We map x → XZ-plane, y → XY-plane.
        Scale: 1 canvas pixel = 1 ternary unit (±364 range → 728px max).
        Centre at (364, 364) to allow signed coordinates.
        """
        cx = max(-364, min(364, self.x - 364))
        cy = max(-364, min(364, self.y - 364))
        # ON_PLANE mode: axis_yz=0, axis_xz=cx≠0, axis_xy=cy≠0
        # Use ABSOLUTE_3D with Y=0 for 2D canvas
        return build_map_word(0, 1 if cx >= 0 else -1,
                              1 if cy >= 0 else -1,
                              abs(cx) * 729 + abs(cy))

    def to_udp_word(self) -> int:
        """Encode this symbol as a USER-DEF POINTER word."""
        sub_t1, sub_t0 = SYMBOL_SUBCLASS[self.kind]
        return build_udp_word(sub_t1, sub_t0,
                              self.offset, self.code_seg, self.data_seg)

    def to_dict(self) -> dict:
        return {'id': self.id, 'kind': self.kind, 'x': self.x, 'y': self.y,
                'label': self.label, 'code_seg': self.code_seg,
                'data_seg': self.data_seg, 'offset': self.offset}

    @classmethod
    def from_dict(cls, d: dict) -> 'FCSymbol':
        s = cls(d['kind'], d['x'], d['y'], d.get('label',''),
                d.get('code_seg',0), d.get('data_seg',0))
        s.id     = d['id']
        s.offset = d.get('offset', 0)
        FCSymbol._next_id = max(FCSymbol._next_id, s.id + 1)
        return s

    def __repr__(self):
        return f"FCSymbol({self.kind} #{self.id} @({self.x},{self.y}))"


class FCEdge:
    """A FlowCode directed edge — one TernOO EXEC word."""

    def __init__(self, src_id: int, dst_id: int,
                 privilege: int = EXEC_PRIV_USER,
                 call_style: int = EXEC_CALL_REGISTER,
                 return_type: int = EXEC_RET_DATA,
                 seg_idx: int = 0, offset: int = 0):
        self.src_id      = src_id
        self.dst_id      = dst_id
        self.privilege   = privilege
        self.call_style  = call_style
        self.return_type = return_type
        self.seg_idx     = seg_idx
        self.offset      = offset

    def to_exec_word(self) -> int:
        return build_exec_word(self.privilege, self.call_style, self.return_type,
                               self.seg_idx, self.offset)

    def to_dict(self) -> dict:
        return {'src': self.src_id, 'dst': self.dst_id,
                'privilege': self.privilege, 'call_style': self.call_style,
                'return_type': self.return_type,
                'seg_idx': self.seg_idx, 'offset': self.offset}

    @classmethod
    def from_dict(cls, d: dict) -> 'FCEdge':
        return cls(d['src'], d['dst'], d.get('privilege', EXEC_PRIV_USER),
                   d.get('call_style', EXEC_CALL_REGISTER),
                   d.get('return_type', EXEC_RET_DATA),
                   d.get('seg_idx', 0), d.get('offset', 0))


class FCCanvas:
    """
    FlowCode canvas — the program as a collection of symbols and edges.
    This is the data model; rendering is separate (TkCanvas or terminal).
    """

    def __init__(self):
        self.symbols: Dict[int, FCSymbol] = {}
        self.edges:   List[FCEdge]        = []

    def add_symbol(self, kind: str, x: int, y: int, label: str = '') -> FCSymbol:
        s = FCSymbol(kind, x, y, label)
        self.symbols[s.id] = s
        return s

    def add_edge(self, src_id: int, dst_id: int, **kwargs) -> Optional[FCEdge]:
        if src_id not in self.symbols or dst_id not in self.symbols:
            return None
        e = FCEdge(src_id, dst_id, **kwargs)
        self.edges.append(e)
        return e

    def remove_symbol(self, sym_id: int):
        self.symbols.pop(sym_id, None)
        self.edges = [e for e in self.edges
                      if e.src_id != sym_id and e.dst_id != sym_id]

    def symbol_at(self, x: int, y: int,
                  hw: int = SYMBOL_W//2, hh: int = SYMBOL_H//2) -> Optional[FCSymbol]:
        for s in reversed(list(self.symbols.values())):
            if abs(s.x - x) <= hw and abs(s.y - y) <= hh:
                return s
        return None

    # ── TernOO word generation ────────────────────────────────────────────────

    def to_word_program(self) -> List[Tuple[str, int]]:
        """
        Convert the canvas to a sequence of labelled TernOO words.
        Returns list of (label, word_integer) pairs.
        Each symbol produces two words: a MAP (position) and a UDP (object).
        Each edge produces one EXEC word.
        """
        words = []
        for s in self.symbols.values():
            words.append((f"MAP  #{s.id} {s.label}", s.to_map_word()))
            words.append((f"UDP  #{s.id} {s.label}", s.to_udp_word()))
        for e in self.edges:
            src = self.symbols.get(e.src_id)
            dst = self.symbols.get(e.dst_id)
            slabel = src.label if src else f"#{e.src_id}"
            dlabel = dst.label if dst else f"#{e.dst_id}"
            words.append((f"EXEC {slabel}→{dlabel}", e.to_exec_word()))
        return words

    def load_into_emulator(self, cpu, start_addr: int = 100) -> int:
        """
        Load the canvas word program into the emulator's memory.
        Returns the address after the last loaded word.
        """
        words = self.to_word_program()
        for i, (label, word) in enumerate(words):
            cpu.mem_write(start_addr + i, word)
        return start_addr + len(words)

    def print_word_dump(self):
        """Print all TernOO words to terminal."""
        words = self.to_word_program()
        print(f"\n{'─'*60}")
        print(f"FlowCode Canvas → TernOO Word Dump")
        print(f"  {len(self.symbols)} symbols,  {len(self.edges)} edges,  "
              f"{len(words)} words total")
        print(f"{'─'*60}")
        for label, word in words:
            print(f"  {label:<28} {word_to_str(word)}  ({word})")
            print(f"  {'':28} {describe_word(word)}")
        print(f"{'─'*60}\n")

    # ── Serialisation ─────────────────────────────────────────────────────────

    def save(self, path: str):
        data = {
            'symbols': [s.to_dict() for s in self.symbols.values()],
            'edges':   [e.to_dict() for e in self.edges],
        }
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"Saved: {path}")

    def load(self, path: str):
        with open(path) as f:
            data = json.load(f)
        self.symbols.clear()
        self.edges.clear()
        for d in data.get('symbols', []):
            s = FCSymbol.from_dict(d)
            self.symbols[s.id] = s
        for d in data.get('edges', []):
            self.edges.append(FCEdge.from_dict(d))
        print(f"Loaded: {path}  "
              f"({len(self.symbols)} symbols, {len(self.edges)} edges)")

    def ascii_render(self) -> str:
        """Render canvas as ASCII art for terminal display."""
        lines = ["FlowCode Canvas (ASCII preview):", ""]
        sym_shapes = {
            SYMBOL_PROCESS:  ('[{label}]',  '[{label}]'),
            SYMBOL_DECISION: ('<{label}>', '<{label}>'),
            SYMBOL_IO:       ('({label})', '({label})'),
        }
        for s in self.symbols.values():
            shape = sym_shapes.get(s.kind, ('{label}', '{label}'))[0]
            rendered = shape.format(label=s.label)
            lines.append(f"  {rendered:<20} @ ({s.x:4d}, {s.y:4d})")
        if self.edges:
            lines.append("")
            lines.append("  Connections:")
            for e in self.edges:
                src = self.symbols.get(e.src_id)
                dst = self.symbols.get(e.dst_id)
                sl = src.label if src else f"#{e.src_id}"
                dl = dst.label if dst else f"#{e.dst_id}"
                priv_sym = {EXEC_PRIV_KERNEL:'K',
                            EXEC_PRIV_USER:'U',
                            EXEC_PRIV_SANDBOX:'S'}.get(e.privilege,'?')
                call_sym = {EXEC_CALL_STACK:'stk',
                            EXEC_CALL_REGISTER:'reg',
                            EXEC_CALL_MESSAGE:'msg'}.get(e.call_style,'?')
                lines.append(f"    {sl} ──[{priv_sym}/{call_sym}]──→ {dl}")
        return '\n'.join(lines)


# ── Terminal (headless) demo ──────────────────────────────────────────────────

def run_headless_demo():
    """Demonstrate FlowCode data model without GUI."""
    print("="*60)
    print("FlowCode v0.1.0 — Headless Demo")
    print("="*60)
    print()

    # Build a small flowchart programmatically
    canvas = FCCanvas()

    start   = canvas.add_symbol(SYMBOL_IO,       200, 100, "START")
    check   = canvas.add_symbol(SYMBOL_DECISION, 200, 220, "CHECK")
    process = canvas.add_symbol(SYMBOL_PROCESS,  350, 340, "PROCESS")
    end     = canvas.add_symbol(SYMBOL_IO,       200, 460, "END")

    canvas.add_edge(start.id,   check.id)
    canvas.add_edge(check.id,   process.id,
                    call_style=EXEC_CALL_MESSAGE)  # conditional branch
    canvas.add_edge(check.id,   end.id)
    canvas.add_edge(process.id, end.id,
                    privilege=EXEC_PRIV_USER,
                    call_style=EXEC_CALL_REGISTER)

    # ASCII preview
    print(canvas.ascii_render())
    print()

    # TernOO word dump
    canvas.print_word_dump()

    # Load into emulator and verify
    print("Loading into emulator...")
    cpu = CPU5500FP()
    cpu.write_cs(0, 1000)
    cpu.write_ds(0, 2000)
    end_addr = canvas.load_into_emulator(cpu, start_addr=100)
    print(f"  Loaded {end_addr - 100} words at addresses 100–{end_addr-1}")
    print()

    # Verify round-trip: read back and decode
    print("Verifying round-trip (read back from emulator memory):")
    words = canvas.to_word_program()
    all_ok = True
    for i, (label, original_word) in enumerate(words):
        read_back = cpu.mem_read(100 + i)
        ok = read_back == original_word
        if not ok:
            print(f"  MISMATCH at {100+i}: {label}")
            all_ok = False
    if all_ok:
        print(f"  All {len(words)} words verified ✓")
    print()

    # Save to JSON
    save_path = '/tmp/flowcode_demo.json'
    canvas.save(save_path)

    # Reload and verify
    canvas2 = FCCanvas()
    canvas2.load(save_path)
    words2 = canvas2.to_word_program()
    assert len(words2) == len(words), "Round-trip word count mismatch"
    print(f"  JSON round-trip: {len(words2)} words ✓")
    print()
    print("Headless demo complete.")


# ── Tkinter GUI ───────────────────────────────────────────────────────────────

def run_gui():
    try:
        import tkinter as tk
        from tkinter import messagebox, filedialog
    except ImportError:
        print("tkinter not available.")
        print("Install with: sudo apt install python3-tk")
        print("Running headless demo instead.")
        run_headless_demo()
        return

    CANVAS_W = 900
    CANVAS_H = 650
    STATUS_H =  28

    # Colours
    COL_BG       = '#1a1a2e'
    COL_CANVAS   = '#16213e'
    COL_GRID     = '#1e2a4a'
    COL_PROCESS  = '#0f3460'
    COL_DECISION = '#533483'
    COL_IO       = '#1a6b5e'
    COL_BORDER   = '#4a9eff'
    COL_SELECTED = '#ff6b35'
    COL_EDGE     = '#7ab4ff'
    COL_EDGE_MSG = '#ff9f43'
    COL_TEXT     = '#e0e0e0'
    COL_STATUS   = '#0d1117'

    canvas_model = FCCanvas()
    cpu          = CPU5500FP()
    cpu.write_cs(0, 1000)
    cpu.write_ds(0, 2000)

    state = {
        'mode':          'select',   # select | place_process | place_decision
                                     # | place_io | edge_src
        'selected':      None,       # FCSymbol id or None
        'edge_src':      None,       # FCSymbol id when drawing edge
        'drag_offset':   (0, 0),
        'dragging':      False,
        'status':        'Ready — R=Process  D=Decision  I/O=I  E=Edge  W=Words  L=Load',
    }

    root = tk.Tk()
    root.title("FlowCode v0.1.0 — TernOO-5500FP Visual IDE")
    root.configure(bg=COL_BG)
    root.resizable(True, True)

    frame = tk.Frame(root, bg=COL_BG)
    frame.pack(fill='both', expand=True)

    tk_canvas = tk.Canvas(frame, width=CANVAS_W, height=CANVAS_H,
                          bg=COL_CANVAS, highlightthickness=0)
    tk_canvas.pack(side='top', fill='both', expand=True)

    status_bar = tk.Label(frame, text=state['status'], anchor='w',
                          bg=COL_STATUS, fg='#7ab4ff',
                          font=('Monospace', 10), padx=8)
    status_bar.pack(side='bottom', fill='x', ipady=4)

    def set_status(msg: str):
        state['status'] = msg
        status_bar.config(text=msg)

    # ── Drawing helpers ───────────────────────────────────────────────────────

    def draw_grid():
        for x in range(0, CANVAS_W, 40):
            tk_canvas.create_line(x, 0, x, CANVAS_H, fill=COL_GRID, width=1)
        for y in range(0, CANVAS_H, 40):
            tk_canvas.create_line(0, y, CANVAS_W, y, fill=COL_GRID, width=1)

    def draw_symbol(s: FCSymbol, selected: bool = False):
        x, y = s.x, s.y
        hw, hh = SYMBOL_W // 2, SYMBOL_H // 2
        col = COL_SELECTED if selected else {
            SYMBOL_PROCESS:  COL_PROCESS,
            SYMBOL_DECISION: COL_DECISION,
            SYMBOL_IO:       COL_IO,
        }.get(s.kind, COL_PROCESS)
        border = COL_SELECTED if selected else COL_BORDER

        if s.kind == SYMBOL_PROCESS:
            tk_canvas.create_rectangle(x-hw, y-hh, x+hw, y+hh,
                                       fill=col, outline=border, width=2)
        elif s.kind == SYMBOL_DECISION:
            pts = [x, y-hh, x+hw, y, x, y+hh, x-hw, y]
            tk_canvas.create_polygon(pts, fill=col, outline=border, width=2)
        elif s.kind == SYMBOL_IO:
            r = 12
            tk_canvas.create_rectangle(x-hw+r, y-hh, x+hw-r, y+hh,
                                       fill=col, outline=col)
            tk_canvas.create_oval(x-hw, y-hh, x-hw+r*2, y+hh,
                                  fill=col, outline=border, width=2)
            tk_canvas.create_oval(x+hw-r*2, y-hh, x+hw, y+hh,
                                  fill=col, outline=border, width=2)
            tk_canvas.create_line(x-hw+r, y-hh, x+hw-r, y-hh,
                                  fill=border, width=2)
            tk_canvas.create_line(x-hw+r, y+hh, x+hw-r, y+hh,
                                  fill=border, width=2)

        tk_canvas.create_text(x, y, text=s.label,
                              fill=COL_TEXT,
                              font=('Monospace', 10, 'bold'))
        # Show word type hint
        udp = s.to_udp_word()
        hint = f"UDP {describe_word(udp)[:20]}"
        tk_canvas.create_text(x, y + hh + 10, text=hint,
                              fill='#556080', font=('Monospace', 7))

    def draw_edge(e: FCEdge):
        src = canvas_model.symbols.get(e.src_id)
        dst = canvas_model.symbols.get(e.dst_id)
        if not src or not dst: return

        x1, y1 = src.x, src.y
        x2, y2 = dst.x, dst.y

        col = COL_EDGE_MSG if e.call_style == EXEC_CALL_MESSAGE else COL_EDGE
        dash = (6, 4) if e.call_style == EXEC_CALL_MESSAGE else None

        if dash:
            tk_canvas.create_line(x1, y1, x2, y2, fill=col, width=2, dash=dash)
        else:
            tk_canvas.create_line(x1, y1, x2, y2, fill=col, width=2,
                                  arrow='last', arrowshape=(12, 15, 5))

        # Label with EXEC word hint
        mx, my = (x1+x2)//2, (y1+y2)//2
        priv = {EXEC_PRIV_KERNEL:'K', EXEC_PRIV_USER:'U',
                EXEC_PRIV_SANDBOX:'S'}.get(e.privilege, '?')
        call = {EXEC_CALL_STACK:'stk', EXEC_CALL_REGISTER:'reg',
                EXEC_CALL_MESSAGE:'msg'}.get(e.call_style, '?')
        tk_canvas.create_text(mx, my - 10, text=f"{priv}/{call}",
                              fill='#556080', font=('Monospace', 8))

    def redraw():
        tk_canvas.delete('all')
        draw_grid()
        for e in canvas_model.edges:
            draw_edge(e)
        for s in canvas_model.symbols.values():
            draw_symbol(s, selected=(s.id == state['selected']))

    # ── Event handlers ────────────────────────────────────────────────────────

    def on_click(event):
        x, y = event.x, event.y
        mode = state['mode']

        if mode == 'place_process':
            s = canvas_model.add_symbol(SYMBOL_PROCESS, x, y)
            state['selected'] = s.id
            state['mode'] = 'select'
            set_status(f"Placed {s.label} — {describe_word(s.to_udp_word())}")
            redraw()

        elif mode == 'place_decision':
            s = canvas_model.add_symbol(SYMBOL_DECISION, x, y)
            state['selected'] = s.id
            state['mode'] = 'select'
            set_status(f"Placed {s.label} — {describe_word(s.to_udp_word())}")
            redraw()

        elif mode == 'place_io':
            s = canvas_model.add_symbol(SYMBOL_IO, x, y)
            state['selected'] = s.id
            state['mode'] = 'select'
            set_status(f"Placed {s.label} — {describe_word(s.to_udp_word())}")
            redraw()

        elif mode == 'edge_src':
            hit = canvas_model.symbol_at(x, y)
            if hit:
                state['edge_src'] = hit.id
                state['mode'] = 'edge_dst'
                set_status(f"Edge from {hit.label} — click target symbol")
            else:
                state['mode'] = 'select'
                state['edge_src'] = None
                set_status("Cancelled — click a symbol to start edge")

        elif mode == 'edge_dst':
            hit = canvas_model.symbol_at(x, y)
            if hit and hit.id != state['edge_src']:
                e = canvas_model.add_edge(state['edge_src'], hit.id)
                src = canvas_model.symbols[state['edge_src']]
                set_status(f"Edge {src.label}→{hit.label} — "
                           f"{describe_word(e.to_exec_word())}")
                state['mode'] = 'select'
                state['edge_src'] = None
                redraw()
            elif hit and hit.id == state['edge_src']:
                set_status("Can't connect symbol to itself")
            else:
                state['mode'] = 'select'
                state['edge_src'] = None
                set_status("Cancelled")

        else:  # select mode
            hit = canvas_model.symbol_at(x, y)
            if hit:
                state['selected'] = hit.id
                state['drag_offset'] = (x - hit.x, y - hit.y)
                state['dragging'] = True
                udp = hit.to_udp_word()
                mp  = hit.to_map_word()
                set_status(f"{hit.label}  UDP: {describe_word(udp)}  "
                           f"MAP: {describe_word(mp)}")
            else:
                state['selected'] = None
                state['dragging'] = False
                set_status("Click a symbol, or press R/D/I to place, E for edge")
            redraw()

    def on_drag(event):
        if state['dragging'] and state['selected']:
            s = canvas_model.symbols.get(state['selected'])
            if s:
                dx, dy = state['drag_offset']
                s.x = event.x - dx
                s.y = event.y - dy
                redraw()

    def on_release(event):
        if state['dragging'] and state['selected']:
            s = canvas_model.symbols.get(state['selected'])
            if s:
                set_status(f"Moved {s.label} to ({s.x},{s.y})  "
                           f"MAP: {describe_word(s.to_map_word())}")
        state['dragging'] = False

    def on_key(event):
        key = event.keysym.lower()

        if key == 'r':
            state['mode'] = 'place_process'
            set_status("Click to place Process rectangle (→ UDP word)")
        elif key == 'd':
            state['mode'] = 'place_decision'
            set_status("Click to place Decision diamond (→ UDP word)")
        elif key == 'i':
            state['mode'] = 'place_io'
            set_status("Click to place I/O symbol (→ UDP word)")
        elif key == 'e':
            state['mode'] = 'edge_src'
            state['edge_src'] = None
            set_status("Click source symbol for edge (→ EXEC word)")
        elif key == 'w':
            canvas_model.print_word_dump()
            set_status(f"Word dump printed to terminal "
                       f"({len(canvas_model.to_word_program())} words)")
        elif key == 'l':
            end = canvas_model.load_into_emulator(cpu, start_addr=100)
            n = end - 100
            set_status(f"Loaded {n} words into emulator at 100–{end-1}")
            print(f"\nLoaded {n} words into emulator.")
            canvas_model.print_word_dump()
        elif key == 'delete':
            if state['selected']:
                s = canvas_model.symbols.get(state['selected'])
                if s:
                    canvas_model.remove_symbol(state['selected'])
                    set_status(f"Deleted {s.label}")
                    state['selected'] = None
                    redraw()
        elif event.state & 0x4:  # Ctrl
            if key == 's':
                path = filedialog.asksaveasfilename(
                    defaultextension='.json',
                    filetypes=[('FlowCode JSON', '*.json'), ('All', '*.*')],
                    title='Save FlowCode canvas')
                if path:
                    canvas_model.save(path)
                    set_status(f"Saved: {path}")
            elif key == 'o':
                path = filedialog.askopenfilename(
                    filetypes=[('FlowCode JSON', '*.json'), ('All', '*.*')],
                    title='Load FlowCode canvas')
                if path:
                    canvas_model.load(path)
                    state['selected'] = None
                    set_status(f"Loaded: {path}")
                    redraw()

    tk_canvas.bind('<Button-1>',   on_click)
    tk_canvas.bind('<B1-Motion>',  on_drag)
    tk_canvas.bind('<ButtonRelease-1>', on_release)
    root.bind('<Key>', on_key)

    # Help panel
    help_text = (
        "R = Process □   D = Decision ◇   I = I/O ○\n"
        "E = Draw edge    Del = Delete    W = Word dump\n"
        "L = Load → emulator    Ctrl+S/O = Save/Load"
    )
    tk.Label(frame, text=help_text, bg=COL_STATUS, fg='#4a9eff',
             font=('Monospace', 9), justify='left', padx=8
             ).pack(side='bottom', fill='x', pady=0)

    redraw()
    set_status("FlowCode v0.1.0 ready — "
               "R=Process  D=Decision  I=IO  E=Edge  W=Words  L=Load")
    root.mainloop()


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if '--headless' in sys.argv or '--test' in sys.argv:
        run_headless_demo()
    else:
        run_gui()
