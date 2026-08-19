#!/usr/bin/env python3
"""flowcode_dpg_academy — the Academy tab ORGAN of FlowCode's DPG face.

The classroom, ported whole. EVERY engine is the Tk face's, reused
untouched:

  ghost_harness.Harness — GHOST: route/chat/!learn/train, majors,
      .chat save/open, node-private brain dir (D1).
  ghost_bonsai — the Professor: BonsaiProcess (local subprocess, NO
      network — the one rail that never comes off), build_request,
      consistency_gate, consent ceremony (CONSENT_PROMPT).
  ghost_tab_view — the PURE presenter helpers (format_report,
      student_thought, prof_thought, grading_label, present_bonsai,
      backstage_ghost_text) + the FROZEN geometry/colour contract
      (art commission: balloons cut, board/book ARE the utterances,
      thought bubbles stay, borderless live-text surfaces).
  glyph_canvas — the pure layout half (plan_layout, resolve_glyph,
      scale_for, grid_to_xy, VOICES): DpgGlyphSurface below re-renders
      the same plans into a drawlist. Same deterministic per-line
      jitter recipe, so chalk never shimmers on redraw.
  ternoo_glyph — the house font codec (to_house_words, specimen
      ordinals, O4 unknown-glyph ledger).

DPG-face notes (ledger, not user docs): panes are fixed-height (no Tk
relative reflow yet); Tk splines curved strokes, the drawlist draws the
raw polylines — chalk jitter still supplies the hand. Backstage is a
floating panel (same corridor rules: never touches harness.turns).
"""
import atexit
import importlib.util as _ilu
import os
import random
import sys
import threading

import dearpygui.dearpygui as dpg

_FIVE = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "5500fp")

STYLE = {}
AC = {"err": "", "harness": None, "bonsai": None, "timeout": 2400.0,
      "accuracy": None, "pending_lesson": None, "pending_delegation": None,
      "prof_thought": "", "stud_thought": "", "curious": False,
      "pulse": False, "idea": False, "busy": False}
M = {}          # loaded engine modules


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _mods():
    if not M and not AC["err"]:
        try:
            if _FIVE not in sys.path:
                sys.path.insert(0, _FIVE)
            for key, name in (("H", "ghost_harness"), ("B", "ghost_bonsai"),
                              ("GTV", "ghost_tab_view"),
                              ("GLY", "ternoo_glyph"), ("GC", "glyph_canvas"),
                              ("GT", "ghost_train")):
                spec = _ilu.spec_from_file_location(
                    name, os.path.join(_FIVE, name + ".py"))
                mod = _ilu.module_from_spec(spec)
                spec.loader.exec_module(mod)
                M[key] = mod
        except Exception as e:                  # noqa: BLE001
            AC["err"] = str(e)
    return M


def _harness():
    if AC["harness"] is None and not AC["err"]:
        m = _mods()
        if m:
            AC["harness"] = m["H"].Harness()
    return AC["harness"]


def _bonsai():
    """Self-wiring Professor — BONSAI_CMD → bonsai.json discovery →
    professor-not-present (classroom fully usable). NOT started under
    SMOKE/gates: tests must never launch a model subprocess."""
    if AC["bonsai"] is None and not AC["err"]:
        m = _mods()
        cmd = None
        if not os.environ.get("SMOKE"):
            bc = os.environ.get("BONSAI_CMD")
            if bc:
                cmd = bc.split()
            else:
                try:
                    spec = _ilu.spec_from_file_location(
                        "bonsai_runner",
                        os.path.join(_FIVE, "bonsai_runner.py"))
                    br = _ilu.module_from_spec(spec)
                    spec.loader.exec_module(br)
                    cmd = br.classroom_command()
                    AC["timeout"] = br.ask_timeout()
                except Exception:               # noqa: BLE001
                    cmd = None
        AC["bonsai"] = m["B"].BonsaiProcess(cmd)
        AC["bonsai"].start()
        atexit.register(AC["bonsai"].stop)
    return AC["bonsai"]


def _ui(fn):
    try:
        dpg.set_frame_callback(dpg.get_frame_count() + 1, lambda: fn())
    except Exception:                           # noqa: BLE001
        pass


def _status(msg):
    cb = STYLE.get("SET_STATUS")
    if cb:
        cb(msg)


