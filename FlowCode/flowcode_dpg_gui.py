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

Not yet ported from Tk (stated, not hidden): non-absolute layout
preview (vbox/grid/stacked modes are STORED faithfully but children
are not auto-laid-out), the signal/handler editor, RNODE widget
geometry rendering, and Import. They ride the next legs.
"""
import json
import os

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
}


def is_dirty():
    return bool(GS["dirty"]) and bool(GS["widgets"])


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
                                  "n": GS["next"]}))
    GS["undo"] = GS["undo"][-50:]
    GS["redo"].clear()


def _restore(blob):
    d = json.loads(blob)
    GS["widgets"] = {int(k): v for k, v in d["w"].items()}
    GS["edges"] = d["e"]
    GS["next"] = d["n"]
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
        "layout_mode": LAYOUT_DEFAULTS.get(kind, "absolute"),
        "properties": [], "signal_ids": {},
    }
    GS["sel"] = wid
    redraw()
    _sync_props()
    _status(f"placed {kind[4:]} #{wid}")
    return wid


def delete_selected(*_):
    wid = GS["sel"]
    if wid is None:
        return
    _snapshot()
    GS["widgets"].pop(wid, None)
    GS["raw"].pop(wid, None)
    for w in GS["widgets"].values():
        if w.get("parent_id") == wid:
            w["parent_id"] = None
    GS["sel"] = None
    redraw()
    _sync_props()
    _status(f"deleted #{wid}")


def clear_all(*_):
    if not GS["widgets"]:
        return
    _snapshot()
    GS["widgets"].clear()
    GS["raw"].clear()
    GS["edges"].clear()
    GS["sel"] = None
    redraw()
    _sync_props()
    _status("canvas cleared")


def _assign_parent(wid):
    """Containment by geometry: centre inside a container -> child of it."""
    w = GS["widgets"][wid]
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
    for wid, w in GS["widgets"].items():
        x, y = w["x"] * Z, w["y"] * Z
        ww, hh = w["w"] * Z, w["h"] * Z
        is_ct = w["kind"] in CONTAINER_KINDS
        fill = (30, 41, 66) if is_ct else (42, 47, 63)
        dpg.draw_rectangle((x, y), (x + ww, y + hh), fill=fill,
                           color=C["BORDER"], parent=D)
        if is_ct and hh > 34:
            dpg.draw_rectangle((x, y), (x + ww, y + 18),
                               fill=(24, 33, 54), color=C["BORDER"],
                               parent=D)
        label = w.get("label") or w["kind"][4:]
        dpg.draw_text((x + max(4, ww / 2 - len(label) * 4 * Z),
                       y + hh / 2 - 8 * Z), label, size=14 * Z,
                      color=C["TEXT"], parent=D)
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
            dpg.draw_text((x, y + hh + 8 * Z), cap, size=13 * Z,
                          color=(255, 140, 70), parent=D)


# ── selection + properties panel sync ───────────────────────────────────────
def _sync_props():
    wid = GS["sel"]
    have = wid is not None and wid in GS["widgets"]
    for t in ("gp_name", "gp_x", "gp_y", "gp_w", "gp_h", "gp_label",
              "gp_title", "gp_modal", "gp_layout", "gp_bind"):
        dpg.configure_item(t, enabled=have)
    if not have:
        dpg.set_value("gp_kind", "nothing selected")
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
    redraw()


# ── mouse interaction (drawlist space) ──────────────────────────────────────
def _hit(mx, my):
    for wid in reversed(list(GS["widgets"])):
        w = GS["widgets"][wid]
        if w["x"] <= mx <= w["x"] + w["w"] and w["y"] <= my <= w["y"] + w["h"]:
            return wid
    return None


def _handle_hit(mx, my):
    wid = GS["sel"]
    if wid is None or wid not in GS["widgets"]:
        return None
    w = GS["widgets"][wid]
    corners = {"nw": (w["x"], w["y"]), "ne": (w["x"] + w["w"], w["y"]),
               "sw": (w["x"], w["y"] + w["h"]),
               "se": (w["x"] + w["w"], w["y"] + w["h"])}
    for mode, (hx, hy) in corners.items():
        if abs(mx - hx) <= 6 and abs(my - hy) <= 6:
            return mode
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
    GS["sel"] = wid
    if wid is not None:
        w = GS["widgets"][wid]
        _snapshot()
        GS["drag"] = {"mode": "move", "orig": (w["x"], w["y"], w["w"], w["h"])}
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
    if GS["drag"] is None:
        return
    GS["drag"] = None
    if GS["sel"] is not None and GS["sel"] in GS["widgets"]:
        _assign_parent(GS["sel"])
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
        sym = {"id": wid, "kind": w["kind"], "label": w.get("label", ""),
               "name": w.get("name", ""),
               "gtk_class": raw.get("gtk_class", ""),
               "x": w["x"], "y": w["y"],
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
        "sequence": list(GS["widgets"].keys()),
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
            "layout_mode": sym.get("layout_mode",
                                   LAYOUT_DEFAULTS.get(kind, "absolute")),
            "properties": list(sym.get("properties", [])),
            "signal_ids": dict(sym.get("signal_ids", {})),
        }
        GS["raw"][wid] = dict(sym)
        GS["next"] = max(GS["next"], wid + 1)
    GS["edges"] = [dict(e) for e in doc.get("edges", [])]
    GS["file"] = path
    GS["dirty"] = False
    redraw()
    _sync_props()
    _status(f"opened {os.path.basename(path)} — "
            f"{len(GS['widgets'])} widgets, {len(GS['edges'])} edges")


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
            dpg.add_spacer(height=6)
            dpg.add_text("WIDGETS", color=C["DIM"])
            for sec, kinds in PALETTE:
                with dpg.collapsing_header(label=sec,
                                           default_open=(sec == "CONTAINERS")):
                    for k in kinds:
                        dpg.add_button(label=f" {k[4:]} ", width=-1,
                                       user_data=k,
                                       callback=lambda s, a, u:
                                       _pick_kind(u))
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
            dpg.add_text("(non-absolute layout preview\n rides the next leg)",
                         color=C["DIM"])
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
