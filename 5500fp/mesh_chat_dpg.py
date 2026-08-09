#!/usr/bin/env python3
"""mesh_chat_dpg.py — Mesh-Chat on Dear PyGui: the face-lift.

Same mesh, same Professor, same macro specs — new pixels, now at feature
depth: the macro workshop (Macros / Forge / Editor) lives in the left panel,
the Forge renders the Professor's --help drafts as a pruning tree, the Editor
carries the shoulder-reading assistant, chat URLs are clickable, and the
FlowCode-taste tab keeps the native node editor. Logic rides p2pcp_service
and macro_panel untouched; only the view is DPG.

Run:   ~/.venvs/p2pcp/bin/python 5500fp/mesh_chat_dpg.py
Zoom:  MESH_DPG_FONT=23 ... (default 20)
Smoke: SMOKE=1 ...
"""

import importlib.util as _ilu
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SVC = _load("p2pcp_service")
MP = _load("macro_panel")            # tk-free at module level: specs, validate,
#                                      forge prompt, first-json, review prompt

import dearpygui.dearpygui as dpg  # noqa: E402  (after the stdlib plumbing)

# ── TernOO terminal-noir: lighter, layered, larger ───────────────────────────
BG = (26, 29, 40)
PANEL = (33, 37, 51)
FIELD = (42, 47, 63)
CHAT_BG = (20, 23, 32)
BORDER = (66, 74, 98)
TEXT = (238, 240, 245)
DIM = (168, 175, 190)
GRN = (63, 208, 143)
ORN = (255, 143, 63)
BLU = (109, 179, 255)
RED = (224, 106, 106)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FONT_SIZE = int(os.environ.get("MESH_DPG_FONT", "22"))
CFG = os.path.expanduser("~/.config/ternoo-mesh-chat.json")


def _cfg_load():
    try:
        return json.load(open(CFG))
    except Exception:
        return {}


def _cfg_save(d):
    try:
        json.dump(d, open(CFG, "w"))
    except Exception:
        pass


SCALE = float(_cfg_load().get("font_scale", 1.0))


def zoom(delta):
    """Live text zoom — remembered between sessions."""
    global SCALE
    SCALE = max(0.8, min(1.9, round(SCALE + delta, 2)))
    dpg.set_global_font_scale(SCALE)
    _cfg_save({"font_scale": SCALE})
    try:
        set_status(f"text zoom {int(SCALE * 100)}%")
    except Exception:
        pass

PERSONA = ('[You are the Professor — the assistant in this dialogue. The '
           '"Professor:" lines are your own earlier replies; the "You:" '
           'lines are the user speaking to you. The user is NOT the '
           'Professor — never address them by that title. Answer the '
           'user\'s last message, as the Professor.]\n\n')
ATTACH_MAX = 20000

HISTORY = []
ATTACH = None
BUYER = SVC.MeshService(worker_kind=None, seed="dpg-mesh")
BUSY = False

FORGE_SPEC = None                 # the spec the Forge tree is editing
FORGE_CMD = None
ED_PATH = None
ED_DIRTY = False
ED_LAST_KEY = time.time()
REVIEW_BUSY = False


def ui(fn):
    """Run `fn` on the render thread next frame — worker threads call this
    instead of mutating heavy UI directly."""
    try:
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: fn())
    except Exception:
        fn()


# ── mesh plumbing (mirrors the tk client) ────────────────────────────────────
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
    urls = re.findall(r"https?://[^\s<>\"')\]]+", text)
    if urls:
        for u in urls[:6]:
            u = u.rstrip(".,;:")
            b = dpg.add_button(label=u if len(u) <= 76 else u[:73] + "...",
                               parent="chat", small=True,
                               callback=lambda s, a, link=u: webbrowser.open(link))
            dpg.bind_item_theme(b, "linkbtn")
    dpg.add_spacer(height=8, parent="chat")
    dpg.set_y_scroll("chat", 999999.0)


def set_status(msg, color=DIM):
    dpg.set_value("status", msg)
    dpg.configure_item("status", color=color)


def new_chat(*_):
    global HISTORY
    HISTORY = []
    dpg.delete_item("chat", children_only=True)
    dpg.add_text("New chat — the Professor remembers this conversation as "
                 "you go.", parent="chat", color=DIM, wrap=880)
    dpg.add_spacer(height=6, parent="chat")
    set_status("fresh chat")


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

        def done():
            global BUSY, ATTACH
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
                a = trim_followups(ans)
                HISTORY.append(("assistant", a))
                append_block(f"Professor · {where}", a, GRN)
                ATTACH = None
                dpg.set_value("attachlbl", "")
                set_status("ready", GRN)
            BUSY = False
            dpg.configure_item("askbtn", label="   Ask   ", enabled=True)
        ui(done)
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


