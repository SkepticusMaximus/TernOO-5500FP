/*
 * cpu.c — 5500FP CPU Emulator Core Implementation
 *
 * This file implements the 5500FP balanced ternary RISC processor emulator.
 * The emulator runs on x86/x86-64 hosts. Performance-critical inner loops
 * use GCC inline assembly to leverage x86 integer and shift instructions
 * directly, avoiding overhead from the C compiler's abstraction layers.
 *
 * Architecture summary:
 *   - 24-trit balanced ternary word (trits: -1, 0, +1)
 *   - 81 general-purpose registers (R0 hardwired to 0, R80 = link register)
 *   - RISC instruction set: 4 formats (R, I, J, B)
 *   - Balanced ternary ALU: add, sub, mul, div, min, max, and, or, consensus
 *   - Load/store architecture with 22-trit address space
 */

#include "../include/cpu.h"
#include "../include/pigart.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -----------------------------------------------------------------------
 * Internal helpers
 * --------------------------------------------------------------------- */

/* Safe register read: R0 always returns 0 */
static inline int64_t reg_read(const cpu_t *cpu, int r) {
    if (r == 0) return 0LL;
    return cpu->reg[r];
}

/* Safe register write: R0 writes are silently discarded */
static inline void reg_write(cpu_t *cpu, int r, int64_t val) {
    if (r == 0) return;
    cpu->reg[r] = tword_clamp(val);
}

/* Memory read (word-addressed) */
static inline int64_t mem_read(const cpu_t *cpu, int64_t addr) {
    if (addr < 0 || (uint64_t)addr >= cpu->mem_size) {
        fprintf(stderr, "[5500FP] Memory read fault at address %lld\n", (long long)addr);
        return 0;
    }
    return cpu->mem[addr];
}

/* Memory write (word-addressed) */
static inline void mem_write(cpu_t *cpu, int64_t addr, int64_t val) {
    if (addr < 0 || (uint64_t)addr >= cpu->mem_size) {
        fprintf(stderr, "[5500FP] Memory write fault at address %lld\n", (long long)addr);
        return;
    }
    cpu->mem[addr] = tword_clamp(val);
}

/* -----------------------------------------------------------------------
 * x86 inline assembly: fast trit-by-trit addition with carry
 *
 * For balanced ternary addition, we use the standard carry-propagation
 * algorithm. Each trit sum can be -2..+2; if |sum| > 1 we carry ±1 to
 * the next trit. This inner loop is written with x86 inline assembly
 * to demonstrate the binary-encoded ternary execution on x86 silicon.
 *
 * The C fallback (int64 arithmetic) is used for correctness; the inline
 * asm version shows how x86 instructions map to ternary operations.
 * --------------------------------------------------------------------- */

/*
 * x86 assembly: ternary add using 2-bit-per-trit encoding.
 * Inputs: ea (encoded a), eb (encoded b), both uint64_t.
 * Output: encoded result uint64_t.
 *
 * Algorithm:
 *   For each trit i (0..23):
 *     decode trit a[i] and b[i] from 2-bit fields
 *     sum = a[i] + b[i] + carry
 *     if sum > 1:  result_trit = sum - 3, carry = +1
 *     if sum < -1: result_trit = sum + 3, carry = -1
 *     else:        result_trit = sum,     carry =  0
 *     encode result_trit into output
 */
