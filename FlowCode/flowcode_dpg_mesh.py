#!/usr/bin/env python3
"""flowcode_dpg_mesh — the Mesh-Chat tab ORGAN of FlowCode's DPG face.

THE FULL CLIENT, IN-PANE (captain's ruling 19-08: no pop-out hop — the
tab IS the client, built into the parent interface). The trick is total
reuse: 5500fp/mesh_chat_dpg.py's behaviour lives in module-level
functions bound to fixed tags (prompt/chat/maclist/fg_*/editor/
ed_notes/chatsel/status/…). This organ builds those SAME tags inside
the tab and delegates every action to the standalone's own functions —
ask, saved-chat pick/rename/export/delete, macro buttons + dialogs,
the Forge (AI-proposed pruning trees), the Editor with Professor
reviews, attachments, draggable seams (panel/ask-box/notes, remembered
in the shared config). One codebase, the same muscles, two mounts.

NOT wired from the standalone: its global zoom (FlowCode's shell owns
font scale + wheel), its clipboard sync + right-click layer (the CLIP
service is the app-wide text authority), its menu-bar chrome, and the
"FlowCode taste" node-editor demo (this IS FlowCode).
"""
import importlib.util as _ilu
import os
import threading

import dearpygui.dearpygui as dpg

_HERE = os.path.dirname(os.path.abspath(__file__))
_FIVE = os.path.join(os.path.dirname(_HERE), "5500fp")

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


def _theme_once(tag, kind, colors):
    if dpg.does_item_exist(tag):
        return
    with dpg.theme(tag=tag):
        with dpg.theme_component(kind):
            for which, col in colors:
                dpg.add_theme_color(which, col)


def _keys(sender, key):
    """Scoped keyboard: Ctrl+Enter asks (prompt focused), Ctrl+S saves
    the editor (editor focused). Nothing global — other tabs unbothered."""
    MC = _mc()
    if MC is None:
        return
    ctrl = (dpg.is_key_down(dpg.mvKey_LControl)
            or dpg.is_key_down(dpg.mvKey_RControl))
    if not ctrl:
        return
    if key == dpg.mvKey_Return and dpg.is_item_focused("prompt"):
        MC.on_ask()
    elif key == dpg.mvKey_S and dpg.is_item_focused("editor"):
        MC.ed_save()


