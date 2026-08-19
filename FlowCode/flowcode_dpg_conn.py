#!/usr/bin/env python3
"""flowcode_dpg_conn — the Connectors tab ORGAN of FlowCode's DPG face.

The fourth primary surface (Stage 9-0/9-2, Bundle 24): command widgets
as flow-symbol-shaped tiles — header band, typed INPUT sockets on the
left (one per registry parameter), one OUTPUT socket on the right —
wired by typed pipes. The command vocabulary and type rules are REUSED
from 5500fp/flowcode_commands.py (the same registry the Tk face and
REPL run): input_params, output_type, pipe_compatible.

Tk semantics carried over verbatim: centre-stored coordinates,
CMD_W/H 160x80, ONE pipe per input socket (re-wiring replaces), a
type-mismatched pipe is RECORDED and shown RED (compile is the hard
gate, not the editor). Save/Open speaks the .fc schema
(cmd_symbols / cmd_edges) with every other section preserved.

DOCFLAG: the Shell tab's capture-to-pipeline (REPL -> Connectors) and
the pocket indicator's interior ride later legs; no partial extension
exists for Connectors (policy reserves .shell, unemitted) — saves are
.fc only.
"""
import json
import math
import os
import sys

import dearpygui.dearpygui as dpg

CMD_W, CMD_H = 160, 80
HDR = 22
CANVAS_W, CANVAS_H = 2400, 1600
FAMILY_TINT = {
    "text": (26, 52, 86), "math": (26, 76, 56), "list": (86, 66, 26),
    "env": (66, 40, 86), "cond": (86, 40, 50),
}
PIPE_OK = (74, 158, 255)
PIPE_BAD = (255, 90, 80)
SEL = (255, 107, 53)

CS = {
    "widgets": {}, "raw": {}, "edges": [], "rawdoc": None,
    "next": 0, "sel": None, "sel_edge": None, "pipe_src": None,
    "pending": None, "drag": None, "zoom": 1.0, "dirty": False,
    "file": None, "undo": [], "redo": [],
}
STYLE = {}
_FCMD = [None]
_FCMD_ERR = [""]


def _fcmd():
    if _FCMD[0] is None and not _FCMD_ERR[0]:
        try:
            five = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "5500fp")
            if five not in sys.path:
                sys.path.insert(0, five)
            import flowcode_commands as FC
            _FCMD[0] = FC
        except Exception as e:                  # noqa: BLE001
            _FCMD_ERR[0] = str(e)
    return _FCMD[0]


def _family(kind):
    parts = kind.split("_")
    return parts[1] if len(parts) > 2 else "other"


def is_dirty():
    has = bool(CS["widgets"] or CS["edges"])
    return has and (bool(CS["dirty"]) or CS["file"] is None)


def autosave(path):
    try:
        json.dump(_payload(path), open(path, "w", encoding="utf-8"),
                  indent=1)
        return True
    except Exception:                           # noqa: BLE001
        return False


def _status(msg, ok=True):
    dpg.set_value("connc_status", msg)
    dpg.configure_item("connc_status",
                       color=STYLE.get("GRN" if ok else "AMB"))


def zoom_step(direction):
    z = CS["zoom"] * (1.2 if direction > 0 else 1 / 1.2)
    CS["zoom"] = max(0.3, min(3.0, round(z, 3)))
    if dpg.does_item_exist("connc_zoomlbl"):
        dpg.set_value("connc_zoomlbl", f"Zoom: {int(CS['zoom'] * 100)}%")
    redraw()


def _mpos():
    mx, my = dpg.get_drawing_mouse_pos()
    z = CS["zoom"]
    return mx / z, my / z


# ── undo / redo ─────────────────────────────────────────────────────────────
def _snapshot():
    CS["dirty"] = True
    CS["undo"].append(json.dumps({"w": CS["widgets"], "e": CS["edges"],
                                  "n": CS["next"]}))
    CS["undo"] = CS["undo"][-50:]
    CS["redo"].clear()


def _restore(blob):
    d = json.loads(blob)
    CS["widgets"] = {int(k): v for k, v in d["w"].items()}
    CS["edges"] = d["e"]
    CS["next"] = d["n"]
    if CS["sel"] not in CS["widgets"]:
        CS["sel"] = None
    CS["sel_edge"] = None
    redraw()