static uint64_t trit_add_asm(uint64_t ea, uint64_t eb) {
    uint64_t result = 0;

#if defined(__x86_64__)
    /*
     * x86-64 inline assembly: ternary add using 2-bit-per-trit encoding.
     *
     * For each of the 24 trits:
     *   1. Extract 2-bit field from ea and eb at position bit_pos*2
     *   2. Decode to trit value (-1, 0, +1)
     *   3. sum = trit_a + trit_b + carry
     *   4. Balanced ternary carry adjustment
     *   5. Encode result trit back to 2-bit field
     *   6. Insert into result
     *
     * Register allocation:
     *   rax = scratch / ea copy
     *   rbx = scratch / eb copy
     *   rcx = loop counter (24 -> 0), also used as shift count via %cl
     *   rdx = result accumulator
     *   rsi = carry (-1, 0, +1)
     *   rdi = bit_pos (0..23)
     *   r8  = shift amount (bit_pos * 2)
     *   r9  = raw 2-bit field
     *   r10 = trit_a
     *   r11 = trit_b / sum
     *   r12 = encoded result trit
     *
     * Note: x86 variable-count shifts require the count in %cl.
     * We save/restore rcx around the shift operations.
     */
    __asm__ volatile (
        "xorq   %%rdx, %%rdx       \n\t"  /* result = 0                  */
        "xorq   %%rsi, %%rsi       \n\t"  /* carry = 0                   */
        "movq   $24,   %%rcx       \n\t"  /* loop counter = 24           */
        "xorq   %%rdi, %%rdi       \n\t"  /* bit_pos = 0                 */

        "1:                        \n\t"  /* loop top                    */

        /* Compute shift amount = bit_pos * 2 into r8 */
        "movq   %%rdi, %%r8        \n\t"
        "shlq   $1,    %%r8        \n\t"  /* r8 = bit_pos * 2            */

        /* Extract 2-bit trit field from ea */
        "movq   %1,    %%rax       \n\t"  /* rax = ea                    */
        "movq   %%r8,  %%rcx       \n\t"  /* rcx = shift amount          */
        "shrq   %%cl,  %%rax       \n\t"  /* rax >>= bit_pos*2           */
        "andq   $3,    %%rax       \n\t"  /* mask 2 bits -> r9           */
        "movq   %%rax, %%r9        \n\t"

        /* Decode trit a: 01->+1, 11->-1, 00->0 */
        "xorq   %%r10, %%r10       \n\t"  /* trit_a = 0                  */
        "cmpq   $1,    %%r9        \n\t"
        "jne    0f                 \n\t"
        "movq   $1,    %%r10       \n\t"  /* trit_a = +1                 */
        "jmp    2f                 \n\t"
        "0:                        \n\t"
        "cmpq   $3,    %%r9        \n\t"
        "jne    2f                 \n\t"
        "movq   $-1,   %%r10       \n\t"  /* trit_a = -1                 */
        "2:                        \n\t"

        /* Extract 2-bit trit field from eb */
        "movq   %2,    %%rbx       \n\t"  /* rbx = eb                    */
        "movq   %%r8,  %%rcx       \n\t"  /* rcx = shift amount          */
        "shrq   %%cl,  %%rbx       \n\t"  /* rbx >>= bit_pos*2           */
        "andq   $3,    %%rbx       \n\t"  /* mask 2 bits -> r9           */
        "movq   %%rbx, %%r9        \n\t"

        /* Decode trit b: 01->+1, 11->-1, 00->0 */
        "xorq   %%r11, %%r11       \n\t"  /* trit_b = 0                  */
        "cmpq   $1,    %%r9        \n\t"
        "jne    3f                 \n\t"
        "movq   $1,    %%r11       \n\t"  /* trit_b = +1                 */
        "jmp    4f                 \n\t"
        "3:                        \n\t"
        "cmpq   $3,    %%r9        \n\t"
        "jne    4f                 \n\t"
        "movq   $-1,   %%r11       \n\t"  /* trit_b = -1                 */
        "4:                        \n\t"

        /* sum = trit_a + trit_b + carry (rsi) */
        "addq   %%r10, %%r11       \n\t"  /* r11 = trit_a + trit_b       */
        "addq   %%rsi, %%r11       \n\t"  /* r11 += carry                */
        "xorq   %%rsi, %%rsi       \n\t"  /* carry = 0                   */

        /* Balanced ternary carry adjustment */
        "cmpq   $2,    %%r11       \n\t"
        "jl     5f                 \n\t"
        "subq   $3,    %%r11       \n\t"  /* sum -= 3                    */
        "movq   $1,    %%rsi       \n\t"  /* carry = +1                  */
        "jmp    7f                 \n\t"
        "5:                        \n\t"
        "cmpq   $-2,   %%r11       \n\t"
        "jg     7f                 \n\t"
        "addq   $3,    %%r11       \n\t"  /* sum += 3                    */
        "movq   $-1,   %%rsi       \n\t"  /* carry = -1                  */
        "7:                        \n\t"

        /* Encode result trit: +1->01, -1->11, 0->00 */
        "xorq   %%r12, %%r12       \n\t"  /* encoded = 0                 */
        "cmpq   $1,    %%r11       \n\t"
        "jne    8f                 \n\t"
        "movq   $1,    %%r12       \n\t"  /* +1 -> 01                    */
        "jmp    9f                 \n\t"
        "8:                        \n\t"
        "cmpq   $-1,   %%r11       \n\t"
        "jne    9f                 \n\t"
        "movq   $3,    %%r12       \n\t"  /* -1 -> 11                    */
        "9:                        \n\t"

        /* Shift encoded trit into result at bit_pos*2 */
        "movq   %%r8,  %%rcx       \n\t"  /* rcx = bit_pos * 2           */
        "shlq   %%cl,  %%r12       \n\t"  /* r12 <<= bit_pos*2           */
        "orq    %%r12, %%rdx       \n\t"  /* result |= r12               */

        /* Advance loop */
        "incq   %%rdi              \n\t"  /* bit_pos++                   */
        "movq   $24,   %%rcx       \n\t"  /* restore loop counter        */
        "subq   %%rdi, %%rcx       \n\t"  /* rcx = 24 - bit_pos          */
        "jnz    1b                 \n\t"  /* loop if not done            */

        "movq   %%rdx, %0          \n\t"  /* store result                */

        : "=m"(result)
        : "m"(ea), "m"(eb)
        : "rax", "rbx", "rcx", "rdx", "rsi", "rdi",
          "r8", "r9", "r10", "r11", "r12", "memory"
    );
#else
    /* Portable fallback: use int64 arithmetic directly */
    int64_t a = tword_enc_to_int64(ea);
    int64_t b = tword_enc_to_int64(eb);
    result = int64_to_tword_enc(tword_clamp(a + b));
#endif

    return result;
}