def build_mesh_tab(style):
    STYLE.update(style)
    C = STYLE
    MC = _mc()
    if MC is None:
        dpg.add_text(f"mesh core unavailable: {_MC_ERR[0]}", color=C["AMB"])
        return
    GRN = tuple(MC.GRN) if hasattr(MC, "GRN") else (63, 208, 143)
    panel_w = int(MC.CFGD.get("panel_w", getattr(MC, "PANEL_W", 380)))
    prompt_h = int(MC.CFGD.get("prompt_h", getattr(MC, "PROMPT_H", 110)))
    notes_h = int(MC.CFGD.get("notes_h", getattr(MC, "NOTES_H", 150)))

    _theme_once("greenbtn", dpg.mvButton, [
        (dpg.mvThemeCol_Button, GRN),
        (dpg.mvThemeCol_ButtonHovered, (87, 224, 160)),
        (dpg.mvThemeCol_ButtonActive, (46, 160, 110)),
        (dpg.mvThemeCol_Text, (12, 14, 20))])
    _theme_once("gripbtn", dpg.mvButton, [
        (dpg.mvThemeCol_Button, (44, 50, 66)),
        (dpg.mvThemeCol_ButtonHovered, (70, 78, 100)),
        (dpg.mvThemeCol_ButtonActive, GRN)])
    _theme_once("chatpane", dpg.mvChildWindow, [
        (dpg.mvThemeCol_ChildBg, tuple(getattr(MC, "CHAT_BG", (16, 19, 27))))])

    with dpg.group(horizontal=True):
        # ── left: the macro workshop (the standalone's own tags) ────────
        with dpg.child_window(width=panel_w, tag="workshop"):
            dpg.add_text("macro workshop", color=C["DIM"])
            with dpg.tab_bar():
                with dpg.tab(label=" Macros "):
                    with dpg.child_window(tag="maclist", height=-1):
                        pass
                with dpg.tab(label=" Forge "):
                    with dpg.group(horizontal=True):
                        dpg.add_text("file (.json):", color=C["DIM"])
                        dpg.add_input_text(tag="fg_file", width=-1)
                    with dpg.group(horizontal=True):
                        dpg.add_text("command", color=C["DIM"])
                        dpg.add_input_text(tag="fg_cmd", width=-1,
                                           hint="what this macro runs")
                    with dpg.group(horizontal=True):
                        dpg.add_text("button name", color=C["DIM"])
                        dpg.add_input_text(tag="fg_name", width=-1)
                    with dpg.group(horizontal=True):
                        b = dpg.add_button(label="Forge...",
                                           callback=MC.forge_ai)
                        dpg.bind_item_theme(b, "greenbtn")
                        dpg.add_button(label="new", callback=MC.forge_new)
                        dpg.add_button(label="{ }", callback=MC.forge_raw)
                        dpg.add_button(label="Save", callback=MC.forge_save)
                    dpg.add_text("", tag="fg_msg", color=C["DIM"], wrap=340)
                    dpg.add_text("tick = keep - edit labels & defaults",
                                 color=C["DIM"])
                    with dpg.child_window(tag="fg_rows", height=-1):
                        pass
                with dpg.tab(label=" Editor "):
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Open", callback=lambda:
                                       dpg.show_item("edopendlg"))
                        dpg.add_button(label="Save", callback=MC.ed_save)
                        dpg.add_button(label="Review", callback=MC.ed_review)
                        dpg.add_checkbox(label="auto", tag="ed_auto")
                    dpg.add_input_text(tag="editor", multiline=True,
                                       width=-1, height=-(notes_h + 62),
                                       callback=MC.ed_key)
                    dpg.add_button(tag="ngrip_btn", label="", width=-1,
                                   height=8)
                    with dpg.group(horizontal=True):
                        dpg.add_text("assistant notes", color=C["DIM"])
                        dpg.add_button(label="copy", small=True,
                                       callback=MC.copy_note)
                    with dpg.child_window(tag="ed_notes", width=-1,
                                          height=notes_h):
                        pass
        # the draggable seam (the standalone's proven grip mechanism)
        with dpg.child_window(tag="hgrip", width=12, height=-1,
                              border=False, no_scrollbar=True):
            dpg.add_button(tag="hgrip_btn", label="", width=-1, height=2600)
        # ── right: the conversation ─────────────────────────────────────
        with dpg.group():
            dpg.add_input_text(multiline=True, width=-1, height=prompt_h,
                               tag="prompt",
                               hint="Ask the Professor…  (Ctrl+Enter sends)")
            dpg.add_button(tag="vgrip_btn", label="", width=-1, height=10)
            with dpg.group(horizontal=True):
                dpg.add_button(label="Attach file",
                               callback=lambda: dpg.show_item("filedlg"))
                dpg.add_text("", tag="attachlbl", color=C["DIM"])
                dpg.add_combo([], tag="chatsel", width=300,
                              callback=MC.on_chat_pick)
                dpg.add_button(label="...", small=True,
                               callback=MC.chat_menu)
                dpg.add_button(label="New chat", callback=MC.new_chat)
                ask = dpg.add_button(label="   Ask   ", tag="askbtn",
                                     callback=MC.on_ask)
                dpg.bind_item_theme(ask, "greenbtn")
            with dpg.child_window(tag="chat", height=-30):
                dpg.add_text("You're connected to the mesh — ask the "
                             "Professor anything. Ctrl+Enter sends; the "
                             "workshop (macros · forge · editor) lives on "
                             "the left.", color=C["DIM"], wrap=880)
                dpg.add_spacer(height=6)
            dpg.add_text("mesh client ready", tag="status", color=C["DIM"])

    dpg.bind_item_theme("chat", "chatpane")
    dpg.bind_item_theme("hgrip", "chatpane")
    dpg.bind_item_theme("hgrip_btn", "gripbtn")
    dpg.bind_item_theme("vgrip_btn", "gripbtn")
    dpg.bind_item_theme("ngrip_btn", "gripbtn")

    # the standalone's own dialogs (attach · editor open/save · export)
    for tag, cb, kw in (
            ("filedlg", MC.on_attach_pick, {}),
            ("edopendlg", MC.ed_open_pick, {}),
            ("edsavedlg", MC.ed_save_pick, {}),
            ("expdlg", MC.on_export_pick,
             {"default_filename": "chat-export.md"})):
        if dpg.does_item_exist(tag):
            continue
        with dpg.file_dialog(directory_selector=False, show=False,
                             modal=True, callback=cb, tag=tag, width=760,
                             height=460,
                             default_path=os.path.expanduser("~"), **kw):
            dpg.add_file_extension(".*")
            dpg.add_file_extension(".md", color=GRN)
            dpg.add_file_extension(".txt", color=GRN)

    with dpg.handler_registry():
        dpg.add_key_press_handler(callback=_keys)
        dpg.add_mouse_move_handler(callback=MC._drag_grips)
        dpg.add_mouse_release_handler(callback=MC._grip_up)

    MC.refresh_macro_buttons()
    MC.refresh_chats()
    threading.Thread(target=MC.auto_loop, daemon=True).start()

    CLIP = STYLE.get("CLIP")
    if CLIP:
        CLIP.input_menu("prompt", "prompt")
        CLIP.input_menu("editor", "editor")
        CLIP.input_menu("fg_cmd", "forge command")
        CLIP.menu("chat", [
            ("Copy last answer", MC.copy_last_answer),
            ("Copy whole chat", MC.copy_whole_chat),
            ("Paste into prompt", MC.paste_into_prompt), None,
            ("Export chat...", lambda: dpg.show_item("expdlg"))])
        CLIP.menu("ed_notes", [
            ("Copy last review", MC.copy_note),
            ("Copy all reviews", MC.copy_all_reviews), None,
            ("Open review log", lambda: MC.open_path(MC.REVIEW_LOG))])


