#!/usr/bin/env python3
"""flowcode_dpg_ted — TED, the ternary editor (the Text tab's organs).

Editor services (find/replace, live counts) plus the star: the NATIVE
GLYPH PLANE pane — text encoded as XYZ GLYPH WORDS per the captured
park-session design (private/DeepAI-Consult-Glyph-Word-Brief.md):

  24-trit word · type header T23–T19 · payload T18–T0
  T18 MODE: 0 = character, ±1 = signed numeric literal (18-trit mag)
  X tribble (T17–T12): position in the containing list — charmaps and
    collation orders are USER-DEFINED LIST OBJECTS; the word carries
    its own position.
  Y tribble (T11–T6): identity — top trit case (+1 upper, −1 lower,
    0 caseless), 5 trits signed ordinal (A=1..Z=26; others by list-
    declared convention).
  Z tribble (T5–T0): font registry index → the PIGART vector font
    object that renders the glyph.

FORMATIVE choices here, awaiting the ruling round (brief Q1–Q6):
tribble order X-high/Z-low is an ASSUMPTION; space = caseless ordinal
27 (dodging the all-zeros-Y null trap of Q1); digits at 30..39;
punctuation from 40; Z = 0 (default font slot). Marked as sketch
everywhere it shows. DOCFLAG: ruling requested from CF5 via POBOX.
"""
import dearpygui.dearpygui as dpg

STYLE = {}
P3 = [3 ** i for i in range(20)]

# ── the formative ordinal convention (sketch — list-object canon later) ─────
_PUNCT = ".,:;!?'\"-()[]{}<>/\\|@#$%^&*_+=~`"


def _char_yid(ch):
    """(case_trit, ordinal) per the brief's Y-tribble identity."""
    if ch.isalpha() and ch.lower() in "abcdefghijklmnopqrstuvwxyz":
        return (1 if ch.isupper() else -1), ord(ch.lower()) - 96
    if ch == " ":
        return 0, 27                    # caseless space ≠ all-zeros (Q1)
    if ch == "\n":
        return 0, 28
    if ch == "\t":
        return 0, 29
    if ch.isdigit():
        return 0, 30 + int(ch)
    i = _PUNCT.find(ch)
    if i >= 0:
        return 0, 40 + i
    return 0, 120                       # formative "unknown" slot


def _yid_char(case, ordinal):
    if 1 <= ordinal <= 26:
        c = chr(96 + ordinal)
        return c.upper() if case == 1 else c
    if ordinal == 27:
        return " "
    if ordinal == 28:
        return "\n"
    if ordinal == 29:
        return "\t"
    if 30 <= ordinal <= 39:
        return str(ordinal - 30)
    if 40 <= ordinal < 40 + len(_PUNCT):
        return _PUNCT[ordinal - 40]
    return "�"


def _tribble(val):
    """Signed value -> 6 balanced trits value contribution (±364 max)."""
    return max(-364, min(364, int(val)))


def glyph_word(ch, pos, font=0):
    """One XYZ glyph word (payload value; header left to the STRING-word
    builder). MODE T18=0 (character)."""
    case, ordinal = _char_yid(ch)
    y = case * 243 + ordinal            # top trit of the 6 = case
    return (_tribble(pos) * P3[12]
            + _tribble(y) * P3[6]
            + _tribble(font))


def decode_glyph(word):
    """payload value -> (char, pos, case, ordinal, font)."""
    v = int(word)

    def field(pos, n):
        out = 0
        vv = v
        # extract trits pos..pos+n-1 of the balanced representation
        for i in range(pos):
            r = vv % 3
            vv = (vv + 1) // 3 if r == 2 else (vv - r) // 3
        for i in range(n):
            r = vv % 3
            t = -1 if r == 2 else r
            vv = (vv + 1) // 3 if r == 2 else (vv - r) // 3
            out += t * P3[i]
        return out
    x = field(12, 6)
    y = field(6, 6)
    z = field(0, 6)
    case = 1 if y > 121 else (-1 if y < -121 else 0)
    ordinal = y - case * 243
    return _yid_char(case, ordinal), x, case, ordinal, z


def encode_text(text, font=0, limit=None):
    words = []
    for i, ch in enumerate(text if limit is None else text[:limit]):
        words.append((ch, glyph_word(ch, i, font)))
    return words


# ── UI ──────────────────────────────────────────────────────────────────────
def _counts(*_):
    v = dpg.get_value("txt_edit") or ""
    lines = v.count("\n") + (1 if v else 0)
    words = len(v.split())
    dpg.set_value("ted_counts",
                  f"{lines} lines · {words} words · {len(v)} chars")


def _find(next_only=True):
    v = dpg.get_value("txt_edit") or ""
    needle = dpg.get_value("ted_find")
    if not needle:
        return
    n = v.count(needle)
    dpg.set_value("ted_findinfo", f"{n} match(es)" if n else "no matches")


def _replace_all(*_):
    v = dpg.get_value("txt_edit") or ""
    needle = dpg.get_value("ted_find")
    repl = dpg.get_value("ted_repl")
    if not needle:
        return
    n = v.count(needle)
    if n:
        dpg.set_value("txt_edit", v.replace(needle, repl))
        cb = STYLE.get("ON_EDIT")
        if cb:
            cb()
    dpg.set_value("ted_findinfo", f"replaced {n}")
    _counts()


