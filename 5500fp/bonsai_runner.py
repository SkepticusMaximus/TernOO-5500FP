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

Wiring: point the harness at it —
    BONSAI_CMD="python3 bonsai_runner.py --llama '<your llama.cpp command>'"
    (or --mock for a binary-less classroom / the tests).

Backends:
  * LlamaBackend — shells to a local llama.cpp runner over the .gguf. Stevo
    owns the exact command + prompt format for the real model (flagged).
  * EchoBackend — a deterministic mock (tests + no-binary fallback).

Date: 2026-07-09, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

CONTRACT_VERSION = 1


# ═══════════════════════════════════════════════════════════════════════════
# Contract v1 shaping (pure — pinned in tests, and cross-checked by ghost_bonsai)
# ═══════════════════════════════════════════════════════════════════════════

def build_prompt(req: dict) -> str:
    """Compose the model prompt from a Contract v1 request. GHOST delegates
    only what it couldn't answer, so we frame it as an honest ask. The exact
    template is Stevo's to tune against the real model (flagged)."""
    text = req.get('text', '')
    return ("You are Bonsai, a local assistant consulted by GHOST when a "
            "question is beyond GHOST's own competence. Answer plainly and "
            "honestly; if you do not know, say so.\n\n"
            f"Question: {text}\nAnswer:")


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

class EchoBackend:
    """Deterministic mock — no model. Lets the classroom and the tests run a
    full contract round-trip with a present-but-fake professor."""

    def generate(self, prompt: str) -> str:
        q = prompt.rsplit('Question:', 1)[-1].split('\nAnswer:', 1)[0].strip()
        return f"(echo professor) I would say something about: {q}"


class LlamaBackend:
    """Shells to a local llama.cpp runner over the .gguf. `cmd` is the token
    list; a '{PROMPT}' token is substituted with the prompt, else the prompt
    is appended as the final argument. Stevo sets the exact command."""

    def __init__(self, cmd, timeout: float = 300.0):
        self.cmd = list(cmd)
        self.timeout = timeout

    def generate(self, prompt: str) -> str:
        if '{PROMPT}' in self.cmd:
            argv = [a.replace('{PROMPT}', prompt) for a in self.cmd]
        else:
            argv = self.cmd + [prompt]
        r = subprocess.run(argv, capture_output=True, text=True,
                           timeout=self.timeout)
        return r.stdout.strip()


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
    text = backend.generate(build_prompt(req))
    return json.dumps(build_response(text, req)) + '\n'


def serve(stdin, stdout, backend) -> None:
    for line in stdin:
        out = handle_line(line, backend)
        if out is not None:
            stdout.write(out)
            stdout.flush()


def _make_backend(argv) -> object:
    if '--mock' in argv:
        return EchoBackend()
    llama = None
    if '--llama' in argv:
        llama = argv[argv.index('--llama') + 1]
    else:
        llama = os.environ.get('BONSAI_LLAMA')
    if not llama:
        sys.stderr.write("[bonsai_runner] no --llama command and no "
                         "BONSAI_LLAMA env; falling back to --mock\n")
        return EchoBackend()
    return LlamaBackend(llama.split())


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    serve(sys.stdin, sys.stdout, _make_backend(argv))


if __name__ == '__main__':
    main()
