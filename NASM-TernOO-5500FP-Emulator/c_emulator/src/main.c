/*
 * main.c — 5500FP Emulator Driver
 *
 * Usage:
 *   ./5500fp [--run <file.t5asm>]    Run an assembly file
 *   ./5500fp --demo                  Run built-in demo programs
 *   ./5500fp --test                  Run self-tests
 *   ./5500fp --interactive           Interactive assembler/debugger
 */

#define _GNU_SOURCE
#include "../include/cpu.h"
#include "../include/pigart.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Forward declarations from assembler.c */
int  assemble(const char *source, int64_t *program, int max_words, int64_t start_addr);
void disassemble_program(const int64_t *prog, int len, int64_t start_addr);
void disassemble(int64_t inst, int64_t addr, char *out, int out_len);

/* -----------------------------------------------------------------------
 * Demo programs (inline assembly source)
 * --------------------------------------------------------------------- */

/* Demo 1: Hello World via SYSCALL (print chars) */
static const char *demo_hello =
    "    LI   R1, 3\n"   /* syscall PRINT_CHAR */
    "    LI   R2, 72\n"  /* 'H' */
    "    SYSCALL\n"
    "    LI   R2, 105\n" /* 'i' */
    "    SYSCALL\n"
    "    LI   R2, 33\n"  /* '!' */
    "    SYSCALL\n"
    "    LI   R1, 6\n"   /* PRINT_NL */
    "    SYSCALL\n"
    "    HALT\n";

/* Demo 2: Fibonacci sequence (first 10 terms) */
static const char *demo_fibonacci =
    "    LI   R10, 0\n"  /* a = fib[0] = 0 */
    "    LI   R11, 1\n"  /* b = fib[1] = 1 */
    "    LI   R12, 10\n" /* count = 10 */
    "fib_loop:\n"
    "    BEQZ R12, fib_done\n"
    "    LI   R1, 1\n"
    "    MOV  R2, R10\n"
    "    SYSCALL\n"
    "    LI   R1, 6\n"
    "    SYSCALL\n"
    "    ADD  R13, R10, R11\n" /* temp = a + b */
    "    MOV  R10, R11\n"      /* a = b */
    "    MOV  R11, R13\n"      /* b = temp */
    "    SUBI R12, R12, 1\n"
    "    JMP  fib_loop\n"
    "fib_done:\n"
    "    HALT\n";

/* Demo 3: Ternary arithmetic showcase */
/* R1=13 (111 in ternary), R2=-4 (T01 in ternary)
   Results: ADD=9, SUB=17, MUL=-52, INV=-13, SHLI=39 */
static const char *demo_ternary_arith =
    "    LI   R1, 13\n"
    "    LI   R2, -4\n"
    "    ADD  R3, R1, R2\n"   /* R3 = 9  */
    "    SUB  R4, R1, R2\n"   /* R4 = 17 */
    "    MUL  R5, R1, R2\n"   /* R5 = -52 */
    "    INV  R6, R1\n"       /* R6 = -13 */
    "    ABS  R7, R2\n"       /* R7 = 4  */
    "    MIN  R8, R1, R2\n"   /* R8 = -4 */
    "    MAX  R9, R1, R2\n"   /* R9 = 13 */
    "    SIGN R10, R2\n"      /* R10 = -1 */
    "    SHLI R11, R1, 1\n"   /* R11 = 39 */
    "    SHRI R12, R11, 1\n"  /* R12 = 13 */
    "    LI   R1, 1\n"
    "    MOV  R2, R3\n"
    "    SYSCALL\n"
    "    LI   R1, 6\n"
    "    SYSCALL\n"
    "    LI   R1, 1\n"
    "    MOV  R2, R4\n"
    "    SYSCALL\n"
    "    LI   R1, 6\n"
    "    SYSCALL\n"
    "    LI   R1, 1\n"
    "    MOV  R2, R5\n"
    "    SYSCALL\n"
    "    LI   R1, 6\n"
    "    SYSCALL\n"
    "    LI   R1, 1\n"
    "    MOV  R2, R6\n"
    "    SYSCALL\n"
    "    LI   R1, 6\n"
    "    SYSCALL\n"
    "    LI   R1, 1\n"
    "    MOV  R2, R11\n"
    "    SYSCALL\n"
    "    LI   R1, 6\n"
    "    SYSCALL\n"
    "    HALT\n";

/* Demo 4: Factorial (iterative) - computes 6! = 720 */
static const char *demo_factorial =
    "    LI   R1, 6\n"
    "    LI   R2, 1\n"
    "fact_loop:\n"
    "    BEQZ R1, fact_done\n"
    "    MUL  R2, R2, R1\n"
    "    SUBI R1, R1, 1\n"
    "    JMP  fact_loop\n"
    "fact_done:\n"
    "    LI   R1, 1\n"
    "    SYSCALL\n"
    "    LI   R1, 6\n"
    "    SYSCALL\n"
    "    HALT\n";

/* Demo 5: Memory load/store and array sum - stores [1,2,3,4,5], sums to 15 */
static const char *demo_array_sum =
    "    LI   R10, 100\n"
    "    LI   R1, 1\n"
    "    STW  R1, R10, 0\n"
    "    LI   R1, 2\n"
    "    STW  R1, R10, 1\n"
    "    LI   R1, 3\n"
    "    STW  R1, R10, 2\n"
    "    LI   R1, 4\n"
    "    STW  R1, R10, 3\n"
    "    LI   R1, 5\n"
    "    STW  R1, R10, 4\n"
    "    LI   R2, 0\n"
    "    LI   R3, 0\n"
    "    LI   R4, 5\n"
    "sum_loop:\n"
    "    BEQ  R3, R4, sum_done\n"
    "    ADD  R5, R10, R3\n"
    "    LDW  R6, R5, 0\n"
    "    ADD  R2, R2, R6\n"
    "    ADDI R3, R3, 1\n"
    "    JMP  sum_loop\n"
    "sum_done:\n"
    "    LI   R1, 1\n"
    "    SYSCALL\n"
    "    LI   R1, 6\n"
    "    SYSCALL\n"
    "    HALT\n";