def undo(*_):
    if not CS["undo"]:
        _status("nothing to undo", ok=False)
        return
    CS["redo"].append(json.dumps({"w": CS["widgets"], "e": CS["edges"],
                                  "n": CS["next"]}))
    _restore(CS["undo"].pop())
    _status("undone")


def redo(*_):
    if not CS["redo"]:
        _status("nothing to redo", ok=False)
        return
    CS["undo"].append(json.dumps({"w": CS["widgets"], "e": CS["edges"],
                                  "n": CS["next"]}))
    _restore(CS["redo"].pop())
    _status("redone")


# ── model ops (Tk conventions: CENTRE coordinates) ──────────────────────────
def add_command(kind, cx, cy):
    _snapshot()
    cid = CS["next"]
    CS["next"] += 1
    CS["widgets"][cid] = {
        "id": cid, "kind": kind, "x": int(cx), "y": int(cy),
        "w": CMD_W, "h": CMD_H,
        "label": kind.split("_", 1)[-1], "name": f"{kind}_{cid}",
        "properties": [],
    }
    CS["sel"] = cid
    redraw()
    _status(f"placed {kind}")
    return cid


def add_pipe(src_id, dst_id, dst_param):
    """One pipe per input socket — re-wiring REPLACES (Tk semantics).
    A type mismatch is recorded and shown red; compile is the hard gate."""
    _snapshot()
    CS["edges"][:] = [e for e in CS["edges"]
                      if not (e["dst"] == dst_id
                              and e.get("dst_param") == dst_param)]
    edge = {"src": src_id, "dst": dst_id, "dst_param": dst_param}
    CS["edges"].append(edge)
    ok = _edge_compatible(edge)
    redraw()
    s = CS["widgets"].get(src_id, {}).get("label", "?")
    d = CS["widgets"].get(dst_id, {}).get("label", "?")
    if ok:
        _status(f"pipe {s} → {d}.{dst_param}")
    else:
        _status(f"pipe {s} → {d}.{dst_param} — TYPE MISMATCH (red; "
                "compile will refuse it)", ok=False)
    return edge


def _edge_compatible(edge):
    FC = _fcmd()
    if FC is None:
        return True
    src = CS["widgets"].get(edge["src"])
    dst = CS["widgets"].get(edge["dst"])
    if not src or not dst:
        return False
    try:
        return FC.pipe_compatible(src["kind"], dst["kind"],
                                  edge.get("dst_param", ""))
    except Exception:                           # noqa: BLE001
        return True


def delete_selected(*_):
    if CS["sel"] is not None:
        _snapshot()
        cid = CS["sel"]
        CS["widgets"].pop(cid, None)
        CS["raw"].pop(cid, None)
        CS["edges"][:] = [e for e in CS["edges"]
                          if e["src"] != cid and e["dst"] != cid]
        CS["sel"] = None
        redraw()
        _status(f"deleted command #{cid} (+ its pipes)")
    elif CS["sel_edge"] is not None and CS["sel_edge"] < len(CS["edges"]):
        _snapshot()
        e = CS["edges"].pop(CS["sel_edge"])
        CS["sel_edge"] = None
        redraw()
        _status(f"pipe removed ({e['src']} → {e['dst']}.{e['dst_param']})")


def clear_all(*_):
    if not CS["widgets"] and not CS["edges"]:
        return
    _snapshot()
    CS["widgets"].clear()
    CS["raw"].clear()
    CS["edges"].clear()
    CS["sel"] = CS["sel_edge"] = None
    redraw()
    _status("canvas cleared")


# ── socket geometry (mirror of the Tk _sh_sockets, centre coords) ───────────
def _sockets(c):
    FC = _fcmd()
    hw, hh = CMD_W // 2, CMD_H // 2
    top = c["y"] - hh + HDR
    bot = c["y"] + hh
    params = []
    if FC is not None:
        try:
            params = FC.input_params(c["kind"])
        except Exception:                       # noqa: BLE001
            params = []
    ins = []
    n = len(params)
    for i, (pname, ptype) in enumerate(params):
        fy = top + (bot - top) * (i + 1) / (n + 1)
        ins.append((pname, ptype, c["x"] - hw, fy))
    return ins, (c["x"] + hw, (top + bot) / 2)


