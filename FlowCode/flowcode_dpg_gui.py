#!/usr/bin/env python3
"""flowcode_dpg_gui — the GUI tab ORGAN of FlowCode's Dear PyGui face.

The real builder, ported against the Tk face's own data model:
palette (six Tk sections, full 56-kind vocabulary) -> click-place ->
select / drag-move / corner-resize -> properties panel (Identity,
Geometry, Appearance, Container, Cell binding) -> undo/redo ->
Save / Open `.gui` in the Tk face's EXACT JSON schema. Fields this
editor does not yet edit (signals, custom properties, edges) are
PRESERVED through load->save round-trips — the two faces exchange
files without data loss.

This leg (19-08): the LAYOUT ENGINE (hbox/vbox/grid/stacked place
children live — the Tk guic_apply_layout algorithm in this organ's
absolute coords), the Phase 7c-2 Signals → handlers panel (read-only,
naming IS the wiring — flowcode_signals reused, wired-state checked
against the live Flow organ), Import (merge another .gui/.fc into the
canvas), and Tk-schema child coordinates: parented widgets save/load
as CENTRE-OFFSETS from the parent centre, the Tk face's convention —
nested designs now cross the faces without scattering.

Still not ported (stated, not hidden): RNODE widget geometry
rendering — the parametric faces below carry the WYSIWYG standard
meanwhile.
"""
import importlib.util as _ilu
import json
import math
import os
import sys

import dearpygui.dearpygui as dpg

