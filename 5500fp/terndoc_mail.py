#!/usr/bin/env python3
"""terndoc_mail.py — TernDoc S4: the ship's mail, on the ship's editor.

MailSurface: read the POBOX (repo `private/POBOX/`, newest first, parsed
headers) with TernDoc-rendered styled bodies, and compose with the shared
engine — markdown source pane + live rendered preview, spellcheck pass
included. SEND IS THE DROP: the letter is written into
`private/POBOX/Outbox/` and the standing watcher stamps, names, commits,
pushes and archives, exactly as it always has. This module invents no
transport; it inherits the rails.

Twin pattern (Mesh-Chat's, on the captain's consolidation ruling):
  * standalone:  python3 terndoc_mail.py            (p2pcp venv)
  * embedded:    build_mail_tab() inside a dpg.tab — mesh_chat_dpg adds
                 `with dpg.tab(label=" Mail "): terndoc_mail.build_mail_tab()`
Same module, same behavior, one maintenance surface.

Added: 22 Sep 2026 (S4). Authors: Stevo + Claude.
"""

import os
import re
import sys

import dearpygui.dearpygui as dpg

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import terndoc as TD

_HERE = os.path.dirname(os.path.abspath(__file__))
POBOX = os.path.join(os.path.dirname(_HERE), "private", "POBOX")
OUTBOX = os.path.join(POBOX, "Outbox")
ROSTER = "CC, CF5, CAI, Stevo, crew"

COL_TEXT = (220, 220, 225)
COL_BOLD = (245, 245, 250)
COL_ITAL = (200, 210, 235)
COL_CODE = (235, 200, 140)
COL_CODE_BG = (45, 45, 55)
COL_LINK = (120, 170, 250)
COL_HEAD = (240, 220, 160)
BASE_SIZE = 15

M = {"files": [], "checker": None, "prefix": "mail"}


def _t(name):
    return f"{M['prefix']}_{name}"


# ── mailbox reading ──────────────────────────────────────────────────────────
def list_mail():
    if not os.path.isdir(POBOX):
        return []
    out = []
    for f in os.listdir(POBOX):
        p = os.path.join(POBOX, f)
        if os.path.isfile(p) and f.endswith(".md"):
            out.append(f)
    # date-stamped letters first, newest first; README and friends last
    return sorted(out, key=lambda f: (f[0].isdigit(), f), reverse=True)


def parse_headers(text):
    """Best-effort From/To/Subject from the ship's letter conventions."""
    hdr = {"from": "?", "to": "?", "subject": ""}
    for ln in text.splitlines()[:14]:
        m = re.match(r"(From|To|Subject):\s*(.+)", ln.strip())
        if m:
            hdr[m.group(1).lower()] = m.group(2).strip()
        m2 = re.match(r"#\s+(.*)", ln.strip())
        if m2 and not hdr["subject"]:
            hdr["subject"] = m2.group(1)
    return hdr


# ── rendered read pane (drawlist; shared style family with terndoc_dpg) ──────
def _measure(text, _sk=None):
    if not text:
        return 0
    sz = dpg.get_text_size(text)
    if not sz or sz[0] <= 0:
        return 8 * len(text)
    return sz[0]


def render_doc_into(drawlist, doc, wrap_px):
    import terndoc_editor as ED
    dpg.delete_item(drawlist, children_only=True)
    lay = ED.Layout(doc, _measure, wrap_px, int(BASE_SIZE * 1.35))
    dpg.configure_item(drawlist, height=max(lay.height + 30, 60))
    for ln in lay.lines:
        meta = lay.block_meta[ln["bi"]]
        kind = meta["kind"]
        size = {"h1": BASE_SIZE * 1.6, "h2": BASE_SIZE * 1.35,
                "h3": BASE_SIZE * 1.15}.get(kind, BASE_SIZE)
        x, y = 8, 6 + ln["y"]
        if kind == "code":
            dpg.draw_rectangle((4, y), (wrap_px + 12, y + ln["h"]),
                               fill=COL_CODE_BG, color=COL_CODE_BG,
                               parent=drawlist)
        if meta["prefix"] and ln["start"] == 0:
            dpg.draw_text((x, y), meta["prefix"], size=size,
                          color=COL_TEXT, parent=drawlist)
            x += _measure(meta["prefix"])
        for frag, sk, href, w, _s0 in ln["segs"]:
            col = (COL_LINK if href else
                   {"b": COL_BOLD, "i": COL_ITAL, "bi": COL_BOLD,
                    "c": COL_CODE}.get(sk, COL_TEXT))
            if kind in ("h1", "h2", "h3"):
                col = COL_HEAD
            dpg.draw_text((x, y), frag, size=size, color=col,
                          parent=drawlist)
            if sk in ("b", "bi"):
                dpg.draw_text((x + 0.7, y), frag, size=size, color=col,
                              parent=drawlist)
            if href:
                dpg.draw_line((x, y + ln["h"] - 3), (x + w, y + ln["h"] - 3),
                              color=COL_LINK, parent=drawlist)
            x += w


