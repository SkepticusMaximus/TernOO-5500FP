#!/usr/bin/env python3
"""flowcode_dpg_clip — the TEXT SERVICE every surface must use.

The captain's standing order (19-08, re-iterated from the Mesh-Chat
client): every text area gets copious clipboard service — context
menus, keybindings, the lot. This module is the one implementation:

- clip_set / clip_get: the battle-tested layer from the standalone
  client — xclip/xsel own the X clipboard (survives app exit), Tk read
  fallback, DPG buffer mirrored for in-field Ctrl+V, and a rescue file
  so copied text is never unreachable.
- install_ctrl_sync(): Ctrl press pulls X→DPG (so native in-field
  Ctrl+V pastes SYSTEM content); Ctrl+C/X pushes the field selection
  back out to X a frame later. Registered once; every input_text in
  the app becomes system-true.
- menu(tag, actions): context-menu framework — one global right-click
  handler shows the registered popup for whichever surface is hovered
  (child windows refuse per-item click handlers; this is the proven
  sandbox pattern).
- input_menu(tag): the standard Cut/Copy/Paste/Clear menu for any
  input_text, wired through clip_set/clip_get.
"""
import os
import shutil
import subprocess

import dearpygui.dearpygui as dpg

CLIP_FILE = os.path.expanduser("~/.config/ternoo-flowcode-dpg-clip.txt")
_CTX = {}          # hovered-surface tag -> popup tag
_N = [0]


def clip_set(text):
    text = text or ""
    for tool in (["xclip", "-selection", "clipboard"], ["xsel", "-b", "-i"]):
        if shutil.which(tool[0]):
            try:
                subprocess.run(tool, input=text.encode(),
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, timeout=3)
                break
            except Exception:                   # noqa: BLE001
                pass
    try:
        dpg.set_clipboard_text(text)
    except Exception:                           # noqa: BLE001
        pass
    try:
        open(CLIP_FILE, "w", encoding="utf-8").write(text)
    except Exception:                           # noqa: BLE001
        pass


def clip_get():
    for tool in (["xclip", "-selection", "clipboard", "-o"],
                 ["xsel", "-b", "-o"]):
        if shutil.which(tool[0]):
            try:
                r = subprocess.run(tool, capture_output=True, timeout=3)
                if r.returncode == 0 and r.stdout:
                    return r.stdout.decode("utf-8", "replace")
            except Exception:                   # noqa: BLE001
                pass
    try:                                        # Tk can READ X reliably
        import tkinter as _tk
        rt = _tk.Tk()
        rt.withdraw()
        try:
            t = rt.clipboard_get()
        finally:
            rt.destroy()
        if t:
            return t
    except Exception:                           # noqa: BLE001
        pass
    try:
        return dpg.get_clipboard_text() or ""
    except Exception:                           # noqa: BLE001
        return ""


def _ctrl_pull(*_):
    t = clip_get()
    try:
        if t and t != dpg.get_clipboard_text():
            dpg.set_clipboard_text(t)
    except Exception:                           # noqa: BLE001
        pass


def _ctrl_push(*_):
    if not (dpg.is_key_down(dpg.mvKey_LControl)
            or dpg.is_key_down(dpg.mvKey_RControl)):
        return

    def later():
        try:
            t = dpg.get_clipboard_text() or ""
        except Exception:                       # noqa: BLE001
            return
        if t:
            for tool in (["xclip", "-selection", "clipboard"],
                         ["xsel", "-b", "-i"]):
                if shutil.which(tool[0]):
                    try:
                        subprocess.run(tool, input=t.encode(),
                                       stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL,
                                       timeout=3)
                        return
                    except Exception:           # noqa: BLE001
                        pass
    try:
        dpg.set_frame_callback(dpg.get_frame_count() + 1, later)
    except Exception:                           # noqa: BLE001
        pass


def _rclick(*_):
    for surface, pop in _CTX.items():
        try:
            if dpg.does_item_exist(surface) and dpg.is_item_hovered(surface):
                dpg.configure_item(pop, show=True)
                mx, my = dpg.get_mouse_pos(local=False)
                dpg.set_item_pos(pop, (mx + 4, my + 4))
                return
        except Exception:                       # noqa: BLE001
            pass


def install(installed=[False]):                 # noqa: B006 — once-flag
    """Register the global handlers ONCE (call during build)."""
    if installed[0]:
        return
    installed[0] = True
    with dpg.handler_registry():
        dpg.add_key_press_handler(dpg.mvKey_LControl, callback=_ctrl_pull)
        dpg.add_key_press_handler(dpg.mvKey_RControl, callback=_ctrl_pull)
        dpg.add_key_press_handler(dpg.mvKey_C, callback=_ctrl_push)
        dpg.add_key_press_handler(dpg.mvKey_X, callback=_ctrl_push)
        dpg.add_mouse_click_handler(dpg.mvMouseButton_Right,
                                    callback=_rclick)


def menu(surface_tag, actions):
    """Register a context menu on a hovered surface.
    actions: [(label, callback)] — None entries become separators."""
    _N[0] += 1
    pop = f"ctxpop_{_N[0]}"
    with dpg.window(tag=pop, popup=True, show=False, autosize=True,
                    no_title_bar=True):
        for entry in actions:
            if entry is None:
                dpg.add_separator()
                continue
            label, cb = entry
            dpg.add_menu_item(label=label,
                              user_data=cb,
                              callback=lambda s, a, u, p=pop:
                              (dpg.configure_item(p, show=False), u()))
    _CTX[surface_tag] = pop
    return pop


def input_menu(tag, label="text"):
    """The standard clipboard menu for an input_text `tag`."""
    def cut():
        clip_set(dpg.get_value(tag))
        dpg.set_value(tag, "")

    def copy():
        clip_set(dpg.get_value(tag))

    def paste():
        dpg.set_value(tag, (dpg.get_value(tag) or "") + clip_get())

    def clear():
        dpg.set_value(tag, "")
    menu(tag, [(f"Cut {label}", cut), (f"Copy {label}", copy),
               ("Paste (append)", paste), None, (f"Clear {label}", clear)])
