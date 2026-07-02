"""text_tab_view.py — the Text tab: dual-mode editor (Piece 1).

FlowCode-dialect mode (.fc): a textual projection of the substrate with
bidirectional Sync.  General text mode (anything else): an ordinary editor
through the FileSystem abstraction — design notes, configs, scratch files —
so nobody leaves FlowCode to open Kate.  Hospitable-infrastructure
archetype: the canvas is first-class, this tab exists so nobody has to
use it, and both statements matter.

Wiring contract (kept thin so flowcode.py stays the only fc_state expert):
    TextTabView(parent, C, root,
                get_model,      # () -> dialect model dicts (projection src)
                apply_model,    # (model) -> None (replace state + refresh)
                set_status)     # (msg) -> None

tkinter is imported lazily so the module loads headless for tests of the
mode/gating logic.

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


_dialect = _load('flowcode_dialect')
_fs_mod = _load('filesystem')


def mode_for(path) -> str:
    """'flowcode' for .fc files, 'text' otherwise (including untitled)."""
    if path and str(path).lower().endswith('.fc'):
        return 'flowcode'
    return 'text'


class TextTabView:
    def __init__(self, parent, C, root, get_model, apply_model, set_status):
        import tkinter as tk
        self.tk = tk
        self.C = C
        self.root = root
        self.get_model = get_model
        self.apply_model = apply_model
        self.set_status = set_status
        self.path = None            # current file path (None = untitled)
        self.mode = 'text'
        self._dirty = False

        bar = tk.Frame(parent, bg=C['palette'])
        bar.pack(side='top', fill='x')
        for label, cmd in (('New', self.new_file),
                           ('Open', self.open_file), ('Save', self.save),
                           ('Save As', self.save_as), ('Sync ⇄', self.sync),
                           ('Format', self.format_text),
                           ('From Canvas', self.render_from_substrate)):
            tk.Button(bar, text=label, command=cmd, bg=C['palette'],
                      fg=C['text'], relief='flat', bd=0, padx=10, pady=4,
                      activebackground=C['inspect'], cursor='hand2',
                      font=('Monospace', 9, 'bold')).pack(side='left')
        self.mode_lbl = tk.Label(bar, text='[Text] untitled', bg=C['palette'],
                                 fg=C['dim'], font=('Monospace', 9))
        self.mode_lbl.pack(side='right', padx=8)

        self.txt = tk.Text(parent, bg=C['inspect'], fg=C['text'],
                           insertbackground=C['text'], font=('Monospace', 10),
                           relief='flat', wrap='none', undo=True, padx=8,
                           pady=6, highlightthickness=0)
        self.txt.pack(fill='both', expand=True, padx=6, pady=(6, 0))
        self.txt.tag_configure('errline', background='#5a2020')
        self.txt.bind('<<Modified>>', self._on_modified)

        self.status = tk.Label(parent, text='general text mode',
                               bg=C['palette'], fg=C['dim'], anchor='w',
                               font=('Monospace', 9))
        self.status.pack(side='bottom', fill='x', padx=6, pady=(2, 6))

    # ── helpers ─────────────────────────────────────────────────────────────
    def _fs(self):
        return _fs_mod.get_fs()

    def _set_mode(self, path):
        self.path = path
        self.mode = mode_for(path)
        name = os.path.basename(path) if path else 'untitled'
        tag = '[FlowCode]' if self.mode == 'flowcode' else '[Text]'
        self.mode_lbl.config(text=f'{tag} {name}')
        self.status.config(
            text=('FlowCode dialect — Sync ⇄ projects edits to the canvas'
                  if self.mode == 'flowcode' else 'general text mode'))

    def _on_modified(self, _e=None):
        if self.txt.edit_modified():
            self._dirty = True
            if self.mode == 'flowcode':
                self.status.config(
                    text='text modified — Sync ⇄ to project to canvas')
            self.txt.edit_modified(False)

    def text(self) -> str:
        return self.txt.get('1.0', 'end-1c')

    def set_text(self, s: str):
        self.txt.delete('1.0', 'end')
        self.txt.insert('1.0', s)
        self.txt.edit_modified(False)
        self._dirty = False

    def _confirm_discard(self) -> bool:
        """True if it's safe to replace the buffer (clean, or user agrees)."""
        if not self._dirty:
            return True
        from tkinter import messagebox
        return messagebox.askyesno(
            'Unsaved changes',
            'The current document has unsaved changes.\nDiscard them?')

    def new_file(self):
        """Fresh untitled buffer — no close-and-reopen dance required."""
        if not self._confirm_discard():
            return
        self.set_text('')
        self._set_mode(None)
        self.status.config(text='new document')

    # ── actions ─────────────────────────────────────────────────────────────
    def render_from_substrate(self):
        """Canvas → text (the projection direction)."""
        try:
            self.set_text(_dialect.project(self.get_model()))
            self.mode = 'flowcode'
            self.mode_lbl.config(
                text='[FlowCode] ' + (os.path.basename(self.path)
                                      if self.path else 'untitled'))
            self.status.config(text='in sync with canvas')
        except Exception as e:
            self.set_status(f'Text tab: projection failed: {e}')

    def sync(self):
        """Text → substrate.  Parse first; failed parses never touch the
        canvas.  Errors highlight the offending line."""
        if self.mode != 'flowcode':
            self.status.config(text='general text mode — nothing to sync '
                                    '(save as .fc for dialect mode)')
            return
        self.txt.tag_remove('errline', '1.0', 'end')
        try:
            model = _dialect.parse(self.text())
        except _dialect.DialectError as e:
            self.txt.tag_add('errline', f'{e.line_no}.0',
                             f'{e.line_no}.end')
            self.txt.see(f'{e.line_no}.0')
            self.status.config(text=str(e))
            return
        try:
            self.apply_model(model)
            self.status.config(text='in sync — canvas updated')
            self.set_status('Text ⇄ canvas: synced')
        except Exception as e:
            self.status.config(text=f'apply failed: {e}')

    def format_text(self):
        """Canonicalize: parse then re-project.  Only valid text formats."""
        if self.mode != 'flowcode':
            return
        try:
            self.set_text(_dialect.project(_dialect.parse(self.text())))
            self.status.config(text='formatted (canonical form)')
        except _dialect.DialectError as e:
            self.txt.tag_add('errline', f'{e.line_no}.0', f'{e.line_no}.end')
            self.status.config(text=str(e))

    def open_file(self):
        from tkinter import filedialog
        if not self._confirm_discard():
            return
        p = filedialog.askopenfilename(title='Open file')
        if not p:
            return
        try:
            self.set_text(self._fs().read(p))
            self._set_mode(p)
        except OSError as e:
            self.status.config(text=f'open failed: {e}')

    def save(self):
        if not self.path:
            return self.save_as()
        try:
            self._fs().save(self.path, self.text())
            self._dirty = False
            self.status.config(text=f'saved {os.path.basename(self.path)}')
            if self.mode == 'flowcode':
                self.sync()
        except OSError as e:
            self.status.config(text=f'save failed: {e}')

    def save_as(self):
        from tkinter import filedialog
        p = filedialog.asksaveasfilename(title='Save as')
        if not p:
            return
        self._set_mode(p)   # extension decides mode; any extension respected
        self.save()
