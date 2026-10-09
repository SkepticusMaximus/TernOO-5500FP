#!/home/stevo/.venvs/p2pcp/bin/python3
"""TernDO — the ship's captain's objective tracker.   (TernPIM tool #1)

A standalone FlowCode-ecosystem app (DPG + FlowCode theme/font) that keeps
OBJECTIVES and nested SUB-GOALS with a three-state status, free-text NOTES, a
full timestamped history, and a graphical timeline.

Status (glyph in the right-hand column — click to advance, right-click to set):
    ✓  pending        O  in progress        X  complete   (red)

Records are KEPT for history. They are never removed by normal use — delete is
an explicit, double-checked, confirmed action only. Every status change writes a
date+time stamp to the record's history and to the append-only timeline file.

Sensible defaults throughout: menu bar, Undo (Ctrl+Z), right-click context menu,
clipboard, keyboard shortcuts, selection. Objectives nest to any depth; each has
a notes field.

Part of TernPIM — a modular FlowCode PIM suite (100% TernOO, 100% FlowCode).

Data:   ~/.config/ternoo/todo.json      (objectives + sub-goals + notes + history)
        ~/.config/ternoo/timeline.json  (append-only log of every status change)
Launch: terndo.py          (or the TernDO menu / desktop icon)
"""
import os
import json
import datetime
import dearpygui.dearpygui as dpg

CFG = os.path.expanduser("~/.config/ternoo")
STORE = os.path.join(CFG, "todo.json")
TLINE = os.path.join(CFG, "timeline.json")
os.makedirs(CFG, exist_ok=True)

GRN, INK, DIM = (63, 208, 143), (230, 230, 236), (150, 150, 165)
BAD, ACC, AMB = (240, 130, 130), (110, 168, 254), (232, 200, 144)

STATUSES = ["pending", "progress", "complete"]
GLYPH = {"pending": "✓", "progress": "O", "complete": "X"}
SCOLOR = {"pending": ACC, "progress": AMB, "complete": BAD}
SLABEL = {"pending": "Pending", "progress": "In progress", "complete": "Complete"}
NEXT = {"pending": "progress", "progress": "complete", "complete": "pending"}

DB = {"version": 2, "seq": 0, "items": []}   # {id,text,status,parent,notes,history:[{ts,status,note?}]}
TIMELINE = []                                # [{ts,id,text,to,note?}]
UNDO = []                                    # (DB, TIMELINE) snapshots
SEL = [None]                                 # selected item id
ROW_SEL = {}                                 # id -> text-button item (rebuilt each render)
THEMES = {}


def _now():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ── persistence (+ one-time migration of the old flat list) ───────────────────
def _load_db():
    try:
        raw = json.load(open(STORE, encoding="utf-8"))
    except Exception:
        raw = []
    if isinstance(raw, dict) and raw.get("version") == 2:
        raw.setdefault("seq", len(raw.get("items", [])))
        for it in raw.get("items", []):
            it.setdefault("parent", None)
            it.setdefault("status", "pending")
            it.setdefault("notes", "")
            it.setdefault("history", [])
        return raw
    try:
        if os.path.exists(STORE):
            json.dump(raw, open(STORE + ".v1bak", "w", encoding="utf-8"), indent=1)
    except Exception:
        pass
    items, seq, now = [], 0, _now()
    for t in (raw if isinstance(raw, list) else []):
        seq += 1
        st = "complete" if t.get("done") else "pending"
        items.append({"id": f"g{seq}", "text": t.get("text", ""), "status": st,
                      "parent": None, "notes": "",
                      "history": [{"ts": now, "status": st, "note": "imported"}]})
    return {"version": 2, "seq": seq, "items": items}


def _load_timeline():
    try:
        return json.load(open(TLINE, encoding="utf-8"))
    except Exception:
        return []


