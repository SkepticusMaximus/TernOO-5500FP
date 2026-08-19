#!/usr/bin/env python3
"""flowcode_dpg_babble — the Babble-Fish tab ORGAN of FlowCode's DPG face.

The fish goes in the ear. Two views, both REUSING the Tk engines whole:

VOCABULARY — the GristMill explorer. 5500fp/gristmill_tab_view.py's
pure data builders (build_vocabulary_data / build_program_data — "no
tkinter dependency" by design) feed a tree of the static vocabulary
(Opcodes · Shapes · Styles · Layouts · Signals) plus the LIVE Program
(GUI containment tree, flow symbols, handler bindings). Read-only, a
reference surface — the Language Audit is the canon behind it.

TRANSLATOR — the star. 5500fp/flowcode_lingo_translate.py renders the
CURRENT DESIGN (GUI widgets + Flow symbols + Sheet cells + Connector
pipelines, assembled exactly like the Tk `_dialect_model`) into five
tongues: the canonical FlowCode dialect (flowcode_dialect.project) and
Python / Java / VB / C. Left pane always speaks FlowCode; right pane
speaks whatever you pick. Same engines, same output, both faces.
"""
import importlib.util as _ilu
import os
import sys

import dearpygui.dearpygui as dpg

_FIVE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "5500fp")

STYLE = {}
BM = {"D": None, "T": None, "G": None, "err": ""}
DIALECT_LABELS = {"flowcode": "FlowCode", "python": "Python",
                  "java": "Java", "vb": "VB", "c": "C"}


def _mods():
    """Lazy-load the three shared engines (dialect, translate, gristmill)."""
    if BM["D"] is None and not BM["err"]:
        try:
            if _FIVE not in sys.path:
                sys.path.insert(0, _FIVE)
            for key, name in (("D", "flowcode_dialect"),
                              ("T", "flowcode_lingo_translate"),
                              ("G", "gristmill_tab_view")):
                spec = _ilu.spec_from_file_location(
                    name, os.path.join(_FIVE, name + ".py"))
                mod = _ilu.module_from_spec(spec)
                spec.loader.exec_module(mod)
                BM[key] = mod
        except Exception as e:                  # noqa: BLE001
            BM["err"] = str(e)
    return BM


def live_model():
    """The Tk `_dialect_model`, assembled from the DPG organs' live state."""
    F = STYLE.get("FLOW")
    G = STYLE.get("GUI")
    S = STYLE.get("SHEET")
    C = STYLE.get("CONN")
    return {"widgets": (G.GS["widgets"] if G else {}),
            "flows": (F.FS["syms"] if F else {}),
            "cells": (S.SS["cells"] if S else {}),
            "cmds": (C.CS["widgets"] if C else {}),
            "flow_edges": (F.FS["edges"] if F else []),
            "cmd_edges": (C.CS["edges"] if C else []),
            "notes": []}


# ── the Translator view ─────────────────────────────────────────────────────
def refresh_translation(*_):
    m = _mods()
    if BM["err"]:
        return
    model = live_model()
    try:
        src = m["D"].project(model)
    except Exception as e:                      # noqa: BLE001
        src = f"# projection error: {e}"
    dial = (dpg.get_value("babble_dialect") or "Python").lower()
    try:
        out = m["T"].render(model, dial)
    except Exception as e:                      # noqa: BLE001
        out = f"# translation error ({dial}): {e}"
    n = (len(model["widgets"]) + len(model["flows"]) + len(model["cells"])
         + len(model["cmds"]))
    dpg.set_value("babble_src", src)
    dpg.set_value("babble_out", out)
    dpg.set_value("babble_info",
                  f"{n} entities · live from Flow+GUI+Sheet+Connectors"
                  if n else "empty design — draw something on the other "
                            "tabs, then ↻")


def _show_view(which):
    dpg.configure_item("babble_vocab", show=which == "vocab")
    dpg.configure_item("babble_trans", show=which == "trans")
    if which == "trans":
        refresh_translation()
    else:
        refresh_vocab()


# ── the Vocabulary view ─────────────────────────────────────────────────────
def _detail(lines, color=None):
    D = "babble_detail"
    dpg.delete_item(D, children_only=True)
    for ln in lines:
        dpg.add_text(ln, parent=D, wrap=430,
                     color=color or STYLE.get("TEXT"))


_OP_BLURB = {
    "RNODE": "render-node — places a widget/symbol node in the mesh",
    "REDGE": "render-edge — wires two nodes (signal/flow linkage)",
    "RENDER": "render — realize the described tree on a surface",
    "RPOINT": "render-point — geometry primitive (point)",
    "RLINE": "render-line — geometry primitive (line)",
}