# ── macros: same specs, DPG dialogs ──────────────────────────────────────────
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


def refresh_macro_buttons():
    dpg.delete_item("maclist", children_only=True)
    for spec in MP._specs():
        glyph = "[cmd]" if spec.get("kind") == "command" else "[ask]"
        dpg.add_button(label=f"{glyph}  {spec.get('name', '?')}", width=-1,
                       parent="maclist",
                       callback=lambda s, a, u: open_macro(u), user_data=spec)


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
                    width=560, height=300, pos=(220, 160)):
        dpg.add_text(spec.get("desc", ""), color=DIM, wrap=520)
        entries = []
        for f in spec.get("fields", []):
            dpg.add_text(f.get("label", f.get("arg", "?")), color=TEXT)
            entries.append(dpg.add_input_text(
                width=-1, default_value=str(f.get("default", ""))))

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
                    width=680, height=580, pos=(200, 90)):
        if spec.get("desc"):
            dpg.add_text(spec["desc"], color=DIM, wrap=640)
        prev = None

        def refresh(*_):
            vals = [dpg.get_value(w) for w in widgets]
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
        prev = dpg.add_text("", color=BLU, wrap=640)
        out = dpg.add_input_text(multiline=True, readonly=True, width=-1,
                                 height=210)

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
                    ui(lambda: dpg.set_value(out, dpg.get_value(out)
                                             + (body[:8000] or "(no output)")))
                except Exception as e:          # noqa: BLE001
                    ui(lambda: dpg.set_value(out, dpg.get_value(out)
                                             + f"error: {e}"))
            threading.Thread(target=work, daemon=True).start()
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Run  ", callback=run)
            dpg.add_button(label="Close",
                           callback=lambda: dpg.delete_item(tag))
        refresh()


# ── the Forge: pruning tree + the AI forge ───────────────────────────────────
def forge_show_tree():
    dpg.delete_item("fg_rows", children_only=True)
    s = FORGE_SPEC or {}
    dpg.set_value("fg_cmdlbl", f"command: {s.get('command', '?')}")
    dpg.set_value("fg_name", s.get("name", ""))
    for i, f in enumerate(s.get("fields", [])):
        with dpg.group(parent="fg_rows"):
            with dpg.group(horizontal=True):
                dpg.add_checkbox(tag=f"fr{i}_inc", default_value=True)
                dpg.add_input_text(tag=f"fr{i}_lbl", width=-1,
                                   default_value=f.get("label", ""))
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=26)
                dpg.add_text(f.get("flag", f.get("arg", "?")), color=DIM)
                t = f.get("type")
                if t == "check":
                    dpg.add_checkbox(tag=f"fr{i}_dv", label="on by default",
                                     default_value=bool(f.get("default")))
                elif t == "choice":
                    opts = [str(o) for o in f.get("options", [])] or [""]
                    dpg.add_combo(opts, tag=f"fr{i}_dv", width=160,
                                  default_value=str(f.get("default", "")))
                else:
                    dpg.add_input_text(tag=f"fr{i}_dv", width=160,
                                       default_value=str(f.get("default", "")))
        dpg.add_spacer(height=3, parent="fg_rows")


def forge_tree_to_spec():
    s = FORGE_SPEC or {}
    s["name"] = dpg.get_value("fg_name").strip() or s.get("name", "macro")
    fields = []
    for i, f in enumerate(s.get("fields", [])):
        if not dpg.get_value(f"fr{i}_inc"):
            continue
        f2 = dict(f)
        f2["label"] = dpg.get_value(f"fr{i}_lbl").strip() or f.get("label", "")
        dv = dpg.get_value(f"fr{i}_dv")
        f2["default"] = bool(dv) if f.get("type") == "check" else dv
        fields.append(f2)
    s["fields"] = fields
    return s


def forge_new(*_):
    global FORGE_SPEC, FORGE_CMD
    FORGE_SPEC = json.loads(json.dumps(MP.SKELETON))
    FORGE_CMD = FORGE_SPEC.get("command")
    if not dpg.get_value("fg_file").strip():
        dpg.set_value("fg_file", "my-macro")
    forge_show_tree()
    dpg.set_value("fg_msg", "skeleton loaded — prune, name, Save")


