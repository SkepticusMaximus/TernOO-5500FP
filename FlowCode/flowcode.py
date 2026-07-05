#!/usr/bin/env python3
"""
FlowCode  v0.6.0
================
Visual programming IDE for TernOO-5500FP.

New in v0.5.0:
  - Terminator symbol (oval) for START/END — keyboard shortcut T
  - Canvas clutter removed: UDP/EXEC text only on selected symbol/edge
  - Condition labels always visible on edges
  - Hover tooltip (700ms) shows UDP/EXEC word for any symbol or edge
  - default_output dropdown on Decision nodes (from outgoing edge conditions)
  - Arrowheads trimmed to symbol boundary

New in v0.4.0:
  - Symbol properties dialog (double-click symbol): label, code_seg, data_seg, offset
  - Edge properties dialog (double-click edge): condition label, call_style, privilege, return_type
  - Condition labels shown on canvas edges in yellow
  - Live TernOO word preview inside both dialogs

New in v0.3.0:
  - PIL-rendered palette icons (crisp symbol previews at 36x30px)
  - Right-angle edge routing: click src → click canvas waypoint → click dst
  - Connection points on symbol edges (not just centres)
  - Arrowheads on all edges
  - Graceful fallback to canvas-drawn icons if PIL not available

Requires:
    5500fp_ternoo.py (or 5500fp_ternoo_v03.py) in same directory
    tkinter:  sudo apt install python3-tk
    Pillow:   pip3 install Pillow  (optional, improves icons)
"""

import sys, os, json, math
from typing import List, Dict, Optional, Tuple

# ── Emulator import ───────────────────────────────────────────────────────────

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
        if os.path.exists(p): return p
    return None

def _find_interpreter():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ternoo_interpreter.py'),
        os.path.join(os.getcwd(), 'ternoo_interpreter.py'),
        os.path.expanduser('~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/ternoo_interpreter.py'),
    ]
    for p in candidates:
        if os.path.exists(p): return p
    return None

_emu_path  = _find_emulator()
_interp_path = _find_interpreter()
if _emu_path is None:
    print("ERROR: Cannot find 5500fp_ternoo.py"); sys.exit(1)

from importlib.util import spec_from_file_location, module_from_spec
import unittest.mock
_spec = spec_from_file_location("emu", _emu_path)
_emu  = module_from_spec(_spec)
with unittest.mock.patch.object(_emu, "__name__", "emu"):
    _spec.loader.exec_module(_emu)
globals().update({k: getattr(_emu,k) for k in dir(_emu) if not k.startswith('__')})

# Import interpreter if available
_TernOOInterpreter = None
if _interp_path:
    _ispec = spec_from_file_location("interp", _interp_path)
    _imod  = module_from_spec(_ispec)
    with unittest.mock.patch.object(_imod, "__name__", "interp"):
        _ispec.loader.exec_module(_imod)
    _TernOOInterpreter = _imod.TernOOInterpreter

# ── Compiler + engine (Phase 7b-1) ───────────────────────────────────────────
_compile_to_t5asm = None
_CompileError     = None
_compiler_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '..', '5500fp', 'compile_to_t5asm.py')
if os.path.exists(_compiler_path):
    _cspec = spec_from_file_location("compile_to_t5asm", _compiler_path)
    _cmod  = module_from_spec(_cspec)
    _cspec.loader.exec_module(_cmod)
    _compile_to_t5asm = _cmod.compile_wordstream_to_t5asm
    _CompileError     = _cmod.CompileError

# Absolute path to C emulator binary (built by Bundle 14).
# If missing, the Run button shows an error rather than crashing.
_engine_path = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', 'NASM-TernOO-5500FP-Emulator', 'c_emulator', '5500fp'))

# ── Brain loader (FlowCodeBrain / shadow-GHOST) ───────────────────────────────

def _find_neural():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '../5500fp/ternoo_neural.py'),
        os.path.expanduser('~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/ternoo_neural.py'),
    ]
    for p in candidates:
        if os.path.exists(p): return os.path.abspath(p)
    return None

def _find_brain_file():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '../5500fp/flowcode_brain.json'),
        os.path.expanduser('~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/flowcode_brain.json'),
    ]
    for p in candidates:
        if os.path.exists(p): return os.path.abspath(p)
    return None

def _find_ghost_brain():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '../5500fp/ghost_gui_brain.json'),
        os.path.expanduser('~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/ghost_gui_brain.json'),
    ]
    for p in candidates:
        if os.path.exists(p): return os.path.abspath(p)
    return None

def _find_bridge():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '../5500fp/ternoo_cambalache_bridge.py'),
        os.path.expanduser('~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/ternoo_cambalache_bridge.py'),
    ]
    for p in candidates:
        if os.path.exists(p): return os.path.abspath(p)
    return None

def _find_geometry():
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '../5500fp/ternoo_widget_geometry.py'),
        os.path.expanduser('~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/ternoo_widget_geometry.py'),
    ]
    for p in candidates:
        if os.path.exists(p): return os.path.abspath(p)
    return None

# ── GHOST brain + palette — loaded once at startup ────────────────────────────

_ghost_weights: dict = {}
_ghost_brain_path = _find_ghost_brain()
if _ghost_brain_path:
    try:
        with open(_ghost_brain_path) as _gf:
            _ghost_weights = json.load(_gf).get('weights', {})
        print(f"[FlowCode] GHOST brain loaded: {len(_ghost_weights)} types")
    except Exception as _ge:
        print(f"[FlowCode] GHOST brain load failed: {_ge}")

# palette: list of (mmoe_type, y_lo) sorted containers → menus
_ghost_palette_types: list = []
_bridge_path_fc = _find_bridge()
if _bridge_path_fc:
    try:
        from importlib.util import spec_from_file_location as _sfl2, module_from_spec as _mfs2
        _bspec = _sfl2('_ghost_bridge', _bridge_path_fc)
        _bmod  = _mfs2(_bspec)
        _bspec.loader.exec_module(_bmod)
        for _bt, _bi in _bmod.GUI_MMOE_TYPES.items():
            if _bt == 'gui_unknown': continue
            _ghost_palette_types.append((_bt, _bi.get('y_range', (0, 0))[0]))
        _ghost_palette_types.sort(key=lambda t: (-t[1], t[0]))
        print(f"[FlowCode] GHOST palette: {len(_ghost_palette_types)} widget types")
    except Exception as _gpe:
        print(f"[FlowCode] GHOST palette load failed: {_gpe}")

if not _ghost_palette_types:   # fallback if bridge not found
    _ghost_palette_types = [(t, 0) for t in [
        'gui_window','gui_box','gui_button','gui_entry',
        'gui_label','gui_dialog','gui_menu','gui_treeview']]

# ── Widget geometry — CC-09 ───────────────────────────────────────────────────
# Added: 01 Jun 2026, Adelaide  Author: Stevo + Claude
# Purpose: Load canonical RNODE/RLINE/RPOINT word sequences for guic_draw_widget
# Companion: private/TernOO-5500FP-Companion.md § G6 (CC-09)

_widget_geometry_mod = None
_geom_path_fc = _find_geometry()
if _geom_path_fc:
    try:
        from importlib.util import spec_from_file_location as _sfl3, module_from_spec as _mfs3
        _gspec = _sfl3('_wgeom', _geom_path_fc)
        _gmod  = _mfs3(_gspec)
        _gspec.loader.exec_module(_gmod)
        _widget_geometry_mod = _gmod
        print(f"[FlowCode] Widget geometry loaded: {len(_gmod.WIDGET_GEOMETRY)} types")
    except Exception as _wge:
        print(f"[FlowCode] Widget geometry load failed: {_wge}")

_neural_path = _find_neural()
_FlowCodeBrain = None
_brain_instance = None
if _neural_path:
    try:
        _nspec = spec_from_file_location("neural", _neural_path)
        _nmod  = module_from_spec(_nspec)
        with unittest.mock.patch.object(_nmod, "__name__", "neural"):
            _nspec.loader.exec_module(_nmod)
        _FlowCodeBrain = _nmod.FlowCodeBrain
        # Load existing trained brain if available
        _bf = _find_brain_file()
        if _bf:
            import json as _json
            with open(_bf) as _f:
                _bdata = _json.load(_f)
            _brain_instance = _FlowCodeBrain()
            # Restore weights from saved brain
            for cd in _bdata.get('connections', []):
                _brain_instance._set_weight(cd['source'], cd['target'], cd['weight'])
            print(f"[FlowCode] Brain loaded: {len(_bdata.get('connections',[]))} connections")
        else:
            _brain_instance = _FlowCodeBrain()
            print("[FlowCode] Brain initialised (no saved weights)")
    except Exception as _e:
        print(f"[FlowCode] Brain load failed: {_e}")

# ── Constants ─────────────────────────────────────────────────────────────────

SYMBOL_PROCESS    = 'process'
SYMBOL_DECISION   = 'decision'
SYMBOL_IO         = 'io'
SYMBOL_TERMINATOR = 'terminator'
SYMBOL_SUBCLASS = {
    SYMBOL_PROCESS:   (0,   0),
    SYMBOL_DECISION:  (0,  +1),
    SYMBOL_IO:        (+1,  0),
    SYMBOL_TERMINATOR:(+1, +1),
}
SYMBOL_W, SYMBOL_H, GRID = 120, 60, 40
CMD_W, CMD_H = 160, 80   # Stage 9-0: command-widget block size on Shell canvas
# Stage 8-1: Sheet grid geometry (design-space pixels at zoom 1.0)
CELL_W, CELL_H = 80, 24          # column width, row height
SHEET_ROW_HDR_W = 40             # row-number gutter width
SHEET_COL_HDR_H = 22             # column-letter header height
SHEET_ROWS, SHEET_COLS = 20, 8   # default visible grid

def _sheet_col_label(col):
    """0→A, 25→Z, 26→AA, … (spreadsheet column letters)."""
    s = ''
    col += 1
    while col > 0:
        col, r = divmod(col - 1, 26)
        s = chr(65 + r) + s
    return s

def _sheet_a1(row, col):
    """(row, col) zero-based → A1-style address, e.g. (0,0)→'A1'."""
    return f"{_sheet_col_label(col)}{row + 1}"

def snap(v): return round(v/GRID)*GRID

# ── Colours ───────────────────────────────────────────────────────────────────
C = {
    'bg':'#1a1a2e',       'canvas':'#16213e',    'grid':'#1e2a4a',
    'palette':'#0d1117',  'pal_btn':'#1e2a4a',   'pal_active':'#0f3460',
    'pal_border':'#4a9eff','process':'#0f3460',   'decision':'#533483',
    'io':'#1a6b5e',       'terminator':'#1a4a6b', 'border':'#4a9eff',    'selected':'#ff6b35',
    'edge':'#7ab4ff',     'edge_msg':'#ff9f43',  'edge_stk':'#ff6b9d',
    'text':'#e0e0e0',     'dim':'#556080',        'status':'#0d1117',
    'inspect':'#0a0f1a',  'inspect_fg':'#7ab4ff','waypoint':'#ffdd57',
}

# ── PIL icon generation ───────────────────────────────────────────────────────

def _hex_to_rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2],16) for i in (0,2,4))

def _make_icons():
    """Generate palette icons as PIL images. Returns dict of name→PhotoImage,
    or None if PIL unavailable (caller falls back to canvas drawing)."""
    try:
        from PIL import Image, ImageDraw
        import io as _io
        import tkinter as tk
    except ImportError:
        return None

    W, H = 36, 30
    BG   = (0,0,0,0)

    def new():
        img = Image.new('RGBA',(W,H),BG)
        return img, ImageDraw.Draw(img)

    def col(h, a=255):
        r,g,b = _hex_to_rgb(h)
        return (r,g,b,a)

    icons = {}

    # Process — rectangle
    img,d = new()
    d.rectangle([2,4,W-2,H-4], fill=col(C['process']), outline=col(C['border']), width=2)
    icons['process'] = img

    # Decision — diamond
    img,d = new()
    pts = [W//2,2, W-2,H//2, W//2,H-2, 2,H//2]
    d.polygon(pts, fill=col(C['decision']), outline=col(C['border']), width=0)
    d.line([W//2,2,W-2,H//2], fill=col(C['border']), width=2)
    d.line([W-2,H//2,W//2,H-2], fill=col(C['border']), width=2)
    d.line([W//2,H-2,2,H//2], fill=col(C['border']), width=2)
    d.line([2,H//2,W//2,2], fill=col(C['border']), width=2)
    icons['decision'] = img

    # I/O — rounded rectangle (stadium)
    img,d = new()
    r = H//2 - 3
    d.ellipse([2,3,2+r*2,H-3], fill=col(C['io']), outline=col(C['border']), width=2)
    d.ellipse([W-2-r*2,3,W-2,H-3], fill=col(C['io']), outline=col(C['border']), width=2)
    d.rectangle([2+r,3,W-2-r,H-3], fill=col(C['io']), outline=col(C['io']))
    d.line([2+r,3,W-2-r,3], fill=col(C['border']), width=2)
    d.line([2+r,H-3,W-2-r,H-3], fill=col(C['border']), width=2)
    icons['io'] = img

    # Terminator — full oval
    img,d = new()
    d.ellipse([2,3,W-2,H-3], fill=col(C['terminator']),
              outline=col(C['border']), width=2)
    icons['terminator'] = img

    # Edge — arrow
    img,d = new()
    d.line([4,H//2,W-8,H//2], fill=col(C['edge']), width=2)
    d.polygon([W-2,H//2, W-10,H//2-5, W-10,H//2+5],
              fill=col(C['edge']))
    icons['edge'] = img

    # Select — pointer arrow
    img,d = new()
    pts2 = [6,2, 6,22, 10,18, 14,26, 17,25, 13,17, 19,17]
    d.polygon(pts2, fill=col(C['text']), outline=col(C['border']), width=1)
    icons['select'] = img

    # Delete — X
    img,d = new()
    d.line([6,5,W-6,H-5], fill=(255,80,80,255), width=3)
    d.line([W-6,5,6,H-5], fill=(255,80,80,255), width=3)
    icons['delete'] = img

    # Word dump — down arrow with lines
    img,d = new()
    for i,y in enumerate([6,11,16]):
        x2 = W-4 if i==0 else (W-8 if i==1 else W-12)
        d.line([4,y,x2,y], fill=col(C['inspect_fg']), width=2)
    d.line([W//2,18,W//2,H-4], fill=col(C['inspect_fg']), width=2)
    d.polygon([W//2-5,H-4,W//2+5,H-4,W//2,H-1], fill=col(C['inspect_fg']))
    icons['dump'] = img

    # Load — play triangle
    img,d = new()
    d.polygon([4,4,4,H-4,W-4,H//2], fill=col('#7aff7a'))
    icons['load'] = img

    # Save — floppy-ish
    img,d = new()
    d.rectangle([4,4,W-4,H-4], fill=col(C['pal_btn']),
                outline=col(C['border']), width=2)
    d.rectangle([8,4,W-8,14], fill=col(C['dim']))
    d.rectangle([8,18,W-8,H-6], fill=col(C['canvas']))
    icons['save'] = img

    # Open — folder
    img,d = new()
    d.rectangle([4,10,W-4,H-4], fill=col(C['pal_btn']),
                outline=col(C['border']), width=2)
    d.rectangle([4,6,14,11], fill=col(C['pal_btn']),
                outline=col(C['border']), width=2)
    icons['open'] = img

    # Clear — trash
    img,d = new()
    d.rectangle([8,8,W-8,H-4], fill=col(C['pal_btn']),
                outline=(255,100,100,255), width=2)
    d.line([4,8,W-4,8], fill=(255,100,100,255), width=2)
    d.line([W//2-4,4,W//2+4,4], fill=(255,100,100,255), width=2)
    for x in [13,W//2,W-13]:
        d.line([x,10,x,H-6], fill=(255,100,100,255), width=1)
    icons['clear'] = img

    # Convert to tkinter PhotoImage
    result = {}
    for name, img in icons.items():
        buf = _io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        try:
            from PIL import ImageTk
            result[name] = ImageTk.PhotoImage(img)
        except Exception:
            result[name] = None
    return result

# ── Data model ────────────────────────────────────────────────────────────────

class FCSymbol:
    _next_id = 1
    def __init__(self, kind, x, y, label='', code_seg=0, data_seg=0):
        self.id       = FCSymbol._next_id; FCSymbol._next_id += 1
        self.kind     = kind
        self.x        = snap(x); self.y = snap(y)
        self.label    = label or f"{kind[0].upper()}{self.id}"
        self.code_seg = code_seg; self.data_seg = data_seg; self.offset = 0
        self.default_output: str = ''  # Decision only: fallback if no handler
        self.default_output: str = ''  # Decision only: pushed to stack if no handler

    def connection_points(self):
        """Return dict of named edge attachment points."""
        hw, hh = SYMBOL_W//2, SYMBOL_H//2
        return {'N':(self.x,self.y-hh), 'S':(self.x,self.y+hh),
                'E':(self.x+hw,self.y), 'W':(self.x-hw,self.y),
                'C':(self.x,self.y)}

    def nearest_cp(self, tx, ty):
        """Return the connection point nearest to (tx,ty)."""
        best, bd = 'C', float('inf')
        for name,(cx,cy) in self.connection_points().items():
            d = (cx-tx)**2+(cy-ty)**2
            if d < bd: best,bd = name,d
        return best

    def to_map_word(self):
        cx = max(-364,min(364,self.x-364))
        cy = max(-364,min(364,self.y-364))
        return build_map_word(0,1 if cx>=0 else -1,1 if cy>=0 else -1,
                              abs(cx)*729+abs(cy))

    def to_udp_word(self):
        t1,t0 = SYMBOL_SUBCLASS[self.kind]
        return build_udp_word(t1,t0,self.offset,self.code_seg,self.data_seg)

    def to_dict(self):
        return {'id':self.id,'kind':self.kind,'x':self.x,'y':self.y,
                'label':self.label,'code_seg':self.code_seg,
                'data_seg':self.data_seg,'offset':self.offset,
                'default_output':self.default_output}

    @classmethod
    def from_dict(cls,d):
        s = cls(d['kind'],d['x'],d['y'],d.get('label',''),
                d.get('code_seg',0),d.get('data_seg',0))
        s.id=d['id']; s.offset=d.get('offset',0)
        s.default_output = d.get('default_output','')
        FCSymbol._next_id = max(FCSymbol._next_id, s.id+1)
        return s


class FCEdge:
    def __init__(self, src_id, dst_id,
                 privilege=EXEC_PRIV_USER, call_style=EXEC_CALL_REGISTER,
                 return_type=EXEC_RET_DATA, seg_idx=0, offset=0,
                 waypoints=None, condition=''):
        self.src_id=src_id; self.dst_id=dst_id
        self.privilege=privilege; self.call_style=call_style
        self.return_type=return_type; self.seg_idx=seg_idx; self.offset=offset
        self.waypoints: List[Tuple[int,int]] = waypoints or []
        self.condition: str = condition  # branch label e.g. 'yes','no','true','false'

    def to_exec_word(self):
        return build_exec_word(self.privilege,self.call_style,self.return_type,
                               self.seg_idx,self.offset)

    def to_dict(self):
        return {'src':self.src_id,'dst':self.dst_id,
                'privilege':self.privilege,'call_style':self.call_style,
                'return_type':self.return_type,'seg_idx':self.seg_idx,
                'offset':self.offset,'waypoints':self.waypoints,
                'condition':self.condition}

    @classmethod
    def from_dict(cls,d):
        return cls(d['src'],d['dst'],d.get('privilege',EXEC_PRIV_USER),
                   d.get('call_style',EXEC_CALL_REGISTER),
                   d.get('return_type',EXEC_RET_DATA),
                   d.get('seg_idx',0),d.get('offset',0),
                   [tuple(w) for w in d.get('waypoints',[])],
                   d.get('condition',''))


class FCCanvas:
    def __init__(self):
        self.symbols: Dict[int,FCSymbol] = {}
        self.edges:   List[FCEdge]       = []

    def add_symbol(self,kind,x,y,label=''):
        s=FCSymbol(kind,x,y,label); self.symbols[s.id]=s; return s

    def add_edge(self,src_id,dst_id,waypoints=None,**kw):
        if src_id not in self.symbols or dst_id not in self.symbols: return None
        for e in self.edges:
            if e.src_id==src_id and e.dst_id==dst_id: return None
        e=FCEdge(src_id,dst_id,waypoints=waypoints or [],**kw)
        self.edges.append(e); return e

    def remove_symbol(self,sid):
        self.symbols.pop(sid,None)
        self.edges=[e for e in self.edges if e.src_id!=sid and e.dst_id!=sid]

    def remove_edge(self,src_id,dst_id):
        self.edges=[e for e in self.edges
                    if not(e.src_id==src_id and e.dst_id==dst_id)]

    def symbol_at(self,x,y):
        hw,hh=SYMBOL_W//2,SYMBOL_H//2
        for s in reversed(list(self.symbols.values())):
            if abs(s.x-x)<=hw and abs(s.y-y)<=hh: return s
        return None

    def edge_near(self,x,y,tol=12):
        """Return edge whose path passes near (x,y)."""
        for e in self.edges:
            pts = self._edge_points(e)
            for i in range(len(pts)-1):
                x1,y1=pts[i]; x2,y2=pts[i+1]
                # distance from point to segment
                dx,dy=x2-x1,y2-y1
                if dx==0 and dy==0: continue
                t=max(0,min(1,((x-x1)*dx+(y-y1)*dy)/(dx*dx+dy*dy)))
                px,py=x1+t*dx,y1+t*dy
                if (px-x)**2+(py-y)**2 <= tol**2: return e
        return None

    def _edge_points(self, e: FCEdge) -> List[Tuple[int,int]]:
        """Return point list trimmed to destination symbol boundary."""
        src = self.symbols.get(e.src_id)
        dst = self.symbols.get(e.dst_id)
        if not src or not dst: return []
        hw, hh = SYMBOL_W//2, SYMBOL_H//2
        pts_before = [(src.x, src.y)] + list(e.waypoints)
        cx, cy = dst.x, dst.y
        px, py = pts_before[-1]
        dx, dy = cx - px, cy - py
        dist = (dx*dx + dy*dy) ** 0.5
        if dist > 0:
            import math as _m
            adx, ady = abs(dx)/dist, abs(dy)/dist
            if dst.kind == SYMBOL_DECISION:
                margin = hw*adx + hh*ady
            elif dst.kind in (SYMBOL_IO, SYMBOL_TERMINATOR):
                a = _m.atan2(dy, dx)
                margin = (hw*hh)/max(1,_m.sqrt((hh*_m.cos(a))**2+(hw*_m.sin(a))**2))
            else:
                margin = min(hw/max(adx,0.001), hh/max(ady,0.001))
                margin = min(margin, hw)
            ex = cx - dx/dist*(margin+3)
            ey = cy - dy/dist*(margin+3)
        else:
            ex, ey = cx, cy
        return pts_before + [(int(ex), int(ey))]

    def _ortho_points(self, e: FCEdge) -> List[Tuple[int,int]]:
        """Return orthogonal (right-angle) routing through waypoints."""
        raw = self._edge_points(e)
        if len(raw) < 2: return raw
        result = [raw[0]]
        for i in range(1, len(raw)):
            px, py = result[-1]
            nx, ny = raw[i]
            # Route: horizontal then vertical (L-shape)
            if px != nx and py != ny:
                result.append((nx, py))   # elbow point
            result.append((nx, ny))
        return result

    def to_word_program(self):
        words = []
        for s in self.symbols.values():
            words.append((f"MAP  #{s.id} {s.label}", s.to_map_word()))
            words.append((f"UDP  #{s.id} {s.label}", s.to_udp_word()))
        for e in self.edges:
            src=self.symbols.get(e.src_id); dst=self.symbols.get(e.dst_id)
            sl=src.label if src else f"#{e.src_id}"
            dl=dst.label if dst else f"#{e.dst_id}"
            words.append((f"EXEC {sl}→{dl}", e.to_exec_word()))
        return words

    def load_into_emulator(self,cpu,start=100):
        words=self.to_word_program()
        for i,(_,w) in enumerate(words): cpu.mem_write(start+i,w)
        return start+len(words)

    def print_word_dump(self):
        words=self.to_word_program()
        print(f"\n{'─'*60}\nFlowCode → TernOO Word Dump")
        print(f"  {len(self.symbols)} symbols  {len(self.edges)} edges"
              f"  {len(words)} words\n{'─'*60}")
        for label,word in words:
            print(f"  {label:<28} {word_to_str(word)}")
            print(f"  {'':28} {describe_word(word)}")
        print(f"{'─'*60}\n")

    def save(self,path):
        with open(path,'w') as f:
            json.dump({'symbols':[s.to_dict() for s in self.symbols.values()],
                       'edges':[e.to_dict() for e in self.edges]},f,indent=2)
        print(f"Saved: {path}")

    def load(self,path):
        with open(path) as f: data=json.load(f)
        self.symbols.clear(); self.edges.clear()
        for d in data.get('symbols',[]): s=FCSymbol.from_dict(d); self.symbols[s.id]=s
        for d in data.get('edges',[]): self.edges.append(FCEdge.from_dict(d))
        print(f"Loaded: {path}")

    def ascii_render(self):
        lines=["FlowCode Canvas:",""]
        sh={SYMBOL_PROCESS:'[{l}]',SYMBOL_DECISION:'<{l}>',SYMBOL_IO:'({l})'}
        for s in self.symbols.values():
            lines.append(f"  {sh.get(s.kind,'{l}').format(l=s.label):<20}"
                         f" @({s.x:4d},{s.y:4d})")
        if self.edges:
            lines.append("")
            for e in self.edges:
                src=self.symbols.get(e.src_id); dst=self.symbols.get(e.dst_id)
                sl=src.label if src else f"#{e.src_id}"
                dl=dst.label if dst else f"#{e.dst_id}"
                wp=f" via {len(e.waypoints)} waypoints" if e.waypoints else ""
                call={-1:'stk',0:'reg',1:'msg'}.get(e.call_style,'?')
                lines.append(f"    {sl} ──[{call}]──→ {dl}{wp}")
        return '\n'.join(lines)


# ── Headless demo ─────────────────────────────────────────────────────────────

def run_headless_demo():
    print("="*60+"\nFlowCode v0.7.0 — Headless Demo\n"+"="*60)
    canvas=FCCanvas()
    start=canvas.add_symbol(SYMBOL_IO,200,80,"START")
    check=canvas.add_symbol(SYMBOL_DECISION,200,240,"CHECK")
    proc=canvas.add_symbol(SYMBOL_PROCESS,360,320,"PROCESS")
    end=canvas.add_symbol(SYMBOL_IO,200,480,"END")
    canvas.add_edge(start.id,check.id)
    canvas.add_edge(check.id,proc.id,waypoints=[(280,240)],
                    call_style=EXEC_CALL_MESSAGE)
    canvas.add_edge(check.id,end.id)
    canvas.add_edge(proc.id,end.id,waypoints=[(360,480)])
    print(canvas.ascii_render()); print()
    canvas.print_word_dump()
    cpu=CPU5500FP(); cpu.write_cs(0,1000); cpu.write_ds(0,2000)
    end_addr=canvas.load_into_emulator(cpu,100)
    words=canvas.to_word_program()
    ok=all(cpu.mem_read(100+i)==w for i,(_,w) in enumerate(words))
    print(f"Emulator round-trip: {'PASS' if ok else 'FAIL'} ({len(words)} words)")


# ── GUI ───────────────────────────────────────────────────────────────────────

def run_gui():
    try:
        import tkinter as tk
        from tkinter import filedialog, simpledialog, messagebox, ttk
    except ImportError:
        print("tkinter not available — sudo apt install python3-tk")
        run_headless_demo(); return

    PALETTE_W = 140

    canvas_model = FCCanvas()      # Phase 6C: kept for execution only (do_run/do_dump/do_load)
    cpu = CPU5500FP(); cpu.write_cs(0,1000); cpu.write_ds(0,2000)

    # Phase 6C: draw-kind map — flow_* namespace → old SYMBOL_* draw constants
    _FC_KIND_DRAW = {
        'flow_terminator': SYMBOL_TERMINATOR,
        'flow_process':    SYMBOL_PROCESS,
        'flow_decision':   SYMBOL_DECISION,
        'flow_io':         SYMBOL_IO,
        'flow_subroutine': SYMBOL_PROCESS,    # rectangle, double-border added in draw
        'flow_connector':  SYMBOL_TERMINATOR, # circle (small)
    }
    # Phase 6C: palette mode → flow kind
    _FC_PLACE_KIND = {
        'place_terminator': 'flow_terminator',
        'place_process':    'flow_process',
        'place_decision':   'flow_decision',
        'place_io':         'flow_io',
    }

    state = {
        'mode':            'select',
        'selected_sym':    None,
        'selected_edge':   None,
        'edge_src':        None,
        'edge_waypoints':  [],      # collected waypoints for current edge
        'drag_offset':     (0, 0),
        'dragging':        False,
        'ghost':           None,
        'hover_wp':        None,    # waypoint index being hovered
        'fc_drag_origin':  None,    # Phase 6C: (x,y) at drag-start for undo
    }

    # ── Root ─────────────────────────────────────────────────────────────────
    root = tk.Tk()
    root.title("FlowCode v0.7.0 — TernOO-5500FP Visual IDE")
    root.configure(bg=C['bg'])
    root.resizable(True,True)
    root.minsize(960, 600)   # Bundle 17 B1: usable at 1366×768

    outer = tk.Frame(root,bg=C['bg']); outer.pack(fill='both',expand=True)
    palette_frame = tk.Frame(outer,bg=C['palette'],width=PALETTE_W)
    palette_frame.pack(side='left',fill='y'); palette_frame.pack_propagate(False)

    # Tab-aware tools sub-frame (middle of sidebar — content rebuilt per tab)
    _pal_tools_frame = tk.Frame(palette_frame, bg=C['palette'])

    # ── Tabbed right panel ────────────────────────────────────────────────────
    right_outer = tk.Frame(outer,bg=C['bg'])
    right_outer.pack(side='left',fill='both',expand=True)

    # Style the notebook to match dark theme
    _nb_style = ttk.Style()
    _nb_style.theme_use('default')
    _nb_style.configure('TNotebook', background=C['palette'], borderwidth=0)
    _nb_style.configure('TNotebook.Tab', background=C['pal_btn'], foreground=C['text'],
                        padding=[12, 4], font=('Monospace', 9))
    _nb_style.map('TNotebook.Tab',
                  background=[('selected', C['pal_active'])],
                  foreground=[('selected', C['pal_border'])])

    # ── Run output panel (Phase 7b-1 + Bundle 17 B2: collapsible) ───────────
    # Pack order (side='bottom'): toggle header → panel → notebook fills rest.
    _output_collapsed = [False]

    _run_toggle_hdr = tk.Frame(right_outer, bg=C['palette'], cursor='hand2')
    _run_toggle_hdr.pack(side='bottom', fill='x')
    _run_toggle_lbl = tk.Label(_run_toggle_hdr, text='▾ Output',
                               bg=C['palette'], fg=C['pal_border'],
                               font=('Monospace', 8, 'bold'), anchor='w',
                               padx=6, pady=1, cursor='hand2')
    _run_toggle_lbl.pack(side='left')

    _run_panel = tk.Frame(right_outer, bg=C['palette'], height=120)
    _run_panel.pack(side='bottom', fill='x')
    _run_panel.pack_propagate(False)
    _run_inner = tk.Frame(_run_panel, bg=C['inspect'])
    _run_inner.pack(fill='both', expand=True)
    _run_txt = tk.Text(_run_inner, bg=C['inspect'], fg=C['text'],
                       font=('Monospace', 8), state='disabled',
                       wrap='word', relief='flat', padx=6, pady=4,
                       insertbackground=C['text'])
    _run_sb  = tk.Scrollbar(_run_inner, command=_run_txt.yview, bg=C['palette'])
    _run_txt.configure(yscrollcommand=_run_sb.set)
    _run_sb.pack(side='right', fill='y')
    _run_txt.pack(fill='both', expand=True)
    _run_txt.tag_config('header_run', foreground='#5599ff')
    _run_txt.tag_config('header_ok',  foreground='#7aff7a')
    _run_txt.tag_config('header_err', foreground='#ff6666')
    _run_txt.tag_config('stderr_out', foreground='#cc8844')

    def _toggle_output_panel(e=None):
        _output_collapsed[0] = not _output_collapsed[0]
        if _output_collapsed[0]:
            _run_panel.pack_forget()
            _run_toggle_lbl.config(text='▸ Output')
        else:
            _run_panel.pack(side='bottom', fill='x', before=_run_toggle_hdr)
            _run_toggle_lbl.config(text='▾ Output')
    _run_toggle_hdr.bind('<Button-1>', _toggle_output_panel)
    _run_toggle_lbl.bind('<Button-1>', _toggle_output_panel)

    notebook = ttk.Notebook(right_outer)
    notebook.pack(fill='both',expand=True)

    # ── Tab 1: FlowCode ───────────────────────────────────────────────────────
    fc_tab = tk.Frame(notebook,bg=C['bg'])
    notebook.add(fc_tab, text='  Flow  ')

    # Phase 7c-4: breadcrumb bar (pocket scope path) above the Flow canvas
    _fc_breadcrumb = tk.Frame(fc_tab, bg=C['palette'])
    _fc_breadcrumb.pack(side='top', fill='x')

    _fc_cv_frame = tk.Frame(fc_tab, bg=C['canvas'])
    _fc_cv_frame.pack(side='top', fill='both', expand=True)
    _fc_vsb = tk.Scrollbar(_fc_cv_frame, orient='vertical',   bg=C['palette'])
    _fc_hsb = tk.Scrollbar(_fc_cv_frame, orient='horizontal', bg=C['palette'])
    _fc_hsb.pack(side='bottom', fill='x')
    _fc_vsb.pack(side='right',  fill='y')
    tk_canvas = tk.Canvas(_fc_cv_frame, bg=C['canvas'], highlightthickness=0)
    tk_canvas.pack(fill='both', expand=True)
    inspect = tk.Label(fc_tab,text="Select a symbol or edge to inspect",
                       bg=C['inspect'],fg=C['inspect_fg'],
                       font=('Monospace',9),anchor='nw',justify='left',
                       padx=8,pady=4,height=6)
    inspect.pack(side='top',fill='x')
    _fc_status_frame = tk.Frame(fc_tab, bg=C['status'])
    _fc_status_frame.pack(side='bottom', fill='x')
    status = tk.Label(_fc_status_frame, text="Ready", anchor='w',
                      bg=C['status'], fg=C['pal_border'],
                      font=('Monospace', 9), padx=8)
    status.pack(side='left', fill='x', expand=True, ipady=3)
    _fc_zoom_lbl = tk.Label(_fc_status_frame, text='Zoom: 100%', anchor='e',
                            bg=C['status'], fg=C['dim'],
                            font=('Monospace', 8), padx=8)
    _fc_zoom_lbl.pack(side='right', ipady=3)

    # ── Tab 2: GHOST Canvas (built below after FlowCode palette) ─────────────
    ghost_tab = tk.Frame(notebook,bg=C['bg'])
    notebook.add(ghost_tab, text='  GUI  ')

    # ── Tab 3: Sheet — spreadsheet grid (Stage 8-1, built below). Internal
    # symbol sheet_tab; the third leg of the trinity. ─────────────────────────
    sheet_tab = tk.Frame(notebook,bg=C['bg'])
    notebook.add(sheet_tab, text='  Sheet  ')

    # ── Text tab — dual-mode editor (text/language bundle Piece 1). View
    # class lives in 5500fp/text_tab_view.py; mounted after fc_state exists. ──
    text_tab = tk.Frame(notebook,bg=C['bg'])
    notebook.add(text_tab, text='  Text  ')

    # ── Tab 4: Shell — three-pane command builder (Bundle 24). Internal symbol
    # stays sh_tab; the three-pane _lingo_view lives here. ────────────────────
    sh_tab = tk.Frame(notebook,bg=C['bg'])
    notebook.add(sh_tab, text='  Shell  ')

    # ── Tab 4: Connectors — Stage 9-0 cmd_* canvas (Bundle 24). Internal symbol
    # conn_tab; hosts the canvas (_sh_cv_frame etc.). Future: binding graph. ───
    conn_tab = tk.Frame(notebook,bg=C['bg'])
    notebook.add(conn_tab, text='  Connectors  ')

    # ── Tab 5: Lingo — OTree/vocabulary explorer (Bundle 13). Internal symbol
    # stays gm_tab; module is still ternoo_gristmill / GristMill concept. The
    # "GristMill" name is reserved for the future package-manager arc. ─────────
    gm_tab = tk.Frame(notebook,bg=C['bg'])
    notebook.add(gm_tab, text='  Babble-Fish  ')
    # ── Tab 8: GHOST — the Academy (chat + curriculum + harness). View
    #    class lives in 5500fp/ghost_tab_view.py; mounted at the bottom of
    #    this file alongside the Text/Translator mounts.
    academy_tab = tk.Frame(notebook, bg=C['bg'])
    notebook.add(academy_tab, text='  GHOST  ')
    # Piece 2: Lingo hosts two views — Vocabulary (GristMillTabView, as
    # before) and Translator (multi-dialect projections). Toggle header:
    _lingo_hdr = tk.Frame(gm_tab, bg=C['palette'])
    _lingo_hdr.pack(side='top', fill='x')
    _lingo_vocab_frame = tk.Frame(gm_tab, bg=C['bg'])
    _lingo_trans_frame = tk.Frame(gm_tab, bg=C['bg'])
    _lingo_view_btns = {}
    def _lingo_show_view(which):
        _lingo_vocab_frame.pack_forget(); _lingo_trans_frame.pack_forget()
        (_lingo_vocab_frame if which == 'vocab'
         else _lingo_trans_frame).pack(fill='both', expand=True)
        for k, b in _lingo_view_btns.items():
            b.config(fg=C['pal_border'] if k == which else C['dim'])
        if which == 'trans' and _translator_view[0] is not None:
            _translator_view[0].refresh()
    for _k, _lbl in (('vocab', 'Vocabulary'), ('trans', 'Translator')):
        _b = tk.Button(_lingo_hdr, text=_lbl, bg=C['palette'], fg=C['dim'],
                       font=('Monospace', 9, 'bold'), relief='flat', bd=0,
                       activebackground=C['palette'], cursor='hand2',
                       padx=10, pady=3,
                       command=lambda k=_k: _lingo_show_view(k))
        _b.pack(side='left')
        _lingo_view_btns[_k] = _b
    _translator_view = [None]
    _lingo_show_view('vocab')

    def set_status(m): status.config(text=m)
    def set_inspect(m): inspect.config(text=m)

    # ── Bundle 18: Flow canvas viewport state + coord helpers ─────────────────
    _fc_view = {'zoom': 1.0, 'sx': 0.0, 'sy': 0.0}
    _fc_pan  = [None]   # [{'ox':, 'oy':, 'ex':, 'ey':}] during middle-drag, else None

    def _fc_d2s(dx, dy):
        """Design → screen coords for the Flow canvas."""
        z = _fc_view['zoom']
        return (dx - _fc_view['sx']) * z, (dy - _fc_view['sy']) * z

    def _fc_s2d(ex, ey):
        """Screen → design coords for the Flow canvas."""
        z = _fc_view['zoom']
        return ex / z + _fc_view['sx'], ey / z + _fc_view['sy']

    def _fc_update_scrollregion():
        """Update Flow canvas scrollregion and scrollbar thumb positions.
        Bundle 21: scrollbar .set() added so thumbs reflect current view."""
        syms = fc_state.get('flow_symbols', {})
        cw   = tk_canvas.winfo_width()  or 860
        ch   = tk_canvas.winfo_height() or 660
        if not syms:
            tk_canvas.config(scrollregion=(0, 0, cw, ch))
            _fc_vsb.set(0.0, 1.0)
            _fc_hsb.set(0.0, 1.0)
            return
        z   = _fc_view['zoom']
        pad = 60
        d_min_x = min(s['x'] - SYMBOL_W // 2 for s in syms.values()) - pad / z
        d_max_x = max(s['x'] + SYMBOL_W // 2 for s in syms.values()) + pad / z
        d_min_y = min(s['y'] - SYMBOL_H // 2 for s in syms.values()) - pad / z
        d_max_y = max(s['y'] + SYMBOL_H // 2 for s in syms.values()) + pad / z
        d_rng_x = max(d_max_x - d_min_x, 1.0)
        d_rng_y = max(d_max_y - d_min_y, 1.0)
        # scrollregion in screen space (d_min * z gives same result as old
        # min(xs) - pad because d_min_x = min_sx - pad/z → d_min_x*z = min_sx*z - pad)
        tk_canvas.config(scrollregion=(d_min_x * z, d_min_y * z,
                                       d_max_x * z, d_max_y * z))
        # Scrollbar thumb: fraction of design-space currently visible
        vis_w = cw / z
        vis_h = ch / z
        f0x = (_fc_view['sx'] - d_min_x) / d_rng_x
        f1x = f0x + vis_w / d_rng_x
        f0y = (_fc_view['sy'] - d_min_y) / d_rng_y
        f1y = f0y + vis_h / d_rng_y
        _fc_hsb.set(max(0.0, f0x), min(1.0, max(f0x + 0.001, f1x)))
        _fc_vsb.set(max(0.0, f0y), min(1.0, max(f0y + 0.001, f1y)))

    # ── Bundle 21: Flow canvas scrollbar command callbacks ────────────────────

    def _fc_vsb_command(*args):
        """Drive _fc_view['sy'] from vertical scrollbar (moveto / scroll)."""
        syms = fc_state.get('flow_symbols', {})
        z    = _fc_view['zoom']
        pad  = 60
        if syms:
            d_min_y = min(s['y'] - SYMBOL_H // 2 for s in syms.values()) - pad / z
            d_max_y = max(s['y'] + SYMBOL_H // 2 for s in syms.values()) + pad / z
        else:
            d_min_y, d_max_y = 0.0, (tk_canvas.winfo_height() or 660) / z
        d_rng_y = max(d_max_y - d_min_y, 1.0)
        if args[0] == 'moveto':
            _fc_view['sy'] = d_min_y + float(args[1]) * d_rng_y
        elif args[0] == 'scroll':
            n = int(args[1])
            _fc_view['sy'] += (n * GRID if args[2] == 'units'
                               else n * (tk_canvas.winfo_height() or 660) / z)
        _fc_update_scrollregion(); redraw()

    def _fc_hsb_command(*args):
        """Drive _fc_view['sx'] from horizontal scrollbar (moveto / scroll)."""
        syms = fc_state.get('flow_symbols', {})
        z    = _fc_view['zoom']
        pad  = 60
        if syms:
            d_min_x = min(s['x'] - SYMBOL_W // 2 for s in syms.values()) - pad / z
            d_max_x = max(s['x'] + SYMBOL_W // 2 for s in syms.values()) + pad / z
        else:
            d_min_x, d_max_x = 0.0, (tk_canvas.winfo_width() or 860) / z
        d_rng_x = max(d_max_x - d_min_x, 1.0)
        if args[0] == 'moveto':
            _fc_view['sx'] = d_min_x + float(args[1]) * d_rng_x
        elif args[0] == 'scroll':
            n = int(args[1])
            _fc_view['sx'] += (n * GRID if args[2] == 'units'
                               else n * (tk_canvas.winfo_width() or 860) / z)
        _fc_update_scrollregion(); redraw()

    def _fc_on_scroll_v(event):
        """Touchpad / mouse-wheel vertical scroll (Button-4 up, Button-5 down)."""
        _fc_view['sy'] += -3 * GRID if event.num == 4 else 3 * GRID
        _fc_update_scrollregion(); redraw()

    def _fc_on_scroll_h(event):
        """Touchpad / mouse-wheel horizontal scroll (Shift-Button-4/5)."""
        _fc_view['sx'] += -3 * GRID if event.num == 4 else 3 * GRID
        _fc_update_scrollregion(); redraw()

    # Load PIL icons (or None if unavailable)
    icons = _make_icons()

    # ── Palette ───────────────────────────────────────────────────────────────
    pal_btns = {}

    def set_mode(mode):
        state['mode']=mode
        state['edge_src']=None
        state['edge_waypoints']=[]
        state['ghost']=None
        for m,b in pal_btns.items():
            b.config(bg=C['pal_active'] if m==mode else C['pal_btn'],
                     relief='sunken' if m==mode else 'flat')
        hints={
            'select':         'Click to select · Drag to move · Dbl-click to rename',
            'place_terminator':'Click canvas to place Terminator [UDP word]',
            'place_process':  'Click canvas to place Process  [UDP word]',
            'place_decision': 'Click canvas to place Decision [UDP word]',
            'place_io':       'Click canvas to place I/O      [UDP word]',
            'edge_src':       'Click SOURCE symbol, then waypoints, then TARGET',
            'delete':         'Click a symbol or edge to delete',
        }
        set_status(hints.get(mode,''))
        redraw()

    def _pal_section(title, parent=None):
        p = parent if parent is not None else _pal_tools_frame
        tk.Label(p, text=title, bg=C['palette'], fg=C['dim'],
                 font=('Monospace',8), pady=3).pack(fill='x', padx=4)

    def _pal_btn(mode, label, sub, icon_key=None, fg=None, parent=None):
        p = parent if parent is not None else _pal_tools_frame
        frm = tk.Frame(p, bg=C['pal_btn'], cursor='hand2',
                       relief='flat', bd=1)
        frm.pack(fill='x', padx=6, pady=2, ipady=3)

        # Icon: PIL image or fallback mini canvas
        if icons and icon_key and icons.get(icon_key):
            ico_lbl = tk.Label(frm,image=icons[icon_key],bg=C['pal_btn'])
            ico_lbl.pack(side='left',padx=3)
        else:
            # Fallback: small canvas-drawn icon
            mini = tk.Canvas(frm,width=36,height=30,
                             bg=C['pal_btn'],highlightthickness=0)
            mini.pack(side='left',padx=3)
            _draw_mini_icon(mini,mode)

        txt = tk.Frame(frm,bg=C['pal_btn']); txt.pack(side='left',fill='x',expand=True)
        tk.Label(txt,text=label,bg=C['pal_btn'],fg=fg or C['text'],
                 font=('Monospace',9,'bold'),anchor='w').pack(fill='x')
        tk.Label(txt,text=sub,bg=C['pal_btn'],fg=C['dim'],
                 font=('Monospace',7),anchor='w').pack(fill='x')

        def onclick(e,m=mode): set_mode(m)
        all_w = [frm,txt]+list(frm.winfo_children())+list(txt.winfo_children())
        for w in all_w:
            try: w.bind('<Button-1>',onclick)
            except: pass

        pal_btns[mode]=frm

    def _draw_mini_icon(c,mode):
        """Fallback canvas-drawn icons when PIL unavailable."""
        W,H=36,30
        if mode=='place_process':
            c.create_rectangle(2,5,W-2,H-5,fill=C['process'],outline=C['border'],width=1)
        elif mode=='place_decision':
            c.create_polygon([W//2,3,W-2,H//2,W//2,H-3,2,H//2],
                             fill=C['decision'],outline=C['border'],width=1)
        elif mode=='place_terminator':
            c.create_oval(2,5,W-2,H-5,fill=C['terminator'],outline=C['border'],width=1)
        elif mode=='place_io':
            c.create_oval(2,5,16,H-5,fill=C['io'],outline=C['border'],width=1)
            c.create_oval(W-16,5,W-2,H-5,fill=C['io'],outline=C['border'],width=1)
            c.create_rectangle(9,5,W-9,H-5,fill=C['io'],outline=C['io'])
            c.create_line(9,5,W-9,5,fill=C['border'],width=1)
            c.create_line(9,H-5,W-9,H-5,fill=C['border'],width=1)
        elif mode=='edge_src':
            c.create_line(4,H//2,W-8,H//2,fill=C['edge'],width=2,
                          arrow='last',arrowshape=(8,10,4))
        elif mode=='select':
            pts=[6,2,6,22,10,18,14,26,17,25,13,17,19,17]
            c.create_polygon(pts,fill=C['text'],outline=C['border'],width=1)
        elif mode=='delete':
            c.create_line(6,5,W-6,H-5,fill='#ff5050',width=3)
            c.create_line(W-6,5,6,H-5,fill='#ff5050',width=3)

    # ── Build palette — static header ─────────────────────────────────────────
    tk.Label(palette_frame, text="FlowCode", bg=C['palette'], fg=C['pal_border'],
             font=('Monospace',11,'bold'), pady=6).pack(fill='x')
    tk.Frame(palette_frame, bg=C['dim'], height=1).pack(fill='x', padx=6)

    # Actions section frame — packed BEFORE tools frame so it claims the bottom
    _pal_actions_frame = tk.Frame(palette_frame, bg=C['palette'])
    _pal_actions_frame.pack(side='bottom', fill='x')

    # Tools frame fills the middle (dynamic, rebuilt per tab)
    _pal_tools_frame.pack(fill='both', expand=True)

    def _build_flow_tools():
        """Rebuild tools frame for the Flow tab."""
        for w in _pal_tools_frame.winfo_children(): w.destroy()
        pal_btns.clear()
        _pal_section("TOOLS")
        _pal_btn('select','Select','move·edit','select')
        _pal_btn('delete','Delete','click to del','delete',fg='#ff6b6b')
        _pal_section("SYMBOLS → UDP")
        _pal_btn('place_terminator','Terminator','oval · start/end','terminator')
        _pal_btn('place_process','Process','rectangle','process')
        _pal_btn('place_decision','Decision','diamond','decision')
        _pal_btn('place_io','I/O','parallelogram','io')
        _pal_section("CONNECT → EXEC")
        _pal_btn('edge_src','Edge','src→[wp]→dst','edge')

    _build_flow_tools()   # Flow tab is shown first

    # Actions section header (inside _pal_actions_frame)
    tk.Frame(_pal_actions_frame, bg=C['dim'], height=1).pack(fill='x', padx=6, pady=4)
    _pal_section("ACTIONS", parent=_pal_actions_frame)

    def _action_btn(label, cmd, fg=None, icon_key=None):
        btn = tk.Button(_pal_actions_frame, text=label, command=cmd,
                        bg=C['pal_btn'], fg=fg or C['text'],
                        font=('Monospace',9), relief='flat',
                        activebackground=C['pal_active'],
                        activeforeground=C['text'],
                        cursor='hand2', padx=4, pady=4)
        btn.pack(fill='x', padx=6, pady=2)
        return btn

    def do_run():
        """▶ Step — run the flow via the Python interpreter; output goes to the panel."""
        def _rout(text, tag=None):
            _run_txt.config(state='normal')
            if tag: _run_txt.insert('end', text, tag)
            else:   _run_txt.insert('end', text)
            _run_txt.see('end')
            _run_txt.config(state='disabled')

        _run_txt.config(state='normal'); _run_txt.delete('1.0', 'end')
        _run_txt.config(state='disabled')

        _fc_sync_canvas_model()
        if not _TernOOInterpreter:
            _rout('✗ Interpreter not found — place ternoo_interpreter.py in 5500fp/\n', 'header_err')
            return
        if not canvas_model.symbols:
            _rout('✗ Flow canvas is empty — add flow symbols on the Flow tab first\n', 'header_err')
            return

        data = {
            'symbols': [s.to_dict() for s in canvas_model.symbols.values()],
            'edges':   [e.to_dict() for e in canvas_model.edges],
        }

        _rout(f'▶ Step-running flow  ({len(canvas_model.symbols)} symbols)…\n', 'header_run')
        root.update_idletasks()

        interp = _TernOOInterpreter(trace=True)

        def on_step(node_id):
            state['selected_sym']       = node_id
            state['selected_edge']      = None
            fc_state['flow_selected']   = node_id
            s = canvas_model.symbols.get(node_id)
            if s:
                _rout(f'  ► {s.label}  [{s.kind}]\n')
                set_inspect(f"► {s.label}  [{s.kind}]")
            redraw(); root.update()

        _orig_execute = interp._execute_node
        def _patched_execute(node, end_ids, depth):
            on_step(node.id)
            return _orig_execute(node, end_ids, depth)
        interp._execute_node = _patched_execute

        interp.load_dict(data)
        try:
            result = interp.run()
            steps  = result['steps']
            _rout(f'✓ Done — {steps} step(s)\n', 'header_ok')
            set_status(f'Step-run complete — {steps} steps')
        except Exception as ex:
            _rout(f'✗ Error: {ex}\n', 'header_err')
            set_status(f'Step-run error: {ex}')

    def do_dump():
        _fc_sync_canvas_model()  # Phase 6C: sync before execution
        canvas_model.print_word_dump()
        set_status(f"Word dump → terminal ({len(canvas_model.to_word_program())} words)")

    def do_load():
        _fc_sync_canvas_model()  # Phase 6C: sync before execution
        end = canvas_model.load_into_emulator(cpu, 100)
        n = end - 100
        set_status(f"Loaded {n} words → emulator  (addr 100–{end-1})")
        print(f"[FlowCode] Loaded {n} TernOO words into emulator at addr 100–{end-1}")

    def do_save():
        """Phase 7c-0 Smart Save: write to current path if known; otherwise
        delegate to guic_do_save() (Save As dialog).  Prompts for .ternoo →
        .fc migration when the current file uses the legacy extension."""
        path = _current_design_path[0]
        if not path:
            guic_do_save(); return
        ext = os.path.splitext(path)[1].lower()
        if ext == '.ternoo':
            ans = messagebox.askyesnocancel(
                "Legacy .ternoo file",
                "This file uses the legacy .ternoo extension.\n"
                "Save as .fc (the new FlowCode default)?",
                icon='info')
            if ans is None: return
            if ans:
                path = os.path.splitext(path)[0] + '.fc'
        _save_to_path(path)

    def do_open():
        guic_do_open()  # Phase 6C: unified .tgui open

    def _clear_flow():
        """Bundle 22: Clear flow canvas state without prompting."""
        fc_state['flow_symbols'].clear()
        fc_state['flow_edges'].clear()
        state['selected_sym']       = None
        state['selected_edge']      = None
        fc_state['flow_selected']   = None
        fc_state['flow_multi_sel'].clear()
        fc_state['flow_next_id']    = 0
        set_inspect('Canvas cleared')
        set_status('Flow canvas cleared')
        redraw()

    def _clear_gui():
        """Bundle 22: Clear GUI canvas state without prompting."""
        fc_state['widgets'].clear()
        fc_state['edges'].clear()
        fc_state['child_order'].clear()
        fc_state['prop_committed'].clear()
        fc_state['selected']  = None
        fc_state['multi_sel'] = set()
        fc_state['next_id']   = 0
        guic_set_mode('select')
        guic_set_status('GUI canvas cleared')
        guic_redraw()

    def _clear_shell():
        """Clear the Connectors canvas (cmd_* widgets) without prompting."""
        fc_state['cmd_widgets'].clear()
        fc_state['cmd_edges'].clear()
        fc_state['cmd_pipe_src']  = None
        fc_state['cmd_selected']  = None
        fc_state['cmd_multi_sel'] = set()
        fc_state['cmd_next_id']   = 0
        _sh_set_mode('select')
        _sh_set_status('Connectors canvas cleared')
        _sh_redraw()

    def do_clear():
        # Tab-aware clear (Stage 8-1 order: Flow|GUI|Sheet|Shell|Connectors|Lingo)
        idx      = notebook.index('current')
        has_flow = bool(fc_state.get('flow_symbols'))
        has_gui  = bool(fc_state.get('widgets'))

        if idx == 5:       # Lingo (vocabulary explorer) — read-only
            return

        if idx == 2:       # Sheet tab — clears cells only
            if not fc_state.get('cells'):
                _sheet_set_status('Sheet already empty'); return
            if not messagebox.askyesno('Clear Sheet',
                    'Clear all cells? Unsaved changes will be lost.'):
                return
            _clear_sheet()
            return

        if idx == 4:       # Connectors tab — clears cmd_* canvas widgets only
            if not fc_state.get('cmd_widgets'):
                _sh_set_status('Connectors canvas already empty'); return
            if not messagebox.askyesno('Clear Connectors canvas',
                    'Clear all command widgets? Unsaved changes will be lost.'):
                return
            _clear_shell()
            return

        if idx == 3:       # Shell tab — clears the staged pipeline
            if not _lingo.get('pipeline'):
                set_status('Pipeline already empty'); return
            if not messagebox.askyesno('Clear pipeline',
                    'Clear all staged pipeline steps?'):
                return
            _lingo_clear_pipeline()
            set_status('Pipeline cleared')
            return

        if idx == 0:       # Flow tab
            if not has_flow:
                set_status('Flow canvas already empty'); return
            if has_gui:
                ans = messagebox.askyesnocancel(
                    'Clear flow canvas?',
                    'Clear all flowchart symbols?\n\n'
                    'Yes    → Clear flow symbols only (GUI widgets preserved)\n'
                    'No     → Clear everything (flow + GUI)\n'
                    'Cancel → Abort')
                if ans is None:   return
                elif ans:         _clear_flow()
                else:             _clear_flow(); _clear_gui()
            else:
                if not messagebox.askyesno('Clear canvas',
                        'Clear the canvas? Unsaved changes will be lost.'):
                    return
                _clear_flow()

        elif idx == 1:     # GUI tab
            if not has_gui:
                guic_set_status('GUI canvas already empty'); return
            if has_flow:
                ans = messagebox.askyesnocancel(
                    'Clear GUI canvas?',
                    'Clear all GUI widgets?\n\n'
                    'Yes    → Clear GUI widgets only (flow symbols preserved)\n'
                    'No     → Clear everything (GUI + flow)\n'
                    'Cancel → Abort')
                if ans is None:   return
                elif ans:         _clear_gui()
                else:             _clear_flow(); _clear_gui()
            else:
                if not messagebox.askyesno('Clear canvas',
                        'Clear the canvas? Unsaved changes will be lost.'):
                    return
                _clear_gui()

    def do_learn():
        """Train the FlowCodeBrain on the current canvas."""
        _fc_sync_canvas_model()  # Phase 6C: sync before execution
        if not _FlowCodeBrain or not _brain_instance:
            set_status("Brain not available — check ternoo_neural.py in 5500fp/")
            return
        if not canvas_model.symbols:
            set_status("Canvas is empty — nothing to learn from")
            return
        data = {
            'symbols': [s.to_dict() for s in canvas_model.symbols.values()],
            'edges':   [e.to_dict() for e in canvas_model.edges],
        }
        transitions = _brain_instance.train_on_canvas(data)
        import json as _json
        bf = _find_brain_file() or os.path.expanduser(
            '~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/flowcode_brain.json')
        with open(bf, 'w') as _f:
            _json.dump(_brain_instance.to_json(), _f, indent=2)
        set_status(f"Brain learned {len(transitions)} transitions — saved")
        print(f"[FlowCode] Brain trained: {len(transitions)} transitions from canvas")
        _brain_instance.show_weights()

    def do_suggest():
        """Ask the brain what symbol should come next."""
        _fc_sync_canvas_model()  # Phase 6C: sync before execution
        if not _brain_instance:
            set_status("Brain not available")
            return
        sym = canvas_model.symbols.get(state.get('selected_sym'))
        if not sym and canvas_model.symbols:
            sym = list(canvas_model.symbols.values())[-1]
        if not sym:
            set_status("Place a symbol first")
            return
        from ternoo_neural import flowcode_symbol_type as _fst, FLOWCODE_VOCAB_INV as _inv
        try:
            tok = _fst(sym.to_dict())
        except Exception:
            tok = sym.kind
        nxt, conf = _brain_instance.predict_next(tok)
        set_status(f"Brain suggests: after {tok} → {nxt.upper() if nxt else '(none)'} ({conf})")
        print(f"[FlowCode] Brain suggestion: {tok} → {nxt} ({conf})")

    _action_btn("⬇ Word Dump", do_dump,   icon_key='dump')
    _action_btn("▶ Load→EMU",  do_load,   fg='#7aff7a', icon_key='load')
    _action_btn("▶ Step",      do_run,    fg='#ffdd57')

    # ── Phase 7b-1: Compile + Run via C emulator (SDL window) ────────────────

    _btn_emulate = [None]    # ▶▶ Emulate button ref
    _btn_stop    = [None]    # ⬛ Stop button ref
    _running_proc = [None]  # currently-running SDL subprocess

    def do_compile_run():
        import subprocess, threading, queue as _queue, time as _time, traceback as _tb

        def _append(text, tag=None):
            _run_txt.config(state='normal')
            if tag:
                _run_txt.insert('end', text, tag)
            else:
                _run_txt.insert('end', text)
            _run_txt.see('end')
            _run_txt.config(state='disabled')

        # Clear previous output
        _run_txt.config(state='normal')
        _run_txt.delete('1.0', 'end')
        _run_txt.config(state='disabled')

        if _btn_emulate[0]: _btn_emulate[0].config(state='disabled')
        root.update_idletasks()

        try:
            if not _compile_to_t5asm:
                _append('✗ compile_to_t5asm.py not found in 5500fp/\n', 'header_err')
                return
            if not os.path.isfile(_engine_path) or not os.access(_engine_path, os.X_OK):
                _append(
                    f'✗ Engine not found: {os.path.relpath(_engine_path)}\n'
                    f'  Run `make` in NASM-TernOO-5500FP-Emulator/c_emulator/ first.\n',
                    'header_err')
                return

            _append('▶ Compiling…\n', 'header_run')
            root.update_idletasks()

            src_path = _current_design_path[0] or '<in-memory>'
            stream   = fc_state.get('stream')
            if stream is None:
                _append('✗ No WordStream available\n', 'header_err')
                return
            try:
                t5asm_text = _compile_to_t5asm(stream, source_path=src_path)
            except _CompileError as ce:
                _append(f'✗ CompileError: {ce}\n', 'header_err')
                set_status(f'Compile error: {ce}'); return
            except Exception:
                _append(f'✗ Internal compiler error:\n{_tb.format_exc()}\n', 'header_err')
                return

            pid = os.getpid()
            ts  = _time.strftime('%Y%m%dT%H%M%S')
            tmp_path = f'/tmp/flowcode_{pid}_{ts}.t5asm'
            with open(tmp_path, 'w') as _f:
                _f.write(t5asm_text)

            rel_engine = os.path.relpath(_engine_path)
            _append(f'▶ Launching SDL window…  {rel_engine}\n', 'header_run')
            root.update_idletasks()

            try:
                proc = subprocess.Popen(
                    [_engine_path, '--display', 'sdl', '--run', tmp_path],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, bufsize=1)
            except OSError as oe:
                _append(f'✗ Launch failed: {oe}\n', 'header_err')
                return

            _running_proc[0] = proc
            if _btn_stop[0]: _btn_stop[0].config(state='normal')
            _append('SDL window is now open — close it when finished.\n')
            set_status('SDL window running — close it to finish')
            # Push FlowCode behind so the SDL window is immediately visible
            root.lower()

            # Background threads drain stdout/stderr into a queue
            out_q = _queue.SimpleQueue()
            def _read(pipe, tag):
                try:
                    for line in pipe:
                        out_q.put((tag, line))
                finally:
                    out_q.put((tag, None))
            threading.Thread(target=_read, args=(proc.stdout, None),        daemon=True).start()
            threading.Thread(target=_read, args=(proc.stderr, 'stderr_out'), daemon=True).start()

            def _poll():
                # Drain any queued output lines
                while True:
                    try:
                        tag, line = out_q.get_nowait()
                        if line is not None:
                            _append(line, tag)
                    except Exception:
                        break
                # Check if process has exited
                # Bundle 22: defensive try/except — a silent exception in _poll
                # would prevent rescheduling and leave Run button stuck disabled.
                try:
                    rc = proc.poll()
                except Exception:
                    rc = None
                if rc is not None:
                    _running_proc[0] = None
                    try:
                        if _btn_stop[0]:    _btn_stop[0].config(state='disabled')
                        if _btn_emulate[0]: _btn_emulate[0].config(state='normal')
                        root.lift()   # bring FlowCode back to front when SDL exits
                    except Exception:
                        pass
                    if rc == 0:
                        _append('✓ SDL window closed (Exit 0)\n', 'header_ok')
                        set_status('Run complete — Exit 0')
                    else:
                        _append(f'✗ SDL exited with code {rc}\n', 'header_err')
                        set_status(f'Run failed — Exit {rc}')
                else:
                    root.after(100, _poll)   # poll again in 100 ms

            root.after(100, _poll)
            return   # button stays disabled until _poll sees process exit

        except Exception:
            _append(f'✗ Unexpected error:\n{_tb.format_exc()}\n', 'header_err')
        finally:
            # Only re-enable here if we did NOT successfully launch a Popen
            if _running_proc[0] is None and _btn_emulate[0]:
                _btn_emulate[0].config(state='normal')

    def do_stop():
        proc = _running_proc[0]
        if proc and proc.poll() is None:
            proc.terminate()
            set_status('SDL process stopped')

    _btn_emulate[0] = _action_btn("▶▶ Run",     do_compile_run, fg='#7aff7a')
    _btn_stop[0]    = _action_btn("⬛ Stop",      do_stop,        fg='#ff8888')
    _btn_stop[0].config(state='disabled')

    _action_btn("💾 Save",     do_save,           icon_key='save')
    _action_btn("📂 Open",     do_open,           icon_key='open')
    _action_btn("📥 Import",   lambda: guic_do_import())  # Phase 7c-0: merge into current
    _action_btn("🗑 Clear",    do_clear,  fg='#ff8888', icon_key='clear')
    _action_btn("🧠 Learn",   do_learn,  fg='#7affcc')
    _action_btn("💡 Suggest", do_suggest, fg='#ffcc44')

    # Undo / Redo — refs used by guic_update_undo_btns to enable/disable
    _pal_undo_btn_ref = [None]
    _pal_redo_btn_ref = [None]
    _pal_undo_btn_ref[0] = _action_btn("↩ Undo", lambda: guic_undo(), C['dim'])
    _pal_redo_btn_ref[0] = _action_btn("↪ Redo", lambda: guic_redo(), C['dim'])

    tk.Label(_pal_actions_frame, text=f"v0.6.0\n{os.path.basename(_emu_path)}",
             bg=C['palette'], fg=C['dim'], font=('Monospace',7), pady=4
             ).pack(side='bottom', fill='x')

    # ── Phase 6C: FlowCode dict helpers ──────────────────────────────────────

    def _fc_sym_at(x, y):
        """Hit test: return flow symbol dict at (x,y) or None — current scope only."""
        hw, hh = SYMBOL_W // 2, SYMBOL_H // 2
        scope = fc_state.get('flow_scope')
        for s in reversed(list(fc_state['flow_symbols'].values())):
            if s.get('parent_scope') != scope:
                continue   # Phase 7c-4: only symbols in the current pocket scope
            if abs(s['x'] - x) <= hw and abs(s['y'] - y) <= hh:
                return s
        return None

    # ── Phase 7c-4: pocket scope helpers ──────────────────────────────────────
    _FC_CONTAINER_KINDS = {'flow_process', 'flow_subroutine'}

    def _fc_children_of(scope_name):
        """All flow symbols whose parent_scope == scope_name."""
        return [s for s in fc_state['flow_symbols'].values()
                if s.get('parent_scope') == scope_name]

    def _fc_pocket_contents(sym):
        """(name, kind) for each child of `sym` (by its name)."""
        return [(c.get('name', ''), c.get('kind', ''))
                for c in _fc_children_of(sym.get('name'))]

    def _fc_has_pocket(sym):
        """True if `sym` has any children (renders the 📦 affordance)."""
        nm = sym.get('name')
        return bool(nm) and any(s.get('parent_scope') == nm
                                for s in fc_state['flow_symbols'].values())

    def _fc_port_positions(sym):
        """Phase 7c-4b: design-space positions of a container's ports.
        Returns {'entry': [(port, x, y)], 'exit': [(port, x, y)]}. Entry ports
        sit on the left edge, exit ports on the right, distributed vertically."""
        out = {'entry': [], 'exit': []}
        if _flowcode_ports is None or sym.get('kind') not in _FC_CONTAINER_KINDS:
            return out
        hw, hh = SYMBOL_W // 2, SYMBOL_H // 2
        top, bot = sym['y'] - hh, sym['y'] + hh
        for edge, key, ex in (('entry', 'entry_points', sym['x'] - hw),
                              ('exit', 'exit_points', sym['x'] + hw)):
            ports = sym.get(key) or []
            n = len(ports)
            for i, p in enumerate(ports):
                py = top + (bot - top) * (i + 1) / (n + 1)
                out[edge].append((p, ex, py))
        return out

    def _fc_port_at(x, y, tol=8):
        """Return (sym, 'entry'|'exit', port) whose dot is near design (x,y)."""
        scope = fc_state.get('flow_scope')
        for s in reversed(list(fc_state['flow_symbols'].values())):
            if s.get('parent_scope') != scope:
                continue
            pp = _fc_port_positions(s)
            for edge in ('entry', 'exit'):
                for port, px, py in pp[edge]:
                    if abs(px - x) <= tol and abs(py - y) <= tol:
                        return s, edge, port
        return None

    def _fc_sym_by_name(name):
        for s in fc_state['flow_symbols'].values():
            if s.get('name') == name:
                return s
        return None

    def _fc_scope_path():
        """Breadcrumb segments from top-level to current scope: list of names
        ([] at top level)."""
        path = []
        cur = fc_state.get('flow_scope')
        seen = set()
        while cur and cur not in seen:
            seen.add(cur)
            path.append(cur)
            sym = _fc_sym_by_name(cur)
            cur = sym.get('parent_scope') if sym else None
        return list(reversed(path))

    def _fc_set_scope(scope_name):
        """Drill into / out to a pocket scope and refresh breadcrumb + canvas."""
        fc_state['flow_scope'] = scope_name
        state['selected_sym'] = None
        fc_state['flow_selected'] = None
        _fc_build_breadcrumb()
        redraw()

    def _fc_build_breadcrumb():
        """Render the pocket scope path: MainFlow > Process > Validate."""
        for w in _fc_breadcrumb.winfo_children():
            w.destroy()
        segments = [('MainFlow', None)] + [(nm, nm) for nm in _fc_scope_path()]
        for i, (label, scope) in enumerate(segments):
            if i:
                tk.Label(_fc_breadcrumb, text='›', bg=C['palette'], fg=C['dim'],
                         font=('Monospace', 9)).pack(side='left')
            is_last = (i == len(segments) - 1)
            lbl = tk.Label(_fc_breadcrumb, text=f' {label} ', bg=C['palette'],
                           fg=C['pal_border'] if is_last else C['text'],
                           font=('Monospace', 9, 'bold' if is_last else 'normal'),
                           cursor='hand2', padx=2, pady=2)
            lbl.pack(side='left')
            if not is_last:
                lbl.bind('<Button-1>', lambda e, s=scope: _fc_set_scope(s))

    def _fc_edge_points(e):
        """Point list for edge dict, trimmed to dst boundary."""
        src = fc_state['flow_symbols'].get(e['src'])
        dst = fc_state['flow_symbols'].get(e['dst'])
        if not src or not dst: return []
        hw, hh = SYMBOL_W // 2, SYMBOL_H // 2
        pts_before = [(src['x'], src['y'])] + [tuple(wp) for wp in e.get('waypoints', [])]
        cx, cy = dst['x'], dst['y']
        px, py = pts_before[-1]
        dx, dy = cx - px, cy - py
        dist = (dx*dx + dy*dy) ** 0.5
        if dist > 0:
            import math as _m
            adx, ady = abs(dx)/dist, abs(dy)/dist
            draw_kind = _FC_KIND_DRAW.get(dst.get('kind', ''), SYMBOL_PROCESS)
            if draw_kind == SYMBOL_DECISION:
                margin = hw*adx + hh*ady
            elif draw_kind in (SYMBOL_IO, SYMBOL_TERMINATOR):
                a = _m.atan2(dy, dx)
                margin = (hw*hh)/max(1, _m.sqrt((hh*_m.cos(a))**2 + (hw*_m.sin(a))**2))
            else:
                margin = min(hw/max(adx, 0.001), hh/max(ady, 0.001))
                margin = min(margin, hw)
            ex = cx - dx/dist*(margin + 3)
            ey = cy - dy/dist*(margin + 3)
        else:
            ex, ey = cx, cy
        return pts_before + [(int(ex), int(ey))]

    def _fc_ortho_points(e):
        """Orthogonal (right-angle) routing through waypoints for edge dict."""
        raw = _fc_edge_points(e)
        if len(raw) < 2: return raw
        result = [raw[0]]
        for i in range(1, len(raw)):
            px, py = result[-1]
            nx, ny = raw[i]
            if px != nx and py != ny:
                result.append((nx, py))  # elbow
            result.append((nx, ny))
        return result

    def _fc_edge_near(x, y, tol=12):
        """Hit test: return flow edge dict near (x,y) or None."""
        for e in fc_state['flow_edges']:
            pts = _fc_ortho_points(e)
            for i in range(len(pts) - 1):
                x1, y1 = pts[i]; x2, y2 = pts[i + 1]
                dx, dy = x2 - x1, y2 - y1
                if dx == 0 and dy == 0: continue
                t = max(0, min(1, ((x-x1)*dx + (y-y1)*dy) / (dx*dx + dy*dy)))
                px2, py2 = x1 + t*dx, y1 + t*dy
                if (px2 - x)**2 + (py2 - y)**2 <= tol**2:
                    return e
        return None

    def _fc_make_default_name(kind, wid):
        """Phase 7c-1: default programmatic name <kind>_<id>, bumped with a
        numeric suffix if that exact name is already taken in the stream."""
        base = f"{kind}_{wid}"
        stream = fc_state.get('stream')
        if stream is None:
            return base
        nm, n = base, 1
        while stream.name_in_use(nm):
            nm = f"{base}_{n}"; n += 1
        return nm

    def _fc_add_symbol(kind, x, y, label=''):
        """Add flow symbol dict to fc_state, push undo. Returns sym dict.
        Phase 7c-4: the new symbol belongs to the current pocket scope."""
        sid = fc_state['flow_next_id']
        fc_state['flow_next_id'] += 1
        lbl = label or f"{kind.split('_', 1)[-1][0].upper()}{sid}"
        sym = {'id': sid, 'kind': kind,
               'x': snap(x), 'y': snap(y),
               'w': SYMBOL_W, 'h': SYMBOL_H,
               'label': lbl, 'name': _fc_make_default_name(kind, sid),
               'parent_scope': fc_state.get('flow_scope'),  # Phase 7c-4
               'properties': []}
        # Phase 7c-4: container kinds carry (stubbed) named entry/exit points for
        # the future cross-scope-connection mechanism (built in a later bundle).
        if kind in _FC_CONTAINER_KINDS:
            sym['entry_points'] = []
            sym['exit_points'] = []
        fc_state['flow_symbols'][sid] = sym
        _guic_push_undo({'kind': 'flow_remove', 'sym': dict(sym)})  # undo = remove
        return sym

    def _fc_remove_symbol(sid):
        """Remove flow symbol + cascade edges from fc_state, push undo."""
        sym = fc_state['flow_symbols'].pop(sid, None)
        if sym is None: return
        fc_state['flow_edges'] = [e for e in fc_state['flow_edges']
                             if e['src'] != sid and e['dst'] != sid]
        if fc_state['flow_selected'] == sid:
            fc_state['flow_selected'] = None
        fc_state['flow_multi_sel'].discard(sid)
        _guic_push_undo({'kind': 'flow_add', 'sym': dict(sym)})  # undo = re-add

    def _fc_add_edge(src_id, dst_id, waypoints=(), condition='', bound_port_name=''):
        """Add flow edge dict to fc_state, push undo. Returns edge dict or None.

        Phase 7c-4b: an edge may bind to one of dst's (a container's) entry/exit
        ports by name (bound_port_name). Same-scope edges stay scope-local; the
        port binding is what crosses into the container's pocket interior."""
        src = fc_state['flow_symbols'].get(src_id)
        dst = fc_state['flow_symbols'].get(dst_id)
        if src is None or dst is None: return None
        # Phase 7c-4 (L3): flow edges are strictly scope-local unless the edge
        # binds to a named port on the destination container (Phase 7c-4b).
        if not bound_port_name and src.get('parent_scope') != dst.get('parent_scope'):
            set_status("Can't connect across pocket scopes — bind to a named port")
            return None
        for e in fc_state['flow_edges']:
            if e['src'] == src_id and e['dst'] == dst_id: return None
        edge = {'src': src_id, 'dst': dst_id,
                'waypoints': list(waypoints), 'condition': condition}
        if bound_port_name:
            edge['bound_port_name'] = bound_port_name
        fc_state['flow_edges'].append(edge)
        _guic_push_undo({'kind': 'flow_edge_remove', 'edge': dict(edge)})  # undo = remove
        return edge

    def _fc_remove_edge(src_id, dst_id):
        """Remove flow edge from fc_state, push undo."""
        removed = None
        for e in fc_state['flow_edges']:
            if e['src'] == src_id and e['dst'] == dst_id:
                removed = e; break
        if removed is None: return
        fc_state['flow_edges'] = [e for e in fc_state['flow_edges']
                             if not (e['src'] == src_id and e['dst'] == dst_id)]
        _guic_push_undo({'kind': 'flow_edge_add', 'edge': dict(removed)})  # undo = re-add

    def _fc_sync_canvas_model():
        """Rebuild canvas_model (FCCanvas) from fc_state['flow_*'] for execution functions."""
        canvas_model.symbols.clear()
        canvas_model.edges.clear()
        FCSymbol._next_id = 1
        _fc_kind_map = {
            'flow_terminator': SYMBOL_TERMINATOR,
            'flow_process':    SYMBOL_PROCESS,
            'flow_decision':   SYMBOL_DECISION,
            'flow_io':         SYMBOL_IO,
            'flow_subroutine': SYMBOL_PROCESS,
            'flow_connector':  SYMBOL_IO,
        }
        for sid, sym in sorted(fc_state['flow_symbols'].items()):
            fc_kind = _fc_kind_map.get(sym.get('kind', ''), SYMBOL_PROCESS)
            s = FCSymbol(fc_kind, sym['x'], sym['y'], sym.get('label', ''))
            s.id = sid
            canvas_model.symbols[sid] = s
        FCSymbol._next_id = (max(fc_state['flow_symbols'].keys()) + 1
                             if fc_state['flow_symbols'] else 1)
        for e_dict in fc_state['flow_edges']:
            src_id = e_dict['src']; dst_id = e_dict['dst']
            if src_id in canvas_model.symbols and dst_id in canvas_model.symbols:
                wps = [tuple(w) for w in e_dict.get('waypoints', [])]
                canvas_model.add_edge(src_id, dst_id, waypoints=wps,
                                      condition=e_dict.get('condition', ''))

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw_grid():
        cw = tk_canvas.winfo_width() or 860
        ch = tk_canvas.winfo_height() or 660
        z  = _fc_view['zoom']
        gstep = GRID * z
        if gstep < 4: return   # skip grid when too zoomed out
        ox = (-_fc_view['sx'] * z) % gstep
        oy = (-_fc_view['sy'] * z) % gstep
        x = ox
        while x <= cw:
            tk_canvas.create_line(int(x), 0, int(x), ch, fill=C['grid'])
            x += gstep
        y = oy
        while y <= ch:
            tk_canvas.create_line(0, int(y), cw, int(y), fill=C['grid'])
            y += gstep

    def draw_symbol(s):
        # Phase 6C: s is a flow symbol dict {id, kind, x, y, w, h, label, properties}
        sid = s['id']
        sel = (sid == fc_state['flow_selected'] or sid in fc_state['flow_multi_sel'])
        draw_kind = _FC_KIND_DRAW.get(s['kind'], SYMBOL_PROCESS)
        fill = C['selected'] if sel else {
            SYMBOL_PROCESS:   C['process'],
            SYMBOL_DECISION:  C['decision'],
            SYMBOL_IO:        C['io'],
            SYMBOL_TERMINATOR:C['terminator'],
        }.get(draw_kind, C['process'])
        bor = C['selected'] if sel else C['border']
        lw  = 3 if sel else 2
        # ── Bundle 18: viewport transform (design → screen) ───────────────────
        _sx2, _sy2 = _fc_d2s(s['x'], s['y'])
        x, y = int(_sx2), int(_sy2)
        z    = _fc_view['zoom']
        hw   = int(SYMBOL_W // 2 * z)
        hh   = int(SYMBOL_H // 2 * z)
        _ofs = max(3, int(10 * z))   # label vertical clearance
        _sub = max(1, int(4  * z))   # subroutine inset
        _cp  = max(2, int(4  * z))   # connection-point half-size
        _fl  = max(6, int(10 * z))   # main label font size
        _fs  = max(5, int(7  * z))   # sub label font size
        # ─────────────────────────────────────────────────────────────────────

        if draw_kind == SYMBOL_PROCESS:
            tk_canvas.create_rectangle(x-hw, y-hh, x+hw, y+hh,
                                       fill=fill, outline=bor, width=lw)
            if s['kind'] == 'flow_subroutine':  # double-border for predefined process
                tk_canvas.create_rectangle(x-hw+_sub, y-hh+_sub, x+hw-_sub, y+hh-_sub,
                                           fill='', outline=bor, width=1)
        elif draw_kind == SYMBOL_DECISION:
            tk_canvas.create_polygon([x, y-hh, x+hw, y, x, y+hh, x-hw, y],
                                     fill=fill, outline=bor, width=lw)
        elif draw_kind == SYMBOL_IO:
            r = max(4, int(12 * z))
            tk_canvas.create_rectangle(x-hw+r, y-hh, x+hw-r, y+hh, fill=fill, outline=fill)
            tk_canvas.create_oval(x-hw, y-hh, x-hw+r*2, y+hh, fill=fill, outline=bor, width=lw)
            tk_canvas.create_oval(x+hw-r*2, y-hh, x+hw, y+hh, fill=fill, outline=bor, width=lw)
            tk_canvas.create_line(x-hw+r, y-hh, x+hw-r, y-hh, fill=bor, width=lw)
            tk_canvas.create_line(x-hw+r, y+hh, x+hw-r, y+hh, fill=bor, width=lw)
        elif draw_kind == SYMBOL_TERMINATOR:
            tk_canvas.create_oval(x-hw, y-hh, x+hw, y+hh,
                                  fill=fill, outline=bor, width=lw)
            # Phase 6D: dot if this is a bound entry handler
            if (_guic_get_prop_value(s, 'is_entry') and
                    (s['x'], s['y']) in fc_state.get('_bound_targets', set())):
                _dr = max(2, int(5 * z)); _d2 = max(1, int(2 * z))
                tk_canvas.create_oval(x+hw-_dr*2-_d2, y-hh+_d2,
                                      x+hw-_d2,       y-hh+_dr*2+_d2,
                                      fill='#00e5ff', outline='', width=0)

        tk_canvas.create_text(x, y, text=s['label'], fill=C['text'],
                              font=('Monospace', _fl, 'bold'))
        tk_canvas.create_text(x, y+hh+_ofs,
                              text=s['kind'].replace('flow_', ''),
                              fill=C['dim'], font=('Monospace', _fs))
        if sel:
            tk_canvas.create_text(x, y-hh-_ofs, text=f"({s['x']},{s['y']})",
                                  fill=C['selected'], font=('Monospace', _fs))

        # Phase 7c-4: 📦 pocket affordance on symbols that have children
        if _fc_has_pocket(s):
            tk_canvas.create_text(x+hw-_cp*2, y-hh+_cp*2, text='\U0001F4E6',
                                  font=('Monospace', max(7, int(11*z))))

        # Phase 7c-4b: entry/exit ports on the container's edges (labelled dots)
        pp = _fc_port_positions(s)
        _pr = max(2, int(3 * z))
        for edge, anchor, dx in (('entry', 'e', _pr + 2), ('exit', 'w', -_pr - 2)):
            for port, px, py in pp[edge]:
                sx, sy = _fc_d2s(px, py); sx, sy = int(sx), int(sy)
                tk_canvas.create_oval(sx-_pr, sy-_pr, sx+_pr, sy+_pr,
                                      fill='#00e5ff' if edge == 'entry' else '#ffb000',
                                      outline=bor, width=1)
                if z >= 0.7:
                    tk_canvas.create_text(sx+dx, sy, anchor=anchor, text=port['name'],
                                          fill=C['dim'], font=('Monospace', _fs))

        # Connection points in edge mode
        if state['mode'] in ('edge_src', 'edge_dst_pending'):
            for cx, cy in [(x, y-hh), (x, y+hh), (x+hw, y), (x-hw, y)]:
                tk_canvas.create_oval(cx-_cp, cy-_cp, cx+_cp, cy+_cp,
                                      fill=C['pal_border'], outline=C['border'])

    def draw_edge(e):
        # Phase 6C: e is a flow edge dict {src, dst, waypoints, condition}
        sel_e  = state['selected_edge']
        is_sel = (sel_e and sel_e.get('src') == e['src']
                  and sel_e.get('dst') == e['dst'])
        col = C['selected'] if is_sel else C['edge']
        lw  = 3 if is_sel else 2

        # ── Bundle 18: transform pts from design → screen ─────────────────────
        pts_d = _fc_ortho_points(e)
        if len(pts_d) < 2: return
        z = _fc_view['zoom']
        pts = [(int(_fc_d2s(px2, py2)[0]), int(_fc_d2s(px2, py2)[1])) for px2, py2 in pts_d]
        _asz = (int(16 * z), int(20 * z), int(6 * z))
        _wp  = max(2, int(5 * z))

        for i in range(len(pts) - 1):
            x1, y1 = pts[i]; x2, y2 = pts[i + 1]
            kw = dict(fill=col, width=lw)
            if i == len(pts) - 2:
                kw.update(arrow='last', arrowshape=_asz)
            tk_canvas.create_line(x1, y1, x2, y2, **kw)

        for wx, wy in e.get('waypoints', []):
            wxs, wys = _fc_d2s(wx, wy)
            tk_canvas.create_oval(wxs-_wp, wys-_wp, wxs+_wp, wys+_wp,
                                  fill=C['waypoint'], outline=C['border'], width=1)

        cond = e.get('condition', '')
        if len(pts) >= 2 and cond:
            mx = (pts[0][0] + pts[1][0]*2) // 3
            my = (pts[0][1] + pts[1][1]*2) // 3 - max(4, int(10 * z))
            tk_canvas.create_text(mx, my, text=f"[{cond}]",
                                  fill=C['waypoint'],
                                  font=('Monospace', max(5, int(8 * z)), 'bold'))

    def draw_edge_in_progress():
        """Draw the edge being constructed with waypoints collected so far."""
        src_id = state.get('edge_src')
        if not src_id: return
        src = fc_state['flow_symbols'].get(src_id)  # Phase 6C: use fc_state dict
        if not src: return
        # All coords in design space; convert to screen for drawing
        pts_d = [(src['x'], src['y'])] + state['edge_waypoints']
        if len(pts_d) < 1: return
        pts = [_fc_d2s(px2, py2) for px2, py2 in pts_d]
        z   = _fc_view['zoom']
        _wp = max(2, int(4 * z))
        # Draw path so far
        for i in range(len(pts)-1):
            x1,y1=pts[i]; x2,y2=pts[i+1]
            tk_canvas.create_line(x1,y1,x2,y2,fill=C['waypoint'],
                                  width=1,dash=(4,3))
        # Waypoint dots
        for wx_d,wy_d in state['edge_waypoints']:
            wxs,wys = _fc_d2s(wx_d,wy_d)
            tk_canvas.create_oval(wxs-_wp,wys-_wp,wxs+_wp,wys+_wp,
                                  fill=C['waypoint'],outline=C['border'])
        # Ghost line to cursor (ghost stored in design space)
        if state['ghost']:
            gx_d,gy_d = state['ghost']
            gxs,gys   = _fc_d2s(gx_d,gy_d)
            lx,ly     = pts[-1]
            # Ortho ghost
            tk_canvas.create_line(lx,ly,gxs,ly,fill=C['waypoint'],
                                  width=1,dash=(2,4))
            tk_canvas.create_line(gxs,ly,gxs,gys,fill=C['waypoint'],
                                  width=1,dash=(2,4))

    def redraw():
        tk_canvas.delete('all')
        draw_grid()
        # Phase 7c-4: only render the current pocket scope's symbols + their edges.
        _scope = fc_state.get('flow_scope')
        _in_scope = {sid for sid, s in fc_state['flow_symbols'].items()
                     if s.get('parent_scope') == _scope}
        for e in fc_state['flow_edges']:            # Phase 6C: draw from fc_state
            if e['src'] in _in_scope and e['dst'] in _in_scope:
                draw_edge(e)
        # Bundle 12: build set of bound target positions for visual annotation
        # Reads from 'signal_ids' (Bundle 12 format; 'bindings' retired)
        _bound_targets: set = set()
        for _bw in fc_state['widgets'].values():
            for _bi in (_bw.get('signal_ids') or {}).values():
                if _bi:
                    _bound_targets.add((_bi.get('dst_x', 0), _bi.get('dst_y', 0)))
        fc_state['_bound_targets'] = _bound_targets
        for s in fc_state['flow_symbols'].values():  # Phase 6C: draw from fc_state
            if s.get('parent_scope') == _scope:      # Phase 7c-4: scope filter
                draw_symbol(s)
        draw_edge_in_progress()
        if (state['ghost'] and
                state['mode'] in ('place_terminator','place_process',
                                  'place_decision','place_io')):
            _draw_placement_ghost(*state['ghost'])

    def _draw_placement_ghost(x,y):
        # x,y are design-space ghost coords (stored by on_motion in design space)
        x,y = snap(x),snap(y)           # snap in design space
        sx,sy = _fc_d2s(x,y)            # convert to screen space
        sx,sy = int(sx),int(sy)
        z  = _fc_view['zoom']
        hw = int(SYMBOL_W//2*z); hh=int(SYMBOL_H//2*z)
        mode=state['mode']
        fill='#161b30'; bor='#3a4060'
        if mode=='place_terminator':
            tk_canvas.create_oval(sx-hw,sy-hh,sx+hw,sy+hh,
                                  fill=fill,outline=bor,width=1,dash=(4,4))
        elif mode=='place_process':
            tk_canvas.create_rectangle(sx-hw,sy-hh,sx+hw,sy+hh,
                                       fill=fill,outline=bor,width=1,dash=(4,4))
        elif mode=='place_decision':
            tk_canvas.create_polygon([sx,sy-hh,sx+hw,sy,sx,sy+hh,sx-hw,sy],
                                     fill=fill,outline=bor,width=1)
        elif mode=='place_io':
            r=max(4,int(12*z))
            tk_canvas.create_rectangle(sx-hw+r,sy-hh,sx+hw-r,sy+hh,fill=fill,outline=fill)
            tk_canvas.create_oval(sx-hw,sy-hh,sx-hw+r*2,sy+hh,
                                  fill=fill,outline=bor,width=1,dash=(4,4))
            tk_canvas.create_oval(sx+hw-r*2,sy-hh,sx+hw,sy+hh,
                                  fill=fill,outline=bor,width=1,dash=(4,4))
        _gt = max(4,int(10*z)); _gf = max(5,int(7*z))
        tk_canvas.create_text(sx,sy+hh+_gt,text=f"snap ({x},{y})",
                              fill='#2a3050',font=('Monospace',_gf))

    def update_inspect():
        # Phase 6C: read from fc_state['flow_*'] dicts
        sid = state['selected_sym']
        se  = state['selected_edge']
        if sid is not None and sid in fc_state['flow_symbols']:   # Bundle 23 P2: id 0 is valid
            s = fc_state['flow_symbols'][sid]
            cond_prop = _guic_get_prop_value(s, 'condition')
            cond_str = f"\n  condition='{cond_prop}'" if cond_prop else ""
            is_entry = _guic_get_prop_value(s, 'is_entry')
            entry_str = "  [entry]" if is_entry else ""
            set_inspect(
                f"Symbol #{s['id']}  {s['kind'].upper()}  '{s['label']}'"
                f"{entry_str}\n"
                f"  Kind: {s['kind']}\n"
                f"  Pos:  ({s['x']}, {s['y']})  Size: {s['w']}×{s['h']}"
                f"{cond_str}")
        elif se:
            src = fc_state['flow_symbols'].get(se.get('src'))
            dst = fc_state['flow_symbols'].get(se.get('dst'))
            sl = src['label'] if src else f"#{se.get('src')}"
            dl = dst['label'] if dst else f"#{se.get('dst')}"
            cond = se.get('condition', '')
            cond_str = f"\n  condition='{cond}'" if cond else ""
            set_inspect(
                f"Edge  {sl} → {dl}"
                f"  ({len(se.get('waypoints', []))} waypoints)"
                f"{cond_str}")
        else:
            set_inspect("Select a symbol or edge to inspect its TernOO word")


    # ── Tooltip ───────────────────────────────────────────────────────────────

    _tooltip_win  = [None]
    _tooltip_after = [None]

    def _show_tooltip(x, y, text):
        _hide_tooltip()
        tw = tk.Toplevel(root)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{root.winfo_rootx()+x+16}+{root.winfo_rooty()+y+10}")
        tk.Label(tw, text=text, bg='#1a1f2e', fg=C['inspect_fg'],
                 font=('Monospace', 8), relief='flat', bd=1,
                 padx=6, pady=3).pack()
        _tooltip_win[0] = tw

    def _hide_tooltip():
        if _tooltip_after[0]:
            try: root.after_cancel(_tooltip_after[0])
            except Exception: pass
            _tooltip_after[0] = None
        if _tooltip_win[0]:
            try: _tooltip_win[0].destroy()
            except Exception: pass
            _tooltip_win[0] = None

    def _schedule_tooltip(event):
        # Phase 6C: use fc_state dicts; Bundle 18: convert event to design space
        _hide_tooltip()
        dx, dy = _fc_s2d(event.x, event.y)
        sym = _fc_sym_at(dx, dy)
        if sym:
            tip = f"{sym['kind'].upper()} #{sym['id']}  '{sym['label']}'"
            ex, ey = event.x, event.y
            _tooltip_after[0] = root.after(700, lambda: _show_tooltip(ex, ey, tip))
        else:
            edg = _fc_edge_near(dx, dy)
            if edg:
                src = fc_state['flow_symbols'].get(edg['src'])
                dst = fc_state['flow_symbols'].get(edg['dst'])
                sl = src['label'] if src else f"#{edg['src']}"
                dl = dst['label'] if dst else f"#{edg['dst']}"
                tip = f"Edge  {sl} → {dl}"
                if edg.get('condition'): tip += f"\ncondition: {edg['condition']}"
                ex, ey = event.x, event.y
                _tooltip_after[0] = root.after(700, lambda: _show_tooltip(ex, ey, tip))

    # ── Event handlers ────────────────────────────────────────────────────────

    def on_motion(event):
        # Bundle 18: store ghost in design space; all drag arithmetic in design space
        ddx, ddy = _fc_s2d(event.x, event.y)
        state['ghost'] = (ddx, ddy)
        # Bundle 19: defensive reset — if Button-1 was released outside the canvas
        # (common with dodgy hardware) state['dragging'] can get stuck True.
        # Check the actual button state and clear it so the next click starts clean.
        if state['dragging'] and not (event.state & 0x0100):
            state['dragging'] = False
        if state['dragging'] and state['selected_sym'] is not None:  # Bundle 23 P2: id 0 valid
            s = fc_state['flow_symbols'].get(state['selected_sym'])  # Phase 6C
            if s:
                offx, offy = state['drag_offset']   # design-space offset
                s['x'] = snap(ddx - offx)
                s['y'] = snap(ddy - offy)
            _hide_tooltip()
        else:
            _schedule_tooltip(event)
        redraw()

    def on_click(event):
        # Phase 6C: all flow operations go through fc_state['flow_*'] + _fc_* helpers
        # Bundle 18: convert click from screen to design space at input layer
        x, y = _fc_s2d(event.x, event.y)
        mode = state['mode']

        # Phase 7c-4: 📦 pocket affordance — click near a symbol's top-right
        # corner (when it has children) drills into its scope.
        if mode == 'select':
            hw, hh = SYMBOL_W // 2, SYMBOL_H // 2
            for s in _fc_children_of(fc_state.get('flow_scope')):
                if not _fc_has_pocket(s):
                    continue
                bx, by = s['x'] + hw, s['y'] - hh   # top-right corner (design)
                if abs(x - bx) <= 14 and abs(y - by) <= 14:
                    _fc_set_scope(s['name'])
                    set_status(f"Opened pocket: {s['name']}")
                    return

        # Placement modes
        if mode in ('place_terminator', 'place_process', 'place_decision', 'place_io'):
            kind = _FC_PLACE_KIND[mode]
            s = _fc_add_symbol(kind, x, y)
            state['selected_sym']  = s['id']
            state['selected_edge'] = None
            state['ghost']         = None
            fc_state['flow_selected']   = s['id']
            set_status(f"Placed {s['label']}")
            update_inspect(); set_mode('select'); return

        # Delete mode
        if mode == 'delete':
            hit_s = _fc_sym_at(x, y)
            hit_e = _fc_edge_near(x, y)
            if hit_s:
                lbl = hit_s['label']
                _fc_remove_symbol(hit_s['id'])
                if state['selected_sym'] == hit_s['id']:
                    state['selected_sym'] = None
                    fc_state['flow_selected']  = None
                set_status(f"Deleted {lbl}")
                set_inspect("Select a symbol or edge to inspect")
            elif hit_e:
                _fc_remove_edge(hit_e['src'], hit_e['dst'])
                state['selected_edge'] = None
                set_status("Edge deleted")
            redraw(); return

        # Edge source selection
        if mode == 'edge_src':
            hit = _fc_sym_at(x, y)
            if hit:
                state['edge_src']       = hit['id']
                state['edge_waypoints'] = []
                state['mode']           = 'edge_dst_pending'
                set_status(f"From {hit['label']} — click canvas for waypoints, "
                           f"click target symbol to finish")
            redraw(); return

        # Edge waypoint / destination
        if state['mode'] == 'edge_dst_pending':
            # Phase 7c-4b: dropping on a container's port dot binds the edge to
            # that port by name (crosses into the pocket); else a normal edge.
            port_hit = _fc_port_at(x, y)
            hit = port_hit[0] if port_hit else _fc_sym_at(x, y)
            bpn = port_hit[2]['name'] if port_hit else ''
            if hit and hit['id'] != state['edge_src']:
                wps = state['edge_waypoints']
                e = _fc_add_edge(state['edge_src'], hit['id'], waypoints=wps,
                                 bound_port_name=bpn)
                if e:
                    src = fc_state['flow_symbols'].get(state['edge_src'])
                    state['selected_edge'] = {'src': e['src'], 'dst': e['dst'],
                                              'waypoints': list(e['waypoints']),
                                              'condition': e['condition']}
                    state['selected_sym'] = None
                    sl = src['label'] if src else f"#{state['edge_src']}"
                    tail = f" → port {bpn}" if bpn else ''
                    set_status(f"Edge {sl}→{hit['label']}{tail} ({len(wps)} waypoints)")
                    update_inspect()
                state['edge_src'] = None; state['edge_waypoints'] = []
                set_mode('select')
            elif hit and hit['id'] == state['edge_src']:
                set_status("Can't connect to self — click canvas or different symbol")
            else:
                wx, wy = snap(x), snap(y)
                state['edge_waypoints'].append((wx, wy))
                set_status(f"Waypoint added ({wx},{wy}) — "
                           f"{len(state['edge_waypoints'])} total. "
                           f"Click target symbol to finish, or add more.")
            redraw(); return

        # Select mode
        hit_s = _fc_sym_at(x, y)
        hit_e = _fc_edge_near(x, y)
        if hit_s:
            state['selected_sym']    = hit_s['id']
            fc_state['flow_selected']     = hit_s['id']
            state['selected_edge']   = None
            state['drag_offset']     = (x - hit_s['x'], y - hit_s['y'])
            state['dragging']        = True
            state['fc_drag_origin']  = (hit_s['x'], hit_s['y'])
        elif hit_e:
            state['selected_edge'] = {'src': hit_e['src'], 'dst': hit_e['dst'],
                                      'waypoints': list(hit_e.get('waypoints', [])),
                                      'condition': hit_e.get('condition', '')}
            state['selected_sym']  = None
            fc_state['flow_selected']   = None
            state['dragging']      = False
        else:
            state['selected_sym']  = None
            fc_state['flow_selected']   = None
            state['selected_edge'] = None
            state['dragging']      = False
        update_inspect(); redraw()

    def on_release(event):
        if state['dragging'] and state['selected_sym'] is not None:  # Bundle 23 P2: id 0 valid
            sid = state['selected_sym']
            s = fc_state['flow_symbols'].get(sid)  # Phase 6C
            if s:
                if state.get('fc_drag_origin'):
                    ox, oy = state['fc_drag_origin']
                    if ox != s['x'] or oy != s['y']:
                        _guic_push_undo({'kind': 'flow_move', 'id': sid,
                                       'x': ox, 'y': oy})
                set_status(f"Moved {s['label']} → ({s['x']},{s['y']})")
                update_inspect()
        state['dragging']       = False
        state['fc_drag_origin'] = None

    def on_double_click(event):
        # Phase 6C: use fc_state dict hit tests; Bundle 18: convert to design space
        ddx, ddy = _fc_s2d(event.x, event.y)
        hit_s = _fc_sym_at(ddx, ddy)
        hit_e = _fc_edge_near(ddx, ddy)
        if hit_s:
            _open_symbol_props_fc(hit_s)
        elif hit_e:
            _open_edge_props_fc(hit_e)

    def _open_symbol_props_fc(s):
        """Phase 6C: Modal dialog to edit flow symbol label and kind-specific props."""
        dlg = tk.Toplevel(root)
        dlg.title(f"Symbol Properties — {s['label']}")
        dlg.configure(bg=C['bg'])
        dlg.resizable(False, False)
        dlg.transient(root)   # always stay above parent window

        frm = tk.Frame(dlg, bg=C['bg']); frm.pack(padx=12, pady=8)
        tk.Label(frm, text=f"{s['kind'].upper()}  #{s['id']}",
                 bg=C['bg'], fg=C['pal_border'],
                 font=('Monospace', 10, 'bold')
                 ).grid(row=0, column=0, columnspan=2, pady=(0, 8))

        tk.Label(frm, text="Label:", bg=C['bg'], fg=C['inspect_fg'],
                 font=('Monospace', 9), anchor='e', width=12
                 ).grid(row=1, column=0, padx=8, pady=4, sticky='e')
        v_label = tk.StringVar(value=s['label'])
        _lbl_entry = tk.Entry(frm, textvariable=v_label, bg=C['canvas'], fg=C['text'],
                 insertbackground=C['text'], font=('Monospace', 10), width=20,
                 relief='flat', bd=4)
        _lbl_entry.grid(row=1, column=1, padx=8, pady=4)
        # Auto-select existing text so typing replaces it rather than inserting
        dlg.after(50, lambda: (_lbl_entry.focus_set(),
                               _lbl_entry.selection_range(0, 'end')))

        # Phase 7c-1: Name (programmatic identity, distinct from Label)
        tk.Label(frm, text="Name:", bg=C['bg'], fg=C['inspect_fg'],
                 font=('Monospace', 9), anchor='e', width=12
                 ).grid(row=2, column=0, padx=8, pady=4, sticky='e')
        v_name = tk.StringVar(value=s.get('name', ''))
        if s.get('kind') == 'flow_terminator':
            # Phase 7c-2: autocomplete the terminator name from the set of
            # available widget handler names — naming it to a handler wires it.
            _handler_opts = sorted(_aw_all_handler_names(fc_state['stream']))
            ttk.Combobox(frm, textvariable=v_name, values=_handler_opts,
                         font=('Monospace', 10), width=19
                         ).grid(row=2, column=1, padx=8, pady=4)
        else:
            tk.Entry(frm, textvariable=v_name, bg=C['canvas'], fg=C['text'],
                     insertbackground=C['text'], font=('Monospace', 10), width=20,
                     relief='flat', bd=4).grid(row=2, column=1, padx=8, pady=4)

        row_idx = [3]
        extra_vars = {}
        from_props = _fp_properties_for(s['kind'])
        for pd in from_props:
            pname = pd['name']
            if pname in ('name', 'x', 'y', 'w', 'h', 'label'): continue
            tk.Label(frm, text=f"{pname}:", bg=C['bg'], fg=C['inspect_fg'],
                     font=('Monospace', 9), anchor='e', width=12
                     ).grid(row=row_idx[0], column=0, padx=8, pady=4, sticky='e')
            cur_val = _guic_get_prop_value(s, pname)
            if pd['kind'] == 'bool':
                var = tk.BooleanVar(value=bool(cur_val))
                tk.Checkbutton(frm, variable=var, bg=C['bg'], fg=C['text'],
                               activebackground=C['bg'], selectcolor=C['canvas']
                               ).grid(row=row_idx[0], column=1, padx=8, pady=4, sticky='w')
            else:
                var = tk.StringVar(value=str(cur_val or ''))
                tk.Entry(frm, textvariable=var, bg=C['canvas'], fg=C['text'],
                         insertbackground=C['text'], font=('Monospace', 10), width=20,
                         relief='flat', bd=4
                         ).grid(row=row_idx[0], column=1, padx=8, pady=4)
            extra_vars[pname] = (pd, var)
            row_idx[0] += 1

        def _apply():
            try:
                # Phase 7c-1: name change (validated for uniqueness)
                old_name = s.get('name', '')
                new_name = v_name.get().strip()
                if new_name != old_name:
                    if new_name and fc_state['stream'].name_in_use(new_name, exclude=s):
                        import tkinter.messagebox as _mb
                        _mb.showwarning("Duplicate name",
                                        f"The name '{new_name}' is already in use.\n"
                                        "Names must be unique within the program.",
                                        parent=dlg)
                        return
                    s['name'] = new_name
                    _guic_push_undo({'kind': 'flow_prop_change', 'sym_id': s['id'],
                                   'property': 'name',
                                   'old_value': old_name, 'new_value': new_name})
                old_label = s['label']
                new_label = v_label.get().strip()
                if new_label and new_label != old_label:
                    # Update s FIRST so _guic_push_undo captures correct after-state
                    s['label'] = new_label
                    _guic_push_undo({'kind': 'flow_prop_change', 'sym_id': s['id'],
                                   'property': 'label',
                                   'old_value': old_label, 'new_value': new_label})
                for pname, (pd, var) in extra_vars.items():
                    raw_old = _guic_get_prop_value(s, pname)
                    new_v = var.get()
                    if pd['kind'] == 'bool':
                        new_v = bool(new_v)
                        old_v = bool(raw_old) if raw_old is not None else False
                    elif pd['kind'] == 'int':
                        try: new_v = int(new_v)
                        except ValueError: new_v = int(raw_old or 0)
                        old_v = int(raw_old) if raw_old is not None else 0
                    else:
                        new_v = str(new_v) if new_v is not None else ''
                        old_v = str(raw_old) if raw_old is not None else ''
                    if new_v != old_v:
                        # Update s FIRST so _guic_push_undo captures correct after-state
                        _guic_set_prop_value(s, pname, new_v)
                        _guic_push_undo({'kind': 'flow_prop_change', 'sym_id': s['id'],
                                       'property': pname,
                                       'old_value': old_v, 'new_value': new_v})
                set_status(f"Updated {s['label']}")
                _guic_sync_stream()
                update_inspect(); redraw(); dlg.destroy()
            except Exception as _apply_err:
                import traceback as _tb; _tb.print_exc()
                import tkinter.messagebox as _mb
                _mb.showerror("Apply Error",
                              f"Could not apply changes:\n{_apply_err}",
                              parent=dlg)

        # ── Phase 7c-4: Pocket section (container kinds only) ─────────────────
        if s.get('kind') in _FC_CONTAINER_KINDS:
            pk = tk.Frame(dlg, bg=C['bg']); pk.pack(fill='x', padx=12, pady=(0, 4))
            tk.Label(pk, text='Pocket', bg=C['bg'], fg=C['pal_border'],
                     font=('Monospace', 9, 'bold'), anchor='w').pack(fill='x')
            contents = _fc_pocket_contents(s)
            if contents:
                for nm, knd in contents:
                    tk.Label(pk, text=f"  • {nm}  ({knd.replace('flow_','')})",
                             bg=C['bg'], fg=C['text'], font=('Monospace', 8),
                             anchor='w').pack(fill='x')
            else:
                tk.Label(pk, text='  (empty)', bg=C['bg'], fg=C['dim'],
                         font=('Monospace', 8), anchor='w').pack(fill='x')
            def _open_pocket():
                dlg.destroy()
                _fc_set_scope(s['name'])
                set_status(f"Opened pocket: {s['name']}")
            tk.Button(pk, text='Open pocket →', command=_open_pocket,
                      bg=C['pal_btn'], fg=C['text'], font=('Monospace', 9),
                      relief='flat', padx=10, pady=3, cursor='hand2'
                      ).pack(anchor='w', pady=(4, 0))

            # ── Phase 7c-4b: Entry / Exit Points ─────────────────────────────
            if _flowcode_ports is not None:
                s.setdefault('entry_points', [])
                s.setdefault('exit_points', [])
                _fp = _flowcode_ports

                def _port_add_edit(pkind, existing=None):
                    """Modal to add or edit one port (name/type/description)."""
                    pd = tk.Toplevel(dlg); pd.configure(bg=C['palette'])
                    pd.title(('Edit' if existing else 'Add') + f' {pkind} point')
                    pd.transient(dlg); pd.grab_set()
                    nv = tk.StringVar(value=(existing or {}).get('name', ''))
                    tv = tk.StringVar(value=(existing or {}).get('type', 'number'))
                    dv = tk.StringVar(value=(existing or {}).get('description', ''))
                    ev = tk.StringVar(value=(existing or {}).get('expr', ''))
                    _rows = [('Name', nv, None), ('Type', tv, _fp.PORT_TYPES),
                             ('Description', dv, None)]
                    if pkind == 'exit':   # interior computation over entry names
                        _rows.append(('Expr (= interior formula)', ev, None))
                    for r, (lbl, var, opts) in enumerate(_rows):
                        tk.Label(pd, text=lbl + ':', bg=C['palette'], fg=C['text'],
                                 font=('Monospace', 9), anchor='w').grid(
                                     row=r, column=0, sticky='w', padx=8, pady=2)
                        if opts:
                            tk.OptionMenu(pd, var, *opts).grid(
                                row=r, column=1, sticky='w', padx=8, pady=2)
                        else:
                            tk.Entry(pd, textvariable=var, bg=C['inspect'],
                                     fg=C['text'], insertbackground=C['text'],
                                     font=('Monospace', 9), width=22).grid(
                                         row=r, column=1, padx=8, pady=2)
                    _wrow = len(_rows)
                    warn = tk.Label(pd, text='', bg=C['palette'], fg='#ff8888',
                                    font=('Monospace', 8))
                    warn.grid(row=_wrow, column=0, columnspan=2, sticky='w', padx=8)

                    def _commit_port():
                        ok, msg = _fp.validate_new_port(s, nv.get(), tv.get(),
                                                        exclude=existing)
                        if not ok:
                            warn.config(text=msg); return
                        port = _fp.make_port(nv.get(), tv.get(), dv.get(),
                                             expr=ev.get() if pkind == 'exit' else '')
                        lst = s['entry_points'] if pkind == 'entry' else s['exit_points']
                        if existing is not None:
                            lst[lst.index(existing)] = port
                        else:
                            lst.append(port)
                        pd.destroy(); dlg.destroy()
                        _guic_sync_stream(); redraw()
                        _open_flow_props_fc(s)   # reopen to show the update

                    bf = tk.Frame(pd, bg=C['palette']); bf.grid(row=_wrow + 1, column=0,
                                                                columnspan=2, pady=8)
                    tk.Button(bf, text='OK', command=_commit_port, bg=C['pal_btn'],
                              fg=C['text'], font=('Monospace', 9), relief='flat',
                              padx=10).pack(side='left', padx=4)
                    tk.Button(bf, text='Cancel', command=pd.destroy, bg=C['pal_btn'],
                              fg=C['text'], font=('Monospace', 9), relief='flat',
                              padx=10).pack(side='left', padx=4)

                def _port_remove(pkind, port):
                    lst = s['entry_points'] if pkind == 'entry' else s['exit_points']
                    if port in lst:
                        lst.remove(port)
                    dlg.destroy(); _guic_sync_stream(); redraw()
                    _open_flow_props_fc(s)

                def _ports_section(title, pkind, ports):
                    fr = tk.Frame(dlg, bg=C['bg']); fr.pack(fill='x', padx=12, pady=(6, 0))
                    tk.Label(fr, text=title, bg=C['bg'], fg=C['pal_border'],
                             font=('Monospace', 9, 'bold'), anchor='w').pack(fill='x')
                    for p in ports:
                        row = tk.Frame(fr, bg=C['bg']); row.pack(fill='x')
                        tk.Label(row, text=f"  • {p['name']} : {p['type']}",
                                 bg=C['bg'], fg=C['text'], font=('Monospace', 8),
                                 anchor='w').pack(side='left')
                        tk.Button(row, text='✕', command=lambda pp=p: _port_remove(pkind, pp),
                                  bg=C['bg'], fg='#ff8888', font=('Monospace', 8),
                                  relief='flat', cursor='hand2').pack(side='right')
                        tk.Button(row, text='edit',
                                  command=lambda pp=p: _port_add_edit(pkind, pp),
                                  bg=C['bg'], fg=C['dim'], font=('Monospace', 8),
                                  relief='flat', cursor='hand2').pack(side='right')
                    if not ports:
                        tk.Label(fr, text='  (none)', bg=C['bg'], fg=C['dim'],
                                 font=('Monospace', 8), anchor='w').pack(fill='x')
                    tk.Button(fr, text=f'+ Add {pkind} point',
                              command=lambda: _port_add_edit(pkind),
                              bg=C['pal_btn'], fg=C['text'], font=('Monospace', 8),
                              relief='flat', padx=8, cursor='hand2').pack(anchor='w', pady=(2, 0))

                _ports_section('Entry Points', 'entry', s['entry_points'])
                _ports_section('Exit Points', 'exit', s['exit_points'])

        btn_frm = tk.Frame(dlg, bg=C['bg']); btn_frm.pack(pady=8)
        tk.Button(btn_frm, text="Apply", command=_apply,
                  bg=C['pal_active'], fg=C['text'],
                  font=('Monospace', 9, 'bold'), relief='flat', padx=12, pady=4,
                  cursor='hand2').pack(side='left', padx=6)
        tk.Button(btn_frm, text="Cancel", command=dlg.destroy,
                  bg=C['pal_btn'], fg=C['dim'],
                  font=('Monospace', 9), relief='flat', padx=12, pady=4,
                  cursor='hand2').pack(side='left', padx=6)
        dlg.bind('<Return>', lambda ev: _apply())
        dlg.bind('<Escape>', lambda ev: dlg.destroy())
        dlg.update_idletasks(); dlg.grab_set(); dlg.lift(); dlg.focus_force()

    def _open_edge_props_fc(e):
        """Phase 6C: Modal dialog to edit flow edge condition."""
        # e is a flow edge dict {src, dst, waypoints, condition}
        src = fc_state['flow_symbols'].get(e['src'])
        dst = fc_state['flow_symbols'].get(e['dst'])
        sl  = src['label'] if src else f"#{e['src']}"
        dl  = dst['label'] if dst else f"#{e['dst']}"

        dlg = tk.Toplevel(root)
        dlg.title(f"Edge Properties — {sl} → {dl}")
        dlg.configure(bg=C['bg'])
        dlg.resizable(False, False)
        dlg.transient(root)   # always stay above parent window

        frm = tk.Frame(dlg, bg=C['bg']); frm.pack(padx=12, pady=8)
        tk.Label(frm, text=f"Edge  {sl} → {dl}",
                 bg=C['bg'], fg=C['pal_border'],
                 font=('Monospace', 10, 'bold')
                 ).grid(row=0, column=0, columnspan=2, pady=(0, 8))

        tk.Label(frm, text="Condition:", bg=C['bg'], fg=C['inspect_fg'],
                 font=('Monospace', 9), anchor='e', width=12
                 ).grid(row=1, column=0, padx=8, pady=4, sticky='e')
        v_cond = tk.StringVar(value=e.get('condition', ''))
        tk.Entry(frm, textvariable=v_cond, bg=C['canvas'], fg=C['text'],
                 insertbackground=C['text'], font=('Monospace', 10), width=18,
                 relief='flat', bd=4
                 ).grid(row=1, column=1, padx=8, pady=4)

        def _apply():
            try:
                new_cond = v_cond.get().strip()
                e['condition'] = new_cond
                if (state['selected_edge'] and
                        state['selected_edge'].get('src') == e['src'] and
                        state['selected_edge'].get('dst') == e['dst']):
                    state['selected_edge']['condition'] = new_cond
                set_status(f"Edge {sl}→{dl}  condition='{new_cond}'")
                _guic_sync_stream()
                update_inspect(); redraw(); dlg.destroy()
            except Exception as _apply_err:
                import traceback as _tb; _tb.print_exc()
                import tkinter.messagebox as _mb
                _mb.showerror("Apply Error",
                              f"Could not apply changes:\n{_apply_err}",
                              parent=dlg)

        btn_frm = tk.Frame(dlg, bg=C['bg']); btn_frm.pack(pady=8)
        tk.Button(btn_frm, text="Apply", command=_apply,
                  bg=C['pal_active'], fg=C['text'],
                  font=('Monospace', 9, 'bold'), relief='flat', padx=12, pady=4,
                  cursor='hand2').pack(side='left', padx=6)
        tk.Button(btn_frm, text="Cancel", command=dlg.destroy,
                  bg=C['pal_btn'], fg=C['dim'],
                  font=('Monospace', 9), relief='flat', padx=12, pady=4,
                  cursor='hand2').pack(side='left', padx=6)
        dlg.bind('<Return>', lambda ev: _apply())
        dlg.bind('<Escape>', lambda ev: dlg.destroy())
        dlg.update_idletasks(); dlg.grab_set(); dlg.lift(); dlg.focus_force()

    def on_key(event):
        if notebook.index('current') != 0:
            return   # Let GHOST canvas handle its own keys
        k = event.keysym.lower()
        # Bundle 18: Home key resets Flow canvas view
        if k == 'home':
            _fc_view['zoom'] = 1.0; _fc_view['sx'] = 0.0; _fc_view['sy'] = 0.0
            _fc_update_scrollregion(); redraw(); _update_zoom_indicator(); return
        # Bundle 21: arrow keys + Page Up/Down scroll the Flow canvas
        if k in ('up', 'kp_up'):
            _fc_view['sy'] -= GRID; _fc_update_scrollregion(); redraw(); return
        if k in ('down', 'kp_down'):
            _fc_view['sy'] += GRID; _fc_update_scrollregion(); redraw(); return
        if k in ('left', 'kp_left'):
            _fc_view['sx'] -= GRID; _fc_update_scrollregion(); redraw(); return
        if k in ('right', 'kp_right'):
            _fc_view['sx'] += GRID; _fc_update_scrollregion(); redraw(); return
        if k == 'prior':    # Page Up
            _fc_view['sy'] -= (tk_canvas.winfo_height() or 660) / _fc_view['zoom']
            _fc_update_scrollregion(); redraw(); return
        if k == 'next':     # Page Down
            _fc_view['sy'] += (tk_canvas.winfo_height() or 660) / _fc_view['zoom']
            _fc_update_scrollregion(); redraw(); return
        if k == 't': set_mode('place_terminator')
        elif k == 'r': set_mode('place_process')
        elif k == 'd': set_mode('place_decision')
        elif k == 'i': set_mode('place_io')
        elif k == 'e': set_mode('edge_src')
        elif k == 'escape':
            # Phase 7c-4: Escape closes the current pocket (out one scope level)
            if fc_state.get('flow_scope') is not None:
                cur = _fc_sym_by_name(fc_state['flow_scope'])
                _fc_set_scope(cur.get('parent_scope') if cur else None)
                set_status('Closed pocket')
            else:
                set_mode('select')
        elif k == 'w':
            _fc_sync_canvas_model(); do_dump()
        elif k == 'l':
            _fc_sync_canvas_model(); do_load()
        elif k == 'delete':
            if state['selected_sym'] is not None:   # Bundle 23 P2: id 0 valid
                s = fc_state['flow_symbols'].get(state['selected_sym'])  # Phase 6C
                if s:
                    lbl = s['label']
                    _fc_remove_symbol(state['selected_sym'])
                    state['selected_sym'] = None
                    fc_state['flow_selected']  = None
                    set_status(f"Deleted {lbl}")
                    set_inspect("Select a symbol or edge to inspect"); redraw()
            elif state['selected_edge']:
                e = state['selected_edge']
                _fc_remove_edge(e['src'], e['dst'])
                state['selected_edge'] = None
                set_status("Edge deleted"); redraw()
        elif event.state & 0x4:
            if k == 's': guic_do_save()    # Phase 6C: unified .tgui save
            elif k == 'o': guic_do_open()  # Phase 6C: unified .tgui open
            elif k == 'z': set_mode('select')  # Ctrl+Z as cancel/escape

    # ═══════════════════════════════════════════════════════════════════════════
    # GHOST Canvas tab
    # ═══════════════════════════════════════════════════════════════════════════

    GW, GH = 160, 72   # widget block size on ghost canvas

    # Category colour by Y-range bracket
    def _ghost_cat_color(y_lo):
        if y_lo >= 500: return '#0f3060'   # containers  — blue
        if y_lo >= 400: return '#3a1060'   # controls    — purple
        if y_lo >= 300: return '#0f3a3a'   # inputs      — teal
        if y_lo >= 200: return '#0f3a1a'   # display     — green
        if y_lo >= 100: return '#3a2a0f'   # dialogs     — amber
        return '#3a0f1a'                    # menus       — dark red

    _guic_color = {t: _ghost_cat_color(y) for t, y in _ghost_palette_types}

    # ── GHOST canvas constants ────────────────────────────────────────────────
    # Widget kinds that can contain children (D5)
    CONTAINER_KINDS = frozenset({
        'gui_window', 'gui_dialog', 'gui_box', 'gui_grid', 'gui_frame',
        'gui_notebook', 'gui_paned', 'gui_scrolled', 'gui_stack',
        'gui_expander', 'gui_revealer', 'gui_overlay', 'gui_flowbox',
        'gui_listbox', 'gui_headerbar', 'gui_actionbar', 'gui_menubar',
        'gui_toolbar', 'gui_statusbar',
    })

    # Default (w, h) per kind; fallback to (GW, GH)
    _GC_DEFAULT_SIZE = {
        'gui_window':    (200, 160), 'gui_dialog':    (200, 160),
        'gui_box':       (200, 120), 'gui_grid':      (200, 120),
        'gui_frame':     (200, 120), 'gui_notebook':  (200, 120),
        'gui_paned':     (240, 120), 'gui_scrolled':  (200, 120),
        'gui_stack':     (200, 120), 'gui_expander':  (200,  80),
        'gui_revealer':  (200, 100), 'gui_overlay':   (200, 120),
        'gui_flowbox':   (240, 120), 'gui_listbox':   (200, 120),
        'gui_headerbar': (240,  50), 'gui_actionbar': (240,  50),
        'gui_menubar':   (240,  25), 'gui_toolbar':   (240,  40),
        'gui_statusbar': (240,  25),
    }
    _GC_MIN_SIZE = 20   # minimum width and height in px (D3)

    # Per-kind default layout mode (Bundle 7 Stage 4)
    _GC_LAYOUT_DEFAULTS: dict = {
        'gui_window': 'absolute', 'gui_dialog': 'absolute',
        'gui_box': 'vbox',        'gui_grid': 'grid',
        'gui_frame': 'absolute',  'gui_notebook': 'stacked', 'gui_stack': 'stacked',
        'gui_paned': 'hbox',
        'gui_expander': 'absolute', 'gui_revealer': 'absolute',
        'gui_overlay': 'absolute',  'gui_scrolled': 'absolute',
        'gui_flowbox': 'vbox',      'gui_listbox': 'vbox',
        'gui_headerbar': 'hbox',    'gui_actionbar': 'hbox',
        'gui_menubar': 'hbox',      'gui_toolbar': 'hbox', 'gui_statusbar': 'hbox',
    }
    _GC_PROP_W = 280   # property panel width in pixels

    # ── Load flowcode_signals (Phase 6D) ─────────────────────────────────────
    _fsig_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '../5500fp/flowcode_signals.py')
    if os.path.exists(_fsig_path):
        import importlib.util as _fsig_u
        _fsig_spec = _fsig_u.spec_from_file_location('flowcode_signals', _fsig_path)
        _fsig_mod  = _fsig_u.module_from_spec(_fsig_spec)
        _fsig_spec.loader.exec_module(_fsig_mod)
        _signals_for         = _fsig_mod.signals_for
        _common_signals_for  = _fsig_mod.common_signals_for_kinds
        # Phase 7c-2: name-based auto-wiring helpers
        _aw_materialize      = _fsig_mod.materialize_auto_wired_bindings
        _aw_reconcile        = _fsig_mod.reconcile_loaded_bindings
        _aw_conform          = _fsig_mod.conform_manual_bindings
        _aw_nonconforming    = _fsig_mod.find_nonconforming_manual_bindings
        _aw_all_handler_names= _fsig_mod.all_handler_names
        _aw_names_for_widget = _fsig_mod.auto_handler_names_for_widget
        _aw_canonical        = _fsig_mod.canonical_handler_name
    else:
        _signals_for         = lambda kind: []
        _common_signals_for  = lambda kinds: []
        _aw_materialize      = lambda stream: 0
        _aw_reconcile        = lambda stream: []
        _aw_conform          = lambda stream: 0
        _aw_nonconforming    = lambda stream: []
        _aw_all_handler_names= lambda stream: set()
        _aw_names_for_widget = lambda widget: []
        _aw_canonical        = lambda wn, sn: ''

    # ── Load sheet_formula (Stage 8-3 formula engine) ────────────────────────
    _sf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '../5500fp/sheet_formula.py')
    _sheet_formula = None
    if os.path.exists(_sf_path):
        try:
            import importlib.util as _sf_u
            _sf_spec = _sf_u.spec_from_file_location('sheet_formula', _sf_path)
            _sheet_formula = _sf_u.module_from_spec(_sf_spec)
            _sf_spec.loader.exec_module(_sheet_formula)
        except Exception as _sf_err:
            print(f'[FlowCode] sheet_formula failed to load: {_sf_err}')

    # ── Load flowcode_commands (Stage 9-1A Shell command registry) ───────────
    _fcmd_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '../5500fp/flowcode_commands.py')
    _flowcode_commands = None
    if os.path.exists(_fcmd_path):
        try:
            import importlib.util as _fcmd_u
            _fcmd_spec = _fcmd_u.spec_from_file_location('flowcode_commands', _fcmd_path)
            _flowcode_commands = _fcmd_u.module_from_spec(_fcmd_spec)
            _fcmd_spec.loader.exec_module(_flowcode_commands)
        except Exception as _fcmd_err:
            print(f'[FlowCode] flowcode_commands failed to load: {_fcmd_err}')

    # ── Load flowcode_ports (Phase 7c-4b entry/exit points) ──────────────────
    _fport_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '../5500fp/flowcode_ports.py')
    _flowcode_ports = None
    if os.path.exists(_fport_path):
        try:
            import importlib.util as _fport_u
            _fport_spec = _fport_u.spec_from_file_location('flowcode_ports', _fport_path)
            _flowcode_ports = _fport_u.module_from_spec(_fport_spec)
            _fport_spec.loader.exec_module(_flowcode_ports)
        except Exception as _fport_err:
            print(f'[FlowCode] flowcode_ports failed to load: {_fport_err}')

    # ── Load ghost_meccano for incremental word-stream updates (Phase 6E) ───────
    # flowcode_bridge.py deleted; functions now live in ghost_meccano.py
    # (GHOST+flow bridges) and flowcode_signals.py (handler binding emitter).
    _ghmc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '../5500fp/ghost_meccano.py')
    if os.path.exists(_ghmc_path):
        import importlib.util as _ghmc_u
        _ghmc_spec = _ghmc_u.spec_from_file_location('ghost_meccano', _ghmc_path)
        _ghmc_mod  = _ghmc_u.module_from_spec(_ghmc_spec)
        _ghmc_spec.loader.exec_module(_ghmc_mod)
        _ghost_to_meccano      = _ghmc_mod.ghost_to_meccano
        _update_meccano_widget = _ghmc_mod.update_meccano_for_widget
        # Phase 6C: flow-dict → MeccanoProgram bridge
        _flow_to_meccano       = _ghmc_mod.flow_symbols_to_meccano
    else:
        _ghost_to_meccano      = None
        _update_meccano_widget = None
        _flow_to_meccano       = None
    # Phase 6D/Phase 6E: handler binding REDGE word emitter — now in flowcode_signals
    _build_handler_bindings = (getattr(_fsig_mod, 'build_handler_bindings', None)
                                if os.path.exists(_fsig_path) else None)

    # ── Load WordStream + WordStreamEdit (Phase 6A) ───────────────────────────
    _ws_path  = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             '../5500fp/word_stream.py')
    _wse_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             '../5500fp/word_stream_edit.py')
    if os.path.exists(_ws_path) and os.path.exists(_wse_path):
        import importlib.util as _wsu
        _ws_spec  = _wsu.spec_from_file_location('word_stream',      _ws_path)
        _wse_spec = _wsu.spec_from_file_location('word_stream_edit', _wse_path)
        import sys as _wssys
        _ws_mod   = _wsu.module_from_spec(_ws_spec)
        _wse_mod  = _wsu.module_from_spec(_wse_spec)
        _wssys.modules['word_stream']      = _ws_mod
        _wssys.modules['word_stream_edit'] = _wse_mod
        _ws_spec.loader.exec_module(_ws_mod)
        _wse_spec.loader.exec_module(_wse_mod)
        WordStream     = _ws_mod.WordStream
        WordStreamEdit = _wse_mod.WordStreamEdit
    else:
        WordStream     = None
        WordStreamEdit = None

    # ── Load property registry ────────────────────────────────────────────────
    _fp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '../5500fp/flowcode_properties.py')
    if os.path.exists(_fp_path):
        import importlib.util as _fpu
        _fp_spec = _fpu.spec_from_file_location('flowcode_properties', _fp_path)
        _fp_mod  = _fpu.module_from_spec(_fp_spec)
        _fp_spec.loader.exec_module(_fp_mod)
        _fp_properties_for       = _fp_mod.properties_for
        _fp_common_for_kinds     = _fp_mod.common_properties_for_kinds
    else:
        def _fp_properties_for(kind): return []
        def _fp_common_for_kinds(kinds): return []

    # Phase 7b-1: track the most recently saved/opened .ternoo path for compiler header.
    _current_design_path = [None]   # mutable so closures can update it

    # ── Shared canvas state (GHOST + FlowCode) ───────────────────────────────
    fc_state = {
        'widgets':       {},    # id → {id, kind, x, y, label, w, h, parent_id, layout_mode, properties}
        'edges':         [],    # [{src, dst}, …]
        'stream':        WordStream() if WordStream else None,  # Phase 6A: mirrors widgets in lockstep
        # Phase 6C: FlowCode tab — parallel to widgets/edges, same stream
        'flow_symbols':  {},    # id → {id, kind, x, y, w, h, label, properties}
        'flow_edges':    [],    # [{src, dst, waypoints, condition}]
        'flow_next_id':  0,
        'flow_selected': None,
        'flow_multi_sel': set(),
        'flow_scope':     None,    # Phase 7c-4: current pocket scope (symbol name)
        # Stage 9-0: Shell tab — command widgets (cmd_*), own canvas/mode state
        'cmd_widgets':    {},   # id → {id, kind, x, y, w, h, label, name, properties}
        'cmd_next_id':    0,
        'cmd_selected':   None,
        'cmd_multi_sel':  set(),
        'cmd_mode':       'select',  # 'select' | 'delete' | 'place'
        'cmd_dragging':   False,
        'cmd_drag_offset':(0, 0),
        'cmd_drag_origin':None,  # (x, y) at drag-start for undo
        'cmd_ghost':      None,  # (x, y) design-space placement ghost
        # Stage 9-2: typed pipe edges between commands
        'cmd_edges':      [],    # [{src, dst, dst_param}]
        'cmd_pipe_src':   None,  # (cmd_id) while dragging a pipe from an output
        'cmd_pipe_xy':    None,  # (x, y) current drag end during pipe draw
        # Stage 8-1: Sheet tab — cells keyed by (row, col)
        'cells':          {},    # (row,col) → {id, kind, row, col, name, value, properties}
        'cell_next_id':   0,
        'cell_sel':       (0, 0),  # (row, col) of the selected cell
        'cell_editing':   False,
        # Stage 8-9: free-form regions on the Sheet canvas
        'sheet_regions':  {},      # id → {id, kind:'sheet_region', x, y, w, h, name, label}
        'free_cells':     {},      # id → free cell {id, kind, region_id, px, py, name, value}
        'region_next_id': 0,
        'sheet_mode':     'select',  # 'select' | 'place_region'
        'selected':      None,  # int id of primary selected widget
        'multi_sel':     set(), # all selected ids (includes selected)
        'mode':          'select',
        'place_kind':    None,
        'edge_src':      None,
        'next_id':       0,
        'dragging':      False,
        'drag_offset':   (0, 0),
        'drag_origin':   None,  # (x, y) at drag-start for undo
        'resize_handle': None,  # 'NW'|'N'|… or None
        'resize_origin': None,  # (wx, wy, ww, wh) at resize-start for undo
        'drop_target':   None,  # id of highlighted container drop target
        # Stage 4 — layout
        'child_order':   {},    # parent_id → [child_ids] in insertion order
        'drag_insert_parent': None,  # parent id being reordered within
        'drag_insert_idx':    None,  # target insertion index for reorder
        # Stage 5 — property panel
        'prop_committed': {},   # widget_id → {prop_name: committed_value}
        'guic_program':    None,  # current MeccanoProgram (updated at each commit)
        # Bundle 10 — lasso multi-select
        'lasso_start':   None,  # (x, y) canvas start of rubber-band drag
        'lasso_end':     None,  # (x, y) current end during drag
    }

    # Phase 6B: make fc_state['stream']._widget_meta the same object as fc_state['widgets'].
    # This means fc_state['widgets'] IS the stream's metadata dict — zero read-site changes
    # needed for the 74 read sites; writes to fc_state['widgets'] automatically update the
    # stream's _widget_meta.  (D5: "may exist as lazy derived property" satisfied here
    # by aliasing rather than deriving.)
    # Phase 6C: same alias for flow symbols.
    if fc_state.get('stream') is not None:
        fc_state['stream']._widget_meta = fc_state['widgets']
        fc_state['stream']._flow_meta   = fc_state['flow_symbols']  # Phase 6C
        fc_state['stream']._cmd_meta    = fc_state['cmd_widgets']   # Stage 9-0
        fc_state['stream']._cmd_edges   = fc_state['cmd_edges']     # Stage 9-2
        fc_state['stream']._cell_meta   = fc_state['cells']         # Stage 8-1

    # ── Ghost canvas layout ───────────────────────────────────────────────────
    # guic_pal removed — sidebar is now the universal palette_frame (tab-aware).
    # Kept as an unmanaged dummy so legacy refs compile; never packed.
    guic_pal = tk.Frame(ghost_tab, bg=C['palette'])

    # Right-side property panel (packed before guic_right so it claims the right boundary)
    _guic_prop_visible = [True]
    guic_prop_outer = tk.Frame(ghost_tab, bg=C['palette'], width=_GC_PROP_W)
    guic_prop_outer.pack(side='right', fill='y')
    guic_prop_outer.pack_propagate(False)

    guic_right = tk.Frame(ghost_tab, bg=C['bg'])
    guic_right.pack(side='left', fill='both', expand=True)
    _gc_cv_frame = tk.Frame(guic_right, bg=C['canvas'])
    _gc_cv_frame.pack(fill='both', expand=True)
    _gc_vsb = tk.Scrollbar(_gc_cv_frame, orient='vertical',   bg=C['palette'])
    _gc_hsb = tk.Scrollbar(_gc_cv_frame, orient='horizontal', bg=C['palette'])
    _gc_hsb.pack(side='bottom', fill='x')
    _gc_vsb.pack(side='right',  fill='y')
    guic = tk.Canvas(_gc_cv_frame, bg=C['canvas'], highlightthickness=0)
    guic.pack(fill='both', expand=True)
    _gc_status_frame = tk.Frame(guic_right, bg=C['status'])
    _gc_status_frame.pack(side='bottom', fill='x')
    guic_bar   = tk.Label(_gc_status_frame,
                        text="GUI Canvas — pick a widget type from the palette",
                        bg=C['status'], fg=C['pal_border'],
                        font=('Monospace', 9), anchor='w', padx=8)
    guic_bar.pack(side='left', fill='x', expand=True, ipady=3)
    _gc_zoom_lbl = tk.Label(_gc_status_frame, text='Zoom: 100%', anchor='e',
                            bg=C['status'], fg=C['dim'],
                            font=('Monospace', 8), padx=8)
    _gc_zoom_lbl.pack(side='right', ipady=3)

    # ── Bundle 18: GUI canvas viewport state + coord helpers ──────────────────
    _gc_view = {'zoom': 1.0, 'sx': 0.0, 'sy': 0.0}
    _gc_pan  = [None]   # [{'ox':, 'oy':, 'ex':, 'ey':}] during middle-drag, else None

    def _gc_d2s(dx, dy):
        """Design → screen coords for the GUI canvas."""
        z = _gc_view['zoom']
        return (dx - _gc_view['sx']) * z, (dy - _gc_view['sy']) * z

    def _gc_s2d(ex, ey):
        """Screen → design coords for the GUI canvas."""
        z = _gc_view['zoom']
        return ex / z + _gc_view['sx'], ey / z + _gc_view['sy']

    def _gc_update_scrollregion():
        """Update GUI canvas scrollregion and scrollbar thumb positions.
        Bundle 21: scrollbar .set() added so thumbs reflect current view."""
        wgts = fc_state.get('widgets', {})
        cw   = guic.winfo_width()  or 860
        ch   = guic.winfo_height() or 660
        if not wgts:
            guic.config(scrollregion=(0, 0, cw, ch))
            _gc_vsb.set(0.0, 1.0)
            _gc_hsb.set(0.0, 1.0)
            return
        z        = _gc_view['zoom']
        pad      = 60
        all_pos  = [guic_abs_pos(w) for w in wgts.values()]
        wgts_lst = list(wgts.values())
        d_min_x  = min(ax - w.get('w', GW) // 2
                       for (ax, _), w in zip(all_pos, wgts_lst)) - pad / z
        d_max_x  = max(ax + w.get('w', GW) // 2
                       for (ax, _), w in zip(all_pos, wgts_lst)) + pad / z
        d_min_y  = min(ay - w.get('h', GH) // 2
                       for (_, ay), w in zip(all_pos, wgts_lst)) - pad / z
        d_max_y  = max(ay + w.get('h', GH) // 2
                       for (_, ay), w in zip(all_pos, wgts_lst)) + pad / z
        d_rng_x  = max(d_max_x - d_min_x, 1.0)
        d_rng_y  = max(d_max_y - d_min_y, 1.0)
        # scrollregion in screen space (consistent with _gc_d2s)
        guic.config(scrollregion=((d_min_x - _gc_view['sx']) * z,
                                  (d_min_y - _gc_view['sy']) * z,
                                  (d_max_x - _gc_view['sx']) * z,
                                  (d_max_y - _gc_view['sy']) * z))
        # Scrollbar thumb: fraction of design-space currently visible
        vis_w = cw / z
        vis_h = ch / z
        f0x = (_gc_view['sx'] - d_min_x) / d_rng_x
        f1x = f0x + vis_w / d_rng_x
        f0y = (_gc_view['sy'] - d_min_y) / d_rng_y
        f1y = f0y + vis_h / d_rng_y
        _gc_hsb.set(max(0.0, f0x), min(1.0, max(f0x + 0.001, f1x)))
        _gc_vsb.set(max(0.0, f0y), min(1.0, max(f0y + 0.001, f1y)))

    # ── Property panel interior ───────────────────────────────────────────────
    _guic_prop_chev = tk.Button(guic_prop_outer, text='›',
                               bg=C['palette'], fg=C['dim'],
                               font=('Monospace', 10, 'bold'),
                               relief='flat', bd=0, cursor='hand2', width=2)
    _guic_prop_chev.pack(side='left', fill='y', pady=2)

    _guic_prop_body = tk.Frame(guic_prop_outer, bg=C['palette'])
    _guic_prop_body.pack(side='left', fill='both', expand=True)

    tk.Label(_guic_prop_body, text='PROPERTIES',
             bg=C['palette'], fg=C['pal_border'],
             font=('Monospace', 8, 'bold'), pady=4).pack(fill='x')

    _guic_prop_cvs = tk.Canvas(_guic_prop_body, bg=C['palette'], highlightthickness=0)
    _guic_prop_sb  = tk.Scrollbar(_guic_prop_body, orient='vertical',
                                 command=_guic_prop_cvs.yview)
    _guic_prop_sb.pack(side='right', fill='y')
    _guic_prop_cvs.pack(side='left', fill='both', expand=True)
    _guic_prop_cvs.configure(yscrollcommand=_guic_prop_sb.set)

    _guic_prop_inner = tk.Frame(_guic_prop_cvs, bg=C['palette'])
    _guic_prop_inner_id = _guic_prop_cvs.create_window(
        (0, 0), window=_guic_prop_inner, anchor='nw')

    def _guic_prop_on_frame_configure(event):
        _guic_prop_cvs.configure(scrollregion=_guic_prop_cvs.bbox('all'))
    _guic_prop_inner.bind('<Configure>', _guic_prop_on_frame_configure)

    def _guic_prop_on_canvas_configure(event):
        _guic_prop_cvs.itemconfig(_guic_prop_inner_id, width=event.width)
    _guic_prop_cvs.bind('<Configure>', _guic_prop_on_canvas_configure)

    def _guic_prop_toggle():
        _guic_prop_visible[0] = not _guic_prop_visible[0]
        if _guic_prop_visible[0]:
            _guic_prop_body.pack(side='left', fill='both', expand=True)
            _guic_prop_chev.config(text='›')
            guic_prop_outer.config(width=_GC_PROP_W)
        else:
            _guic_prop_body.pack_forget()
            _guic_prop_chev.config(text='‹')
            guic_prop_outer.config(width=16)
    _guic_prop_chev.config(command=_guic_prop_toggle)

    def guic_set_status(m): guic_bar.config(text=m)

    def guic_set_mode(m, kind=None):
        fc_state['mode'] = m; fc_state['place_kind'] = kind
        if m == 'select':   guic_set_status("GUI Canvas — select, drag, or connect widgets")
        elif m == 'place':  guic_set_status(f"Click canvas to place  {kind}  (Esc to cancel)")
        elif m == 'edge_src': guic_set_status("Click the parent (source) widget")
        elif m == 'edge_dst': guic_set_status("Click the child (destination) widget")
        elif m == 'delete': guic_set_status("Click a widget or edge to delete it")

    # ── Action handlers (buttons now in tab-aware sidebar) ───────────────────
    def guic_do_connect(): guic_set_mode('edge_src')
    def guic_do_delete():  guic_set_mode('delete')

    def guic_do_suggest():
        sel = fc_state['selected']
        if sel is None or sel not in fc_state['widgets']:
            guic_set_status("Select a widget first, then Suggest"); return
        kind = fc_state['widgets'][sel]['kind']
        row  = {k: v for k, v in _ghost_weights.get(kind, {}).items() if k != kind}
        if not row:
            guic_set_status(f"No suggestions for {kind} — train more first"); return
        best  = max(row, key=row.get)
        total = sum(row.values())
        pct   = int(100 * row[best] / total) if total else 0
        # Auto-place suggested widget to the right of selected
        sw  = fc_state['widgets'][sel]
        nid = fc_state['next_id']; fc_state['next_id'] += 1
        _dw, _dh = _GC_DEFAULT_SIZE.get(best, (GW, GH))
        fc_state['widgets'][nid] = {
            'id': nid, 'kind': best,
            'x': snap(sw['x'] + GW + 30), 'y': sw['y'],
            'label': best.replace('gui_', ''),
            'name': _fc_make_default_name(best, nid),
            'w': _dw, 'h': _dh, 'parent_id': None,
            'layout_mode': _GC_LAYOUT_DEFAULTS.get(best, 'absolute'),
            'properties': [],
        }
        fc_state['edges'].append({'src': sel, 'dst': nid})
        fc_state['selected'] = nid; fc_state['multi_sel'] = {nid}
        guic_set_status(f"GHOST suggests: {kind} → {best}  ({pct}%)")
        guic_redraw()

    def guic_do_clear():
        if fc_state['widgets']:
            from tkinter import messagebox as _mb2
            if not _mb2.askyesno('Clear', 'Clear GHOST canvas?'): return
        fc_state['widgets'].clear(); fc_state['edges'].clear()
        fc_state['selected'] = None; fc_state['next_id'] = 0
        guic_set_mode('select'); guic_redraw()

    def _save_to_path(path):
        """Phase 7c-0: Write fc_state to `path`.
        Handles .fc / .flow / .gui / .ternoo extensions, partial-save warning
        dialogs, and titlebar update. Called by do_save() and guic_do_save()."""
        ext      = os.path.splitext(path)[1].lower()
        has_gui  = bool(fc_state['widgets'])
        has_flow = bool(fc_state['flow_symbols'])

        # ── Partial-save warnings ─────────────────────────────────────────
        if ext == '.gui' and has_flow:
            ans = messagebox.askyesnocancel(
                "Save as .gui?",
                "Your program contains flowchart symbols that won't be saved "
                "in a .gui file.\n\n"
                "  Yes    → save as .fc instead (keeps everything)\n"
                "  No     → save anyway as .gui  (flow content lost)\n"
                "  Cancel → don't save",
                icon='warning')
            if ans is None: return
            if ans:
                path = os.path.splitext(path)[0] + '.fc'
                ext  = '.fc'
        elif ext == '.flow' and has_gui:
            ans = messagebox.askyesnocancel(
                "Save as .flow?",
                "Your program contains GUI widgets that won't be saved "
                "in a .flow file.\n\n"
                "  Yes    → save as .fc instead (keeps everything)\n"
                "  No     → save anyway as .flow (GUI content lost)\n"
                "  Cancel → don't save",
                icon='warning')
            if ans is None: return
            if ans:
                path = os.path.splitext(path)[0] + '.fc'
                ext  = '.fc'

        # ── Build payload filtered by extension ───────────────────────────
        if ext == '.flow':
            # Flow-only partial save — no GUI content
            save_syms  = []
            save_edges = []
        else:
            save_syms = [
                {'id': w['id'], 'kind': w['kind'], 'label': w['label'],
                 'name': w.get('name', ''),
                 'gtk_class': '', 'x': w['x'], 'y': w['y'], 'depth': 0,
                 'w': w.get('w', GW), 'h': w.get('h', GH),
                 'parent_id': w.get('parent_id'),
                 'layout_mode': w.get('layout_mode',
                                      _GC_LAYOUT_DEFAULTS.get(w['kind'], 'absolute')),
                 'properties': list(w.get('properties', [])), 'signals': [],
                 # Bundle 12: 'bindings' retired; signal_ids uses int signal IDs.
                 # Phase 7c-2: auto-wired entries are derived from names — omit
                 # them (regenerated on load); only manual edges are persisted.
                 'signal_ids': {str(k): {kk: vv for kk, vv in v.items()
                                         if kk != 'auto_wired'}
                                for k, v in (w.get('signal_ids') or {}).items()
                                if not v.get('auto_wired')}}
                for w in fc_state['widgets'].values()]
            save_edges = [
                {'src': e['src'], 'dst': e['dst'],
                 'privilege': 0, 'call_style': 0, 'return_type': 1,
                 'seg_idx': 0, 'offset': 0, 'waypoints': [], 'condition': ''}
                for e in fc_state['edges']]

        if ext == '.gui':
            # GUI-only partial save — no flow content
            save_flow_syms  = []
            save_flow_edges = []
        else:
            save_flow_syms  = [dict(s) for s in fc_state['flow_symbols'].values()]
            save_flow_edges = [dict(e) for e in fc_state['flow_edges']]

        # Stage 9-0: Shell command widgets — saved in full programs only.
        # .gui / .flow partials carry their own surface; a dedicated .shell
        # partial is reserved by the file-extension policy but not yet emitted.
        if ext in ('.gui', '.flow'):
            save_cmd_syms = []
            save_cmd_edges = []
        else:
            save_cmd_syms = [dict(c) for c in fc_state['cmd_widgets'].values()]
            save_cmd_edges = [dict(e) for e in fc_state.get('cmd_edges', [])]

        # Stage 8-1: Sheet cells — saved in full programs only.
        if ext in ('.gui', '.flow'):
            save_cell_syms = []
            save_regions = []
            save_free = []
        else:
            save_cell_syms = [dict(c) for c in fc_state['cells'].values()]
            save_regions = [dict(r) for r in fc_state['sheet_regions'].values()]
            save_free = [dict(c) for c in fc_state['free_cells'].values()]

        _stream_words = (list(fc_state['stream'].words)
                         if fc_state.get('stream') is not None else [])

        payload = {
            'ternoo_version': '0.3',
            'source_file':   os.path.basename(path),
            'source_type':   'ternoo_design',
            'word_stream':   _stream_words,
            'symbols':       save_syms,
            'edges':         save_edges,
            'flow_symbols':  save_flow_syms,
            'flow_edges':    save_flow_edges,
            'cmd_symbols':   save_cmd_syms,   # Stage 9-0: Shell command widgets
            'cmd_edges':     save_cmd_edges,  # Stage 9-2: typed pipe edges
            'cell_symbols':  save_cell_syms,  # Stage 8-1: Sheet cells
            'sheet_regions': save_regions,    # Stage 8-9: free-form regions
            'free_cells':    save_free,       # Stage 8-9: absolutely-positioned cells
            'sequence':      ([w['id'] for w in fc_state['widgets'].values()]
                              if ext != '.flow' else []),
            'tgui_meta': {
                'widget_count':      len(save_syms),
                'edge_count':        len(save_edges),
                'flow_symbol_count': len(save_flow_syms),
                'flow_edge_count':   len(save_flow_edges),
                'cmd_widget_count':  len(save_cmd_syms),
                'cell_count':        len(save_cell_syms),
                'mmoe_types_used':   (list({w['kind']
                                           for w in fc_state['widgets'].values()})
                                      if ext != '.flow' else []),
            },
        }
        with open(path, 'w') as _sf:
            json.dump(payload, _sf, indent=2)
        _current_design_path[0] = path   # Phase 7b-1: track for compiler header
        _name = os.path.basename(path)
        root.title(f"FlowCode v0.7.0 — TernOO-5500FP Visual IDE  [{_name}]")
        guic_set_status(f"Saved: {_name}")

    def guic_do_save():
        """Phase 7c-0 Save As — always prompts for filename + extension."""
        if not fc_state['widgets'] and not fc_state['flow_symbols']:
            guic_set_status("Nothing to save"); return
        init_path = _current_design_path[0] or ''
        path = filedialog.asksaveasfilename(
            parent=root, title='Save FlowCode program',
            initialdir=_FC_DIR,
            initialfile=os.path.basename(init_path) if init_path else 'untitled.fc',
            defaultextension='.fc',
            filetypes=[
                ('FlowCode program',     '*.fc'),
                ('Flow-only partial',    '*.flow'),
                ('GUI-only partial',     '*.gui'),
                ('Legacy TernOO design', '*.ternoo'),
                ('All files',            '*.*'),
            ])
        if not path: return
        _save_to_path(path)

    # Directory where FlowCode saves/opens files (same dir as flowcode.py)
    _FC_DIR = os.path.dirname(os.path.abspath(__file__))

    # ── Bundle 12: migrate Phase 6D 'bindings' → 'signal_ids' on load ────────
    def _migrate_bindings_to_signal_ids(sym: dict) -> dict:
        """Convert a loaded widget's binding data to Bundle 12 signal_ids format.

        Handles three cases:
          1. 'signal_ids' present (Bundle 12 format) — use directly.
          2. 'bindings' present (Phase 6D format) — convert via signal_name_to_id.
          3. Neither — return empty dict.

        Phase 6D stored: {'clicked': {'dst_x': int, 'dst_y': int, 'symbolic': str}}
        Bundle 12 stores: {300: {'dst_x': int, 'dst_y': int}}

        The integer keys are stored as strings in JSON; int() conversion is applied
        when reading 'signal_ids'.  When reading 'bindings', the signal name is
        looked up via signal_name_to_id(); if the name is not found (truncated
        3-char Phase 6D form like 'cli'), the truncated form is tried as a prefix
        against all known signal names.
        """
        # Case 1: Bundle 12 native format
        raw_sig_ids = sym.get('signal_ids')
        if raw_sig_ids:
            result = {}
            for k, v in raw_sig_ids.items():
                try:
                    result[int(k)] = dict(v)
                except (ValueError, TypeError):
                    pass
            return result

        # Case 2: Phase 6D 'bindings' dict — migrate
        old_bindings = sym.get('bindings')
        if not old_bindings:
            return {}
        result = {}
        for sig_name, binfo in old_bindings.items():
            if not binfo:
                continue
            # Try direct lookup first
            sig_id = None
            try:
                _fs = _guic_get_signals_mod()
                sig_id = _fs.signal_name_to_id(sig_name)
                if sig_id is None:
                    # Try matching by prefix (Phase 6D truncated to 3 chars)
                    for entries in _fs.SIGNAL_REGISTRY.values():
                        for entry in entries:
                            if entry['name'].startswith(sig_name[:3]):
                                sig_id = entry['id']
                                break
                        if sig_id is not None:
                            break
            except Exception:
                pass
            if sig_id is not None:
                result[sig_id] = {'dst_x': binfo.get('dst_x', 0),
                                  'dst_y': binfo.get('dst_y', 0)}
            else:
                print(f"[Bundle12] Warning: could not migrate binding '{sig_name}' "
                      f"— no matching SIGNAL_* ID found; skipped.")
        return result

    def _guic_get_signals_mod():
        """Lazy-load flowcode_signals module."""
        import importlib.util as _ilu2
        _path2 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              '../5500fp/flowcode_signals.py')
        if not os.path.exists(_path2):
            _path2 = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  'flowcode_signals.py')
        _spec2 = _ilu2.spec_from_file_location('flowcode_signals', _path2)
        _mod2  = _ilu2.module_from_spec(_spec2)
        _spec2.loader.exec_module(_mod2)
        return _mod2

    def guic_do_open():
        # Phase 7c-0: updated title + extension filters
        path = filedialog.askopenfilename(
            parent=root, title='Open FlowCode program',
            initialdir=_FC_DIR,
            filetypes=[
                ('FlowCode files',       '*.fc *.flow *.gui *.ternoo'),
                ('FlowCode program',     '*.fc'),
                ('Flow-only partial',    '*.flow'),
                ('GUI-only partial',     '*.gui'),
                ('Legacy TernOO design', '*.ternoo'),
                ('All files',            '*.*'),
            ])
        if not path: return
        try:
            with open(path) as _of:
                tgui = json.load(_of)
            _ternoo_version = tgui.get('ternoo_version', tgui.get('tgui_version', '0.1'))
            if 'ternoo_version' not in tgui and 'tgui_version' not in tgui:
                guic_set_status("File is not a TernOO design — convert via tools/migrate_to_ternoo.py")
                return
            fc_state['widgets'].clear(); fc_state['edges'].clear()
            fc_state['selected'] = None; fc_state['next_id'] = 0
            fc_state['child_order'].clear(); fc_state['prop_committed'].clear()
            # Phase 6B: v0.2+ files carry word_stream alongside the dicts.
            # The dicts are authoritative on load; the saved words are used
            # as a projection-verification check after the stream is
            # regenerated (see the mismatch check below, 3 Jul 2026).
            for sym in tgui.get('symbols', []):
                wid  = sym['id']
                kind = sym.get('kind', 'gui_button')
                _dw, _dh = _GC_DEFAULT_SIZE.get(kind, (GW, GH))
                fc_state['widgets'][wid] = {
                    'id':          wid,
                    'kind':        kind,
                    'label':       sym.get('label', ''),
                    'x':           sym.get('x', 0),
                    'y':           sym.get('y', 0),
                    'w':           sym.get('w', _dw),
                    'h':           sym.get('h', _dh),
                    'parent_id':   sym.get('parent_id'),
                    'layout_mode': sym.get('layout_mode',
                                          _GC_LAYOUT_DEFAULTS.get(kind, 'absolute')),
                    'properties':  list(sym.get('properties', [])),
                    'signal_ids':  _migrate_bindings_to_signal_ids(sym),  # Bundle 12
                }
                # Phase 7c-1: preserve explicit name (incl. empty); legacy files
                # without a name key get a default assigned by ensure_unique_names.
                if 'name' in sym:
                    fc_state['widgets'][wid]['name'] = sym['name']
                fc_state['next_id'] = max(fc_state['next_id'], wid + 1)
            # Rebuild child_order from parent_id links (preserve file order)
            for wid, w in fc_state['widgets'].items():
                pid = w.get('parent_id')
                if pid is not None:
                    fc_state['child_order'].setdefault(pid, [])
                    if wid not in fc_state['child_order'][pid]:
                        fc_state['child_order'][pid].append(wid)
            for e in tgui.get('edges', []):
                fc_state['edges'].append({'src': e['src'], 'dst': e['dst']})
            # Phase 6C: load flow symbols and edges
            fc_state['flow_symbols'].clear()
            fc_state['flow_edges'].clear()
            fc_state['flow_next_id'] = 0
            for sym in tgui.get('flow_symbols', []):
                sid = sym['id']
                fc_state['flow_symbols'][sid] = {
                    'id':         sid,
                    'kind':       sym.get('kind', 'flow_process'),
                    'x':          sym.get('x', 0),
                    'y':          sym.get('y', 0),
                    'w':          sym.get('w', SYMBOL_W),
                    'h':          sym.get('h', SYMBOL_H),
                    'label':      sym.get('label', ''),
                    'properties': list(sym.get('properties', [])),
                    # Phase 7c-4: nesting (legacy files lack it → null = top level)
                    'parent_scope': sym.get('parent_scope'),
                }
                if 'name' in sym:   # Phase 7c-1: preserve explicit name
                    fc_state['flow_symbols'][sid]['name'] = sym['name']
                for _hook in ('entry_points', 'exit_points'):   # Phase 7c-4 stubs
                    if _hook in sym:
                        fc_state['flow_symbols'][sid][_hook] = list(sym[_hook])
                fc_state['flow_next_id'] = max(fc_state['flow_next_id'], sid + 1)
            fc_state['flow_scope'] = None   # Phase 7c-4: reset to top-level on load
            for e in tgui.get('flow_edges', []):
                _ne = {
                    'src':       e['src'],
                    'dst':       e['dst'],
                    'waypoints': [tuple(w) for w in e.get('waypoints', [])],
                    'condition': e.get('condition', ''),
                }
                if e.get('bound_port_name'):     # Phase 7c-4b port binding
                    _ne['bound_port_name'] = e['bound_port_name']
                fc_state['flow_edges'].append(_ne)
            fc_state['flow_selected'] = None
            fc_state['flow_multi_sel'].clear()
            # Stage 9-0: load Shell command widgets
            fc_state['cmd_widgets'].clear()
            fc_state['cmd_next_id'] = 0
            for cmd in tgui.get('cmd_symbols', []):
                cid = cmd['id']
                fc_state['cmd_widgets'][cid] = {
                    'id':         cid,
                    'kind':       cmd.get('kind', 'cmd_placeholder'),
                    'x':          cmd.get('x', 0),
                    'y':          cmd.get('y', 0),
                    'w':          cmd.get('w', CMD_W),
                    'h':          cmd.get('h', CMD_H),
                    'label':      cmd.get('label', ''),
                    'properties': list(cmd.get('properties', [])),
                }
                if 'name' in cmd:   # Phase 7c-1: preserve explicit name
                    fc_state['cmd_widgets'][cid]['name'] = cmd['name']
                fc_state['cmd_next_id'] = max(fc_state['cmd_next_id'], cid + 1)
            fc_state['cmd_selected'] = None
            fc_state['cmd_multi_sel'].clear()
            # Stage 9-2: load typed pipe edges (drop dangling endpoints)
            fc_state['cmd_edges'].clear()
            _cmd_ids = set(fc_state['cmd_widgets'])
            for e in tgui.get('cmd_edges', []):
                if e.get('src') in _cmd_ids and e.get('dst') in _cmd_ids:
                    fc_state['cmd_edges'].append({
                        'src':       e['src'],
                        'dst':       e['dst'],
                        'dst_param': e.get('dst_param', ''),
                    })
            fc_state['cmd_pipe_src'] = None
            # Stage 8-1: load Sheet cells
            fc_state['cells'].clear()
            fc_state['cell_next_id'] = 0
            for cell in tgui.get('cell_symbols', []):
                r = cell.get('row', 0); c = cell.get('col', 0)
                fc_state['cells'][(r, c)] = {
                    'id':         cell.get('id', 0),
                    'kind':       cell.get('kind', 'cell_text'),
                    'row':        r, 'col': c,
                    'label':      cell.get('label', _sheet_a1(r, c)),
                    'value':      cell.get('value', ''),
                    'properties': list(cell.get('properties', [])),
                }
                if 'name' in cell:
                    fc_state['cells'][(r, c)]['name'] = cell['name']
                if cell.get('bound_to_port'):    # Stage 8-6 cell↔port binding
                    fc_state['cells'][(r, c)]['bound_to_port'] = \
                        dict(cell['bound_to_port'])
                fc_state['cell_next_id'] = max(fc_state['cell_next_id'],
                                               cell.get('id', 0) + 1)
            fc_state['cell_sel'] = (0, 0)
            # Stage 8-9: load free-form regions + free cells
            fc_state['sheet_regions'].clear(); fc_state['free_cells'].clear()
            fc_state['region_next_id'] = 0
            for reg in tgui.get('sheet_regions', []):
                rid = reg.get('id', 0)
                fc_state['sheet_regions'][rid] = dict(reg)
                fc_state['region_next_id'] = max(fc_state['region_next_id'], rid + 1)
            for cell in tgui.get('free_cells', []):
                cid = cell.get('id', 0)
                fc_state['free_cells'][cid] = dict(cell)
                fc_state['cell_next_id'] = max(fc_state['cell_next_id'], cid + 1)
            # Phase 7c-1: assign default names to legacy widgets/symbols that
            # lack one, and disambiguate any duplicate non-empty names.
            fc_state['stream'].ensure_unique_names()
            # Phase 7c-2: reconcile name-based auto-wiring (legacy prompt if any
            # manual bindings don't match the convention).
            _guic_reconcile_autowire()
            # Phase 6B/6C: sync stream from widgets+flow content
            _guic_sync_stream()
            # 3 Jul 2026 — verified-projection check: the .fc carries the word
            # stream that was live at save; after rebuilding the dicts and
            # regenerating the stream, the two must agree.  A mismatch means
            # the dict→word bridge changed since the file was saved (or the
            # file was edited by hand) — surfaced loudly, never silently.
            _saved_words = tgui.get('word_stream')
            if _saved_words is not None:
                _regen = list(fc_state['stream'].words)
                if list(_saved_words) != _regen:
                    print(f"[FlowCode] word-stream projection mismatch on load: "
                          f"saved {len(_saved_words)} word(s), regenerated "
                          f"{len(_regen)} — dicts remain authoritative; the "
                          f"saved words reflect an older bridge encoding.")
                    guic_set_status(
                        f"Opened with word-stream mismatch (saved "
                        f"{len(_saved_words)} vs regenerated {len(_regen)} "
                        f"words) — see console")
            guic_set_mode('select')
            _current_design_path[0] = path   # Phase 7b-1: track for compiler header
            _name = os.path.basename(path)
            root.title(f"FlowCode v0.7.0 — TernOO-5500FP Visual IDE  [{_name}]")
            guic_set_status(f"Opened: {_name}")
            guic_layout_all()
            guic_redraw()
            _sh_redraw()   # Stage 9-0: refresh Shell canvas
            _sheet_recompute()   # Stage 8-3: evaluate loaded formulas
            _sheet_redraw()   # Stage 8-1: refresh Sheet grid
        except Exception as _oe:
            guic_set_status(f"Open failed: {_oe}")

    def guic_do_import():
        """Phase 7c-0: Import/merge a FlowCode file into the current session.
        Widget and symbol IDs are remapped to avoid collision with existing
        content; cross-references within the imported content are renumbered
        to match.  Cross-subsystem bindings are not restored (partial saves
        don't carry them)."""
        path = filedialog.askopenfilename(
            parent=root, title='Import FlowCode content',
            initialdir=_FC_DIR,
            filetypes=[
                ('FlowCode files',       '*.fc *.flow *.gui *.ternoo'),
                ('FlowCode program',     '*.fc'),
                ('Flow-only partial',    '*.flow'),
                ('GUI-only partial',     '*.gui'),
                ('Legacy TernOO design', '*.ternoo'),
                ('All files',            '*.*'),
            ])
        if not path: return
        try:
            with open(path) as _if:
                data = json.load(_if)
            if ('ternoo_version' not in data and 'tgui_version' not in data):
                guic_set_status("Not a FlowCode file — import cancelled"); return

            # ── Remap GUI widget IDs ──────────────────────────────────────
            next_wid = fc_state.get('next_id', 0)
            wid_map  = {}   # old_id → new_id
            for sym in data.get('symbols', []):
                old_id = sym['id']
                new_id = next_wid;  next_wid += 1
                wid_map[old_id] = new_id
                kind = sym.get('kind', 'gui_button')
                _dw, _dh = _GC_DEFAULT_SIZE.get(kind, (GW, GH))
                fc_state['widgets'][new_id] = {
                    'id':          new_id,
                    'kind':        kind,
                    'label':       sym.get('label', ''),
                    'x':           sym.get('x', 0),
                    'y':           sym.get('y', 0),
                    'w':           sym.get('w', _dw),
                    'h':           sym.get('h', _dh),
                    'parent_id':   wid_map.get(sym.get('parent_id')),
                    'layout_mode': sym.get('layout_mode',
                                          _GC_LAYOUT_DEFAULTS.get(kind, 'absolute')),
                    'properties':  list(sym.get('properties', [])),
                    'signal_ids':  _migrate_bindings_to_signal_ids(sym),
                }
                if 'name' in sym:   # Phase 7c-1: preserve name; deduped below
                    fc_state['widgets'][new_id]['name'] = sym['name']
            fc_state['next_id'] = next_wid

            # GUI edges — remap src/dst through wid_map
            for e in data.get('edges', []):
                ns = wid_map.get(e['src'])
                nd = wid_map.get(e['dst'])
                if ns is not None and nd is not None:
                    fc_state['edges'].append({'src': ns, 'dst': nd})

            # Rebuild child_order for newly imported widgets
            for wid, w in fc_state['widgets'].items():
                pid = w.get('parent_id')
                if pid is not None:
                    fc_state['child_order'].setdefault(pid, [])
                    if wid not in fc_state['child_order'][pid]:
                        fc_state['child_order'][pid].append(wid)

            # ── Remap flow symbol IDs ─────────────────────────────────────
            next_fsid = fc_state.get('flow_next_id', 0)
            fsid_map  = {}   # old_id → new_id
            for sym in data.get('flow_symbols', []):
                old_id = sym['id']
                new_id = next_fsid;  next_fsid += 1
                fsid_map[old_id] = new_id
                fc_state['flow_symbols'][new_id] = {
                    'id':         new_id,
                    'kind':       sym.get('kind', 'flow_process'),
                    'x':          sym.get('x', 0),
                    'y':          sym.get('y', 0),
                    'w':          sym.get('w', SYMBOL_W),
                    'h':          sym.get('h', SYMBOL_H),
                    'label':      sym.get('label', ''),
                    'properties': list(sym.get('properties', [])),
                    'parent_scope': sym.get('parent_scope'),   # Phase 7c-4
                }
                if 'name' in sym:   # Phase 7c-1: preserve name; deduped below
                    fc_state['flow_symbols'][new_id]['name'] = sym['name']
                for _hook in ('entry_points', 'exit_points'):
                    if _hook in sym:
                        fc_state['flow_symbols'][new_id][_hook] = list(sym[_hook])
            fc_state['flow_next_id'] = next_fsid

            # Flow edges — remap src/dst through fsid_map
            for e in data.get('flow_edges', []):
                ns = fsid_map.get(e['src'])
                nd = fsid_map.get(e['dst'])
                if ns is not None and nd is not None:
                    fc_state['flow_edges'].append({
                        'src':       ns,
                        'dst':       nd,
                        'waypoints': [tuple(wp) for wp in e.get('waypoints', [])],
                        'condition': e.get('condition', ''),
                    })

            # ── Stage 9-0: Remap Shell command-widget IDs ─────────────────
            next_cid = fc_state.get('cmd_next_id', 0)
            for cmd in data.get('cmd_symbols', []):
                new_id = next_cid;  next_cid += 1
                fc_state['cmd_widgets'][new_id] = {
                    'id':         new_id,
                    'kind':       cmd.get('kind', 'cmd_placeholder'),
                    'x':          cmd.get('x', 0),
                    'y':          cmd.get('y', 0),
                    'w':          cmd.get('w', CMD_W),
                    'h':          cmd.get('h', CMD_H),
                    'label':      cmd.get('label', ''),
                    'properties': list(cmd.get('properties', [])),
                }
                if 'name' in cmd:   # Phase 7c-1: preserve name; deduped below
                    fc_state['cmd_widgets'][new_id]['name'] = cmd['name']
            fc_state['cmd_next_id'] = next_cid

            # ── Stage 8-1: Import Sheet cells (skip cells already occupied) ──
            next_cell_id = fc_state.get('cell_next_id', 0)
            for cell in data.get('cell_symbols', []):
                r = cell.get('row', 0); c = cell.get('col', 0)
                if (r, c) in fc_state['cells']:
                    continue
                fc_state['cells'][(r, c)] = {
                    'id':         next_cell_id,
                    'kind':       cell.get('kind', 'cell_text'),
                    'row':        r, 'col': c,
                    'label':      cell.get('label', _sheet_a1(r, c)),
                    'value':      cell.get('value', ''),
                    'properties': list(cell.get('properties', [])),
                }
                if 'name' in cell:
                    fc_state['cells'][(r, c)]['name'] = cell['name']
                next_cell_id += 1
            fc_state['cell_next_id'] = next_cell_id

            # Phase 7c-1: fill defaults for unnamed imports and disambiguate
            # any names that collide with existing session content.
            fc_state['stream'].ensure_unique_names()
            # Phase 7c-2: reconcile name-based auto-wiring for imported content.
            _guic_reconcile_autowire()
            _guic_sync_stream()
            guic_redraw()
            redraw()
            _sh_redraw()   # Stage 9-0: refresh Shell canvas
            _sheet_recompute()   # Stage 8-3: evaluate loaded formulas
            _sheet_redraw()   # Stage 8-1: refresh Sheet grid
            n_gui  = len(data.get('symbols', []))
            n_flow = len(data.get('flow_symbols', []))
            n_cmd  = len(data.get('cmd_symbols', []))
            guic_set_status(
                f"Imported {n_gui} GUI widget{'s' if n_gui != 1 else ''}, "
                f"{n_flow} flow symbol{'s' if n_flow != 1 else ''}, "
                f"{n_cmd} command{'s' if n_cmd != 1 else ''} "
                f"from {os.path.basename(path)}")
        except Exception as _ie:
            guic_set_status(f"Import failed: {_ie}")

    # ── Undo / redo (D10 + Phase 6A word-level layer) ────────────────────────
    _guic_undo_stack      = []   # semantic: list of inverse action dicts, newest last
    _guic_redo_stack      = []   # semantic redo stack
    _guic_word_undo_stack = []   # Phase 6A: word-level WordStreamEdit list (Alt+Z)
    _guic_word_redo_stack = []   # Phase 6A: word-level redo (Alt+Y)
    _GC_UNDO_LIMIT      = 100
    _guic_undo_btn_ref    = _pal_undo_btn_ref   # palette Actions section (universal)
    _guic_redo_btn_ref    = _pal_redo_btn_ref   # palette Actions section (universal)
    # Phase 6A dev-mode assertion removed (D8): no parallel representation to assert.

    def _guic_action_label(action):
        """Human-readable label for the action the user just performed.

        The undo stack stores the INVERSE of what the user did, so the
        kind-to-label mapping is inverted here:
          stack 'delete' → user PLACED  → label "Place <kind>"
          stack 'place'  → user DELETED → label "Delete <kind>"
        """
        k = action.get('kind', 'edit')
        w  = action.get('widget', {}) or {}
        wid = action.get('widget_id') or action.get('id')
        gw  = fc_state['widgets'].get(wid, {}) if wid else {}
        kn  = (w.get('kind') or gw.get('kind') or '').replace('gui_', '').replace('_', ' ')
        _fk = action.get('sym', {}).get('kind', '').replace('flow_', '').title()
        label_map = {
            'delete':          f'Place {kn}'.strip(),
            'place':           f'Delete {kn}'.strip(),
            'delete_multi':    f'Delete {len(action.get("widgets", []))} widget(s)',
            'move':            'Move widget',
            'move_multi':      f'Move {len(action.get("origins", {}))} widget(s)',  # Phase 6B
            'resize':          'Resize widget',
            'reparent':        'Drop into container',
            'property_change': f'Change {action.get("property", "property")}',
            'binding_change':  f'Bind {action.get("signal", "signal")}',
            'reorder':         'Reorder children',
            # Phase 6C: FlowCode tab actions
            # (undo stack stores inverse; label describes what the user DID)
            'flow_remove':       f'Add {_fk}',          # undo=remove → user added
            'flow_add':          f'Remove {_fk}',        # undo=re-add → user removed
            'flow_edge_remove':  'Connect symbols',      # undo=remove → user connected
            'flow_edge_add':     'Disconnect symbols',   # undo=re-add → user disconnected
            'flow_move':         'Move symbol',
            'flow_prop_change':  f'Change {action.get("property", "property")}',
        }
        return label_map.get(k, k.replace('_', ' ').title())

    def _guic_sync_stream(label=''):
        """Recompute fc_state['stream'] from fc_state['widgets']+fc_state['edges'] (GHOST)
        and fc_state['flow_symbols']+fc_state['flow_edges'] (FlowCode tab).

        Phase 6C: GHOST words come first (preserving _word_map and identity
        coordinates from the GHOST bridge); flow words are appended after.
        Both sets of words are concatenated into one shared stream so the
        canonical word list contains all program content.
        The Phase 6A dev-mode parallel-rep assertion is removed (D8).
        """
        if fc_state.get('stream') is None:
            return

        # ── Phase 7c-2: refresh name-based auto-wiring before emitting bindings.
        # This is the single live hook for the whole rename cascade — every edit
        # (rename, create, delete, move) flows through here, so auto-wired
        # signal_ids always reflect the current widget/terminator name agreements.
        _aw_materialize(fc_state['stream'])

        combined: list = []

        # ── GHOST content ─────────────────────────────────────────────────
        if _ghost_to_meccano is not None:
            g_prog = _ghost_to_meccano(fc_state['widgets'], fc_state['edges'])
            combined.extend(g_prog.words)
            # Preserve GHOST identity + word-map (used by GHOST canvas)
            fc_state['stream']._word_map   = dict(getattr(g_prog, '_ghost_word_map', {}))
            fc_state['stream']._mmid_word  = g_prog.mmid.word
            fc_state['stream']._otree_word = g_prog.otree_word

        # ── FlowCode content (Phase 6C) ───────────────────────────────────
        if _flow_to_meccano is not None:
            f_prog = _flow_to_meccano(fc_state['flow_symbols'], fc_state['flow_edges'])
            combined.extend(f_prog.words)

        # ── Handler bindings (Phase 6D) ───────────────────────────────────
        if _build_handler_bindings is not None:
            combined.extend(_build_handler_bindings(
                fc_state['widgets'], fc_state['flow_symbols']))

        fc_state['stream'].words = combined
        fc_state['stream']._rebuild_indices()
        fc_state['stream']._notify()

    def _guic_reconcile_autowire():
        """Phase 7c-2 load reconciliation. Conforming manual bindings become
        auto-wired (regenerated from names); non-conforming legacy bindings raise
        the one-time prompt: Update names / Keep as-is / Cancel(=keep)."""
        stream = fc_state.get('stream')
        if stream is None:
            return
        nonconf = _aw_reconcile(stream)
        if nonconf:
            ans = messagebox.askyesnocancel(
                'Legacy handler bindings',
                f'This file has {len(nonconf)} manual handler binding(s) that '
                "don't match the name-based convention (Phase 7c-2).\n\n"
                'Yes    → Update names: rename the bound terminators to match\n'
                '          (they become auto-wired)\n'
                'No     → Keep as-is: preserve the manual bindings\n'
                'Cancel → Keep as-is',
                icon='question')
            if ans:               # Yes → Update names
                _aw_conform(stream)
            # No / Cancel → leave the manual bindings untouched

    def guic_update_undo_btns():
        """Grey-out Undo/Redo buttons; update tooltips with next semantic label."""
        ub = _guic_undo_btn_ref[0]
        rb = _guic_redo_btn_ref[0]
        if ub is not None:
            if _guic_undo_stack:
                lbl = _guic_undo_stack[-1].get('semantic_label', 'action')
                ub.config(state='normal', fg='#aaffaa')
                _guic_tooltip(ub, f'Undo: {lbl} (Ctrl+Z)')
            else:
                ub.config(state='disabled', fg=C['dim'])
                _guic_tooltip(ub, 'Undo (Ctrl+Z)')
        if rb is not None:
            if _guic_redo_stack:
                lbl = _guic_redo_stack[-1].get('semantic_label', 'action')
                rb.config(state='normal', fg='#aaffcc')
                _guic_tooltip(rb, f'Redo: {lbl} (Ctrl+Y)')
            else:
                rb.config(state='disabled', fg=C['dim'])
                _guic_tooltip(rb, 'Redo (Ctrl+Y)')

    def _guic_push_undo(action):
        """Push action dict to semantic stack; mirror as WordStreamEdit on word stack."""
        # Capture word state BEFORE this edit (stream is one step behind)
        before_words = list(fc_state['stream'].words) if fc_state.get('stream') else []

        # Annotate with semantic label
        action['semantic_label'] = _guic_action_label(action)

        # Semantic stack (drives Ctrl+Z/Y)
        _guic_undo_stack.append(action)
        if len(_guic_undo_stack) > _GC_UNDO_LIMIT:
            _guic_undo_stack.pop(0)
        _guic_redo_stack.clear()

        # Sync stream to new state; capture after-words
        _guic_sync_stream(action['semantic_label'])
        after_words = list(fc_state['stream'].words) if fc_state.get('stream') else []

        # Word-level stack (drives Alt+Z/Y)
        if WordStreamEdit is not None:
            edit = WordStreamEdit(
                op='replace', position=0,
                words_before=before_words,
                words_after=after_words,
                semantic_label=action['semantic_label'],
            )
            _guic_word_undo_stack.append(edit)
            if len(_guic_word_undo_stack) > _GC_UNDO_LIMIT:
                _guic_word_undo_stack.pop(0)
            _guic_word_redo_stack.clear()

        guic_update_undo_btns()

    def _guic_apply_action(act, opposite_stack):
        k = act['kind']
        if k == 'delete':
            w = act['widget'].copy()
            opposite_stack.append({'kind': 'place', 'widget': w})
            fc_state['widgets'].pop(w['id'], None)
            fc_state['edges'] = [e for e in fc_state['edges']
                            if e['src'] != w['id'] and e['dst'] != w['id']]
            if fc_state['selected'] == w['id']:
                fc_state['selected'] = None
            fc_state['multi_sel'].discard(w['id'])
            # Clean up child_order
            pid_d = w.get('parent_id')
            if pid_d is not None and pid_d in fc_state['child_order']:
                try: fc_state['child_order'][pid_d].remove(w['id'])
                except ValueError: pass
                guic_apply_layout(pid_d)
        elif k == 'place':
            w = act['widget'].copy()
            opposite_stack.append({'kind': 'delete', 'widget': w})
            fc_state['widgets'][w['id']] = w
            fc_state['next_id'] = max(fc_state['next_id'], w['id'] + 1)
            # Restore child_order and re-run layout
            pid_p = w.get('parent_id')
            if pid_p is not None:
                order = fc_state['child_order'].setdefault(pid_p, [])
                if w['id'] not in order:
                    order.append(w['id'])
                guic_apply_layout(pid_p)
        elif k == 'move':
            wid = act['id']
            if wid in fc_state['widgets']:
                w = fc_state['widgets'][wid]
                opposite_stack.append({'kind': 'move', 'id': wid,
                                       'x': w['x'], 'y': w['y']})
                w['x'] = act['x']; w['y'] = act['y']
        elif k == 'move_multi':
            # Phase 6B: single atomic group-move action (D9 lasso group-drag fix).
            # act['origins']: {wid: (old_x, old_y)} — positions BEFORE the move.
            # Inverse: capture current positions, then restore origins.
            cur_pos = {}
            for wid, (ox, oy) in act['origins'].items():
                w = fc_state['widgets'].get(wid)
                if w:
                    cur_pos[wid] = (w['x'], w['y'])
                    w['x'] = ox; w['y'] = oy
            opposite_stack.append({'kind': 'move_multi', 'origins': cur_pos})
        elif k == 'resize':
            wid = act['id']
            if wid in fc_state['widgets']:
                w = fc_state['widgets'][wid]
                opposite_stack.append({'kind': 'resize', 'id': wid,
                                       'x': w['x'], 'y': w['y'],
                                       'w': w['w'], 'h': w['h']})
                w['x'] = act['x']; w['y'] = act['y']
                w['w'] = act['w']; w['h'] = act['h']
        elif k == 'reparent':
            wid = act['id']
            if wid in fc_state['widgets']:
                w = fc_state['widgets'][wid]
                opposite_stack.append({'kind': 'reparent', 'id': wid,
                                       'parent_id': w['parent_id'],
                                       'x': w['x'], 'y': w['y']})
                w['parent_id'] = act['parent_id']
                w['x'] = act['x']; w['y'] = act['y']
        elif k == 'delete_multi':
            restored = []
            for wc in act['widgets']:
                w = wc.copy()
                fc_state['widgets'][w['id']] = w
                fc_state['next_id'] = max(fc_state['next_id'], w['id'] + 1)
                restored.append(w)
            opposite_stack.append({'kind': 'delete_multi', 'widgets': restored})
        elif k == 'property_change':
            wid  = act['widget_id']
            pname = act['property']
            old_v = act['old_value']
            new_v = act['new_value']
            if wid in fc_state['widgets']:
                w = fc_state['widgets'][wid]
                # Capture current value for the inverse action
                cur = _guic_get_prop_value(w, pname)
                opposite_stack.append({'kind': 'property_change', 'widget_id': wid,
                                       'property': pname,
                                       'old_value': cur, 'new_value': old_v})
                _guic_set_prop_value(w, pname, old_v)
                # Also update committed state
                fc_state['prop_committed'].setdefault(wid, {})[pname] = old_v
                # Trigger layout if layout_mode changed
                if pname == 'layout_mode':
                    guic_apply_layout(wid)
                elif pname in ('w', 'h', 'x', 'y'):
                    pid = w.get('parent_id')
                    if pid is not None:
                        guic_apply_layout(pid)
        elif k == 'reorder':
            pid = act['parent_id']
            order = fc_state['child_order'].get(pid, [])
            opposite_stack.append({'kind': 'reorder', 'parent_id': pid,
                                   'order': list(order)})
            fc_state['child_order'][pid] = list(act['order'])
            guic_apply_layout(pid)
        elif k == 'binding_change':
            # Bundle 12: undo/redo a signal binding change (uses signal_id: int)
            wid       = act['widget_id']
            signal_id = act['signal_id']   # int SIGNAL_* constant
            old_b     = act['old_binding']
            w = fc_state['widgets'].get(wid)
            if w is not None:
                cur_b = (w.get('signal_ids') or {}).get(signal_id)
                opposite_stack.append({'kind': 'binding_change', 'widget_id': wid,
                                       'signal_id': signal_id, 'old_binding': cur_b})
                sig_ids = w.setdefault('signal_ids', {})
                if old_b is None:
                    sig_ids.pop(signal_id, None)
                else:
                    sig_ids[signal_id] = old_b
        # ── Phase 6C: FlowCode tab undo/redo actions ─────────────────────────
        elif k == 'flow_remove':
            # Undo of user adding a symbol → remove it
            sym = act['sym'].copy()
            opposite_stack.append({'kind': 'flow_add', 'sym': sym})
            fc_state['flow_symbols'].pop(sym['id'], None)
            fc_state['flow_edges'] = [e for e in fc_state['flow_edges']
                                 if e['src'] != sym['id'] and e['dst'] != sym['id']]
            if fc_state['flow_selected'] == sym['id']:
                fc_state['flow_selected'] = None
            fc_state['flow_multi_sel'].discard(sym['id'])
        elif k == 'flow_add':
            # Undo of user removing a symbol → re-add it
            sym = act['sym'].copy()
            opposite_stack.append({'kind': 'flow_remove', 'sym': sym})
            fc_state['flow_symbols'][sym['id']] = sym
            fc_state['flow_next_id'] = max(fc_state['flow_next_id'], sym['id'] + 1)
        elif k == 'flow_edge_remove':
            # Undo of user adding an edge → remove it
            edge = act['edge'].copy()
            opposite_stack.append({'kind': 'flow_edge_add', 'edge': edge})
            fc_state['flow_edges'] = [e for e in fc_state['flow_edges']
                                 if not (e['src'] == edge['src'] and
                                         e['dst'] == edge['dst'])]
        elif k == 'flow_edge_add':
            # Undo of user removing an edge → re-add it
            edge = act['edge'].copy()
            opposite_stack.append({'kind': 'flow_edge_remove', 'edge': edge})
            fc_state['flow_edges'].append(edge)
        elif k == 'flow_move':
            sid = act['id']
            if sid in fc_state['flow_symbols']:
                s = fc_state['flow_symbols'][sid]
                opposite_stack.append({'kind': 'flow_move', 'id': sid,
                                       'x': s['x'], 'y': s['y']})
                s['x'] = act['x']; s['y'] = act['y']
        elif k == 'flow_prop_change':
            sid = act.get('sym_id')
            if sid is not None and sid in fc_state['flow_symbols']:
                s = fc_state['flow_symbols'][sid]
                cur = _guic_get_prop_value(s, act['property'])
                opposite_stack.append({'kind': 'flow_prop_change', 'sym_id': sid,
                                       'property': act['property'],
                                       'old_value': cur,
                                       'new_value': act.get('old_value')})
                _guic_set_prop_value(s, act['property'], act.get('old_value'))

    def guic_undo():
        if not _guic_undo_stack: guic_set_status("Nothing to undo"); return
        _guic_apply_action(_guic_undo_stack.pop(), _guic_redo_stack)
        _guic_sync_stream()   # Phase 6A: keep stream in lockstep after semantic undo
        guic_rebuild_prop_panel()
        guic_redraw()
        guic_update_undo_btns()

    def guic_redo():
        if not _guic_redo_stack: guic_set_status("Nothing to redo"); return
        _guic_apply_action(_guic_redo_stack.pop(), _guic_undo_stack)
        _guic_sync_stream()   # Phase 6A: keep stream in lockstep after semantic redo
        guic_rebuild_prop_panel()
        guic_redraw()
        guic_update_undo_btns()

    def guic_undo_word():
        """Phase 6A: Alt+Z — word-level undo (delegates to semantic undo 1:1)."""
        guic_undo()

    def guic_redo_word():
        """Phase 6A: Alt+Y — word-level redo (delegates to semantic redo 1:1)."""
        guic_redo()

    # ── Property helpers (read/write from widget dict or properties list) ─────
    def _guic_get_prop_value(w, name):
        """Get property value from widget dict (common) or properties list."""
        if name in ('name', 'x', 'y', 'w', 'h', 'label', 'layout_mode'):
            return w.get(name)
        for p in w.get('properties', []):
            if p['name'] == name:
                return p['value']
        return None

    def _guic_set_prop_value(w, name, value):
        """Set property value in widget dict (common) or properties list."""
        if name in ('name', 'x', 'y', 'w', 'h', 'label', 'layout_mode'):
            w[name] = value
        else:
            for p in w.get('properties', []):
                if p['name'] == name:
                    p['value'] = value
                    return
            w.setdefault('properties', []).append({'name': name, 'value': value})

    # ── Layout algorithm (Stage 4) ────────────────────────────────────────────
    def guic_children_of(parent_id):
        """Return ordered list of direct child widget dicts for parent_id."""
        order = fc_state['child_order'].get(parent_id, [])
        # Include any children not yet in order (e.g. loaded without order)
        extra = [wid for wid, w in fc_state['widgets'].items()
                 if w.get('parent_id') == parent_id and wid not in order]
        full_order = order + extra
        return [fc_state['widgets'][wid] for wid in full_order if wid in fc_state['widgets']]

    def guic_apply_layout(container_id):
        """Apply the container's layout_mode to position its direct children.

        Modifies children's x, y, w, h in-place (relative to parent centre).
        No undo entries pushed — the triggering action owns the undo snapshot.
        """
        ct = fc_state['widgets'].get(container_id)
        if ct is None: return
        mode = ct.get('layout_mode', _GC_LAYOUT_DEFAULTS.get(ct['kind'], 'absolute'))
        if mode == 'absolute': return  # no-op

        children = guic_children_of(container_id)
        N = len(children)
        if N == 0: return

        W = ct.get('w', GW)
        H = ct.get('h', GH)
        PAD = 4

        if mode == 'hbox':
            child_w = max(_GC_MIN_SIZE, (W - 2*PAD - PAD*(N-1)) // N)
            child_h = max(_GC_MIN_SIZE, H - 2*PAD)
            for i, ch in enumerate(children):
                ch['x'] = int(-W/2 + PAD + i*(child_w + PAD) + child_w/2)
                ch['y'] = 0
                ch['w'] = child_w; ch['h'] = child_h

        elif mode == 'vbox':
            child_w = max(_GC_MIN_SIZE, W - 2*PAD)
            child_h = max(_GC_MIN_SIZE, (H - 2*PAD - PAD*(N-1)) // N)
            for i, ch in enumerate(children):
                ch['x'] = 0
                ch['y'] = int(-H/2 + PAD + i*(child_h + PAD) + child_h/2)
                ch['w'] = child_w; ch['h'] = child_h

        elif mode == 'grid':
            cols = max(1, math.ceil(math.sqrt(N)))
            rows = max(1, math.ceil(N / cols))
            cell_w = max(_GC_MIN_SIZE, (W - PAD*(cols+1)) // cols)
            cell_h = max(_GC_MIN_SIZE, (H - PAD*(rows+1)) // rows)
            for idx, ch in enumerate(children):
                r, c = divmod(idx, cols)
                ch['x'] = int(-W/2 + PAD*(c+1) + c*cell_w + cell_w/2)
                ch['y'] = int(-H/2 + PAD*(r+1) + r*cell_h + cell_h/2)
                ch['w'] = cell_w; ch['h'] = cell_h

        elif mode == 'stacked':
            # First child covers content area; others hidden (not drawn)
            if children:
                ch = children[0]
                ch['x'] = 0; ch['y'] = 0
                ch['w'] = max(_GC_MIN_SIZE, W - 2*PAD)
                ch['h'] = max(_GC_MIN_SIZE, H - 2*PAD)

    def guic_layout_all():
        """Apply layout to every container widget on the canvas."""
        for wid, w in fc_state['widgets'].items():
            if w['kind'] in CONTAINER_KINDS:
                guic_apply_layout(wid)

    def _guic_action_btn(parent, label, cmd, fg):
        b = tk.Button(parent, text=label, command=cmd,
                      bg=C['pal_btn'], fg=fg,
                      font=('Monospace', 8), relief='flat', bd=0,
                      padx=4, pady=3, cursor='hand2', anchor='w')
        b.pack(fill='x', padx=4, pady=1)
        return b

    _guic_active_tip = [None]   # shared ref — destroyed on tab switch

    def _guic_tooltip(widget, text):
        """Attach a simple hover tooltip to a tkinter widget."""
        tip = [None]
        def _show(e):
            # Destroy any lingering tip from a previous widget
            if _guic_active_tip[0] and _guic_active_tip[0] is not tip[0]:
                try: _guic_active_tip[0].destroy()
                except Exception: pass
            tip[0] = tk.Toplevel(widget)
            tip[0].wm_overrideredirect(True)
            tip[0].wm_geometry(f"+{e.x_root+12}+{e.y_root+16}")
            tk.Label(tip[0], text=text, bg='#222', fg='#eee',
                     font=('Monospace', 7), relief='flat',
                     padx=4, pady=2).pack()
            _guic_active_tip[0] = tip[0]
        def _hide(e):
            if tip[0]: tip[0].destroy(); tip[0] = None
            if _guic_active_tip[0] is tip[0]: _guic_active_tip[0] = None
        widget.bind('<Enter>', _show)
        widget.bind('<Leave>', _hide)

    # ── Bundle 17 A7: guic_pal buttons removed — now in universal sidebar ───────
    # Select/Connect/Delete → _build_gui_tools() in tab-aware tools section
    # Suggest/Clear/Undo/Redo → universal Actions section in palette_frame
    # Widget palette → _build_gui_tools() scrollable section in tools frame
    guic_update_undo_btns()   # initialise disabled/enabled state on palette buttons

    # ── Drawing ───────────────────────────────────────────────────────────────
    def guic_draw_grid():
        cw = guic.winfo_width() or 860; ch = guic.winfo_height() or 660
        z  = _gc_view['zoom']
        gstep = GRID * z
        if gstep < 4: return   # skip grid when too zoomed out
        ox = (-_gc_view['sx'] * z) % gstep
        oy = (-_gc_view['sy'] * z) % gstep
        x = ox
        while x <= cw:
            guic.create_line(int(x), 0, int(x), ch, fill=C['grid'])
            x += gstep
        y = oy
        while y <= ch:
            guic.create_line(0, int(y), cw, int(y), fill=C['grid'])
            y += gstep

    def _guic_render_words(words, L, T, R, B, col, bor, txt, dim):
        # ── CC-09 geometry word interpreter ───────────────────────────────────
        # Added: 01 Jun 2026, Adelaide  Author: Stevo + Claude
        # Purpose: Render TernOO RNODE/RLINE/RPOINT sequences on guic Tkinter canvas
        # Companion: private/TernOO-5500FP-Companion.md § G6 (CC-09)
        W = R - L; H = B - T

        def px(nx): return L + nx * W
        def py(ny): return T + ny * H

        def _rc(role):
            """(fill, outline) for a geometry role."""
            if role == 'body':                  return col,            bor
            if role in ('titlebar', 'header'):  return C['canvas'],   col
            if role in ('strip', 'tab'):        return C['pal_btn'],  col
            if role in ('row', 'cell'):         return '',             col
            if role in ('button', 'input', 'dropdown'): return C['pal_btn'], dim
            if role == 'thumb':                 return dim,            col
            if role == 'fill':                  return txt,            ''
            if role == 'ctrl_close':            return '#cc4444',      ''
            if role == 'ctrl_min':              return '#ccaa44',      ''
            if role == 'ctrl_max':              return '#44aa44',      ''
            if role in ('radio', 'check'):      return txt,            dim
            if role == 'spinner':               return '',             col
            if role in ('icon',):               return C['canvas'],    dim
            return C['pal_btn'], dim

        def _lc(role):
            """Line colour for a geometry role."""
            if role == 'cursor':  return txt
            if role == 'cross':   return dim
            if role == 'track':   return dim
            return col

        for word in words:
            op = word['op']
            if op == 'RENDER':
                break
            role  = word.get('role',  '')
            shape = word.get('shape', 'rect')

            if op == 'RNODE':
                x0 = px(word['x0']); y0 = py(word['y0'])
                x1 = px(word['x1']); y1 = py(word['y1'])
                fc, oc = _rc(role)
                if shape in ('rect', 'square'):
                    guic.create_rectangle(x0, y0, x1, y1,
                                        fill=fc, outline=oc, width=1)
                elif shape == 'circle':
                    guic.create_oval(x0, y0, x1, y1,
                                   fill=fc, outline=oc, width=1)
                elif shape == 'tri':
                    span_x = word['x1'] - word['x0']
                    span_y = word['y1'] - word['y0']
                    cx2 = (x0 + x1) / 2; cy2 = (y0 + y1) / 2
                    if span_x >= span_y:
                        pts = [x0, y0, x1, y0, cx2, y1]   # down-pointing
                    else:
                        pts = [x0, y0, x1, cy2, x0, y1]   # right-pointing
                    guic.create_polygon(pts, fill=fc, outline='')

            elif op == 'RLINE':
                x0 = px(word['x0']); y0 = py(word['y0'])
                x1 = px(word['x1']); y1 = py(word['y1'])
                guic.create_line(x0, y0, x1, y1, fill=_lc(role), width=1)

            elif op == 'RPOINT':
                cx2 = px(word['x']); cy2 = py(word['y'])
                r2 = 2
                guic.create_oval(cx2-r2, cy2-r2, cx2+r2, cy2+r2,
                               fill=txt, outline='')

    def guic_abs_pos(w):
        """Return absolute (x, y) of widget w, walking up the parent chain."""
        x, y = w['x'], w['y']
        pid = w.get('parent_id')
        visited = set()
        while pid is not None:
            if pid in visited: break
            visited.add(pid)
            p = fc_state['widgets'].get(pid)
            if p is None: break
            px, py = guic_abs_pos(p)
            x += px; y += py
            break  # relative to direct parent only; parent already computes its own chain
        return x, y

    def guic_handle_positions(w):
        """Return {name: (cx,cy)} for the 8 resize handles of widget w."""
        ax, ay = guic_abs_pos(w)
        ww, wh = w.get('w', GW), w.get('h', GH)
        L, R = ax - ww // 2, ax + ww // 2
        T, B = ay - wh // 2, ay + wh // 2
        mx, my = (L + R) // 2, (T + B) // 2
        return {
            'NW': (L, T), 'N': (mx, T), 'NE': (R, T),
            'W':  (L, my),               'E':  (R, my),
            'SW': (L, B), 'S': (mx, B), 'SE': (R, B),
        }

    def guic_handle_at(x, y):
        """Return (widget, handle_name) if (x,y) hits a handle on the selected widget."""
        sel = fc_state['selected']
        if sel is None or sel not in fc_state['widgets']: return None, None
        if len(fc_state['multi_sel']) > 1: return None, None  # handles only for single selection
        w = fc_state['widgets'][sel]
        hs = 5  # hit radius (6×6 handle, ±5 px)
        for name, (hx, hy) in guic_handle_positions(w).items():
            if abs(x - hx) <= hs and abs(y - hy) <= hs:
                return w, name
        return None, None

    def guic_is_descendant(wid, ancestor_id):
        """Return True if wid is ancestor_id or a descendant of it."""
        cur = wid
        visited = set()
        while cur is not None:
            if cur == ancestor_id: return True
            if cur in visited: break
            visited.add(cur)
            p = fc_state['widgets'].get(cur)
            if p is None: break
            cur = p.get('parent_id')
        return False

    def guic_container_at(x, y, exclude_id):
        """Return topmost CONTAINER_KIND widget at (x,y), excluding exclude_id subtree."""
        for w in reversed(list(fc_state['widgets'].values())):
            if w['id'] == exclude_id: continue
            if guic_is_descendant(w['id'], exclude_id): continue
            if w['kind'] not in CONTAINER_KINDS: continue
            ax, ay = guic_abs_pos(w)
            ww, wh = w.get('w', GW), w.get('h', GH)
            if (ax - ww // 2 <= x <= ax + ww // 2 and
                    ay - wh // 2 <= y <= ay + wh // 2):
                return w
        return None

    def guic_draw_widget(w):
        # ── CC-09 geometry renderer ────────────────────────────────────────────
        sel  = (w['id'] == fc_state['selected'])
        col  = _guic_color.get(w['kind'], C['pal_btn'])
        bor  = C['selected'] if sel else C['pal_border']
        lw   = 3 if sel else 1
        x, y = guic_abs_pos(w)
        ww, wh = w.get('w', GW), w.get('h', GH)
        hw, hh = ww // 2, wh // 2
        L, R, T, B = x - hw, x + hw, y - hh, y + hh
        kind = w['kind']
        txt  = C['text']; dim = C['dim']

        # ── Bundle 18: viewport transform (design → screen) ───────────────────
        _xs2, _ys2 = _gc_d2s(x, y)
        z    = _gc_view['zoom']
        x, y = int(_xs2), int(_ys2)
        hw   = int(hw * z);  hh   = int(hh * z)
        L    = x - hw;       R    = x + hw
        T    = y - hh;       B    = y + hh
        _gft = max(5, int(8 * z))   # main widget font size
        _gfs = max(4, int(7 * z))   # sub/type label font size
        # ─────────────────────────────────────────────────────────────────────

        # Container/layout types get a dashed background before geometry
        if kind in ('gui_box', 'gui_grid', 'gui_canvas', 'gui_stack',
                    'gui_overlay', 'gui_revealer'):
            guic.create_rectangle(L, T, R, B, fill=C['canvas'],
                                outline=bor, width=lw, dash=(5, 3))

        # Geometry word sequence → canvas primitives
        if _widget_geometry_mod is not None:
            words = _widget_geometry_mod.get_geometry(kind)
        else:
            words = [{'op': 'RNODE', 'shape': 'rect', 'role': 'body',
                      'x0': 0, 'y0': 0, 'x1': 1, 'y1': 1}, {'op': 'RENDER'}]
        _guic_render_words(words, L, T, R, B, col, bor, txt, dim)

        # Label overlay — render w['label'] on the canvas tile (live-update path)
        # The geometry renderer draws shapes only; labels must be composited here.
        _label_text = w.get('label', '')
        # Stage 8-4: a read-only cell binding overrides the displayed text.
        _bind_cell = _guic_get_prop_value(w, 'bind_value_to')
        if _bind_cell:
            _bound_val = _sheet_value_by_name(_bind_cell)
            if _bound_val is not None:
                _label_text = _bound_val
        if _label_text:
            guic.create_text(x, y, text=str(_label_text)[:20],
                           fill=txt, font=('Monospace', _gft), anchor='center')

        # Kind-specific string properties overlay (title, placeholder, etc.)
        for _kp in w.get('properties', []):
            _kpname = _kp.get('name', '')
            _kpval  = str(_kp.get('value', '') or '')
            if not _kpval: continue
            if _kpname == 'title':
                # Title bar text — top strip of the widget tile
                guic.create_text(x, T + max(3, int(7 * z)), text=_kpval[:22],
                               fill=txt, font=('Monospace', _gfs, 'bold'), anchor='center')
            elif _kpname == 'placeholder':
                # Placeholder — dimmed italic centred (only visible when label absent)
                guic.create_text(x, y, text=_kpval[:20],
                               fill=dim, font=('Monospace', _gfs, 'italic'), anchor='center')

        # Type label below tile
        guic.create_text(x, B + max(4, int(9 * z)), text=kind.replace('gui_', ''),
                       fill=dim, font=('Monospace', _gfs))

        # Drop-target highlight (thick dashed border when this widget is the drop target)
        if fc_state.get('drop_target') == w['id']:
            guic.create_rectangle(L - 3, T - 3, R + 3, B + 3,
                                outline=C['selected'], width=3, fill='', dash=(4, 2))

        # Resize handles — 8 small squares, only for single-selected widget (D3)
        if sel and len(fc_state['multi_sel']) <= 1:
            _hs = max(2, int(3 * z))   # handle half-size, scales with zoom
            for hx_d, hy_d in guic_handle_positions(w).values():
                hxs, hys = _gc_d2s(hx_d, hy_d)
                guic.create_rectangle(int(hxs) - _hs, int(hys) - _hs,
                                    int(hxs) + _hs, int(hys) + _hs,
                                    fill=C['selected'], outline=C['canvas'], width=1)

        # ── sea monkeys removed CC-09 — geometry renderer above is the renderer ──
        kind = '_dead_'   # sentinel: dead-codes all elif branches below

        if False:
            pass

        elif kind in ('gui_dialog','gui_messagedialog','gui_aboutdialog','gui_assistant'):
            guic.create_rectangle(L, T, R, B, fill='#1a1008', outline=bor, width=lw)
            guic.create_rectangle(L, T, R, T+13, fill='#2a1a0a', outline=bor, width=1)
            guic.create_text(x, T+6, text=w.get('label','Dialog')[:18],
                           fill=txt, font=('Monospace',7,'bold'))
            guic.create_oval(R-8,T+3,R-3,T+9, fill='#cc4444', outline='')
            bw = 28
            guic.create_rectangle(R-bw-4,B-14,R-4,B-4, fill='#0f3060', outline=dim, width=1)
            guic.create_text(R-bw//2-4,B-9, text='OK', fill=txt, font=('Monospace',7))
            guic.create_rectangle(R-bw*2-8,B-14,R-bw-8,B-4, fill='#3a1010', outline=dim, width=1)
            guic.create_text(R-bw*3//2-8,B-9, text='Cancel', fill=txt, font=('Monospace',7))

        elif kind == 'gui_button':
            guic.create_rectangle(L+2,T+6,R-2,B-6, fill='#1a4a7a', outline=dim, width=1)
            guic.create_rectangle(L+2,T+6,R-2,T+10, fill='#2a5a8a', outline='')
            guic.create_rectangle(L+2,B-10,R-2,B-6, fill='#0d2a4a', outline='')
            guic.create_text(x, y, text=w.get('label','Button')[:14],
                           fill=txt, font=('Monospace',8,'bold'))

        elif kind in ('gui_toggle','gui_link','gui_menubutton'):
            guic.create_rectangle(L+2,T+6,R-2,B-6, fill='#2a1a5a', outline=dim, width=1)
            guic.create_text(x, y, text=w.get('label',kind.replace('gui_',''))[:14],
                           fill='#aaffcc', font=('Monospace',8))

        elif kind == 'gui_check':
            cx = L+10
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_rectangle(cx-7,y-7,cx+7,y+7, fill='#070d1a', outline=dim, width=1)
            guic.create_line(cx-4,y,cx,y+5,cx+6,y-5, fill='#44cc44', width=2)
            guic.create_text(cx+16+(hw//2),y, text=w.get('label','Check')[:10],
                           fill=txt, font=('Monospace',8))

        elif kind == 'gui_radio':
            cx = L+10
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_oval(cx-7,y-7,cx+7,y+7, fill='#070d1a', outline=dim, width=1)
            guic.create_oval(cx-3,y-3,cx+3,y+3, fill='#4a9eff', outline='')
            guic.create_text(cx+16+(hw//2),y, text=w.get('label','Radio')[:10],
                           fill=txt, font=('Monospace',8))

        elif kind == 'gui_switch':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            pw,ph = 40,18
            ox,oy = x-4, y
            guic.create_oval(ox-pw//2,oy-ph//2,ox-pw//2+ph,oy+ph//2, fill='#1a6b3a',outline=dim)
            guic.create_rectangle(ox-pw//2+ph//2,oy-ph//2,ox+pw//2-ph//2,oy+ph//2, fill='#1a6b3a',outline=dim)
            guic.create_oval(ox+pw//2-ph,oy-ph//2,ox+pw//2,oy+ph//2, fill='#1a6b3a',outline=dim)
            guic.create_oval(ox+pw//2-ph+2,oy-ph//2+2,ox+pw//2-2,oy+ph//2-2, fill='#e0e0e0',outline='')
            guic.create_text(ox+pw//2+14,oy, text='ON', fill='#44cc44', font=('Monospace',7,'bold'))

        elif kind == 'gui_entry':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_rectangle(L+4,T+10,R-4,B-10, fill='#050a12', outline=dim, width=1)
            guic.create_line(L+10,y,L+50,y, fill='#2a3050', width=1)
            guic.create_line(L+10,T+13,L+10,B-13, fill=C['pal_border'], width=1)

        elif kind == 'gui_searchentry':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_rectangle(L+4,T+10,R-4,B-10, fill='#050a12', outline=dim, width=1)
            guic.create_oval(L+8,T+13,L+16,B-13, outline=dim, width=1)
            guic.create_line(L+15,B-14,L+19,B-10, fill=dim, width=1)
            guic.create_line(L+22,y,L+55,y, fill='#2a3050', width=1)

        elif kind == 'gui_textview':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_rectangle(L+3,T+4,R-3,B-4, fill='#050a12', outline=dim, width=1)
            for i in range(3):
                yl = T+12+i*10
                guic.create_line(L+7,yl, R-7-(i*9)%18,yl, fill='#2a3050', width=1)

        elif kind == 'gui_label':
            guic.create_rectangle(L,T,R,B, fill=col, outline='', width=0)
            guic.create_text(x, y, text=w.get('label','Label')[:20],
                           fill=txt, font=('Monospace',9))

        elif kind == 'gui_image':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            inn = 8
            guic.create_rectangle(L+inn,T+inn,R-inn,B-inn, fill='#0a1220', outline=dim, width=1)
            mx,my = x, B-inn-4
            guic.create_polygon(mx-14,my,mx,T+inn+6,mx+14,my, fill=dim, outline='')
            guic.create_polygon(mx+4,my,mx+18,T+inn+12,mx+28,my, fill='#1a2a3a', outline='')
            guic.create_oval(L+inn+4,T+inn+4,L+inn+12,T+inn+12, fill='#ccaa00', outline='')

        elif kind == 'gui_progress':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_rectangle(L+6,y-7,R-6,y+7, fill='#050a12', outline=dim, width=1)
            guic.create_rectangle(L+6,y-7,L+6+(R-L-12)//2,y+7, fill='#1a6b3a', outline='')
            guic.create_text(x, y, text='50%', fill=txt, font=('Monospace',7))

        elif kind == 'gui_level':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            seg_w = (R-L-10)//5
            for i in range(5):
                sx2 = L+5+i*seg_w
                fc2 = '#1a6b3a' if i<3 else '#ccaa00' if i<4 else '#cc3333'
                guic.create_rectangle(sx2+1,y-6,sx2+seg_w-1,y+6, fill=fc2, outline='')

        elif kind == 'gui_scale':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_line(L+10,y,R-10,y, fill=dim, width=3)
            tx = x-10
            guic.create_oval(tx-7,y-7,tx+7,y+7, fill='#1a5a8a', outline=C['pal_border'], width=1)

        elif kind in ('gui_box','gui_grid','gui_canvas'):
            guic.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw, dash=(5,3))
            badge2 = kind.replace('gui_','')
            guic.create_text(x,T+9, text=f'‹ {badge2} ›', fill=dim, font=('Monospace',7,'italic'))
            if kind in ('gui_box','gui_grid'):
                for i in range(1,3):
                    gx = L+(R-L)*i//3
                    guic.create_line(gx,T+16,gx,B-4, fill=dim, width=1, dash=(2,4))

        elif kind in ('gui_frame','gui_bin','gui_alignment','gui_aspectframe',
                      'gui_handlebox','gui_eventbox'):
            guic.create_rectangle(L,T,R,B, fill='#060b10', outline=dim, width=1)
            guic.create_rectangle(L,T,R,B, fill='', outline=bor, width=lw, dash=(4,3))
            guic.create_text(L+10,T+1, text=w.get('label','frame')[:12],
                           fill=dim, font=('Monospace',7), bg='#060b10')

        elif kind == 'gui_notebook':
            guic.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw)
            for i,tab_lbl in enumerate(['Tab 1','Tab 2']):
                tx0=L+i*48+2; tx1=tx0+46; ty0=T; ty1=T+14
                guic.create_rectangle(tx0,ty0,tx1,ty1,
                                     fill='#1a3a5a' if i==0 else '#0a1a2a', outline=dim, width=1)
                guic.create_text((tx0+tx1)//2,(ty0+ty1)//2, text=tab_lbl, fill=txt, font=('Monospace',7))
            guic.create_rectangle(L,T+13,R,B, fill='#07101e', outline=dim, width=1)

        elif kind == 'gui_paned':
            guic.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw)
            mid = y
            guic.create_rectangle(L+3,T+3,R-3,mid-2, fill='#07101e', outline=dim, width=1, dash=(3,3))
            guic.create_rectangle(L+3,mid+2,R-3,B-3, fill='#07101e', outline=dim, width=1, dash=(3,3))
            guic.create_line(L+3,mid,R-3,mid, fill=dim, width=2)

        elif kind == 'gui_scrolled':
            guic.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw)
            guic.create_rectangle(R-10,T+2,R-2,B-2, fill='#0a1220', outline=dim, width=1)
            guic.create_rectangle(R-10,T+2,R-2,T+18, fill='#1a3a5a', outline='')
            guic.create_rectangle(L+2,T+2,R-12,B-2, fill='#07101e', outline=dim, width=1, dash=(3,3))

        elif kind == 'gui_expander':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_text(L+9,T+10, text='▶', fill=C['pal_border'], font=('Monospace',9), anchor='w')
            guic.create_text(L+22,T+10, text=w.get('label','Expander')[:14],
                           fill=txt, font=('Monospace',8), anchor='w')
            guic.create_rectangle(L+2,T+18,R-2,B-2, fill='#07101e', outline=dim, width=1, dash=(3,3))

        elif kind in ('gui_revealer','gui_overlay','gui_stack'):
            guic.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw, dash=(4,2))
            for i in range(3,0,-1):
                off=i*3
                guic.create_rectangle(L+off,T+off,R-off+6,B-off+6, fill='#0a1020', outline=dim, width=1)
            guic.create_text(x+3,y+3, text=kind.replace('gui_',''), fill=dim, font=('Monospace',7,'italic'))

        elif kind in ('gui_flowbox','gui_listbox'):
            guic.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw)
            bx2,by2 = L+4,T+8
            for i in range(6):
                bw2=22+(i%2)*8; bh2=14
                if bx2+bw2>R-4: bx2=L+4; by2+=bh2+2
                guic.create_rectangle(bx2,by2,bx2+bw2,by2+bh2, fill='#0a1a30', outline=dim, width=1)
                bx2+=bw2+2

        elif kind == 'gui_headerbar':
            guic.create_rectangle(L,T,R,B, fill='#0a1830', outline=bor, width=lw)
            for i in range(2):
                bx=L+11+i*20
                guic.create_oval(bx-7,y-7,bx+7,y+7, fill='#1a3a5a', outline=dim)
                guic.create_text(bx,y, text=['◀','▶'][i], fill=dim, font=('Monospace',8))
            guic.create_text(x,y, text=w.get('label','Header')[:14], fill=txt, font=('Monospace',8,'bold'))
            guic.create_rectangle(R-24,y-8,R-4,y+8, fill='#0f3060', outline=dim)
            guic.create_text(R-14,y, text='☰', fill=txt, font=('Monospace',9))

        elif kind == 'gui_menubar':
            guic.create_rectangle(L,T,R,B, fill='#140808', outline=bor, width=lw)
            for i,item in enumerate(['File','Edit','View','Help']):
                guic.create_text(L+10+i*34,y, text=item, fill=txt, font=('Monospace',7), anchor='w')

        elif kind in ('gui_menu','gui_popover'):
            guic.create_rectangle(L,T,R,B, fill='#100808', outline=dim, width=lw)
            guic.create_rectangle(L+2,T+2,R-2,B-2, fill='#0d0606', outline='')
            for i,(itm,clr) in enumerate([('Item 1',txt),('Item 2',txt),('---',dim)]):
                iy = T+10+i*11
                if itm=='---': guic.create_line(L+4,iy,R-4,iy, fill=dim, width=1)
                else: guic.create_text(L+8,iy, text=itm, fill=clr, font=('Monospace',7), anchor='w')

        elif kind == 'gui_menuitem':
            guic.create_rectangle(L,T,R,B, fill='#100808', outline=bor, width=lw)
            guic.create_text(L+10,y, text='▶ '+w.get('label','Item')[:14],
                           fill=txt, font=('Monospace',8), anchor='w')

        elif kind in ('gui_toolbar','gui_actionbar'):
            guic.create_rectangle(L,T,R,B, fill='#0a100a', outline=bor, width=lw)
            for i in range(4):
                bx=L+12+i*28
                guic.create_rectangle(bx-9,y-9,bx+9,y+9, fill='#1a2a1a', outline=dim, width=1)
                guic.create_text(bx,y, text=['📁','💾','✂','📋'][i], font=('Monospace',9))

        elif kind == 'gui_treeview':
            guic.create_rectangle(L,T,R,B, fill='#060c12', outline=bor, width=lw)
            guic.create_rectangle(L,T,R,T+13, fill='#0a1a30', outline=dim, width=1)
            guic.create_text(L+22,T+6, text='Name', fill=txt, font=('Monospace',7), anchor='w')
            guic.create_text(R-24,T+6, text='Val', fill=txt, font=('Monospace',7), anchor='w')
            for i in range(2):
                ry=T+13+i*12
                guic.create_rectangle(L,ry,R,ry+12,
                                     fill='#070d1a' if i%2 else '#080f20', outline='')
                guic.create_text(L+8,ry+6, text=f'▶ row {i+1}',
                               fill=dim, font=('Monospace',7), anchor='w')

        elif kind == 'gui_iconview':
            guic.create_rectangle(L,T,R,B, fill='#060c12', outline=bor, width=lw)
            for ix in range(3):
                for iy in range(2):
                    bx=L+10+ix*40; by=T+6+iy*22
                    guic.create_rectangle(bx,by,bx+28,by+14, fill='#0a1a30', outline=dim, width=1)

        elif kind == 'gui_combobox':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_rectangle(L+4,T+10,R-18,B-10, fill='#050a12', outline=dim, width=1)
            guic.create_rectangle(R-18,T+10,R-4,B-10, fill='#1a3a5a', outline=dim, width=1)
            guic.create_text(R-11,y, text='▼', fill=txt, font=('Monospace',8))
            guic.create_line(L+10,y,L+36,y, fill='#2a3050', width=1)

        elif kind == 'gui_spinbutton':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_rectangle(L+4,T+10,R-17,B-10, fill='#050a12', outline=dim, width=1)
            midh=(T+B)//2
            guic.create_rectangle(R-17,T+10,R-3,midh, fill='#0f2a0f', outline=dim, width=1)
            guic.create_rectangle(R-17,midh,R-3,B-10, fill='#0f0a0f', outline=dim, width=1)
            guic.create_text(R-10,T+16, text='▲', fill=txt, font=('Monospace',7))
            guic.create_text(R-10,B-16, text='▼', fill=txt, font=('Monospace',7))

        elif kind == 'gui_calendar':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_rectangle(L,T,R,T+13, fill='#0f2060', outline=dim, width=1)
            guic.create_text(x,T+6, text='Jun 2026', fill=txt, font=('Monospace',7))
            for ci in range(7):
                for ri in range(3):
                    day=ci+ri*7+1
                    if day<=30:
                        guic.create_text(L+5+ci*18,T+18+ri*10, text=str(day),
                                       fill=dim, font=('Monospace',6))

        elif kind == 'gui_separator':
            guic.create_rectangle(L,T,R,B, fill=col, outline='', width=0)
            guic.create_line(L+4,y,R-4,y, fill=dim, width=2)
            guic.create_oval(x-4,y-4,x+4,y+4, fill=dim, outline='')

        elif kind in ('gui_statusbar','gui_infobar'):
            guic.create_rectangle(L,T,R,B, fill='#080d0a', outline=bor, width=lw)
            guic.create_text(L+8,y, text='● Ready', fill='#44cc44', font=('Monospace',8), anchor='w')
            if kind=='gui_infobar':
                guic.create_rectangle(R-28,T+5,R-4,B-5, fill='#0f3060', outline=dim)
                guic.create_text(R-16,y, text='✕', fill=txt, font=('Monospace',8))

        elif kind == 'gui_filechooser':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            guic.create_rectangle(L+2,T+4,R-2,T+14, fill='#050a12', outline=dim, width=1)
            guic.create_text(L+6,T+9, text='📁 /home/', fill=dim, font=('Monospace',7), anchor='w')
            guic.create_text(L+8,T+22, text='📄 file.txt', fill=txt, font=('Monospace',7), anchor='w')

        elif kind == 'gui_colorchooser':
            guic.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            for ci,fc2 in enumerate(['#cc2222','#22cc22','#2222cc',
                                      '#cccc22','#cc22cc','#22cccc']):
                gci=L+6+(ci%3)*20; gri=T+6+(ci//3)*14
                guic.create_oval(gci,gri,gci+16,gri+10, fill=fc2, outline='')

        elif kind == 'gui_fontchooser':
            pass  # sea monkey end

        kind = w['kind']  # restore: sentinel removed — selection overlay uses real kind

        # ── Selection + edge-src overlay (always on top) ──────────────────────
        if fc_state['mode'] == 'edge_dst' and fc_state['edge_src'] == w['id']:
            guic.create_rectangle(L-3, T-3, R+3, B+3,
                                 outline=C['waypoint'], width=2, dash=(4, 3))
        if sel:
            guic.create_rectangle(L, T, R, B, outline=C['selected'], width=3)
            guic.create_text(x, B + 20, text=f"#{w['id']} ({x},{y})",
                           fill=C['selected'], font=('Monospace', 7))

    def guic_draw_edge(e):
        src = fc_state['widgets'].get(e['src']); dst = fc_state['widgets'].get(e['dst'])
        if not src or not dst: return
        # Design-space positions
        sdx, sdy = guic_abs_pos(src); ddx, ddy = guic_abs_pos(dst)
        dx1_d, dy1_d = sdx, sdy + src.get('h', GH) // 2
        dx2_d, dy2_d = ddx, ddy - dst.get('h', GH) // 2
        # Convert to screen space
        x1, y1 = _gc_d2s(dx1_d, dy1_d)
        x2, y2 = _gc_d2s(dx2_d, dy2_d)
        z  = _gc_view['zoom']
        _asz = (int(12 * z), int(16 * z), int(5 * z))
        # If same row, draw a horizontal arc
        if abs(dy1_d - ddy) < GH:
            mx = (x1 + x2) // 2; my = y1 + int(30 * z)
            guic.create_line(x1, y1, mx, my, x2, y2,
                           fill=C['edge'], width=2,
                           arrow='last', arrowshape=_asz, smooth=True)
        else:
            guic.create_line(x1, y1, x2, y2,
                           fill=C['edge'], width=2,
                           arrow='last', arrowshape=_asz)

    def guic_redraw():
        guic.delete('all'); guic_draw_grid()
        for e in fc_state['edges']:      guic_draw_edge(e)

        # Determine which widget ids to skip (non-first children in stacked containers)
        _stacked_hidden = set()
        for wid, w in fc_state['widgets'].items():
            if (w['kind'] in CONTAINER_KINDS and
                    w.get('layout_mode', 'absolute') == 'stacked'):
                children = guic_children_of(wid)
                for ch in children[1:]:   # skip first; hide the rest
                    _stacked_hidden.add(ch['id'])

        for w in fc_state['widgets'].values():
            if w['id'] not in _stacked_hidden:
                guic_draw_widget(w)

        # Draw drag insertion-point line for hbox/vbox reorder
        insert_pid = fc_state.get('drag_insert_parent')
        insert_idx = fc_state.get('drag_insert_idx')
        if insert_pid is not None and insert_idx is not None:
            parent_w = fc_state['widgets'].get(insert_pid)
            if parent_w:
                mode = parent_w.get('layout_mode', 'absolute')
                siblings = guic_children_of(insert_pid)
                pax, pay = guic_abs_pos(parent_w)
                pw = parent_w.get('w', GW); ph = parent_w.get('h', GH)
                if mode == 'hbox' and siblings:
                    # Vertical line at left edge of slot insert_idx
                    if insert_idx < len(siblings):
                        ref = guic_abs_pos(siblings[insert_idx])
                        lx = ref[0] - siblings[insert_idx].get('w', GW)//2 - 2
                    else:
                        ref = guic_abs_pos(siblings[-1])
                        lx = ref[0] + siblings[-1].get('w', GW)//2 + 2
                    # Bundle 18: transform insertion line to screen space
                    lxs, top_s = _gc_d2s(lx, pay - ph//2)
                    _  , bot_s = _gc_d2s(lx, pay + ph//2)
                    guic.create_line(int(lxs), int(top_s), int(lxs), int(bot_s),
                                   fill=C['selected'], width=2, dash=(4, 2))
                elif mode == 'vbox' and siblings:
                    if insert_idx < len(siblings):
                        ref = guic_abs_pos(siblings[insert_idx])
                        ly = ref[1] - siblings[insert_idx].get('h', GH)//2 - 2
                    else:
                        ref = guic_abs_pos(siblings[-1])
                        ly = ref[1] + siblings[-1].get('h', GH)//2 + 2
                    # Bundle 18: transform insertion line to screen space
                    left_s, lys = _gc_d2s(pax - pw//2, ly)
                    right_s, _  = _gc_d2s(pax + pw//2, ly)
                    guic.create_line(int(left_s), int(lys), int(right_s), int(lys),
                                   fill=C['selected'], width=2, dash=(4, 2))

        # ── Lasso rubber band ─────────────────────────────────────────────────
        # lasso_start / lasso_end stored in design space (set by guic_on_click/motion)
        if fc_state['lasso_start'] is not None and fc_state['lasso_end'] is not None:
            lx0 = min(fc_state['lasso_start'][0], fc_state['lasso_end'][0])
            ly0 = min(fc_state['lasso_start'][1], fc_state['lasso_end'][1])
            lx1 = max(fc_state['lasso_start'][0], fc_state['lasso_end'][0])
            ly1 = max(fc_state['lasso_start'][1], fc_state['lasso_end'][1])
            # Bundle 18: transform lasso corners to screen space
            slx0, sly0 = _gc_d2s(lx0, ly0)
            slx1, sly1 = _gc_d2s(lx1, ly1)
            guic.create_rectangle(int(slx0), int(sly0), int(slx1), int(sly1),
                                outline=C['selected'], fill='', dash=(4, 2), width=1)

    def guic_widget_at(x, y):
        """Return topmost widget whose absolute bounds contain (x, y)."""
        for w in reversed(list(fc_state['widgets'].values())):
            ax, ay = guic_abs_pos(w)
            ww, wh = w.get('w', GW), w.get('h', GH)
            if abs(ax - x) <= ww // 2 and abs(ay - y) <= wh // 2:
                return w
        return None

    # ── Property panel (Stage 5) ──────────────────────────────────────────────

    def guic_commit_property(widget_ids, prop_name, new_value):
        """Commit a property edit: update widget dict, push undo, update word stream.

        widget_ids: list of widget ids to update (multi-select)
        prop_name:  property name (e.g. 'label', 'w', 'layout_mode')
        new_value:  new value (type matches property kind)
        """
        for wid in widget_ids:
            w = fc_state['widgets'].get(wid)
            if w is None: continue
            old_v = fc_state['prop_committed'].get(wid, {}).get(prop_name,
                        _guic_get_prop_value(w, prop_name))
            if old_v == new_value: continue   # no change

            # Commit to widget dict
            _guic_set_prop_value(w, prop_name, new_value)

            # Push undo entry
            _guic_push_undo({'kind': 'property_change', 'widget_id': wid,
                           'property': prop_name,
                           'old_value': old_v, 'new_value': new_value})

            # Update committed-state tracking
            fc_state['prop_committed'].setdefault(wid, {})[prop_name] = new_value

            # Update word stream (deferred bridge update)
            if _update_meccano_widget is not None and fc_state['guic_program'] is not None:
                fc_state['guic_program'] = _update_meccano_widget(
                    fc_state['guic_program'], wid, w)

            # Trigger layout re-run if relevant
            if prop_name == 'layout_mode':
                guic_apply_layout(wid)
            elif prop_name in ('w', 'h'):
                if w['kind'] in CONTAINER_KINDS:
                    guic_apply_layout(wid)
                pid = w.get('parent_id')
                if pid is not None:
                    guic_apply_layout(pid)
            elif prop_name in ('x', 'y'):
                pid = w.get('parent_id')
                if pid is not None:
                    guic_apply_layout(pid)

        guic_redraw()

    def guic_rebuild_prop_panel():
        """Rebuild the right-side property panel for the current selection."""
        # Clear existing contents
        for child in _guic_prop_inner.winfo_children():
            child.destroy()

        sel  = fc_state['selected']
        multi = fc_state['multi_sel']

        if sel is None or not multi:
            tk.Label(_guic_prop_inner, text="No selection",
                     bg=C['palette'], fg=C['dim'],
                     font=('Monospace', 8), pady=20).pack(fill='x')
            return

        # Determine which widgets are selected and get properties
        sel_widgets = [fc_state['widgets'][wid] for wid in multi
                       if wid in fc_state['widgets']]
        if not sel_widgets: return

        kinds = [w['kind'] for w in sel_widgets]
        if len(set(kinds)) == 1:
            props = _fp_properties_for(kinds[0])
        else:
            props = _fp_common_for_kinds(kinds)

        if not props:
            tk.Label(_guic_prop_inner, text="No editable properties",
                     bg=C['palette'], fg=C['dim'],
                     font=('Monospace', 8), pady=10).pack(fill='x')
            return

        widget_ids = list(multi)
        is_multi   = len(widget_ids) > 1
        primary_w  = fc_state['widgets'].get(sel) or sel_widgets[0]

        # Group properties by section
        sections: dict = {}
        for p in props:
            sec = p.get('section', 'General')
            sections.setdefault(sec, []).append(p)

        for sec_name, sec_props in sections.items():
            # Section header
            tk.Label(_guic_prop_inner, text=sec_name,
                     bg=C['pal_btn'], fg=C['pal_border'],
                     font=('Monospace', 7, 'bold'),
                     anchor='w', padx=6, pady=2).pack(fill='x', pady=(4, 0))

            for p in sec_props:
                pname = p['name']
                pkind = p['kind']

                # Get current value (primary widget; detect mixed for multi)
                cur_val = _guic_get_prop_value(primary_w, pname)
                is_mixed = False
                if is_multi:
                    vals = [_guic_get_prop_value(fc_state['widgets'][wid], pname)
                            for wid in widget_ids if wid in fc_state['widgets']]
                    if len(set(v if not isinstance(v, list) else str(v)
                               for v in vals)) > 1:
                        is_mixed = True

                row = tk.Frame(_guic_prop_inner, bg=C['palette'])
                row.pack(fill='x', padx=4, pady=1)
                tk.Label(row, text=pname, bg=C['palette'], fg=C['dim'],
                         font=('Monospace', 7), width=12, anchor='w').pack(side='left')

                if pname == 'name':
                    # Phase 7c-1: programmatic identity. Unique across the stream,
                    # so it is edited single-widget only; multi-select shows it as
                    # read-only. Validation refuses duplicates and reverts.
                    if is_multi:
                        ne = tk.Entry(row, bg=C['canvas'], fg=C['dim'],
                                      font=('Monospace', 8), relief='flat')
                        ne.insert(0, '(unique per widget)')
                        ne.config(state='readonly')
                        ne.pack(side='left', fill='x', expand=True)
                    else:
                        nvar = tk.StringVar(value=cur_val or '')
                        nentry = tk.Entry(row, textvariable=nvar,
                                          bg=C['canvas'], fg=C['text'],
                                          font=('Monospace', 8), relief='flat',
                                          insertbackground=C['text'])
                        nentry.pack(side='left', fill='x', expand=True)

                        def _on_name_commit(event, _var=nvar, _wid=sel, _w=primary_w):
                            new = _var.get().strip()
                            if new and fc_state['stream'].name_in_use(new, exclude=_w):
                                guic_set_status(
                                    f"Name '{new}' already in use — reverted")
                                _var.set(_w.get('name', ''))
                                return
                            guic_commit_property([_wid], 'name', new)
                            # Phase 7c-2: re-materialise auto-wiring for the new
                            # name and refresh the read-only handler display.
                            _guic_sync_stream()
                            guic_rebuild_prop_panel()

                        nentry.bind('<Return>',   _on_name_commit)
                        nentry.bind('<FocusOut>', _on_name_commit)
                    continue

                if pkind == 'string':
                    var = tk.StringVar(value='' if is_mixed else (cur_val or ''))
                    entry = tk.Entry(row, textvariable=var,
                                     bg=C['canvas'], fg=C['text'],
                                     font=('Monospace', 8), relief='flat',
                                     insertbackground=C['text'])
                    if is_mixed:
                        entry.config(foreground=C['dim'])
                        entry.insert(0, '(multiple values)')
                    entry.pack(side='left', fill='x', expand=True)

                    # Live update on keystroke (visual feedback)
                    def _on_string_change(event, _pname=pname, _var=var, _wids=widget_ids):
                        v = _var.get()
                        for wid in _wids:
                            w = fc_state['widgets'].get(wid)
                            if w: _guic_set_prop_value(w, _pname, v)
                        guic_redraw()

                    # Commit on Enter or FocusOut
                    def _on_string_commit(event, _pname=pname, _var=var, _wids=widget_ids):
                        guic_commit_property(_wids, _pname, _var.get())

                    entry.bind('<KeyRelease>', _on_string_change)
                    entry.bind('<Return>',     _on_string_commit)
                    entry.bind('<FocusOut>',   _on_string_commit)

                elif pkind == 'int':
                    _min = p.get('min', -9999)
                    _max = p.get('max',  9999)
                    var = tk.StringVar(value='' if is_mixed else str(cur_val or 0))
                    spin = tk.Spinbox(row, textvariable=var,
                                      from_=_min, to=_max, increment=1, width=7,
                                      bg=C['canvas'], fg=C['text'],
                                      font=('Monospace', 8), relief='flat',
                                      insertbackground=C['text'],
                                      buttonbackground=C['pal_btn'])
                    if is_mixed:
                        spin.delete(0, 'end')
                        spin.insert(0, '(multiple)')
                    spin.pack(side='left')

                    def _on_int_commit(event=None, _pname=pname, _var=var, _wids=widget_ids,
                                       _min=_min, _max=_max):
                        try:
                            v = int(_var.get())
                            v = max(_min, min(_max, v))
                        except (ValueError, TypeError):
                            return
                        guic_commit_property(_wids, _pname, v)

                    spin.bind('<Return>',   _on_int_commit)
                    spin.bind('<FocusOut>', _on_int_commit)
                    spin.config(command=lambda _f=_on_int_commit: root.after(10, _f))

                elif pkind == 'choice':
                    options = p.get('options', [])
                    var = tk.StringVar(value=cur_val if cur_val in options else
                                       (options[0] if options else ''))
                    om = tk.OptionMenu(row, var, *options)
                    om.config(bg=C['pal_btn'], fg=C['text'],
                               font=('Monospace', 8), relief='flat',
                               activebackground=C['selected'], width=10)
                    om['menu'].config(bg=C['pal_btn'], fg=C['text'],
                                       font=('Monospace', 8))
                    om.pack(side='left')

                    def _on_choice(*args, _pname=pname, _var=var, _wids=widget_ids):
                        guic_commit_property(_wids, _pname, _var.get())
                    var.trace_add('write', _on_choice)

                elif pkind == 'bool':
                    var = tk.BooleanVar(value=False if is_mixed else bool(cur_val))
                    cb = tk.Checkbutton(row, variable=var,
                                        bg=C['palette'], fg=C['text'],
                                        activebackground=C['palette'],
                                        selectcolor=C['canvas'],
                                        relief='flat')
                    cb.pack(side='left')

                    def _on_bool(_pname=pname, _var=var, _wids=widget_ids):
                        guic_commit_property(_wids, _pname, _var.get())
                    var.trace_add('write', lambda *a, _f=_on_bool: _f())

        # ── Phase 6D: Signals section ────────────────────────────────────────
        if len(set(kinds)) == 1:
            sig_list = _signals_for(kinds[0])
        else:
            sig_list = _common_signals_for(kinds)

        # ── Phase 7c-2: Signals → handler names (read-only). The explicit
        # binding picker is retired; wiring happens by naming a flow_terminator
        # to match a handler name shown here.
        if sig_list:
            tk.Label(_guic_prop_inner, text='Signals → handlers',
                     bg=C['pal_btn'], fg=C['pal_border'],
                     font=('Monospace', 7, 'bold'),
                     anchor='w', padx=6, pady=2).pack(fill='x', pady=(4, 0))

            def _term_is_entry_named(handler_name):
                """True if an entry flow_terminator named `handler_name` exists."""
                if not handler_name:
                    return False
                for _sym in fc_state['flow_symbols'].values():
                    if (_sym.get('kind') == 'flow_terminator'
                            and _sym.get('name', '') == handler_name):
                        for _p in _sym.get('properties', []):
                            if _p.get('name') == 'is_entry' and _p.get('value'):
                                return True
                return False

            if is_multi:
                tk.Label(_guic_prop_inner,
                         text='(select one widget to see its handler names)',
                         bg=C['palette'], fg=C['dim'], font=('Monospace', 7),
                         anchor='w', padx=6).pack(fill='x')
            else:
                wname = primary_w.get('name', '')
                for sig in sig_list:
                    sig_name = sig['name']; sig_id = sig['id']
                    handler  = _aw_canonical(wname, sig_name)
                    sig_dict = primary_w.get('signal_ids') or {}
                    binfo    = sig_dict.get(sig_id) or sig_dict.get(str(sig_id))
                    if binfo and not binfo.get('auto_wired'):
                        state_txt, col = 'manual', '#ffcc66'
                    elif _term_is_entry_named(handler):
                        state_txt, col = '✓ wired', '#7aff7a'
                    else:
                        state_txt, col = 'unwired', C['dim']
                    row = tk.Frame(_guic_prop_inner, bg=C['palette'])
                    row.pack(fill='x', padx=4, pady=1)
                    tk.Label(row, text=sig_name, bg=C['palette'], fg=C['dim'],
                             font=('Monospace', 7), width=9, anchor='w').pack(side='left')
                    tk.Label(row, text=(handler or '(name the widget)'),
                             bg=C['palette'], fg=C['text'], font=('Monospace', 7),
                             anchor='w').pack(side='left', fill='x', expand=True)
                    tk.Label(row, text=state_txt, bg=C['palette'], fg=col,
                             font=('Monospace', 7), anchor='e').pack(side='right', padx=4)
                tk.Label(_guic_prop_inner,
                         text='Name a flow_terminator to a handler above to wire it.',
                         bg=C['palette'], fg=C['dim'], font=('Monospace', 7),
                         anchor='w', justify='left', wraplength=_GC_PROP_W - 24,
                         padx=6, pady=2).pack(fill='x', pady=(2, 0))

        # ── Stage 8-4: Cell binding (read-only) — single-select only ──────────
        if not is_multi:
            tk.Label(_guic_prop_inner, text='Cell binding',
                     bg=C['pal_btn'], fg=C['pal_border'],
                     font=('Monospace', 7, 'bold'),
                     anchor='w', padx=6, pady=2).pack(fill='x', pady=(4, 0))
            brow = tk.Frame(_guic_prop_inner, bg=C['palette']); brow.pack(fill='x', padx=4, pady=1)
            tk.Label(brow, text='bind_value_to', bg=C['palette'], fg=C['dim'],
                     font=('Monospace', 7), width=12, anchor='w').pack(side='left')
            _bv_var = tk.StringVar(value=_guic_get_prop_value(primary_w, 'bind_value_to') or '')
            _bv_cb = ttk.Combobox(brow, textvariable=_bv_var,
                                  values=_sheet_all_cell_names(),
                                  font=('Monospace', 7))
            _bv_cb.pack(side='left', fill='x', expand=True)
            def _bv_commit(_e=None, _w=primary_w, _v=_bv_var):
                guic_commit_property([_w['id']], 'bind_value_to', _v.get().strip())
                guic_redraw()
            _bv_cb.bind('<Return>', _bv_commit)
            _bv_cb.bind('<FocusOut>', _bv_commit)
            _bv_cb.bind('<<ComboboxSelected>>', _bv_commit)

            # Stage 8-5: write-back — push a value into the bound cell. (In the
            # editor there is no live widget input; this is the editor-side
            # expression of the bidirectional binding. Runtime write-back from a
            # running widget is the compiler-runtime follow-on.)
            if (_guic_get_prop_value(primary_w, 'bind_value_to') or '').strip():
                wrow = tk.Frame(_guic_prop_inner, bg=C['palette']); wrow.pack(fill='x', padx=4, pady=1)
                tk.Label(wrow, text='push value', bg=C['palette'], fg=C['dim'],
                         font=('Monospace', 7), width=12, anchor='w').pack(side='left')
                _wb_var = tk.StringVar()
                _wb_e = tk.Entry(wrow, textvariable=_wb_var, bg=C['canvas'], fg=C['text'],
                                 insertbackground=C['text'], font=('Monospace', 7), relief='flat')
                _wb_e.pack(side='left', fill='x', expand=True)
                def _wb_commit(_e=None, _w=primary_w, _v=_wb_var):
                    name = (_guic_get_prop_value(_w, 'bind_value_to') or '').strip()
                    rc = _sheet_cell_by_name(name)
                    if rc is not None:
                        _sheet_set_cell(rc[0], rc[1], _v.get())
                        if fc_state.get('stream') is not None:
                            fc_state['stream'].ensure_unique_names()
                        _sheet_recompute(); _sheet_redraw(); guic_redraw()
                        guic_set_status(f"Wrote '{_v.get()}' → {name}")
                _wb_e.bind('<Return>', _wb_commit)

        # Scroll to top after rebuild
        _guic_prop_cvs.yview_moveto(0)

    # ── Events ────────────────────────────────────────────────────────────────
    def guic_on_click(event):
        # Bundle 18: convert click from screen to design space at input layer
        x, y = _gc_s2d(event.x, event.y)
        mode = fc_state['mode']
        shift = bool(event.state & 0x0001)   # Shift key

        if mode == 'place':
            nid = fc_state['next_id']; fc_state['next_id'] += 1
            sx, sy = snap(x), snap(y)
            kind = fc_state['place_kind']
            _dw, _dh = _GC_DEFAULT_SIZE.get(kind, (GW, GH))
            # Check if dropped inside a container
            drop_ct = guic_container_at(sx, sy, nid)
            new_pid = None
            if drop_ct is not None:
                ctx, cty = guic_abs_pos(drop_ct)
                sx = sx - ctx; sy = sy - cty
                new_pid = drop_ct['id']
            new_w = {'id': nid, 'kind': kind, 'x': sx, 'y': sy,
                     'label': kind.replace('gui_', ''),
                     'name': _fc_make_default_name(kind, nid),
                     'w': _dw, 'h': _dh, 'parent_id': new_pid,
                     'layout_mode': _GC_LAYOUT_DEFAULTS.get(kind, 'absolute'),
                     'properties': []}
            fc_state['widgets'][nid] = new_w
            if new_pid is not None:
                fc_state['child_order'].setdefault(new_pid, []).append(nid)
                guic_apply_layout(new_pid)
            _guic_push_undo({'kind': 'delete', 'widget': new_w.copy()})
            fc_state['selected'] = nid; fc_state['multi_sel'] = {nid}
            # Bundle 23 P2: return to Select mode after a drop (matches Flow tab).
            # Staying in 'place' trapped the canvas — every later click placed a
            # duplicate instead of selecting/dragging/deleting.
            guic_set_mode('select')
            guic_set_status(f"Placed {kind}  #{nid} — now in Select mode")
            guic_rebuild_prop_panel()
            guic_redraw(); return

        if mode == 'delete':
            hit = guic_widget_at(x, y)
            if hit:
                wc = hit.copy()
                hid = hit['id']
                old_pid = hit.get('parent_id')
                fc_state['widgets'].pop(hid)
                fc_state['edges'] = [e for e in fc_state['edges']
                                 if e['src'] != hid and e['dst'] != hid]
                if fc_state['selected'] == hid:
                    fc_state['selected'] = None; fc_state['multi_sel'].clear()
                fc_state['multi_sel'].discard(hid)
                # Remove from parent's child_order and re-run layout
                if old_pid is not None and old_pid in fc_state['child_order']:
                    try: fc_state['child_order'][old_pid].remove(hid)
                    except ValueError: pass
                    guic_apply_layout(old_pid)
                _guic_push_undo({'kind': 'place', 'widget': wc})
                guic_set_status(f"Deleted {hit['kind']} #{hid}")
            guic_redraw(); return

        if mode == 'edge_src':
            hit = guic_widget_at(x, y)
            if hit:
                fc_state['edge_src'] = hit['id']; fc_state['mode'] = 'edge_dst'
                guic_set_status(f"From  {hit['kind']} — now click the child widget")
            guic_redraw(); return

        if mode == 'edge_dst':
            hit = guic_widget_at(x, y)
            if hit and hit['id'] != fc_state['edge_src']:
                fc_state['edges'].append({'src': fc_state['edge_src'], 'dst': hit['id']})
                src_w = fc_state['widgets'].get(fc_state['edge_src'])
                guic_set_status(f"Connected  {src_w['kind'] if src_w else '?'}  →  {hit['kind']}")
                fc_state['edge_src'] = None; guic_set_mode('select')
            elif hit and hit['id'] == fc_state['edge_src']:
                guic_set_status("Can't connect to self")
            guic_redraw(); return

        # ── Select / resize / drag ─────────────────────────────────────────────
        # 1. Handle hit takes priority over widget body (D4)
        hw, hname = guic_handle_at(x, y)
        if hw is not None:
            ax, ay = guic_abs_pos(hw)
            ww, wh = hw.get('w', GW), hw.get('h', GH)
            fc_state['resize_handle'] = hname
            fc_state['resize_origin'] = (ax, ay, ww, wh)
            fc_state['dragging'] = False
            guic_redraw(); return

        # 2. Widget body hit
        hit = guic_widget_at(x, y)
        if hit:
            if shift:
                # Shift+click: toggle in multi-selection
                if hit['id'] in fc_state['multi_sel']:
                    fc_state['multi_sel'].discard(hit['id'])
                    if fc_state['selected'] == hit['id']:
                        fc_state['selected'] = next(iter(fc_state['multi_sel']), None)
                else:
                    fc_state['multi_sel'].add(hit['id'])
                    fc_state['selected'] = hit['id']
            else:
                fc_state['selected'] = hit['id']; fc_state['multi_sel'] = {hit['id']}

            ax, ay = guic_abs_pos(hit)
            fc_state['dragging']   = True
            fc_state['drag_offset']= (x - ax, y - ay)
            fc_state['drag_origin']= {wid: (fc_state['widgets'][wid]['x'], fc_state['widgets'][wid]['y'])
                                 for wid in fc_state['multi_sel'] if wid in fc_state['widgets']}
            guic_set_status(f"Selected  {hit['kind']}  #{hit['id']}")
        else:
            if not shift:
                fc_state['selected'] = None; fc_state['multi_sel'].clear()
            fc_state['dragging'] = False
            # Start lasso rubber-band drag on empty canvas in select mode
            if mode == 'select' and not shift:
                fc_state['lasso_start'] = (x, y)
                fc_state['lasso_end']   = (x, y)
        fc_state['drop_target'] = None
        guic_rebuild_prop_panel()
        guic_redraw()

    def guic_on_motion(event):
        # Bundle 18: convert motion event to design space at input layer
        x, y = _gc_s2d(event.x, event.y)

        # ── Lasso drag (design-space coords stored) ────────────────────────────
        if fc_state['lasso_start'] is not None:
            fc_state['lasso_end'] = (x, y)
            guic_redraw(); return

        # ── Resize drag ────────────────────────────────────────────────────────
        if fc_state['resize_handle'] is not None and fc_state['selected'] is not None:
            w = fc_state['widgets'].get(fc_state['selected'])
            if w:
                ox, oy, ow, oh = fc_state['resize_origin']
                h = fc_state['resize_handle']
                # Each handle constrains different edges (all in design space)
                nx, ny, nw, nh = ox, oy, ow, oh
                if 'W' in h:
                    delta = x - (ox - ow // 2)
                    nw = max(_GC_MIN_SIZE, ow - delta)
                    nx = ox + (ow - nw) // 2
                if 'E' in h:
                    nw = max(_GC_MIN_SIZE, (x - (ox - ow // 2)))
                    nx = (ox - ow // 2) + nw // 2
                if 'N' in h:
                    delta = y - (oy - oh // 2)
                    nh = max(_GC_MIN_SIZE, oh - delta)
                    ny = oy + (oh - nh) // 2
                if 'S' in h:
                    nh = max(_GC_MIN_SIZE, (y - (oy - oh // 2)))
                    ny = (oy - oh // 2) + nh // 2
                w['x'] = nx; w['y'] = ny; w['w'] = nw; w['h'] = nh
                # Re-run layout if this is a container (trigger #3)
                if w['kind'] in CONTAINER_KINDS:
                    guic_apply_layout(w['id'])
            guic_redraw(); return

        # ── Move drag ──────────────────────────────────────────────────────────
        if fc_state['dragging'] and fc_state['selected'] is not None:
            primary = fc_state['widgets'].get(fc_state['selected'])
            if primary:
                ax, ay = guic_abs_pos(primary)
                dx_off, dy_off = fc_state['drag_offset']
                new_ax = snap(x - dx_off); new_ay = snap(y - dy_off)
                ddx = new_ax - ax; ddy = new_ay - ay
                for wid in fc_state['multi_sel']:
                    w = fc_state['widgets'].get(wid)
                    if w: w['x'] += ddx; w['y'] += ddy

            # Drop-target detection for the primary dragged widget
            sel = fc_state['selected']
            if sel in fc_state['widgets']:
                ct = guic_container_at(x, y, sel)
                fc_state['drop_target'] = ct['id'] if ct else None

                # Detect drag-within-layout-container for hbox/vbox reorder
                prim_w = fc_state['widgets'].get(sel)
                pid = prim_w.get('parent_id') if prim_w else None
                parent_w = fc_state['widgets'].get(pid) if pid is not None else None
                parent_mode = (parent_w.get('layout_mode', 'absolute')
                               if parent_w else 'absolute')
                if parent_mode in ('hbox', 'vbox') and len(fc_state['multi_sel']) == 1:
                    # Compute insertion index based on cursor vs sibling centres (design space)
                    siblings = guic_children_of(pid)
                    pax, pay = guic_abs_pos(parent_w)
                    if parent_mode == 'hbox':
                        centres = [guic_abs_pos(s)[0] for s in siblings]
                        idx = sum(1 for cx2 in centres if cx2 < x)
                    else:
                        centres = [guic_abs_pos(s)[1] for s in siblings]
                        idx = sum(1 for cy2 in centres if cy2 < y)
                    # Clamp to exclude the dragged widget's own position
                    cur_idx = next((i for i, s in enumerate(siblings)
                                    if s['id'] == sel), None)
                    fc_state['drag_insert_parent'] = pid
                    fc_state['drag_insert_idx']    = idx
                else:
                    fc_state['drag_insert_parent'] = None
                    fc_state['drag_insert_idx']    = None

            guic_redraw()

    def guic_on_release(event):
        sel = fc_state['selected']

        # ── Finalize resize ────────────────────────────────────────────────────
        if fc_state['resize_handle'] is not None and sel in (fc_state['widgets'] or {}):
            w = fc_state['widgets'].get(sel)
            ro = fc_state['resize_origin']
            if w and ro:
                ox, oy, ow, oh = ro
                # Only push undo if something actually changed
                if (w['x'], w['y'], w['w'], w['h']) != (ox, oy, ow, oh):
                    _guic_push_undo({'kind': 'resize', 'id': sel,
                                   'x': ox, 'y': oy, 'w': ow, 'h': oh})
            fc_state['resize_handle'] = None; fc_state['resize_origin'] = None

        # ── Finalize move / reparent ───────────────────────────────────────────
        elif fc_state['dragging'] and sel is not None:
            # Drag-reorder within hbox/vbox parent
            insert_pid = fc_state.get('drag_insert_parent')
            insert_idx = fc_state.get('drag_insert_idx')
            if (insert_pid is not None and insert_idx is not None
                    and sel in fc_state['widgets']
                    and fc_state['widgets'][sel].get('parent_id') == insert_pid):
                old_order = list(fc_state['child_order'].get(insert_pid, []))
                # Build new order with sel removed then inserted at idx
                new_order = [wid for wid in old_order if wid != sel]
                new_order.insert(min(insert_idx, len(new_order)), sel)
                if new_order != old_order:
                    _guic_push_undo({'kind': 'reorder', 'parent_id': insert_pid,
                                   'order': old_order})
                    fc_state['child_order'][insert_pid] = new_order
                    guic_apply_layout(insert_pid)
                    guic_set_status(f"Reordered children of #{insert_pid}")
                fc_state['drag_insert_parent'] = None
                fc_state['drag_insert_idx']    = None

            # Reparent if dropped onto a different container
            elif fc_state['drop_target'] is not None and sel in fc_state['widgets']:
                w      = fc_state['widgets'][sel]
                ct     = fc_state['widgets'].get(fc_state['drop_target'])
                if ct and ct['id'] != w.get('parent_id'):
                    old_pid = w.get('parent_id')
                    old_x, old_y = w['x'], w['y']
                    # Remove from old parent's child_order
                    if old_pid is not None and old_pid in fc_state['child_order']:
                        try: fc_state['child_order'][old_pid].remove(sel)
                        except ValueError: pass
                    # Rebase coordinates to be relative to container
                    ctx, cty = guic_abs_pos(ct)
                    ax, ay   = guic_abs_pos(w)
                    w['parent_id'] = ct['id']
                    w['x'] = ax - ctx
                    w['y'] = ay - cty
                    fc_state['child_order'].setdefault(ct['id'], []).append(sel)
                    # Run layout for old and new parent
                    if old_pid is not None: guic_apply_layout(old_pid)
                    guic_apply_layout(ct['id'])
                    _guic_push_undo({'kind': 'reparent', 'id': sel,
                                   'parent_id': old_pid, 'x': old_x, 'y': old_y})
                    guic_set_status(f"Nested {w['kind']} inside {ct['kind']}")
            else:
                # Phase 6B: emit a single atomic 'move_multi' action for the group.
                # This is the D9 lasso group-drag fix — one semantic undo entry
                # covers all moved widgets; Ctrl+Z restores all positions at once.
                origin = fc_state.get('drag_origin') or {}
                moved_origins = {wid: (ox, oy)
                                 for wid, (ox, oy) in origin.items()
                                 if fc_state['widgets'].get(wid) is not None
                                 and (fc_state['widgets'][wid]['x'],
                                      fc_state['widgets'][wid]['y']) != (ox, oy)}
                if moved_origins:
                    if len(moved_origins) == 1:
                        # Single widget: use classic 'move' entry
                        wid, (ox, oy) = next(iter(moved_origins.items()))
                        _guic_push_undo({'kind': 'move', 'id': wid, 'x': ox, 'y': oy})
                    else:
                        # Group: single atomic entry with all widget origins
                        _guic_push_undo({'kind': 'move_multi', 'origins': moved_origins})

        # ── Finalise lasso ─────────────────────────────────────────────────────
        if fc_state['lasso_start'] is not None and fc_state['lasso_end'] is not None:
            lx0 = min(fc_state['lasso_start'][0], fc_state['lasso_end'][0])
            ly0 = min(fc_state['lasso_start'][1], fc_state['lasso_end'][1])
            lx1 = max(fc_state['lasso_start'][0], fc_state['lasso_end'][0])
            ly1 = max(fc_state['lasso_start'][1], fc_state['lasso_end'][1])
            if lx1 - lx0 > 5 or ly1 - ly0 > 5:  # not a degenerate click
                for wid, w in fc_state['widgets'].items():
                    ax, ay = guic_abs_pos(w)
                    ww2, wh2 = w.get('w', GW), w.get('h', GH)
                    if (ax - ww2//2 < lx1 and ax + ww2//2 > lx0 and
                            ay - wh2//2 < ly1 and ay + wh2//2 > ly0):
                        fc_state['multi_sel'].add(wid)
                        if fc_state['selected'] is None:
                            fc_state['selected'] = wid
                if fc_state['multi_sel']:
                    guic_set_status(f"Selected {len(fc_state['multi_sel'])} widget(s)")
                    guic_rebuild_prop_panel()
            fc_state['lasso_start'] = None
            fc_state['lasso_end']   = None

        fc_state['dragging']          = False
        fc_state['drop_target']       = None
        fc_state['drag_origin']       = None
        fc_state['drag_insert_parent'] = None
        fc_state['drag_insert_idx']   = None
        guic_redraw()

    def guic_on_key(event):
        k = event.keysym.lower()
        ctrl = bool(event.state & 0x0004)

        # Bundle 18: Home key resets GUI canvas view
        if k == 'home':
            _gc_view['zoom'] = 1.0; _gc_view['sx'] = 0.0; _gc_view['sy'] = 0.0
            _gc_update_scrollregion(); guic_redraw()
            _update_zoom_indicator(); return
        # Bundle 21: arrow keys + Page Up/Down scroll the GUI canvas
        if k in ('up', 'kp_up'):
            _gc_view['sy'] -= GH; _gc_update_scrollregion(); guic_redraw(); return
        if k in ('down', 'kp_down'):
            _gc_view['sy'] += GH; _gc_update_scrollregion(); guic_redraw(); return
        if k in ('left', 'kp_left'):
            _gc_view['sx'] -= GW; _gc_update_scrollregion(); guic_redraw(); return
        if k in ('right', 'kp_right'):
            _gc_view['sx'] += GW; _gc_update_scrollregion(); guic_redraw(); return
        if k == 'prior':    # Page Up
            _gc_view['sy'] -= (guic.winfo_height() or 660) / _gc_view['zoom']
            _gc_update_scrollregion(); guic_redraw(); return
        if k == 'next':     # Page Down
            _gc_view['sy'] += (guic.winfo_height() or 660) / _gc_view['zoom']
            _gc_update_scrollregion(); guic_redraw(); return

        if k == 'escape':
            guic_set_mode('select')
        elif k == 'e' and not ctrl:
            guic_set_mode('edge_src')

        elif k == 'z' and ctrl:
            if event.state & 0x0001:   # Ctrl+Shift+Z → redo
                guic_redo()
            else:
                guic_undo()
        elif k == 'y' and ctrl:
            guic_redo()

        # Phase 6A: Alt+Z / Alt+Y — word-level undo/redo (delegates to semantic in 6A)
        elif k == 'z' and (event.state & 0x0008):   # Alt+Z
            guic_undo_word()
        elif k == 'y' and (event.state & 0x0008):   # Alt+Y
            guic_redo_word()

        elif k == 'delete':
            sel = fc_state['selected']
            multi = fc_state['multi_sel']
            if multi:
                removed = []
                affected_parents = set()
                for wid in list(multi):
                    if wid in fc_state['widgets']:
                        w_del = fc_state['widgets'].pop(wid)
                        removed.append(w_del.copy())
                        fc_state['edges'] = [e for e in fc_state['edges']
                                        if e['src'] != wid and e['dst'] != wid]
                        pid_del = w_del.get('parent_id')
                        if pid_del is not None:
                            if pid_del in fc_state['child_order']:
                                try: fc_state['child_order'][pid_del].remove(wid)
                                except ValueError: pass
                            affected_parents.add(pid_del)
                if removed:
                    _guic_push_undo({'kind': 'delete_multi', 'widgets': removed})
                    guic_set_status(f"Deleted {len(removed)} widget(s)")
                for apid in affected_parents:
                    guic_apply_layout(apid)
                fc_state['selected'] = None; fc_state['multi_sel'].clear()
                guic_rebuild_prop_panel()
                guic_redraw()
            elif sel is not None and sel in fc_state['widgets']:
                wc = fc_state['widgets'].pop(sel).copy()
                fc_state['edges'] = [e for e in fc_state['edges']
                                 if e['src'] != sel and e['dst'] != sel]
                old_pid_k = wc.get('parent_id')
                if old_pid_k is not None and old_pid_k in fc_state['child_order']:
                    try: fc_state['child_order'][old_pid_k].remove(sel)
                    except ValueError: pass
                    guic_apply_layout(old_pid_k)
                _guic_push_undo({'kind': 'place', 'widget': wc})
                fc_state['selected'] = None; fc_state['multi_sel'].clear()
                guic_set_status(f"Deleted {wc['kind']} #{wc['id']}")
                guic_rebuild_prop_panel()
                guic_redraw()

    guic.bind('<Button-1>',      guic_on_click)
    guic.bind('<B1-Motion>',     guic_on_motion)
    guic.bind('<ButtonRelease-1>', guic_on_release)
    guic.bind('<Enter>',         lambda e: guic.focus_set())
    guic.bind('<Key>',           guic_on_key)

    # ── Bundle 17 A: Tab-aware sidebar builders ───────────────────────────────

    def _build_gui_tools():
        """Rebuild tools frame for the GUI tab: Select/Connect/Delete + widget palette."""
        for w in _pal_tools_frame.winfo_children(): w.destroy()
        pal_btns.clear()

        _pal_section("TOOLS")
        for _lbl, _mode, _fg in [
            ('☞ Select',  'select',   '#aaaaff'),
            ('⬡ Connect', 'edge_src', '#7aff7a'),
            ('✕ Delete',  'delete',   '#ff8888'),
        ]:
            tk.Button(_pal_tools_frame, text=_lbl,
                      bg=C['pal_btn'], fg=_fg,
                      font=('Monospace', 9), relief='flat',
                      activebackground=C['pal_active'], activeforeground=C['text'],
                      cursor='hand2', padx=4, pady=4,
                      command=lambda m=_mode: guic_set_mode(m)
                      ).pack(fill='x', padx=6, pady=2)

        tk.Frame(_pal_tools_frame, bg=C['dim'], height=1).pack(fill='x', padx=6, pady=2)
        _pal_section("WIDGETS")

        # Scrollable canvas to hold collapsible widget categories
        _pal_wgt_cvs = tk.Canvas(_pal_tools_frame, bg=C['palette'], highlightthickness=0)
        _pal_wgt_sb  = tk.Scrollbar(_pal_tools_frame, orient='vertical',
                                    command=_pal_wgt_cvs.yview)
        _pal_wgt_sb.pack(side='right', fill='y')
        _pal_wgt_cvs.pack(fill='both', expand=True)
        _pal_wgt_cvs.configure(yscrollcommand=_pal_wgt_sb.set)

        _pal_wgt_inner = tk.Frame(_pal_wgt_cvs, bg=C['palette'])
        _pal_wgt_win   = _pal_wgt_cvs.create_window((0, 0), window=_pal_wgt_inner, anchor='nw')

        def _on_inner_cfg(e):
            _pal_wgt_cvs.configure(scrollregion=_pal_wgt_cvs.bbox('all'))
        _pal_wgt_inner.bind('<Configure>', _on_inner_cfg)

        def _on_cvs_cfg(e):
            _pal_wgt_cvs.itemconfig(_pal_wgt_win, width=e.width)
        _pal_wgt_cvs.bind('<Configure>', _on_cvs_cfg)

        _grp_names = {5: 'CONTAINERS', 4: 'CONTROLS', 3: 'INPUTS',
                      2: 'DISPLAY', 1: 'DIALOGS', 0: 'MENUS'}
        _sections  = {}
        _pal_wgt_inner.columnconfigure(0, weight=1)
        _row = [0]

        def _make_sec_toggle(hdr_ref, sec_frame, open_state, name):
            def _toggle():
                open_state[0] = not open_state[0]
                if open_state[0]:
                    sec_frame.grid()
                    hdr_ref[0].config(text=f'▾ {name}')
                else:
                    sec_frame.grid_remove()
                    hdr_ref[0].config(text=f'▸ {name}')
            return _toggle

        for wtype, y_lo in _ghost_palette_types:
            grp_key = y_lo // 100
            if grp_key not in _sections:
                name       = _grp_names.get(grp_key, f'GROUP_{grp_key}')
                open_state = [True]
                sec_frame  = tk.Frame(_pal_wgt_inner, bg=C['palette'])
                hdr_ref    = [None]
                toggle_fn  = _make_sec_toggle(hdr_ref, sec_frame, open_state, name)
                hdr_btn    = tk.Button(_pal_wgt_inner, text=f'▾ {name}',
                                       bg=C['palette'], fg=C['dim'],
                                       font=('Monospace', 7, 'bold'), relief='flat', bd=0,
                                       pady=2, padx=4, anchor='w', cursor='hand2',
                                       command=toggle_fn)
                hdr_btn.grid(row=_row[0], column=0, sticky='ew', padx=2, pady=(4, 0))
                _row[0] += 1
                hdr_ref[0] = hdr_btn
                sec_frame.grid(row=_row[0], column=0, sticky='ew')
                _row[0] += 1
                _sections[grp_key] = {'open': open_state, 'frame': sec_frame, 'btn': hdr_btn}
            col   = _guic_color.get(wtype, C['pal_btn'])
            short = wtype.replace('gui_', '')
            tk.Button(_sections[grp_key]['frame'], text=short,
                      bg=col, fg=C['text'],
                      font=('Monospace', 8), relief='flat', bd=0,
                      padx=4, pady=2, cursor='hand2', anchor='w',
                      command=lambda k=wtype: guic_set_mode('place', k)
                      ).pack(fill='x', padx=4, pady=1)

    # ═══════════════════════════════════════════════════════════════════════════
    # Connectors tab — command-composition canvas (Stage 9-0; Bundle 24 promoted
    # it from a dormant sub-view to its own tab)
    #
    # Command widgets (cmd_*) are flow-symbol-shaped tiles with a header
    # (name + kind) and a body (placeholder input/output sockets + a pocket
    # indicator). Placement, selection, drag, delete, scroll/zoom/pan, and .fc
    # persistence. Pipes (edges) and the real command vocabulary arrive later.
    # The canvas mirrors the Flow canvas machinery (viewport transform,
    # scrollbars, Home reset). Internal symbols stay sh_*/cmd_* (the canvas
    # predates the Connectors name). Future: binding-graph view of the trinity.
    # ═══════════════════════════════════════════════════════════════════════════

    # ── Connectors canvas widgets (live in conn_tab) ──────────────────────────
    _sh_cv_frame = tk.Frame(conn_tab, bg=C['canvas'])
    _sh_cv_frame.pack(side='top', fill='both', expand=True)
    _sh_vsb = tk.Scrollbar(_sh_cv_frame, orient='vertical',   bg=C['palette'])
    _sh_hsb = tk.Scrollbar(_sh_cv_frame, orient='horizontal', bg=C['palette'])
    _sh_hsb.pack(side='bottom', fill='x')
    _sh_vsb.pack(side='right',  fill='y')
    sh_canvas = tk.Canvas(_sh_cv_frame, bg=C['canvas'], highlightthickness=0)
    sh_canvas.pack(fill='both', expand=True)
    sh_inspect = tk.Label(conn_tab, text="Connectors — Add Command, then click the canvas",
                          bg=C['inspect'], fg=C['inspect_fg'],
                          font=('Monospace', 9), anchor='nw', justify='left',
                          padx=8, pady=4, height=3)
    sh_inspect.pack(side='top', fill='x')
    _sh_status_frame = tk.Frame(conn_tab, bg=C['status'])
    _sh_status_frame.pack(side='bottom', fill='x')
    sh_status = tk.Label(_sh_status_frame, text="Ready", anchor='w',
                         bg=C['status'], fg=C['pal_border'],
                         font=('Monospace', 9), padx=8)
    sh_status.pack(side='left', fill='x', expand=True, ipady=3)
    _sh_zoom_lbl = tk.Label(_sh_status_frame, text='Zoom: 100%', anchor='e',
                            bg=C['status'], fg=C['dim'],
                            font=('Monospace', 8), padx=8)
    _sh_zoom_lbl.pack(side='right', ipady=3)

    def _sh_set_status(m): sh_status.config(text=m)
    def _sh_set_inspect(m): sh_inspect.config(text=m)

    # ── Shell viewport state + coord helpers (mirrors Flow canvas) ────────────
    _sh_view = {'zoom': 1.0, 'sx': 0.0, 'sy': 0.0}
    _sh_pan  = [None]
    sh_pal_btns = {}

    def _sh_d2s(dx, dy):
        z = _sh_view['zoom']
        return (dx - _sh_view['sx']) * z, (dy - _sh_view['sy']) * z

    def _sh_s2d(ex, ey):
        z = _sh_view['zoom']
        return ex / z + _sh_view['sx'], ey / z + _sh_view['sy']

    def _sh_update_scrollregion():
        cmds = fc_state.get('cmd_widgets', {})
        cw   = sh_canvas.winfo_width()  or 860
        ch   = sh_canvas.winfo_height() or 660
        if not cmds:
            sh_canvas.config(scrollregion=(0, 0, cw, ch))
            _sh_vsb.set(0.0, 1.0); _sh_hsb.set(0.0, 1.0)
            return
        z = _sh_view['zoom']; pad = 60
        d_min_x = min(c['x'] - CMD_W // 2 for c in cmds.values()) - pad / z
        d_max_x = max(c['x'] + CMD_W // 2 for c in cmds.values()) + pad / z
        d_min_y = min(c['y'] - CMD_H // 2 for c in cmds.values()) - pad / z
        d_max_y = max(c['y'] + CMD_H // 2 for c in cmds.values()) + pad / z
        d_rng_x = max(d_max_x - d_min_x, 1.0)
        d_rng_y = max(d_max_y - d_min_y, 1.0)
        sh_canvas.config(scrollregion=(d_min_x * z, d_min_y * z,
                                       d_max_x * z, d_max_y * z))
        vis_w = cw / z; vis_h = ch / z
        f0x = (_sh_view['sx'] - d_min_x) / d_rng_x
        f0y = (_sh_view['sy'] - d_min_y) / d_rng_y
        _sh_hsb.set(max(0.0, f0x), min(1.0, max(f0x + 0.001, f0x + vis_w / d_rng_x)))
        _sh_vsb.set(max(0.0, f0y), min(1.0, max(f0y + 0.001, f0y + vis_h / d_rng_y)))

    def _sh_vsb_command(*args):
        cmds = fc_state.get('cmd_widgets', {}); z = _sh_view['zoom']; pad = 60
        if cmds:
            d_min_y = min(c['y'] - CMD_H // 2 for c in cmds.values()) - pad / z
            d_max_y = max(c['y'] + CMD_H // 2 for c in cmds.values()) + pad / z
        else:
            d_min_y, d_max_y = 0.0, (sh_canvas.winfo_height() or 660) / z
        d_rng_y = max(d_max_y - d_min_y, 1.0)
        if args[0] == 'moveto':
            _sh_view['sy'] = d_min_y + float(args[1]) * d_rng_y
        elif args[0] == 'scroll':
            n = int(args[1])
            _sh_view['sy'] += (n * GRID if args[2] == 'units'
                               else n * (sh_canvas.winfo_height() or 660) / z)
        _sh_update_scrollregion(); _sh_redraw()

    def _sh_hsb_command(*args):
        cmds = fc_state.get('cmd_widgets', {}); z = _sh_view['zoom']; pad = 60
        if cmds:
            d_min_x = min(c['x'] - CMD_W // 2 for c in cmds.values()) - pad / z
            d_max_x = max(c['x'] + CMD_W // 2 for c in cmds.values()) + pad / z
        else:
            d_min_x, d_max_x = 0.0, (sh_canvas.winfo_width() or 860) / z
        d_rng_x = max(d_max_x - d_min_x, 1.0)
        if args[0] == 'moveto':
            _sh_view['sx'] = d_min_x + float(args[1]) * d_rng_x
        elif args[0] == 'scroll':
            n = int(args[1])
            _sh_view['sx'] += (n * GRID if args[2] == 'units'
                               else n * (sh_canvas.winfo_width() or 860) / z)
        _sh_update_scrollregion(); _sh_redraw()

    def _sh_on_scroll_v(event):
        _sh_view['sy'] += -3 * GRID if event.num == 4 else 3 * GRID
        _sh_update_scrollregion(); _sh_redraw()

    def _sh_on_scroll_h(event):
        _sh_view['sx'] += -3 * GRID if event.num == 4 else 3 * GRID
        _sh_update_scrollregion(); _sh_redraw()

    # ── Shell model helpers ───────────────────────────────────────────────────
    def _sh_cmd_at(x, y):
        """Hit test: return command-widget dict at design coords (x,y) or None."""
        hw, hh = CMD_W // 2, CMD_H // 2
        for c in reversed(list(fc_state['cmd_widgets'].values())):
            if abs(c['x'] - x) <= hw and abs(c['y'] - y) <= hh:
                return c
        return None

    def _sh_sockets(c):
        """Design-space socket geometry for a command widget.
        Returns (inputs, output) where inputs = [(param_name, type, x, y)] on
        the left edge (one per registry input param) and output = (x, y) on the
        right edge. Placeholder / unknown kinds get no typed inputs."""
        hw, hh = CMD_W // 2, CMD_H // 2
        top = c['y'] - hh + 22          # below the header band
        bot = c['y'] + hh
        params = (_flowcode_commands.input_params(c['kind'])
                  if _flowcode_commands else [])
        inputs = []
        n = len(params)
        for i, (pname, ptype) in enumerate(params):
            fy = top + (bot - top) * (i + 1) / (n + 1)
            inputs.append((pname, ptype, c['x'] - hw, fy))
        return inputs, (c['x'] + hw, (top + bot) / 2)

    def _sh_output_hit(x, y, tol=8):
        """Command id whose output socket is within tol design px of (x,y)."""
        for c in reversed(list(fc_state['cmd_widgets'].values())):
            _ins, (ox, oy) = _sh_sockets(c)
            if abs(ox - x) <= tol and abs(oy - y) <= tol:
                return c['id']
        return None

    def _sh_input_hit(x, y, tol=8):
        """(cmd, param_name) whose input socket is within tol of (x,y), or None."""
        for c in reversed(list(fc_state['cmd_widgets'].values())):
            ins, _out = _sh_sockets(c)
            for pname, _pt, ix, iy in ins:
                if abs(ix - x) <= tol and abs(iy - y) <= tol:
                    return c, pname
        return None

    def _sh_edge_compatible(edge):
        """True if a pipe edge's types are compatible (Stage 9-2)."""
        if _flowcode_commands is None:
            return True
        src = fc_state['cmd_widgets'].get(edge['src'])
        dst = fc_state['cmd_widgets'].get(edge['dst'])
        if not src or not dst:
            return False
        return _flowcode_commands.pipe_compatible(
            src['kind'], dst['kind'], edge.get('dst_param', ''))

    def _sh_add_pipe(src_id, dst_id, dst_param):
        """Create (or replace) the pipe feeding (dst_id, dst_param). One pipe per
        input socket. Warns on a type mismatch but still records the edge so the
        red indicator is visible (compile is the hard gate)."""
        edges = fc_state['cmd_edges']
        edges[:] = [e for e in edges
                    if not (e['dst'] == dst_id and e.get('dst_param') == dst_param)]
        edge = {'src': src_id, 'dst': dst_id, 'dst_param': dst_param}
        edges.append(edge)
        if not _sh_edge_compatible(edge):
            _sh_set_status(f"⚠ type mismatch: pipe into .{dst_param} — "
                           f"will error at compile")
        else:
            _sh_set_status(f"Piped → .{dst_param}")

    def _sh_add_cmd(kind, x, y, label=''):
        """Add a command-widget dict to fc_state. Returns the cmd dict."""
        cid = fc_state['cmd_next_id']
        fc_state['cmd_next_id'] += 1
        lbl = label or kind.replace('cmd_', '')
        cmd = {'id': cid, 'kind': kind,
               'x': snap(x), 'y': snap(y),
               'w': CMD_W, 'h': CMD_H,
               'label': lbl,
               'name': _fc_make_default_name(kind, cid),  # Phase 7c-1 default
               'properties': []}
        fc_state['cmd_widgets'][cid] = cmd
        return cmd

    def _sh_remove_cmd(cid):
        """Remove a command widget from fc_state."""
        cmd = fc_state['cmd_widgets'].pop(cid, None)
        if cmd is None: return
        if fc_state['cmd_selected'] == cid:
            fc_state['cmd_selected'] = None
        fc_state['cmd_multi_sel'].discard(cid)
        # Stage 9-2: drop any pipe edges touching the removed command
        fc_state['cmd_edges'][:] = [
            e for e in fc_state['cmd_edges']
            if e['src'] != cid and e['dst'] != cid]

    # ── Shell drawing ─────────────────────────────────────────────────────────
    def _sh_draw_grid():
        cw = sh_canvas.winfo_width() or 860
        ch = sh_canvas.winfo_height() or 660
        z  = _sh_view['zoom']; gstep = GRID * z
        if gstep < 4: return
        ox = (-_sh_view['sx'] * z) % gstep
        oy = (-_sh_view['sy'] * z) % gstep
        x = ox
        while x <= cw:
            sh_canvas.create_line(int(x), 0, int(x), ch, fill=C['grid']); x += gstep
        y = oy
        while y <= ch:
            sh_canvas.create_line(0, int(y), cw, int(y), fill=C['grid']); y += gstep

    def _sh_draw_cmd(c):
        """Draw one command widget: header (name + kind) + body (sockets + pocket)."""
        cid = c['id']
        sel = (cid == fc_state['cmd_selected'] or cid in fc_state['cmd_multi_sel'])
        _xs, _ys = _sh_d2s(c['x'], c['y'])
        x, y = int(_xs), int(_ys)
        z  = _sh_view['zoom']
        hw = int(CMD_W // 2 * z); hh = int(CMD_H // 2 * z)
        L, T, R, B = x - hw, y - hh, x + hw, y + hh
        hdr_h = int(22 * z)
        body_fill = C['selected'] if sel else C['process']
        hdr_fill  = C['selected'] if sel else C['pal_active']
        bor = C['selected'] if sel else C['border']
        lw  = 3 if sel else 2
        _f1 = max(6, int(9 * z))   # header name font
        _f2 = max(5, int(7 * z))   # kind / type font
        # Body + header (header drawn as a band across the top)
        sh_canvas.create_rectangle(L, T, R, B, fill=body_fill, outline=bor, width=lw)
        sh_canvas.create_rectangle(L, T, R, T + hdr_h, fill=hdr_fill, outline=bor, width=lw)
        sh_canvas.create_text((L + R) // 2, T + hdr_h // 2,
                              text=c.get('name') or c['label'],
                              fill=C['text'], font=('Monospace', _f1, 'bold'))
        sh_canvas.create_text((L + R) // 2, T + hdr_h + max(6, int(9 * z)),
                              text=c['kind'].replace('cmd_', ''),
                              fill=C['dim'], font=('Monospace', _f2))
        # Typed sockets (Stage 9-2): one input dot per registry param on the
        # left edge, a single output dot on the right edge. Placeholder kinds
        # fall back to a pair of untyped input dots.
        _sr = max(2, int(4 * z))
        inputs, (ox, oy) = _sh_sockets(c)
        if inputs:
            for pname, _pt, ix, iy in inputs:
                sxp, syp = _sh_d2s(ix, iy)
                sh_canvas.create_oval(sxp - _sr, syp - _sr, sxp + _sr, syp + _sr,
                                      fill=C['io'], outline=bor, width=1)
                if z >= 0.8:
                    sh_canvas.create_text(sxp + _sr + 2, syp, anchor='w',
                                          text=pname, fill=C['dim'],
                                          font=('Monospace', _f2))
        else:
            body_mid = T + hdr_h + (B - (T + hdr_h)) // 2
            for sy in (body_mid - int(12 * z), body_mid + int(12 * z)):
                sh_canvas.create_oval(L - _sr, sy - _sr, L + _sr, sy + _sr,
                                      fill=C['io'], outline=bor, width=1)
        oxs, oys = _sh_d2s(ox, oy)
        sh_canvas.create_oval(oxs - _sr, oys - _sr, oxs + _sr, oys + _sr,
                              fill=C['pal_border'], outline=bor, width=1)  # output
        # Pocket indicator
        sh_canvas.create_text((L + R) // 2, B - max(6, int(10 * z)),
                              text='\U0001F4E6', font=('Monospace', max(6, int(11 * z))))
        if sel:
            sh_canvas.create_text((L + R) // 2, T - max(4, int(9 * z)),
                                  text=f"({c['x']},{c['y']})",
                                  fill=C['selected'], font=('Monospace', _f2))

    def _sh_draw_ghost(x, y):
        x, y = snap(x), snap(y)
        sx, sy = _sh_d2s(x, y); sx, sy = int(sx), int(sy)
        z = _sh_view['zoom']
        hw = int(CMD_W // 2 * z); hh = int(CMD_H // 2 * z)
        sh_canvas.create_rectangle(sx - hw, sy - hh, sx + hw, sy + hh,
                                   fill='#161b30', outline='#3a4060',
                                   width=1, dash=(4, 4))
        sh_canvas.create_text(sx, sy + hh + max(4, int(10 * z)),
                              text=f"snap ({x},{y})", fill='#2a3050',
                              font=('Monospace', max(5, int(7 * z))))

    def _sh_draw_edges():
        """Draw pipe edges: src output socket → dst input socket. Mismatched
        types are drawn red (the edit-time warning)."""
        for e in fc_state['cmd_edges']:
            src = fc_state['cmd_widgets'].get(e['src'])
            dst = fc_state['cmd_widgets'].get(e['dst'])
            if not src or not dst:
                continue
            _ins, (ox, oy) = _sh_sockets(src)
            dins, _o = _sh_sockets(dst)
            tgt = next((s for s in dins if s[0] == e.get('dst_param')), None)
            if tgt is None:
                continue
            x1, y1 = _sh_d2s(ox, oy)
            x2, y2 = _sh_d2s(tgt[2], tgt[3])
            ok = _sh_edge_compatible(e)
            col = C['pal_border'] if ok else '#ff5555'
            sh_canvas.create_line(x1, y1, x2, y2, fill=col,
                                  width=2, arrow='last',
                                  dash=() if ok else (5, 3))

    def _sh_redraw():
        sh_canvas.delete('all')
        _sh_draw_grid()
        _sh_draw_edges()
        for c in fc_state['cmd_widgets'].values():
            _sh_draw_cmd(c)
        # Rubber-band while dragging a new pipe from an output socket
        if fc_state.get('cmd_pipe_src') is not None and fc_state.get('cmd_pipe_xy'):
            src = fc_state['cmd_widgets'].get(fc_state['cmd_pipe_src'])
            if src:
                _ins, (ox, oy) = _sh_sockets(src)
                x1, y1 = _sh_d2s(ox, oy)
                x2, y2 = _sh_d2s(*fc_state['cmd_pipe_xy'])
                sh_canvas.create_line(x1, y1, x2, y2, fill=C['pal_border'],
                                      width=2, arrow='last', dash=(3, 2))
        if fc_state['cmd_mode'] == 'place' and fc_state.get('cmd_ghost'):
            _sh_draw_ghost(*fc_state['cmd_ghost'])

    def _sh_update_inspect():
        cid = fc_state['cmd_selected']
        if cid is not None and cid in fc_state['cmd_widgets']:
            c = fc_state['cmd_widgets'][cid]
            _sh_set_inspect(
                f"Command #{c['id']}  {c['kind']}\n"
                f"  name: {c.get('name','')}   label: {c['label']}\n"
                f"  pos: ({c['x']}, {c['y']})  size: {c['w']}×{c['h']}")
        else:
            _sh_set_inspect("Connectors — Add Command, then click the canvas")

    # ── Shell mode / palette ──────────────────────────────────────────────────
    def _sh_set_mode(mode):
        fc_state['cmd_mode'] = mode
        for m, b in sh_pal_btns.items():
            b.config(bg=C['pal_active'] if m == mode else C['pal_btn'],
                     relief='sunken' if m == mode else 'flat')
        hints = {
            'select': 'Click to select · Drag to move · Dbl-click to rename',
            'place':  'Click canvas to place a command  (Esc to cancel)',
            'delete': 'Click a command to delete',
        }
        _sh_set_status(hints.get(mode, ''))
        _sh_redraw()

    # ── Shell event handlers ──────────────────────────────────────────────────
    def _sh_on_motion(event):
        ddx, ddy = _sh_s2d(event.x, event.y)
        fc_state['cmd_ghost'] = (ddx, ddy)
        # Stage 9-2: dragging a pipe from an output socket
        if fc_state.get('cmd_pipe_src') is not None:
            fc_state['cmd_pipe_xy'] = (ddx, ddy)
            _sh_redraw(); return
        if fc_state['cmd_dragging'] and not (event.state & 0x0100):
            fc_state['cmd_dragging'] = False
        if fc_state['cmd_dragging'] and fc_state['cmd_selected'] is not None:
            c = fc_state['cmd_widgets'].get(fc_state['cmd_selected'])
            if c:
                offx, offy = fc_state['cmd_drag_offset']
                c['x'] = snap(ddx - offx); c['y'] = snap(ddy - offy)
        _sh_redraw()

    def _sh_on_click(event):
        x, y = _sh_s2d(event.x, event.y)
        mode = fc_state['cmd_mode']
        if mode == 'place':
            kind = _sh_pick_command_kind() or 'cmd_placeholder'
            c = _sh_add_cmd(kind, x, y)
            fc_state['cmd_selected'] = c['id']
            _sh_set_status(f"Placed {c.get('name') or c['label']} ({kind})")
            _sh_update_inspect(); _sh_set_mode('select'); return
        if mode == 'delete':
            hit = _sh_cmd_at(x, y)
            if hit:
                lbl = hit.get('name') or hit['label']
                _sh_remove_cmd(hit['id'])
                _sh_set_status(f"Deleted {lbl}")
                _sh_update_inspect()
            _sh_redraw(); return
        # Select mode — an output socket under the cursor starts a pipe drag
        pipe_src = _sh_output_hit(x, y)
        if pipe_src is not None:
            fc_state['cmd_pipe_src'] = pipe_src
            fc_state['cmd_pipe_xy']  = (x, y)
            _sh_set_status('Drag to an input socket to pipe (release to connect)')
            _sh_redraw(); return
        hit = _sh_cmd_at(x, y)
        if hit:
            fc_state['cmd_selected']   = hit['id']
            fc_state['cmd_multi_sel']  = {hit['id']}
            fc_state['cmd_drag_offset']= (x - hit['x'], y - hit['y'])
            fc_state['cmd_dragging']   = True
            fc_state['cmd_drag_origin']= (hit['x'], hit['y'])
        else:
            fc_state['cmd_selected']  = None
            fc_state['cmd_multi_sel'] = set()
            fc_state['cmd_dragging']  = False
        _sh_update_inspect(); _sh_redraw()

    def _sh_on_release(event):
        # Stage 9-2: complete a pipe drag onto an input socket
        if fc_state.get('cmd_pipe_src') is not None:
            x, y = _sh_s2d(event.x, event.y)
            tgt = _sh_input_hit(x, y)
            src_id = fc_state['cmd_pipe_src']
            if tgt and tgt[0]['id'] != src_id:
                _sh_add_pipe(src_id, tgt[0]['id'], tgt[1])
            else:
                _sh_set_status('Pipe cancelled')
            fc_state['cmd_pipe_src'] = None
            fc_state['cmd_pipe_xy']  = None
            _sh_redraw(); return
        if fc_state['cmd_dragging'] and fc_state['cmd_selected'] is not None:
            c = fc_state['cmd_widgets'].get(fc_state['cmd_selected'])
            if c:
                _sh_set_status(f"Moved {c.get('name') or c['label']} → ({c['x']},{c['y']})")
                _sh_update_inspect()
        fc_state['cmd_dragging']    = False
        fc_state['cmd_drag_origin'] = None

    def _sh_on_double_click(event):
        ddx, ddy = _sh_s2d(event.x, event.y)
        hit = _sh_cmd_at(ddx, ddy)
        if hit:
            _sh_open_cmd_props(hit)

    def _sh_pick_command_kind():
        """Modal picker: choose a real command kind from the registry.
        Returns the chosen kind (e.g. 'cmd_math_add') or None if cancelled."""
        if _flowcode_commands is None:
            return None
        names = sorted(_flowcode_commands.command_names())
        dlg = tk.Toplevel(root)
        dlg.title('Add command')
        dlg.configure(bg=C['palette']); dlg.transient(root); dlg.grab_set()
        tk.Label(dlg, text='Choose a command:', bg=C['palette'], fg=C['text'],
                 font=('Monospace', 9), anchor='w').pack(fill='x', padx=8, pady=(8, 2))
        lb = tk.Listbox(dlg, bg=C['inspect'], fg=C['text'], height=14, width=28,
                        font=('Monospace', 9), selectbackground=C['pal_active'])
        for n in names:
            lb.insert('end', n.replace('cmd_', ''))
        lb.pack(padx=8, pady=2)
        if names:
            lb.selection_set(0)
        chosen = {'kind': None}

        def _ok(_e=None):
            sel = lb.curselection()
            if sel:
                chosen['kind'] = names[sel[0]]
            dlg.destroy()

        lb.bind('<Double-Button-1>', _ok)
        lb.bind('<Return>', _ok)
        btns = tk.Frame(dlg, bg=C['palette']); btns.pack(pady=8)
        tk.Button(btns, text='Add', command=_ok, bg=C['pal_btn'], fg=C['text'],
                  font=('Monospace', 9), relief='flat', padx=10).pack(side='left', padx=4)
        tk.Button(btns, text='Cancel', command=dlg.destroy, bg=C['pal_btn'],
                  fg=C['text'], font=('Monospace', 9), relief='flat',
                  padx=10).pack(side='left', padx=4)
        dlg.wait_window()
        return chosen['kind']

    def _sh_open_cmd_props(c):
        """Stage 9-0: minimal dialog to edit a command's name and label, with
        WordStream-level name-uniqueness validation (Phase 7c-1)."""
        dlg = tk.Toplevel(root)
        dlg.title(f"Command #{c['id']}")
        dlg.configure(bg=C['palette']); dlg.transient(root); dlg.resizable(False, False)
        stream = fc_state.get('stream')

        tk.Label(dlg, text='Name (unique):', bg=C['palette'], fg=C['text'],
                 font=('Monospace', 9), anchor='w').grid(row=0, column=0,
                 sticky='w', padx=8, pady=(10, 2))
        name_var = tk.StringVar(value=c.get('name', ''))
        tk.Entry(dlg, textvariable=name_var, bg=C['inspect'], fg=C['text'],
                 insertbackground=C['text'], font=('Monospace', 9), width=24
                 ).grid(row=0, column=1, padx=8, pady=(10, 2))
        tk.Label(dlg, text='Label:', bg=C['palette'], fg=C['text'],
                 font=('Monospace', 9), anchor='w').grid(row=1, column=0,
                 sticky='w', padx=8, pady=2)
        label_var = tk.StringVar(value=c.get('label', ''))
        tk.Entry(dlg, textvariable=label_var, bg=C['inspect'], fg=C['text'],
                 insertbackground=C['text'], font=('Monospace', 9), width=24
                 ).grid(row=1, column=1, padx=8, pady=2)
        warn = tk.Label(dlg, text='', bg=C['palette'], fg='#ff8888',
                        font=('Monospace', 8))
        warn.grid(row=2, column=0, columnspan=2, sticky='w', padx=8)

        def _commit():
            new_name = name_var.get().strip()
            # Phase 7c-1: empty is legal; non-empty must be unique (excluding self)
            if (stream is not None and new_name
                    and stream.name_in_use(new_name, exclude=c)):
                warn.config(text=f"Name '{new_name}' already in use")
                return
            c['name']  = new_name
            c['label'] = label_var.get().strip()
            _sh_update_inspect(); _sh_redraw(); dlg.destroy()

        btns = tk.Frame(dlg, bg=C['palette']); btns.grid(row=3, column=0,
                        columnspan=2, pady=8)
        tk.Button(btns, text='OK', command=_commit, bg=C['pal_btn'], fg=C['text'],
                  font=('Monospace', 9), relief='flat', padx=10).pack(side='left', padx=4)
        tk.Button(btns, text='Cancel', command=dlg.destroy, bg=C['pal_btn'],
                  fg=C['text'], font=('Monospace', 9), relief='flat',
                  padx=10).pack(side='left', padx=4)

    def _sh_on_key(event):
        k = event.keysym.lower()
        if k == 'home':
            _sh_view['zoom'] = 1.0; _sh_view['sx'] = 0.0; _sh_view['sy'] = 0.0
            _sh_update_scrollregion(); _sh_redraw(); _update_zoom_indicator(); return
        if k in ('up', 'kp_up'):
            _sh_view['sy'] -= GRID; _sh_update_scrollregion(); _sh_redraw(); return
        if k in ('down', 'kp_down'):
            _sh_view['sy'] += GRID; _sh_update_scrollregion(); _sh_redraw(); return
        if k in ('left', 'kp_left'):
            _sh_view['sx'] -= GRID; _sh_update_scrollregion(); _sh_redraw(); return
        if k in ('right', 'kp_right'):
            _sh_view['sx'] += GRID; _sh_update_scrollregion(); _sh_redraw(); return
        if k == 'prior':
            _sh_view['sy'] -= (sh_canvas.winfo_height() or 660) / _sh_view['zoom']
            _sh_update_scrollregion(); _sh_redraw(); return
        if k == 'next':
            _sh_view['sy'] += (sh_canvas.winfo_height() or 660) / _sh_view['zoom']
            _sh_update_scrollregion(); _sh_redraw(); return
        if k == 'escape': _sh_set_mode('select')
        elif k == 'delete':
            if fc_state['cmd_selected'] is not None:
                c = fc_state['cmd_widgets'].get(fc_state['cmd_selected'])
                if c:
                    lbl = c.get('name') or c['label']
                    _sh_remove_cmd(fc_state['cmd_selected'])
                    _sh_set_status(f"Deleted {lbl}"); _sh_update_inspect(); _sh_redraw()

    def _sh_on_zoom(event):
        factor = 1.2 if event.num == 4 else (1 / 1.2)
        new_z = max(0.25, min(4.0, _sh_view['zoom'] * factor))
        if new_z == _sh_view['zoom']: return
        dx_b, dy_b = _sh_s2d(event.x, event.y)
        _sh_view['zoom'] = new_z
        _sh_view['sx'] = dx_b - event.x / new_z
        _sh_view['sy'] = dy_b - event.y / new_z
        _sh_update_scrollregion(); _sh_redraw(); _update_zoom_indicator()

    def _sh_pan_start(event):
        _sh_pan[0] = {'ox': _sh_view['sx'], 'oy': _sh_view['sy'],
                      'ex': event.x, 'ey': event.y}
        sh_canvas.config(cursor='fleur')

    def _sh_pan_motion(event):
        if _sh_pan[0] is None: return
        z = _sh_view['zoom']
        _sh_view['sx'] = _sh_pan[0]['ox'] - (event.x - _sh_pan[0]['ex']) / z
        _sh_view['sy'] = _sh_pan[0]['oy'] - (event.y - _sh_pan[0]['ey']) / z
        _sh_update_scrollregion(); _sh_redraw()

    def _sh_pan_end(event):
        _sh_pan[0] = None; sh_canvas.config(cursor='')

    # ── Shell bindings ────────────────────────────────────────────────────────
    _sh_vsb.config(command=_sh_vsb_command)
    _sh_hsb.config(command=_sh_hsb_command)
    sh_canvas.bind('<Enter>',            lambda e: sh_canvas.focus_set())
    sh_canvas.bind('<Button-1>',         _sh_on_click)
    sh_canvas.bind('<B1-Motion>',        _sh_on_motion)
    sh_canvas.bind('<Motion>',           _sh_on_motion)
    sh_canvas.bind('<ButtonRelease-1>',  _sh_on_release)
    sh_canvas.bind('<Double-Button-1>',  _sh_on_double_click)
    sh_canvas.bind('<Key>',              _sh_on_key)
    sh_canvas.bind('<Button-4>',         _sh_on_scroll_v)
    sh_canvas.bind('<Button-5>',         _sh_on_scroll_v)
    sh_canvas.bind('<Shift-Button-4>',   _sh_on_scroll_h)
    sh_canvas.bind('<Shift-Button-5>',   _sh_on_scroll_h)
    sh_canvas.bind('<Control-Button-4>', _sh_on_zoom)
    sh_canvas.bind('<Control-Button-5>', _sh_on_zoom)
    sh_canvas.bind('<Button-2>',         _sh_pan_start)
    sh_canvas.bind('<B2-Motion>',        _sh_pan_motion)
    sh_canvas.bind('<ButtonRelease-2>',  _sh_pan_end)

    # ═══════════════════════════════════════════════════════════════════════════
    # Bundle 23 Piece 3 — Lingo three-pane command-builder interface
    #
    # Native-tkinter IDE chrome (same approach as the GMill tab and the palette).
    # This REPLACES the Stage 9-0 canvas as the active Lingo view. The canvas is
    # kept dormant and reachable from the sidebar "Connectors" toggle — it will be
    # reframed later as a connection-graph view of named bindings across the
    # trinity. Commands here are cosmetic stubs until native TernOO commands land.
    # ═══════════════════════════════════════════════════════════════════════════
    # Stage 9-1A: build the Shell command list from the real registry. Bool
    # params render as flags (checkboxes); other params as labelled entries.
    def _lingo_build_commands():
        out = []
        if _flowcode_commands is None:
            return out
        for full, spec in _flowcode_commands.COMMAND_REGISTRY.items():
            flags, params = [], []
            for p in spec['params']:
                if p['type'] == 'bool':
                    flags.append({'short': p['name'], 'desc': p['name'],
                                  'pname': p['name']})
                else:
                    params.append({'name': p['name'],
                                   'optional': p.get('optional', False)})
            out.append({'name': full[4:], 'full': full, 'desc': spec['desc'],
                        'flags': flags, 'params': params})
        return out
    LINGO_COMMANDS = _lingo_build_commands()
    _lingo = {'active': None, 'filtered': list(LINGO_COMMANDS),
              'flag_vars': {}, 'param_vars': {}, 'pipeline': []}

    # Three-pane builder lives in the Shell tab (sh_tab), packed permanently.
    _lingo_view = tk.Frame(sh_tab, bg=C['bg'])
    _lingo_view.pack(fill='both', expand=True)

    # ── Title bar ─────────────────────────────────────────────────────────────
    _lg_title = tk.Frame(_lingo_view, bg=C['palette'])
    _lg_title.pack(side='top', fill='x')
    tk.Label(_lg_title, text='Shell', bg=C['palette'], fg=C['pal_border'],
             font=('Monospace', 11, 'bold'), padx=8, pady=4).pack(side='left')
    tk.Label(_lg_title, text='— visual command builder', bg=C['palette'],
             fg=C['dim'], font=('Monospace', 8)).pack(side='left')

    _lg_panes = tk.PanedWindow(_lingo_view, orient='horizontal', bg=C['bg'],
                               sashwidth=5, sashrelief='flat', bd=0)
    _lg_panes.pack(side='top', fill='both', expand=True)

    # ── LEFT PANE — command list + search ─────────────────────────────────────
    _lg_left = tk.Frame(_lg_panes, bg=C['palette'])
    _lg_panes.add(_lg_left, minsize=150, width=210)
    tk.Label(_lg_left, text='Commands', bg=C['palette'], fg=C['pal_border'],
             font=('Monospace', 9, 'bold'), anchor='w', padx=6, pady=3).pack(fill='x')
    _lg_search_var = tk.StringVar()
    tk.Entry(_lg_left, textvariable=_lg_search_var, bg=C['inspect'], fg=C['text'],
             insertbackground=C['text'], font=('Monospace', 9),
             relief='flat').pack(fill='x', padx=6, pady=(0, 4), ipady=2)
    _lg_list_wrap = tk.Frame(_lg_left, bg=C['palette'])
    _lg_list_wrap.pack(fill='both', expand=True, padx=6, pady=(0, 6))
    _lg_list_sb = tk.Scrollbar(_lg_list_wrap, orient='vertical')
    _lg_list_sb.pack(side='right', fill='y')
    _lg_listbox = tk.Listbox(_lg_list_wrap, bg=C['inspect'], fg=C['text'],
                             font=('Monospace', 9), relief='flat',
                             selectbackground=C['pal_active'],
                             selectforeground=C['text'], activestyle='none',
                             highlightthickness=0, yscrollcommand=_lg_list_sb.set)
    _lg_listbox.pack(side='left', fill='both', expand=True)
    _lg_list_sb.config(command=_lg_listbox.yview)

    def _lingo_refresh_list():
        q = _lg_search_var.get().lower().strip()
        _lg_listbox.delete(0, 'end')
        _lingo['filtered'] = []
        for c in LINGO_COMMANDS:
            if q in c['name'].lower() or q in c['desc'].lower():
                _lg_listbox.insert('end', f" {c['name']}")
                _lingo['filtered'].append(c)
    _lg_search_var.trace_add('write', lambda *a: _lingo_refresh_list())

    def _lingo_on_select(_e=None):
        sel = _lg_listbox.curselection()
        if sel and sel[0] < len(_lingo['filtered']):
            _lingo_activate(_lingo['filtered'][sel[0]])
    _lg_listbox.bind('<<ListboxSelect>>', _lingo_on_select)

    # ── CENTER PANE — parameter form ──────────────────────────────────────────
    _lg_center = tk.Frame(_lg_panes, bg=C['bg'])
    _lg_panes.add(_lg_center, minsize=240, width=330)
    _lg_name = tk.Label(_lg_center, text='Select a command', bg=C['bg'],
                        fg=C['pal_border'], font=('Monospace', 12, 'bold'),
                        anchor='w', padx=10, pady=4)
    _lg_name.pack(fill='x', pady=(6, 0))
    _lg_desc = tk.Label(_lg_center, text='Pick a command from the left to '
                        'configure it.', bg=C['bg'], fg=C['dim'],
                        font=('Monospace', 9), anchor='w', justify='left',
                        wraplength=300, padx=10)
    _lg_desc.pack(fill='x')
    tk.Frame(_lg_center, bg=C['dim'], height=1).pack(fill='x', padx=10, pady=6)
    _lg_form = tk.Frame(_lg_center, bg=C['bg'])   # rebuilt per command
    _lg_form.pack(fill='both', expand=True, padx=10)
    _lg_actions = tk.Frame(_lg_center, bg=C['bg'])
    _lg_actions.pack(side='bottom', fill='x', padx=10, pady=8)

    # ── RIGHT PANE — output / pipeline ────────────────────────────────────────
    _lg_right = tk.Frame(_lg_panes, bg=C['palette'])
    _lg_panes.add(_lg_right, minsize=170, width=250)
    _lg_tabbar = tk.Frame(_lg_right, bg=C['palette'])
    _lg_tabbar.pack(side='top', fill='x')
    _lg_out_frame  = tk.Frame(_lg_right, bg=C['palette'])
    _lg_pipe_frame = tk.Frame(_lg_right, bg=C['palette'])

    _lg_out = tk.Text(_lg_out_frame, bg=C['inspect'], fg='#7aff7a',
                      font=('Monospace', 10), relief='flat', wrap='word',
                      height=8, padx=8, pady=6,
                      insertbackground='#7aff7a', highlightthickness=0)
    _lg_out.pack(fill='both', expand=True, padx=6, pady=6)

    # ── Piece 3: the Output area is a live REPL. Same command engine the
    # visual Shell compiles to (flowcode_repl.Repl → compile → C emulator);
    # fs commands route through the FileSystem abstraction. ─────────────────
    _repl = [None]
    _repl_hist_pos = [0]
    _REPL_PROMPT = '> '
    try:
        import importlib.util as _rpl_u
        _rpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 '../5500fp/flowcode_repl.py')
        _rpl_spec = _rpl_u.spec_from_file_location('flowcode_repl', _rpl_path)
        _rpl_mod  = _rpl_u.module_from_spec(_rpl_spec)
        _rpl_spec.loader.exec_module(_rpl_mod)
        _repl[0] = _rpl_mod.Repl()
    except Exception as _rpl_err:
        print(f'[FlowCode] REPL engine failed to load: {_rpl_err}')

    def _repl_new_prompt():
        _lg_out.insert('end', _REPL_PROMPT)
        _lg_out.mark_set('repl_input', 'end-1c')
        _lg_out.mark_gravity('repl_input', 'left')
        _lg_out.see('end')

    def _repl_print(text):
        """Program/system output goes above the live prompt line."""
        _lg_out.insert('repl_input linestart', text.rstrip('\n') + '\n')
        _lg_out.see('end')

    def _repl_current_input():
        return _lg_out.get('repl_input', 'end-1c')

    def _repl_set_input(text):
        _lg_out.delete('repl_input', 'end-1c')
        _lg_out.insert('repl_input', text)

    def _repl_enter(_e=None):
        line = _repl_current_input()
        _lg_out.insert('end', '\n')
        if _repl[0] is None:
            _lg_out.insert('end', 'REPL engine unavailable\n')
        elif line.strip():
            try:
                out = _repl[0].execute(line)
            except Exception as ex:
                out = f'error: {ex}'
            if out:
                _lg_out.insert('end', out + '\n')
        _repl_hist_pos[0] = len(_repl[0].history) if _repl[0] else 0
        _repl_new_prompt()
        return 'break'

    def _repl_hist(delta):
        if _repl[0] is None or not _repl[0].history:
            return 'break'
        _repl_hist_pos[0] = max(0, min(len(_repl[0].history),
                                       _repl_hist_pos[0] + delta))
        h = _repl[0].history
        _repl_set_input(h[_repl_hist_pos[0]]
                        if _repl_hist_pos[0] < len(h) else '')
        return 'break'

    def _repl_clear(_e=None):
        _lg_out.delete('1.0', 'end')
        _repl_new_prompt()
        return 'break'

    def _repl_guard(_e=None):
        """Keep edits at/after the prompt: clicks above just move the view."""
        try:
            if _lg_out.compare('insert', '<', 'repl_input'):
                _lg_out.mark_set('insert', 'end-1c')
        except Exception:
            pass

    def _repl_capture(_e=None):
        """Capture-to-Pipeline: last successful registry pipeline becomes
        Connectors widgets + typed pipes."""
        if _repl[0] is None or not _repl[0].capture_last():
            _repl_print('(nothing to capture — run a command pipeline first)')
            return 'break'
        seg_cmds, seg_edges = _repl[0].capture_last()
        idmap = {}
        for old in sorted(seg_cmds):
            nid = fc_state['cmd_next_id']; fc_state['cmd_next_id'] += 1
            c = dict(seg_cmds[old]); c['id'] = nid
            c['x'] = 60 + 180 * len(idmap); c['y'] = 60
            idmap[old] = nid
            fc_state['cmd_widgets'][nid] = c
        for e in seg_edges:
            fc_state['cmd_edges'].append({'src': idmap[e['src']],
                                          'dst': idmap[e['dst']],
                                          'dst_param': e.get('dst_param')})
        _guic_sync_stream()
        _sh_redraw()
        _repl_print(f'captured {len(idmap)} command(s) to Connectors')
        guic_set_status('REPL pipeline captured to Connectors canvas')
        return 'break'

    def _repl_paste(_e=None):
        """Paste at the prompt regardless of where the insert mark sits;
        newlines become spaces so a pasted command stays one line."""
        try:
            clip = root.clipboard_get()
        except Exception:
            return 'break'
        clip = clip.replace('\r', '').replace('\n', ' ').strip()
        _lg_out.mark_set('insert', 'end-1c')
        _lg_out.insert('insert', clip)
        _lg_out.see('end')
        return 'break'

    def _repl_copy(_e=None):
        """Copy the selection (or the current input line if none)."""
        try:
            sel = _lg_out.get('sel.first', 'sel.last')
        except Exception:
            sel = _repl_current_input()
        if sel:
            root.clipboard_clear()
            root.clipboard_append(sel)
        return 'break'

    _repl_menu = tk.Menu(_lg_out, tearoff=0, bg=C['palette'], fg=C['text'],
                         activebackground=C['inspect'],
                         activeforeground=C['text'])
    _repl_menu.add_command(label='Copy', command=_repl_copy)
    _repl_menu.add_command(label='Paste', command=_repl_paste)
    _repl_menu.add_separator()
    _repl_menu.add_command(label='Clear (Ctrl+L)', command=_repl_clear)
    _repl_menu.add_command(label='Capture pipeline (Ctrl+P)',
                           command=_repl_capture)

    def _repl_context(e):
        _repl_menu.tk_popup(e.x_root, e.y_root)
        return 'break'

    _lg_out.bind('<<Paste>>', _repl_paste)
    _lg_out.bind('<Control-Shift-V>', _repl_paste)
    _lg_out.bind('<Control-Shift-v>', _repl_paste)
    _lg_out.bind('<<Copy>>', _repl_copy)
    _lg_out.bind('<Control-Shift-C>', _repl_copy)
    _lg_out.bind('<Control-Shift-c>', _repl_copy)
    _lg_out.bind('<Button-3>', _repl_context)
    _lg_out.bind('<Return>', _repl_enter)
    _lg_out.bind('<Up>',   lambda e: _repl_hist(-1))
    _lg_out.bind('<Down>', lambda e: _repl_hist(+1))
    _lg_out.bind('<Control-l>', _repl_clear)
    _lg_out.bind('<Control-p>', _repl_capture)
    _lg_out.bind('<KeyPress>', _repl_guard, add='+')
    _lg_out.insert('end', 'TernOO Shell — type help for commands; '
                          'Ctrl+P captures the last pipeline\n')
    _repl_new_prompt()
    _lg_pipe_sb = tk.Scrollbar(_lg_pipe_frame, orient='vertical')
    _lg_pipe_sb.pack(side='right', fill='y')
    _lg_pipe = tk.Listbox(_lg_pipe_frame, bg=C['inspect'], fg=C['text'],
                          font=('Monospace', 9), relief='flat', activestyle='none',
                          highlightthickness=0, yscrollcommand=_lg_pipe_sb.set)
    _lg_pipe.pack(side='left', fill='both', expand=True, padx=(6, 0), pady=6)
    _lg_pipe_sb.config(command=_lg_pipe.yview)

    def _lingo_reflect_connectors():
        """Stage 9-2: mirror the Connectors-canvas command pipeline into the
        Pipeline list — each command with its incoming pipes annotated."""
        cmds = fc_state.get('cmd_widgets', {})
        edges = fc_state.get('cmd_edges', [])
        _lg_pipe.delete(0, 'end')
        for i, txt in enumerate(_lingo['pipeline']):
            _lg_pipe.insert('end', f"{i + 1}. {txt}")
        real = {cid: c for cid, c in cmds.items()
                if c.get('kind', '') != 'cmd_placeholder'}
        if real:
            _lg_pipe.insert('end', '── Connectors pipeline ──')
            incoming = {}
            for e in edges:
                incoming.setdefault(e['dst'], []).append(e)
            for cid, c in real.items():
                nm = c.get('name') or c.get('label') or c['kind']
                _lg_pipe.insert('end', f"• {nm}  [{c['kind'].replace('cmd_', '')}]")
                for e in incoming.get(cid, []):
                    src = cmds.get(e['src'], {})
                    sn = src.get('name') or src.get('kind', '?')
                    _lg_pipe.insert('end', f"     {e.get('dst_param')} ← {sn}")

    def _lingo_show_out(mode):
        _lingo['out_mode'] = mode
        _lg_out_frame.pack_forget(); _lg_pipe_frame.pack_forget()
        (_lg_out_frame if mode == 'output' else _lg_pipe_frame).pack(
            fill='both', expand=True)
        if mode == 'pipeline':
            _lingo_reflect_connectors()
        for key, b in _lg_tab_btns.items():
            b.config(fg=C['pal_border'] if key == mode else C['dim'])

    _lg_tab_btns = {}
    for _key, _lbl in (('output', 'Output'), ('pipeline', 'Pipeline')):
        b = tk.Button(_lg_tabbar, text=_lbl, bg=C['palette'], fg=C['dim'],
                      font=('Monospace', 9, 'bold'), relief='flat', bd=0,
                      activebackground=C['palette'], cursor='hand2', padx=10, pady=3,
                      command=lambda k=_key: _lingo_show_out(k))
        b.pack(side='left')
        _lg_tab_btns[_key] = b

    _lg_btnrow = tk.Frame(_lg_right, bg=C['palette'])
    _lg_btnrow.pack(side='bottom', fill='x', padx=6, pady=6)

    # ── Generation + actions ──────────────────────────────────────────────────
    def _lingo_collect_args():
        """Gather the current form values into an args dict for the registry."""
        cmd = _lingo['active']
        args = {}
        if not cmd:
            return args
        for f in cmd['flags']:
            v = _lingo['flag_vars'].get(f['short'])
            args[f.get('pname', f['short'])] = bool(v.get()) if v is not None else False
        for p in cmd['params']:
            v = _lingo['param_vars'].get(p['name'])
            args[p['name']] = v.get() if v is not None else ''
        return args

    def _lingo_generate():
        """Stage 9-1A: run the active command for real and show its result."""
        cmd = _lingo['active']
        if not cmd:
            return ''
        full = cmd.get('full', 'cmd_' + cmd['name'])
        if _flowcode_commands is not None:
            result = _flowcode_commands.run_command(full, _lingo_collect_args())
            if isinstance(result, list):
                result = ', '.join(str(x) for x in result)
            _shown = ', '.join(f"{k}={v!r}" if isinstance(v, str)
                               else f"{k}={v}"
                               for k, v in _lingo_collect_args().items())
            return f"{cmd['name']}({_shown}) → {result}"
        return cmd['name']

    def _lingo_run_interactive():
        """Stage 9-1C: compile the active command on its own and launch it in
        an SDL window so interactive (cmd_io_*) dialogs run for real."""
        import subprocess as _sp, time as _t
        cmd = _lingo['active']
        if not cmd:
            return
        full = cmd.get('full', 'cmd_' + cmd['name'])
        if not _compile_to_t5asm or WordStream is None:
            guic_set_status('Compiler/WordStream unavailable'); return
        if not os.path.isfile(_engine_path) or not os.access(_engine_path, os.X_OK):
            guic_set_status('Engine not built — run make in c_emulator/'); return
        args = _lingo_collect_args()
        stream = WordStream()
        stream._cmd_meta = {1: {
            'id': 1, 'kind': full, 'x': 0, 'y': 0, 'w': 160, 'h': 80,
            'label': '', 'name': f'{full}_1',
            'properties': [{'name': k, 'value': v} for k, v in args.items()],
        }}
        try:
            t5 = _compile_to_t5asm(stream, source_path='<lingo>')
        except Exception as e:
            guic_set_status(f'Compile error: {e}'); return
        tmp = f'/tmp/lingo_{os.getpid()}_{int(_t.time())}.t5asm'
        try:
            with open(tmp, 'w') as f:
                f.write(t5)
            _sp.Popen([_engine_path, '--display', 'sdl', '--run', tmp])
            guic_set_status(f'Running {cmd["name"]} — interact in the SDL window')
        except OSError as e:
            guic_set_status(f'Launch failed: {e}')

    def _lingo_update_preview(*_a):
        txt = _lingo_generate()
        # Piece 3: the Output area is a live REPL now — preview text goes
        # above the prompt instead of wiping/disabling the widget.
        if txt:
            _repl_print(txt)

    def _lingo_activate(cmd):
        _lingo['active'] = cmd
        _lingo['flag_vars'] = {}
        _lingo['param_vars'] = {}
        _lg_name.config(text=cmd['name'])
        _lg_desc.config(text=cmd['desc'])
        for w in _lg_form.winfo_children():
            w.destroy()
        if cmd['flags']:
            tk.Label(_lg_form, text='Flags', bg=C['bg'], fg=C['dim'],
                     font=('Monospace', 8, 'bold'), anchor='w').pack(fill='x', pady=(4, 2))
            for f in cmd['flags']:
                var = tk.BooleanVar(value=False)
                _lingo['flag_vars'][f['short']] = var
                tk.Checkbutton(_lg_form,
                               text=f"{f['short']}   {f['desc']}",
                               variable=var, command=_lingo_update_preview,
                               bg=C['bg'], fg=C['text'], selectcolor=C['inspect'],
                               activebackground=C['bg'], activeforeground=C['text'],
                               font=('Monospace', 9), anchor='w',
                               highlightthickness=0).pack(fill='x')
        if cmd['params']:
            tk.Label(_lg_form, text='Parameters', bg=C['bg'], fg=C['dim'],
                     font=('Monospace', 8, 'bold'), anchor='w').pack(fill='x', pady=(8, 2))
            for p in cmd['params']:
                row = tk.Frame(_lg_form, bg=C['bg']); row.pack(fill='x', pady=2)
                lbl = p['name'] + ('  (optional)' if p.get('optional') else '')
                tk.Label(row, text=lbl, bg=C['bg'], fg=C['text'],
                         font=('Monospace', 9), width=14, anchor='w').pack(side='left')
                var = tk.StringVar()
                _lingo['param_vars'][p['name']] = var
                tk.Entry(row, textvariable=var, bg=C['inspect'], fg=C['text'],
                         insertbackground=C['text'], font=('Monospace', 9),
                         relief='flat').pack(side='left', fill='x', expand=True, ipady=2)
                var.trace_add('write', _lingo_update_preview)
        _lingo_update_preview()

    def _lingo_add_pipeline():
        txt = _lingo_generate()
        if not txt:
            return
        _lingo['pipeline'].append(txt)
        _lg_pipe.insert('end', f"{len(_lingo['pipeline'])}. {txt}")
        _lingo_show_out('pipeline')

    def _lingo_clear_form():
        if _lingo['active']:
            _lingo_activate(_lingo['active'])   # re-create vars empty

    def _lingo_copy():
        txt = _lg_out.get('1.0', 'end').strip()
        if txt:
            root.clipboard_clear(); root.clipboard_append(txt)
            try: guic_set_status(f"Copied to clipboard: {txt[:40]}")
            except Exception: pass

    def _lingo_save():
        # Stub — real .fc partial save lands with native commands (file-ext policy
        # reserves a .shell/.lingo partial). For now, surface what would be saved.
        n = len(_lingo['pipeline'])
        try:
            guic_set_status(f"Save (stub): {n} pipeline step(s) — "
                            f".fc partial save arrives with native commands")
        except Exception:
            pass

    tk.Button(_lg_actions, text='Add to Pipeline', command=_lingo_add_pipeline,
              bg=C['pal_btn'], fg='#7aff7a', font=('Monospace', 9), relief='flat',
              activebackground=C['pal_active'], cursor='hand2', padx=8, pady=4
              ).pack(side='left', padx=(0, 6))
    tk.Button(_lg_actions, text='Run interactively…', command=_lingo_run_interactive,
              bg=C['pal_btn'], fg='#7ad0ff', font=('Monospace', 9), relief='flat',
              activebackground=C['pal_active'], cursor='hand2', padx=8, pady=4
              ).pack(side='left', padx=(0, 6))
    tk.Button(_lg_actions, text='Clear', command=_lingo_clear_form,
              bg=C['pal_btn'], fg='#ff8888', font=('Monospace', 9), relief='flat',
              activebackground=C['pal_active'], cursor='hand2', padx=8, pady=4
              ).pack(side='left')
    tk.Button(_lg_btnrow, text='Copy', command=_lingo_copy,
              bg=C['pal_btn'], fg=C['text'], font=('Monospace', 9), relief='flat',
              activebackground=C['pal_active'], cursor='hand2', padx=10, pady=3
              ).pack(side='left', padx=(0, 6))
    tk.Button(_lg_btnrow, text='Save', command=_lingo_save,
              bg=C['pal_btn'], fg=C['text'], font=('Monospace', 9), relief='flat',
              activebackground=C['pal_active'], cursor='hand2', padx=10, pady=3
              ).pack(side='left')

    _lingo_refresh_list()
    _lingo_show_out('output')

    _lingo_refresh_list()
    _lingo_show_out('output')

    def _lingo_clear_pipeline():
        """Clear the staged pipeline (the Shell tab's clearable content)."""
        _lingo['pipeline'].clear()
        _lg_pipe.delete(0, 'end')
        _lingo_show_out('pipeline')

    # ── Sidebar builders (Bundle 24: Shell and Connectors are now separate) ────
    def _build_shell_tools():
        """Shell tab (three-pane builder) sidebar. The builder is self-contained
        in its three panes, so the sidebar just describes the surface."""
        for w in _pal_tools_frame.winfo_children(): w.destroy()
        pal_btns.clear(); sh_pal_btns.clear()
        _pal_section("SHELL")
        tk.Label(_pal_tools_frame,
                 text='Visual command builder.\nSearch a command, set its\n'
                      'flags & parameters, then\nAdd to Pipeline.',
                 bg=C['palette'], fg=C['dim'], font=('Monospace', 8),
                 anchor='w', justify='left').pack(fill='x', padx=6, pady=4)

    def _build_connectors_tools():
        """Connectors tab (cmd_* canvas) sidebar — Stage 9-0 placement tools."""
        for w in _pal_tools_frame.winfo_children(): w.destroy()
        pal_btns.clear(); sh_pal_btns.clear()
        _pal_section("TOOLS")
        for _lbl, _mode, _fg in [
            ('☞ Select',      'select', '#aaaaff'),
            ('➕ Add Command', 'place',  '#7aff7a'),
            ('✕ Delete',      'delete', '#ff8888'),
        ]:
            b = tk.Button(_pal_tools_frame, text=_lbl,
                          bg=C['pal_btn'], fg=_fg, font=('Monospace', 9),
                          relief='flat', activebackground=C['pal_active'],
                          activeforeground=C['text'], cursor='hand2', padx=4, pady=4,
                          command=lambda m=_mode: _sh_set_mode(m))
            b.pack(fill='x', padx=6, pady=2)
            sh_pal_btns[_mode] = b
        _sh_set_mode(fc_state['cmd_mode'])

    root.after(220, _sh_redraw)

    # ═══════════════════════════════════════════════════════════════════════════
    # Stage 8-1 — Sheet tab: spreadsheet grid (third leg of the trinity)
    #
    # Cells are cell_* metadata dicts keyed by (row, col) in fc_state['cells'],
    # aliased to WordStream._cell_meta so names join the global namespace.
    # The grid uses the same viewport transform as the other canvases. Headers
    # (row numbers / column letters) are drawn in design space (scroll with the
    # grid) for scaffolding simplicity.
    # ═══════════════════════════════════════════════════════════════════════════
    _sheet_fbar = tk.Frame(sheet_tab, bg=C['palette'])   # formula bar (8-2 fills it)
    _sheet_fbar.pack(side='top', fill='x')
    tk.Label(_sheet_fbar, text=' fx ', bg=C['palette'], fg=C['pal_border'],
             font=('Monospace', 9, 'bold')).pack(side='left')
    _sheet_addr_lbl = tk.Label(_sheet_fbar, text='A1', bg=C['palette'], fg=C['dim'],
                               font=('Monospace', 9), width=6, anchor='w')
    _sheet_addr_lbl.pack(side='left', padx=(0, 4))
    _sheet_fbar_var = tk.StringVar()
    _sheet_fbar_result = tk.Label(_sheet_fbar, text='', bg=C['palette'],
                                  fg='#7aff7a', font=('Monospace', 9), anchor='e')
    _sheet_fbar_result.pack(side='right', padx=6)
    _sheet_fbar_entry = tk.Entry(_sheet_fbar, textvariable=_sheet_fbar_var,
                                 bg=C['inspect'], fg=C['text'], insertbackground=C['text'],
                                 font=('Monospace', 9), relief='flat')
    _sheet_fbar_entry.pack(side='left', fill='x', expand=True, padx=4, ipady=2)

    _sheet_cv_frame = tk.Frame(sheet_tab, bg=C['canvas'])
    _sheet_cv_frame.pack(side='top', fill='both', expand=True)
    _sht_vsb = tk.Scrollbar(_sheet_cv_frame, orient='vertical',   bg=C['palette'])
    _sht_hsb = tk.Scrollbar(_sheet_cv_frame, orient='horizontal', bg=C['palette'])
    _sht_hsb.pack(side='bottom', fill='x')
    _sht_vsb.pack(side='right',  fill='y')
    sheet_canvas = tk.Canvas(_sheet_cv_frame, bg=C['canvas'], highlightthickness=0)
    sheet_canvas.pack(fill='both', expand=True)
    _sheet_status_frame = tk.Frame(sheet_tab, bg=C['status'])
    _sheet_status_frame.pack(side='bottom', fill='x')
    sheet_status = tk.Label(_sheet_status_frame, text="Ready", anchor='w',
                            bg=C['status'], fg=C['pal_border'],
                            font=('Monospace', 9), padx=8)
    sheet_status.pack(side='left', fill='x', expand=True, ipady=3)
    _sht_zoom_lbl = tk.Label(_sheet_status_frame, text='Zoom: 100%', anchor='e',
                             bg=C['status'], fg=C['dim'], font=('Monospace', 8), padx=8)
    _sht_zoom_lbl.pack(side='right', ipady=3)

    def _sheet_set_status(m): sheet_status.config(text=m)

    # ── Viewport ──────────────────────────────────────────────────────────────
    _sht_view = {'zoom': 1.0, 'sx': 0.0, 'sy': 0.0}
    _sht_pan  = [None]

    def _sht_d2s(dx, dy):
        z = _sht_view['zoom']
        return (dx - _sht_view['sx']) * z, (dy - _sht_view['sy']) * z

    def _sht_s2d(ex, ey):
        z = _sht_view['zoom']
        return ex / z + _sht_view['sx'], ey / z + _sht_view['sy']

    def _sheet_extent():
        """Visible grid size: at least the default, expanding to include cells."""
        nr, nc = SHEET_ROWS, SHEET_COLS
        for (r, c) in fc_state['cells']:
            nr = max(nr, r + 2); nc = max(nc, c + 2)
        return nr, nc

    def _sht_update_scrollregion():
        nr, nc = _sheet_extent()
        z = _sht_view['zoom']
        w = (SHEET_ROW_HDR_W + nc * CELL_W) * z
        h = (SHEET_COL_HDR_H + nr * CELL_H) * z
        sheet_canvas.config(scrollregion=(-_sht_view['sx'] * z, -_sht_view['sy'] * z,
                                          w - _sht_view['sx'] * z, h - _sht_view['sy'] * z))
        cw = sheet_canvas.winfo_width()  or 860
        ch = sheet_canvas.winfo_height() or 660
        rng_x = max(w, 1.0); rng_y = max(h, 1.0)
        f0x = (_sht_view['sx'] * z) / rng_x
        f0y = (_sht_view['sy'] * z) / rng_y
        _sht_hsb.set(max(0.0, f0x), min(1.0, max(f0x + 0.001, f0x + cw / rng_x)))
        _sht_vsb.set(max(0.0, f0y), min(1.0, max(f0y + 0.001, f0y + ch / rng_y)))

    def _sht_vsb_command(*args):
        z = _sht_view['zoom']
        if args[0] == 'moveto':
            nr, _ = _sheet_extent()
            _sht_view['sy'] = float(args[1]) * (SHEET_COL_HDR_H + nr * CELL_H)
        elif args[0] == 'scroll':
            _sht_view['sy'] += int(args[1]) * CELL_H
        _sht_view['sy'] = max(0.0, _sht_view['sy'])
        _sht_update_scrollregion(); _sheet_redraw()

    def _sht_hsb_command(*args):
        if args[0] == 'moveto':
            _, nc = _sheet_extent()
            _sht_view['sx'] = float(args[1]) * (SHEET_ROW_HDR_W + nc * CELL_W)
        elif args[0] == 'scroll':
            _sht_view['sx'] += int(args[1]) * CELL_W
        _sht_view['sx'] = max(0.0, _sht_view['sx'])
        _sht_update_scrollregion(); _sheet_redraw()

    def _sht_on_scroll_v(event):
        _sht_view['sy'] = max(0.0, _sht_view['sy'] + (-CELL_H if event.num == 4 else CELL_H) * 3)
        _sht_update_scrollregion(); _sheet_redraw()

    def _sht_on_scroll_h(event):
        _sht_view['sx'] = max(0.0, _sht_view['sx'] + (-CELL_W if event.num == 4 else CELL_W) * 3)
        _sht_update_scrollregion(); _sheet_redraw()

    # ── Cell model helpers ────────────────────────────────────────────────────
    def _sheet_cell_rect(row, col):
        """Design-space rect (L, T, R, B) for cell (row, col)."""
        L = SHEET_ROW_HDR_W + col * CELL_W
        T = SHEET_COL_HDR_H + row * CELL_H
        return L, T, L + CELL_W, T + CELL_H

    def _sheet_cell_at(dx, dy):
        """Design coords → (row, col) cell, or None if over a header."""
        if dx < SHEET_ROW_HDR_W or dy < SHEET_COL_HDR_H:
            return None
        col = int((dx - SHEET_ROW_HDR_W) // CELL_W)
        row = int((dy - SHEET_COL_HDR_H) // CELL_H)
        if row < 0 or col < 0:
            return None
        return (row, col)

    def _sheet_make_cell_name(row, col):
        base = f"cell_{_sheet_a1(row, col)}"
        stream = fc_state.get('stream')
        if stream is None:
            return base
        nm, n = base, 1
        while stream.name_in_use(nm):
            nm = f"{base}_{n}"; n += 1
        return nm

    def _sheet_detect_kind(text):
        """Stage 8-2 auto-detect: leading '=' → cell_formula; number/bool →
        cell_value; otherwise cell_text."""
        t = text.strip()
        if t.startswith('='):
            return 'cell_formula'
        try:
            int(t); return 'cell_value'
        except ValueError:
            pass
        try:
            float(t); return 'cell_value'
        except ValueError:
            pass
        if t.lower() in ('true', 'false'):
            return 'cell_value'
        return 'cell_text'

    def _sheet_recompute():
        """Stage 8-3: evaluate every formula cell; store result/error on the
        cell as '_result' / '_error'. Re-run after any cell change."""
        if _sheet_formula is None:
            return
        # Stage 8-8: context for WIDGET(...).prop and SIGNAL_LAST(...).
        def _ctx_widget_prop(name, prop):
            for w in fc_state['widgets'].values():
                if w.get('name') == name:
                    v = _guic_get_prop_value(w, prop)
                    return v if v is not None else w.get(prop)
            return None
        # No runtime signal state in the editor → last value is 0 (never fired).
        _ctx = {'widget_prop': _ctx_widget_prop, 'signal_last': lambda nm: 0}
        results, errors = _sheet_formula.evaluate_sheet(fc_state['cells'], _ctx)
        for rc, cell in fc_state['cells'].items():
            cell.pop('_result', None); cell.pop('_error', None)
            if cell.get('kind') == 'cell_formula':
                if rc in errors:
                    cell['_error'] = errors[rc]
                elif rc in results:
                    cell['_result'] = _sheet_formula.format_result(results[rc])
        if errors:
            _sheet_set_status(f"{len(errors)} formula error(s): "
                              + ", ".join(f"{_sheet_a1(*rc)} {e}"
                                          for rc, e in list(errors.items())[:3]))
        # Stage 8-4: bound GUI widgets read cell values — refresh them.
        try: guic_redraw()
        except Exception: pass

    def _sheet_value_by_name(name):
        """Stage 8-4: display value of the cell named `name`, or None."""
        if not name:
            return None
        for cell in fc_state['cells'].values():
            if cell.get('name') == name:
                return _sheet_display(cell)
        return None

    def _sheet_cell_by_name(name):
        """(row, col) of the cell named `name`, or None."""
        for rc, cell in fc_state['cells'].items():
            if cell.get('name') == name:
                return rc
        return None

    def _sheet_all_cell_names():
        return sorted(c.get('name', '') for c in fc_state['cells'].values()
                      if c.get('name'))

    def _sheet_fmt_number(cell, text):
        """Stage 8-7: apply number formatting (decimals/currency/percent) to a
        numeric display string; non-numeric text passes through unchanged."""
        try:
            v = float(text)
        except (ValueError, TypeError):
            return text
        if cell.get('fmt_percent'):
            v *= 100.0
        dec = cell.get('fmt_decimals')
        s = (f"{v:.{int(dec)}f}" if dec not in (None, '') else
             (f"{int(v)}" if v == int(v) else f"{v:g}"))
        if cell.get('fmt_currency'):
            s = '$' + s
        if cell.get('fmt_percent'):
            s = s + '%'
        return s

    def _sheet_display(cell):
        """Visible text for a cell. Stage 8-3: formula cells render their
        evaluated result (or error); value/text render their literal.
        Stage 8-7: numeric content honours the cell's number format."""
        if cell.get('kind') == 'cell_formula':
            if '_error' in cell:
                return cell['_error']
            if '_result' in cell:
                return _sheet_fmt_number(cell, cell['_result'])
            return str(cell.get('value', ''))   # not yet computed
        if cell.get('kind') == 'cell_value':
            return _sheet_fmt_number(cell, str(cell.get('value', '')))
        return str(cell.get('value', ''))

    def _sheet_set_cell(row, col, text):
        """Create / update / delete the cell at (row, col) from `text`."""
        cells = fc_state['cells']
        if text == '':
            cells.pop((row, col), None)   # empty clears the cell
            return
        existing = cells.get((row, col))
        kind = _sheet_detect_kind(text)
        if existing is None:
            cid = fc_state['cell_next_id']; fc_state['cell_next_id'] += 1
            cells[(row, col)] = {
                'id': cid, 'kind': kind, 'row': row, 'col': col,
                'name': _sheet_make_cell_name(row, col),
                'label': _sheet_a1(row, col), 'value': text, 'properties': []}
        else:
            existing['kind'] = kind
            existing['value'] = text

    def _clear_sheet():
        fc_state['cells'].clear()
        fc_state['cell_next_id'] = 0
        fc_state['sheet_regions'].clear()
        fc_state['free_cells'].clear()
        fc_state['region_next_id'] = 0
        fc_state['cell_sel'] = (0, 0)
        _sheet_cancel_edit()
        _sheet_set_status('Sheet cleared'); _sheet_redraw()

    # ── Stage 8-9: free-form regions ──────────────────────────────────────────
    def _sheet_add_region(dx, dy):
        rid = fc_state['region_next_id']; fc_state['region_next_id'] += 1
        reg = {'id': rid, 'kind': 'sheet_region',
               'x': int(dx), 'y': int(dy), 'w': 240, 'h': 120,
               'name': _sheet_make_region_name(rid),
               'label': f'region_{rid}'}
        fc_state['sheet_regions'][rid] = reg
        return reg

    def _sheet_make_region_name(rid):
        base = f"region_{rid}"
        stream = fc_state.get('stream')
        if stream is None:
            return base
        nm, n = base, 1
        while stream.name_in_use(nm):
            nm = f"{base}_{n}"; n += 1
        return nm

    def _sheet_region_at(dx, dy):
        """Topmost region containing design point (dx, dy), or None."""
        for reg in reversed(list(fc_state['sheet_regions'].values())):
            if (reg['x'] <= dx <= reg['x'] + reg['w'] and
                    reg['y'] <= dy <= reg['y'] + reg['h']):
                return reg
        return None

    def _sheet_add_free_cell(reg, dx, dy):
        """Create a free (absolutely-positioned) cell inside a region."""
        cid = fc_state['cell_next_id']; fc_state['cell_next_id'] += 1
        cell = {'id': cid, 'kind': 'cell_text', 'region_id': reg['id'],
                'px': int(dx - reg['x']), 'py': int(dy - reg['y']),
                'name': _sheet_make_cell_name(0, 0).replace('cell_A1', f'cell_f{cid}'),
                'label': f'f{cid}', 'value': '', 'properties': []}
        # ensure a clean unique name
        cell['name'] = f"cell_free_{cid}"
        fc_state['free_cells'][cid] = cell
        return cell

    def _sheet_free_cell_rect(cell):
        """Design-space rect of a free cell (positioned within its region)."""
        reg = fc_state['sheet_regions'].get(cell.get('region_id'))
        bx = reg['x'] if reg else 0
        by = reg['y'] if reg else 0
        L = bx + cell.get('px', 0); T = by + cell.get('py', 0)
        return L, T, L + CELL_W, T + CELL_H

    # ── Drawing ───────────────────────────────────────────────────────────────
    def _sheet_redraw():
        sheet_canvas.delete('all')
        z = _sht_view['zoom']
        cw = sheet_canvas.winfo_width()  or 860
        ch = sheet_canvas.winfo_height() or 660
        nr, nc = _sheet_extent()
        hdr_fill = C['pal_active']; grid_col = C['grid']
        # Column header (letters) + row gutter (numbers)
        for col in range(nc):
            L, _, R, _ = _sheet_cell_rect(0, col)
            sx, _sy = _sht_d2s(L, 0); ex, _ = _sht_d2s(R, 0)
            sel_c = (fc_state['cell_sel'][1] == col)
            sheet_canvas.create_rectangle(sx, 0, ex, SHEET_COL_HDR_H * z,
                                          fill=C['selected'] if sel_c else hdr_fill,
                                          outline=grid_col)
            sheet_canvas.create_text((sx + ex) / 2, SHEET_COL_HDR_H * z / 2,
                                     text=_sheet_col_label(col), fill=C['text'],
                                     font=('Monospace', max(6, int(8 * z)), 'bold'))
        for row in range(nr):
            _, T, _, B = _sheet_cell_rect(row, 0)
            _sx, sy = _sht_d2s(0, T); _, ey = _sht_d2s(0, B)
            sel_r = (fc_state['cell_sel'][0] == row)
            sheet_canvas.create_rectangle(0, sy, SHEET_ROW_HDR_W * z, ey,
                                          fill=C['selected'] if sel_r else hdr_fill,
                                          outline=grid_col)
            sheet_canvas.create_text(SHEET_ROW_HDR_W * z / 2, (sy + ey) / 2,
                                     text=str(row + 1), fill=C['text'],
                                     font=('Monospace', max(6, int(8 * z))))
        # Grid cells
        for row in range(nr):
            for col in range(nc):
                L, T, R, B = _sheet_cell_rect(row, col)
                sx, sy = _sht_d2s(L, T); ex, ey = _sht_d2s(R, B)
                if ex < SHEET_ROW_HDR_W * z or ey < SHEET_COL_HDR_H * z:
                    continue
                if sx > cw or sy > ch:
                    continue
                cell = fc_state['cells'].get((row, col))
                # Stage 8-7: per-cell background colour
                bgfill = (cell.get('fmt_bg') if cell and cell.get('fmt_bg')
                          else C['canvas'])
                sheet_canvas.create_rectangle(sx, sy, ex, ey, fill=bgfill,
                                              outline=grid_col)
                # Stage 8-6: port-binding indicator dot (cyan entry / amber exit)
                _pb = (_flowcode_ports.cell_bound_port(cell)
                       if (cell and _flowcode_ports is not None) else None)
                if _pb:
                    _dr = max(2, int(3 * z))
                    _dc = '#00e5ff' if _pb['direction'] == 'entry' else '#ffb000'
                    sheet_canvas.create_oval(ex - _dr * 2 - 2, sy + 2,
                                             ex - 2, sy + _dr * 2 + 2,
                                             fill=_dc, outline='')
                if cell:
                    # Stage 8-2 per-kind defaults: numbers right, text/formula
                    # left, formula in accent colour. Stage 8-7 format overrides.
                    k = cell.get('kind')
                    fsz = max(6, int(9 * z))
                    fnt = (('Monospace', fsz, 'bold') if cell.get('fmt_bold')
                           else ('Monospace', fsz))
                    align = cell.get('fmt_align') or (
                        'right' if k == 'cell_value' else 'left')
                    if cell.get('fmt_fg'):
                        col_fill = cell['fmt_fg']
                    elif k == 'cell_formula':
                        col_fill = C['pal_border']
                    else:
                        col_fill = C['text']
                    if align == 'right':
                        tx, anc = ex - 4, 'e'
                    elif align == 'center':
                        tx, anc = (sx + ex) / 2, 'center'
                    else:
                        tx, anc = sx + 4, 'w'
                    sheet_canvas.create_text(tx, (sy + ey) / 2,
                                             text=_sheet_display(cell), anchor=anc,
                                             fill=col_fill, font=fnt)
        # Stage 8-9: free-form regions (dashed boundary) + their free cells
        for reg in fc_state['sheet_regions'].values():
            rx, ry = _sht_d2s(reg['x'], reg['y'])
            rex, rey = _sht_d2s(reg['x'] + reg['w'], reg['y'] + reg['h'])
            sheet_canvas.create_rectangle(rx, ry, rex, rey, outline=C['pal_border'],
                                          width=2, dash=(6, 4))
            sheet_canvas.create_text(rx + 4, ry + max(7, int(8 * z)),
                                     text=reg.get('label', ''), anchor='w',
                                     fill=C['pal_border'],
                                     font=('Monospace', max(6, int(7 * z))))
        for cell in fc_state['free_cells'].values():
            L, T, R, B = _sheet_free_cell_rect(cell)
            sx, sy = _sht_d2s(L, T); ex, ey = _sht_d2s(R, B)
            sheet_canvas.create_rectangle(sx, sy, ex, ey, fill=C['canvas'],
                                          outline=C['dim'])
            sheet_canvas.create_text(sx + 4, (sy + ey) / 2, text=_sheet_display(cell),
                                     anchor='w', fill=C['text'],
                                     font=('Monospace', max(6, int(9 * z))))
        # Selection highlight (grid cell)
        srow, scol = fc_state['cell_sel']
        L, T, R, B = _sheet_cell_rect(srow, scol)
        sx, sy = _sht_d2s(L, T); ex, ey = _sht_d2s(R, B)
        sheet_canvas.create_rectangle(sx, sy, ex, ey, outline=C['selected'],
                                      width=2)
        # Reposition the in-place editor if active
        if fc_state['cell_editing']:
            _sheet_place_editor()

    # ── In-place editor ───────────────────────────────────────────────────────
    _sheet_edit = tk.Entry(sheet_canvas, bg='#ffffff', fg='#000000',
                           insertbackground='#000000', font=('Monospace', 9),
                           relief='solid', bd=1)
    _sheet_edit_var = tk.StringVar()
    _sheet_edit.config(textvariable=_sheet_edit_var)

    _free_edit = [None]   # Stage 8-9: id of the free cell being edited, or None

    def _sheet_place_editor():
        if _free_edit[0] is not None:
            cell = fc_state['free_cells'].get(_free_edit[0])
            L, T, R, B = _sheet_free_cell_rect(cell)
        else:
            srow, scol = fc_state['cell_sel']
            L, T, R, B = _sheet_cell_rect(srow, scol)
        sx, sy = _sht_d2s(L, T); ex, ey = _sht_d2s(R, B)
        _sheet_edit.place(x=int(sx) + 1, y=int(sy) + 1,
                          width=int(ex - sx) - 2, height=int(ey - sy) - 2)
        _sheet_edit.focus_set()

    def _sheet_begin_edit(initial=None):
        srow, scol = fc_state['cell_sel']
        cell = fc_state['cells'].get((srow, scol))
        if initial is not None:
            _sheet_edit_var.set(initial)
        else:
            _sheet_edit_var.set(cell.get('value', '') if cell else '')
        fc_state['cell_editing'] = True
        _sheet_place_editor()
        _sheet_edit.icursor('end')

    def _sheet_begin_free_edit(cell):
        _free_edit[0] = cell['id']
        _sheet_edit_var.set(cell.get('value', ''))
        fc_state['cell_editing'] = True
        _sheet_place_editor()
        _sheet_edit.icursor('end')

    def _sheet_commit_edit(advance=(1, 0)):
        if not fc_state['cell_editing']:
            return
        if _free_edit[0] is not None:          # Stage 8-9: free cell
            cell = fc_state['free_cells'].get(_free_edit[0])
            if cell is not None:
                txt = _sheet_edit_var.get()
                if txt == '':
                    fc_state['free_cells'].pop(_free_edit[0], None)
                else:
                    cell['value'] = txt
                    cell['kind'] = _sheet_detect_kind(txt)
            _sheet_cancel_edit(); _sheet_recompute(); _sheet_redraw()
            return
        srow, scol = fc_state['cell_sel']
        _sheet_set_cell(srow, scol, _sheet_edit_var.get())
        _sheet_cancel_edit()
        if fc_state.get('stream') is not None:
            fc_state['stream'].ensure_unique_names()
        _sheet_recompute()       # Stage 8-3: re-evaluate dependents
        _sheet_move_sel(*advance)
        _sheet_redraw()

    def _sheet_cancel_edit():
        fc_state['cell_editing'] = False
        _free_edit[0] = None
        _sheet_edit.place_forget()
        sheet_canvas.focus_set()

    def _sheet_move_sel(dr, dc):
        r, c = fc_state['cell_sel']
        fc_state['cell_sel'] = (max(0, r + dr), max(0, c + dc))
        _sheet_sync_fbar()

    def _sheet_sync_fbar():
        r, c = fc_state['cell_sel']
        _sheet_addr_lbl.config(text=_sheet_a1(r, c))
        cell = fc_state['cells'].get((r, c))
        _sheet_fbar_var.set(cell.get('value', '') if cell else '')
        # Stage 8-3: show the evaluated result of a formula cell (=A1+B1 → 42)
        if cell and cell.get('kind') == 'cell_formula':
            res = cell.get('_error') or cell.get('_result', '')
            _sheet_fbar_result.config(text=f"→ {res}" if res != '' else '')
        else:
            _sheet_fbar_result.config(text='')

    # ── Event handlers ────────────────────────────────────────────────────────
    def _sheet_on_click(event):
        if fc_state['cell_editing']:
            _sheet_commit_edit(advance=(0, 0))
        dx, dy = _sht_s2d(event.x, event.y)
        if fc_state['sheet_mode'] == 'place_region':   # Stage 8-9
            reg = _sheet_add_region(snap(dx), snap(dy))
            fc_state['sheet_mode'] = 'select'
            _sheet_set_status(f"Placed {reg['label']} — double-click inside to add a cell")
            _build_sheet_tools(); _sheet_redraw(); return
        hit = _sheet_cell_at(dx, dy)
        if hit:
            fc_state['cell_sel'] = hit
            _sheet_sync_fbar()
        _sheet_redraw()

    def _sheet_on_double(event):
        dx, dy = _sht_s2d(event.x, event.y)
        # Stage 8-9: double-click inside a region → free (absolutely-positioned)
        # cell; double-click a free cell edits it.
        for cell in reversed(list(fc_state['free_cells'].values())):
            L, T, R, B = _sheet_free_cell_rect(cell)
            if L <= dx <= R and T <= dy <= B:
                _sheet_begin_free_edit(cell); return
        reg = _sheet_region_at(dx, dy)
        if reg is not None:
            cell = _sheet_add_free_cell(reg, dx, dy)
            _sheet_redraw(); _sheet_begin_free_edit(cell); return
        hit = _sheet_cell_at(dx, dy)
        if hit:
            fc_state['cell_sel'] = hit; _sheet_sync_fbar()
            _sheet_begin_edit()

    def _sheet_on_rclick(event):
        """Stage 8-7: right-click a cell → Format cell dialog."""
        dx, dy = _sht_s2d(event.x, event.y)
        hit = _sheet_cell_at(dx, dy)
        if hit:
            fc_state['cell_sel'] = hit; _sheet_sync_fbar(); _sheet_redraw()
            _sheet_format_dialog(*hit)

    def _sheet_format_dialog(row, col):
        cell = fc_state['cells'].get((row, col))
        if cell is None:   # format an empty cell → create a blank text cell
            cid = fc_state['cell_next_id']; fc_state['cell_next_id'] += 1
            cell = {'id': cid, 'kind': 'cell_text', 'row': row, 'col': col,
                    'name': _sheet_make_cell_name(row, col),
                    'label': _sheet_a1(row, col), 'value': '', 'properties': []}
            fc_state['cells'][(row, col)] = cell
        dlg = tk.Toplevel(root); dlg.title(f"Format {_sheet_a1(row, col)}")
        dlg.configure(bg=C['palette']); dlg.transient(root); dlg.resizable(False, False)
        r = [0]
        def addrow(lbl):
            tk.Label(dlg, text=lbl, bg=C['palette'], fg=C['text'],
                     font=('Monospace', 9), anchor='e', width=12
                     ).grid(row=r[0], column=0, padx=8, pady=3, sticky='e')
        addrow('Align:')
        align_var = tk.StringVar(value=cell.get('fmt_align', ''))
        ttk.Combobox(dlg, textvariable=align_var, width=10,
                     values=['', 'left', 'center', 'right']
                     ).grid(row=r[0], column=1, padx=8, pady=3, sticky='w'); r[0] += 1
        addrow('Bold:')
        bold_var = tk.BooleanVar(value=bool(cell.get('fmt_bold')))
        tk.Checkbutton(dlg, variable=bold_var, bg=C['palette'], selectcolor=C['canvas'],
                       activebackground=C['palette']).grid(row=r[0], column=1, sticky='w', padx=8); r[0] += 1
        addrow('Decimals:')
        dec_var = tk.StringVar(value=str(cell.get('fmt_decimals', '')))
        tk.Entry(dlg, textvariable=dec_var, width=6, bg=C['canvas'], fg=C['text'],
                 insertbackground=C['text']).grid(row=r[0], column=1, sticky='w', padx=8); r[0] += 1
        addrow('Currency $:')
        cur_var = tk.BooleanVar(value=bool(cell.get('fmt_currency')))
        tk.Checkbutton(dlg, variable=cur_var, bg=C['palette'], selectcolor=C['canvas'],
                       activebackground=C['palette']).grid(row=r[0], column=1, sticky='w', padx=8); r[0] += 1
        addrow('Percent %:')
        pct_var = tk.BooleanVar(value=bool(cell.get('fmt_percent')))
        tk.Checkbutton(dlg, variable=pct_var, bg=C['palette'], selectcolor=C['canvas'],
                       activebackground=C['palette']).grid(row=r[0], column=1, sticky='w', padx=8); r[0] += 1
        addrow('Text colour:')
        fg_var = tk.StringVar(value=cell.get('fmt_fg', ''))
        tk.Entry(dlg, textvariable=fg_var, width=10, bg=C['canvas'], fg=C['text'],
                 insertbackground=C['text']).grid(row=r[0], column=1, sticky='w', padx=8); r[0] += 1
        addrow('Cell colour:')
        bg_var = tk.StringVar(value=cell.get('fmt_bg', ''))
        tk.Entry(dlg, textvariable=bg_var, width=10, bg=C['canvas'], fg=C['text'],
                 insertbackground=C['text']).grid(row=r[0], column=1, sticky='w', padx=8); r[0] += 1

        # ── Stage 8-6: cell ↔ port binding ───────────────────────────────────
        if _flowcode_ports is not None:
            _fp = _flowcode_ports
            addrow('Port binding:')
            b = _fp.cell_bound_port(cell)
            bind_lbl = tk.Label(dlg, bg=C['palette'], fg=C['text'],
                                font=('Monospace', 8), anchor='w',
                                text=(f"{b['container_name']}.{b['port_name']} "
                                      f"({b['direction']})" if b else '(none)'))
            bind_lbl.grid(row=r[0], column=1, sticky='w', padx=8); r[0] += 1

            def _do_bind():
                conts = {s['name']: s for s in fc_state['flow_symbols'].values()
                         if _fp.is_container(s.get('kind', ''))
                         and (s.get('entry_points') or s.get('exit_points'))}
                if not conts:
                    _sheet_set_status('No containers with ports to bind to')
                    return
                bd = tk.Toplevel(dlg); bd.configure(bg=C['palette'])
                bd.title('Bind cell to port'); bd.transient(dlg); bd.grab_set()
                cvar = tk.StringVar(value=sorted(conts)[0])
                pvar = tk.StringVar()
                tk.Label(bd, text='Container:', bg=C['palette'], fg=C['text'],
                         font=('Monospace', 9)).grid(row=0, column=0, padx=8, pady=4, sticky='e')
                tk.Label(bd, text='Port:', bg=C['palette'], fg=C['text'],
                         font=('Monospace', 9)).grid(row=1, column=0, padx=8, pady=4, sticky='e')
                cmenu = ttk.Combobox(bd, textvariable=cvar, width=18,
                                     values=sorted(conts), state='readonly')
                cmenu.grid(row=0, column=1, padx=8, pady=4, sticky='w')
                pmenu = ttk.Combobox(bd, textvariable=pvar, width=18, state='readonly')
                pmenu.grid(row=1, column=1, padx=8, pady=4, sticky='w')
                warn = tk.Label(bd, text='', bg=C['palette'], fg='#ff8888',
                                font=('Monospace', 8))
                warn.grid(row=2, column=0, columnspan=2, sticky='w', padx=8)

                def _refresh_ports(*_a):
                    sym = conts.get(cvar.get(), {})
                    opts = ([f"{p['name']} (entry)" for p in _fp.entry_points(sym)]
                            + [f"{p['name']} (exit)" for p in _fp.exit_points(sym)])
                    pmenu['values'] = opts
                    if opts:
                        pvar.set(opts[0])
                cmenu.bind('<<ComboboxSelected>>', _refresh_ports)
                _refresh_ports()

                def _commit_bind():
                    sym = conts.get(cvar.get())
                    sel = pvar.get()
                    if not sel:
                        return
                    pname = sel.rsplit(' (', 1)[0]
                    direction = 'entry' if sel.endswith('(entry)') else 'exit'
                    ok, msg = _fp.validate_cell_binding(cell, sym, pname, direction)
                    if not ok:
                        warn.config(text=msg); return
                    cell['bound_to_port'] = _fp.make_cell_binding(
                        cvar.get(), pname, direction)
                    bd.destroy(); _sheet_redraw(); dlg.destroy()
                    _sheet_set_status(f"Bound {cell.get('name')} → "
                                      f"{cvar.get()}.{pname} ({direction})")

                bfr = tk.Frame(bd, bg=C['palette']); bfr.grid(row=3, column=0,
                                                              columnspan=2, pady=8)
                tk.Button(bfr, text='Bind', command=_commit_bind, bg=C['pal_btn'],
                          fg=C['text'], relief='flat', padx=10).pack(side='left', padx=4)
                tk.Button(bfr, text='Cancel', command=bd.destroy, bg=C['pal_btn'],
                          fg=C['text'], relief='flat', padx=10).pack(side='left', padx=4)

            def _do_unbind():
                cell.pop('bound_to_port', None)
                _sheet_redraw(); dlg.destroy()
                _sheet_set_status('Port binding removed')

            pbtns = tk.Frame(dlg, bg=C['palette'])
            pbtns.grid(row=r[0], column=0, columnspan=2, pady=(0, 4)); r[0] += 1
            tk.Button(pbtns, text='Bind to port…', command=_do_bind, bg=C['pal_btn'],
                      fg=C['text'], relief='flat', padx=8,
                      font=('Monospace', 8)).pack(side='left', padx=4)
            if b:
                tk.Button(pbtns, text='Unbind', command=_do_unbind, bg=C['pal_btn'],
                          fg='#ff8888', relief='flat', padx=8,
                          font=('Monospace', 8)).pack(side='left', padx=4)

        def _apply():
            def setf(key, val):
                if val in ('', None, False):
                    cell.pop(key, None)
                else:
                    cell[key] = val
            setf('fmt_align', align_var.get().strip())
            setf('fmt_bold', bool(bold_var.get()))
            d = dec_var.get().strip()
            setf('fmt_decimals', int(d) if d.isdigit() else '')
            setf('fmt_currency', bool(cur_var.get()))
            setf('fmt_percent', bool(pct_var.get()))
            setf('fmt_fg', fg_var.get().strip())
            setf('fmt_bg', bg_var.get().strip())
            _sheet_redraw(); dlg.destroy()
        btns = tk.Frame(dlg, bg=C['palette']); btns.grid(row=r[0], column=0, columnspan=2, pady=8)
        tk.Button(btns, text='Apply', command=_apply, bg=C['pal_btn'], fg=C['text'],
                  relief='flat', padx=10).pack(side='left', padx=4)
        tk.Button(btns, text='Cancel', command=dlg.destroy, bg=C['pal_btn'], fg=C['text'],
                  relief='flat', padx=10).pack(side='left', padx=4)

    def _sheet_edit_key(event):
        k = event.keysym
        if k == 'Return':
            _sheet_commit_edit(advance=(-1, 0) if (event.state & 0x0001) else (1, 0)); return 'break'
        if k == 'Tab':
            _sheet_commit_edit(advance=(0, 1)); return 'break'
        if k == 'ISO_Left_Tab':
            _sheet_commit_edit(advance=(0, -1)); return 'break'
        if k == 'Escape':
            _sheet_cancel_edit(); _sheet_redraw(); return 'break'

    def _sheet_on_key(event):
        if fc_state['cell_editing']:
            return
        k = event.keysym
        if k == 'Home':
            _sht_view['zoom'] = 1.0; _sht_view['sx'] = 0.0; _sht_view['sy'] = 0.0
            _sht_update_scrollregion(); _sheet_redraw(); _update_zoom_indicator(); return
        nav = {'Up': (-1, 0), 'Down': (1, 0), 'Left': (0, -1), 'Right': (0, 1),
               'Tab': (0, 1), 'Return': (1, 0)}
        if k in nav:
            dr, dc = nav[k]
            if k == 'Tab' and (event.state & 0x0001): dc = -1
            if k == 'Return' and (event.state & 0x0001): dr = -1
            _sheet_move_sel(dr, dc); _sheet_redraw(); return 'break'
        if k == 'BackSpace' or k == 'Delete':
            r, c = fc_state['cell_sel']
            fc_state['cells'].pop((r, c), None)
            _sheet_recompute(); _sheet_sync_fbar(); _sheet_redraw(); return
        if k == 'F2':
            _sheet_begin_edit(); return
        # Typing a printable char starts an edit pre-filled with that char
        if len(event.char) == 1 and event.char.isprintable():
            _sheet_begin_edit(initial=event.char); return 'break'

    def _sheet_fbar_commit(event=None):
        r, c = fc_state['cell_sel']
        _sheet_set_cell(r, c, _sheet_fbar_var.get())
        if fc_state.get('stream') is not None:
            fc_state['stream'].ensure_unique_names()
        _sheet_recompute()       # Stage 8-3
        _sheet_redraw()

    def _sheet_on_zoom(event):
        factor = 1.2 if event.num == 4 else (1 / 1.2)
        new_z = max(0.4, min(3.0, _sht_view['zoom'] * factor))
        if new_z == _sht_view['zoom']: return
        dx_b, dy_b = _sht_s2d(event.x, event.y)
        _sht_view['zoom'] = new_z
        _sht_view['sx'] = max(0.0, dx_b - event.x / new_z)
        _sht_view['sy'] = max(0.0, dy_b - event.y / new_z)
        _sht_update_scrollregion(); _sheet_redraw(); _update_zoom_indicator()

    def _sht_pan_start(event):
        _sht_pan[0] = {'ox': _sht_view['sx'], 'oy': _sht_view['sy'], 'ex': event.x, 'ey': event.y}
        sheet_canvas.config(cursor='fleur')

    def _sht_pan_motion(event):
        if _sht_pan[0] is None: return
        z = _sht_view['zoom']
        _sht_view['sx'] = max(0.0, _sht_pan[0]['ox'] - (event.x - _sht_pan[0]['ex']) / z)
        _sht_view['sy'] = max(0.0, _sht_pan[0]['oy'] - (event.y - _sht_pan[0]['ey']) / z)
        _sht_update_scrollregion(); _sheet_redraw()

    def _sht_pan_end(event):
        _sht_pan[0] = None; sheet_canvas.config(cursor='')

    _sht_vsb.config(command=_sht_vsb_command)
    _sht_hsb.config(command=_sht_hsb_command)
    sheet_canvas.bind('<Enter>',            lambda e: sheet_canvas.focus_set())
    sheet_canvas.bind('<Button-1>',         _sheet_on_click)
    sheet_canvas.bind('<Double-Button-1>',  _sheet_on_double)
    sheet_canvas.bind('<Button-3>',         _sheet_on_rclick)
    sheet_canvas.bind('<Key>',              _sheet_on_key)
    sheet_canvas.bind('<Button-4>',         _sht_on_scroll_v)
    sheet_canvas.bind('<Button-5>',         _sht_on_scroll_v)
    sheet_canvas.bind('<Shift-Button-4>',   _sht_on_scroll_h)
    sheet_canvas.bind('<Shift-Button-5>',   _sht_on_scroll_h)
    sheet_canvas.bind('<Control-Button-4>', _sheet_on_zoom)
    sheet_canvas.bind('<Control-Button-5>', _sheet_on_zoom)

    def _sheet_ctrl_click(event):
        """Stage 8-6: Ctrl+click a port-bound cell → jump to its container."""
        dx, dy = _sht_s2d(event.x, event.y)
        hit = _sheet_cell_at(dx, dy)
        cell = fc_state['cells'].get(hit) if hit else None
        b = (_flowcode_ports.cell_bound_port(cell)
             if (cell and _flowcode_ports is not None) else None)
        if not b:
            _sheet_set_status('Ctrl+click a port-bound cell to jump to its container')
            return 'break'
        csym = _fc_sym_by_name(b['container_name'])
        if csym is None:
            _sheet_set_status(f"Container {b['container_name']} not found")
            return 'break'
        notebook.select(0)                       # Flow tab
        _nav_center_flow_on(csym['id'])
        set_status(f"→ {b['container_name']}.{b['port_name']} ({b['direction']})")
        return 'break'
    sheet_canvas.bind('<Control-Button-1>', _sheet_ctrl_click)

    sheet_canvas.bind('<Button-2>',         _sht_pan_start)
    sheet_canvas.bind('<B2-Motion>',        _sht_pan_motion)
    sheet_canvas.bind('<ButtonRelease-2>',  _sht_pan_end)
    _sheet_edit.bind('<Key>',               _sheet_edit_key)
    _sheet_fbar_entry.bind('<Return>',      _sheet_fbar_commit)

    def _build_sheet_tools():
        """Sheet tab sidebar — tools + info."""
        for w in _pal_tools_frame.winfo_children(): w.destroy()
        pal_btns.clear()
        _pal_section("TOOLS")
        def _set_region_mode():
            fc_state['sheet_mode'] = 'place_region'
            _sheet_set_status('Click the grid to place a free-form region')
            _build_sheet_tools()
        for _lbl, _active, _fg, _cmd in [
            ('☞ Select', fc_state['sheet_mode'] == 'select', '#aaaaff',
             lambda: (fc_state.update(sheet_mode='select'), _build_sheet_tools())),
            ('▦ Add Region', fc_state['sheet_mode'] == 'place_region', '#7aff7a',
             _set_region_mode),
        ]:
            tk.Button(_pal_tools_frame, text=_lbl,
                      bg=C['pal_active'] if _active else C['pal_btn'], fg=_fg,
                      font=('Monospace', 9), relief='sunken' if _active else 'flat',
                      activebackground=C['pal_active'], cursor='hand2', padx=4, pady=4,
                      command=_cmd).pack(fill='x', padx=6, pady=2)
        tk.Frame(_pal_tools_frame, bg=C['dim'], height=1).pack(fill='x', padx=6, pady=3)
        tk.Label(_pal_tools_frame,
                 text='Click a cell to select.\nDouble-click or type to edit.\n'
                      'Tab/Enter/arrows navigate.\nAdd Region → free-form area;\n'
                      'double-click inside it to\nplace a free cell.',
                 bg=C['palette'], fg=C['dim'], font=('Monospace', 8),
                 anchor='w', justify='left').pack(fill='x', padx=6, pady=4)

    root.after(230, _sheet_redraw)

    def _build_gristmill_tools():
        """Lingo tab (vocabulary explorer) sidebar — read-only."""
        for w in _pal_tools_frame.winfo_children(): w.destroy()
        pal_btns.clear()
        _pal_section("TOOLS")
        tk.Label(_pal_tools_frame, text='(read-only)', bg=C['palette'], fg=C['dim'],
                 font=('Monospace', 7), pady=2).pack(fill='x', padx=4)

    def _rebuild_sidebar_tools():
        """Rebuild the tab-aware tools section for the currently active tab.
        Tab order (Stage 8-1): Flow | GUI | Sheet | Shell | Connectors | Lingo."""
        idx = notebook.index('current')
        if idx == 0:   _build_flow_tools()
        elif idx == 1: _build_gui_tools()
        elif idx == 2: _build_sheet_tools()        # spreadsheet grid
        elif idx == 3: _build_shell_tools()        # three-pane builder
        elif idx == 4: _build_connectors_tools()   # cmd_* canvas
        else:          _build_gristmill_tools()    # Lingo vocabulary explorer

    def _on_tab_change(event):
        idx = notebook.index('current')
        _rebuild_sidebar_tools()   # ← Bundle 17 A8: rebuild tools per tab
        _update_zoom_indicator()   # ← Bundle 18: refresh zoom % for active canvas
        # Destroy any GHOST-panel tooltip that survived the tab switch
        if _guic_active_tip[0]:
            try: _guic_active_tip[0].destroy()
            except Exception: pass
            _guic_active_tip[0] = None
        if idx == 1:   guic_redraw()
        elif idx == 2: _sheet_redraw()  # Sheet grid
        elif idx == 4: _sh_redraw()    # Connectors canvas
        elif idx == 5:
            # Lingo (vocabulary explorer) — force refresh on switch
            try: _gristmill_view._rebuild_program()
            except Exception: pass
        elif idx == 0: redraw()
    notebook.bind('<<NotebookTabChanged>>', _on_tab_change)

    root.after(200, guic_redraw)

    # ═══════════════════════════════════════════════════════════════════════════
    # End GHOST Canvas
    # ═══════════════════════════════════════════════════════════════════════════

    # ── Phase 6C: FlowCodeTabView — subscribes to WordStream changes ──────────
    class FlowCodeTabView:
        """Subscribes to the shared WordStream; triggers FlowCode canvas redraw.

        fc_state['flow_symbols'] and fc_state['flow_edges'] are the primary representation;
        this view keeps the tkinter canvas in sync when the stream changes (e.g.
        after undo/redo or after a cross-tab load).
        """
        def on_stream_change(self):
            """Called by WordStream._notify() whenever words change."""
            try:
                root.after_idle(redraw)
            except Exception:
                pass   # root may not yet exist during startup

    _flowcode_tab_view = FlowCodeTabView()
    if fc_state.get('stream') is not None:
        fc_state['stream'].subscribe(_flowcode_tab_view.on_stream_change)

    # ── Bundle 13: GristMillTabView — OTree/vocabulary explorer ──────────────
    _gristmill_view = None
    _gmtv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '../5500fp/gristmill_tab_view.py')
    if os.path.exists(_gmtv_path):
        try:
            import importlib.util as _gmtv_u
            _gmtv_spec = _gmtv_u.spec_from_file_location('gristmill_tab_view', _gmtv_path)
            _gmtv_mod  = _gmtv_u.module_from_spec(_gmtv_spec)
            _gmtv_spec.loader.exec_module(_gmtv_mod)
            _gristmill_view = _gmtv_mod.GristMillTabView(_lingo_vocab_frame, fc_state, C, root)
            if fc_state.get('stream') is not None:
                fc_state['stream'].subscribe(_gristmill_view.on_stream_change)
        except Exception as _gmtv_err:
            import traceback
            traceback.print_exc()
            print(f'[FlowCode] GristMill tab failed to load: {_gmtv_err}')

    # ── Text/language bundle: model plumbing shared by Text tab, Translator
    # and the Shell REPL. flowcode.py stays the only fc_state expert; the
    # view modules receive closures. ─────────────────────────────────────────
    def _dialect_model():
        return {'widgets': fc_state['widgets'],
                'flows': fc_state['flow_symbols'],
                'cells': fc_state['cells'],
                'cmds': fc_state['cmd_widgets'],
                'flow_edges': fc_state['flow_edges'],
                'cmd_edges': fc_state['cmd_edges'],
                'notes': []}

    def _apply_dialect_model(model):
        """Replace program state with a parsed dialect model, then run the
        same refresh sequence the Open path uses."""
        fc_state['widgets'].clear(); fc_state['widgets'].update(model['widgets'])
        fc_state['edges'].clear()
        fc_state['flow_symbols'].clear()
        fc_state['flow_symbols'].update(model['flows'])
        fc_state['flow_edges'].clear()
        fc_state['flow_edges'].extend(model['flow_edges'])
        fc_state['cells'].clear(); fc_state['cells'].update(model['cells'])
        fc_state['cmd_widgets'].clear()
        fc_state['cmd_widgets'].update(model['cmds'])
        fc_state['cmd_edges'].clear()
        fc_state['cmd_edges'].extend(model['cmd_edges'])
        fc_state['flow_selected'] = None
        fc_state['flow_multi_sel'].clear()
        _guic_sync_stream()
        redraw()
        guic_layout_all()
        guic_redraw()
        _sh_redraw()
        _sheet_recompute()
        _sheet_redraw()
        if _translator_view[0] is not None:
            _translator_view[0].refresh()

    _text_tab_view = [None]
    _ttv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             '../5500fp/text_tab_view.py')
    if os.path.exists(_ttv_path):
        try:
            import importlib.util as _ttv_u
            _ttv_spec = _ttv_u.spec_from_file_location('text_tab_view', _ttv_path)
            _ttv_mod  = _ttv_u.module_from_spec(_ttv_spec)
            _ttv_spec.loader.exec_module(_ttv_mod)
            _text_tab_view[0] = _ttv_mod.TextTabView(
                text_tab, C, root, _dialect_model, _apply_dialect_model,
                guic_set_status)
        except Exception as _ttv_err:
            import traceback; traceback.print_exc()
            print(f'[FlowCode] Text tab failed to load: {_ttv_err}')

    _gtv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             '../5500fp/ghost_tab_view.py')
    _ghost_tab_view = [None]
    if os.path.exists(_gtv_path):
        try:
            import importlib.util as _gtv_u
            _gtv_spec = _gtv_u.spec_from_file_location('ghost_tab_view',
                                                       _gtv_path)
            _gtv_mod = _gtv_u.module_from_spec(_gtv_spec)
            _gtv_spec.loader.exec_module(_gtv_mod)
            _ghost_tab_view[0] = _gtv_mod.GhostTabView(
                academy_tab, C, root, guic_set_status)
        except Exception as _gtv_err:
            import traceback; traceback.print_exc()
            print(f'[FlowCode] GHOST tab failed to load: {_gtv_err}')

    _trv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             '../5500fp/translator_view.py')
    if os.path.exists(_trv_path):
        try:
            import importlib.util as _trv_u
            _trv_spec = _trv_u.spec_from_file_location('translator_view', _trv_path)
            _trv_mod  = _trv_u.module_from_spec(_trv_spec)
            _translator_view[0] = _trv_mod.TranslatorView(
                _lingo_trans_frame, C, _dialect_model)
        except Exception as _trv_err:
            import traceback; traceback.print_exc()
            print(f'[FlowCode] Translator failed to load: {_trv_err}')

    # ── Bundle 18: zoom indicator update helper ───────────────────────────────
    def _update_zoom_indicator():
        """Refresh zoom % labels for the active canvas."""
        _fc_zoom_lbl.config(text=f"Zoom: {int(_fc_view['zoom'] * 100)}%")
        _gc_zoom_lbl.config(text=f"Zoom: {int(_gc_view['zoom'] * 100)}%")
        _sh_zoom_lbl.config(text=f"Zoom: {int(_sh_view['zoom'] * 100)}%")  # Stage 9-0
        _sht_zoom_lbl.config(text=f"Zoom: {int(_sht_view['zoom'] * 100)}%")  # Stage 8-1

    # ── Bundle 18: Flow canvas zoom / pan bindings ────────────────────────────
    def _fc_on_zoom(event):
        factor = 1.2 if event.num == 4 else (1 / 1.2)
        new_z = max(0.25, min(4.0, _fc_view['zoom'] * factor))
        if new_z == _fc_view['zoom']: return
        # Keep design coord under cursor fixed after zoom (D7)
        dx_b, dy_b = _fc_s2d(event.x, event.y)
        _fc_view['zoom'] = new_z
        _fc_view['sx'] = dx_b - event.x / new_z
        _fc_view['sy'] = dy_b - event.y / new_z
        _fc_update_scrollregion(); redraw(); _update_zoom_indicator()

    def _fc_pan_start(event):
        _fc_pan[0] = {'ox': _fc_view['sx'], 'oy': _fc_view['sy'],
                      'ex': event.x, 'ey': event.y}
        tk_canvas.config(cursor='fleur')

    def _fc_pan_motion(event):
        if _fc_pan[0] is None: return
        z = _fc_view['zoom']
        _fc_view['sx'] = _fc_pan[0]['ox'] - (event.x - _fc_pan[0]['ex']) / z
        _fc_view['sy'] = _fc_pan[0]['oy'] - (event.y - _fc_pan[0]['ey']) / z
        _fc_update_scrollregion(); redraw()

    def _fc_pan_end(event):
        _fc_pan[0] = None
        tk_canvas.config(cursor='')

    # Bundle 21: wire scrollbar commands and touchpad/keyboard scroll
    _fc_vsb.config(command=_fc_vsb_command)
    _fc_hsb.config(command=_fc_hsb_command)
    tk_canvas.bind('<Button-4>',       _fc_on_scroll_v)   # touchpad / wheel up
    tk_canvas.bind('<Button-5>',       _fc_on_scroll_v)   # touchpad / wheel down
    tk_canvas.bind('<Shift-Button-4>', _fc_on_scroll_h)   # shift+wheel left
    tk_canvas.bind('<Shift-Button-5>', _fc_on_scroll_h)   # shift+wheel right
    # Ctrl+Wheel = zoom (Bundle 18)
    tk_canvas.bind('<Control-Button-4>', _fc_on_zoom)
    tk_canvas.bind('<Control-Button-5>', _fc_on_zoom)
    tk_canvas.bind('<Button-2>',     _fc_pan_start)
    tk_canvas.bind('<B2-Motion>',    _fc_pan_motion)
    tk_canvas.bind('<ButtonRelease-2>', _fc_pan_end)

    # ── Bundle 18: GUI canvas zoom / pan bindings ─────────────────────────────
    def _gc_on_zoom(event):
        factor = 1.2 if event.num == 4 else (1 / 1.2)
        new_z = max(0.25, min(4.0, _gc_view['zoom'] * factor))
        if new_z == _gc_view['zoom']: return
        dx_b, dy_b = _gc_s2d(event.x, event.y)
        _gc_view['zoom'] = new_z
        _gc_view['sx'] = dx_b - event.x / new_z
        _gc_view['sy'] = dy_b - event.y / new_z
        _gc_update_scrollregion(); guic_redraw(); _update_zoom_indicator()

    def _gc_pan_start(event):
        _gc_pan[0] = {'ox': _gc_view['sx'], 'oy': _gc_view['sy'],
                      'ex': event.x, 'ey': event.y}
        guic.config(cursor='fleur')

    def _gc_pan_motion(event):
        if _gc_pan[0] is None: return
        z = _gc_view['zoom']
        _gc_view['sx'] = _gc_pan[0]['ox'] - (event.x - _gc_pan[0]['ex']) / z
        _gc_view['sy'] = _gc_pan[0]['oy'] - (event.y - _gc_pan[0]['ey']) / z
        _gc_update_scrollregion(); guic_redraw()

    def _gc_pan_end(event):
        _gc_pan[0] = None
        guic.config(cursor='')

    # ── Bundle 21: GUI canvas scrollbar command callbacks ─────────────────────

    def _gc_vsb_command(*args):
        """Drive _gc_view['sy'] from vertical scrollbar (moveto / scroll)."""
        wgts = fc_state.get('widgets', {})
        z    = _gc_view['zoom']
        pad  = 60
        if wgts:
            all_pos = [guic_abs_pos(w) for w in wgts.values()]
            wgts_l  = list(wgts.values())
            d_min_y = min(ay - w.get('h', GH) // 2
                          for (_, ay), w in zip(all_pos, wgts_l)) - pad / z
            d_max_y = max(ay + w.get('h', GH) // 2
                          for (_, ay), w in zip(all_pos, wgts_l)) + pad / z
        else:
            d_min_y, d_max_y = 0.0, (guic.winfo_height() or 660) / z
        d_rng_y = max(d_max_y - d_min_y, 1.0)
        if args[0] == 'moveto':
            _gc_view['sy'] = d_min_y + float(args[1]) * d_rng_y
        elif args[0] == 'scroll':
            n = int(args[1])
            _gc_view['sy'] += (n * GH if args[2] == 'units'
                               else n * (guic.winfo_height() or 660) / z)
        _gc_update_scrollregion(); guic_redraw()

    def _gc_hsb_command(*args):
        """Drive _gc_view['sx'] from horizontal scrollbar (moveto / scroll)."""
        wgts = fc_state.get('widgets', {})
        z    = _gc_view['zoom']
        pad  = 60
        if wgts:
            all_pos = [guic_abs_pos(w) for w in wgts.values()]
            wgts_l  = list(wgts.values())
            d_min_x = min(ax - w.get('w', GW) // 2
                          for (ax, _), w in zip(all_pos, wgts_l)) - pad / z
            d_max_x = max(ax + w.get('w', GW) // 2
                          for (ax, _), w in zip(all_pos, wgts_l)) + pad / z
        else:
            d_min_x, d_max_x = 0.0, (guic.winfo_width() or 860) / z
        d_rng_x = max(d_max_x - d_min_x, 1.0)
        if args[0] == 'moveto':
            _gc_view['sx'] = d_min_x + float(args[1]) * d_rng_x
        elif args[0] == 'scroll':
            n = int(args[1])
            _gc_view['sx'] += (n * GW if args[2] == 'units'
                               else n * (guic.winfo_width() or 860) / z)
        _gc_update_scrollregion(); guic_redraw()

    def _gc_on_scroll_v(event):
        """Touchpad / mouse-wheel vertical scroll on GUI canvas."""
        _gc_view['sy'] += -3 * GH if event.num == 4 else 3 * GH
        _gc_update_scrollregion(); guic_redraw()

    def _gc_on_scroll_h(event):
        """Touchpad / mouse-wheel horizontal scroll on GUI canvas."""
        _gc_view['sx'] += -3 * GW if event.num == 4 else 3 * GW
        _gc_update_scrollregion(); guic_redraw()

    # Bundle 21: wire GUI scrollbar commands and touchpad scroll
    _gc_vsb.config(command=_gc_vsb_command)
    _gc_hsb.config(command=_gc_hsb_command)
    guic.bind('<Button-4>',       _gc_on_scroll_v)
    guic.bind('<Button-5>',       _gc_on_scroll_v)
    guic.bind('<Shift-Button-4>', _gc_on_scroll_h)
    guic.bind('<Shift-Button-5>', _gc_on_scroll_h)
    # Ctrl+Wheel = zoom (Bundle 18)
    guic.bind('<Control-Button-4>', _gc_on_zoom)
    guic.bind('<Control-Button-5>', _gc_on_zoom)
    guic.bind('<Button-2>',         _gc_pan_start)
    guic.bind('<B2-Motion>',        _gc_pan_motion)
    guic.bind('<ButtonRelease-2>',  _gc_pan_end)

    # ── Bundle 18: Flow canvas bindings ───────────────────────────────────────
    tk_canvas.bind('<Enter>',          lambda e: tk_canvas.focus_set())
    tk_canvas.bind('<Button-1>',       on_click)
    tk_canvas.bind('<B1-Motion>',      on_motion)
    tk_canvas.bind('<Motion>',         on_motion)
    tk_canvas.bind('<ButtonRelease-1>',on_release)
    tk_canvas.bind('<Double-Button-1>',on_double_click)
    tk_canvas.bind('<Leave>',          lambda e: _hide_tooltip())
    root.bind('<Key>',on_key)

    # ── Phase 7c-3: Ctrl+click cross-tab navigation ───────────────────────────
    # Ctrl+click a GUI widget → jump to its handler terminator (or offer to
    # create it); Ctrl+click a flow_terminator → jump to the widget it handles.
    def _nav_center_flow_on(sym_id):
        s = fc_state['flow_symbols'].get(sym_id)
        if not s:
            return
        # Phase 7c-4: drill into the target's pocket scope if it lives in one.
        if fc_state.get('flow_scope') != s.get('parent_scope'):
            fc_state['flow_scope'] = s.get('parent_scope')
            _fc_build_breadcrumb()
        cw = tk_canvas.winfo_width() or 860
        ch = tk_canvas.winfo_height() or 660
        z  = _fc_view['zoom']
        _fc_view['sx'] = s['x'] - (cw / 2) / z
        _fc_view['sy'] = s['y'] - (ch / 2) / z
        state['selected_sym']     = sym_id
        state['selected_edge']    = None
        fc_state['flow_selected'] = sym_id
        _fc_update_scrollregion(); redraw(); update_inspect()

    def _nav_center_gui_on(wid):
        w = fc_state['widgets'].get(wid)
        if not w:
            return
        ax, ay = guic_abs_pos(w)
        cw = guic.winfo_width() or 860
        ch = guic.winfo_height() or 660
        z  = _gc_view['zoom']
        _gc_view['sx'] = ax - (cw / 2) / z
        _gc_view['sy'] = ay - (ch / 2) / z
        fc_state['selected']  = wid
        fc_state['multi_sel'] = {wid}
        _gc_update_scrollregion(); guic_redraw(); guic_rebuild_prop_panel()

    def _nav_center_sheet_on(rc):
        """Stage 8-4: jump to the Sheet tab and select cell (row, col)."""
        notebook.select(2)
        fc_state['cell_sel'] = rc
        _sheet_sync_fbar(); _sheet_redraw()

    def _nav_find_terminator_by_name(name):
        if not name:
            return None
        for s in fc_state['flow_symbols'].values():
            if s.get('kind') == 'flow_terminator' and s.get('name', '') == name:
                return s
        return None

    def _nav_find_widget_for_handler(handler_name):
        if not handler_name:
            return None
        for w in fc_state['widgets'].values():
            for (_sid, _sname, hname) in _aw_names_for_widget(w):
                if hname and hname == handler_name:
                    return w
        return None

    def _nav_create_and_go(handler_name):
        # Create an entry flow_terminator named to match, then jump to it.
        cw = tk_canvas.winfo_width() or 860
        ch = tk_canvas.winfo_height() or 660
        z  = _fc_view['zoom']
        cx = snap(_fc_view['sx'] + (cw / 2) / z)
        cy = snap(_fc_view['sy'] + (ch / 2) / z)
        s = _fc_add_symbol('flow_terminator', cx, cy, label=handler_name)
        s['name'] = handler_name
        _guic_set_prop_value(s, 'is_entry', True)
        _guic_sync_stream()          # materialise the new auto-wired binding
        notebook.select(0)
        _nav_center_flow_on(s['id'])
        set_status(f"Created handler '{handler_name}' and wired it")

    def _nav_popup(event, actions):
        menu = tk.Menu(root, tearoff=0, bg=C['palette'], fg=C['text'],
                       activebackground=C['pal_active'], activeforeground=C['text'])
        for lbl, fn in actions:
            menu.add_command(label=lbl, command=fn)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def _gui_ctrl_click(event):
        x, y = _gc_s2d(event.x, event.y)
        w = guic_widget_at(x, y)
        if not w:
            return 'break'
        actions = []
        # Stage 8-4: cell binding navigation
        _bv = _guic_get_prop_value(w, 'bind_value_to')
        if _bv:
            rc = _sheet_cell_by_name(_bv)
            if rc is not None:
                actions.append((f"Go to cell: {_bv}",
                                lambda r=rc: _nav_center_sheet_on(r)))
        # 7c-3: signal-handler navigation (named widgets only)
        if w.get('name'):
            for (_sid, sname, hname) in _aw_names_for_widget(w):
                term = _nav_find_terminator_by_name(hname)
                if term is not None:
                    actions.append((f"Go to handler: {hname}",
                                    lambda t=term: (notebook.select(0),
                                                    _nav_center_flow_on(t['id']))))
                else:
                    actions.append((f"Create handler: {hname}",
                                    lambda h=hname: _nav_create_and_go(h)))
        if not actions:
            guic_set_status('No handlers or cell binding on this widget'); return 'break'
        if len(actions) == 1:
            actions[0][1]()
        else:
            _nav_popup(event, actions)
        return 'break'

    def _find_cell_bound_to(cname, pname):
        """Stage 8-6: (row, col, cell) of a cell bound to <cname>.<pname>, or None."""
        if _flowcode_ports is None:
            return None
        for (r, c), cell in fc_state['cells'].items():
            b = _flowcode_ports.cell_bound_port(cell)
            if b and b['container_name'] == cname and b['port_name'] == pname:
                return r, c, cell
        return None

    def _flow_ctrl_click(event):
        x, y = _fc_s2d(event.x, event.y)
        # Phase 7c-4b / Stage 8-6: Ctrl+click a container's port dot. If a Sheet
        # cell is bound to that port, jump to the cell; otherwise drill into the
        # container's pocket interior.
        ph = _fc_port_at(x, y)
        if ph:
            csym, edge, port = ph
            hit = _find_cell_bound_to(csym['name'], port['name'])
            if hit:
                r, c, cell = hit
                notebook.select(2)               # Sheet tab
                fc_state['cell_sel'] = (r, c)
                _sheet_sync_fbar(); _sheet_redraw()
                _sheet_set_status(f"→ cell {cell.get('name') or _sheet_a1(r, c)} "
                                  f"(bound {edge} {port['name']})")
                return 'break'
            _fc_set_scope(csym['name'])
            set_status(f"→ pocket {csym['name']}  ({edge} port {port['name']})")
            return 'break'
        s = _fc_sym_at(x, y)
        if not s:
            return 'break'
        if s.get('kind') != 'flow_terminator':
            set_status('Ctrl+click a terminator to find its widget'); return 'break'
        w = _nav_find_widget_for_handler(s.get('name', ''))
        if w is None:
            set_status('No matching widget signal'); return 'break'
        notebook.select(1)
        _nav_center_gui_on(w['id'])
        guic_set_status(f"→ {w.get('name') or w['kind']}  #{w['id']}")
        return 'break'

    guic.bind('<Control-Button-1>',      _gui_ctrl_click)
    tk_canvas.bind('<Control-Button-1>', _flow_ctrl_click)

    def on_close():
        # Phase 7c-0: use smart do_save (current path or Save As dialog)
        if fc_state['flow_symbols'] or fc_state['widgets']:
            ans = messagebox.askyesnocancel('Quit FlowCode',
                    'Save before closing?')
            if ans is None: return
            if ans: do_save()
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', on_close)
    set_mode('select')
    _fc_build_breadcrumb()   # Phase 7c-4: initial top-level breadcrumb
    root.after(100,redraw)
    root.mainloop()


if __name__=='__main__':
    if '--headless' in sys.argv or '--test' in sys.argv:
        run_headless_demo()
    else:
        run_gui()