def _pick(sender, app_data, ud):
    kind, e = ud
    if kind == "opcode":
        _detail([f"OPCODE · {e['name']} · id {e['id']}",
                 _OP_BLURB.get(e["name"], ""),
                 "", "canon: private/TernOO-Language-Audit.md"])
    elif kind in ("shape", "style", "layout"):
        _detail([f"{kind.upper()} · {e['name']} · id {e['id']}"])
    elif kind == "signal":
        _detail([f"SIGNAL · {e['name']} · id {e['id']}",
                 e.get("human", ""),
                 "emitted by: " + (", ".join(e.get("emitters") or [])
                                   or "(none registered)")])
    elif kind == "widget":
        w = e["w"]
        span = e.get("span")
        _detail([f"widget #{e['wid']} · {w.get('kind', '?')}",
                 f"label: {w.get('label', '')!r}"
                 + (f" · name: {w.get('name')}" if w.get("name") else ""),
                 f"at {w.get('x', 0)},{w.get('y', 0)} "
                 f"size {w.get('w', 0)}x{w.get('h', 0)}",
                 f"word span: {span[0]}–{span[1]}" if span
                 else "word span: (dump the stream on Flow to map)"])
    elif kind == "flow":
        s = e["s"]
        _detail([f"flow #{e['sid']} · {s.get('kind', '?')}",
                 f"label: {s.get('label', '')!r}"
                 + (f" · name: {s.get('name')}" if s.get("name") else "")])
    elif kind == "binding":
        _detail([f"binding · {e.get('sig_name', '?')}",
                 f"{e.get('src_label', '?')} → {e.get('dst_label', '?')}"])


def _leaf(parent, label, ud, indent=0):
    dpg.add_selectable(label=" " * indent + label, parent=parent,
                       user_data=ud, callback=_pick, span_columns=True)


def refresh_vocab(*_):
    m = _mods()
    L = "babble_tree"
    dpg.delete_item(L, children_only=True)
    if BM["err"]:
        dpg.add_text(f"engines unavailable: {BM['err']}", parent=L,
                     color=STYLE.get("AMB"))
        return
    G = m["G"]

    # The live Program — same fc_state keys the Tk view reads
    F = STYLE.get("FLOW")
    GO = STYLE.get("GUI")
    pd = G.build_program_data({
        "widgets": (GO.GS["widgets"] if GO else {}),
        "flow_symbols": (F.FS["syms"] if F else {}),
        "stream": None})
    with dpg.tree_node(label="Program (live)", parent=L, default_open=True):
        widgets = pd["widgets"]
        kids = pd["widget_children"]

        def _add_widget(wid, ind):
            w = widgets[wid]
            lbl = w.get("label") or ""
            disp = (f"{lbl}  #{wid} ({w.get('kind', '?')})" if lbl
                    else f"#{wid} ({w.get('kind', '?')})")
            _leaf(dpg.top_container_stack(), disp,
                  ("widget", {"wid": wid, "w": w,
                              "span": pd["word_map"].get(wid)}), ind)
            for cid in sorted(kids.get(wid, [])):
                _add_widget(cid, ind + 2)
        for wid in sorted(pd["widget_roots"]):
            _add_widget(wid, 0)
        for sid, s in sorted((F.FS["syms"] if F else {}).items()):
            _leaf(dpg.top_container_stack(),
                  f"{s.get('label') or ''}  ⟨{s.get('kind', '?')}⟩",
                  ("flow", {"sid": sid, "s": s}))
        for b in pd["bindings"]:
            _leaf(dpg.top_container_stack(),
                  f"⚡ {b.get('sig_name', '?')}: {b.get('src_label', '?')}"
                  f" → {b.get('dst_label', '?')}", ("binding", b))
        if not widgets and not (F and F.FS["syms"]):
            dpg.add_text("  (empty — the tree fills as you draw)",
                         color=STYLE.get("DIM"))

    # The static vocabulary registry
    for section in G.build_vocabulary_data():
        with dpg.tree_node(label=section["section"], parent=L,
                           default_open=False):
            for e in section["entries"]:
                _leaf(dpg.top_container_stack(),
                      f"{e['name']}  ·{e['id']}", (e["type"], e))


def on_show():
    """Tab-switch hook — refresh whichever view is up from live state."""
    if dpg.does_item_exist("babble_trans") and \
            dpg.is_item_shown("babble_trans"):
        refresh_translation()
    elif dpg.does_item_exist("babble_tree"):
        refresh_vocab()