# ── the Tk face's canon constants, carried over verbatim ────────────────────
GW, GH = 160, 72
MIN_SIZE = 20
CONTAINER_KINDS = frozenset({
    'gui_window', 'gui_dialog', 'gui_box', 'gui_grid', 'gui_frame',
    'gui_notebook', 'gui_paned', 'gui_scrolled', 'gui_stack',
    'gui_expander', 'gui_revealer', 'gui_overlay', 'gui_flowbox',
    'gui_listbox', 'gui_headerbar', 'gui_actionbar', 'gui_menubar',
    'gui_toolbar', 'gui_statusbar',
})
DEFAULT_SIZE = {
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
LAYOUT_DEFAULTS = {
    'gui_window': 'absolute', 'gui_dialog': 'absolute',
    'gui_box': 'vbox',        'gui_grid': 'grid',
    'gui_frame': 'absolute',  'gui_notebook': 'stacked',
    'gui_stack': 'stacked',   'gui_paned': 'hbox',
    'gui_expander': 'absolute', 'gui_revealer': 'absolute',
    'gui_overlay': 'absolute',  'gui_scrolled': 'absolute',
    'gui_flowbox': 'vbox',      'gui_listbox': 'vbox',
    'gui_headerbar': 'hbox',    'gui_actionbar': 'hbox',
    'gui_menubar': 'hbox',      'gui_toolbar': 'hbox',
    'gui_statusbar': 'hbox',
}
LAYOUT_MODES = ['absolute', 'vbox', 'hbox', 'grid', 'stacked']

# The palette, grouped in the Tk sidebar's six sections. (The Tk rank
# table is implicit in its builder; this grouping mirrors the visible
# sidebar — flag me if a kind sits in the wrong drawer.)
PALETTE = [
    ("CONTAINERS", ['gui_headerbar', 'gui_actionbar', 'gui_window',
                    'gui_dialog', 'gui_box', 'gui_grid', 'gui_frame',
                    'gui_notebook', 'gui_paned', 'gui_scrolled',
                    'gui_stack', 'gui_expander', 'gui_revealer',
                    'gui_overlay', 'gui_flowbox', 'gui_listbox',
                    'gui_toolbar', 'gui_statusbar', 'gui_bin',
                    'gui_eventbox', 'gui_alignment', 'gui_aspectframe',
                    'gui_handlebox']),
    ("CONTROLS",   ['gui_button', 'gui_toggle', 'gui_check', 'gui_radio',
                    'gui_switch', 'gui_menubutton', 'gui_link',
                    'gui_scale', 'gui_spinbutton']),
    ("INPUTS",     ['gui_entry', 'gui_searchentry', 'gui_textview',
                    'gui_combobox', 'gui_calendar', 'gui_colorchooser',
                    'gui_fontchooser', 'gui_filechooser']),
    ("DISPLAY",    ['gui_label', 'gui_image', 'gui_progress', 'gui_level',
                    'gui_separator', 'gui_treeview', 'gui_iconview',
                    'gui_infobar', 'gui_canvas']),
    ("DIALOGS",    ['gui_messagedialog', 'gui_aboutdialog',
                    'gui_assistant', 'gui_popover']),
    ("MENUS",      ['gui_menu', 'gui_menubar', 'gui_menuitem']),
]

CANVAS_W, CANVAS_H = 2400, 1600
GRID_STEP = 20

# ── state ───────────────────────────────────────────────────────────────────
GS = {
    "widgets": {},    # id -> widget dict (Tk-model fields)
    "raw": {},        # id -> the loaded raw sym dict (preserved extras)
    "edges": [],      # preserved verbatim
    "next": 0,
    "sel": None,
    "file": None,
    "pending": None,  # kind waiting to be placed
    "drag": None,     # {"mode": move|nw|ne|sw|se, "orig": (x,y,w,h)}
    "grip": None, "grip2": None, "zoom": 1.0, "dirty": False,
    "undo": [], "redo": [],
    "multi": set(), "lasso": None,      # the VB kit (20-08)
    "groups": {},                       # name -> [ids] — FIRST-CLASS,
    #                                     NAMED, SAVED (captain's ruling)
}


def is_dirty():
    has = bool(GS["widgets"])
    return has and (bool(GS["dirty"]) or GS["file"] is None)


def autosave(path):
    try:
        json.dump(_payload(path), open(path, "w", encoding="utf-8"),
                  indent=1)
        return True
    except Exception:                           # noqa: BLE001
        return False


def zoom_step(direction):
    """CANVAS zoom (the drawing), not UI-text zoom."""
    z = GS["zoom"] * (1.2 if direction > 0 else 1 / 1.2)
    GS["zoom"] = max(0.3, min(3.0, round(z, 3)))
    if dpg.does_item_exist("guic_zoomlbl"):
        dpg.set_value("guic_zoomlbl", f"Zoom: {int(GS['zoom'] * 100)}%")
    redraw()


def _mpos():
    mx, my = dpg.get_drawing_mouse_pos()
    z = GS["zoom"]
    return mx / z, my / z
STYLE = {}


def _status(msg, ok=True):
    dpg.set_value("guic_status", msg)
    dpg.configure_item("guic_status",
                       color=STYLE.get("GRN" if ok else "AMB"))


# ── properties helpers (the Tk 'properties' list of [name, value]) ──────────
def _prop_get(w, name, default=""):
    """Tk properties are dicts {'name': n, 'value': v}; tolerate legacy
    [name, value] pairs from this organ's first day."""
    for p in w.get("properties", []):
        if isinstance(p, dict) and p.get("name") == name:
            return p.get("value")
        if isinstance(p, (list, tuple)) and len(p) >= 2 and p[0] == name:
            return p[1]
    return default


def _prop_set(w, name, value):
    props = w.setdefault("properties", [])
    for i, p in enumerate(props):
        if (isinstance(p, dict) and p.get("name") == name) or \
                (isinstance(p, list) and len(p) >= 2 and p[0] == name):
            props[i] = {"name": name, "value": value}
            return
    props.append({"name": name, "value": value})


# ── undo / redo ─────────────────────────────────────────────────────────────
def _snapshot():
    GS["dirty"] = True
    GS["undo"].append(json.dumps({"w": GS["widgets"], "e": GS["edges"],
                                  "n": GS["next"], "g": GS["groups"]}))
    GS["undo"] = GS["undo"][-50:]
    GS["redo"].clear()


def _restore(blob):
    d = json.loads(blob)
    GS["widgets"] = {int(k): v for k, v in d["w"].items()}
    GS["edges"] = d["e"]
    GS["next"] = d["n"]
    GS["groups"] = {k: [int(i) for i in v]
                    for k, v in d.get("g", {}).items()}
    GS["multi"] = {i for i in GS["multi"] if i in GS["widgets"]}
    GS["sel"] = GS["sel"] if GS["sel"] in GS["widgets"] else None
    redraw()
    _sync_props()


def undo(*_):
    if not GS["undo"]:
        _status("nothing to undo", ok=False)
        return
    GS["redo"].append(json.dumps({"w": GS["widgets"], "e": GS["edges"],
                                  "n": GS["next"]}))
    _restore(GS["undo"].pop())
    _status("undone")


def redo(*_):
    if not GS["redo"]:
        _status("nothing to redo", ok=False)
        return
    GS["undo"].append(json.dumps({"w": GS["widgets"], "e": GS["edges"],
                                  "n": GS["next"]}))
    _restore(GS["redo"].pop())
    _status("redone")


# ── model ops ───────────────────────────────────────────────────────────────
def add_widget(kind, x, y):
    _snapshot()
    wid = GS["next"]
    GS["next"] += 1
    dw, dh = DEFAULT_SIZE.get(kind, (GW, GH))
    GS["widgets"][wid] = {
        "id": wid, "kind": kind, "label": kind[4:],
        "name": f"{kind[4:]}_{wid}",
        "x": int(x), "y": int(y), "w": dw, "h": dh,
        "parent_id": None,
        "layout_mode": "absolute",  # VB doctrine (20-08): layout engines
        "properties": [], "signal_ids": {},     # are OPT-IN via the combo
    }
    GS["sel"] = wid
    _assign_parent(wid)
    layout_all()
    redraw()
    _sync_props()
    _status(f"placed {kind[4:]} #{wid}")
    return wid


def _multi_ids():
    return [i for i in (GS["multi"] or ({GS["sel"]}
                                        if GS["sel"] is not None
                                        else set()))
            if i in GS["widgets"]]


def align_selected(how):
    """VB kit: align lefts/tops/h-centres/v-centres of the selection."""
    ids = _multi_ids()
    if len(ids) < 2:
        _status("select 2+ widgets to align (rubber-band drag)",
                ok=False)
        return
    _snapshot()
    ws = [GS["widgets"][i] for i in ids]
    if how == "left":
        v = min(w["x"] for w in ws)
        for w in ws:
            w["x"] = v
    elif how == "top":
        v = min(w["y"] for w in ws)
        for w in ws:
            w["y"] = v
    elif how == "hcenter":
        v = sum(w["x"] + w["w"] / 2 for w in ws) / len(ws)
        for w in ws:
            w["x"] = int(v - w["w"] / 2)
    elif how == "vcenter":
        v = sum(w["y"] + w["h"] / 2 for w in ws) / len(ws)
        for w in ws:
            w["y"] = int(v - w["h"] / 2)
    layout_all()
    redraw()
    _status(f"aligned {len(ids)} · {how}")


def distribute_selected(axis):
    """VB kit: equal gaps along an axis."""
    ids = _multi_ids()
    if len(ids) < 3:
        _status("select 3+ widgets to distribute", ok=False)
        return
    _snapshot()
    key, size = ("x", "w") if axis == "h" else ("y", "h")
    ws = sorted((GS["widgets"][i] for i in ids), key=lambda w: w[key])
    lo = ws[0][key]
    hi = ws[-1][key] + ws[-1][size]
    total = sum(w[size] for w in ws)
    gap = max(0, (hi - lo - total)) / (len(ws) - 1)
    pos = float(lo)
    for w in ws:
        w[key] = int(pos)
        pos += w[size] + gap
    layout_all()
    redraw()
    _status(f"distributed {len(ids)} · {axis}")


def group_selection(name):
    """FIRST-CLASS NAMED GROUPS (captain's ruling): the selection
    becomes a saved, named thing — clicking any member selects it
    whole; it moves, aligns and deletes as one; it rides the .gui."""
    name = str(name or "").strip()
    ids = _multi_ids()
    if not name:
        _status("give the group a name first", ok=False)
        return
    if len(ids) < 2:
        _status("rubber-band 2+ widgets, then group them", ok=False)
        return
    if name in GS["groups"]:
        _status(f"group '{name}' already exists", ok=False)
        return
    _snapshot()
    GS["groups"][name] = sorted(ids)
    if dpg.does_item_exist("guic_grpname"):
        dpg.set_value("guic_grpname", "")
    _grplist_refresh()
    redraw()
    _status(f"⌘ group '{name}' saved ({len(ids)} widgets)")


def ungroup(name):
    if name in GS["groups"]:
        _snapshot()
        GS["groups"].pop(name)
        _grplist_refresh()
        redraw()
        _status(f"ungrouped '{name}' (widgets stay)")


def select_group(name):
    ids = {i for i in GS["groups"].get(name, []) if i in GS["widgets"]}
    if not ids:
        return
    GS["multi"] = ids
    GS["sel"] = sorted(ids)[0]
    redraw()
    _sync_props()
    _status(f"group '{name}' selected ({len(ids)})")


def _grplist_refresh():
    L = "guic_grplist"
    if not dpg.does_item_exist(L):
        return
    dpg.delete_item(L, children_only=True)
    if not GS["groups"]:
        dpg.add_text("(rubber-band widgets,\n name them, press ⌘)",
                     parent=L, color=STYLE.get("DIM"))
        return
    for name in sorted(GS["groups"]):
        with dpg.group(horizontal=True, parent=L):
            dpg.add_button(label=f" ⌘ {name} "
                           f"({len(GS['groups'][name])}) ", width=-40,
                           user_data=name,
                           callback=lambda s, a, u: select_group(u))
            dpg.add_button(label="×", small=True, user_data=name,
                           callback=lambda s, a, u: ungroup(u))


def delete_selected(*_):
    ids = _multi_ids()
    if not ids:
        return
    _snapshot()
    for wid in ids:
        GS["widgets"].pop(wid, None)
        GS["raw"].pop(wid, None)
    for w in GS["widgets"].values():
        if w.get("parent_id") not in GS["widgets"] \
                and w.get("parent_id") is not None:
            w["parent_id"] = None
    for g in GS["groups"].values():
        g[:] = [i for i in g if i in GS["widgets"]]
    GS["groups"] = {k: v for k, v in GS["groups"].items() if v}
    GS["sel"] = None
    GS["multi"] = set()
    redraw()
    _sync_props()
    _status(f"deleted {len(ids)} widget(s)")


def clear_all(*_):
    if not GS["widgets"]:
        return
    _snapshot()
    GS["widgets"].clear()
    GS["raw"].clear()
    GS["edges"].clear()
    GS["groups"].clear()
    GS["multi"] = set()
    GS["sel"] = None
    _grplist_refresh()
    redraw()
    _sync_props()
    _status("canvas cleared")


TOP_LEVEL_KINDS = {"gui_window", "gui_dialog"}      # never adopted (VB: forms)


def _assign_parent(wid):
    """Containment by geometry: centre inside a container -> child of it.
    Windows and dialogs are TOP-LEVEL — they adopt, never get adopted."""
    w = GS["widgets"][wid]
    if w["kind"] in TOP_LEVEL_KINDS:
        w["parent_id"] = None
        return
    cx, cy = w["x"] + w["w"] / 2, w["y"] + w["h"] / 2
    best = None
    for oid, o in GS["widgets"].items():
        if oid == wid or o["kind"] not in CONTAINER_KINDS:
            continue
        if o["x"] <= cx <= o["x"] + o["w"] and o["y"] <= cy <= o["y"] + o["h"]:
            if best is None or (o["w"] * o["h"] <
                                GS["widgets"][best]["w"] * GS["widgets"][best]["h"]):
                best = oid
    w["parent_id"] = best


# ── z-order — the STACKING SEQUENCE (captain's report, 20-08) ───────────────
# GS["zorder"] is the persistent front-to-back list of widget ids (last =
# front). Rendering walks ROOTS in sequence order, each followed by its
# children (containment implies stacking: a child can NEVER be buried
# under its own container, whatever a loaded file's order says).
def _zorder():
    seq = GS.setdefault("zorder", [])
    seq[:] = [i for i in seq if i in GS["widgets"]]
    seq.extend(i for i in GS["widgets"] if i not in seq)
    return seq


def render_order():
    seq = _zorder()
    kids = {}
    for i in seq:
        kids.setdefault(GS["widgets"][i].get("parent_id"), []).append(i)
    out = []

    def walk(i):
        out.append(i)
        for c in kids.get(i, []):
            walk(c)
    for i in kids.get(None, []):
        walk(i)
    for i in seq:                       # orphans of a vanished parent
        if i not in out:
            out.append(i)
    return out


def bring_to_front(*_):
    if GS["sel"] in GS["widgets"]:
        seq = _zorder()
        seq.remove(GS["sel"])
        seq.append(GS["sel"])
        GS["dirty"] = True
        redraw()


def send_to_back(*_):
    if GS["sel"] in GS["widgets"]:
        seq = _zorder()
        seq.remove(GS["sel"])
        seq.insert(0, GS["sel"])
        GS["dirty"] = True
        redraw()


# ── the layout engine — Tk guic_apply_layout, absolute-coord port ───────────
PAD = 4


def children_of(pid):
    """Direct children, id-ordered (the organ keeps no child_order yet)."""
    return [GS["widgets"][i] for i in sorted(GS["widgets"])
            if GS["widgets"][i].get("parent_id") == pid]


def apply_layout(cid):
    """Place cid's direct children per its layout_mode (absolute = no-op).
    Same arithmetic as the Tk face, expressed in absolute top-left."""
    ct = GS["widgets"].get(cid)
    if ct is None:
        return
    mode = ct.get("layout_mode",
                  LAYOUT_DEFAULTS.get(ct["kind"], "absolute"))
    kids = children_of(cid)
    N = len(kids)
    if mode == "absolute" or N == 0:
        return
    X, Y, W, H = ct["x"], ct["y"], ct["w"], ct["h"]
    if mode == "hbox":
        cw = max(MIN_SIZE, (W - 2 * PAD - PAD * (N - 1)) // N)
        chh = max(MIN_SIZE, H - 2 * PAD)
        for i, ch in enumerate(kids):
            ch["x"] = int(X + PAD + i * (cw + PAD))
            ch["y"] = int(Y + PAD)
            ch["w"], ch["h"] = cw, chh
    elif mode == "vbox":
        cw = max(MIN_SIZE, W - 2 * PAD)
        chh = max(MIN_SIZE, (H - 2 * PAD - PAD * (N - 1)) // N)
        for i, ch in enumerate(kids):
            ch["x"] = int(X + PAD)
            ch["y"] = int(Y + PAD + i * (chh + PAD))
            ch["w"], ch["h"] = cw, chh
    elif mode == "grid":
        cols = max(1, math.ceil(math.sqrt(N)))
        rows = max(1, math.ceil(N / cols))
        cw = max(MIN_SIZE, (W - PAD * (cols + 1)) // cols)
        chh = max(MIN_SIZE, (H - PAD * (rows + 1)) // rows)
        for idx, ch in enumerate(kids):
            r, c = divmod(idx, cols)
            ch["x"] = int(X + PAD * (c + 1) + c * cw)
            ch["y"] = int(Y + PAD * (r + 1) + r * chh)
            ch["w"], ch["h"] = cw, chh
    elif mode == "stacked":
        for ch in kids:                 # all pages cover the content area
            ch["x"], ch["y"] = int(X + PAD), int(Y + PAD)
            ch["w"] = max(MIN_SIZE, W - 2 * PAD)
            ch["h"] = max(MIN_SIZE, H - 2 * PAD)


def _depth_of(wid, seen=()):
    p = GS["widgets"].get(wid, {}).get("parent_id")
    if p is None or p not in GS["widgets"] or wid in seen:
        return 0
    return 1 + _depth_of(p, seen + (wid,))


def layout_all():
    """Apply every container's layout, parents before their children."""
    for wid in sorted(GS["widgets"], key=_depth_of):
        if GS["widgets"][wid]["kind"] in CONTAINER_KINDS:
            apply_layout(wid)


# ── drawing ─────────────────────────────────────────────────────────────────
def redraw():
    D = "guic_draw"
    Z = GS["zoom"]
    if dpg.does_item_exist(D):
        dpg.configure_item(D, width=int(CANVAS_W * Z),
                           height=int(CANVAS_H * Z))
    dpg.delete_item(D, children_only=True)
    C = STYLE
    for gx in range(0, CANVAS_W + 1, GRID_STEP):
        dpg.draw_line((gx * Z, 0), (gx * Z, CANVAS_H * Z),
                      color=(40, 46, 62, 90), parent=D)
    for gy in range(0, CANVAS_H + 1, GRID_STEP):
        dpg.draw_line((0, gy * Z), (CANVAS_W * Z, gy * Z),
                      color=(40, 46, 62, 90), parent=D)
    for wid in render_order():
        w = GS["widgets"][wid]
        x, y = w["x"] * Z, w["y"] * Z
        ww, hh = w["w"] * Z, w["h"] * Z
        label = w.get("label") or w["kind"][4:]
        _render_widget(D, w["kind"], x, y, ww, hh, label=label, px=Z)
        if wid in GS["multi"] and wid != GS["sel"]:
            dpg.draw_rectangle((x - 2, y - 2), (x + ww + 2, y + hh + 2),
                               color=(255, 170, 90), thickness=1.5,
                               parent=D)
        if wid == GS["sel"]:
            dpg.draw_rectangle((x - 2, y - 2), (x + ww + 2, y + hh + 2),
                               color=(255, 120, 50), thickness=2, parent=D)
            for hx, hy in ((x, y), (x + ww, y), (x, y + hh),
                           (x + ww, y + hh), (x + ww / 2, y),
                           (x + ww / 2, y + hh), (x, y + hh / 2),
                           (x + ww, y + hh / 2)):
                dpg.draw_rectangle((hx - 3, hy - 3), (hx + 3, hy + 3),
                                   fill=(255, 120, 50), parent=D)
            cap = f"{w.get('name', '')}  #{wid} ({w['x']},{w['y']})"
            g = _group_of(wid)
            if g:
                cap += f"  ⌘{g}"
            dpg.draw_text((x, y + hh + 8 * Z), cap, size=13 * Z,
                          color=(255, 140, 70), parent=D)
    if GS.get("lasso") is not None:
        x0, y0, x1, y1 = [v * Z for v in GS["lasso"]]
        dpg.draw_rectangle((x0, y0), (x1, y1), color=(255, 170, 90),
                           thickness=1, parent=D)


# ── the widget-face renderer — ONE vocabulary for palette icons and the
#    canvas, WYSIWYG doctrine: a checkbox looks like a checkbox at 40px in
#    the toolbar and at full size on the canvas. Hand-drawn primitives are
#    a stand-in until the CC-09 RNODE widget-geometry organ renders canon
#    shapes; this renderer is built to be swapped out for it. ─────────────
def _render_widget(D, kind, x, y, w, h, label="", px=1.0):
    """px = pixel-unit scale (canvas zoom). CHROME is fixed-size in px
    units (titlebars, scrollbars, row pitch, checkbox glyphs) and only
    the CONTENT area scales with the widget — a taller treeview gets
    MORE rows, not stretched rows; a bigger window keeps its titlebar."""
    u = max(0.35, px)
    TB = min(20 * u, h * 0.34)          # titlebar height
    PITCH = max(9.0, 18 * u)            # list/text row pitch
    B = (96, 116, 160)
    T = (238, 240, 245)
    DIMc = (150, 158, 175)
    ACC = (74, 158, 255)
    FLD = (214, 219, 228)
    PANEL = (44, 52, 72)
    DARK = (30, 38, 56)
    k = kind[4:] if kind.startswith("gui_") else kind
    small = w < 64

    def R(x0, y0, x1, y1, fill=None, col=B, r=0, th=1):
        dpg.draw_rectangle((x + x0 * w, y + y0 * h), (x + x1 * w, y + y1 * h),
                           fill=fill, color=col, rounding=r, thickness=th,
                           parent=D)

    def L(x0, y0, x1, y1, col=B, th=1):
        dpg.draw_line((x + x0 * w, y + y0 * h), (x + x1 * w, y + y1 * h),
                      color=col, thickness=th, parent=D)

    def C(cx, cy, rr, fill=None, col=B):
        dpg.draw_circle((x + cx * w, y + cy * h), rr * min(w, h),
                        fill=fill, color=col, parent=D)

    def TXT(tx, ty, text, col=T, size=13):
        if not small:
            dpg.draw_text((x + tx * w, y + ty * h), text, color=col,
                          size=max(9, min(size, h * 0.3)), parent=D)

    R(0, 0, 1, 1, fill=PANEL, col=B, r=2)                # base body
    if k in ("window", "dialog", "messagedialog", "aboutdialog",
             "assistant", "popover"):
        dpg.draw_rectangle((x, y), (x + w, y + TB), fill=DARK, color=B,
                           parent=D)                     # FIXED titlebar
        dpg.draw_circle((x + w - 0.55 * TB, y + 0.5 * TB), 0.26 * TB,
                        fill=(220, 90, 80), color=(220, 90, 80), parent=D)
        if k == "dialog":
            bh = min(18 * u, h * 0.25)
            bw = min(44 * u, w * 0.3)
            dpg.draw_rectangle((x + w - 2 * bw - 12 * u, y + h - bh - 5 * u),
                               (x + w - bw - 8 * u, y + h - 5 * u),
                               fill=DARK, color=B, parent=D)
            dpg.draw_rectangle((x + w - bw - 5 * u, y + h - bh - 5 * u),
                               (x + w - 5 * u, y + h - 5 * u),
                               fill=(52, 90, 150), color=B, parent=D)
        elif k == "messagedialog":
            TXT(0.12, 0.4, "!", (255, 200, 90), 22)
            C(0.14, 0.55, 0.1, col=(255, 200, 90))
        elif k == "aboutdialog":
            C(0.5, 0.5, 0.14, col=ACC)
            TXT(0.465, 0.36, "i", ACC, 16)
        elif k == "assistant":
            dpg.draw_arrow((x + 0.85 * w, y + 0.55 * h),
                           (x + 0.35 * w, y + 0.55 * h), color=ACC,
                           thickness=2, size=6, parent=D)
        elif k == "popover":
            dpg.draw_triangle((x + 0.42 * w, y + h), (x + 0.58 * w, y + h),
                              (x + 0.5 * w, y + 1.25 * h), fill=PANEL,
                              color=B, parent=D)
    elif k in ("box", "bin", "eventbox", "alignment", "aspectframe",
               "handlebox", "revealer", "overlay", "scrolled", "stack",
               "expander", "flowbox"):
        if k == "box":
            L(0.05, 0.36, 0.95, 0.36)
            L(0.05, 0.66, 0.95, 0.66)
        elif k == "scrolled":
            sw = min(10 * u, w * 0.2)
            dpg.draw_rectangle((x + w - sw - 3 * u, y + 3 * u),
                               (x + w - 3 * u, y + h - 3 * u),
                               fill=DARK, parent=D)
            dpg.draw_rectangle((x + w - sw - 2 * u, y + 5 * u),
                               (x + w - 4 * u, y + 5 * u + (h - 10 * u) * 0.4),
                               fill=B, parent=D)
        elif k == "stack":
            R(0.18, 0.2, 0.82, 0.85, fill=DARK, col=B)
            R(0.1, 0.1, 0.74, 0.75, fill=PANEL, col=ACC)
        elif k == "expander":
            dpg.draw_triangle((x + 0.08 * w, y + 0.18 * h),
                              (x + 0.08 * w, y + 0.42 * h),
                              (x + 0.2 * w, y + 0.3 * h), fill=T, parent=D)
            L(0.28, 0.3, 0.9, 0.3, T)
        elif k == "revealer":
            R(0.05, 0.5, 0.95, 0.95, fill=DARK)
            dpg.draw_arrow((x + 0.5 * w, y + 0.45 * h),
                           (x + 0.5 * w, y + 0.15 * h), color=ACC,
                           thickness=2, size=5, parent=D)
        elif k == "overlay":
            R(0.3, 0.3, 0.95, 0.95, fill=DARK)
        elif k == "flowbox":
            for i2 in range(3):
                R(0.06 + i2 * 0.32, 0.15, 0.3 + i2 * 0.32, 0.45, fill=DARK)
            R(0.06, 0.55, 0.3, 0.85, fill=DARK)
        elif k == "eventbox":
            for i2 in range(6):
                L(0.05 + i2 * 0.16, 0.05, 0.13 + i2 * 0.16, 0.05, ACC)
                L(0.05 + i2 * 0.16, 0.95, 0.13 + i2 * 0.16, 0.95, ACC)
        elif k == "alignment":
            L(0.5, 0.1, 0.5, 0.9)
            L(0.1, 0.5, 0.9, 0.5)
        elif k == "aspectframe":
            L(0.05, 0.95, 0.95, 0.05)
        elif k == "handlebox":
            for i2 in range(3):
                C(0.09, 0.25 + i2 * 0.25, 0.035, fill=DIMc, col=DIMc)
    elif k == "grid":
        L(0.5, 0.05, 0.5, 0.95)
        L(0.05, 0.5, 0.95, 0.5)
    elif k == "frame":
        R(0.12, 0.0, 0.55, 0.16, fill=PANEL, col=PANEL)
        TXT(0.14, 0.0, label or "frame", DIMc, 11)
    elif k == "notebook":
        th = min(16 * u, h * 0.4)
        tw = min(34 * u, w * 0.3)
        dpg.draw_rectangle((x + 2 * u, y + 2 * u),
                           (x + 2 * u + tw, y + 2 * u + th),
                           fill=(58, 96, 160), color=B, parent=D)
        dpg.draw_rectangle((x + 4 * u + tw, y + 2 * u),
                           (x + 4 * u + 2 * tw, y + 2 * u + th),
                           fill=DARK, color=B, parent=D)
        dpg.draw_line((x + 2 * u, y + 2 * u + th),
                      (x + w - 2 * u, y + 2 * u + th), color=ACC, parent=D)
    elif k == "paned":
        L(0.5, 0.05, 0.5, 0.95, ACC, 3)
    elif k == "listbox" or k == "treeview":
        rows = max(2, int((h - 6 * u) / PITCH))
        for i2 in range(rows):
            ry = y + 4 * u + (i2 + 0.55) * PITCH
            if ry > y + h - 4 * u:
                break
            if k == "treeview":
                ix = x + 8 * u + (i2 % 3) * 12 * u
                t = 4.5 * u
                dpg.draw_triangle((ix, ry - t), (ix, ry + t),
                                  (ix + 1.6 * t, ry), fill=DIMc, parent=D)
                dpg.draw_line((ix + 2.2 * t, ry), (x + w * 0.9, ry),
                              color=DIMc, thickness=max(1, 1.6 * u),
                              parent=D)
            else:
                dpg.draw_line((x + 8 * u, ry), (x + w * 0.9, ry),
                              color=DIMc, thickness=max(1, 1.6 * u),
                              parent=D)
        if k == "listbox":
            dpg.draw_rectangle((x + 3 * u, y + 4 * u),
                               (x + w - 3 * u, y + 4 * u + PITCH),
                               fill=(52, 90, 150, 90), parent=D)
    elif k in ("headerbar", "actionbar", "menubar", "toolbar", "statusbar"):
        if k == "headerbar":
            R(0, 0, 1, 1, fill=DARK, col=B, r=2)
            dr = min(6 * u, h * 0.28)
            dpg.draw_circle((x + 10 * u, y + h * 0.5), dr,
                            fill=(220, 90, 80), parent=D)
            dpg.draw_circle((x + 10 * u + 2.6 * dr, y + h * 0.5), dr,
                            fill=(240, 180, 80), parent=D)
            TXT(0.4, 0.22, label or "title", T)
        elif k == "actionbar":
            R(0, 0, 1, 1, fill=DARK, col=B)
            R(0.62, 0.2, 0.78, 0.8, fill=(52, 90, 150))
            R(0.82, 0.2, 0.97, 0.8, fill=PANEL)
        elif k == "menubar":
            R(0, 0, 1, 1, fill=DARK, col=B)
            for i2, ww2 in enumerate((0.12, 0.1, 0.14)):
                L(0.05 + i2 * 0.2, 0.5, 0.05 + i2 * 0.2 + ww2, 0.5, T, 2)
        elif k == "toolbar":
            R(0, 0, 1, 1, fill=DARK, col=B)
            for i2 in range(4):
                R(0.05 + i2 * 0.14, 0.2, 0.15 + i2 * 0.14, 0.8, fill=PANEL)
        else:
            R(0, 0, 1, 1, fill=DARK, col=B)
            L(0.05, 0.5, 0.4, 0.5, DIMc, 2)
    elif k in ("button", "toggle", "menubutton", "link"):
        R(0.05, 0.12, 0.95, 0.88,
          fill=(58, 96, 160) if k != "toggle" else (36, 60, 104),
          col=ACC if k == "toggle" else B, r=4)
        if k == "menubutton":
            dpg.draw_triangle((x + 0.78 * w, y + 0.42 * h),
                              (x + 0.92 * w, y + 0.42 * h),
                              (x + 0.85 * w, y + 0.62 * h), fill=T, parent=D)
            TXT(0.12, 0.3, label or "menu", T)
        elif k == "link":
            TXT(0.15, 0.28, label or "link", ACC)
            L(0.15, 0.75, 0.6, 0.75, ACC)
        else:
            TXT(0.5 - 0.05 * len(label or "btn"), 0.3, label or "btn", T)
    elif k == "check":
        bx = min(16 * u, h * 0.6)
        cy0 = y + h * 0.5
        dpg.draw_rectangle((x + 5 * u, cy0 - bx / 2),
                           (x + 5 * u + bx, cy0 + bx / 2),
                           fill=FLD, color=B, rounding=2, parent=D)
        dpg.draw_line((x + 5 * u + 0.2 * bx, cy0 + 0.05 * bx),
                      (x + 5 * u + 0.42 * bx, cy0 + 0.3 * bx),
                      color=(30, 120, 60), thickness=max(2, 2.2 * u),
                      parent=D)
        dpg.draw_line((x + 5 * u + 0.42 * bx, cy0 + 0.3 * bx),
                      (x + 5 * u + 0.82 * bx, cy0 - 0.32 * bx),
                      color=(30, 120, 60), thickness=max(2, 2.2 * u),
                      parent=D)
        TXT(0.42, 0.3, label or "check", T)
    elif k == "radio":
        rr = min(8 * u, h * 0.3)
        dpg.draw_circle((x + 5 * u + rr, y + h * 0.5), rr, fill=FLD,
                        color=B, parent=D)
        dpg.draw_circle((x + 5 * u + rr, y + h * 0.5), rr * 0.45,
                        fill=(30, 120, 60), color=(30, 120, 60), parent=D)
        TXT(0.42, 0.3, label or "radio", T)
    elif k == "switch":
        R(0.08, 0.25, 0.6, 0.75, fill=(46, 140, 90), col=B, r=h * 0.25)
        C(0.47, 0.5, 0.2, fill=T, col=T)
    elif k in ("entry", "searchentry", "spinbutton", "combobox"):
        R(0.04, 0.15, 0.96, 0.85, fill=FLD, col=B, r=2)
        mid = y + h * 0.5
        if k == "entry":
            dpg.draw_line((x + 8 * u, mid - 7 * u), (x + 8 * u, mid + 7 * u),
                          color=(40, 44, 55), thickness=max(1, 1.6 * u),
                          parent=D)
        elif k == "searchentry":
            r0 = 5.5 * u
            dpg.draw_circle((x + 10 * u, mid - 1.5 * u), r0,
                            color=(90, 96, 110), parent=D)
            dpg.draw_line((x + 10 * u + 0.7 * r0, mid - 1.5 * u + 0.7 * r0),
                          (x + 10 * u + 1.8 * r0, mid - 1.5 * u + 1.8 * r0),
                          color=(90, 96, 110), thickness=max(1, 1.8 * u),
                          parent=D)
        elif k == "spinbutton":
            bw2 = min(16 * u, w * 0.22)
            dpg.draw_rectangle((x + w - bw2 - 2 * u, y + h * 0.15),
                               (x + w - 2 * u, mid),
                               fill=(200, 205, 215), color=B, parent=D)
            dpg.draw_rectangle((x + w - bw2 - 2 * u, mid),
                               (x + w - 2 * u, y + h * 0.85),
                               fill=(200, 205, 215), color=B, parent=D)
            cxx = x + w - 2 * u - bw2 / 2
            dpg.draw_triangle((cxx - 3.5 * u, mid - 3 * u),
                              (cxx + 3.5 * u, mid - 3 * u),
                              (cxx, mid - 8 * u),
                              fill=(60, 66, 80), parent=D)
            dpg.draw_triangle((cxx - 3.5 * u, mid + 3 * u),
                              (cxx + 3.5 * u, mid + 3 * u),
                              (cxx, mid + 8 * u),
                              fill=(60, 66, 80), parent=D)
        else:
            ax = x + w - 12 * u
            dpg.draw_triangle((ax - 5 * u, mid - 3 * u),
                              (ax + 5 * u, mid - 3 * u),
                              (ax, mid + 5 * u),
                              fill=(60, 66, 80), parent=D)
        if k in ("entry", "combobox"):
            TXT(0.16, 0.3, label or "", (60, 66, 80))
    elif k == "textview":
        R(0.03, 0.05, 0.97, 0.95, fill=FLD, col=B)
        lines = max(2, int((h - 10 * u) / PITCH))
        for i2 in range(lines):
            ly = y + 7 * u + (i2 + 0.5) * PITCH
            if ly > y + h - 6 * u:
                break
            dpg.draw_line((x + 8 * u, ly),
                          (x + w * (0.9 - (i2 % 2) * 0.15), ly),
                          color=(120, 126, 140),
                          thickness=max(1, 1.6 * u), parent=D)
    elif k == "calendar":
        R(0.05, 0.05, 0.95, 0.28, fill=(52, 90, 150), col=B)
        for r2 in range(2):
            for c2 in range(4):
                R(0.08 + c2 * 0.22, 0.38 + r2 * 0.28,
                  0.24 + c2 * 0.22, 0.58 + r2 * 0.28, fill=FLD, col=B)
    elif k == "colorchooser":
        for i2, col2 in enumerate(((220, 90, 80), (240, 180, 80),
                                   (63, 208, 143), (74, 158, 255))):
            R(0.06 + i2 * 0.23, 0.25, 0.24 + i2 * 0.23, 0.75,
              fill=col2, col=B)
    elif k == "fontchooser":
        TXT(0.12, 0.15, "Aa", T, 20)
        L(0.1, 0.8, 0.9, 0.8, DIMc)
    elif k == "filechooser":
        dpg.draw_quad((x + 0.08 * w, y + 0.28 * h), (x + 0.3 * w, y + 0.28 * h),
                      (x + 0.34 * w, y + 0.38 * h), (x + 0.08 * w, y + 0.38 * h),
                      fill=(240, 180, 80), parent=D)
        R(0.08, 0.36, 0.6, 0.8, fill=(240, 180, 80), col=(180, 130, 50))
        R(0.66, 0.36, 0.94, 0.8, fill=FLD, col=B)
    elif k == "label":
        TXT(0.1, 0.28, label or "label", T)
        if small:
            L(0.1, 0.4, 0.7, 0.4, T, 2)
            L(0.1, 0.65, 0.5, 0.65, DIMc, 2)
    elif k == "image":
        R(0.06, 0.08, 0.94, 0.92, fill=DARK, col=B)
        C(0.72, 0.3, 0.09, fill=(240, 200, 90), col=(240, 200, 90))
        dpg.draw_triangle((x + 0.12 * w, y + 0.9 * h),
                          (x + 0.42 * w, y + 0.45 * h),
                          (x + 0.68 * w, y + 0.9 * h),
                          fill=(70, 120, 90), parent=D)
        dpg.draw_triangle((x + 0.5 * w, y + 0.9 * h),
                          (x + 0.72 * w, y + 0.58 * h),
                          (x + 0.92 * w, y + 0.9 * h),
                          fill=(60, 100, 80), parent=D)
    elif k == "progress":
        R(0.05, 0.32, 0.95, 0.68, fill=DARK, col=B, r=3)
        R(0.05, 0.32, 0.62, 0.68, fill=(63, 208, 143),
          col=(63, 208, 143), r=3)
    elif k == "level":
        for i2 in range(5):
            R(0.06 + i2 * 0.19, 0.3, 0.21 + i2 * 0.19, 0.7,
              fill=(63, 208, 143) if i2 < 3 else DARK, col=B)
    elif k == "scale":
        L(0.06, 0.5, 0.94, 0.5, DARK, 4)
        L(0.06, 0.5, 0.55, 0.5, ACC, 4)
        C(0.55, 0.5, 0.16, fill=T, col=B)
    elif k == "separator":
        L(0.05, 0.5, 0.95, 0.5, DIMc, 2)
    elif k == "iconview":
        for r2 in range(2):
            for c2 in range(3):
                R(0.08 + c2 * 0.31, 0.12 + r2 * 0.45,
                  0.3 + c2 * 0.31, 0.42 + r2 * 0.45, fill=(52, 90, 150),
                  col=B)
    elif k == "infobar":
        R(0, 0.2, 1, 0.8, fill=(60, 90, 140), col=ACC)
        C(0.1, 0.5, 0.14, col=T)
        TXT(0.085, 0.3, "i", T)
    elif k == "canvas":
        L(0.05, 0.05, 0.95, 0.95, DIMc)
        L(0.95, 0.05, 0.05, 0.95, DIMc)
    elif k in ("menu", "menuitem"):
        if k == "menu":
            for i2 in range(3):
                L(0.12, 0.22 + i2 * 0.28, 0.85, 0.22 + i2 * 0.28, DIMc, 2)
            R(0.06, 0.1, 0.94, 0.36, fill=(52, 90, 150, 90),
              col=(0, 0, 0, 0))
        else:
            L(0.12, 0.5, 0.7, 0.5, T, 2)
            dpg.draw_triangle((x + 0.85 * w, y + 0.35 * h),
                              (x + 0.85 * w, y + 0.65 * h),
                              (x + 0.95 * w, y + 0.5 * h), fill=DIMc,
                              parent=D)
    else:
        TXT(0.1, 0.3, label or k, T)


# ── selection + properties panel sync ───────────────────────────────────────
_FSIG = [None]
_FSIG_ERR = [""]


def _fsig():
    """The Phase 7c signals module (flowcode_signals) — reused whole."""
    if _FSIG[0] is None and not _FSIG_ERR[0]:
        try:
            five = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "5500fp")
            if five not in sys.path:
                sys.path.insert(0, five)
            spec = _ilu.spec_from_file_location(
                "flowcode_signals", os.path.join(five,
                                                 "flowcode_signals.py"))
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _FSIG[0] = mod
        except Exception as e:                  # noqa: BLE001
            _FSIG_ERR[0] = str(e)
    return _FSIG[0]


def _wired_state(w, sig, handler):
    """Phase 7c-2 truth for one signal row: manual binding beats auto;
    auto is '✓ wired' when the ENTRY flow_terminator carries the handler
    name — explicit is_entry, or the dump-time synthesis rule (first
    terminator when none is explicit), same as the compiler will do."""
    binfo = (w.get("signal_ids") or {}).get(sig["id"]) or \
        (w.get("signal_ids") or {}).get(str(sig["id"]))
    if binfo and isinstance(binfo, dict) and not binfo.get("auto_wired"):
        return "manual", (255, 204, 102)
    F = STYLE.get("FLOW")
    if not handler or F is None:
        return "unwired", STYLE.get("DIM", (110, 110, 110))
    terms = [s for _i, s in sorted(F.FS["syms"].items())
             if s.get("kind") == "flow_terminator"]
    explicit = [s for s in terms
                if any(isinstance(p, dict) and p.get("name") == "is_entry"
                       and p.get("value")
                       for p in s.get("properties", []))]
    entries = explicit if explicit else terms[:1]
    if any(s.get("name", "") == handler for s in entries):
        return "✓ wired", (122, 255, 122)
    if any(s.get("name", "") == handler for s in terms):
        return "named (not entry)", (240, 180, 80)
    return "unwired", STYLE.get("DIM", (110, 110, 110))


def _sync_signals(w):
    """Rebuild the Signals → handlers rows for the selected widget."""
    G = "gp_signals"
    if not dpg.does_item_exist(G):
        return
    dpg.delete_item(G, children_only=True)
    FS = _fsig()
    if FS is None:
        dpg.add_text(f"signals: {_FSIG_ERR[0]}", parent=G,
                     color=STYLE.get("AMB"))
        return
    sigs = FS.signals_for(w["kind"])
    if not sigs:
        dpg.add_text("(this kind emits no signals)", parent=G,
                     color=STYLE.get("DIM"))
        return
    wname = w.get("name", "")
    for sig in sigs:
        handler = FS.canonical_handler_name(wname, sig["name"]) \
            if wname else ""
        state, col = _wired_state(w, sig, handler)
        with dpg.group(horizontal=True, parent=G):
            dpg.add_text(f"{sig['name']:<9}", color=STYLE.get("DIM"))
            dpg.add_text(handler or "(name the widget)",
                         color=STYLE.get("TEXT"))
            dpg.add_text(state, color=col)
    dpg.add_text("name a flow_terminator to a handler\nabove to wire it",
                 parent=G, color=STYLE.get("DIM"))


def _sync_props():
    wid = GS["sel"]
    have = wid is not None and wid in GS["widgets"]
    for t in ("gp_name", "gp_x", "gp_y", "gp_w", "gp_h", "gp_label",
              "gp_title", "gp_modal", "gp_layout", "gp_bind"):
        dpg.configure_item(t, enabled=have)
    if not have:
        dpg.set_value("gp_kind", "nothing selected")
        if dpg.does_item_exist("gp_signals"):
            dpg.delete_item("gp_signals", children_only=True)
        return
    w = GS["widgets"][wid]
    dpg.set_value("gp_kind", f"{w['kind']}   #{wid}")
    dpg.set_value("gp_name", w.get("name", ""))
    dpg.set_value("gp_x", int(w["x"]))
    dpg.set_value("gp_y", int(w["y"]))
    dpg.set_value("gp_w", int(w["w"]))
    dpg.set_value("gp_h", int(w["h"]))
    dpg.set_value("gp_label", w.get("label", ""))
    dpg.set_value("gp_title", str(_prop_get(w, "title", "")))
    dpg.set_value("gp_modal", bool(_prop_get(w, "modal", False)))
    dpg.set_value("gp_layout", w.get("layout_mode", "absolute"))
    dpg.set_value("gp_bind", str(_prop_get(w, "bind_value_to", "")))
    _sync_signals(w)


def _apply_prop(sender, value, field):
    wid = GS["sel"]
    if wid is None or wid not in GS["widgets"]:
        return
    w = GS["widgets"][wid]
    if field in ("x", "y"):
        w[field] = max(0, int(value))
    elif field in ("w", "h"):
        w[field] = max(MIN_SIZE, int(value))
    elif field in ("name", "label", "layout_mode"):
        w[field] = value
    elif field in ("title", "bind_value_to"):
        _prop_set(w, field, value)
    elif field == "modal":
        _prop_set(w, field, bool(value))
    if field in ("layout_mode", "w", "h"):
        layout_all()                    # containers re-flow their children
    redraw()
    if field in ("name", "layout_mode"):
        _sync_props()                   # handler names / states follow


# ── mouse interaction (drawlist space) ──────────────────────────────────────
def _hit(mx, my):
    for wid in reversed(render_order()):        # topmost first
        w = GS["widgets"][wid]
        if w["x"] <= mx <= w["x"] + w["w"] and w["y"] <= my <= w["y"] + w["h"]:
            return wid
    return None


def _handle_hit(mx, my):
    """All EIGHT handles: corners resize both axes, edge midpoints
    resize ONE axis (the one you grabbed) — per the captain, 19-08."""
    wid = GS["sel"]
    if wid is None or wid not in GS["widgets"]:
        return None
    w = GS["widgets"][wid]
    handles = {"nw": (w["x"], w["y"]), "ne": (w["x"] + w["w"], w["y"]),
               "sw": (w["x"], w["y"] + w["h"]),
               "se": (w["x"] + w["w"], w["y"] + w["h"]),
               "n": (w["x"] + w["w"] / 2, w["y"]),
               "s": (w["x"] + w["w"] / 2, w["y"] + w["h"]),
               "w": (w["x"], w["y"] + w["h"] / 2),
               "e": (w["x"] + w["w"], w["y"] + w["h"] / 2)}
    tol = 7 / max(0.5, GS["zoom"])
    for mode, (hx, hy) in handles.items():
        if abs(mx - hx) <= tol and abs(my - hy) <= tol:
            return mode
    return None


def _group_of(wid):
    for name, ids in GS.get("groups", {}).items():
        if wid in ids:
            return name
    return None


def _on_click(*_):
    if not dpg.is_item_hovered("guic_draw"):
        return
    mx, my = _mpos()
    if GS["pending"]:
        add_widget(GS["pending"], mx, my)
        GS["pending"] = None
        dpg.set_value("guic_tool", "tool: Select")
        return
    mode = _handle_hit(mx, my)
    if mode:
        w = GS["widgets"][GS["sel"]]
        _snapshot()
        GS["drag"] = {"mode": mode,
                      "orig": (w["x"], w["y"], w["w"], w["h"])}
        return
    wid = _hit(mx, my)
    if wid is None:
        # RUBBER-BAND (VB kit, 20-08): drag on empty canvas lassos
        GS["sel"] = None
        GS["multi"] = set()
        GS["lasso"] = (mx, my, mx, my)
        redraw()
        _sync_props()
        return
    # a grouped widget selects its WHOLE group (VB doctrine)
    gname = _group_of(wid)
    if gname and wid not in GS["multi"]:
        GS["multi"] = {i for i in GS["groups"][gname]
                       if i in GS["widgets"]}
        _status(f"group '{gname}' — {len(GS['multi'])} widgets")
    elif wid not in GS["multi"]:
        GS["multi"] = set()
    GS["sel"] = wid
    w = GS["widgets"][wid]
    _snapshot()
    GS["drag"] = {"mode": "move", "orig": (w["x"], w["y"], w["w"], w["h"]),
                  "multi0": {i: (GS["widgets"][i]["x"],
                                 GS["widgets"][i]["y"])
                             for i in GS["multi"] if i in GS["widgets"]}}
    redraw()
    _sync_props()


def _on_drag(sender, app_data):
    for grip, key, panel, lo, hi, inv in (
            ("guic_grip", "grip", "guic_panel", 140, 420, False),
            ("guic_grip2", "grip2", "guic_props", 200, 480, True)):
        if dpg.is_item_active(grip) and GS[key] is None:
            GS[key] = dpg.get_item_width(panel) or 200
        if GS[key] is not None:
            _b, gdx, _gdy = app_data
            d = -gdx if inv else gdx
            w = max(lo, min(int(GS[key] + d), hi))
            dpg.configure_item(panel, width=w)
            if panel == "guic_props":
                dpg.configure_item("guic_wrap", width=-(w + 16))
            return
    if GS.get("lasso") is not None:
        mx, my = _mpos()
        x0, y0, _x1, _y1 = GS["lasso"]
        GS["lasso"] = (x0, y0, mx, my)
        redraw()
        return
    if GS["drag"] is None or GS["sel"] is None:
        return
    _btn, dx, dy = app_data
    z = GS["zoom"]
    dx, dy = dx / z, dy / z
    w = GS["widgets"].get(GS["sel"])
    if w is None:
        return
    ox, oy, ow, oh = GS["drag"]["orig"]
    m = GS["drag"]["mode"]
    if m == "move":
        w["x"], w["y"] = max(0, int(ox + dx)), max(0, int(oy + dy))
        for i, (ix, iy) in GS["drag"].get("multi0", {}).items():
            if i != GS["sel"] and i in GS["widgets"]:
                GS["widgets"][i]["x"] = max(0, int(ix + dx))
                GS["widgets"][i]["y"] = max(0, int(iy + dy))
    elif m == "se":
        w["w"], w["h"] = max(MIN_SIZE, int(ow + dx)), max(MIN_SIZE, int(oh + dy))
    elif m == "nw":
        w["x"], w["y"] = max(0, int(ox + dx)), max(0, int(oy + dy))
        w["w"], w["h"] = max(MIN_SIZE, int(ow - dx)), max(MIN_SIZE, int(oh - dy))
    elif m == "ne":
        w["y"] = max(0, int(oy + dy))
        w["w"], w["h"] = max(MIN_SIZE, int(ow + dx)), max(MIN_SIZE, int(oh - dy))
    elif m == "sw":
        w["x"] = max(0, int(ox + dx))
        w["w"], w["h"] = max(MIN_SIZE, int(ow - dx)), max(MIN_SIZE, int(oh + dy))
    elif m == "e":
        w["w"] = max(MIN_SIZE, int(ow + dx))
    elif m == "s":
        w["h"] = max(MIN_SIZE, int(oh + dy))
    elif m == "w":
        w["x"] = max(0, int(ox + dx))
        w["w"] = max(MIN_SIZE, int(ow - dx))
    elif m == "n":
        w["y"] = max(0, int(oy + dy))
        w["h"] = max(MIN_SIZE, int(oh - dy))
    redraw()


def _on_release(*_):
    if GS["grip"] is not None or GS["grip2"] is not None:
        cfg = STYLE.get("CFG")
        if cfg is not None:
            cfg["gui_panel_w"] = dpg.get_item_width("guic_panel")
            cfg["gui_props_w"] = dpg.get_item_width("guic_props")
            if STYLE.get("SAVE"):
                STYLE["SAVE"]()
        GS["grip"] = GS["grip2"] = None
    if GS.get("lasso") is not None:
        x0, y0, x1, y1 = GS["lasso"]
        GS["lasso"] = None
        lo_x, hi_x = min(x0, x1), max(x0, x1)
        lo_y, hi_y = min(y0, y1), max(y0, y1)
        hits = {i for i, w2 in GS["widgets"].items()
                if w2["x"] < hi_x and w2["x"] + w2["w"] > lo_x
                and w2["y"] < hi_y and w2["y"] + w2["h"] > lo_y}
        GS["multi"] = hits
        GS["sel"] = next(iter(hits)) if len(hits) == 1 else GS["sel"]
        redraw()
        _sync_props()
        if hits:
            _status(f"{len(hits)} selected — drag any to move the set, "
                    "align/group in TOOLS")
        return
    if GS["drag"] is None:
        return
    was_multi = bool(GS["drag"].get("multi0"))
    GS["drag"] = None
    if GS["sel"] is not None and GS["sel"] in GS["widgets"]:
        _assign_parent(GS["sel"])
        if was_multi:
            for i in GS["multi"]:
                if i in GS["widgets"]:
                    _assign_parent(i)
        layout_all()                    # dropping into an hbox flows it
        redraw()
    _sync_props()


def _on_del(*_):
    if dpg.is_item_hovered("guic_wrap") or dpg.is_item_hovered("guic_draw"):
        delete_selected()


# ── save / open in the Tk face's exact schema ───────────────────────────────
def _payload(path):
    syms = []
    for wid, w in GS["widgets"].items():
        raw = dict(GS["raw"].get(wid, {}))
        sx, sy = w["x"], w["y"]
        p = GS["widgets"].get(w.get("parent_id"))
        if p is not None:   # Tk schema: children carry centre-offsets
            sx = int(w["x"] + w["w"] / 2 - (p["x"] + p["w"] / 2))
            sy = int(w["y"] + w["h"] / 2 - (p["y"] + p["h"] / 2))
        sym = {"id": wid, "kind": w["kind"], "label": w.get("label", ""),
               "name": w.get("name", ""),
               "gtk_class": raw.get("gtk_class", ""),
               "x": sx, "y": sy,
               "depth": raw.get("depth", 0),
               "w": w["w"], "h": w["h"],
               "parent_id": w.get("parent_id"),
               "layout_mode": w.get("layout_mode", "absolute"),
               "properties": list(w.get("properties", [])),
               "signals": raw.get("signals", []),
               "signal_ids": {k: v for k, v in
                              (w.get("signal_ids") or {}).items()
                              if not (isinstance(v, dict)
                                      and v.get("auto_wired"))}}
        for k, v in raw.items():          # preserve fields we don't edit
            sym.setdefault(k, v)
        syms.append(sym)
    return {
        "ternoo_version": "0.3",
        "source_file": os.path.basename(path),
        "source_type": "ternoo_design",
        "word_stream": [],
        "symbols": syms,
        "edges": list(GS["edges"]),
        "flow_symbols": [], "flow_edges": [],
        "cmd_symbols": [], "cmd_edges": [],
        "cell_symbols": [], "sheet_regions": [], "free_cells": [],
        "sequence": list(_zorder()),
        "groups": {k: list(v) for k, v in GS["groups"].items()},
        "tgui_meta": {"widget_count": len(syms),
                      "edge_count": len(GS["edges"]),
                      "flow_symbol_count": 0, "flow_edge_count": 0},
    }


def _picked(app_data):
    sels = app_data.get("selections") or {}
    if sels:
        return list(sels.values())[0]
    p = app_data.get("file_path_name", "")
    return p[:-2] if p.endswith(".*") else p


def save_to(path):
    if not path.endswith((".gui", ".fc")):
        path += ".gui"
    try:
        json.dump(_payload(path), open(path, "w", encoding="utf-8"), indent=1)
        GS["file"] = path
        GS["dirty"] = False
        _status(f"saved {os.path.basename(path)} — "
                f"{len(GS['widgets'])} widgets (Tk-readable .gui)")
    except Exception as e:                      # noqa: BLE001
        _status(f"save failed: {e}", ok=False)


def load_from(path):
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as e:                      # noqa: BLE001
        _status(f"open failed: {e}", ok=False)
        return
    GS["widgets"].clear()
    GS["raw"].clear()
    GS["sel"] = None
    GS["undo"].clear()
    GS["redo"].clear()
    for sym in doc.get("symbols", []):
        wid = int(sym["id"])
        kind = sym.get("kind", "gui_button")
        dw, dh = DEFAULT_SIZE.get(kind, (GW, GH))
        GS["widgets"][wid] = {
            "id": wid, "kind": kind,
            "label": sym.get("label", ""),
            "name": sym.get("name", f"{kind[4:]}_{wid}"),
            "x": sym.get("x", 0), "y": sym.get("y", 0),
            "w": sym.get("w", dw), "h": sym.get("h", dh),
            "parent_id": sym.get("parent_id"),
            "layout_mode": sym.get("layout_mode", "absolute"),
            "properties": list(sym.get("properties", [])),
            "signal_ids": dict(sym.get("signal_ids", {})),
        }
        GS["raw"][wid] = dict(sym)
        GS["next"] = max(GS["next"], wid + 1)
    _rel_to_abs(list(GS["widgets"]))
    # THE FILE IS TRUTH (20-08): no layout re-flow on open — saved
    # coordinates render exactly as saved. The engine runs only on live
    # actions (drop / resize / layout_mode change).
    seq = [int(i) for i in doc.get("sequence", [])
           if int(i) in GS["widgets"]]
    GS["zorder"] = seq + [i for i in GS["widgets"] if i not in seq]
    GS["groups"] = {str(k): [int(i) for i in v if int(i) in GS["widgets"]]
                    for k, v in (doc.get("groups") or {}).items()}
    GS["groups"] = {k: v for k, v in GS["groups"].items() if v}
    GS["multi"] = set()
    _rescue_offcanvas()
    GS["edges"] = [dict(e) for e in doc.get("edges", [])]
    GS["file"] = path
    GS["dirty"] = False
    redraw()
    _sync_props()
    _grplist_refresh()
    _status(f"opened {os.path.basename(path)} — "
            f"{len(GS['widgets'])} widgets, {len(GS['edges'])} edges"
            + (f", {len(GS['groups'])} groups" if GS["groups"] else ""))


def _rel_to_abs(ids):
    """Tk schema: PARENTED widgets carry centre-offsets from the parent's
    centre. Convert those ids to this organ's absolute top-left, parents
    first, so nested designs land where the Tk face put them."""
    for wid in sorted(ids, key=_depth_of):
        w = GS["widgets"][wid]
        p = GS["widgets"].get(w.get("parent_id"))
        if p is not None:
            w["x"] = int(p["x"] + p["w"] / 2 + w["x"] - w["w"] / 2)
            w["y"] = int(p["y"] + p["h"] / 2 + w["y"] - w["h"] / 2)


def _rescue_offcanvas():
    """Heal scattered files (the 19-08 offset-migration wound): any widget
    lying entirely OUTSIDE the canvas is pulled back into view, cascaded,
    and counted in the status line — work is never invisibly lost."""
    lost = [w for w in GS["widgets"].values()
            if w["x"] + w["w"] < 0 or w["x"] > CANVAS_W
            or w["y"] + w["h"] < 0 or w["y"] > CANVAS_H]
    for i, w in enumerate(lost):
        w["x"] = 30 + (i % 8) * 40
        w["y"] = 30 + (i // 8) * 40
        if w.get("parent_id") is not None:
            w["parent_id"] = None       # placement no longer inside it
    if lost:
        GS["dirty"] = True
        _status(f"⚠ rescued {len(lost)} off-canvas widget(s) back into "
                "view — re-place and save", ok=False)
    return len(lost)


def import_merge(path):
    """Merge another design's widgets into the canvas: fresh ids, parent
    links remapped within the import, roots nudged +30 so the arrival is
    visible, then the layout engine flows any laid-out containers."""
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as e:                      # noqa: BLE001
        _status(f"import failed: {e}", ok=False)
        return 0
    syms = doc.get("symbols", [])
    if not syms:
        _status("nothing to import — no widgets in that file", ok=False)
        return 0
    _snapshot()
    idmap = {}
    for sym in syms:
        wid = GS["next"]
        GS["next"] += 1
        idmap[int(sym["id"])] = wid
        kind = sym.get("kind", "gui_button")
        dw, dh = DEFAULT_SIZE.get(kind, (GW, GH))
        GS["widgets"][wid] = {
            "id": wid, "kind": kind,
            "label": sym.get("label", ""),
            "name": sym.get("name", f"{kind[4:]}_{wid}"),
            "x": sym.get("x", 0), "y": sym.get("y", 0),
            "w": sym.get("w", dw), "h": sym.get("h", dh),
            "parent_id": sym.get("parent_id"),
            "layout_mode": sym.get("layout_mode",
                                   LAYOUT_DEFAULTS.get(kind, "absolute")),
            "properties": list(sym.get("properties", [])),
            "signal_ids": dict(sym.get("signal_ids", {})),
        }
        GS["raw"][wid] = dict(sym)
    for old, new in idmap.items():
        w = GS["widgets"][new]
        op = w.get("parent_id")
        w["parent_id"] = idmap.get(int(op)) if op is not None else None
        if w["parent_id"] is None:
            w["x"], w["y"] = int(w["x"]) + 30, int(w["y"]) + 30
    _rel_to_abs(list(idmap.values()))
    _zorder()                           # arrivals stack on top, file truth
    GS["dirty"] = True
    redraw()
    _sync_props()
    _status(f"imported {len(idmap)} widgets from {os.path.basename(path)}")
    return len(idmap)


def _save_clicked(*_):
    if GS["file"]:
        save_to(GS["file"])
    else:
        dpg.show_item("guic_save_dlg")


# ── build ───────────────────────────────────────────────────────────────────
def _pick_kind(kind):
    GS["pending"] = kind
    dpg.set_value("guic_tool", f"tool: place {kind[4:]} — click the canvas")


def build_gui_tab(style):
    STYLE.update(style)
    C = STYLE
    _designs = os.path.dirname(os.path.abspath(__file__))
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         tag="guic_save_dlg", width=780, height=480,
                         default_path=_designs, default_filename="design",
                         callback=lambda s, a: save_to(_picked(a))):
        dpg.add_file_extension(".gui", color=(74, 158, 255))
        dpg.add_file_extension(".*")
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         tag="guic_open_dlg", width=780, height=480,
                         default_path=_designs, default_filename="",
                         callback=lambda s, a: load_from(_picked(a))):
        dpg.add_file_extension(".gui", color=(74, 158, 255))
        dpg.add_file_extension(".fc", color=(63, 208, 143))
        dpg.add_file_extension(".*")
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         tag="guic_import_dlg", width=780, height=480,
                         default_path=_designs, default_filename="",
                         callback=lambda s, a: import_merge(_picked(a))):
        dpg.add_file_extension(".gui", color=(74, 158, 255))
        dpg.add_file_extension(".fc", color=(63, 208, 143))
        dpg.add_file_extension(".*")

    with dpg.group(horizontal=True):
        # ── left: tools + palette ──
        with dpg.child_window(width=int(C.get("CFG", {})
                              .get("gui_panel_w", 320)),
                              tag="guic_panel"):
            dpg.add_text("TOOLS", color=C["DIM"])
            dpg.add_button(label=" Select ", width=-1,
                           callback=lambda: (GS.update(pending=None),
                                             dpg.set_value("guic_tool",
                                                           "tool: Select")))
            dpg.add_button(label=" Delete ", width=-1,
                           callback=delete_selected)
            with dpg.group(horizontal=True):
                dpg.add_button(label=" ▲ Front ", callback=bring_to_front)
                dpg.add_button(label=" ▼ Back ", callback=send_to_back)
            dpg.add_text("ALIGN (rubber-band 2+)", color=C["DIM"])
            with dpg.group(horizontal=True):
                dpg.add_button(label="⇤", callback=lambda:
                               align_selected("left"))
                dpg.add_button(label="⇞", callback=lambda:
                               align_selected("top"))
                dpg.add_button(label="↔", callback=lambda:
                               align_selected("hcenter"))
                dpg.add_button(label="↕", callback=lambda:
                               align_selected("vcenter"))
                dpg.add_button(label="⇹", callback=lambda:
                               distribute_selected("h"))
                dpg.add_button(label="⇳", callback=lambda:
                               distribute_selected("v"))
            dpg.add_text("GROUPS (named · saved)", color=C["DIM"])
            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="guic_grpname", width=-64,
                                   hint="group name")
                dpg.add_button(label=" ⌘ ", callback=lambda:
                               group_selection(
                                   dpg.get_value("guic_grpname")))
            with dpg.group(tag="guic_grplist"):
                pass
            dpg.add_spacer(height=6)
            dpg.add_text("WIDGETS", color=C["DIM"])
            for sec, kinds in PALETTE:
                with dpg.collapsing_header(label=sec,
                                           default_open=(sec == "CONTAINERS")):
                    for k in kinds:
                        with dpg.group(horizontal=True):
                            dl = dpg.add_drawlist(width=46, height=28)
                            _render_widget(dl, k, 2, 2, 42, 24, px=0.55)
                            dpg.add_button(label=f" {k[4:]} ", width=-1,
                                           user_data=k,
                                           callback=lambda s, a, u:
                                           _pick_kind(u))
                        with dpg.item_handler_registry() as hreg:
                            dpg.add_item_clicked_handler(
                                callback=lambda s, a, u=k: _pick_kind(u))
                        dpg.bind_item_handler_registry(dl, hreg)
            dpg.add_spacer(height=6)
            dpg.add_text("ACTIONS", color=C["DIM"])
            dpg.add_button(label=" Save ", width=-1, callback=_save_clicked)
            dpg.add_button(label=" Save as... ", width=-1,
                           callback=lambda: dpg.show_item("guic_save_dlg"))
            dpg.add_button(label=" Open ", width=-1,
                           callback=lambda: dpg.show_item("guic_open_dlg"))
            dpg.add_button(label=" Clear ", width=-1, callback=clear_all)
            dpg.add_button(label=" Undo ", width=-1, callback=undo)
            dpg.add_button(label=" Redo ", width=-1, callback=redo)
        with dpg.child_window(width=10, height=-1, no_scrollbar=True,
                              border=False):
            dpg.add_button(tag="guic_grip", label="", width=-1, height=2600)
        # ── centre: the canvas ──
        props_w = int(C.get("CFG", {}).get("gui_props_w", 300))
        with dpg.child_window(tag="guic_wrap", width=-(props_w + 16),
                              horizontal_scrollbar=True):
            with dpg.drawlist(width=CANVAS_W, height=CANVAS_H,
                              tag="guic_draw"):
                pass
        with dpg.child_window(width=10, height=-1, no_scrollbar=True,
                              border=False):
            dpg.add_button(tag="guic_grip2", label="", width=-1, height=2600)
        # ── right: properties ──
        with dpg.child_window(width=props_w, tag="guic_props"):
            dpg.add_text("PROPERTIES", color=C["DIM"])
            dpg.add_text("Zoom: 100%", tag="guic_zoomlbl", color=C["DIM"])
            dpg.add_text("nothing selected", tag="gp_kind", color=C["GRN"])
            dpg.add_text("Identity", color=C["DIM"])
            with dpg.group(horizontal=True):
                dpg.add_text("name ", color=C["DIM"])
                dpg.add_input_text(tag="gp_name", width=-1,
                                   callback=lambda s, a: _apply_prop(s, a,
                                                                    "name"))
            dpg.add_text("Geometry", color=C["DIM"])
            for f in ("x", "y", "w", "h"):
                with dpg.group(horizontal=True):
                    dpg.add_text(f"{f:5s}", color=C["DIM"])
                    dpg.add_input_int(tag=f"gp_{f}", width=-1,
                                      user_data=f,
                                      callback=lambda s, a, u:
                                      _apply_prop(s, a, u))
            dpg.add_text("Appearance", color=C["DIM"])
            with dpg.group(horizontal=True):
                dpg.add_text("label", color=C["DIM"])
                dpg.add_input_text(tag="gp_label", width=-1,
                                   callback=lambda s, a:
                                   _apply_prop(s, a, "label"))
            with dpg.group(horizontal=True):
                dpg.add_text("title", color=C["DIM"])
                dpg.add_input_text(tag="gp_title", width=-1,
                                   callback=lambda s, a:
                                   _apply_prop(s, a, "title"))
            dpg.add_checkbox(label="modal", tag="gp_modal",
                             callback=lambda s, a: _apply_prop(s, a, "modal"))
            dpg.add_text("Container", color=C["DIM"])
            dpg.add_combo(LAYOUT_MODES, tag="gp_layout", width=-1,
                          callback=lambda s, a:
                          _apply_prop(s, a, "layout_mode"))
            dpg.add_text("Signals → handlers", color=C["DIM"])
            with dpg.group(tag="gp_signals"):
                pass
            dpg.add_text("Cell binding", color=C["DIM"])
            dpg.add_input_text(tag="gp_bind", width=-1, hint="bind_value_to",
                               callback=lambda s, a:
                               _apply_prop(s, a, "bind_value_to"))
    dpg.add_text("tool: Select", tag="guic_tool", color=C["DIM"])
    dpg.add_text("GUI builder ready — reads and writes the Tk face's .gui",
                 tag="guic_status", color=C["DIM"])

    with dpg.handler_registry():
        dpg.add_mouse_click_handler(dpg.mvMouseButton_Left,
                                    callback=_on_click)
        dpg.add_mouse_drag_handler(dpg.mvMouseButton_Left,
                                   callback=_on_drag)
        dpg.add_mouse_release_handler(dpg.mvMouseButton_Left,
                                      callback=_on_release)
        dpg.add_key_press_handler(dpg.mvKey_Delete, callback=_on_del)
    redraw()
    _sync_props()
    _grplist_refresh()


def _selftest():
    """The 19-08 leg's gate: layout engine (vbox/hbox/grid), Tk-schema
    child centre-offsets through save+load, import merge, signals rows."""
    import tempfile
    clear_all()
    GS["undo"].clear()
    box = add_widget("gui_box", 100, 100)
    GS["widgets"][box].update(w=200, h=150, layout_mode="vbox")  # opt-in
    b1 = add_widget("gui_button", 140, 120)
    b2 = add_widget("gui_button", 140, 170)
    assert GS["widgets"][b1]["parent_id"] == box
    layout_all()
    w1, w2 = GS["widgets"][b1], GS["widgets"][b2]
    assert w1["x"] == w2["x"] == 104 and w1["w"] == w2["w"] == 192
    assert w1["y"] < w2["y"], "vbox must stack downward"
    GS["widgets"][box]["layout_mode"] = "hbox"
    layout_all()
    assert w1["y"] == w2["y"] and w1["x"] < w2["x"], "hbox side-by-side"

    pay = _payload("gate.gui")
    child = next(s for s in pay["symbols"] if s["id"] == b1)
    assert child["x"] == int(w1["x"] + w1["w"] / 2
                             - (100 + 200 / 2)), "centre-offset save"
    with tempfile.NamedTemporaryFile("w", suffix=".gui",
                                     delete=False) as f:
        json.dump(pay, f)
        tmp = f.name
    ax, ay = w1["x"], w1["y"]
    load_from(tmp)
    r1 = GS["widgets"][b1]
    assert (r1["x"], r1["y"]) == (ax, ay), "rel→abs load round-trip"
    n0 = len(GS["widgets"])
    added = import_merge(tmp)
    assert added == n0 and len(GS["widgets"]) == 2 * n0
    kid = next(w for w in GS["widgets"].values()
               if w["id"] >= n0 and w["kind"] == "gui_button")
    assert kid["parent_id"] is not None and kid["parent_id"] >= n0, \
        "import parent remap"
    os.unlink(tmp)

    FS = _fsig()
    assert FS is not None, f"signals module: {_FSIG_ERR[0]}"
    sigs = FS.signals_for("gui_button")
    assert sigs, "gui_button emits no signals?"
    h = FS.canonical_handler_name("save_btn", sigs[0]["name"])
    assert h and " " not in h
    state, _col = _wired_state(GS["widgets"][b1], sigs[0], h)
    assert state in ("unwired", "manual", "✓ wired", "named (not entry)")

    # ── 20-08 z-order + file-truth + rescue invariants ──────────────────
    clear_all()
    win = add_widget("gui_window", 60, 60)
    GS["widgets"][win]["w"], GS["widgets"][win]["h"] = 400, 300
    btn = add_widget("gui_button", 120, 120)
    assert GS["widgets"][btn]["parent_id"] == win
    GS["zorder"] = [btn, win]           # a hostile file order buries it...
    ro = render_order()
    assert ro.index(win) < ro.index(btn), \
        "child buried under its own container"        # ...containment wins
    assert _hit(130, 130) == btn, "topmost hit must be the child"
    inner = add_widget("gui_window", 100, 100)
    assert GS["widgets"][inner]["parent_id"] is None, \
        "windows are top-level — never adopted"
    assert GS["widgets"][inner]["layout_mode"] == "absolute", \
        "layouts are opt-in (VB doctrine)"
    GS["sel"] = win
    bring_to_front()
    assert _zorder()[-1] == win
    send_to_back()
    assert _zorder()[0] == win

    box = add_widget("gui_box", 600, 60)
    GS["widgets"][box].update(w=200, h=150, layout_mode="vbox")
    stray = add_widget("gui_button", 640, 90)   # hand-placed inside box
    layout_all()                                # explicit vbox flows it...
    sx, sy = GS["widgets"][stray]["x"], GS["widgets"][stray]["y"]
    import tempfile as _tf
    with _tf.NamedTemporaryFile("w", suffix=".gui", delete=False) as f:
        json.dump(_payload(f.name), f)
        tmp2 = f.name
    load_from(tmp2)
    assert (GS["widgets"][stray]["x"],
            GS["widgets"][stray]["y"]) == (sx, sy), \
        "open must NOT re-flow — the file is truth"
    seq_saved = json.load(open(tmp2))["sequence"]
    assert [int(i) for i in seq_saved] == _zorder(), "sequence round-trip"
    os.unlink(tmp2)
    GS["widgets"][stray]["x"] = -5000           # scatter victim
    n_resc = _rescue_offcanvas()
    assert n_resc == 1 and GS["widgets"][stray]["x"] >= 0, "rescue"

    # ── the VB kit (20-08): align · distribute · named groups ───────────
    clear_all()
    a1 = add_widget("gui_button", 100, 100)
    a2 = add_widget("gui_button", 300, 160)
    a3 = add_widget("gui_button", 500, 240)
    GS["multi"] = {a1, a2, a3}
    align_selected("top")
    ys = {GS["widgets"][i]["y"] for i in (a1, a2, a3)}
    assert ys == {100}, ys
    distribute_selected("h")
    xs = sorted(GS["widgets"][i]["x"] for i in (a1, a2, a3))
    gaps = [xs[1] - xs[0], xs[2] - xs[1]]
    assert gaps[0] == gaps[1], gaps
    group_selection("trio")
    assert GS["groups"]["trio"] == sorted([a1, a2, a3])
    assert _group_of(a2) == "trio"
    with tempfile.NamedTemporaryFile("w", suffix=".gui",
                                     delete=False) as f:
        json.dump(_payload(f.name), f)
        tmpg = f.name
    load_from(tmpg)
    os.unlink(tmpg)
    assert GS["groups"].get("trio") == sorted([a1, a2, a3]), \
        "named groups ride the .gui"
    select_group("trio")
    assert GS["multi"] == {a1, a2, a3}
    n_grp = len(GS["groups"])

    clear_all()
    GS["undo"].clear()
    GS["redo"].clear()
    GS["zorder"] = []
    GS["next"] = 0      # downstream gates index from a fresh canvas
    return {"layout": "vbox+hbox", "roundtrip": "centre-offsets",
            "imported": added, "signals": len(sigs), "handler": h,
            "zorder": "containment-safe", "rescue": n_resc,
            "vbkit": f"align+distribute+{n_grp} named group(s)"}
