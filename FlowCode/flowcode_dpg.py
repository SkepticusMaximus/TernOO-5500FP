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
GRAPH = os.path.expanduser("~/.config/ternoo-flowcode-dpg-graph.json")
try:
    CFGD = json.load(open(CFG, encoding="utf-8"))
except Exception:                               # noqa: BLE001
    CFGD = {}
SCALE = float(CFGD.get("font_scale", 1.25))
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

# ── the application manifest — the Tk TAB_CHROME, carried over whole ────────
TAB_CHROME = [
    {"key": "flow",        "title": "Flow",          "live": True},
    {"key": "gui",         "title": "GUI",           "live": False,
     "charter": "The GHOST GUI builder — drag widgets, wire named\n"
                "handlers, auto-wiring per Phase 7c."},
    {"key": "sheet",       "title": "Sheet",         "live": False,
     "charter": "The Sheet leg — cells, formulas and flows on the\n"
                "grid, per the Stage 8 design memo."},
    {"key": "connectors",  "title": "Connectors",    "live": False,
     "charter": "The canvas-based connector view — sockets, wires\n"
                "and mesh plumbing between organs."},
    {"key": "shell",       "title": "Shell",         "live": True},
    {"key": "text",        "title": "Text",          "live": False,
     "charter": "The plain text editor pane."},
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

# ── Flow tab: node-editor scaffold state ────────────────────────────────────
NODES = {}          # node tag -> {"kind": str, "label": str}
LINKS = {}          # link tag -> (out_attr, in_attr)
_NODE_N = [0]
SYMBOL_KINDS = ["DATA", "EXEC", "MAP", "NEURAL", "I-O"]


def _flow_note(msg, color=DIM):
    dpg.set_value("flow_note", msg)
    dpg.configure_item("flow_note", color=color)


def add_node(kind):
    _NODE_N[0] += 1
    tag = f"fnode_{_NODE_N[0]}"
    label = f"{kind} {_NODE_N[0]}"
    with dpg.node(label=label, tag=tag, parent="flow_editor",
                  pos=(120 + 30 * (_NODE_N[0] % 8), 80 + 24 * (_NODE_N[0] % 9))):
        with dpg.node_attribute(tag=f"{tag}_in",
                                attribute_type=dpg.mvNode_Attr_Input):
            dpg.add_text("in")
        with dpg.node_attribute(tag=f"{tag}_out",
                                attribute_type=dpg.mvNode_Attr_Output):
            dpg.add_text("out")
    NODES[tag] = {"kind": kind, "label": label}
    _flow_note(f"added {label} — drag pins to wire", GRN)


def on_link(sender, app_data):
    out_attr, in_attr = app_data
    tag = dpg.add_node_link(out_attr, in_attr, parent=sender)
    LINKS[tag] = (dpg.get_item_alias(out_attr) or out_attr,
                  dpg.get_item_alias(in_attr) or in_attr)
    _flow_note("wired", GRN)


def on_delink(sender, app_data):
    LINKS.pop(app_data, None)
    dpg.delete_item(app_data)
    _flow_note("unwired")


def del_selected(*_):
    for ln in dpg.get_selected_links("flow_editor"):
        LINKS.pop(ln, None)
        dpg.delete_item(ln)
    for nd in dpg.get_selected_nodes("flow_editor"):
        alias = dpg.get_item_alias(nd) or nd
        NODES.pop(alias, None)
        dead = [t for t, (o, i) in LINKS.items()
                if str(o).startswith(str(alias)) or str(i).startswith(str(alias))]
        for t in dead:
            LINKS.pop(t, None)
        dpg.delete_item(nd)
    _flow_note("selection deleted")


def graph_save(*_):
    data = {"nodes": [{"tag": t, "kind": n["kind"], "label": n["label"],
                       "pos": dpg.get_item_pos(t)} for t, n in NODES.items()],
            "links": [[str(o), str(i)] for (o, i) in LINKS.values()]}
    try:
        json.dump(data, open(GRAPH, "w", encoding="utf-8"), indent=1)
        _flow_note(f"graph saved — {len(NODES)} nodes, {len(LINKS)} links "
                   f"(scaffold JSON, not yet .flow)", GRN)
    except Exception as e:                      # noqa: BLE001
        _flow_note(f"save failed: {e}", AMB)


def graph_load(*_):
    try:
        data = json.load(open(GRAPH, encoding="utf-8"))
    except Exception as e:                      # noqa: BLE001
        _flow_note(f"no saved graph: {e}", AMB)
        return
    for t in list(NODES):
        if dpg.does_item_exist(t):
            dpg.delete_item(t)
    NODES.clear()
    LINKS.clear()
    for nd in data.get("nodes", []):
        tag = nd["tag"]
        with dpg.node(label=nd["label"], tag=tag, parent="flow_editor",
                      pos=nd.get("pos", (100, 100))):
            with dpg.node_attribute(tag=f"{tag}_in",
                                    attribute_type=dpg.mvNode_Attr_Input):
                dpg.add_text("in")
            with dpg.node_attribute(tag=f"{tag}_out",
                                    attribute_type=dpg.mvNode_Attr_Output):
                dpg.add_text("out")
        NODES[tag] = {"kind": nd["kind"], "label": nd["label"]}
        n = int(tag.rsplit("_", 1)[-1])
        _NODE_N[0] = max(_NODE_N[0], n)
    for o, i in data.get("links", []):
        if dpg.does_item_exist(o) and dpg.does_item_exist(i):
            tag = dpg.add_node_link(o, i, parent="flow_editor")
            LINKS[tag] = (o, i)
    _flow_note(f"graph loaded — {len(NODES)} nodes, {len(LINKS)} links", GRN)


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


def _zoom_keys(sender, key):
    if dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl):
        if key in (dpg.mvKey_Plus, dpg.mvKey_Add):
            zoom(+0.1)
        elif key in (dpg.mvKey_Minus, dpg.mvKey_Subtract):
            zoom(-0.1)


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


