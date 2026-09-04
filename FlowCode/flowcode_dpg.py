#!/usr/bin/env python3
"""flowcode_dpg — the KEEL of FlowCode's Dear PyGui face (step 3 of the
consolidation, laid 18-08-2026).

Both-faces doctrine: the Tk FlowCode (flowcode.py) remains the working
surface while this face grows beside it, tab by tab, until parity. The
full ten-tab canon surface exists here from day one — live organs where
they're built, honest charter cards where they're pending.

Live tonight:
  - the house style proven in the Mesh-Chat sandbox (palette, zoom,
    remembered geometry, SMOKE-gated builds)
  - Flow tab: the native GPU node editor — add symbol nodes, wire and
    unwire edges, save/load a scaffold graph (JSON; NOT yet .fc/.flow)
  - Shell tab: BOUND TO THE NATIVE C CORE via ternoo_bridge — t5asm in,
    libternoo_c.so executes, registers and cycle counts out. FlowCode
    touching a fast core for the first time in its life.
  - Mesh-Chat tab: launches the standalone DPG client (one codebase;
    in-pane mounting is the next leg)

    python3 FlowCode/flowcode_dpg.py            # the new face
    SMOKE=1 python3 FlowCode/flowcode_dpg.py    # build-only gate
    SMOKE_FRAMES=60 ...                          # render N frames, exit
"""
import importlib.util as _ilu
import json
import os
import shutil
import subprocess
import sys

import dearpygui.dearpygui as dpg

# ── the house style (the sandbox's palette, verbatim) ────────────────────────
BG = (26, 29, 40)
PANEL = (33, 37, 51)
FIELD = (42, 47, 63)
CANVAS = (20, 23, 32)
BORDER = (66, 74, 98)
TEXT = (238, 240, 245)
DIM = (168, 175, 190)
GRN = (63, 208, 143)
AMB = (240, 180, 80)

CFG = os.path.expanduser("~/.config/ternoo-flowcode-dpg.json")
AUTOSAVE_FLOW = os.path.expanduser(
    "~/.config/ternoo-flowcode-dpg-autosave.flow")
AUTOSAVE_GUI = os.path.expanduser(
    "~/.config/ternoo-flowcode-dpg-autosave.gui")
AUTOSAVE_SHEET = os.path.expanduser(
    "~/.config/ternoo-flowcode-dpg-autosave.sheet")
AUTOSAVE_CONN = os.path.expanduser(
    "~/.config/ternoo-flowcode-dpg-autosave-conn.fc")
try:
    CFGD = json.load(open(CFG, encoding="utf-8"))
except Exception:                               # noqa: BLE001
    CFGD = {}
SCALE = float(CFGD.get("font_scale", 1.0))
FONT_SIZE = int(os.environ.get("FLOW_DPG_FONT", "20"))


def save_cfg():
    try:
        os.makedirs(os.path.dirname(CFG), exist_ok=True)
        json.dump(CFGD, open(CFG, "w", encoding="utf-8"))
    except Exception:                           # noqa: BLE001
        pass


# ── the native core, through the bridge (the consolidation's point) ─────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_BRIDGE_PATH = os.path.join(os.path.dirname(_HERE),
                            "NASM-TernOO-5500FP-Emulator", "ternoo_bridge.py")


def _load_bridge():
    spec = _ilu.spec_from_file_location("ternoo_bridge", _BRIDGE_PATH)
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BRIDGE = None
BRIDGE_ERR = ""
try:
    BRIDGE = _load_bridge()
except Exception as e:                          # noqa: BLE001
    BRIDGE_ERR = str(e)


