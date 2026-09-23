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
    if (!t || !*t || !f) return;
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
            text(s, fs, x + 52, y + 4, w->label, INK);
        } else if (is_kind(w, "gui_button")) {
            fill(s, x, y, w->w, w->h, ACCENT);
            fill(s, x, y, w->w, 2, ACC_HI);
            frame(s, x, y, w->w, w->h, LINE);
            text(s, f, x + 10, y + (w->h - 18) / 2, w->label, INK);
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
                text(s, fs, sx + 6, y + 4, segs[k], on ? INK : DIM);
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
            text(s, f, x + 4, y + 2, w->label,
                 cube_colour(w->colour, INK));
        } else if (is_container(w)) {
            fill(s, x, y, w->w, w->h, PANEL2);
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
    if (!load_stream(tuw)) { fprintf(stderr, "no widgets\n"); return 2; }
    if (SDL_Init(SDL_INIT_VIDEO) || TTF_Init()) {
        fprintf(stderr, "init: %s\n", SDL_GetError()); return 1;
    }
    TTF_Font *f = NULL, *fs = NULL;
    for (int i = 0; FONTS[i] && !f; i++) {
        f = TTF_OpenFont(FONTS[i], 15);
        fs = TTF_OpenFont(FONTS[i], 12);
    }
    int W, H; bounds(&W, &H);
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
                    if (is_container(n)) continue;
                    if (mx >= n->x && mx <= n->x + n->w &&
                        my >= n->y && my <= n->y + n->h) {
                        if (is_kind(n, "gui_radio"))
                            snprintf(SELECTED, sizeof SELECTED, "%s",
                                     n->name);
                        FILE *sf = fopen(sig, "a");
                        if (sf) { fprintf(sf, "%s\tclicked\n", n->name);
                                  fclose(sf); }
                        dirty = 1;
                        break;
                    }
                }
            }
        }
        char tud[520];
        snprintf(tud, sizeof tud, "%s.tud", tuw);
        if (apply_tud(tud)) dirty = 1;           /* Q3 deltas */
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
