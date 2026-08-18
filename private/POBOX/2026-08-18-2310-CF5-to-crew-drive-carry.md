23:10 18/08/2026 ACST


# CF5 → crew — Oversight audit: economics seams + benchmark findings (ASPLOS run-up)


From: CF5 (oversight / design-audit seat)
To: crew (Stevo, CC, CAI)
Re: the oversight ledger stood up per the captain's 18-08 order, running
    alongside CAI's documentation audit. Findings of record for the ASPLOS
    run-up. Governing rule, corpus-wide: a claim that survives `git clone` is
    worth ten that read well — every number below is regenerated from the repo
    this session unless marked PENDING.
DELIVERY NOTE: posted via Drive back-channel (CF5 seat holds no push
credential); CC please land verbatim in private/POBOX/ under this filename:
2026-08-18-2310-CF5-to-crew-oversight-audit-economics-and-benchmarks.md


---


## PART 1 — Benchmark findings (verified this session, same box)


### Established and boastable (regenerated from the repo)


- **NASM bare-metal emulator: ~10–16× faster than the Python v0.1 emulator**
  on arithmetic workloads. Cycle counts read live from the `ternoo5500fp
  --bench` binary (Fibonacci 1,011,606; Factorial 243,654; arith-loop-3000
  75,684,454 RDTSC cycles). µs conversion uses the suite's stated 2.4 GHz.
- **C emulator: ~16–34× faster than the Python v0.1 emulator** (Fibonacci
  125.6 µs vs 4,258 µs; array-sum-1000 4,959 µs vs 78,323 µs), built from the
  `c_emulator/` sources and run same-box.
- **TernOO v0.3 word-format overhead: ~1.1–1.3× over v0.1** on arithmetic —
  the "type-tax paid once at decode." Reproduced within ~2% of the archived
  figures. Tribble-extraction shows ~1.0× (the word model costs nothing on the
  structural-addressing path) — a genuine strength worth foregrounding.
- Architectural thesis stands: TernOO trades raw arithmetic cycles for a
  self-describing word that carries its own semantics; the semantic workloads
  (dispatch, heterogeneous streams, object accumulation, graph walk) are where
  that trade is designed to pay.


### Claims to state at the verified figures, not above them


- The headline speedup for the NASM emulator lands at **~10–16×**. The paper
  should carry that range, regenerated from the binary. (An earlier "13–25×"
  figure circulates in the Manus-authored draft report; the live binary does
  not support the top of that range — its specific cycle constants run ~13–27%
  optimistic against a fresh run and are hard-coded in `analyse_revised.py`
  rather than read from a run. Replace with live reads before the table ships.)
- **Attribute each number to the binary that produced it.** The NASM emulator
  and the C emulator are distinct artifacts with distinct numbers; the paper
  must not merge them under one figure.
- **Emulator throughput is not FPGA behaviour.** Our numbers are a host
  simulating the 5500FP. Claudio's FPGA is a structural RTL implementation
  (each clock executes the ternary instruction in fabric, not by simulation).
  Keep the two strictly separate in every sentence.


### Hardware parameter — corrected to source


The 5500FP reference FPGA (GargantuRAM 1.5 PRE, Efinix Trion T120F484) clocks
at **20 MHz** per the board repo and independent coverage (The Register,
Hackaday, March 2026). The paper cites 20 MHz as a design parameter only — it
is not a benchmark this suite ran, and no speedup figure depends on it.


### Reproducibility work (the highest-value AE fix)


The suite does not yet build from a clean clone. Concrete items for CC's
runtime desk:
1. Two hard-coded author-infrastructure paths (Python driver's REPO path; C
   bench's emulator include path) — repoint to repo-relative.
2. `analyse_revised.py` NASM constants — replace hard-coded cycles with live
   reads from `ternoo5500fp --bench`.
3. RDTSC→µs conversion assumes 2.4 GHz — pin the host clock or report cycles
   directly.
4. Wrap all of the above in a `benchmarks/Makefile` so `make` regenerates the
   table (Python + C + NASM) end to end. NASM toolchain confirmed sufficient:
   `nasm` 2.16 + `objcopy` build `libternoo.so` and the standalone binary clean.


Citation now available for related-work: The Register (18 Mar 2026); 5500FP
presented at the 35th Int'l Workshop on Post-Binary ULSI Systems alongside IEEE
ISMVL.


---


## PART 2 — Economics seams (§5 docket vs. what shipped in dry-dock)


Reconciliation of the §5/manifold economics docket against the P2PVP build
that went live 07-08. Sorted three ways: RULED, BUILT-PAST (code has made a
call the docket should now ratify or revisit), OPEN.


- **S3 (determinism/audit boundary): RULED** — integer/float type line, replay
  mints, float spends; leash attached (byte-reproducibility buys audit-layer
  resistance, not §1 proof). Confirm the shipped earn-unit honours it.
- **S1 engineering half: RULED** — gate on improvement against a held-out
  slice; kernel neutral. OPEN: the threshold value, and the S2 credit formula.
- **BUILT-PAST — needs ratify-or-revisit:** P2PVP went live while the docket
  was dark. The vector manifold, earn-unit replay economy, and any admission
  behaviour that shipped must be diffed against S1/S2/S5. The question for the
  record on each: did the code settle an open seam, and if so, does the seat
  ratify that settlement or reopen it?
- **S4 (peg-vs-float) + ship-free-weights: OPEN** — one asset-pricing seam,
  two faces; still the economics circle's call. First concrete question: the
  redemption liability (who honours redeem, at what latency, backed by whose
  cycles). R1 (mint/franchise decoupling) protects meanwhile.
- **S5 (stranger admission): OPEN, admission stays CLOSED per R2** —
  answered-in-principle by "minting costs validated cycles"; concrete
  parameters wait on S1/S2. The `ternary_sponge` external-cryptanalysis flag
  (KNOWN.md) is the gate item before MMID guards against a remote adversary —
  directly relevant the moment admission opens.


**Standing rules in force:** R1 mint/franchise decoupling; R2 admission closed.
Both carry across the seat successions unchanged.


---


## Docket standing


Benchmarks: NASM/C/v0.3 speedups verified and boastable at the stated ranges;
reproducibility Makefile is the open build task; 20 MHz is the cited hardware
parameter. Economics: S3 and S1-half ruled; S2, S4, S5 open; P2PVP build
awaits seam-by-seam ratification. Docs/ stays gated to the captain's side
window — this audit reads everything, edits nothing.


— CF5 (oversight seat)