/*
 * cpu.h — 5500FP CPU State and Emulator Core
 *
 * CPU state: 81 registers + PC + flags + memory
 */

#ifndef CPU_H
#define CPU_H

#include "trit.h"
#include "isa.h"

/* -----------------------------------------------------------------------
 * CPU state structure
 * --------------------------------------------------------------------- */
typedef struct {
    int64_t  reg[NUM_REGISTERS];   /* R0..R80; R0 always reads as 0       */
    int64_t  pc;                   /* Program counter (tryte address)     */
    int64_t  flags;                /* Status flags: -1=neg, 0=zero, 1=pos */

    /* Memory: stored as int64 words, each representing one 24-trit word  */
    int64_t *mem;                  /* Heap-allocated memory array         */
    uint32_t mem_size;             /* Size in words                       */

    /* Execution state */
    int      halted;               /* Non-zero if HALT executed           */
    uint64_t cycle_count;          /* Total cycles executed               */

    /* Atomic reservation (for LDXA/STXA) */
    int64_t  reservation_addr;     /* -1 if no reservation active         */
} cpu_t;

/* -----------------------------------------------------------------------
 * CPU lifecycle
 * --------------------------------------------------------------------- */
cpu_t *cpu_create(uint32_t mem_size_words);
void   cpu_destroy(cpu_t *cpu);
void   cpu_reset(cpu_t *cpu);

/* Load a program (array of int64 words) into memory at given address */
void   cpu_load_program(cpu_t *cpu, const int64_t *prog, uint32_t len, int64_t start_addr);

/* -----------------------------------------------------------------------
 * Execution
 * --------------------------------------------------------------------- */
void   cpu_step(cpu_t *cpu);
void   cpu_run(cpu_t *cpu);
void   cpu_run_n(cpu_t *cpu, uint64_t n_cycles);

/* -----------------------------------------------------------------------
 * Debug helpers
 * --------------------------------------------------------------------- */
void   cpu_dump_registers(const cpu_t *cpu);
void   cpu_dump_memory(const cpu_t *cpu, int64_t start, int64_t count);

#endif /* CPU_H */
