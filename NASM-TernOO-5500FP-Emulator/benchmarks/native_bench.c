/*
 * native_bench.c — Native x86 C benchmark
 * Runs identical workloads to the emulator benchmarks but directly in C.
 * This establishes the bare-metal baseline.
 *
 * Workloads:
 *   1. fib(30)        — recursive Fibonacci
 *   2. factorial(12)  — iterative factorial
 *   3. array_sum(N)   — sum of array[0..N-1]
 *   4. arith_loop(N)  — tight ADD+MUL loop N iterations
 */

#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdint.h>

#define ARRAY_N      1000
#define ARITH_N      10000
#define FIB_N        30
#define FACT_N       12
#define REPEAT       100   /* repeat each benchmark this many times for stable timing */

/* ── Timing helper ─────────────────────────────────────────────────────────── */
static double now_sec(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

/* ── Workload 1: Fibonacci ─────────────────────────────────────────────────── */
static long long fib(int n) {
    if (n <= 1) return n;
    long long a = 0, b = 1;
    for (int i = 2; i <= n; i++) {
        long long t = a + b;
        a = b;
        b = t;
    }
    return b;
}

/* ── Workload 2: Factorial ─────────────────────────────────────────────────── */
static long long factorial(int n) {
    long long r = 1;
    for (int i = 2; i <= n; i++) r *= i;
    return r;
}

/* ── Workload 3: Array sum ─────────────────────────────────────────────────── */
static long long array_sum(int n) {
    long long *arr = (long long *)malloc(n * sizeof(long long));
    for (int i = 0; i < n; i++) arr[i] = i + 1;
    long long s = 0;
    for (int i = 0; i < n; i++) s += arr[i];
    free(arr);
    return s;
}

/* ── Workload 4: Arithmetic loop ───────────────────────────────────────────── */
static long long arith_loop(int n) {
    long long a = 1, b = 2, c = 0;
    for (int i = 0; i < n; i++) {
        c = a + b;
        a = b;
        b = c * 3;
        if (b > 1000000) b = b % 1000 + 1;
    }
    return c;
}

/* ── Main ──────────────────────────────────────────────────────────────────── */
int main(void) {
    double t0, t1, elapsed;
    long long result;
    volatile long long sink; /* prevent optimisation */

    printf("target,workload,iterations,total_sec,avg_us,result\n");

    /* Fibonacci */
    t0 = now_sec();
    for (int r = 0; r < REPEAT; r++) { result = fib(FIB_N); sink = result; }
    t1 = now_sec();
    elapsed = t1 - t0;
    printf("native_c,fibonacci_%d,%d,%.9f,%.3f,%lld\n",
           FIB_N, REPEAT, elapsed, elapsed/REPEAT*1e6, result);

    /* Factorial */
    t0 = now_sec();
    for (int r = 0; r < REPEAT; r++) { result = factorial(FACT_N); sink = result; }
    t1 = now_sec();
    elapsed = t1 - t0;
    printf("native_c,factorial_%d,%d,%.9f,%.3f,%lld\n",
           FACT_N, REPEAT, elapsed, elapsed/REPEAT*1e6, result);

    /* Array sum */
    t0 = now_sec();
    for (int r = 0; r < REPEAT; r++) { result = array_sum(ARRAY_N); sink = result; }
    t1 = now_sec();
    elapsed = t1 - t0;
    printf("native_c,array_sum_%d,%d,%.9f,%.3f,%lld\n",
           ARRAY_N, REPEAT, elapsed, elapsed/REPEAT*1e6, result);

    /* Arithmetic loop */
    t0 = now_sec();
    for (int r = 0; r < REPEAT; r++) { result = arith_loop(ARITH_N); sink = result; }
    t1 = now_sec();
    elapsed = t1 - t0;
    printf("native_c,arith_loop_%d,%d,%.9f,%.3f,%lld\n",
           ARITH_N, REPEAT, elapsed, elapsed/REPEAT*1e6, result);

    (void)sink;
    return 0;
}
