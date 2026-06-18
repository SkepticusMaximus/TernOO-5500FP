/*
 * assembler.c — 5500FP Macro-Assembler and Disassembler
 *
 * Assembles 5500FP assembly source text into an array of int64 words
 * (each word is a 24-trit balanced ternary instruction encoded as int64).
 *
 * Assembly syntax:
 *   MNEMONIC [Rd,] [Rs1,] [Rs2/imm]   ; comment
 *
 * Labels:
 *   label:
 *
 * Registers: R0..R80 (or r0..r80)
 * Immediates: decimal integers (positive or negative)
 * Ternary literals: prefix 't' followed by ternary digits (0, 1, T for -1)
 *   e.g. t1T0 = 1*9 + (-1)*3 + 0*1 = 9-3 = 6
 *
 * Directives:
 *   .word <value>   — emit a raw word
 *   .tryte <value>  — emit a 6-trit tryte (stored as word)
 *   .org <addr>     — set current address
 */

#define _GNU_SOURCE
#include "../include/cpu.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>

#define MAX_LABELS    512
#define MAX_PROGRAM   65536
#define MAX_LINE      256

/* -----------------------------------------------------------------------
 * Label table
 * --------------------------------------------------------------------- */
typedef struct {
    char    name[64];
    int64_t addr;
} label_t;

static label_t labels[MAX_LABELS];
static int     n_labels = 0;

static void label_define(const char *name, int64_t addr) {
    for (int i = 0; i < n_labels; i++) {
        if (strcmp(labels[i].name, name) == 0) {
            labels[i].addr = addr;
            return;
        }
    }
    if (n_labels < MAX_LABELS) {
        strncpy(labels[n_labels].name, name, 63);
        labels[n_labels].addr = addr;
        n_labels++;
    }
}

static int64_t label_lookup(const char *name) {
    for (int i = 0; i < n_labels; i++) {
        if (strcmp(labels[i].name, name) == 0)
            return labels[i].addr;
    }
    return -999999; /* sentinel: unresolved */
}

/* -----------------------------------------------------------------------
 * Instruction encoding helpers
 *
 * We build instructions as int64 balanced ternary values.
 * Fields are placed by multiplying by powers of 3.
 * --------------------------------------------------------------------- */

/* Encode a field of n trits at trit position pos into an instruction */
static int64_t encode_field(int64_t val, int pos, int n) {
    /* Clamp val to n-trit range */
    int64_t max_val = (POW3[n] - 1) / 2;
    if (val > max_val) val = max_val;
    if (val < -max_val) val = -max_val;
    return val * POW3[pos];
}

static int64_t encode_r(int op, int rd, int rs1, int rs2, int func) {
    return encode_field(op,   18, 6)
         + encode_field(rd,   14, 4)
         + encode_field(rs1,  10, 4)
         + encode_field(rs2,   6, 4)
         + encode_field(func,  0, 6);
}

static int64_t encode_i(int op, int rd, int rs1, int64_t imm) {
    return encode_field(op,  18, 6)
         + encode_field(rd,  14, 4)
         + encode_field(rs1, 10, 4)
         + encode_field(imm,  0, 10);
}

static int64_t encode_j(int op, int64_t imm18) {
    return encode_field(op,    18, 6)
         + encode_field(imm18,  0, 18);
}

static int64_t encode_b(int op, int rs1, int rs2, int64_t imm) {
    return encode_field(op,  18, 6)
         + encode_field(rs1, 14, 4)
         + encode_field(rs2, 10, 4)
         + encode_field(imm,  0, 10);
}

/* -----------------------------------------------------------------------
 * Token parsing
 * --------------------------------------------------------------------- */

static char *skip_ws(char *p) {
    while (*p == ' ' || *p == '\t') p++;
    return p;
}

static char *read_token(char *p, char *tok, int maxlen) {
    p = skip_ws(p);
    int i = 0;
    while (*p && *p != ' ' && *p != '\t' && *p != ',' && *p != ';'
           && *p != '\n' && *p != '\r' && i < maxlen - 1) {
        tok[i++] = *p++;
    }
    tok[i] = '\0';
    if (*p == ',') p++;
    return p;
}

