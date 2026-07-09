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

# ── the room check (the frozen-mouse lesson, 2026-07-10) ────────────────────
# An 8B whose weights don't fit in FREE RAM doesn't fail — it thrashes the
# page cache and freezes the whole desktop. -c/-t/--prio can't cap the
# weights themselves, so the professor CHECKS THE ROOM before entering and
# refuses honestly if he won't fit (the humility gate, applied to memory).

MEM_HEADROOM_MB = 800          # beyond the model file: KV/compute + slack


def mem_available_mb():
    """MemAvailable from /proc/meminfo, in MB. None if unreadable (non-Linux)."""
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                if line.startswith('MemAvailable:'):
                    return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return None


def mem_guard(model_path: str, min_free_mb=None, draft_path=None):
    """None if it's safe to wake the professor, else the honest refusal
    message (with the real numbers, so the captain knows what to close).
    A draft model (the intern) adds its own residency to the bill."""
    avail = mem_available_mb()
    if avail is None:
        return None                        # can't tell — proceed
    if min_free_mb is None:
        try:
            model_mb = os.path.getsize(model_path) // (1024 * 1024)
        except OSError:
            model_mb = 2300                # the 8B's ballpark
        if draft_path:
            try:
                model_mb += os.path.getsize(draft_path) // (1024 * 1024)
            except OSError:
                model_mb += 450            # small-draft ballpark
        min_free_mb = model_mb + MEM_HEADROOM_MB
    if avail < min_free_mb:
        return (f'professor needs ~{min_free_mb} MB free to think safely; '
                f'only {avail} MB available right now — close something '
                f'heavy (browser? video?) and ask again')
    return None


# ── the intern (speculative decoding — EXPERIMENTAL until measured) ─────────
# DSpark at laptop scale: a small same-family draft model proposes tokens,
# Bonsai verifies them in one batch. On CPU the win is memory bandwidth —
# verifying k drafted tokens reads the 2.2GB of weights ONCE instead of k
# times. Lossless by construction: the boss model has the final say.
# llama-completion has no local -md flag, so the drafted path runs the
# SIBLING binary llama-speculative — which has no -st chat mode, so we
# hand-roll Qwen3's documented chat template (the identity-crisis fix must
# not regress) and strip the prompt echo ourselves.

ASSISTANT_MARK = '<|im_start|>assistant\n'


def speculative_binary(llama_path: str) -> str:
    """llama-speculative living beside the configured llama binary."""
    return os.path.join(os.path.dirname(llama_path), 'llama-speculative')


def qwen3_prompt(system: str, user: str) -> str:
    """Qwen3's chat template, hand-rolled for the non-conversational
    speculative binary. Deterministic text; format per Qwen3's public spec."""
    return (f'<|im_start|>system\n{system}<|im_end|>\n'
            f'<|im_start|>user\n{user}<|im_end|>\n'
            + ASSISTANT_MARK)


def extract_drafted_reply(stdout: str) -> str:
    """llama-speculative can't suppress the prompt echo — take everything
    after the LAST assistant marker if echoed, and cut at the end-of-turn."""
    if ASSISTANT_MARK in stdout:
        stdout = stdout.rsplit(ASSISTANT_MARK, 1)[1]
    return stdout.split('<|im_end|>')[0]


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
                 threads: int = 2, ctx: int = 1024, timeout: float = 2400.0,
                 min_free_mb=None, draft_model=None, draft_max: int = 12):
        self.llama, self.model = llama, model
        self.n_predict, self.threads, self.ctx = n_predict, threads, ctx
        self.timeout = timeout
        self.min_free_mb = min_free_mb     # None = auto (model size + headroom)
        self.draft_model = draft_model     # the intern (None = classic path)
        self.draft_max = draft_max

    def argv(self, prompt: str) -> list:
        # Memory/desktop kindness (the hard-reboot lesson, 2026-07-09): the
        # X550LA has ~7.6GB shared with FlowCode + Claude Desktop. So: -c caps
        # the KV cache (the default takes the model's full context and can eat
        # hundreds of MB); -t 2 leaves cores for the mouse; --prio -1 makes
        # the professor the lowest-priority process on the box.
        #
        caps = ['-n', str(self.n_predict), '--temp', '0.2',
                '-c', str(self.ctx), '-t', str(self.threads),
                '--prio', '-1']
        if self.draft_model:
            # drafted path: the sibling llama-speculative (no -st chat mode,
            # no prompt suppression) — hand-rolled Qwen3 template + echo strip
            # keep the identity-crisis fix intact. Flags verified against the
            # binary's --help on this machine (2026-07-10).
            return ([speculative_binary(self.llama), '-m', self.model,
                     '-md', self.draft_model,
                     '--draft-max', str(self.draft_max), '--draft-min', '2',
                     '-p', qwen3_prompt(SYSTEM_PROMPT, prompt)] + caps)
        # -st single-turn chat + -sys persona (the identity-crisis fix): the
        # gguf's chat template assigns the roles, exactly as Stevo's own
        # interview script ran it. One turn, then the process exits.
        return ([self.llama, '-m', self.model,
                 '-sys', SYSTEM_PROMPT, '-p', prompt, '-st',
                 '--no-display-prompt'] + caps)

    def generate(self, prompt: str) -> str:
        """The model's text, or raises BackendError with the REAL reason —
        an empty answer must never ship as silence (screen-truth lesson:
        the CUDA-less binary died fast and the board showed a mute professor)."""
        refusal = mem_guard(self.model, self.min_free_mb, self.draft_model)
        if refusal:
            raise BackendError(refusal)    # refuse > thrash the whole desktop
        r = subprocess.run(self.argv(prompt), capture_output=True, text=True,
                           timeout=self.timeout)
        out = extract_drafted_reply(r.stdout) if self.draft_model else r.stdout
        text = clean_reply(out)
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
                              ('threads', '--threads'), ('ctx', '--ctx'),
                              ('min_free_mb', '--min-free-mb'),
                              ('draft_max', '--draft-max')):
                if cfg.get(key):
                    argv += [flag, str(cfg[key])]
            # the intern rides only if its file is really there
            draft = cfg.get('draft_model')
            if draft and os.path.exists(draft):
                argv += ['--draft-model', draft]
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
    min_free = _opt(argv, '--min-free-mb')
    return LlamaBackend(llama, model, n_predict, threads, ctx,
                        min_free_mb=int(min_free) if min_free else None,
                        draft_model=_opt(argv, '--draft-model'),
                        draft_max=int(_opt(argv, '--draft-max') or 12))


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
