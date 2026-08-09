#!/usr/bin/env python3
"""mesh_chat_dpg.py — the TRIPOD TASTE-TEST: Mesh-Chat rendered by Dear PyGui.

Same mesh, same Professor, same macro library — new pixels. The logic rides
p2pcp_service untouched; macro specs come from macro_panel's loader; only the
view layer is new. Dear PyGui is GPU-rendered immediate-mode (the ImGui
family): the whole UI is drawn every frame by our own loop — architecturally
the same shape PIGART must one day take, which is why it's the candidate for
TernOO on its own tripod.

Run:   ~/.venvs/p2pcp/bin/python 5500fp/mesh_chat_dpg.py
Smoke: SMOKE=1 ~/.venvs/p2pcp/bin/python 5500fp/mesh_chat_dpg.py
"""

import importlib.util as _ilu
import json
import os
import socket
import subprocess
import sys
import threading

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SVC = _load("p2pcp_service")
MP = _load("macro_panel")                    # tk-free at module level: specs+validate

import dearpygui.dearpygui as dpg  # noqa: E402  (after the stdlib plumbing)

# ── TernOO terminal-noir, second pour: lighter, layered, larger ──────────────
BG = (26, 29, 40)                 # window
PANEL = (33, 37, 51)              # raised surfaces (workshop, popups)
FIELD = (42, 47, 63)              # inputs — clearly lighter than their ground
CHAT_BG = (20, 23, 32)            # the transcript sits deepest
BORDER = (66, 74, 98)
TEXT = (238, 240, 245)
DIM = (168, 175, 190)
GRN = (63, 208, 143)
ORN = (255, 143, 63)
BLU = (109, 179, 255)
RED = (224, 106, 106)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = int(os.environ.get("MESH_DPG_FONT", "20"))   # your zoom knob

PERSONA = ('[You are the Professor — the assistant in this dialogue. The '
           '"Professor:" lines are your own earlier replies; the "You:" '
           'lines are the user speaking to you. The user is NOT the '
           'Professor — never address them by that title. Answer the '
           'user\'s last message, as the Professor.]\n\n')
ATTACH_MAX = 20000

HISTORY = []                                  # [(role, text)]
ATTACH = None                                 # {name, text}
BUYER = SVC.MeshService(worker_kind=None, seed="dpg-mesh")
BUSY = False


# ── mesh plumbing (mirrors the tk client's behaviour) ────────────────────────
def candidates():
    cands = [("127.0.0.1", 9000)]
    try:
        for line in open(os.path.expanduser("~/.p2pcp/nodes.txt")):
            line = line.strip()
            if ":" in line:
                h, p = line.rsplit(":", 1)
                if (h, int(p)) not in cands:
                    cands.append((h, int(p)))
    except Exception:
        pass
    return cands


def build_context():
    lines, total = [], 0
    for role, text in reversed(HISTORY):
        tag = "You" if role == "user" else "Professor"
        chunk = f"{tag}: {text}\n"
        if total + len(chunk) > 2400 and lines:
            break
        lines.append(chunk)
        total += len(chunk)
    lines.reverse()
    prefix = ""
    if ATTACH:
        prefix = (f'[The user attached a file "{ATTACH["name"]}". Its contents:]\n'
                  f'"""\n{ATTACH["text"]}\n"""\n\n')
    return PERSONA + prefix + "".join(lines) + "Professor:"


def trim_followups(ans):
    for marker in ("\nYou:", "\nUser:", "\nYou :", "\nHuman:"):
        i = ans.find(marker)
        if i != -1:
            ans = ans[:i]
    ans = ans.strip()
    if ans.lower().startswith("professor"):
        colon = ans.find(":")
        if 0 < colon < 40:
            ans = ans[colon + 1:].strip()
    return ans


# ── chat rendering ───────────────────────────────────────────────────────────
def _wrap_width():
    try:
        w = dpg.get_item_rect_size("chat")[0]
        return max(320, int(w) - 28)
    except Exception:
        return 880


def append_block(who, text, who_color):
    dpg.add_text(who, parent="chat", color=who_color)
    dpg.add_text(text, parent="chat", color=TEXT, wrap=_wrap_width())
    dpg.add_spacer(height=8, parent="chat")
    dpg.set_y_scroll("chat", 999999.0)


def set_status(msg, color=DIM):
    dpg.set_value("status", msg)
    dpg.configure_item("status", color=color)


