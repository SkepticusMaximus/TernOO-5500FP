#!/usr/bin/env python3
"""DPG baseline — same probe content, measured to first rendered frame."""
import time
T0 = time.perf_counter()
import dearpygui.dearpygui as dpg
T_IMPORT = time.perf_counter()
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ternword as W


def rss_mb():
    for line in open("/proc/self/status"):
        if line.startswith("VmRSS"):
            return int(line.split()[1]) / 1024.0
    return 0.0


dpg.create_context()
fp = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
if os.path.exists(fp):
    with dpg.font_registry():
        ft = dpg.add_font(fp, 14)
    dpg.bind_font(ft)
trits = W.to_trits(W.SAMPLE)
col = {-1: (255, 138, 138), 0: (154, 154, 172), 1: (125, 211, 160)}
with dpg.window(tag="w"):
    dpg.add_text("TernOO · Widget Probe (DPG baseline)", color=(63, 208, 143))
    with dpg.group(horizontal=True):
        for t in trits:
            dpg.add_text(W.GLYPH[t], color=col[t])
    dpg.add_text("primary: %s" % W.decode_primary(trits), color=(232, 200, 144))
    dpg.add_input_text(multiline=True, default_value=W.MUSING, width=-1, height=-1)
dpg.create_viewport(title="DPG", width=560, height=580)
dpg.setup_dearpygui()
dpg.set_primary_window("w", True)
dpg.show_viewport()
dpg.render_dearpygui_frame()
shown = time.perf_counter()
print("BENCH kit=DPG import_ms=%.1f build_show_ms=%.1f startup_ms=%.1f rss_mb=%.1f"
      % ((T_IMPORT - T0) * 1000, (shown - T_IMPORT) * 1000, (shown - T0) * 1000, rss_mb()))
dpg.destroy_context()
