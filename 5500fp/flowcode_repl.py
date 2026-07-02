"""flowcode_repl.py — the Shell REPL engine.

The interactive command line behind the Shell tab's Output area.  Pure
engine, no tkinter: the UI feeds lines in and prints results out, so the
whole behavior is unit-testable headlessly.

Two command families, one prompt:

* **Registry commands** (`text_*`, `math_*`, `list_*`, `env_*`) execute on
  the C emulator through the SAME compile path the visual Shell uses —
  the REPL is provably the visual Shell in text form, protected by the
  same parity harness.  Pipes `|` build dst-param chains; `&&` sequences.

      > text_upper("hello")
      > text_split("a,b,c", ",") | list_count
      > math_add(a=4, b=5) | math_multiply.b

  Bare-word sugar: `env_set FOO "bar"` == `env_set(name="FOO", value="bar")`.

* **Filesystem commands** (`ls cat pwd cd cp mv rm mkdir touch echo run`)
  execute engine-side through the FileSystem abstraction (`filesystem.py`),
  never via raw open()/os.path — so the native TernOO FS slots in later
  without touching this file.  Per the text/language handoff's scoping
  lean these are REPL-only for now (no t5asm lowering); emulator-side
  execution arrives with the native FS.

  `run <file.t5asm> [--sdl]` spawns an emulator instance on a program —
  the shell learning to exec.  Session-layer rung 1 (DocPhase note B2).

`capture_last()` returns the last successful registry pipeline as
(cmd_meta, cmd_edges) ready to place on the Connectors canvas.

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import os
import re
import subprocess
import tempfile

import importlib.util as _ilu

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_fs_mod = _load('filesystem')
_fcmd = _load('flowcode_commands')
_dialect = _load('flowcode_dialect')

_EMU = os.path.abspath(os.path.join(
    _HERE, '..', 'NASM-TernOO-5500FP-Emulator', 'c_emulator', '5500fp'))

FS_COMMANDS = ('ls', 'cat', 'pwd', 'cd', 'cp', 'mv', 'rm', 'mkdir',
               'touch', 'echo', 'run', 'help', 'history')


class ReplError(ValueError):
    pass


# ═══════════════════════════════════════════════════════════════════════════
# Line parsing
# ═══════════════════════════════════════════════════════════════════════════

_CALL_RE = re.compile(r'^(?P<name>[A-Za-z_]\w*)\s*(?:\((?P<params>.*)\))?'
                      r'(?:\.(?P<inparam>\w+))?\s*$')


def _split_top(s: str, sep: str):
    parts, buf, q = [], '', False
    i = 0
    while i < len(s):
        ch = s[i]
        if ch == '"':
            q = not q
        if not q and s.startswith(sep, i):
            parts.append(buf); buf = ''; i += len(sep); continue
        buf += ch; i += 1
    parts.append(buf)
    return parts


def _registry_kind(name: str):
    for cand in (name, 'cmd_' + name):
        if cand in _fcmd.COMMAND_REGISTRY:
            return cand
    return None


def _bareword_call(text: str):
    """`env_set FOO "bar"` sugar → name + positional params by registry
    signature order."""
    toks = re.findall(r'"(?:[^"\\]|\\.)*"|\S+', text.strip())
    if not toks:
        return None
    kind = _registry_kind(toks[0])
    if not kind:
        return None
    spec = _fcmd.COMMAND_REGISTRY[kind]
    params = {}
    for p, tok in zip(spec.get('params', []), toks[1:]):
        v = tok[1:-1].replace('\\"', '"') if tok.startswith('"') else tok
        if p.get('type') == 'number':
            try:
                v = int(v)
            except ValueError:
                pass
        params[p['name']] = v
    return kind, params, None


def parse_pipeline(text: str):
    """One pipeline (`a | b.param | c`) → (cmd_meta dict, cmd_edges list)."""
    stages = [s.strip() for s in _split_top(text, '|')]
    cmds, edges = {}, []
    prev = None
    for idx, stage in enumerate(stages):
        m = _CALL_RE.match(stage)
        if m and _registry_kind(m['name']):
            kind = _registry_kind(m['name'])
            params = _call_params(kind, m['params'] or '') \
                if m['params'] is not None else {}
            inparam = m['inparam']
        else:
            bw = _bareword_call(stage)
            if not bw:
                raise ReplError(f"unknown command: {stage.split('(')[0].split()[0]!r}")
            kind, params, inparam = bw
        cid = 1000 + idx
        cmds[cid] = {'id': cid, 'name': f'r{idx}', 'kind': kind,
                     'x': 10 + 60 * idx, 'y': 10, 'w': 160, 'h': 80,
                     'label': '',
                     'properties': [{'name': k, 'value': v}
                                    for k, v in params.items()]}
        if prev is not None:
            dst_param = inparam or _default_in_param(kind, params)
            edges.append({'src': prev, 'dst': cid, 'dst_param': dst_param})
        prev = cid
    return cmds, edges


def _call_params(kind, raw: str) -> dict:
    """key=value and/or positional args; positionals map onto the registry
    signature in order, skipping names already given."""
    params, positional = {}, []
    raw = raw.strip()
    if raw:
        for tok in _split_top(raw, ','):
            tok = tok.strip()
            m = re.match(r'^([A-Za-z_]\w*)\s*=\s*(.+)$', tok)
            if m:
                params[m.group(1)] = _coerce(m.group(2))
            else:
                positional.append(_coerce(tok))
    sig = [p['name'] for p in _fcmd.COMMAND_REGISTRY[kind].get('params', [])]
    free = [n for n in sig if n not in params]
    if len(positional) > len(free):
        raise ReplError(f"too many arguments for {kind}")
    for name, val in zip(free, positional):
        params[name] = val
    return params


def _coerce(v: str):
    v = v.strip()
    if v.startswith('"') and v.endswith('"'):
        return v[1:-1].replace('\\"', '"')
    try:
        return int(v)
    except ValueError:
        return v


def _default_in_param(kind, given):
    """First registry param not already supplied — the natural pipe target."""
    for p in _fcmd.COMMAND_REGISTRY[kind].get('params', []):
        if p['name'] not in given:
            return p['name']
    return 'value'


# ═══════════════════════════════════════════════════════════════════════════
# Execution
# ═══════════════════════════════════════════════════════════════════════════

class Repl:
    def __init__(self, fs=None, emulator=_EMU):
        self.fs = fs or _fs_mod.get_fs()
        self.emulator = emulator
        self.history = []
        self._last_pipeline = None     # (cmds, edges) of last registry run

    # -- public ------------------------------------------------------------
    def execute(self, line: str) -> str:
        """One prompt line → output text.  `&&` sequences short-circuit on
        error."""
        line = line.strip()
        if not line:
            return ''
        self.history.append(line)
        outs = []
        parts = [p.strip() for p in _split_top(line, '&&')]
        i = 0
        try:
            while i < len(parts):
                head = parts[i].split('(')[0].split()[0] if parts[i] else ''
                if head in FS_COMMANDS:
                    outs.append(self._fs_command(parts[i]))
                    i += 1
                    continue
                # group consecutive registry parts into ONE program so
                # env state persists across `&&` within a line (a line is
                # one invocation, like a real shell)
                group = []
                while i < len(parts):
                    h = parts[i].split('(')[0].split()[0] if parts[i] else ''
                    if h in FS_COMMANDS:
                        break
                    group.append(parse_pipeline(parts[i]))
                    i += 1
                outs.append(self._run_group(group))
                self._last_pipeline = group[-1]
        except (ReplError, FileNotFoundError, IsADirectoryError,
                NotADirectoryError, PermissionError, OSError) as e:
            outs.append(f"error: {e}")
        return '\n'.join(o for o in outs if o != '')

    def capture_last(self):
        """(cmd_meta, cmd_edges) of the last successful registry pipeline,
        for placement on the Connectors canvas."""
        return self._last_pipeline

    # -- registry path: compile + run on the emulator -----------------------
    def _run_group(self, group) -> str:
        """Merge N pipelines into one program (ids re-based per segment),
        printing each segment's terminal result in order."""
        cmds, edges, terminals = {}, [], []
        base = 1000
        for seg_cmds, seg_edges in group:
            idmap = {}
            for old in sorted(seg_cmds):
                new = base; base += 1
                idmap[old] = new
                c = dict(seg_cmds[old]); c['id'] = new
                cmds[new] = c
            for e in seg_edges:
                edges.append({'src': idmap[e['src']], 'dst': idmap[e['dst']],
                              'dst_param': e.get('dst_param')})
            terminals.append(idmap[max(seg_cmds)])
        return self._run_on_emulator(cmds, edges, terminals)

    def _run_on_emulator(self, cmds, edges, terminals=None) -> str:
        C = _load('compile_to_t5asm')
        ws = _load('word_stream')
        stream = ws.WordStream([])
        stream._widget_meta = {}
        stream._flow_meta = {}
        stream._cell_meta = {}
        stream._cmd_meta = cmds
        stream._cmd_edges = edges
        asm = C.compile_wordstream_to_t5asm(stream)
        _cmdc = _load('command_t5asm')
        for n, tid in enumerate(terminals or [max(cmds)]):
            out_type = _cmdc.command_output_kind(cmds[tid]['kind'])
            if out_type and out_type != 'none':
                asm = _inject_result_print(asm, tid, out_type, n)
        if not (os.path.isfile(self.emulator)
                and os.access(self.emulator, os.X_OK)):
            raise ReplError("emulator not built — run `make` in "
                            "NASM-TernOO-5500FP-Emulator/c_emulator/")
        with tempfile.NamedTemporaryFile('w', suffix='.t5asm',
                                         delete=False) as f:
            f.write(asm)
            path = f.name
        try:
            r = subprocess.run([self.emulator, '--run', path],
                               capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        lines = [l for l in r.stdout.splitlines()
                 if l and not l.startswith(('5500FP', 'Architecture', '---'))
                 and not (l.startswith('[') and l.endswith('cycles]'))]
        return '\n'.join(lines)

    # -- fs path: through the abstraction ------------------------------------
    def _fs_command(self, part: str) -> str:
        # echo redirect first: echo "text" > path   /  >> path
        m = re.match(r'^echo\s+(?P<txt>"(?:[^"\\]|\\.)*"|\S+)\s*'
                     r'(?P<redir>>>|>)?\s*(?P<path>\S+)?\s*$', part)
        if m and part.startswith('echo'):
            txt = m['txt']
            txt = txt[1:-1].replace('\\"', '"') if txt.startswith('"') else txt
            if m['redir'] and m['path']:
                if m['redir'] == '>':
                    self.fs.save(m['path'], txt + '\n')
                else:
                    self.fs.append(m['path'], txt + '\n')
                return ''
            return txt

        toks = part.split()
        cmd, args = toks[0], toks[1:]
        if cmd == 'pwd':
            return self.fs.getcwd()
        if cmd == 'ls':
            path = args[0] if args else '.'
            return '  '.join(self.fs.list(path))
        if cmd == 'cat':
            if not args:
                raise ReplError("cat: path required")
            return self.fs.read(args[0]).rstrip('\n')
        if cmd == 'cd':
            self.fs.chdir(args[0] if args else '~')
            return ''
        if cmd == 'cp':
            self.fs.copy(args[0], args[1]); return ''
        if cmd == 'mv':
            self.fs.move(args[0], args[1]); return ''
        if cmd == 'rm':
            self.fs.delete(args[0]); return ''
        if cmd == 'mkdir':
            self.fs.mkdir(args[0]); return ''
        if cmd == 'touch':
            self.fs.touch(args[0]); return ''
        if cmd == 'history':
            return '\n'.join(f"{i+1}  {h}"
                             for i, h in enumerate(self.history[:-1]))
        if cmd == 'help':
            reg = sorted(k[4:] if k.startswith('cmd_') else k
                         for k in _fcmd.COMMAND_REGISTRY)
            return ("registry: " + ' '.join(reg) + "\n"
                    "fs: " + ' '.join(FS_COMMANDS) + "\n"
                    "pipes: a | b.param   sequence: a && b   "
                    "redirect: echo \"x\" > file")
        if cmd == 'run':
            if not args:
                raise ReplError("run: program path required")
            prog = args[0]
            sdl = '--sdl' in args
            if not self.fs.exists(prog):
                raise ReplError(f"run: no such program: {prog}")
            host_path = self.fs._abs(prog) if hasattr(self.fs, '_abs') else prog
            argv = [self.emulator,
                    '--display', 'sdl' if sdl else 'ascii',
                    '--run', host_path]
            if sdl:
                subprocess.Popen(argv)           # fire and forget: a window
                return f"launched {prog}"
            r = subprocess.run(argv, capture_output=True, text=True,
                               timeout=60)
            return r.stdout.rstrip('\n')
        raise ReplError(f"unknown command: {cmd!r}")


def _inject_result_print(asm: str, last_id: int, out_type: str, n: int = 0) -> str:
    """The compiled shell program leaves the terminal command's result in
    its state slot; the REPL wants it on stdout.  Insert a print stanza
    before the final HALT: numbers via syscall 1; text handles by walking
    the NUL-terminated char run at handle+1 (same pattern the command
    test-suite uses); lists print their count (their elements are handles —
    full pretty-printing arrives with the native string formatter)."""
    slot = f'state_cmd_{last_id}'
    if out_type in ('number', 'bool'):
        stanza = [f'    LI   R20, {slot}',
                  '    LDW  R2, R20, 0',
                  '    LI   R1, 1', '    SYSCALL',
                  '    LI   R1, 6', '    SYSCALL']
    elif out_type == 'list':
        stanza = [f'    LI   R20, {slot}',
                  '    LDW  R10, R20, 0',
                  '    LDW  R2, R10, 0   ; list header word 0 = count',
                  '    LI   R1, 1', '    SYSCALL',
                  '    LI   R1, 6', '    SYSCALL']
    else:  # text handle
        stanza = [f'    LI   R20, {slot}',
                  '    LDW  R10, R20, 0',
                  '    ADDI R10, R10, 1',
                  f'repl_pl_{n}:',
                  '    LDW  R2, R10, 0',
                  f'    BEQZ R2, repl_pd_{n}',
                  '    LI   R1, 3', '    SYSCALL',
                  '    ADDI R10, R10, 1',
                  f'    JMP  repl_pl_{n}',
                  f'repl_pd_{n}:',
                  '    LI   R1, 6', '    SYSCALL']
    idx = asm.rfind('HALT')
    return asm[:idx] + '\n'.join(stanza) + '\n    ' + asm[idx:]
