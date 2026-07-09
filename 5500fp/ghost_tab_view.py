"""ghost_tab_view.py — the GHOST Academy classroom tab (Front 1: classroom UI + Bonsai).

Mounted by flowcode.py:  GhostTabView(parent_frame, C, root, set_status)

A vertically split classroom (measured geometry — CF5-Submit-2026-07-08_004000,
amended by CF5-Submit-2026-07-09_164000):
  * TOP pane  (~44% H) — Professor (Bonsai): sprite zone (~28% pane W, bottom-
    weighted) + placard ("local subprocess · no network") + the BLACKBOARD
    (upper ~70% of the pane, right of a 12px gutter) + thought bubble.
  * SEAM      (~12% H) — the training desk: Train control + the GRADING STRIP
    (belt test, bound to the REAL report-card accuracy — never fabricated).
  * BOTTOM pane (~44% H) — Student (GHOST): sprite zone + the OPEN BOOK
    (the .chat log — the kept original made visible) + entry + curious `?`
    indicator (pulses while routing / on a `none`) + thought bubble.
  * BACKSTAGE PANEL (right edge, ~30% tab W, hidden by default) — the corridor
    conversation, not the classroom performance: direct consoles to the
    Professor (ungated at our layer) and to GHOST (no curriculum side effects).
    When open, the classroom panes compress to the remaining width; the art-
    contract percentages apply to the CLASSROOM AREA, not the tab.

Geometry contract note (art commission): SPEECH BALLOONS ARE CUT — the board
and the book ARE the utterances (captain's ruling, 2026-07-09); their reserved
positions are RELEASED. THOUGHT-BUBBLE positions stay FROZEN (introspection
only: professor generation status; GHOST margin self-talk + the curious ?).

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
GLY = _load('ternoo_glyph')         # glyph words (for the font specimen)

PROMPT = 'you: '

# Sprite/asset home — the contract with the commissioned overlay art.
ASSETS_DIR = os.path.join(_HERE, '..', 'FlowCode', 'assets', 'academy')

# ── measured layout geometry (fractions of the client area / pane) ──────────
PROF_H, SEAM_H, STUD_H = 0.44, 0.12, 0.44     # pane heights (sum = 1.0)
SPRITE_W = 0.28                                # sprite zone width, per pane
BOARD_H = 0.70                                 # blackboard height, of prof pane
BOOK_H = 0.70                                  # open book height, of stud pane
GUTTER = 12                                    # px gutter around board/book

# ── classroom colours (dispatch §2). Literal so they survive palette variance. ───
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

# ── the Backstage Panel (CF5-Submit-2026-07-09_164000) ──────────────────────
BACKSTAGE_W = 0.30                 # of the tab client area, when open
BACKSTAGE_TEACHING_NOTICE = ('teaching happens in class — use the classroom, '
                             'not the corridor')
BACKSTAGE_PROF_LOG = 'backstage-prof.log'
BACKSTAGE_GHOST_LOG = 'backstage-ghost.log'


def backstage_ghost_text(route: str, margin) -> str:
    """The GHOST console's reply line — same engine and phrasing as the
    classroom, but composed here so the corridor NEVER touches harness.turns
    (the .chat stream) or any teaching state. The corridor is not the
    curriculum."""
    if route == 'none':
        return f"I'm sorry, I can't do that — yet.  (margin {margin})"
    short = route[4:] if route.startswith('cmd_') else route
    return f"that sounds like {short}  (margin {margin}) — try `{short}(...)`"


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
# The classroom tab (furniture)
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
        self._stud_thought = ''            # thought bubbles stay (introspection);
        self._prof_thought = ''            # speech balloons are CUT (164000 §0)
        self._backstage_open = False       # per-session only, not persisted

        # Bonsai — self-wiring, no terminal needed: BONSAI_CMD env (power-user
        # override) → bonsai.json → auto-discovery of the local runtime+model.
        # Nothing found → professor-not-present, classroom fully usable.
        bonsai_cmd = os.environ.get('BONSAI_CMD')
        self._ask_timeout = 2400.0
        if bonsai_cmd:
            cmd = bonsai_cmd.split()
        else:
            try:
                _runner = _load('bonsai_runner')
                cmd = _runner.classroom_command()
                self._ask_timeout = _runner.ask_timeout()
            except Exception:
                cmd = None
        self.bonsai = B.BonsaiProcess(cmd)
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
                           ('Save As', self.save_chat_as),
                           ('Copy', self.copy_chat),
                           ('Curriculum', self.open_curriculum),
                           ('Brain scan', self.open_brain_scan),
                           ('Chars', self.show_specimen),
                           ('Translate', self.open_translator),
                           ('Backstage', self.toggle_backstage)):
            tk.Button(bar, text=label, command=cmd, bg=C['palette'],
                      fg=C['text'], font=('Monospace', 9), relief='flat',
                      bd=0, padx=8, pady=3, cursor='hand2').pack(side='left')

        # ── the three placed regions (44 / 12 / 44) ──────────────────────────
        container = tk.Frame(parent, bg=C['bg'])
        container.pack(side='top', fill='both', expand=True)
        self._container = container

        self.prof_pane = tk.Frame(container, bg=C['bg'])
        self.seam = tk.Frame(container, bg=C['palette'])
        self.stud_pane = tk.Frame(container, bg=C['bg'])
        seam = self.seam
        self._reflow()          # places the three panes (full width, no panel)

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
        self.board = GC.GlyphSurface(self.blackboard, voice='chalk', size=18)
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
        # the open book renders in NORMAL text (captain's call) — the native
        # glyph font is showcased on the professor's board; the book stays a
        # readable log. Same borderless surface tone.
        self.book = tk.Text(self.stud_pane, bg=BOOK_FACE, fg='#e6dcc8',
                            insertbackground='#e6dcc8', bd=0, relief='flat',
                            highlightthickness=0, font=('Monospace', 11),
                            wrap='word', padx=10, pady=8)
        self.book.place(relx=SPRITE_W, x=GUTTER, rely=0.0, y=6,
                        relwidth=1 - SPRITE_W, width=-2 * GUTTER,
                        relheight=BOOK_H, height=-6)
        self.book.insert('end', 'Academy — the book is the log. Talk below; '
                                'teach with !learn <class> "<phrase>", '
                                '!learn-undo, !learn-log.\n')
        self.entry = tk.Entry(self.stud_pane, bg=C['inspect'], fg=C['text'],
                             insertbackground=C['text'], relief='flat', bd=0,
                             highlightthickness=0, font=('Monospace', 10))
        self.entry.place(relx=SPRITE_W, x=GUTTER, rely=BOOK_H, y=6,
                         relwidth=1 - SPRITE_W, width=-2 * GUTTER, height=26)
        self.entry.bind('<Return>', self._on_enter)
        self.stud_pane.bind('<Configure>', lambda e: self._redraw_student())

        self._build_backstage(container)
        self._redraw_prof()
        self._redraw_student()
        self._draw_grade()

    # ── layout: classroom ⟷ backstage reflow ────────────────────────────────
    def _reflow(self):
        """Place the classroom panes across whatever width the backstage
        panel leaves. The art-contract percentages (sprite 28%, board 70%…)
        are fractions of the CLASSROOM AREA, not the tab — pane-relative
        placement makes that automatic (164000 §5)."""
        w = 1 - BACKSTAGE_W if self._backstage_open else 1
        self.prof_pane.place(relx=0, rely=0, relwidth=w, relheight=PROF_H)
        self.seam.place(relx=0, rely=PROF_H, relwidth=w, relheight=SEAM_H)
        self.stud_pane.place(relx=0, rely=PROF_H + SEAM_H, relwidth=w,
                             relheight=STUD_H)

    # ── the Backstage Panel — the corridor, not the classroom ───────────────
    def _build_backstage(self, container):
        """Two stacked consoles (Professor above, GHOST below, 50/50 sash),
        hidden by default. Backstage renders PLAIN UTF-8 Tk text, deliberately
        — fast and unceremonious; the native-font showcase is the classroom's
        job. Do NOT 'upgrade' this to GlyphSurface without a ruling (164000)."""
        tk = self.tk
        C = self.C
        self.backstage = tk.Frame(container, bg=C['palette'])
        pw = tk.PanedWindow(self.backstage, orient='vertical', bg=C['palette'],
                            sashwidth=4)
        pw.pack(fill='both', expand=True, padx=(4, 0))

        def _console(parent_pw, title):
            frame = tk.Frame(parent_pw, bg=C['bg'])
            tk.Label(frame, text=title, bg=C['bg'], fg=C['dim'],
                     font=('Monospace', 8, 'bold'), anchor='w'
                     ).pack(fill='x', padx=4, pady=(4, 0))
            txt = tk.Text(frame, bg=C['inspect'], fg=C['text'],
                          insertbackground=C['text'], bd=0, relief='flat',
                          highlightthickness=0, font=('Monospace', 9),
                          wrap='word', padx=6, pady=4, state='disabled')
            txt.pack(fill='both', expand=True, padx=4, pady=2)
            ent = tk.Entry(frame, bg=C['inspect'], fg=C['text'],
                           insertbackground=C['text'], relief='flat', bd=0,
                           highlightthickness=0, font=('Monospace', 9))
            ent.pack(fill='x', padx=4, pady=(0, 4))
            parent_pw.add(frame, minsize=80)
            return txt, ent

        self._bs_prof_txt, self._bs_prof_ent = _console(
            pw, 'PROFESSOR — corridor (ungated at our layer)')
        self._bs_ghost_txt, self._bs_ghost_ent = _console(
            pw, 'GHOST — corridor (no curriculum side effects)')
        self._bs_prof_ent.bind('<Return>', self._backstage_send_prof)
        self._bs_ghost_ent.bind('<Return>', self._backstage_send_ghost)
        if self.bonsai.status == B.NOT_RUNNING:
            self._console_write(self._bs_prof_txt, '(professor not present)')
            self._bs_prof_ent.config(state='disabled')

    def toggle_backstage(self):
        self._backstage_open = not self._backstage_open
        if self._backstage_open:
            self.backstage.place(relx=1 - BACKSTAGE_W, rely=0,
                                 relwidth=BACKSTAGE_W, relheight=1)
        else:
            self.backstage.place_forget()
        self._reflow()
        self._status('backstage ' + ('open' if self._backstage_open
                                     else 'closed'))

    def _console_write(self, txt, line):
        txt.config(state='normal')
        txt.insert('end', line + '\n')
        txt.see('end')
        txt.config(state='disabled')

    def _backstage_log(self, path, who, text):
        """Raw UTF-8, kept-original — to the corridor's OWN files. Nothing
        from the panel enters any .chat curriculum document, the Academy
        ledger, or training state, ever, by construction — not filtered out,
        never wired in. The corridor is not the curriculum."""
        try:
            self.harness.fs.append(path, f'{who}: {text}\n')
        except Exception:
            pass

    def _backstage_send_prof(self, _e=None):
        """Corridor line to the Professor. UNGATED BY US: no consistency
        gate, no consent ceremony, no routing through GHOST — prompt in,
        subprocess, text out. Nothing here strips or works around the model's
        own trained behaviour (Qwen's character rides inside the GGUF); we
        remove OUR gates only. The no-socket construction is absolute and
        unchanged — the one rail that never comes off."""
        line = self._bs_prof_ent.get().strip()
        if not line:
            return
        self._bs_prof_ent.delete(0, 'end')
        self._console_write(self._bs_prof_txt, f'you: {line}')
        self._backstage_log(BACKSTAGE_PROF_LOG, 'you', line)
        if self.bonsai.status == B.NOT_RUNNING:
            self._console_write(self._bs_prof_txt, '(professor not present)')
            return
        # the corridor does not consult the student: zero feature vector,
        # route tagged 'backstage' — contract shape kept, gate NOT applied.
        req = B.build_request(line, [0] * 81, 'backstage', 0,
                              self.harness.major)
        self._console_write(self._bs_prof_txt, '(professor is thinking…)')
        import threading
        box = {}

        def _work():
            box['resp'], box['err'] = self.bonsai.ask(
                req, timeout=self._ask_timeout)

        t = threading.Thread(target=_work, daemon=True)
        t.start()

        def _poll():
            if t.is_alive():
                self.root.after(150, _poll)
                return
            resp, err = box.get('resp'), box.get('err')
            if resp is None:
                self._console_write(self._bs_prof_txt,
                                    f'[professor unreachable — {err}]')
            else:
                text = resp.get('text', '')
                self._console_write(self._bs_prof_txt, f'prof: {text}')
                self._backstage_log(BACKSTAGE_PROF_LOG, 'prof', text)

        self.root.after(150, _poll)

    def _backstage_send_ghost(self, _e=None):
        """Corridor line to GHOST: text in → router → routed reply / none.
        Same engine as the classroom, but nothing appends to harness.turns
        (the .chat stream) and teaching commands are refused — the backstage
        must never silently mutate the student."""
        line = self._bs_ghost_ent.get().strip()
        if not line:
            return
        self._bs_ghost_ent.delete(0, 'end')
        self._console_write(self._bs_ghost_txt, f'you: {line}')
        self._backstage_log(BACKSTAGE_GHOST_LOG, 'you', line)
        if line.startswith('!learn'):      # every teaching form, incl. malformed
            reply = BACKSTAGE_TEACHING_NOTICE
        else:
            try:
                route, margin = self.harness.route(line)
                reply = backstage_ghost_text(route, margin)
            except (H.HarnessError, OSError) as e:
                reply = f'error: {e}'
        self._console_write(self._bs_ghost_txt, f'ghost: {reply}')
        self._backstage_log(BACKSTAGE_GHOST_LOG, 'ghost', reply)

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
        """A borderless THOUGHT annotation (introspection only — speech
        balloons are cut; the board/book are the utterances). Text only —
        the art layer draws the bubble shape; a code outline would double it."""
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
        # thought bubble up-left (frozen position) — the introspection window
        self._bubble(c, 14, 12, self._prof_thought, self.C['dim'])

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
        # thought bubble up-left (frozen position) — the introspection window
        self._bubble(c, 14, 12, self._stud_thought, self.C['text'])

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

    def _say(self, who, text):
        self.book.insert('end', f'{who}{text}\n')
        self.book.see('end')

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
            # timeout from bonsai.json (ask_timeout) — at 0.3 tok/s a real
            # answer takes minutes; 120s was a fantasy (screen-truth lesson).
            box['resp'], box['err'] = self.bonsai.ask(
                req, timeout=self._ask_timeout)

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
                self._board(present_bonsai(gate, resp))
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

    # ── curriculum + brain scan (preserved from the pre-classroom tab) ──────────
    # NOTE: these two panes were in the single-pane tab; the classroom spec doesn't
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

    # ── font specimen (print the whole house font in BOTH voices) ──────────
    SPECIMEN_LINES = ('THE HOUSE FONT ~ SPECIMEN',
                      'A B C D E F G H I J K L M N O P Q R S T U V W X Y Z',
                      'a b c d e f g h i j k l m n o p q r s t u v w x y z',
                      '0 1 2 3 4 5 6 7 8 9',
                      '. , : ; ! ? - \' " ( )',
                      '+ - × ÷ = ≠ < > ≤ ≥ ± / \\ * ^ % · _ | #',
                      '[ ] { } → π √ Δ ° ∑ ∫ ∞')

    def show_specimen(self):
        """Print the full house-font set to the chalk board for review (the
        board is the native-font showcase; the book renders normal text)."""
        space = GLY.make_glyph(GLY.ORDINAL[' '])
        for line in self.SPECIMEN_LINES:
            self.board.append_text(line)
        self.board.append_words([GLY.make_glyph(GLY.ANSWER_ORD), space,
                                 GLY.make_glyph(GLY.IDEA_ORD), space,
                                 GLY.make_glyph(GLY.PLACEHOLDER_ORD)])
        self._status('house-font specimen printed to the board')

    # ── ASCII/Unicode → TernOO glyph-string word translator ────────────────
    def open_translator(self):
        """Port external ASCII/Unicode text into native TernOO glyph-string
        words (the same projection the board uses on Bonsai's output), preview
        it in a chosen voice, and report characters the house font can't yet
        supply — those feed the O4 char-map charter."""
        tk = self.tk
        C = self.C
        top = tk.Toplevel(self.root, bg=C['bg'])
        top.title('ASCII / Unicode → TernOO glyph-string')

        tk.Label(top, text='Text in (ASCII/Unicode — e.g. Bonsai output):',
                 bg=C['bg'], fg=C['text'], font=('Monospace', 9)
                 ).pack(anchor='w', padx=8, pady=(8, 0))
        inp = tk.Text(top, height=4, width=70, bg=C['inspect'], fg=C['text'],
                     insertbackground=C['text'], relief='flat', bd=0,
                     highlightthickness=0, font=('Monospace', 10), padx=6,
                     pady=4)
        inp.pack(fill='x', padx=8)
        inp.insert('1.0', 'GHOST + Bonsai = the two-mind stack ± humility')

        row = tk.Frame(top, bg=C['bg'])
        row.pack(fill='x', padx=8, pady=4)
        voice = tk.StringVar(value='chalk')
        tk.OptionMenu(row, voice, 'chalk', 'ink', 'both').pack(side='left')
        status = tk.Label(row, text='', bg=C['bg'], fg=C['dim'],
                         font=('Monospace', 8))
        status.pack(side='left', padx=10)

        chalk_cv = tk.Canvas(top, bg=BLACKBOARD_FACE, height=100, bd=0,
                            highlightthickness=0)
        ink_cv = tk.Canvas(top, bg=BOOK_FACE, height=100, bd=0,
                          highlightthickness=0)
        chalk_cv.pack(fill='x', padx=8, pady=(4, 2))
        ink_cv.pack(fill='x', padx=8, pady=(0, 8))
        s_chalk = GC.GlyphSurface(chalk_cv, voice='chalk', size=18)
        s_ink = GC.GlyphSurface(ink_cv, voice='ink', size=18)

        def translate(*_):
            text = inp.get('1.0', 'end-1c')
            # unknowns AFTER normalization, reported by ORIGINAL identity
            unknown, seen = [], set()
            for c in text:
                if c == '\n' or c in seen:
                    continue
                if any(not GLY.house_representable(n)
                       for n in GLY.normalize_for_house(c)):
                    unknown.append(c); seen.add(c)
            v = voice.get()
            s_chalk.clear(); s_ink.clear()
            for ln in text.split('\n'):
                if v in ('chalk', 'both'):
                    s_chalk.append_text(ln)          # normalizes + ledgers
                if v in ('ink', 'both'):
                    s_ink.append_text(ln)
            n = len(GLY.to_house_words(text.replace('\n', ' '), record=False))
            msg = f'{n} glyph words (normalized)'
            if unknown:
                msg += '  ·  no house glyph → ~ (logged to O4 ledger): ' \
                       + ' '.join(unknown)
            status.config(text=msg)

        tk.Button(row, text='Translate', command=translate, bg=C['palette'],
                  fg=C.get('accent', '#7ab4ff'), font=('Monospace', 9),
                  relief='flat', bd=0, padx=10, cursor='hand2').pack(side='left')
        voice.trace_add('write', translate)
        top.after(50, translate)          # initial render once mapped

    # ── file furniture ──────────────────────────────────────────────────────
    def save_chat(self):
        if not self.harness.turns:
            self._status('nothing to save yet — talk to GHOST first')
            return
        self.harness.save_chat('session.chat')
        self._status('saved session.chat')

    def save_chat_as(self):
        p = self.fd.asksaveasfilename(title='Save chat as',
                                      defaultextension='.chat')
        if p:
            self.harness.save_chat(p)
            self._status(f'saved {os.path.basename(p)}')

    def open_chat(self):
        p = self.fd.askopenfilename(title='Open .chat')
        if not p:
            return
        try:
            turns = self.harness.open_chat(p)
        except H.HarnessError as e:
            self._status(f'open failed: {e}')
            return
        self.book.insert('end', f'--- {os.path.basename(p)} ---\n')
        for t in turns:
            self._say(PROMPT, t['user'])
            self._say('ghost: ', t['ghost'])
        self._status(f'loaded {len(turns)} turns')

    def copy_chat(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.book.get('1.0', 'end-1c'))
        self._status('book copied to clipboard')

    def close(self):
        """Clean shutdown of the Bonsai subprocess on tab/app close."""
        try:
            self.bonsai.stop()
        except Exception:
            pass
