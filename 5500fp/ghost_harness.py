"""ghost_harness.py — the GHOST Academy engine (harness, headless).

Everything the GHOST tab does, minus pixels — so the whole Academy is
unit-testable without a display:

  * Curriculum  — the corpus externalized to ghost_corpus.json (seeded from
    ghost_train.TEMPLATES on first run); add/remove phrases per class.
  * !learn      — explicit teaching at any prompt:
                     !learn <class> "<phrase>"      (teach a routing)
                     !learn none "<phrase>"         (teach a refusal)
                     !learn-undo                    (revert last lesson)
                     !learn-log                     (show the education)
    Every lesson appends to ghost_learnlog.jsonl (append-only: an
    inspectable mind deserves an inspectable education — Reference §3).
  * Train       — retrain from the live curriculum; returns a REPORT CARD:
    held-out accuracy, refusal correctness, worst-confused class pairs.
  * .chat v1    — the conversation file format (B4): front-matter metadata
    + turn lines with @route annotations; writer + parser + round-trip.
  * chat()      — one prompt turn: route on the EMULATOR (native forward
    pass), apply the humility gate, log the turn for the archive.

Epistemic humility invariants preserved (Reference §3): the none class,
the margin gate (now teachable via !learn none), and inspectability
(model-as-words via ghost_train.export_neural_words).

Date: 2026-07-05, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import importlib.util as _ilu
import json
import os
import subprocess
import tempfile
import time

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


G = _load('ghost_train')
GEN = _load('gen_ghost_t5asm')
_fs_mod = _load('filesystem')

_EMU = os.path.join(_HERE, '..', 'NASM-TernOO-5500FP-Emulator',
                    'c_emulator', '5500fp')

CORPUS_FILE = 'ghost_corpus.json'
MODEL_FILE = 'ghost_model.json'
LEARNLOG_FILE = 'ghost_learnlog.jsonl'
CHAT_VERSION = 1

# ── Majors (Spec A / B6): a major = corpus + model + learnlog triple. ──────
# The default major is the command router (original files, untouched paths).
MAJORS = {
    'commands': {'corpus': 'ghost_corpus.json',
                 'model': 'ghost_model.json',
                 'learnlog': 'ghost_learnlog.jsonl',
                 'seed_from_templates': True},
    'surfaces': {'corpus': 'ghost_corpus_surfaces.json',
                 'model': 'ghost_major_surfaces.json',
                 'learnlog': 'ghost_learnlog_surfaces.jsonl',
                 'seed_from_templates': False},
}


class HarnessError(ValueError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# Curriculum (corpus persistence)
# ═══════════════════════════════════════════════════════════════════════════

def load_corpus(fs=None, major='commands') -> dict:
    """{class: [template, ...]}. The commands major seeds from
    ghost_train.TEMPLATES on first run (the shipped syllabus); other
    majors seed from their corpus file in the repo (copied into the fs
    root on first use)."""
    fs = fs or _fs_mod.get_fs()
    m = MAJORS[major]
    if fs.exists(m['corpus']):
        return json.loads(fs.read(m['corpus']))
    if m.get('seed_from_templates'):
        corpus = {k: list(v) for k, v in G.TEMPLATES.items()}
    else:
        repo_seed = os.path.join(_HERE, m['corpus'])
        if not os.path.exists(repo_seed):
            raise HarnessError(f"no corpus for major {major!r}")
        corpus = json.loads(open(repo_seed).read())
    save_corpus(corpus, fs, major)
    return corpus


def save_corpus(corpus: dict, fs=None, major='commands') -> None:
    fs = fs or _fs_mod.get_fs()
    fs.save(MAJORS[major]['corpus'], json.dumps(corpus, indent=1))


# ═══════════════════════════════════════════════════════════════════════════
# The Harness
# ═══════════════════════════════════════════════════════════════════════════

class Harness:
    def __init__(self, fs=None, emulator=_EMU, major='commands'):
        if major not in MAJORS:
            raise HarnessError(f"unknown major {major!r} — one of: "
                               + ', '.join(sorted(MAJORS)))
        self.major = major
        self._files = MAJORS[major]
        self.fs = fs or _fs_mod.get_fs()
        self.emulator = emulator
        self.corpus = load_corpus(self.fs, major)
        model_path = self._files['model']
        if self.fs.exists(model_path):
            self.model = json.loads(self.fs.read(model_path))
        elif major != 'commands' and os.path.exists(os.path.join(_HERE, model_path)):
            self.model = json.loads(open(os.path.join(_HERE, model_path)).read())
        else:
            self.model = None
        self.turns = []                 # current session, for .chat save

    # ── !learn ───────────────────────────────────────────────────────────
    def learn(self, cls: str, phrase: str) -> str:
        """Teach one phrase.  Confirmation is the CALLER's job (the tab and
        the REPL both echo-and-confirm before invoking this); here the
        lesson is committed and logged."""
        if cls != 'none' and cls not in self.corpus:
            if 'cmd_' + cls in self.corpus:
                cls = 'cmd_' + cls
            else:
                raise HarnessError(f"unknown class {cls!r} — one of: "
                                   + ', '.join(sorted(self.corpus)))
        phrase = phrase.strip()
        if not phrase:
            raise HarnessError("empty phrase")
        if phrase in self.corpus[cls]:
            return f"already known: {cls} ← {phrase!r}"
        self.corpus[cls].append(phrase)
        save_corpus(self.corpus, self.fs, self.major)
        self._log({'op': 'learn', 'class': cls, 'phrase': phrase,
                   'ts': int(time.time())})
        return (f"learned: {cls} ← {phrase!r}   "
                f"(takes effect on next train)")

    def learn_undo(self) -> str:
        entries = self._log_entries()
        for e in reversed(entries):
            if e.get('op') == 'learn' and not e.get('undone'):
                cls, phrase = e['class'], e['phrase']
                if phrase in self.corpus.get(cls, []):
                    self.corpus[cls].remove(phrase)
                    save_corpus(self.corpus, self.fs, self.major)
                self._log({'op': 'undo', 'class': cls, 'phrase': phrase,
                           'ts': int(time.time())})
                return f"unlearned: {cls} ← {phrase!r}"
        return "nothing to undo"

    def learn_log(self) -> str:
        entries = self._log_entries()
        if not entries:
            return "(no lessons yet)"
        lines = []
        for e in entries:
            mark = '↩' if e['op'] == 'undo' else '＋'
            lines.append(f"{mark} {e['class']:20s} {e['phrase']!r}")
        return '\n'.join(lines)

    def _log(self, entry: dict) -> None:
        self.fs.append(self._files['learnlog'], json.dumps(entry) + '\n')

    def _log_entries(self):
        if not self.fs.exists(self._files['learnlog']):
            return []
        out = []
        undone_pairs = set()
        raw = [json.loads(l) for l in
               self.fs.read(self._files['learnlog']).splitlines() if l.strip()]
        for e in raw:
            if e['op'] == 'undo':
                undone_pairs.add((e['class'], e['phrase']))
        for e in raw:
            if e['op'] == 'learn' and (e['class'], e['phrase']) in undone_pairs:
                e = dict(e); e['undone'] = True
            out.append(e)
        return out

    # ── training + report card ───────────────────────────────────────────
    def train(self, seed=27) -> dict:
        """Retrain from the live curriculum.  Returns the report card and
        persists the new model (the golden suite re-verifies it)."""
        saved_t, saved_c = G.TEMPLATES, G.CLASSES
        classes = ['none'] + sorted(k for k in self.corpus if k != 'none')
        try:
            G.TEMPLATES = {k: list(v) for k, v in self.corpus.items()}
            G.CLASSES = classes
            W1, W2, held = G.train(seed=seed)
            acc = G.accuracy(held, W1, W2)
        finally:
            G.TEMPLATES, G.CLASSES = saved_t, saved_c
        self.model = {'nfeat': G.NFEAT, 'nhid': G.NHID,
                      'classes': classes, 'margin': G.MARGIN,
                      'W1': W1, 'W2': W2}
        self.fs.save(self._files['model'], json.dumps(self.model))
        confusion = {}
        for text, y in held:
            got, _m = self._route_host(text, W1, W2, classes)
            want = classes[y]
            if got != want:
                pair = f"{want} → {got}"
                confusion[pair] = confusion.get(pair, 0) + 1
        worst = sorted(confusion.items(), key=lambda kv: -kv[1])[:5]
        refusals_ok = sum(1 for t in
                          self.corpus.get('none', [])[:10]
                          if self._route_host(t.format(*(['x'] * t.count('{}'))),
                                              W1, W2, classes)[0] == 'none')
        report = {'held_out_accuracy': round(acc, 4),
                  'held_out_n': len(held),
                  'refusal_check': f"{refusals_ok}/10",
                  'worst_confusions': worst,
                  'weights_as_words': len(
                      G.export_neural_words(W1, W2))}
        self._log({'op': 'train', 'accuracy': report['held_out_accuracy'],
                   'ts': int(time.time()), 'class': '-', 'phrase': '-'})
        return report

    @staticmethod
    def _route_host(text, W1, W2, classes):
        """Host-reference routing with an explicit class list (majors have
        different class sets than the module-level G.CLASSES)."""
        saved = G.CLASSES
        try:
            G.CLASSES = classes          # ref_forward sizes its output loop
            cls_idx, margin, _ = G.ref_forward(text, W1, W2)
        finally:
            G.CLASSES = saved
        cls = classes[cls_idx]
        if cls == 'none' or margin < G.MARGIN:
            return 'none', margin
        return cls, margin

    # ── routing (native, on the emulator) ────────────────────────────────
    def route(self, text: str):
        """(class_name, margin) via the NATIVE forward pass."""
        if self.model is None:
            raise HarnessError("no model — press Train first")
        asm = GEN.emit_forward(text, self.model)
        with tempfile.NamedTemporaryFile('w', suffix='.t5asm',
                                         delete=False) as f:
            f.write(asm); p = f.name
        try:
            r = subprocess.run([self.emulator, '--run', p],
                               capture_output=True, text=True, timeout=60)
        finally:
            os.unlink(p)
        nums = [int(l) for l in r.stdout.splitlines()
                if l.strip().lstrip('-').isdigit()]
        if len(nums) < 2:
            raise HarnessError("native forward pass produced no result")
        cls_idx, margin = nums[0], nums[1]
        cls = self.model['classes'][cls_idx]
        if cls == 'none' or margin < self.model['margin']:
            return 'none', margin
        return cls, margin

    def chat(self, text: str) -> str:
        """One conversational turn: route natively, humility-gate, log."""
        cls, margin = self.route(text)
        if cls == 'none':
            reply = f"I'm sorry, I can't do that — yet.  (margin {margin})"
        else:
            short = cls[4:] if cls.startswith('cmd_') else cls
            reply = (f"that sounds like {short}  (margin {margin}) — "
                     f"try `{short}(...)`")
        self.turns.append({'user': text, 'ghost': reply,
                           'route': cls, 'margin': margin,
                           'ts': int(time.time())})
        return reply

    # ── .chat v1 ─────────────────────────────────────────────────────────
    def save_chat(self, path: str, title: str = 'GHOST session') -> str:
        self.fs.save(path, format_chat(self.turns, self.model, title))
        return path

    def open_chat(self, path: str) -> list:
        return parse_chat(self.fs.read(path))['turns']


# ═══════════════════════════════════════════════════════════════════════════
# .chat v1 format — writer + parser (round-trip pinned in tests)
# ═══════════════════════════════════════════════════════════════════════════

def format_chat(turns, model, title='GHOST session') -> str:
    L = ['---',
         f'chat-version: {CHAT_VERSION}',
         f'title: {title}',
         f'date: {time.strftime("%Y-%m-%d %H:%M")}',
         f'model-classes: {len(model["classes"]) if model else 0}',
         f'margin: {model["margin"] if model else "-"}',
         'participants: user, ghost',
         '---']
    for t in turns:
        L.append(f'> {t["user"]}')
        L.append(f'ghost: {t["ghost"]}')
        L.append(f'@route({t["route"]}, {t["margin"]})')
        L.append('')
    return '\n'.join(L) + '\n'


def parse_chat(text: str) -> dict:
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        raise HarnessError(".chat: missing front-matter")
    i = 1
    meta = {}
    while i < len(lines) and lines[i].strip() != '---':
        if ':' in lines[i]:
            k, _, v = lines[i].partition(':')
            meta[k.strip()] = v.strip()
        i += 1
    i += 1
    turns, cur = [], None
    for ln in lines[i:]:
        if ln.startswith('> '):
            cur = {'user': ln[2:], 'ghost': '', 'route': None, 'margin': None}
            turns.append(cur)
        elif ln.startswith('ghost: ') and cur:
            cur['ghost'] = ln[len('ghost: '):]
        elif ln.startswith('@route(') and cur:
            inner = ln[len('@route('):].rstrip(')')
            cls, _, m = inner.partition(',')
            cur['route'] = cls.strip()
            cur['margin'] = int(m.strip())
    return {'meta': meta, 'turns': turns}


# ═══════════════════════════════════════════════════════════════════════════
# !learn command-line parsing (shared by REPL and GHOST tab)
# ═══════════════════════════════════════════════════════════════════════════

def parse_bang(line: str):
    """'!learn cls \"phrase\"' → ('learn', cls, phrase);
    '!learn-undo' → ('undo',); '!learn-log' → ('log',); else None."""
    s = line.strip()
    if s == '!learn-undo':
        return ('undo',)
    if s == '!learn-log':
        return ('log',)
    if s.startswith('!learn '):
        rest = s[len('!learn '):].strip()
        cls, _, phrase = rest.partition(' ')
        phrase = phrase.strip()
        if phrase.startswith('"') and phrase.endswith('"'):
            phrase = phrase[1:-1]
        if not cls or not phrase:
            raise HarnessError('usage: !learn <class> "<phrase>"')
        return ('learn', cls, phrase)
    return None