# ── the ask ──────────────────────────────────────────────────────────────────
def on_ask(*_):
    global BUSY, ATTACH
    if BUSY:
        return
    prompt = dpg.get_value("prompt").strip()
    if not prompt:
        set_status("type a question first")
        return
    shown = prompt + (f"\n[attached: {ATTACH['name']}]" if ATTACH else "")
    HISTORY.append(("user", shown))
    append_block("You", shown, DIM)
    dpg.set_value("prompt", "")
    context = build_context()
    BUSY = True
    dpg.configure_item("askbtn", label="  ...thinking  ", enabled=False)
    dpg.add_text("Professor is thinking...", parent="chat", tag="pending",
                 color=DIM)
    dpg.set_y_scroll("chat", 999999.0)
    set_status("asking the mesh...")

    def work():
        global BUSY, ATTACH
        where = ans = err = None
        try:
            where, ans = BUYER.ask_mesh(context, candidates=candidates())
        except Exception as e:                  # noqa: BLE001 — surfaced to user
            err = str(e)
        try:
            dpg.delete_item("pending")
            if err:
                append_block("mesh", f"(couldn't reach a model: {err})", RED)
                HISTORY.pop()
                set_status("ask failed", RED)
            elif not where or ans is None:
                append_block("mesh", "(no model on the mesh answered)", RED)
                HISTORY.pop()
                set_status("no model answered", RED)
            else:
                ans = trim_followups(ans)
                HISTORY.append(("assistant", ans))
                append_block(f"Professor · {where}", ans, GRN)
                ATTACH = None
                dpg.set_value("attachlbl", "")
                set_status("ready", GRN)
        finally:
            BUSY = False
            dpg.configure_item("askbtn", label="   Ask   ", enabled=True)
    threading.Thread(target=work, daemon=True).start()


# ── attachment ───────────────────────────────────────────────────────────────
def on_attach_pick(_s, app_data):
    global ATTACH
    path = app_data.get("file_path_name", "")
    if not path:
        return
    try:
        body = open(path, encoding="utf-8", errors="replace").read()
    except Exception as e:                      # noqa: BLE001
        set_status(f"couldn't read file: {e}", RED)
        return
    clipped = len(body) > ATTACH_MAX
    ATTACH = {"name": os.path.basename(path), "text": body[:ATTACH_MAX]}
    dpg.set_value("attachlbl",
                  f"[{ATTACH['name']}]" + (" (clipped)" if clipped else ""))
    set_status("attachment armed — rides with your next ask")


# ── macros: same specs, new dialogs ──────────────────────────────────────────
def assemble(spec, values):
    if spec.get("kind") == "prompt":
        slots = {f.get("arg", f.get("flag", "")): str(v)
                 for f, v in zip(spec.get("fields", []), values)}
        try:
            return spec["template"].format(**slots)
        except KeyError as e:
            return f"(template needs a value for {e})"
    argv = [spec["command"]]
    fields = spec.get("fields", [])
    for f, v in zip(fields, values):
        if f.get("type") == "check":
            if v:
                argv.append(f["flag"])
        elif "flag" in f and str(v):
            argv += [f["flag"], str(v)]
    for f, v in zip(fields, values):
        if "arg" in f and f.get("type") != "check" and str(v):
            argv.append(os.path.expanduser(str(v))
                        if f.get("type") == "path" else str(v))
    return argv


def open_macro(spec):
    if spec.get("kind") == "prompt":
        _prompt_macro_modal(spec)
    else:
        _command_macro_modal(spec)


def _prompt_macro_modal(spec):
    tag = f"pm_{spec['_file']}"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    with dpg.window(label=spec.get("name", "macro"), modal=True, tag=tag,
                    width=520, height=260, pos=(200, 160)):
        dpg.add_text(spec.get("desc", ""), color=DIM, wrap=480)
        entries = []
        for f in spec.get("fields", []):
            dpg.add_text(f.get("label", f.get("arg", "?")), color=TEXT)
            e = dpg.add_input_text(width=-1,
                                   default_value=str(f.get("default", "")))
            entries.append(e)

        def fire():
            vals = [dpg.get_value(e) for e in entries]
            text = assemble(spec, vals)
            dpg.delete_item(tag)
            dpg.set_value("prompt", text)
            on_ask()
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Ask the Professor  ", callback=fire)
            dpg.add_button(label="Cancel",
                           callback=lambda: dpg.delete_item(tag))


