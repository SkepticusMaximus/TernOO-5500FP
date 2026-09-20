"""dick_train.py — DICK v0.3: the kernel LEARNS, in integers, deterministically.

Stage 1 of the integer-training brief (CAI → CC, 19-09-2026; captain's GO
19-09 21:18 ACST): a training loop in which weights, activations, errors,
pseudo-gradients, and updates are ALL integers, so the same run replayed on
any machine yields bit-identical weights. The float trainer
(ghost_train.py) is untouched — it remains the accuracy baseline.

The backward road is DIRECT FEEDBACK ALIGNMENT (PocketNN, Song & Lin 2022,
arXiv:2201.02863): the output error is broadcast straight to the hidden
layer through a FIXED random ternary matrix instead of back through the
weight chain. No transposes, no softmax, no chain of float-fragile
gradients — the shortest road to integer purity at GHOST's scale.

Determinism rules (same spirit as dick_kernel):
  - all randomness from one LCG, seeded by the job;
  - divisions are TRUNCATING toward zero (sym_shift) — Python's ``>>``
    floors, which biases negative gradients into a permanent -1 drift;
    truncation gives a symmetric dead-zone instead, and is bit-identical
    everywhere;
  - ties in argmax resolve to the lowest index;
  - weights clip to a fixed band so no run ever leaves int range.

Audit surface: the trainer emits a PER-EPOCH digest chain (sha3-256 over
canonical weight bytes) — the training-time analog of dick_kernel's
per-layer digests. Replay any prefix of epochs and compare seals.

Run:  python3 dick_train.py --selftest     # train the toy, print acc + digest
      python3 dick_train.py --digest       # final-weights digest only (for pins)

Added: 19 Sep 2026. Authors: Stevo + Claude.
"""

import hashlib
import json
import sys

# ── deterministic primitives ─────────────────────────────────────────────────
LCG_M = 2**63 - 25
LCG_A = 6364136223846793005
LCG_C = 1442695040888963407


def _lcg(seed):
    s = seed % LCG_M
    while True:
        s = (LCG_A * s + LCG_C) % LCG_M
        yield s


def rand_int(gen, lo, hi):
    """Uniform int in [lo, hi] from the LCG stream."""
    return lo + next(gen) % (hi - lo + 1)


def sym_shift(v, s):
    """Truncate-toward-zero shift: symmetric dead-zone for small values.
    Python's >> floors (-1 >> 4 == -1), which turns every tiny negative
    gradient into a full -1 update — a permanent drift. This doesn't."""
    return -((-v) >> s) if v < 0 else v >> s


def clip(v, cap):
    return -cap if v < -cap else cap if v > cap else v


def imatmul(W, x):
    """Integer matrix @ vector — adds and multiplies only."""
    return [sum(w * xi for w, xi in zip(row, x)) for row in W]


def argmax_low(v):
    """Argmax, ties to the LOWEST index — deterministic everywhere."""
    best, bi = v[0], 0
    for i, val in enumerate(v):
        if val > best:
            best, bi = val, i
    return bi


def canonical_bytes(obj):
    return json.dumps(obj, separators=(",", ":"), sort_keys=True).encode()


def weights_digest(Ws):
    return hashlib.sha3_256(canonical_bytes(Ws)).hexdigest()


# ── hyperparameters (all fixed; part of the job identity) ───────────────────
HP = {
    "n_in": 27, "n_hid": 27, "n_out": 9,
    "w_init": 8,          # weights init uniform in [-8, 8]
    "w_cap": 127,         # weight band — int8-shaped on purpose
    "a_shift": 3,         # hidden activation: sym_shift(z, 3) then clip
    "a_cap": 63,          # hidden activation cap
    "o_shift": 7,         # loss sees o >> 7: single weight steps regain
                          # sub-unit authority over the compared logits —
                          # without this the output scale wars with the
                          # targets and training is bang-bang chaos
    "t_hi": 100, "t_lo": -100,  # one-hot targets in scaled-logit space
    "e_clip": 127,        # error clip (integer gradient clipping)
    "lr2_shift": 11,      # output-layer update: (e*h) >> 11
    "lr1_shift": 10,      # hidden-layer update:  (eh*x) >> 10
    "b_scale": 1,         # DFA feedback matrix entries in {-1,0,1}
    "epochs": 40,
    "n_train": 243, "n_test": 81,
    "x_band": 3,          # inputs uniform in [-3, 3]
    "seed_weights": 3**9,
    "seed_dfa": 3**7,
    "seed_data": 3**11,
    "seed_teacher": 3**13,
}


# ── net construction ─────────────────────────────────────────────────────────
def init_matrix(gen, rows, cols, band):
    return [[rand_int(gen, -band, band) for _ in range(cols)] for _ in range(rows)]