def _selftest():
    """Headless: core + store, context builds, workshop populated from
    the real macro library, chat surface renders a block (no network)."""
    MC = _mc()
    assert MC is not None, f"mesh core failed: {_MC_ERR[0]}"
    for tag in ("workshop", "maclist", "fg_rows", "editor", "ed_notes",
                "prompt", "chat", "chatsel", "status", "askbtn"):
        assert dpg.does_item_exist(tag), f"missing surface: {tag}"
    MC.HISTORY[:] = []
    MC.HISTORY.append(("user", "gate probe"))
    ctx = MC.build_context()
    assert "gate probe" in ctx
    MC.append_block("You", "gate probe (render check)", tuple(MC.DIM))
    MC.HISTORY[:] = []
    macros = len(dpg.get_item_children("maclist", 1) or [])
    # Forge regression (Aug-29): long options ATTACH their value (--o=v);
    # separated form made grep read the pattern as a filename.
    argv = MC.assemble(
        {"kind": "command", "command": "grep", "fields": [
            {"flag": "--color", "type": "choice", "default": "auto"},
            {"arg": "patterns", "type": "text", "default": ""},
            {"arg": "files", "type": "path", "default": "."}]},
        ["auto", "PAT", "."])
    assert "--color=auto" in argv and \
        argv.index("PAT") < argv.index("."), argv
    return {"core": True, "store": MC.STORE is not None, "macros": macros,
            "seams": True, "forge_argv": "attached-form"}
