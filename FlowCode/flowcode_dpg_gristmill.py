#!/usr/bin/env python3
"""flowcode_dpg_gristmill — the GristMill tab ORGAN of FlowCode's DPG face.

Storm leg 3 (captain's gale order, 06-09): the Tk face's GristMill tab is a
thin view over PURE, headless builders (gristmill_tab_view.py:
build_vocabulary_data / build_program_data / render_detail). This organ is a
second face over the SAME builders — the one-engine-two-faces claim made
literal, again.

Left: the Vocabulary registries (Opcodes, Shapes, Styles, Layouts, Signals)
plus the live Program section (widgets from the GUI organ, flow symbols from
the Flow organ, the word-stream identity from the Flow organ's live mirror).
Right: the detail panel, rendered by the Tk face's own render_detail().
Read-only, like its sibling.
"""
import importlib.util as _ilu
import os

import dearpygui.dearpygui as dpg

_HERE = os.path.dirname(os.path.abspath(__file__))
_FIVE = os.path.join(os.path.dirname(_HERE), "5500fp")

STYLE = {}
_G = [None]
_G_ERR = [""]

_SECTION_TYPE = {"Opcodes": "opcode", "Shapes": "shape", "Styles": "style",
                 "Layouts": "layout", "Signals": "signal"}


def _g():
    if _G[0] is None and not _G_ERR[0]:
        try:
            spec = _ilu.spec_from_file_location(
                "gristmill_tab_view",
                os.path.join(_FIVE, "gristmill_tab_view.py"))
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _G[0] = mod
        except Exception as e:                  # noqa: BLE001
            _G_ERR[0] = str(e)
    return _G[0]


def _fcstate():
    gui = STYLE.get("GUI")
    flow = STYLE.get("FLOW")
    return {
        "widgets": dict(gui.GS["widgets"]) if gui is not None else {},
        "flow_symbols": dict(flow.FS["syms"]) if flow is not None else {},
        "stream": None,
    }


def _show_detail(node):
    G = _g()
    try:
        txt = G.render_detail(node, _fcstate())
    except Exception as e:                      # noqa: BLE001
        txt = f"(detail unavailable: {e})"
    if dpg.does_item_exist("gm2_detail_txt"):
        dpg.set_value("gm2_detail_txt", txt)


def _show_symbol(sym, face):
    lines = [f"{face} symbol",
             f"kind:   {sym.get('kind', '?')}",
             f"name:   {sym.get('name', '')}",
             f"label:  {sym.get('label', '')}",
             f"at:     ({sym.get('x')}, {sym.get('y')}) "
             f"{sym.get('w')}×{sym.get('h')}"]
    props = sym.get("properties") or []
    if props:
        lines.append("properties:")
        for p in props:
            if isinstance(p, dict):
                lines.append(f"  {p.get('name')} = {p.get('value')!r}")
    if dpg.does_item_exist("gm2_detail_txt"):
        dpg.set_value("gm2_detail_txt", "\n".join(lines))


def refresh(*_):
    G = _g()
    if G is None or not dpg.does_item_exist("gm2_tree"):
        return
    dpg.delete_item("gm2_tree", children_only=True)
    C = STYLE
    with dpg.tree_node(label="Vocabulary", parent="gm2_tree",
                       default_open=True):
        for section in G.build_vocabulary_data():
            stype = _SECTION_TYPE.get(section.get("section", ""), "")
            with dpg.tree_node(label=section.get("section", "?")):
                for e in section.get("entries", []):
                    node = {"type": stype, **e}
                    dpg.add_selectable(
                        label=f"{e.get('name', '?')}"
                              + (f"  ({e.get('id')})"
                                 if e.get("id") is not None else ""),
                        user_data=node,
                        callback=lambda s, a, u: _show_detail(u))
    fc = _fcstate()
    with dpg.tree_node(label="Program (live)", parent="gm2_tree",
                       default_open=True):
        flow = STYLE.get("FLOW")
        if flow is not None and hasattr(flow, "rebuild_stream"):
            prog = flow.rebuild_stream()
            if prog is not None:
                dpg.add_text(f"stream: {len(prog.words)} words",
                             color=C.get("GRN"))
                dpg.add_text(f"MMID  {prog.mmid.word:+d}",
                             color=C.get("DIM"))
                dpg.add_text(f"OTree {prog.otree_word:+d}",
                             color=C.get("DIM"))
            else:
                dpg.add_text("stream: empty flow canvas",
                             color=C.get("DIM"))
        with dpg.tree_node(label=f"Flow symbols "
                                 f"({len(fc['flow_symbols'])})"):
            for sid, s in sorted(fc["flow_symbols"].items()):
                dpg.add_selectable(
                    label=f"{s.get('kind', '?').split('_', 1)[-1]}: "
                          f"{s.get('label', '?')}",
                    user_data=(dict(s), "Flow"),
                    callback=lambda sn, a, u: _show_symbol(u[0], u[1]))
        with dpg.tree_node(label=f"GUI widgets ({len(fc['widgets'])})"):
            for wid, w in sorted(fc["widgets"].items()):
                dpg.add_selectable(
                    label=f"{w.get('kind', '?').split('_', 1)[-1]}: "
                          f"{w.get('name', '?')}",
                    user_data=(dict(w), "GUI"),
                    callback=lambda sn, a, u: _show_symbol(u[0], u[1]))


def build_gristmill_tab(style):
    STYLE.update(style)
    C = STYLE
    G = _g()
    if G is None:
        dpg.add_text(f"gristmill view unavailable: {_G_ERR[0]}",
                     color=C.get("AMB"))
        return
    with dpg.group(horizontal=True):
        with dpg.child_window(width=430):
            with dpg.group(horizontal=True):
                dpg.add_text("OTree / vocabulary browser", color=C["DIM"])
                dpg.add_button(label="refresh", small=True, callback=refresh)
            with dpg.group(tag="gm2_tree"):
                pass
        with dpg.child_window():
            dpg.add_text("select a node on the left", tag="gm2_detail_txt",
                         wrap=700)
    refresh()


def _selftest():
    G = _g()
    assert G is not None, f"builders failed: {_G_ERR[0]}"
    secs = G.build_vocabulary_data()
    names = [s.get("section") for s in secs]
    assert "Opcodes" in names and "Signals" in names, names
    pd = G.build_program_data(_fcstate())
    assert isinstance(pd, dict) and "widget_roots" in pd
    first = {"type": "opcode", **secs[0]["entries"][0]}
    txt = G.render_detail(first, _fcstate())
    assert isinstance(txt, str) and len(txt) > 20
    assert dpg.does_item_exist("gm2_tree") and \
        dpg.does_item_exist("gm2_detail_txt")
    return {"sections": len(secs), "detail": len(txt)}
