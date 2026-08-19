#!/usr/bin/env python3
"""flowcode_dpg_flow — the Flow tab ORGAN of FlowCode's Dear PyGui face.

The real FlowCode language, ported against the Tk face's own model:
the four UDP symbols — Terminator (oval), Process (rectangle), Decision
(diamond), I/O (parallelogram) — plus the EXEC Edge. Tk conventions
carried over verbatim: SYMBOL_W/H 120x60, GRID snap 40, labels
kind-initial + id (T0, P1, D2, I3), names kind_id, the Tk colour table,
selected-orange, no duplicate edges. Save/Open reads and writes the Tk
.fc/.flow schema; on .fc files every section this tab does not edit is
PRESERVED verbatim through load->save.

Not yet ported (stated, not hidden): Word Dump / Load->EMU / Step / Run /
Stop (the execution projection), Import, Learn, Suggest, waypoint
editing (loaded waypoints ARE rendered), pocket scopes (loaded nested
scopes are preserved untouched; the canvas shows top level), canvas
zoom. Each rides a later leg of this tab's port.
"""
import json
import math
import os
import subprocess
import sys
import tempfile
import threading
import time

import dearpygui.dearpygui as dpg

SYMBOL_W, SYMBOL_H, GRID = 120, 60, 40
CANVAS_W, CANVAS_H = 2400, 1600

COL = {
    "flow_process":    (15, 52, 96),
    "flow_decision":   (83, 52, 131),
    "flow_io":         (26, 107, 94),
    "flow_terminator": (26, 74, 107),
    "border":          (74, 158, 255),
    "selected":        (255, 107, 53),
}
KINDS = [
    ("flow_terminator", "Terminator", ""),
    ("flow_process",    "Process",    ""),
    ("flow_decision",   "Decision",   ""),
    ("flow_io",         "I/O",        ""),
]

FS = {
    "syms": {}, "raw": {}, "edges": [], "rawdoc": None,
    "next": 0, "sel": None, "sel_edge": None, "file": None,
    "tool": "select", "edge_src": None, "edge_wps": [], "drag": None,
    "wpdrag": None, "grip": None, "zoom": 1.0, "dirty": False,
    "multi": set(), "lasso": None, "scope": None,
    "undo": [], "redo": [],
}

CONTAINER_KINDS = {"flow_process", "flow_subroutine"}


def _in_scope(sym):
    return sym.get("parent_scope") == FS["scope"]


def _sym_by_name(name):
    for sy in FS["syms"].values():
        if sy.get("name") == name:
            return sy
    return None


def _has_pocket(sym):
    nm = sym.get("name")
    return bool(nm) and any(sy.get("parent_scope") == nm
                            for sy in FS["syms"].values())


def _scope_path():
    path, cur, seen = [], FS["scope"], set()
    while cur and cur not in seen:
        seen.add(cur)
        path.append(cur)
        sym = _sym_by_name(cur)
        cur = sym.get("parent_scope") if sym else None
    return list(reversed(path))


def set_scope(scope_name):
    """Drill into / out of a pocket; rebuild breadcrumb; clear selection."""
    FS["scope"] = scope_name
    FS["sel"] = None
    FS["sel_edge"] = None
    FS["multi"] = set()
    _build_breadcrumb()
    redraw()
    _status(f"opened pocket: {scope_name}" if scope_name
            else "back to MainFlow")


def leave_scope(*_):
    cur = FS["scope"]
    if cur is None:
        return
    sym = _sym_by_name(cur)
    set_scope(sym.get("parent_scope") if sym else None)


def _build_breadcrumb():
    bar = "flowc_crumbs"
    if not dpg.does_item_exist(bar):
        return
    dpg.delete_item(bar, children_only=True)
    segs = [("MainFlow", None)] + [(nm, nm) for nm in _scope_path()]
    for i, (label, scope) in enumerate(segs):
        if i:
            dpg.add_text("›", parent=bar, color=STYLE.get("DIM"))
        dpg.add_button(label=f" {label} ", parent=bar, small=True,
                       user_data=scope,
                       callback=lambda s2, a2, u: set_scope(u))


def _port_positions(sym):
    """Entry ports on the left edge, exit ports on the right (7c-4b)."""
    out = {"entry": [], "exit": []}
    if sym.get("kind") not in CONTAINER_KINDS:
        return out
    hw, hh = sym["w"] / 2, sym["h"] / 2
    top, bot = sym["y"], sym["y"] + sym["h"]
    for edge, key, ex in (("entry", "entry_points", sym["x"]),
                          ("exit", "exit_points", sym["x"] + sym["w"])):
        ports = sym.get(key) or []
        n = len(ports)
        for i, p in enumerate(ports):
            py = top + (bot - top) * (i + 1) / (n + 1)
            out[edge].append((p, ex, py))
    return out


def _port_at(x, y, tol=9):
    for sy in reversed(list(FS["syms"].values())):
        if not _in_scope(sy):
            continue
        pp = _port_positions(sy)
        for edge in ("entry", "exit"):
            for port, px, py in pp[edge]:
                if abs(px - x) <= tol and abs(py - y) <= tol:
                    return sy, edge, port
    return None


def is_dirty():
    """Content with NO file home is always dirty — a restored rescue or a
    never-saved sketch can never read as clean (19-08 loss bug)."""
    has = bool(FS["syms"] or FS["edges"])
    return has and (bool(FS["dirty"]) or FS["file"] is None)


def autosave(path):
    """Emergency rescue on exit — no side effects on FS['file']."""
    try:
        json.dump(_payload(path), open(path, "w", encoding="utf-8"),
                  indent=1)
        return True
    except Exception:                           # noqa: BLE001
        return False

# ── the execution layer (lazy: flowcode.py imports headless — the Tk app
#    only launches under __main__ — so FCCanvas/FCSymbol, the interpreter,
#    WordStream and the Stage-6 compiler are all REUSED, one source of
#    truth, no copies) ─────────────────────────────────────────────────────
_EXEC = {}
_ENG = [None]          # persistent native-core engine for Load→EMU
_RUN_PROC = [None]     # the SDL engine subprocess
_STEPPING = [False]
BARE = {"flow_terminator": "terminator", "flow_process": "process",
        "flow_decision": "decision", "flow_io": "io",
        "flow_subroutine": "process", "flow_connector": "io"}


def _exec_mods():
    if _EXEC.get("ready") or _EXEC.get("err"):
        return _EXEC
    try:
        import importlib.util as ilu
        here = os.path.dirname(os.path.abspath(__file__))
        five = os.path.join(os.path.dirname(here), "5500fp")
        if five not in sys.path:
            sys.path.insert(0, five)
        import word_stream as WS
        import compile_to_t5asm as CT
        import ternoo_interpreter as TI
        spec = ilu.spec_from_file_location(
            "flowcode_mod", os.path.join(here, "flowcode.py"))
        FC = ilu.module_from_spec(spec)
        spec.loader.exec_module(FC)
        _EXEC.update(ready=True, WS=WS, CT=CT, TI=TI, FC=FC,
                     engine=os.path.join(
                         os.path.dirname(here),
                         "NASM-TernOO-5500FP-Emulator", "c_emulator",
                         "5500fp"))
    except Exception as e:                      # noqa: BLE001
        _EXEC["err"] = str(e)
    return _EXEC


def _ui(fn):
    """Schedule a UI mutation from a worker thread onto the render thread."""
    try:
        dpg.set_frame_callback(dpg.get_frame_count() + 1,
                               lambda: fn())
    except Exception:                           # noqa: BLE001
        pass


def _out(text, color=None):
    if not dpg.does_item_exist("flowc_out"):
        return
    dpg.add_text(text, parent="flowc_out",
                 color=color or STYLE.get("TEXT", (238, 240, 245)),
                 wrap=int(1000 / max(0.5, FS["zoom"])))
    dpg.set_y_scroll("flowc_out", 999999.0)


def _out_clear(*_):
    if dpg.does_item_exist("flowc_out"):
        dpg.delete_item("flowc_out", children_only=True)


def _sync_canvas(E):
    """FS dicts -> FCCanvas, mirroring the Tk face's sync verbatim."""
    c = E["FC"].FCCanvas()
    Sym = E["FC"].FCSymbol
    for sid, sym in sorted(FS["syms"].items()):
        s = Sym(BARE.get(sym.get("kind", ""), "process"),
                sym["x"], sym["y"], sym.get("label", ""))
        s.id = sid
        c.symbols[sid] = s
    Sym._next_id = (max(FS["syms"].keys()) + 1) if FS["syms"] else 1
    for e in FS["edges"]:
        if e["src"] in c.symbols and e["dst"] in c.symbols:
            c.add_edge(e["src"], e["dst"],
                       waypoints=[tuple(w) for w in e.get("waypoints", [])],
                       condition=e.get("condition", ""))
    return c


