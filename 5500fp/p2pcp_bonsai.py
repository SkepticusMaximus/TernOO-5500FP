"""p2pcp_bonsai.py — the Professor as a mesh worker (the payoff loop).

Wires bonsai_runner (Bonsai = ternarized qwen3-8B under llama.cpp, the Academy's
Professor) behind the P2PCP WorkerAdapter interface, so the Professor can SELL
inference on the mesh for CompuToken — the answer to "Bonsai is starving for
compute". It is FLOAT-class (llama.cpp accumulates in float, §3): the output is
quorum-verified, earns money, and is NEVER weight-bearing (§10). The Professor
gets paid; it never gets a vote.

A P2PCP job is a prompt (UTF-8 bytes); the reply is the output (UTF-8 bytes).
Bonsai is single-shot, so one Professor job is one chunk (use n_chunks=1). Inject
a backend for tests (bonsai_runner.EchoBackend); production auto-discovers the real
LlamaBackend and degrades gracefully to the echo mock if no model is present (the
mute-professor lesson: a present-but-mock professor beats a crash).

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import os

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WK = _load("p2pcp_worker")


def professor_backend(config_path=None):
    """Assemble the real Professor backend from bonsai.json + auto-discovery,
    exactly as the classroom does. Degrades to EchoBackend (a present-but-mock
    professor) if no runnable model is found — so a node without the 2.2 GB model
    still speaks the contract rather than crashing."""
    B = _load("bonsai_runner")
    cfg = B.load_config(config_path) or {}
    llama, model = cfg.get("llama"), cfg.get("model")
    if not (llama and model):
        found = B.discover()
        if found:
            llama = llama or found["llama"]
            model = model or found["model"]
    if not (llama and model and B.runnable(llama)):
        return B.EchoBackend()
    return B.LlamaBackend(
        llama, model,
        n_predict=int(cfg.get("n_predict", 128)),
        threads=int(cfg.get("threads", 2)),
        ctx=int(cfg.get("ctx", 1024)),
        timeout=float(cfg.get("ask_timeout", 2400)),
        min_free_mb=cfg.get("min_free_mb"),
        draft_model=cfg.get("draft_model"),
        fmt=cfg.get("format", "qwen3"),
    )


class BonsaiWorker(WK.WorkerAdapter):
    """The Professor as a float-class P2PCP worker. ``backend`` is any object with
    ``generate(prompt: str) -> str``; the default is the auto-discovered Professor."""

    vclass = WK.VCLASS_FLOAT      # llama.cpp = float accumulation → quorum, not replay

    def __init__(self, backend=None, config_path=None):
        self._backend = (backend if backend is not None
                         else professor_backend(config_path))

    def run_chunk(self, job: bytes, index: int) -> bytes:
        """One job = one inference (Bonsai is single-shot; use n_chunks=1). The
        job bytes are the prompt; the reply bytes are the output."""
        prompt = job.decode("utf-8", "replace")
        reply = self._backend.generate(prompt)
        return str(reply).encode("utf-8")