# ── callbacks ────────────────────────────────────────────────────────────────
def refresh_list(*_):
    M["files"] = list_mail()
    items = []
    for f in M["files"]:
        try:
            with open(os.path.join(POBOX, f), encoding="utf-8") as fh:
                h = parse_headers(fh.read(2000))
            items.append(f"{f[:16]}  {h['from']} → {h['to']}"[:80])
        except Exception:
            items.append(f)
    dpg.configure_item(_t("list"), items=items,
                       num_items=min(14, max(4, len(items))))


def open_selected(*_):
    sel = dpg.get_value(_t("list"))
    items = dpg.get_item_configuration(_t("list"))["items"]
    if sel not in items:
        return
    fname = M["files"][items.index(sel)]
    with open(os.path.join(POBOX, fname), encoding="utf-8") as f:
        text = f.read()
    doc = TD.from_markdown(text)
    wrap = max(320, dpg.get_item_rect_size(_t("readwin"))[0] - 40)
    render_doc_into(_t("readcanvas"), doc, wrap)
    dpg.set_value(_t("readname"), fname)


def preview(*_):
    md = dpg.get_value(_t("body"))
    doc = TD.from_markdown(md or "*empty*")
    wrap = max(320, dpg.get_item_rect_size(_t("prevwin"))[0] - 40)
    render_doc_into(_t("prevcanvas"), doc, wrap)
    if M["checker"]:
        n = len(TD.spellcheck(doc, M["checker"]))
        dpg.set_value(_t("spell"), f"spell: {n} flagged" if n else "spell: clean")


def send(*_):
    to = (dpg.get_value(_t("to")) or "crew").strip()
    subject = (dpg.get_value(_t("subject")) or "no subject").strip()
    body = dpg.get_value(_t("body")) or ""
    if not body.strip():
        dpg.set_value(_t("status"), "refusing to send an empty letter")
        return
    os.makedirs(OUTBOX, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", subject.lower()).strip("-")[:48] or "letter"
    path = os.path.join(OUTBOX, f"{slug}.md")
    letter = (f"To: {to}\nFrom: CC (via TernDoc mail)\n"
              f"Subject: {subject}\n\n{body}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.write(letter)
    dpg.set_value(_t("status"),
                  f"dropped {os.path.basename(path)} — the drop IS the send")
    dpg.set_value(_t("body"), "")
    dpg.set_value(_t("subject"), "")


def save_html(*_):
    body = dpg.get_value(_t("body")) or ""
    doc = TD.from_markdown(body or "*empty*")
    out = os.path.join(os.path.expanduser("~"), "terndoc-letter.html")
    TD.save_as(doc, out, title=dpg.get_value(_t("subject")) or "letter")
    dpg.set_value(_t("status"), f"saved {out}")


# ── surface builder (works standalone or inside any parent/tab) ─────────────
def build_mail_tab(prefix="mail"):
    M["prefix"] = prefix
    if M["checker"] is None:
        try:
            M["checker"] = TD.WordlistChecker()
        except Exception:
            M["checker"] = None
    with dpg.group(horizontal=True):
        dpg.add_button(label="Refresh box", callback=refresh_list)
        dpg.add_button(label="Open", callback=open_selected)
        dpg.add_text("", tag=_t("readname"))
    with dpg.group(horizontal=True):
        with dpg.group(width=430):
            dpg.add_listbox(tag=_t("list"), items=[], num_items=10,
                            width=-1, callback=open_selected)
            dpg.add_separator()
            dpg.add_text("Compose")
            dpg.add_input_text(tag=_t("to"), hint=f"To ({ROSTER})",
                               width=-1)
            dpg.add_input_text(tag=_t("subject"), hint="Subject", width=-1)
            dpg.add_input_text(tag=_t("body"), multiline=True, width=-1,
                               height=220, tab_input=True,
                               hint="markdown body — preview renders it",
                               callback=preview)
            with dpg.group(horizontal=True):
                dpg.add_button(label="SEND (drop to Outbox)", callback=send)
                dpg.add_button(label="Preview", callback=preview)
                dpg.add_button(label="Save HTML", callback=save_html)
                dpg.add_text("", tag=_t("spell"))
            dpg.add_text("", tag=_t("status"))
        with dpg.group():
            dpg.add_text("Letter")
            with dpg.child_window(tag=_t("readwin"), height=300, width=-1):
                dpg.add_drawlist(tag=_t("readcanvas"), width=1400, height=80)
            dpg.add_text("Compose preview")
            with dpg.child_window(tag=_t("prevwin"), height=-1, width=-1):
                dpg.add_drawlist(tag=_t("prevcanvas"), width=1400, height=80)
    refresh_list()


def main():
    dpg.create_context()
    with dpg.window(tag="root"):
        build_mail_tab()
    dpg.create_viewport(title="TernDoc Mail — the drop is the send",
                        width=1180, height=720)
    dpg.setup_dearpygui()
    dpg.show_viewport()
    dpg.set_primary_window("root", True)
    dpg.start_dearpygui()
    dpg.destroy_context()


if __name__ == "__main__":
    main()