def do_word_dump(*_):
    E = _exec_mods()
    if E.get("err"):
        _out(f"✗ execution layer unavailable: {E['err']}", (255, 120, 90))
        return
    c = _sync_canvas(E)
    words = c.to_word_program()
    import contextlib
    import io as _io
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        c.print_word_dump()
    _out(f"⬇ Word Dump — {len(words)} TernOO words", (74, 158, 255))
    for line in buf.getvalue().splitlines():
        _out("  " + line, STYLE.get("DIM"))
    _status(f"word dump → Output ({len(words)} words)")


def do_load_emu(*_):
    E = _exec_mods()
    if E.get("err"):
        _out(f"✗ execution layer unavailable: {E['err']}", (255, 120, 90))
        return
    bridge = STYLE.get("BRIDGE")
    if bridge is None:
        _out("✗ native bridge unavailable — build libternoo_c.so",
             (255, 120, 90))
        return
    c = _sync_canvas(E)
    words = c.to_word_program()
    try:
        if _ENG[0] is None:
            _ENG[0] = bridge.TernOONativeEngine("c")
        _ENG[0].load_program(words, start_addr=100)
    except Exception as ex:                     # noqa: BLE001
        _out(f"✗ native core unavailable: {ex}", (255, 120, 90))
        _status("native core unavailable — see Output", ok=False)
        return
    _out(f"▶ Loaded {len(words)} words → NATIVE C core "
         f"(addr 100–{100 + len(words) - 1})", (63, 208, 143))
    _status(f"loaded {len(words)} words → native C core at addr 100")


def do_step(*_):
    """▶ Step — walk the flow via the interpreter, live-highlighting each
    symbol on the canvas (runs in a worker; UI updates per step)."""
    if _STEPPING[0]:
        _status("step-run already in progress", ok=False)
        return
    E = _exec_mods()
    if E.get("err"):
        _out(f"✗ execution layer unavailable: {E['err']}", (255, 120, 90))
        return
    if not FS["syms"]:
        _out("✗ Flow canvas is empty — place symbols first", (255, 120, 90))
        return
    data = {"symbols": [{**s, "kind": BARE.get(s.get("kind", ""), "process")}
                        for s in FS["syms"].values()],
            "edges": [dict(e) for e in FS["edges"]]}
    _out(f"▶ Step-running flow ({len(FS['syms'])} symbols)…",
         (74, 158, 255))

    def work():
        _STEPPING[0] = True
        try:
            interp = E["TI"].TernOOInterpreter(trace=False)
            orig = interp._execute_node

            def patched(node, end_ids, depth):
                sym = FS["syms"].get(node.id)
                lbl = sym.get("label", "?") if sym else "?"
                knd = sym.get("kind", "?") if sym else "?"

                def show(nid=node.id, t=f"  ► {lbl}  [{knd}]"):
                    FS["sel"] = nid
                    redraw()
                    _out(t)
                    _selinfo(f"► {lbl}  [{knd}]")
                _ui(show)
                time.sleep(0.25)
                return orig(node, end_ids, depth)
            interp._execute_node = patched
            interp.load_dict(data)
            result = interp.run()
            _ui(lambda: (_out(f"✓ Done — {result['steps']} step(s)",
                              (63, 208, 143)),
                         _status(f"step-run complete — "
                                 f"{result['steps']} steps")))
        except Exception as ex:                 # noqa: BLE001
            _ui(lambda ex=ex: (_out(f"✗ Error: {ex}", (255, 120, 90)),
                               _status(f"step-run error: {ex}", ok=False)))
        finally:
            _STEPPING[0] = False
    threading.Thread(target=work, daemon=True).start()


def _entry_meta():
    """Flow meta for the compiler, with is_entry synthesized on the first
    terminator that has no incoming edge (unless a loaded file already
    carries an explicit is_entry property)."""
    meta = {sid: dict(s, properties=[dict(p) if isinstance(p, dict) else p
                                     for p in s.get("properties", [])])
            for sid, s in FS["syms"].items()}
    have = any(isinstance(p, dict) and p.get("name") == "is_entry"
               and p.get("value")
               for s in meta.values() for p in s.get("properties", []))
    if not have:
        incoming = {e["dst"] for e in FS["edges"]}
        for sid in sorted(meta):
            s = meta[sid]
            if s.get("kind") == "flow_terminator" and sid not in incoming:
                s.setdefault("properties", []).append(
                    {"name": "is_entry", "value": True})
                return meta, s.get("label", "")
    return meta, None


def do_run_sdl(*_):
    """▶▶ Run — compile the flow to t5asm and execute it on the native C
    engine (SDL window), exactly as the Tk face does."""
    E = _exec_mods()
    if E.get("err"):
        _out(f"✗ execution layer unavailable: {E['err']}", (255, 120, 90))
        return
    if not FS["syms"]:
        _out("✗ Flow canvas is empty — place symbols first", (255, 120, 90))
        return
    engine = E["engine"]
    if not (os.path.isfile(engine) and os.access(engine, os.X_OK)):
        _out(f"✗ Engine not found: {engine}\n  Run `make` in "
             "NASM-TernOO-5500FP-Emulator/c_emulator/ first.",
             (255, 120, 90))
        return
    _out("▶ Compiling…", (74, 158, 255))
    c = _sync_canvas(E)
    ws = E["WS"].WordStream(c.to_word_program())
    meta, auto_entry = _entry_meta()
    ws._flow_meta = meta
    ws._flow_edges = [dict(e) for e in FS["edges"]]
    if auto_entry is not None:
        _out(f"  entry: \"{auto_entry}\" (auto-detected — no-incoming "
             "terminator)", STYLE.get("DIM"))
    try:
        t5 = E["CT"].compile_wordstream_to_t5asm(
            ws, source_path=FS["file"] or "<in-memory>")
    except E["CT"].CompileError as ce:
        _out(f"✗ CompileError: {ce}", (255, 120, 90))
        _status(f"compile error: {ce}", ok=False)
        return
    except Exception:                           # noqa: BLE001
        import traceback
        _out("✗ Internal compiler error:\n" + traceback.format_exc(),
             (255, 120, 90))
        return
    tmp = os.path.join(tempfile.gettempdir(),
                       f"flowcode_dpg_{os.getpid()}.t5asm")
    open(tmp, "w", encoding="utf-8").write(t5)
    _out(f"  compiled {len(t5.splitlines())} lines → {tmp}",
         STYLE.get("DIM"))
    try:
        proc = subprocess.Popen([engine, "--display", "sdl", "--run", tmp],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True, bufsize=1)
    except OSError as oe:
        _out(f"✗ Launch failed: {oe}", (255, 120, 90))
        return
    _RUN_PROC[0] = proc
    _out("▶ SDL window is open — close it when finished (or ⬛ Stop).",
         (63, 208, 143))
    _status("SDL engine running — close its window or press Stop")

    def drain(pipe, tag):
        for line in pipe:
            _ui(lambda t=line.rstrip(): _out("  " + t, STYLE.get(tag)))

    threading.Thread(target=drain, args=(proc.stdout, "DIM"),
                     daemon=True).start()
    threading.Thread(target=drain, args=(proc.stderr, "AMB"),
                     daemon=True).start()

    def watch():
        rc = proc.wait()
        _ui(lambda: (_out(f"■ engine exited (rc={rc})", (74, 158, 255)),
                     _status("engine finished")))
    threading.Thread(target=watch, daemon=True).start()


def do_learn(*_):
    """🧠 Train the FlowCodeBrain on the current canvas (Tk parity)."""
    E = _exec_mods()
    if E.get("err"):
        _out(f"✗ execution layer unavailable: {E['err']}", (255, 120, 90))
        return
    FC = E["FC"]
    brain = getattr(FC, "_brain_instance", None)
    if not brain:
        _out("✗ Brain not available — check ternoo_neural.py in 5500fp/",
             (255, 120, 90))
        return
    if not FS["syms"]:
        _out("✗ Canvas is empty — nothing to learn from", (255, 120, 90))
        return
    c = _sync_canvas(E)
    data = {"symbols": [sy.to_dict() for sy in c.symbols.values()],
            "edges": [e.to_dict() for e in c.edges]}
    try:
        transitions = brain.train_on_canvas(data)
        bf = FC._find_brain_file() or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "5500fp", "flowcode_brain.json")
        json.dump(brain.to_json(), open(bf, "w", encoding="utf-8"),
                  indent=2)
        _out(f"Brain learned {len(transitions)} transitions — saved to "
             f"{os.path.basename(bf)}", (122, 255, 204))
        _status(f"brain learned {len(transitions)} transitions")
    except Exception as ex:                     # noqa: BLE001
        _out(f"✗ learn failed: {ex}", (255, 120, 90))