/* -----------------------------------------------------------------------
 * Run a demo program
 * --------------------------------------------------------------------- */
static void run_demo(const char *name, const char *source, int verbose) {
    printf("\n=== Demo: %s ===\n", name);

    int64_t program[1024];
    int len = assemble(source, program, 1024, 0);

    if (verbose) {
        printf("--- Assembled %d instructions ---\n", len);
        disassemble_program(program, len, 0);
        printf("--- Execution output ---\n");
    }

    cpu_t *cpu = cpu_create(65536);
    cpu_load_program(cpu, program, len, 0);
    cpu_run(cpu);

    if (verbose) {
        printf("\n--- Register state after execution ---\n");
        cpu_dump_registers(cpu);
    }

    printf("[Completed in %llu cycles]\n", (unsigned long long)cpu->cycle_count);
    cpu_destroy(cpu);
}

/* -----------------------------------------------------------------------
 * Self-test suite
 * --------------------------------------------------------------------- */
static int tests_passed = 0;
static int tests_failed = 0;

static void test_assert(const char *name, int64_t got, int64_t expected) {
    if (got == expected) {
        printf("  PASS: %-40s got=%lld\n", name, (long long)got);
        tests_passed++;
    } else {
        printf("  FAIL: %-40s got=%lld, expected=%lld\n",
               name, (long long)got, (long long)expected);
        tests_failed++;
    }
}

