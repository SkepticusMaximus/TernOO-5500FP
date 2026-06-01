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

    canvas_model = FCCanvas()
    cpu = CPU5500FP(); cpu.write_cs(0,1000); cpu.write_ds(0,2000)

    state = {
        'mode':         'select',
        'selected_sym': None,
        'selected_edge':None,
        'edge_src':     None,
        'edge_waypoints':[],       # collected waypoints for current edge
        'drag_offset':  (0,0),
        'dragging':     False,
        'ghost':        None,
        'hover_wp':     None,      # waypoint index being hovered
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
    notebook.add(fc_tab, text='  FlowCode  ')

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
    notebook.add(ghost_tab, text='  GHOST Canvas  ')

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
        if not _TernOOInterpreter:
            set_status("Interpreter not found — place ternoo_interpreter.py in 5500fp/")
            return
        if not canvas_model.symbols:
            set_status("Canvas is empty — draw some symbols first")
            return

        # Serialize current canvas to dict
        data = {
            'symbols': [s.to_dict() for s in canvas_model.symbols.values()],
            'edges':   [e.to_dict() for e in canvas_model.edges],
        }

        print(f"\n{'═'*56}")
        print(f"  FlowCode → Running canvas ({len(canvas_model.symbols)} symbols)")
        print(f"{'═'*56}")

        # Create interpreter with a step callback that highlights
        # the currently executing symbol on the canvas
        interp = _TernOOInterpreter(trace=True)

        # Highlight callback — called before each node executes
        def on_step(node_id):
            state['selected_sym']  = node_id
            state['selected_edge'] = None
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
            root.update()   # force UI refresh during execution

        # Patch execute_node to call our highlight
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
        canvas_model.print_word_dump()
        set_status(f"Word dump → terminal ({len(canvas_model.to_word_program())} words)")
    def do_load():
        end=canvas_model.load_into_emulator(cpu,100)
        n=end-100
        set_status(f"Loaded {n} words → emulator  (addr 100–{end-1})")
        print(f"[FlowCode] Loaded {n} TernOO words into emulator at addr 100–{end-1}")
    def do_save():
        p=filedialog.asksaveasfilename(defaultextension='.json',
            filetypes=[('FlowCode JSON','*.json'),('All','*.*')])
        if p:
            canvas_model.save(p)
            root.title(f"FlowCode v0.6.0 — {os.path.basename(p)}")
            set_status(f"Saved: {os.path.basename(p)}")
    def do_open():
        p=filedialog.askopenfilename(
            filetypes=[('FlowCode JSON','*.json'),('All','*.*')])
        if p:
            canvas_model.load(p)
            state['selected_sym']=None; state['selected_edge']=None
            root.title(f"FlowCode v0.6.0 — {os.path.basename(p)}")
            set_status(f"Loaded: {os.path.basename(p)}"); redraw()
    def do_clear():
        if canvas_model.symbols:
            if not messagebox.askyesno('Clear Canvas',
                    'Clear the canvas? Unsaved changes will be lost.'):
                return
        canvas_model.symbols.clear(); canvas_model.edges.clear()
        state['selected_sym']=None; state['selected_edge']=None
        FCSymbol._next_id=1
        set_inspect('Canvas cleared'); set_status('Cleared'); redraw()

    def do_learn():
        """Train the FlowCodeBrain on the current canvas."""
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
        # Save updated brain
        import json as _json
        bf = _find_brain_file() or os.path.expanduser(
            '~/dev/SkepticusMaximus/TernOO-5500FP/5500fp/flowcode_brain.json')
        with open(bf, 'w') as _f:
            _json.dump(_brain_instance.to_json(), _f, indent=2)
        set_status(f"Brain learned {len(transitions)} transitions — saved")
        print(f"[FlowCode] Brain trained: {len(transitions)} transitions from canvas")
        # Show weight matrix in terminal
        _brain_instance.show_weights()

    def do_suggest():
        """Ask the brain what symbol should come next."""
        if not _brain_instance:
            set_status("Brain not available")
            return
        # Find the last placed or selected symbol
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
        set_status(f"Brain suggests: after {tok} → {nxt.upper()} ({conf})")
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

    # ── Drawing ───────────────────────────────────────────────────────────────

    def draw_grid():
        w=tk_canvas.winfo_width() or 860
        h=tk_canvas.winfo_height() or 660
        for x in range(0,w,GRID): tk_canvas.create_line(x,0,x,h,fill=C['grid'])
        for y in range(0,h,GRID): tk_canvas.create_line(0,y,w,y,fill=C['grid'])

    def draw_symbol(s):
        sel = s.id==state['selected_sym']
        fill = C['selected'] if sel else {
            SYMBOL_PROCESS:C['process'],SYMBOL_DECISION:C['decision'],
            SYMBOL_IO:C['io'],SYMBOL_TERMINATOR:C['terminator']
        }.get(s.kind,C['process'])
        bor = C['selected'] if sel else C['border']
        lw = 3 if sel else 2
        x,y=s.x,s.y; hw,hh=SYMBOL_W//2,SYMBOL_H//2

        if s.kind==SYMBOL_PROCESS:
            tk_canvas.create_rectangle(x-hw,y-hh,x+hw,y+hh,
                                       fill=fill,outline=bor,width=lw)
        elif s.kind==SYMBOL_DECISION:
            tk_canvas.create_polygon([x,y-hh,x+hw,y,x,y+hh,x-hw,y],
                                     fill=fill,outline=bor,width=lw)
        elif s.kind==SYMBOL_IO:
            r=12
            tk_canvas.create_rectangle(x-hw+r,y-hh,x+hw-r,y+hh,fill=fill,outline=fill)
            tk_canvas.create_oval(x-hw,y-hh,x-hw+r*2,y+hh,fill=fill,outline=bor,width=lw)
            tk_canvas.create_oval(x+hw-r*2,y-hh,x+hw,y+hh,fill=fill,outline=bor,width=lw)
            tk_canvas.create_line(x-hw+r,y-hh,x+hw-r,y-hh,fill=bor,width=lw)
            tk_canvas.create_line(x-hw+r,y+hh,x+hw-r,y+hh,fill=bor,width=lw)
        elif s.kind==SYMBOL_TERMINATOR:
            tk_canvas.create_oval(x-hw,y-hh,x+hw,y+hh,
                                  fill=fill,outline=bor,width=lw)

        tk_canvas.create_text(x,y,text=s.label,fill=C['text'],
                              font=('Monospace',10,'bold'))
        tk_canvas.create_text(x,y+hh+10,text=describe_word(s.to_udp_word())[:28],
                              fill=C['dim'],font=('Monospace',7))
        if s.kind == SYMBOL_DECISION and s.default_output:
            tk_canvas.create_text(x,y+hh+22,text=f"→{s.default_output}",
                                  fill=C['waypoint'],font=('Monospace',7,'bold'))
        if sel:
            tk_canvas.create_text(x,y-hh-10,text=f"({x},{y})",
                                  fill=C['selected'],font=('Monospace',7))

        # Draw connection points when in edge mode
        if state['mode'] in ('edge_src','edge_dst_pending'):
            for name,(cx,cy) in s.connection_points().items():
                if name=='C': continue
                tk_canvas.create_oval(cx-4,cy-4,cx+4,cy+4,
                                      fill=C['pal_border'],outline=C['border'])

    def draw_edge(e):
        sel_e = state['selected_edge']
        is_sel = (sel_e and sel_e.get('src')==e.src_id
                  and sel_e.get('dst')==e.dst_id)
        col = C['selected'] if is_sel else {
            EXEC_CALL_STACK:C['edge_stk'],
            EXEC_CALL_REGISTER:C['edge'],
            EXEC_CALL_MESSAGE:C['edge_msg']}.get(e.call_style,C['edge'])
        lw = 3 if is_sel else 2
        dash = (6,3) if e.call_style==EXEC_CALL_MESSAGE else None

        pts = canvas_model._ortho_points(e)
        if len(pts)<2: return

        # Draw each segment
        for i in range(len(pts)-1):
            x1,y1=pts[i]; x2,y2=pts[i+1]
            last = (i==len(pts)-2)
            kw = dict(fill=col,width=lw)
            if dash: kw['dash']=dash
            if last: kw.update(arrow='last',arrowshape=(16,20,6))
            tk_canvas.create_line(x1,y1,x2,y2,**kw)

        # Waypoint handles
        for wx,wy in e.waypoints:
            tk_canvas.create_oval(wx-5,wy-5,wx+5,wy+5,
                                  fill=C['waypoint'],outline=C['border'],width=1)

        # Edge labels: condition always, EXEC on selected only
        if len(pts)>=2:
            # Place label 2/3 along first segment, away from source symbol
            mx=(pts[0][0]+pts[1][0]*2)//3; my=(pts[0][1]+pts[1][1]*2)//3-10
            if e.condition:
                tk_canvas.create_text(mx,my,text=f"[{e.condition}]",
                                      fill=C['waypoint'],font=('Monospace',8,'bold'))
            if is_sel:
                priv={-1:'K',0:'U',1:'S'}.get(e.privilege,'?')
                call={-1:'stk',0:'reg',1:'msg'}.get(e.call_style,'?')
                ret={-1:'X',0:'M',1:'D'}.get(e.return_type,'?')
                tk_canvas.create_text(mx,my+(14 if e.condition else 0),
                                      text=f"EXEC {priv}/{call}→{ret}",
                                      fill=col,font=('Monospace',7))

    def draw_edge_in_progress():
        """Draw the edge being constructed with waypoints collected so far."""
        src_id = state.get('edge_src')
        if not src_id: return
        src = canvas_model.symbols.get(src_id)
        if not src: return
        pts = [(src.x,src.y)] + state['edge_waypoints']
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
        for e in canvas_model.edges: draw_edge(e)
        for s in canvas_model.symbols.values(): draw_symbol(s)
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
        sid=state['selected_sym']; se=state['selected_edge']
        if sid and sid in canvas_model.symbols:
            s=canvas_model.symbols[sid]
            udp=s.to_udp_word(); mp=s.to_map_word()
            set_inspect(
                f"Symbol #{s.id}  {s.kind.upper()}  '{s.label}'\n"
                f"  UDP: {describe_word(udp)}\n"
                f"       {word_to_str(udp)}\n"
                f"  MAP: {describe_word(mp)}\n"
                f"       {word_to_str(mp)}")
        elif se:
            for e in canvas_model.edges:
                if e.src_id==se.get('src') and e.dst_id==se.get('dst'):
                    ew=e.to_exec_word()
                    src=canvas_model.symbols.get(e.src_id)
                    dst=canvas_model.symbols.get(e.dst_id)
                    sl=src.label if src else f"#{e.src_id}"
                    dl=dst.label if dst else f"#{e.dst_id}"
                    call={-1:'stack',0:'register',1:'message'}.get(e.call_style,'?')
                    cond_str = f"  condition='{e.condition}'" if e.condition else ""
                    set_inspect(
                        f"Edge  {sl} → {dl}"
                        f"  ({len(e.waypoints)} waypoints)\n"
                        f"  EXEC: {describe_word(ew)}\n"
                        f"        {word_to_str(ew)}\n"
                        f"  Call: {call}  "
                        f"Priv: {['kernel','user','sandbox'][e.privilege+1]}  "
                        f"Ret: {['EXEC','MAP','DATA'][e.return_type+1]}"
                        f"{cond_str}")
                    break
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
        _hide_tooltip()
        sym = canvas_model.symbol_at(event.x, event.y)
        if sym:
            tip = f"{sym.kind.upper()} #{sym.id}  '{sym.label}'\nUDP: {describe_word(sym.to_udp_word())}"
            if sym.kind == SYMBOL_DECISION and getattr(sym,'default_output',''):
                tip += f"\ndefault → {sym.default_output}"
            ex, ey = event.x, event.y
            _tooltip_after[0] = root.after(700, lambda: _show_tooltip(ex, ey, tip))
        else:
            edg = canvas_model.edge_near(event.x, event.y)
            if edg:
                srcs = canvas_model.symbols.get(edg.src_id)
                dsts = canvas_model.symbols.get(edg.dst_id)
                sl = srcs.label if srcs else f"#{edg.src_id}"
                dl = dsts.label if dsts else f"#{edg.dst_id}"
                tip = f"Edge  {sl} → {dl}"
                if edg.condition: tip += f"\ncondition: {edg.condition}"
                tip += f"\n{describe_word(edg.to_exec_word())}"
                ex, ey = event.x, event.y
                _tooltip_after[0] = root.after(700, lambda: _show_tooltip(ex, ey, tip))

    # ── Event handlers ────────────────────────────────────────────────────────

    def on_motion(event):
        state['ghost']=(event.x,event.y)
        if state['dragging'] and state['selected_sym']:
            s=canvas_model.symbols.get(state['selected_sym'])
            if s:
                dx,dy=state['drag_offset']
                s.x=snap(event.x-dx); s.y=snap(event.y-dy)
            _hide_tooltip()
        else:
            _schedule_tooltip(event)
        redraw()

    def on_click(event):
        x,y=event.x,event.y
        mode=state['mode']

        # Placement modes
        if mode in ('place_terminator','place_process','place_decision','place_io'):
            kind={'place_terminator':SYMBOL_TERMINATOR,
                  'place_process':SYMBOL_PROCESS,
                  'place_decision':SYMBOL_DECISION,
                  'place_io':SYMBOL_IO}[mode]
            s=canvas_model.add_symbol(kind,x,y)
            state['selected_sym']=s.id; state['selected_edge']=None
            state['ghost']=None
            set_status(f"Placed {s.label}")
            update_inspect(); set_mode('select'); return

        # Delete mode
        if mode=='delete':
            hit_s=canvas_model.symbol_at(x,y)
            hit_e=canvas_model.edge_near(x,y)
            if hit_s:
                canvas_model.remove_symbol(hit_s.id)
                if state['selected_sym']==hit_s.id: state['selected_sym']=None
                set_status(f"Deleted {hit_s.label}")
                set_inspect("Select a symbol or edge to inspect")
            elif hit_e:
                canvas_model.remove_edge(hit_e.src_id,hit_e.dst_id)
                state['selected_edge']=None
                set_status("Edge deleted")
            redraw(); return

        # Edge source selection
        if mode=='edge_src':
            hit=canvas_model.symbol_at(x,y)
            if hit:
                state['edge_src']=hit.id
                state['edge_waypoints']=[]
                state['mode']='edge_dst_pending'
                set_status(f"From {hit.label} — click canvas for waypoints, "
                           f"click target symbol to finish")
            redraw(); return

        # Edge waypoint / destination
        if state['mode']=='edge_dst_pending':
            hit=canvas_model.symbol_at(x,y)
            if hit and hit.id!=state['edge_src']:
                # Finalise edge
                wps=state['edge_waypoints']
                e=canvas_model.add_edge(state['edge_src'],hit.id,waypoints=wps)
                if e:
                    src=canvas_model.symbols[state['edge_src']]
                    state['selected_edge']={'src':e.src_id,'dst':e.dst_id}
                    state['selected_sym']=None
                    set_status(f"Edge {src.label}→{hit.label}"
                               f" ({len(wps)} waypoints)")
                    update_inspect()
                state['edge_src']=None; state['edge_waypoints']=[]
                set_mode('select')
            elif hit and hit.id==state['edge_src']:
                set_status("Can't connect to self — click canvas or different symbol")
            else:
                # Add waypoint (snapped)
                wx,wy=snap(x),snap(y)
                state['edge_waypoints'].append((wx,wy))
                set_status(f"Waypoint added ({wx},{wy}) — "
                           f"{len(state['edge_waypoints'])} total. "
                           f"Click target symbol to finish, or add more.")
            redraw(); return

        # Select mode
        hit_s=canvas_model.symbol_at(x,y)
        hit_e=canvas_model.edge_near(x,y)
        if hit_s:
            state['selected_sym']=hit_s.id; state['selected_edge']=None
            state['drag_offset']=(x-hit_s.x,y-hit_s.y); state['dragging']=True
        elif hit_e:
            state['selected_edge']={'src':hit_e.src_id,'dst':hit_e.dst_id}
            state['selected_sym']=None; state['dragging']=False
        else:
            state['selected_sym']=None; state['selected_edge']=None
            state['dragging']=False
        update_inspect(); redraw()

    def on_release(event):
        if state['dragging'] and state['selected_sym']:
            s=canvas_model.symbols.get(state['selected_sym'])
            if s: set_status(f"Moved {s.label} → ({s.x},{s.y})"); update_inspect()
        state['dragging']=False

    def on_double_click(event):
        hit_s = canvas_model.symbol_at(event.x, event.y)
        hit_e = canvas_model.edge_near(event.x, event.y)
        if hit_s:
            _open_symbol_props(hit_s)
        elif hit_e:
            _open_edge_props(hit_e)

    def _open_symbol_props(s):
        """Modal dialog to edit symbol label, code_seg, data_seg, offset."""
        dlg = tk.Toplevel(root)
        dlg.title(f"Symbol Properties — {s.label}")
        dlg.configure(bg=C['bg'])
        dlg.resizable(False, False)

        def _row(parent, text, row):
            tk.Label(parent, text=text, bg=C['bg'], fg=C['inspect_fg'],
                     font=('Monospace', 9), anchor='e', width=12
                     ).grid(row=row, column=0, padx=8, pady=4, sticky='e')
            var = tk.StringVar()
            ent = tk.Entry(parent, textvariable=var, bg=C['canvas'],
                           fg=C['text'], insertbackground=C['text'],
                           font=('Monospace', 10), width=20,
                           relief='flat', bd=4)
            ent.grid(row=row, column=1, padx=8, pady=4)
            return var

        frm = tk.Frame(dlg, bg=C['bg']); frm.pack(padx=12, pady=8)

        tk.Label(frm, text=f"{s.kind.upper()}  #{s.id}",
                 bg=C['bg'], fg=C['pal_border'],
                 font=('Monospace', 10, 'bold')
                 ).grid(row=0, column=0, columnspan=2, pady=(0,8))

        v_label    = _row(frm, "Label:",    1)
        v_code_seg = _row(frm, "code_seg:", 2)
        v_data_seg = _row(frm, "data_seg:", 3)
        v_offset   = _row(frm, "offset:",   4)

        v_label.set(s.label)
        v_code_seg.set(str(s.code_seg))
        v_data_seg.set(str(s.data_seg))
        v_offset.set(str(s.offset))

        # Default output dropdown — decision nodes only
        v_default = None
        if s.kind == SYMBOL_DECISION:
            outgoing_conds = [e.condition for e in canvas_model.edges
                              if e.src_id == s.id and e.condition]
            tk.Label(frm, text='default out:', bg=C['bg'], fg=C['inspect_fg'],
                     font=('Monospace', 9), anchor='e', width=12
                     ).grid(row=5, column=0, padx=8, pady=4, sticky='e')
            v_default = tk.StringVar(value=s.default_output or '(none)')
            opts = ['(none)'] + outgoing_conds
            om = tk.OptionMenu(frm, v_default, *opts)
            om.config(bg=C['canvas'], fg=C['text'], activebackground=C['pal_active'],
                      activeforeground=C['text'], font=('Monospace', 9),
                      relief='flat', highlightthickness=0)
            om['menu'].config(bg=C['canvas'], fg=C['text'], font=('Monospace', 9))
            om.grid(row=5, column=1, padx=8, pady=4, sticky='ew')
            tk.Label(frm, text='fallback branch if no runtime result',
                     bg=C['bg'], fg=C['dim'], font=('Monospace', 7),
                     ).grid(row=6, column=0, columnspan=2, pady=(0,4))

        # TernOO word preview
        preview_row = 7 if s.kind == SYMBOL_DECISION else 5
        preview = tk.Label(frm, text='', bg=C['inspect'], fg=C['inspect_fg'],
                           font=('Monospace', 8), anchor='w', justify='left',
                           padx=6, pady=4, width=38)
        preview.grid(row=preview_row, column=0, columnspan=2,
                     padx=0, pady=4, sticky='ew')

        def _update_preview(*_):
            try:
                cs = int(v_code_seg.get() or 0)
                ds = int(v_data_seg.get() or 0)
                off = int(v_offset.get() or 0)
                t1, t0 = SYMBOL_SUBCLASS[s.kind]
                w = build_udp_word(t1, t0, off, cs, ds)
                preview.config(text=f"UDP: {describe_word(w)}\n     {word_to_str(w)}")
            except Exception:
                preview.config(text="(invalid values)")

        for v in (v_label, v_code_seg, v_data_seg, v_offset):
            v.trace_add('write', _update_preview)
        _update_preview()

        def _apply():
            lbl = v_label.get().strip()
            if lbl: s.label = lbl
            try: s.code_seg = int(v_code_seg.get() or 0)
            except ValueError: pass
            try: s.data_seg = int(v_data_seg.get() or 0)
            except ValueError: pass
            try: s.offset   = int(v_offset.get() or 0)
            except ValueError: pass
            if v_default is not None:
                chosen = v_default.get()
                s.default_output = '' if chosen == '(none)' else chosen
            set_status(f"Updated {s.label}  code_seg={s.code_seg}"
                       f"  data_seg={s.data_seg}  offset={s.offset}")
            update_inspect(); redraw(); dlg.destroy()

        btn_frm = tk.Frame(dlg, bg=C['bg']); btn_frm.pack(pady=8)
        tk.Button(btn_frm, text="Apply", command=_apply,
                  bg=C['pal_active'], fg=C['text'],
                  font=('Monospace', 9, 'bold'),
                  relief='flat', padx=12, pady=4,
                  cursor='hand2').pack(side='left', padx=6)
        tk.Button(btn_frm, text="Cancel", command=dlg.destroy,
                  bg=C['pal_btn'], fg=C['dim'],
                  font=('Monospace', 9),
                  relief='flat', padx=12, pady=4,
                  cursor='hand2').pack(side='left', padx=6)
        dlg.bind('<Return>', lambda e: _apply())
        dlg.bind('<Escape>', lambda e: dlg.destroy())
        dlg.update_idletasks()
        dlg.grab_set()
        dlg.focus_force()

    def _open_edge_props(e):
        """Modal dialog to edit edge condition, call_style, privilege, return_type."""
        src = canvas_model.symbols.get(e.src_id)
        dst = canvas_model.symbols.get(e.dst_id)
        sl  = src.label if src else f"#{e.src_id}"
        dl  = dst.label if dst else f"#{e.dst_id}"

        dlg = tk.Toplevel(root)
        dlg.title(f"Edge Properties — {sl} → {dl}")
        dlg.configure(bg=C['bg'])
        dlg.resizable(False, False)

        frm = tk.Frame(dlg, bg=C['bg']); frm.pack(padx=12, pady=8)

        tk.Label(frm, text=f"Edge  {sl} → {dl}",
                 bg=C['bg'], fg=C['pal_border'],
                 font=('Monospace', 10, 'bold')
                 ).grid(row=0, column=0, columnspan=2, pady=(0,8))

        def _lbl(text, row):
            tk.Label(frm, text=text, bg=C['bg'], fg=C['inspect_fg'],
                     font=('Monospace', 9), anchor='e', width=14
                     ).grid(row=row, column=0, padx=8, pady=4, sticky='e')

        # Condition label (free text)
        _lbl("Condition:", 1)
        v_cond = tk.StringVar(value=e.condition)
        tk.Entry(frm, textvariable=v_cond, bg=C['canvas'], fg=C['text'],
                 insertbackground=C['text'], font=('Monospace', 10), width=18,
                 relief='flat', bd=4
                 ).grid(row=1, column=1, padx=8, pady=4)

        # Call style
        _lbl("Call style:", 2)
        call_opts = ['stack', 'register', 'message']
        call_vals = [-1, 0, 1]
        v_call = tk.StringVar(value=call_opts[e.call_style + 1])
        tk.OptionMenu(frm, v_call, *call_opts
                      ).grid(row=2, column=1, padx=8, pady=4, sticky='ew')

        # Privilege
        _lbl("Privilege:", 3)
        priv_opts = ['kernel', 'user', 'sandbox']
        priv_vals = [-1, 0, 1]
        v_priv = tk.StringVar(value=priv_opts[e.privilege + 1])
        tk.OptionMenu(frm, v_priv, *priv_opts
                      ).grid(row=3, column=1, padx=8, pady=4, sticky='ew')

        # Return type
        _lbl("Return type:", 4)
        ret_opts = ['EXEC', 'MAP', 'DATA']
        ret_vals = [-1, 0, 1]
        v_ret = tk.StringVar(value=ret_opts[e.return_type + 1])
        tk.OptionMenu(frm, v_ret, *ret_opts
                      ).grid(row=4, column=1, padx=8, pady=4, sticky='ew')

        # EXEC word preview
        preview = tk.Label(frm, text="", bg=C['inspect'], fg=C['inspect_fg'],
                           font=('Monospace', 8), anchor='w', justify='left',
                           padx=6, pady=4, width=38)
        preview.grid(row=5, column=0, columnspan=2, padx=0, pady=4, sticky='ew')

        def _update_preview(*_):
            try:
                cs = call_vals[call_opts.index(v_call.get())]
                pr = priv_vals[priv_opts.index(v_priv.get())]
                rt = ret_vals[ret_opts.index(v_ret.get())]
                w  = build_exec_word(pr, cs, rt, e.seg_idx, e.offset)
                cond = v_cond.get().strip()
                cond_str = f"  [{cond}]" if cond else ""
                preview.config(text=f"EXEC: {describe_word(w)}{cond_str}\n"
                                    f"      {word_to_str(w)}")
            except Exception:
                preview.config(text="(invalid)")

        for v in (v_cond, v_call, v_priv, v_ret):
            v.trace_add('write', _update_preview)
        _update_preview()

        def _apply():
            e.condition   = v_cond.get().strip()
            e.call_style  = call_vals[call_opts.index(v_call.get())]
            e.privilege   = priv_vals[priv_opts.index(v_priv.get())]
            e.return_type = ret_vals[ret_opts.index(v_ret.get())]
            set_status(f"Edge {sl}→{dl}  condition='{e.condition}'"
                       f"  call={v_call.get()}  priv={v_priv.get()}")
            update_inspect(); redraw(); dlg.destroy()

        btn_frm = tk.Frame(dlg, bg=C['bg']); btn_frm.pack(pady=8)
        tk.Button(btn_frm, text="Apply", command=_apply,
                  bg=C['pal_active'], fg=C['text'],
                  font=('Monospace', 9, 'bold'),
                  relief='flat', padx=12, pady=4,
                  cursor='hand2').pack(side='left', padx=6)
        tk.Button(btn_frm, text="Cancel", command=dlg.destroy,
                  bg=C['pal_btn'], fg=C['dim'],
                  font=('Monospace', 9),
                  relief='flat', padx=12, pady=4,
                  cursor='hand2').pack(side='left', padx=6)
        dlg.bind('<Return>', lambda e: _apply())
        dlg.bind('<Escape>', lambda e: dlg.destroy())
        dlg.update_idletasks()
        dlg.grab_set()
        dlg.focus_force()

    def on_key(event):
        if notebook.index('current') != 0:
            return   # Let GHOST canvas handle its own keys
        k=event.keysym.lower()
        if k=='t': set_mode('place_terminator')
        elif k=='r': set_mode('place_process')
        elif k=='d': set_mode('place_decision')
        elif k=='i': set_mode('place_io')
        elif k=='e': set_mode('edge_src')
        elif k=='escape': set_mode('select')
        elif k=='w': do_dump()
        elif k=='l': do_load()
        elif k=='delete':
            if state['selected_sym']:
                s=canvas_model.symbols.get(state['selected_sym'])
                if s:
                    canvas_model.remove_symbol(state['selected_sym'])
                    state['selected_sym']=None
                    set_status(f"Deleted {s.label}")
                    set_inspect("Select a symbol or edge to inspect"); redraw()
            elif state['selected_edge']:
                e=state['selected_edge']
                canvas_model.remove_edge(e['src'],e['dst'])
                state['selected_edge']=None
                set_status("Edge deleted"); redraw()
        elif event.state & 0x4:
            if k=='s': do_save()
            elif k=='o': do_open()
            elif k=='z': set_mode('select')  # Ctrl+Z as cancel/escape

    # ═══════════════════════════════════════════════════════════════════════════
    # GHOST Canvas tab
    # ═══════════════════════════════════════════════════════════════════════════

    GW, GH = 140, 52   # widget block size on ghost canvas

    # Category colour by Y-range bracket
    def _ghost_cat_color(y_lo):
        if y_lo >= 500: return '#0f3060'   # containers  — blue
        if y_lo >= 400: return '#3a1060'   # controls    — purple
        if y_lo >= 300: return '#0f3a3a'   # inputs      — teal
        if y_lo >= 200: return '#0f3a1a'   # display     — green
        if y_lo >= 100: return '#3a2a0f'   # dialogs     — amber
        return '#3a0f1a'                    # menus       — dark red

    _gc_color = {t: _ghost_cat_color(y) for t, y in _ghost_palette_types}

    # ── GHOST canvas state ────────────────────────────────────────────────────
    gst = {
        'widgets':    {},    # id → {id, kind, x, y, label}
        'edges':      [],    # [{src, dst}, …]
        'selected':   None,
        'mode':       'select',   # select | place | edge_src | edge_dst | delete
        'place_kind': None,
        'edge_src':   None,
        'next_id':    0,
        'dragging':   False,
        'drag_offset':(0, 0),
    }

    # ── Ghost canvas layout ───────────────────────────────────────────────────
    gc_pal   = tk.Frame(ghost_tab, bg=C['palette'], width=PALETTE_W)
    gc_pal.pack(side='left', fill='y'); gc_pal.pack_propagate(False)
    gc_right = tk.Frame(ghost_tab, bg=C['bg'])
    gc_right.pack(side='left', fill='both', expand=True)
    gc       = tk.Canvas(gc_right, bg=C['canvas'], highlightthickness=0)
    gc.pack(fill='both', expand=True)
    gc_bar   = tk.Label(gc_right,
                        text="GHOST Canvas — pick a widget type from the palette",
                        bg=C['status'], fg=C['pal_border'],
                        font=('Monospace', 9), anchor='w', padx=8)
    gc_bar.pack(side='bottom', fill='x', ipady=3)

    def gc_set_status(m): gc_bar.config(text=m)

    def gc_set_mode(m, kind=None):
        gst['mode'] = m; gst['place_kind'] = kind
        if m == 'select':   gc_set_status("GHOST Canvas — select, drag, or connect widgets")
        elif m == 'place':  gc_set_status(f"Click canvas to place  {kind}  (Esc to cancel)")
        elif m == 'edge_src': gc_set_status("Click the parent (source) widget")
        elif m == 'edge_dst': gc_set_status("Click the child (destination) widget")
        elif m == 'delete': gc_set_status("Click a widget or edge to delete it")

    # ── Palette ───────────────────────────────────────────────────────────────
    tk.Label(gc_pal, text="GHOST", bg=C['palette'], fg=C['pal_border'],
             font=('Monospace', 9, 'bold'), pady=6).pack(fill='x')
    tk.Label(gc_pal, text="WIDGETS", bg=C['palette'], fg=C['pal_border'],
             font=('Monospace', 9, 'bold')).pack(fill='x')
    tk.Frame(gc_pal, bg=C['dim'], height=1).pack(fill='x', padx=6, pady=2)

    _gc_pal_inner = tk.Frame(gc_pal, bg=C['palette'])
    _gc_pal_inner.pack(fill='x')

    _gc_grp_cur = [None]
    _gc_grp_names = {
        5: 'CONTAINERS', 4: 'CONTROLS', 3: 'INPUTS',
        2: 'DISPLAY', 1: 'DIALOGS', 0: 'MENUS',
    }
    for wtype, y_lo in _ghost_palette_types:
        grp_key = y_lo // 100
        if grp_key != _gc_grp_cur[0]:
            _gc_grp_cur[0] = grp_key
            tk.Label(_gc_pal_inner, text=_gc_grp_names.get(grp_key, ''),
                     bg=C['palette'], fg=C['dim'],
                     font=('Monospace', 7), pady=1).pack(fill='x', padx=4)
        col   = _gc_color.get(wtype, C['pal_btn'])
        short = wtype.replace('gui_', '')
        tk.Button(_gc_pal_inner, text=short,
                  bg=col, fg=C['text'],
                  font=('Monospace', 8), relief='flat', bd=0,
                  padx=4, pady=2, cursor='hand2', anchor='w',
                  command=lambda k=wtype: gc_set_mode('place', k)
                  ).pack(fill='x', padx=4, pady=1)

    tk.Frame(gc_pal, bg=C['dim'], height=1).pack(fill='x', padx=6, pady=4)

    # ── Action buttons ────────────────────────────────────────────────────────
    def gc_do_connect(): gc_set_mode('edge_src')
    def gc_do_delete():  gc_set_mode('delete')

    def gc_do_suggest():
        sel = gst['selected']
        if sel is None or sel not in gst['widgets']:
            gc_set_status("Select a widget first, then Suggest"); return
        kind = gst['widgets'][sel]['kind']
        row  = {k: v for k, v in _ghost_weights.get(kind, {}).items() if k != kind}
        if not row:
            gc_set_status(f"No suggestions for {kind} — train more first"); return
        best  = max(row, key=row.get)
        total = sum(row.values())
        pct   = int(100 * row[best] / total) if total else 0
        # Auto-place suggested widget to the right of selected
        sw  = gst['widgets'][sel]
        nid = gst['next_id']; gst['next_id'] += 1
        gst['widgets'][nid] = {
            'id': nid, 'kind': best,
            'x': snap(sw['x'] + GW + 30), 'y': sw['y'],
            'label': best.replace('gui_', ''),
        }
        gst['edges'].append({'src': sel, 'dst': nid})
        gst['selected'] = nid
        gc_set_status(f"GHOST suggests: {kind} → {best}  ({pct}%)")
        gc_redraw()

    def gc_do_clear():
        if gst['widgets']:
            from tkinter import messagebox as _mb2
            if not _mb2.askyesno('Clear', 'Clear GHOST canvas?'): return
        gst['widgets'].clear(); gst['edges'].clear()
        gst['selected'] = None; gst['next_id'] = 0
        gc_set_mode('select'); gc_redraw()

    def gc_do_save():
        if not gst['widgets']:
            gc_set_status("Nothing to save"); return
        path = filedialog.asksaveasfilename(
            parent=root, title='Save GHOST design as .tgui',
            defaultextension='.tgui',
            filetypes=[('TernOO GUI training', '*.tgui'), ('All files', '*.*')])
        if not path: return
        syms  = [{'id': w['id'], 'kind': w['kind'], 'label': w['label'],
                  'gtk_class': '', 'x': w['x'], 'y': w['y'], 'depth': 0,
                  'properties': [], 'signals': []}
                 for w in gst['widgets'].values()]
        edges = [{'src': e['src'], 'dst': e['dst'],
                  'privilege': 0, 'call_style': 0, 'return_type': 1,
                  'seg_idx': 0, 'offset': 0, 'waypoints': [], 'condition': ''}
                 for e in gst['edges']]
        tgui  = {
            'tgui_version': '0.1',
            'source_file':  os.path.basename(path),
            'source_type':  'ghost_canvas',
            'symbols':      syms,
            'edges':        edges,
            'sequence':     [w['id'] for w in gst['widgets'].values()],
            'tgui_meta': {
                'widget_count':    len(syms),
                'edge_count':      len(edges),
                'mmoe_types_used': list({w['kind'] for w in gst['widgets'].values()}),
            },
        }
        with open(path, 'w') as _sf:
            json.dump(tgui, _sf, indent=2)
        gc_set_status(f"Saved: {os.path.basename(path)}")

    for _lbl, _cmd, _fg in [
        ('⬡ Connect', gc_do_connect, '#7aff7a'),
        ('✕ Delete',  gc_do_delete,  '#ff8888'),
        ('💡 Suggest', gc_do_suggest, '#ffcc44'),
        ('🗑 Clear',  gc_do_clear,   '#ff8888'),
        ('💾 Save',   gc_do_save,    '#7ab4ff'),
    ]:
        tk.Button(gc_pal, text=_lbl, command=_cmd,
                  bg=C['pal_btn'], fg=_fg,
                  font=('Monospace', 8), relief='flat', bd=0,
                  padx=4, pady=3, cursor='hand2', anchor='w'
                  ).pack(fill='x', padx=4, pady=1)

    tk.Label(gc_pal, text="GHOST Canvas\nv0.6.0",
             bg=C['palette'], fg=C['dim'],
             font=('Monospace', 7), pady=4
             ).pack(side='bottom', fill='x')

    # ── Drawing ───────────────────────────────────────────────────────────────
    def gc_draw_grid():
        w = gc.winfo_width() or 860; h = gc.winfo_height() or 660
        for x in range(0, w, GRID): gc.create_line(x, 0, x, h, fill=C['grid'])
        for y in range(0, h, GRID): gc.create_line(0, y, w, y, fill=C['grid'])

    def gc_draw_widget(w):
        # ── Added: 01 Jun 2026, Adelaide
        # ── Purpose: placeholder — geometry renderer (CC-09) replaces this
        # ── Each widget will be drawn from TernOO RNODE/RLINE/RPOINT words
        # ──   derived from GTK Cairo render geometry, not hand-coded primitives
        sel  = (w['id'] == gst['selected'])
        col  = _gc_color.get(w['kind'], C['pal_btn'])
        bor  = C['selected'] if sel else C['pal_border']
        lw   = 3 if sel else 1
        x, y = w['x'], w['y']
        hw, hh = GW // 2, GH // 2
        L, R, T, B = x - hw, x + hw, y - hh, y + hh
        kind = w['kind']
        txt  = C['text']; dim = C['dim']

        # Flat tile — category colour, type label, nothing pretending to be a widget
        gc.create_rectangle(L, T, R, B, fill=col, outline=bor, width=lw)
        gc.create_text(x, y - 5, text=kind.replace('gui_', ''),
                       fill=txt, font=('Monospace', 9, 'bold'))
        gc.create_text(x, y + 8, text='[ geometry pending ]',
                       fill=dim, font=('Monospace', 6))

        if False and kind in ('gui_window', 'gui_applicationwindow', 'gui_offscreenwindow',
                    'gui_plug', 'gui_socket', 'gui_shortcutswindow'):
            gc.create_rectangle(L, T, R, B, fill='#0a1828', outline=bor, width=lw)
            gc.create_rectangle(L, T, R, T+14, fill='#0d2040', outline=bor, width=1)
            gc.create_text(x, T+7, text=w.get('label','Window')[:18],
                           fill=txt, font=('Monospace',7,'bold'))
            for i,(fc) in enumerate(['#cc4444','#ccaa00','#44aa44']):
                gc.create_oval(R-10-i*13,T+3,R-4-i*13,T+9, fill=fc, outline='')
            gc.create_rectangle(L+4,T+18,R-4,B-4, fill='#07101e', outline=dim, width=1, dash=(3,3))

        elif kind in ('gui_dialog','gui_messagedialog','gui_aboutdialog','gui_assistant'):
            gc.create_rectangle(L, T, R, B, fill='#1a1008', outline=bor, width=lw)
            gc.create_rectangle(L, T, R, T+13, fill='#2a1a0a', outline=bor, width=1)
            gc.create_text(x, T+6, text=w.get('label','Dialog')[:18],
                           fill=txt, font=('Monospace',7,'bold'))
            gc.create_oval(R-8,T+3,R-3,T+9, fill='#cc4444', outline='')
            bw = 28
            gc.create_rectangle(R-bw-4,B-14,R-4,B-4, fill='#0f3060', outline=dim, width=1)
            gc.create_text(R-bw//2-4,B-9, text='OK', fill=txt, font=('Monospace',7))
            gc.create_rectangle(R-bw*2-8,B-14,R-bw-8,B-4, fill='#3a1010', outline=dim, width=1)
            gc.create_text(R-bw*3//2-8,B-9, text='Cancel', fill=txt, font=('Monospace',7))

        elif kind == 'gui_button':
            gc.create_rectangle(L+2,T+6,R-2,B-6, fill='#1a4a7a', outline=dim, width=1)
            gc.create_rectangle(L+2,T+6,R-2,T+10, fill='#2a5a8a', outline='')
            gc.create_rectangle(L+2,B-10,R-2,B-6, fill='#0d2a4a', outline='')
            gc.create_text(x, y, text=w.get('label','Button')[:14],
                           fill=txt, font=('Monospace',8,'bold'))

        elif kind in ('gui_toggle','gui_link','gui_menubutton'):
            gc.create_rectangle(L+2,T+6,R-2,B-6, fill='#2a1a5a', outline=dim, width=1)
            gc.create_text(x, y, text=w.get('label',kind.replace('gui_',''))[:14],
                           fill='#aaffcc', font=('Monospace',8))

        elif kind == 'gui_check':
            cx = L+10
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_rectangle(cx-7,y-7,cx+7,y+7, fill='#070d1a', outline=dim, width=1)
            gc.create_line(cx-4,y,cx,y+5,cx+6,y-5, fill='#44cc44', width=2)
            gc.create_text(cx+16+(hw//2),y, text=w.get('label','Check')[:10],
                           fill=txt, font=('Monospace',8))

        elif kind == 'gui_radio':
            cx = L+10
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_oval(cx-7,y-7,cx+7,y+7, fill='#070d1a', outline=dim, width=1)
            gc.create_oval(cx-3,y-3,cx+3,y+3, fill='#4a9eff', outline='')
            gc.create_text(cx+16+(hw//2),y, text=w.get('label','Radio')[:10],
                           fill=txt, font=('Monospace',8))

        elif kind == 'gui_switch':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            pw,ph = 40,18
            ox,oy = x-4, y
            gc.create_oval(ox-pw//2,oy-ph//2,ox-pw//2+ph,oy+ph//2, fill='#1a6b3a',outline=dim)
            gc.create_rectangle(ox-pw//2+ph//2,oy-ph//2,ox+pw//2-ph//2,oy+ph//2, fill='#1a6b3a',outline=dim)
            gc.create_oval(ox+pw//2-ph,oy-ph//2,ox+pw//2,oy+ph//2, fill='#1a6b3a',outline=dim)
            gc.create_oval(ox+pw//2-ph+2,oy-ph//2+2,ox+pw//2-2,oy+ph//2-2, fill='#e0e0e0',outline='')
            gc.create_text(ox+pw//2+14,oy, text='ON', fill='#44cc44', font=('Monospace',7,'bold'))

        elif kind == 'gui_entry':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_rectangle(L+4,T+10,R-4,B-10, fill='#050a12', outline=dim, width=1)
            gc.create_line(L+10,y,L+50,y, fill='#2a3050', width=1)
            gc.create_line(L+10,T+13,L+10,B-13, fill=C['pal_border'], width=1)

        elif kind == 'gui_searchentry':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_rectangle(L+4,T+10,R-4,B-10, fill='#050a12', outline=dim, width=1)
            gc.create_oval(L+8,T+13,L+16,B-13, outline=dim, width=1)
            gc.create_line(L+15,B-14,L+19,B-10, fill=dim, width=1)
            gc.create_line(L+22,y,L+55,y, fill='#2a3050', width=1)

        elif kind == 'gui_textview':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_rectangle(L+3,T+4,R-3,B-4, fill='#050a12', outline=dim, width=1)
            for i in range(3):
                yl = T+12+i*10
                gc.create_line(L+7,yl, R-7-(i*9)%18,yl, fill='#2a3050', width=1)

        elif kind == 'gui_label':
            gc.create_rectangle(L,T,R,B, fill=col, outline='', width=0)
            gc.create_text(x, y, text=w.get('label','Label')[:20],
                           fill=txt, font=('Monospace',9))

        elif kind == 'gui_image':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            inn = 8
            gc.create_rectangle(L+inn,T+inn,R-inn,B-inn, fill='#0a1220', outline=dim, width=1)
            mx,my = x, B-inn-4
            gc.create_polygon(mx-14,my,mx,T+inn+6,mx+14,my, fill=dim, outline='')
            gc.create_polygon(mx+4,my,mx+18,T+inn+12,mx+28,my, fill='#1a2a3a', outline='')
            gc.create_oval(L+inn+4,T+inn+4,L+inn+12,T+inn+12, fill='#ccaa00', outline='')

        elif kind == 'gui_progress':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_rectangle(L+6,y-7,R-6,y+7, fill='#050a12', outline=dim, width=1)
            gc.create_rectangle(L+6,y-7,L+6+(R-L-12)//2,y+7, fill='#1a6b3a', outline='')
            gc.create_text(x, y, text='50%', fill=txt, font=('Monospace',7))

        elif kind == 'gui_level':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            seg_w = (R-L-10)//5
            for i in range(5):
                sx2 = L+5+i*seg_w
                fc2 = '#1a6b3a' if i<3 else '#ccaa00' if i<4 else '#cc3333'
                gc.create_rectangle(sx2+1,y-6,sx2+seg_w-1,y+6, fill=fc2, outline='')

        elif kind == 'gui_scale':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_line(L+10,y,R-10,y, fill=dim, width=3)
            tx = x-10
            gc.create_oval(tx-7,y-7,tx+7,y+7, fill='#1a5a8a', outline=C['pal_border'], width=1)

        elif kind in ('gui_box','gui_grid','gui_canvas'):
            gc.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw, dash=(5,3))
            badge2 = kind.replace('gui_','')
            gc.create_text(x,T+9, text=f'‹ {badge2} ›', fill=dim, font=('Monospace',7,'italic'))
            if kind in ('gui_box','gui_grid'):
                for i in range(1,3):
                    gx = L+(R-L)*i//3
                    gc.create_line(gx,T+16,gx,B-4, fill=dim, width=1, dash=(2,4))

        elif kind in ('gui_frame','gui_bin','gui_alignment','gui_aspectframe',
                      'gui_handlebox','gui_eventbox'):
            gc.create_rectangle(L,T,R,B, fill='#060b10', outline=dim, width=1)
            gc.create_rectangle(L,T,R,B, fill='', outline=bor, width=lw, dash=(4,3))
            gc.create_text(L+10,T+1, text=w.get('label','frame')[:12],
                           fill=dim, font=('Monospace',7), bg='#060b10')

        elif kind == 'gui_notebook':
            gc.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw)
            for i,tab_lbl in enumerate(['Tab 1','Tab 2']):
                tx0=L+i*48+2; tx1=tx0+46; ty0=T; ty1=T+14
                gc.create_rectangle(tx0,ty0,tx1,ty1,
                                     fill='#1a3a5a' if i==0 else '#0a1a2a', outline=dim, width=1)
                gc.create_text((tx0+tx1)//2,(ty0+ty1)//2, text=tab_lbl, fill=txt, font=('Monospace',7))
            gc.create_rectangle(L,T+13,R,B, fill='#07101e', outline=dim, width=1)

        elif kind == 'gui_paned':
            gc.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw)
            mid = y
            gc.create_rectangle(L+3,T+3,R-3,mid-2, fill='#07101e', outline=dim, width=1, dash=(3,3))
            gc.create_rectangle(L+3,mid+2,R-3,B-3, fill='#07101e', outline=dim, width=1, dash=(3,3))
            gc.create_line(L+3,mid,R-3,mid, fill=dim, width=2)

        elif kind == 'gui_scrolled':
            gc.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw)
            gc.create_rectangle(R-10,T+2,R-2,B-2, fill='#0a1220', outline=dim, width=1)
            gc.create_rectangle(R-10,T+2,R-2,T+18, fill='#1a3a5a', outline='')
            gc.create_rectangle(L+2,T+2,R-12,B-2, fill='#07101e', outline=dim, width=1, dash=(3,3))

        elif kind == 'gui_expander':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_text(L+9,T+10, text='▶', fill=C['pal_border'], font=('Monospace',9), anchor='w')
            gc.create_text(L+22,T+10, text=w.get('label','Expander')[:14],
                           fill=txt, font=('Monospace',8), anchor='w')
            gc.create_rectangle(L+2,T+18,R-2,B-2, fill='#07101e', outline=dim, width=1, dash=(3,3))

        elif kind in ('gui_revealer','gui_overlay','gui_stack'):
            gc.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw, dash=(4,2))
            for i in range(3,0,-1):
                off=i*3
                gc.create_rectangle(L+off,T+off,R-off+6,B-off+6, fill='#0a1020', outline=dim, width=1)
            gc.create_text(x+3,y+3, text=kind.replace('gui_',''), fill=dim, font=('Monospace',7,'italic'))

        elif kind in ('gui_flowbox','gui_listbox'):
            gc.create_rectangle(L,T,R,B, fill='#06090f', outline=bor, width=lw)
            bx2,by2 = L+4,T+8
            for i in range(6):
                bw2=22+(i%2)*8; bh2=14
                if bx2+bw2>R-4: bx2=L+4; by2+=bh2+2
                gc.create_rectangle(bx2,by2,bx2+bw2,by2+bh2, fill='#0a1a30', outline=dim, width=1)
                bx2+=bw2+2

        elif kind == 'gui_headerbar':
            gc.create_rectangle(L,T,R,B, fill='#0a1830', outline=bor, width=lw)
            for i in range(2):
                bx=L+11+i*20
                gc.create_oval(bx-7,y-7,bx+7,y+7, fill='#1a3a5a', outline=dim)
                gc.create_text(bx,y, text=['◀','▶'][i], fill=dim, font=('Monospace',8))
            gc.create_text(x,y, text=w.get('label','Header')[:14], fill=txt, font=('Monospace',8,'bold'))
            gc.create_rectangle(R-24,y-8,R-4,y+8, fill='#0f3060', outline=dim)
            gc.create_text(R-14,y, text='☰', fill=txt, font=('Monospace',9))

        elif kind == 'gui_menubar':
            gc.create_rectangle(L,T,R,B, fill='#140808', outline=bor, width=lw)
            for i,item in enumerate(['File','Edit','View','Help']):
                gc.create_text(L+10+i*34,y, text=item, fill=txt, font=('Monospace',7), anchor='w')

        elif kind in ('gui_menu','gui_popover'):
            gc.create_rectangle(L,T,R,B, fill='#100808', outline=dim, width=lw)
            gc.create_rectangle(L+2,T+2,R-2,B-2, fill='#0d0606', outline='')
            for i,(itm,clr) in enumerate([('Item 1',txt),('Item 2',txt),('---',dim)]):
                iy = T+10+i*11
                if itm=='---': gc.create_line(L+4,iy,R-4,iy, fill=dim, width=1)
                else: gc.create_text(L+8,iy, text=itm, fill=clr, font=('Monospace',7), anchor='w')

        elif kind == 'gui_menuitem':
            gc.create_rectangle(L,T,R,B, fill='#100808', outline=bor, width=lw)
            gc.create_text(L+10,y, text='▶ '+w.get('label','Item')[:14],
                           fill=txt, font=('Monospace',8), anchor='w')

        elif kind in ('gui_toolbar','gui_actionbar'):
            gc.create_rectangle(L,T,R,B, fill='#0a100a', outline=bor, width=lw)
            for i in range(4):
                bx=L+12+i*28
                gc.create_rectangle(bx-9,y-9,bx+9,y+9, fill='#1a2a1a', outline=dim, width=1)
                gc.create_text(bx,y, text=['📁','💾','✂','📋'][i], font=('Monospace',9))

        elif kind == 'gui_treeview':
            gc.create_rectangle(L,T,R,B, fill='#060c12', outline=bor, width=lw)
            gc.create_rectangle(L,T,R,T+13, fill='#0a1a30', outline=dim, width=1)
            gc.create_text(L+22,T+6, text='Name', fill=txt, font=('Monospace',7), anchor='w')
            gc.create_text(R-24,T+6, text='Val', fill=txt, font=('Monospace',7), anchor='w')
            for i in range(2):
                ry=T+13+i*12
                gc.create_rectangle(L,ry,R,ry+12,
                                     fill='#070d1a' if i%2 else '#080f20', outline='')
                gc.create_text(L+8,ry+6, text=f'▶ row {i+1}',
                               fill=dim, font=('Monospace',7), anchor='w')

        elif kind == 'gui_iconview':
            gc.create_rectangle(L,T,R,B, fill='#060c12', outline=bor, width=lw)
            for ix in range(3):
                for iy in range(2):
                    bx=L+10+ix*40; by=T+6+iy*22
                    gc.create_rectangle(bx,by,bx+28,by+14, fill='#0a1a30', outline=dim, width=1)

        elif kind == 'gui_combobox':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_rectangle(L+4,T+10,R-18,B-10, fill='#050a12', outline=dim, width=1)
            gc.create_rectangle(R-18,T+10,R-4,B-10, fill='#1a3a5a', outline=dim, width=1)
            gc.create_text(R-11,y, text='▼', fill=txt, font=('Monospace',8))
            gc.create_line(L+10,y,L+36,y, fill='#2a3050', width=1)

        elif kind == 'gui_spinbutton':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_rectangle(L+4,T+10,R-17,B-10, fill='#050a12', outline=dim, width=1)
            midh=(T+B)//2
            gc.create_rectangle(R-17,T+10,R-3,midh, fill='#0f2a0f', outline=dim, width=1)
            gc.create_rectangle(R-17,midh,R-3,B-10, fill='#0f0a0f', outline=dim, width=1)
            gc.create_text(R-10,T+16, text='▲', fill=txt, font=('Monospace',7))
            gc.create_text(R-10,B-16, text='▼', fill=txt, font=('Monospace',7))

        elif kind == 'gui_calendar':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_rectangle(L,T,R,T+13, fill='#0f2060', outline=dim, width=1)
            gc.create_text(x,T+6, text='Jun 2026', fill=txt, font=('Monospace',7))
            for ci in range(7):
                for ri in range(3):
                    day=ci+ri*7+1
                    if day<=30:
                        gc.create_text(L+5+ci*18,T+18+ri*10, text=str(day),
                                       fill=dim, font=('Monospace',6))

        elif kind == 'gui_separator':
            gc.create_rectangle(L,T,R,B, fill=col, outline='', width=0)
            gc.create_line(L+4,y,R-4,y, fill=dim, width=2)
            gc.create_oval(x-4,y-4,x+4,y+4, fill=dim, outline='')

        elif kind in ('gui_statusbar','gui_infobar'):
            gc.create_rectangle(L,T,R,B, fill='#080d0a', outline=bor, width=lw)
            gc.create_text(L+8,y, text='● Ready', fill='#44cc44', font=('Monospace',8), anchor='w')
            if kind=='gui_infobar':
                gc.create_rectangle(R-28,T+5,R-4,B-5, fill='#0f3060', outline=dim)
                gc.create_text(R-16,y, text='✕', fill=txt, font=('Monospace',8))

        elif kind == 'gui_filechooser':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_rectangle(L+2,T+4,R-2,T+14, fill='#050a12', outline=dim, width=1)
            gc.create_text(L+6,T+9, text='📁 /home/', fill=dim, font=('Monospace',7), anchor='w')
            gc.create_text(L+8,T+22, text='📄 file.txt', fill=txt, font=('Monospace',7), anchor='w')

        elif kind == 'gui_colorchooser':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            for ci,fc2 in enumerate(['#cc2222','#22cc22','#2222cc',
                                      '#cccc22','#cc22cc','#22cccc']):
                gci=L+6+(ci%3)*20; gri=T+6+(ci//3)*14
                gc.create_oval(gci,gri,gci+16,gri+10, fill=fc2, outline='')

        elif kind == 'gui_fontchooser':
            gc.create_rectangle(L,T,R,B, fill=col, outline=bor, width=lw)
            gc.create_text(x,T+16, text='Aa Bb Cc', fill=txt, font=('Monospace',10))
            gc.create_text(x,B-12, text='Serif  Sans  Mono', fill=dim, font=('Monospace',6))

        # CC-09: geometry renderer replaces the dead if/else block above
        # ── Selection + edge-src overlay (always on top) ──────────────────────
        if gst['mode'] == 'edge_dst' and gst['edge_src'] == w['id']:
            gc.create_rectangle(L-3,T-3,R+3,B+3,
                                 outline=C['waypoint'], width=2, dash=(4,3))
        if sel:
            gc.create_rectangle(L,T,R,B, outline=C['selected'], width=3)
            gc.create_text(x, B+11, text=f"#{w['id']} ({x},{y})",
                           fill=C['selected'], font=('Monospace',7))

    def gc_draw_edge(e):
        src = gst['widgets'].get(e['src']); dst = gst['widgets'].get(e['dst'])
        if not src or not dst: return
        x1, y1 = src['x'], src['y'] + GH // 2
        x2, y2 = dst['x'], dst['y'] - GH // 2
        # If same row, draw a horizontal arc
        if abs(y1 - dst['y']) < GH:
            mx = (x1 + x2) // 2; my = y1 + 30
            gc.create_line(x1, y1, mx, my, x2, y2,
                           fill=C['edge'], width=2,
                           arrow='last', arrowshape=(12, 16, 5), smooth=True)
        else:
            gc.create_line(x1, y1, x2, y2,
                           fill=C['edge'], width=2,
                           arrow='last', arrowshape=(12, 16, 5))

    def gc_redraw():
        gc.delete('all'); gc_draw_grid()
        for e in gst['edges']:      gc_draw_edge(e)
        for w in gst['widgets'].values(): gc_draw_widget(w)

    def gc_widget_at(x, y):
        hw, hh = GW // 2, GH // 2
        for w in reversed(list(gst['widgets'].values())):
            if abs(w['x'] - x) <= hw and abs(w['y'] - y) <= hh:
                return w
        return None

    # ── Events ────────────────────────────────────────────────────────────────
    def gc_on_click(event):
        x, y = event.x, event.y
        mode = gst['mode']

        if mode == 'place':
            nid = gst['next_id']; gst['next_id'] += 1
            sx, sy = snap(x), snap(y)
            kind = gst['place_kind']
            gst['widgets'][nid] = {'id': nid, 'kind': kind,
                                    'x': sx, 'y': sy,
                                    'label': kind.replace('gui_', '')}
            gst['selected'] = nid
            gc_set_status(f"Placed {kind} — click to place another, Esc to stop")
            gc_redraw(); return

        if mode == 'delete':
            hit = gc_widget_at(x, y)
            if hit:
                gst['widgets'].pop(hit['id'])
                gst['edges'] = [e for e in gst['edges']
                                 if e['src'] != hit['id'] and e['dst'] != hit['id']]
                if gst['selected'] == hit['id']: gst['selected'] = None
                gc_set_status(f"Deleted {hit['kind']} #{hit['id']}")
            gc_redraw(); return

        if mode == 'edge_src':
            hit = gc_widget_at(x, y)
            if hit:
                gst['edge_src'] = hit['id']; gst['mode'] = 'edge_dst'
                gc_set_status(f"From  {hit['kind']} — now click the child widget")
            gc_redraw(); return

        if mode == 'edge_dst':
            hit = gc_widget_at(x, y)
            if hit and hit['id'] != gst['edge_src']:
                gst['edges'].append({'src': gst['edge_src'], 'dst': hit['id']})
                src_w = gst['widgets'].get(gst['edge_src'])
                gc_set_status(f"Connected  {src_w['kind'] if src_w else '?'}  →  {hit['kind']}")
                gst['edge_src'] = None; gc_set_mode('select')
            elif hit and hit['id'] == gst['edge_src']:
                gc_set_status("Can't connect to self")
            gc_redraw(); return

        # Select / drag
        hit = gc_widget_at(x, y)
        if hit:
            gst['selected'] = hit['id']; gst['dragging'] = True
            gst['drag_offset'] = (x - hit['x'], y - hit['y'])
            gc_set_status(f"Selected  {hit['kind']}  #{hit['id']}")
        else:
            gst['selected'] = None; gst['dragging'] = False
        gc_redraw()

    def gc_on_motion(event):
        if gst['dragging'] and gst['selected'] is not None:
            w = gst['widgets'].get(gst['selected'])
            if w:
                dx, dy = gst['drag_offset']
                w['x'] = snap(event.x - dx); w['y'] = snap(event.y - dy)
            gc_redraw()

    def gc_on_release(event):
        gst['dragging'] = False

    def gc_on_key(event):
        k = event.keysym.lower()
        if k == 'escape':        gc_set_mode('select')
        elif k == 'e':           gc_set_mode('edge_src')
        elif k == 'delete':
            sel = gst['selected']
            if sel is not None and sel in gst['widgets']:
                w = gst['widgets'].pop(sel)
                gst['edges'] = [e for e in gst['edges']
                                 if e['src'] != sel and e['dst'] != sel]
                gst['selected'] = None
                gc_set_status(f"Deleted {w['kind']} #{w['id']}")
                gc_redraw()

    gc.bind('<Button-1>',      gc_on_click)
    gc.bind('<B1-Motion>',     gc_on_motion)
    gc.bind('<ButtonRelease-1>', gc_on_release)
    gc.bind('<Enter>',         lambda e: gc.focus_set())
    gc.bind('<Key>',           gc_on_key)

    def _on_tab_change(event):
        idx = notebook.index('current')
        if idx == 1: gc_redraw()
        else: redraw()
    notebook.bind('<<NotebookTabChanged>>', _on_tab_change)

    root.after(200, gc_redraw)

    # ═══════════════════════════════════════════════════════════════════════════
    # End GHOST Canvas
    # ═══════════════════════════════════════════════════════════════════════════

    tk_canvas.bind('<Button-1>',on_click)
    tk_canvas.bind('<B1-Motion>',on_motion)
    tk_canvas.bind('<Motion>',on_motion)
    tk_canvas.bind('<ButtonRelease-1>',on_release)
    tk_canvas.bind('<Double-Button-1>',on_double_click)
    tk_canvas.bind('<Leave>', lambda e: _hide_tooltip())
    root.bind('<Key>',on_key)

    def on_close():
        if canvas_model.symbols:
            ans = messagebox.askyesnocancel('Quit FlowCode',
                    'Save canvas before closing?')
            if ans is None: return
            if ans: do_save()
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