def do_suggest(*_):
    """💡 Ask the brain what symbol should come next (Tk parity)."""
    E = _exec_mods()
    if E.get("err"):
        _out(f"✗ execution layer unavailable: {E['err']}", (255, 120, 90))
        return
    brain = getattr(E["FC"], "_brain_instance", None)
    if not brain:
        _out("✗ Brain not available", (255, 120, 90))
        return
    if not FS["syms"]:
        _out("Place a symbol first — the brain suggests what follows",
             (255, 204, 68))
        return
    c = _sync_canvas(E)
    sym = c.symbols.get(FS["sel"])
    if sym is None:
        sym = list(c.symbols.values())[-1]
    try:
        import ternoo_neural as TN
        try:
            tok = TN.flowcode_symbol_type(sym.to_dict())
        except Exception:                       # noqa: BLE001
            tok = sym.kind
        nxt, conf = brain.predict_next(tok)
        _out(f"Brain suggests: after {tok} → "
             f"{(nxt or '(none)').upper()}  ({conf})", (255, 204, 68))
        _status(f"suggestion: {tok} → {nxt or '(none)'}")
    except Exception as ex:                     # noqa: BLE001
        _out(f"✗ suggest failed: {ex}", (255, 120, 90))


def do_stop(*_):
    proc = _RUN_PROC[0]
    if proc and proc.poll() is None:
        proc.terminate()
        _out("⬛ engine stopped", (255, 120, 90))
        _status("SDL engine stopped")
    else:
        _status("nothing running")


def _import_merge(path):
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as e:                      # noqa: BLE001
        _status(f"import failed: {e}", ok=False)
        return
    syms = doc.get("flow_symbols", [])
    if not syms:
        _status("no flow symbols in that file", ok=False)
        return
    _snapshot()
    idmap = {}
    base = FS["next"]
    for i, sym in enumerate(sorted(syms, key=lambda s: s["id"])):
        nid = base + i
        idmap[int(sym["id"])] = nid
        FS["syms"][nid] = {
            "id": nid, "kind": sym.get("kind", "flow_process"),
            "x": sym.get("x", 0) + 48, "y": sym.get("y", 0) + 48,
            "w": sym.get("w", SYMBOL_W), "h": sym.get("h", SYMBOL_H),
            "label": sym.get("label", ""),
            "name": f"{sym.get('kind', 'flow')}_{nid}",
            "parent_scope": sym.get("parent_scope"),
            "properties": list(sym.get("properties", [])),
        }
    FS["next"] = base + len(syms)
    added_e = 0
    for e in doc.get("flow_edges", []):
        if e.get("src") in idmap and e.get("dst") in idmap:
            ne = dict(e)
            ne["src"], ne["dst"] = idmap[e["src"]], idmap[e["dst"]]
            ne["waypoints"] = [[wx + 48, wy + 48]
                               for wx, wy in e.get("waypoints", [])]
            FS["edges"].append(ne)
            added_e += 1
    redraw()
    _status(f"imported {len(syms)} symbols + {added_e} edges "
            f"from {os.path.basename(path)} (merged, offset +48)")


def zoom_step(direction):
    """CANVAS zoom (the drawing itself), not UI-text zoom."""
    z = FS["zoom"] * (1.2 if direction > 0 else 1 / 1.2)
    FS["zoom"] = max(0.3, min(3.0, round(z, 3)))
    if dpg.does_item_exist("flowc_zoomlbl"):
        dpg.set_value("flowc_zoomlbl", f"   Zoom: {int(FS['zoom'] * 100)}%")
    redraw()


def _mpos():
    mx, my = dpg.get_drawing_mouse_pos()
    z = FS["zoom"]
    return mx / z, my / z


# ── minimap (the little viewport, back by request) ──────────────────────────
MM_W, MM_H = 220, 146
MM_F = min(MM_W / CANVAS_W, MM_H / CANVAS_H)


def toggle_minimap():
    if not dpg.does_item_exist("flowc_mm"):
        return
    show = not dpg.is_item_shown("flowc_mm")
    dpg.configure_item("flowc_mm", show=show)
    cfg = STYLE.get("CFG")
    if cfg is not None:
        cfg["flow_minimap"] = show
        if STYLE.get("SAVE"):
            STYLE["SAVE"]()
    if show:
        _mm_redraw()


def _mm_redraw():
    D = "flowc_mmdraw"
    if not dpg.does_item_exist(D) or not dpg.is_item_shown("flowc_mm"):
        return
    dpg.delete_item(D, children_only=True)
    dpg.draw_rectangle((0, 0), (MM_W, MM_H), fill=(16, 19, 28),
                       color=(74, 158, 255), parent=D)
    for s in FS["syms"].values():
        if not _in_scope(s):
            continue
        col = COL.get(s["kind"], COL["flow_process"])
        dpg.draw_rectangle((s["x"] * MM_F, s["y"] * MM_F),
                           ((s["x"] + s["w"]) * MM_F,
                            (s["y"] + s["h"]) * MM_F),
                           fill=col, parent=D)
    try:                       # the visible-region rectangle
        z = FS["zoom"]
        vx = dpg.get_x_scroll("flowc_wrap") / z
        vy = dpg.get_y_scroll("flowc_wrap") / z
        vw, vh = dpg.get_item_rect_size("flowc_wrap")
        dpg.draw_rectangle((vx * MM_F, vy * MM_F),
                           ((vx + vw / z) * MM_F, (vy + vh / z) * MM_F),
                           color=(238, 240, 245), thickness=1, parent=D)
    except Exception:                           # noqa: BLE001
        pass


_MM_LAST = [None]


def _mm_tick():
    """Obedient tracking: refresh the minimap whenever the canvas scroll
    or zoom changes (scrollbars, wheel, Home — anything)."""
    try:
        cur = (round(dpg.get_x_scroll("flowc_wrap"), 1),
               round(dpg.get_y_scroll("flowc_wrap"), 1),
               FS["zoom"])
        if cur != _MM_LAST[0]:
            _MM_LAST[0] = cur
            _mm_redraw()
        dpg.set_frame_callback(dpg.get_frame_count() + 12, _mm_tick)
    except Exception:                           # noqa: BLE001
        pass


def _mm_jump():
    """Click on the minimap -> centre the canvas there."""
    mx, my = dpg.get_drawing_mouse_pos()
    z = FS["zoom"]
    cx, cy = mx / MM_F * z, my / MM_F * z
    try:
        vw, vh = dpg.get_item_rect_size("flowc_wrap")
        dpg.set_x_scroll("flowc_wrap", max(0, cx - vw / 2))
        dpg.set_y_scroll("flowc_wrap", max(0, cy - vh / 2))
    except Exception:                           # noqa: BLE001
        pass
    _mm_redraw()
STYLE = {}


def snap(v):
    return round(v / GRID) * GRID


def _status(msg, ok=True):
    dpg.set_value("flowc_status", msg)
    dpg.configure_item("flowc_status",
                       color=STYLE.get("GRN" if ok else "AMB"))


def _selinfo(msg=""):
    dpg.set_value("flowc_selinfo", msg)


# ── undo / redo ─────────────────────────────────────────────────────────────
def _snapshot():
    FS["dirty"] = True
    FS["undo"].append(json.dumps({"s": FS["syms"], "e": FS["edges"],
                                  "n": FS["next"]}))
    FS["undo"] = FS["undo"][-50:]
    FS["redo"].clear()


def _restore(blob):
    d = json.loads(blob)
    FS["syms"] = {int(k): v for k, v in d["s"].items()}
    FS["edges"] = d["e"]
    FS["next"] = d["n"]
    if FS["sel"] not in FS["syms"]:
        FS["sel"] = None
    FS["sel_edge"] = None
    redraw()


def undo(*_):
    if not FS["undo"]:
        _status("nothing to undo", ok=False)
        return
    FS["redo"].append(json.dumps({"s": FS["syms"], "e": FS["edges"],
                                  "n": FS["next"]}))
    _restore(FS["undo"].pop())
    _status("undone")


