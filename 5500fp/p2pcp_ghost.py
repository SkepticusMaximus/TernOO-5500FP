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

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


WK = _load("p2pcp_worker")
G = _load("ghost_train")

MODEL_FILE = os.path.join(_HERE, "ghost_model.json")


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


class GhostWorker(WK.WorkerAdapter):
    """GHOST as a float-free, replay-class P2PCP worker. ``model`` is a loaded
    GHOST model dict; the default loads the shipped ghost_model.json."""

    vclass = WK.VCLASS_NATIVE     # deterministic integer → replay, weight-bearing

    def __init__(self, model=None, model_path=None):
        self._model = model if model is not None else load_model(model_path)

    def run_chunk(self, job: bytes, index: int) -> bytes:
        """Classify the job text. Deterministic, so any peer can replay-audit it
        and a forged answer never survives (§3/§7). Output = ``class\\tmargin``."""
        text = job.decode("utf-8", "replace")
        cls, margin = classify(self._model, text)
        return f"{cls}\t{margin}".encode("utf-8")
