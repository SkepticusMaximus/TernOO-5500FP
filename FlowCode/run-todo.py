#!/home/stevo/.venvs/p2pcp/bin/python3
"""TernOO · To-Do — a standalone task list for the ship's captain.

A working FlowCode-ecosystem app in the same run-window pattern as the Word
Explorer: a DearPyGui window, FlowCode's theme + font, with the sensible
defaults every basic GUI app is owed —

    • Menu bar          File / Edit / Help
    • Undo              Ctrl+Z  (also Edit menu + right-click)  — nothing is lost
    • Context menu      right-click any task: Toggle / Edit / Copy / Delete / Undo
    • Edit a task       double-click it, or F2, or the context menu
    • Clipboard         Copy (Ctrl+C) / Paste-as-task (Ctrl+V); the input box has
                        the standard Ctrl+C/V/X/A/Z while you type
    • Keyboard          Enter add · Del delete · F2 edit · Ctrl+N new · Ctrl+Z undo
    • Selection         click a task to select it; menu actions act on it

Persisted to ~/.config/ternoo/todo.json.
Launch:  run-todo.py        (or the TernOO To-Do desktop icon)
"""
import os
import json
import dearpygui.dearpygui as dpg

STORE = os.path.expanduser("~/.config/ternoo/todo.json")
os.makedirs(os.path.dirname(STORE), exist_ok=True)

GRN, INK, DIM, BAD, ACC = (63, 208, 143), (230, 230, 236), (150, 150, 165), \
                          (240, 130, 130), (110, 168, 254)

TASKS = []          # [{"text": str, "done": bool}, ...]
UNDO = []           # snapshots for Ctrl+Z
SEL = [-1]          # selected row index (mutable holder)
ROW_SEL = {}        # idx -> row-button item id, rebuilt each render
THEMES = {}         # flat row themes, built once in build_ui


# ── persistence ──────────────────────────────────────────────────────────────
def _load():
    try:
        return json.load(open(STORE, encoding="utf-8"))
    except Exception:
        return []


def _save():
    json.dump(TASKS, open(STORE, "w", encoding="utf-8"), indent=1)


# ── undo ─────────────────────────────────────────────────────────────────────
def _snapshot():
    UNDO.append([dict(t) for t in TASKS])
    if len(UNDO) > 100:
        UNDO.pop(0)


def _undo(*_):
    if UNDO:
        TASKS[:] = UNDO.pop()
        if SEL[0] >= len(TASKS):
            SEL[0] = -1
        _save()
        _render()


# ── render ───────────────────────────────────────────────────────────────────
def _render():
    ROW_SEL.clear()
    dpg.delete_item("tasklist", children_only=True)
    if not TASKS:
        dpg.add_text("  no tasks yet — type one above and hit Add",
                     color=DIM, parent="tasklist")
    for i, t in enumerate(TASKS):
        with dpg.group(horizontal=True, parent="tasklist"):
            dpg.add_checkbox(default_value=t["done"], callback=_toggle, user_data=i)
            lbl = ("✔  " if t["done"] else "    ") + t["text"]
            sid = dpg.add_button(label=lbl, width=-1, callback=_select, user_data=i)
            if THEMES:
                dpg.bind_item_theme(sid, THEMES["sel"] if i == SEL[0]
                                    else THEMES["row"])
            ROW_SEL[i] = sid
            with dpg.popup(sid, mousebutton=dpg.mvMouseButton_Right):
                dpg.add_menu_item(label="Toggle done", callback=_ctx_toggle, user_data=i)
                dpg.add_menu_item(label="Edit…", callback=_edit_from, user_data=i)
                dpg.add_menu_item(label="Copy text", callback=_ctx_copy, user_data=i)
                dpg.add_menu_item(label="Delete", callback=_delete, user_data=i)
                dpg.add_separator()
                dpg.add_menu_item(label="Undo  (Ctrl+Z)", callback=_undo)
    done = sum(1 for t in TASKS if t["done"])
    if dpg.does_item_exist("count"):
        dpg.set_value("count", f"{len(TASKS)} task(s) · {done} done")


# ── mutations ────────────────────────────────────────────────────────────────
def _add(*_):
    txt = (dpg.get_value("input") or "").strip()
    if txt:
        _snapshot()
        TASKS.append({"text": txt, "done": False})
        _save()
        dpg.set_value("input", "")
        _render()
    if dpg.does_item_exist("input"):
        dpg.focus_item("input")


def _toggle(_s, val, idx):
    if 0 <= idx < len(TASKS):
        _snapshot()
        TASKS[idx]["done"] = bool(val)
        _save()
        _render()