def forge_raw(*_):
    tag = "fg_rawwin"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    spec = forge_tree_to_spec() if FORGE_SPEC else (FORGE_SPEC or {})
    with dpg.window(label="raw spec { }", modal=True, tag=tag, width=680,
                    height=560, pos=(220, 90)):
        raw = dpg.add_input_text(multiline=True, width=-1, height=-52,
                                 default_value=json.dumps(spec, indent=2))

        def apply():
            global FORGE_SPEC
            try:
                FORGE_SPEC = json.loads(dpg.get_value(raw))
            except Exception as e:              # noqa: BLE001
                dpg.set_value("fg_msg", f"raw spec isn't valid JSON: {e}")
                return
            dpg.delete_item(tag)
            forge_show_tree()
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Apply  ", callback=apply)
            dpg.add_button(label="Cancel",
                           callback=lambda: dpg.delete_item(tag))


def forge_save(*_):
    name = dpg.get_value("fg_file").strip()
    if not name:
        dpg.set_value("fg_msg", "give it a file name first")
        return
    spec = forge_tree_to_spec()
    err = MP._validate(spec)
    if err:
        dpg.set_value("fg_msg", f"spec problem: {err}")
        return
    os.makedirs(MP.MACRO_DIR, exist_ok=True)
    path = os.path.join(MP.MACRO_DIR, name + ".json")
    json.dump(spec, open(path, "w", encoding="utf-8"), indent=2)
    dpg.set_value("fg_msg", f"saved {os.path.basename(path)} — it's in Macros")
    refresh_macro_buttons()


def forge_ai(*_):
    tag = "fg_aiwin"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    with dpg.window(label="Forge from a command", modal=True, tag=tag,
                    width=520, height=230, pos=(260, 180)):
        dpg.add_text("Command to forge (must exist on this machine):",
                     color=TEXT)
        cmd_in = dpg.add_input_text(width=-1)
        dpg.add_text("Its --help goes to the Professor; his proposed\n"
                     "spec lands in the tree for YOUR pruning.", color=DIM)

        def go():
            cmd = (dpg.get_value(cmd_in).strip().split() or [""])[0]
            dpg.delete_item(tag)
            if cmd:
                forge_start(cmd)
        with dpg.group(horizontal=True):
            dpg.add_button(label="  Forge  ", callback=go)
            dpg.add_button(label="Cancel",
                           callback=lambda: dpg.delete_item(tag))


def forge_start(cmd):
    global FORGE_CMD
    if not shutil.which(cmd):
        dpg.set_value("fg_msg", f"no such command on this machine: {cmd}")
        return
    try:
        r = subprocess.run([cmd, "--help"], capture_output=True, timeout=10)
        help_text = (r.stdout or r.stderr).decode("utf-8", "replace")
        if len(help_text.strip()) < 40:
            r = subprocess.run([cmd, "-h"], capture_output=True, timeout=10)
            help_text = (r.stdout or r.stderr).decode("utf-8", "replace")
    except Exception as e:                      # noqa: BLE001
        dpg.set_value("fg_msg", f"couldn't read {cmd} --help: {e}")
        return
    FORGE_CMD = cmd
    dpg.set_value("fg_file", cmd)
    dpg.set_value("fg_msg", f"the Professor is reading `{cmd} --help`... "
                            "(a minute or two)")
    prompt = MP.FORGE_HEAD + f"\nCOMMAND: {cmd}\nHELP TEXT:\n{help_text[:5000]}"

    def work():
        try:
            _w, ans = BUYER.ask_mesh(prompt, candidates=candidates())
            text = ans or "(no model answered)"
        except Exception as ex:                 # noqa: BLE001
            text = f"(forge failed: {ex})"

        def done():
            global FORGE_SPEC
            obj = MP._first_json(text)
            if obj is None:
                dpg.set_value("fg_msg", "the Professor went off-protocol — "
                                        "see { } for his raw reply")
                FORGE_SPEC = {"name": cmd, "kind": "command", "command": cmd,
                              "fields": [], "_raw": text}
                return
            obj["kind"] = "command"
            obj["command"] = cmd
            FORGE_SPEC = obj
            forge_show_tree()
            err = MP._validate(obj)
            dpg.set_value("fg_msg",
                          f"proposed — fix before saving: {err}" if err else
                          "the Professor proposes — untick what you don't "
                          "want, tweak labels/defaults, then Save")
        ui(done)
    threading.Thread(target=work, daemon=True).start()


