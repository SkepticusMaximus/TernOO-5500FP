/*
 * c_api.c — the seven-symbol ternoo_* ABI over the C core, matching the
 * NASM bin/libternoo.so surface exactly, so ternoo_bridge.py can drive
 * EITHER core interchangeably — the captain's redundancy doctrine at the
 * ABI level. Additive extras the NASM side lacks: ternoo_asm (text ->
 * encoded words in the C core's OWN dialect — the cores are one
 * architecture, two instruction dialects; words do not interchange) and
 * ternoo_cycles (emulated-cycle count of the last run).
 */
#include "cpu.h"

int assemble(const char *source, int64_t *program, int max_words,
             int64_t start_addr);

#define TERNOO_MEM_WORDS 65536
static cpu_t *g_cpu = NULL;

void ternoo_init(void)
{
    if (!g_cpu)
        g_cpu = cpu_create(TERNOO_MEM_WORDS);
}

void ternoo_reset(void)
{
    if (g_cpu)
        cpu_destroy(g_cpu);
    g_cpu = cpu_create(TERNOO_MEM_WORDS);
}

void ternoo_run(void)
{
    if (g_cpu)
        cpu_run(g_cpu);
}

uint64_t ternoo_read_reg(int reg)
{
    if (!g_cpu || reg < 0 || reg >= NUM_REGISTERS)
        return 0;
    return (uint64_t)g_cpu->reg[reg];
}

void ternoo_write_reg(int reg, uint64_t val)
{
    if (g_cpu && reg > 0 && reg < NUM_REGISTERS)
        g_cpu->reg[reg] = (int64_t)val;
}

void ternoo_mem_write(uint64_t addr, uint64_t val)
{
    if (g_cpu && addr < TERNOO_MEM_WORDS)
        g_cpu->mem[addr] = (int64_t)val;
}

uint64_t ternoo_mem_read(uint64_t addr)
{
    if (!g_cpu || addr >= TERNOO_MEM_WORDS)
        return 0;
    return (uint64_t)g_cpu->mem[addr];
}

uint64_t ternoo_cycles(void)
{
    return g_cpu ? g_cpu->cycle_count : 0;
}

int ternoo_asm(const char *source, int64_t *out_words, int max_words)
{
    return assemble(source, out_words, max_words, 0);
}