def _native_refresh(*_):
    D = "ted_native"
    dpg.delete_item(D, children_only=True)
    v = dpg.get_value("txt_edit") or ""
    if not v.strip():
        dpg.add_text("type something in the editor — its native glyph "
                     "words appear here", parent=D,
                     color=STYLE.get("DIM"))
        return
    words = encode_text(v, limit=48)
    dpg.add_text(f"first {len(words)} of {len(v)} characters as XYZ "
                 "glyph words (formative sketch):", parent=D,
                 color=STYLE.get("DIM"))
    dpg.add_text(" ch   X(pos)  Y(case,ord)   Z(font)   payload value",
                 parent=D, color=(74, 158, 255))
    ok = True
    for ch, w in words:
        c2, x, case, o, z = decode_glyph(w)
        ok = ok and (c2 == ch)
        cs = {1: "+", -1: "−", 0: "0"}[case]
        dpg.add_text(f" {ch!r:<5} {x:<6} ({cs},{o:<3})      {z:<6} {w}",
                     parent=D, color=STYLE.get("TEXT"))
    dpg.add_text("round-trip: " + ("EXACT ✓" if ok else "MISMATCH ✗"),
                 parent=D,
                 color=(63, 208, 143) if ok else (255, 120, 90))


def show_charset(*_):
    tag = "ted_charsetwin"
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    with dpg.window(label="Native charset — formative example (XYZ)",
                    tag=tag, width=640, height=560, pos=(300, 80)):
        dpg.add_text("THE PARK-SESSION DESIGN (captured in private/"
                     "DeepAI-Consult-Glyph-Word-Brief.md)", color=(63, 208, 143))
        dpg.add_text("One word describes a character completely:\n"
                     "  X — where it sits (charmaps are list objects)\n"
                     "  Y — what it is (case trit + signed ordinal)\n"
                     "  Z — how it draws (font registry → PIGART object)",
                     color=STYLE.get("TEXT"))
        dpg.add_separator()
        dpg.add_text("Formative ordinals (sketch — ruling pending):",
                     color=STYLE.get("DIM"))
        rows = [("A–Z", "case +1, ordinal 1–26"),
                ("a–z", "case −1, ordinal 1–26"),
                ("space", "caseless 27 (NOT all-zeros — the Q1 trap)"),
                ("newline · tab", "caseless 28 · 29"),
                ("0–9", "caseless 30–39"),
                (_PUNCT[:18] + "…", "caseless 40+")]
        for a, b in rows:
            dpg.add_text(f"  {a:<14} {b}", color=STYLE.get("TEXT"))
        dpg.add_separator()
        dpg.add_text("OPEN RULINGS (brief Q1–Q6, requested from CF5):\n"
                     " · tribble order X-high/Z-low is an assumption\n"
                     " · Z per-character vs per-list (Q2, 'most wanted')\n"
                     " · position invariants under edit (Q4)\n"
                     " · numeric-literal mixing invariants (Q6)",
                     color=(240, 180, 80))
        dpg.add_button(label="  Close  ",
                       callback=lambda: dpg.delete_item(tag))


def build_ted_header(style):
    STYLE.update(style)
    C = STYLE
    with dpg.group(horizontal=True):
        dpg.add_text("TED", color=(63, 208, 143))
        dpg.add_text("— the ternary editor", color=C["DIM"])
        dpg.add_spacer(width=24)
        dpg.add_input_text(tag="ted_find", width=170, hint="find",
                           callback=lambda *_: _find())
        dpg.add_input_text(tag="ted_repl", width=170, hint="replace with")
        dpg.add_button(label=" count ", callback=lambda: _find())
        dpg.add_button(label=" replace all ", callback=_replace_all)
        dpg.add_text("", tag="ted_findinfo", color=C["DIM"])


def build_ted_footer(style):
    STYLE.update(style)
    C = STYLE
    with dpg.group(horizontal=True):
        dpg.add_text("", tag="ted_counts", color=C["DIM"])
        dpg.add_spacer(width=30)
        dpg.add_button(label=" native glyph view ↻ ",
                       callback=_native_refresh)
        dpg.add_button(label=" charset reference ", callback=show_charset)
    with dpg.collapsing_header(label="Native glyph plane (XYZ words — "
                                     "park-session candidate)",
                               default_open=False):
        with dpg.child_window(tag="ted_native", height=190):
            dpg.add_text("open this drawer and press ↻ to see your text "
                         "as native glyph words", color=C["DIM"])
    _counts()
    clip = STYLE.get("CLIP")
    if clip:
        clip.menu("ted_native", [
            ("Copy glyph-word table", lambda: clip.clip_set("\n".join(
                dpg.get_value(c) for c in
                (dpg.get_item_children("ted_native", 1) or [])
                if dpg.get_item_type(c) == "mvAppItemType::mvText"))),
            ("Refresh", _native_refresh)])


def _selftest():
    probe = "Az 3!\tOK\n"
    words = encode_text(probe)
    back = "".join(decode_glyph(w)[0] for _c, w in words)
    assert back == probe, (probe, back)
    ch, x, case, o, z = decode_glyph(words[0][1])
    assert (ch, x, case, o, z) == ("A", 0, 1, 1, 0), (ch, x, case, o, z)
    ch2, x2, c2, o2, _ = decode_glyph(words[1][1])
    assert (ch2, x2, c2, o2) == ("z", 1, -1, 26)
    return {"chars": len(words), "roundtrip": "exact"}