/* -----------------------------------------------------------------------
 * Instruction decode
 *
 * A 24-trit instruction is stored as int64 in memory.
 * We extract fields using balanced ternary arithmetic (divide by 3^n).
 * --------------------------------------------------------------------- */

typedef struct {
    int opcode;     /* 6-trit opcode field  */
    int rd;         /* 4-trit Rd field      */
    int rs1;        /* 4-trit Rs1 field     */
    int rs2;        /* 4-trit Rs2 field     */
    int func;       /* 6-trit func field    */
    int64_t imm10;  /* 10-trit immediate    */
    int64_t imm18;  /* 18-trit immediate    */
    inst_fmt_t fmt; /* Decoded format       */
} decoded_inst_t;

/* Extract a signed balanced ternary field of n trits starting at trit pos */
static inline int64_t extract_field(int64_t inst, int pos, int n) {
    tword_enc enc = int64_to_tword_enc(inst);
    return tword_field(enc, pos, n);
}

static void decode_instruction(int64_t raw, decoded_inst_t *d) {
    memset(d, 0, sizeof(*d));

    /* Opcode is the top 6 trits (positions 18..23) */
    d->opcode = (int)extract_field(raw, 18, 6);

    /* Determine format from opcode */
    int op = d->opcode;

    if (op >= OP_ADD && op <= OP_SIGN) {
        /* R-type */
        d->fmt  = FMT_R;
        d->rd   = (int)extract_field(raw, 14, 4);
        d->rs1  = (int)extract_field(raw,  10, 4);
        d->rs2  = (int)extract_field(raw,   6, 4);
        d->func = (int)extract_field(raw,   0, 6);
    } else if (op >= OP_ADDI && op <= OP_LI) {
        /* I-type ALU */
        d->fmt   = FMT_I;
        d->rd    = (int)extract_field(raw, 14, 4);
        d->rs1   = (int)extract_field(raw, 10, 4);
        d->imm10 = extract_field(raw, 0, 10);
    } else if (op >= OP_LDW && op <= OP_STT) {
        /* I-type Memory */
        d->fmt   = FMT_I;
        d->rd    = (int)extract_field(raw, 14, 4);
        d->rs1   = (int)extract_field(raw, 10, 4);
        d->imm10 = extract_field(raw, 0, 10);
    } else if (op >= OP_BEQ && op <= OP_BLTZ) {
        /* B-type */
        d->fmt   = FMT_B;
        d->rs1   = (int)extract_field(raw, 14, 4);
        d->rs2   = (int)extract_field(raw, 10, 4);
        d->imm10 = extract_field(raw, 0, 10);
    } else if (op >= OP_JMP && op <= OP_JMPR) {
        /* J-type */
        d->fmt   = FMT_J;
        d->imm18 = extract_field(raw, 0, 18);
        if (op == OP_CALLR || op == OP_JMPR) {
            d->rs1 = (int)extract_field(raw, 14, 4);
        }
    } else {
        /* Special / Atomic */
        d->fmt  = FMT_R;
        d->rd   = (int)extract_field(raw, 14, 4);
        d->rs1  = (int)extract_field(raw, 10, 4);
        d->rs2  = (int)extract_field(raw,  6, 4);
    }
}

