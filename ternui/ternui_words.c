/* ternui_words.c — Road B stage 1: C decodes CANONICAL TernOO WORDS.
 *
 * Reads a TUW0 word-stream binary (ternui_words.py) and walks the
 * 24-trit balanced-ternary words themselves: OPCODE spans (PIGART
 * RNODE geometry, MODEL kind/name/scope strings, MMORE continuation)
 * — no JSON, no TSV in, no Python. Emits the renderer TSV; parity
 * with the python decoder (meccano_to_model) is the acceptance test.
 *
 * Per CF5's 23-09 rulings: RNODE grammar unchanged; containment read
 * from the stream (MSCOPE by name).
 *
 * Build: gcc -O2 -o ternui_words ternui_words.c
 * Added: 23 Sep 2026 (Road B stage 1). Authors: Stevo + Claude.
 */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define GRID 10                       /* FC_GRID_TO_MECCANO */
#define MAXN 512

typedef struct {
    char kind[64], name[64], scope[64], label[64];
    long x, y, w, h;
} Node;
static Node NS[MAXN];
static int NN = 0;

/* balanced-ternary trits of a word, LSB first */
static void trits(int64_t v, int t[24])
{
    for (int i = 0; i < 24; i++) {
        int64_t r = v % 3;               /* C remainder: -2..2 */
        if (r > 1)  r -= 3;              /* normalise to balanced */
        if (r < -1) r += 3;
        t[i] = (int)r;
        v = (v - r) / 3;
    }
}

static long fieldv(const int t[24], int lsb, int width)
{
    long v = 0, p = 1;
    for (int i = 0; i < width; i++) { v += (long)t[lsb + i] * p; p *= 3; }
    return v;
}

static int is_string_word(const int t[24])
{   /* DATA primary (-1,+1) with qualifier T21=+1, T20=-1 */
    return t[23] == -1 && t[22] == 1 && t[21] == 1 && t[20] == -1;
}

static void append_chars(char *dst, size_t cap, long pay)
{
    char c[4] = { (char)(pay % 128), (char)((pay / 128) % 128),
                  (char)((pay / 16384) % 128), 0 };
    size_t l = strlen(dst);
    for (int i = 0; i < 3 && l + 1 < cap; i++)
        if (c[i]) dst[l++] = c[i];
    dst[l] = 0;
}

static void decode_strings(int64_t *ops, int n, char *dst, size_t cap)
{
    for (int i = 0; i < n; i++) {
        int t[24]; trits(ops[i], t);
        if (!is_string_word(t)) continue;
        append_chars(dst, cap, fieldv(t, 0, 18));
    }
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s file.tuw\n", argv[0]);
                    return 2; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 2; }
    char magic[4]; uint32_t count;
    if (fread(magic, 1, 4, f) != 4 || memcmp(magic, "TUW0", 4) ||
        fread(&count, 4, 1, f) != 1) {
        fprintf(stderr, "bad TUW0 header\n"); return 2;
    }
    int64_t *W = malloc(sizeof(int64_t) * count);
    if (fread(W, sizeof(int64_t), count, f) != count) {
        fprintf(stderr, "short read\n"); return 2;
    }
    fclose(f);

    char *last_attr = NULL; size_t last_cap = 0;
    for (uint32_t i = 0; i < count; i++) {
        int t[24]; trits(W[i], t);
        long primary = fieldv(t, 22, 2);
        if (primary != 2) continue;              /* OPCODE = (+1,-1) */
        long family = fieldv(t, 20, 2);
        long arity  = fieldv(t, 18, 2) + 4;
        long op     = fieldv(t, 12, 6);
        int64_t *ops = &W[i + 1];
        long n = (i + 1 + arity <= count) ? arity : (long)(count - i - 1);
        if (family == -1 && op == 40 && n >= 2 && NN < MAXN) {
            /* PIGART RNODE: MAP(xy) + dims + shape + STRING label words */
            int tm[24], td[24];
            trits(ops[0], tm); trits(ops[1], td);
            Node *nd = &NS[NN++];
            memset(nd, 0, sizeof *nd);
            nd->x = fieldv(tm, 9, 9); nd->y = fieldv(tm, 0, 9);
            nd->w = fieldv(td, 6, 6); nd->h = fieldv(td, 0, 6);
            decode_strings(ops + 2, (int)n - 2, nd->label,
                           sizeof nd->label);
            last_attr = nd->label; last_cap = sizeof nd->label;
        } else if (family == 1 && NN > 0) {      /* MODEL */
            Node *nd = &NS[NN - 1];
            char *dst = NULL; size_t cap = 0;
            if (op == 0)      { dst = nd->kind;  cap = sizeof nd->kind; }
            else if (op == 1) { dst = nd->name;  cap = sizeof nd->name; }
            else if (op == 6) { dst = nd->scope; cap = sizeof nd->scope; }
            else if (op == 7) { dst = last_attr; cap = last_cap; }
            else if (op == 9) {                  /* MFLAG key=value */
                char kv[160] = "";
                decode_strings(ops, (int)n, kv, sizeof kv);
                if (!strncmp(kv, "label=", 6)) {
                    snprintf(nd->label, sizeof nd->label, "%.63s",
                             kv + 6);
                    last_attr = nd->label;   /* MMORE continues the flag */
                    last_cap = sizeof nd->label;
                } else {
                    last_attr = NULL;        /* never a stale target */
                }
            } else if (op != 7) {
                last_attr = NULL;            /* unknown op: no bleed */
            }
            if (dst) {
                decode_strings(ops, (int)n, dst, cap);
                if (op != 7) { last_attr = dst; last_cap = cap; }
            }
        }
        i += n;                                  /* skip operands */
    }
    for (int k = 0; k < NN; k++)
        printf("%s\t%ld\t%ld\t%ld\t%ld\t%s\t%s\t%s\n",
               NS[k].kind, NS[k].x * GRID, NS[k].y * GRID,
               NS[k].w * GRID, NS[k].h * GRID,
               NS[k].label, NS[k].name, NS[k].scope);
    free(W);
    return 0;
}