# ── build ───────────────────────────────────────────────────────────────────
def _fish_icon():
    with dpg.drawlist(width=34, height=22):
        dpg.draw_circle((14, 11), 8, fill=(74, 158, 255, 90),
                        color=(74, 158, 255))
        dpg.draw_triangle((21, 11), (30, 4), (30, 18),
                          fill=(74, 158, 255, 90), color=(74, 158, 255))
        dpg.draw_circle((10, 9), 1.6, fill=(230, 237, 243))
        dpg.draw_circle((27, 3), 1.4, color=(120, 200, 255))
        dpg.draw_circle((31, 0.5), 1.0, color=(120, 200, 255))


def build_babble_tab(style):
    STYLE.update(style)
    C = STYLE
    with dpg.group(horizontal=True):
        _fish_icon()
        dpg.add_text("BABBLE-FISH", color=(63, 208, 143))
        dpg.add_text("— TernOO words in and out of human tongues",
                     color=C["DIM"])
        dpg.add_spacer(width=20)
        dpg.add_radio_button(("Vocabulary", "Translator"),
                             default_value="Translator", horizontal=True,
                             callback=lambda s, a: _show_view(
                                 "vocab" if a == "Vocabulary" else "trans"))

    with dpg.group(tag="babble_vocab", show=False, horizontal=True):
        with dpg.child_window(tag="babble_tree", width=440, height=-8):
            pass
        with dpg.child_window(tag="babble_detail", width=-1, height=-8):
            dpg.add_text("pick an entry — its story appears here",
                         color=C["DIM"])

    with dpg.group(tag="babble_trans"):
        with dpg.group(horizontal=True):
            dpg.add_text("FlowCode dialect", color=(74, 158, 255))
            dpg.add_text("→", color=C["DIM"])
            dpg.add_combo(("Python", "Java", "VB", "C"),
                          tag="babble_dialect", default_value="Python",
                          width=110, callback=refresh_translation)
            dpg.add_button(label=" ↻ from design ",
                           callback=refresh_translation)
            clip = C.get("CLIP")
            if clip:
                dpg.add_button(label=" copy dialect ", callback=lambda:
                               clip.clip_set(dpg.get_value("babble_src")))
                dpg.add_button(label=" copy translation ", callback=lambda:
                               clip.clip_set(dpg.get_value("babble_out")))
            dpg.add_text("", tag="babble_info", color=C["DIM"])
        with dpg.group(horizontal=True):
            dpg.add_input_text(tag="babble_src", multiline=True,
                               readonly=True, width=620, height=-8)
            dpg.add_input_text(tag="babble_out", multiline=True,
                               readonly=True, width=-1, height=-8)
    if C.get("CLIP"):
        C["CLIP"].input_menu("babble_src", "FlowCode dialect")
        C["CLIP"].input_menu("babble_out", "translation")
    refresh_translation()


FIXTURE = '''# selftest program
window main_win "Customer" at 200,150 size 400x300 layout vbox:
    button save_btn "Save" at 200,200 size 120x60
terminator on_save "clicked" at 700,100 size 120x60 entry
process doubler "Doubler" at 300,200 size 120x60:
    in input_value: number
    out output_value: number = input_value * 2
edge on_save -> doubler
cell A1 = 10
cell A2 = =A1+A1
cmd k1 = math_add(a=4, b=5) at 10,10
pipe k1 -> k1.a
'''


def _selftest():
    m = _mods()
    assert not BM["err"], f"engines failed: {BM['err']}"
    model = m["D"].parse(FIXTURE)
    outs = {}
    for d in m["T"].DIALECTS:
        outs[d] = m["T"].render(model, d)
        assert outs[d].strip() and "doubler" in outs[d], d
    assert outs["flowcode"] == m["D"].project(model), "canonical drift"
    live = live_model()
    assert m["T"].render(live, "python") is not None
    secs = {s["section"]: s["entries"] for s in m["G"].build_vocabulary_data()}
    assert {"Opcodes", "Shapes", "Styles", "Layouts",
            "Signals"} <= set(secs), sorted(secs)
    assert any(e["name"] == "RNODE" for e in secs["Opcodes"])
    pd = m["G"].build_program_data(
        {"widgets": {1: {"kind": "window", "label": "w"}},
         "flow_symbols": {}, "stream": None})
    assert pd["widget_roots"] == [1], pd["widget_roots"]
    return {"dialects": len(outs), "vocab_sections": len(secs),
            "python_has_def": "def " in outs["python"]}
