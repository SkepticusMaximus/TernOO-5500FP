#!/usr/bin/env python3
"""terndoc_dpg.py — TernDoc S2: the custom DPG editing surface.

The face is deliberately DUMB: all caret math, wrapping, hit-testing and
editing behavior live in terndoc_editor (tested face-blind); this file
only measures text, draws what Layout computed, and forwards events.

Two modes, Ctrl+E to switch:
  RENDERED  the custom surface — styled blocks, model-side caret,
            click/drag selection, spell squiggles. Keyboard reaches the
            model through a hidden input sink (the proven DPG pattern for
            custom text surfaces).
  SOURCE    a plain multiline markdown pane (native input_text) with the
            same document underneath — the de-risk lane and the power-
            user lane in one.

Style rendering honesty: bold = double-strike, italic = tinted, code =
background slab, headings = draw_text size scaling, links = underline.
Real font variants can come later; nothing else changes when they do.

Usage:  python3 terndoc_dpg.py [file.md]

Added: 22 Sep 2026 (S2). Authors: Stevo + Claude.
"""

import os
import sys

import dearpygui.dearpygui as dpg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import terndoc as TD
import terndoc_editor as ED

# ── palette (mesh_chat family) ───────────────────────────────────────────────
COL_TEXT = (220, 220, 225)
COL_BOLD = (245, 245, 250)
COL_ITAL = (200, 210, 235)
COL_CODE = (235, 200, 140)
COL_CODE_BG = (45, 45, 55)
COL_LINK = (120, 170, 250)
COL_CARET = (250, 250, 250)
COL_SEL = (60, 90, 140, 120)
COL_SPELL = (230, 90, 90)
BASE_SIZE = 15
PAD_X, PAD_Y = 10, 8

S = {"doc": None, "editor": None, "layout": None, "path": None,
     "mode": "rendered", "dirty_layout": True, "spell": True,
     "issues": [], "checker": None, "wrap_px": 640, "sink_last": "",
     "status": ""}


def _measure(text, sk):
    if not text:
        return 0
    sz = dpg.get_text_size(text)          # None until the font atlas lives
    if not sz or sz[0] <= 0:
        return 8 * len(text)
    return sz[0]


def _measure_for(kind):
    scale = {"h1": 1.6, "h2": 1.35, "h3": 1.15}.get(kind, 1.0)
    return lambda t, sk: _measure(t, sk) * scale


def relayout():
    S["layout"] = ED.Layout(S["doc"], _measure, S["wrap_px"],
                            int(BASE_SIZE * 1.35))
    S["editor"].attach_layout(S["layout"])
    if S["spell"] and S["checker"]:
        S["issues"] = TD.spellcheck(S["doc"], S["checker"])
    S["dirty_layout"] = False


def mark_dirty():
    S["dirty_layout"] = True


# ── drawing ──────────────────────────────────────────────────────────────────
def _seg_color(sk, href):
    if href:
        return COL_LINK
    return {"b": COL_BOLD, "i": COL_ITAL, "bi": COL_BOLD,
            "c": COL_CODE}.get(sk, COL_TEXT)