/* -----------------------------------------------------------------------
 * Syscall handler
 * --------------------------------------------------------------------- */
static void handle_syscall(cpu_t *cpu) {
    int64_t call = reg_read(cpu, 1);
    int64_t arg  = reg_read(cpu, 2);

    switch ((int)call) {
        case SYS_PRINT_INT:
            printf("%lld", (long long)arg);
            break;
        case SYS_PRINT_TRIT:
            print_tword(arg);
            break;
        case SYS_PRINT_CHAR:
            putchar((int)(arg & 0x7F));
            break;
        case SYS_READ_INT: {
            long long v;
            if (scanf("%lld", &v) == 1)
                reg_write(cpu, 2, (int64_t)v);
            break;
        }
        case SYS_EXIT:
            cpu->halted = 1;
            break;
        case SYS_PRINT_NL:
            putchar('\n');
            /* stdout is fully buffered when piped — flush so the IDE sees
             * output immediately rather than waiting for process exit. */
            fflush(stdout);
            break;
        /* ---- PIGART rendering syscalls 100-111 ---- */
        case PIGART_OPEN_WINDOW:
        case PIGART_CLEAR:
        case PIGART_DRAW_RECT:
        case PIGART_DRAW_POLYGON:
        case PIGART_DRAW_OVAL:
        case PIGART_DRAW_TEXT:
        case PIGART_DRAW_LINE:
        case PIGART_PRESENT:
        case PIGART_POLL_EVENT:
        case PIGART_SLEEP_MS:
        case PIGART_GET_TICKS:
        case PIGART_CLOSE_WINDOW:
            pigart_handle_syscall((int)call, cpu->reg, cpu->mem, cpu->mem_size);
            break;
        default:
            fprintf(stderr, "[5500FP] Unknown syscall %lld\n", (long long)call);
            break;
    }
}

/* -----------------------------------------------------------------------
 * Single-step execution
 * --------------------------------------------------------------------- */
