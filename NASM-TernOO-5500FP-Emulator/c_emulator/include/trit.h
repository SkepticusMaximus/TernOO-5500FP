/*
 * trit.h — 5500FP Balanced Ternary Emulator
 * Core trit/tryte/word type definitions and encoding primitives.
 *
 * Architecture: 5500FP (24-trit balanced ternary RISC)
 * Encoding: 2 bits per trit packed into uint64_t
 *   00 = 0,  01 = +1,  11 = -1  (10 = invalid)
 *
 * A 24-trit word uses 48 bits, fitting in a uint64_t.
 * A 6-trit tryte uses 12 bits.
 * A 12-trit short uses 24 bits.
 *
 * Balanced ternary range:
 *   Tryte  (6 trits): -364 .. +364
 *   Short (12 trits): -265,720 .. +265,720
 *   Word  (24 trits): -141,214,768,240 .. +141,214,768,240
 */

#ifndef TRIT_H
#define TRIT_H

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -----------------------------------------------------------------------
 * Fundamental types
 * --------------------------------------------------------------------- */

typedef int8_t   trit_t;    /* Single trit: -1, 0, +1                   */
typedef int64_t  tword_t;   /* Balanced ternary word (native int64)      */
typedef uint64_t tword_enc; /* Binary-encoded ternary word (2 bits/trit) */

/* -----------------------------------------------------------------------
 * Architecture constants
 * --------------------------------------------------------------------- */

#define TRITS_PER_TRYTE   6
#define TRITS_PER_SHORT  12
#define TRITS_PER_WORD   24

#define NUM_REGISTERS    81   /* R0 .. R80; R0 hardwired to 0 */
#define MEMORY_SIZE      (1 << 24)  /* 16M trytes (simplified for emulator) */

/* Balanced ternary limits */
#define TWORD_MAX  141214768240LL
#define TWORD_MIN (-141214768240LL)

/* Powers of 3 table */
static const int64_t POW3[25] = {
    1LL, 3LL, 9LL, 27LL, 81LL, 243LL, 729LL, 2187LL, 6561LL, 19683LL,
    59049LL, 177147LL, 531441LL, 1594323LL, 4782969LL, 14348907LL,
    43046721LL, 129140163LL, 387420489LL, 1162261467LL, 3486784401LL,
    10460353203LL, 31381059609LL, 94143178827LL, 282429536481LL
};

/* -----------------------------------------------------------------------
 * 2-bit encoding per trit
 *   Trit +1 -> 0b01
 *   Trit  0 -> 0b00
 *   Trit -1 -> 0b11
 * --------------------------------------------------------------------- */

static inline uint8_t trit_encode(trit_t t) {
    if (t == 1)  return 0x1;
    if (t == -1) return 0x3;
    return 0x0;
}

static inline trit_t trit_decode(uint8_t enc) {
    if (enc == 0x1) return  1;
    if (enc == 0x3) return -1;
    return 0;
}

/* -----------------------------------------------------------------------
 * Convert int64 <-> binary-encoded ternary word (24 trits)
 * --------------------------------------------------------------------- */

/* Encode a balanced ternary integer into 2-bits-per-trit packed uint64 */
static inline tword_enc int64_to_tword_enc(int64_t val) {
    tword_enc enc = 0;
    for (int i = 0; i < TRITS_PER_WORD; i++) {
        int64_t rem = val % 3;
        if (rem == 2)  { rem = -1; val += 1; }
        if (rem == -2) { rem =  1; val -= 1; }
        val /= 3;
        uint8_t bits = trit_encode((trit_t)rem);
        enc |= ((tword_enc)bits << (i * 2));
    }
    return enc;
}

/* Decode a 2-bits-per-trit packed uint64 back to int64 */
static inline int64_t tword_enc_to_int64(tword_enc enc) {
    int64_t val = 0;
    for (int i = 0; i < TRITS_PER_WORD; i++) {
        uint8_t bits = (enc >> (i * 2)) & 0x3;
        trit_t t = trit_decode(bits);
        val += (int64_t)t * POW3[i];
    }
    return val;
}

/* Extract a single trit from a packed word (position 0 = LST) */
static inline trit_t tword_get_trit(tword_enc enc, int pos) {
    uint8_t bits = (enc >> (pos * 2)) & 0x3;
    return trit_decode(bits);
}

/* Set a single trit in a packed word */
static inline tword_enc tword_set_trit(tword_enc enc, int pos, trit_t t) {
    tword_enc mask = ~((tword_enc)0x3 << (pos * 2));
    enc = (enc & mask) | ((tword_enc)trit_encode(t) << (pos * 2));
    return enc;
}

