#!/usr/bin/env python3
"""flowcode_dpg_flow — the Flow tab ORGAN of FlowCode's Dear PyGui face.

The real FlowCode language, ported against the Tk face's own model:
the four UDP symbols — Terminator (oval), Process (rectangle), Decision
(diamond), I/O (parallelogram) — plus the EXEC Edge. Tk conventions
carried over verbatim: SYMBOL_W/H 120x60, GRID snap 40, labels
kind-initial + id (T0, P1, D2, I3), names kind_id, the Tk colour table,
selected-orange, no duplicate edges. Save/Open reads and writes the Tk
.fc/.flow schema; on .fc files every section this tab does not edit is
PRESERVED verbatim through load->save.

Not yet ported (stated, not hidden): Word Dump / Load->EMU / Step / Run /
Stop (the execution projection), Import, Learn, Suggest, waypoint
editing (loaded waypoints ARE rendered), pocket scopes (loaded nested
scopes are preserved untouched; the canvas shows top level), canvas
zoom. Each rides a later leg of this tab's port.
"""
import json
import math
import os

import dearpygui.dearpygui as dpg

SYMBOL_W, SYMBOL_H, GRID = 120, 60, 40
CANVAS_W, CANVAS_H = 2400, 1600

COL = {
    "flow_process":    (15, 52, 96),
    "flow_decision":   (83, 52, 131),
    "flow_io":         (26, 107, 94),
    "flow_terminator": (26, 74, 107),
    "border":          (74, 158, 255),
    "selected":        (255, 107, 53),
}
KINDS = [
    ("flow_terminator", "Terminator", "oval · start/end"),
    ("flow_process",    "Process",    "rectangle"),
    ("flow_decision",   "Decision",   "diamond"),
    ("flow_io",         "I/O",        "parallelogram"),
]

FS = {
    "syms": {}, "raw": {}, "edges": [], "rawdoc": None,
    "next": 0, "sel": None, "sel_edge": None, "file": None,
    "tool": "select", "edge_src": None, "drag": None,
    "undo": [], "redo": [],
}
STYLE = {}


def snap(v):
    return round(v / GRID) * GRID


def _status(msg, ok=True):
    dpg.set_value("flowc_status", msg)
    dpg.configure_item("flowc_status",
                       color=STYLE.get("GRN" if ok else "AMB"))


def _selinfo(msg=""):
    dpg.set_value("flowc_selinfo", msg)


# ── undo / redo ─────────────────────────────────────────────────────────────
def _snapshot():
    FS["undo"].append(json.dumps({"s": FS["syms"], "e": FS["edges"],
                                  "n": FS["next"]}))
    FS["undo"] = FS["undo"][-50:]
    FS["redo"].clear()


def _restore(blob):
    d = json.loads(blob)
    FS["syms"] = {int(k): v for k, v in d["s"].items()}
    FS["edges"] = d["e"]
    FS["next"] = d["n"]
    if FS["sel"] not in FS["syms"]:
        FS["sel"] = None
    FS["sel_edge"] = None
    redraw()


def undo(*_):
    if not FS["undo"]:
        _status("nothing to undo", ok=False)
        return
    FS["redo"].append(json.dumps({"s": FS["syms"], "e": FS["edges"],
                                  "n": FS["next"]}))
    _restore(FS["undo"].pop())
    _status("undone")


def redo(*_):
    if not FS["redo"]:
        _status("nothing to redo", ok=False)
        return
    FS["undo"].append(json.dumps({"s": FS["syms"], "e": FS["edges"],
                                  "n": FS["next"]}))
    _restore(FS["redo"].pop())
    _status("redone")


