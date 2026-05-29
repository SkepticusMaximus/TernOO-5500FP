#!/usr/bin/env python3
"""
FlowCode  v0.4.0
================
Visual programming IDE for TernOO-5500FP.

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

# ── Constants ─────────────────────────────────────────────────────────────────

SYMBOL_PROCESS  = 'process'
SYMBOL_DECISION = 'decision'
SYMBOL_IO       = 'io'
SYMBOL_SUBCLASS = {SYMBOL_PROCESS:(0,0), SYMBOL_DECISION:(0,+1), SYMBOL_IO:(+1,0)}
SYMBOL_W, SYMBOL_H, GRID = 120, 60, 40

def snap(v): return round(v/GRID)*GRID

# ── Colours ───────────────────────────────────────────────────────────────────
C = {
    'bg':'#1a1a2e',       'canvas':'#16213e',    'grid':'#1e2a4a',
    'palette':'#0d1117',  'pal_btn':'#1e2a4a',   'pal_active':'#0f3460',
    'pal_border':'#4a9eff','process':'#0f3460',   'decision':'#533483',
    'io':'#1a6b5e',       'border':'#4a9eff',    'selected':'#ff6b35',
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
                'data_seg':self.data_seg,'offset':self.offset}

    @classmethod
    def from_dict(cls,d):
        s = cls(d['kind'],d['x'],d['y'],d.get('label',''),
                d.get('code_seg',0),d.get('data_seg',0))
        s.id=d['id']; s.offset=d.get('offset',0)
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
        """Return full point list for an edge including waypoints."""
        src = self.symbols.get(e.src_id)
        dst = self.symbols.get(e.dst_id)
        if not src or not dst: return []
        pts = [(src.x, src.y)] + list(e.waypoints) + [(dst.x, dst.y)]
        return pts

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
    print("="*60+"\nFlowCode v0.4.0 — Headless Demo\n"+"="*60)
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
        from tkinter import filedialog, simpledialog
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
    root.title("FlowCode v0.4.0 — TernOO-5500FP Visual IDE")
    root.configure(bg=C['bg'])
    root.resizable(True,True)

    outer = tk.Frame(root,bg=C['bg']); outer.pack(fill='both',expand=True)
    palette_frame = tk.Frame(outer,bg=C['palette'],width=PALETTE_W)
    palette_frame.pack(side='left',fill='y'); palette_frame.pack_propagate(False)
    right = tk.Frame(outer,bg=C['bg']); right.pack(side='left',fill='both',expand=True)
    tk_canvas = tk.Canvas(right,bg=C['canvas'],highlightthickness=0)
    tk_canvas.pack(side='top',fill='both',expand=True)
    inspect = tk.Label(right,text="Select a symbol or edge to inspect",
                       bg=C['inspect'],fg=C['inspect_fg'],
                       font=('Monospace',9),anchor='nw',justify='left',
                       padx=8,pady=4,height=6)
    inspect.pack(side='top',fill='x')
    status = tk.Label(right,text="Ready",anchor='w',
                      bg=C['status'],fg=C['pal_border'],
                      font=('Monospace',9),padx=8)
    status.pack(side='bottom',fill='x',ipady=3)

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
    _pal_btn('place_process','Process','rectangle','process')
    _pal_btn('place_decision','Decision','diamond','decision')
    _pal_btn('place_io','I/O','rounded','io')
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
        if p: canvas_model.save(p); set_status(f"Saved: {os.path.basename(p)}")
    def do_open():
        p=filedialog.askopenfilename(
            filetypes=[('FlowCode JSON','*.json'),('All','*.*')])
        if p:
            canvas_model.load(p)
            state['selected_sym']=None; state['selected_edge']=None
            set_status(f"Loaded: {os.path.basename(p)}"); redraw()
    def do_clear():
        canvas_model.symbols.clear(); canvas_model.edges.clear()
        state['selected_sym']=None; state['selected_edge']=None
        FCSymbol._next_id=1
        set_inspect("Canvas cleared"); set_status("Cleared"); redraw()

    _action_btn("⬇ Word Dump", do_dump,   icon_key='dump')
    _action_btn("▶ Load→EMU",  do_load,   fg='#7aff7a', icon_key='load')
    _action_btn("▶▶ Run",      do_run,    fg='#ffdd57')
    _action_btn("💾 Save",     do_save,   icon_key='save')
    _action_btn("📂 Open",     do_open,   icon_key='open')
    _action_btn("🗑 Clear",    do_clear,  fg='#ff8888', icon_key='clear')

    tk.Label(palette_frame,text=f"v0.4.0\n{os.path.basename(_emu_path)}",
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
            SYMBOL_IO:C['io']}.get(s.kind,C['process'])
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

        tk_canvas.create_text(x,y,text=s.label,fill=C['text'],
                              font=('Monospace',10,'bold'))
        tk_canvas.create_text(x,y+hh+10,text=describe_word(s.to_udp_word())[:28],
                              fill=C['dim'],font=('Monospace',7))
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

        # Edge label at midpoint of first segment
        if len(pts)>=2:
            mx=(pts[0][0]+pts[1][0])//2; my=(pts[0][1]+pts[1][1])//2-12
            priv={-1:'K',0:'U',1:'S'}.get(e.privilege,'?')
            call={-1:'stk',0:'reg',1:'msg'}.get(e.call_style,'?')
            ret={-1:'X',0:'M',1:'D'}.get(e.return_type,'?')
            tk_canvas.create_text(mx,my,text=f"EXEC {priv}/{call}→{ret}",
                                  fill=col,font=('Monospace',7))
            if e.condition:
                tk_canvas.create_text(mx,my-12,text=f"[{e.condition}]",
                                      fill=C['waypoint'],font=('Monospace',8,'bold'))

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
                state['mode'] in ('place_process','place_decision','place_io')):
            _draw_placement_ghost(*state['ghost'])

    def _draw_placement_ghost(x,y):
        sx,sy=snap(x),snap(y); hw,hh=SYMBOL_W//2,SYMBOL_H//2
        mode=state['mode']
        fill='#161b30'; bor='#3a4060'
        if mode=='place_process':
            tk_canvas.create_rectangle(sx-hw,sy-hh,sx+hw,sy+hh,
                                       fill=fill,outline=bor,width=1,dash=(4,4))
        elif mode=='place_decision':
            tk_canvas.create_polygon([sx,sy-hh,sx+hw,sy,sx,sy+hh,sx-hw,sy],
                                     fill=fill,outline=bor,width=1)
        elif mode=='place_io':
            tk_canvas.create_oval(sx-hw,sy-hh,sx+hw,sy+hh,
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

    # ── Event handlers ────────────────────────────────────────────────────────

    def on_motion(event):
        state['ghost']=(event.x,event.y)
        if state['dragging'] and state['selected_sym']:
            s=canvas_model.symbols.get(state['selected_sym'])
            if s:
                dx,dy=state['drag_offset']
                s.x=snap(event.x-dx); s.y=snap(event.y-dy)
        redraw()

    def on_click(event):
        x,y=event.x,event.y
        mode=state['mode']

        # Placement modes
        if mode in ('place_process','place_decision','place_io'):
            kind={'place_process':SYMBOL_PROCESS,
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

        # TernOO word preview label
        preview = tk.Label(frm, text="", bg=C['inspect'], fg=C['inspect_fg'],
                           font=('Monospace', 8), anchor='w', justify='left',
                           padx=6, pady=4, width=38)
        preview.grid(row=5, column=0, columnspan=2, padx=0, pady=4, sticky='ew')

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
        k=event.keysym.lower()
        if k=='r': set_mode('place_process')
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

    tk_canvas.bind('<Button-1>',on_click)
    tk_canvas.bind('<B1-Motion>',on_motion)
    tk_canvas.bind('<Motion>',on_motion)
    tk_canvas.bind('<ButtonRelease-1>',on_release)
    tk_canvas.bind('<Double-Button-1>',on_double_click)
    root.bind('<Key>',on_key)

    set_mode('select')
    root.after(100,redraw)
    root.mainloop()


if __name__=='__main__':
    if '--headless' in sys.argv or '--test' in sys.argv:
        run_headless_demo()
    else:
        run_gui()