/* Extract a field of n_trits starting at position pos */
static inline int64_t tword_field(tword_enc enc, int pos, int n_trits) {
    int64_t val = 0;
    for (int i = 0; i < n_trits; i++) {
        trit_t t = tword_get_trit(enc, pos + i);
        val += (int64_t)t * POW3[i];
    }
    return val;
}

/* -----------------------------------------------------------------------
 * Ternary ALU primitives (operate on int64 balanced ternary values)
 * --------------------------------------------------------------------- */

/* Clamp to 24-trit word range */
static inline int64_t tword_clamp(int64_t v) {
    if (v > TWORD_MAX) return TWORD_MAX;
    if (v < TWORD_MIN) return TWORD_MIN;
    return v;
}

/* Ternary negation (invert all trits = arithmetic negation) */
static inline int64_t ternary_neg(int64_t v) { return -v; }

/* Ternary AND (min of each trit pair) */
static inline int64_t ternary_and(int64_t a, int64_t b) {
    tword_enc ea = int64_to_tword_enc(a);
    tword_enc eb = int64_to_tword_enc(b);
    tword_enc er = 0;
    for (int i = 0; i < TRITS_PER_WORD; i++) {
        trit_t ta = tword_get_trit(ea, i);
        trit_t tb = tword_get_trit(eb, i);
        trit_t tr = (ta < tb) ? ta : tb;
        er = tword_set_trit(er, i, tr);
    }
    return tword_enc_to_int64(er);
}

/* Ternary OR (max of each trit pair) */
static inline int64_t ternary_or(int64_t a, int64_t b) {
    tword_enc ea = int64_to_tword_enc(a);
    tword_enc eb = int64_to_tword_enc(b);
    tword_enc er = 0;
    for (int i = 0; i < TRITS_PER_WORD; i++) {
        trit_t ta = tword_get_trit(ea, i);
        trit_t tb = tword_get_trit(eb, i);
        trit_t tr = (ta > tb) ? ta : tb;
        er = tword_set_trit(er, i, tr);
    }
    return tword_enc_to_int64(er);
}

/* Ternary consensus (Kleene logic: -1 if either is -1, +1 if both +1, else 0) */
static inline int64_t ternary_consensus(int64_t a, int64_t b) {
    tword_enc ea = int64_to_tword_enc(a);
    tword_enc eb = int64_to_tword_enc(b);
    tword_enc er = 0;
    for (int i = 0; i < TRITS_PER_WORD; i++) {
        trit_t ta = tword_get_trit(ea, i);
        trit_t tb = tword_get_trit(eb, i);
        trit_t tr;
        if (ta == -1 || tb == -1) tr = -1;
        else if (ta == 1 && tb == 1) tr = 1;
        else tr = 0;
        er = tword_set_trit(er, i, tr);
    }
    return tword_enc_to_int64(er);
}

/* Ternary shift left by n trits (multiply by 3^n) */
static inline int64_t ternary_shl(int64_t v, int n) {
    if (n >= TRITS_PER_WORD) return 0;
    return tword_clamp(v * POW3[n]);
}

/* Ternary shift right by n trits (divide by 3^n, truncate toward zero) */
static inline int64_t ternary_shr(int64_t v, int n) {
    if (n >= TRITS_PER_WORD) return 0;
    return v / POW3[n];
}

/* -----------------------------------------------------------------------
 * Display helpers
 * --------------------------------------------------------------------- */

/* Print a 24-trit word in ternary notation using T for -1 */
static inline void print_tword(int64_t val) {
    tword_enc enc = int64_to_tword_enc(val);
    char buf[TRITS_PER_WORD + 1];
    buf[TRITS_PER_WORD] = '\0';
    for (int i = TRITS_PER_WORD - 1; i >= 0; i--) {
        trit_t t = tword_get_trit(enc, i);
        if (t == 1)  buf[TRITS_PER_WORD - 1 - i] = '1';
        else if (t == -1) buf[TRITS_PER_WORD - 1 - i] = 'T';
        else              buf[TRITS_PER_WORD - 1 - i] = '0';
    }
    printf("%s", buf);
}

/* Print a 6-trit tryte */
static inline void print_tryte(int64_t val) {
    tword_enc enc = int64_to_tword_enc(val);
    char buf[TRITS_PER_TRYTE + 1];
    buf[TRITS_PER_TRYTE] = '\0';
    for (int i = TRITS_PER_TRYTE - 1; i >= 0; i--) {
        trit_t t = tword_get_trit(enc, i);
        if (t == 1)  buf[TRITS_PER_TRYTE - 1 - i] = '1';
        else if (t == -1) buf[TRITS_PER_TRYTE - 1 - i] = 'T';
        else              buf[TRITS_PER_TRYTE - 1 - i] = '0';
    }
    printf("%s", buf);
}

#endif /* TRIT_H */