def _load_organ(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GUI_ORGAN = None
GUI_ORGAN_ERR = ""
try:
    GUI_ORGAN = _load_organ("flowcode_dpg_gui")
except Exception as e:                          # noqa: BLE001
    GUI_ORGAN_ERR = str(e)

FLOW_ORGAN = None
FLOW_ORGAN_ERR = ""
try:
    FLOW_ORGAN = _load_organ("flowcode_dpg_flow")
except Exception as e:                          # noqa: BLE001
    FLOW_ORGAN_ERR = str(e)

SHEET_ORGAN = None
SHEET_ORGAN_ERR = ""
try:
    SHEET_ORGAN = _load_organ("flowcode_dpg_sheet")
except Exception as e:                          # noqa: BLE001
    SHEET_ORGAN_ERR = str(e)

CONN_ORGAN = None
CONN_ORGAN_ERR = ""
try:
    CONN_ORGAN = _load_organ("flowcode_dpg_conn")
except Exception as e:                          # noqa: BLE001
    CONN_ORGAN_ERR = str(e)

MESH_ORGAN = None
MESH_ORGAN_ERR = ""
try:
    MESH_ORGAN = _load_organ("flowcode_dpg_mesh")
except Exception as e:                          # noqa: BLE001
    MESH_ORGAN_ERR = str(e)

SHELL_ORGAN = None
SHELL_ORGAN_ERR = ""
try:
    SHELL_ORGAN = _load_organ("flowcode_dpg_shell")
except Exception as e:                          # noqa: BLE001
    SHELL_ORGAN_ERR = str(e)

CLIP = _load_organ("flowcode_dpg_clip")   # the text service — mandatory

TED_ORGAN = None
TED_ORGAN_ERR = ""
try:
    TED_ORGAN = _load_organ("flowcode_dpg_ted")
except Exception as e:                          # noqa: BLE001
    TED_ORGAN_ERR = str(e)

BABBLE_ORGAN = None
BABBLE_ORGAN_ERR = ""
try:
    BABBLE_ORGAN = _load_organ("flowcode_dpg_babble")
except Exception as e:                          # noqa: BLE001
    BABBLE_ORGAN_ERR = str(e)

ACAD_ORGAN = None
ACAD_ORGAN_ERR = ""
try:
    ACAD_ORGAN = _load_organ("flowcode_dpg_academy")
except Exception as e:                          # noqa: BLE001
    ACAD_ORGAN_ERR = str(e)

# ── the application manifest — the Tk TAB_CHROME, carried over whole ────────
TAB_CHROME = [
    {"key": "flow",        "title": "Flow",          "live": True},
    {"key": "gui",         "title": "GUI",           "live": True},
    {"key": "sheet",       "title": "Sheet",         "live": True},
    {"key": "connectors",  "title": "Connectors",    "live": True},
    {"key": "shell",       "title": "Shell",         "live": True},
    {"key": "text",        "title": "Text",          "live": True},
    {"key": "babble-fish", "title": "Babble-Fish",   "live": True},
    {"key": "academy",     "title": "Academy",       "live": True},
    {"key": "mesh",        "title": "Mesh-Chat",     "live": True},
    {"key": "docs",        "title": "Documentation", "live": False,
     "charter": "The helpdown viewer — index, search, raw/preview\n"
                "editing with atomic saves."},
]

# ── Shell tab: the native console ───────────────────────────────────────────
SHELL_DEMO = (
    "LI   R10, 0\nLI   R11, 1\nLI   R12, 29\n"
    "fib_loop:\nBEQZ R12, fib_done\nADD  R13, R10, R11\nMOV  R10, R11\n"
    "MOV  R11, R13\nSUBI R12, R12, 1\nJMP  fib_loop\nfib_done:\nHALT\n")


def shell_out(text, color=TEXT):
    dpg.add_text(text, parent="shell_log", color=color,
                 wrap=int(900 / max(0.5, SCALE)))
    dpg.set_y_scroll("shell_log", 999999.0)


def shell_run(*_):
    if BRIDGE is None:
        shell_out(f"native core unavailable: {BRIDGE_ERR}", AMB)
        return
    src = dpg.get_value("shell_src")
    try:
        words = BRIDGE.assemble(src)
    except Exception as e:                      # noqa: BLE001
        shell_out(f"assembly failed: {e}", AMB)
        return
    try:
        eng = BRIDGE.TernOONativeEngine("c")
        eng.run_program(words)
        cyc = eng._lib.ternoo_cycles()
        regs = {r: eng.read_reg(r) for r in range(1, 16)}
        hot = {f"R{r}": v for r, v in regs.items() if v}
        shell_out(f"ran {len(words)} words on the C core — "
                  f"{cyc} emulated cycles", GRN)
        shell_out("registers: " + (", ".join(f"{k}={v}"
                  for k, v in hot.items()) or "(R1..R15 all zero)"))
    except Exception as e:                      # noqa: BLE001
        shell_out(f"native run failed: {e}", AMB)


def shell_clear(*_):
    dpg.delete_item("shell_log", children_only=True)


# ── zoom ────────────────────────────────────────────────────────────────────
def _apply_zoom():
    dpg.set_global_font_scale(SCALE)
    CFGD["font_scale"] = SCALE
    save_cfg()


def zoom(delta):
    global SCALE
    SCALE = max(0.8, min(1.9, round(SCALE + delta, 2)))
    _apply_zoom()
    dpg.set_value("statusbar", f"text zoom {int(SCALE * 100)}%")


ACTIVE_TAB = ["flow"]
TEXT_DIRTY = [False]


def _menu_save(*_):
    t = ACTIVE_TAB[0]
    if t == "flow" and FLOW_ORGAN:
        FLOW_ORGAN._save_clicked()
    elif t == "sheet" and SHEET_ORGAN:
        SHEET_ORGAN._save_clicked()
    elif t == "connectors" and CONN_ORGAN:
        CONN_ORGAN._save_clicked()
    elif t == "gui" and GUI_ORGAN:
        GUI_ORGAN._save_clicked()
    elif t == "text":
        text_save()
    else:
        dpg.set_value("statusbar", "no file actions on this tab")


def _menu_save_as(*_):
    t = ACTIVE_TAB[0]
    if t == "flow" and FLOW_ORGAN:
        dpg.show_item("flowc_save_dlg")
    elif t == "sheet" and SHEET_ORGAN:
        dpg.show_item("shc_save_dlg")
    elif t == "connectors" and CONN_ORGAN:
        dpg.show_item("connc_save_dlg")
    elif t == "gui" and GUI_ORGAN:
        dpg.show_item("guic_save_dlg")
    elif t == "text":
        dpg.show_item("txt_save_dlg")
    else:
        dpg.set_value("statusbar", "no file actions on this tab")


def _menu_open(*_):
    t = ACTIVE_TAB[0]
    if t == "flow" and FLOW_ORGAN:
        dpg.show_item("flowc_open_dlg")
    elif t == "sheet" and SHEET_ORGAN:
        dpg.show_item("shc_open_dlg")
    elif t == "connectors" and CONN_ORGAN:
        dpg.show_item("connc_open_dlg")
    elif t == "gui" and GUI_ORGAN:
        dpg.show_item("guic_open_dlg")
    elif t == "text":
        dpg.show_item("txt_open_dlg")
    else:
        dpg.set_value("statusbar", "no file actions on this tab")


def _any_dirty():
    d = []
    if FLOW_ORGAN and FLOW_ORGAN.is_dirty():
        d.append("Flow")
    if GUI_ORGAN and GUI_ORGAN.is_dirty():
        d.append("GUI")
    if SHEET_ORGAN and SHEET_ORGAN.is_dirty():
        d.append("Sheet")
    if CONN_ORGAN and CONN_ORGAN.is_dirty():
        d.append("Connectors")
    if TEXT_DIRTY[0] and dpg.does_item_exist("txt_edit") \
            and dpg.get_value("txt_edit").strip():
        d.append("Text")
    return d


AUTOSAVE_HIST = os.path.expanduser(
    "~/.config/ternoo-flowcode-dpg-autosaves")
AUTOSAVE_KEEP = 8                   # cascade depth (slots per tab)


def _cascade_slots(n):
    """THE CAPTAIN'S CASCADE (20-08): slot k refreshes every 3^k ticks —
    the JK flip-flop retention ladder with CUBIC periods (his ruling:
    powers of 2 'stink like binary'). Eight slots at a ~2-min tick
    reach: 2m · 6m · 18m · 54m · 2.7h · 8.1h · 24.3h · ~3 days.
    Same 8 files, exponential lookback."""
    return [k for k in range(AUTOSAVE_KEEP) if n % (3 ** k) == 0]


def _autosave_history(tab, ext, src):
    """Tick the tab's cascade counter and refresh the slots due."""
    try:
        import shutil
        os.makedirs(AUTOSAVE_HIST, exist_ok=True)
        tick = int(CFGD.get(f"as_tick_{tab}", 0)) + 1
        CFGD[f"as_tick_{tab}"] = tick
        save_cfg()
        for k in _cascade_slots(tick):
            shutil.copyfile(src, os.path.join(
                AUTOSAVE_HIST, f"{tab}-slot{k}{ext}"))
    except Exception:                           # noqa: BLE001
        pass


def _autosave_dirty():
    for organ, slot, tab, ext in (
            (FLOW_ORGAN, AUTOSAVE_FLOW, "flow", ".flow"),
            (GUI_ORGAN, AUTOSAVE_GUI, "gui", ".gui"),
            (SHEET_ORGAN, AUTOSAVE_SHEET, "sheet", ".sheet"),
            (CONN_ORGAN, AUTOSAVE_CONN, "conn", ".fc")):
        if organ and organ.is_dirty():
            if organ.autosave(slot):
                _autosave_history(tab, ext, slot)


_RECOVER_ORGAN = {"flow": lambda: FLOW_ORGAN, "gui": lambda: GUI_ORGAN,
                  "sheet": lambda: SHEET_ORGAN,
                  "conn": lambda: CONN_ORGAN}


def show_recover_window(*_):
    """File ▸ Recover autosave… — the rotating history, newest first;
    click one to load it into its tab (as rescued, homeless content)."""
    tag = "recoverhist"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    files = []
    try:
        files = sorted(os.listdir(AUTOSAVE_HIST), reverse=True)
    except OSError:
        pass
    with dpg.window(label="Recover autosave — the cascade",
                    tag=tag, width=560, height=420, pos=(340, 140)):
        if not files:
            dpg.add_text("no autosave history yet — snapshots appear "
                         "here every ~2 minutes while work is unsaved",
                         color=DIM, wrap=520)
        dpg.add_text("slot k refreshes every 3^k ticks — shallow slots "
                     "are recent, deep slots reach back hours. Loading "
                     "marks the tab DIRTY (save to keep).",
                     color=DIM, wrap=520)

        def _load(sender, a, fname):
            tab = fname.split("-", 1)[0]
            organ = _RECOVER_ORGAN.get(tab, lambda: None)()
            if organ is None:
                return
            organ.load_from(os.path.join(AUTOSAVE_HIST, fname))
            st = getattr(organ, {"flow": "FS", "gui": "GS",
                                 "sheet": "SS", "conn": "CS"}[tab])
            st["file"] = None           # rescued content is homeless:
            st["dirty"] = True          # ALWAYS dirty until saved
            dpg.delete_item(tag)
            dpg.set_value("statusbar",
                          f"recovered {fname} → {tab.upper()} tab "
                          "(unsaved — save to keep it)")
        import time as _t
        for f in sorted(files):
            tab = f.split("-", 1)[0]
            slot = f.split("-", 1)[1].rsplit(".", 1)[0] \
                if "-" in f else f
            try:
                age = _t.time() - os.path.getmtime(
                    os.path.join(AUTOSAVE_HIST, f))
                when = (f"{int(age // 60)} min ago" if age < 3600
                        else f"{age / 3600:.1f} h ago")
            except OSError:
                when = "?"
            dpg.add_button(label=f"  {tab.upper():<6} {slot:<10} "
                           f"saved {when}  ",
                           width=-1, user_data=f, callback=_load)
        dpg.add_button(label="  Close  ",
                       callback=lambda: dpg.delete_item(tag))


def do_quit(*_):
    dirty = _any_dirty()
    if not dirty:
        dpg.stop_dearpygui()
        return
    tag = "quitconfirm"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    with dpg.window(label="Unsaved changes", tag=tag, modal=True,
                    width=520, height=180, pos=(360, 260)):
        dpg.add_text(f"Unsaved work on: {', '.join(dirty)}", color=AMB)
        dpg.add_text("Save first? (Tabs without a file yet keep an\n"
                     "autosave and are offered back on next launch.)",
                     color=TEXT)

        def _save_and_quit():
            for organ, st in ((FLOW_ORGAN, "FS"), (GUI_ORGAN, "GS"),
                              (SHEET_ORGAN, "SS"), (CONN_ORGAN, "CS")):
                if organ and organ.is_dirty():
                    f = getattr(organ, st)["file"]
                    if f:
                        organ.save_to(f)
            _autosave_dirty()               # homeless tabs: the net holds
            dpg.stop_dearpygui()
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Save & Quit  ",
                           callback=_save_and_quit)
            dpg.add_button(label="  Quit without saving  ",
                           callback=lambda: (_autosave_dirty(),
                                             dpg.stop_dearpygui()))
            dpg.add_button(label="  Cancel  ",
                           callback=lambda: dpg.delete_item(tag))