# ── build ───────────────────────────────────────────────────────────────────
def build_ui():
    with dpg.theme() as th:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, FIELD)
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_Tab, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, FIELD)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, BORDER)
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
                dpg.add_menu_item(label="Save Flow graph", callback=graph_save)
                dpg.add_menu_item(label="Load Flow graph", callback=graph_load)
                dpg.add_separator()
                dpg.add_menu_item(label="Quit", callback=dpg.stop_dearpygui)
            with dpg.menu(label=" View "):
                dpg.add_menu_item(label="Zoom in        Ctrl +",
                                  callback=lambda: zoom(+0.1))
                dpg.add_menu_item(label="Zoom out       Ctrl -",
                                  callback=lambda: zoom(-0.1))
            with dpg.menu(label=" Help "):
                dpg.add_menu_item(label="About / port charter",
                                  callback=show_about)

        with dpg.tab_bar():
            for row in TAB_CHROME:
                with dpg.tab(label=f"  {row['title']}  "):
                    if row["key"] == "flow":
                        with dpg.group(horizontal=True):
                            dpg.add_text("add symbol:", color=DIM)
                            for kind in SYMBOL_KINDS:
                                dpg.add_button(
                                    label=f" {kind} ",
                                    callback=lambda s, a, k=kind: add_node(k))
                            dpg.add_button(label=" Delete selected ",
                                           callback=del_selected)
                            dpg.add_button(label=" Save ", callback=graph_save)
                            dpg.add_button(label=" Load ", callback=graph_load)
                        dpg.add_text("scaffold graphs only — the real "
                                     ".fc/.flow model rides the next leg",
                                     tag="flow_note", color=DIM)
                        with dpg.node_editor(tag="flow_editor",
                                             callback=on_link,
                                             delink_callback=on_delink,
                                             minimap=True,
                                             minimap_location=dpg.
                                             mvNodeMiniMap_Location_BottomRight):
                            pass
                    elif row["key"] == "shell":
                        core = ("C core (crowned spine) via ternoo_bridge"
                                if BRIDGE else
                                f"NATIVE CORE UNAVAILABLE: {BRIDGE_ERR}")
                        dpg.add_text(f"t5asm in -> {core}",
                                     color=GRN if BRIDGE else AMB)
                        with dpg.group(horizontal=True):
                            dpg.add_input_text(tag="shell_src", multiline=True,
                                               width=520, height=300,
                                               default_value=SHELL_DEMO)
                            with dpg.child_window(tag="shell_log", width=-1,
                                                  height=300):
                                dpg.add_text("output appears here — the "
                                             "demo program is fib(30); "
                                             "expect R11=832040", color=DIM)
                        with dpg.group(horizontal=True):
                            b = dpg.add_button(label="  Run on native core  ",
                                               callback=shell_run)
                            dpg.add_button(label=" Clear ",
                                           callback=shell_clear)
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


def main():
    dpg.create_context()
    build_ui()
    if os.environ.get("SMOKE"):
        print("SMOKE OK — FlowCode DPG keel builds clean")
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