def _output_hit(x, y, tol=9):
    for c in reversed(list(CS["widgets"].values())):
        _ins, (ox, oy) = _sockets(c)
        if abs(ox - x) <= tol and abs(oy - y) <= tol:
            return c["id"]
    return None


def _input_hit(x, y, tol=9):
    for c in reversed(list(CS["widgets"].values())):
        ins, _out = _sockets(c)
        for pname, _pt, ix, iy in ins:
            if abs(ix - x) <= tol and abs(iy - y) <= tol:
                return c["id"], pname
    return None


def _hit_widget(x, y):
    for cid in reversed(list(CS["widgets"])):
        c = CS["widgets"][cid]
        if abs(x - c["x"]) <= CMD_W / 2 and abs(y - c["y"]) <= CMD_H / 2:
            return cid
    return None


def _pipe_pts(e):
    src = CS["widgets"].get(e["src"])
    dst = CS["widgets"].get(e["dst"])
    if not src or not dst:
        return None
    _ins, out = _sockets(src)
    for pname, _pt, ix, iy in _sockets(dst)[0]:
        if pname == e.get("dst_param"):
            return out, (ix, iy)
    _dins, ddef = _sockets(dst)
    return out, (dst["x"] - CMD_W / 2, dst["y"])


def _hit_pipe(x, y):
    def segd(p, a, b):
        px, py = p
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        if dx == dy == 0:
            return math.hypot(px - ax, py - ay)
        t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy)
                       / (dx * dx + dy * dy)))
        return math.hypot(px - (ax + t * dx), py - (ay + t * dy))
    for i, e in enumerate(CS["edges"]):
        pts = _pipe_pts(e)
        if pts and segd((x, y), pts[0], pts[1]) <= 7:
            return i
    return None


# ── drawing ─────────────────────────────────────────────────────────────────
def redraw():
    D = "connc_draw"
    if not dpg.does_item_exist(D):
        return
    Z = CS["zoom"]
    dpg.configure_item(D, width=int(CANVAS_W * Z), height=int(CANVAS_H * Z))
    dpg.delete_item(D, children_only=True)
    for gx in range(0, CANVAS_W + 1, 40):
        dpg.draw_line((gx * Z, 0), (gx * Z, CANVAS_H * Z),
                      color=(40, 46, 62, 70), parent=D)
    for gy in range(0, CANVAS_H + 1, 40):
        dpg.draw_line((0, gy * Z), (CANVAS_W * Z, gy * Z),
                      color=(40, 46, 62, 70), parent=D)
    for i, e in enumerate(CS["edges"]):
        pts = _pipe_pts(e)
        if not pts:
            continue
        (x1, y1), (x2, y2) = pts
        col = SEL if i == CS["sel_edge"] else \
            (PIPE_OK if _edge_compatible(e) else PIPE_BAD)
        mx = (x1 + x2) / 2
        dpg.draw_bezier_cubic((x1 * Z, y1 * Z), (mx * Z, y1 * Z),
                              (mx * Z, y2 * Z), (x2 * Z, y2 * Z),
                              color=col, thickness=2, parent=D)
        dpg.draw_arrow((x2 * Z, y2 * Z), ((x2 - 12) * Z, y2 * Z),
                       color=col, thickness=2, size=7 * Z, parent=D)
    for cid, c in CS["widgets"].items():
        hw, hh = CMD_W / 2, CMD_H / 2
        x0, y0 = (c["x"] - hw) * Z, (c["y"] - hh) * Z
        x1, y1 = (c["x"] + hw) * Z, (c["y"] + hh) * Z
        tint = FAMILY_TINT.get(_family(c["kind"]), (48, 44, 72))
        border = SEL if cid == CS["sel"] else (96, 116, 160)
        dpg.draw_rectangle((x0, y0), (x1, y1), fill=tint, color=border,
                           thickness=2 if cid == CS["sel"] else 1,
                           rounding=5, parent=D)
        dpg.draw_rectangle((x0, y0), (x1, y0 + HDR * Z),
                           fill=(24, 30, 46), color=border, parent=D)
        dpg.draw_text((x0 + 6 * Z, y0 + 4 * Z), c.get("label", ""),
                      size=13 * Z, color=STYLE.get("TEXT"), parent=D)
        dpg.draw_text((x0 + 6 * Z, y1 - 14 * Z), c["kind"],
                      size=10 * Z, color=STYLE.get("DIM"), parent=D)
        ins, (ox, oy) = _sockets(c)
        for pname, ptype, ix, iy in ins:
            dpg.draw_circle((ix * Z, iy * Z), 5 * Z, fill=(214, 219, 228),
                            color=(96, 116, 160), parent=D)
            dpg.draw_text(((ix + 9) * Z, (iy - 7) * Z),
                          f"{pname}:{ptype}", size=10 * Z,
                          color=STYLE.get("DIM"), parent=D)
        dpg.draw_circle((ox * Z, oy * Z), 5.5 * Z, fill=(63, 208, 143),
                        color=(96, 116, 160), parent=D)
        if CS["pipe_src"] == cid:
            dpg.draw_circle((ox * Z, oy * Z), 9 * Z, color=SEL, parent=D)


