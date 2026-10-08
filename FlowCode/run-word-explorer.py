#!/home/stevo/.venvs/p2pcp/bin/python3
"""Standalone Word Format Explorer — the FlowCode running program in its OWN window.

Reuses the IDE's real Run-GUI builder (flowcode_dpg_gui._run_wfe_window) but hosts it
in its own DearPyGui viewport, so it pops up as a separate desktop window — no IDE.
Launch:  python3 run-word-explorer.py   (or the TernOO desktop icon)
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import dearpygui.dearpygui as dpg

dpg.create_context()

import flowcode_dpg_gui as G

# The IDE fills STYLE at startup; standalone we seed just the colours the
# Word-Explorer window reads (the rest are only used by live/save, unused here).
G.STYLE.update({
    "GRN": (63, 208, 143),
    "TEXT": (230, 230, 236),
    "DIM": (150, 150, 165),
    "AMB": (232, 200, 144),
    "FLOW": None, "SHEET": None, "SAVE": None, "CFG": None,
})

# Build the real running window (creates item tag "rungui_win" + populates it).
G._run_wfe_window()

dpg.create_viewport(title="TernOO · Word Format Explorer",
                    width=760, height=560, small_icon="", large_icon="")
dpg.setup_dearpygui()
dpg.set_primary_window("rungui_win", True)   # the window IS the app
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
