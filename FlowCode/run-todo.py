#!/home/stevo/.venvs/p2pcp/bin/python3
"""TernOO · To-Do — a standalone task list for the ship's captain.

A working FlowCode-ecosystem app in the same run-window pattern as the Word
Explorer: a DearPyGui window, FlowCode's theme + font, real interactivity
(add / tick-off / delete / clear-done), persisted to ~/.config/ternoo/todo.json.
Launch:  run-todo.py        (or the TernOO To-Do desktop icon)
"""
import os
import json
import dearpygui.dearpygui as dpg

STORE = os.path.expanduser("~/.config/ternoo/todo.json")
os.makedirs(os.path.dirname(STORE), exist_ok=True)

GRN, INK, DIM, BAD, ACC = (63, 208, 143), (230, 230, 236), (150, 150, 165), \
                          (240, 130, 130), (110, 168, 254)


def _load():
    try:
        return json.load(open(STORE, encoding="utf-8"))
    except Exception:
        return []


def _save():
    json.dump(TASKS, open(STORE, "w", encoding="utf-8"), indent=1)


TASKS = _load()                       # [{"text": str, "done": bool}, ...]


def _render():
    dpg.delete_item("tasklist", children_only=True)
    if not TASKS:
        dpg.add_text("  no tasks yet — type one above and hit Add",
                     color=DIM, parent="tasklist")
    for i, t in enumerate(TASKS):
        with dpg.group(horizontal=True, parent="tasklist"):
            dpg.add_checkbox(default_value=t["done"], callback=_toggle, user_data=i)
            dpg.add_text(("  " + t["text"]), color=(DIM if t["done"] else INK))
            dpg.add_button(label="x", width=22, callback=_delete, user_data=i)
    done = sum(1 for t in TASKS if t["done"])
    dpg.set_value("count", f"{len(TASKS)} task(s) · {done} done")


def _add(*_):
    txt = (dpg.get_value("input") or "").strip()
    if txt:
        TASKS.append({"text": txt, "done": False})
        _save()
        dpg.set_value("input", "")
        _render()
    if dpg.does_item_exist("input"):
        dpg.focus_item("input")


def _toggle(_s, val, idx):
    if 0 <= idx < len(TASKS):
        TASKS[idx]["done"] = bool(val)
        _save()
        _render()


def _delete(_s, _a, idx):
    if 0 <= idx < len(TASKS):
        del TASKS[idx]
        _save()
        _render()


def _clear_done(*_):
    TASKS[:] = [t for t in TASKS if not t["done"]]
    _save()
    _render()


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
            dpg.add_theme_color(dpg.mvThemeCol_Border, (90, 130, 190))
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 4)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
    with dpg.window(tag="main", no_scrollbar=True):
        dpg.add_text("TernOO · To-Do", color=GRN)
        dpg.add_text("the ship's captain's task list", color=DIM)
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_input_text(tag="input", hint="new task…", width=-84,
                               on_enter=True, callback=_add)
            dpg.add_button(label=" Add ", width=78, callback=_add)
        dpg.add_spacer(height=8)
        dpg.add_child_window(tag="tasklist", height=-44, border=True)
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_text("", tag="count", color=DIM)
            dpg.add_spacer(width=12)
            dpg.add_button(label="Clear done", callback=_clear_done)
    _render()
    dpg.bind_theme(theme)


def main():
    dpg.create_context()
    build_ui()
    dpg.create_viewport(title="TernOO · To-Do", width=460, height=560)
    dpg.setup_dearpygui()
    dpg.set_primary_window("main", True)
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