def _save():
    json.dump(DB, open(STORE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def _save_timeline():
    json.dump(TIMELINE, open(TLINE, "w", encoding="utf-8"), indent=1, ensure_ascii=False)


def _by_id(iid):
    for it in DB.get("items", []):
        if it["id"] == iid:
            return it
    return None


def _descendants(iid):
    out, stack = set(), [iid]
    while stack:
        p = stack.pop()
        for x in DB.get("items", []):
            if x.get("parent") == p and x["id"] not in out:
                out.add(x["id"]); stack.append(x["id"])
    return out


# ── undo ─────────────────────────────────────────────────────────────────────
def _snapshot():
    UNDO.append((json.loads(json.dumps(DB)), json.loads(json.dumps(TIMELINE))))
    if len(UNDO) > 100:
        UNDO.pop(0)


def _undo(*_):
    if UNDO:
        db, tl = UNDO.pop()
        DB.clear(); DB.update(db)
        TIMELINE[:] = tl
        if SEL[0] and not _by_id(SEL[0]):
            SEL[0] = None
        _save(); _save_timeline(); _render()


# ── ordering (recursive, arbitrary depth) + render ────────────────────────────
def _ordered():
    """[(item, depth), ...] — depth-first; orphans float to top level."""
    ids = {it["id"] for it in DB.get("items", [])}
    kids = {}
    for it in DB.get("items", []):
        p = it.get("parent")
        kids.setdefault(p if p in ids else None, []).append(it)
    out = []

    def walk(pid, depth):
        for it in kids.get(pid, []):
            out.append((it, depth))
            walk(it["id"], depth + 1)

    walk(None, 0)
    return out


def _counts():
    c = {"pending": 0, "progress": 0, "complete": 0}
    for it in DB.get("items", []):
        c[it.get("status", "pending")] = c.get(it.get("status", "pending"), 0) + 1
    return c


def _render():
    ROW_SEL.clear()
    dpg.delete_item("tasklist", children_only=True)
    rows = _ordered()
    if not rows:
        dpg.add_text("  no objectives yet — type one above and hit Add",
                     color=DIM, parent="tasklist")
    for it, depth in rows:
        iid = it["id"]
        st = it.get("status", "pending")
        has_notes = bool((it.get("notes") or "").strip())
        with dpg.group(horizontal=True, parent="tasklist"):
            if depth:
                dpg.add_spacer(width=depth * 22)
            lbl = ("· " if depth else "") + ("✎ " if has_notes else "") + it["text"]
            tb = dpg.add_button(label=lbl, width=-52, callback=_select, user_data=iid)
            if THEMES:
                dpg.bind_item_theme(tb, THEMES["sel"] if iid == SEL[0]
                                    else THEMES["row"])
            ROW_SEL[iid] = tb
            sb = dpg.add_button(label=GLYPH[st], width=40,
                                callback=_cycle_status, user_data=iid)
            if THEMES:
                dpg.bind_item_theme(sb, THEMES["st_" + st])
            with dpg.tooltip(sb):
                dpg.add_text(f"{SLABEL[st]} — click to advance")
            for anchor in (tb, sb):
                with dpg.popup(anchor, mousebutton=dpg.mvMouseButton_Right):
                    with dpg.menu(label="Set status"):
                        dpg.add_menu_item(label="✓  Pending", callback=_set_status,
                                          user_data=(iid, "pending"))
                        dpg.add_menu_item(label="O  In progress", callback=_set_status,
                                          user_data=(iid, "progress"))
                        dpg.add_menu_item(label="X  Complete", callback=_set_status,
                                          user_data=(iid, "complete"))
                    dpg.add_menu_item(label="Properties…", callback=_props_from, user_data=iid)
                    dpg.add_menu_item(label="Add sub-goal…", callback=_add_sub_dialog,
                                      user_data=iid)
                    dpg.add_menu_item(label="Copy text", callback=_ctx_copy, user_data=iid)
                    dpg.add_menu_item(label="History…", callback=_show_history, user_data=iid)
                    dpg.add_separator()
                    dpg.add_menu_item(label="Delete record…", callback=_confirm_delete,
                                      user_data=iid)
                    dpg.add_separator()
                    dpg.add_menu_item(label="Undo  (Ctrl+Z)", callback=_undo)
    c = _counts()
    if dpg.does_item_exist("count"):
        dpg.set_value("count", f"{len(DB.get('items', []))} records · "
                      f"{c['pending']} pending · {c['progress']} in progress · "
                      f"{c['complete']} complete")


# ── status changes (timestamped → history + timeline) ─────────────────────────
def _apply_status(iid, new):
    it = _by_id(iid)
    if not it or it.get("status") == new:
        return
    _snapshot()
    ts = _now()
    it["status"] = new
    it.setdefault("history", []).append({"ts": ts, "status": new})
    TIMELINE.append({"ts": ts, "id": iid, "text": it["text"], "to": new})
    _save(); _save_timeline(); _render()


def _cycle_status(_s, _a, iid):
    it = _by_id(iid)
    if it:
        _apply_status(iid, NEXT[it.get("status", "pending")])


def _set_status(_s, _a, ud):
    _apply_status(ud[0], ud[1])


# ── add / edit / notes ────────────────────────────────────────────────────────
def _new_item(text, parent=None):
    DB["seq"] = DB.get("seq", 0) + 1
    iid = f"g{DB['seq']}"
    ts = _now()
    DB["items"].append({"id": iid, "text": text, "status": "pending",
                        "parent": parent, "notes": "",
                        "history": [{"ts": ts, "status": "pending", "note": "created"}]})
    TIMELINE.append({"ts": ts, "id": iid, "text": text, "to": "pending", "note": "created"})
    return iid


def _add(*_):
    txt = (dpg.get_value("input") or "").strip()
    if txt:
        _snapshot(); _new_item(txt); _save(); _save_timeline()
        dpg.set_value("input", ""); _render()
    if dpg.does_item_exist("input"):
        dpg.focus_item("input")


def _add_sub_dialog(_s, _a, parent_id):
    if dpg.does_item_exist("sub_modal"):
        dpg.delete_item("sub_modal")
    parent = _by_id(parent_id)
    with dpg.window(label="Add sub-goal", modal=True, tag="sub_modal",
                    width=420, height=130, pos=[48, 110], no_resize=True):
        dpg.add_text("under: " + (parent["text"][:46] if parent else "?"), color=DIM)
        dpg.add_input_text(tag="sub_field", hint="sub-goal…", width=-1,
                           on_enter=True, callback=lambda *a: _sub_commit(parent_id))
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Add", width=100, callback=lambda *a: _sub_commit(parent_id))
            dpg.add_button(label="Cancel", width=100,
                           callback=lambda *a: dpg.delete_item("sub_modal"))
    dpg.focus_item("sub_field")


def _sub_commit(parent_id):
    txt = (dpg.get_value("sub_field") or "").strip()
    if txt and _by_id(parent_id):
        _snapshot(); _new_item(txt, parent=parent_id); _save(); _save_timeline(); _render()
    if dpg.does_item_exist("sub_modal"):
        dpg.delete_item("sub_modal")


def _props_from(_s, _a, iid):
    _open_props(iid)


def _props_sel(*_):
    if SEL[0]:
        _open_props(SEL[0])


def _open_props(iid):
    """Properties dialog — text + status + notes + metadata, all in one place."""
    it = _by_id(iid)
    if not it:
        return
    if dpg.does_item_exist("props_modal"):
        dpg.delete_item("props_modal")
    with dpg.window(label="Properties", modal=True, tag="props_modal",
                    width=500, height=450, pos=[32, 50], no_resize=True):
        dpg.add_text("Text", color=ACC)
        dpg.add_input_text(tag="p_text", default_value=it["text"], width=-1,
                           on_enter=True, callback=lambda *a: _props_commit(iid))
        dpg.add_spacer(height=6)
        dpg.add_text("Status", color=ACC)
        dpg.add_radio_button(tag="p_status", items=[SLABEL[s] for s in STATUSES],
                             default_value=SLABEL.get(it.get("status", "pending")),
                             horizontal=True)
        dpg.add_spacer(height=6)
        dpg.add_text("Notes  (Markdown — shared format with skills/Obsidian)", color=ACC)
        dpg.add_input_text(tag="p_notes", default_value=it.get("notes", ""),
                           multiline=True, width=-1, height=175)
        dpg.add_spacer(height=6)
        h = it.get("history", [])
        meta = f"id {it['id']}  ·  created {h[0]['ts'] if h else '—'}  ·  {len(h)} change(s)"
        if it.get("parent"):
            meta += f"  ·  sub-goal of {it['parent']}"
        dpg.add_text(meta, color=DIM)
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Save", width=110, callback=lambda *a: _props_commit(iid))
            dpg.add_button(label="Cancel", width=110,
                           callback=lambda *a: dpg.delete_item("props_modal"))
    dpg.focus_item("p_text")


def _props_commit(iid):
    it = _by_id(iid)
    if it:
        new_text = (dpg.get_value("p_text") or "").strip()
        new_notes = dpg.get_value("p_notes") or ""
        lbl2st = {v: k for k, v in SLABEL.items()}
        new_status = lbl2st.get(dpg.get_value("p_status"), it.get("status"))
        tc = bool(new_text) and new_text != it["text"]
        nc = new_notes != it.get("notes", "")
        sc = new_status != it.get("status")
        if tc or nc or sc:
            _snapshot()
            if tc:
                it["text"] = new_text
            if nc:
                it["notes"] = new_notes
            if sc:
                ts = _now(); it["status"] = new_status
                it.setdefault("history", []).append({"ts": ts, "status": new_status})
                TIMELINE.append({"ts": ts, "id": iid, "text": it["text"], "to": new_status})
            _save(); _save_timeline(); _render()
    if dpg.does_item_exist("props_modal"):
        dpg.delete_item("props_modal")


# ── selection + clipboard ─────────────────────────────────────────────────────
def _select(_s, _a, iid):
    SEL[0] = iid
    _render()


def _ctx_copy(_s, _a, iid):
    it = _by_id(iid)
    if it:
        dpg.set_clipboard_text(it["text"])


def _copy_sel(*_):
    it = _by_id(SEL[0]) if SEL[0] else None
    if it:
        dpg.set_clipboard_text(it["text"])


def _paste_new(*_):
    try:
        txt = (dpg.get_clipboard_text() or "").strip()
    except Exception:
        txt = ""
    if txt:
        _snapshot(); _new_item(txt); _save(); _save_timeline(); _render()


# ── delete (gated: confirm + double-check; recursive) ─────────────────────────
def _confirm_delete(_s, _a, iid):
    it = _by_id(iid)
    if not it:
        return
    desc = _descendants(iid)
    if dpg.does_item_exist("del_modal"):
        dpg.delete_item("del_modal")
    with dpg.window(label="Delete record", modal=True, tag="del_modal",
                    width=440, height=240, pos=[40, 80], no_resize=True):
        dpg.add_text("Permanently delete this record?", color=BAD)
        dpg.add_text(it["text"], wrap=400, color=INK)
        if desc:
            dpg.add_text(f"This also deletes {len(desc)} nested sub-goal(s).", color=AMB)
        dpg.add_spacer(height=4)
        dpg.add_text("Records are normally kept for history. This removes it from",
                     color=DIM, wrap=400)
        dpg.add_text("the active list for good.", color=DIM, wrap=400)
        dpg.add_spacer(height=8)
        dpg.add_checkbox(label="I understand — remove it permanently", tag="del_ok",
                         callback=lambda _s, v: dpg.configure_item("del_go", enabled=v))
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Delete permanently", tag="del_go", enabled=False,
                           width=190, callback=lambda *a: _do_delete(iid))
            dpg.add_button(label="Cancel", width=100,
                           callback=lambda *a: dpg.delete_item("del_modal"))


def _do_delete(iid):
    if not dpg.get_value("del_ok"):
        return
    it = _by_id(iid)
    if it:
        _snapshot()
        ids = {iid} | _descendants(iid)
        ts = _now()
        for d in ids:
            d_it = _by_id(d)
            if d_it:
                TIMELINE.append({"ts": ts, "id": d, "text": d_it["text"],
                                 "to": "deleted", "note": "deleted"})
        DB["items"][:] = [x for x in DB["items"] if x["id"] not in ids]
        if SEL[0] in ids:
            SEL[0] = None
        _save(); _save_timeline(); _render()
    if dpg.does_item_exist("del_modal"):
        dpg.delete_item("del_modal")


def _delete_sel(*_):
    if SEL[0]:
        _confirm_delete(None, None, SEL[0])


# ── history + timeline views ──────────────────────────────────────────────────
def _show_history(_s, _a, iid):
    it = _by_id(iid)
    if not it:
        return
    if dpg.does_item_exist("hist_modal"):
        dpg.delete_item("hist_modal")
    with dpg.window(label="Record history", modal=True, tag="hist_modal",
                    width=460, height=340, pos=[50, 70]):
        dpg.add_text(it["text"][:54], color=GRN, wrap=430)
        dpg.add_separator()
        hist = it.get("history", [])
        if not hist:
            dpg.add_text("  (no recorded changes)", color=DIM)
        for h in hist:
            s = h.get("status", "?")
            with dpg.group(horizontal=True):
                dpg.add_text(GLYPH.get(s, "?"), color=SCOLOR.get(s, DIM))
                dpg.add_text(f"  {h.get('ts', '—')}   {SLABEL.get(s, s)}"
                             + (f"  ({h['note']})" if h.get("note") else ""), color=INK)
        if (it.get("notes") or "").strip():
            dpg.add_separator()
            dpg.add_text("Notes:", color=ACC)
            dpg.add_text(it["notes"], wrap=430, color=DIM)
        dpg.add_spacer(height=8)
        dpg.add_button(label="Close", width=100,
                       callback=lambda *a: dpg.delete_item("hist_modal"))


def _show_timeline(*_):
    if dpg.does_item_exist("tl_win"):
        dpg.delete_item("tl_win")
    ev = sorted(TIMELINE, key=lambda e: e.get("ts", ""))
    days = sorted({e.get("ts", "")[:10] for e in ev})
    with dpg.window(label="Timeline", tag="tl_win", width=640, height=580, pos=[30, 30]):
        dpg.add_text(f"{len(ev)} status change(s) across {len(days)} day(s) — oldest first",
                     color=DIM)
        with dpg.group(horizontal=True):
            for s in STATUSES:
                dpg.add_text(GLYPH[s], color=SCOLOR[s])
                dpg.add_text(SLABEL[s] + "  ", color=DIM)
            dpg.add_text("•", color=(200, 120, 120))
            dpg.add_text("deleted", color=DIM)
        dpg.add_separator()
        if not ev:
            dpg.add_text("  no status changes yet — advance a goal to begin its timeline",
                         color=DIM)
            dpg.add_spacer(height=6)
            dpg.add_button(label="Close", width=100,
                           callback=lambda *a: dpg.delete_item("tl_win"))
            return
        # height: each event 44px + each day header 30px
        h = 20 + len(ev) * 44 + len(days) * 30
        with dpg.child_window(autosize_x=True, height=-40):
            with dpg.drawlist(width=600, height=h):
                x0 = 30
                dpg.draw_line((x0, 6), (x0, h - 6), color=(70, 80, 100), thickness=2)
                y = 16
                cur_day = None
                for e in ev:
                    ts = e.get("ts", "")
                    day = ts[:10]
                    if day != cur_day:
                        cur_day = day
                        dpg.draw_text((10, y), day, size=15, color=GRN)
                        y += 26
                    to = e.get("to", "")
                    col = SCOLOR.get(to, (200, 120, 120) if to == "deleted" else DIM)
                    gly = GLYPH.get(to, "•" if to == "deleted" else "·")
                    dpg.draw_circle((x0, y + 8), 8, fill=col, color=col)
                    dpg.draw_text((x0 - 4, y + 1), gly, size=14, color=(20, 24, 32))
                    tgt = SLABEL.get(to, "Deleted" if to == "deleted" else to)
                    dpg.draw_text((x0 + 20, y - 3), ts[11:], size=13, color=DIM)
                    note = f"   ({e['note']})" if e.get("note") else ""
                    dpg.draw_text((x0 + 20, y + 14),
                                  f"{e.get('text', '')[:44]}  →  {tgt}{note}",
                                  size=15, color=INK)
                    y += 44
        dpg.add_button(label="Close", width=100,
                       callback=lambda *a: dpg.delete_item("tl_win"))


# ── misc ──────────────────────────────────────────────────────────────────────
def _focus_input(*_):
    if dpg.does_item_exist("input"):
        dpg.focus_item("input")


def _quit(*_):
    dpg.stop_dearpygui()


def _show_help(*_):
    if dpg.does_item_exist("help_modal"):
        dpg.delete_item("help_modal")
    with dpg.window(label="Keyboard shortcuts", modal=True, tag="help_modal",
                    width=400, height=320, pos=[60, 60], no_resize=True):
        for k, v in [("Enter", "add the typed objective"),
                     ("click status", "advance ✓ → O → X"),
                     ("Ctrl+Z", "undo the last change"),
                     ("Ctrl+C", "copy the selected record"),
                     ("Ctrl+V", "paste clipboard as an objective"),
                     ("F2 / Ctrl+E", "open Properties (text + status + notes)"),
                     ("Del", "delete selected (asks first)"),
                     ("Ctrl+N", "jump to the new box"),
                     ("double-click", "open Properties"),
                     ("right-click", "status / properties / sub-goal / history")]:
            with dpg.group(horizontal=True):
                dpg.add_text(f"{k:>13}", color=ACC)
                dpg.add_text("  " + v, color=INK)
        dpg.add_spacer(height=8)
        dpg.add_button(label="Close", width=100,
                       callback=lambda *a: dpg.delete_item("help_modal"))


# ── keyboard ──────────────────────────────────────────────────────────────────
def _ctrl():
    return dpg.is_key_down(dpg.mvKey_LControl) or dpg.is_key_down(dpg.mvKey_RControl)


def _typing():
    for t in ("input", "sub_field", "p_text", "p_notes"):
        if dpg.does_item_exist(t) and dpg.is_item_focused(t):
            return True
    return False


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


def _k_props(*_):
    if _ctrl() and not _typing():
        _props_sel()


def _k_delete(*_):
    if not _typing():
        _delete_sel()


def _k_edit(*_):
    if not _typing():
        _props_sel()


def _on_dblclick(_s, button):
    if button != 0:
        return
    for iid, sid in list(ROW_SEL.items()):
        if dpg.does_item_exist(sid) and dpg.is_item_hovered(sid):
            _open_props(iid)
            return


# ── build ─────────────────────────────────────────────────────────────────────
def _flat_theme(bg, text=None, align=0.0):
    with dpg.theme() as th:
        with dpg.theme_component(dpg.mvButton):
            dpg.add_theme_color(dpg.mvThemeCol_Button, bg)
            dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered,
                                tuple(min(255, c + 16) for c in bg))
            dpg.add_theme_color(dpg.mvThemeCol_ButtonActive,
                                tuple(min(255, c + 28) for c in bg))
            if text:
                dpg.add_theme_color(dpg.mvThemeCol_Text, text)
            dpg.add_theme_style(dpg.mvStyleVar_ButtonTextAlign, align, 0.5)
    return th


