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
        l2 = hp["lr2_shift"] + (1 if ep >= hp["decay_at"] else 0)
        l1 = hp["lr1_shift"] + (1 if ep >= hp["decay_at"] else 0)
        fisher_yates(gs, rows)
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