# ═══ DpgGlyphSurface — glyph_canvas's voices on a drawlist ══════════════════
class DpgGlyphSurface:
    """The chalk/ink renderer, drawlist edition. Reuses glyph_canvas's
    pure planners + VOICES; keeps the retained-lines model and the
    deterministic jitter recipe (seed = line_index*1009 + int(ox))."""

    def __init__(self, drawlist, face_rgb, voice="chalk", size=18,
                 pad_top=8, line_gap=1.5):
        self.dl = drawlist
        self.face = face_rgb
        self.voice = voice
        self.size = size
        self.pad_top = pad_top
        self.line_gap = line_gap
        self._lines = []

    def clear(self):
        self._lines = []
        self.redraw()

    def append_text(self, text):
        m = _mods()
        for line in str(text).split("\n"):
            self._lines.append(m["GLY"].to_house_words(line))
        self.redraw()

    def append_words(self, words):
        self._lines.append(list(words))
        self.redraw()

    def redraw(self):
        m = _mods()
        GC = m["GC"]
        dpg.delete_item(self.dl, children_only=True)
        w = dpg.get_item_width(self.dl) or 600
        h = dpg.get_item_height(self.dl) or 200
        dpg.draw_rectangle((0, 0), (w, h), fill=self.face, color=self.face,
                           parent=self.dl)
        cfg = GC.VOICES[self.voice]
        color = _hex(cfg["color"])
        line_h = self.size * self.line_gap

        # plan every retained line (pure), then draw the tail that fits
        plans, y = [], self.pad_top
        for li, wl in enumerate(self._lines):
            placed = GC.plan_layout(wl, w, self.size)
            base0 = y + self.size
            rows = max((ln for _, _, ln in placed), default=0) + 1
            plans.append((li, placed, base0))
            y = base0 + rows * line_h - self.size
        overflow = max(0, y - h + self.size)

        for li, placed, base0 in plans:
            for word, cx, ln in placed:
                base = base0 + ln * line_h - overflow
                if base < -self.size:
                    continue
                self._draw_glyph(GC, word, cx, base, li + 1, cfg, color)

    def _draw_glyph(self, GC, word, ox, baseline, line_index, cfg, color):
        try:
            ordv, case, strokes, _ph = GC.resolve_glyph(word)
        except Exception:                       # literal → renderer refuses
            raise
        scale = GC.scale_for(self.size, case)
        rng = random.Random(line_index * 1009 + int(ox))
        jit = cfg["jitter"]

        def pt(gx, gy):
            x, y = GC.grid_to_xy(gx, gy, ox, baseline, scale)
            if jit:
                x += rng.uniform(-jit, jit)
                y += rng.uniform(-jit, jit)
            return (x, y)

        for poly in strokes:
            pts = [pt(gx, gy) for gx, gy in poly]
            if len(pts) == 1:
                dpg.draw_circle(pts[0], cfg["width"] / 2.0, fill=color,
                                color=color, parent=self.dl)
                continue
            if cfg["dust"]:
                dpg.draw_polyline(pts, color=(*color, 70),
                                  thickness=cfg["width"] + 1.5,
                                  parent=self.dl)
            dpg.draw_polyline(pts, color=color, thickness=cfg["width"],
                              parent=self.dl)


BOARD = [None]          # the blackboard DpgGlyphSurface


# ═══ classroom voices ═══════════════════════════════════════════════════════
def _board(text):
    if BOARD[0]:
        BOARD[0].append_text(text)


def _say(who, text):
    if not dpg.does_item_exist("acad_book"):
        return
    dpg.add_text(f"{who}{text}", parent="acad_book", wrap=640,
                 color=_hex("#e6dcc8"))
    dpg.set_y_scroll("acad_book", 999999.0)


def _book_text():
    return "\n".join(dpg.get_value(c)
                     for c in dpg.get_item_children("acad_book", 1) or []
                     if dpg.get_item_type(c) == "mvAppItemType::mvText")


# ═══ sprite zones (dashed placeholders — the frozen art contract) ═══════════
def _dashed_rect(dl, x0, y0, x1, y1, color):
    def seg(ax, ay, bx, by):
        dpg.draw_line((ax, ay), (bx, by), color=color, parent=dl)
    for x in range(int(x0), int(x1), 7):
        seg(x, y0, min(x + 4, x1), y0)
        seg(x, y1, min(x + 4, x1), y1)
    for y in range(int(y0), int(y1), 7):
        seg(x0, y, x0, min(y + 4, y1))
        seg(x1, y, x1, min(y + 4, y1))