# ── model ops (Tk conventions verbatim) ─────────────────────────────────────
def add_symbol(kind, x, y, label=""):
    _snapshot()
    sid = FS["next"]
    FS["next"] += 1
    lbl = label or f"{kind.split('_', 1)[-1][0].upper()}{sid}"
    FS["syms"][sid] = {
        "id": sid, "kind": kind, "x": snap(x), "y": snap(y),
        "w": SYMBOL_W, "h": SYMBOL_H, "label": lbl,
        "name": f"{kind}_{sid}", "parent_scope": None, "properties": [],
    }
    FS["sel"] = sid
    redraw()
    _status(f"placed {lbl}")
    return sid


def add_edge(src_id, dst_id):
    if src_id == dst_id or src_id not in FS["syms"] \
            or dst_id not in FS["syms"]:
        return None
    for e in FS["edges"]:
        if e["src"] == src_id and e["dst"] == dst_id:
            _status("edge already exists", ok=False)
            return None
    _snapshot()
    edge = {"src": src_id, "dst": dst_id, "waypoints": [], "condition": ""}
    FS["edges"].append(edge)
    redraw()
    _status(f"Edge {FS['syms'][src_id]['label']} → "
            f"{FS['syms'][dst_id]['label']}")
    return edge


def delete_symbol(sid):
    if sid not in FS["syms"]:
        return
    _snapshot()
    lbl = FS["syms"][sid]["label"]
    FS["syms"].pop(sid)
    FS["raw"].pop(sid, None)
    FS["edges"] = [e for e in FS["edges"]
                   if e["src"] != sid and e["dst"] != sid]
    if FS["sel"] == sid:
        FS["sel"] = None
    redraw()
    _status(f"deleted {lbl} (+ its edges)")


def delete_edge(idx):
    if 0 <= idx < len(FS["edges"]):
        _snapshot()
        e = FS["edges"].pop(idx)
        FS["sel_edge"] = None
        redraw()
        _status(f"edge removed ({e['src']} → {e['dst']})")


def delete_selected(*_):
    if FS["sel"] is not None:
        delete_symbol(FS["sel"])
    elif FS["sel_edge"] is not None:
        delete_edge(FS["sel_edge"])


def clear_all(*_):
    if not FS["syms"] and not FS["edges"]:
        return
    _snapshot()
    FS["syms"].clear()
    FS["raw"].clear()
    FS["edges"].clear()
    FS["sel"] = FS["sel_edge"] = None
    redraw()
    _status("canvas cleared")


# ── geometry ────────────────────────────────────────────────────────────────
def _center(s):
    return (s["x"] + s["w"] / 2, s["y"] + s["h"] / 2)


def _border_point(s, toward):
    """Point on s's rectangle border along the line centre->toward."""
    cx, cy = _center(s)
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    tx = (s["w"] / 2) / abs(dx) if dx else math.inf
    ty = (s["h"] / 2) / abs(dy) if dy else math.inf
    t = min(tx, ty)
    return (cx + dx * t, cy + dy * t)


def _edge_points(e):
    src, dst = FS["syms"].get(e["src"]), FS["syms"].get(e["dst"])
    if not src or not dst:
        return []
    pts = [_center(src)] + [tuple(p) for p in e.get("waypoints", [])] \
        + [_center(dst)]
    first = _border_point(src, pts[1])
    last = _border_point(dst, pts[-2])
    return [first] + pts[1:-1] + [last]


