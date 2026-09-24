#!/usr/bin/env python3
"""train_lora.py — LoRA fine-tune OLMo-2-7B into the ship-fluency Professor.

Teaches OLMo-2-1124-7B the TernOO/FlowCode/GHOST knowledge it lacks, as a
small LoRA adapter (a few MB that snaps onto the base model) — cheap,
reversible, offline. Consumes professor/train.jsonl (built by
build_dataset.py).

STATUS: box-ready, syntax-checked. NOT yet run on real hardware — it
awaits the training tower (24GB GPU). Do not treat as verified until it
has completed a run on the box; the runbook (README.md) says the same.

Hardware: a ~24GB GPU (used RTX 3090 is the value pick). CPU-only works
but is glacial. Deps:
    pip install torch transformers peft trl datasets accelerate bitsandbytes

Run (on the box):
    python3 professor/train_lora.py \
        --base allenai/OLMo-2-1124-7B-SFT \
        --data professor/train.jsonl \
        --out  professor/ship-fluency-adapter

Added: 25 Sep 2026 (Professor training pipeline). Authors: Stevo + Claude.
"""
import argparse
import os
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="allenai/OLMo-2-1124-7B-SFT",
                    help="full-precision HF weights (NOT the GGUF)")
    ap.add_argument("--data", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "train.jsonl"))
    ap.add_argument("--out", default=os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "ship-fluency-adapter"))
    ap.add_argument("--epochs", type=float, default=3.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--accum", type=int, default=8)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--maxlen", type=int, default=2048)
    ap.add_argument("--qlora", action="store_true",
                    help="4-bit base (QLoRA) — fits a smaller GPU")
    args = ap.parse_args()

    try:
        import torch
        from datasets import load_dataset
        from transformers import (AutoModelForCausalLM, AutoTokenizer,
                                  BitsAndBytesConfig)
        from peft import LoraConfig, get_peft_model
        from trl import SFTTrainer, SFTConfig
    except ImportError as e:
        sys.exit(f"missing deps ({e}).\n  pip install torch transformers "
                 "peft trl datasets accelerate bitsandbytes")

    if not os.path.isfile(args.data):
        sys.exit(f"no dataset at {args.data} — run build_dataset.py first")

    tok = AutoTokenizer.from_pretrained(args.base)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token

    quant = None
    if args.qlora:
        quant = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True)

    model = AutoModelForCausalLM.from_pretrained(
        args.base, quantization_config=quant,
        torch_dtype=torch.bfloat16,
        device_map="auto" if torch.cuda.is_available() else None)

    lora = LoraConfig(
        r=args.rank, lora_alpha=args.alpha, lora_dropout=0.05,
        bias="none", task_type="CAUSAL_LM",
        # OLMo-2 attention + MLP projection names
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"])
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    ds = load_dataset("json", data_files=args.data, split="train")

    def fmt(rec):
        return {"text": tok.apply_chat_template(
            rec["messages"], tokenize=False, add_generation_prompt=False)}
    ds = ds.map(fmt, remove_columns=ds.column_names)

    cfg = SFTConfig(
        output_dir=args.out, num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.accum,
        learning_rate=args.lr, warmup_ratio=0.03,
        logging_steps=5, save_strategy="epoch",
        max_seq_length=args.maxlen, bf16=torch.cuda.is_available(),
        report_to="none", dataset_text_field="text")
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds,
                         processing_class=tok)
    trainer.train()
    trainer.save_model(args.out)
    tok.save_pretrained(args.out)
    print(f"\nship-fluency adapter saved to {args.out}")
    print("serve: load the base model + this adapter, or merge and "
          "re-export to GGUF for llama-server.")


if __name__ == "__main__":
    main()
