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

# ── the application manifest — the Tk TAB_CHROME, carried over whole ────────
TAB_CHROME = [
    {"key": "flow",        "title": "Flow",          "live": True},
    {"key": "gui",         "title": "GUI",           "live": True},
    {"key": "sheet",       "title": "Sheet",         "live": True},
    {"key": "connectors",  "title": "Connectors",    "live": False,
     "charter": "The canvas-based connector view — sockets, wires\n"
                "and mesh plumbing between organs."},
    {"key": "shell",       "title": "Shell",         "live": True},
    {"key": "text",        "title": "Text",          "live": True},
    {"key": "babble-fish", "title": "Babble-Fish",   "live": False,
     "charter": "GristMill translation — TernOO words in and out of\n"
                "human tongues."},
    {"key": "academy",     "title": "Academy",       "live": False,
     "charter": "The classroom: board and book GlyphSurfaces, the\n"
                "GHOST router and humility gate, consent-gated Bonsai,\n"
                "belt tests, brain scan, curriculum editor, Backstage."},
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
    if TEXT_DIRTY[0] and dpg.does_item_exist("txt_edit") \
            and dpg.get_value("txt_edit").strip():
        d.append("Text")
    return d


def _autosave_dirty():
    if FLOW_ORGAN and FLOW_ORGAN.is_dirty():
        FLOW_ORGAN.autosave(AUTOSAVE_FLOW)
    if GUI_ORGAN and GUI_ORGAN.is_dirty():
        GUI_ORGAN.autosave(AUTOSAVE_GUI)
    if SHEET_ORGAN and SHEET_ORGAN.is_dirty():
        SHEET_ORGAN.autosave(AUTOSAVE_SHEET)


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
        dpg.add_text("Quit anyway? An autosave will be kept and offered\n"
                     "back on the next launch.", color=TEXT)
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Quit (autosave kept)  ",
                           callback=lambda: (_autosave_dirty(),
                                             dpg.stop_dearpygui()))
            dpg.add_button(label="  Cancel  ",
                           callback=lambda: dpg.delete_item(tag))


def _offer_recovery():
    have = [p for p in (AUTOSAVE_FLOW, AUTOSAVE_GUI, AUTOSAVE_SHEET)
            if os.path.exists(p)]
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
            discard(keep_state=True)

        def discard(keep_state=False):
            for p in (AUTOSAVE_FLOW, AUTOSAVE_GUI, AUTOSAVE_SHEET):
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
    else:
        zoom(0.1 * direction)


def _zoom_keys(sender, key):
    if dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
        if key in (dpg.mvKey_Plus, dpg.mvKey_Add):
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


def _on_tab(sender, app_data):
    alias = dpg.get_item_alias(app_data) or ""
    if alias.startswith("tab_"):
        ACTIVE_TAB[0] = alias[4:]


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


def build_text_tab():
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
    dpg.add_input_text(tag="txt_edit", multiline=True, width=-1, height=-1,
                       callback=lambda *_: TEXT_DIRTY.__setitem__(0, True))


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
                                 "CFG": CFGD, "SAVE": save_cfg,
                                 "BRIDGE": BRIDGE})
                        else:
                            dpg.add_text("Flow organ failed to load: "
                                         + FLOW_ORGAN_ERR, color=AMB)
                    elif row["key"] == "sheet":
                        if SHEET_ORGAN:
                            SHEET_ORGAN.build_sheet_tab(
                                {"BORDER": BORDER, "TEXT": TEXT,
                                 "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                 "CFG": CFGD, "SAVE": save_cfg,
                                 "GUI": GUI_ORGAN})
                        else:
                            dpg.add_text("Sheet organ failed to load: "
                                         + SHEET_ORGAN_ERR, color=AMB)
                    elif row["key"] == "gui":
                        if GUI_ORGAN:
                            GUI_ORGAN.build_gui_tab(
                                {"BORDER": BORDER, "TEXT": TEXT,
                                 "DIM": DIM, "GRN": GRN, "AMB": AMB,
                                 "CFG": CFGD, "SAVE": save_cfg,
                                 "BRIDGE": BRIDGE})
                        else:
                            dpg.add_text("GUI organ failed to load: "
                                         + GUI_ORGAN_ERR, color=AMB)
                    elif row["key"] == "text":
                        build_text_tab()
                    elif row["key"] == "mesh":
                        dpg.add_text("Mesh-Chat lives as the standalone DPG "
                                     "client — one codebase,\ntwo doors. "
                                     "In-pane mounting is the next leg.",
                                     color=TEXT)
                        dpg.add_button(
                            label="  Launch Mesh-Chat (DPG)  ",
                            callback=lambda: subprocess.Popen(
                                [sys.executable,
                                 os.path.join(os.path.dirname(_HERE),
                                              "5500fp", "mesh_chat_dpg.py")]))
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
                            or "Learn" in lbl:
                        continue
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
    dpg.create_viewport(title="FlowCode — TernOO (Dear PyGui face)",
                        width=int(CFGD.get("vp_w", 1460)),
                        height=int(CFGD.get("vp_h", 980)),
                        x_pos=int(CFGD.get("vp_x", 100)),
                        y_pos=int(CFGD.get("vp_y", 40)))
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main", True)
    dpg.set_global_font_scale(SCALE)
    dpg.set_exit_callback(_autosave_dirty)    # X-button can't be vetoed in
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