def _command_macro_modal(spec):
    tag = f"cm_{spec['_file']}"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    widgets = []
    with dpg.window(label=spec.get("name", "macro"), modal=True, tag=tag,
                    width=640, height=560, pos=(180, 100)):
        if spec.get("desc"):
            dpg.add_text(spec["desc"], color=DIM, wrap=600)
        prev = None

        def refresh(*_):
            vals = []
            for f, w in zip(spec.get("fields", []), widgets):
                vals.append(dpg.get_value(w))
            a = assemble(spec, vals)
            dpg.set_value(prev, "-> " + (" ".join(a) if isinstance(a, list)
                                         else str(a)))
        for f in spec.get("fields", []):
            t = f.get("type")
            label = f.get("label", f.get("flag", f.get("arg", "?")))
            if t == "check":
                w = dpg.add_checkbox(label=label,
                                     default_value=bool(f.get("default")),
                                     callback=refresh)
            elif t == "choice":
                opts = [str(o) for o in f.get("options", [])] or [""]
                dpg.add_text(label, color=TEXT)
                w = dpg.add_combo(opts, default_value=str(f.get("default", "")),
                                  width=-1, callback=refresh)
            else:
                dpg.add_text(label, color=TEXT)
                w = dpg.add_input_text(width=-1, callback=refresh,
                                       default_value=str(f.get("default", "")))
            widgets.append(w)
        dpg.add_spacer(height=6)
        prev = dpg.add_text("", color=BLU, wrap=600)
        out = dpg.add_input_text(multiline=True, readonly=True, width=-1,
                                 height=200)

        def run(*_):
            vals = [dpg.get_value(w) for w in widgets]
            argv = assemble(spec, vals)
            dpg.set_value(out, "$ " + " ".join(argv) + "\n\n")

            def work():
                try:
                    r = subprocess.run(argv, capture_output=True, timeout=60,
                                       cwd=os.path.expanduser("~"))
                    body = (r.stdout.decode("utf-8", "replace")
                            + r.stderr.decode("utf-8", "replace"))
                    dpg.set_value(out, dpg.get_value(out)
                                  + (body[:8000] or "(no output)"))
                except Exception as e:          # noqa: BLE001
                    dpg.set_value(out, dpg.get_value(out) + f"error: {e}")
            threading.Thread(target=work, daemon=True).start()
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Run  ", callback=run, tag=f"{tag}_run")
            dpg.add_button(label="Close",
                           callback=lambda: dpg.delete_item(tag))
        refresh()


