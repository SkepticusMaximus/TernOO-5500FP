#!/usr/bin/env python3
"""flowcode_dpg_mesh — the Mesh-Chat tab ORGAN of FlowCode's DPG face.

IN-PANE mount of the mesh conversation, maximally REUSED: this organ is
a thin UI over the standalone client's own non-UI core —
5500fp/mesh_chat_dpg.py is imported as a library (its module level
carries the MeshService buyer, the candidates() roster, the portable
ChatStore and the context builder; its UI only exists under launch).
One codebase, three doors: the FlowCode Tk tab, the standalone DPG
client, and now this pane — all reading the same saved chats.

DOCFLAG: the pane carries the CONVERSATION surface (ask, history,
saved chats). The workshop (macros / forge / editor+reviews) remains
the standalone client's specialty — the "Full client" button opens it.
"""
import importlib.util as _ilu
import os
import subprocess
import sys
import threading

import dearpygui.dearpygui as dpg

_HERE = os.path.dirname(os.path.abspath(__file__))
_FIVE = os.path.join(os.path.dirname(_HERE), "5500fp")

MS = {"chat_id": None, "created": None, "busy": False, "chats": []}
STYLE = {}
_MC = [None]
_MC_ERR = [""]


def _mc():
    if _MC[0] is None and not _MC_ERR[0]:
        try:
            spec = _ilu.spec_from_file_location(
                "mesh_chat_core", os.path.join(_FIVE, "mesh_chat_dpg.py"))
            mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _MC[0] = mod
        except Exception as e:                  # noqa: BLE001
            _MC_ERR[0] = str(e)
    return _MC[0]


def _status(msg, ok=True):
    dpg.set_value("meshc_status", msg)
    dpg.configure_item("meshc_status",
                       color=STYLE.get("GRN" if ok else "AMB"))


def _ui(fn):
    try:
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: fn())
    except Exception:                           # noqa: BLE001
        pass


def _append(who, text, color=None):
    dpg.add_text(who, parent="meshc_log",
                 color=color or STYLE.get("GRN"))
    dpg.add_text(text, parent="meshc_log", color=STYLE.get("TEXT"),
                 wrap=1000)
    dpg.add_spacer(height=6, parent="meshc_log")
    dpg.set_y_scroll("meshc_log", 999999.0)


def refresh_chats(select_cid=None):
    MC = _mc()
    if MC is None or MC.STORE is None:
        return
    MS["chats"] = [(cid, f"{ttl}  ·{str(cid)[-4:]}")
                   for cid, ttl, _u in MC.STORE.list()[:30]]
    dpg.configure_item("meshc_sel",
                       items=[lab for _c, lab in MS["chats"]])
    if select_cid:
        for cid, lbl in MS["chats"]:
            if cid == select_cid:
                dpg.set_value("meshc_sel", lbl)


def load_chat(sender=None, app_data=None):
    MC = _mc()
    if MC is None or MC.STORE is None:
        return
    lbl = dpg.get_value("meshc_sel")
    cid = next((c for c, l2 in MS["chats"] if l2 == lbl), None)
    if cid is None:
        return
    doc = MC.STORE.load(cid)
    if not doc:
        _status("couldn't load that chat", ok=False)
        return
    MS["chat_id"] = cid
    MS["created"] = doc.get("created")
    MC.HISTORY[:] = [(m.get("role", "user"), m.get("text", ""))
                     for m in doc.get("messages", [])]
    dpg.delete_item("meshc_log", children_only=True)
    for role, text in MC.HISTORY:
        _append("You" if role == "user" else "Professor", text,
                STYLE.get("DIM") if role == "user" else STYLE.get("GRN"))
    _status(f"continuing: {doc.get('title', '')} "
            f"({len(MC.HISTORY)} turns)")


def new_chat(*_):
    MC = _mc()
    if MC is None:
        return
    MC.HISTORY[:] = []
    MS["chat_id"] = None
    MS["created"] = None
    dpg.delete_item("meshc_log", children_only=True)
    _status("new conversation")


def _save_chat():
    MC = _mc()
    if MC is None or MC.STORE is None or not MC.HISTORY:
        return
    try:
        if MS["chat_id"] is None:
            MS["chat_id"] = MC.STORE.new_id()
        msgs = [{"role": r, "text": t} for r, t in MC.HISTORY]
        first = next((t for r, t in MC.HISTORY if r == "user"), "chat")
        MC.STORE.save(MS["chat_id"], MC.STORE.title_for(first), msgs,
                      created=MS["created"])
        refresh_chats(select_cid=MS["chat_id"])
    except Exception:                           # noqa: BLE001
        pass