# ── the Editor: writing pad + shoulder-reader ────────────────────────────────
def ed_key(*_):
    global ED_DIRTY, ED_LAST_KEY
    ED_DIRTY = True
    ED_LAST_KEY = time.time()


def ed_open_pick(_s, app_data):
    global ED_PATH, ED_DIRTY
    path = app_data.get("file_path_name", "")
    if not path:
        return
    try:
        dpg.set_value("editor", open(path, encoding="utf-8",
                                     errors="replace").read())
        ED_PATH = path
        ED_DIRTY = False
        dpg.set_value("ed_notes", f"opened {os.path.basename(path)}")
    except Exception as e:                      # noqa: BLE001
        dpg.set_value("ed_notes", f"couldn't open: {e}")


def ed_save_pick(_s, app_data):
    global ED_PATH
    path = app_data.get("file_path_name", "")
    if path:
        ED_PATH = path
        ed_save()


def ed_save(*_):
    if not ED_PATH:
        dpg.show_item("edsavedlg")
        return
    try:
        open(ED_PATH, "w", encoding="utf-8").write(dpg.get_value("editor"))
        dpg.set_value("ed_notes", f"saved {os.path.basename(ED_PATH)}")
    except Exception as e:                      # noqa: BLE001
        dpg.set_value("ed_notes", f"couldn't save: {e}")


def ed_review(*_):
    global REVIEW_BUSY, ED_DIRTY
    if REVIEW_BUSY:
        return
    draft = dpg.get_value("editor").strip()
    if len(draft) < 40:
        dpg.set_value("ed_notes", "(draft too short to review)")
        return
    REVIEW_BUSY = True
    ED_DIRTY = False
    dpg.set_value("ed_notes", "the Professor is reading...")

    def work():
        global REVIEW_BUSY
        try:
            _w, ans = BUYER.ask_mesh(MP.REVIEW_PROMPT + draft[:6000],
                                     candidates=candidates())
            note = ans or "(no model answered)"
        except Exception as e:                  # noqa: BLE001
            note = f"(review failed: {e})"

        def done():
            global REVIEW_BUSY
            dpg.set_value("ed_notes", note)
            REVIEW_BUSY = False
        ui(done)
    threading.Thread(target=work, daemon=True).start()


def auto_loop():
    while True:
        time.sleep(5)
        try:
            if (dpg.get_value("ed_auto") and ED_DIRTY and not REVIEW_BUSY
                    and not BUSY and time.time() - ED_LAST_KEY > 90):
                ui(ed_review)
        except Exception:
            pass