def redo(*_):
    if not FS["redo"]:
        _status("nothing to redo", ok=False)
        return
    FS["undo"].append(json.dumps({"s": FS["syms"], "e": FS["edges"],
                                  "n": FS["next"]}))
    _restore(FS["redo"].pop())
    _status("redone")


# ── model ops (Tk conventions verbatim) ─────────────────────────────────────
def add_symbol(kind, x, y, label=""):
    _snapshot()
    sid = FS["next"]
    FS["next"] += 1
    lbl = label or f"{kind.split('_', 1)[-1][0].upper()}{sid}"
    FS["syms"][sid] = {
        "id": sid, "kind": kind, "x": snap(x), "y": snap(y),
        "w": SYMBOL_W, "h": SYMBOL_H, "label": lbl,
        "name": f"{kind}_{sid}", "parent_scope": FS["scope"],
        "properties": [],
    }
    if kind in CONTAINER_KINDS:
        FS["syms"][sid]["entry_points"] = []
        FS["syms"][sid]["exit_points"] = []
    FS["sel"] = sid
    redraw()
    _status(f"placed {lbl}")
    return sid


def add_edge(src_id, dst_id, waypoints=None, bound_port_name=""):
    if src_id == dst_id or src_id not in FS["syms"] \
            or dst_id not in FS["syms"]:
        return None
    src, dst = FS["syms"][src_id], FS["syms"][dst_id]
    if not bound_port_name \
            and src.get("parent_scope") != dst.get("parent_scope"):
        _status("can't connect across pocket scopes — bind to a named "
                "port", ok=False)
        return None
    for e in FS["edges"]:
        if e["src"] == src_id and e["dst"] == dst_id:
            _status("edge already exists", ok=False)
            return None
    _snapshot()
    edge = {"src": src_id, "dst": dst_id,
            "waypoints": [list(w) for w in (waypoints or [])],
            "condition": ""}
    if bound_port_name:
        edge["bound_port_name"] = bound_port_name
    FS["edges"].append(edge)
    redraw()
    _status(f"Edge {FS['syms'][src_id]['label']} → "
            f"{FS['syms'][dst_id]['label']}")
    return edge


def delete_symbol(sid):
    if sid not in FS["syms"]:
        return
    _snapshot()
    lbl = FS["syms"][sid]["label"]
    FS["syms"].pop(sid)
    FS["raw"].pop(sid, None)
    FS["edges"] = [e for e in FS["edges"]
                   if e["src"] != sid and e["dst"] != sid]
    if FS["sel"] == sid:
        FS["sel"] = None
    redraw()
    _status(f"deleted {lbl} (+ its edges)")


def delete_edge(idx):
    if 0 <= idx < len(FS["edges"]):
        _snapshot()
        e = FS["edges"].pop(idx)
        FS["sel_edge"] = None
        redraw()
        _status(f"edge removed ({e['src']} → {e['dst']})")


def delete_selected(*_):
    if len(FS["multi"]) > 1:
        _snapshot()
        n = len(FS["multi"])
        for sid in list(FS["multi"]):
            FS["syms"].pop(sid, None)
            FS["raw"].pop(sid, None)
        FS["edges"] = [e for e in FS["edges"]
                       if e["src"] in FS["syms"] and e["dst"] in FS["syms"]]
        FS["multi"] = set()
        FS["sel"] = None
        redraw()
        _status(f"deleted {n} symbols (+ their edges)")
    elif FS["sel"] is not None:
        delete_symbol(FS["sel"])
    elif FS["sel_edge"] is not None:
        delete_edge(FS["sel_edge"])


def _lasso_apply(rect):
    """Select every symbol intersecting the lasso rectangle."""
    x0, y0, x1, y1 = rect
    hits = {sid for sid, s in FS["syms"].items()
            if s["x"] < x1 and s["x"] + s["w"] > x0
            and s["y"] < y1 and s["y"] + s["h"] > y0
            and _in_scope(s)}
    FS["multi"] = hits
    FS["sel"] = next(iter(hits)) if len(hits) == 1 else None
    redraw()
    if hits:
        _selinfo(f"lasso: {len(hits)} selected — drag any to move the "
                 "group · Del deletes all")
        _status(f"{len(hits)} symbols selected")
    else:
        _selinfo("")


def clear_all(*_):
    if not FS["syms"] and not FS["edges"]:
        return
    _snapshot()
    FS["syms"].clear()
    FS["raw"].clear()
    FS["edges"].clear()
    FS["sel"] = FS["sel_edge"] = None
    redraw()
    _status("canvas cleared")


# ── geometry ────────────────────────────────────────────────────────────────
def _center(s):
    return (s["x"] + s["w"] / 2, s["y"] + s["h"] / 2)


def _border_point(s, toward):
    """Point on s's rectangle border along the line centre->toward."""
    cx, cy = _center(s)
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return (cx, cy)
    tx = (s["w"] / 2) / abs(dx) if dx else math.inf
    ty = (s["h"] / 2) / abs(dy) if dy else math.inf
    t = min(tx, ty)
    return (cx + dx * t, cy + dy * t)


def _edge_points(e):
    src, dst = FS["syms"].get(e["src"]), FS["syms"].get(e["dst"])
    if not src or not dst:
        return []
    pts = [_center(src)] + [tuple(p) for p in e.get("waypoints", [])] \
        + [_center(dst)]
    first = _border_point(src, pts[1])
    last = _border_point(dst, pts[-2])
    return [first] + pts[1:-1] + [last]