def _ctx_toggle(_s, _a, idx):
    if 0 <= idx < len(TASKS):
        _snapshot()
        TASKS[idx]["done"] = not TASKS[idx]["done"]
        _save()
        _render()


def _delete(_s, _a, idx):
    if 0 <= idx < len(TASKS):
        _snapshot()
        del TASKS[idx]
        if SEL[0] == idx:
            SEL[0] = -1
        elif SEL[0] > idx:
            SEL[0] -= 1
        _save()
        _render()


def _delete_sel(*_):
    if 0 <= SEL[0] < len(TASKS):
        _delete(None, None, SEL[0])


def _clear_done(*_):
    if any(t["done"] for t in TASKS):
        _snapshot()
        TASKS[:] = [t for t in TASKS if not t["done"]]
        SEL[0] = -1
        _save()
        _render()


def _delete_all(*_):
    if TASKS:
        _snapshot()
        TASKS.clear()
        SEL[0] = -1
        _save()
        _render()


# ── selection ────────────────────────────────────────────────────────────────
def _select(_s, _val, idx):
    SEL[0] = idx
    _render()


# ── clipboard ────────────────────────────────────────────────────────────────
def _ctx_copy(_s, _a, idx):
    if 0 <= idx < len(TASKS):
        dpg.set_clipboard_text(TASKS[idx]["text"])


def _copy_sel(*_):
    if 0 <= SEL[0] < len(TASKS):
        dpg.set_clipboard_text(TASKS[SEL[0]]["text"])


def _paste_new(*_):
    try:
        txt = (dpg.get_clipboard_text() or "").strip()
    except Exception:
        txt = ""
    if txt:
        _snapshot()
        TASKS.append({"text": txt, "done": False})
        _save()
        _render()


# ── edit ─────────────────────────────────────────────────────────────────────
def _edit_from(_s, _a, idx):
    _open_edit(idx)


def _edit_sel(*_):
    if 0 <= SEL[0] < len(TASKS):
        _open_edit(SEL[0])


def _open_edit(idx):
    if not (0 <= idx < len(TASKS)):
        return
    if dpg.does_item_exist("edit_modal"):
        dpg.delete_item("edit_modal")
    with dpg.window(label="Edit task", modal=True, tag="edit_modal",
                    width=400, height=130, pos=[48, 110], no_resize=True):
        dpg.add_input_text(tag="edit_field", default_value=TASKS[idx]["text"],
                           width=-1, on_enter=True,
                           callback=lambda *a: _edit_commit(idx))
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Save", width=100,
                           callback=lambda *a: _edit_commit(idx))
            dpg.add_button(label="Cancel", width=100,
                           callback=lambda *a: dpg.delete_item("edit_modal"))
    dpg.focus_item("edit_field")


def _edit_commit(idx):
    new = (dpg.get_value("edit_field") or "").strip()
    if new and 0 <= idx < len(TASKS):
        _snapshot()
        TASKS[idx]["text"] = new
        _save()
        _render()
    if dpg.does_item_exist("edit_modal"):
        dpg.delete_item("edit_modal")


# ── misc actions ─────────────────────────────────────────────────────────────
def _focus_input(*_):
    if dpg.does_item_exist("input"):
        dpg.focus_item("input")


def _quit(*_):
    dpg.stop_dearpygui()


def _show_help(*_):
    if dpg.does_item_exist("help_modal"):
        dpg.delete_item("help_modal")
    with dpg.window(label="Keyboard shortcuts", modal=True, tag="help_modal",
                    width=360, height=250, pos=[60, 90], no_resize=True):
        for k, v in [("Enter", "add the typed task"),
                     ("Ctrl+Z", "undo the last change"),
                     ("Ctrl+C", "copy the selected task"),
                     ("Ctrl+V", "paste clipboard as a new task"),
                     ("F2", "edit the selected task"),
                     ("Del", "delete the selected task"),
                     ("Ctrl+N", "jump to the new-task box"),
                     ("double-click", "edit a task"),
                     ("right-click", "task options menu")]:
            with dpg.group(horizontal=True):
                dpg.add_text(f"{k:>12}", color=ACC)
                dpg.add_text("  " + v, color=INK)
        dpg.add_spacer(height=8)
        dpg.add_text("The new-task box also has the standard", color=DIM)
        dpg.add_text("Ctrl+C / V / X / A / Z while you type.", color=DIM)
        dpg.add_spacer(height=6)
        dpg.add_button(label="Close", width=100,
                       callback=lambda *a: dpg.delete_item("help_modal"))


# ── keyboard ─────────────────────────────────────────────────────────────────
def _ctrl():
    return dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)


