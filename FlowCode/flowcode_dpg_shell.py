#!/usr/bin/env python3
"""flowcode_dpg_shell — the Shell tab ORGAN of FlowCode's DPG face.

The Shell REPL engine is REUSED whole: 5500fp/flowcode_repl.py — the
same engine behind the Tk Shell ("provably the visual Shell in text
form"): registry commands execute on the C emulator through the shared
compile path, pipes `|` chain dst-params, `&&` sequences, filesystem
commands ride the FileSystem abstraction, and `run file.t5asm` execs a
program. capture_last() lifts the last successful registry pipeline
straight onto the CONNECTORS canvas — the text and visual faces of the
same pipeline, round-tripping.

Layout: registry browser (left) · REPL log + prompt (right) · the
native t5asm console remains in the tab below (main builds it).

DOCFLAG: the Tk three-pane STAGED-pipeline builder (the Lingo view) is
not yet ported — the REPL + capture covers its execution heart; the
visual staging UI rides a later leg.
"""
import importlib.util as _ilu
import os
import sys
import threading

import dearpygui.dearpygui as dpg

_FIVE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "5500fp")

SH = {"repl": None, "err": "", "hist": [], "hist_i": 0}
STYLE = {}


def _repl():
    if SH["repl"] is None and not SH["err"]:
        try:
            if _FIVE not in sys.path:
                sys.path.insert(0, _FIVE)
            spec = _ilu.spec_from_file_location(
                "flowcode_repl_mod", os.path.join(_FIVE, "flowcode_repl.py"))
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            SH["repl"] = mod.Repl()
        except Exception as e:                  # noqa: BLE001
            SH["err"] = str(e)
    return SH["repl"]


def _out(text, color=None):
    if not dpg.does_item_exist("shrepl_log"):
        return
    dpg.add_text(text, parent="shrepl_log",
                 color=color or STYLE.get("TEXT"), wrap=1000)
    dpg.set_y_scroll("shrepl_log", 999999.0)


def _ui(fn):
    try:
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: fn())
    except Exception:                           # noqa: BLE001
        pass


def run_line(*_):
    r = _repl()
    if r is None:
        _out(f"✗ REPL engine unavailable: {SH['err']}", (255, 120, 90))
        return
    line = dpg.get_value("shrepl_in").strip()
    if not line:
        return
    SH["hist"].append(line)
    SH["hist_i"] = len(SH["hist"])
    dpg.set_value("shrepl_in", "")
    _out("> " + line, (74, 158, 255))

    def work():
        try:
            res = r.execute(line)
        except Exception as e:                  # noqa: BLE001
            res = f"✗ {e}"
        _ui(lambda: _out(str(res)))
    threading.Thread(target=work, daemon=True).start()


def capture_to_connectors(*_):
    r = _repl()
    CONN = STYLE.get("CONN")
    if r is None or CONN is None:
        _out("✗ capture unavailable (REPL or Connectors organ missing)",
             (255, 120, 90))
        return
    res = r.capture_last()
    if not res:
        _out("(nothing to capture — run a registry pipeline first)",
             STYLE.get("DIM"))
        return
    seg_cmds, seg_edges = res
    CONN._snapshot()
    idmap = {}
    base_x = 80
    for i, old in enumerate(sorted(seg_cmds)):
        nid = CONN.CS["next"]
        CONN.CS["next"] += 1
        c = dict(seg_cmds[old])
        c["id"] = nid
        c.setdefault("w", CONN.CMD_W)
        c.setdefault("h", CONN.CMD_H)
        c["x"] = base_x + 200 * i
        c["y"] = 120
        c.setdefault("label", str(c.get("kind", "cmd"))[4:])
        c.setdefault("name", f"{c.get('kind', 'cmd')}_{nid}")
        c.setdefault("properties", [])
        idmap[old] = nid
        CONN.CS["widgets"][nid] = c
    added = 0
    for e in seg_edges:
        if e.get("src") in idmap and e.get("dst") in idmap:
            CONN.CS["edges"].append({"src": idmap[e["src"]],
                                     "dst": idmap[e["dst"]],
                                     "dst_param": e.get("dst_param", "")})
            added += 1
    CONN.redraw()
    _out(f"✓ captured {len(idmap)} commands + {added} pipes → the "
         "Connectors tab", (63, 208, 143))