static void run_tests(void) {
    printf("\n=== 5500FP Self-Test Suite ===\n");

    /* Test 1: Trit encoding/decoding */
    printf("\n-- Trit Encoding Tests --\n");
    test_assert("encode(+1)=01",  trit_encode(1),  1);
    test_assert("encode(0)=00",   trit_encode(0),  0);
    test_assert("encode(-1)=11",  trit_encode(-1), 3);
    test_assert("decode(01)=+1",  trit_decode(1),  1);
    test_assert("decode(00)=0",   trit_decode(0),  0);
    test_assert("decode(11)=-1",  trit_decode(3), -1);

    /* Test 2: int64 <-> tword_enc round-trip */
    printf("\n-- Int64 <-> Encoded Round-Trip Tests --\n");
    int64_t vals[] = {0, 1, -1, 13, -13, 364, -364, 100, -100, 12345, -12345};
    for (int i = 0; i < 11; i++) {
        tword_enc enc = int64_to_tword_enc(vals[i]);
        int64_t back  = tword_enc_to_int64(enc);
        char name[64];
        snprintf(name, sizeof(name), "round-trip(%lld)", (long long)vals[i]);
        test_assert(name, back, vals[i]);
    }

    /* Test 3: ALU operations via emulator */
    printf("\n-- ALU Emulator Tests --\n");

    struct { const char *name; const char *src; int64_t expected_r3; } alu_tests[] = {
        { "ADD 7+5=12",    "LI R1,7\nLI R2,5\nADD R3,R1,R2\nHALT\n", 12 },
        { "SUB 7-5=2",     "LI R1,7\nLI R2,5\nSUB R3,R1,R2\nHALT\n", 2  },
        { "MUL 7*5=35",    "LI R1,7\nLI R2,5\nMUL R3,R1,R2\nHALT\n", 35 },
        { "DIV 35/5=7",    "LI R1,35\nLI R2,5\nDIV R3,R1,R2\nHALT\n", 7 },
        { "INV -13",       "LI R1,13\nINV R3,R1\nHALT\n", -13 },
        { "ABS -7=7",      "LI R1,-7\nABS R3,R1\nHALT\n", 7  },
        { "MIN(-3,5)=-3",  "LI R1,-3\nLI R2,5\nMIN R3,R1,R2\nHALT\n", -3 },
        { "MAX(-3,5)=5",   "LI R1,-3\nLI R2,5\nMAX R3,R1,R2\nHALT\n", 5  },
        { "SIGN(-7)=-1",   "LI R1,-7\nSIGN R3,R1\nHALT\n", -1 },
        { "SIGN(7)=1",     "LI R1,7\nSIGN R3,R1\nHALT\n",   1 },
        { "SIGN(0)=0",     "LI R1,0\nSIGN R3,R1\nHALT\n",   0 },
        { "SHLI 3<<1=9",   "LI R1,3\nSHLI R3,R1,1\nHALT\n", 9 },
        { "SHRI 9>>1=3",   "LI R1,9\nSHRI R3,R1,1\nHALT\n", 3 },
        { "ADDI 5+3=8",    "LI R1,5\nADDI R3,R1,3\nHALT\n", 8 },
        { "CMPI 5>3=1",    "LI R1,5\nCMPI R3,R1,3\nHALT\n", 1 },
        { "CMPI 3>5=-1",   "LI R1,3\nCMPI R3,R1,5\nHALT\n",-1 },
        { NULL, NULL, 0 }
    };

    for (int i = 0; alu_tests[i].name; i++) {
        int64_t prog[64];
        int len = assemble(alu_tests[i].src, prog, 64, 0);
        cpu_t *cpu = cpu_create(4096);
        cpu_load_program(cpu, prog, len, 0);
        cpu_run(cpu);
        test_assert(alu_tests[i].name, cpu->reg[3], alu_tests[i].expected_r3);
        cpu_destroy(cpu);
    }

    /* Test 4: Memory load/store */
    printf("\n-- Memory Tests --\n");
    {
        const char *src =
            "LI R1, 42\n"
            "LI R2, 50\n"
            "STW R1, R2, 0\n"
            "LDW R3, R2, 0\n"
            "HALT\n";
        int64_t prog[64];
        int len = assemble(src, prog, 64, 0);
        cpu_t *cpu = cpu_create(4096);
        cpu_load_program(cpu, prog, len, 0);
        cpu_run(cpu);
        test_assert("STW/LDW round-trip 42", cpu->reg[3], 42);
        cpu_destroy(cpu);
    }

    /* Test 5: Branch and loop */
    printf("\n-- Branch/Loop Tests --\n");
    {
        /* Sum 1..5 = 15 */
        const char *src =
            "LI R1, 1\n"
            "LI R2, 0\n"
            "LI R3, 5\n"
            "loop:\n"
            "ADD R2, R2, R1\n"
            "ADDI R1, R1, 1\n"
            "BLE R1, R3, loop\n"
            "HALT\n";
        int64_t prog[64];
        int len = assemble(src, prog, 64, 0);
        cpu_t *cpu = cpu_create(4096);
        cpu_load_program(cpu, prog, len, 0);
        cpu_run(cpu);
        test_assert("Sum 1..5=15", cpu->reg[2], 15);
        cpu_destroy(cpu);
    }

    /* Test 5b: Nested CALL/RET — return-address stack (R80 hazard fix) */
    printf("\n-- Nested CALL/RET Tests --\n");
    {
        /* Three levels; each frame adds a distinct magnitude before AND after
         * its inner call, so the result only comes out right if every RET
         * resumes at the correct site: 0 +1 +100 +5 +1000 +10 = 1116. */
        const char *src =
            "LI R2, 0\n"
            "CALL a\n"
            "HALT\n"
            "a:\n  ADDI R2, R2, 1\n  CALL b\n  ADDI R2, R2, 10\n  RET\n"
            "b:\n  ADDI R2, R2, 100\n  CALL c\n  ADDI R2, R2, 1000\n  RET\n"
            "c:\n  ADDI R2, R2, 5\n  RET\n";
        int64_t prog[64];
        int len = assemble(src, prog, 64, 0);
        cpu_t *cpu = cpu_create(4096);
        cpu_load_program(cpu, prog, len, 0);
        cpu_run_n(cpu, 100000);
        test_assert("Nested CALL/RET 3 levels resume correctly",
                    cpu->reg[2], 1116);
        cpu_destroy(cpu);
    }
    {
        /* Deep recursion to depth 150 (well past the old 1-level limit, under
         * RA_STACK_MAX=1024): rec increments R2 each frame until R2==R3, then
         * unwinds. Bounded run so a regression fails loud instead of hanging. */
        const char *src =
            "LI R2, 0\n"
            "LI R3, 150\n"
            "CALL rec\n"
            "HALT\n"
            "rec:\n"
            "  ADDI R2, R2, 1\n"
            "  BGE R2, R3, done\n"
            "  CALL rec\n"
            "done:\n"
            "  RET\n";
        int64_t prog[64];
        int len = assemble(src, prog, 64, 0);
        cpu_t *cpu = cpu_create(4096);
        cpu_load_program(cpu, prog, len, 0);
        cpu_run_n(cpu, 1000000);
        test_assert("Deep recursion depth 150 unwinds", cpu->reg[2], 150);
        test_assert("Deep recursion halted (stack balanced)",
                    (int64_t)cpu->halted, 1);
        cpu_destroy(cpu);
    }

    /* Test 5c: Runtime value substrate — variable-length strings */
    printf("\n-- String Runtime Tests --\n");
    {
        struct { const char *name; const char *src; int reg; int64_t exp; } st[] = {
        { "STR_FROMBUF+LEN 'hello'=5",
          "LI R1,41\nLI R2,sbuf\nSYSCALL\nMOV R5,R1\n"
          "LI R1,42\nMOV R2,R5\nSYSCALL\nMOV R3,R1\nHALT\n"
          "sbuf:\n.word 104\n.word 101\n.word 108\n.word 108\n.word 111\n.word 0\n",
          3, 5 },
        { "STR_CONCAT len 'ab'+'cd'=4",
          "LI R1,41\nLI R2,b1\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,b2\nSYSCALL\nMOV R6,R1\n"
          "LI R1,45\nMOV R2,R5\nMOV R3,R6\nSYSCALL\nMOV R7,R1\n"
          "LI R1,42\nMOV R2,R7\nSYSCALL\nMOV R3,R1\nHALT\n"
          "b1:\n.word 97\n.word 98\n.word 0\nb2:\n.word 99\n.word 100\n.word 0\n",
          3, 4 },
        { "STR_CONCAT char[2]='c'",
          "LI R1,41\nLI R2,b1\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,b2\nSYSCALL\nMOV R6,R1\n"
          "LI R1,45\nMOV R2,R5\nMOV R3,R6\nSYSCALL\nMOV R7,R1\n"
          "LI R1,43\nMOV R2,R7\nLI R3,2\nSYSCALL\nMOV R4,R1\nHALT\n"
          "b1:\n.word 97\n.word 98\n.word 0\nb2:\n.word 99\n.word 100\n.word 0\n",
          4, 99 },
        { "STR_EQ equal=1",
          "LI R1,41\nLI R2,b1\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,b2\nSYSCALL\nMOV R6,R1\n"
          "LI R1,46\nMOV R2,R5\nMOV R3,R6\nSYSCALL\nMOV R3,R1\nHALT\n"
          "b1:\n.word 97\n.word 98\n.word 0\nb2:\n.word 97\n.word 98\n.word 0\n",
          3, 1 },
        { "STR_EQ unequal=0",
          "LI R1,41\nLI R2,b1\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,b2\nSYSCALL\nMOV R6,R1\n"
          "LI R1,46\nMOV R2,R5\nMOV R3,R6\nSYSCALL\nMOV R3,R1\nHALT\n"
          "b1:\n.word 97\n.word 98\n.word 0\nb2:\n.word 97\n.word 99\n.word 0\n",
          3, 0 },
        { "STR_SUB('hello',1,3) len=3",
          "LI R1,41\nLI R2,sbuf\nSYSCALL\nMOV R5,R1\n"
          "LI R1,47\nMOV R2,R5\nLI R3,1\nLI R4,3\nSYSCALL\nMOV R6,R1\n"
          "LI R1,42\nMOV R2,R6\nSYSCALL\nMOV R3,R1\nHALT\n"
          "sbuf:\n.word 104\n.word 101\n.word 108\n.word 108\n.word 111\n.word 0\n",
          3, 3 },
        { "STR_SUB('hello',1,3) char[0]='e'",
          "LI R1,41\nLI R2,sbuf\nSYSCALL\nMOV R5,R1\n"
          "LI R1,47\nMOV R2,R5\nLI R3,1\nLI R4,3\nSYSCALL\nMOV R6,R1\n"
          "LI R1,43\nMOV R2,R6\nLI R3,0\nSYSCALL\nMOV R3,R1\nHALT\n"
          "sbuf:\n.word 104\n.word 101\n.word 108\n.word 108\n.word 111\n.word 0\n",
          3, 101 },
        { "STR_INDEXOF('hello','ll')=2",
          "LI R1,41\nLI R2,sbuf\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,nbuf\nSYSCALL\nMOV R6,R1\n"
          "LI R1,48\nMOV R2,R5\nMOV R3,R6\nLI R4,0\nSYSCALL\nMOV R3,R1\nHALT\n"
          "sbuf:\n.word 104\n.word 101\n.word 108\n.word 108\n.word 111\n.word 0\n"
          "nbuf:\n.word 108\n.word 108\n.word 0\n",
          3, 2 },
        { "STR_ALLOC+SETCHAR+CHAR round-trips",
          "LI R1,40\nLI R2,3\nSYSCALL\nMOV R5,R1\n"
          "LI R1,44\nMOV R2,R5\nLI R3,0\nLI R4,88\nSYSCALL\n"
          "LI R1,43\nMOV R2,R5\nLI R3,0\nSYSCALL\nMOV R3,R1\nHALT\n",
          3, 88 },
        { "STR_UPPER 'ab' -> char[0]='A'",
          "LI R1,41\nLI R2,ub\nSYSCALL\nMOV R5,R1\n"
          "LI R1,49\nMOV R2,R5\nSYSCALL\nMOV R6,R1\n"
          "LI R1,43\nMOV R2,R6\nLI R3,0\nSYSCALL\nMOV R3,R1\nHALT\n"
          "ub:\n.word 97\n.word 98\n.word 0\n",
          3, 65 },
        { "STR_LOWER 'AB' -> char[0]='a'",
          "LI R1,41\nLI R2,lb\nSYSCALL\nMOV R5,R1\n"
          "LI R1,50\nMOV R2,R5\nSYSCALL\nMOV R6,R1\n"
          "LI R1,43\nMOV R2,R6\nLI R3,0\nSYSCALL\nMOV R3,R1\nHALT\n"
          "lb:\n.word 65\n.word 66\n.word 0\n",
          3, 97 },
        { "STR_TRIM ' hi ' -> len 2",
          "LI R1,41\nLI R2,tb\nSYSCALL\nMOV R5,R1\n"
          "LI R1,51\nMOV R2,R5\nSYSCALL\nMOV R6,R1\n"
          "LI R1,42\nMOV R2,R6\nSYSCALL\nMOV R3,R1\nHALT\n"
          "tb:\n.word 32\n.word 104\n.word 105\n.word 32\n.word 0\n",
          3, 2 },
        { "STR_REPLACE 'axbxc'/x/- (cs) char[1]='-'",
          "LI R1,41\nLI R2,rt\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,rf\nSYSCALL\nMOV R6,R1\n"
          "LI R1,41\nLI R2,rw\nSYSCALL\nMOV R7,R1\n"
          "LI R1,52\nMOV R2,R5\nMOV R3,R6\nMOV R4,R7\nLI R5,0\nSYSCALL\nMOV R8,R1\n"
          "LI R1,43\nMOV R2,R8\nLI R3,1\nSYSCALL\nMOV R3,R1\nHALT\n"
          "rt:\n.word 97\n.word 120\n.word 98\n.word 120\n.word 99\n.word 0\n"
          "rf:\n.word 120\n.word 0\n"
          "rw:\n.word 45\n.word 0\n",
          3, 45 },
        { "STR_REPLACE 'aXa'/x/y (ci) char[1]='y'",
          "LI R1,41\nLI R2,ct\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,cf\nSYSCALL\nMOV R6,R1\n"
          "LI R1,41\nLI R2,cw\nSYSCALL\nMOV R7,R1\n"
          "LI R1,52\nMOV R2,R5\nMOV R3,R6\nMOV R4,R7\nLI R5,1\nSYSCALL\nMOV R8,R1\n"
          "LI R1,43\nMOV R2,R8\nLI R3,1\nSYSCALL\nMOV R3,R1\nHALT\n"
          "ct:\n.word 97\n.word 88\n.word 97\n.word 0\n"
          "cf:\n.word 120\n.word 0\n"
          "cw:\n.word 121\n.word 0\n",
          3, 121 },
        };
        for (unsigned i = 0; i < sizeof(st)/sizeof(st[0]); i++) {
            int64_t prog[128];
            int len = assemble(st[i].src, prog, 128, 0);
            cpu_t *cpu = cpu_create(65536);
            cpu_load_program(cpu, prog, len, 0);
            cpu_run_n(cpu, 100000);
            test_assert(st[i].name, cpu->reg[st[i].reg], st[i].exp);
            cpu_destroy(cpu);
        }
    }

    /* Test 5d: Runtime value substrate — fixed-length lists */
    printf("\n-- List Runtime Tests --\n");
    {
        struct { const char *name; const char *src; int reg; int64_t exp; } lt[] = {
        { "LIST_ALLOC+SET+GET [1]=42",
          "LI R1,60\nLI R2,3\nSYSCALL\nMOV R5,R1\n"
          "LI R1,63\nMOV R2,R5\nLI R3,1\nLI R4,42\nSYSCALL\n"
          "LI R1,62\nMOV R2,R5\nLI R3,1\nSYSCALL\nMOV R3,R1\nHALT\n", 3, 42 },
        { "LIST_LEN alloc 5 = 5",
          "LI R1,60\nLI R2,5\nSYSCALL\nMOV R5,R1\n"
          "LI R1,61\nMOV R2,R5\nSYSCALL\nMOV R3,R1\nHALT\n", 3, 5 },
        { "LIST_GET out-of-bounds = 0",
          "LI R1,60\nLI R2,2\nSYSCALL\nMOV R5,R1\n"
          "LI R1,62\nMOV R2,R5\nLI R3,9\nSYSCALL\nMOV R3,R1\nHALT\n", 3, 0 },
        { "LIST_APPEND grows length to 3",
          "LI R1,60\nLI R2,2\nSYSCALL\nMOV R5,R1\n"
          "LI R1,63\nMOV R2,R5\nLI R3,0\nLI R4,10\nSYSCALL\n"
          "LI R1,63\nMOV R2,R5\nLI R3,1\nLI R4,20\nSYSCALL\n"
          "LI R1,64\nMOV R2,R5\nLI R3,30\nSYSCALL\nMOV R6,R1\n"
          "LI R1,61\nMOV R2,R6\nSYSCALL\nMOV R3,R1\nHALT\n", 3, 3 },
        { "LIST_APPEND value lands at [2]",
          "LI R1,60\nLI R2,2\nSYSCALL\nMOV R5,R1\n"
          "LI R1,64\nMOV R2,R5\nLI R3,77\nSYSCALL\nMOV R6,R1\n"
          "LI R1,62\nMOV R2,R6\nLI R3,2\nSYSCALL\nMOV R3,R1\nHALT\n", 3, 77 },
        };
        for (unsigned i = 0; i < sizeof(lt)/sizeof(lt[0]); i++) {
            int64_t prog[128];
            int len = assemble(lt[i].src, prog, 128, 0);
            cpu_t *cpu = cpu_create(65536);
            cpu_load_program(cpu, prog, len, 0);
            cpu_run_n(cpu, 100000);
            test_assert(lt[i].name, cpu->reg[lt[i].reg], lt[i].exp);
            cpu_destroy(cpu);
        }
    }

    /* Test 5e: Value algorithms — split/join/reverse/sort/unique/format */
    printf("\n-- Value Algorithm Tests --\n");
    {
        struct { const char *name; const char *src; int reg; int64_t exp; } vt[] = {
        { "STR_SPLIT 'a,b,c' -> len 3",
          "LI R1,41\nLI R2,st\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,sd\nSYSCALL\nMOV R6,R1\n"
          "LI R1,53\nMOV R2,R5\nMOV R3,R6\nSYSCALL\nMOV R7,R1\n"
          "LI R1,61\nMOV R2,R7\nSYSCALL\nMOV R3,R1\nHALT\n"
          "st:\n.word 97\n.word 44\n.word 98\n.word 44\n.word 99\n.word 0\n"
          "sd:\n.word 44\n.word 0\n", 3, 3 },
        { "LIST_JOIN split('a,b,c') by '-' -> len 5",
          "LI R1,41\nLI R2,st\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,sd\nSYSCALL\nMOV R6,R1\n"
          "LI R1,53\nMOV R2,R5\nMOV R3,R6\nSYSCALL\nMOV R7,R1\n"
          "LI R1,41\nLI R2,js\nSYSCALL\nMOV R8,R1\n"
          "LI R1,65\nMOV R2,R7\nMOV R3,R8\nSYSCALL\nMOV R9,R1\n"
          "LI R1,42\nMOV R2,R9\nSYSCALL\nMOV R3,R1\nHALT\n"
          "st:\n.word 97\n.word 44\n.word 98\n.word 44\n.word 99\n.word 0\n"
          "sd:\n.word 44\n.word 0\njs:\n.word 45\n.word 0\n", 3, 5 },
        { "LIST_REVERSE [3,1,2] -> [0]=2",
          "LI R1,60\nLI R2,3\nSYSCALL\nMOV R5,R1\n"
          "LI R1,63\nMOV R2,R5\nLI R3,0\nLI R4,3\nSYSCALL\n"
          "LI R1,63\nMOV R2,R5\nLI R3,1\nLI R4,1\nSYSCALL\n"
          "LI R1,63\nMOV R2,R5\nLI R3,2\nLI R4,2\nSYSCALL\n"
          "LI R1,66\nMOV R2,R5\nSYSCALL\nMOV R6,R1\n"
          "LI R1,62\nMOV R2,R6\nLI R3,0\nSYSCALL\nMOV R3,R1\nHALT\n", 3, 2 },
        { "LIST_SORT asc '3,1,2' -> [0] char='1'",
          "LI R1,41\nLI R2,st\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,sd\nSYSCALL\nMOV R6,R1\n"
          "LI R1,53\nMOV R2,R5\nMOV R3,R6\nSYSCALL\nMOV R7,R1\n"
          "LI R1,67\nMOV R2,R7\nLI R3,1\nSYSCALL\nMOV R8,R1\n"
          "LI R1,62\nMOV R2,R8\nLI R3,0\nSYSCALL\nMOV R9,R1\n"
          "LI R1,43\nMOV R2,R9\nLI R3,0\nSYSCALL\nMOV R3,R1\nHALT\n"
          "st:\n.word 51\n.word 44\n.word 49\n.word 44\n.word 50\n.word 0\n"
          "sd:\n.word 44\n.word 0\n", 3, 49 },
        { "LIST_UNIQUE 'a,a,b' -> len 2",
          "LI R1,41\nLI R2,st\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,sd\nSYSCALL\nMOV R6,R1\n"
          "LI R1,53\nMOV R2,R5\nMOV R3,R6\nSYSCALL\nMOV R7,R1\n"
          "LI R1,68\nMOV R2,R7\nSYSCALL\nMOV R8,R1\n"
          "LI R1,61\nMOV R2,R8\nSYSCALL\nMOV R3,R1\nHALT\n"
          "st:\n.word 97\n.word 44\n.word 97\n.word 44\n.word 98\n.word 0\n"
          "sd:\n.word 44\n.word 0\n", 3, 2 },
        { "STR_FORMAT 'X{0}Y{1}' [p,q] -> char[1]='p'",
          "LI R1,41\nLI R2,tp\nSYSCALL\nMOV R5,R1\n"
          "LI R1,41\nLI R2,ag\nSYSCALL\nMOV R6,R1\n"
          "LI R1,41\nLI R2,sd\nSYSCALL\nMOV R7,R1\n"
          "LI R1,53\nMOV R2,R6\nMOV R3,R7\nSYSCALL\nMOV R8,R1\n"
          "LI R1,54\nMOV R2,R5\nMOV R3,R8\nSYSCALL\nMOV R9,R1\n"
          "LI R1,43\nMOV R2,R9\nLI R3,1\nSYSCALL\nMOV R3,R1\nHALT\n"
          "tp:\n.word 88\n.word 123\n.word 48\n.word 125\n.word 89\n.word 123\n.word 49\n.word 125\n.word 0\n"
          "ag:\n.word 112\n.word 44\n.word 113\n.word 0\n"
          "sd:\n.word 44\n.word 0\n", 3, 112 },
        };
        for (unsigned i = 0; i < sizeof(vt)/sizeof(vt[0]); i++) {
            int64_t prog[160];
            int len = assemble(vt[i].src, prog, 160, 0);
            cpu_t *cpu = cpu_create(65536);
            cpu_load_program(cpu, prog, len, 0);
            cpu_run_n(cpu, 100000);
            test_assert(vt[i].name, cpu->reg[vt[i].reg], vt[i].exp);
            cpu_destroy(cpu);
        }
    }

    /* Test 6: Ternary trit operations */
    printf("\n-- Ternary Logic Tests --\n");
    {
        /* AND of 13 (111 in ternary) and 4 (011) = min each trit = 011 = 4 */
        const char *src =
            "LI R1, 13\n"
            "LI R2, 4\n"
            "AND R3, R1, R2\n"
            "HALT\n";
        int64_t prog[64];
        int len = assemble(src, prog, 64, 0);
        cpu_t *cpu = cpu_create(4096);
        cpu_load_program(cpu, prog, len, 0);
        cpu_run(cpu);
        int64_t expected = ternary_and(13, 4);
        test_assert("Ternary AND(13,4)", cpu->reg[3], expected);
        cpu_destroy(cpu);
    }

    /* -----------------------------------------------------------------------
     * PIGART Tests — ASCII backend (6 new tests, Phase 7b-2)
     * --------------------------------------------------------------------- */
    printf("\n-- PIGART ASCII Backend Tests --\n");

    /* Test P1: PIGART_OPEN_WINDOW returns 0 with no backend */
    {
        pigart_active_backend = NULL;
        int64_t regs[81];
        memset(regs, 0, sizeof(regs));
        regs[1] = PIGART_OPEN_WINDOW;
        regs[2] = 800; regs[3] = 600; regs[4] = 0;
        int64_t tmem[1] = {0};
        pigart_handle_syscall(PIGART_OPEN_WINDOW, regs, tmem, 1);
        test_assert("PIGART_OPEN_WINDOW returns 0, no backend", regs[1], 0);
    }

    /* Test P2: PIGART_OPEN_WINDOW returns 1 with ASCII backend */
    {
        pigart_active_backend = pigart_ascii_backend();
        int64_t regs[81];
        memset(regs, 0, sizeof(regs));
        regs[1] = PIGART_OPEN_WINDOW;
        regs[2] = 800; regs[3] = 600; regs[4] = 0;
        int64_t tmem[1] = {0};
        pigart_handle_syscall(PIGART_OPEN_WINDOW, regs, tmem, 1);
        test_assert("PIGART_OPEN_WINDOW returns 1 with backend", regs[1], 1);
        /* Leave window open for subsequent tests */
    }

    /* Test P3: PIGART_DRAW_TEXT places text at correct ASCII grid position
     *   Window: 800x600, grid: 80x24 (default).
     *   draw_text at pixel (80, 150) → grid (80*80/800=8, 150*24/600=6).
     *   So 'H' at grid[6][8], 'i' at grid[6][9]. */
    {
        pigart_active_backend->clear(0);
        pigart_active_backend->draw_text(80, 150, "Hi", 16, 0xFFFFFF);
        char ch = pigart_ascii_cell(8, 6);
        test_assert("PIGART_DRAW_TEXT 'H' at grid(8,6)", (int64_t)ch, (int64_t)'H');
        char ci = pigart_ascii_cell(9, 6);
        test_assert("PIGART_DRAW_TEXT 'i' at grid(9,6)", (int64_t)ci, (int64_t)'i');
    }

    /* Test P3b: PIGART_DRAW_STRING renders a length-prefixed heap string.
     * A string "Hi" at handle 100: mem[100]=2, mem[101]='H', mem[102]='i'. */
    {
        int64_t m[128];
        for (int i = 0; i < 128; i++) m[i] = 0;
        m[100] = 2; m[101] = 'H'; m[102] = 'i';
        int64_t regs[NUM_REGISTERS];
        for (int i = 0; i < NUM_REGISTERS; i++) regs[i] = 0;
        regs[2] = 80; regs[3] = 150; regs[4] = 100; regs[5] = 16; regs[6] = 0xFFFFFF;
        pigart_active_backend->clear(0);
        pigart_handle_syscall(PIGART_DRAW_STRING, regs, m, 128);
        test_assert("PIGART_DRAW_STRING 'H' at grid(8,6)",
                    (int64_t)pigart_ascii_cell(8, 6), (int64_t)'H');
        test_assert("PIGART_DRAW_STRING 'i' at grid(9,6)",
                    (int64_t)pigart_ascii_cell(9, 6), (int64_t)'i');
    }

    /* Test P4: PIGART_DRAW_RECT filled region contains '#'
     *   Filled rect at pixel (400,300,200,120).
     *   Scaled: x=400*80/800=40, y=300*24/600=12, w=200*80/800=20, h=120*24/600=4.
     *   Centre of rect: grid(50, 14) → should be '#'. */
    {
        pigart_active_backend->clear(0);
        pigart_active_backend->draw_rect(400, 300, 200, 120, 0x0000FF, 1);
        char c = pigart_ascii_cell(50, 14);
        test_assert("PIGART_DRAW_RECT filled → '#' at centre", (int64_t)c, (int64_t)'#');
    }

    /* Test P5: PIGART_POLL_EVENT returns 0 in ASCII mode */
    {
        int64_t ev4[4] = {1, 2, 3, 4};
        int r = pigart_active_backend->poll_event(ev4);
        test_assert("PIGART_POLL_EVENT returns 0 in ASCII mode", (int64_t)r, 0);
    }

    /* Test P7-P10: Stage 9-1C dialog syscalls dispatch through
     * pigart_handle_syscall (memory read/write + backend routing). The ASCII
     * backend returns deterministic defaults so this is headless-verifiable;
     * live SDL modal behaviour is screen-only. */
    {
        int64_t dmem[256];
        for (int i = 0; i < 256; i++) dmem[i] = 0;
        int64_t regs[81];
        for (int i = 0; i < 81; i++) regs[i] = 0;
        /* message "Go?" @10, title "T" @20, options "a\0b\0c" @30 */
        const char *m = "Go?"; for (int i = 0; m[i]; i++) dmem[10 + i] = m[i];
        dmem[20] = 'T';
        dmem[30] = 'a'; dmem[32] = 'b'; dmem[34] = 'c';

        regs[2] = 10;
        pigart_handle_syscall(PIGART_DIALOG_CONFIRM, regs, dmem, 256);
        test_assert("DIALOG_CONFIRM ascii default=0", regs[1], 0);

        regs[1] = 0;
        regs[2] = 20; regs[3] = 10;
        int rc = pigart_handle_syscall(PIGART_DIALOG_DISPLAY, regs, dmem, 256);
        test_assert("DIALOG_DISPLAY dispatch ok", (int64_t)rc, 0);

        regs[1] = 999; regs[2] = 10; regs[3] = 50; regs[4] = 16;
        pigart_handle_syscall(PIGART_DIALOG_PROMPT, regs, dmem, 256);
        test_assert("DIALOG_PROMPT ascii empty len=0", regs[1], 0);
        test_assert("DIALOG_PROMPT out NUL-terminated", dmem[50], 0);

        regs[1] = 999; regs[2] = 10; regs[3] = 30; regs[4] = 3;
        pigart_handle_syscall(PIGART_DIALOG_CHOICE, regs, dmem, 256);
        test_assert("DIALOG_CHOICE ascii default index=0", regs[1], 0);
    }

    /* Test P6: PIGART_GET_TICKS returns positive value after sleep */
    {
        pigart_active_backend->sleep_ms(50);
        int ticks = pigart_active_backend->get_ticks();
        test_assert("PIGART_GET_TICKS > 0 after 50ms", (int64_t)(ticks > 0 ? 1 : 0), 1);
        pigart_active_backend->close_window();
        pigart_active_backend = NULL;
    }

    printf("\n=== Test Results: %d passed, %d failed ===\n",
           tests_passed, tests_failed);
}