def redraw():
    L = S["layout"]
    dpg.delete_item("canvas", children_only=True)
    dpg.configure_item("canvas", height=max(L.height + 40, 100))
    doc = S["doc"]

    # selection rectangles (single-block selections, per S2 scope)
    sel = S["editor"]._sel()
    if sel:
        bi, a, b = sel
        for off0, off1 in ((a, b),):
            i0, i1 = L.line_index_of(bi, off0), L.line_index_of(bi, off1)
            for i in range(i0, i1 + 1):
                ln = L.lines[i]
                if ln["bi"] != bi:
                    continue
                x0 = L.caret_xy(bi, max(off0, ln["start"]))[0]
                x1 = L.caret_xy(bi, min(off1, ln["end"]))[0]
                dpg.draw_rectangle((PAD_X + x0, PAD_Y + ln["y"]),
                                   (PAD_X + x1, PAD_Y + ln["y"] + ln["h"]),
                                   fill=COL_SEL, color=COL_SEL,
                                   parent="canvas")

    spell_by_line = {}
    for bi, a, z, w, sug in S["issues"]:
        spell_by_line.setdefault(bi, []).append((a, z))

    for ln in L.lines:
        meta = L.block_meta[ln["bi"]]
        kind = meta["kind"]
        size = {"h1": BASE_SIZE * 1.6, "h2": BASE_SIZE * 1.35,
                "h3": BASE_SIZE * 1.15}.get(kind, BASE_SIZE)
        x = PAD_X
        y = PAD_Y + ln["y"]
        if kind == "code":
            dpg.draw_rectangle((PAD_X - 4, y), (S["wrap_px"] + PAD_X + 4,
                               y + ln["h"]), fill=COL_CODE_BG,
                               color=COL_CODE_BG, parent="canvas")
        if meta["prefix"] and ln["start"] == 0:
            dpg.draw_text((x - 0, y), meta["prefix"], size=size,
                          color=COL_TEXT, parent="canvas")
            x += _measure(meta["prefix"], "r")
        for frag, sk, href, w, s0 in ln["segs"]:
            col = _seg_color(sk, href)
            dpg.draw_text((x, y), frag, size=size, color=col,
                          parent="canvas")
            if sk in ("b", "bi"):                     # poor-man's bold
                dpg.draw_text((x + 0.7, y), frag, size=size, color=col,
                              parent="canvas")
            if href:
                dpg.draw_line((x, y + ln["h"] - 3),
                              (x + w, y + ln["h"] - 3),
                              color=COL_LINK, parent="canvas")
            x += w
        # spell squiggles
        for a, z in spell_by_line.get(ln["bi"], ()):
            s0, s1 = max(a, ln["start"]), min(z, ln["end"])
            if s0 >= s1:
                continue
            xa = L.caret_xy(ln["bi"], s0)[0]
            xz = L.caret_xy(ln["bi"], s1)[0]
            yy = PAD_Y + ln["y"] + ln["h"] - 2
            xx = xa
            while xx < xz:                            # dotted underline
                dpg.draw_line((PAD_X + xx, yy),
                              (PAD_X + min(xx + 3, xz), yy),
                              color=COL_SPELL, parent="canvas")
                xx += 6

    # caret
    bi, off = doc.cursor
    cx, cy, ch = L.caret_xy(bi, off)
    dpg.draw_line((PAD_X + cx, PAD_Y + cy + 2),
                  (PAD_X + cx, PAD_Y + cy + ch - 2),
                  color=COL_CARET, thickness=1.5, parent="canvas")

    name = os.path.basename(S["path"]) if S["path"] else "(unsaved)"
    dpg.set_value("status", f"{name}   blocks:{len(doc.blocks)}   "
                            f"spell:{len(S['issues'])}   {S['status']}")


# ── keyboard: hidden sink for typed text + key handlers for specials ─────────
def _shift():
    return (dpg.is_key_down(dpg.mvKey_LShift)
            or dpg.is_key_down(dpg.mvKey_RShift))


def _ctrl():
    return (dpg.is_key_down(dpg.mvKey_LControl)
            or dpg.is_key_down(dpg.mvKey_RControl))


def on_key(sender, key):
    if S["mode"] != "rendered":
        if _ctrl() and key == dpg.mvKey_E:
            switch_mode()
        return
    ed = S["editor"]
    ctrl, shift = _ctrl(), _shift()
    if ctrl:
        combos = {dpg.mvKey_B: lambda: ed.toggle("b"),
                  dpg.mvKey_I: lambda: ed.toggle("i"),
                  dpg.mvKey_D: lambda: ed.toggle("c"),
                  dpg.mvKey_Z: ed.undo, dpg.mvKey_Y: ed.redo,
                  dpg.mvKey_A: ed.select_all_block,
                  dpg.mvKey_S: save_doc, dpg.mvKey_E: switch_mode}
        fn = combos.get(key)
        if fn:
            fn()
            mark_dirty()
        return
    moves = {dpg.mvKey_Left: lambda: ed.move_h(-1, shift),
             dpg.mvKey_Right: lambda: ed.move_h(+1, shift),
             dpg.mvKey_Up: lambda: ed.move_v(-1, shift),
             dpg.mvKey_Down: lambda: ed.move_v(+1, shift),
             dpg.mvKey_Home: lambda: ed.home(shift),
             dpg.mvKey_End: lambda: ed.end(shift),
             dpg.mvKey_Back: ed.key_backspace,
             dpg.mvKey_Delete: ed.key_delete,
             dpg.mvKey_Return: ed.key_enter}
    fn = moves.get(key)
    if fn:
        fn()
        mark_dirty()


def poll_sink():
    """Typed characters arrive through the hidden input sink."""
    if S["mode"] != "rendered":
        return
    val = dpg.get_value("sink")
    if val:
        S["editor"].type_text(val)
        dpg.set_value("sink", "")
        mark_dirty()
    if dpg.is_item_hovered("canvaswin") or True:
        dpg.focus_item("sink")


def on_click():
    if S["mode"] != "rendered" or not dpg.is_item_hovered("canvaswin"):
        return
    mx, my = dpg.get_mouse_pos(local=False)
    rx, ry = dpg.get_item_rect_min("canvas")
    S["editor"].click(mx - rx - PAD_X, my - ry - PAD_Y, select=_shift())
    mark_dirty()


def on_drag():
    if S["mode"] != "rendered" or not dpg.is_mouse_button_down(0):
        return
    if not dpg.is_item_hovered("canvaswin"):
        return
    mx, my = dpg.get_mouse_pos(local=False)
    rx, ry = dpg.get_item_rect_min("canvas")
    S["editor"].drag(mx - rx - PAD_X, my - ry - PAD_Y)
    mark_dirty()


