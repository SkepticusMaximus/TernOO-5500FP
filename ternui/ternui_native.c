/* ternui_native.c — Road B stage 2: the native window TALKS BACK.
 *
 * Eats the TUW0 word stream DIRECTLY (no TSV middleman), renders it as
 * a live SDL2 window, and closes the loop both ways through the stream:
 *   IN:  polls the .tuw file; when the engine rewrites it, the window
 *        re-decodes and repaints (~5 Hz). The stream feeds the face.
 *   OUT: clicks hit-test the decoded widgets and append
 *        "<name>\tclicked\n" to <stream>.sig — the engine's drive
 *        (ternui_drive.py) answers by walking the design and
 *        re-emitting words. No RPC, no JSON: words in, signals out.
 *
 * Build:  gcc -O2 -o ternui_native ternui_native.c \
 *             $(pkg-config --cflags --libs sdl2 SDL2_ttf)
 * Run:    ./ternui_native design.tuw
 *
 * Added: 23 Sep 2026 (Road B stage 2). Authors: Stevo + Claude.
 */
#include <SDL2/SDL.h>
#include <SDL2/SDL_ttf.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#define GRID 10
#define MAXN 512

typedef struct {
    char kind[64], name[64], scope[64], label[64];
    long x, y, w, h;
    int value;                        /* MVALUE (tri-state), default 0 */
    long colour;                      /* MPROP colour=, ternary cube */
    char items[768];                  /* MPROP items= (\n-joined) */
    int sel;                          /* selected row, -1 none */
    int tsize;                        /* MPROP size=, 0 = default */
    int rowh;                         /* listbox row height (render) */
} Node;
static Node NS[MAXN];
static int NN = 0;
static char SELECTED[64];             /* last-clicked radio, by name */

