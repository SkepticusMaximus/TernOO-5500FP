#!/usr/bin/env python3
"""build_dataset.py — assemble + validate the Professor's training data.

Takes the hand-authored ship-fluency seed (and any extra *.jsonl lesson
files you drop in professor/lessons/) and produces professor/train.jsonl,
validated line by line. Pure stdlib — runs on any box, no GPU, no torch.
This is the testable, hardware-free half of the training pipeline: get
the DATA right here, then train_lora.py consumes train.jsonl on the box.

Usage:
    python3 professor/build_dataset.py            # build + validate
    python3 professor/build_dataset.py --stats    # just report

Added: 25 Sep 2026 (Professor training pipeline). Authors: Stevo + Claude.
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "ship_fluency_seed.jsonl")
LESSONS = os.path.join(HERE, "lessons")          # optional extra *.jsonl
OUT = os.path.join(HERE, "train.jsonl")


def _valid(rec):
    """A record is a messages list with a user turn and an assistant turn,
    both non-empty strings — the shape TRL's SFTTrainer expects."""
    msgs = rec.get("messages")
    if not isinstance(msgs, list) or len(msgs) < 2:
        return False
    roles = [m.get("role") for m in msgs]
    if "user" not in roles or "assistant" not in roles:
        return False
    return all(isinstance(m.get("content"), str) and m["content"].strip()
               for m in msgs)


def _load(path):
    out, bad = [], 0
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                print(f"  ! {os.path.basename(path)}:{i} bad JSON")
                continue
            if _valid(rec):
                out.append(rec)
            else:
                bad += 1
                print(f"  ! {os.path.basename(path)}:{i} bad shape")
    return out, bad


def main():
    stats_only = "--stats" in sys.argv
    sources = [SEED] + sorted(glob.glob(os.path.join(LESSONS, "*.jsonl")))
    sources = [p for p in sources if os.path.isfile(p)]
    recs, bad, seen = [], 0, set()
    for p in sources:
        got, b = _load(p)
        bad += b
        for r in got:
            key = json.dumps(r, sort_keys=True)
            if key not in seen:                  # dedup identical lessons
                seen.add(key)
                recs.append(r)
        print(f"  {os.path.basename(p)}: {len(got)} valid")
    print(f"total: {len(recs)} lessons, {bad} rejected, "
          f"from {len(sources)} file(s)")
    if not recs:
        print("no valid lessons — nothing to write")
        return 1
    if stats_only:
        return 0
    with open(OUT, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