def _seg_dist(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _hit_symbol(mx, my):
    for sid in reversed(list(FS["syms"])):
        s = FS["syms"][sid]
        if s["x"] <= mx <= s["x"] + s["w"] and s["y"] <= my <= s["y"] + s["h"]:
            return sid
    return None


def _hit_edge(mx, my):
    for i, e in enumerate(FS["edges"]):
        pts = _edge_points(e)
        for a, b in zip(pts, pts[1:]):
            if _seg_dist((mx, my), a, b) <= 8:
                return i
    return None


# ── drawing ─────────────────────────────────────────────────────────────────
def _draw_symbol(s, selected):
    D = "flowc_draw"
    Z = FS["zoom"]
    x, y, w, h = s["x"] * Z, s["y"] * Z, s["w"] * Z, s["h"] * Z
    fill = COL.get(s["kind"], COL["flow_process"])
    border = COL["selected"] if selected else COL["border"]
    th = 3 if selected else 2
    k = s["kind"]
    if k == "flow_terminator":
        dpg.draw_rectangle((x, y), (x + w, y + h), fill=fill, color=border,
                           thickness=th, rounding=h / 2, parent=D)
    elif k == "flow_decision":
        cx, cy = x + w / 2, y + h / 2
        dpg.draw_quad((cx, y), (x + w, cy), (cx, y + h), (x, cy),
                      fill=fill, color=border, thickness=th, parent=D)
    elif k == "flow_io":
        sk = 16
        dpg.draw_quad((x + sk, y), (x + w, y), (x + w - sk, y + h),
                      (x, y + h), fill=fill, color=border, thickness=th,
                      parent=D)
    else:                                   # process (and subroutine kin)
        dpg.draw_rectangle((x, y), (x + w, y + h), fill=fill, color=border,
                           thickness=th, parent=D)
    lbl = s.get("label", "")
    dpg.draw_text((x + w / 2 - len(lbl) * 4.2 * Z, y + h / 2 - 8 * Z), lbl,
                  size=15 * Z, color=STYLE.get("TEXT", (238, 240, 245)),
                  parent=D)
    kindword = s["kind"].split("_", 1)[-1]
    dpg.draw_text((x + w / 2 - len(kindword) * 3.2 * Z, y + h + 4 * Z),
                  kindword, size=max(8, 11 * Z),
                  color=STYLE.get("DIM", (168, 175, 190)), parent=D)
    if selected:
        dpg.draw_text((x, y - 16 * Z), f"({s['x']},{s['y']})", size=12 * Z,
                      color=COL["selected"], parent=D)


def redraw():
    _mm_redraw()
    D = "flowc_draw"
    Z = FS["zoom"]
    if dpg.does_item_exist(D):
        dpg.configure_item(D, width=int(CANVAS_W * Z),
                           height=int(CANVAS_H * Z))
    dpg.delete_item(D, children_only=True)
    for gx in range(0, CANVAS_W + 1, GRID):
        dpg.draw_line((gx * Z, 0), (gx * Z, CANVAS_H * Z),
                      color=(40, 46, 62, 80), parent=D)
    for gy in range(0, CANVAS_H + 1, GRID):
        dpg.draw_line((0, gy * Z), (CANVAS_W * Z, gy * Z),
                      color=(40, 46, 62, 80), parent=D)
    for i, e in enumerate(FS["edges"]):
        s1 = FS["syms"].get(e["src"])
        s2 = FS["syms"].get(e["dst"])
        if not s1 or not s2 or not _in_scope(s1) or not _in_scope(s2):
            continue
        pts = [(px * Z, py * Z) for px, py in _edge_points(e)]
        if len(pts) < 2:
            continue
        col = COL["selected"] if i == FS["sel_edge"] else COL["border"]
        for a, b in zip(pts, pts[1:-1]):
            dpg.draw_line(a, b, color=col, thickness=2, parent=D)
        dpg.draw_arrow(pts[-1], pts[-2], color=col, thickness=2,
                       size=8 * Z, parent=D)
        if i == FS["sel_edge"]:
            for wx, wy in e.get("waypoints", []):
                dpg.draw_rectangle((wx * Z - 4, wy * Z - 4),
                                   (wx * Z + 4, wy * Z + 4),
                                   fill=COL["selected"], parent=D)
        if e.get("condition"):
            mx = (pts[0][0] + pts[-1][0]) / 2
            my = (pts[0][1] + pts[-1][1]) / 2
            dpg.draw_text((mx + 4, my - 14 * Z), e["condition"],
                          size=12 * Z, color=STYLE.get("DIM"), parent=D)
    for sid, s in FS["syms"].items():
        if not _in_scope(s):
            continue                        # other scopes render when entered
        _draw_symbol(s, sid == FS["sel"] or sid in FS["multi"])
        if s.get("kind") in CONTAINER_KINDS:   # 📦 on EVERY container:
            solid = _has_pocket(s)             # solid = inhabited,
            bx = (s["x"] + s["w"]) * Z         # hollow = empty pocket
            by = s["y"] * Z
            dpg.draw_rectangle((bx - 14 * Z, by + 2 * Z),
                               (bx - 2 * Z, by + 12 * Z),
                               fill=(240, 180, 80) if solid else None,
                               color=(240, 180, 80),
                               parent="flowc_draw")
            dpg.draw_line((bx - 14 * Z, by + 5 * Z),
                          (bx - 2 * Z, by + 5 * Z),
                          color=(120, 90, 40) if solid
                          else (240, 180, 80), parent="flowc_draw")
        pp = _port_positions(s)
        for port, px, py in pp["entry"]:
            dpg.draw_circle((px * Z, py * Z), 4.5 * Z,
                            fill=(80, 200, 255), parent="flowc_draw")
            dpg.draw_text(((px + 7) * Z, (py - 7) * Z),
                          str(port.get("name", "")), size=10 * Z,
                          color=(80, 200, 255), parent="flowc_draw")
        for port, px, py in pp["exit"]:
            dpg.draw_circle((px * Z, py * Z), 4.5 * Z,
                            fill=(63, 208, 143), parent="flowc_draw")
            dpg.draw_text(((px - 40) * Z, (py - 7) * Z),
                          str(port.get("name", "")), size=10 * Z,
                          color=(63, 208, 143), parent="flowc_draw")
    if FS["lasso"] is not None:
        Z = FS["zoom"]
        ax, ay = FS["lasso"]["a"]
        bx, by = FS["lasso"]["b"]
        dpg.draw_rectangle((ax * Z, ay * Z), (bx * Z, by * Z),
                           color=COL["selected"], thickness=1,
                           fill=(255, 107, 53, 24), parent="flowc_draw")


# ── tools + mouse ───────────────────────────────────────────────────────────
# ── toolbar eye-candy: drawn shape/tool icons + Tk action colours ──────────
def _sym_icon(kind):
    col = COL.get(kind, COL["flow_process"])

    def draw(D):
        if kind == "flow_terminator":
            dpg.draw_rectangle((4, 5), (44, 25), fill=col,
                               color=COL["border"], rounding=10, parent=D)
        elif kind == "flow_decision":
            dpg.draw_quad((24, 3), (45, 15), (24, 27), (3, 15), fill=col,
                          color=COL["border"], parent=D)
        elif kind == "flow_io":
            dpg.draw_quad((10, 5), (46, 5), (38, 25), (2, 25), fill=col,
                          color=COL["border"], parent=D)
        else:
            dpg.draw_rectangle((4, 5), (44, 25), fill=col,
                               color=COL["border"], parent=D)
    return draw


def _tool_icon(name):
    def draw(D):
        if name == "select":
            dpg.draw_triangle((16, 4), (16, 24), (28, 18),
                              fill=(238, 240, 245), parent=D)
            dpg.draw_line((24, 17), (32, 26), color=(238, 240, 245),
                          thickness=3, parent=D)
        elif name == "delete":
            dpg.draw_line((14, 6), (34, 24), color=COL["selected"],
                          thickness=4, parent=D)
            dpg.draw_line((34, 6), (14, 24), color=COL["selected"],
                          thickness=4, parent=D)
        elif name == "edge":
            dpg.draw_arrow((42, 8), (6, 24), color=COL["border"],
                           thickness=3, size=10, parent=D)
    return draw


def _icon_btn(draw_fn, label, sub, tool):
    """A toolbar row: drawn icon + button; both select the tool."""
    with dpg.group(horizontal=True):
        dl = dpg.add_drawlist(width=50, height=30)
        draw_fn(dl)
        with dpg.group():
            dpg.add_button(label=label, width=-1, user_data=tool,
                           callback=set_tool)
            if sub:
                dpg.add_text(" " + sub, color=STYLE.get("DIM"))
    with dpg.item_handler_registry() as h:
        dpg.add_item_clicked_handler(
            callback=lambda s, a, u=tool: set_tool(None, None, u))
    dpg.bind_item_handler_registry(dl, h)


def _act_icon(name):
    W = (238, 240, 245)

    def draw(D):
        if name == "save":                      # floppy
            dpg.draw_rectangle((6, 4), (34, 26), fill=(52, 90, 150),
                               color=W, parent=D)
            dpg.draw_rectangle((12, 4), (28, 12), fill=(20, 23, 32),
                               color=W, parent=D)
            dpg.draw_rectangle((11, 16), (29, 26), fill=(200, 205, 215),
                               parent=D)
        elif name == "open":                    # folder
            dpg.draw_quad((5, 8), (16, 8), (19, 12), (5, 12),
                          fill=(240, 180, 80), parent=D)
            dpg.draw_rectangle((5, 11), (35, 26), fill=(240, 180, 80),
                               color=(180, 130, 50), parent=D)
        elif name == "import":                  # folder + in-arrow
            dpg.draw_rectangle((5, 11), (35, 26), fill=(240, 180, 80),
                               color=(180, 130, 50), parent=D)
            dpg.draw_arrow((20, 22), (20, 2), color=(63, 208, 143),
                           thickness=3, size=6, parent=D)
        elif name == "clear":                   # trash can
            dpg.draw_rectangle((10, 10), (30, 26), fill=(120, 60, 60),
                               color=W, parent=D)
            dpg.draw_rectangle((7, 6), (33, 10), fill=(160, 80, 80),
                               color=W, parent=D)
            dpg.draw_line((16, 13), (16, 23), color=W, parent=D)
            dpg.draw_line((24, 13), (24, 23), color=W, parent=D)
        elif name == "stop":                    # red square
            dpg.draw_rectangle((9, 6), (29, 24), fill=(220, 80, 80),
                               color=(255, 136, 136), parent=D)
        elif name == "learn":                   # mini neural graph
            pts = [(10, 8), (10, 22), (24, 15), (34, 8), (34, 22)]
            for a2 in (0, 1):
                for b2 in (2,):
                    dpg.draw_line(pts[a2], pts[b2], color=(122, 255, 204),
                                  parent=D)
            for b2 in (3, 4):
                dpg.draw_line(pts[2], pts[b2], color=(122, 255, 204),
                              parent=D)
            for p2 in pts:
                dpg.draw_circle(p2, 3.4, fill=(122, 255, 204), parent=D)
        elif name == "suggest":                 # light bulb
            dpg.draw_circle((20, 12), 8, fill=(255, 204, 68),
                            color=(200, 160, 50), parent=D)
            dpg.draw_rectangle((16, 20), (24, 26), fill=(160, 130, 60),
                               parent=D)
            for ang in ((6, 2), (34, 2), (4, 14), (36, 14)):
                dpg.draw_line((20, 12), ang, color=(255, 204, 68),
                              parent=D)
            dpg.draw_circle((20, 12), 8, fill=(255, 204, 68),
                            color=(200, 160, 50), parent=D)
    return draw


def _icon_act(draw_fn, label, cb, fg=None):
    """Action row with a DRAWN icon (font-independent), icon clickable."""
    with dpg.group(horizontal=True):
        dl = dpg.add_drawlist(width=38, height=28)
        draw_fn(dl)
        _abtn(label, cb, fg)
    with dpg.item_handler_registry() as h:
        dpg.add_item_clicked_handler(callback=lambda *_: cb())
    dpg.bind_item_handler_registry(dl, h)


def _abtn(label, cb, fg=None):
    """Action button with the Tk face's accent colours."""
    b = dpg.add_button(label=label, width=-1, callback=cb)
    if fg:
        with dpg.theme() as th:
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Text, fg)
        dpg.bind_item_theme(b, th)
    return b


