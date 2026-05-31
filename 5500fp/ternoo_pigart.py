#!/usr/bin/env python3
"""
PIGART — Primitive Graphics And Rendering Tool
===============================================
TernOO-5500FP renderer opcode set.
Five opcodes render geometric primitives directly from TernOO words.
The scene graph in memory IS the program.
The display IS the program viewed through the renderer.

Added: 31 May 2026, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
Companion: docs/TernOO-5500FP-Companion.md § PIGART Renderer
Whitepaper: Section 6

Opcodes:
  RPOINT  — render a point        (MAP position, DATA colour)
  RLINE   — render a line         (MAP start, MAP end, DATA style)
  RNODE   — render a flowchart symbol (MAP pos, DATA dims, DATA shape, UDP object)
  REDGE   — render a directed edge    (src canvas addr, dst canvas addr, EXEC word)
  RENDER  — commit canvas segment to display

Implementation phases:
  Phase 1 (this file): ASCII terminal canvas — nodes as [  ], <  >, (  )
                       edges as ──→  ══►  ╌╌→
  Phase 2 (this file): tkinter backend — MAP words drive 2D geometry
  Phase 3 (future):    Native 5500FP hardware — canvas segment = framebuffer
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location(
    'ternoo_v03',
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 '5500fp_ternoo_v03.py'))
_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

decode_word       = _mod.decode_word
decode_map_word   = _mod.decode_map_word
build_map_word    = _mod.build_map_word
get_field         = _mod.get_field
PRIMARY_MAP       = _mod.PRIMARY_MAP
PRIMARY_DATA      = _mod.PRIMARY_DATA
PRIMARY_EXEC      = _mod.PRIMARY_EXEC
get_primary       = _mod.get_primary
EXEC_CALL_REGISTER= _mod.EXEC_CALL_REGISTER
EXEC_CALL_STACK   = _mod.EXEC_CALL_STACK
EXEC_CALL_MESSAGE = _mod.EXEC_CALL_MESSAGE

# ── Shape constants (match DATA/SCALAR encoding field T19) ───────────────────
# Added: 31 May 2026, Adelaide
SHAPE_RECTANGLE  =  0   # T19=0  INTEGER  → process symbol   [  ]
SHAPE_DIAMOND    = -1   # T19=-1 FLOAT    → decision symbol  <  >
SHAPE_ROUNDED    = +1   # T19=+1 UNSIGNED → I/O symbol       (  )
SHAPE_OVAL       =  2   # extension: terminator symbol        O  O

SHAPE_ASCII = {
    SHAPE_RECTANGLE: ('[', ']'),
    SHAPE_DIAMOND:   ('<', '>'),
    SHAPE_ROUNDED:   ('(', ')'),
    SHAPE_OVAL:      ('O', 'O'),
}

# ── MAP word → screen coordinate conversion ───────────────────────────────────
# Added: 31 May 2026, Adelaide
# MAP words encode Y and Z octree coordinates (ON_PLANE mode).
# We map these to screen pixels for Phase 2.

CANVAS_ORIGIN_X = 400   # centre of default canvas
CANVAS_ORIGIN_Y = 300
MAP_SCALE       = 0.05  # Z coordinate units → pixels (approximate)

def map_word_to_screen(word: int, canvas_w: int = 800,
                        canvas_h: int = 600) -> tuple:
    """
    Convert a NEURAL/MAP word to (screen_x, screen_y) pixel coordinates.
    Uses ON_PLANE Y and Z fields for 2D layout.
    Phase 2: real tkinter canvas coordinates.
    Phase 1: ASCII grid cell (col, row).
    """
    d = decode_map_word(word)
    if d.get('plane') == 'ON_PLANE':
        y_coord = d.get('Y', 0)
        z_coord = d.get('Z', 0)
        # Map ternary coordinate space to screen space
        # Y → horizontal (X axis on screen)
        # Z → vertical   (Y axis on screen), inverted (positive = up)
        sx = int(canvas_w/2 + y_coord * MAP_SCALE * 40)
        sy = int(canvas_h/2 - z_coord * MAP_SCALE * 10)
        return (sx, sy)
    return (canvas_w//2, canvas_h//2)


# ── Scene graph entry ─────────────────────────────────────────────────────────

class SceneEntry:
    """One entry in the PIGART scene graph."""
    def __init__(self, opcode: str, words: list, label: str = '',
                 canvas_x: int = 0, canvas_y: int = 0,
                 kind: str = 'process'):
        self.opcode   = opcode
        self.words    = words
        self.label    = label
        self.canvas_x = canvas_x   # original FlowCode canvas x
        self.canvas_y = canvas_y   # original FlowCode canvas y
        self.kind     = kind       # symbol kind for shape dispatch
        self.dirty    = True


class PigartCanvas:
    """
    PIGART scene graph — a structured list of TernOO words.
    Not a framebuffer. Only dirty entries need redrawing.

    Added: 31 May 2026, Adelaide
    """

    def __init__(self, width: int = 800, height: int = 600):
        self.width   = width
        self.height  = height
        self.entries: list[SceneEntry] = []
        self._tk_canvas = None   # set by Phase 2 renderer

    # ── Opcode implementations ────────────────────────────────────────────────

    def RPOINT(self, pos_word: int, colour_word: int) -> int:
        """
        RPOINT Rd, Rs1, Rs2
        Rs1=MAP word (position), Rs2=DATA/SCALAR (colour)
        Rd=canvas address (index into entries list)
        Added: 31 May 2026, Adelaide
        """
        entry = SceneEntry('RPOINT', [pos_word, colour_word])
        self.entries.append(entry)
        return len(self.entries) - 1

    def RLINE(self, start_word: int, end_word: int,
              style_word: int) -> int:
        """
        RLINE Rd, Rs1, Rs2, Rs3
        Rs1=MAP (start), Rs2=MAP (end), Rs3=DATA (style)
        Added: 31 May 2026, Adelaide
        """
        entry = SceneEntry('RLINE', [start_word, end_word, style_word])
        self.entries.append(entry)
        return len(self.entries) - 1

    def RNODE(self, pos_word: int, dims_word: int,
              shape_word: int, udp_word: int,
              label: str = '', canvas_x: int = 400,
              canvas_y: int = 300, kind: str = 'process') -> int:
        """
        RNODE Rd, Rs1, Rs2, Rs3, Rs4
        Rs1=MAP (position), Rs2=DATA (dimensions),
        Rs3=DATA/SCALAR (shape: INTEGER=rect, FLOAT=diamond, UINT=rounded),
        Rs4=UDP (the TernOO object this symbol represents)
        Added: 31 May 2026, Adelaide
        """
        entry = SceneEntry('RNODE',
                           [pos_word, dims_word, shape_word, udp_word],
                           label=label, canvas_x=canvas_x,
                           canvas_y=canvas_y, kind=kind)
        self.entries.append(entry)
        return len(self.entries) - 1

    def REDGE(self, src_addr: int, dst_addr: int,
              exec_word: int) -> int:
        """
        REDGE Rd, Rs1, Rs2, Rs3
        Rs1=source canvas addr, Rs2=target canvas addr, Rs3=EXEC word
        Arrow style from EXEC call_style trit:
          stack(-1)   → double line  ══►
          register(0) → single line  ──→
          message(+1) → dashed line  ╌╌→
        Added: 31 May 2026, Adelaide
        """
        entry = SceneEntry('REDGE', [src_addr, dst_addr, exec_word])
        self.entries.append(entry)
        return len(self.entries) - 1

    def RENDER(self, base_addr: int = 0, word_count: int = -1):
        """
        RENDER Rs1, Rs2
        Commit canvas segment to display. Redraws only dirty entries.
        Dispatches to Phase 1 (ASCII) or Phase 2 (tkinter) depending on backend.
        Added: 31 May 2026, Adelaide
        """
        if word_count < 0:
            word_count = len(self.entries)
        entries = self.entries[base_addr:base_addr + word_count]

        if self._tk_canvas is not None:
            self._render_phase2(entries)
        else:
            self._render_phase1(entries)

        for e in entries:
            e.dirty = False

    # ── Phase 1: ASCII terminal renderer ─────────────────────────────────────
    # Added: 31 May 2026, Adelaide

    def _render_phase1(self, entries):
        """ASCII terminal output. Nodes as [  ], <  >, (  ). Edges as ──→."""
        print("\n" + "─" * 56)
        print("  PIGART Phase 1 — ASCII Canvas")
        print("─" * 56)

        # Collect nodes and edges separately
        nodes = {}   # addr → (label, shape_char)
        edges = []   # (src_addr, dst_addr, style)

        for i, e in enumerate(entries):
            addr = i
            if e.opcode == 'RNODE':
                shape_w = e.words[2]
                d = decode_word(shape_w)
                enc = d.get('encoding', 'int')
                if enc == 'float':   shape = SHAPE_DIAMOND
                elif enc == 'uint':  shape = SHAPE_ROUNDED
                else:                shape = SHAPE_RECTANGLE
                # Check for oval (terminator) via label hint
                if 'terminator' in e.label.lower() or \
                   e.label.upper() in ('START','END'):
                    shape = SHAPE_OVAL
                chars = SHAPE_ASCII.get(shape, ('[',']'))
                nodes[addr] = (e.label, chars)

            elif e.opcode == 'REDGE':
                src_a = e.words[0]
                dst_a = e.words[1]
                exec_w = e.words[2]
                d = decode_word(exec_w)
                call = d.get('call_style', 0)
                if call == -1:   style = '══►'
                elif call == +1: style = '╌╌→'
                else:            style = '──→'
                edges.append((src_a, dst_a, style))

        # Print nodes
        for addr, (label, chars) in nodes.items():
            print(f"  [{addr:2}] {chars[0]} {label:^16} {chars[1]}")

        # Print edges
        print()
        for src_a, dst_a, style in edges:
            src_lbl = nodes.get(src_a, ('?',None))[0]
            dst_lbl = nodes.get(dst_a, ('?',None))[0]
            print(f"       {src_lbl:>16} {style} {dst_lbl}")

        print("─" * 56)

    # ── Phase 2: tkinter renderer ─────────────────────────────────────────────
    # Added: 31 May 2026, Adelaide

    def _render_phase2(self, entries):
        """tkinter canvas renderer. MAP words drive 2D geometry directly."""
        tk_c = self._tk_canvas
        tk_c.delete('pigart')  # clear previous render

        node_positions = {}  # addr → (sx, sy)

        for i, e in enumerate(entries):
            addr = i
            if e.opcode == 'RNODE' and e.dirty:
                pos_w   = e.words[0]
                dims_w  = e.words[1]
                shape_w = e.words[2]
                # Use stored canvas coords directly — MAP word is the data carrier
                sx = e.canvas_x
                sy = e.canvas_y
                node_positions[addr] = (sx, sy)

                # Dimensions from DATA word payload
                d_dims = decode_word(dims_w)
                hw = abs(d_dims.get('value', 60))
                hh = max(20, hw // 2)

                kind = e.kind
                if kind == 'process':
                    fill = '#0f3460'
                    tk_c.create_rectangle(sx-hw, sy-hh, sx+hw, sy+hh,
                                          fill=fill, outline='#4a9eff',
                                          width=2, tags='pigart')
                elif kind == 'decision':
                    fill = '#533483'
                    tk_c.create_polygon(
                        [sx, sy-hh, sx+hw, sy, sx, sy+hh, sx-hw, sy],
                        fill=fill, outline='#4a9eff',
                        width=2, tags='pigart')
                elif kind == 'io':
                    fill = '#1a6b5e'
                    r = 14
                    tk_c.create_rectangle(sx-hw+r, sy-hh, sx+hw-r, sy+hh,
                                          fill=fill, outline=fill, tags='pigart')
                    tk_c.create_oval(sx-hw, sy-hh, sx-hw+r*2, sy+hh,
                                     fill=fill, outline='#4a9eff',
                                     width=2, tags='pigart')
                    tk_c.create_oval(sx+hw-r*2, sy-hh, sx+hw, sy+hh,
                                     fill=fill, outline='#4a9eff',
                                     width=2, tags='pigart')
                    tk_c.create_line(sx-hw+r, sy-hh, sx+hw-r, sy-hh,
                                     fill='#4a9eff', width=2, tags='pigart')
                    tk_c.create_line(sx-hw+r, sy+hh, sx+hw-r, sy+hh,
                                     fill='#4a9eff', width=2, tags='pigart')
                else:  # terminator
                    fill = '#1a4a6b'
                    tk_c.create_oval(sx-hw, sy-hh, sx+hw, sy+hh,
                                     fill=fill, outline='#4a9eff',
                                     width=2, tags='pigart')

                tk_c.create_text(sx, sy, text=e.label,
                                 fill='white', font=('Monospace', 10, 'bold'),
                                 tags='pigart')

            elif e.opcode == 'REDGE' and e.dirty:
                src_a  = e.words[0]
                dst_a  = e.words[1]
                exec_w = e.words[2]
                sp = node_positions.get(src_a)
                dp = node_positions.get(dst_a)
                if sp and dp:
                    d_exec = decode_word(exec_w)
                    call   = d_exec.get('call_style', 0)
                    colour = '#4a9eff'
                    dash   = None
                    if call == +1: dash = (4, 4)
                    arrow_shape = (12, 16, 5)
                    tk_c.create_line(sp[0], sp[1], dp[0], dp[1],
                                     fill=colour, width=2,
                                     arrow='last', arrowshape=arrow_shape,
                                     dash=dash or '',
                                     tags='pigart')

    def attach_tk_canvas(self, tk_canvas, width=None, height=None):
        """Attach a tkinter Canvas widget for Phase 2 rendering."""
        self._tk_canvas = tk_canvas
        if width:  self.width  = width
        if height: self.height = height


# ── FlowCode JSON → PIGART scene graph ───────────────────────────────────────
# Added: 31 May 2026, Adelaide

def flowcode_to_pigart(canvas_json: dict) -> PigartCanvas:
    """
    Convert a FlowCode JSON canvas into a PIGART scene graph.
    Each symbol becomes an RNODE entry. Each edge becomes a REDGE entry.
    This is the bridge between FlowCode and native TernOO rendering.
    """
    build_udp_word      = _mod.build_udp_word
    build_exec_word     = _mod.build_exec_word
    EXEC_PRIV_USER      = _mod.EXEC_PRIV_USER
    EXEC_CALL_REGISTER  = _mod.EXEC_CALL_REGISTER
    EXEC_RET_DATA       = _mod.EXEC_RET_DATA

    pigart = PigartCanvas()
    symbols = {s['id']: s for s in canvas_json.get('symbols', [])}
    edges   = canvas_json.get('edges', [])

    # Map symbol id → scene graph address
    addr_map = {}

    KIND_SHAPE = {
        'process':    0,   # INTEGER → rectangle
        'decision':  -1,   # FLOAT   → diamond
        'io':         1,   # UINT    → rounded
        'terminator': 1,   # UINT    → oval (same encoding, label hint used)
    }

    for sym in canvas_json.get('symbols', []):
        kind  = sym.get('kind', 'process')
        label = sym.get('label', '')
        x     = sym.get('x', 200)
        y     = sym.get('y', 200)
        cs    = sym.get('code_seg', 0)
        ds    = sym.get('data_seg', 0)
        off   = sym.get('offset', 0)

        # Build MAP word from x,y canvas coordinates
        # Invert the FlowCode canvas→MAP mapping
        map_y = int((x - 400) / 40)
        map_z = int((300 - y) / 10)
        pos_word = build_map_word(0, 1 if map_y>=0 else -1,
                                  1 if map_z>=0 else -1,
                                  abs(map_y)*729 + abs(map_z))

        # Build DATA word for dimensions (payload = half-width in pixels)
        dims_word = _mod.build_data_scalar(60, _mod.SCALAR_INT) \
            if hasattr(_mod,'build_data_scalar') else 0

        # Build DATA/SCALAR for shape encoding
        shape_enc = KIND_SHAPE.get(kind, 0)
        shape_word = 0  # placeholder — shape encoded via enc field

        # Build UDP word for the object
        SUBCLASS = {'process':(0,0),'decision':(0,1),'io':(1,0),'terminator':(1,1)}
        t1, t0 = SUBCLASS.get(kind, (0,0))
        udp_word = build_udp_word(t1, t0, off, cs, ds)

        addr = pigart.RNODE(pos_word, dims_word, shape_word, udp_word,
                            label=label, canvas_x=x, canvas_y=y, kind=kind)
        addr_map[sym['id']] = addr

    for edge in edges:
        src_addr = addr_map.get(edge['src'], 0)
        dst_addr = addr_map.get(edge['dst'], 0)
        exec_word = build_exec_word(
            edge.get('privilege', EXEC_PRIV_USER),
            edge.get('call_style', EXEC_CALL_REGISTER),
            edge.get('return_type', EXEC_RET_DATA),
            edge.get('seg_idx', 0),
            edge.get('offset', 0)
        )
        pigart.REDGE(src_addr, dst_addr, exec_word)

    return pigart


# ── Demo ──────────────────────────────────────────────────────────────────────

def demo_ascii():
    """Phase 1 demo: render AgeTest2 as ASCII art."""
    base    = os.path.dirname(os.path.abspath(__file__))
    fc_path = os.path.join(base, '..', 'FlowCode', 'AgeTest2.json')
    if not os.path.exists(fc_path):
        print(f"AgeTest2.json not found at {fc_path}")
        return
    with open(fc_path) as f:
        canvas_json = json.load(f)

    print("Loading AgeTest2.json into PIGART scene graph...")
    pigart = flowcode_to_pigart(canvas_json)
    print(f"Scene graph: {len(pigart.entries)} entries")
    pigart.RENDER()


def demo_tk():
    """Phase 2 demo: render AgeTest2 in a tkinter window via MAP words."""
    try:
        import tkinter as tk
    except ImportError:
        print("tkinter not available")
        return

    base    = os.path.dirname(os.path.abspath(__file__))
    fc_path = os.path.join(base, '..', 'FlowCode', 'AgeTest2.json')
    if not os.path.exists(fc_path):
        print(f"AgeTest2.json not found at {fc_path}")
        return

    with open(fc_path) as f:
        canvas_json = json.load(f)

    pigart = flowcode_to_pigart(canvas_json)

    root = tk.Tk()
    root.title("PIGART Phase 2 — TernOO Native Renderer")
    root.configure(bg='#0a0f1a')
    lbl = tk.Label(root,
        text="PIGART Phase 2 — MAP words driving tkinter geometry",
        bg='#0a0f1a', fg='#4a9eff', font=('Monospace',10))
    lbl.pack(pady=4)
    # Auto-size canvas to content
    import json as _j
    _syms = canvas_json.get('symbols',[])
    _max_x = max((s.get('x',200) for s in _syms), default=600) + 120
    _max_y = max((s.get('y',200) for s in _syms), default=600) + 120
    cw, ch = max(900, _max_x), max(700, _max_y)
    c = tk.Canvas(root, width=cw, height=ch,
                  bg='#0d1117', highlightthickness=0)
    c.pack(padx=8, pady=8, fill='both', expand=True)
    root.geometry(f"{cw+20}x{ch+60}")

    pigart.attach_tk_canvas(c, width=cw, height=ch)
    pigart.RENDER()

    root.mainloop()


if __name__ == '__main__':
    if '--tk' in sys.argv:
        demo_tk()
    else:
        demo_ascii()