/* ── word decode (parity-proven in ternui_words.c) ──────────────────── */
static void trits(int64_t v, int t[24])
{
    for (int i = 0; i < 24; i++) {
        int64_t r = v % 3;
        if (r > 1)  r -= 3;
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
{
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

static int64_t *SW = NULL;            /* the live word stream */
static uint32_t SWN = 0;
static long TUD_OFF = 4;              /* consumed bytes of the .tud */

static void decode_stream(void);

static int load_stream(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) return 0;
    char magic[4]; uint32_t count;
    if (fread(magic, 1, 4, f) != 4 || memcmp(magic, "TUW0", 4) ||
        fread(&count, 4, 1, f) != 1) { fclose(f); return 0; }
    free(SW);
    SW = malloc(sizeof(int64_t) * count);
    if (fread(SW, sizeof(int64_t), count, f) != count) {
        fclose(f); return 0;
    }
    fclose(f);
    SWN = count;
    decode_stream();
    return NN;
}

/* Q3: apply appended TUD0 replace-records (pos, ndel, nins, words) —
 * WordStreamEdit on the wire, integer ops, deterministic. */
static int apply_tud(const char *tud)
{
    FILE *f = fopen(tud, "rb");
    if (!f) return 0;
    fseek(f, TUD_OFF, SEEK_SET);
    int applied = 0;
    uint32_t rec[3];
    while (fread(rec, 4, 3, f) == 3) {
        uint32_t pos = rec[0], ndel = rec[1], nins = rec[2];
        int64_t *ins = malloc(sizeof(int64_t) * (nins ? nins : 1));
        if (fread(ins, sizeof(int64_t), nins, f) != nins) {
            free(ins); break;                    /* partial write: retry */
        }
        if (pos + ndel > SWN) { free(ins); break; }
        uint32_t nn = SWN - ndel + nins;
        int64_t *nw = malloc(sizeof(int64_t) * nn);
        memcpy(nw, SW, sizeof(int64_t) * pos);
        memcpy(nw + pos, ins, sizeof(int64_t) * nins);
        memcpy(nw + pos + nins, SW + pos + ndel,
               sizeof(int64_t) * (SWN - pos - ndel));
        free(SW); free(ins);
        SW = nw; SWN = nn;
        TUD_OFF = ftell(f);
        applied++;
    }
    fclose(f);
    if (applied) decode_stream();
    return applied;
}

static void decode_stream(void)
{
    int64_t *W = SW;
    uint32_t count = SWN;
    NN = 0;
    char *last_attr = NULL; size_t last_cap = 0;
    for (uint32_t i = 0; i < count; i++) {
        int t[24]; trits(W[i], t);
        if (fieldv(t, 22, 2) != 2) continue;         /* OPCODE only */
        long family = fieldv(t, 20, 2);
        long arity  = fieldv(t, 18, 2) + 4;
        long op     = fieldv(t, 12, 6);
        int64_t *ops = &W[i + 1];
        long n = (i + 1 + arity <= count) ? arity : (long)(count - i - 1);
        if (family == -1 && op == 40 && n >= 2 && NN < MAXN) {
            int tm[24], td[24];
            trits(ops[0], tm); trits(ops[1], td);
            Node *nd = &NS[NN++];
            memset(nd, 0, sizeof *nd);
            nd->x = fieldv(tm, 9, 9) * GRID;
            nd->y = fieldv(tm, 0, 9) * GRID;
            nd->w = fieldv(td, 6, 6) * GRID;
            nd->h = fieldv(td, 0, 6) * GRID;
            decode_strings(ops + 2, (int)n - 2, nd->label,
                           sizeof nd->label);
            last_attr = nd->label; last_cap = sizeof nd->label;
        } else if (family == 1 && NN > 0) {
            Node *nd = &NS[NN - 1];
            char *dst = NULL; size_t cap = 0;
            if (op == 11) {                      /* peek for items= */
                char kv0[80] = "";
                decode_strings(ops, (int)n > 3 ? 3 : (int)n,
                               kv0, sizeof kv0);
                if (!strncmp(kv0, "items=", 6)) {
                    nd->items[0] = 0;
                    decode_strings(ops, (int)n, nd->items,
                                   sizeof nd->items);
                    memmove(nd->items, nd->items + 6,
                            strlen(nd->items + 6) + 1);
                    last_attr = nd->items;
                    last_cap = sizeof nd->items;
                    i += n;
                    continue;
                }
            }
            if (op == 0)      { dst = nd->kind;  cap = sizeof nd->kind; }
            else if (op == 1) { dst = nd->name;  cap = sizeof nd->name; }
            else if (op == 6) { dst = nd->scope; cap = sizeof nd->scope; }
            else if (op == 7) { dst = last_attr; cap = last_cap; }
            else if (op == 9 || op == 11) {      /* MFLAG / MPROP k=v */
                char kv[160] = "";
                decode_strings(ops, (int)n, kv, sizeof kv);
                if (op == 9 && !strncmp(kv, "label=", 6)) {
                    snprintf(nd->label, sizeof nd->label, "%.63s",
                             kv + 6);
                    last_attr = nd->label;   /* MMORE continues the flag */
                    last_cap = sizeof nd->label;
                } else {
                    if (op == 11 && !strncmp(kv, "colour=", 7))
                        nd->colour = atol(kv + 7);
                    if (op == 11 && !strncmp(kv, "selected=", 9))
                        nd->sel = -2;            /* engine confirmed */
                    if (op == 11 && !strncmp(kv, "size=", 5))
                        nd->tsize = (int)atol(kv + 5);
                    last_attr = NULL;        /* never a stale target */
                }
            } else if (op == 13 && n >= 1) {     /* MVALUE: DATA word */
                int tv[24]; trits(ops[0], tv);
                nd->value = (int)fieldv(tv, 0, 18);
                last_attr = NULL;
            } else if (op != 7) {
                last_attr = NULL;            /* unknown op: no bleed */
            }
            if (dst) {
                decode_strings(ops, (int)n, dst, cap);
                if (op != 7) { last_attr = dst; last_cap = cap; }
            }
        }
        i += n;
    }
}

/* ── render (FlowCode dark palette, spike lineage) ──────────────────── */
static const SDL_Color BG     = { 20,  20,  29, 255};
static const SDL_Color PANEL  = { 35,  35,  50, 255};
static const SDL_Color PANEL2 = { 43,  43,  61, 255};
static const SDL_Color LINE   = { 58,  58,  82, 255};
static const SDL_Color INK    = {232, 232, 240, 255};
static const SDL_Color DIM    = {139, 139, 160, 255};
static const SDL_Color ACCENT = { 61, 110, 168, 255};
static const SDL_Color ACC_HI = { 90, 150, 220, 255};

/* ── the HOUSE STROKE FONT (THF0, exported from the ruled tables) ──
 * one font, every size, no atlas: polylines on a 0..4 x -2..6 grid,
 * monospace advance 6, lowercase = small-caps at 2/3 (case is DATA). */
typedef struct { signed char x, y; } SPt;    /* quarter-grid units */
typedef struct { unsigned char npts; SPt pts[60]; } SPoly;
typedef struct { unsigned char npolys, advance4; SPoly polys[12]; } SGlyph;
static SGlyph *THF[3][244];           /* [case+1][ordinal+121] */
static int THF_OK = 0;
static int THF_V1 = 0;                /* outline font: FILL the glyphs */
static char THF_PATH[512];
static time_t THF_MTIME = 0;

static void thf_reset(void)
{
    for (int cs = 0; cs < 3; cs++)
        for (int o = 0; o < 244; o++) {
            free(THF[cs][o]);
            THF[cs][o] = NULL;
        }
    THF_OK = 0;
}

static void load_thf(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f) return;
    char magic[4];
    if (fread(magic, 1, 4, f) != 4 || memcmp(magic, "THF", 3)) {
        fclose(f); return;
    }
    int v1 = magic[3] == '1';
    THF_V1 = v1;
    {   struct stat fst;
        if (stat(path, &fst) == 0) THF_MTIME = fst.st_mtime;
        snprintf(THF_PATH, sizeof THF_PATH, "%s", path);
    }
    for (;;) {
        int32_t o; signed char cs = 0;
        unsigned char adv = 24, np;
        if (fread(&o, 4, 1, f) != 1) break;
        if (v1 && (fread(&cs, 1, 1, f) != 1 ||
                   fread(&adv, 1, 1, f) != 1)) break;
        if (fread(&np, 1, 1, f) != 1) break;
        SGlyph *g = calloc(1, sizeof *g);
        g->npolys = np > 12 ? 12 : np;
        g->advance4 = adv;
        for (int p = 0; p < np; p++) {
            unsigned char n2;
            if (fread(&n2, 1, 1, f) != 1) break;
            SPoly *pl = p < 12 ? &g->polys[p] : NULL;
            if (pl) pl->npts = n2 > 60 ? 60 : n2;
            for (int k = 0; k < n2; k++) {
                signed char xy[2];
                if (fread(xy, 1, 2, f) != 2) break;
                if (pl && k < 60) {
                    /* THF0 stores whole-grid; scale to quarter-grid */
                    pl->pts[k].x = v1 ? xy[0] : (signed char)(xy[0] * 4);
                    pl->pts[k].y = v1 ? xy[1] : (signed char)(xy[1] * 4);
                }
            }
        }
        if (o >= -121 && o <= 121 && cs >= -1 && cs <= 1)
            THF[cs + 1][o + 121] = g;
        else free(g);
    }
    fclose(f);
    THF_OK = 1;
}

/* the RULED seed table (23-09): digits 1-10, letters 11-36, space 37,
 * punctuation 38+, math band 52+ — mirrored from ternoo_glyph.py */
static int char_ordinal(unsigned char ch, int *small)
{
    *small = 0;
    if (ch >= '0' && ch <= '9') return 1 + ch - '0';
    if (ch >= 'A' && ch <= 'Z') return 11 + ch - 'A';
    if (ch >= 'a' && ch <= 'z') { *small = 1; return 11 + ch - 'a'; }
    switch (ch) {
    case ' ': return 37;  case '.': return 38;  case ',': return 39;
    case ':': return 40;  case ';': return 41;  case '!': return 42;
    case '?': return 43;  case '~': return 46;  case '-': return 47;
    case '\'': return 48; case '"': return 49;  case '(': return 50;
    case ')': return 51;  case '+': return 52;  case '=': return 56;
    case '<': return 58;  case '>': return 59;  case '/': return 63;
    case '\\': return 64; case '*': return 65;  case '^': return 66;
    case '%': return 67;  case '_': return 69;  case '|': return 70;
    case '#': return 71;  case '[': return 72;  case ']': return 73;
    case '{': return 74;  case '}': return 75;
    }
    return 46;                                   /* unknown -> ~ (R1) */
}

static void putpx2(SDL_Surface *s, int x, int y, Uint32 col)
{
    for (int dy = 0; dy < 2; dy++)
        for (int dx = 0; dx < 2; dx++) {
            int px = x + dx, py = y + dy;
            if (px >= 0 && px < s->w && py >= 0 && py < s->h)
                ((Uint32 *)((Uint8 *)s->pixels + py * s->pitch))[px] = col;
        }
}

static void bres(SDL_Surface *s, int x0, int y0, int x1, int y1,
                 Uint32 col)
{
    int dx = abs(x1 - x0), sx = x0 < x1 ? 1 : -1;
    int dy = -abs(y1 - y0), sy = y0 < y1 ? 1 : -1;
    int err = dx + dy;
    for (;;) {
        putpx2(s, x0, y0, col);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 >= dy) { err += dy; x0 += sx; }
        if (e2 <= dx) { err += dx; y0 += sy; }
    }
}