def set_tool(sender, app_data, tool):
    FS["tool"] = tool
    FS["edge_src"] = None
    names = {"select": "Select — click/drag symbols · drag empty canvas "
                       "to LASSO a group · dbl-click renames",
             "delete": "Delete — click a symbol or edge to delete it",
             "edge": "Edge — click the SOURCE symbol"}
    label = names.get(tool, f"place {tool.split('_', 1)[-1]} — "
                            "click the canvas")
    dpg.set_value("flowc_tool", f"tool: {label}")


def _on_click(*_):
    if dpg.does_item_exist("flowc_mmdraw") \
            and dpg.is_item_hovered("flowc_mmdraw"):
        _mm_jump()
        return
    if not dpg.is_item_hovered("flowc_draw"):
        return
    mx, my = _mpos()
    tool = FS["tool"]
    if tool == "select":
        for sy in FS["syms"].values():      # 📦 drill-in, top-right ±14
            if not _in_scope(sy) \
                    or sy.get("kind") not in CONTAINER_KINDS:
                continue
            bx, by = sy["x"] + sy["w"], sy["y"]
            if abs(mx - bx) <= 14 and abs(my - by) <= 14:
                set_scope(sy["name"])
                return
    if tool.startswith("flow_"):
        add_symbol(tool, mx - SYMBOL_W / 2, my - SYMBOL_H / 2)
        FS["tool"] = "select"
        set_tool(None, None, "select")
        return
    if tool == "edge":
        sid = _hit_symbol(mx, my)
        if FS["edge_src"] is None:
            if sid is None:
                set_tool(None, None, "select")
                _status("edge cancelled")
                return
            FS["edge_src"] = sid
            FS["edge_wps"] = []
            dpg.set_value("flowc_tool",
                          f"tool: Edge — {FS['syms'][sid]['label']} → click "
                          "DESTINATION (empty canvas adds a waypoint)")
            return
        port_hit = _port_at(mx, my)
        if port_hit is not None:            # 7c-4b: bind to a named port
            psym, _pedge, port = port_hit
            add_edge(FS["edge_src"], psym["id"], FS["edge_wps"],
                     bound_port_name=str(port.get("name", "")))
            FS["edge_src"] = None
            FS["edge_wps"] = []
            FS["tool"] = "select"
            set_tool(None, None, "select")
            return
        if sid is None:
            FS["edge_wps"].append([snap(mx), snap(my)])
            _status(f"waypoint {len(FS['edge_wps'])} — click the "
                    "destination symbol (or more waypoints)")
            return
        add_edge(FS["edge_src"], sid, FS["edge_wps"])
        FS["edge_src"] = None
        FS["edge_wps"] = []
        FS["tool"] = "select"
        set_tool(None, None, "select")
        return
    if tool == "delete":
        sid = _hit_symbol(mx, my)
        if sid is not None:
            delete_symbol(sid)
            return
        ei = _hit_edge(mx, my)
        if ei is not None:
            delete_edge(ei)
        return
    # select tool — a selected edge's waypoints are draggable handles
    if FS["sel_edge"] is not None and FS["sel_edge"] < len(FS["edges"]):
        e = FS["edges"][FS["sel_edge"]]
        for j, wp in enumerate(e.get("waypoints", [])):
            if math.hypot(mx - wp[0], my - wp[1]) <= 8:
                _snapshot()
                FS["wpdrag"] = {"e": FS["sel_edge"], "j": j,
                                "orig": (wp[0], wp[1])}
                return
    sid = _hit_symbol(mx, my)
    FS["sel_edge"] = None
    if sid is not None:
        if sid in FS["multi"] and len(FS["multi"]) > 1:
            _snapshot()          # group drag: move every selected symbol
            FS["sel"] = sid
            FS["drag"] = {"group": {i: (FS["syms"][i]["x"],
                                        FS["syms"][i]["y"])
                                    for i in FS["multi"]
                                    if i in FS["syms"]}}
            _selinfo(f"group of {len(FS['multi'])} — drag to move")
        else:
            FS["multi"] = {sid}
            FS["sel"] = sid
            s = FS["syms"][sid]
            _snapshot()
            FS["drag"] = {"orig": (s["x"], s["y"])}
            _selinfo(f"{s['label']}  {s['name']}  ({s['x']},{s['y']})")
    else:
        ei = _hit_edge(mx, my)
        FS["sel_edge"] = ei
        FS["sel"] = None
        FS["multi"] = set()
        if ei is not None:
            e = FS["edges"][ei]
            _selinfo(f"Edge  {FS['syms'][e['src']]['label']} → "
                     f"{FS['syms'][e['dst']]['label']}  "
                     f"({len(e.get('waypoints', []))} waypoints)")
        else:                    # empty canvas: begin the lasso
            FS["lasso"] = {"a": (mx, my), "b": (mx, my)}
            _selinfo("")
    redraw()


def _on_drag(sender, app_data):
    if dpg.is_item_active("flowc_grip") and FS["grip"] is None:
        FS["grip"] = dpg.get_item_width("flowc_panel") or 185
    if FS["grip"] is not None:
        _b, gdx, _gdy = app_data
        dpg.configure_item("flowc_panel",
                           width=max(140, min(int(FS["grip"] + gdx), 480)))
        return
    if FS["wpdrag"] is not None:
        _b, dx, dy = app_data
        z = FS["zoom"]
        w = FS["wpdrag"]
        try:
            wp = FS["edges"][w["e"]]["waypoints"][w["j"]]
            wp[0] = w["orig"][0] + dx / z
            wp[1] = w["orig"][1] + dy / z
            redraw()
        except (IndexError, KeyError):
            FS["wpdrag"] = None
        return
    if FS["lasso"] is not None:
        _b, dx, dy = app_data
        z = FS["zoom"]
        ax, ay = FS["lasso"]["a"]
        FS["lasso"]["b"] = (ax + dx / z, ay + dy / z)
        redraw()
        return
    if FS["drag"] is None:
        return
    _b, dx, dy = app_data
    z = FS["zoom"]
    if "group" in FS["drag"]:
        for i, (ox, oy) in FS["drag"]["group"].items():
            gs = FS["syms"].get(i)
            if gs:
                gs["x"] = max(0, int(ox + dx / z))
                gs["y"] = max(0, int(oy + dy / z))
        redraw()
        return
    if FS["sel"] is None:
        return
    s = FS["syms"].get(FS["sel"])
    if s is None:
        return
    ox, oy = FS["drag"]["orig"]
    s["x"], s["y"] = max(0, int(ox + dx / z)), max(0, int(oy + dy / z))
    redraw()


def _on_release(*_):
    if FS["wpdrag"] is not None:
        w = FS["wpdrag"]
        FS["wpdrag"] = None
        try:
            wp = FS["edges"][w["e"]]["waypoints"][w["j"]]
            wp[0], wp[1] = snap(wp[0]), snap(wp[1])
            redraw()
        except (IndexError, KeyError):
            pass
    if FS["grip"] is not None:
        FS["grip"] = None
        cfg = STYLE.get("CFG")
        if cfg is not None:
            cfg["flow_panel_w"] = dpg.get_item_width("flowc_panel")
            if STYLE.get("SAVE"):
                STYLE["SAVE"]()
    if FS["lasso"] is not None:
        ax, ay = FS["lasso"]["a"]
        bx, by = FS["lasso"]["b"]
        FS["lasso"] = None
        _lasso_apply((min(ax, bx), min(ay, by), max(ax, bx), max(ay, by)))
        return
    if FS["drag"] is None:
        return
    grp = FS["drag"].get("group") if isinstance(FS["drag"], dict) else None
    FS["drag"] = None
    if grp:
        for i in grp:
            gs = FS["syms"].get(i)
            if gs:
                gs["x"], gs["y"] = max(0, snap(gs["x"])), max(0, snap(gs["y"]))
        redraw()
        return
    s = FS["syms"].get(FS["sel"])
    if s:
        s["x"], s["y"] = max(0, snap(s["x"])), max(0, snap(s["y"]))
        _selinfo(f"{s['label']}  {s['name']}  ({s['x']},{s['y']})")
        redraw()