def build_ui():
    """Build window + widgets (no viewport) — callable headless for tests."""
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

    THEMES["row"] = _flat_theme((34, 40, 54))
    THEMES["sel"] = _flat_theme((46, 70, 110))
    for s in STATUSES:
        THEMES["st_" + s] = _flat_theme((34, 40, 54), text=SCOLOR[s], align=0.5)

    with dpg.window(tag="main", no_scrollbar=True, menubar=True):
        with dpg.menu_bar():
            with dpg.menu(label="File"):
                dpg.add_menu_item(label="New objective\tCtrl+N", callback=_focus_input)
                dpg.add_separator()
                dpg.add_menu_item(label="Quit", callback=_quit)
            with dpg.menu(label="Edit"):
                dpg.add_menu_item(label="Undo\tCtrl+Z", callback=_undo)
                dpg.add_separator()
                dpg.add_menu_item(label="Copy selected\tCtrl+C", callback=_copy_sel)
                dpg.add_menu_item(label="Paste as objective\tCtrl+V", callback=_paste_new)
                dpg.add_menu_item(label="Properties…\tF2", callback=_props_sel)
                dpg.add_separator()
                dpg.add_menu_item(label="Delete selected…\tDel", callback=_delete_sel)
            with dpg.menu(label="View"):
                dpg.add_menu_item(label="Timeline…", callback=_show_timeline)
            with dpg.menu(label="Help"):
                dpg.add_menu_item(label="Keyboard shortcuts", callback=_show_help)

        dpg.add_text("TernDO", color=GRN)
        dpg.add_text("TernPIM · objectives · sub-goals · notes · timeline", color=DIM)
        dpg.add_spacer(height=8)
        with dpg.group(horizontal=True):
            dpg.add_input_text(tag="input", hint="new objective…", width=-84,
                               on_enter=True, callback=_add)
            dpg.add_button(label=" Add ", width=78, callback=_add)
        dpg.add_spacer(height=4)
        with dpg.group(horizontal=True):
            dpg.add_text("status:", color=DIM)
            dpg.add_text(GLYPH["pending"], color=SCOLOR["pending"])
            dpg.add_text("pending ", color=DIM)
            dpg.add_text(GLYPH["progress"], color=SCOLOR["progress"])
            dpg.add_text("in progress ", color=DIM)
            dpg.add_text(GLYPH["complete"], color=SCOLOR["complete"])
            dpg.add_text("complete  · ✎ = has notes · right-click for options", color=DIM)
        dpg.add_spacer(height=4)
        dpg.add_child_window(tag="tasklist", height=-44, border=True)
        dpg.add_separator()
        with dpg.group(horizontal=True):
            dpg.add_text("", tag="count", color=DIM)
            dpg.add_spacer(width=12)
            dpg.add_button(label="Timeline", callback=_show_timeline)

    with dpg.handler_registry():
        dpg.add_key_press_handler(dpg.mvKey_Z, callback=_k_undo)
        dpg.add_key_press_handler(dpg.mvKey_C, callback=_k_copy)
        dpg.add_key_press_handler(dpg.mvKey_V, callback=_k_paste)
        dpg.add_key_press_handler(dpg.mvKey_N, callback=_k_new)
        dpg.add_key_press_handler(dpg.mvKey_E, callback=_k_props)
        dpg.add_key_press_handler(dpg.mvKey_Delete, callback=_k_delete)
        dpg.add_key_press_handler(dpg.mvKey_F2, callback=_k_edit)
        dpg.add_mouse_double_click_handler(callback=_on_dblclick)

    _render()
    dpg.bind_theme(theme)


def main():
    global DB, TIMELINE
    DB = _load_db()
    TIMELINE = _load_timeline()
    _save()
    dpg.create_context()
    build_ui()
    dpg.create_viewport(title="TernDO", width=520, height=620)
    dpg.setup_dearpygui()
    dpg.set_primary_window("main", True)
    dpg.show_viewport()
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
