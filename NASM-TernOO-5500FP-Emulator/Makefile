# ============================================================================
# NASM-TernOO-5500FP-Emulator — Top-level Makefile
# Builds: bin/libternoo.so — hybrid bridge shared library
#         (C-API over the NASM 5500FP core)
#
# Architecture:
#   c_api.c       thin C wrappers (ternoo_init → cpu_init, etc.)
#   cpu_shim.c    ABI bridge — owns global CPU struct + memory; provides the
#                 no-arg cpu_init/reset/run/read_reg… that c_api.c expects;
#                 calls the NASM versions (renamed to _n_cpu_*) via objcopy
#   cpu.asm       NASM 5500FP CPU core — struct-pointer ABI
#   trit.asm      NASM ternary math primitives
#
# Why the shim:  cpu.asm uses a struct-pointer ABI (rdi=cpu*, rsi=mem*).
# c_api.c expects no-arg stateful calls.  cpu_shim.c bridges the gap by
# allocating global CPU state and forwarding to the renamed NASM functions.
#
# objcopy renames cpu.o's exports (cpu_init → _n_cpu_init etc.) so the
# shim's no-arg versions don't clash.
#
# Both .asm files use [rel …] RIP-relative addressing throughout — PIC-
# compatible without special NASM flags.
# ============================================================================

NASM        = nasm
CC          = gcc
OBJCOPY     = objcopy
NASMFLAGS   = -f elf64 -I nasm_emulator/
CFLAGS      = -fPIC -O2 -Wall -std=c11
# -Bsymbolic: resolve intra-library calls at link time (avoids R_X86_64_PC32
# errors from NASM's 32-bit relative calls between objects in the same .so)
LDFLAGS     = -shared -Wl,-Bsymbolic

BIN_DIR     = bin
OBJ_DIR     = obj
LIB         = $(BIN_DIR)/libternoo.so

NASM_OBJS   = $(OBJ_DIR)/trit.o \
              $(OBJ_DIR)/cpu_renamed.o

C_OBJS      = $(OBJ_DIR)/c_api.o \
              $(OBJ_DIR)/cpu_shim.o

ALL_OBJS    = $(NASM_OBJS) $(C_OBJS)

# Symbols to rename in cpu.o so they don't clash with cpu_shim.c's wrappers
RENAME_SYMS = --redefine-sym cpu_init=_n_cpu_init        \
              --redefine-sym cpu_reset=_n_cpu_reset       \
              --redefine-sym cpu_run=_n_cpu_run           \
              --redefine-sym cpu_read_reg=_n_cpu_read_reg \
              --redefine-sym cpu_write_reg=_n_cpu_write_reg \
              --redefine-sym cpu_mem_read=_n_cpu_mem_read \
              --redefine-sym cpu_mem_write=_n_cpu_mem_write \
              --redefine-sym cpu_fetch=_n_cpu_fetch       \
              --redefine-sym cpu_execute=_n_cpu_execute   \
              --redefine-sym cpu_dump_regs=_n_cpu_dump_regs \
              --redefine-sym cpu_load_program=_n_cpu_load_program

.PHONY: all clean

all: $(LIB)

$(LIB): $(ALL_OBJS) | $(BIN_DIR)
	$(CC) $(LDFLAGS) -o $@ $^

# Assemble NASM sources
$(OBJ_DIR)/trit.o: nasm_emulator/src/trit.asm | $(OBJ_DIR)
	$(NASM) $(NASMFLAGS) -o $@ $<

$(OBJ_DIR)/cpu.o: nasm_emulator/src/cpu.asm | $(OBJ_DIR)
	$(NASM) $(NASMFLAGS) -o $@ $<

# Rename cpu.o's exported symbols so they don't clash with cpu_shim.c
$(OBJ_DIR)/cpu_renamed.o: $(OBJ_DIR)/cpu.o
	$(OBJCOPY) $(RENAME_SYMS) $< $@

# Compile C sources
$(OBJ_DIR)/c_api.o: c_api.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) -c -o $@ $<

$(OBJ_DIR)/cpu_shim.o: cpu_shim.c | $(OBJ_DIR)
	$(CC) $(CFLAGS) -c -o $@ $<

$(BIN_DIR):
	mkdir -p $(BIN_DIR)

$(OBJ_DIR):
	mkdir -p $(OBJ_DIR)

clean:
	rm -rf $(OBJ_DIR) $(BIN_DIR)