/* -----------------------------------------------------------------------
 * Interactive mode
 * --------------------------------------------------------------------- */
static void run_interactive(void) {
    printf("=== 5500FP Interactive Assembler/Emulator ===\n");
    printf("Enter assembly instructions (one per line).\n");
    printf("Type 'RUN' to execute, 'DUMP' to show registers,\n");
    printf("'DISASM' to disassemble, 'RESET' to clear, 'QUIT' to exit.\n\n");

    char source[65536] = {0};
    char line[256];
    cpu_t *cpu = cpu_create(65536);

    while (1) {
        printf("5500FP> ");
        fflush(stdout);
        if (!fgets(line, sizeof(line), stdin)) break;

        /* Strip newline */
        line[strcspn(line, "\r\n")] = '\0';

        if (strcasecmp(line, "QUIT") == 0 || strcasecmp(line, "EXIT") == 0) {
            break;
        } else if (strcasecmp(line, "RUN") == 0) {
            int64_t prog[4096];
            int len = assemble(source, prog, 4096, 0);
            printf("[Assembled %d instructions]\n", len);
            cpu_reset(cpu);
            cpu_load_program(cpu, prog, len, 0);
            cpu_run(cpu);
            printf("\n[Halted after %llu cycles]\n",
                   (unsigned long long)cpu->cycle_count);
        } else if (strcasecmp(line, "DUMP") == 0) {
            cpu_dump_registers(cpu);
        } else if (strcasecmp(line, "DISASM") == 0) {
            int64_t prog[4096];
            int len = assemble(source, prog, 4096, 0);
            disassemble_program(prog, len, 0);
        } else if (strcasecmp(line, "RESET") == 0) {
            memset(source, 0, sizeof(source));
            cpu_reset(cpu);
            printf("[Reset]\n");
        } else if (strcasecmp(line, "LIST") == 0) {
            printf("--- Current source ---\n%s\n---\n", source);
        } else {
            /* Append line to source */
            strncat(source, line, sizeof(source) - strlen(source) - 2);
            strncat(source, "\n", sizeof(source) - strlen(source) - 1);
        }
    }

    cpu_destroy(cpu);
    printf("Goodbye.\n");
}

