#!/usr/bin/env python3
"""flowcode_dpg_sheet — the Sheet tab ORGAN of FlowCode's Dear PyGui face.

The third leg of the trinity (Stage 8): cells as first-class content,
hybrid formula evaluation, name-based binding, grid-primary UX — per
docs/design/CAI-Sheet-Leg-Design-Memo.md.

The evaluator is REUSED, not copied: 5500fp/sheet_formula.py (A1 refs,
named refs, ranges, WIDGET(...)/SIGNAL_LAST(...) context) — the same
module the Tk face runs. Cell model mirrors the Tk fc_state shape
verbatim: kind auto-detected (= → cell_formula, number/bool →
cell_value, else cell_text), '_result'/'_error' stamped by recalc,
number formats (fmt_decimals / fmt_currency / fmt_percent).

Save/Open speaks the Tk .fc schema (cell_symbols / sheet_regions /
free_cells); on .fc files every other section is PRESERVED verbatim;
.sheet saves a sheet-only partial per the extensions policy.

DOCFLAG: regions + free cells are RENDERED and PRESERVED but not yet
creatable/editable here; no canvas zoom yet. They ride later legs.
"""
import json
import os
import sys

import dearpygui.dearpygui as dpg

CELL_W, CELL_H = 96, 24
HDR_W, HDR_H = 46, 22
COLS, ROWS = 26, 60
GRID_COL = (52, 60, 82)
HDR_BG = (33, 40, 58)
SEL_COL = (255, 107, 53)
FORMULA_COL = (150, 200, 255)
ERR_COL = (255, 120, 90)

SS = {
    "cells": {},      # (row, col) -> Tk-shape cell dict
    "regions": {},    # id -> region dict (rendered + preserved)
    "free": {},       # id -> free cell (rendered + preserved)
    "next": 0,
    "sel": (0, 0),
    "file": None, "rawdoc": None, "dirty": False,
    "undo": [], "redo": [],
}
STYLE = {}
_SF = [None]
_SF_ERR = [""]


def _sf():
    if _SF[0] is None and not _SF_ERR[0]:
        try:
            five = os.path.join(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__))), "5500fp")
            if five not in sys.path:
                sys.path.insert(0, five)
            import sheet_formula as SF
            _SF[0] = SF
        except Exception as e:                  # noqa: BLE001
            _SF_ERR[0] = str(e)
    return _SF[0]


def is_dirty():
    has = bool(SS["cells"] or SS["regions"] or SS["free"])
    return has and (bool(SS["dirty"]) or SS["file"] is None)


def autosave(path):
    try:
        json.dump(_payload(path), open(path, "w", encoding="utf-8"),
                  indent=1)
        return True
    except Exception:                           # noqa: BLE001
        return False


def _status(msg, ok=True):
    dpg.set_value("shc_status", msg)
    dpg.configure_item("shc_status",
                       color=STYLE.get("GRN" if ok else "AMB"))


def _a1(row, col):
    SF = _sf()
    if SF:
        return SF.rc_to_a1(row, col)
    return f"{chr(65 + col)}{row + 1}"


# ── undo / redo (cells serialized as lists — tuple keys aren't JSON) ────────
def _dump_state():
    return json.dumps({"c": list(SS["cells"].values()),
                       "r": list(SS["regions"].values()),
                       "f": list(SS["free"].values()),
                       "n": SS["next"]})


def _load_state(blob):
    d = json.loads(blob)
    SS["cells"] = {(c["row"], c["col"]): c for c in d["c"]}
    SS["regions"] = {r["id"]: r for r in d["r"]}
    SS["free"] = {f["id"]: f for f in d["f"]}
    SS["next"] = d["n"]


def _snapshot():
    SS["dirty"] = True
    SS["undo"].append(_dump_state())
    SS["undo"] = SS["undo"][-50:]
    SS["redo"].clear()


def undo(*_):
    if not SS["undo"]:
        _status("nothing to undo", ok=False)
        return
    SS["redo"].append(_dump_state())
    _load_state(SS["undo"].pop())
    recalc()
    _status("undone")


def redo(*_):
    if not SS["redo"]:
        _status("nothing to redo", ok=False)
        return
    SS["undo"].append(_dump_state())
    _load_state(SS["redo"].pop())
    recalc()
    _status("redone")


