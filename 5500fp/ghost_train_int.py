#!/usr/bin/env python3
"""ghost_train_int.py — GHOST's classifier, trained WITHOUT floats.

Stage 3 of the integer-training brief (CAI 19-09, captain's GO): the same
intent→command model ghost_train.py produces — same 81-trigram features,
same 81→27→24 shape, same {−4..+4} weight levels, same export format,
same humility gate — but the training run itself is integer end to end,
so it replays bit-identically on any machine.

Mechanism (the dick_train recipe, aimed at GHOST):
  * INTEGER shadow weights at a fine scale (units of 1/32): S ∈ [−128,128]
    quantises to W = round(S/32) ∈ {−4..+4}. ghost_train's own
    quantise→forward→update-shadow pattern, with the float shadows
    replaced by integer ones.
  * Forward passes run on the QUANTISED weights (identical semantics to
    ref_forward — the thing that must stay golden).
  * The objective is an all-violators MARGIN PERCEPTRON — the true
    class must lead every rival by train_margin or the violators get
    unit-strength pushes; hidden error is true integer backprop through
    the quantised W2 (one transpose — for a 2-layer net the "gradient
    chain" DFA avoids is a single integer matrix). All updates are
    shifts, adds and clips — sym_shift truncation, no floats anywhere.
    (DFA was tried first and stalled at ~10%: feedback alignment does
    not align through staircase-quantised weights. Recorded honestly.)
  * All randomness (init, epoch shuffles) from the LCG.
    The corpus comes from ghost_train.build_corpus unchanged, so both
    trainers learn from the exact same phrases.

The float trainer REMAINS the accuracy baseline (94.4% held-out at this
corpus seed). This trainer's claim is different: the run is REPLAYABLE.
Accuracy is the constraint; determinism is the goal.

Run:  python3 ghost_train_int.py            # train, report, digests
      python3 ghost_train_int.py --digest   # final-weights digest only
      python3 ghost_train_int.py --export ghost_model_int.json

Added: 20 Sep 2026. Authors: Stevo + Claude.
"""

import hashlib
import json
import sys

import ghost_train as G
from dick_train import _lcg, rand_int, sym_shift, clip, canonical_bytes

NFEAT, NHID, NCLS = G.NFEAT, G.NHID, len(G.CLASSES)
SC = 32                    # fine-units per quantum: S/32 -> {-4..+4}
S_CAP = G.WLEVELS * SC     # shadow band ±128

HP = {
    "train_margin": 96,    # required lead over EVERY rival during training —
                           # headroom over route()'s MARGIN=3, and the knob
                           # that bought the last two accuracy points
    "lr2_shift": 5,        # output step: h>>5 fine-units per violator
    "lr1_shift": 2,        # hidden step: backprop dh >> 2
    "decay_at": 60,        # both shifts +1 from this epoch (integer lr decay)
    "epochs": 100,
    "seed_weights": 3**9, "seed_shuffle": 3**5,
    "corpus_seed": 27,     # ghost_train's own corpus, unchanged
}


