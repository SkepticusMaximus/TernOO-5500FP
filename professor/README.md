# Professor Training Pipeline — Captain's Runbook

Teaching the Professor (OLMo-2-1124-7B) actual **ship fluency** — the
TernOO / FlowCode / GHOST knowledge it confessed it doesn't have — as a
small, cheap, reversible **LoRA adapter**. Offline, yours, no cloud.

## What training actually is (ELI5)
We don't grow his brain. We take his 7-billion existing knobs, freeze
them, and nudge a tiny **new sheet of knobs** (the LoRA adapter, a few
MB) so that when he hears "TernOO" he answers from *our specs* instead
of guessing. Small, cheap, reversible, runs on **your** box, no internet.

## The two halves
1. **Data (runs anywhere, no GPU — do this now):**
   - `ship_fluency_seed.jsonl` — hand-authored, canon-accurate lessons
     (the seed; grow it by dropping more `*.jsonl` into `professor/lessons/`).
   - `build_dataset.py` — assembles + validates → `train.jsonl`.
2. **Training (needs the tower):**
   - `train_lora.py` — LoRA fine-tunes OLMo-2-7B on `train.jsonl`,
     saves the adapter. Box-ready; **not yet run on hardware.**

## The hardware (the tower)
The Colibri videos taught the real lesson: **it's the RAM, not the GPU.**
For LoRA-training a 7B and running mid-size models locally:

| Part | Spec | Why |
|---|---|---|
| GPU | used **RTX 3090, 24 GB** | value king; 24 GB fits a 7B LoRA + 13–30B inference |
| RAM | **128 GB DDR4** | training headroom + room to play with Colibri-style MoE |
| SSD | **2 TB NVMe** | 1 TB fills instantly (a Colibri model is ~372 GB) |
| CPU/board | Ryzen on AM4/AM5, 4 DIMM slots | cheap; leaves budget for the GPU |
| PSU | 850 W+ | a 3090 is hungry |

Rough total ~$1,600–2,100 (RAM prices are up). The 3090 is the best dollar.

## Captain's itinerary
1. **Buy**, in priority order: 24 GB GPU → 128 GB RAM → 2 TB NVMe →
   plain board+CPU+PSU+case.
2. **Assemble**, install Linux Mint (same as the other boxes).
3. **Install the AI stack** (copy-paste):
   ```
   # NVIDIA driver first, then:
   python3 -m venv ~/.venvs/prof && . ~/.venvs/prof/bin/activate
   pip install torch transformers peft trl datasets accelerate bitsandbytes
   ```
4. **Build the lessons** (works now, any machine):
   ```
   python3 professor/build_dataset.py
   ```
5. **Train** (on the box; a few hours on a 3090; add `--qlora` for a
   smaller GPU):
   ```
   python3 professor/train_lora.py \
       --base allenai/OLMo-2-1124-7B-SFT \
       --data professor/train.jsonl \
       --out  professor/ship-fluency-adapter
   ```
6. **Serve** the trained Professor: load the base model + the adapter,
   or merge and re-export to GGUF for `llama-server` (the current
   `olmo7b-server` path), replacing the blank Professor with the
   ship-fluent one.

## Growing the curriculum
The seed is 20 lessons — a starting point and a template. Add more by
dropping `professor/lessons/*.jsonl` files in the same `messages` shape
(`{"messages":[{"role":"user","content":...},{"role":"assistant",
"content":...}]}`), then re-run `build_dataset.py`. Good lessons come
from the ship's own canon: the Language Audit, the north-star brief,
the glyph-plane and King-X rulings, the CLAUDE.md conventions.

Added: 25 Sep 2026. Authors: Stevo + Claude.
