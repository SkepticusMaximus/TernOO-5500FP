"""terndoc_html.py — Road A's bridge: browser HTML → TernDoc.

The web face edits in a contenteditable surface; what comes back is the
browser's HTML dialect. This module parses the SUPPORTED SUBSET into
TernDoc blocks so markdown stays the canonical form — the engine never
becomes an HTML system; the browser is just another dumb face whose
native output we translate at the door.

Subset accepted (everything else degrades to its text content):
  h1 h2 h3 p div li  → blocks     (div soup — browsers love it — = p)
  ul ol              → list context for their li children
  pre                → code block
  b strong           → bold        i em → italic
  code               → inline code (inside pre: part of the block)
  a[href]            → link
  br                 → block break (contenteditable's favorite)

Added: 22 Sep 2026 (Road A). Authors: Stevo + Claude.
"""

from __future__ import annotations

from html.parser import HTMLParser

import terndoc as TD

_BLOCK_TAGS = {"h1", "h2", "h3", "p", "div", "li", "pre", "blockquote"}


class _Walker(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []
        self.spans = []
        self.kind = "p"
        self.list_ctx = []          # stack of "ul"/"ol"
        self.styles = []            # stack of style flags
        self.hrefs = []             # stack of link targets
        self.in_pre = 0
        self.pre_text = []

    # — helpers —
    def _flush(self, force=False):
        spans = [s for s in self.spans if s["t"]]
        if spans or force:
            self.blocks.append(TD.block(self.kind, spans))
        self.spans = []

    def _cur_styles(self):
        out = set()
        for s in self.styles:
            out.add(s)
        return tuple(out)

    def _cur_href(self):
        return self.hrefs[-1] if self.hrefs else None

    # — parser events —
    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self._flush()
            return
        if tag == "pre":
            self._flush()
            self.in_pre += 1
            return
        if self.in_pre:
            if tag == "code":
                cls = dict(attrs).get("class", "")
                if cls.startswith("language-"):
                    self.pre_lang = cls[len("language-"):]
            return
        if tag in ("ul", "ol"):
            self._flush()
            self.list_ctx.append(tag)
        elif tag in _BLOCK_TAGS:
            self._flush()
            if tag in ("h1", "h2", "h3"):
                self.kind = tag
            elif tag == "li":
                self.kind = self.list_ctx[-1] if self.list_ctx else "ul"
            else:
                self.kind = "p"
        elif tag in ("b", "strong"):
            self.styles.append("b")
        elif tag in ("i", "em"):
            self.styles.append("i")
        elif tag == "code":
            self.styles.append("c")
        elif tag == "a":
            href = dict(attrs).get("href")
            self.hrefs.append(href)

    def handle_endtag(self, tag):
        if tag == "pre":
            if self.in_pre:
                self.in_pre -= 1
                text = "".join(self.pre_text).strip("\n")
                self.blocks.append(TD.block("code", text,
                                            getattr(self, "pre_lang", "")))
                self.pre_text = []
                self.pre_lang = ""
            return
        if self.in_pre:
            return
        if tag in ("ul", "ol"):
            self._flush()
            if self.list_ctx:
                self.list_ctx.pop()
            self.kind = "p"
        elif tag in _BLOCK_TAGS:
            self._flush()
            self.kind = (self.list_ctx[-1] if self.list_ctx else "p") \
                if self.list_ctx else "p"
        elif tag in ("b", "strong") and "b" in self.styles:
            self.styles.remove("b")
        elif tag in ("i", "em") and "i" in self.styles:
            self.styles.remove("i")
        elif tag == "code" and "c" in self.styles:
            self.styles.remove("c")
        elif tag == "a" and self.hrefs:
            self.hrefs.pop()

    def handle_data(self, data):
        if self.in_pre:
            self.pre_text.append(data)
            return
        text = data.replace(" ", " ")
        if text.strip("\n") == "" and "\n" in text:
            return                          # formatting whitespace
        text = text.replace("\n", " ")
        if text:
            self.spans.append(TD.span(text, self._cur_styles(),
                                      self._cur_href()))

    def result(self):
        self._flush()
        blocks = [b for b in self.blocks
                  if b["kind"] == "code" or b["spans"]]
        return blocks or None


def from_html(html, codec=None):
    """Browser HTML (supported subset) → TernDoc."""
    w = _Walker()
    w.feed(html)
    w.close()
    return TD.TernDoc(w.result(), codec)


def html_to_markdown(html):
    return TD.to_markdown(from_html(html))