void cpu_step(cpu_t *cpu) {
    if (cpu->halted) return;

    /* Fetch instruction */
    int64_t raw = mem_read(cpu, cpu->pc);
    cpu->pc++;

    /* Decode */
    decoded_inst_t d;
    decode_instruction(raw, &d);

    int64_t a, b, result;

    switch ((opcode_t)d.opcode) {

        /* ---- ALU R-Type ---- */
        case OP_ADD:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            /* Use x86 asm trit adder for demonstration */
            {
                uint64_t ea = int64_to_tword_enc(a);
                uint64_t eb = int64_to_tword_enc(b);
                uint64_t er = trit_add_asm(ea, eb);
                result = tword_enc_to_int64(er);
            }
            reg_write(cpu, d.rd, result);
            break;

        case OP_SUB:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            reg_write(cpu, d.rd, tword_clamp(a - b));
            break;

        case OP_MUL:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            reg_write(cpu, d.rd, tword_clamp(a * b));
            break;

        case OP_DIV:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            if (b == 0) {
                fprintf(stderr, "[5500FP] Division by zero at PC=%lld\n",
                        (long long)(cpu->pc - 1));
                reg_write(cpu, d.rd, 0);
            } else {
                reg_write(cpu, d.rd, a / b);
            }
            break;

        case OP_MOD:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            if (b == 0) { reg_write(cpu, d.rd, 0); break; }
            reg_write(cpu, d.rd, a % b);
            break;

        case OP_MIN:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            reg_write(cpu, d.rd, (a < b) ? a : b);
            break;

        case OP_MAX:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            reg_write(cpu, d.rd, (a > b) ? a : b);
            break;

        case OP_AND:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            reg_write(cpu, d.rd, ternary_and(a, b));
            break;

        case OP_OR:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            reg_write(cpu, d.rd, ternary_or(a, b));
            break;

        case OP_CON:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            reg_write(cpu, d.rd, ternary_consensus(a, b));
            break;

        case OP_SHL:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            reg_write(cpu, d.rd, ternary_shl(a, (int)b));
            break;

        case OP_SHR:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            reg_write(cpu, d.rd, ternary_shr(a, (int)b));
            break;

        case OP_CMP:
            a = reg_read(cpu, d.rs1);
            b = reg_read(cpu, d.rs2);
            result = (a > b) ? 1 : (a < b) ? -1 : 0;
            reg_write(cpu, d.rd, result);
            break;

        case OP_MOV:
            reg_write(cpu, d.rd, reg_read(cpu, d.rs1));
            break;

        case OP_INV:
            reg_write(cpu, d.rd, ternary_neg(reg_read(cpu, d.rs1)));
            break;

        case OP_ABS:
            a = reg_read(cpu, d.rs1);
            reg_write(cpu, d.rd, (a < 0) ? -a : a);
            break;

        case OP_SIGN:
            a = reg_read(cpu, d.rs1);
            reg_write(cpu, d.rd, (a > 0) ? 1 : (a < 0) ? -1 : 0);
            break;

        /* ---- ALU I-Type ---- */
        case OP_ADDI:
            reg_write(cpu, d.rd, tword_clamp(reg_read(cpu, d.rs1) + d.imm10));
            break;

        case OP_SUBI:
            reg_write(cpu, d.rd, tword_clamp(reg_read(cpu, d.rs1) - d.imm10));
            break;

        case OP_MULI:
            reg_write(cpu, d.rd, tword_clamp(reg_read(cpu, d.rs1) * d.imm10));
            break;

        case OP_ANDI:
            reg_write(cpu, d.rd, ternary_and(reg_read(cpu, d.rs1), d.imm10));
            break;

        case OP_ORI:
            reg_write(cpu, d.rd, ternary_or(reg_read(cpu, d.rs1), d.imm10));
            break;

        case OP_SHLI:
            reg_write(cpu, d.rd, ternary_shl(reg_read(cpu, d.rs1), (int)d.imm10));
            break;

        case OP_SHRI:
            reg_write(cpu, d.rd, ternary_shr(reg_read(cpu, d.rs1), (int)d.imm10));
            break;

        case OP_CMPI:
            a = reg_read(cpu, d.rs1);
            b = d.imm10;
            reg_write(cpu, d.rd, (a > b) ? 1 : (a < b) ? -1 : 0);
            break;

        case OP_LI:
            reg_write(cpu, d.rd, d.imm10);
            break;

        /* ---- Memory ---- */
        case OP_LDW:
            result = mem_read(cpu, reg_read(cpu, d.rs1) + d.imm10);
            reg_write(cpu, d.rd, result);
            break;

        case OP_STW:
            mem_write(cpu, reg_read(cpu, d.rs1) + d.imm10, reg_read(cpu, d.rd));
            break;

        case OP_LDT: {
            /* Load tryte: read word, extract low 6 trits */
            int64_t w = mem_read(cpu, reg_read(cpu, d.rs1) + d.imm10);
            tword_enc enc = int64_to_tword_enc(w);
            int64_t tryte = 0;
            for (int i = 0; i < TRITS_PER_TRYTE; i++)
                tryte += (int64_t)tword_get_trit(enc, i) * POW3[i];
            reg_write(cpu, d.rd, tryte);
            break;
        }

        case OP_STT: {
            /* Store tryte: write low 6 trits of Rd into word at address */
            int64_t addr = reg_read(cpu, d.rs1) + d.imm10;
            int64_t existing = mem_read(cpu, addr);
            tword_enc enc = int64_to_tword_enc(existing);
            tword_enc src = int64_to_tword_enc(reg_read(cpu, d.rd));
            for (int i = 0; i < TRITS_PER_TRYTE; i++)
                enc = tword_set_trit(enc, i, tword_get_trit(src, i));
            mem_write(cpu, addr, tword_enc_to_int64(enc));
            break;
        }

        /* ---- Branches ---- */
        case OP_BEQ:
            if (reg_read(cpu, d.rs1) == reg_read(cpu, d.rs2))
                cpu->pc += d.imm10 - 1;
            break;

        case OP_BNE:
            if (reg_read(cpu, d.rs1) != reg_read(cpu, d.rs2))
                cpu->pc += d.imm10 - 1;
            break;

        case OP_BGT:
            if (reg_read(cpu, d.rs1) > reg_read(cpu, d.rs2))
                cpu->pc += d.imm10 - 1;
            break;

        case OP_BLT:
            if (reg_read(cpu, d.rs1) < reg_read(cpu, d.rs2))
                cpu->pc += d.imm10 - 1;
            break;

        case OP_BGE:
            if (reg_read(cpu, d.rs1) >= reg_read(cpu, d.rs2))
                cpu->pc += d.imm10 - 1;
            break;

        case OP_BLE:
            if (reg_read(cpu, d.rs1) <= reg_read(cpu, d.rs2))
                cpu->pc += d.imm10 - 1;
            break;

        case OP_BEQZ:
            if (reg_read(cpu, d.rs1) == 0)
                cpu->pc += d.imm10 - 1;
            break;

        case OP_BNEZ:
            if (reg_read(cpu, d.rs1) != 0)
                cpu->pc += d.imm10 - 1;
            break;

        case OP_BGTZ:
            if (reg_read(cpu, d.rs1) > 0)
                cpu->pc += d.imm10 - 1;
            break;

        case OP_BLTZ:
            if (reg_read(cpu, d.rs1) < 0)
                cpu->pc += d.imm10 - 1;
            break;

        /* ---- Jumps ---- */
        case OP_JMP:
            cpu->pc += d.imm18 - 1;
            break;

        case OP_JMPA:
            cpu->pc = d.imm18;
            break;

        case OP_CALL:
            reg_write(cpu, 80, cpu->pc);
            cpu->pc += d.imm18 - 1;
            break;

        case OP_RET:
            cpu->pc = reg_read(cpu, 80);
            break;

        case OP_CALLR:
            reg_write(cpu, 80, cpu->pc);
            cpu->pc = reg_read(cpu, d.rs1);
            break;

        case OP_JMPR:
            cpu->pc = reg_read(cpu, d.rs1);
            break;

        /* ---- Special ---- */
        case OP_NOP:
            break;

        case OP_HALT:
            cpu->halted = 1;
            break;

        case OP_SYSCALL:
            handle_syscall(cpu);
            break;

        /* ---- Atomic ---- */
        case OP_LDXA:
            cpu->reservation_addr = reg_read(cpu, d.rs1);
            reg_write(cpu, d.rd, mem_read(cpu, cpu->reservation_addr));
            break;

        case OP_STXA:
            if (cpu->reservation_addr == reg_read(cpu, d.rs1)) {
                mem_write(cpu, reg_read(cpu, d.rs1), reg_read(cpu, d.rd));
                reg_write(cpu, d.rd, 1);  /* success */
            } else {
                reg_write(cpu, d.rd, 0);  /* failure */
            }
            cpu->reservation_addr = -1;
            break;

        case OP_CAS: {
            int64_t addr = reg_read(cpu, d.rs1);
            int64_t expected = reg_read(cpu, d.rs2);
            int64_t current  = mem_read(cpu, addr);
            if (current == expected) {
                mem_write(cpu, addr, reg_read(cpu, d.rd));
                reg_write(cpu, d.rd, 1);
            } else {
                reg_write(cpu, d.rd, 0);
            }
            break;
        }

        default:
            fprintf(stderr, "[5500FP] Unknown opcode %d at PC=%lld\n",
                    d.opcode, (long long)(cpu->pc - 1));
            break;
    }

    /* R0 is always zero */
    cpu->reg[0] = 0;
    cpu->cycle_count++;
}