def make_net(hp):
    g = _lcg(hp["seed_weights"])
    W1 = init_matrix(g, hp["n_hid"], hp["n_in"], hp["w_init"])
    W2 = init_matrix(g, hp["n_out"], hp["n_hid"], hp["w_init"])
    return W1, W2


def make_dfa(hp):
    g = _lcg(hp["seed_dfa"])
    # fixed ternary feedback: hidden j hears output k through B[k][j]
    return [[rand_int(g, -hp["b_scale"], hp["b_scale"])
             for _ in range(hp["n_hid"])] for _ in range(hp["n_out"])]


def forward(W1, W2, x, hp):
    z1 = imatmul(W1, x)
    h = [clip(sym_shift(z, hp["a_shift"]), hp["a_cap"]) for z in z1]
    o = imatmul(W2, h)
    return z1, h, o


# ── the toy problem: learn a hidden ternary teacher ─────────────────────────
def make_dataset(hp):
    """Inputs from the LCG; labels = argmax of a FIXED random ternary
    teacher net. Learnable, deterministic, no floats anywhere."""
    gt = _lcg(hp["seed_teacher"])
    T1 = init_matrix(gt, hp["n_hid"], hp["n_in"], 1)     # ternary teacher
    T2 = init_matrix(gt, hp["n_out"], hp["n_hid"], 1)
    gd = _lcg(hp["seed_data"])
    data = []
    for _ in range(hp["n_train"] + hp["n_test"]):
        x = [rand_int(gd, -hp["x_band"], hp["x_band"]) for _ in range(hp["n_in"])]
        th = [clip(sym_shift(z, 1), hp["a_cap"]) for z in imatmul(T1, x)]
        y = argmax_low(imatmul(T2, th))
        data.append((x, y))
    return data[:hp["n_train"]], data[hp["n_train"]:]


# ── training ─────────────────────────────────────────────────────────────────
def train_step(W1, W2, B, x, y, hp):
    z1, h, o = forward(W1, W2, x, hp)
    o_scaled = [sym_shift(ok, hp["o_shift"]) for ok in o]
    t = [hp["t_hi"] if k == y else hp["t_lo"] for k in range(hp["n_out"])]
    e = [clip(ok - tk, hp["e_clip"]) for ok, tk in zip(o_scaled, t)]

    # output layer: plain integer SGD
    for k in range(hp["n_out"]):
        ek = e[k]
        if ek == 0:
            continue
        row = W2[k]
        for j in range(hp["n_hid"]):
            row[j] = clip(row[j] - sym_shift(ek * h[j], hp["lr2_shift"]), hp["w_cap"])

    # hidden layer: DFA — error arrives through the fixed ternary B,
    # gated by the activation's derivative (0 where the clip saturated)
    for j in range(hp["n_hid"]):
        if abs(sym_shift(z1[j], hp["a_shift"])) >= hp["a_cap"]:
            continue
        eh = sum(B[k][j] * e[k] for k in range(hp["n_out"]))
        if eh == 0:
            continue
        row = W1[j]
        for i in range(hp["n_in"]):
            row[i] = clip(row[i] - sym_shift(eh * x[i], hp["lr1_shift"]), hp["w_cap"])


def accuracy(W1, W2, data, hp):
    good = sum(1 for x, y in data if argmax_low(forward(W1, W2, x, hp)[2]) == y)
    return good, len(data)


def _setup(hp):
    """Everything a run (or a resumed epoch) derives from the job identity."""
    W1, W2 = make_net(hp)
    B = make_dfa(hp)
    train_set, test_set = make_dataset(hp)
    return W1, W2, B, train_set, test_set


def _run_epoch(W1, W2, B, train_set, hp):
    """Exactly one epoch, in place. Fixed sample order — the toy consumes
    no shuffle stream, so an epoch is a pure function of (weights, job)."""
    for x, y in train_set:
        train_step(W1, W2, B, x, y, hp)


def train(hp=None):
    """The whole run. Returns dict with final weights digest, the per-epoch
    digest chain, and train/test accuracy counts. Pure integers throughout."""
    hp = dict(HP, **(hp or {}))
    W1, W2, B, train_set, test_set = _setup(hp)
    epoch_digests = []
    for _ in range(hp["epochs"]):
        _run_epoch(W1, W2, B, train_set, hp)
        epoch_digests.append(weights_digest([W1, W2]))
    tr_good, tr_n = accuracy(W1, W2, train_set, hp)
    te_good, te_n = accuracy(W1, W2, test_set, hp)
    return {
        "unit": "dick-train-v0.3-dfa",
        "final_digest": epoch_digests[-1],
        "epoch_digests": epoch_digests,
        "train_acc": [tr_good, tr_n],
        "test_acc": [te_good, te_n],
        "hp_digest": hashlib.sha3_256(canonical_bytes(hp)).hexdigest(),
    }