# ── the cell model (Tk conventions verbatim) ────────────────────────────────
def _detect_kind(text):
    t = text.strip()
    if t.startswith("="):
        return "cell_formula"
    try:
        int(t)
        return "cell_value"
    except ValueError:
        pass
    try:
        float(t)
        return "cell_value"
    except ValueError:
        pass
    if t.lower() in ("true", "false"):
        return "cell_value"
    return "cell_text"


def _fmt_number(cell, text):
    try:
        v = float(text)
    except (ValueError, TypeError):
        return text
    if cell.get("fmt_percent"):
        v *= 100.0
    dec = cell.get("fmt_decimals")
    s = (f"{v:.{int(dec)}f}" if dec not in (None, "") else
         (f"{int(v)}" if v == int(v) else f"{v:g}"))
    if cell.get("fmt_currency"):
        s = "$" + s
    if cell.get("fmt_percent"):
        s = s + "%"
    return s


def _display(cell):
    if cell.get("kind") == "cell_formula":
        if "_error" in cell:
            return cell["_error"]
        if "_result" in cell:
            return _fmt_number(cell, cell["_result"])
        return str(cell.get("value", ""))
    if cell.get("kind") == "cell_value":
        return _fmt_number(cell, str(cell.get("value", "")))
    return str(cell.get("value", ""))


def set_cell(row, col, text, name=None):
    """Commit text into (row, col) — Tk auto-detect semantics."""
    _snapshot()
    text = text if text is not None else ""
    if text.strip() == "" and not name:
        SS["cells"].pop((row, col), None)
    else:
        cell = SS["cells"].get((row, col))
        if cell is None:
            cell = {"id": SS["next"], "row": row, "col": col,
                    "label": _a1(row, col), "properties": []}
            SS["next"] += 1
            SS["cells"][(row, col)] = cell
        cell["kind"] = _detect_kind(text)
        cell["value"] = text.strip()
        if name is not None:
            if name.strip():
                cell["name"] = name.strip()
            else:
                cell.pop("name", None)
    recalc()


def recalc():
    """Evaluate every formula cell via the shared evaluator; stamp
    _result/_error; GUI widgets bound by name read fresh values."""
    SF = _sf()
    if SF is None:
        _status(f"formula engine unavailable: {_SF_ERR[0]}", ok=False)
        redraw()
        return

    GUI = STYLE.get("GUI")

    def widget_prop(name, prop):
        if GUI is None:
            return None
        for w in GUI.GS["widgets"].values():
            if w.get("name") == name:
                if prop in ("name", "x", "y", "w", "h", "label",
                            "layout_mode"):
                    return w.get(prop)
                return GUI._prop_get(w, prop, None)
        return None

    ctx = {"widget_prop": widget_prop, "signal_last": lambda nm: 0}
    try:
        results, errors = SF.evaluate_sheet(SS["cells"], ctx)
    except Exception as e:                      # noqa: BLE001
        _status(f"recalc failed: {e}", ok=False)
        redraw()
        return
    for rc, cell in SS["cells"].items():
        cell.pop("_result", None)
        cell.pop("_error", None)
        if cell.get("kind") == "cell_formula":
            if rc in errors:
                cell["_error"] = str(errors[rc])
            elif rc in results:
                cell["_result"] = SF.format_result(results[rc])
    if errors:
        _status(f"{len(errors)} formula error(s): " + ", ".join(
            f"{_a1(*rc)} {e}" for rc, e in list(errors.items())[:3]),
            ok=False)
    else:
        _status(f"{len(SS['cells'])} cells — recalc clean")
    redraw()
    try:
        if GUI is not None:
            GUI.redraw()          # bound widgets may display cell values
    except Exception:                           # noqa: BLE001
        pass


def clear_all(*_):
    if not SS["cells"] and not SS["regions"] and not SS["free"]:
        return
    _snapshot()
    SS["cells"].clear()
    SS["regions"].clear()
    SS["free"].clear()
    redraw()
    _status("sheet cleared")