static void fill_glyph(SDL_Surface *s, SGlyph *g, int cx, int base,
                       int h, Uint32 col)
{
    float ex[128][2]; int ne = 0;
    float miny = 1e9f, maxy = -1e9f;
    for (int pi = 0; pi < g->npolys; pi++) {
        SPoly *pl = &g->polys[pi];
        for (int k = 0; k + 1 < pl->npts && ne < 126; k++) {
            float x1 = cx + pl->pts[k].x * (float)h / 24.0f;
            float y1 = base - pl->pts[k].y * (float)h / 24.0f;
            float x2 = cx + pl->pts[k + 1].x * (float)h / 24.0f;
            float y2 = base - pl->pts[k + 1].y * (float)h / 24.0f;
            if (y1 == y2) continue;
            ex[ne][0] = x1; ex[ne][1] = y1; ne++;
            ex[ne][0] = x2; ex[ne][1] = y2; ne++;
            if (y1 < miny) miny = y1; if (y2 < miny) miny = y2;
            if (y1 > maxy) maxy = y1; if (y2 > maxy) maxy = y2;
        }
    }
    for (int y = (int)miny; y <= (int)maxy + 1; y++) {
        float yc = y + 0.5f, xs[64]; int nx = 0;
        for (int e = 0; e + 1 < ne; e += 2) {
            float y1 = ex[e][1], y2 = ex[e + 1][1];
            if ((yc >= y1 && yc < y2) || (yc >= y2 && yc < y1)) {
                float t = (yc - y1) / (y2 - y1);
                if (nx < 64)
                    xs[nx++] = ex[e][0] + t * (ex[e + 1][0] - ex[e][0]);
            }
        }
        for (int a = 0; a < nx; a++)            /* insertion sort */
            for (int b = a + 1; b < nx; b++)
                if (xs[b] < xs[a]) { float t2 = xs[a]; xs[a] = xs[b];
                                     xs[b] = t2; }
        for (int p = 0; p + 1 < nx; p += 2) {
            int xa = (int)xs[p], xb = (int)(xs[p + 1] + 0.5f);
            if (xb > xa && y >= 0 && y < s->h) {
                if (xa < 0) xa = 0;
                if (xb > s->w) xb = s->w;
                Uint32 *rowp = (Uint32 *)((Uint8 *)s->pixels
                                          + y * s->pitch);
                for (int xx = xa; xx < xb; xx++) rowp[xx] = col;
            }
        }
    }
}

