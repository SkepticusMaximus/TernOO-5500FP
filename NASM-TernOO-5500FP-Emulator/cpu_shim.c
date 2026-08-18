/*
 * cpu_shim.c — ABI bridge between c_api.c (no-arg interface) and cpu.asm
 *              (struct-pointer interface).
 *
 * cpu.asm was designed to be stateless — callers pass a CPU struct pointer
 * (rdi) and optionally a memory pointer (rsi) on every call.  c_api.c
 * expects a stateful no-arg interface (global CPU instance).
 *
 * This shim:
 *   1. Owns a static global CPU struct (CPU_STRUCT_SIZE = 2752 bytes) and
 *      a static global memory array (MEMORY_SIZE = 531441 × int64_t ≈ 4 MB).
 *   2. Declares the "real" NASM functions under renamed symbols (prefix _n_)
 *      — see the Makefile's objcopy --redefine-sym step.
 *   3. Provides the no-arg cpu_init / cpu_reset / cpu_run / cpu_read_reg /
 *      cpu_write_reg / cpu_mem_read / cpu_mem_write that c_api.c links against.
 *
 * Date: 2026-06-19 (Bundle 14 — libternoo.so wiring)
 */

#include <stdint.h>
#include <string.h>

/* ── Constants from ternoo.inc ─────────────────────────────────────────── */
#define CPU_STRUCT_SIZE  2752
#define MEMORY_SIZE      531441
#define CPU_REGS_OFFSET  0

/* ── Renamed NASM function declarations ────────────────────────────────── */
/* These match the NASM ABI after objcopy renames cpu_* → _n_cpu_* in cpu.o */
extern void     _n_cpu_init    (void *cpu_struct, void *mem);
extern void     _n_cpu_reset   (void *cpu_struct);
extern void     _n_cpu_run     (void *cpu_struct, uint64_t max_cycles);
extern uint64_t _n_cpu_read_reg(void *cpu_struct, int64_t reg_idx);
extern void     _n_cpu_write_reg(void *cpu_struct, int64_t reg_idx, uint64_t val);
extern uint64_t _n_cpu_mem_read(void *cpu_struct, int64_t addr);
extern void     _n_cpu_mem_write(void *cpu_struct, int64_t addr, uint64_t val);

/* ── Global state ──────────────────────────────────────────────────────── */
static uint8_t  g_cpu[CPU_STRUCT_SIZE];
static int64_t  g_mem[MEMORY_SIZE];

/* ── No-arg wrappers ────────────────────────────────────────────────────── */

void cpu_init(void) {
    memset(g_cpu, 0, sizeof(g_cpu));
    memset(g_mem, 0, sizeof(g_mem));
    _n_cpu_init(g_cpu, g_mem);
}

void cpu_reset(void) {
    _n_cpu_reset(g_cpu);
}

void cpu_run(void) {
    /* rsi = max_cycles; 0 selects the NASM core's own default (1,000,000).
     * The old one-arg declaration left rsi as caller garbage — the cap was
     * whatever junk sat in the register: junk < cycles -> ran NOTHING,
     * junk huge -> unbounded. Bundle-14's "fully operational" bridge had
     * only ever been tested on register pokes, never a run. */
    _n_cpu_run(g_cpu, 0);
}

uint64_t cpu_read_reg(int reg) {
    return _n_cpu_read_reg(g_cpu, (int64_t)reg);
}

void cpu_write_reg(int reg, uint64_t val) {
    _n_cpu_write_reg(g_cpu, (int64_t)reg, val);
}

uint64_t cpu_mem_read(uint64_t addr) {
    return _n_cpu_mem_read(g_cpu, (int64_t)addr);
}

/* Raw INSTRUCTION port. cpu_mem_write is a DATA port — it clamps values
 * to the 24-trit word range, and BET-packed instructions (op trits live
 * at bits 40+) always exceed it, so instructions could never enter memory
 * through the exported ABI. The core fetches from g_mem (wired in by
 * cpu_init), so a raw store IS cpu_load_program's write, word for word. */
void cpu_load_word(uint64_t addr, uint64_t val) {
    if (addr < MEMORY_SIZE)
        g_mem[addr] = (int64_t)val;
}

void cpu_mem_write(uint64_t addr, uint64_t val) {
    _n_cpu_mem_write(g_cpu, (int64_t)addr, val);
}