# ── mode switch / file plumbing ─────────────────────────────────────────────
def switch_mode(*_):
    if S["mode"] == "rendered":
        dpg.set_value("source", TD.to_markdown(S["doc"]))
        dpg.hide_item("canvaswin")
        dpg.show_item("sourcewin")
        S["mode"] = "source"
    else:
        md = dpg.get_value("source")
        keep_codec = S["doc"].codec
        S["doc"] = TD.from_markdown(md, codec=keep_codec)
        S["editor"] = ED.Editor(S["doc"])
        dpg.hide_item("sourcewin")
        dpg.show_item("canvaswin")
        S["mode"] = "rendered"
        mark_dirty()


def load_path(path):
    S["path"] = path
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            S["doc"] = TD.from_markdown(f.read())
    else:
        S["doc"] = TD.TernDoc()
    S["editor"] = ED.Editor(S["doc"])
    mark_dirty()


def save_doc(*_):
    if S["mode"] == "source":
        S["doc"] = TD.from_markdown(dpg.get_value("source"))
        S["editor"] = ED.Editor(S["doc"])
    if not S["path"]:
        S["path"] = "untitled.md"
    TD.save_as(S["doc"], S["path"])
    S["status"] = f"saved {S['path']}"
    mark_dirty()


def save_html(*_):
    if S["mode"] == "source":
        S["doc"] = TD.from_markdown(dpg.get_value("source"))
        S["editor"] = ED.Editor(S["doc"])
    base = os.path.splitext(S["path"] or "untitled.md")[0]
    out = base + ".html"
    TD.save_as(S["doc"], out)
    S["status"] = f"saved {out}"
    mark_dirty()


def toggle_spell(*_):
    S["spell"] = not S["spell"]
    S["issues"] = []
    mark_dirty()


def _kindbtn(kind):
    def cb(*_):
        S["editor"].set_kind(kind)
        mark_dirty()
    return cb


def _stylebtn(flag):
    def cb(*_):
        S["editor"].toggle(flag)
        mark_dirty()
    return cb


# ── app assembly ─────────────────────────────────────────────────────────────
def main():
    path = sys.argv[1] if len(sys.argv) > 1 else None
    dpg.create_context()
    S["checker"] = TD.WordlistChecker()

    with dpg.window(tag="root"):
        with dpg.group(horizontal=True):
            dpg.add_button(label="Save", callback=save_doc)
            dpg.add_button(label="Save HTML", callback=save_html)
            dpg.add_button(label="B", callback=_stylebtn("b"))
            dpg.add_button(label="I", callback=_stylebtn("i"))
            dpg.add_button(label="`c`", callback=_stylebtn("c"))
            for k in ("h1", "h2", "h3", "p", "ul", "ol", "code"):
                dpg.add_button(label=k.upper(), callback=_kindbtn(k))
            dpg.add_button(label="Spell", callback=toggle_spell)
            dpg.add_button(label="MD/Rich (^E)", callback=switch_mode)
        dpg.add_text("", tag="status")
        # hidden keyboard sink (1px, always focused in rendered mode)
        dpg.add_input_text(tag="sink", width=1, height=1, multiline=True,
                           on_enter=False)
        with dpg.child_window(tag="canvaswin", height=-1):
            dpg.add_drawlist(tag="canvas", width=1200, height=400)
        with dpg.child_window(tag="sourcewin", height=-1, show=False):
            dpg.add_input_text(tag="source", multiline=True, width=-1,
                               height=-1, tab_input=True)

    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=lambda s, k: on_key(s, k))
        dpg.add_mouse_click_handler(callback=lambda *_: on_click())
        dpg.add_mouse_drag_handler(callback=lambda *_: on_drag())

    if path:
        load_path(path)
    else:
        S["doc"] = TD.from_markdown(
            "# TernDoc\n\nType here. **Bold** with Ctrl+B, *italic* "
            "Ctrl+I, `code` Ctrl+D. Ctrl+E for markdown source view.\n")
        S["editor"] = ED.Editor(S["doc"])
        mark_dirty()

    dpg.create_viewport(title="TernDoc — the ship's editor",
                        width=980, height=680)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("root", True)
    while dpg.is_dearpygui_running():
        vw = dpg.get_viewport_client_width()
        wrap = max(300, vw - 60)
        if wrap != S["wrap_px"]:
            S["wrap_px"] = wrap
            mark_dirty()
        poll_sink()
        if dpg.get_frame_count() == 2:
            mark_dirty()                   # font atlas ready: real metrics
        if S["mode"] == "rendered" and S["dirty_layout"]:
            relayout()
            redraw()
        dpg.render_dearpygui_frame()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