def _redraw_prof():
    dl = "acad_prof_zone"
    if not dpg.does_item_exist(dl):
        return
    m = _mods()
    GTV = m["GTV"]
    dpg.delete_item(dl, children_only=True)
    w = dpg.get_item_width(dl)
    h = dpg.get_item_height(dl)
    DIM = STYLE.get("DIM", (110, 110, 110))
    _dashed_rect(dl, 8, int(h * 0.16), w - 6, h - 46, DIM)
    dpg.draw_text((w // 2 - 16, h // 2 - 8), "prof", size=15, color=DIM,
                  parent=dl)
    present = AC["bonsai"] is not None and \
        AC["bonsai"].status != m["B"].NOT_RUNNING
    placard = GTV.PLACARD_TEXT if present else "professor not present"
    col = _hex(GTV.CURIOUS_B) if present else DIM
    dpg.draw_rectangle((8, h - 40), (w - 6, h - 12),
                       fill=_hex(GTV.PLACARD_FACE),
                       color=_hex(GTV.PLACARD_FACE), parent=dl)
    dpg.draw_text((14, h - 33), placard, size=11, color=col, parent=dl)
    if AC["prof_thought"]:
        dpg.draw_text((10, 8), AC["prof_thought"], size=12, color=DIM,
                      parent=dl)


def _redraw_student():
    dl = "acad_stud_zone"
    if not dpg.does_item_exist(dl):
        return
    m = _mods()
    GTV = m["GTV"]
    dpg.delete_item(dl, children_only=True)
    w = dpg.get_item_width(dl)
    h = dpg.get_item_height(dl)
    DIM = STYLE.get("DIM", (110, 110, 110))
    _dashed_rect(dl, 8, int(h * 0.16), w - 6, h - 16, DIM)
    dpg.draw_text((w // 2 - 22, h // 2 - 8), "ghost", size=15, color=DIM,
                  parent=dl)
    col = _hex(GTV.CURIOUS_A) if AC["curious"] else DIM
    mark = GTV.IDEA_MARK if AC["idea"] else "?"
    dpg.draw_text((w - 30, 14), mark, size=22, color=col, parent=dl)
    if AC["stud_thought"]:
        dpg.draw_text((10, 8), AC["stud_thought"], size=12,
                      color=STYLE.get("TEXT"), parent=dl)


def _pulse(on):
    AC["curious"] = on
    AC["pulse"] = on
    _redraw_student()
    if on:
        def _flip():
            if not AC["pulse"] or not dpg.does_item_exist("acad_stud_zone"):
                return
            AC["curious"] = not AC["curious"]
            _redraw_student()
            dpg.set_frame_callback(dpg.get_frame_count() + 27, _flip)
        dpg.set_frame_callback(dpg.get_frame_count() + 27, _flip)


def _flash_idea():
    AC["idea"] = True
    _redraw_student()

    def _off():
        AC["idea"] = False
        if dpg.does_item_exist("acad_stud_zone"):
            _redraw_student()
    dpg.set_frame_callback(dpg.get_frame_count() + 55, _off)


def _draw_grade():
    dl = "acad_grade"
    if not dpg.does_item_exist(dl):
        return
    m = _mods()
    dpg.delete_item(dl, children_only=True)
    w = dpg.get_item_width(dl)
    h = dpg.get_item_height(dl)
    dpg.draw_rectangle((0, 0), (w, h), fill=(24, 28, 34),
                       color=(24, 28, 34), parent=dl)
    if AC["accuracy"] is None:
        dpg.draw_text((w // 2 - 92, h // 2 - 7), "belt test — press Train",
                      size=12, color=STYLE.get("DIM"), parent=dl)
        return
    fw = int(w * max(0.0, min(1.0, AC["accuracy"])))
    dpg.draw_rectangle((0, 0), (fw, h), fill=_hex(m["GTV"].CURIOUS_B),
                       color=_hex(m["GTV"].CURIOUS_B), parent=dl)
    dpg.draw_text((w // 2 - 20, h // 2 - 8),
                  m["GTV"].grading_label(AC["accuracy"]), size=13,
                  color=(230, 237, 243), parent=dl)


# ═══ chat + !learn + consent-gated delegation (the Tk flow, verbatim) ═══════
def on_enter(*_):
    h = _harness()
    m = _mods()
    if h is None:
        _say("ghost: ", f"engine unavailable: {AC['err']}")
        return
    line = (dpg.get_value("acad_entry") or "").strip()
    dpg.set_value("acad_entry", "")
    if not line:
        return
    _say(m["GTV"].PROMPT, line)
    H, B = m["H"], m["B"]
    try:
        if AC["pending_delegation"] is not None:
            text = AC["pending_delegation"]
            AC["pending_delegation"] = None
            dpg.set_value("acad_consent", "")
            if line.lower() in ("y", "yes"):
                _delegate(text)
            else:
                _say("ghost: ", "refusal stands — I won't pretend.")
            return
        if AC["pending_lesson"] is not None:
            if line.lower() in ("y", "yes"):
                cls, phrase = AC["pending_lesson"]
                _say("ghost: ", h.learn(cls, phrase))
                _flash_idea()
            else:
                _say("ghost: ", "lesson discarded")
            AC["pending_lesson"] = None
            return
        bang = H.parse_bang(line)
        if bang:
            if bang[0] == "undo":
                _say("ghost: ", h.learn_undo())
            elif bang[0] == "log":
                _say("ghost: ", "\n" + h.learn_log())
            else:
                _, cls, phrase = bang
                AC["pending_lesson"] = (cls, phrase)
                _say("ghost: ", f"you want me to learn {cls} ← {phrase!r}"
                     " — confirm? (y/n)")
            return
        _pulse(True)
        reply = h.chat(line)
        last = h.turns[-1]
        AC["stud_thought"] = m["GTV"].student_thought(last["route"],
                                                      last["margin"])
        _pulse(last["route"] == "none")
        _say("ghost: ", reply)
        bon = _bonsai()
        if last["route"] == "none" and bon.status != B.NOT_RUNNING:
            AC["pending_delegation"] = line
            dpg.set_value("acad_consent", B.CONSENT_PROMPT)
    except (m["H"].HarnessError, OSError) as e:
        _pulse(False)
        _say("ghost: ", f"error: {e}")


def _delegate(text):
    """Cross to the Professor — consent given. Threaded; the reply passes
    the consistency gate before it ever reaches the blackboard."""
    m = _mods()
    h = _harness()
    B = m["B"]
    if not B.should_delegate("none", True):
        return
    feats = m["GT"].features(text)
    route, margin = "none", 0
    try:
        route, margin = h.route(text)
    except m["H"].HarnessError:
        pass
    req = B.build_request(text, feats, route, margin, h.major)
    _board("prof, the student is stuck: " + text)
    AC["prof_thought"] = m["GTV"].prof_thought(0)
    _redraw_prof()

    def work():
        resp, err = _bonsai().ask(req, timeout=AC["timeout"])

        def land():
            AC["prof_thought"] = ""
            if resp is None:
                _board(f"[professor unreachable — {err}]")
            else:
                gate = B.consistency_gate(resp, route, margin)
                _board(m["GTV"].present_bonsai(gate, resp))
            _redraw_prof()
        _ui(land)
    threading.Thread(target=work, daemon=True).start()


def set_major(sender, major):
    m = _mods()
    try:
        AC["harness"] = m["H"].Harness(major=major)
    except m["H"].HarnessError as e:
        _status(f"major switch failed: {e}")
        return
    AC["accuracy"] = None
    _draw_grade()
    _say("ghost: ", f"now majoring in {major}")
    _status(f"GHOST major: {major}")


def do_train(*_):
    if AC["busy"]:
        return
    h = _harness()
    if h is None:
        return
    AC["busy"] = True
    _status("GHOST training — a couple of minutes of trits…")
    dpg.configure_item("acad_train", label="  … training …  ")

    def work():
        try:
            report = h.train()
            err = None
        except Exception as e:                  # noqa: BLE001
            report, err = None, e

        def land():
            AC["busy"] = False
            dpg.configure_item("acad_train", label="  ▸ Train (belt test)  ")
            if err is not None:
                _status(f"training failed: {err}")
                return
            AC["accuracy"] = report["held_out_accuracy"]    # REAL value only
            _draw_grade()
            _board("report card:\n" + _mods()["GTV"].format_report(report))
            _status(f"GHOST trained — {AC['accuracy']:.1%} held-out")
        _ui(land)
    threading.Thread(target=work, daemon=True).start()


# ═══ satellite windows ══════════════════════════════════════════════════════
def _float(tag, label, w, h, x, y):
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    return dpg.window(label=label, tag=tag, width=w, height=h, pos=(x, y))


def open_curriculum(*_):
    h = _harness()
    if h is None:
        return
    with _float("acad_curr", "Curriculum", 620, 480, 260, 90):
        with dpg.group(horizontal=True):
            with dpg.child_window(width=210, height=-8):
                for cls in sorted(h.corpus):
                    dpg.add_selectable(label=cls, user_data=cls,
                                       callback=lambda s, a, u:
                                       dpg.set_value("acad_curr_txt",
                                                     "\n".join(
                                                         h.corpus.get(u, []))))
            dpg.add_input_text(tag="acad_curr_txt", multiline=True,
                               readonly=True, width=-1, height=-8)
    clip = STYLE.get("CLIP")
    if clip:
        clip.input_menu("acad_curr_txt", "curriculum phrases")


def open_brain_scan(*_):
    h = _harness()
    if h is None:
        return
    lines = []
    if not h.model:
        lines.append("(no model — press Train first)")
    else:
        try:
            m = _mods()
            spec = _ilu.spec_from_file_location(
                "v03", os.path.join(_FIVE, "5500fp_ternoo_v03.py"))
            v = _ilu.module_from_spec(spec)
            spec.loader.exec_module(v)
            words = m["GT"].export_neural_words(h.model["W1"], h.model["W2"])
            lines.append(f"{len(words)} NEURAL_CONNECTION words; first 40:")
            for w in words[:40]:
                d = v.decode_word(w)
                lines.append(f"  w={d['weight']:+d}  src={d['source']:3d} "
                             f"dst={d['target']:3d}   raw={w}")
        except Exception as e:                  # noqa: BLE001
            lines.append(f"(brain scan failed: {e})")
    with _float("acad_brain", "Brain scan — model as words", 560, 520,
                300, 70):
        dpg.add_input_text(tag="acad_brain_txt", multiline=True,
                           readonly=True, width=-1, height=-8,
                           default_value="\n".join(lines))
    clip = STYLE.get("CLIP")
    if clip:
        clip.input_menu("acad_brain_txt", "brain scan")


def show_specimen(*_):
    m = _mods()
    GLY = m["GLY"]
    space = GLY.make_glyph(GLY.ORDINAL[" "])
    for line in m["GTV"].GhostTabView.SPECIMEN_LINES:
        _board(line)
    if BOARD[0]:
        BOARD[0].append_words([GLY.make_glyph(GLY.ANSWER_ORD), space,
                               GLY.make_glyph(GLY.IDEA_ORD), space,
                               GLY.make_glyph(GLY.PLACEHOLDER_ORD)])
    _status("house-font specimen printed to the board")


def open_translator(*_):
    """ASCII/Unicode → native glyph-string words, previewed in both
    voices; unknowns feed the O4 char-map ledger."""
    m = _mods()
    GLY, GTV = m["GLY"], m["GTV"]
    with _float("acad_xlat", "ASCII / Unicode → TernOO glyph-string",
                760, 470, 220, 80):
        dpg.add_text("Text in (ASCII/Unicode — e.g. Bonsai output):",
                     color=STYLE.get("DIM"))
        dpg.add_input_text(tag="acad_xlat_in", multiline=True, width=-1,
                           height=64, default_value="GHOST + Bonsai = the "
                           "two-mind stack ± humility")
        with dpg.group(horizontal=True):
            dpg.add_button(label=" Translate ", callback=lambda: _xlat())
            dpg.add_text("", tag="acad_xlat_status", color=STYLE.get("DIM"))
        dpg.add_drawlist(tag="acad_xlat_chalk", width=720, height=120)
        dpg.add_drawlist(tag="acad_xlat_ink", width=720, height=120)
    chalk = DpgGlyphSurface("acad_xlat_chalk", _hex(GTV.BLACKBOARD_FACE),
                            voice="chalk", size=18)
    ink = DpgGlyphSurface("acad_xlat_ink", _hex(GTV.BOOK_FACE),
                          voice="ink", size=18)

    def _xlat():
        text = dpg.get_value("acad_xlat_in") or ""
        unknown, seen = [], set()
        for c in text:
            if c == "\n" or c in seen:
                continue
            if any(not GLY.house_representable(n)
                   for n in GLY.normalize_for_house(c)):
                unknown.append(c)
                seen.add(c)
        chalk._lines = []
        ink._lines = []
        for ln in text.split("\n"):
            chalk._lines.append(GLY.to_house_words(ln))
            ink._lines.append(GLY.to_house_words(ln, record=False))
        chalk.redraw()
        ink.redraw()
        n = len(GLY.to_house_words(text.replace("\n", " "), record=False))
        msg = f"{n} glyph words (normalized)"
        if unknown:
            msg += "  ·  no house glyph → ~ (logged to O4 ledger): " \
                   + " ".join(unknown)
        dpg.set_value("acad_xlat_status", msg)
    _xlat()
    clip = STYLE.get("CLIP")
    if clip:
        clip.input_menu("acad_xlat_in", "text to translate")


# ═══ backstage — the corridor, not the curriculum ═══════════════════════════
def _console_write(log, line):
    dpg.add_text(line, parent=log, wrap=330, color=STYLE.get("TEXT"))
    dpg.set_y_scroll(log, 999999.0)


def _bs_log(path, who, text):
    h = _harness()
    try:
        h.fs.append(path, f"{who}: {text}\n")
    except Exception:                           # noqa: BLE001
        pass


def bs_send_prof(*_):
    """UNGATED at our layer: no gate, no consent, no GHOST routing —
    prompt in, subprocess, text out. No-socket construction absolute."""
    m = _mods()
    line = (dpg.get_value("acad_bs_prof_in") or "").strip()
    if not line:
        return
    dpg.set_value("acad_bs_prof_in", "")
    _console_write("acad_bs_prof", f"you: {line}")
    _bs_log(m["GTV"].BACKSTAGE_PROF_LOG, "you", line)
    bon = _bonsai()
    if bon.status == m["B"].NOT_RUNNING:
        _console_write("acad_bs_prof", "(professor not present)")
        return
    req = m["B"].build_request(line, [0] * 81, "backstage", 0,
                               _harness().major)
    _console_write("acad_bs_prof", "(professor is thinking… minutes, not "
                                   "seconds, at 0.3 tok/s)")

    def work():
        resp, err = bon.ask(req, timeout=AC["timeout"])

        def land():
            if resp is None:
                _console_write("acad_bs_prof",
                               f"[professor unreachable — {err}]")
            else:
                text = resp.get("text", "")
                _console_write("acad_bs_prof", f"prof: {text}")
                _bs_log(m["GTV"].BACKSTAGE_PROF_LOG, "prof", text)
        _ui(land)
    threading.Thread(target=work, daemon=True).start()


def bs_send_ghost(*_):
    """Same engine as class, but harness.turns is NEVER touched and
    teaching is refused — the corridor must not mutate the student."""
    m = _mods()
    h = _harness()
    line = (dpg.get_value("acad_bs_ghost_in") or "").strip()
    if not line:
        return
    dpg.set_value("acad_bs_ghost_in", "")
    _console_write("acad_bs_ghost", f"you: {line}")
    _bs_log(m["GTV"].BACKSTAGE_GHOST_LOG, "you", line)
    if line.startswith("!learn"):
        reply = m["GTV"].BACKSTAGE_TEACHING_NOTICE
    else:
        try:
            route, margin = h.route(line)
            reply = m["GTV"].backstage_ghost_text(route, margin)
        except (m["H"].HarnessError, OSError) as e:
            reply = f"error: {e}"
    _console_write("acad_bs_ghost", f"ghost: {reply}")
    _bs_log(m["GTV"].BACKSTAGE_GHOST_LOG, "ghost", reply)


def toggle_backstage(*_):
    vis = dpg.is_item_shown("acad_backstage")
    dpg.configure_item("acad_backstage", show=not vis)
    _status("backstage " + ("closed" if vis else "open"))


# ═══ .chat furniture ════════════════════════════════════════════════════════
def save_chat(*_):
    h = _harness()
    if h is None or not h.turns:
        _status("nothing to save yet — talk to GHOST first")
        return
    h.save_chat("session.chat")
    _status("saved session.chat")


def _chat_dialog(tag, label, save, cb):
    if dpg.does_item_exist(tag):
        dpg.delete_item(tag)
    with dpg.file_dialog(tag=tag, label=label, width=640, height=420,
                         modal=True, show=True, callback=cb,
                         default_path=os.path.dirname(
                             os.path.abspath(__file__)),
                         default_filename="session.chat" if save else ""):
        dpg.add_file_extension(".chat", color=(63, 208, 143))
        dpg.add_file_extension(".*")


def save_chat_as(*_):
    h = _harness()
    if h is None or not h.turns:
        _status("nothing to save yet — talk to GHOST first")
        return

    def cb(sender, app):
        p = app.get("file_path_name")
        if p:
            h.save_chat(p)
            _status(f"saved {os.path.basename(p)}")
    _chat_dialog("acad_fd_save", "Save chat as", True, cb)


def open_chat(*_):
    h = _harness()
    if h is None:
        return

    def cb(sender, app):
        p = app.get("file_path_name")
        if not p:
            return
        try:
            turns = h.open_chat(p)
        except _mods()["H"].HarnessError as e:
            _status(f"open failed: {e}")
            return
        _say("", f"--- {os.path.basename(p)} ---")
        for t in turns:
            _say(_mods()["GTV"].PROMPT, t["user"])
            _say("ghost: ", t["ghost"])
        _status(f"loaded {len(turns)} turns")
    _chat_dialog("acad_fd_open", "Open .chat", False, cb)


def copy_chat(*_):
    clip = STYLE.get("CLIP")
    if clip:
        clip.clip_set(_book_text())
        _status("book copied to clipboard")


# ═══ build ══════════════════════════════════════════════════════════════════
def build_academy_tab(style):
    STYLE.update(style)
    C = STYLE
    m = _mods()
    if AC["err"]:
        dpg.add_text(f"Academy engines unavailable: {AC['err']}",
                     color=C["AMB"])
        return
    GTV = m["GTV"]
    _harness()
    _bonsai()

    VW = 1210                       # classroom client width (fixed-pane v1)
    SPR = 172                       # sprite column (the ~28% contract col)
    BOARD_W, BOARD_H = VW - SPR - 24, 168
    BOOK_H = 152

    with dpg.group(horizontal=True):
        dpg.add_combo(sorted(m["H"].MAJORS), default_value="commands",
                      width=120, callback=set_major)
        for label, cb in (("Open .chat", open_chat), ("Save", save_chat),
                          ("Save As", save_chat_as), ("Copy", copy_chat),
                          ("Curriculum", open_curriculum),
                          ("Brain scan", open_brain_scan),
                          ("Chars", show_specimen),
                          ("Translate", open_translator),
                          ("Backstage", toggle_backstage)):
            dpg.add_button(label=f" {label} ", callback=cb)

    # ── TOP: Professor — sprite zone + the BLACKBOARD (chalk voice) ─────
    with dpg.group(horizontal=True):
        dpg.add_drawlist(tag="acad_prof_zone", width=SPR, height=BOARD_H + 8)
        dpg.add_drawlist(tag="acad_board", width=BOARD_W, height=BOARD_H + 8)
    BOARD[0] = DpgGlyphSurface("acad_board", _hex(GTV.BLACKBOARD_FACE),
                               voice="chalk", size=18)
    BOARD[0].redraw()

    # ── SEAM: the training desk ─────────────────────────────────────────
    with dpg.group(horizontal=True):
        dpg.add_button(label="  ▸ Train (belt test)  ", tag="acad_train",
                       callback=do_train)
        dpg.add_drawlist(tag="acad_grade", width=560, height=24)
        dpg.add_text("", tag="acad_consent", color=C["AMB"])

    # ── BOTTOM: Student — sprite zone + the OPEN BOOK + entry ───────────
    with dpg.group(horizontal=True):
        dpg.add_drawlist(tag="acad_stud_zone", width=SPR, height=BOOK_H + 34)
        with dpg.group():
            with dpg.child_window(tag="acad_book", width=BOARD_W,
                                  height=BOOK_H):
                dpg.add_text("Academy — the book is the log. Talk below; "
                             "teach with !learn <class> \"<phrase>\", "
                             "!learn-undo, !learn-log.", wrap=640,
                             color=_hex("#e6dcc8"))
            dpg.add_input_text(tag="acad_entry", width=BOARD_W,
                               on_enter=True, callback=on_enter,
                               hint="talk to GHOST — Enter sends")
    with dpg.theme() as booktheme:
        with dpg.theme_component(dpg.mvChildWindow):
            dpg.add_theme_color(dpg.mvThemeCol_ChildBg, _hex(GTV.BOOK_FACE))
    dpg.bind_item_theme("acad_book", booktheme)

    # ── BACKSTAGE: floating corridor panel (hidden by default) ──────────
    with dpg.window(label="BACKSTAGE — the corridor, not the curriculum",
                    tag="acad_backstage", width=400, height=560,
                    pos=(840, 70), show=False, no_collapse=True,
                    on_close=lambda: dpg.configure_item("acad_backstage",
                                                        show=False)):
        dpg.add_text("PROFESSOR — corridor (ungated at our layer)",
                     color=C["DIM"])
        with dpg.child_window(tag="acad_bs_prof", width=-1, height=190):
            pass
        dpg.add_input_text(tag="acad_bs_prof_in", width=-1, on_enter=True,
                           callback=bs_send_prof)
        dpg.add_separator()
        dpg.add_text("GHOST — corridor (no curriculum side effects)",
                     color=C["DIM"])
        with dpg.child_window(tag="acad_bs_ghost", width=-1, height=190):
            pass
        dpg.add_input_text(tag="acad_bs_ghost_in", width=-1, on_enter=True,
                           callback=bs_send_ghost)
    if AC["bonsai"].status == m["B"].NOT_RUNNING:
        _console_write("acad_bs_prof", "(professor not present)")

    _redraw_prof()
    _redraw_student()
    _draw_grade()

    clip = C.get("CLIP")
    if clip:
        clip.input_menu("acad_entry", "classroom entry")
        clip.input_menu("acad_bs_prof_in", "corridor line (prof)")
        clip.input_menu("acad_bs_ghost_in", "corridor line (ghost)")
        clip.menu("acad_book", [
            ("Copy the whole book", copy_chat),
            ("Paste into entry", lambda: dpg.set_value(
                "acad_entry", (dpg.get_value("acad_entry") or "")
                + clip.clip_get()))])


def on_show():
    if dpg.does_item_exist("acad_prof_zone"):
        _redraw_prof()
        _redraw_student()
        _draw_grade()


# ═══ gate ═══════════════════════════════════════════════════════════════════
def _selftest():
    m = _mods()
    assert not AC["err"], f"engines failed: {AC['err']}"
    h = _harness()
    assert h is not None and h.corpus, "harness has no corpus"
    route, margin = h.route("add 2 and 3")
    assert isinstance(route, str), route
    assert m["H"].parse_bang('!learn cmd_math_add "sum these"') is not None
    rep = m["GTV"].format_report(
        {"held_out_accuracy": 0.5, "held_out_n": 4, "refusal_check": "ok",
         "weights_as_words": 7, "worst_confusions": []})
    assert "50.0%" in rep, rep
    assert m["GTV"].grading_label(0.875) == "87.5%"
    assert m["GTV"].backstage_ghost_text("none", 0).startswith("I'm sorry")
    gate = m["B"].GateResult(True, "ok", None)
    assert m["GTV"].present_bonsai(gate, {"text": "hi"}) == "hi"
    words = m["GLY"].to_house_words("Az 3?", record=False)
    placed = m["GC"].plan_layout(words, 600, 18)
    assert len(placed) == len(words)
    for w, _x, _ln in placed:
        _o, _c, strokes, _ph = m["GC"].resolve_glyph(w)
        assert strokes is not None, f"no strokes for word {w}"  # space = []
    if dpg.does_item_exist("acad_board") and BOARD[0]:
        BOARD[0].clear()                    # sweep may have specimen up
        n0 = len(dpg.get_item_children("acad_board", 2) or [])
        _board("gate: chalk line")
        assert len(dpg.get_item_children("acad_board", 2) or []) > n0
    prof = (AC["bonsai"].status if AC["bonsai"] else "unbuilt")
    return {"classes": len(h.corpus), "route": route,
            "glyphs": len(words), "prof": prof}