# ── build ────────────────────────────────────────────────────────────────────
def build():
    with dpg.font_registry():
        if os.path.exists(FONT):
            dpg.bind_font(dpg.add_font(FONT, FONT_SIZE))
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

    with dpg.theme(tag="chatpane"):
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, CHAT_BG)
    with dpg.theme(tag="linkbtn"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 0, 0, 0))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (40, 46, 62))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (52, 60, 80))
            dpg.add_theme_color(dpg.mvThemeCol_Text, BLU)
    with dpg.theme(tag="greenbtn"):
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, GRN)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (87, 224, 160))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (46, 160, 110))
            dpg.add_theme_color(dpg.mvThemeCol_Text, (12, 14, 20))

    with dpg.window(tag="main"):
        with dpg.group(horizontal=True):
            # ── left: the macro workshop ──────────────────────────────────
            with dpg.child_window(width=380, tag="workshop"):
                dpg.add_text("macro workshop", color=DIM)
                with dpg.tab_bar():
                    with dpg.tab(label=" Macros "):
                        with dpg.child_window(tag="maclist", height=-1):
                            pass
                    with dpg.tab(label=" Forge "):
                        with dpg.group(horizontal=True):
                            dpg.add_text("file (.json):", color=DIM)
                            dpg.add_input_text(tag="fg_file", width=-1)
                        dpg.add_text("command: ?", tag="fg_cmdlbl", color=DIM)
                        with dpg.group(horizontal=True):
                            dpg.add_text("button name", color=DIM)
                            dpg.add_input_text(tag="fg_name", width=-1)
                        with dpg.group(horizontal=True):
                            b = dpg.add_button(label="Forge...",
                                               callback=forge_ai)
                            dpg.bind_item_theme(b, "greenbtn")
                            dpg.add_button(label="new", callback=forge_new)
                            dpg.add_button(label="{ }", callback=forge_raw)
                            dpg.add_button(label="Save", callback=forge_save)
                        dpg.add_text("", tag="fg_msg", color=DIM, wrap=340)
                        dpg.add_text("tick = keep - edit labels & defaults",
                                     color=DIM)
                        with dpg.child_window(tag="fg_rows", height=-1):
                            pass
                    with dpg.tab(label=" Editor "):
                        with dpg.group(horizontal=True):
                            dpg.add_button(label="Open", callback=lambda:
                                           dpg.show_item("edopendlg"))
                            dpg.add_button(label="Save", callback=ed_save)
                            dpg.add_button(label="Review", callback=ed_review)
                            dpg.add_checkbox(label="auto", tag="ed_auto")
                        dpg.add_input_text(tag="editor", multiline=True,
                                           width=-1, height=-190,
                                           callback=ed_key)
                        dpg.add_text("assistant notes", color=DIM)
                        dpg.add_input_text(tag="ed_notes", multiline=True,
                                           readonly=True, width=-1, height=150)
            # ── right: the chat ───────────────────────────────────────────
            with dpg.group():
                with dpg.group(horizontal=True):
                    hdr = dpg.add_text("Ask the mesh", color=TEXT)
                    if big:
                        dpg.bind_item_font(hdr, big)
                dpg.add_input_text(multiline=True, width=-1, height=100,
                                   tag="prompt")
                with dpg.group(horizontal=True):
                    dpg.add_button(label="Attach file",
                                   callback=lambda: dpg.show_item("filedlg"))
                    dpg.add_text("", tag="attachlbl", color=DIM)
                    dpg.add_button(label="A-", small=True,
                                   callback=lambda: zoom(-0.1))
                    dpg.add_button(label="A+", small=True,
                                   callback=lambda: zoom(+0.1))
                    dpg.add_button(label="New chat", callback=new_chat)
                    ask = dpg.add_button(label="   Ask   ", tag="askbtn",
                                         callback=on_ask)
                    dpg.bind_item_theme(ask, "greenbtn")
                with dpg.tab_bar():
                    with dpg.tab(label=" Chat "):
                        with dpg.child_window(tag="chat", height=-32):
                            dpg.add_text("You're connected to the mesh — ask "
                                         "the Professor anything. Ctrl+Enter "
                                         "sends.", color=DIM, wrap=880)
                            dpg.add_spacer(height=6)
                    with dpg.tab(label=" FlowCode taste "):
                        dpg.add_text("DPG's native node editor — FlowCode's "
                                     "future organ, stock:", color=DIM)
                        with dpg.node_editor(tag="nodes", height=-32):
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

    dpg.bind_item_theme("chat", "chatpane")
    refresh_macro_buttons()

    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         callback=on_attach_pick, tag="filedlg",
                         width=760, height=460,
                         default_path=os.path.expanduser("~")):
        dpg.add_file_extension(".*")
        dpg.add_file_extension(".txt", color=tuple(GRN))
        dpg.add_file_extension(".md", color=tuple(GRN))
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         callback=ed_open_pick, tag="edopendlg",
                         width=760, height=460,
                         default_path=os.path.expanduser("~")):
        dpg.add_file_extension(".*")
    with dpg.file_dialog(directory_selector=False, show=False, modal=True,
                         callback=ed_save_pick, tag="edsavedlg",
                         width=760, height=460,
                         default_path=os.path.expanduser("~")):
        dpg.add_file_extension(".*")

    with dpg.handler_registry():
        dpg.add_key_press_handler(dpg.mvKey_Return, callback=_ctrl_enter)
        dpg.add_mouse_wheel_handler(callback=_ctrl_wheel)


def _ctrl_wheel(_s, app_data):
    """Ctrl+scroll = live text zoom, the way every civilised app does it."""
    if (dpg.is_key_down(dpg.mvKey_LControl)
            or dpg.is_key_down(dpg.mvKey_RControl)):
        zoom(0.05 if app_data > 0 else -0.05)


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
    def show():
        if n:
            set_status(f"mesh ready · {n} node(s) reachable", GRN)
        else:
            set_status("no nodes reachable — is the tunnel/HP up?", RED)
    try:
        ui(show)
    except Exception:
        pass


def main():
    dpg.create_context()
    build()
    if os.environ.get("SMOKE"):
        print("SMOKE OK — UI built clean")
        dpg.destroy_context()
        return
    dpg.create_viewport(title="Mesh-Chat — TernOO (Dear PyGui)",
                        width=1380, height=940, x_pos=40, y_pos=40)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("main", True)
    dpg.set_global_font_scale(SCALE)          # your remembered zoom
    threading.Thread(target=_probe, daemon=True).start()
    threading.Thread(target=auto_loop, daemon=True).start()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