# ── drawing ─────────────────────────────────────────────────────────────────
def redraw():
    D = "shc_draw"
    if not dpg.does_item_exist(D):
        return
    dpg.delete_item(D, children_only=True)
    SF = _sf()
    W = HDR_W + COLS * CELL_W
    H = HDR_H + ROWS * CELL_H
    dpg.draw_rectangle((0, 0), (W, HDR_H), fill=HDR_BG, parent=D)
    dpg.draw_rectangle((0, 0), (HDR_W, H), fill=HDR_BG, parent=D)
    for c in range(COLS):
        cx = HDR_W + c * CELL_W
        lbl = SF.index_to_col(c) if SF else chr(65 + c)
        dpg.draw_text((cx + CELL_W / 2 - 4 * len(lbl), 4), lbl,
                      color=STYLE.get("DIM"), size=13, parent=D)
        dpg.draw_line((cx, 0), (cx, H), color=GRID_COL, parent=D)
    for r in range(ROWS):
        ry = HDR_H + r * CELL_H
        dpg.draw_text((6, ry + 4), str(r + 1), color=STYLE.get("DIM"),
                      size=12, parent=D)
        dpg.draw_line((0, ry), (W, ry), color=GRID_COL, parent=D)
    for reg in SS["regions"].values():          # rendered + preserved
        rx, ryy = reg.get("x", 0), reg.get("y", 0)
        dpg.draw_rectangle((rx, ryy),
                           (rx + reg.get("w", 120), ryy + reg.get("h", 80)),
                           color=(74, 158, 255), thickness=1,
                           fill=(74, 158, 255, 18), parent=D)
        dpg.draw_text((rx + 4, ryy + 2), reg.get("label", reg.get("name", "")),
                      color=(74, 158, 255), size=12, parent=D)
    for fc in SS["free"].values():
        fx, fy = fc.get("px", 0), fc.get("py", 0)
        dpg.draw_rectangle((fx, fy), (fx + 80, fy + 20),
                           fill=(44, 52, 72), color=(74, 158, 255),
                           rounding=4, parent=D)
        dpg.draw_text((fx + 5, fy + 3), str(fc.get("value", "")),
                      color=STYLE.get("TEXT"), size=12, parent=D)
    for (r, c), cell in SS["cells"].items():
        if r >= ROWS or c >= COLS:
            continue
        cx = HDR_W + c * CELL_W
        ry = HDR_H + r * CELL_H
        txt = _display(cell)
        col = (ERR_COL if "_error" in cell else
               FORMULA_COL if cell.get("kind") == "cell_formula" else
               STYLE.get("TEXT"))
        dpg.draw_text((cx + 4, ry + 4), str(txt)[:14], color=col, size=13,
                      parent=D)
        if cell.get("name"):
            dpg.draw_circle((cx + CELL_W - 6, ry + 6), 2.5,
                            fill=(63, 208, 143), parent=D)
    if SS["sel"] is not None:
        r, c = SS["sel"]
        cx = HDR_W + c * CELL_W
        ry = HDR_H + r * CELL_H
        dpg.draw_rectangle((cx, ry), (cx + CELL_W, ry + CELL_H),
                           color=SEL_COL, thickness=2, parent=D)


def _sync_bar():
    r, c = SS["sel"]
    cell = SS["cells"].get((r, c), {})
    dpg.set_value("shc_addr", _a1(r, c))
    dpg.set_value("shc_input", str(cell.get("value", "")))
    dpg.set_value("shc_name", str(cell.get("name", "")))
    k = cell.get("kind", "")
    shown = _display(cell) if cell else ""
    dpg.set_value("shc_kind", f"{k or 'empty'}"
                  + (f"  →  {shown}" if k == "cell_formula" else ""))


