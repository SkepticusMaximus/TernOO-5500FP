"""terndoc_tk.py — TernDoc S5: the THIN Tk legacy adapter.

Renders a TernDoc into a tk.Text using tags. Deliberately read-mostly and
deliberately dumb: no editing logic lives here (that is terndoc_editor's,
face-blind), and per the captain's ruling no NEW dependency on Tk is ever
built — this exists so the legacy panes (help, ghost, macro output areas)
can display shipped markdown through the SAME engine as the DPG surfaces,
with zero investment beyond this file.

Usage:
    import terndoc, terndoc_tk
    doc = terndoc.from_markdown(md_text)
    terndoc_tk.render_into(text_widget, doc)          # tags auto-configured

Added: 22 Sep 2026 (S5). Authors: Stevo + Claude.
"""

from __future__ import annotations

import terndoc as TD

_FAM = "Monospace"
_BASE = 10


def configure_tags(t, base=_BASE, family=_FAM,
                   code_bg="#2d2d37", link_fg="#78aafa"):
    t.tag_configure("td_h1", font=(family, base + 5, "bold"),
                    spacing1=8, spacing3=6)
    t.tag_configure("td_h2", font=(family, base + 3, "bold"),
                    spacing1=6, spacing3=4)
    t.tag_configure("td_h3", font=(family, base + 1, "bold"),
                    spacing1=4, spacing3=3)
    t.tag_configure("td_p", font=(family, base), spacing3=5)
    t.tag_configure("td_li", font=(family, base),
                    lmargin1=18, lmargin2=32, spacing3=2)
    t.tag_configure("td_b", font=(family, base, "bold"))
    t.tag_configure("td_i", font=(family, base, "italic"))
    t.tag_configure("td_bi", font=(family, base, "bold italic"))
    t.tag_configure("td_c", font=(family, base), background=code_bg)
    t.tag_configure("td_codeblock", font=(family, base),
                    background=code_bg, lmargin1=14, lmargin2=14,
                    spacing1=4, spacing3=6)
    t.tag_configure("td_link", foreground=link_fg, underline=True)


def _span_tags(s, block_tag):
    tags = [block_tag]
    st = s["st"]
    if "b" in st and "i" in st:
        tags.append("td_bi")
    elif "b" in st:
        tags.append("td_b")
    elif "i" in st:
        tags.append("td_i")
    if "c" in st:
        tags.append("td_c")
    if s["href"]:
        tags.append("td_link")
    return tuple(tags)


def render_into(t, doc, clear=True, link_cb=None):
    """Paint `doc` into tk.Text `t`. If `link_cb(href)` is given, links
    become clickable. Widget state (readonly etc.) is the caller's."""
    configure_tags(t)
    prev_state = t.cget("state")
    t.configure(state="normal")
    if clear:
        t.delete("1.0", "end")
    n_links = 0
    for b in doc.blocks:
        kind = b["kind"]
        if kind == "code":
            t.insert("end", b["text"] + "\n", ("td_codeblock",))
            continue
        block_tag = {"h1": "td_h1", "h2": "td_h2", "h3": "td_h3",
                     "ul": "td_li", "ol": "td_li"}.get(kind, "td_p")
        if kind == "ul":
            t.insert("end", "• ", (block_tag,))
        elif kind == "ol":
            t.insert("end", "1. ", (block_tag,))
        for s in b["spans"]:
            tags = _span_tags(s, block_tag)
            if s["href"] and link_cb is not None:
                n_links += 1
                ltag = f"td_href_{n_links}"
                t.tag_configure(ltag)
                t.tag_bind(ltag, "<Button-1>",
                           lambda _e, h=s["href"]: link_cb(h))
                tags = tags + (ltag,)
            t.insert("end", s["t"], tags)
        t.insert("end", "\n")
    t.configure(state=prev_state)


def render_markdown_into(t, md_text, **kw):
    """Convenience: parse + paint in one call."""
    render_into(t, TD.from_markdown(md_text), **kw)
