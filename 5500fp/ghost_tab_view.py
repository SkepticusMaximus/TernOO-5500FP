"""ghost_tab_view.py — the GHOST Academy DOJO tab (Front 1: dojo UI + Bonsai).

Mounted by flowcode.py:  GhostTabView(parent_frame, C, root, set_status)

A vertically split classroom (measured geometry — CF5-Submit-2026-07-08_004000):
  * TOP pane  (~44% H) — Professor (Bonsai): sprite zone (~28% pane W, bottom-
    weighted) + placard ("local subprocess · no network") + the BLACKBOARD
    (upper ~70% of the pane, right of a 12px gutter) + thought/speech vectors.
  * SEAM      (~12% H) — the training desk: Train control + the GRADING STRIP
    (belt test, bound to the REAL report-card accuracy — never fabricated).
  * BOTTOM pane (~44% H) — Student (GHOST): sprite zone + the OPEN BOOK
    (the .chat log — the kept original made visible) + entry + curious `?`
    indicator (pulses while routing / on a `none`) + thought/speech vectors.

Cosmetics: live-text regions are BORDERLESS — distinctness is surface colour
alone (board #0a1410, book #141210, placard lifted-navy #0d1624). No code-drawn
frames or reliefs; the commissioned sprite art supplies the frames later, and a
code border would double them. Sprite-zone placeholders keep their dashed
outlines (scaffolding, they vanish when the art loads). The zone geometry is
the FROZEN contract with that overlay art.

Harness logic lives in ghost_harness.py (GHOST) and ghost_bonsai.py (the
Professor plumbing). This file is furniture.

Date: 2026-07-07, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import os
import importlib.util as _ilu

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H = _load('ghost_harness')
B = _load('ghost_bonsai')
GC = _load('glyph_canvas')          # native glyph-plane renderer (chalk + ink)

PROMPT = 'you: '

# Sprite/asset home — the contract with the commissioned overlay art.
ASSETS_DIR = os.path.join(_HERE, '..', 'FlowCode', 'assets', 'academy')

# ── measured layout geometry (fractions of the client area / pane) ──────────
PROF_H, SEAM_H, STUD_H = 0.44, 0.12, 0.44     # pane heights (sum = 1.0)
SPRITE_W = 0.28                                # sprite zone width, per pane
BOARD_H = 0.70                                 # blackboard height, of prof pane
BOOK_H = 0.70                                  # open book height, of stud pane
GUTTER = 12                                    # px gutter around board/book

# ── dojo colours (dispatch §2). Literal so they survive palette variance. ───
BLACKBOARD_FACE = '#0a1410'
BOOK_FACE = '#141210'
PLACARD_FACE = '#0d1624'          # slightly lifted navy, no outline
PLACARD_TEXT = 'local subprocess · no network'
CURIOUS_A = '#7f77dd'   # purple
CURIOUS_B = '#639922'   # green

# The idea mark: `?` completing into U+2E2E (reversed ?) + U+003F. The native
# ternary-glyph-plane original of this mark is a SEPARATE future work item
# (Stevo's char-map charter) — this Unicode projection is the v1 rendering.
IDEA_MARK = '⸮?'


# ═══════════════════════════════════════════════════════════════════════════
# Pure presentation helpers (UI-free — pinned in test_academy_tab.py)
# ═══════════════════════════════════════════════════════════════════════════

def format_report(report: dict) -> str:
    """Report card → display text (pure; tested headless)."""
    lines = [f"held-out accuracy : {report['held_out_accuracy']:.1%} "
             f"({report['held_out_n']} phrases)",
             f"refusal check     : {report['refusal_check']}",
             f"weights as words  : {report['weights_as_words']} "
             f"NEURAL_CONNECTION"]
    if report['worst_confusions']:
        lines.append("worst confusions  :")
        for pair, n in report['worst_confusions']:
            lines.append(f"    {pair}  ×{n}")
    else:
        lines.append("worst confusions  : (none)")
    return '\n'.join(lines)


def _short(cls: str) -> str:
    return cls[4:] if cls.startswith('cmd_') else cls


def student_thought(route: str, margin) -> str:
    """Router introspection for the student's thought bubble: the routed class
    and margin, or `?` on a `none`."""
    if route == 'none':
        return '?'
    return f'{_short(route)} · margin {margin}'


def prof_thought(n_tok: int) -> str:
    """Professor's live introspection while generating."""
    return f'composing… {int(n_tok)} tok'