# ── interaction ─────────────────────────────────────────────────────────────
def _on_click(*_):
    if not dpg.does_item_exist("shc_draw") \
            or not dpg.is_item_hovered("shc_draw"):
        return
    mx, my = dpg.get_drawing_mouse_pos()
    if mx < HDR_W or my < HDR_H:
        return
    c = int((mx - HDR_W) // CELL_W)
    r = int((my - HDR_H) // CELL_H)
    if 0 <= r < ROWS and 0 <= c < COLS:
        SS["sel"] = (r, c)
        _sync_bar()
        redraw()


def _apply(*_):
    r, c = SS["sel"]
    set_cell(r, c, dpg.get_value("shc_input"), dpg.get_value("shc_name"))
    _sync_bar()


def _apply_and_down(*_):
    _apply()
    r, c = SS["sel"]
    SS["sel"] = (min(ROWS - 1, r + 1), c)
    _sync_bar()
    redraw()


def _del_cell(*_):
    if dpg.does_item_exist("shc_draw") \
            and (dpg.is_item_hovered("shc_draw")
                 or dpg.is_item_hovered("shc_wrap")):
        r, c = SS["sel"]
        if (r, c) in SS["cells"]:
            set_cell(r, c, "")
            _sync_bar()


def _fmt(field, delta=None):
    r, c = SS["sel"]
    cell = SS["cells"].get((r, c))
    if cell is None:
        _status("select a non-empty cell first", ok=False)
        return
    _snapshot()
    if field == "currency":
        cell["fmt_currency"] = not cell.get("fmt_currency")
    elif field == "percent":
        cell["fmt_percent"] = not cell.get("fmt_percent")
    elif field == "dec":
        cur = cell.get("fmt_decimals")
        cur = 0 if cur in (None, "") else int(cur)
        cell["fmt_decimals"] = max(0, cur + delta)
    recalc()


# ── save / open (Tk schema; .fc sections preserved; .sheet partial) ─────────
def _payload(path):
    ext = os.path.splitext(path)[1].lower()
    doc = dict(SS["rawdoc"]) if SS["rawdoc"] else {
        "ternoo_version": "0.3", "source_type": "ternoo_design",
        "word_stream": [], "symbols": [], "edges": [],
        "flow_symbols": [], "flow_edges": [],
        "cmd_symbols": [], "cmd_edges": [], "sequence": [],
    }
    doc["source_file"] = os.path.basename(path)
    doc["cell_symbols"] = [dict(c) for c in SS["cells"].values()]
    doc["sheet_regions"] = [dict(r) for r in SS["regions"].values()]
    doc["free_cells"] = [dict(f) for f in SS["free"].values()]
    if ext == ".sheet":                # sheet-only partial, per policy
        doc["symbols"] = doc["edges"] = []
        doc["flow_symbols"] = doc["flow_edges"] = []
        doc["cmd_symbols"] = doc["cmd_edges"] = []
    meta = dict(doc.get("tgui_meta", {}))
    meta["cell_count"] = len(SS["cells"])
    doc["tgui_meta"] = meta
    return doc


def _picked(app_data):
    sels = app_data.get("selections") or {}
    if sels:
        return list(sels.values())[0]
    p = app_data.get("file_path_name", "")
    return p[:-2] if p.endswith(".*") else p


def save_to(path):
    if not path.endswith((".sheet", ".fc")):
        path += ".sheet"
    try:
        json.dump(_payload(path), open(path, "w", encoding="utf-8"),
                  indent=1)
        SS["file"] = path
        SS["dirty"] = False
        kept = " (other .fc sections preserved)" \
            if SS["rawdoc"] and path.endswith(".fc") else ""
        _status(f"saved {os.path.basename(path)} — "
                f"{len(SS['cells'])} cells{kept}")
    except Exception as e:                      # noqa: BLE001
        _status(f"save failed: {e}", ok=False)


def load_from(path):
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as e:                      # noqa: BLE001
        _status(f"open failed: {e}", ok=False)
        return
    SS["rawdoc"] = doc
    SS["cells"].clear()
    SS["regions"].clear()
    SS["free"].clear()
    SS["undo"].clear()
    SS["redo"].clear()
    for cell in doc.get("cell_symbols", []):
        r, c = cell.get("row", 0), cell.get("col", 0)
        cc = dict(cell)
        cc.setdefault("label", _a1(r, c))
        cc.setdefault("properties", [])
        SS["cells"][(r, c)] = cc
        SS["next"] = max(SS["next"], cc.get("id", 0) + 1)
    for reg in doc.get("sheet_regions", []):
        SS["regions"][reg.get("id", len(SS["regions"]))] = dict(reg)
    for fc in doc.get("free_cells", []):
        SS["free"][fc.get("id", len(SS["free"]))] = dict(fc)
    SS["file"] = path
    SS["dirty"] = False
    SS["sel"] = (0, 0)
    recalc()
    _sync_bar()
    extra = ""
    if SS["regions"] or SS["free"]:
        extra = (f" (+{len(SS['regions'])} regions, {len(SS['free'])} free "
                 "cells — rendered; editing rides a later leg)")
    _status(f"opened {os.path.basename(path)} — "
            f"{len(SS['cells'])} cells{extra}")


def _save_clicked(*_):
    if SS["file"]:
        save_to(SS["file"])
    else:
        dpg.show_item("shc_save_dlg")


# ── build ───────────────────────────────────────────────────────────────────
def _typing_keymap():
    """DPG 2.3.1 has no char handler — map the principal keys."""
    km = {}
    for i in range(26):
        km[dpg.mvKey_A + i] = chr(ord("a") + i)
    for i in range(10):
        km[dpg.mvKey_0 + i] = str(i)
    for name, ch in (("mvKey_Minus", "-"), ("mvKey_Period", "."),
                     ("mvKey_Comma", ","), ("mvKey_Plus", "="),
                     ("mvKey_Equal", "="), ("mvKey_Spacebar", " ")):
        k = getattr(dpg, name, None)
        if k is not None:
            km[k] = ch
    return km


_KEYMAP = None


def _grid_type(sender, key):
    """Click a cell and just TYPE — spreadsheet manners: the first
    keystroke opens the formula bar seeded with that character."""
    global _KEYMAP
    if STYLE.get("ACTIVE", lambda: "")() != "sheet":
        return
    if dpg.is_item_focused("shc_input") or dpg.is_item_focused("shc_name"):
        return
    if not (dpg.is_item_hovered("shc_draw")
            or dpg.is_item_hovered("shc_wrap")):
        return
    if dpg.is_key_down(dpg.mvKey_LControl) \
            or dpg.is_key_down(dpg.mvKey_RControl):
        return
    if _KEYMAP is None:
        _KEYMAP = _typing_keymap()
    ch = _KEYMAP.get(key)
    if ch is None:
        return
    if ch.isalpha() and (dpg.is_key_down(dpg.mvKey_LShift)
                         or dpg.is_key_down(dpg.mvKey_RShift)):
        ch = ch.upper()
    dpg.set_value("shc_input", ch)
    dpg.focus_item("shc_input")


def _grid_f2(sender, key):
    if STYLE.get("ACTIVE", lambda: "")() != "sheet":
        return
    if key == dpg.mvKey_F2:
        dpg.focus_item("shc_input")
    elif key == dpg.mvKey_Escape and dpg.is_item_focused("shc_input"):
        _sync_bar()


def _cell_copy(raw=False):
    cell = SS["cells"].get(tuple(SS["sel"]), {})
    CLIP = STYLE.get("CLIP")
    if CLIP:
        CLIP.clip_set(str(cell.get("value", "")) if raw
                      else str(_display(cell)))


def _cell_paste():
    CLIP = STYLE.get("CLIP")
    if CLIP:
        r, c = SS["sel"]
        set_cell(r, c, CLIP.clip_get().strip())
        _sync_bar()


def _cell_cut():
    _cell_copy(raw=True)
    r, c = SS["sel"]
    set_cell(r, c, "")
    _sync_bar()


def build_sheet_tab(style):
    STYLE.update(style)
    C = STYLE
    _designs = os.path.dirname(os.path.abspath(__file__))
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         tag="shc_save_dlg", width=780, height=480,
                         default_path=_designs, default_filename="design",
                         callback=lambda s, a: save_to(_picked(a))):
        dpg.add_file_extension("Sheets (*.sheet *.fc){.sheet,.fc}",
                               color=(122, 255, 122))
        dpg.add_file_extension(".sheet", color=(255, 204, 68))
        dpg.add_file_extension(".fc", color=(63, 208, 143))
        dpg.add_file_extension(".*")
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         tag="shc_open_dlg", width=780, height=480,
                         default_path=_designs, default_filename="",
                         callback=lambda s, a: load_from(_picked(a))):
        dpg.add_file_extension("Sheets (*.sheet *.fc){.sheet,.fc}",
                               color=(122, 255, 122))
        dpg.add_file_extension(".fc", color=(63, 208, 143))
        dpg.add_file_extension(".sheet", color=(255, 204, 68))
        dpg.add_file_extension(".*")

    with dpg.group(horizontal=True):
        dpg.add_text("A1", tag="shc_addr", color=(74, 158, 255))
        dpg.add_input_text(tag="shc_input", width=-420,
                           hint="value or =formula  (A1 refs · names · "
                                "WIDGET(name).prop)",
                           on_enter=True, callback=_apply_and_down)
        dpg.add_button(label=" Apply ", callback=_apply)
        dpg.add_text(" name:", color=C["DIM"])
        dpg.add_input_text(tag="shc_name", width=110, on_enter=True,
                           callback=_apply)
        dpg.add_button(label=" $ ", callback=lambda: _fmt("currency"))
        dpg.add_button(label=" % ", callback=lambda: _fmt("percent"))
        dpg.add_button(label=" .0+ ", callback=lambda: _fmt("dec", +1))
        dpg.add_button(label=" .0- ", callback=lambda: _fmt("dec", -1))
    with dpg.group(horizontal=True):
        dpg.add_text("", tag="shc_kind", color=C["DIM"])
        dpg.add_spacer(width=30)
        dpg.add_button(label=" Save ", callback=_save_clicked)
        dpg.add_button(label=" Save as... ",
                       callback=lambda: dpg.show_item("shc_save_dlg"))
        dpg.add_button(label=" Open ",
                       callback=lambda: dpg.show_item("shc_open_dlg"))
        dpg.add_button(label=" Clear ", callback=clear_all)
        dpg.add_button(label=" Undo ", callback=undo)
        dpg.add_button(label=" Redo ", callback=redo)
    with dpg.child_window(tag="shc_wrap", width=-1, height=-58,
                          horizontal_scrollbar=True):
        with dpg.drawlist(width=HDR_W + COLS * CELL_W,
                          height=HDR_H + ROWS * CELL_H, tag="shc_draw"):
            pass
    dpg.add_text("Sheet ready — the shared formula engine (A1 refs, names, "
                 "ranges, WIDGET(...) bindings). Click a cell, type in the "
                 "bar, Enter applies and moves down.",
                 tag="shc_status", color=C["DIM"])

    with dpg.handler_registry():
        dpg.add_mouse_click_handler(dpg.mvMouseButton_Left,
                                    callback=_on_click)
        dpg.add_key_press_handler(dpg.mvKey_Delete, callback=_del_cell)
        dpg.add_key_press_handler(callback=_grid_type)
        dpg.add_key_press_handler(callback=_grid_f2)
    CLIP = STYLE.get("CLIP")
    if CLIP:
        CLIP.input_menu("shc_input", "formula")
        CLIP.input_menu("shc_name", "name")
        CLIP.menu("shc_draw", [
            ("Copy cell (shown value)", lambda: _cell_copy(False)),
            ("Copy cell (raw formula)", lambda: _cell_copy(True)),
            ("Paste into cell", _cell_paste),
            ("Cut cell", _cell_cut), None,
            ("Clear cell", _cell_cut)])
    redraw()
    _sync_bar()


