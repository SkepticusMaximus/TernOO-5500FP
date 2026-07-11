"""helpdown — the deliberately small help-content format for FlowCode.

CF5-authored core, docs phase 2026-07.

A topic file is UTF-8 text:
  line 1            : the topic title (plain text)
  line 2 (optional) : "section: <name>"  — index-tree placement
  remainder         : helpdown body

Body syntax (ALL of it — this list is exhaustive by design):
  # Heading            level-1 heading line
  ## Heading           level-2 heading line
  - item               bullet line
  **bold**             bold span
  `code`               code span
  [[topic-id]]         link, label = topic-id
  [[topic-id|label]]   link with explicit label
  (blank line)         paragraph break

LAW: unknown or malformed syntax renders as literal text. The parser
NEVER raises on content. A help-file typo must never crash the IDE.

Output is renderer-agnostic: parse_topic() returns a dict the Tk
viewer (or any other surface: SVG, HTML) walks. No Tk imports here.
"""

# span styles
PLAIN, BOLD, CODE = "plain", "bold", "code"
# block kinds
H1, H2, BULLET, PARA = "h1", "h2", "bullet", "para"


def parse_inline(text):
    """Parse one line's inline syntax -> list of span dicts.

    span = {"text": str, "style": PLAIN|BOLD|CODE, "link": str|None}
    Unmatched **, `, [[ render literally (the never-crash law).
    """
    spans = []
    i, n = 0, len(text)
    buf = []

    def flush():
        if buf:
            spans.append({"text": "".join(buf), "style": PLAIN, "link": None})
            del buf[:]

    while i < n:
        # bold
        if text.startswith("**", i):
            end = text.find("**", i + 2)
            if end != -1 and end > i + 2:
                flush()
                spans.append({"text": text[i + 2:end], "style": BOLD,
                              "link": None})
                i = end + 2
                continue
            # unmatched: literal
        # code
        if text[i] == "`":
            end = text.find("`", i + 1)
            if end != -1 and end > i + 1:
                flush()
                spans.append({"text": text[i + 1:end], "style": CODE,
                              "link": None})
                i = end + 1
                continue
        # link
        if text.startswith("[[", i):
            end = text.find("]]", i + 2)
            if end != -1 and end > i + 2:
                inner = text[i + 2:end]
                if "|" in inner:
                    target, label = inner.split("|", 1)
                else:
                    target, label = inner, inner
                target = target.strip()
                label = label.strip()
                if target:  # empty target -> literal
                    flush()
                    spans.append({"text": label or target, "style": PLAIN,
                                  "link": target})
                    i = end + 2
                    continue
        buf.append(text[i])
        i += 1
    flush()
    return spans


def parse_topic(raw):
    """Parse a whole topic file's text -> topic dict.

    topic = {"title": str, "section": str|None, "blocks": [block]}
    block = {"kind": H1|H2|BULLET|PARA, "spans": [span]}
    Never raises on content. Empty input -> untitled empty topic.
    """
    lines = raw.split("\n") if raw else []
    title = lines[0].strip() if lines else ""
    body_start = 1
    section = None
    if len(lines) > 1 and lines[1].strip().lower().startswith("section:"):
        section = lines[1].split(":", 1)[1].strip() or None
        body_start = 2

    blocks = []
    para_spans = []

    def flush_para():
        if para_spans:
            blocks.append({"kind": PARA, "spans": list(para_spans)})
            del para_spans[:]

    for line in lines[body_start:]:
        stripped = line.strip()
        if not stripped:
            flush_para()
            continue
        if stripped.startswith("## "):
            flush_para()
            blocks.append({"kind": H2, "spans": parse_inline(stripped[3:])})
        elif stripped.startswith("# "):
            flush_para()
            blocks.append({"kind": H1, "spans": parse_inline(stripped[2:])})
        elif stripped.startswith("- "):
            flush_para()
            blocks.append({"kind": BULLET,
                           "spans": parse_inline(stripped[2:])})
        else:
            if para_spans:
                # paragraph continuation: join with a space
                para_spans.append({"text": " ", "style": PLAIN, "link": None})
            para_spans.extend(parse_inline(stripped))
    flush_para()
    return {"title": title or "(untitled)", "section": section,
            "blocks": blocks}


def topic_links(topic):
    """All link targets in a parsed topic (for the docs-lint dead-link
    check). Returns a sorted, de-duplicated list of target ids."""
    seen = set()
    for block in topic["blocks"]:
        for span in block["spans"]:
            if span["link"]:
                seen.add(span["link"])
    return sorted(seen)


def plain_text(topic):
    """Flatten a topic to searchable plain text (title + body).
    Used by the Documentation tab's v1 substring search."""
    parts = [topic["title"]]
    for block in topic["blocks"]:
        parts.append("".join(s["text"] for s in block["spans"]))
    return "\n".join(parts)
