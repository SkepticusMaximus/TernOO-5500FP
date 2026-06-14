# TernOO-5500FP Benchmark Suite

Two-part benchmark comparing native C, the NASM TernOO emulator,
the Python v0.1 5500FP emulator (raw ISA), and the TernOO v0.3
emulator (full word architecture).

- **Part A** — raw arithmetic throughput (Fibonacci, Factorial, tight arith loop)
- **Part B** — semantic workloads (word dispatch, heterogeneous streams,
  tribble extraction, object accumulation, FlowCode-style graph walk)

Source: Manus AI, contributed June 2026.

## Layout

- `scripts/` — benchmark drivers (Python + C)
- `raw_data/` — extracted benchmark zip contents (CSV / JSON outputs)
- `figures/` — generated charts (PNG)

## Report

See [`../docs/benchmarks/Benchmark-Report.md`](../docs/benchmarks/Benchmark-Report.md).

## Reproducibility

Not yet wired into a reproducible build. The scripts ran on Manus's
infrastructure; we have the outputs and the report. A future commit
should add a `Makefile` here to re-run the suite locally.
