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

/* ── Run a program and return (wall_sec, cycles, result_reg1) ─────────────── */
static void run_bench(const char *label, const char *workload,
                      const char *src, int repeat) {
    int64_t program[4096];
    int len = assemble(src, program, 4096, 0);

    double t0 = now_sec();
    int64_t result = 0;
    uint64_t cycles = 0;
    for (int r = 0; r < repeat; r++) {
        cpu_t *cpu = cpu_create(65536);
        cpu_load_program(cpu, program, len, 0);
        cpu_run(cpu);
        result = cpu->reg[1];   /* result in R1 by convention */
        cycles = cpu->cycle_count;
        cpu_destroy(cpu);
    }
    double elapsed = now_sec() - t0;
    printf("c_emu_5500fp,%s,%d,%.9f,%.3f,%lld,%llu\n",
           workload, repeat, elapsed, elapsed/repeat*1e6,
           (long long)result, (unsigned long long)cycles);
}

/* ── Benchmark programs ───────────────────────────────────────────────────── */

/* Fibonacci(30) iterative — result in R1 */
static const char *fib30_src =
    "LI   R10, 0\n"   /* a = 0 */
    "LI   R11, 1\n"   /* b = 1 */
    "LI   R12, 30\n"  /* count = 30 */
    "fib_loop:\n"
    "BEQZ R12, fib_done\n"
    "ADD  R13, R10, R11\n"
    "MOV  R10, R11\n"
    "MOV  R11, R13\n"
    "SUBI R12, R12, 1\n"
    "JMP  fib_loop\n"
    "fib_done:\n"
    "MOV  R1, R11\n"  /* result = fib(30) */
    "HALT\n";

/* Factorial(12) iterative — result in R1 */
static const char *fact12_src =
    "LI   R10, 12\n"  /* n = 12 */
    "LI   R11, 1\n"   /* acc = 1 */
    "fact_loop:\n"
    "BEQZ R10, fact_done\n"
    "MUL  R11, R11, R10\n"
    "SUBI R10, R10, 1\n"
    "JMP  fact_loop\n"
    "fact_done:\n"
    "MOV  R1, R11\n"
    "HALT\n";

/* Array sum: store 1..1000 in memory, sum them — result in R1 */
static const char *array_sum_src =
    "LI   R20, 500\n"   /* base address */
    "LI   R21, 1\n"     /* i = 1 */
    "LI   R22, 1000\n"  /* limit */
    "LI   R23, 0\n"     /* idx = 0 */
    "store_loop:\n"
    "BEQ  R21, R22, store_done\n"
    "ADD  R24, R20, R23\n"
    "STW  R21, R24, 0\n"
    "ADDI R21, R21, 1\n"
    "ADDI R23, R23, 1\n"
    "JMP  store_loop\n"
    "store_done:\n"
    "STW  R22, R24, 0\n"   /* store last element */
    "LI   R2, 0\n"         /* sum = 0 */
    "LI   R3, 0\n"         /* j = 0 */
    "LI   R4, 1000\n"      /* count */
    "sum_loop:\n"
    "BEQ  R3, R4, sum_done\n"
    "ADD  R5, R20, R3\n"
    "LDW  R6, R5, 0\n"
    "ADD  R2, R2, R6\n"
    "ADDI R3, R3, 1\n"
    "JMP  sum_loop\n"
    "sum_done:\n"
    "MOV  R1, R2\n"
    "HALT\n";

/* Arithmetic loop: 10000 iterations of ADD+MUL with modular reduction */
static const char *arith_loop_src =
    "LI   R10, 1\n"      /* a = 1 */
    "LI   R11, 2\n"      /* b = 2 */
    "LI   R12, 0\n"      /* c = 0 */
    "LI   R13, 10000\n"  /* count */
    "LI   R14, 1000\n"   /* modulus */
    "arith_loop:\n"
    "BEQZ R13, arith_done\n"
    "ADD  R12, R10, R11\n"
    "MOV  R10, R11\n"
    "MUL  R15, R11, 3\n"
    "MOV  R11, R15\n"
    "BGTZ R11, check_mod\n"
    "JMP  arith_next\n"
    "check_mod:\n"
    "CMPI R16, R11, 1000\n"
    "BGTZ R16, do_mod\n"
    "JMP  arith_next\n"
    "do_mod:\n"
    "MOD  R11, R11, R14\n"
    "ADDI R11, R11, 1\n"
    "arith_next:\n"
    "SUBI R13, R13, 1\n"
    "JMP  arith_loop\n"
    "arith_done:\n"
    "MOV  R1, R12\n"
    "HALT\n";

int main(void) {
    printf("target,workload,iterations,total_sec,avg_us,result,emu_cycles\n");

    run_bench("c_emu", "fibonacci_30",  fib30_src,      REPEAT);
    run_bench("c_emu", "factorial_12",  fact12_src,     REPEAT);
    run_bench("c_emu", "array_sum_1000",array_sum_src,  REPEAT);
    run_bench("c_emu", "arith_loop_10000", arith_loop_src, REPEAT);

    return 0;
}