def _on_dblclick(*_):
    if not dpg.is_item_hovered("flowc_draw"):
        return
    mx, my = _mpos()
    sid = _hit_symbol(mx, my)
    if sid is None:
        return
    FS["sel"] = sid
    redraw()
    tag = "flowc_rename"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    with dpg.window(label="Rename symbol", tag=tag, modal=True, width=360,
                    height=130, pos=(400, 260)):
        inp = dpg.add_input_text(default_value=FS["syms"][sid]["label"],
                                 width=-1)

        def apply():
            _snapshot()
            FS["syms"][sid]["label"] = dpg.get_value(inp).strip() \
                or FS["syms"][sid]["label"]
            dpg.delete_item(tag)
            redraw()
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Rename  ", callback=apply)
            dpg.add_button(label="Cancel",
                           callback=lambda: dpg.delete_item(tag))


def show_ports(*_):
    """Port editor for the selected container (7c-4b)."""
    sid = FS["sel"]
    sym = FS["syms"].get(sid) if sid is not None else None
    if sym is None or sym.get("kind") not in CONTAINER_KINDS:
        _status("select a Process/Subroutine first — ports live on "
                "containers", ok=False)
        return
    tag = "flowc_ports"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)

    def refresh():
        for lst, key in (("fpl_entry", "entry_points"),
                         ("fpl_exit", "exit_points")):
            dpg.delete_item(lst, children_only=True)
            for i, p in enumerate(sym.get(key) or []):
                with dpg.group(horizontal=True, parent=lst):
                    dpg.add_text(str(p.get("name", "?")))
                    dpg.add_button(label=" x ", user_data=(key, i),
                                   callback=lambda s2, a2, u:
                                   (_snapshot(),
                                    sym[u[0]].pop(u[1]),
                                    refresh(), redraw()))

    def add(key, inp):
        nm = dpg.get_value(inp).strip()
        if not nm:
            return
        _snapshot()
        sym.setdefault(key, []).append({"name": nm})
        dpg.set_value(inp, "")
        refresh()
        redraw()

    with dpg.window(label=f"Ports — {sym['label']}", tag=tag, modal=True,
                    width=460, height=360, pos=(380, 200)):
        dpg.add_text("Entry ports (left edge) / exit ports (right edge). "
                     "Edges from other scopes bind to these by name.",
                     color=STYLE.get("DIM"))
        with dpg.group(horizontal=True):
            with dpg.group():
                dpg.add_text("ENTRY", color=(80, 200, 255))
                with dpg.child_window(tag="fpl_entry", width=200,
                                      height=180):
                    pass
                ei = dpg.add_input_text(width=140, hint="port name")
                dpg.add_button(label=" + entry ",
                               callback=lambda s2, a2, u=None:
                               add("entry_points", ei))
            with dpg.group():
                dpg.add_text("EXIT", color=(63, 208, 143))
                with dpg.child_window(tag="fpl_exit", width=200,
                                      height=180):
                    pass
                xi = dpg.add_input_text(width=140, hint="port name")
                dpg.add_button(label=" + exit ",
                               callback=lambda s2, a2, u=None:
                               add("exit_points", xi))
        dpg.add_button(label="  Close  ",
                       callback=lambda: dpg.delete_item(tag))
    refresh()


def _on_esc(*_):
    if dpg.is_item_hovered("flowc_draw") or dpg.is_item_hovered("flowc_wrap"):
        leave_scope()


def _on_del_key(*_):
    if dpg.is_item_hovered("flowc_wrap") or dpg.is_item_hovered("flowc_draw"):
        delete_selected()


# ── save / open (Tk schema; .fc sections preserved) ─────────────────────────
def _payload(path):
    ext = os.path.splitext(path)[1].lower()
    syms = []
    for sid, s in FS["syms"].items():
        merged = dict(FS["raw"].get(sid, {}))
        merged.update(s)
        syms.append(merged)
    doc = dict(FS["rawdoc"]) if FS["rawdoc"] else {
        "ternoo_version": "0.3", "source_type": "ternoo_design",
        "word_stream": [], "symbols": [], "edges": [],
        "cmd_symbols": [], "cmd_edges": [],
        "cell_symbols": [], "sheet_regions": [], "free_cells": [],
        "sequence": [],
    }
    doc["source_file"] = os.path.basename(path)
    doc["flow_symbols"] = syms
    doc["flow_edges"] = [dict(e) for e in FS["edges"]]
    if ext == ".flow":                      # flow-only partial, per policy
        doc["symbols"] = []
        doc["edges"] = []
        doc["cmd_symbols"] = doc["cmd_edges"] = []
        doc["cell_symbols"] = doc["sheet_regions"] = doc["free_cells"] = []
    meta = dict(doc.get("tgui_meta", {}))
    meta.update({"flow_symbol_count": len(syms),
                 "flow_edge_count": len(FS["edges"]),
                 "widget_count": len(doc.get("symbols", [])),
                 "edge_count": len(doc.get("edges", []))})
    doc["tgui_meta"] = meta
    return doc


def _picked(app_data):
    sels = app_data.get("selections") or {}
    if sels:
        return list(sels.values())[0]
    p = app_data.get("file_path_name", "")
    return p[:-2] if p.endswith(".*") else p


def save_to(path):
    if not path.endswith((".flow", ".fc")):
        path += ".flow"
    try:
        json.dump(_payload(path), open(path, "w", encoding="utf-8"),
                  indent=1)
        FS["file"] = path
        FS["dirty"] = False
        kept = " (other .fc sections preserved)" \
            if FS["rawdoc"] and path.endswith(".fc") else ""
        _status(f"saved {os.path.basename(path)} — {len(FS['syms'])} "
                f"symbols, {len(FS['edges'])} edges{kept}")
    except Exception as e:                      # noqa: BLE001
        _status(f"save failed: {e}", ok=False)


def load_from(path):
    try:
        doc = json.load(open(path, encoding="utf-8"))
    except Exception as e:                      # noqa: BLE001
        _status(f"open failed: {e}", ok=False)
        return
    FS["rawdoc"] = doc
    FS["syms"].clear()
    FS["raw"].clear()
    FS["sel"] = FS["sel_edge"] = None
    FS["undo"].clear()
    FS["redo"].clear()
    for sym in doc.get("flow_symbols", []):
        sid = int(sym["id"])
        FS["syms"][sid] = {
            "id": sid, "kind": sym.get("kind", "flow_process"),
            "x": sym.get("x", 0), "y": sym.get("y", 0),
            "w": sym.get("w", SYMBOL_W), "h": sym.get("h", SYMBOL_H),
            "label": sym.get("label", ""),
            "name": sym.get("name", f"{sym.get('kind', 'flow')}_{sid}"),
            "parent_scope": sym.get("parent_scope"),
            "properties": list(sym.get("properties", [])),
        }
        if sym.get("kind") in CONTAINER_KINDS:
            FS["syms"][sid]["entry_points"] = list(
                sym.get("entry_points", []))
            FS["syms"][sid]["exit_points"] = list(
                sym.get("exit_points", []))
        FS["raw"][sid] = dict(sym)
        FS["next"] = max(FS["next"], sid + 1)
    FS["edges"] = [dict(e) for e in doc.get("flow_edges", [])]
    FS["file"] = path
    FS["dirty"] = False
    FS["scope"] = None
    _build_breadcrumb()
    nested = sum(1 for s in FS["syms"].values()
                 if s.get("parent_scope") is not None)
    redraw()
    note = f" ({nested} in pockets — 📦 on their containers to enter)" \
        if nested else ""
    _status(f"opened {os.path.basename(path)} — {len(FS['syms'])} symbols, "
            f"{len(FS['edges'])} edges{note}")


def _save_clicked(*_):
    if FS["file"]:
        save_to(FS["file"])
    else:
        dpg.show_item("flowc_save_dlg")