def grading_label(accuracy: float) -> str:
    """Belt-test label from a real report-card accuracy in [0,1]."""
    return f'{accuracy:.1%}'


def present_bonsai(gate, resp) -> str:
    """What the blackboard shows for a Bonsai reply, honestly. Held-back
    replies say why; accepted-with-caveat replies carry the caveat."""
    if not gate.accepted:
        return f'[held back by the gate — {gate.reason}]'
    text = resp.get('text', '')
    if gate.caveat:
        return f'{text}\n  ⚠ {gate.caveat}'
    return text


# ═══════════════════════════════════════════════════════════════════════════
# The dojo tab (furniture)
# ═══════════════════════════════════════════════════════════════════════════

class GhostTabView:
    _show_idea = False
    _prof_pose_name = 'idle'

    def __init__(self, parent, C, root, set_status):
        import tkinter as tk
        from tkinter import filedialog, messagebox
        self.tk, self.fd, self.mb = tk, filedialog, messagebox
        self.C, self.root, self._status = C, root, set_status
        self.harness = H.Harness()
        self.G = _load('ghost_train')          # for the 81-trit feature vector
        self._pending_lesson = None
        self._pending_delegation = None
        self._sprites = {}                     # keep PhotoImage refs alive
        self._accuracy = None                  # last real report-card accuracy
        self._curious_on = False
        self._curious_job = None
        self._stud_thought = ''
        self._stud_speech = ''
        self._prof_thought = ''
        self._prof_speech = ''

        # Bonsai: cmd from env (no binary yet → stays NOT_RUNNING, graceful).
        bonsai_cmd = os.environ.get('BONSAI_CMD')
        self.bonsai = B.BonsaiProcess(bonsai_cmd.split() if bonsai_cmd else None)
        self.bonsai.start()

        acc = C.get('accent', '#7ab4ff')

        # ── toolbar ────────────────────────────────────────────────────────
        bar = tk.Frame(parent, bg=C['palette'])
        bar.pack(side='top', fill='x')
        self._major_var = tk.StringVar(value='commands')
        majors_menu = tk.OptionMenu(bar, self._major_var,
                                    *sorted(H.MAJORS), command=self._set_major)
        majors_menu.config(bg=C['palette'], fg=C['text'], font=('Monospace', 9),
                           relief='flat', highlightthickness=0)
        majors_menu.pack(side='left', padx=(2, 8))
        for label, cmd in (('Open .chat', self.open_chat),
                           ('Save', self.save_chat),
                           ('Copy', self.copy_chat),
                           ('Curriculum', self.open_curriculum),
                           ('Brain scan', self.open_brain_scan)):
            tk.Button(bar, text=label, command=cmd, bg=C['palette'],
                      fg=C['text'], font=('Monospace', 9), relief='flat',
                      bd=0, padx=8, pady=3, cursor='hand2').pack(side='left')

        # ── the three placed regions (44 / 12 / 44) ──────────────────────────
        container = tk.Frame(parent, bg=C['bg'])
        container.pack(side='top', fill='both', expand=True)

        self.prof_pane = tk.Frame(container, bg=C['bg'])
        self.prof_pane.place(relx=0, rely=0, relwidth=1, relheight=PROF_H)
        seam = tk.Frame(container, bg=C['palette'])
        seam.place(relx=0, rely=PROF_H, relwidth=1, relheight=SEAM_H)
        self.stud_pane = tk.Frame(container, bg=C['bg'])
        self.stud_pane.place(relx=0, rely=PROF_H + SEAM_H, relwidth=1,
                             relheight=STUD_H)

        # ── TOP pane: Professor (Bonsai) — canvas for vectors + borderless board
        self.prof_canvas = tk.Canvas(self.prof_pane, bg=C['bg'],
                                     highlightthickness=0)
        self.prof_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        # the blackboard is a GlyphSurface (native glyph plane, chalk voice)
        self.blackboard = tk.Canvas(self.prof_pane, bg=BLACKBOARD_FACE,
                                    bd=0, highlightthickness=0)
        self.blackboard.place(relx=SPRITE_W, x=GUTTER, rely=0.0, y=6,
                              relwidth=1 - SPRITE_W, width=-2 * GUTTER,
                              relheight=BOARD_H, height=-6)
        self.board = GC.GlyphSurface(self.blackboard, voice='chalk', size=16)
        self.blackboard.bind('<Configure>', lambda e: self.board.redraw())
        self.prof_pane.bind('<Configure>', lambda e: self._redraw_prof())

        # ── SEAM: the training desk ──────────────────────────────────────────
        self.train_btn = tk.Button(seam, text='▸ Train (belt test)',
                                   command=self.train, bg=C['palette'],
                                   fg=acc, font=('Monospace', 10, 'bold'),
                                   relief='flat', bd=0, padx=10, cursor='hand2')
        self.train_btn.pack(side='left', padx=8)
        self.grade_canvas = tk.Canvas(seam, bg=C['inspect'], height=22,
                                     highlightthickness=0)      # borderless
        self.grade_canvas.pack(side='left', fill='x', expand=True,
                               padx=8, pady=6)
        self.grade_canvas.bind('<Configure>', lambda e: self._draw_grade())
        self.consent_lbl = tk.Label(seam, text='', bg=C['palette'],
                                    fg=C['edge_msg'], font=('Monospace', 9))
        self.consent_lbl.pack(side='right', padx=10)

        # ── BOTTOM pane: Student (GHOST) — canvas + borderless book + entry ──
        self.stud_canvas = tk.Canvas(self.stud_pane, bg=C['bg'],
                                    highlightthickness=0)
        self.stud_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        # the open book is a GlyphSurface (native glyph plane, ink voice)
        self.book_canvas = tk.Canvas(self.stud_pane, bg=BOOK_FACE,
                                     bd=0, highlightthickness=0)
        self.book_canvas.place(relx=SPRITE_W, x=GUTTER, rely=0.0, y=6,
                               relwidth=1 - SPRITE_W, width=-2 * GUTTER,
                               relheight=BOOK_H, height=-6)
        self.book = GC.GlyphSurface(self.book_canvas, voice='ink', size=16)
        self.book_canvas.bind('<Configure>', lambda e: self.book.redraw())
        self._book_shadow = []           # plain-text mirror for Copy
        self._book_append('GHOST ACADEMY — THE BOOK IS THE LOG. TALK BELOW; '
                          'TEACH WITH !LEARN.')
        self.entry = tk.Entry(self.stud_pane, bg=C['inspect'], fg=C['text'],
                             insertbackground=C['text'], relief='flat', bd=0,
                             highlightthickness=0, font=('Monospace', 10))
        self.entry.place(relx=SPRITE_W, x=GUTTER, rely=BOOK_H, y=6,
                         relwidth=1 - SPRITE_W, width=-2 * GUTTER, height=26)
        self.entry.bind('<Return>', self._on_enter)
        self.stud_pane.bind('<Configure>', lambda e: self._redraw_student())

        self._redraw_prof()
        self._redraw_student()
        self._draw_grade()

    # ── sprite zones + vector overlays (the art contract) ──────────────────
    def _load_sprite(self, name):
        """PhotoImage for FlowCode/assets/academy/<name>.png, or None. When the
        commissioned art lands, poses light up automatically."""
        if name in self._sprites:
            return self._sprites[name]
        path = os.path.join(ASSETS_DIR, name + '.png')
        img = None
        if os.path.exists(path):
            try:
                img = self.tk.PhotoImage(file=path)
            except Exception:
                img = None
        self._sprites[name] = img
        return img

    def _sprite_zone(self, canvas, label, sprite_name):
        """Draw the figure (art if present, else the dashed placeholder) in the
        left ~28% column, bottom-weighted so figures 'stand'. Returns the zone
        rect — the FROZEN geometry the overlay art will occupy."""
        w = canvas.winfo_width() or 400
        h = canvas.winfo_height() or 200
        sprite_w = int(w * SPRITE_W)
        zone = (12, int(h * 0.16), sprite_w - 6, h - 46)
        img = self._load_sprite(sprite_name)
        if img is not None:
            canvas.create_image((zone[0] + zone[2]) // 2, zone[3] - img.height()
                                // 2, image=img)
        else:
            canvas.create_rectangle(*zone, dash=(4, 3), outline=self.C['dim'])
            canvas.create_text((zone[0] + zone[2]) // 2,
                               (zone[1] + zone[3]) // 2, text=label,
                               fill=self.C['dim'], font=('Monospace', 11))
        return zone, sprite_w

    def _bubble(self, canvas, x, y, text, colour, anchor='nw'):
        """A borderless annotation (thought/speech). Text only — the art layer
        will draw the balloon shapes; a code outline would double them."""
        if text:
            canvas.create_text(x, y, text=text, fill=colour, anchor=anchor,
                              font=('Monospace', 8))

    def _redraw_prof(self):
        c = self.prof_canvas
        c.delete('all')
        w = c.winfo_width() or 400
        h = c.winfo_height() or 200
        _, sprite_w = self._sprite_zone(c, 'prof', 'prof_' + self._prof_pose_name)
        # placard — centred under the sprite zone, filled navy, no outline
        present = self.bonsai.status != B.NOT_RUNNING
        placard = PLACARD_TEXT if present else 'professor not present'
        col = CURIOUS_B if present else self.C['dim']
        c.create_rectangle(12, h - 40, sprite_w - 6, h - 12,
                          fill=PLACARD_FACE, outline='')
        c.create_text((12 + sprite_w - 6) // 2, h - 26, text=placard,
                     fill=col, font=('Monospace', 8))
        # thought bubble up-left; speech balloon below-right (lower band, tail
        # toward the seam below)
        self._bubble(c, 14, 12, self._prof_thought, self.C['dim'])
        self._bubble(c, sprite_w + GUTTER + 4, int(h * BOARD_H) + 10,
                     self._prof_speech, '#cfe8d8')

    def _redraw_student(self):
        c = self.stud_canvas
        c.delete('all')
        w = c.winfo_width() or 400
        h = c.winfo_height() or 200
        _, sprite_w = self._sprite_zone(c, 'ghost', 'ghost_curious')
        # the curious `?` / idea mark — adjacent to the figure's upper-right
        col = CURIOUS_A if self._curious_on else self.C['dim']
        mark = IDEA_MARK if self._show_idea else '?'
        c.create_text(sprite_w - 14, 22, text=mark, fill=col,
                     font=('Monospace', 18, 'bold'), anchor='e')
        # thought bubble up-left; speech balloon below the figure (tail up)
        self._bubble(c, 14, 12, self._stud_thought, self.C['text'])
        self._bubble(c, 14, h - 30, self._stud_speech, '#e6dcc8')

    def _pulse_curious(self, on: bool):
        """Pulse the `?` while routing / on a none. Single indicator + one
        pose replaces the attentive/confident/puzzled triad (dispatch §4)."""
        self._curious_on = on
        if self._curious_job:
            try:
                self.root.after_cancel(self._curious_job)
            except Exception:
                pass
            self._curious_job = None
        self._redraw_student()
        if on:
            def _flip():
                self._curious_on = not self._curious_on
                self._redraw_student()
                self._curious_job = self.root.after(450, _flip)
            self._curious_job = self.root.after(450, _flip)

    def _flash_idea_mark(self):
        """On a confirmed !learn: the `?` briefly completes into the idea
        mark before fading back (the transfer moment)."""
        self._show_idea = True
        self._redraw_student()
        self.root.after(900, self._clear_idea)

    def _clear_idea(self):
        self._show_idea = False
        self._redraw_student()

    # ── the grading strip (belt test) — borderless trough, flat fill ───────
    def _draw_grade(self):
        c = self.grade_canvas
        c.delete('all')
        w = c.winfo_width() or 200
        h = c.winfo_height() or 22
        acc = self.C.get('accent', '#7ab4ff')
        if self._accuracy is None:
            c.create_text(w // 2, h // 2, text='belt test — press Train',
                         fill=self.C['dim'], font=('Monospace', 8))
            return
        fill_w = int(w * max(0.0, min(1.0, self._accuracy)))
        c.create_rectangle(0, 0, fill_w, h, fill=CURIOUS_B, outline='')
        c.create_text(w // 2, h // 2, text=grading_label(self._accuracy),
                     fill=acc, font=('Monospace', 9, 'bold'))

    # ── blackboard / book writers ──────────────────────────────────────────
    def _board(self, text):
        self.board.append_text(text)

    def _book_append(self, line):
        self._book_shadow.append(line)
        self.book.append_text(line)

    def _say(self, who, text):
        self._book_append(f'{who}{text}')

    # ── chat + !learn + consent-gated delegation ───────────────────────────
    def _on_enter(self, _e=None):
        line = self.entry.get().strip()
        self.entry.delete(0, 'end')
        if not line:
            return
        self._say(PROMPT, line)
        try:
            if self._pending_delegation is not None:
                text = self._pending_delegation
                self._pending_delegation = None
                self.consent_lbl.config(text='')
                if line.lower() in ('y', 'yes'):
                    self._delegate_to_bonsai(text)
                else:
                    self._say('ghost: ', 'refusal stands — I won\'t pretend.')
                return
            if self._pending_lesson is not None:
                if line.lower() in ('y', 'yes'):
                    cls, phrase = self._pending_lesson
                    self._say('ghost: ', self.harness.learn(cls, phrase))
                    self._flash_idea_mark()
                else:
                    self._say('ghost: ', 'lesson discarded')
                self._pending_lesson = None
                return
            bang = H.parse_bang(line)
            if bang:
                if bang[0] == 'undo':
                    self._say('ghost: ', self.harness.learn_undo())
                elif bang[0] == 'log':
                    self._say('ghost: ', '\n' + self.harness.learn_log())
                else:
                    _, cls, phrase = bang
                    self._pending_lesson = (cls, phrase)
                    self._say('ghost: ', f'you want me to learn {cls} ← '
                              f'{phrase!r} — confirm? (y/n)')
                return
            self._pulse_curious(True)
            self.root.update_idletasks()
            reply = self.harness.chat(line)
            last = self.harness.turns[-1]
            self._stud_thought = student_thought(last['route'], last['margin'])
            self._stud_speech = reply
            self._pulse_curious(last['route'] == 'none')
            self._say('ghost: ', reply)
            if last['route'] == 'none' and self.bonsai.status != B.NOT_RUNNING:
                self._pending_delegation = line
                self.consent_lbl.config(text=B.CONSENT_PROMPT)
        except (H.HarnessError, OSError) as e:
            self._pulse_curious(False)
            self._say('ghost: ', f'error: {e}')

    def _delegate_to_bonsai(self, text):
        """Cross to the Professor — consent already given. Threaded so the UI
        stays live; the reply passes the interim consistency gate before it
        ever reaches the blackboard."""
        if not B.should_delegate('none', True):
            return
        feats = self.G.features(text)
        route, margin = 'none', 0
        try:
            route, margin = self.harness.route(text)
        except H.HarnessError:
            pass
        req = B.build_request(text, feats, route, margin, self.harness.major)
        self._board('prof, the student is stuck: ' + text)
        self._prof_thought = prof_thought(0)
        self._prof_pose('writing')
        import threading
        box = {}

        def _work():
            box['resp'], box['err'] = self.bonsai.ask(req, timeout=120.0)

        t = threading.Thread(target=_work, daemon=True)
        t.start()

        def _poll():
            if t.is_alive():
                self.root.after(120, _poll)
                return
            self._prof_thought = ''
            self._prof_pose('speaking')
            resp, err = box.get('resp'), box.get('err')
            if resp is None:
                self._board(f'[professor unreachable — {err}]')
            else:
                gate = B.consistency_gate(resp, route, margin)
                shown = present_bonsai(gate, resp)
                self._prof_speech = shown.splitlines()[0][:48]
                self._board(shown)
            self.root.after(1200, lambda: self._prof_pose('idle'))

        self.root.after(120, _poll)

    def _prof_pose(self, pose):
        """writing while generating, speaking on completion, idle otherwise.
        Drives sprite selection once the art lands; redraws the zone now."""
        self._prof_pose_name = pose
        self._redraw_prof()

    def _set_major(self, major):
        try:
            self.harness = H.Harness(major=major)
        except H.HarnessError as e:
            self._status(f'major switch failed: {e}')
            return
        self._accuracy = None
        self._draw_grade()
        self._say('ghost: ', f'now majoring in {major}')
        self._status(f'GHOST major: {major}')

    # ── train / report → grading strip ─────────────────────────────────────
    def train(self):
        self._status('GHOST training — a couple of minutes of trits…')
        self.train_btn.config(text='… training …')
        self.root.update_idletasks()
        report = self.harness.train()
        self._accuracy = report['held_out_accuracy']    # REAL value only
        self._draw_grade()
        self.train_btn.config(text='▸ Train (belt test)')
        self._board('report card:\n' + format_report(report))
        self._status(f"GHOST trained — {self._accuracy:.1%} held-out")

    # ── curriculum + brain scan (preserved from the pre-dojo tab) ──────────
    # NOTE: these two panes were in the single-pane tab; the dojo spec doesn't
    # place them, so they're preserved on-demand in Toplevels rather than
    # dropped. Flagged for Stevo/CF5: keep here, relocate, or retire.
    def open_curriculum(self):
        tk = self.tk
        top = tk.Toplevel(self.root, bg=self.C['bg'])
        top.title('Curriculum')
        lst = tk.Listbox(top, bg=self.C['inspect'], fg=self.C['text'],
                        relief='flat', font=('Monospace', 9),
                        exportselection=False, width=24)
        lst.pack(side='left', fill='y')
        txt = tk.Text(top, bg=self.C['inspect'], fg=self.C['text'],
                     relief='flat', font=('Monospace', 9), wrap='word',
                     padx=6, pady=4, width=50)
        txt.pack(side='left', fill='both', expand=True)
        for cls in sorted(self.harness.corpus):
            lst.insert('end', cls)

        def _show(_e=None):
            sel = lst.curselection()
            if not sel:
                return
            txt.delete('1.0', 'end')
            txt.insert('1.0', '\n'.join(self.harness.corpus[lst.get(sel[0])]))
        lst.bind('<<ListboxSelect>>', _show)

    def open_brain_scan(self):
        tk = self.tk
        top = tk.Toplevel(self.root, bg=self.C['bg'])
        top.title('Brain scan — model as words')
        brain = tk.Text(top, bg=self.C['inspect'], fg=self.C['dim'],
                       relief='flat', font=('Monospace', 8), wrap='none',
                       padx=6, pady=4, width=60, height=30)
        brain.pack(fill='both', expand=True)
        if not self.harness.model:
            brain.insert('end', '(no model — press Train first)')
            return
        try:
            v = _load('5500fp_ternoo_v03')
            words = self.G.export_neural_words(self.harness.model['W1'],
                                               self.harness.model['W2'])
            brain.insert('end', f'{len(words)} NEURAL_CONNECTION words; '
                                f'first 40:\n')
            for w in words[:40]:
                d = v.decode_word(w)
                brain.insert('end', f"  w={d['weight']:+d}  "
                                    f"src={d['source']:3d} dst={d['target']:3d}"
                                    f"   raw={w}\n")
        except Exception as e:
            brain.insert('end', f'(brain scan failed: {e})')

    # ── file furniture ──────────────────────────────────────────────────────
    def save_chat(self):
        if not self.harness.turns:
            self._status('nothing to save yet — talk to GHOST first')
            return
        self.harness.save_chat('session.chat')
        self._status('saved session.chat')

    def open_chat(self):
        p = self.fd.askopenfilename(title='Open .chat')
        if not p:
            return
        try:
            turns = self.harness.open_chat(p)
        except H.HarnessError as e:
            self._status(f'open failed: {e}')
            return
        self._book_append(f'--- {os.path.basename(p)} ---')
        for t in turns:
            self._say(PROMPT, t['user'])
            self._say('ghost: ', t['ghost'])
        self._status(f'loaded {len(turns)} turns')

    def copy_chat(self):
        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(self._book_shadow))
        self._status('book copied to clipboard')

    def close(self):
        """Clean shutdown of the Bonsai subprocess on tab/app close."""
        try:
            self.bonsai.stop()
        except Exception:
            pass
