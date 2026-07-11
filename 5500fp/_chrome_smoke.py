"""Headless full-app smoke for the TAB_CHROME chrome contract.

Builds the entire FlowCode GUI (run_gui), then — instead of entering mainloop —
cycles every tab through the real <<NotebookTabChanged>> handler and checks:
  * all 10 tabs created, in canon order;
  * firing each tab's change handler raises nothing (key-based dispatch holds);
  * exactly one live "?  Help" affordance per tab (no global bar, no Mesh double);
  * the Mesh header ? Help opens the shared viewer AND offers the trust diagram
    (help_extra wired through TAB_CHROME).
Run under a working DISPLAY. Prints RESULT: <json> and exits non-zero on failure.
"""
import importlib.util
import json
import os
import sys
import traceback

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_FLOWCODE = os.path.join(_ROOT, "FlowCode", "flowcode.py")

CANON = ["Flow", "GUI", "Sheet", "Connectors", "Shell", "Text",
         "Babble-Fish", "Academy", "Mesh", "Documentation"]

import tkinter as tk
from tkinter import ttk

res = {"ok": True, "errors": []}


def fail(msg):
    res["ok"] = False
    res["errors"].append(msg)


def all_widgets(w):
    yield w
    for c in w.winfo_children():
        yield from all_widgets(c)


def live_help_buttons(root):
    out = []
    for w in all_widgets(root):
        if isinstance(w, tk.Button):
            try:
                if w.cget("text").strip() == "?  Help" and w.winfo_ismapped():
                    out.append(w)
            except tk.TclError:
                pass
    return out


def fake_mainloop(self, *a, **k):
    root = self.winfo_toplevel()
    try:
        root.update_idletasks()
        root.update()
        nb = next((w for w in all_widgets(root)
                   if isinstance(w, ttk.Notebook)), None)
        if nb is None:
            fail("no ttk.Notebook found"); root.destroy(); return
        tabs = nb.tabs()
        res["n_tabs"] = len(tabs)
        res["titles"] = [nb.tab(t, "text").strip() for t in tabs]
        if res["titles"] != CANON:
            fail(f"tab order != canon: {res['titles']}")

        per_tab_help = {}
        for t in tabs:
            title = nb.tab(t, "text").strip()
            try:
                nb.select(t)
                root.update_idletasks(); root.update()   # real <<NotebookTabChanged>>
            except Exception as e:                        # noqa: BLE001
                fail(f"tab '{title}' change handler raised: {e!r}")
                continue
            per_tab_help[title] = len(live_help_buttons(root))
        res["help_buttons_per_tab"] = per_tab_help
        bad = {k: v for k, v in per_tab_help.items() if v != 1}
        if bad:
            fail(f"tabs without exactly one live ? Help: {bad}")

        # Mesh ? Help end-to-end: invoke it, expect a viewer Toplevel that also
        # carries the native "Show the trust diagram" button (help_extra wired in).
        mesh_id = tabs[res["titles"].index("Mesh")]
        nb.select(mesh_id); root.update_idletasks(); root.update()
        before = set(map(str, root.winfo_children()))
        hb = live_help_buttons(root)
        if len(hb) == 1:
            hb[0].invoke()
            root.update_idletasks(); root.update()
            new_tops = [w for w in root.winfo_children()
                        if str(w) not in before and isinstance(w, tk.Toplevel)]
            diagram_btn = any(
                isinstance(x, tk.Button)
                and x.cget("text").strip() == "Show the trust diagram"
                for top in new_tops for x in all_widgets(top))
            res["mesh_help_opens_window"] = bool(new_tops)
            res["mesh_help_has_diagram"] = diagram_btn
            if not new_tops:
                fail("Mesh ? Help opened no window")
            if not diagram_btn:
                fail("Mesh Help window missing trust-diagram button (help_extra)")
            for top in new_tops:
                try: top.destroy()
                except tk.TclError: pass
        else:
            fail(f"Mesh had {len(hb)} live Help buttons, expected 1")

        # Babble-Fish Translator sub-pane must actually render — guards the
        # exec_module fix (the "Split ⇆" button is unique to TranslatorView; if
        # the module were left un-exec'd again this drops to False).
        bf_id = tabs[res["titles"].index("Babble-Fish")]
        nb.select(bf_id); root.update_idletasks(); root.update()
        res["translator_pane_live"] = any(
            isinstance(w, tk.Button) and w.cget("text").strip() == "Split ⇆"
            for w in all_widgets(root))
        if not res["translator_pane_live"]:
            fail("Babble-Fish Translator pane did not render (Split button absent)")
    except Exception:                                     # noqa: BLE001
        fail("smoke crashed:\n" + traceback.format_exc())
    finally:
        try: root.destroy()
        except Exception: pass                            # noqa: BLE001


tk.Misc.mainloop = fake_mainloop

spec = importlib.util.spec_from_file_location("flowcode", _FLOWCODE)
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)
try:
    fc.run_gui()
except Exception:                                         # noqa: BLE001
    fail("run_gui() raised:\n" + traceback.format_exc())

print("RESULT:", json.dumps(res, indent=2))
sys.exit(0 if res["ok"] else 1)
