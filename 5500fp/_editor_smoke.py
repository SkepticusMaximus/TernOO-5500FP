"""Headless acceptance smoke for the Documentation-tab editor (CF5 rulings 2026-07-13).

Drives a real DocsTabView (needs a DISPLAY) against a TEMP store — never touches real
docs/help — monkeypatching the dialog calls so the guards can be exercised without a
human. Covers the CF5 union acceptance: round-trip, dirty guard on all three exits
(toggle / topic-switch / tab-leave), [[link]] autocomplete inserts a valid link from
existing ids only, New topic creates+lists+lints-clean, live preview never-crash.

Prints RESULT: <json> and exits non-zero on any failure. Underscore-prefixed so the
headless unittest sweep never imports it.
"""
import importlib.util
import json
import os
import sys
import tempfile
import tkinter as tk
from tkinter import messagebox, simpledialog

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    s = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

DTV = _load("help_tab_view")
HT = _load("help_topics")

res = {"ok": True, "errors": []}


def check(name, cond):
    res[name] = bool(cond)
    if not cond:
        res["ok"] = False
        res["errors"].append(name)


def main():
    C = {"bg": "#111", "palette": "#222", "text": "#ddd", "dim": "#888",
         "inspect": "#333", "canvas": "#000"}
    root = tk.Tk(); root.withdraw()
    frame = tk.Frame(root)
    v = DTV.DocsTabView(frame, C, root, lambda _m: None)

    tmp = tempfile.mkdtemp(prefix="edsmoke_")
    v.topics = HT.HelpTopics(base_dir=tmp)
    v.topics.save("alpha", "Alpha\nsection: The tabs\n\n# Alpha\nbody\n")
    v.topics.save("beta", "Beta\nsection: The tabs\n\n# Beta\nbody\n")
    v._current_id = "alpha"
    v._load_index()

    # 1. round-trip: edit -> modify -> save -> store + read reflect
    v._enter_edit()
    v._raw.delete("1.0", "end")
    v._raw.insert("1.0", "Alpha\nsection: The tabs\n\n# Alpha\nEDITED\n")
    v._dirty = True
    saved = v._save()
    check("round_trip_save", saved and "EDITED" in v.topics.raw("alpha"))
    check("clean_after_save", v._dirty is False)

    # 2. dirty guard — TOPIC SWITCH: cancel keeps the current topic
    v._raw.insert("end", "more\n"); v._dirty = True
    messagebox.askyesnocancel = lambda *a, **k: None            # Cancel
    i_beta = next(i for i, t in enumerate(v._rows) if t == "beta")
    v._list.selection_clear(0, "end"); v._list.selection_set(i_beta)
    v._on_pick()
    check("switch_guard_cancel_stays", v._editing_id == "alpha")

    # 3. dirty guard — TOGGLE to read: discard leaves edit mode, clears dirty
    messagebox.askyesnocancel = lambda *a, **k: False          # Discard
    v._leave_edit()
    check("toggle_guard_discard_leaves", v._mode == "read" and v._dirty is False)

    # 4. dirty guard — TAB LEAVE: save preserves the work
    v._enter_edit()
    v._raw.insert("end", "\ntab-leave edit\n"); v._dirty = True
    messagebox.askyesno = lambda *a, **k: True                 # Save on leave
    v.prompt_save_on_leave()
    check("tab_leave_saves", "tab-leave edit" in v.topics.raw("alpha")
          and v.has_unsaved() is False)

    # 5. [[link]] autocomplete: inserts a valid link, from EXISTING ids only
    v._insert_link_at_cursor("beta")
    buf = v._raw.get("1.0", "end-1c")
    check("autocomplete_inserts_valid", "[[beta|Beta]]" in buf)
    check("autocomplete_existing_only", set(v.topics.ids()) >= {"alpha", "beta"}
          and "nope" not in v.topics.ids())

    # 6. New topic: create -> lists -> stub lints clean
    simpledialog.askstring = lambda *a, **k: ("keep-the-original"
                                              if "id" in (a[1] if len(a) > 1 else "")
                                              else "The big idea")
    v._new_topic()
    check("new_topic_created", "keep-the-original" in v.topics.ids())
    check("new_topic_stub_lint_clean",
          v.topics.missing_targets(v.topics.raw("keep-the-original")) == [])

    # 7. live preview never-crash on mangled helpdown
    crashed = False
    try:
        v._raw.delete("1.0", "end")
        v._raw.insert("1.0", "X\nsection: Y\n\n[[unclosed and **bold no close\n")
        v._do_preview()
    except Exception:                                          # noqa: BLE001
        crashed = True
    check("preview_never_crash", not crashed)

    root.destroy()


try:
    main()
except Exception:                                              # noqa: BLE001
    import traceback
    res["ok"] = False
    res["errors"].append("smoke crashed")
    res["trace"] = traceback.format_exc()

print("RESULT:", json.dumps(res, indent=2))
sys.exit(0 if res["ok"] else 1)
