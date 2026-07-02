"""translator_view.py — the Lingo Translator pane (Piece 2).

Read-only multi-dialect projections of the current program: pick the
mental model that fits how you think.  A teaching / porting surface, not
an editor — canonical text lives in the Text tab.

Wiring contract:
    TranslatorView(parent, C, get_model)   # get_model() -> dialect model
    .refresh()  — re-project (call when the substrate changes)

Projections are cached until refresh() to keep dialect-switching instant.

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import importlib.util as _ilu
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_translate = _load('flowcode_lingo_translate')

DIALECT_LABELS = (('flowcode', 'FlowCode'), ('python', 'Python'),
                  ('java', 'Java'), ('vb', 'VB'), ('c', 'C'))


class TranslatorView:
    def __init__(self, parent, C, get_model):
        import tkinter as tk
        self.tk = tk
        self.C = C
        self.get_model = get_model
        self._cache = {}
        self.left_dialect = 'flowcode'
        self.right_dialect = 'python'
        self.split = False

        bar = tk.Frame(parent, bg=C['palette'])
        bar.pack(side='top', fill='x')
        self._btns = {}
        for key, label in DIALECT_LABELS:
            b = tk.Button(bar, text=label, bg=C['palette'], fg=C['dim'],
                          relief='flat', bd=0, padx=8, pady=3,
                          font=('Monospace', 9, 'bold'), cursor='hand2',
                          activebackground=C['inspect'],
                          command=lambda k=key: self.select(k))
            b.pack(side='left')
            self._btns[key] = b
        tk.Button(bar, text='Split ⇆', command=self.toggle_split,
                  bg=C['palette'], fg=C['dim'], relief='flat', bd=0,
                  padx=8, pady=3, font=('Monospace', 9),
                  cursor='hand2').pack(side='right')
        tk.Button(bar, text='Copy', command=self.copy_current,
                  bg=C['palette'], fg=C['dim'], relief='flat', bd=0,
                  padx=8, pady=3, font=('Monospace', 9),
                  cursor='hand2').pack(side='right')

        self.panes = tk.PanedWindow(parent, orient='horizontal',
                                    bg=C['bg'], sashwidth=4, bd=0)
        self.panes.pack(fill='both', expand=True, padx=6, pady=6)
        self.left = self._make_pane()
        self.right = self._make_pane()
        self.panes.add(self.left['frame'])
        self.refresh()
        self.select('flowcode')

    def _make_pane(self):
        tk = self.tk
        f = tk.Frame(self.panes, bg=self.C['bg'])
        t = tk.Text(f, bg=self.C['inspect'], fg=self.C['text'],
                    font=('Monospace', 9), relief='flat', wrap='none',
                    state='disabled', padx=8, pady=6, highlightthickness=0)
        t.pack(fill='both', expand=True)
        return {'frame': f, 'text': t}

    # ── behavior ────────────────────────────────────────────────────────────
    def _projection(self, dialect):
        if dialect not in self._cache:
            try:
                self._cache[dialect] = _translate.render(self.get_model(),
                                                         dialect)
            except Exception as e:
                self._cache[dialect] = f'(projection failed: {e})'
        return self._cache[dialect]

    def _show(self, pane, dialect):
        t = pane['text']
        t.config(state='normal')
        t.delete('1.0', 'end')
        t.insert('1.0', self._projection(dialect))
        t.config(state='disabled')

    def select(self, dialect):
        if self.split:
            self.right_dialect = dialect
            self._show(self.right, dialect)
        else:
            self.left_dialect = dialect
            self._show(self.left, dialect)
        for k, b in self._btns.items():
            active = k in ((self.left_dialect, self.right_dialect)
                           if self.split else (self.left_dialect,))
            b.config(fg=self.C.get('pal_border', '#6cf')
                     if active else self.C['dim'])

    def toggle_split(self):
        self.split = not self.split
        if self.split:
            self.panes.add(self.right['frame'])
            self._show(self.right, self.right_dialect)
        else:
            self.panes.forget(self.right['frame'])
        self.select(self.right_dialect if self.split else self.left_dialect)

    def copy_current(self):
        d = self.right_dialect if self.split else self.left_dialect
        txt = self._projection(d)
        self.panes.clipboard_clear()
        self.panes.clipboard_append(txt)

    def refresh(self):
        """Substrate changed: drop the cache and re-render visible panes."""
        self._cache = {}
        self._show(self.left, self.left_dialect)
        if self.split:
            self._show(self.right, self.right_dialect)