/* -----------------------------------------------------------------------
 * Run loop
 * --------------------------------------------------------------------- */
void cpu_run(cpu_t *cpu) {
    while (!cpu->halted) {
        cpu_step(cpu);
    }
}

void cpu_run_n(cpu_t *cpu, uint64_t n) {
    for (uint64_t i = 0; i < n && !cpu->halted; i++) {
        cpu_step(cpu);
    }
}

/* -----------------------------------------------------------------------
 * Lifecycle
 * --------------------------------------------------------------------- */
cpu_t *cpu_create(uint32_t mem_size_words) {
    cpu_t *cpu = (cpu_t *)calloc(1, sizeof(cpu_t));
    if (!cpu) { perror("cpu_create"); exit(1); }
    cpu->mem = (int64_t *)calloc(mem_size_words, sizeof(int64_t));
    if (!cpu->mem) { perror("cpu_create mem"); exit(1); }
    cpu->mem_size = mem_size_words;
    cpu->reservation_addr = -1;
    return cpu;
}

void cpu_destroy(cpu_t *cpu) {
    if (cpu) {
        free(cpu->mem);
        free(cpu);
    }
}

void cpu_reset(cpu_t *cpu) {
    memset(cpu->reg, 0, sizeof(cpu->reg));
    cpu->pc = 0;
    cpu->flags = 0;
    cpu->halted = 0;
    cpu->cycle_count = 0;
    cpu->reservation_addr = -1;
    memset(cpu->mem, 0, cpu->mem_size * sizeof(int64_t));
}