/* draw text with the house strokes. px = cap height in pixels;
 * (x, y) = top-left of the line box (box spans cap..descender). */
static void stroke_text(SDL_Surface *s, int x, int y, int px,
                        const char *txt, SDL_Color c)
{
    Uint32 col = SDL_MapRGB(s->format, c.r, c.g, c.b);
    int cx = x;
    for (const unsigned char *p = (const unsigned char *)txt; *p; p++) {
        unsigned char ch = *p;
        if (ch >= 0x80) {                        /* utf-8: ~ once */
            if ((ch & 0xC0) == 0x80) continue;
            ch = '~';
        }
        int small = 0;
        int o = char_ordinal(ch, &small);
        int cs = (ch >= 'A' && ch <= 'Z') ? 2 : small ? 0 : 1;
        SGlyph *g = THF[cs][o + 121];            /* exact case first */
        int h = px;
        if (!g) {                                /* fall through cases */
            g = THF[1][o + 121];
            if (!g && cs != 2) g = THF[2][o + 121];
            if (g && small) h = px * 2 / 3;      /* small-caps interim */
            if (!g) { g = THF[1][46 + 121];
                      if (!g) g = THF[2][46 + 121]; }
        }
        if (o == 37 || !g) { cx += px * 2 / 3; continue; }
        int base = y + px;                       /* baseline row */
        if (THF_V1) {
            fill_glyph(s, g, cx, base, h, col);  /* SOLID letterforms */
        } else
            for (int pi = 0; pi < g->npolys; pi++) {
                SPoly *pl = &g->polys[pi];
                if (pl->npts == 1) {
                    putpx2(s, cx + pl->pts[0].x * h / 24,
                           base - pl->pts[0].y * h / 24, col);
                    continue;
                }
                for (int k = 0; k + 1 < pl->npts; k++)
                    bres(s,
                         cx + pl->pts[k].x * h / 24,
                         base - pl->pts[k].y * h / 24,
                         cx + pl->pts[k + 1].x * h / 24,
                         base - pl->pts[k + 1].y * h / 24, col);
            }
        cx += g->advance4 * px / 24 + px / 4;    /* proportional + air */
    }
}

