#!/usr/bin/env python3
"""ghost_senses.py — GHOST's first senses: a live sensory tick stream (PROTOTYPE).

The minimal loop the developmental papers describe, made runnable tonight:
capture → ternary features → predict the next tick → measure surprise.
"The next input is the label": prediction error against the machine's own
microphone needs no labeler, no reward model, no judge but the environment.

WHAT THIS IS (and isn't):
  * A capture front-end + integer prediction loop. Per tick (default 100 ms)
    the mic's samples are split into 9 time slices; each slice's RMS delta vs
    the previous tick is ternarized {-1,0,+1} with an adaptive integer
    deadband → a 9-trit sensory word. A first-order per-trit learner (pure
    counts) predicts the next word; surprise = ternary distance pred↔actual.
  * All-integer throughout (the ship's type line, §S3) — but a LIVE stream is
    not replayable, so sensory ticks are OBSERVATIONAL: never mint-eligible,
    never weight-bearing. What IS mesh cargo: the recorded corpus (--corpus),
    whose (context → next-word) pairs can later be trained on and validated
    against held-out slices — the P2PVP training manifold's food.
  * Camera: /dev/video0 exists but this box has no ffmpeg/cv2; a guarded
    read() attempt is made and declines honestly on the usual mmap-only
    drivers. Mic is the sense that ships today.

Run:  python3 ghost_senses.py mic --ticks 300 --corpus ~/ghost_mic.jsonl
Test: python3 -m unittest test_ghost_senses   (synthetic streams, no hardware)

Added: 06 Aug 2026, Adelaide. Authors: Stevo (SkepticusMaximus) + CC.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time

RATE = 8000                 # Hz, mono S16_LE
SLICES = 9                  # time slices per tick → one 9-trit sensory word
DEADBAND_NUM = 1            # deadband = max(1, mean|delta| * NUM // DEN):
DEADBAND_DEN = 2            #   changes smaller than half the recent mean are "same"
DEADBAND_WIN = 32           # ticks of |delta| history per slice


def slice_rms(samples: list) -> list:
    """RMS per time slice, integer (isqrt). ``samples`` are signed ints."""
    n = len(samples)
    out = []
    for s in range(SLICES):
        seg = samples[s * n // SLICES:(s + 1) * n // SLICES] or [0]
        acc = sum(v * v for v in seg)
        out.append(_isqrt(acc // len(seg)))
    return out


def _isqrt(x: int) -> int:
    import math
    return math.isqrt(x)


class Ternarizer:
    """Per-slice adaptive deadband: delta vs previous tick → {-1,0,+1}.
    Integer state only, so a recorded corpus replays bit-exactly."""

    def __init__(self):
        self.prev = None
        self.hist = [[] for _ in range(SLICES)]

    def tick(self, rms: list) -> list:
        if self.prev is None:
            self.prev = rms
            return [0] * SLICES
        trits = []
        for i in range(SLICES):
            d = rms[i] - self.prev[i]
            h = self.hist[i]
            h.append(abs(d))
            if len(h) > DEADBAND_WIN:
                h.pop(0)
            dead = max(1, (sum(h) // len(h)) * DEADBAND_NUM // DEADBAND_DEN)
            trits.append(0 if abs(d) <= dead else (1 if d > 0 else -1))
        self.prev = rms
        return trits


class TritLearner:
    """First-order per-trit model: counts[slice][prev+1][next+1] += 1;
    prediction = argmax count (tie → persistence). Pure integers — the
    humblest thing that can be said to learn."""

    def __init__(self):
        self.counts = [[[0] * 3 for _ in range(3)] for _ in range(SLICES)]
        self.prev = [0] * SLICES

    def predict(self) -> list:
        pred = []
        for i in range(SLICES):
            row = self.counts[i][self.prev[i] + 1]
            best = max(range(3), key=lambda t: (row[t], t == self.prev[i] + 1))
            pred.append(best - 1)
        return pred

    def observe(self, actual: list) -> None:
        for i in range(SLICES):
            self.counts[i][self.prev[i] + 1][actual[i] + 1] += 1
        self.prev = list(actual)


def surprise(pred: list, actual: list) -> int:
    """Ternary distance, 0..2 per trit (0 = anticipated, 2 = full reversal)."""
    return sum(abs(p - a) for p, a in zip(pred, actual))


def mic_ticks(tick_ms=100):
    """Yield lists of signed samples per tick from arecord (raw S16_LE mono)."""
    frames = RATE * tick_ms // 1000
    proc = subprocess.Popen(
        ["arecord", "-q", "-f", "S16_LE", "-r", str(RATE), "-c", "1",
         "-t", "raw"],
        stdout=subprocess.PIPE)
    try:
        while True:
            raw = proc.stdout.read(frames * 2)
            if not raw or len(raw) < frames * 2:
                return
            yield [int.from_bytes(raw[i:i + 2], "little", signed=True)
                   for i in range(0, len(raw), 2)]
    finally:
        proc.terminate()


def camera_probe(dev="/dev/video0"):
    """Honest capability check: most UVC drivers are mmap-only, so a plain
    read() usually declines. We try, we report, we do not pretend."""
    try:
        with open(dev, "rb", buffering=0) as f:
            data = f.read(64)
        return bool(data)
    except OSError as e:
        print(f"[senses] camera: {dev} declined plain read() ({e.strerror}) — "
              f"needs ffmpeg or a V4L2 mmap reader; mic mode works today.",
              file=sys.stderr)
        return False


def run_mic(ticks=0, tick_ms=100, corpus=None, quiet=False):
    """The loop: capture → ternarize → predict → observe → surprise."""
    tern, brain = Ternarizer(), TritLearner()
    log = open(os.path.expanduser(corpus), "a") if corpus else None
    n, sur_hist = 0, []
    try:
        for samples in mic_ticks(tick_ms):
            word = tern.tick(slice_rms(samples))
            pred = brain.predict()
            s = surprise(pred, word)
            brain.observe(word)
            n += 1
            sur_hist.append(s)
            if log:
                log.write(json.dumps({"t": n, "word": word, "pred": pred,
                                      "surprise": s},
                                     separators=(",", ":")) + "\n")
            if not quiet:
                bar = "".join("+0-"[1 - t] for t in word)
                print(f"tick {n:5d}  word {bar}  surprise {s:2d}")
            if ticks and n >= ticks:
                break
    except KeyboardInterrupt:
        pass
    finally:
        if log:
            log.close()
    if sur_hist:
        half = max(1, len(sur_hist) // 2)
        early = sum(sur_hist[:half]) / half
        late = sum(sur_hist[half:]) / max(1, len(sur_hist) - half)
        print(f"\n[senses] {n} ticks. mean surprise early {early:.2f} → "
              f"late {late:.2f} "
              f"({'learning visible' if late < early else 'no drop yet'})")
    return sur_hist


def main(argv=None):
    ap = argparse.ArgumentParser(prog="ghost_senses",
                                 description="GHOST's live sensory tick loop")
    sub = ap.add_subparsers(dest="cmd", required=True)
    pm = sub.add_parser("mic", help="listen: predict the mic's next tick")
    pm.add_argument("--ticks", type=int, default=0, help="stop after N (0 = ∞)")
    pm.add_argument("--tick-ms", type=int, default=100)
    pm.add_argument("--corpus", help="append JSONL ticks here (future cargo)")
    pm.add_argument("--quiet", action="store_true")
    pc = sub.add_parser("camera", help="probe whether the webcam is readable")
    pc.add_argument("--dev", default="/dev/video0")
    args = ap.parse_args(argv)
    if args.cmd == "mic":
        run_mic(args.ticks, args.tick_ms, args.corpus, args.quiet)
    elif args.cmd == "camera":
        ok = camera_probe(args.dev)
        print(f"[senses] camera readable: {ok}")


if __name__ == "__main__":
    main()