# ── build ───────────────────────────────────────────────────────────────────
def build_flow_tab(style):
    STYLE.update(style)
    C = STYLE
    _designs = os.path.dirname(os.path.abspath(__file__))
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         tag="flowc_save_dlg", width=780, height=480,
                         default_path=_designs, default_filename="design",
                         callback=lambda s, a: save_to(_picked(a))):
        dpg.add_file_extension(".flow", color=(74, 158, 255))
        dpg.add_file_extension(".fc", color=(63, 208, 143))
        dpg.add_file_extension(".*")
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         tag="flowc_open_dlg", width=780, height=480,
                         default_path=_designs, default_filename="",
                         callback=lambda s, a: load_from(_picked(a))):
        dpg.add_file_extension(".fc", color=(63, 208, 143))
        dpg.add_file_extension(".flow", color=(74, 158, 255))
        dpg.add_file_extension(".*")
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         tag="flowc_import_dlg", width=780, height=480,
                         default_path=_designs, default_filename="",
                         callback=lambda s, a: _import_merge(_picked(a))):
        dpg.add_file_extension(".fc", color=(63, 208, 143))
        dpg.add_file_extension(".flow", color=(74, 158, 255))
        dpg.add_file_extension(".*")

    with dpg.group(horizontal=True):
        with dpg.child_window(width=int(C.get("CFG", {})
                              .get("flow_panel_w", 320)),
                              tag="flowc_panel"):
            with dpg.collapsing_header(label="TOOLS", default_open=True):
                _icon_btn(_tool_icon("select"), " Select ", "move · edit",
                          "select")
                _icon_btn(_tool_icon("delete"), " Delete ", "click to del",
                          "delete")
            with dpg.collapsing_header(label="SYMBOLS → UDP",
                                       default_open=True):
                for kind, name, sub in KINDS:
                    _icon_btn(_sym_icon(kind), f" {name} ", sub, kind)
            with dpg.collapsing_header(label="CONNECT → EXEC",
                                       default_open=True):
                _icon_btn(_tool_icon("edge"), " Edge ", "src→[wp]→dst",
                          "edge")
                _abtn(" Ports... ", show_ports, (80, 200, 255))
                dpg.add_text("  the 📦 on any Process /\n  Subroutine "
                             "opens its pocket\n  (hollow = empty) · Esc "
                             "goes up", color=C["DIM"])
            with dpg.collapsing_header(label="ACTIONS", default_open=True):
                _abtn(" ⬇ Word Dump ", do_word_dump)
                _abtn(" ▶ Load→EMU (native) ", do_load_emu,
                      (122, 255, 122))
                _abtn(" ▶ Step ", do_step, (255, 221, 87))
                _abtn(" ▶▶ Run (SDL) ", do_run_sdl, (122, 255, 122))
                _icon_act(_act_icon("stop"), " Stop ", do_stop,
                          (255, 136, 136))
                _icon_act(_act_icon("learn"), " Learn ", do_learn,
                          (122, 255, 204))
                _icon_act(_act_icon("suggest"), " Suggest ", do_suggest,
                          (255, 204, 68))
                dpg.add_spacer(height=4)
                _icon_act(_act_icon("save"), " Save ", _save_clicked)
                _icon_act(_act_icon("save"), " Save as... ",
                          lambda: dpg.show_item("flowc_save_dlg"))
                _icon_act(_act_icon("open"), " Open ",
                          lambda: dpg.show_item("flowc_open_dlg"))
                _icon_act(_act_icon("import"), " Import ",
                          lambda: dpg.show_item("flowc_import_dlg"))
                _icon_act(_act_icon("clear"), " Clear ", clear_all)
                _abtn(" ↩ Undo ", undo)
                _abtn(" ↪ Redo ", redo)
            dpg.add_spacer(height=8)

        with dpg.child_window(width=10, height=-1, no_scrollbar=True,
                              border=False):
            dpg.add_button(tag="flowc_grip", label="", width=-1,
                           height=2600)
        with dpg.child_window(tag="flowc_wrap", width=-1,
                              horizontal_scrollbar=True):
            with dpg.group(horizontal=True, tag="flowc_crumbs"):
                pass
            with dpg.drawlist(width=CANVAS_W, height=CANVAS_H,
                              tag="flowc_draw"):
                pass
    dpg.add_text("", tag="flowc_selinfo", color=(74, 158, 255))
    with dpg.group(horizontal=True):
        dpg.add_text("tool: Select — click to select · drag to move · "
                     "dbl-click to rename", tag="flowc_tool", color=C["DIM"])
        dpg.add_text("   Zoom: 100%", tag="flowc_zoomlbl", color=C["DIM"])
        dpg.add_text("  Ctrl+wheel / Ctrl± zooms the canvas · drag the "
                     "divider for panel width", color=C["DIM"])
    dpg.add_text("Flow ready — reads/writes the Tk face's .fc/.flow",
                 tag="flowc_status", color=C["DIM"])
    with dpg.collapsing_header(label="Output", default_open=True):
        with dpg.group(horizontal=True):
            dpg.add_button(label=" clear output ", callback=_out_clear)
        with dpg.child_window(tag="flowc_out", height=170):
            dpg.add_text("execution output appears here — Word Dump · "
                         "Load→EMU (native C core) · Step (interpreter "
                         "walk with live highlight) · Run (compile + SDL "
                         "engine)", color=C["DIM"])

    _register_handlers()
    cfg0 = C.get("CFG", {})
    with dpg.window(tag="flowc_mm", no_title_bar=True, no_resize=True,
                    no_collapse=True, width=MM_W + 14, height=MM_H + 14,
                    pos=(int(cfg0.get("vp_w", 1460)) - MM_W - 60,
                         int(cfg0.get("vp_h", 980)) - MM_H - 90),
                    show=bool(cfg0.get("flow_minimap", True))):
        with dpg.drawlist(width=MM_W, height=MM_H, tag="flowc_mmdraw"):
            pass
    try:
        dpg.set_frame_callback(dpg.get_frame_count() + 12, _mm_tick)
    except Exception:                           # noqa: BLE001
        pass
    redraw()


def _selftest_exec():
    """Headless gate: dump -> compile -> interpret -> import round-trip."""
    E = _exec_mods()
    if E.get("err"):
        raise AssertionError(f"exec layer failed to load: {E['err']}")
    clear_all()
    FS["undo"].clear()
    a = add_symbol("flow_terminator", 200, 80, "START")
    b = add_symbol("flow_process", 200, 240)
    c2 = add_symbol("flow_terminator", 200, 400, "END")
    add_edge(a, b, [[400, 160]])
    add_edge(b, c2)
    canvas = _sync_canvas(E)
    words = canvas.to_word_program()
    assert words, "no words from canvas"
    ws = E["WS"].WordStream(words)
    meta, entry = _entry_meta()
    ws._flow_meta = meta
    ws._flow_edges = [dict(e) for e in FS["edges"]]
    t5 = E["CT"].compile_wordstream_to_t5asm(ws, source_path="gate")
    assert len(t5) > 100, "compile produced nothing"
    data = {"symbols": [{**s, "kind": BARE.get(s.get("kind", ""),
                                               "process")}
                        for s in FS["syms"].values()],
            "edges": [dict(e) for e in FS["edges"]]}
    interp = E["TI"].TernOOInterpreter(trace=False)
    interp.load_dict(data)
    res = interp.run()
    assert res.get("steps", 0) >= 3, f"interpreter walked {res}"
    import tempfile as _tf
    tmpf = os.path.join(_tf.gettempdir(), "fdpg-exec-test.flow")
    save_to(tmpf)
    _import_merge(tmpf)
    assert len(FS["syms"]) == 6, "import merge failed"
    clear_all()
    return {"words": len(words), "t5_chars": len(t5),
            "steps": res["steps"], "entry": entry}


def _register_handlers():
    with dpg.handler_registry():
        dpg.add_mouse_click_handler(dpg.mvMouseButton_Left,
                                    callback=_on_click)
        dpg.add_mouse_drag_handler(dpg.mvMouseButton_Left,
                                   callback=_on_drag)
        dpg.add_mouse_release_handler(dpg.mvMouseButton_Left,
                                      callback=_on_release)
        dpg.add_mouse_double_click_handler(dpg.mvMouseButton_Left,
                                           callback=_on_dblclick)
        dpg.add_key_press_handler(dpg.mvKey_Delete, callback=_on_del_key)
        dpg.add_key_press_handler(dpg.mvKey_Escape, callback=_on_esc)