# ── build ────────────────────────────────────────────────────────────────────
def build():
    with dpg.font_registry():
        if os.path.exists(FONT):
            default = dpg.add_font(FONT, FONT_SIZE)
            dpg.bind_font(default)
        big = (dpg.add_font(FONT_B, FONT_SIZE + 7)
               if os.path.exists(FONT_B) else None)

    with dpg.theme() as t:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_WindowBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_PopupBg, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_ModalWindowDimBg, (10, 12, 18, 160))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, FIELD)
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (52, 58, 78))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgActive, (58, 65, 88))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgActive, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_Button, (48, 54, 72))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (60, 68, 90))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (72, 82, 108))
            dpg.add_theme_color(dpg.mvThemeCol_Text, TEXT)
            dpg.add_theme_color(dpg.mvThemeCol_Border, BORDER)
            dpg.add_theme_color(dpg.mvThemeCol_Tab, BG)
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, FIELD)
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, PANEL)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarBg, BG)
            dpg.add_theme_color(dpg.mvThemeCol_ScrollbarGrab, FIELD)
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, GRN)
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 6)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 5)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 10, 7)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 9, 8)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarSize, 12)
    dpg.bind_theme(t)

    with dpg.theme() as chat_theme:               # the transcript sits deepest
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, CHAT_BG)

    with dpg.theme() as green_btn:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, GRN)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (87, 224, 160))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (46, 160, 110))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (12, 14, 20))

    with dpg.window(tag="main"):
        with dpg.group(horizontal=True):
            # ── left: the macro workshop, always a citizen ────────────────
            with dpg.child_window(width=340, tag="workshop"):
                dpg.add_text("macro workshop", color=DIM)
                dpg.add_separator()
                for spec in MP._specs():
                    glyph = "[cmd]" if spec.get("kind") == "command" else "[ask]"
                    dpg.add_button(label=f"{glyph}  {spec.get('name', '?')}",
                                   width=-1,
                                   callback=lambda s, a, u: open_macro(u),
                                   user_data=spec)
                dpg.add_spacer(height=10)
                dpg.add_text("forge & editor live in the tk\nclient for now — "
                             "this window is\nthe RENDERING taste-test",
                             color=DIM)
            # ── right: the chat ───────────────────────────────────────────
            with dpg.group():
                hdr = dpg.add_text("Ask the mesh", color=TEXT)
                if big:
                    dpg.bind_item_font(hdr, big)
                dpg.add_input_text(multiline=True, width=-1, height=100,
                                   tag="prompt")
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Attach file",
                                   callback=lambda: dpg.show_item("filedlg"))
                    dpg.add_text("", tag="attachlbl", color=DIM)
                    ask = dpg.add_button(label="   Ask   ", tag="askbtn",
                                         callback=on_ask)
                    dpg.bind_item_theme(ask, green_btn)
                with dpg.tab_bar():
                    with dpg.tab(label=" Chat "):
                        with dpg.child_window(tag="chat", height=-32):
                            dpg.add_text("You're connected to the mesh — ask "
                                         "the Professor anything.",
                                         color=DIM, wrap=880)
                            dpg.add_spacer(height=6)
                    with dpg.tab(label=" FlowCode taste "):
                        dpg.add_text("DPG's native node editor — FlowCode's "
                                     "future organ, stock:", color=DIM)
                        with dpg.node_editor(tag="nodes", height=-28):
                            with dpg.node(label="Terminator", pos=(40, 60)):
                                with dpg.node_attribute(
                                        attribute_type=dpg.mvNode_Attr_Output,
                                        tag="n1o"):
                                    dpg.add_text("start", color=GRN)
                            with dpg.node(label="Process", pos=(260, 140)):
                                with dpg.node_attribute(tag="n2i"):
                                    dpg.add_text("in", color=BLU)
                                with dpg.node_attribute(
                                        attribute_type=dpg.mvNode_Attr_Output,
                                        tag="n2o"):
                                    dpg.add_text("out", color=BLU)
                            with dpg.node(label="Decision", pos=(490, 80)):
                                with dpg.node_attribute(tag="n3i"):
                                    dpg.add_text("test", color=ORN)
                                with dpg.node_attribute(
                                        attribute_type=dpg.mvNode_Attr_Output,
                                        tag="n3y"):
                                    dpg.add_text("+ / 0 / -", color=ORN)
                        dpg.add_node_link("n1o", "n2i", parent="nodes")
                        dpg.add_node_link("n2o", "n3i", parent="nodes")
                dpg.add_text("starting...", tag="status", color=DIM)

    dpg.bind_item_theme("chat", chat_theme)
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         callback=on_attach_pick, tag="filedlg",
                         width=760, height=460,
                         default_path=os.path.expanduser("~")):
        dpg.add_file_extension(".*")
        dpg.add_file_extension(".txt", color=tuple(GRN))
        dpg.add_file_extension(".md", color=tuple(GRN))

    with dpg.handler_registry():
        dpg.add_key_press_handler(dpg.mvKey_Return, callback=_ctrl_enter)


def _ctrl_enter(*_):
    if (dpg.is_key_down(dpg.mvKey_LControl)
            or dpg.is_key_down(dpg.mvKey_RControl)):
        if dpg.is_item_focused("prompt"):
            on_ask()


def _probe():
    n = 0
    for h, p in candidates():
        try:
            s = socket.create_connection((h, p), timeout=3)
            s.close()
            n += 1
        except Exception:
            pass
    try:
        if n:
            set_status(f"mesh ready · {n} node(s) reachable", GRN)
        else:
            set_status("no nodes reachable — is the tunnel/HP up?", RED)
    except Exception:
        pass


def main():
    dpg.create_context()
    build()
    if os.environ.get("SMOKE"):
        print("SMOKE OK — UI built clean")
        dpg.destroy_context()
        return
    dpg.create_viewport(title="Mesh-Chat — TernOO (Dear PyGui taste)",
                        width=1320, height=920, x_pos=40, y_pos=40)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main", True)
    threading.Thread(target=_probe, daemon=True).start()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