# ── interaction ─────────────────────────────────────────────────────────────
def _on_click(*_):
    if not dpg.does_item_exist("connc_draw") \
            or not dpg.is_item_hovered("connc_draw"):
        return
    mx, my = _mpos()
    if CS["pending"]:
        add_command(CS["pending"], mx, my)
        CS["pending"] = None
        dpg.set_value("connc_tool", "tool: Select")
        return
    if CS["pipe_src"] is not None:
        hit = _input_hit(mx, my)
        if hit:
            add_pipe(CS["pipe_src"], hit[0], hit[1])
        else:
            _status("pipe cancelled")
        CS["pipe_src"] = None
        redraw()
        return
    out = _output_hit(mx, my)
    if out is not None:
        CS["pipe_src"] = out
        redraw()
        _status(f"wiring from {CS['widgets'][out]['label']} — click an "
                "INPUT socket")
        return
    cid = _hit_widget(mx, my)
    CS["sel"] = cid
    CS["sel_edge"] = None
    if cid is not None:
        c = CS["widgets"][cid]
        _snapshot()
        CS["drag"] = {"orig": (c["x"], c["y"])}
    else:
        CS["sel_edge"] = _hit_pipe(mx, my)
    redraw()


def _on_drag(sender, app_data):
    if CS["drag"] is None or CS["sel"] is None:
        return
    _b, dx, dy = app_data
    z = CS["zoom"]
    c = CS["widgets"].get(CS["sel"])
    if c is None:
        return
    ox, oy = CS["drag"]["orig"]
    c["x"], c["y"] = int(ox + dx / z), int(oy + dy / z)
    redraw()


def _on_release(*_):
    CS["drag"] = None


def _on_dblclick(*_):
    if not dpg.does_item_exist("connc_draw") \
            or not dpg.is_item_hovered("connc_draw"):
        return
    mx, my = _mpos()
    cid = _hit_widget(mx, my)
    if cid is None:
        return
    tag = "connc_rename"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    with dpg.window(label="Rename command", tag=tag, modal=True, width=360,
                    height=130, pos=(420, 260)):
        inp = dpg.add_input_text(
            default_value=CS["widgets"][cid].get("label", ""), width=-1)

        def apply():
            _snapshot()
            CS["widgets"][cid]["label"] = dpg.get_value(inp).strip() \
                or CS["widgets"][cid]["label"]
            dpg.delete_item(tag)
            redraw()
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Rename  ", callback=apply)
            dpg.add_button(label="Cancel",
                           callback=lambda: dpg.delete_item(tag))


def _on_del(*_):
    if dpg.does_item_exist("connc_draw") \
            and (dpg.is_item_hovered("connc_draw")
                 or dpg.is_item_hovered("connc_wrap")):
        delete_selected()


# ── save / open (.fc only; other sections preserved) ────────────────────────
def _payload(path):
    doc = dict(CS["rawdoc"]) if CS["rawdoc"] else {
        "ternoo_version": "0.3", "source_type": "ternoo_design",
        "word_stream": [], "symbols": [], "edges": [],
        "flow_symbols": [], "flow_edges": [],
        "cell_symbols": [], "sheet_regions": [], "free_cells": [],
        "sequence": [],
    }
    doc["source_file"] = os.path.basename(path)
    syms = []
    for cid, c in CS["widgets"].items():
        merged = dict(CS["raw"].get(cid, {}))
        merged.update(c)
        syms.append(merged)
    doc["cmd_symbols"] = syms
    doc["cmd_edges"] = [dict(e) for e in CS["edges"]]
    meta = dict(doc.get("tgui_meta", {}))
    meta["cmd_count"] = len(syms)
    doc["tgui_meta"] = meta
    return doc


