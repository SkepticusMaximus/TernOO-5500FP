"""ghost_tab_view.py — the GHOST Academy tab (Piece: GHOST tab + harness).

Mounted by flowcode.py:  GhostTabView(parent_frame, C, root, set_status)

Left: chat pane — talk to GHOST (native routing), !learn commands with a
confirmation echo before any lesson commits.  Right, stacked: curriculum
editor (per-class phrase list), Train button + report card, brain-scan
(model-as-NEURAL-words inspector).  Toolbar: Open/Save/Save As (.chat via
the FileSystem abstraction), Copy.  All logic lives in ghost_harness.py;
this file is furniture.

Date: 2026-07-05, Adelaide
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

PROMPT = 'you: '


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


class GhostTabView:
    def __init__(self, parent, C, root, set_status):
        import tkinter as tk
        from tkinter import filedialog, messagebox
        self.tk, self.fd, self.mb = tk, filedialog, messagebox
        self.C, self.root, self._status = C, root, set_status
        self.harness = H.Harness()
        self._pending_lesson = None

        bar = tk.Frame(parent, bg=C['palette'])
        bar.pack(side='top', fill='x')
        for label, cmd in (('Open .chat', self.open_chat),
                           ('Save', self.save_chat),
                           ('Save As', self.save_chat_as),
                           ('Copy', self.copy_chat),
                           ('Train', self.train)):
            tk.Button(bar, text=label, command=cmd, bg=C['palette'],
                      fg=C['text'], font=('Monospace', 9), relief='flat',
                      bd=0, padx=8, pady=3, cursor='hand2').pack(side='left')

        body = tk.PanedWindow(parent, orient='horizontal', bg=C['bg'],
                              sashwidth=4)
        body.pack(fill='both', expand=True)

        # ── left: chat ────────────────────────────────────────────────────
        left = tk.Frame(body, bg=C['bg'])
        self.chat = tk.Text(left, bg=C['inspect'], fg=C['text'],
                            insertbackground=C['text'], relief='flat',
                            font=('Monospace', 10), wrap='word',
                            padx=8, pady=6, highlightthickness=0)
        self.chat.pack(fill='both', expand=True)
        self.chat.insert('end',
                         "GHOST Academy — talk below; teach with "
                         '!learn <class> "<phrase>", !learn-undo, '
                         "!learn-log\n")
        self.entry = tk.Entry(left, bg=C['inspect'], fg=C['text'],
                              insertbackground=C['text'], relief='flat',
                              font=('Monospace', 10))
        self.entry.pack(fill='x', pady=(4, 0))
        self.entry.bind('<Return>', self._on_enter)
        body.add(left, minsize=320)

        # ── right: curriculum / report / brain scan ───────────────────────
        right = tk.PanedWindow(body, orient='vertical', bg=C['bg'],
                               sashwidth=4)
        cur = tk.Frame(right, bg=C['bg'])
        tk.Label(cur, text='Curriculum', bg=C['bg'], fg=C['accent'],
                 font=('Monospace', 10, 'bold')).pack(anchor='w')
        row = tk.Frame(cur, bg=C['bg']); row.pack(fill='both', expand=True)
        self.cls_list = tk.Listbox(row, bg=C['inspect'], fg=C['text'],
                                   relief='flat', font=('Monospace', 9),
                                   exportselection=False, width=22)
        self.cls_list.pack(side='left', fill='y')
        self.cls_list.bind('<<ListboxSelect>>', self._show_class)
        self.phrases = tk.Text(row, bg=C['inspect'], fg=C['text'],
                               relief='flat', font=('Monospace', 9),
                               wrap='word', padx=6, pady=4)
        self.phrases.pack(side='left', fill='both', expand=True)
        for cls in sorted(self.harness.corpus):
            self.cls_list.insert('end', cls)
        right.add(cur, minsize=140)

        rep = tk.Frame(right, bg=C['bg'])
        tk.Label(rep, text='Report card', bg=C['bg'], fg=C['accent'],
                 font=('Monospace', 10, 'bold')).pack(anchor='w')
        self.report = tk.Text(rep, bg=C['inspect'], fg=C['text'],
                              relief='flat', font=('Monospace', 9),
                              height=7, padx=6, pady=4)
        self.report.pack(fill='both', expand=True)
        self.report.insert('end', '(press Train for a fresh report card)')
        right.add(rep, minsize=110)

        scan = tk.Frame(right, bg=C['bg'])
        tk.Label(scan, text='Brain scan — model as words', bg=C['bg'],
                 fg=C['accent'], font=('Monospace', 10, 'bold')
                 ).pack(anchor='w')
        self.brain = tk.Text(scan, bg=C['inspect'], fg=C['dim'],
                             relief='flat', font=('Monospace', 8),
                             wrap='none', padx=6, pady=4)
        self.brain.pack(fill='both', expand=True)
        self._brain_scan()
        right.add(scan, minsize=100)
        body.add(right, minsize=300)

    # ── chat + !learn (with confirmation echo) ────────────────────────────
    def _say(self, who, text):
        self.chat.insert('end', f'{who}{text}\n')
        self.chat.see('end')

    def _on_enter(self, _e=None):
        line = self.entry.get().strip()
        self.entry.delete(0, 'end')
        if not line:
            return
        self._say(PROMPT, line)
        try:
            if self._pending_lesson is not None:
                if line.lower() in ('y', 'yes'):
                    cls, phrase = self._pending_lesson
                    self._say('ghost: ', self.harness.learn(cls, phrase))
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
                    self._say('ghost: ',
                              f'you want me to learn {cls} ← {phrase!r} '
                              f'— confirm? (y/n)')
                return
            self._say('ghost: ', self.harness.chat(line))
        except (H.HarnessError, OSError) as e:
            self._say('ghost: ', f'error: {e}')

    # ── curriculum ────────────────────────────────────────────────────────
    def _show_class(self, _e=None):
        sel = self.cls_list.curselection()
        if not sel:
            return
        cls = self.cls_list.get(sel[0])
        self.phrases.delete('1.0', 'end')
        self.phrases.insert('1.0', '\n'.join(self.harness.corpus[cls]))

    # ── train / report / brain scan ───────────────────────────────────────
    def train(self):
        self._status('GHOST training — a couple of minutes of trits…')
        self.root.update_idletasks()
        report = self.harness.train()
        self.report.delete('1.0', 'end')
        self.report.insert('1.0', format_report(report))
        self._brain_scan()
        self._status(f"GHOST trained — "
                     f"{report['held_out_accuracy']:.1%} held-out")

    def _brain_scan(self):
        self.brain.delete('1.0', 'end')
        if not self.harness.model:
            self.brain.insert('end', '(no model)')
            return
        try:
            G = _load('ghost_train')
            v = _load('5500fp_ternoo_v03')
            words = G.export_neural_words(self.harness.model['W1'],
                                          self.harness.model['W2'])
            self.brain.insert('end',
                              f'{len(words)} NEURAL_CONNECTION words; '
                              f'first 40:\n')
            for w in words[:40]:
                d = v.decode_word(w)
                self.brain.insert(
                    'end', f"  w={d['weight']:+d}  src={d['source']:3d} "
                           f"dst={d['target']:3d}   raw={w}\n")
        except Exception as e:                       # display-only pane
            self.brain.insert('end', f'(brain scan failed: {e})')

    # ── file furniture ────────────────────────────────────────────────────
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
        self.chat.insert('end', f'--- {os.path.basename(p)} ---\n')
        for t in turns:
            self._say(PROMPT, t['user'])
            self._say('ghost: ', t['ghost'])
        self._status(f'loaded {len(turns)} turns')

    def copy_chat(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.chat.get('1.0', 'end-1c'))
        self._status('chat copied to clipboard')
