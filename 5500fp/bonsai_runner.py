"""bonsai_runner.py — the Professor's Contract v1 adapter (local subprocess).

The keystone that lets the classroom's consent-gated delegation reach a LIVE
professor: it makes the real Bonsai model speak the GHOST<->Bonsai Contract v1
over stdin/stdout. NO sockets, no network — a local subprocess only, so the
five invariants hold structurally (delegation is GHOST -> local-Bonsai, never
GHOST -> cloud).

Reads Contract v1 REQUEST lines on stdin, runs Bonsai, writes Contract v1
RESPONSE lines on stdout, one full reply per request (ONE-SHOT). The streaming
saddle (dispatch 103000 §2) layers on top of this once it's dispatched — this
module is the pipe; §2 is how the water is poured.

Wiring — ZERO-CONFIG by design (Stevo is CLI-averse; no terminal needed):
  1. bonsai.json beside this file (absolute paths, editable in the Text tab)
     — the control switch: {"enabled": true, "llama": ..., "model": ...}.
  2. If no config, AUTO-DISCOVERY: known local homes (~/LOCAL_AI/Llama) are
     searched for a llama-cli/llama-completion binary and the biggest .gguf.
  3. BONSAI_CMD env stays as a power-user override; --mock for tests.
The Academy tab calls classroom_command() at startup and wires whatever it
returns — launch FlowCode normally and the Professor finds his own way in.

Backends:
  * LlamaBackend — shells the PROVEN command from Stevo's own interview
    script: llama-cli -m <gguf> -p <prompt> -n 400 --temp 0.2
    --no-display-prompt -no-cnv (one subprocess per ask, pipes only).
  * EchoBackend — a deterministic mock (tests + binary-less classroom).

Date: 2026-07-09, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

CONTRACT_VERSION = 1


class BackendError(RuntimeError):
    """The model runtime failed to produce an answer — carries the REAL
    reason (rc + stderr tail) so the board never shows a silently mute
    professor again."""


# ═══════════════════════════════════════════════════════════════════════════
# Contract v1 shaping (pure — pinned in tests, and cross-checked by ghost_bonsai)
# ═══════════════════════════════════════════════════════════════════════════

# The persona goes in as a REAL system prompt (-sys, single-turn chat mode)
# so the chat template assigns the roles — as raw completion text the model
# read "You are Bonsai" as the USER's claim and had an identity crisis on
# the board (first contact, 2026-07-10). /no_think is qwen3's soft switch:
# keep the reasoning in his head, not in the chalk (harmless elsewhere).
SYSTEM_PROMPT = ("You are Bonsai, a local assistant consulted by GHOST when "
                 "a question is beyond GHOST's own competence. Answer the "
                 "user's question plainly and honestly; if you do not know, "
                 "say so. /no_think")


def build_prompt(req: dict) -> str:
    """The USER turn: just the delegated question. The persona rides in
    SYSTEM_PROMPT via -sys — never mixed into the user text again."""
    return req.get('text', '')


def build_response(text: str, req: dict,
                   self_confidence='unknown') -> dict:
    """A well-formed Contract v1 response. self_confidence defaults to the
    honest 'unknown' unless the backend can genuinely self-report; the gate
    honours that. claimed_intent_class echoes GHOST's own route (Bonsai does
    not invent a class it cannot stand behind)."""
    claimed = req.get('ghost_route') or 'unknown'
    return {
        'version': CONTRACT_VERSION,
        'text': text,
        'self_confidence': self_confidence,
        'claimed_intent_class': claimed,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Backends
# ═══════════════════════════════════════════════════════════════════════════

_THINK_RE = re.compile(r'<think>.*?</think>', re.DOTALL)


def clean_reply(text: str) -> str:
    """Strip <think>…</think> reasoning from a reply (qwen3-style models
    emit it even when asked nicely). An UNTERMINATED think block — the token
    budget ran out mid-thought — is dropped from <think> to the end: better
    an honest BackendError than the professor's stream of consciousness
    presented as his answer (first-contact lesson)."""
    text = _THINK_RE.sub('', text)
    i = text.find('<think>')
    if i != -1:
        text = text[:i]
    return text.strip()


class EchoBackend:
    """Deterministic mock — no model. Lets the classroom and the tests run a
    full contract round-trip with a present-but-fake professor."""

    def generate(self, prompt: str) -> str:
        q = prompt.rsplit('Question:', 1)[-1].split('\nAnswer:', 1)[0].strip()
        return f"(echo professor) I would say something about: {q}"


class LlamaBackend:
    """Shells the proven llama.cpp invocation (from bonsai_interview_sed.py,
    already verified on this machine) — one subprocess per ask, pipes only."""

    def __init__(self, llama: str, model: str, n_predict: int = 128,
                 threads: int = 2, ctx: int = 1024, timeout: float = 2400.0):
        self.llama, self.model = llama, model
        self.n_predict, self.threads, self.ctx = n_predict, threads, ctx
        self.timeout = timeout

    def argv(self, prompt: str) -> list:
        # Memory/desktop kindness (the hard-reboot lesson, 2026-07-09): the
        # X550LA has ~7.6GB shared with FlowCode + Claude Desktop. So: -c caps
        # the KV cache (the default takes the model's full context and can eat
        # hundreds of MB); -t 2 leaves cores for the mouse; --prio -1 makes
        # the professor the lowest-priority process on the box.
        #
        # -st single-turn chat + -sys persona (the identity-crisis fix): the
        # gguf's chat template assigns the roles, exactly as Stevo's own
        # interview script ran it. One turn, then the process exits.
        return [self.llama, '-m', self.model,
                '-sys', SYSTEM_PROMPT, '-p', prompt, '-st',
                '-n', str(self.n_predict), '--temp', '0.2',
                '-c', str(self.ctx), '-t', str(self.threads),
                '--prio', '-1', '--no-display-prompt']

    def generate(self, prompt: str) -> str:
        """The model's text, or raises BackendError with the REAL reason —
        an empty answer must never ship as silence (screen-truth lesson:
        the CUDA-less binary died fast and the board showed a mute professor)."""
        r = subprocess.run(self.argv(prompt), capture_output=True, text=True,
                           timeout=self.timeout)
        text = clean_reply(r.stdout)
        if r.returncode != 0:
            tail = (r.stderr or '').strip().splitlines()[-3:]
            raise BackendError(
                f"llama exited rc={r.returncode}: " + ' | '.join(tail))
        if not text:
            raise BackendError(
                'professor produced no answer'
                + (' (only <think> reasoning — raise n_predict in '
                   'bonsai.json?)' if '<think>' in r.stdout else ''))
        return text


# ═══════════════════════════════════════════════════════════════════════════
# Zero-config wiring: bonsai.json → auto-discovery → none
# ═══════════════════════════════════════════════════════════════════════════

_HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(_HERE, 'bonsai.json')

# Known local homes for the runtime + model (verified on Stevo's machine).
SEARCH_ROOTS = [os.path.expanduser('~/LOCAL_AI/Llama'),
                os.path.expanduser('~/LOCAL_AI')]
BINARY_NAMES = ('llama-completion', 'llama-cli')   # completion preferred (one-shot tool)


def runnable(path: str, timeout: float = 10.0) -> bool:
    """Does the binary actually RUN on this machine? (--version loads no
    model; a wrong-arch/CUDA-less build dies instantly — the exact failure
    that put an empty professor on the board.)"""
    try:
        r = subprocess.run([path, '--version'], capture_output=True,
                           timeout=timeout)
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def load_config(path: str = None) -> dict | None:
    """bonsai.json if present and readable, else None. Never raises."""
    path = path or CONFIG_PATH
    try:
        with open(path) as f:
            cfg = json.load(f)
        return cfg if isinstance(cfg, dict) else None
    except (OSError, ValueError):
        return None


def discover(roots=None) -> dict | None:
    """Find a llama binary + the biggest .gguf under the known homes.
    Returns {'llama': ..., 'model': ...} with absolute paths, or None."""
    roots = SEARCH_ROOTS if roots is None else roots
    candidates = []
    ggufs = []
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                p = os.path.join(dirpath, f)
                if f in BINARY_NAMES and os.access(p, os.X_OK):
                    candidates.append((BINARY_NAMES.index(f), p))
                if f.endswith('.gguf'):
                    try:
                        ggufs.append((os.path.getsize(p), p))
                    except OSError:
                        pass
    if not candidates or not ggufs:
        return None
    # prefer llama-completion, and only a binary that PROVES it runs here —
    # a name match isn't enough (the top-level CUDA builds taught us that).
    llama = next((p for _, p in sorted(candidates) if runnable(p)), None)
    if llama is None:
        return None
    return {'llama': llama, 'model': max(ggufs)[1]}


def classroom_command(config_path: str = None, roots=None) -> list | None:
    """The argv the Academy tab spawns for a live Professor, or None (stay
    professor-not-present). Priority: bonsai.json (enabled + valid paths) →
    auto-discovery. Pure decision; the tab just wires what this returns."""
    cfg = load_config(config_path)
    if cfg is not None:
        if not cfg.get('enabled', True):
            return None                       # the OFF switch
        llama, model = cfg.get('llama'), cfg.get('model')
        if llama and model and os.path.exists(llama) and os.path.exists(model):
            argv = [sys.executable, os.path.abspath(__file__),
                    '--llama', llama, '--model', model]
            for key, flag in (('n_predict', '--n-predict'),
                              ('threads', '--threads'), ('ctx', '--ctx')):
                if cfg.get(key):
                    argv += [flag, str(cfg[key])]
            return argv
        # config present but paths broken → fall through to discovery
    found = discover(roots)
    if found is None:
        return None
    return [sys.executable, os.path.abspath(__file__),
            '--llama', found['llama'], '--model', found['model']]


# ═══════════════════════════════════════════════════════════════════════════
# The serve loop (one Contract v1 response per request line)
# ═══════════════════════════════════════════════════════════════════════════

def handle_line(line: str, backend) -> str | None:
    """One request line -> one response line (JSON + newline), or None if the
    line is malformed (logged to stderr, never crashes the runner)."""
    line = line.strip()
    if not line:
        return None
    try:
        req = json.loads(line)
        if not isinstance(req, dict) or 'text' not in req:
            raise ValueError('not a Contract v1 request')
    except (ValueError, TypeError) as e:
        sys.stderr.write(f"[bonsai_runner] dropped malformed request: {e}\n")
        return None
    try:
        text = backend.generate(build_prompt(req))
    except BackendError as e:
        return json.dumps({'backend_error': str(e)}) + '\n'
    except subprocess.TimeoutExpired as e:
        return json.dumps({'backend_error':
                           f'professor timed out after {e.timeout:.0f}s '
                           f'(the X550LA thinks slowly — raise ask_timeout '
                           f'in bonsai.json if he needed longer)'}) + '\n'
    except OSError as e:
        return json.dumps({'backend_error': f'could not run llama: {e}'}) + '\n'
    return json.dumps(build_response(text, req)) + '\n'


def serve(stdin, stdout, backend) -> None:
    for line in stdin:
        out = handle_line(line, backend)
        if out is not None:
            stdout.write(out)
            stdout.flush()


def _opt(argv, flag):
    return argv[argv.index(flag) + 1] if flag in argv else None


def _make_backend(argv) -> object:
    if '--mock' in argv:
        return EchoBackend()
    llama = _opt(argv, '--llama')
    model = _opt(argv, '--model')
    if not (llama and model):
        found = discover()
        if found:
            llama, model = llama or found['llama'], model or found['model']
    if not (llama and model):
        sys.stderr.write("[bonsai_runner] no llama binary/model found; "
                         "falling back to --mock\n")
        return EchoBackend()
    n_predict = int(_opt(argv, '--n-predict') or 128)
    threads = int(_opt(argv, '--threads') or 2)
    ctx = int(_opt(argv, '--ctx') or 1024)
    return LlamaBackend(llama, model, n_predict, threads, ctx)


def ask_timeout(config_path: str = None) -> float:
    """How long the tab waits for one live answer. The classroom's old 120s
    was a fantasy at 0.3 tok/s — default 2400s, tunable in bonsai.json."""
    cfg = load_config(config_path) or {}
    try:
        return float(cfg.get('ask_timeout', 2400))
    except (TypeError, ValueError):
        return 2400.0


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    serve(sys.stdin, sys.stdout, _make_backend(argv))


if __name__ == '__main__':
    main()