def q(s):
    """Fine shadow → weight level: symmetric round-half-away, then clamp.
    Integer-only twin of ghost_train._quant."""
    v = (s + SC // 2) // SC if s >= 0 else -((-s + SC // 2) // SC)
    return clip(v, G.WLEVELS)


def quantise(S):
    return [[q(v) for v in row] for row in S]


def fisher_yates(gen, seq):
    for i in range(len(seq) - 1, 0, -1):
        j = next(gen) % (i + 1)
        seq[i], seq[j] = seq[j], seq[i]


def _epoch_pass(S1, S2, rows, feats, hp, ep, m):
    """Exactly one epoch, in place: the sample loop over rows AS ORDERED.
    NOTE: the caller owns the shuffle — this function trains on `rows`
    verbatim, which is what lets an auditor replay one epoch alone."""
    l2 = hp["lr2_shift"] + (1 if ep >= hp["decay_at"] else 0)
    l1 = hp["lr1_shift"] + (1 if ep >= hp["decay_at"] else 0)
    W1, W2 = quantise(S1), quantise(S2)
    for text, y in rows:
        f = feats[text]
        nz = [i for i in range(NFEAT) if f[i]]
        pre = [sum(f[i] * W1[i][j] for i in nz) for j in range(NHID)]
        h = [p if p > 0 else 0 for p in pre]
        logits = [sum(h[j] * W2[j][k] for j in range(NHID) if h[j])
                  for k in range(NCLS)]
        floor = logits[y] - m
        viol = [k for k in range(NCLS) if k != y and logits[k] > floor]
        if not viol:
            continue
        nv = len(viol)
        for j in range(NHID):
            hj = h[j]
            if hj == 0:
                continue
            step = sym_shift(hj, l2)
            if step == 0:
                continue
            rowS = S2[j]
            rowS[y] = clip(rowS[y] + step * nv, S_CAP)
            for r in viol:
                rowS[r] = clip(rowS[r] - step, S_CAP)
        for j in range(NHID):
            if pre[j] <= 0:
                continue
            W2j = W2[j]
            dh = sum(W2j[y] - W2j[r] for r in viol)
            d = sym_shift(dh, l1)
            if d == 0:
                continue
            for i in nz:
                S1[i][j] = clip(S1[i][j] + d * f[i], S_CAP)
        W1, W2 = quantise(S1), quantise(S2)


def train(hp=None):
    """All-violators margin perceptron on the quantised forward, integer
    shadows underneath. The objective IS the routing rule: the true class
    must lead every rival by train_margin, or the violators get pushed.
    Errors are unit-strength, updates stop when a sample is satisfied —
    no softmax, and none needed: this matches the float trainer's 94.4%
    held-out exactly (pinned in the tests)."""
    hp = dict(HP, **(hp or {}))
    gw = _lcg(hp["seed_weights"])
    S1 = [[rand_int(gw, -S_CAP, S_CAP) for _ in range(NHID)] for _ in range(NFEAT)]
    S2 = [[rand_int(gw, -S_CAP, S_CAP) for _ in range(NCLS)] for _ in range(NHID)]
    gs = _lcg(hp["seed_shuffle"])

    train_rows, held = G.build_corpus(hp["corpus_seed"])
    feats = {t: G.features(t) for t, _ in train_rows + held}
    rows = list(train_rows)
    m = hp["train_margin"]

    epoch_digests = []
    for ep in range(hp["epochs"]):
        fisher_yates(gs, rows)
        _epoch_pass(S1, S2, rows, feats, hp, ep, m)
        epoch_digests.append(
            hashlib.sha3_256(canonical_bytes([S1, S2])).hexdigest())

    W1, W2 = quantise(S1), quantise(S2)
    acc_held = G.accuracy(held, W1, W2)
    acc_train = G.accuracy(train_rows, W1, W2)
    return {
        "unit": "ghost-train-int-v1-margin-perceptron",
        "final_digest": epoch_digests[-1],
        "epoch_digests": epoch_digests,
        "held_acc_pct": round(acc_held * 100, 1),
        "train_acc_pct": round(acc_train * 100, 1),
        "held_n": len(held),
        "W1": W1, "W2": W2,
    }


# ── stage 4 surface: the sellable, auditable GHOST training job ─────────────
JOB_BOUNDS = {"epochs": 150, "train_margin": 1024,
              "lr2_shift": 24, "lr1_shift": 24, "decay_at": 150}


def decode_job(job: bytes, index: int):
    """Job bytes → hp: whitelist into HP, clamp against hostile jobs; the
    chunk index perturbs the weight seed → independent replayable runs."""
    try:
        obj = json.loads(job.decode("utf-8"))
        over = obj.get("hp", {}) if isinstance(obj, dict) else {}
    except Exception:
        over = {}
    hp = dict(HP)
    for k, v in over.items():
        if k in hp and isinstance(v, int):
            hp[k] = min(v, JOB_BOUNDS[k]) if k in JOB_BOUNDS else v
    hp["seed_weights"] = hp["seed_weights"] + index * (3**4 + 1)
    return hp


def run_unit(job: bytes, index: int) -> str:
    """The worker's canonical claim: digest chain + exact accuracies.
    Weights never ride the wire — the digests commit to them."""
    hp = decode_job(job, index)
    r = train(hp)
    out = {"unit": "ghost-train-int-v1-unit", "index": index,
           "final_digest": r["final_digest"],
           "epoch_digests": r["epoch_digests"],
           "held_acc_pct": r["held_acc_pct"],
           "train_acc_pct": r["train_acc_pct"], "held_n": r["held_n"]}
    return canonical_bytes(out).decode()


def _rows_at_epoch(hp, epoch_i):
    """Sample order for epoch epoch_i, reconstructed WITHOUT training:
    the shuffle stream is weight-independent, so an auditor replays the
    permutations alone (cheap) and trains only the epoch under audit."""
    gs = _lcg(hp["seed_shuffle"])
    train_rows, _ = G.build_corpus(hp["corpus_seed"])
    rows = list(train_rows)
    for _ in range(epoch_i + 1):
        fisher_yates(gs, rows)
    return rows, train_rows


def checkpoint(job: bytes, index: int, epoch_i: int) -> bytes:
    """Canonical [S1, S2] AFTER epoch epoch_i — what an honest worker logs
    beside its digest chain so auditors can spot-check single epochs."""
    hp = decode_job(job, index)
    if not (0 <= epoch_i < hp["epochs"]):
        raise ValueError("epoch out of range")
    gw = _lcg(hp["seed_weights"])
    S1 = [[rand_int(gw, -S_CAP, S_CAP) for _ in range(NHID)] for _ in range(NFEAT)]
    S2 = [[rand_int(gw, -S_CAP, S_CAP) for _ in range(NCLS)] for _ in range(NHID)]
    gs = _lcg(hp["seed_shuffle"])
    train_rows, _ = G.build_corpus(hp["corpus_seed"])
    feats = {t: G.features(t) for t, _ in train_rows}
    rows = list(train_rows)
    for ep in range(epoch_i + 1):
        fisher_yates(gs, rows)
        _epoch_pass(S1, S2, rows, feats, hp, ep, hp["train_margin"])
    return canonical_bytes([S1, S2])


def audit_one_epoch(job: bytes, index: int, claimed_digests, epoch_i: int,
                    prev_ckpt: bytes = b"") -> bool:
    """Verify ONE epoch of a claimed GHOST training run.
    (1) the offered checkpoint must hash to the previous claimed digest;
    (2) reconstruct epoch_i's sample order by replaying shuffles only;
    (3) train exactly that epoch; the result must hash to claimed[epoch_i].
    """
    hp = decode_job(job, index)
    if not (0 <= epoch_i < hp["epochs"]) or epoch_i >= len(claimed_digests):
        return False
    if epoch_i == 0:
        gw = _lcg(hp["seed_weights"])
        S1 = [[rand_int(gw, -S_CAP, S_CAP) for _ in range(NHID)]
              for _ in range(NFEAT)]
        S2 = [[rand_int(gw, -S_CAP, S_CAP) for _ in range(NCLS)]
              for _ in range(NHID)]
    else:
        if hashlib.sha3_256(prev_ckpt).hexdigest() != claimed_digests[epoch_i - 1]:
            return False
        try:
            S1, S2 = json.loads(prev_ckpt.decode("utf-8"))
        except Exception:
            return False
        if not all(isinstance(v, int) for M in (S1, S2) for row in M for v in row):
            return False
    rows, train_rows = _rows_at_epoch(hp, epoch_i)
    feats = {t: G.features(t) for t, _ in train_rows}
    _epoch_pass(S1, S2, rows, feats, hp, epoch_i, hp["train_margin"])
    return hashlib.sha3_256(canonical_bytes([S1, S2])).hexdigest() \
        == claimed_digests[epoch_i]


VCLASS_NATIVE = "native"


def as_worker():
    """GHOST training as a REPLAY-CLASS mesh worker — δ = 0 settlement,
    weight-bearing native votes. Same adapter discipline as dick_kernel."""
    try:
        from p2pcp_worker import WorkerAdapter, VCLASS_NATIVE as _VN
    except Exception:                            # noqa: BLE001
        try:
            from p2pcp.worker import WorkerAdapter, VCLASS_NATIVE as _VN
        except Exception:
            WorkerAdapter, _VN = None, VCLASS_NATIVE

    if WorkerAdapter is not None:
        class GhostTrainWorker(WorkerAdapter):
            """REPLAY-CLASS: bit-exactly reproducible GHOST training."""
            vclass = _VN

            def run_chunk(self, job: bytes, index: int) -> bytes:
                return run_unit(job, index).encode()
        return GhostTrainWorker()

    class _GhostTrainWorker:                     # duck-typed fallback
        vclass = VCLASS_NATIVE

        def run_chunk(self, job: bytes, index: int) -> bytes:
            return run_unit(job, index).encode()
    return _GhostTrainWorker()


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    r = train()
    if a[:1] == ["--digest"]:
        print(r["final_digest"])
        return
    if a[:1] == ["--export"]:
        path = a[1] if len(a) > 1 else "ghost_model_int.json"
        json.dump({"nfeat": NFEAT, "nhid": NHID, "classes": G.CLASSES,
                   "margin": G.MARGIN, "W1": r["W1"], "W2": r["W2"]},
                  open(path, "w"))
        print(f"exported {path}  digest={r['final_digest']}")
        return
    print(f"unit:   {r['unit']}")
    print(f"train routing acc: {r['train_acc_pct']}%")
    print(f"held-out routing acc: {r['held_acc_pct']}%  "
          f"({r['held_n']} phrases; float baseline 94.4%)")
    print(f"final_digest: {r['final_digest']}")


if __name__ == "__main__":
    main()