/* Parse register: "R5" or "r5" -> 5 */
static int parse_reg(const char *tok) {
    if (tok[0] == 'R' || tok[0] == 'r') {
        return atoi(tok + 1);
    }
    return -1;
}

/* Parse immediate: decimal or ternary (prefix 't') */
static int64_t parse_imm(const char *tok) {
    if (tok[0] == 't' || tok[0] == 'T') {
        /* Ternary literal: digits are 0, 1, T (for -1) */
        const char *p = tok + 1;
        int64_t val = 0;
        int len = (int)strlen(p);
        for (int i = 0; i < len; i++) {
            val *= 3;
            char c = p[i];
            if (c == '1') val += 1;
            else if (c == 'T') val -= 1;
            /* '0' adds nothing */
        }
        return val;
    }
    return (int64_t)atoll(tok);
}

/* -----------------------------------------------------------------------
 * Mnemonic table
 * --------------------------------------------------------------------- */
typedef struct {
    const char *mnem;
    int         opcode;
    inst_fmt_t  fmt;
    int         n_operands; /* number of explicit operands */
} mnem_entry_t;

static const mnem_entry_t mnem_table[] = {
    /* R-type */
    { "ADD",    OP_ADD,    FMT_R, 3 },
    { "SUB",    OP_SUB,    FMT_R, 3 },
    { "MUL",    OP_MUL,    FMT_R, 3 },
    { "DIV",    OP_DIV,    FMT_R, 3 },
    { "MOD",    OP_MOD,    FMT_R, 3 },
    { "MIN",    OP_MIN,    FMT_R, 3 },
    { "MAX",    OP_MAX,    FMT_R, 3 },
    { "AND",    OP_AND,    FMT_R, 3 },
    { "OR",     OP_OR,     FMT_R, 3 },
    { "CON",    OP_CON,    FMT_R, 3 },
    { "SHL",    OP_SHL,    FMT_R, 3 },
    { "SHR",    OP_SHR,    FMT_R, 3 },
    { "CMP",    OP_CMP,    FMT_R, 3 },
    { "MOV",    OP_MOV,    FMT_R, 2 },
    { "INV",    OP_INV,    FMT_R, 2 },
    { "ABS",    OP_ABS,    FMT_R, 2 },
    { "SIGN",   OP_SIGN,   FMT_R, 2 },
    /* I-type ALU */
    { "ADDI",   OP_ADDI,   FMT_I, 3 },
    { "SUBI",   OP_SUBI,   FMT_I, 3 },
    { "MULI",   OP_MULI,   FMT_I, 3 },
    { "ANDI",   OP_ANDI,   FMT_I, 3 },
    { "ORI",    OP_ORI,    FMT_I, 3 },
    { "SHLI",   OP_SHLI,   FMT_I, 3 },
    { "SHRI",   OP_SHRI,   FMT_I, 3 },
    { "CMPI",   OP_CMPI,   FMT_I, 3 },
    { "LI",     OP_LI,     FMT_I, 2 },
    /* Memory */
    { "LDW",    OP_LDW,    FMT_I, 3 },
    { "STW",    OP_STW,    FMT_I, 3 },
    { "LDT",    OP_LDT,    FMT_I, 3 },
    { "STT",    OP_STT,    FMT_I, 3 },
    /* Branch */
    { "BEQ",    OP_BEQ,    FMT_B, 3 },
    { "BNE",    OP_BNE,    FMT_B, 3 },
    { "BGT",    OP_BGT,    FMT_B, 3 },
    { "BLT",    OP_BLT,    FMT_B, 3 },
    { "BGE",    OP_BGE,    FMT_B, 3 },
    { "BLE",    OP_BLE,    FMT_B, 3 },
    { "BEQZ",   OP_BEQZ,   FMT_B, 2 },
    { "BNEZ",   OP_BNEZ,   FMT_B, 2 },
    { "BGTZ",   OP_BGTZ,   FMT_B, 2 },
    { "BLTZ",   OP_BLTZ,   FMT_B, 2 },
    /* Jump */
    { "JMP",    OP_JMP,    FMT_J, 1 },
    { "JMPA",   OP_JMPA,   FMT_J, 1 },
    { "CALL",   OP_CALL,   FMT_J, 1 },
    { "RET",    OP_RET,    FMT_J, 0 },
    { "CALLR",  OP_CALLR,  FMT_J, 1 },
    { "JMPR",   OP_JMPR,   FMT_J, 1 },
    /* Special */
    { "NOP",    OP_NOP,    FMT_R, 0 },
    { "HALT",   OP_HALT,   FMT_R, 0 },
    { "SYSCALL",OP_SYSCALL,FMT_R, 0 },
    /* Atomic */
    { "LDXA",   OP_LDXA,   FMT_R, 2 },
    { "STXA",   OP_STXA,   FMT_R, 2 },
    { "CAS",    OP_CAS,    FMT_R, 3 },
    { NULL, 0, 0, 0 }
};