def _seg_dist(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _hit_symbol(mx, my):
    for sid in reversed(list(FS["syms"])):
        s = FS["syms"][sid]
        if s["x"] <= mx <= s["x"] + s["w"] and s["y"] <= my <= s["y"] + s["h"]:
            return sid
    return None


def _hit_edge(mx, my):
    for i, e in enumerate(FS["edges"]):
        pts = _edge_points(e)
        for a, b in zip(pts, pts[1:]):
            if _seg_dist((mx, my), a, b) <= 8:
                return i
    return None


# ── drawing ─────────────────────────────────────────────────────────────────
def _draw_symbol(s, selected):
    D = "flowc_draw"
    x, y, w, h = s["x"], s["y"], s["w"], s["h"]
    fill = COL.get(s["kind"], COL["flow_process"])
    border = COL["selected"] if selected else COL["border"]
    th = 3 if selected else 2
    k = s["kind"]
    if k == "flow_terminator":
        dpg.draw_rectangle((x, y), (x + w, y + h), fill=fill, color=border,
                           thickness=th, rounding=h / 2, parent=D)
    elif k == "flow_decision":
        cx, cy = x + w / 2, y + h / 2
        dpg.draw_quad((cx, y), (x + w, cy), (cx, y + h), (x, cy),
                      fill=fill, color=border, thickness=th, parent=D)
    elif k == "flow_io":
        sk = 16
        dpg.draw_quad((x + sk, y), (x + w, y), (x + w - sk, y + h),
                      (x, y + h), fill=fill, color=border, thickness=th,
                      parent=D)
    else:                                   # process (and subroutine kin)
        dpg.draw_rectangle((x, y), (x + w, y + h), fill=fill, color=border,
                           thickness=th, parent=D)
    lbl = s.get("label", "")
    dpg.draw_text((x + w / 2 - len(lbl) * 4.2, y + h / 2 - 8), lbl,
                  size=15, color=STYLE.get("TEXT", (238, 240, 245)),
                  parent=D)
    kindword = s["kind"].split("_", 1)[-1]
    dpg.draw_text((x + w / 2 - len(kindword) * 3.2, y + h + 4), kindword,
                  size=11, color=STYLE.get("DIM", (168, 175, 190)), parent=D)
    if selected:
        dpg.draw_text((x, y - 16), f"({s['x']},{s['y']})", size=12,
                      color=COL["selected"], parent=D)


def redraw():
    D = "flowc_draw"
    dpg.delete_item(D, children_only=True)
    for gx in range(0, CANVAS_W + 1, GRID):
        dpg.draw_line((gx, 0), (gx, CANVAS_H), color=(40, 46, 62, 80),
                      parent=D)
    for gy in range(0, CANVAS_H + 1, GRID):
        dpg.draw_line((0, gy), (CANVAS_W, gy), color=(40, 46, 62, 80),
                      parent=D)
    for i, e in enumerate(FS["edges"]):
        pts = _edge_points(e)
        if len(pts) < 2:
            continue
        col = COL["selected"] if i == FS["sel_edge"] else COL["border"]
        for a, b in zip(pts, pts[1:-1]):
            dpg.draw_line(a, b, color=col, thickness=2, parent=D)
        dpg.draw_arrow(pts[-1], pts[-2], color=col, thickness=2, size=8,
                       parent=D)
        if e.get("condition"):
            mx = (pts[0][0] + pts[-1][0]) / 2
            my = (pts[0][1] + pts[-1][1]) / 2
            dpg.draw_text((mx + 4, my - 14), e["condition"], size=12,
                          color=STYLE.get("DIM"), parent=D)
    for sid, s in FS["syms"].items():
        if s.get("parent_scope") is not None:
            continue                        # pocket interiors: next leg
        _draw_symbol(s, sid == FS["sel"])


# ── tools + mouse ───────────────────────────────────────────────────────────
def set_tool(sender, app_data, tool):
    FS["tool"] = tool
    FS["edge_src"] = None
    names = {"select": "Select — click to select · drag to move · "
                       "dbl-click to rename",
             "delete": "Delete — click a symbol or edge to delete it",
             "edge": "Edge — click the SOURCE symbol"}
    label = names.get(tool, f"place {tool.split('_', 1)[-1]} — "
                            "click the canvas")
    dpg.set_value("flowc_tool", f"tool: {label}")


def _on_click(*_):
    if not dpg.is_item_hovered("flowc_draw"):
        return
    mx, my = dpg.get_drawing_mouse_pos()
    tool = FS["tool"]
    if tool.startswith("flow_"):
        add_symbol(tool, mx - SYMBOL_W / 2, my - SYMBOL_H / 2)
        FS["tool"] = "select"
        set_tool(None, None, "select")
        return
    if tool == "edge":
        sid = _hit_symbol(mx, my)
        if sid is None:
            FS["edge_src"] = None
            set_tool(None, None, "select")
            _status("edge cancelled")
            return
        if FS["edge_src"] is None:
            FS["edge_src"] = sid
            dpg.set_value("flowc_tool",
                          f"tool: Edge — {FS['syms'][sid]['label']} → "
                          "click the DESTINATION")
            return
        add_edge(FS["edge_src"], sid)
        FS["edge_src"] = None
        FS["tool"] = "select"
        set_tool(None, None, "select")
        return
    if tool == "delete":
        sid = _hit_symbol(mx, my)
        if sid is not None:
            delete_symbol(sid)
            return
        ei = _hit_edge(mx, my)
        if ei is not None:
            delete_edge(ei)
        return
    # select tool
    sid = _hit_symbol(mx, my)
    FS["sel"] = sid
    FS["sel_edge"] = None
    if sid is not None:
        s = FS["syms"][sid]
        _snapshot()
        FS["drag"] = {"orig": (s["x"], s["y"])}
        _selinfo(f"{s['label']}  {s['name']}  ({s['x']},{s['y']})")
    else:
        ei = _hit_edge(mx, my)
        FS["sel_edge"] = ei
        if ei is not None:
            e = FS["edges"][ei]
            _selinfo(f"Edge  {FS['syms'][e['src']]['label']} → "
                     f"{FS['syms'][e['dst']]['label']}  "
                     f"({len(e.get('waypoints', []))} waypoints)")
        else:
            _selinfo("")
    redraw()


def _on_drag(sender, app_data):
    if FS["drag"] is None or FS["sel"] is None:
        return
    _b, dx, dy = app_data
    s = FS["syms"].get(FS["sel"])
    if s is None:
        return
    ox, oy = FS["drag"]["orig"]
    s["x"], s["y"] = max(0, int(ox + dx)), max(0, int(oy + dy))
    redraw()


def _on_release(*_):
    if FS["drag"] is None:
        return
    FS["drag"] = None
    s = FS["syms"].get(FS["sel"])
    if s:
        s["x"], s["y"] = max(0, snap(s["x"])), max(0, snap(s["y"]))
        _selinfo(f"{s['label']}  {s['name']}  ({s['x']},{s['y']})")
        redraw()


def _on_dblclick(*_):
    if not dpg.is_item_hovered("flowc_draw"):
        return
    mx, my = dpg.get_drawing_mouse_pos()
    sid = _hit_symbol(mx, my)
    if sid is None:
        return
    FS["sel"] = sid
    redraw()
    tag = "flowc_rename"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    with dpg.window(label="Rename symbol", tag=tag, modal=True, width=360,
                    height=130, pos=(400, 260)):
        inp = dpg.add_input_text(default_value=FS["syms"][sid]["label"],
                                 width=-1)

        def apply():
            _snapshot()
            FS["syms"][sid]["label"] = dpg.get_value(inp).strip() \
                or FS["syms"][sid]["label"]
            dpg.delete_item(tag)
            redraw()
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Rename  ", callback=apply)
            dpg.add_button(label="Cancel",
                           callback=lambda: dpg.delete_item(tag))


def _on_del_key(*_):
    if dpg.is_item_hovered("flowc_wrap") or dpg.is_item_hovered("flowc_draw"):
        delete_selected()


# ── save / open (Tk schema; .fc sections preserved) ─────────────────────────
def _payload(path):
    ext = os.path.splitext(path)[1].lower()
    syms = []
    for sid, s in FS["syms"].items():
        merged = dict(FS["raw"].get(sid, {}))
        merged.update(s)
        syms.append(merged)
    doc = dict(FS["rawdoc"]) if FS["rawdoc"] else {
        "ternoo_version": "0.3", "source_type": "ternoo_design",
        "word_stream": [], "symbols": [], "edges": [],
        "cmd_symbols": [], "cmd_edges": [],
        "cell_symbols": [], "sheet_regions": [], "free_cells": [],
        "sequence": [],
    }
    doc["source_file"] = os.path.basename(path)
    doc["flow_symbols"] = syms
    doc["flow_edges"] = [dict(e) for e in FS["edges"]]
    if ext == ".flow":                      # flow-only partial, per policy
        doc["symbols"] = []
        doc["edges"] = []
        doc["cmd_symbols"] = doc["cmd_edges"] = []
        doc["cell_symbols"] = doc["sheet_regions"] = doc["free_cells"] = []
    meta = dict(doc.get("tgui_meta", {}))
    meta.update({"flow_symbol_count": len(syms),
                 "flow_edge_count": len(FS["edges"]),
                 "widget_count": len(doc.get("symbols", [])),
                 "edge_count": len(doc.get("edges", []))})
    doc["tgui_meta"] = meta
    return doc


def _picked(app_data):
    sels = app_data.get("selections") or {}
    if sels:
        return list(sels.values())[0]
    p = app_data.get("file_path_name", "")
    return p[:-2] if p.endswith(".*") else p


def save_to(path):
    if not path.endswith((".flow", ".fc")):
        path += ".flow"
    try:
        json.dump(_payload(path), open(path, "w", encoding="utf-8"),
                  indent=1)
        FS["file"] = path
        kept = " (other .fc sections preserved)" \
            if FS["rawdoc"] and path.endswith(".fc") else ""
        _status(f"saved {os.path.basename(path)} — {len(FS['syms'])} "
                f"symbols, {len(FS['edges'])} edges{kept}")
    except Exception as e:                      # noqa: BLE001
        _status(f"save failed: {e}", ok=False)


def load_from(path):
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as e:                      # noqa: BLE001
        _status(f"open failed: {e}", ok=False)
        return
    FS["rawdoc"] = doc
    FS["syms"].clear()
    FS["raw"].clear()
    FS["sel"] = FS["sel_edge"] = None
    FS["undo"].clear()
    FS["redo"].clear()
    for sym in doc.get("flow_symbols", []):
        sid = int(sym["id"])
        FS["syms"][sid] = {
            "id": sid, "kind": sym.get("kind", "flow_process"),
            "x": sym.get("x", 0), "y": sym.get("y", 0),
            "w": sym.get("w", SYMBOL_W), "h": sym.get("h", SYMBOL_H),
            "label": sym.get("label", ""),
            "name": sym.get("name", f"{sym.get('kind', 'flow')}_{sid}"),
            "parent_scope": sym.get("parent_scope"),
            "properties": list(sym.get("properties", [])),
        }
        FS["raw"][sid] = dict(sym)
        FS["next"] = max(FS["next"], sid + 1)
    FS["edges"] = [dict(e) for e in doc.get("flow_edges", [])]
    FS["file"] = path
    nested = sum(1 for s in FS["syms"].values()
                 if s.get("parent_scope") is not None)
    redraw()
    note = f" ({nested} in pocket scopes — preserved, shown next leg)" \
        if nested else ""
    _status(f"opened {os.path.basename(path)} — {len(FS['syms'])} symbols, "
            f"{len(FS['edges'])} edges{note}")


def _save_clicked(*_):
    if FS["file"]:
        save_to(FS["file"])
    else:
        dpg.show_item("flowc_save_dlg")


# ── build ───────────────────────────────────────────────────────────────────
def build_flow_tab(style):
    STYLE.update(style)
    C = STYLE
    with dpg.file_dialog(directory_selector=False, show=False,
                         tag="flowc_save_dlg", width=640, height=420,
                         default_path=os.path.expanduser("~"),
                         callback=lambda s, a: save_to(_picked(a))):
        dpg.add_file_extension(".flow")
        dpg.add_file_extension(".fc")
        dpg.add_file_extension(".*")
    with dpg.file_dialog(directory_selector=False, show=False,
                         tag="flowc_open_dlg", width=640, height=420,
                         default_path=os.path.expanduser("~"),
                         callback=lambda s, a: load_from(_picked(a))):
        dpg.add_file_extension(".fc")
        dpg.add_file_extension(".flow")
        dpg.add_file_extension(".*")

    with dpg.group(horizontal=True):
        with dpg.child_window(width=185):
            dpg.add_text("TOOLS", color=C["DIM"])
            dpg.add_button(label=" Select ", width=-1, user_data="select",
                           callback=set_tool)
            dpg.add_button(label=" Delete ", width=-1, user_data="delete",
                           callback=set_tool)
            dpg.add_spacer(height=6)
            dpg.add_text("SYMBOLS → UDP", color=C["DIM"])
            for kind, name, sub in KINDS:
                dpg.add_button(label=f" {name} ", width=-1, user_data=kind,
                               callback=set_tool)
                dpg.add_text("  " + sub, color=C["DIM"])
            dpg.add_spacer(height=6)
            dpg.add_text("CONNECT → EXEC", color=C["DIM"])
            dpg.add_button(label=" Edge ", width=-1, user_data="edge",
                           callback=set_tool)
            dpg.add_text("  src→[wp]→dst", color=C["DIM"])
            dpg.add_spacer(height=6)
            dpg.add_text("ACTIONS", color=C["DIM"])
            dpg.add_button(label=" Save ", width=-1, callback=_save_clicked)
            dpg.add_button(label=" Save as... ", width=-1,
                           callback=lambda: dpg.show_item("flowc_save_dlg"))
            dpg.add_button(label=" Open ", width=-1,
                           callback=lambda: dpg.show_item("flowc_open_dlg"))
            dpg.add_button(label=" Clear ", width=-1, callback=clear_all)
            dpg.add_button(label=" Undo ", width=-1, callback=undo)
            dpg.add_button(label=" Redo ", width=-1, callback=redo)
            dpg.add_spacer(height=8)
            dpg.add_text("not yet ported:\n Word Dump · Load→EMU\n "
                         "Step/Run/Stop · Import\n Learn · Suggest\n "
                         "waypoint editing\n pocket scopes · zoom",
                         color=C["DIM"])
        with dpg.child_window(tag="flowc_wrap", width=-1,
                              horizontal_scrollbar=True):
            dpg.add_text("MainFlow", color=(74, 158, 255))
            with dpg.drawlist(width=CANVAS_W, height=CANVAS_H,
                              tag="flowc_draw"):
                pass
    dpg.add_text("", tag="flowc_selinfo", color=(74, 158, 255))
    with dpg.group(horizontal=True):
        dpg.add_text("tool: Select — click to select · drag to move · "
                     "dbl-click to rename", tag="flowc_tool", color=C["DIM"])
        dpg.add_text("   Zoom: 100%", color=C["DIM"])
    dpg.add_text("Flow ready — reads/writes the Tk face's .fc/.flow",
                 tag="flowc_status", color=C["DIM"])

    with dpg.handler_registry():
        dpg.add_mouse_click_handler(dpg.mvMouseButton_Left,
                                    callback=_on_click)
        dpg.add_mouse_drag_handler(dpg.mvMouseButton_Left,
                                   callback=_on_drag)
        dpg.add_mouse_release_handler(dpg.mvMouseButton_Left,
                                      callback=_on_release)
        dpg.add_mouse_double_click_handler(dpg.mvMouseButton_Left,
                                           callback=_on_dblclick)
        dpg.add_key_press_handler(dpg.mvKey_Delete, callback=_on_del_key)
    redraw()
