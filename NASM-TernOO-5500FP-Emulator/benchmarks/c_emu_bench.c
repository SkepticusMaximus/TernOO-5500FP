/*
 * c_emu_bench.c — 5500FP C/x86 Emulator Benchmark
 *
 * Runs the four benchmark workloads inside our binary-encoded ternary
 * 5500FP emulator and reports wall-clock time and emulated cycle counts.
 *
 * Compiled against the emulator sources in ../c_emulator/
 */

#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#include "../c_emulator/include/cpu.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define REPEAT  10   /* fewer repeats — emulator is slower */

/* Forward declarations from assembler.c */
int  assemble(const char *source, int64_t *program, int max_words, int64_t start_addr);

static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* ── Run a program; verify the result against the Python-oracle value ─────
   The workloads below mirror python_bench.py's builders INSTRUCTION FOR
   INSTRUCTION (same iteration counts, same result registers) so the C leg
   is the identical workload, not a cousin. A mismatch aborts the bench:
   a number from an unverified program is worth nothing. */
static void run_bench(const char *label, const char *workload,
                      const char *src, int repeat,
                      int result_reg, int64_t expected) {
    int64_t program[4096];
    int len = assemble(src, program, 4096, 0);

    double t0 = now_sec();
    int64_t result = 0;
    uint64_t cycles = 0;
    for (int r = 0; r < repeat; r++) {
        cpu_t *cpu = cpu_create(65536);
        cpu_load_program(cpu, program, len, 0);
        cpu_run(cpu);
        result = cpu->reg[result_reg];
        cycles = cpu->cycle_count;
        cpu_destroy(cpu);
    }
    double elapsed = now_sec() - t0;
    if (result != expected) {
        fprintf(stderr, "VERIFY FAIL %s: got %lld want %lld\n",
                workload, (long long)result, (long long)expected);
        exit(1);
    }
    printf("c_emu_5500fp,%s,%d,%.9f,%.3f,%lld,%llu\n",
           workload, repeat, elapsed, elapsed/repeat*1e6,
           (long long)result, (unsigned long long)cycles);
}

/* ── Benchmark programs ───────────────────────────────────────────────────── */

/* Fibonacci(30) iterative — result in R1 */
/* CANONICAL — mirrors python_bench.build_fib30: 29 iterations, result R11 */
static const char *fib30_src =
    "LI   R10, 0\n"   /* a = 0 */
    "LI   R11, 1\n"   /* b = 1 */
    "LI   R12, 29\n"  /* 29 iterations -> R11 = fib(30) */
    "fib_loop:\n"
    "BEQZ R12, fib_done\n"
    "ADD  R13, R10, R11\n"
    "MOV  R10, R11\n"
    "MOV  R11, R13\n"
    "SUBI R12, R12, 1\n"
    "JMP  fib_loop\n"
    "fib_done:\n"
    "HALT\n";

/* CANONICAL — mirrors python_bench.build_fact12: result R11 = 479001600 */
static const char *fact12_src =
    "LI   R10, 12\n"  /* n = 12 */
    "LI   R11, 1\n"   /* acc = 1 */
    "fact_loop:\n"
    "BEQZ R10, fact_done\n"
    "MUL  R11, R11, R10\n"
    "SUBI R10, R10, 1\n"
    "JMP  fact_loop\n"
    "fact_done:\n"
    "HALT\n";

/* CANONICAL — mirrors python_bench.build_array_sum_1000: counting loop,
   result R3 = 500500. (The old memory STW/LDW variant was a DIFFERENT
   workload and stored element 1000 over element 999 — result 499501.) */
static const char *array_sum_src =
    "LI   R3, 0\n"     /* sum = 0 */
    "LI   R4, 1\n"     /* i = 1 */
    "LI   R5, 1001\n"  /* limit */
    "sum_loop:\n"
    "BEQ  R4, R5, sum_done\n"
    "ADD  R3, R3, R4\n"
    "ADDI R4, R4, 1\n"
    "JMP  sum_loop\n"
    "sum_done:\n"
    "HALT\n";

/* CANONICAL — mirrors python_bench.build_arith_loop_3000: 3000 iterations
   of the fib-style ADD/SUB loop, result R12 = 3. (The old 10000-iteration
   MUL/MOD variant contained "MUL R15, R11, 3" — an immediate where the
   assembler wants a register — and ran silently mis-assembled: the source
   of the [ASM] R-1 warning and its unverifiable result.) */
static const char *arith_loop_src =
    "LI   R10, 1\n"    /* a = 1 */
    "LI   R11, 2\n"    /* b = 2 */
    "LI   R12, 0\n"    /* c = 0 */
    "LI   R13, 3000\n" /* count */
    "arith_loop:\n"
    "BEQZ R13, arith_done\n"
    "ADD  R12, R10, R11\n"
    "MOV  R10, R11\n"
    "SUB  R11, R12, R10\n"
    "SUBI R13, R13, 1\n"
    "JMP  arith_loop\n"
    "arith_done:\n"
    "HALT\n";

int main(void) {
    printf("target,workload,iterations,total_sec,avg_us,result,emu_cycles\n");

    run_bench("c_emu", "fibonacci_30",    fib30_src,      REPEAT, 11, 832040);
    run_bench("c_emu", "factorial_12",    fact12_src,     REPEAT, 11, 479001600);
    run_bench("c_emu", "array_sum_1000",  array_sum_src,  REPEAT,  3, 500500);
    run_bench("c_emu", "arith_loop_3000", arith_loop_src, REPEAT, 12, 3);

    return 0;
}