static const mnem_entry_t *find_mnem(const char *name) {
    for (int i = 0; mnem_table[i].mnem; i++) {
        if (strcasecmp(mnem_table[i].mnem, name) == 0)
            return &mnem_table[i];
    }
    return NULL;
}

/* -----------------------------------------------------------------------
 * Assembler: two-pass
 * --------------------------------------------------------------------- */

/* Fixup entry for forward references */
typedef struct {
    int64_t  addr;      /* address in program[] needing fixup */
    char     label[64]; /* label name */
    int      opcode;
    inst_fmt_t fmt;
    int      rd, rs1, rs2;
    int      is_relative; /* 1 = PC-relative, 0 = absolute */
} fixup_t;

static fixup_t fixups[MAX_LABELS];
static int     n_fixups = 0;

int assemble(const char *source, int64_t *program, int max_words,
             int64_t start_addr) {
    n_labels = 0;
    n_fixups = 0;

    /* Make a mutable copy of source */
    char *src = strdup(source);
    int64_t cur_addr = start_addr;
    int word_count = 0;

    /* Pass 1: collect labels and emit instructions */
    char *line = strtok(src, "\n");
    while (line && word_count < max_words) {
        char *p = skip_ws(line);

        /* Skip empty lines and comments */
        if (*p == '\0' || *p == ';') { line = strtok(NULL, "\n"); continue; }

        /* Check for label */
        char *colon = strchr(p, ':');
        if (colon) {
            char lname[64] = {0};
            int llen = (int)(colon - p);
            if (llen > 63) llen = 63;
            strncpy(lname, p, llen);
            /* Trim trailing whitespace from label */
            for (int i = llen - 1; i >= 0 && isspace((unsigned char)lname[i]); i--)
                lname[i] = '\0';
            label_define(lname, cur_addr);
            p = skip_ws(colon + 1);
            if (*p == '\0' || *p == ';') { line = strtok(NULL, "\n"); continue; }
        }

        /* Directives */
        if (*p == '.') {
            char dir[32], val_tok[64];
            p = read_token(p, dir, sizeof(dir));
            p = read_token(p, val_tok, sizeof(val_tok));
            if (strcasecmp(dir, ".word") == 0) {
                program[word_count++] = parse_imm(val_tok);
                cur_addr++;
            } else if (strcasecmp(dir, ".tryte") == 0) {
                program[word_count++] = parse_imm(val_tok);
                cur_addr++;
            } else if (strcasecmp(dir, ".org") == 0) {
                cur_addr = parse_imm(val_tok);
            }
            line = strtok(NULL, "\n");
            continue;
        }

        /* Strip inline comment from line before tokenizing */
        char *semi_pos = strchr(p, ';');
        if (semi_pos) *semi_pos = '\0';
        p = skip_ws(p);
        if (*p == '\0') { line = strtok(NULL, "\n"); continue; }

        /* Mnemonic */
        char mnem[32];
        p = read_token(p, mnem, sizeof(mnem));
        if (mnem[0] == '\0') { line = strtok(NULL, "\n"); continue; }

        const mnem_entry_t *me = find_mnem(mnem);
        if (!me) {
            fprintf(stderr, "[ASM] Unknown mnemonic '%s' at addr %lld\n",
                    mnem, (long long)cur_addr);
            line = strtok(NULL, "\n");
            continue;
        }

        char tok1[64]={0}, tok2[64]={0}, tok3[64]={0};
        if (me->n_operands >= 1) p = read_token(p, tok1, sizeof(tok1));
        if (me->n_operands >= 2) p = read_token(p, tok2, sizeof(tok2));
        if (me->n_operands >= 3) p = read_token(p, tok3, sizeof(tok3));

        int64_t inst = 0;
        int rd  = parse_reg(tok1);
        int rs1 = parse_reg(tok2);
        int rs2 = parse_reg(tok3);

        switch (me->fmt) {
            case FMT_R:
                if (me->n_operands == 0) {
                    inst = encode_r(me->opcode, 0, 0, 0, 0);
                } else if (me->n_operands == 2) {
                    inst = encode_r(me->opcode, rd, rs1, 0, 0);
                } else {
                    inst = encode_r(me->opcode, rd, rs1, rs2, 0);
                }
                break;

            case FMT_I: {
                int64_t imm = 0;
                if (me->opcode == OP_LI) {
                    /* LI Rd, imm */
                    rd  = parse_reg(tok1);
                    rs1 = 0;
                    /* tok2 may be a label or immediate */
                    int64_t lv = label_lookup(tok2);
                    if (lv == -999999) {
                        if (isalpha((unsigned char)tok2[0]) || tok2[0] == '_') {
                            /* Forward label reference — add fixup for pass 2 */
                            if (n_fixups < MAX_LABELS) {
                                fixups[n_fixups].addr        = cur_addr;
                                strncpy(fixups[n_fixups].label, tok2, 63);
                                fixups[n_fixups].opcode      = me->opcode;
                                fixups[n_fixups].fmt         = FMT_I;
                                fixups[n_fixups].rd          = rd;
                                fixups[n_fixups].rs1         = 0;
                                fixups[n_fixups].is_relative = 0;
                                n_fixups++;
                            }
                            imm = 0; /* placeholder */
                        } else {
                            imm = parse_imm(tok2);
                        }
                    } else {
                        imm = lv;
                    }
                } else {
                    /* Check if tok3 is a label */
                    int64_t lv = label_lookup(tok3);
                    if (lv == -999999) {
                        if (isalpha((unsigned char)tok3[0]) || tok3[0] == '_') {
                            /* Forward label reference — add fixup for pass 2 */
                            if (n_fixups < MAX_LABELS) {
                                fixups[n_fixups].addr        = cur_addr;
                                strncpy(fixups[n_fixups].label, tok3, 63);
                                fixups[n_fixups].opcode      = me->opcode;
                                fixups[n_fixups].fmt         = FMT_I;
                                fixups[n_fixups].rd          = rd;
                                fixups[n_fixups].rs1         = rs1;
                                fixups[n_fixups].is_relative = 0;
                                n_fixups++;
                            }
                            imm = 0; /* placeholder */
                        } else {
                            imm = parse_imm(tok3);
                        }
                    } else {
                        imm = lv;
                    }
                }
                inst = encode_i(me->opcode, rd, rs1, imm);
                break;
            }

            case FMT_J: {
                int64_t imm = 0;
                if (me->n_operands == 0) {
                    inst = encode_j(me->opcode, 0);
                    break;
                }
                if (me->opcode == OP_CALLR || me->opcode == OP_JMPR) {
                    int r = parse_reg(tok1);
                    inst = encode_r(me->opcode, 0, r, 0, 0);
                    break;
                }
                /* tok1 may be a label or immediate */
                int64_t lv = label_lookup(tok1);
                if (lv == -999999) {
                    /* Check if it looks like a label name */
                    if (isalpha((unsigned char)tok1[0]) || tok1[0] == '_') {
                        /* Forward reference: emit placeholder, add fixup */
                        if (n_fixups < MAX_LABELS) {
                            fixups[n_fixups].addr = cur_addr;
                            strncpy(fixups[n_fixups].label, tok1, 63);
                            fixups[n_fixups].opcode = me->opcode;
                            fixups[n_fixups].fmt    = FMT_J;
                            fixups[n_fixups].is_relative = (me->opcode == OP_JMP ||
                                                             me->opcode == OP_CALL);
                            n_fixups++;
                        }
                        imm = 0; /* placeholder */
                    } else {
                        imm = parse_imm(tok1);
                    }
                } else {
                    /* PC-relative for JMP/CALL */
                    if (me->opcode == OP_JMP || me->opcode == OP_CALL)
                        imm = lv - cur_addr;
                    else
                        imm = lv;
                }
                inst = encode_j(me->opcode, imm);
                break;
            }

            case FMT_B: {
                int64_t imm = 0;
                int r1, r2;
                if (me->n_operands == 2) {
                    r1 = parse_reg(tok1);
                    r2 = 0;
                    int64_t lv = label_lookup(tok2);
                    if (lv == -999999) {
                        if (isalpha((unsigned char)tok2[0]) || tok2[0] == '_') {
                            if (n_fixups < MAX_LABELS) {
                                fixups[n_fixups].addr = cur_addr;
                                strncpy(fixups[n_fixups].label, tok2, 63);
                                fixups[n_fixups].opcode = me->opcode;
                                fixups[n_fixups].fmt    = FMT_B;
                                fixups[n_fixups].rd     = r1;
                                fixups[n_fixups].rs1    = 0;
                                fixups[n_fixups].is_relative = 1;
                                n_fixups++;
                            }
                            imm = 0;
                        } else {
                            imm = parse_imm(tok2);
                        }
                    } else {
                        imm = lv - cur_addr;
                    }
                    inst = encode_b(me->opcode, r1, 0, imm);
                } else {
                    r1 = parse_reg(tok1);
                    r2 = parse_reg(tok2);
                    int64_t lv = label_lookup(tok3);
                    if (lv == -999999) {
                        if (isalpha((unsigned char)tok3[0]) || tok3[0] == '_') {
                            if (n_fixups < MAX_LABELS) {
                                fixups[n_fixups].addr = cur_addr;
                                strncpy(fixups[n_fixups].label, tok3, 63);
                                fixups[n_fixups].opcode = me->opcode;
                                fixups[n_fixups].fmt    = FMT_B;
                                fixups[n_fixups].rd     = r1;
                                fixups[n_fixups].rs1    = r2;
                                fixups[n_fixups].is_relative = 1;
                                n_fixups++;
                            }
                            imm = 0;
                        } else {
                            imm = parse_imm(tok3);
                        }
                    } else {
                        imm = lv - cur_addr;
                    }
                    inst = encode_b(me->opcode, r1, r2, imm);
                }
                break;
            }
        }

        program[word_count++] = inst;
        cur_addr++;
        line = strtok(NULL, "\n");
    }

    /* Pass 2: resolve forward references */
    for (int i = 0; i < n_fixups; i++) {
        int64_t target = label_lookup(fixups[i].label);
        if (target == -999999) {
            fprintf(stderr, "[ASM] Unresolved label '%s'\n", fixups[i].label);
            continue;
        }
        int64_t fix_idx = fixups[i].addr - start_addr;
        if (fix_idx < 0 || fix_idx >= word_count) continue;

        int64_t imm = fixups[i].is_relative ? (target - fixups[i].addr) : target;
        int op = fixups[i].opcode;

        if (fixups[i].fmt == FMT_J) {
            program[fix_idx] = encode_j(op, imm);
        } else if (fixups[i].fmt == FMT_B) {
            program[fix_idx] = encode_b(op, fixups[i].rd, fixups[i].rs1, imm);
        } else if (fixups[i].fmt == FMT_I) {
            program[fix_idx] = encode_i(op, fixups[i].rd, fixups[i].rs1, imm);
        }
    }

    free(src);
    return word_count;
}