def _offer_recovery():
    have = [p for p in (AUTOSAVE_FLOW, AUTOSAVE_GUI, AUTOSAVE_SHEET,
                        AUTOSAVE_CONN) if os.path.exists(p)]
    if not have:
        return
    tag = "recoverwin"
    with dpg.window(label="Rescued work", tag=tag, modal=True, width=560,
                    height=190, pos=(340, 250)):
        dpg.add_text("Unsaved work from your last session was rescued.",
                     color=GRN)
        dpg.add_text("Restore it onto the canvases?", color=TEXT)

        def restore():
            if os.path.exists(AUTOSAVE_FLOW) and FLOW_ORGAN:
                FLOW_ORGAN.load_from(AUTOSAVE_FLOW)
                FLOW_ORGAN.FS["file"] = None    # rescued work has no home:
                FLOW_ORGAN.FS["dirty"] = True   # stays DIRTY until saved
            if os.path.exists(AUTOSAVE_GUI) and GUI_ORGAN:
                GUI_ORGAN.load_from(AUTOSAVE_GUI)
                GUI_ORGAN.GS["file"] = None
                GUI_ORGAN.GS["dirty"] = True
            if os.path.exists(AUTOSAVE_SHEET) and SHEET_ORGAN:
                SHEET_ORGAN.load_from(AUTOSAVE_SHEET)
                SHEET_ORGAN.SS["file"] = None
                SHEET_ORGAN.SS["dirty"] = True
            if os.path.exists(AUTOSAVE_CONN) and CONN_ORGAN:
                CONN_ORGAN.load_from(AUTOSAVE_CONN)
                CONN_ORGAN.CS["file"] = None
                CONN_ORGAN.CS["dirty"] = True
            discard(keep_state=True)

        def discard(keep_state=False):
            for p in (AUTOSAVE_FLOW, AUTOSAVE_GUI, AUTOSAVE_SHEET,
                  AUTOSAVE_CONN):
                try:
                    os.remove(p)
                except OSError:
                    pass
            dpg.delete_item(tag)
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Restore  ", callback=lambda: restore())
            dpg.add_button(label="  Discard  ", callback=lambda: discard())


def _canvas_zoom(direction):
    """Route Ctrl +/- and Ctrl+wheel to the ACTIVE tab's canvas zoom;
    UI-text zoom lives in the View menu on tabs without a canvas."""
    if ACTIVE_TAB[0] == "flow" and FLOW_ORGAN:
        FLOW_ORGAN.zoom_step(direction)
    elif ACTIVE_TAB[0] == "gui" and GUI_ORGAN:
        GUI_ORGAN.zoom_step(direction)
    elif ACTIVE_TAB[0] == "connectors" and CONN_ORGAN:
        CONN_ORGAN.zoom_step(direction)
    else:
        zoom(0.1 * direction)


def _zoom_keys(sender, key):
    if dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
        # 602 = ImGuiKey_Equal (main-row '='/'+'), absent from DPG 2.3.1's
        # namespace; legacy mvKey_Plus (61) never fires. Captain's 04-09 fix.
        if key in (dpg.mvKey_Plus, dpg.mvKey_Add,
                   getattr(dpg, "mvKey_Equal", 602)):
            _canvas_zoom(+1)
        elif key in (dpg.mvKey_Minus, dpg.mvKey_Subtract):
            _canvas_zoom(-1)
        elif key == dpg.mvKey_S:
            _menu_save()
        elif key == dpg.mvKey_Q:
            do_quit()


def _wheel(sender, app_data):
    if not (dpg.is_key_down(dpg.mvKey_LControl)
            or dpg.is_key_down(dpg.mvKey_RControl)):
        return
    d = 1 if app_data > 0 else -1
    if FLOW_ORGAN and dpg.is_item_hovered("flowc_draw"):
        FLOW_ORGAN.zoom_step(d)
    elif GUI_ORGAN and dpg.is_item_hovered("guic_draw"):
        GUI_ORGAN.zoom_step(d)
    elif CONN_ORGAN and dpg.does_item_exist("connc_draw") \
            and dpg.is_item_hovered("connc_draw"):
        CONN_ORGAN.zoom_step(d)


def _on_tab(sender, app_data):
    alias = dpg.get_item_alias(app_data) or ""
    if alias.startswith("tab_"):
        ACTIVE_TAB[0] = alias[4:]
        if FLOW_ORGAN:
            FLOW_ORGAN.set_minimap_visible(ACTIVE_TAB[0] == "flow")
        if BABBLE_ORGAN and ACTIVE_TAB[0] == "babble-fish":
            try:
                BABBLE_ORGAN.on_show()      # re-babel from live design
            except Exception:               # noqa: BLE001
                pass
        if ACAD_ORGAN and ACTIVE_TAB[0] == "academy":
            try:
                ACAD_ORGAN.on_show()        # refresh classroom furniture
            except Exception:               # noqa: BLE001
                pass


# ── the TernOO Word Explorer — the captain's reference tool (19-08) ─────────
# Primary table per 5500fp_ternoo_v03.py (code truth; value = msb*3 + lsb).
# DOCFLAG: v0.3 names the +− slot OPEN_A; the Manus thread's list says
# OPCODE — naming under audit review.
WORD_PRIMARIES = [
    (-4, "EXEC",   "−−"), (-3, "MAP",    "−0"), (-2, "DATA",   "−+"),
    (-1, "NEURAL", "0−"), (0,  "I/O",    "00"), (1,  "CRYPTO", "0+ (res)"),
    (2,  "OPEN_A", "+− (audit: OPCODE?)"), (3, "OPEN_B", "+0"),
    (4,  "POOL",   "++"),
]
_P3 = [3 ** i for i in range(25)]
WORD_MAX = (_P3[24] - 1) // 2


