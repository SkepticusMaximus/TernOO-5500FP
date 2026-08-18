# TernOO-5500FP benchmark harness — regenerate every leg from a clean clone.
#   make c        build the C emulator + bench, run it, save CSV
#   make python   run the Python suite (pure + v0.1 baseline + v0.3 oracle)
#   make nasm     build + run the NASM emulator bench (needs: sudo apt install nasm)
#   make all      all three legs, same box, one sitting
# CSVs land in raw_data/ stamped by date. The head-to-head table for the paper
# reads identical workloads from these files — same box, same units, per leg.

NASMDIR := ../NASM-TernOO-5500FP-Emulator
OUT     := raw_data
STAMP   := $(shell date +%Y%m%d)
CSRCS   := $(filter-out $(NASMDIR)/c_emulator/src/main.c,$(wildcard $(NASMDIR)/c_emulator/src/*.c))

.PHONY: all python c nasm clean
all: c python nasm

c:
	$(MAKE) -C $(NASMDIR)/c_emulator
	gcc -O2 -march=native -std=c11 -I $(NASMDIR)/c_emulator/include \
	  $(NASMDIR)/benchmarks/c_emu_bench.c $(CSRCS) \
	  -o $(NASMDIR)/benchmarks/c_emu_bench
	mkdir -p $(OUT)
	$(NASMDIR)/benchmarks/c_emu_bench | tee $(OUT)/c_emu_$(STAMP).csv

python:
	mkdir -p $(OUT)
	cd $(NASMDIR)/benchmarks && python3 python_bench.py | tee $(CURDIR)/$(OUT)/python_$(STAMP).csv

nasm:
	@which nasm >/dev/null || { echo "nasm not installed — run: sudo apt install -y nasm"; exit 1; }
	$(MAKE) -C $(NASMDIR)/nasm_emulator -B
	mkdir -p $(OUT)
	$(NASMDIR)/nasm_emulator/ternoo5500fp --bench | tee $(OUT)/nasm_$(STAMP).txt

clean:
	rm -f $(NASMDIR)/benchmarks/c_emu_bench
	$(MAKE) -C $(NASMDIR)/c_emulator clean 2>/dev/null || true