# ── stage 4: log-and-replay as an audit primitive, and the mesh worker ──────
# The sellable claim is the epoch digest chain. Verification comes in two
# strengths: FULL REPLAY (rerun the job; every byte must match — δ = 0), and
# the CHEAP AUDIT (verify ONE epoch from its predecessor's checkpoint — the
# per-layer spot-check of dick_kernel, applied to training time).

# a hostile job must not be able to buy a year of CPU with one line of JSON
JOB_BOUNDS = {"epochs": 200, "n_train": 2000, "n_test": 500,
              "n_in": 256, "n_hid": 256, "n_out": 128}


def decode_job(job: bytes, index: int):
    """Job bytes → hp. Overrides whitelist into HP and clamp to JOB_BOUNDS;
    the chunk index perturbs the weight seed so each chunk is an
    independent, individually-replayable run (a seed ensemble)."""
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
    """The worker's whole claim, canonical: digest chain + exact accuracy.
    Weights never ride the wire — the digests commit to them."""
    hp = decode_job(job, index)
    r = train(hp)
    out = {"unit": "dick-train-v0.3-unit", "index": index,
           "final_digest": r["final_digest"],
           "epoch_digests": r["epoch_digests"],
           "train_acc": r["train_acc"], "test_acc": r["test_acc"],
           "hp_digest": r["hp_digest"]}
    return canonical_bytes(out).decode()


VCLASS_NATIVE = "native"


def as_worker():
    """Training as a REPLAY-CLASS mesh worker (dick_kernel's exact
    optional-wrapper discipline): full replay by the auditor = δ = 0
    settlement, and the work mints weight-bearing native votes."""
    try:
        from p2pcp_worker import WorkerAdapter, VCLASS_NATIVE as _VN
    except Exception:                            # noqa: BLE001
        try:
            from p2pcp.worker import WorkerAdapter, VCLASS_NATIVE as _VN
        except Exception:
            WorkerAdapter, _VN = None, VCLASS_NATIVE

    if WorkerAdapter is not None:
        class TrainWorker(WorkerAdapter):
            """REPLAY-CLASS: bit-exactly reproducible training."""
            vclass = _VN

            def run_chunk(self, job: bytes, index: int) -> bytes:
                return run_unit(job, index).encode()
        return TrainWorker()

    class _TrainWorker:                          # duck-typed fallback
        vclass = VCLASS_NATIVE

        def run_chunk(self, job: bytes, index: int) -> bytes:
            return run_unit(job, index).encode()
    return _TrainWorker()


def checkpoint(job: bytes, index: int, epoch_i: int) -> bytes:
    """Canonical [W1, W2] AFTER epoch epoch_i — what an honest worker logs
    beside its digest chain so auditors can spot-check single epochs."""
    hp = decode_job(job, index)
    if not (0 <= epoch_i < hp["epochs"]):
        raise ValueError("epoch out of range")
    W1, W2, B, train_set, _ = _setup(hp)
    for _ in range(epoch_i + 1):
        _run_epoch(W1, W2, B, train_set, hp)
    return canonical_bytes([W1, W2])


def audit_one_epoch(job: bytes, index: int, claimed_digests, epoch_i: int,
                    prev_ckpt: bytes = b"") -> bool:
    """Verify ONE epoch of a claimed run without recomputing the rest.

    (1) the offered checkpoint must hash to the PREVIOUS claimed digest —
        a forged starting state fails before any compute is spent;
    (2) recompute ONLY epoch epoch_i from it;
    (3) the result must hash to the claimed digest for epoch_i.
    Epoch 0 needs no checkpoint (its predecessor is the job-derived init).
    """
    hp = decode_job(job, index)
    if not (0 <= epoch_i < hp["epochs"]) or epoch_i >= len(claimed_digests):
        return False
    _, _, B, train_set, _ = _setup(hp)
    if epoch_i == 0:
        W1, W2, _, _, _ = _setup(hp)
    else:
        if hashlib.sha3_256(prev_ckpt).hexdigest() != claimed_digests[epoch_i - 1]:
            return False
        try:
            W1, W2 = json.loads(prev_ckpt.decode("utf-8"))
        except Exception:
            return False
        if not all(isinstance(v, int) for M in (W1, W2) for row in M for v in row):
            return False
    _run_epoch(W1, W2, B, train_set, hp)
    return weights_digest([W1, W2]) == claimed_digests[epoch_i]


def main(argv=None):
    a = list(sys.argv[1:] if argv is None else argv)
    if a[:1] == ["--digest"]:
        print(train()["final_digest"])
        return
    r = train()
    tr, te = r["train_acc"], r["test_acc"]
    print(f"unit:   {r['unit']}")
    print(f"train:  {tr[0]}/{tr[1]}  ({100*tr[0]//tr[1]}%)")
    print(f"test:   {te[0]}/{te[1]}  ({100*te[0]//te[1]}%)  chance≈11%")
    print(f"epochs: {len(r['epoch_digests'])}")
    print(f"final_digest: {r['final_digest']}")


if __name__ == "__main__":
    main()