def _word_trits(value):
    out, v = [], int(value)
    for _ in range(24):
        r = v % 3
        if r == 2:
            out.append(-1)
            v = (v + 1) // 3
        else:
            out.append(r)
            v = (v - r) // 3
    return out                      # t0..t23, LSB first


def _word_fields(value):
    t = _word_trits(value)
    prim = t[23] * 3 + t[22]
    qual = sum(t[18 + i] * _P3[i] for i in range(4))
    payl = sum(t[i] * _P3[i] for i in range(18))
    return t, prim, qual, payl


def _we_strip(value):
    D = "we_strip"
    dpg.delete_item(D, children_only=True)
    t = _word_trits(value)
    for i in range(24):             # draw T23 (left) … T0 (right)
        trit = t[23 - i]
        band = ((36, 56, 100) if i < 2 else
                (120, 90, 30) if i < 6 else (40, 46, 62))
        x0 = i * 26
        dpg.draw_rectangle((x0, 8), (x0 + 24, 44), fill=band,
                           color=BORDER, parent=D)
        g = {1: "+", 0: "0", -1: "−"}[trit]
        gc = {1: GRN, 0: DIM, -1: (255, 136, 136)}[trit]
        dpg.draw_text((x0 + 8, 16), g, color=gc, size=20, parent=D)
        dpg.draw_text((x0 + 3, 46), f"{23 - i}", color=DIM, size=10,
                      parent=D)


def _we_decode(*_):
    try:
        v = int(dpg.get_value("we_val").strip() or "0")
    except ValueError:
        dpg.set_value("we_out", "not an integer")
        return
    if abs(v) > WORD_MAX:
        dpg.set_value("we_out", f"out of 24-trit range (±{WORD_MAX})")
        return
    _t, prim, qual, payl = _word_fields(v)
    pname = next((n for pv, n, _ in WORD_PRIMARIES if pv == prim),
                 f"({prim}?)")
    dpg.set_value("we_out",
                  f"primary {pname} ({prim:+d})   qualifier {qual:+d}   "
                  f"payload {payl:+d}")
    _we_strip(v)


def _we_build(*_):
    pname = dpg.get_value("we_prim")
    prim = next((pv for pv, n, _ in WORD_PRIMARIES if n == pname), 0)
    try:
        qual = int(dpg.get_value("we_qual"))
        payl = int(dpg.get_value("we_payl").strip() or "0")
    except ValueError:
        dpg.set_value("we_out", "qualifier/payload must be integers")
        return
    qual = max(-40, min(40, qual))
    pmax = (_P3[18] - 1) // 2
    payl = max(-pmax, min(pmax, payl))
    v = payl + qual * _P3[18] + prim * _P3[22]
    dpg.set_value("we_val", str(v))
    _we_decode()


def show_word_explorer(*_):
    tag = "wordexp"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    with dpg.window(label="TernOO Word Explorer", tag=tag, width=680,
                    height=560, pos=(280, 90)):
        dpg.add_text("The 24-trit word:  2 (type) + 4 (qualifier) + 18 "
                     "(payload)   ·   T23–T22 · T21–T18 · T17–T0",
                     color=GRN)
        with dpg.drawlist(width=630, height=60, tag="we_strip"):
            pass
        with dpg.group(horizontal=True):
            dpg.add_text("word value:", color=DIM)
            dpg.add_input_text(tag="we_val", width=220, default_value="0",
                               on_enter=True, callback=_we_decode)
            dpg.add_button(label=" Decode ", callback=_we_decode)
        dpg.add_text("", tag="we_out", color=TEXT)
        dpg.add_separator()
        dpg.add_text("Build a word:", color=DIM)
        with dpg.group(horizontal=True):
            dpg.add_combo([n for _v, n, _t in WORD_PRIMARIES],
                          tag="we_prim", width=120, default_value="DATA")
            dpg.add_text("qualifier", color=DIM)
            dpg.add_input_int(tag="we_qual", width=100, default_value=0,
                              min_value=-40, max_value=40, min_clamped=True,
                              max_clamped=True)
            dpg.add_text("payload", color=DIM)
            dpg.add_input_text(tag="we_payl", width=160, default_value="0")
            dpg.add_button(label=" Build ", callback=_we_build)
        dpg.add_separator()
        dpg.add_text("The nine primaries (per 5500fp_ternoo_v03.py):",
                     color=DIM)
        for pv, n, tp in WORD_PRIMARIES:
            dpg.add_text(f"  {tp:<22s} {n:<8s} value {pv:+d}", color=TEXT)
        dpg.add_text("Naming note: the +− slot is OPEN_A in v0.3 code; the "
                     "Manus record lists OPCODE — under audit review "
                     "(see docs/REBUILD-DOCFLAGS.md).", color=DIM)
    _we_decode()


def show_about(*_):
    tag = "aboutwin"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    with dpg.window(label="About FlowCode (Dear PyGui face)", tag=tag,
                    modal=True, width=560, height=300, pos=(240, 160)):
        dpg.add_text("FlowCode — the Dear PyGui face (the keel)", color=GRN)
        dpg.add_text("Both-faces doctrine: the Tk FlowCode remains the\n"
                     "working surface while this one grows to parity.\n\n"
                     "Live: Flow node editor (scaffold graphs), Shell\n"
                     "bound to the native C core via ternoo_bridge,\n"
                     "Mesh-Chat launcher.\n\n"
                     "Pending tabs carry their charters honestly.",
                     color=TEXT)
        dpg.add_button(label="  Close  ", callback=lambda: dpg.delete_item(tag))


# ── Text tab: a real editor pane ────────────────────────────────────────────
TEXT_FILE = [None]


def _text_picked(app_data):
    sels = app_data.get("selections") or {}
    if sels:
        return list(sels.values())[0]
    p = app_data.get("file_path_name", "")
    return p[:-2] if p.endswith(".*") else p


def text_open(path):
    try:
        dpg.set_value("txt_edit", open(path, encoding="utf-8",
                                       errors="replace").read())
        TEXT_FILE[0] = path
        dpg.set_value("txt_status", f"opened {os.path.basename(path)}")
    except Exception as e:                      # noqa: BLE001
        dpg.set_value("txt_status", f"open failed: {e}")


def text_save(path=None):
    path = path or TEXT_FILE[0]
    if not path:
        dpg.show_item("txt_save_dlg")
        return
    try:
        open(path, "w", encoding="utf-8").write(dpg.get_value("txt_edit"))
        TEXT_FILE[0] = path
        TEXT_DIRTY[0] = False
        dpg.set_value("txt_status", f"saved {os.path.basename(path)}")
    except Exception as e:                      # noqa: BLE001
        dpg.set_value("txt_status", f"save failed: {e}")


TEXT_RING = {"buf": [""], "i": 0}


def _text_snap(*_):
    TEXT_DIRTY[0] = True
    v = dpg.get_value("txt_edit")
    ring = TEXT_RING
    if v == ring["buf"][ring["i"]]:
        return
    ring["buf"] = ring["buf"][:ring["i"] + 1][-80:]
    ring["buf"].append(v)
    ring["i"] = len(ring["buf"]) - 1


def _text_undo_keys(sender, key):
    if not dpg.is_item_focused("txt_edit"):
        return
    if not (dpg.is_key_down(dpg.mvKey_LControl)
            or dpg.is_key_down(dpg.mvKey_RControl)):
        return
    ring = TEXT_RING
    if key == dpg.mvKey_Z and ring["i"] > 0:
        ring["i"] -= 1
        dpg.set_value("txt_edit", ring["buf"][ring["i"]])
    elif key == dpg.mvKey_Y and ring["i"] < len(ring["buf"]) - 1:
        ring["i"] += 1
        dpg.set_value("txt_edit", ring["buf"][ring["i"]])