def _typing():
    return dpg.does_item_exist("input") and dpg.is_item_focused("input")


def _k_undo(*_):
    if _ctrl():
        _undo()


def _k_copy(*_):
    if _ctrl() and not _typing():
        _copy_sel()


def _k_paste(*_):
    if _ctrl() and not _typing():
        _paste_new()


def _k_new(*_):
    if _ctrl():
        _focus_input()


def _k_delete(*_):
    if not _typing():
        _delete_sel()


def _k_edit(*_):
    if not _typing():
        _edit_sel()


# ── build ────────────────────────────────────────────────────────────────────
def _flat_theme(bg):
    """A flat, left-aligned button theme for task rows."""
    with dpg.theme() as th:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, bg)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,
                                tuple(min(255, c + 16) for c in bg))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,
                                tuple(min(255, c + 28) for c in bg))
            dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, 0.0, 0.5)
    return th


def build_ui():
    """Build the window + widgets (no viewport) — callable headless for tests."""
    font = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    if os.path.exists(font):
        with dpg.font_registry():
            f = dpg.add_font(font, 18)
        dpg.bind_font(f)

    with dpg.theme() as theme:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (26, 31, 43))
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (34, 40, 54))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (21, 21, 31))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (46, 70, 110))
            dpg.add_theme_color(dpg.mvThemeCol_Header, (46, 70, 110))
            dpg.add_theme_color(dpg.mvThemeCol_MenuBarBg, (30, 36, 49))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (90, 130, 190))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)

    THEMES["row"] = _flat_theme((34, 40, 54))      # flat, blends into the list
    THEMES["sel"] = _flat_theme((46, 70, 110))     # selected row highlight

    with dpg.window(tag="main", no_scrollbar=True, menubar=True):
        with dpg.menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="New task\tCtrl+N", callback=_focus_input)
                dpg.add_separator()
                dpg.add_menu_item(label="Quit", callback=_quit)
            with dpg.menu(label="Edit"):
                dpg.add_menu_item(label="Undo\tCtrl+Z", callback=_undo)
                dpg.add_separator()
                dpg.add_menu_item(label="Copy selected\tCtrl+C", callback=_copy_sel)
                dpg.add_menu_item(label="Paste as task\tCtrl+V", callback=_paste_new)
                dpg.add_menu_item(label="Edit selected\tF2", callback=_edit_sel)
                dpg.add_menu_item(label="Delete selected\tDel", callback=_delete_sel)
                dpg.add_separator()
                dpg.add_menu_item(label="Clear done", callback=_clear_done)
                dpg.add_menu_item(label="Delete all", callback=_delete_all)
            with dpg.menu(label="Help"):
                dpg.add_menu_item(label="Keyboard shortcuts", callback=_show_help)

        dpg.add_text("TernOO · To-Do", color=GRN)
        dpg.add_text("the ship's captain's task list", color=DIM)
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_input_text(tag="input", hint="new task…", width=-84,
                               on_enter=True, callback=_add)
            dpg.add_button(label=" Add ", width=78, callback=_add)
        dpg.add_spacer(height=4)
        dpg.add_text("right-click a task for options · double-click to edit "
                     "· Ctrl+Z to undo", color=DIM)
        dpg.add_spacer(height=4)
        dpg.add_child_window(tag="tasklist", height=-44, border=True)
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_text("", tag="count", color=DIM)
            dpg.add_spacer(width=12)
            dpg.add_button(label="Clear done", callback=_clear_done)

    with dpg.handler_registry():
        dpg.add_key_press_handler(dpg.mvKey_Z, callback=_k_undo)
        dpg.add_key_press_handler(dpg.mvKey_C, callback=_k_copy)
        dpg.add_key_press_handler(dpg.mvKey_V, callback=_k_paste)
        dpg.add_key_press_handler(dpg.mvKey_N, callback=_k_new)
        dpg.add_key_press_handler(dpg.mvKey_Delete, callback=_k_delete)
        dpg.add_key_press_handler(dpg.mvKey_F2, callback=_k_edit)
        dpg.add_mouse_double_click_handler(callback=_on_dblclick)

    _render()
    dpg.bind_theme(theme)


def _on_dblclick(_s, button):
    if button != 0:
        return
    for idx, sid in list(ROW_SEL.items()):
        if dpg.does_item_exist(sid) and dpg.is_item_hovered(sid):
            _open_edit(idx)
            return


def main():
    global TASKS
    TASKS = _load()
    dpg.create_context()
    build_ui()
    dpg.create_viewport(title="TernOO · To-Do", width=470, height=580)
    dpg.setup_dearpygui()
    dpg.set_primary_window("main", True)
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
