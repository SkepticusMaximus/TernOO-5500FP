"""p2pcp_ghost.py — GHOST as a REPLAY-CLASS mesh worker (the flagship).

GHOST's native ternary classifier (81→27 MLP, golden-tested bit-exact between the
5500FP emulator and its host reference) sells classification on the mesh. Because
it is DETERMINISTIC integer inference, it is REPLAY-class (§3): any peer replays it
and compares bit-for-bit, so a forger cannot survive audit — and it earns
WEIGHT-BEARING credit (a VOTE, §10), not just money. That is the two-mind pair,
both on the mesh: GHOST earns votes with verifiable native work; the Professor
(float Bonsai) earns rent. The determinism moat, made economic.

The forward pass is the host reference (`ghost_train.ref_forward`) — bit-exactly
equal to the native emulator pass, and 0.2 ms, so it needs no model training and
no emulator binary at call time.

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import json
import os
import subprocess
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WK = _load("p2pcp_worker")
G = _load("ghost_train")
GEN = _load("gen_ghost_t5asm")

MODEL_FILE = os.path.join(_HERE, "ghost_model.json")

# The C emulator binary — the same one test_ghost.py holds golden against
# ref_forward. When present, GHOST's mesh work can run on REAL native ternary
# execution instead of the host reference (both are bit-exact, so replay-audit
# is backend-blind: a host auditor verifies a native worker and vice versa).
EMULATOR_BIN = os.path.join(_HERE, "..", "NASM-TernOO-5500FP-Emulator",
                            "c_emulator", "5500fp")
_PROBE = "make this loud"   # one-shot startup self-check text


def load_model(path=None):
    """Load a trained GHOST model {nfeat, nhid, classes, margin, W1, W2}."""
    with open(path or MODEL_FILE) as f:
        return json.load(f)


def classify(model, text: str):
    """(class_name, margin) via the host reference forward pass — deterministic
    and bit-exactly equal to the native emulator pass (§3). Mirrors the harness's
    `_route_host`: honour the model's own class list + the humility margin gate."""
    saved = G.CLASSES
    try:
        G.CLASSES = model["classes"]
        cls_idx, margin, _scores = G.ref_forward(text, model["W1"], model["W2"])
    finally:
        G.CLASSES = saved
    cls = model["classes"][cls_idx]
    if cls == "none" or margin < model["margin"]:
        return "none", margin
    return cls, margin


def native_available() -> bool:
    """True when the C emulator binary exists and is executable."""
    return os.path.isfile(EMULATOR_BIN) and os.access(EMULATOR_BIN, os.X_OK)


def classify_native(model, text: str):
    """(class_name, margin) via the C emulator executing the emitted t5asm —
    trigram hashing, both MAC layers, ReLU and argmax all run as native ternary
    words, no host-side inference. Must equal ``classify`` bit-for-bit
    (test_ghost.py's golden law; re-checked per worker at startup)."""
    asm = GEN.emit_forward(text, model)
    with tempfile.NamedTemporaryFile("w", suffix=".t5asm", delete=False) as f:
        f.write(asm)
        path = f.name
    try:
        out = subprocess.run([EMULATOR_BIN, "--run", path], capture_output=True,
                             text=True, timeout=60).stdout
    finally:
        os.unlink(path)
    nums = [int(l) for l in out.splitlines()
            if l.strip().lstrip("-").isdigit()]
    cls_idx, margin = nums[0], nums[1]
    cls = model["classes"][cls_idx]
    if cls == "none" or margin < model["margin"]:
        return "none", margin
    return cls, margin


class GhostWorker(WK.WorkerAdapter):
    """GHOST as a float-free, replay-class P2PCP worker. ``model`` is a loaded
    GHOST model dict; the default loads the shipped ghost_model.json.

    ``backend``: "auto" (default) sells native C-emulator execution when the
    binary is present AND agrees with ref_forward on a probe, else the host
    reference; "native" demands the emulator (raises if absent/divergent);
    "host" forces the reference. Outputs are bit-identical either way, so
    mixed-backend replay audits settle normally."""

    vclass = WK.VCLASS_NATIVE     # deterministic integer → replay, weight-bearing

    def __init__(self, model=None, model_path=None, backend="auto"):
        self._model = model if model is not None else load_model(model_path)
        self._classify = self._resolve_backend(backend)

    def _resolve_backend(self, backend):
        if backend == "host":
            return classify
        if backend in ("native", "auto") and native_available():
            try:
                probe_ok = (classify_native(self._model, _PROBE)
                            == classify(self._model, _PROBE))
            except Exception:
                probe_ok = False
            if probe_ok:
                return classify_native
        if backend == "native":
            raise RuntimeError(
                "backend='native': C emulator missing, not executable, or "
                "divergent from ref_forward on the probe — refusing to sell "
                "unverified native work")
        return classify

    @property
    def backend(self) -> str:
        """Which engine this worker sells: 'native' (C emulator) or 'host'."""
        return "native" if self._classify is classify_native else "host"

    def run_chunk(self, job: bytes, index: int) -> bytes:
        """Classify the job text. Deterministic, so any peer can replay-audit it
        and a forged answer never survives (§3/§7). Output = ``class\\tmargin``."""
        text = job.decode("utf-8", "replace")
        cls, margin = self._classify(self._model, text)
        return f"{cls}\t{margin}".encode("utf-8")