def _selftest():
    """Headless gate: detect kinds, evaluate chain + named ref, formats,
    round-trip .sheet + .fc preservation."""
    clear_all()
    SS["undo"].clear()
    set_cell(0, 0, "2", name="alpha")
    set_cell(1, 0, "=A1*3")
    set_cell(2, 0, "=alpha+10")
    assert SS["cells"][(0, 0)]["kind"] == "cell_value"
    assert SS["cells"][(1, 0)]["kind"] == "cell_formula"
    assert SS["cells"][(1, 0)].get("_result") == "6", \
        SS["cells"][(1, 0)]
    assert SS["cells"][(2, 0)].get("_result") == "12"
    _fmt("currency")            # sel is (0,0)? sel unchanged by set_cell
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "fdpg-test.sheet")
    save_to(tmp)
    clear_all()
    load_from(tmp)
    assert len(SS["cells"]) == 3
    assert SS["cells"][(2, 0)].get("_result") == "12"
    tmpc = os.path.join(tempfile.gettempdir(), "fdpg-test-sheet.fc")
    doc = json.load(open(tmp, encoding="utf-8"))
    doc["flow_symbols"] = [{"id": 0, "kind": "flow_process", "x": 0,
                            "y": 0, "label": "KEEP"}]
    json.dump(doc, open(tmpc, "w", encoding="utf-8"))
    load_from(tmpc)
    save_to(tmpc)
    doc2 = json.load(open(tmpc, encoding="utf-8"))
    assert doc2["flow_symbols"][0]["label"] == "KEEP"
    clear_all()
    return {"cells": 3, "chain": "A1*3=6, alpha+10=12"}
