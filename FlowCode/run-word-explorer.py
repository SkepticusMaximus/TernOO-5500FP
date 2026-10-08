#!/home/stevo/.venvs/p2pcp/bin/python3
"""Run a FlowCode design as its OWN standalone desktop window — no IDE.

    run-word-explorer.py [design.ternoo]      (default: Word-Format-Explorer)

Loads the design into the Flow + Sheet + GUI engines (so it fully decodes /
computes) and hosts the IDE's real run-window in a dedicated DearPyGui viewport.
Works for ANY design: the Word Explorer gets its charter window; anything else
gets the generic app window rendered from its own widgets.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DESIGN = (os.path.abspath(sys.argv[1]) if len(sys.argv) > 1
          else os.path.join(HERE, "Word-Format-Explorer.ternoo"))
TITLE = "TernOO · " + os.path.splitext(os.path.basename(DESIGN))[0].replace("-", " ")

import dearpygui.dearpygui as dpg

dpg.create_context()

# The IDE's font — so the −/0/+ trit glyphs render instead of tofu (?).
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_SIZE = int(os.environ.get("FLOW_DPG_FONT", "20"))
if os.path.exists(FONT):
    with dpg.font_registry():
        _font = dpg.add_font(FONT, FONT_SIZE)
    dpg.bind_font(_font)

import flowcode_dpg_gui as GUI
import flowcode_dpg_flow as FLOW
import flowcode_dpg_sheet as SHEET

# Each engine reads its own sections from the one file. load_from() also tries to
# repaint its tab canvas (which we don't build standalone) — swallow that; the
# DATA is loaded before the repaint step (verified: 45 flow syms, 82 cells, 51 widgets).
for _mod in (FLOW, SHEET, GUI):
    try:
        _mod.load_from(DESIGN)
    except Exception:
        pass

GUI.STYLE.update({
    "GRN": (63, 208, 143), "TEXT": (230, 230, 236), "DIM": (150, 150, 165),
    "AMB": (232, 200, 144), "SAVE": (lambda *a: None), "CFG": {},
    "FLOW": FLOW, "SHEET": SHEET, "GUI": GUI,
})

GUI.run_gui_window()          # dispatches: Word Explorer → charter window; else generic

dpg.create_viewport(title=TITLE, width=760, height=560)
dpg.setup_dearpygui()
dpg.set_primary_window("rungui_win", True)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