def build_text_tab():
    if TED_ORGAN:
        TED_ORGAN.build_ted_header({"BORDER": BORDER, "TEXT": TEXT,
                                    "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                    "CLIP": CLIP,
                                    "ON_EDIT": _text_snap})
    for tag, cb in (("txt_open_dlg", lambda s, a: text_open(_text_picked(a))),
                    ("txt_save_dlg", lambda s, a: text_save(_text_picked(a)))):
        with dpg.file_dialog(directory_selector=False, show=False, tag=tag,
                             width=640, height=420,
                             default_path=os.path.expanduser("~"),
                             callback=cb):
            dpg.add_file_extension(".*")
    with dpg.group(horizontal=True):
        dpg.add_button(label=" Open ",
                       callback=lambda: dpg.show_item("txt_open_dlg"))
        dpg.add_button(label=" Save ", callback=lambda: text_save())
        dpg.add_button(label=" Save as... ",
                       callback=lambda: dpg.show_item("txt_save_dlg"))
        dpg.add_text("plain editor — no word wrap in stock DPG (roadmap)",
                     tag="txt_status", color=DIM)
    dpg.add_input_text(tag="txt_edit", multiline=True, width=-1,
                       height=-250, callback=_text_snap)
    if TED_ORGAN:
        TED_ORGAN.build_ted_footer({"BORDER": BORDER, "TEXT": TEXT,
                                    "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                    "CLIP": CLIP})
    else:
        dpg.add_text("Ted organ failed: " + TED_ORGAN_ERR, color=AMB)
    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=_text_undo_keys)


# ── build ───────────────────────────────────────────────────────────────────
def build_ui():
    with dpg.theme() as th:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, FIELD)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_Tab, (36, 56, 100))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, (74, 120, 190))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (90, 150, 230))
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocused, (32, 48, 84))
            dpg.add_theme_color(dpg.mvThemeCol_TabUnfocusedActive,
                                (60, 100, 160))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Button, FIELD)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, BORDER)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
        with dpg.theme_component(dpg.mvNode):
            dpg.add_theme_color(dpg.mvNodeCol_NodeBackground, PANEL,
                                category=dpg.mvThemeCat_Nodes)
            dpg.add_theme_color(dpg.mvNodeCol_TitleBar, FIELD,
                                category=dpg.mvThemeCat_Nodes)
    dpg.bind_theme(th)

    try:
        with dpg.font_registry():
            f = dpg.add_font("/usr/share/fonts/truetype/dejavu/"
                             "DejaVuSansMono.ttf", FONT_SIZE)
        dpg.bind_font(f)
    except Exception:                           # noqa: BLE001
        pass

    with dpg.window(tag="main"):
        with dpg.menu_bar():
            with dpg.menu(label=" File "):
                dpg.add_menu_item(label="Save            Ctrl+S",
                                  callback=_menu_save)
                dpg.add_menu_item(label="Save as...", callback=_menu_save_as)
                dpg.add_menu_item(label="Open...", callback=_menu_open)
                dpg.add_menu_item(label="Import into Flow...",
                                  callback=lambda: FLOW_ORGAN and
                                  dpg.show_item("flowc_import_dlg"))
                dpg.add_menu_item(label="Import into GUI...",
                                  callback=lambda: GUI_ORGAN and
                                  dpg.show_item("guic_import_dlg"))
                dpg.add_menu_item(label="Recover autosave...",
                                  callback=show_recover_window)
                dpg.add_separator()
                dpg.add_menu_item(label="Quit            Ctrl+Q",
                                  callback=do_quit)
            with dpg.menu(label=" View "):
                dpg.add_menu_item(label="Flow minimap on/off",
                                  callback=lambda: FLOW_ORGAN and
                                  FLOW_ORGAN.toggle_minimap())
                dpg.add_separator()
                dpg.add_menu_item(label="Canvas zoom in   Ctrl +",
                                  callback=lambda: _canvas_zoom(+1))
                dpg.add_menu_item(label="Canvas zoom out  Ctrl -",
                                  callback=lambda: _canvas_zoom(-1))
                dpg.add_separator()
                dpg.add_menu_item(label="UI text larger",
                                  callback=lambda: zoom(+0.1))
                dpg.add_menu_item(label="UI text smaller",
                                  callback=lambda: zoom(-0.1))
            with dpg.menu(label=" Help "):
                dpg.add_menu_item(label="TernOO Word Explorer",
                                  callback=show_word_explorer)
                dpg.add_menu_item(label="About / port charter",
                                  callback=show_about)

        with dpg.tab_bar(callback=_on_tab):
            for row in TAB_CHROME:
                with dpg.tab(label=f"  {row['title']}  ",
                             tag=f"tab_{row['key']}"):
                    if row["key"] == "flow":
                        if FLOW_ORGAN:
                            FLOW_ORGAN.build_flow_tab(
                                {"BORDER": BORDER, "TEXT": TEXT,
                                 "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                 "CFG": CFGD, "SAVE": save_cfg, "CLIP": CLIP,
                                 "ACTIVE": lambda: ACTIVE_TAB[0],
                                 "BRIDGE": BRIDGE})
                        else:
                            dpg.add_text("Flow organ failed to load: "
                                         + FLOW_ORGAN_ERR, color=AMB)
                    elif row["key"] == "sheet":
                        if SHEET_ORGAN:
                            SHEET_ORGAN.build_sheet_tab(
                                {"BORDER": BORDER, "TEXT": TEXT,
                                 "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                 "CFG": CFGD, "SAVE": save_cfg, "CLIP": CLIP,
                                 "ACTIVE": lambda: ACTIVE_TAB[0],
                                 "GUI": GUI_ORGAN})
                        else:
                            dpg.add_text("Sheet organ failed to load: "
                                         + SHEET_ORGAN_ERR, color=AMB)
                    elif row["key"] == "connectors":
                        if CONN_ORGAN:
                            CONN_ORGAN.build_conn_tab(
                                {"BORDER": BORDER, "TEXT": TEXT,
                                 "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                 "CFG": CFGD, "SAVE": save_cfg, "CLIP": CLIP,
                                 "ACTIVE": lambda: ACTIVE_TAB[0]})
                        else:
                            dpg.add_text("Connectors organ failed to "
                                         "load: " + CONN_ORGAN_ERR,
                                         color=AMB)
                    elif row["key"] == "gui":
                        if GUI_ORGAN:
                            GUI_ORGAN.build_gui_tab(
                                {"BORDER": BORDER, "TEXT": TEXT,
                                 "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                 "CFG": CFGD, "SAVE": save_cfg, "CLIP": CLIP,
                                 "ACTIVE": lambda: ACTIVE_TAB[0],
                                 "FLOW": FLOW_ORGAN,
                                 "BRIDGE": BRIDGE})
                        else:
                            dpg.add_text("GUI organ failed to load: "
                                         + GUI_ORGAN_ERR, color=AMB)
                    elif row["key"] == "shell":
                        if SHELL_ORGAN:
                            SHELL_ORGAN.build_shell_repl(
                                {"BORDER": BORDER, "TEXT": TEXT,
                                 "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                 "CONN": CONN_ORGAN, "CLIP": CLIP})
                        else:
                            dpg.add_text("Shell REPL organ failed: "
                                         + SHELL_ORGAN_ERR, color=AMB)
                        dpg.add_separator()
                        core = ("C core (crowned spine) via ternoo_bridge"
                                if BRIDGE else
                                f"NATIVE CORE UNAVAILABLE: {BRIDGE_ERR}")
                        dpg.add_text("native console — t5asm in -> " + core,
                                     color=GRN if BRIDGE else AMB)
                        with dpg.group(horizontal=True):
                            dpg.add_input_text(tag="shell_src",
                                               multiline=True, width=520,
                                               height=190,
                                               default_value=SHELL_DEMO)
                            with dpg.child_window(tag="shell_log",
                                                  width=-1, height=190):
                                dpg.add_text("output appears here — the "
                                             "demo program is fib(30); "
                                             "expect R11=832040",
                                             color=DIM)
                        with dpg.group(horizontal=True):
                            dpg.add_button(label="  Run on native core  ",
                                           callback=shell_run)
                            dpg.add_button(label=" Clear ",
                                           callback=shell_clear)
                    elif row["key"] == "text":
                        build_text_tab()
                    elif row["key"] == "babble-fish":
                        if BABBLE_ORGAN:
                            BABBLE_ORGAN.build_babble_tab(
                                {"BORDER": BORDER, "TEXT": TEXT,
                                 "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                 "FLOW": FLOW_ORGAN, "GUI": GUI_ORGAN,
                                 "SHEET": SHEET_ORGAN, "CONN": CONN_ORGAN,
                                 "CLIP": CLIP})
                        else:
                            dpg.add_text("Babble-Fish organ failed: "
                                         + BABBLE_ORGAN_ERR, color=AMB)
                    elif row["key"] == "academy":
                        if ACAD_ORGAN:
                            ACAD_ORGAN.build_academy_tab(
                                {"BORDER": BORDER, "TEXT": TEXT,
                                 "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                 "CLIP": CLIP,
                                 "SET_STATUS": lambda msg:
                                 dpg.set_value("statusbar", msg)})
                        else:
                            dpg.add_text("Academy organ failed: "
                                         + ACAD_ORGAN_ERR, color=AMB)
                    elif row["key"] == "mesh":
                        if MESH_ORGAN:
                            MESH_ORGAN.build_mesh_tab(
                                {"BORDER": BORDER, "TEXT": TEXT,
                                 "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                 "CLIP": CLIP})
                        else:
                            dpg.add_text("Mesh organ failed to load: "
                                         + MESH_ORGAN_ERR, color=AMB)
                    else:
                        dpg.add_text(f"{row['title']} — port pending",
                                     color=AMB)
                        dpg.add_text(row.get("charter", ""), color=DIM)
                        dpg.add_text("The Tk FlowCode face remains the "
                                     "working surface for this tab.",
                                     color=DIM)
        dpg.add_text("ready", tag="statusbar", color=DIM)

    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=_zoom_keys)
        dpg.add_mouse_wheel_handler(callback=_wheel)
    CLIP.install()          # system-true Ctrl+C/X/V + right-click menus
    CLIP.input_menu("txt_edit", "editor text")
    CLIP.input_menu("shell_src", "t5asm source")
    CLIP.menu("shell_log", [
        ("Copy all output", lambda: CLIP.clip_set("\n".join(
            dpg.get_value(c) for c in
            dpg.get_item_children("shell_log", 1) or []
            if dpg.get_item_type(c) == "mvAppItemType::mvText"
            for _ in [0]) or "")),
        ("Clear output", shell_clear)])


def main():
    dpg.create_context()
    build_ui()
    if os.environ.get("SMOKE"):
        if os.environ.get("FLOW_DPG_TEST"):
            # CLICK-PATH SWEEP — fire every button/menu callback exactly the
            # way DPG does (sender, app_data, user_data), so callback-arity
            # bugs can never pass the gate again (19-08 lesson: user_data
            # None clobbered bound-default lambdas; tests had bypassed the
            # click path entirely).
            import inspect
            targets = []
            for it in dpg.get_all_items():
                try:      # inventory pass FIRST — callbacks fired later
                    if dpg.get_item_type(it) not in (
                            "mvAppItemType::mvButton",
                            "mvAppItemType::mvMenuItem"):
                        continue
                    lbl = dpg.get_item_label(it) or ""
                    if "Launch" in lbl or "Quit" in lbl or "▶▶" in lbl \
                            or "Learn" in lbl or "Train" in lbl:
                        continue   # Train: real belt-test thread; app exit
                        #            mid-write could truncate the brain file
                    cb = dpg.get_item_callback(it)
                    if cb is not None:
                        targets.append((it, lbl, cb,
                                        dpg.get_item_user_data(it)))
                except Exception:               # noqa: BLE001
                    continue    # dead/anonymous item — not a target
            fired, bad = 0, []
            for it, lbl, cb, ud in targets:
                try:
                    try:
                        arity = len(inspect.signature(cb).parameters)
                    except (TypeError, ValueError):
                        arity = 3
                    cb(*(it, None, ud)[:arity])   # DPG's dispatch: up to 3
                    fired += 1                    # positional, arity-adapted
                except Exception as ex:           # noqa: BLE001
                    bad.append((lbl, repr(ex)[:70]))
            assert not bad, f"CLICK-PATH FAILURES: {bad}"
            print(f"CLICK-PATH OK — {fired} controls fired clean")
        if os.environ.get("FLOW_DPG_TEST") and FLOW_ORGAN:
            # dirty-semantics regression (19-08 loss bug): content with no
            # file home must ALWAYS read dirty — incl. restored rescues
            FLOW_ORGAN.clear_all()
            FLOW_ORGAN.FS["file"] = None
            FLOW_ORGAN.FS["dirty"] = False
            sid = FLOW_ORGAN.add_symbol("flow_process", 200, 200)
            assert FLOW_ORGAN.is_dirty(), "unsaved sketch must be dirty"
            import tempfile as _tfd
            _p = os.path.join(_tfd.gettempdir(), "fdpg-dirty.flow")
            FLOW_ORGAN.save_to(_p)
            assert not FLOW_ORGAN.is_dirty(), "saved must be clean"
            FLOW_ORGAN.FS["file"] = None      # the restore() situation
            FLOW_ORGAN.FS["dirty"] = False    # even with the flag cleared
            assert FLOW_ORGAN.is_dirty(), \
                "homeless content must stay dirty (rescue-loss bug)"
            FLOW_ORGAN.clear_all()
            print("DIRTY SEMANTICS OK — homeless content always dirty")
            # lasso regression: rect over two symbols selects + deletes both
            a1 = FLOW_ORGAN.add_symbol("flow_process", 200, 200)
            a2 = FLOW_ORGAN.add_symbol("flow_process", 400, 200)
            FLOW_ORGAN._lasso_apply((150, 150, 600, 320))
            assert len(FLOW_ORGAN.FS["multi"]) == 2, "lasso missed"
            FLOW_ORGAN.delete_selected()
            assert not FLOW_ORGAN.FS["syms"], "group delete failed"
            print("LASSO OK — group select + delete")
            FLOW_ORGAN.do_suggest()          # empty canvas: early return
            FLOW_ORGAN.add_symbol("flow_process", 200, 200)
            FLOW_ORGAN.do_suggest()          # with a symbol: predict path
            FLOW_ORGAN.clear_all()
            print("BRAIN SUGGEST OK — no-crash on empty and populated")
            # pocket scopes: scope-local placement, cross-scope refusal,
            # port-bound crossing, round-trip of scopes + ports
            F = FLOW_ORGAN
            F.clear_all()
            F.FS["undo"].clear()
            F.set_scope(None)
            box = F.add_symbol("flow_process", 200, 200, "BOX")
            box_name = F.FS["syms"][box]["name"]
            F.set_scope(box_name)      # furnishes param+return (20-08)
            furnished = [s2 for s2 in F.FS["syms"].values()
                         if s2.get("parent_scope") == box_name]
            assert len(furnished) == 2, "pocket furnishing"
            kid = F.add_symbol("flow_terminator", 240, 240, "KID")
            assert F.FS["syms"][kid]["parent_scope"] == box_name
            F.set_scope(None)
            top2 = F.add_symbol("flow_io", 600, 200, "IO")
            assert F.add_edge(top2, kid) is None      # cross-scope refused
            F.FS["syms"][box]["entry_points"].append({"name": "in0"})
            e = F.add_edge(top2, box, bound_port_name="in0")
            assert e and e.get("bound_port_name") == "in0"
            import tempfile as _tfp
            pth = os.path.join(_tfp.gettempdir(), "fdpg-pocket.flow")
            F.save_to(pth)
            F.clear_all()
            F.load_from(pth)
            names = {s2.get("name"): s2 for s2 in F.FS["syms"].values()}
            assert names[box_name]["entry_points"] == [{"name": "in0"}]
            kids = [s2 for s2 in F.FS["syms"].values()
                    if s2.get("parent_scope") == box_name]
            assert len(kids) == 3      # param + return + KID
            assert any(e2.get("bound_port_name") == "in0"
                       for e2 in F.FS["edges"])
            F.clear_all()
            F.set_scope(None)
            print("POCKET SCOPES OK — scoping, port binding, round-trip")
            ex = FLOW_ORGAN._selftest_exec()
            print(f"EXEC PIPELINE OK — {ex['words']} words, "
                  f"{ex['t5_chars']} t5asm chars, {ex['steps']} interp "
                  f"steps, entry={ex['entry']!r}")
            import tempfile
            FLOW_ORGAN.clear_all()
            FLOW_ORGAN.FS["undo"].clear()
            a = FLOW_ORGAN.add_symbol("flow_terminator", 240, 120)
            b = FLOW_ORGAN.add_symbol("flow_process", 240, 280)
            FLOW_ORGAN.add_edge(a, b)
            assert FLOW_ORGAN.FS["syms"][a]["label"] == f"T{a}"
            tmpf = os.path.join(tempfile.gettempdir(), "fdpg-test.flow")
            FLOW_ORGAN.save_to(tmpf)
            FLOW_ORGAN.clear_all()
            FLOW_ORGAN.load_from(tmpf)
            assert len(FLOW_ORGAN.FS["syms"]) == 2
            assert len(FLOW_ORGAN.FS["edges"]) == 1
            assert FLOW_ORGAN.FS["syms"][a]["kind"] == "flow_terminator"
            assert FLOW_ORGAN.FS["syms"][a]["x"] % 40 == 0   # snapped
            # .fc section preservation: unknown sections survive the trip
            tmpc = os.path.join(tempfile.gettempdir(), "fdpg-test.fc")
            doc = json.load(open(tmpf, encoding="utf-8"))
            doc["academy_marker"] = {"keep": "me"}
            json.dump(doc, open(tmpc, "w", encoding="utf-8"))
            FLOW_ORGAN.load_from(tmpc)
            FLOW_ORGAN.save_to(tmpc)
            doc2 = json.load(open(tmpc, encoding="utf-8"))
            assert doc2["academy_marker"] == {"keep": "me"}
            print("FLOW ROUND-TRIP OK — .flow/.fc schema + preservation "
                  "verified")
        if os.environ.get("FLOW_DPG_TEST"):
            CLIP.clip_set("CLIPSVC-77")
            got = CLIP.clip_get()
            assert "CLIPSVC-77" in got, repr(got)
            assert len(CLIP._CTX) >= 8, f"only {len(CLIP._CTX)} menus"
            print(f"CLIP SERVICE OK — system round-trip + "
                  f"{len(CLIP._CTX)} context menus registered")
        if os.environ.get("FLOW_DPG_TEST") and FLOW_ORGAN:
            counts = {k: 0 for k in range(AUTOSAVE_KEEP)}
            for n in range(1, 28):
                for k in _cascade_slots(n):
                    counts[k] += 1
            assert (counts[0], counts[1], counts[2], counts[3]) == \
                (27, 9, 3, 1), counts       # the cubic ladder
            FLOW_ORGAN.clear_all()
            FLOW_ORGAN.add_symbol("flow_process", 100, 100, "AS")
            FLOW_ORGAN.FS["file"] = None
            _autosave_dirty()
            assert any(f.startswith("flow-slot0")
                       for f in os.listdir(AUTOSAVE_HIST))
            assert _RECOVER_ORGAN["flow"]() is FLOW_ORGAN
            FLOW_ORGAN.clear_all()
            FLOW_ORGAN.FS["undo"].clear()
            print("AUTOSAVE CASCADE OK — 3^k ladder (27·9·3·1 over 27 "
                  "ticks), slot0 written, recover routing sound")
        if os.environ.get("FLOW_DPG_TEST") and TED_ORGAN:
            tres = TED_ORGAN._selftest()
            print(f"TED GLYPH OK — {tres['chars']} chars, XYZ round-trip "
                  f"{tres['roundtrip']}")
        if os.environ.get("FLOW_DPG_TEST") and SHELL_ORGAN:
            shres = SHELL_ORGAN._selftest()
            print(f"SHELL REPL OK — engine reused, out={shres['out']!r}, "
                  f"capture->connectors={shres['captured']}")
        if os.environ.get("FLOW_DPG_TEST") and BABBLE_ORGAN:
            bres = BABBLE_ORGAN._selftest()
            print(f"BABBLE-FISH OK — {bres['dialects']} tongues, "
                  f"{bres['vocab_sections']} vocab sections, "
                  f"python def={bres['python_has_def']}")
        if os.environ.get("FLOW_DPG_TEST") and ACAD_ORGAN:
            ares = ACAD_ORGAN._selftest()
            print(f"ACADEMY OK — {ares['classes']} classes, "
                  f"route={ares['route']!r}, {ares['glyphs']} glyphs "
                  f"planned+stroked, prof={ares['prof']}")
        if os.environ.get("FLOW_DPG_TEST") and FLOW_ORGAN:
            dres = FLOW_ORGAN._selftest_decision()
            print(f"DECISION DOORS OK — {dres['doors']} doors, 4th "
                  f"refused={dres['refused_4th']}, {dres['tongue']!r}, "
                  f"branch round-trip={dres['roundtrip']}, "
                  f"{dres['route']} routing, anchors={dres['anchors']}, "
                  f"0-door speaks {dres['flavor']!r}")
        if os.environ.get("FLOW_DPG_TEST") and FLOW_ORGAN:
            lres = FLOW_ORGAN._selftest_loop()
            print(f"LOOP FAMILY OK — for={lres['walker']['for_ticks']} "
                  f"ticks, {lres['walker']['guard']}, "
                  f"do={lres['walker']['do']}, doors {lres['doors']}, "
                  f"3rd refused={lres['third_refused']}, "
                  f"panel filters={lres['filtered_panel']}, "
                  f".fc round-trip={lres['roundtrip']}")
        if os.environ.get("FLOW_DPG_TEST") and FLOW_ORGAN:
            iores = FLOW_ORGAN._selftest_io()
            print(f"IO FAMILY OK — {iores['while_alive']}, pocket "
                  f"furnishes {iores['pocket']}, "
                  f"{iores['io_words']} real I-O words, vars "
                  f"persist={iores['vars_persist']}")
        if os.environ.get("FLOW_DPG_TEST") and GUI_ORGAN:
            gres = GUI_ORGAN._selftest()
            print(f"GUI LAYOUT+WIRING OK — {gres['layout']}, "
                  f"{gres['roundtrip']}, import={gres['imported']}, "
                  f"{gres['signals']} signals → e.g. {gres['handler']}, "
                  f"zorder {gres['zorder']}, rescue={gres['rescue']}, "
                  f"VB kit: {gres['vbkit']}")
        if os.environ.get("FLOW_DPG_TEST") and MESH_ORGAN:
            mres = MESH_ORGAN._selftest()
            print(f"MESH CLIENT OK — full client in-pane, "
                  f"store={mres['store']}, {mres['macros']} macro buttons, "
                  f"seams live")
        if os.environ.get("FLOW_DPG_TEST") and CONN_ORGAN:
            cres = CONN_ORGAN._selftest()
            print(f"CONNECTORS OK — {cres['widgets']} commands, "
                  f"{cres['edges']} pipes, replace+mismatch semantics")
        if os.environ.get("FLOW_DPG_TEST") and CONN_ORGAN:
            cpres = CONN_ORGAN._selftest_props()
            print(f"CONN PROPS OK — {cpres['kind']}.{cpres['socket']} "
                  f"bound {cpres['binding']}, "
                  f"persists={cpres['persist']}")
        if os.environ.get("FLOW_DPG_TEST") and SHEET_ORGAN:
            sres = SHEET_ORGAN._selftest()
            print(f"SHEET OK — {sres['cells']} cells, {sres['chain']}")
        if os.environ.get("FLOW_DPG_TEST"):
            # word explorer math: round-trip fields
            v = 7 + 5 * _P3[18] + (-2) * _P3[22]
            _t, pr, q, pl = _word_fields(v)
            assert (pr, q, pl) == (-2, 5, 7), (pr, q, pl)
            print("WORD EXPLORER OK — field round-trip exact")
        if os.environ.get("FLOW_DPG_TEST") and GUI_ORGAN:
            # every widget kind must render a face without error
            allk = [k for _s, ks in GUI_ORGAN.PALETTE for k in ks]
            for k in allk:
                GUI_ORGAN._render_widget("guic_draw", k, 0, 0, 120, 80,
                                         label="x")
            dpg.delete_item("guic_draw", children_only=True)
            print(f"WIDGET FACES OK — {len(allk)} kinds render")
            import tempfile
            tmp = os.path.join(tempfile.gettempdir(), "fdpg-test.gui")
            GUI_ORGAN.add_widget("gui_dialog", 248, 160)
            GUI_ORGAN.GS["widgets"][0]["w"] = 377
            GUI_ORGAN._prop_set(GUI_ORGAN.GS["widgets"][0], "title", "Hello")
            GUI_ORGAN.save_to(tmp)
            GUI_ORGAN.clear_all()
            GUI_ORGAN.load_from(tmp)
            w0 = GUI_ORGAN.GS["widgets"][0]
            assert w0["kind"] == "gui_dialog" and w0["x"] == 248
            assert w0["w"] == 377
            assert GUI_ORGAN._prop_get(w0, "title") == "Hello"
            doc = json.load(open(tmp, encoding="utf-8"))
            assert doc["ternoo_version"] == "0.3" and doc["symbols"]
            print("GUI ROUND-TRIP OK — Tk-schema .gui verified")
        print("SMOKE OK — FlowCode DPG builds clean")
        dpg.destroy_context()
        return
    # Title carries the mission, not the widget kit (captain, 04-09).
    # NOTE the title is ALSO the window's WM_CLASS (GLFW derives it) — the
    # .desktop StartupWMClass must match it EXACTLY for the panel to paint
    # the ternary-trio icon; small/large_icon below only act on Windows.
    _ico = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "tools", "flowcode.ico")
    _ikw = ({"small_icon": _ico, "large_icon": _ico}
            if os.path.exists(_ico) else {})
    # ASCII title ONLY: the em-dash reached WM_CLASS/WM_NAME as Latin-1
    # mojibake ("â€”") and broke both the panel's icon match and its label.
    dpg.create_viewport(title="FlowCode - TernOO",
                        width=int(CFGD.get("vp_w", 1460)),
                        height=int(CFGD.get("vp_h", 980)),
                        x_pos=int(CFGD.get("vp_x", 100)),
                        y_pos=int(CFGD.get("vp_y", 40)),
                        **_ikw)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main", True)
    dpg.set_global_font_scale(SCALE)
    # Periodic timed autosave (captain's ruling 20-08): every ~2 minutes,
    # dirty tabs snapshot to the SAME side files the close-event net uses —
    # a crash loses minutes, not a session. Frame-chained, wall-clock gated.
    _as_last = [__import__("time").time()]

    def _autosave_tick():
        now = __import__("time").time()
        if now - _as_last[0] >= int(CFGD.get("autosave_secs", 120)):
            _as_last[0] = now
            _autosave_dirty()
        try:
            dpg.set_frame_callback(dpg.get_frame_count() + 300,
                                   _autosave_tick)
        except Exception:                       # noqa: BLE001
            pass
    dpg.set_frame_callback(300, _autosave_tick)

    dpg.set_exit_callback(_autosave_dirty)    # X-button can't be vetoed in
    if FLOW_ORGAN:                            # minimap: kick once post-show
        FLOW_ORGAN.set_minimap_visible(True)
    # SESSION RESTORE (20-08 — the captain saved Fun-Flow.flow, restarted
    # to an empty canvas and reasonably read it as a lost save): every
    # organ save/open records its path; launch reopens the last file per
    # tab. Skipped under SMOKE so gates never load real work.
    def _remember(organ, st_name, key):
        for fn_name in ("save_to", "load_from"):
            orig = getattr(organ, fn_name)

            def wrapped(path, _orig=orig, _key=key, _organ=organ,
                        _st=st_name):
                out = _orig(path)
                if getattr(_organ, _st)["file"] \
                        and not os.environ.get("SMOKE"):
                    CFGD[_key] = os.path.abspath(path)  # success sets
                    save_cfg()                          # file; gates
                return out                              # never recorded
            setattr(organ, fn_name, wrapped)
    for organ, st, key in ((FLOW_ORGAN, "FS", "last_flow"),
                           (GUI_ORGAN, "GS", "last_gui"),
                           (SHEET_ORGAN, "SS", "last_sheet"),
                           (CONN_ORGAN, "CS", "last_conn")):
        if organ:
            _remember(organ, st, key)
    if not os.environ.get("SMOKE"):
        for organ, key in ((FLOW_ORGAN, "last_flow"),
                           (GUI_ORGAN, "last_gui"),
                           (SHEET_ORGAN, "last_sheet"),
                           (CONN_ORGAN, "last_conn")):
            p = CFGD.get(key)
            if organ and p and os.path.exists(p):
                try:
                    organ.load_from(p)
                except Exception:               # noqa: BLE001
                    pass
    _offer_recovery()                         # DPG — rescue instead, and
                                              # offer it back on launch
    frames = int(os.environ.get("SMOKE_FRAMES", "0"))
    if frames:
        for _ in range(frames):
            dpg.render_dearpygui_frame()
        print(f"SMOKE_FRAMES OK — rendered {frames} frames")
    else:
        dpg.start_dearpygui()
        CFGD["vp_w"] = dpg.get_viewport_width()
        CFGD["vp_h"] = dpg.get_viewport_height()
        CFGD["vp_x"], CFGD["vp_y"] = dpg.get_viewport_pos()
        save_cfg()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