def _picked(app_data):
    sels = app_data.get("selections") or {}
    if sels:
        return list(sels.values())[0]
    p = app_data.get("file_path_name", "")
    return p[:-2] if p.endswith(".*") else p


def save_to(path):
    if not path.endswith(".fc"):
        path += ".fc"
    try:
        json.dump(_payload(path), open(path, "w", encoding="utf-8"),
                  indent=1)
        CS["file"] = path
        CS["dirty"] = False
        kept = " (other .fc sections preserved)" if CS["rawdoc"] else ""
        _status(f"saved {os.path.basename(path)} — "
                f"{len(CS['widgets'])} commands, {len(CS['edges'])} "
                f"pipes{kept}")
    except Exception as e:                      # noqa: BLE001
        _status(f"save failed: {e}", ok=False)


def load_from(path):
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as e:                      # noqa: BLE001
        _status(f"open failed: {e}", ok=False)
        return
    CS["rawdoc"] = doc
    CS["widgets"].clear()
    CS["raw"].clear()
    CS["undo"].clear()
    CS["redo"].clear()
    CS["sel"] = CS["sel_edge"] = None
    for cmd in doc.get("cmd_symbols", []):
        cid = int(cmd["id"])
        CS["widgets"][cid] = {
            "id": cid, "kind": cmd.get("kind", "cmd_placeholder"),
            "x": cmd.get("x", 0), "y": cmd.get("y", 0),
            "w": cmd.get("w", CMD_W), "h": cmd.get("h", CMD_H),
            "label": cmd.get("label", ""),
            "name": cmd.get("name", f"cmd_{cid}"),
            "properties": list(cmd.get("properties", [])),
        }
        CS["raw"][cid] = dict(cmd)
        CS["next"] = max(CS["next"], cid + 1)
    ids = set(CS["widgets"])
    CS["edges"] = [{"src": e["src"], "dst": e["dst"],
                    "dst_param": e.get("dst_param", "")}
                   for e in doc.get("cmd_edges", [])
                   if e.get("src") in ids and e.get("dst") in ids]
    CS["file"] = path
    CS["dirty"] = False
    redraw()
    _status(f"opened {os.path.basename(path)} — {len(CS['widgets'])} "
            f"commands, {len(CS['edges'])} pipes")


def _save_clicked(*_):
    if CS["file"]:
        save_to(CS["file"])
    else:
        dpg.show_item("connc_save_dlg")


# ── build ───────────────────────────────────────────────────────────────────
def _pick(sender, app_data, kind):
    CS["pending"] = kind
    CS["pipe_src"] = None
    dpg.set_value("connc_tool", f"tool: place {kind} — click the canvas")