def _hist_key(sender, key):
    if not dpg.is_item_focused("shrepl_in") or not SH["hist"]:
        return
    if key == dpg.mvKey_Up:
        SH["hist_i"] = max(0, SH["hist_i"] - 1)
        dpg.set_value("shrepl_in", SH["hist"][SH["hist_i"]])
    elif key == dpg.mvKey_Down:
        SH["hist_i"] = min(len(SH["hist"]), SH["hist_i"] + 1)
        dpg.set_value("shrepl_in",
                      SH["hist"][SH["hist_i"]]
                      if SH["hist_i"] < len(SH["hist"]) else "")


def _insert(sender, app_data, name):
    cur = dpg.get_value("shrepl_in")
    dpg.set_value("shrepl_in", (cur + " " if cur.strip() else "") + name)


def build_shell_repl(style):
    STYLE.update(style)
    C = STYLE
    with dpg.group(horizontal=True):
        with dpg.child_window(width=230, height=330):
            dpg.add_text("REGISTRY", color=C["DIM"])
            try:
                if _FIVE not in sys.path:
                    sys.path.insert(0, _FIVE)
                import flowcode_commands as FCMD
                fams = {}
                for k in FCMD.command_names():
                    fams.setdefault(k.split("_")[1] if "_" in k[4:]
                                    else "misc", []).append(k[4:])
                for fam in sorted(fams):
                    with dpg.collapsing_header(label=fam.upper(),
                                               default_open=False):
                        for short in fams[fam]:
                            dpg.add_button(label=" " + short + " ",
                                           width=-1, user_data=short,
                                           callback=lambda s, a, u:
                                           _insert(s, a, u))
            except Exception as e:              # noqa: BLE001
                dpg.add_text(f"registry: {e}", color=C["AMB"])
            dpg.add_text("fs: ls cat pwd cd cp mv\nrm mkdir touch echo run",
                         color=C["DIM"])
        with dpg.group():
            with dpg.child_window(tag="shrepl_log", width=-1, height=260):
                dpg.add_text("The Shell REPL — the same engine as the Tk "
                             "face, executing on the C emulator through "
                             "the shared compile path.\nPipes chain: "
                             'text_split(text="a,b,c", sep=",") | '
                             "list_count.  `help` lists everything.",
                             color=C["DIM"], wrap=900)
            with dpg.group(horizontal=True):
                dpg.add_input_text(tag="shrepl_in", width=-320,
                                   on_enter=True, callback=run_line,
                                   hint="registry pipeline or fs command — "
                                        "Enter runs · ↑↓ history")
                dpg.add_button(label=" Run ", callback=run_line)
                dpg.add_button(label=" Capture → Connectors ",
                               callback=capture_to_connectors)
                dpg.add_button(label=" clear ",
                               callback=lambda: dpg.delete_item(
                                   "shrepl_log", children_only=True))
    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=_hist_key)
    CLIP = STYLE.get("CLIP")
    if CLIP:
        CLIP.input_menu("shrepl_in", "command line")

        def _copy_log():
            txts = []
            for c in dpg.get_item_children("shrepl_log", 1) or []:
                if dpg.get_item_type(c) == "mvAppItemType::mvText":
                    txts.append(dpg.get_value(c))
            CLIP.clip_set("\n".join(txts))
        CLIP.menu("shrepl_log", [
            ("Copy all output", _copy_log),
            ("Paste into command line", lambda: dpg.set_value(
                "shrepl_in", (dpg.get_value("shrepl_in") or "")
                + CLIP.clip_get())), None,
            ("Clear output", lambda: dpg.delete_item(
                "shrepl_log", children_only=True))])


def _selftest():
    r = _repl()
    assert r is not None, f"REPL failed: {SH['err']}"
    out = r.execute('text_upper(text="hello") | text_length')
    assert isinstance(out, str) and out.strip(), repr(out)
    cap = r.capture_last()
    assert cap, "pipeline not capturable"
    CONN = STYLE.get("CONN")
    n0 = len(CONN.CS["widgets"]) if CONN else 0
    if CONN:
        capture_to_connectors()
        assert len(CONN.CS["widgets"]) > n0, "capture placed nothing"
        CONN.clear_all()
        CONN.CS["undo"].clear()
    return {"repl": True, "out": out.strip()[:20], "captured": bool(CONN)}