void cpu_load_program(cpu_t *cpu, const int64_t *prog, uint32_t len, int64_t start_addr) {
    for (uint32_t i = 0; i < len; i++) {
        mem_write(cpu, start_addr + i, prog[i]);
    }
    cpu->pc = start_addr;
}

/* -----------------------------------------------------------------------
 * Debug
 * --------------------------------------------------------------------- */
void cpu_dump_registers(const cpu_t *cpu) {
    printf("=== 5500FP Register Dump (PC=%lld, Cycles=%llu) ===\n",
           (long long)cpu->pc, (unsigned long long)cpu->cycle_count);
    for (int i = 0; i < NUM_REGISTERS; i++) {
        if (cpu->reg[i] != 0 || i < 10) {
            printf("  R%-3d = %12lld  [", i, (long long)cpu->reg[i]);
            print_tword(cpu->reg[i]);
            printf("]\n");
        }
    }
    printf("  HALTED=%d\n", cpu->halted);
}

void cpu_dump_memory(const cpu_t *cpu, int64_t start, int64_t count) {
    printf("=== Memory Dump [%lld .. %lld] ===\n",
           (long long)start, (long long)(start + count - 1));
    for (int64_t i = 0; i < count; i++) {
        int64_t addr = start + i;
        if (addr < 0 || (uint64_t)addr >= cpu->mem_size) break;
        printf("  [%6lld] = %12lld  [", (long long)addr, (long long)cpu->mem[addr]);
        print_tword(cpu->mem[addr]);
        printf("]\n");
    }
}