/* -----------------------------------------------------------------------
 * Disassembler
 * --------------------------------------------------------------------- */

static const char *opcode_name(int op) {
    for (int i = 0; mnem_table[i].mnem; i++) {
        if (mnem_table[i].opcode == op) return mnem_table[i].mnem;
    }
    return "???";
}

static inst_fmt_t opcode_fmt(int op) {
    for (int i = 0; mnem_table[i].mnem; i++) {
        if (mnem_table[i].opcode == op) return mnem_table[i].fmt;
    }
    return FMT_R;
}

static int opcode_nops(int op) {
    for (int i = 0; mnem_table[i].mnem; i++) {
        if (mnem_table[i].opcode == op) return mnem_table[i].n_operands;
    }
    return 0;
}

void disassemble(int64_t inst, int64_t addr, char *out, int out_len) {
    tword_enc enc = int64_to_tword_enc(inst);
    int opcode = (int)tword_field(enc, 18, 6);
    const char *name = opcode_name(opcode);
    inst_fmt_t fmt = opcode_fmt(opcode);
    int nops = opcode_nops(opcode);

    int rd   = (int)tword_field(enc, 14, 4);
    int rs1  = (int)tword_field(enc, 10, 4);
    int rs2  = (int)tword_field(enc,  6, 4);
    int64_t imm10 = tword_field(enc,  0, 10);
    int64_t imm18 = tword_field(enc,  0, 18);

    char tmp[128];
    switch (fmt) {
        case FMT_R:
            if (nops == 0)
                snprintf(tmp, sizeof(tmp), "%s", name);
            else if (nops == 2)
                snprintf(tmp, sizeof(tmp), "%s R%d, R%d", name, rd, rs1);
            else
                snprintf(tmp, sizeof(tmp), "%s R%d, R%d, R%d", name, rd, rs1, rs2);
            break;
        case FMT_I:
            if (opcode == OP_LI)
                snprintf(tmp, sizeof(tmp), "%s R%d, %lld", name, rd, (long long)imm10);
            else
                snprintf(tmp, sizeof(tmp), "%s R%d, R%d, %lld", name, rd, rs1, (long long)imm10);
            break;
        case FMT_J:
            if (nops == 0)
                snprintf(tmp, sizeof(tmp), "%s", name);
            else if (opcode == OP_CALLR || opcode == OP_JMPR)
                snprintf(tmp, sizeof(tmp), "%s R%d", name, rs1);
            else {
                int64_t target = (opcode == OP_JMP || opcode == OP_CALL)
                                 ? addr + imm18 : imm18;
                snprintf(tmp, sizeof(tmp), "%s %lld", name, (long long)target);
            }
            break;
        case FMT_B:
            if (nops == 2)
                snprintf(tmp, sizeof(tmp), "%s R%d, %lld",
                         name, rd, (long long)(addr + imm10));
            else
                snprintf(tmp, sizeof(tmp), "%s R%d, R%d, %lld",
                         name, rd, rs1, (long long)(addr + imm10));
            break;
        default:
            snprintf(tmp, sizeof(tmp), "??? (op=%d)", opcode);
            break;
    }

    snprintf(out, out_len, "%06lld: %-30s ; raw=%lld [",
             (long long)addr, tmp, (long long)inst);
    /* Append ternary representation */
    int used = (int)strlen(out);
    tword_enc enc2 = int64_to_tword_enc(inst);
    for (int i = TRITS_PER_WORD - 1; i >= 0 && used < out_len - 3; i--) {
        trit_t t = tword_get_trit(enc2, i);
        char c = (t == 1) ? '1' : (t == -1) ? 'T' : '0';
        out[used++] = c;
    }
    out[used++] = ']';
    out[used]   = '\0';
}

void disassemble_program(const int64_t *prog, int len, int64_t start_addr) {
    printf("=== 5500FP Disassembly ===\n");
    for (int i = 0; i < len; i++) {
        char buf[256];
        disassemble(prog[i], start_addr + i, buf, sizeof(buf));
        printf("  %s\n", buf);
    }
}