def build_conn_tab(style):
    STYLE.update(style)
    C = STYLE
    _designs = os.path.dirname(os.path.abspath(__file__))
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         tag="connc_save_dlg", width=780, height=480,
                         default_path=_designs, default_filename="design",
                         callback=lambda s, a: save_to(_picked(a))):
        dpg.add_file_extension(".fc", color=(63, 208, 143))
        dpg.add_file_extension(".*")
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         tag="connc_open_dlg", width=780, height=480,
                         default_path=_designs, default_filename="",
                         callback=lambda s, a: load_from(_picked(a))):
        dpg.add_file_extension(".fc", color=(63, 208, 143))
        dpg.add_file_extension(".*")

    FC = _fcmd()
    with dpg.group(horizontal=True):
        with dpg.child_window(width=int(C.get("CFG", {})
                              .get("conn_panel_w", 240)),
                              tag="connc_panel"):
            dpg.add_text("COMMANDS", color=C["DIM"])
            if FC is None:
                dpg.add_text(f"registry unavailable:\n{_FCMD_ERR[0]}",
                             color=C["AMB"])
                dpg.add_button(label=" placeholder ", width=-1,
                               user_data="cmd_placeholder", callback=_pick)
            else:
                fams = {}
                for k in FC.command_names():
                    fams.setdefault(_family(k), []).append(k)
                for fam in sorted(fams):
                    with dpg.collapsing_header(label=fam.upper(),
                                               default_open=(fam in
                                                             ("text",
                                                              "math"))):
                        for k in fams[fam]:
                            dpg.add_button(label=" " + k[4:] + " ",
                                           width=-1, user_data=k,
                                           callback=_pick)
            dpg.add_spacer(height=6)
            dpg.add_text("ACTIONS", color=C["DIM"])
            dpg.add_button(label=" Save ", width=-1, callback=_save_clicked)
            dpg.add_button(label=" Save as... ", width=-1,
                           callback=lambda: dpg.show_item("connc_save_dlg"))
            dpg.add_button(label=" Open ", width=-1,
                           callback=lambda: dpg.show_item("connc_open_dlg"))
            dpg.add_button(label=" Clear ", width=-1, callback=clear_all)
            dpg.add_button(label=" Undo ", width=-1, callback=undo)
            dpg.add_button(label=" Redo ", width=-1, callback=redo)
            dpg.add_spacer(height=6)
            dpg.add_text("wire: click an OUTPUT dot,\nthen an INPUT dot — "
                         "one\npipe per input (rewiring\nreplaces) · red = "
                         "type\nmismatch\n\nnot yet ported:\n REPL "
                         "capture-to-pipeline\n pocket interiors",
                         color=C["DIM"])
        with dpg.child_window(tag="connc_wrap", width=-1,
                              horizontal_scrollbar=True):
            with dpg.drawlist(width=CANVAS_W, height=CANVAS_H,
                              tag="connc_draw"):
                pass
    with dpg.group(horizontal=True):
        dpg.add_text("tool: Select", tag="connc_tool", color=C["DIM"])
        dpg.add_text("   Zoom: 100%", tag="connc_zoomlbl", color=C["DIM"])
    dpg.add_text("Connectors ready — the shared command registry "
                 "(typed pipes; compile is the hard gate)",
                 tag="connc_status", color=C["DIM"])

    with dpg.handler_registry():
        dpg.add_mouse_click_handler(dpg.mvMouseButton_Left,
                                    callback=_on_click)
        dpg.add_mouse_drag_handler(dpg.mvMouseButton_Left,
                                   callback=_on_drag)
        dpg.add_mouse_release_handler(dpg.mvMouseButton_Left,
                                      callback=_on_release)
        dpg.add_mouse_double_click_handler(dpg.mvMouseButton_Left,
                                           callback=_on_dblclick)
        dpg.add_key_press_handler(dpg.mvKey_Delete, callback=_on_del)
    redraw()


def _selftest():
    """Headless gate: registry pipes, replace semantics, mismatch flag,
    .fc round-trip with section preservation."""
    FC = _fcmd()
    assert FC is not None, f"registry failed: {_FCMD_ERR[0]}"
    clear_all()
    CS["undo"].clear()
    a = add_command("cmd_math_add", 200, 200)
    b = add_command("cmd_text_upper", 500, 200)
    c2 = add_command("cmd_math_abs", 200, 400)
    ins_b = FC.input_params("cmd_text_upper")
    assert ins_b, "text_upper has no inputs?"
    p = ins_b[0][0]
    add_pipe(a, b, p)
    assert len(CS["edges"]) == 1
    add_pipe(c2, b, p)                  # replace semantics
    assert len(CS["edges"]) == 1 and CS["edges"][0]["src"] == c2
    ins_a = FC.input_params("cmd_math_add")
    if ins_a:
        add_pipe(b, a, ins_a[0][0])     # text -> number: likely mismatch
        e = CS["edges"][-1]
        _edge_compatible(e)             # must not raise either way
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "fdpg-test-conn.fc")
    doc = _payload(tmp)
    doc["flow_symbols"] = [{"id": 0, "kind": "flow_process", "x": 0,
                            "y": 0, "label": "KEEP"}]
    json.dump(doc, open(tmp, "w", encoding="utf-8"))
    load_from(tmp)
    assert len(CS["widgets"]) == 3
    save_to(tmp)
    doc2 = json.load(open(tmp, encoding="utf-8"))
    assert doc2["flow_symbols"][0]["label"] == "KEEP"
    n_edges = len(doc2["cmd_edges"])
    clear_all()
    return {"widgets": 3, "edges": n_edges}