def on_ask(*_):
    MC = _mc()
    if MC is None:
        _status(f"mesh core unavailable: {_MC_ERR[0]}", ok=False)
        return
    if MS["busy"]:
        _status("already thinking...", ok=False)
        return
    prompt = dpg.get_value("meshc_prompt").strip()
    if not prompt:
        _status("type a question first", ok=False)
        return
    MC.HISTORY.append(("user", prompt))
    _append("You", prompt, STYLE.get("DIM"))
    dpg.set_value("meshc_prompt", "")
    context = MC.build_context()
    MS["busy"] = True
    dpg.configure_item("meshc_ask", label="  ...thinking  ", enabled=False)
    _status("asking the mesh...")

    def work():
        where = ans = err = None
        try:
            where, ans = MC.BUYER.ask_mesh(context,
                                           candidates=MC.candidates())
        except Exception as e:                  # noqa: BLE001
            err = str(e)

        def done():
            MS["busy"] = False
            dpg.configure_item("meshc_ask", label="  Ask  ▶  ",
                               enabled=True)
            if err or not ans:
                _status(f"no answer: {err or 'no model answered'} — "
                        "check ⚙ nodes", ok=False)
                return
            MC.HISTORY.append(("assistant", ans))
            _append("Professor", ans)
            via = f"{where[0]}:{where[1]}" if isinstance(where, tuple) \
                else str(where)
            _status(f"answered via {via}")
            _save_chat()
        _ui(done)
    threading.Thread(target=work, daemon=True).start()


def launch_standalone(*_):
    subprocess.Popen([sys.executable,
                      os.path.join(_FIVE, "mesh_chat_dpg.py")])
    _status("standalone client launched (macros · forge · editor live "
            "there)")


def build_mesh_tab(style):
    STYLE.update(style)
    C = STYLE
    with dpg.group(horizontal=True):
        dpg.add_combo([], tag="meshc_sel", width=340, callback=load_chat)
        dpg.add_button(label=" New chat ", callback=new_chat)
        dpg.add_button(label=" Full client (workshop) ",
                       callback=launch_standalone)
    with dpg.child_window(tag="meshc_log", width=-1, height=-170):
        dpg.add_text("The mesh conversation, in-pane — same saved chats "
                     "as the standalone client and the Tk tab. Pick a "
                     "conversation above or just ask.", color=C["DIM"],
                     wrap=1000)
    with dpg.group(horizontal=True):
        dpg.add_input_text(tag="meshc_prompt", multiline=True, width=-150,
                           height=110,
                           hint="Ask the Professor...  (Ctrl+Enter sends)")
        dpg.add_button(label="  Ask  ▶  ", tag="meshc_ask", height=110,
                       callback=on_ask)
    dpg.add_text("mesh pane ready", tag="meshc_status", color=C["DIM"])

    def _ctrl_enter(sender, key):
        if key == dpg.mvKey_Return \
                and (dpg.is_key_down(dpg.mvKey_LControl)
                     or dpg.is_key_down(dpg.mvKey_RControl)) \
                and dpg.is_item_focused("meshc_prompt"):
            on_ask()
    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=_ctrl_enter)
    CLIP = STYLE.get("CLIP")
    if CLIP:
        CLIP.input_menu("meshc_prompt", "prompt")

        def _copy_last():
            MC = _mc()
            if MC:
                for role, text in reversed(MC.HISTORY):
                    if role == "assistant":
                        CLIP.clip_set(text)
                        return

        def _copy_all():
            MC = _mc()
            if MC:
                CLIP.clip_set("\n\n".join(
                    f"{'You' if r == 'user' else 'Professor'}: {t}"
                    for r, t in MC.HISTORY))
        CLIP.menu("meshc_log", [
            ("Copy last answer", _copy_last),
            ("Copy whole chat", _copy_all),
            ("Paste into prompt", lambda: dpg.set_value(
                "meshc_prompt", (dpg.get_value("meshc_prompt") or "")
                + CLIP.clip_get()))])
    if _mc() is not None:
        refresh_chats()
    else:
        _status(f"mesh core unavailable: {_MC_ERR[0]}", ok=False)


def _selftest():
    """Headless: core imports, context builds, blocks append (no network)."""
    MC = _mc()
    assert MC is not None, f"mesh core failed: {_MC_ERR[0]}"
    MC.HISTORY[:] = []
    MC.HISTORY.append(("user", "gate probe"))
    ctx = MC.build_context()
    assert "gate probe" in ctx
    _append("You", "gate probe (render check)", STYLE.get("DIM"))
    dpg.delete_item("meshc_log", children_only=True)
    MC.HISTORY[:] = []
    return {"core": True, "store": MC.STORE is not None}
