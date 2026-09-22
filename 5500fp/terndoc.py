"""terndoc.py — TernDoc S1: the face-blind rich-text document engine.

Captain's GO 22-09-2026 ("fire away when ready"): ONE document model for
every text surface on the ship — chat, editor, mail, help — so features
are built once, in here, and every face (DPG custom editor, thin Tk
legacy adapters, whatever comes after) stays a dumb renderer + input
router. Nothing that must survive lives in a face.

Design rules (from the captain's steers, 22-09):
  * NO toolkit imports. Pure python, testable like dick_kernel.
  * Cursor and selection are MODEL state, not widget state — the custom
    editor's caret math lives here, wysiwyg-ready before wysiwyg chrome.
  * ALL text passes through a TextCodec — the forward-compat seam for
    the TernOO native glyph-plane encoding (CF5's charter). Codec #1 is
    Unicode; nothing in the model may assume it is the only one.
  * Markdown is the canonical wire format (the fleet already speaks it:
    POBOX letters, docs-bench, the whitepaper). HTML is render-OUT only:
    save-as-html exists, html editing does not.
  * Spellcheck is a face-blind pass: the model reports issue spans; a
    renderer draws squiggles however it likes. Wordlist backend has no
    dependencies; suggestions are edit-distance-1 (Norvig style).
  * Undo is whole-block snapshot based — honest and simple at letter
    scale; refine only if a real document ever makes it slow.

The .fc dialect Sync in the Text tab is NOT this module's business —
the substrate projection keeps its own sacred path.

Added: 22 Sep 2026. Authors: Stevo + Claude.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

# ── the codec seam ───────────────────────────────────────────────────────────
class UnicodeCodec:
    """Codec #1: python str / Unicode. The interface IS the contract —
    a future ternary-glyph-plane codec implements exactly these five
    methods and the model never notices the swap."""

    name = "unicode"

    def normalize(self, s: str) -> str:
        return s.replace("\r\n", "\n").replace("\r", "\n")

    def units(self, s: str) -> int:
        """Length in codec units (cursor arithmetic uses THIS, never len)."""
        return len(s)

    def slice(self, s: str, a: int, b: int) -> str:
        return s[a:b]

    def words(self, s: str):
        """Yield (start, end, word) for spell-class passes."""
        for m in re.finditer(r"[A-Za-z][A-Za-z']*", s):
            yield m.start(), m.end(), m.group(0)

    def canonical_bytes(self, s: str) -> bytes:
        return s.encode("utf-8")


# ── spans and blocks ─────────────────────────────────────────────────────────
STYLES = ("b", "i", "c")            # bold, italic, inline-code
BLOCK_KINDS = ("p", "h1", "h2", "h3", "ul", "ol", "code")


def span(text, styles=(), href=None):
    return {"t": text, "st": sorted(set(styles) & set(STYLES)),
            "href": href}


def block(kind="p", spans_=None, lang=""):
    if kind not in BLOCK_KINDS:
        raise ValueError(f"unknown block kind {kind!r}")
    if kind == "code":
        return {"kind": "code", "lang": lang,
                "text": "" if spans_ is None else spans_}
    return {"kind": kind, "spans": spans_ if spans_ is not None else []}


def _normalize_spans(spans_):
    """Drop empties, merge adjacent spans with identical attrs."""
    out = []
    for s in spans_:
        if not s["t"]:
            continue
        if out and out[-1]["st"] == s["st"] and out[-1]["href"] == s["href"]:
            out[-1] = dict(out[-1], t=out[-1]["t"] + s["t"])
        else:
            out.append(dict(s))
    return out


# ── the document ─────────────────────────────────────────────────────────────
UNDO_CAP = 200


class TernDoc:
    def __init__(self, blocks=None, codec=None):
        self.codec = codec or UnicodeCodec()
        self.blocks = blocks if blocks else [block("p")]
        self.cursor = (0, 0)              # (block index, codec-unit offset)
        self.anchor = None                # selection anchor or None
        self._undo, self._redo = [], []

    # ── inspection ──────────────────────────────────────────────────────
    def text_of(self, bi):
        b = self.blocks[bi]
        if b["kind"] == "code":
            return b["text"]
        return "".join(s["t"] for s in b["spans"])

    def block_len(self, bi):
        return self.codec.units(self.text_of(bi))

    # ── undo machinery (whole-doc snapshot; small docs, honest cost) ────
    def _checkpoint(self):
        self._undo.append((json.loads(json.dumps(self.blocks)),
                           self.cursor, self.anchor))
        if len(self._undo) > UNDO_CAP:
            self._undo.pop(0)
        self._redo.clear()

    def undo(self):
        if not self._undo:
            return False
        self._redo.append((json.loads(json.dumps(self.blocks)),
                           self.cursor, self.anchor))
        self.blocks, self.cursor, self.anchor = self._undo.pop()
        return True

    def redo(self):
        if not self._redo:
            return False
        self._undo.append((json.loads(json.dumps(self.blocks)),
                           self.cursor, self.anchor))
        self.blocks, self.cursor, self.anchor = self._redo.pop()
        return True

    # ── span surgery helpers ────────────────────────────────────────────
    def _split_at(self, spans_, off):
        """Split a span list at codec offset; returns (left, right)."""
        left, right, seen = [], [], 0
        for s in spans_:
            n = self.codec.units(s["t"])
            if seen + n <= off:
                left.append(dict(s))
            elif seen >= off:
                right.append(dict(s))
            else:
                cut = off - seen
                left.append(dict(s, t=self.codec.slice(s["t"], 0, cut)))
                right.append(dict(s, t=self.codec.slice(s["t"], cut, n)))
            seen += n
        return left, right

    # ── edit operations ─────────────────────────────────────────────────
    def insert_text(self, bi, off, text, styles=(), href=None):
        text = self.codec.normalize(text)
        if not text:
            return
        self._checkpoint()
        b = self.blocks[bi]
        if b["kind"] == "code":
            t = b["text"]
            b["text"] = t[:off] + text + t[off:]
        else:
            left, right = self._split_at(b["spans"], off)
            b["spans"] = _normalize_spans(
                left + [span(text, styles, href)] + right)
        self.cursor = (bi, off + self.codec.units(text))
        self.anchor = None

    def delete_range(self, bi, a, b_off):
        if a > b_off:
            a, b_off = b_off, a
        if a == b_off:
            return
        self._checkpoint()
        b = self.blocks[bi]
        if b["kind"] == "code":
            t = b["text"]
            b["text"] = t[:a] + t[b_off:]
        else:
            left, _ = self._split_at(b["spans"], a)
            _, right = self._split_at(b["spans"], b_off)
            b["spans"] = _normalize_spans(left + right)
        self.cursor = (bi, a)
        self.anchor = None

    def toggle_style(self, bi, a, b_off, flag):
        if flag not in STYLES:
            raise ValueError(f"unknown style {flag!r}")
        if a > b_off:
            a, b_off = b_off, a
        b = self.blocks[bi]
        if b["kind"] == "code" or a == b_off:
            return
        self._checkpoint()
        left, rest = self._split_at(b["spans"], a)
        mid, right = self._split_at(rest, b_off - a)
        on = all(flag in s["st"] for s in mid) if mid else False
        for s in mid:
            st = set(s["st"])
            (st.discard if on else st.add)(flag)
            s["st"] = sorted(st)
        b["spans"] = _normalize_spans(left + mid + right)

    def set_link(self, bi, a, b_off, href):
        if a > b_off:
            a, b_off = b_off, a
        b = self.blocks[bi]
        if b["kind"] == "code" or a == b_off:
            return
        self._checkpoint()
        left, rest = self._split_at(b["spans"], a)
        mid, right = self._split_at(rest, b_off - a)
        for s in mid:
            s["href"] = href
        b["spans"] = _normalize_spans(left + mid + right)

    def split_block(self, bi, off):
        """Enter key: split one block into two at the cursor."""
        self._checkpoint()
        b = self.blocks[bi]
        if b["kind"] == "code":
            t = b["text"]
            b["text"], tail = t[:off], t[off:]
            nb = block("code", tail, b["lang"])
        else:
            left, right = self._split_at(b["spans"], off)
            b["spans"] = _normalize_spans(left)
            kind = b["kind"] if b["kind"] in ("ul", "ol") else "p"
            nb = block(kind, _normalize_spans(right))
        self.blocks.insert(bi + 1, nb)
        self.cursor = (bi + 1, 0)
        self.anchor = None

    def merge_with_previous(self, bi):
        """Backspace at block start."""
        if bi == 0:
            return
        self._checkpoint()
        prev, cur = self.blocks[bi - 1], self.blocks[bi]
        at = self.block_len(bi - 1)
        if prev["kind"] == "code" or cur["kind"] == "code":
            joined = self.text_of(bi - 1) + self.text_of(bi)
            self.blocks[bi - 1] = block("code", joined,
                                        prev.get("lang", ""))
        else:
            prev["spans"] = _normalize_spans(prev["spans"] + cur["spans"])
        del self.blocks[bi]
        self.cursor = (bi - 1, at)
        self.anchor = None

    def set_kind(self, bi, kind, lang=""):
        self._checkpoint()
        b = self.blocks[bi]
        if kind == "code":
            self.blocks[bi] = block("code", self.text_of(bi), lang)
        elif b["kind"] == "code":
            self.blocks[bi] = block(kind, [span(b["text"])])
        else:
            nb = block(kind, b["spans"])
            self.blocks[bi] = nb

    def insert_block(self, bi, b):
        self._checkpoint()
        self.blocks.insert(bi, b)

    def delete_block(self, bi):
        self._checkpoint()
        del self.blocks[bi]
        if not self.blocks:
            self.blocks = [block("p")]
        self.cursor = (min(bi, len(self.blocks) - 1), 0)
        self.anchor = None

    # ── canonical form ─────────────────────────────────────────────────
    def canonical_bytes(self):
        return json.dumps(self.blocks, separators=(",", ":"),
                          sort_keys=True).encode("utf-8")

    def digest(self):
        return hashlib.sha3_256(self.canonical_bytes()).hexdigest()


# ── markdown: the wire format ────────────────────────────────────────────────
_INLINE = re.compile(
    r"(\*\*\*(?P<bi>.+?)\*\*\*)|(\*\*(?P<b>.+?)\*\*)|(\*(?P<i>.+?)\*)"
    r"|(`(?P<c>[^`]+)`)|(\[(?P<lt>[^\]]+)\]\((?P<href>[^)\s]+)\))")


def _parse_inline(text, base=()):
    """Recursive over the honest subset: bold may contain italic/code/link,
    italic may contain code. `base` carries inherited styles."""
    spans_, pos = [], 0
    for m in _INLINE.finditer(text):
        if m.start() > pos:
            spans_.append(span(text[pos:m.start()], base))
        if m.group("bi") is not None:
            spans_.append(span(m.group("bi"), base + ("b", "i")))
        elif m.group("b") is not None:
            spans_.extend(_parse_inline(m.group("b"), base + ("b",)))
        elif m.group("i") is not None:
            spans_.extend(_parse_inline(m.group("i"), base + ("i",)))
        elif m.group("c") is not None:
            spans_.append(span(m.group("c"), base + ("c",)))
        else:
            spans_.append(span(m.group("lt"), base, m.group("href")))
        pos = m.end()
    if pos < len(text):
        spans_.append(span(text[pos:], base))
    return _normalize_spans(spans_)


def from_markdown(md, codec=None):
    codec = codec or UnicodeCodec()
    lines = codec.normalize(md).split("\n")
    blocks, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            lang = ln[3:].strip()
            body, i = [], i + 1
            while i < len(lines) and not lines[i].startswith("```"):
                body.append(lines[i])
                i += 1
            i += 1                                    # closing fence
            blocks.append(block("code", "\n".join(body), lang))
            continue
        if not ln.strip():
            i += 1
            continue
        m = re.match(r"(#{1,3})\s+(.*)", ln)
        if m:
            blocks.append(block(f"h{len(m.group(1))}",
                                _parse_inline(m.group(2))))
        elif re.match(r"[-*]\s+", ln):
            blocks.append(block("ul", _parse_inline(ln[2:])))
        elif re.match(r"\d+\.\s+", ln):
            blocks.append(block("ol",
                                _parse_inline(ln.split(". ", 1)[1])))
        else:
            blocks.append(block("p", _parse_inline(ln)))
        i += 1
    return TernDoc(blocks or None, codec)


def _span_md(s):
    t = s["t"]
    if s["href"]:
        return f"[{t}]({s['href']})"
    if "c" in s["st"]:
        return f"`{t}`"
    if "b" in s["st"] and "i" in s["st"]:
        return f"***{t}***"
    if "b" in s["st"]:
        return f"**{t}**"
    if "i" in s["st"]:
        return f"*{t}*"
    return t


def _spans_md(spans_):
    """Serialize a span list with RUN GROUPING: consecutive bold spans get
    ONE **…** pair with italic sub-runs inside — adjacency of markers
    (**a*****b***) would otherwise re-parse wrong."""
    out, i = [], 0
    while i < len(spans_):
        s = spans_[i]
        plain_b = ("b" in s["st"] and not s["href"] and "c" not in s["st"])
        if plain_b:
            j = i
            while (j < len(spans_) and "b" in spans_[j]["st"]
                   and not spans_[j]["href"] and "c" not in spans_[j]["st"]):
                j += 1
            inner = "".join(
                f"*{sp['t']}*" if "i" in sp["st"] else sp["t"]
                for sp in spans_[i:j])
            out.append(f"**{inner}**")
            i = j
            continue
        plain_i = (s["st"] == ["i"] and not s["href"])
        if plain_i:
            j = i
            while (j < len(spans_) and spans_[j]["st"] == ["i"]
                   and not spans_[j]["href"]):
                j += 1
            out.append("*" + "".join(sp["t"] for sp in spans_[i:j]) + "*")
            i = j
            continue
        out.append(_span_md(s))
        i += 1
    return "".join(out)


def to_markdown(doc):
    out, prev_list = [], False
    for i, b in enumerate(doc.blocks):
        is_list = b["kind"] in ("ul", "ol")
        if i and not (is_list and prev_list):
            out.append("")
        if b["kind"] == "code":
            out.append(f"```{b['lang']}")
            out.append(b["text"])
            out.append("```")
        else:
            body = _spans_md(b["spans"])
            prefix = {"h1": "# ", "h2": "## ", "h3": "### ",
                      "ul": "- ", "ol": "1. ", "p": ""}[b["kind"]]
            out.append(prefix + body)
        prev_list = is_list
    return "\n".join(out) + "\n"


# ── html: render-out only (save-as-html; html editing does not exist) ────────
def _esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;"))


def _span_html(s):
    t = _esc(s["t"])
    if "c" in s["st"]:
        t = f"<code>{t}</code>"
    if "i" in s["st"]:
        t = f"<em>{t}</em>"
    if "b" in s["st"]:
        t = f"<strong>{t}</strong>"
    if s["href"]:
        t = f'<a href="{_esc(s["href"])}">{t}</a>'
    return t


def to_html(doc, title=""):
    body, in_list = [], None
    for b in doc.blocks:
        kind = b["kind"]
        if in_list and kind != in_list:
            body.append(f"</{'ul' if in_list == 'ul' else 'ol'}>")
            in_list = None
        if kind == "code":
            cls = f' class="language-{_esc(b["lang"])}"' if b.get("lang") else ""
            body.append(f"<pre><code{cls}>{_esc(b['text'])}</code></pre>")
        elif kind in ("ul", "ol"):
            if in_list != kind:
                body.append(f"<{kind}>")
                in_list = kind
            inner = "".join(_span_html(s) for s in b["spans"])
            body.append(f"<li>{inner}</li>")
        else:
            tag = kind if kind in ("h1", "h2", "h3") else "p"
            inner = "".join(_span_html(s) for s in b["spans"])
            body.append(f"<{tag}>{inner}</{tag}>")
    if in_list:
        body.append(f"</{'ul' if in_list == 'ul' else 'ol'}>")
    inner = "\n".join(body)
    return ("<!DOCTYPE html>\n<html>\n<head>\n<meta charset=\"utf-8\">\n"
            f"<title>{_esc(title)}</title>\n</head>\n<body>\n"
            f"{inner}\n</body>\n</html>\n")


def save_as(doc, path, title=""):
    """Write the document by extension: .md (canonical) or .html/.htm
    (render-out). Anything else is refused loudly — no silent guesses."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".md":
        data = to_markdown(doc)
    elif ext in (".html", ".htm"):
        data = to_html(doc, title or os.path.basename(path))
    else:
        raise ValueError(f"save_as: unsupported extension {ext!r}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)
    return path


# ── spellcheck: a face-blind pass ───────────────────────────────────────────
_WORDS_PATHS = ("/usr/share/dict/words", "/usr/share/dict/american-english")
_ALPHA = "abcdefghijklmnopqrstuvwxyz'"


class WordlistChecker:
    """Zero-dependency backend: system wordlist + edit-distance-1
    suggestions (Norvig style). An aspell/hunspell subprocess backend can
    slot in later behind the same two methods."""

    def __init__(self, path=None, extra=()):
        self.words = set()
        p = path or next((x for x in _WORDS_PATHS if os.path.exists(x)), None)
        if p:
            with open(p, encoding="utf-8", errors="ignore") as f:
                self.words = {w.strip().lower() for w in f if w.strip()}
        self.words |= {w.lower() for w in extra}

    def check(self, word):
        w = word.lower()
        return (not self.words or w in self.words
                or w.rstrip("'s") in self.words)

    def _edits1(self, w):
        sp = [(w[:i], w[i:]) for i in range(len(w) + 1)]
        out = set()
        for a, b in sp:
            if b:
                out.add(a + b[1:])                       # delete
                for ch in _ALPHA:
                    out.add(a + ch + b[1:])              # replace
            if len(b) > 1:
                out.add(a + b[1] + b[0] + b[2:])         # transpose
            for ch in _ALPHA:
                out.add(a + ch + b)                      # insert
        return out

    def suggest(self, word, k=5):
        w = word.lower()
        hits = sorted(self._edits1(w) & self.words)
        return hits[:k]


def spellcheck(doc, checker):
    """Yield (block_idx, start, end, word, suggestions) for every
    misspelling in prose. Code blocks, inline-code spans, and link
    targets are exempt — code is not prose."""
    issues = []
    for bi, b in enumerate(doc.blocks):
        if b["kind"] == "code":
            continue
        base = 0
        for s in b["spans"]:
            n = doc.codec.units(s["t"])
            if "c" not in s["st"]:
                for a, z, w in doc.codec.words(s["t"]):
                    if len(w) > 1 and not checker.check(w):
                        issues.append((bi, base + a, base + z, w,
                                       checker.suggest(w)))
            base += n
    return issues