static const char *FONTS[] = {
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/TTF/DejaVuSans.ttf", NULL};

static int is_kind(const Node *w, const char *k)
{ return strcmp(w->kind, k) == 0; }

static int is_container(const Node *w)
{
    static const char *c[] = {"gui_window", "gui_dialog", "gui_box",
        "gui_frame", "gui_notebook", "gui_toolbar", "gui_statusbar",
        "gui_menubar", "gui_headerbar", "gui_actionbar", "gui_listbox",
        NULL};
    for (int i = 0; c[i]; i++)
        if (is_kind(w, c[i])) return 1;
    return 0;
}

static void fill(SDL_Surface *s, int x, int y, int w, int h, SDL_Color c)
{
    SDL_Rect r = {x, y, w, h};
    SDL_FillRect(s, &r, SDL_MapRGB(s->format, c.r, c.g, c.b));
}

static void frame(SDL_Surface *s, int x, int y, int w, int h, SDL_Color c)
{
    fill(s, x, y, w, 1, c); fill(s, x, y + h - 1, w, 1, c);
    fill(s, x, y, 1, h, c); fill(s, x + w - 1, y, 1, h, c);
}

static void text(SDL_Surface *s, TTF_Font *f, int x, int y,
                 const char *t, SDL_Color c)
{
    if (!t || !*t) return;
    if (THF_OK) {                     /* OUR strokes, any size, no atlas */
        stroke_text(s, x, y, f ? 10 : 8, t, c);
        return;
    }
    if (!f) return;
    SDL_Surface *ts = TTF_RenderUTF8_Blended(f, t, c);
    if (!ts) return;
    SDL_Rect d = {x, y, ts->w, ts->h};
    SDL_BlitSurface(ts, NULL, s, &d);
    SDL_FreeSurface(ts);
}

static SDL_Color cube_colour(long cube, SDL_Color dflt)
{
    if (cube == 0) return dflt;              /* 0 = inherit ink */
    int t[24]; trits(cube, t);
    int r = t[4] + 3 * t[5], g = t[2] + 3 * t[3], b = t[0] + 3 * t[1];
    SDL_Color c = { (Uint8)((r + 4) * 255 / 8),
                    (Uint8)((g + 4) * 255 / 8),
                    (Uint8)((b + 4) * 255 / 8), 255 };
    return c;
}

static TTF_Font *G_F = NULL;          /* ttf fallback handle */

static void wtext(SDL_Surface *s, int x, int y, int px,
                  const char *t, SDL_Color c)
{
    if (!t || !*t) return;
    if (THF_OK) { stroke_text(s, x, y, px, t, c); return; }
    if (!G_F) return;
    SDL_Surface *ts = TTF_RenderUTF8_Blended(G_F, t, c);
    if (!ts) return;
    SDL_Rect d = {x, y, ts->w, ts->h};
    SDL_BlitSurface(ts, NULL, s, &d);
    SDL_FreeSurface(ts);
}

static int OX, OY;                    /* stream-origin offset */

static void render(SDL_Surface *s, TTF_Font *f, TTF_Font *fs)
{
    fill(s, 0, 0, s->w, s->h, BG);
    for (int i = 0; i < NN; i++) {
        Node *w = &NS[i];
        int x = (int)w->x - OX, y = (int)w->y - OY;
        if (is_kind(w, "gui_window") || is_kind(w, "gui_dialog")) {
            fill(s, x, y, w->w, w->h, PANEL);
            frame(s, x, y, w->w, w->h, LINE);
            fill(s, x + 1, y + 1, w->w - 2, 24, PANEL2);
            text(s, fs, x + 10, y + 5,
                 "\xE2\x97\x8F \xE2\x97\x8F \xE2\x97\x8F", DIM);
            wtext(s, x + 52, y + 4, 12, w->label, INK);
        } else if (is_kind(w, "gui_button")) {
            fill(s, x, y, w->w, w->h, ACCENT);
            fill(s, x, y, w->w, 2, ACC_HI);
            frame(s, x, y, w->w, w->h, LINE);
            wtext(s, x + 10, y + (w->h - 18) / 2,
                  w->tsize ? w->tsize : 13, w->label, INK);
        } else if (is_kind(w, "gui_entry")) {
            fill(s, x, y, w->w, w->h, BG);
            frame(s, x, y, w->w, w->h, LINE);
            text(s, f, x + 8, y + (w->h - 18) / 2, w->label, DIM);
        } else if (is_kind(w, "gui_tritoggle") ||
                   is_kind(w, "gui_trifilter")) {
            const char *segs[3] = {"\xE2\x88\x92", "0", "+"};
            for (int k = 0; k < 3; k++) {
                int sx = x + k * 22;
                int on = (w->value == k - 1);
                fill(s, sx, y, 20, w->h > 26 ? 26 : (int)w->h,
                     on ? ACCENT : PANEL2);
                frame(s, sx, y, 20, w->h > 26 ? 26 : (int)w->h, LINE);
                text(s, NULL, sx + 6, y + 4, segs[k], on ? INK : DIM);
            }
            text(s, f, x + 72, y + 2, w->label,
                 cube_colour(w->colour, INK));
        } else if (is_kind(w, "gui_tritstrip")) {
            fill(s, x, y, w->w, w->h, PANEL2);
            frame(s, x, y, w->w, w->h, LINE);
            text(s, f, x + 8, y + (w->h - 18) / 2, w->label,
                 cube_colour(w->colour, INK));
        } else if (is_kind(w, "gui_radio") || is_kind(w, "gui_checkbox")) {
            int on = SELECTED[0] && !strcmp(w->name, SELECTED);
            text(s, f, x, y + 2, is_kind(w, "gui_radio")
                 ? (on ? "\xE2\x97\x89" : "\xE2\x97\x8B")
                 : "\xE2\x98\x90", on ? ACC_HI : DIM);
            text(s, f, x + 22, y + 2, w->label, on ? ACC_HI : INK);
        } else if (is_kind(w, "gui_label")) {
            wtext(s, x + 4, y + 2, w->tsize ? w->tsize : 14,
                  w->label, cube_colour(w->colour, INK));
        } else if (is_kind(w, "gui_listbox") && w->items[0]) {
            int px = w->tsize ? w->tsize : 14;
            int rh = px * 2 + 4;
            w->rowh = rh;
            fill(s, x, y, w->w, w->h, BG);
            frame(s, x, y, w->w, w->h, LINE);
            char tmp[768];
            snprintf(tmp, sizeof tmp, "%s", w->items);
            int row = 0;
            for (char *ln = strtok(tmp, "\n"); ln && row * rh + rh
                 < w->h; ln = strtok(NULL, "\n"), row++) {
                if (row == w->sel)
                    fill(s, x + 2, y + 4 + row * rh, w->w - 4, rh - 2,
                         ACCENT);
                wtext(s, x + 10, y + 6 + row * rh, px, ln, INK);
            }
        } else if (is_container(w)) {
            fill(s, x, y, w->w, w->h,
                 w->colour ? cube_colour(w->colour, PANEL2) : PANEL2);
            frame(s, x, y, w->w, w->h, LINE);
            text(s, fs, x + 8, y + 3, w->label, DIM);
        } else {
            text(s, f, x + 4, y + 2, w->label, INK);
        }
    }
}

static void bounds(int *W, int *H)
{
    long x0 = 1L << 30, y0 = 1L << 30, x1 = 0, y1 = 0;
    for (int i = 0; i < NN; i++) {
        if (NS[i].x < x0) x0 = NS[i].x;
        if (NS[i].y < y0) y0 = NS[i].y;
        if (NS[i].x + NS[i].w > x1) x1 = NS[i].x + NS[i].w;
        if (NS[i].y + NS[i].h > y1) y1 = NS[i].y + NS[i].h;
    }
    OX = (int)x0 - 20; OY = (int)y0 - 20;
    *W = (int)(x1 - x0) + 40; *H = (int)(y1 - y0) + 40;
}

int main(int argc, char **argv)
{
    if (argc < 2) { fprintf(stderr, "usage: %s design.tuw\n", argv[0]);
                    return 2; }
    const char *tuw = argv[1];
    char sig[512];
    snprintf(sig, sizeof sig, "%s.sig", tuw);
    const char *bmp = (argc >= 4 && !strcmp(argv[2], "--bmp"))
                      ? argv[3] : NULL;
    if (!load_stream(tuw)) { fprintf(stderr, "no widgets\n"); return 2; }
    {   /* the house font travels beside the binary or in the repo */
        const char *env = getenv("TERNUI_FONT");
        const char *cand[] = {env, "ternui/house_font.thf",
                              "/tmp/house_font.thf", "house_font.thf",
                              NULL};
        for (int i = 0; i < 4 && !THF_OK; i++)
            if (cand[i]) load_thf(cand[i]);
    }
    if (bmp) SDL_setenv("SDL_VIDEODRIVER", "dummy", 1);
    if (SDL_Init(SDL_INIT_VIDEO) || TTF_Init()) {
        fprintf(stderr, "init: %s\n", SDL_GetError()); return 1;
    }
    TTF_Font *f = NULL, *fs = NULL;
    for (int i = 0; FONTS[i] && !f; i++) {
        f = TTF_OpenFont(FONTS[i], 15);
        fs = TTF_OpenFont(FONTS[i], 12);
    }
    G_F = f;
    int W, H; bounds(&W, &H);
    if (bmp) {
        char tud0[520];
        snprintf(tud0, sizeof tud0, "%s.tud", tuw);
        apply_tud(tud0);                 /* candy shows the LIVE state */
        SDL_Surface *bs = SDL_CreateRGBSurfaceWithFormat(
            0, W, H, 32, SDL_PIXELFORMAT_ARGB8888);
        render(bs, THF_OK ? (TTF_Font *)1 : NULL, NULL); /* size token */
        SDL_SaveBMP(bs, bmp);
        printf("TernUI native (house strokes%s): %d widgets -> %s\n",
               THF_OK ? "" : " UNAVAILABLE", NN, bmp);
        return 0;
    }
    SDL_Window *win = SDL_CreateWindow(
        "TernUI - live on the word stream",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        W > 1500 ? 1500 : W, H > 950 ? 950 : H, SDL_WINDOW_RESIZABLE);
    struct stat st;
    time_t last_m = (stat(tuw, &st) == 0) ? st.st_mtime : 0;
    int dirty = 1;
    for (;;) {
        SDL_Event ev;
        while (SDL_PollEvent(&ev)) {
            if (ev.type == SDL_QUIT) goto done;
            if (ev.type == SDL_KEYDOWN &&
                ev.key.keysym.sym == SDLK_ESCAPE) goto done;
            if (ev.type == SDL_WINDOWEVENT) dirty = 1;
            if (ev.type == SDL_MOUSEBUTTONDOWN) {
                int mx = ev.button.x + OX, my = ev.button.y + OY;
                for (int i = NN - 1; i >= 0; i--) {   /* topmost first */
                    Node *n = &NS[i];
                    int isl = is_kind(n, "gui_listbox") && n->items[0];
                    if (is_container(n) && !isl) continue;
                    if (mx >= n->x && mx <= n->x + n->w &&
                        my >= n->y && my <= n->y + n->h) {
                        if (is_kind(n, "gui_radio"))
                            snprintf(SELECTED, sizeof SELECTED, "%s",
                                     n->name);
                        FILE *sf = fopen(sig, "a");
                        if (sf) {
                            if (isl) {
                                int rh2 = n->rowh ? n->rowh : 22;
                                int row = (int)((my - n->y - 4) / rh2);
                                n->sel = row;
                                fprintf(sf, "%s\tclicked\t%d\n",
                                        n->name, row);
                            } else
                                fprintf(sf, "%s\tclicked\n", n->name);
                            fclose(sf);
                        }
                        dirty = 1;
                        break;
                    }
                }
            }
        }
        char tud[520];
        snprintf(tud, sizeof tud, "%s.tud", tuw);
        if (apply_tud(tud)) dirty = 1;           /* Q3 deltas */
        {   struct stat fst;                     /* live font swap */
            if (THF_PATH[0] && stat(THF_PATH, &fst) == 0
                && fst.st_mtime != THF_MTIME) {
                char keep[512];
                snprintf(keep, sizeof keep, "%s", THF_PATH);
                SDL_Delay(50);
                thf_reset();
                load_thf(keep);
                dirty = 1;
            }
        }
        if (stat(tuw, &st) == 0 && st.st_mtime != last_m) {
            last_m = st.st_mtime;      /* baseline rewritten */
            SDL_Delay(30);
            TUD_OFF = 4;
            if (load_stream(tuw)) dirty = 1;
        }
        if (dirty) {
            SDL_Surface *ws = SDL_GetWindowSurface(win);
            render(ws, f, fs);
            SDL_UpdateWindowSurface(win);
            dirty = 0;
        }
        SDL_Delay(60);
    }
done:
    SDL_DestroyWindow(win);
    if (f) TTF_CloseFont(f);
    if (fs) TTF_CloseFont(fs);
    TTF_Quit(); SDL_Quit();
    return 0;
}
