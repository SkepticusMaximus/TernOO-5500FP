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
    print("="*60+"\nFlowCode v0.6.0 — Headless Demo\n"+"="*60)
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
    root.title("FlowCode v0.6.0 — TernOO-5500FP Visual IDE")
    root.configure(bg=C['bg'])
    root.resizable(True,True)

    outer = tk.Frame(root,bg=C['bg']); outer.pack(fill='both',expand=True)
    palette_frame = tk.Frame(outer,bg=C['palette'],width=PALETTE_W)
    palette_frame.pack(side='left',fill='y'); palette_frame.pack_propagate(False)

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

    notebook = ttk.Notebook(right_outer)
    notebook.pack(fill='both',expand=True)

    # ── Tab 1: FlowCode ───────────────────────────────────────────────────────
    fc_tab = tk.Frame(notebook,bg=C['bg'])
    notebook.add(fc_tab, text='  Flow  ')

    tk_canvas = tk.Canvas(fc_tab,bg=C['canvas'],highlightthickness=0)
    tk_canvas.pack(side='top',fill='both',expand=True)
    inspect = tk.Label(fc_tab,text="Select a symbol or edge to inspect",
                       bg=C['inspect'],fg=C['inspect_fg'],
                       font=('Monospace',9),anchor='nw',justify='left',
                       padx=8,pady=4,height=6)
    inspect.pack(side='top',fill='x')
    status = tk.Label(fc_tab,text="Ready",anchor='w',
                      bg=C['status'],fg=C['pal_border'],
                      font=('Monospace',9),padx=8)
    status.pack(side='bottom',fill='x',ipady=3)

    # ── Tab 2: GHOST Canvas (built below after FlowCode palette) ─────────────
    ghost_tab = tk.Frame(notebook,bg=C['bg'])
    notebook.add(ghost_tab, text='  GUI  ')

    def set_status(m): status.config(text=m)
    def set_inspect(m): inspect.config(text=m)

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

    def _pal_section(title):
        tk.Label(palette_frame,text=title,bg=C['palette'],fg=C['dim'],
                 font=('Monospace',8),pady=3).pack(fill='x',padx=4)

    def _pal_btn(mode, label, sub, icon_key=None, fg=None):
        frm = tk.Frame(palette_frame,bg=C['pal_btn'],cursor='hand2',
                       relief='flat',bd=1)
        frm.pack(fill='x',padx=6,pady=2,ipady=3)

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

    # Build palette
    tk.Label(palette_frame,text="FlowCode",bg=C['palette'],fg=C['pal_border'],
             font=('Monospace',11,'bold'),pady=6).pack(fill='x')
    tk.Frame(palette_frame,bg=C['dim'],height=1).pack(fill='x',padx=6)
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
    tk.Frame(palette_frame,bg=C['dim'],height=1).pack(fill='x',padx=6,pady=4)
    _pal_section("ACTIONS")

    def _action_btn(label, cmd, fg=None, icon_key=None):
        btn = tk.Button(palette_frame, text=label, command=cmd,
                        bg=C['pal_btn'], fg=fg or C['text'],
                        font=('Monospace',9), relief='flat',
                        activebackground=C['pal_active'],
                        activeforeground=C['text'],
                        cursor='hand2', padx=4, pady=4)
        btn.pack(fill='x', padx=6, pady=2)

    def do_run():
        # Phase 6C: sync canvas_model from fc_state for execution
        _fc_sync_canvas_model()
        if not _TernOOInterpreter:
            set_status("Interpreter not found — place ternoo_interpreter.py in 5500fp/")
            return
        if not canvas_model.symbols:
            set_status("Canvas is empty — draw some symbols first")
            return

        data = {
            'symbols': [s.to_dict() for s in canvas_model.symbols.values()],
            'edges':   [e.to_dict() for e in canvas_model.edges],
        }

        print(f"\n{'═'*56}")
        print(f"  FlowCode → Running canvas ({len(canvas_model.symbols)} symbols)")
        print(f"{'═'*56}")

        interp = _TernOOInterpreter(trace=True)

        def on_step(node_id):
            state['selected_sym']  = node_id
            state['selected_edge'] = None
            fc_state['flow_selected']   = node_id  # Phase 6C
            s = canvas_model.symbols.get(node_id)
            if s:
                udp = s.to_udp_word()
                mp  = s.to_map_word()
                set_inspect(
                    f"► Executing: {s.label}  [{s.kind}]\n"
                    f"  UDP: {describe_word(udp)}\n"
                    f"       {word_to_str(udp)}\n"
                    f"  MAP: {describe_word(mp)}\n"
                    f"       {word_to_str(mp)}")
            redraw()
            root.update()

        _orig_execute = interp._execute_node
        def _patched_execute(node, end_ids, depth):
            on_step(node.id)
            return _orig_execute(node, end_ids, depth)
        interp._execute_node = _patched_execute

        interp.load_dict(data)

        try:
            result = interp.run()
            steps  = result['steps']
            stack  = result['eval_stack']
            env    = result['env']
            set_status(f"Run complete — {steps} steps  "
                       f"stack={stack}  env={env}")
            set_inspect(
                f"Run complete — {steps} steps\n"
                f"Eval stack: {stack}\n"
                f"Environment: {env}\n"
                f"Interpreter: {os.path.basename(_interp_path)}")
        except Exception as ex:
            set_status(f"Run error: {ex}")
            set_inspect(f"Run error:\n{ex}")
            print(f"[FlowCode] Run error: {ex}")

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
        guic_do_save()  # Phase 6C: unified .tgui save for both tabs

    def do_open():
        guic_do_open()  # Phase 6C: unified .tgui open

    def do_clear():
        # Phase 6C: clear fc_state['flow_*'] dicts
        if fc_state['flow_symbols']:
            if not messagebox.askyesno('Clear Canvas',
                    'Clear the canvas? Unsaved changes will be lost.'):
                return
        fc_state['flow_symbols'].clear()
        fc_state['flow_edges'].clear()
        state['selected_sym']  = None; state['selected_edge'] = None
        fc_state['flow_selected']   = None; fc_state['flow_multi_sel'].clear()
        fc_state['flow_next_id']    = 0
        set_inspect('Canvas cleared'); set_status('Cleared'); redraw()

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
    _action_btn("▶▶ Run",      do_run,    fg='#ffdd57')
    _action_btn("💾 Save",     do_save,   icon_key='save')
    _action_btn("📂 Open",     do_open,   icon_key='open')
    _action_btn("🗑 Clear",    do_clear,  fg='#ff8888', icon_key='clear')
    _action_btn("🧠 Learn",   do_learn,  fg='#7affcc')
    _action_btn("💡 Suggest", do_suggest, fg='#ffcc44')

    tk.Label(palette_frame,text=f"v0.6.0\n{os.path.basename(_emu_path)}",
             bg=C['palette'],fg=C['dim'],font=('Monospace',7),pady=4
             ).pack(side='bottom',fill='x')

    # ── Phase 6C: FlowCode dict helpers ──────────────────────────────────────

    def _fc_sym_at(x, y):
        """Hit test: return flow symbol dict at (x,y) or None."""
        hw, hh = SYMBOL_W // 2, SYMBOL_H // 2
        for s in reversed(list(fc_state['flow_symbols'].values())):
            if abs(s['x'] - x) <= hw and abs(s['y'] - y) <= hh:
                return s
        return None

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

    def _fc_add_symbol(kind, x, y, label=''):
        """Add flow symbol dict to fc_state, push undo. Returns sym dict."""
        sid = fc_state['flow_next_id']
        fc_state['flow_next_id'] += 1
        lbl = label or f"{kind.split('_', 1)[-1][0].upper()}{sid}"
        sym = {'id': sid, 'kind': kind,
               'x': snap(x), 'y': snap(y),
               'w': SYMBOL_W, 'h': SYMBOL_H,
               'label': lbl, 'properties': []}
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

    def _fc_add_edge(src_id, dst_id, waypoints=(), condition=''):
        """Add flow edge dict to fc_state, push undo. Returns edge dict or None."""
        if src_id not in fc_state['flow_symbols']: return None
        if dst_id not in fc_state['flow_symbols']: return None
        for e in fc_state['flow_edges']:
            if e['src'] == src_id and e['dst'] == dst_id: return None
        edge = {'src': src_id, 'dst': dst_id,
                'waypoints': list(waypoints), 'condition': condition}
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
        w=tk_canvas.winfo_width() or 860
        h=tk_canvas.winfo_height() or 660
        for x in range(0,w,GRID): tk_canvas.create_line(x,0,x,h,fill=C['grid'])
        for y in range(0,h,GRID): tk_canvas.create_line(0,y,w,y,fill=C['grid'])

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
        x, y = s['x'], s['y']
        hw, hh = SYMBOL_W // 2, SYMBOL_H // 2

        if draw_kind == SYMBOL_PROCESS:
            tk_canvas.create_rectangle(x-hw, y-hh, x+hw, y+hh,
                                       fill=fill, outline=bor, width=lw)
            if s['kind'] == 'flow_subroutine':  # double-border for predefined process
                tk_canvas.create_rectangle(x-hw+4, y-hh+4, x+hw-4, y+hh-4,
                                           fill='', outline=bor, width=1)
        elif draw_kind == SYMBOL_DECISION:
            tk_canvas.create_polygon([x, y-hh, x+hw, y, x, y+hh, x-hw, y],
                                     fill=fill, outline=bor, width=lw)
        elif draw_kind == SYMBOL_IO:
            r = 12
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
                    (x, y) in fc_state.get('_bound_targets', set())):
                r = 5
                tk_canvas.create_oval(x+hw-r*2-2, y-hh+2,
                                      x+hw-2,     y-hh+r*2+2,
                                      fill='#00e5ff', outline='', width=0)

        tk_canvas.create_text(x, y, text=s['label'], fill=C['text'],
                              font=('Monospace', 10, 'bold'))
        tk_canvas.create_text(x, y+hh+10,
                              text=s['kind'].replace('flow_', ''),
                              fill=C['dim'], font=('Monospace', 7))
        if sel:
            tk_canvas.create_text(x, y-hh-10, text=f"({x},{y})",
                                  fill=C['selected'], font=('Monospace', 7))

        # Connection points in edge mode
        if state['mode'] in ('edge_src', 'edge_dst_pending'):
            for cx, cy in [(x, y-hh), (x, y+hh), (x+hw, y), (x-hw, y)]:
                tk_canvas.create_oval(cx-4, cy-4, cx+4, cy+4,
                                      fill=C['pal_border'], outline=C['border'])

    def draw_edge(e):
        # Phase 6C: e is a flow edge dict {src, dst, waypoints, condition}
        sel_e  = state['selected_edge']
        is_sel = (sel_e and sel_e.get('src') == e['src']
                  and sel_e.get('dst') == e['dst'])
        col = C['selected'] if is_sel else C['edge']
        lw  = 3 if is_sel else 2

        pts = _fc_ortho_points(e)
        if len(pts) < 2: return

        for i in range(len(pts) - 1):
            x1, y1 = pts[i]; x2, y2 = pts[i + 1]
            kw = dict(fill=col, width=lw)
            if i == len(pts) - 2:
                kw.update(arrow='last', arrowshape=(16, 20, 6))
            tk_canvas.create_line(x1, y1, x2, y2, **kw)

        for wx, wy in e.get('waypoints', []):
            tk_canvas.create_oval(wx-5, wy-5, wx+5, wy+5,
                                  fill=C['waypoint'], outline=C['border'], width=1)

        cond = e.get('condition', '')
        if len(pts) >= 2 and cond:
            mx = (pts[0][0] + pts[1][0]*2) // 3
            my = (pts[0][1] + pts[1][1]*2) // 3 - 10
            tk_canvas.create_text(mx, my, text=f"[{cond}]",
                                  fill=C['waypoint'], font=('Monospace', 8, 'bold'))

    def draw_edge_in_progress():
        """Draw the edge being constructed with waypoints collected so far."""
        src_id = state.get('edge_src')
        if not src_id: return
        src = fc_state['flow_symbols'].get(src_id)  # Phase 6C: use fc_state dict
        if not src: return
        pts = [(src['x'], src['y'])] + state['edge_waypoints']
        if len(pts)<1: return
        # Draw path so far
        for i in range(len(pts)-1):
            x1,y1=pts[i]; x2,y2=pts[i+1]
            tk_canvas.create_line(x1,y1,x2,y2,fill=C['waypoint'],
                                  width=1,dash=(4,3))
        # Waypoint dots
        for wx,wy in state['edge_waypoints']:
            tk_canvas.create_oval(wx-4,wy-4,wx+4,wy+4,
                                  fill=C['waypoint'],outline=C['border'])
        # Ghost line to cursor
        if state['ghost']:
            lx,ly=pts[-1]; gx,gy=state['ghost']
            # Ortho ghost
            tk_canvas.create_line(lx,ly,gx,ly,fill=C['waypoint'],
                                  width=1,dash=(2,4))
            tk_canvas.create_line(gx,ly,gx,gy,fill=C['waypoint'],
                                  width=1,dash=(2,4))

    def redraw():
        tk_canvas.delete('all')
        draw_grid()
        for e in fc_state['flow_edges']:            # Phase 6C: draw from fc_state
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
            draw_symbol(s)
        draw_edge_in_progress()
        if (state['ghost'] and
                state['mode'] in ('place_terminator','place_process',
                                  'place_decision','place_io')):
            _draw_placement_ghost(*state['ghost'])

    def _draw_placement_ghost(x,y):
        sx,sy=snap(x),snap(y); hw,hh=SYMBOL_W//2,SYMBOL_H//2
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
            r=12
            tk_canvas.create_rectangle(sx-hw+r,sy-hh,sx+hw-r,sy+hh,fill=fill,outline=fill)
            tk_canvas.create_oval(sx-hw,sy-hh,sx-hw+r*2,sy+hh,
                                  fill=fill,outline=bor,width=1,dash=(4,4))
            tk_canvas.create_oval(sx+hw-r*2,sy-hh,sx+hw,sy+hh,
                                  fill=fill,outline=bor,width=1,dash=(4,4))
        tk_canvas.create_text(sx,sy+hh+10,text=f"snap ({sx},{sy})",
                              fill='#2a3050',font=('Monospace',7))

    def update_inspect():
        # Phase 6C: read from fc_state['flow_*'] dicts
        sid = state['selected_sym']
        se  = state['selected_edge']
        if sid and sid in fc_state['flow_symbols']:
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
        # Phase 6C: use fc_state dicts
        _hide_tooltip()
        sym = _fc_sym_at(event.x, event.y)
        if sym:
            tip = f"{sym['kind'].upper()} #{sym['id']}  '{sym['label']}'"
            ex, ey = event.x, event.y
            _tooltip_after[0] = root.after(700, lambda: _show_tooltip(ex, ey, tip))
        else:
            edg = _fc_edge_near(event.x, event.y)
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
        state['ghost'] = (event.x, event.y)
        if state['dragging'] and state['selected_sym']:
            s = fc_state['flow_symbols'].get(state['selected_sym'])  # Phase 6C
            if s:
                dx, dy = state['drag_offset']
                s['x'] = snap(event.x - dx)
                s['y'] = snap(event.y - dy)
            _hide_tooltip()
        else:
            _schedule_tooltip(event)
        redraw()

    def on_click(event):
        # Phase 6C: all flow operations go through fc_state['flow_*'] + _fc_* helpers
        x, y = event.x, event.y
        mode = state['mode']

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
            hit = _fc_sym_at(x, y)
            if hit and hit['id'] != state['edge_src']:
                wps = state['edge_waypoints']
                e = _fc_add_edge(state['edge_src'], hit['id'], waypoints=wps)
                if e:
                    src = fc_state['flow_symbols'].get(state['edge_src'])
                    state['selected_edge'] = {'src': e['src'], 'dst': e['dst'],
                                              'waypoints': list(e['waypoints']),
                                              'condition': e['condition']}
                    state['selected_sym'] = None
                    sl = src['label'] if src else f"#{state['edge_src']}"
                    set_status(f"Edge {sl}→{hit['label']} ({len(wps)} waypoints)")
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
        if state['dragging'] and state['selected_sym']:
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
        # Phase 6C: use fc_state dict hit tests
        hit_s = _fc_sym_at(event.x, event.y)
        hit_e = _fc_edge_near(event.x, event.y)
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

        frm = tk.Frame(dlg, bg=C['bg']); frm.pack(padx=12, pady=8)
        tk.Label(frm, text=f"{s['kind'].upper()}  #{s['id']}",
                 bg=C['bg'], fg=C['pal_border'],
                 font=('Monospace', 10, 'bold')
                 ).grid(row=0, column=0, columnspan=2, pady=(0, 8))

        tk.Label(frm, text="Label:", bg=C['bg'], fg=C['inspect_fg'],
                 font=('Monospace', 9), anchor='e', width=12
                 ).grid(row=1, column=0, padx=8, pady=4, sticky='e')
        v_label = tk.StringVar(value=s['label'])
        tk.Entry(frm, textvariable=v_label, bg=C['canvas'], fg=C['text'],
                 insertbackground=C['text'], font=('Monospace', 10), width=20,
                 relief='flat', bd=4
                 ).grid(row=1, column=1, padx=8, pady=4)

        row_idx = [2]
        extra_vars = {}
        from_props = _fp_properties_for(s['kind'])
        for pd in from_props:
            pname = pd['name']
            if pname in ('x', 'y', 'w', 'h', 'label'): continue
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
            old_label = s['label']
            new_label = v_label.get().strip()
            if new_label and new_label != old_label:
                _guic_push_undo({'kind': 'flow_prop_change', 'sym_id': s['id'],
                               'property': 'label',
                               'old_value': old_label, 'new_value': new_label})
                s['label'] = new_label
            for pname, (pd, var) in extra_vars.items():
                old_v = _guic_get_prop_value(s, pname)
                new_v = var.get()
                if pd['kind'] == 'bool':
                    new_v = bool(new_v)
                elif pd['kind'] == 'int':
                    try: new_v = int(new_v)
                    except ValueError: new_v = old_v
                if new_v != old_v:
                    _guic_push_undo({'kind': 'flow_prop_change', 'sym_id': s['id'],
                                   'property': pname,
                                   'old_value': old_v, 'new_value': new_v})
                    _guic_set_prop_value(s, pname, new_v)
            set_status(f"Updated {s['label']}")
            _guic_sync_stream()
            update_inspect(); redraw(); dlg.destroy()

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
        dlg.update_idletasks(); dlg.grab_set(); dlg.focus_force()

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
            new_cond = v_cond.get().strip()
            e['condition'] = new_cond
            if (state['selected_edge'] and
                    state['selected_edge'].get('src') == e['src'] and
                    state['selected_edge'].get('dst') == e['dst']):
                state['selected_edge']['condition'] = new_cond
            set_status(f"Edge {sl}→{dl}  condition='{new_cond}'")
            _guic_sync_stream()
            update_inspect(); redraw(); dlg.destroy()

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
        dlg.update_idletasks(); dlg.grab_set(); dlg.focus_force()

    def on_key(event):
        if notebook.index('current') != 0:
            return   # Let GHOST canvas handle its own keys
        k = event.keysym.lower()
        if k == 't': set_mode('place_terminator')
        elif k == 'r': set_mode('place_process')
        elif k == 'd': set_mode('place_decision')
        elif k == 'i': set_mode('place_io')
        elif k == 'e': set_mode('edge_src')
        elif k == 'escape': set_mode('select')
        elif k == 'w':
            _fc_sync_canvas_model(); do_dump()
        elif k == 'l':
            _fc_sync_canvas_model(); do_load()
        elif k == 'delete':
            if state['selected_sym']:
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
    else:
        _signals_for         = lambda kind: []
        _common_signals_for  = lambda kinds: []

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

    # ── Ghost canvas layout ───────────────────────────────────────────────────
    guic_pal   = tk.Frame(ghost_tab, bg=C['palette'], width=PALETTE_W)
    guic_pal.pack(side='left', fill='y'); guic_pal.pack_propagate(False)

    # Right-side property panel (packed before guic_right so it claims the right boundary)
    _guic_prop_visible = [True]
    guic_prop_outer = tk.Frame(ghost_tab, bg=C['palette'], width=_GC_PROP_W)
    guic_prop_outer.pack(side='right', fill='y')
    guic_prop_outer.pack_propagate(False)

    guic_right = tk.Frame(ghost_tab, bg=C['bg'])
    guic_right.pack(side='left', fill='both', expand=True)
    guic     = tk.Canvas(guic_right, bg=C['canvas'], highlightthickness=0)
    guic.pack(fill='both', expand=True)
    guic_bar   = tk.Label(guic_right,
                        text="GUI Canvas — pick a widget type from the palette",
                        bg=C['status'], fg=C['pal_border'],
                        font=('Monospace', 9), anchor='w', padx=8)
    guic_bar.pack(side='bottom', fill='x', ipady=3)

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

    # ── Palette ───────────────────────────────────────────────────────────────
    tk.Label(guic_pal, text="GUI", bg=C['palette'], fg=C['pal_border'],
             font=('Monospace', 9, 'bold'), pady=6).pack(fill='x')
    tk.Label(guic_pal, text="WIDGETS", bg=C['palette'], fg=C['pal_border'],
             font=('Monospace', 9, 'bold')).pack(fill='x')
    tk.Frame(guic_pal, bg=C['dim'], height=1).pack(fill='x', padx=6, pady=2)

    # ── Action buttons ────────────────────────────────────────────────────────
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

    def guic_do_save():
        # Phase 6C: save both GHOST + FlowCode tab content to .tgui v0.2
        if not fc_state['widgets'] and not fc_state['flow_symbols']:
            guic_set_status("Nothing to save"); return
        path = filedialog.asksaveasfilename(
            parent=root, title='Save TernOO design',
            initialdir=_FC_DIR,
            defaultextension='.ternoo',
            filetypes=[('TernOO design', '*.ternoo'), ('All files', '*.*')])
        if not path: return
        syms  = [{'id': w['id'], 'kind': w['kind'], 'label': w['label'],
                  'gtk_class': '', 'x': w['x'], 'y': w['y'], 'depth': 0,
                  'w': w.get('w', GW), 'h': w.get('h', GH),
                  'parent_id': w.get('parent_id'),
                  'layout_mode': w.get('layout_mode',
                                       _GC_LAYOUT_DEFAULTS.get(w['kind'], 'absolute')),
                  'properties': list(w.get('properties', [])), 'signals': [],
                  'signal_ids': {str(k): dict(v)
                                 for k, v in (w.get('signal_ids') or {}).items()}}
                 # Bundle 12: 'bindings' key retired; signal_ids uses int signal IDs
                 for w in fc_state['widgets'].values()]
        edges = [{'src': e['src'], 'dst': e['dst'],
                  'privilege': 0, 'call_style': 0, 'return_type': 1,
                  'seg_idx': 0, 'offset': 0, 'waypoints': [], 'condition': ''}
                 for e in fc_state['edges']]
        _stream_words = (list(fc_state['stream'].words)
                         if fc_state.get('stream') is not None else [])
        # Phase 6C: include flow symbols and edges
        flow_syms  = [dict(s) for s in fc_state['flow_symbols'].values()]
        flow_edges = [dict(e) for e in fc_state['flow_edges']]
        tgui  = {
            'ternoo_version': '0.3',
            'source_file':  os.path.basename(path),
            'source_type':  'ternoo_design',
            'word_stream':  _stream_words,
            'symbols':      syms,
            'edges':        edges,
            'flow_symbols': flow_syms,           # Phase 6C: FlowCode tab symbols
            'flow_edges':   flow_edges,          # Phase 6C: FlowCode tab edges
            'sequence':     [w['id'] for w in fc_state['widgets'].values()],
            'tgui_meta': {
                'widget_count':      len(syms),
                'edge_count':        len(edges),
                'flow_symbol_count': len(flow_syms),
                'flow_edge_count':   len(flow_edges),
                'mmoe_types_used': list({w['kind'] for w in fc_state['widgets'].values()}),
            },
        }
        with open(path, 'w') as _sf:
            json.dump(tgui, _sf, indent=2)
        guic_set_status(f"Saved: {os.path.basename(path)}")

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
        path = filedialog.askopenfilename(
            parent=root, title='Open TernOO design',
            initialdir=_FC_DIR,
            filetypes=[('TernOO design', '*.ternoo'), ('All files', '*.*')])
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
            # Phase 6B: v0.2 files carry word_stream as canonical.
            # Load symbols regardless (they carry widget metadata); if word_stream
            # present, we also restore the stream words directly after loading.
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
                }
                fc_state['flow_next_id'] = max(fc_state['flow_next_id'], sid + 1)
            for e in tgui.get('flow_edges', []):
                fc_state['flow_edges'].append({
                    'src':       e['src'],
                    'dst':       e['dst'],
                    'waypoints': [tuple(w) for w in e.get('waypoints', [])],
                    'condition': e.get('condition', ''),
                })
            fc_state['flow_selected'] = None
            fc_state['flow_multi_sel'].clear()
            # Phase 6B/6C: sync stream from widgets+flow content
            _guic_sync_stream()
            guic_set_mode('select')
            guic_set_status(f"Opened: {os.path.basename(path)}")
            guic_layout_all()
            guic_redraw()
        except Exception as _oe:
            guic_set_status(f"Open failed: {_oe}")

    # ── Undo / redo (D10 + Phase 6A word-level layer) ────────────────────────
    _guic_undo_stack      = []   # semantic: list of inverse action dicts, newest last
    _guic_redo_stack      = []   # semantic redo stack
    _guic_word_undo_stack = []   # Phase 6A: word-level WordStreamEdit list (Alt+Z)
    _guic_word_redo_stack = []   # Phase 6A: word-level redo (Alt+Y)
    _GC_UNDO_LIMIT      = 100
    _guic_undo_btn_ref    = [None]   # mutable ref set when UI is built
    _guic_redo_btn_ref    = [None]   # mutable ref set when UI is built
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
        if name in ('x', 'y', 'w', 'h', 'label', 'layout_mode'):
            return w.get(name)
        for p in w.get('properties', []):
            if p['name'] == name:
                return p['value']
        return None

    def _guic_set_prop_value(w, name, value):
        """Set property value in widget dict (common) or properties list."""
        if name in ('x', 'y', 'w', 'h', 'label', 'layout_mode'):
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

    # Select / pointer tool — returns to neutral select mode
    _guic_sel_btn = _guic_action_btn(guic_pal, '☞ Select', lambda: guic_set_mode('select'), '#aaaaff')
    _guic_tooltip(_guic_sel_btn, 'Select / pointer (Esc)')
    tk.Frame(guic_pal, bg=C['dim'], height=1).pack(fill='x', padx=6, pady=2)

    for _lbl, _cmd, _fg in [
        ('⬡ Connect', guic_do_connect, '#7aff7a'),
        ('✕ Delete',  guic_do_delete,  '#ff8888'),
        ('💡 Suggest', guic_do_suggest, '#ffcc44'),
        ('🗑 Clear',  guic_do_clear,   '#ff8888'),
    ]:
        _guic_action_btn(guic_pal, _lbl, _cmd, _fg)

    # Undo / Redo — above Save/Open; grey out when stack is empty
    # Tooltips are managed dynamically by guic_update_undo_btns() (Phase 6A).
    _guic_undo_btn_ref[0] = _guic_action_btn(guic_pal, '↩ Undo', guic_undo, C['dim'])
    _guic_redo_btn_ref[0] = _guic_action_btn(guic_pal, '↪ Redo', guic_redo, C['dim'])
    guic_update_undo_btns()   # initialise disabled state + tooltips

    for _lbl, _cmd, _fg in [
        ('💾 Save',   guic_do_save,    '#7ab4ff'),
        ('📂 Open',   guic_do_open,    '#ffcc88'),
    ]:
        _guic_action_btn(guic_pal, _lbl, _cmd, _fg)

    tk.Frame(guic_pal, bg=C['dim'], height=1).pack(fill='x', padx=6, pady=4)

    # ── Widget palette sections ───────────────────────────────────────────────
    _guic_pal_inner = tk.Frame(guic_pal, bg=C['palette'])
    _guic_pal_inner.pack(fill='x')

    # ── Collapsible section builder ───────────────────────────────────────────
    # _guic_pal_inner uses grid so that grid_remove() + grid() can re-show a
    # collapsed section in its original position (pack_forget/pack would
    # re-insert at the end, scrambling section order on re-expand).
    _guic_grp_names = {
        5: 'CONTAINERS', 4: 'CONTROLS', 3: 'INPUTS',
        2: 'DISPLAY', 1: 'DIALOGS', 0: 'MENUS',
    }
    _guic_sections: dict = {}   # grp_key → {'open': [bool], 'frame': Frame, 'btn': Button}
    _guic_pal_inner.columnconfigure(0, weight=1)
    _guic_row = [0]

    def _guic_make_toggle(hdr_ref, sec_frame, open_state, name):
        def _toggle():
            open_state[0] = not open_state[0]
            if open_state[0]:
                sec_frame.grid()        # restores remembered row/column
                hdr_ref[0].config(text=f'▾ {name}')
            else:
                sec_frame.grid_remove() # hides but remembers position
                hdr_ref[0].config(text=f'▸ {name}')
        return _toggle

    for wtype, y_lo in _ghost_palette_types:
        grp_key = y_lo // 100
        if grp_key not in _guic_sections:
            name       = _guic_grp_names.get(grp_key, f'GROUP_{grp_key}')
            open_state = [True]
            sec_frame  = tk.Frame(_guic_pal_inner, bg=C['palette'])
            hdr_ref    = [None]
            toggle_fn  = _guic_make_toggle(hdr_ref, sec_frame, open_state, name)
            hdr_btn    = tk.Button(_guic_pal_inner, text=f'▾ {name}',
                                   bg=C['palette'], fg=C['dim'],
                                   font=('Monospace', 7, 'bold'), relief='flat', bd=0,
                                   pady=2, padx=4, anchor='w', cursor='hand2',
                                   command=toggle_fn)
            hdr_btn.grid(row=_guic_row[0], column=0, sticky='ew', padx=2, pady=(4, 0))
            _guic_row[0] += 1
            hdr_ref[0] = hdr_btn
            sec_frame.grid(row=_guic_row[0], column=0, sticky='ew')
            _guic_row[0] += 1
            _guic_sections[grp_key] = {'open': open_state, 'frame': sec_frame, 'btn': hdr_btn}
        col   = _guic_color.get(wtype, C['pal_btn'])
        short = wtype.replace('gui_', '')
        tk.Button(_guic_sections[grp_key]['frame'], text=short,
                  bg=col, fg=C['text'],
                  font=('Monospace', 8), relief='flat', bd=0,
                  padx=4, pady=2, cursor='hand2', anchor='w',
                  command=lambda k=wtype: guic_set_mode('place', k)
                  ).pack(fill='x', padx=4, pady=1)

    tk.Label(guic_pal, text="GUI Canvas\nv0.6.0",
             bg=C['palette'], fg=C['dim'],
             font=('Monospace', 7), pady=4
             ).pack(side='bottom', fill='x')

    # ── Drawing ───────────────────────────────────────────────────────────────
    def guic_draw_grid():
        w = guic.winfo_width() or 860; h = guic.winfo_height() or 660
        for x in range(0, w, GRID): guic.create_line(x, 0, x, h, fill=C['grid'])
        for y in range(0, h, GRID): guic.create_line(0, y, w, y, fill=C['grid'])

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
        if _label_text:
            guic.create_text(x, y, text=str(_label_text)[:20],
                           fill=txt, font=('Monospace', 8), anchor='center')

        # Kind-specific string properties overlay (title, placeholder, etc.)
        for _kp in w.get('properties', []):
            _kpname = _kp.get('name', '')
            _kpval  = str(_kp.get('value', '') or '')
            if not _kpval: continue
            if _kpname == 'title':
                # Title bar text — top strip of the widget tile
                guic.create_text(x, T + 7, text=_kpval[:22],
                               fill=txt, font=('Monospace', 7, 'bold'), anchor='center')
            elif _kpname == 'placeholder':
                # Placeholder — dimmed italic centred (only visible when label absent)
                guic.create_text(x, y, text=_kpval[:20],
                               fill=dim, font=('Monospace', 7, 'italic'), anchor='center')

        # Type label below tile
        guic.create_text(x, B + 9, text=kind.replace('gui_', ''),
                       fill=dim, font=('Monospace', 7))

        # Drop-target highlight (thick dashed border when this widget is the drop target)
        if fc_state.get('drop_target') == w['id']:
            guic.create_rectangle(L - 3, T - 3, R + 3, B + 3,
                                outline=C['selected'], width=3, fill='', dash=(4, 2))

        # Resize handles — 8 small squares, only for single-selected widget (D3)
        if sel and len(fc_state['multi_sel']) <= 1:
            _hs = 3  # half of 6×6 px square
            for hx, hy in guic_handle_positions(w).values():
                guic.create_rectangle(hx - _hs, hy - _hs, hx + _hs, hy + _hs,
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
        sx, sy = guic_abs_pos(src); dx, dy = guic_abs_pos(dst)
        x1, y1 = sx, sy + src.get('h', GH) // 2
        x2, y2 = dx, dy - dst.get('h', GH) // 2
        # If same row, draw a horizontal arc
        if abs(y1 - dy) < GH:
            mx = (x1 + x2) // 2; my = y1 + 30
            guic.create_line(x1, y1, mx, my, x2, y2,
                           fill=C['edge'], width=2,
                           arrow='last', arrowshape=(12, 16, 5), smooth=True)
        else:
            guic.create_line(x1, y1, x2, y2,
                           fill=C['edge'], width=2,
                           arrow='last', arrowshape=(12, 16, 5))

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
                    guic.create_line(lx, pay - ph//2, lx, pay + ph//2,
                                   fill=C['selected'], width=2, dash=(4, 2))
                elif mode == 'vbox' and siblings:
                    if insert_idx < len(siblings):
                        ref = guic_abs_pos(siblings[insert_idx])
                        ly = ref[1] - siblings[insert_idx].get('h', GH)//2 - 2
                    else:
                        ref = guic_abs_pos(siblings[-1])
                        ly = ref[1] + siblings[-1].get('h', GH)//2 + 2
                    guic.create_line(pax - pw//2, ly, pax + pw//2, ly,
                                   fill=C['selected'], width=2, dash=(4, 2))

        # ── Lasso rubber band ─────────────────────────────────────────────────
        if fc_state['lasso_start'] is not None and fc_state['lasso_end'] is not None:
            lx0 = min(fc_state['lasso_start'][0], fc_state['lasso_end'][0])
            ly0 = min(fc_state['lasso_start'][1], fc_state['lasso_end'][1])
            lx1 = max(fc_state['lasso_start'][0], fc_state['lasso_end'][0])
            ly1 = max(fc_state['lasso_start'][1], fc_state['lasso_end'][1])
            guic.create_rectangle(lx0, ly0, lx1, ly1,
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

        if sig_list:
            tk.Label(_guic_prop_inner, text='Signals',
                     bg=C['pal_btn'], fg=C['pal_border'],
                     font=('Monospace', 7, 'bold'),
                     anchor='w', padx=6, pady=2).pack(fill='x', pady=(4, 0))

            for sig in sig_list:
                sig_name = sig['name']
                sig_id   = sig['id']   # Bundle 12: int SIGNAL_* constant

                # Determine current binding display value.
                # Bundle 12: look up by signal_id (int) in 'signal_ids' dict.
                # Symbolic name is recovered at display time from the flow_terminator
                # at the stored dst position.
                def _get_symbolic(w_dict, s_id):
                    """Return symbolic label for bound terminator, or None if unbound."""
                    binfo = (w_dict.get('signal_ids') or {}).get(s_id)
                    if not binfo:
                        return None
                    dx, dy = binfo.get('dst_x', 0), binfo.get('dst_y', 0)
                    for _sym in fc_state['flow_symbols'].values():
                        if _sym.get('x', 0) == dx and _sym.get('y', 0) == dy:
                            return _sym.get('label', '') or ''
                    return ''   # binding exists but terminator not found

                primary_sym = _get_symbolic(primary_w, sig_id)
                if is_multi:
                    b_vals = []
                    for wid in widget_ids:
                        ww = fc_state['widgets'].get(wid)
                        if ww:
                            b_vals.append(_get_symbolic(ww, sig_id))
                    all_same = len(set(str(v) for v in b_vals)) == 1
                    if not all_same:
                        disp = '(multiple values)'
                    elif b_vals[0] is None:
                        disp = 'Not bound'
                    else:
                        disp = f'{sig_name} → {b_vals[0] or "(unnamed)"}'
                else:
                    if primary_sym is None:
                        disp = 'Not bound'
                    else:
                        disp = f'{sig_name} → {primary_sym or "(unnamed)"}'

                sig_row = tk.Frame(_guic_prop_inner, bg=C['palette'],
                                   cursor='hand2')
                sig_row.pack(fill='x', padx=4, pady=1)
                tk.Label(sig_row, text=sig_name, bg=C['palette'], fg=C['dim'],
                         font=('Monospace', 7), width=12, anchor='w').pack(side='left')
                sig_val_lbl = tk.Label(sig_row, text=disp,
                                       bg=C['palette'], fg=C['text'],
                                       font=('Monospace', 7), anchor='w')
                sig_val_lbl.pack(side='left', fill='x', expand=True)

                # Click anywhere on the row → open picker
                # Guard against double-click firing <Button-1> twice
                _pick_guard = [False]
                def _open_picker(event=None, _sid=sig_id, _sname=sig_name,
                                 _wids=widget_ids, _g=_pick_guard):
                    if _g[0]:
                        return
                    _g[0] = True
                    try:
                        _guic_signal_picker(_sid, _sname, _wids)
                    finally:
                        _g[0] = False
                sig_row.bind('<Button-1>',         _open_picker)
                sig_val_lbl.bind('<Button-1>',     _open_picker)
                # Absorb the Double-Button-1 so it doesn't propagate
                sig_row.bind('<Double-Button-1>',     lambda e: 'break')
                sig_val_lbl.bind('<Double-Button-1>', lambda e: 'break')

        # Scroll to top after rebuild
        _guic_prop_cvs.yview_moveto(0)

    def _guic_signal_picker(signal_id: int, signal_name: str, widget_ids: list):
        """Open a modal picker to bind/unbind a signal to a flow entry (Bundle 12).

        signal_id:   int SIGNAL_* constant (e.g. SIGNAL_CLICKED=300)
        signal_name: display string (e.g. 'clicked') — UI only
        widget_ids:  list of selected widget IDs to bind/unbind
        """
        # Build list of flow_terminator symbols with is_entry=True, directly from
        # fc_state['flow_symbols'] — no stream indirection needed since we are in
        # the same closure as the flow tab.
        entries = []
        for _sid, _sym in fc_state['flow_symbols'].items():
            if _sym.get('kind') != 'flow_terminator':
                continue
            _is_entry = False
            for _p in _sym.get('properties', []):
                if _p.get('name') == 'is_entry' and _p.get('value'):
                    _is_entry = True
                    break
            if _is_entry:
                entries.append((_sid, _sym.get('label', ''),
                                _sym.get('x', 0), _sym.get('y', 0)))
        entries.sort(key=lambda t: t[1])
        # entries: [(sid, label, x, y), ...]

        dlg = tk.Toplevel(root)
        dlg.title(f'Bind signal: {signal_name}')
        dlg.configure(bg=C['bg'])
        dlg.resizable(False, False)
        dlg.update_idletasks()   # ensure window is mapped before grab
        dlg.wait_visibility()    # wait for WM to make it viewable
        dlg.grab_set()

        tk.Label(dlg, text=f'Choose a handler for  "{signal_name}"',
                 bg=C['bg'], fg=C['text'],
                 font=('Monospace', 9, 'bold'), pady=8).pack(fill='x', padx=12)

        lb_frame = tk.Frame(dlg, bg=C['bg'])
        lb_frame.pack(fill='both', expand=True, padx=12)

        scrollbar = tk.Scrollbar(lb_frame, orient='vertical')
        lb = tk.Listbox(lb_frame, yscrollcommand=scrollbar.set,
                        bg=C['canvas'], fg=C['text'],
                        selectbackground=C['selected'],
                        font=('Monospace', 9), width=36, height=10,
                        relief='flat', activestyle='none')
        scrollbar.config(command=lb.yview)
        scrollbar.pack(side='right', fill='y')
        lb.pack(side='left', fill='both', expand=True)

        # First entry: None (unbind)
        lb.insert('end', '  None (unbind)')
        _picker_data = [None]   # parallel list; index 0 = unbind

        for sid, label, ex, ey in entries:
            lb.insert('end', f'  {label or "(unnamed)"}')
            # Bundle 12: no 'symbolic' key — recovered at display time from terminator
            _picker_data.append({'dst_x': ex, 'dst_y': ey})

        if not entries:
            tk.Label(dlg, text='(No flow entries with is_entry=True found)',
                     bg=C['bg'], fg=C['dim'],
                     font=('Monospace', 7), pady=4).pack()

        def _on_select(event=None):
            sel = lb.curselection()
            if not sel:
                return
            idx = sel[0]
            chosen = _picker_data[idx]   # None or {'dst_x': int, 'dst_y': int}
            dlg.destroy()
            # Apply binding to all selected widgets (Bundle 12: uses signal_ids dict)
            for wid in widget_ids:
                w = fc_state['widgets'].get(wid)
                if w is None:
                    continue
                old_b = (w.get('signal_ids') or {}).get(signal_id)
                _guic_push_undo({'kind': 'binding_change', 'widget_id': wid,
                                 'signal_id': signal_id, 'old_binding': old_b})
                sig_ids = w.setdefault('signal_ids', {})
                if chosen is None:
                    sig_ids.pop(signal_id, None)
                else:
                    sig_ids[signal_id] = dict(chosen)
            _guic_sync_stream()
            guic_rebuild_prop_panel()
            guic_update_undo_btns()
            # Recover symbolic name from terminator for status message
            sym_label = None
            if chosen:
                dx, dy = chosen['dst_x'], chosen['dst_y']
                for _sym in fc_state['flow_symbols'].values():
                    if _sym.get('x', 0) == dx and _sym.get('y', 0) == dy:
                        sym_label = _sym.get('label', '') or None
                        break
            if chosen:
                guic_set_status(f"Bound {signal_name} → {sym_label or '(unnamed)'}")
            else:
                guic_set_status(f"Unbound {signal_name}")

        lb.bind('<Double-Button-1>', _on_select)
        lb.bind('<Return>', _on_select)

        btn_frm = tk.Frame(dlg, bg=C['bg'])
        btn_frm.pack(pady=8)
        tk.Button(btn_frm, text='OK', command=_on_select,
                  bg=C['pal_btn'], fg=C['text'],
                  font=('Monospace', 9), relief='flat',
                  padx=10).pack(side='left', padx=4)
        tk.Button(btn_frm, text='Cancel', command=dlg.destroy,
                  bg=C['pal_btn'], fg=C['text'],
                  font=('Monospace', 9), relief='flat',
                  padx=10).pack(side='left', padx=4)

        dlg.bind('<Escape>', lambda e: dlg.destroy())
        dlg.wait_window()

    # ── Events ────────────────────────────────────────────────────────────────
    def guic_on_click(event):
        x, y = event.x, event.y
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
                     'w': _dw, 'h': _dh, 'parent_id': new_pid,
                     'layout_mode': _GC_LAYOUT_DEFAULTS.get(kind, 'absolute'),
                     'properties': []}
            fc_state['widgets'][nid] = new_w
            if new_pid is not None:
                fc_state['child_order'].setdefault(new_pid, []).append(nid)
                guic_apply_layout(new_pid)
            _guic_push_undo({'kind': 'delete', 'widget': new_w.copy()})
            fc_state['selected'] = nid; fc_state['multi_sel'] = {nid}
            guic_set_status(f"Placed {kind} — click to place another, Esc to stop")
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
        x, y = event.x, event.y

        # ── Lasso drag ─────────────────────────────────────────────────────────
        if fc_state['lasso_start'] is not None:
            fc_state['lasso_end'] = (x, y)
            guic_redraw(); return

        # ── Resize drag ────────────────────────────────────────────────────────
        if fc_state['resize_handle'] is not None and fc_state['selected'] is not None:
            w = fc_state['widgets'].get(fc_state['selected'])
            if w:
                ox, oy, ow, oh = fc_state['resize_origin']
                h = fc_state['resize_handle']
                # Each handle constrains different edges
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
                    # Compute insertion index based on cursor vs sibling centres
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

    def _on_tab_change(event):
        idx = notebook.index('current')
        # Destroy any GHOST-panel tooltip that survived the tab switch
        if _guic_active_tip[0]:
            try: _guic_active_tip[0].destroy()
            except Exception: pass
            _guic_active_tip[0] = None
        if idx == 1: guic_redraw()
        else: redraw()
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

    tk_canvas.bind('<Button-1>',on_click)
    tk_canvas.bind('<B1-Motion>',on_motion)
    tk_canvas.bind('<Motion>',on_motion)
    tk_canvas.bind('<ButtonRelease-1>',on_release)
    tk_canvas.bind('<Double-Button-1>',on_double_click)
    tk_canvas.bind('<Leave>', lambda e: _hide_tooltip())
    root.bind('<Key>',on_key)

    def on_close():
        # Phase 6C: unified save for both tabs
        if fc_state['flow_symbols'] or fc_state['widgets']:
            ans = messagebox.askyesnocancel('Quit FlowCode',
                    'Save before closing?')
            if ans is None: return
            if ans: guic_do_save()
        root.destroy()
    root.protocol('WM_DELETE_WINDOW', on_close)
    set_mode('select')
    root.after(100,redraw)
    root.mainloop()


if __name__=='__main__':
    if '--headless' in sys.argv or '--test' in sys.argv:
        run_headless_demo()
    else:
        run_gui()
