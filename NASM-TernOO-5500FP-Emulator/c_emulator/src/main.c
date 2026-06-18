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
    } else {
        printf("Usage:\n");
        printf("  %s                        Run all demos\n", argv[0]);
        printf("  %s --demo                 Run all demos\n", argv[0]);
        printf("  %s --test                 Run self-tests\n", argv[0]);
        printf("  %s --interactive          Interactive mode\n", argv[0]);
        printf("  %s --run <file.t5asm>     Run assembly file\n", argv[0]);
        printf("  %s --run <file> --verbose Verbose output\n", argv[0]);
    }

    return 0;
}