/* -----------------------------------------------------------------------
 * File runner
 * --------------------------------------------------------------------- */
static void run_file(const char *filename, int verbose) {
    FILE *f = fopen(filename, "r");
    if (!f) { perror(filename); return; }

    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    rewind(f);

    char *src = (char *)malloc(sz + 1);
    if (fread(src, 1, sz, f) != (size_t)sz) { /* partial read ok */ }
    src[sz] = '\0';
    fclose(f);

    int64_t program[65536];
    int len = assemble(src, program, 65536, 0);
    free(src);

    if (verbose) {
        printf("Assembled %d instructions from '%s'\n", len, filename);
        disassemble_program(program, len, 0);
        printf("\n--- Output ---\n");
    }

    cpu_t *cpu = cpu_create(65536);
    cpu_load_program(cpu, program, len, 0);
    cpu_run(cpu);

    if (verbose) {
        printf("\n--- Registers ---\n");
        cpu_dump_registers(cpu);
    }

    printf("[%llu cycles]\n", (unsigned long long)cpu->cycle_count);
    cpu_destroy(cpu);
}

/* -----------------------------------------------------------------------
 * Main
 * --------------------------------------------------------------------- */
int main(int argc, char *argv[]) {
    printf("5500FP Balanced Ternary RISC Emulator\n");
    printf("Architecture: 24-trit, 81 registers, binary-encoded ternary on x86\n");
    printf("--------------------------------------------------------------\n");

    /* Scan for --display flag (may appear before --run) */
    for (int i = 1; i < argc - 1; i++) {
        if (strcmp(argv[i], "--display") == 0) {
            const char *name = argv[i + 1];
            pigart_backend_t *b = pigart_select_backend(name);
            if (!b) {
                fprintf(stderr, "Error: unknown display backend '%s' (try: sdl, ascii)\n",
                        name);
                return 1;
            }
            break;
        }
    }

    if (argc < 2 || strcmp(argv[1], "--demo") == 0) {
        run_demo("Hello World",        demo_hello,         1);
        run_demo("Fibonacci",          demo_fibonacci,     0);
        run_demo("Ternary Arithmetic", demo_ternary_arith, 0);
        run_demo("Factorial (6!)",     demo_factorial,     0);
        run_demo("Array Sum",          demo_array_sum,     0);
    } else if (strcmp(argv[1], "--test") == 0) {
        run_tests();
    } else if (strcmp(argv[1], "--interactive") == 0) {
        run_interactive();
    } else if (strcmp(argv[1], "--run") == 0 && argc >= 3) {
        int verbose = (argc >= 4 && strcmp(argv[3], "--verbose") == 0);
        run_file(argv[2], verbose);
    } else if (strcmp(argv[1], "--display") == 0 && argc >= 4
               && strcmp(argv[3], "--run") == 0 && argc >= 5) {
        /* ./5500fp --display <name> --run <file> [--verbose] */
        int verbose = (argc >= 6 && strcmp(argv[5], "--verbose") == 0);
        run_file(argv[4], verbose);
    } else {
        printf("Usage:\n");
        printf("  %s                                Run all demos\n", argv[0]);
        printf("  %s --demo                         Run all demos\n", argv[0]);
        printf("  %s --test                         Run self-tests\n", argv[0]);
        printf("  %s --interactive                  Interactive mode\n", argv[0]);
        printf("  %s --run <file.t5asm>             Run assembly file\n", argv[0]);
        printf("  %s --run <file> --verbose         Verbose output\n", argv[0]);
        printf("  %s --display sdl   --run <file>  Run with SDL2 window\n", argv[0]);
        printf("  %s --display ascii --run <file>  Run with ASCII frames\n", argv[0]);
    }

    return 0;
}
