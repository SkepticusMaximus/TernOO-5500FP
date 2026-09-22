/* ternui_spike.c — Road B stage 0: the FIRST native TernUI renderer.
 *
 * Reads a ternui dump (see ternui_dump.py) and renders the design's
 * GUI as a REAL desktop window — C + SDL2 + SDL_ttf, no Python, no
 * browser, no host widget kit. The FlowCode dark palette, painted by
 * our own hand.
 *
 * Modes:
 *   ./ternui_spike design.dump              live window (Esc/close quits)
 *   ./ternui_spike design.dump --bmp out.bmp  headless render to BMP
 *
 * Build (Lenny carries the kit):
 *   gcc -O2 -o ternui_spike ternui_spike.c $(pkg-config --cflags --libs \
 *       sdl2 SDL2_ttf)
 *
 * TEMPORARY SEAM: consumes the TSV dump only until the widget word
 * vocabulary is ruled (CF5 gate) — then this reads TernOO words.
 *
 * Added: 23 Sep 2026 (Road B stage 0). Authors: Stevo + Claude.
 */
#include <SDL2/SDL.h>
#include <SDL2/SDL_ttf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAXW 512
typedef struct { char kind[40]; int x, y, w, h; char label[160]; } Widget;

static Widget WS[MAXW];
static int NW = 0;

/* FlowCode dark palette */
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
    "/usr/share/fonts/TTF/DejaVuSans.ttf",
    NULL};

static int is_kind(const Widget *w, const char *k)
{ return strcmp(w->kind, k) == 0; }

static int is_container(const Widget *w)
{
    static const char *c[] = {"gui_window", "gui_dialog", "gui_box",
        "gui_frame", "gui_notebook", "gui_toolbar", "gui_statusbar",
        "gui_menubar", "gui_headerbar", "gui_actionbar", "gui_listbox",
        "gui_grid", "gui_paned", "gui_scrolled", "gui_stack", NULL};
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

static void render(SDL_Surface *s, TTF_Font *f, TTF_Font *fsmall,
                   int ox, int oy)
{
    fill(s, 0, 0, s->w, s->h, BG);
    for (int i = 0; i < NW; i++) {
        Widget *w = &WS[i];
        int x = w->x - ox, y = w->y - oy;
        if (is_kind(w, "gui_window") || is_kind(w, "gui_dialog")) {
            fill(s, x, y, w->w, w->h, PANEL);
            frame(s, x, y, w->w, w->h, LINE);
            fill(s, x + 1, y + 1, w->w - 2, 24, PANEL2);
            fill(s, x + 1, y + 25, w->w - 2, 1, LINE);
            text(s, fsmall, x + 10, y + 5, "\xE2\x97\x8F \xE2\x97\x8F "
                 "\xE2\x97\x8F", DIM);
            text(s, fsmall, x + 52, y + 4, w->label, INK);
        } else if (is_kind(w, "gui_button")) {
            fill(s, x, y, w->w, w->h, ACCENT);
            fill(s, x, y, w->w, 2, ACC_HI);
            frame(s, x, y, w->w, w->h, LINE);
            text(s, f, x + 10, y + (w->h - 18) / 2, w->label, INK);
        } else if (is_kind(w, "gui_entry")) {
            fill(s, x, y, w->w, w->h, BG);
            frame(s, x, y, w->w, w->h, LINE);
            text(s, f, x + 8, y + (w->h - 18) / 2, w->label, DIM);
        } else if (is_kind(w, "gui_radio") || is_kind(w, "gui_checkbox")) {
            text(s, f, x, y + 2, is_kind(w, "gui_radio")
                 ? "\xE2\x97\x89" : "\xE2\x98\x90", ACC_HI);
            text(s, f, x + 22, y + 2, w->label, INK);
        } else if (is_kind(w, "gui_label")) {
            text(s, f, x + 4, y + 2, w->label, INK);
        } else if (is_container(w)) {
            fill(s, x, y, w->w, w->h, PANEL2);
            frame(s, x, y, w->w, w->h, LINE);
            text(s, fsmall, x + 8, y + 3, w->label, DIM);
        } else {
            text(s, f, x + 4, y + 2, w->label, INK);
        }
    }
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s design.dump [--bmp out.bmp]\n", argv[0]);
        return 2;
    }
    FILE *fp = fopen(argv[1], "r");
    if (!fp) { perror(argv[1]); return 2; }
    char line[512], title[128] = "TernUI";
    int x0 = 1 << 30, y0 = 1 << 30, x1 = 0, y1 = 0;
    while (fgets(line, sizeof line, fp) && NW < MAXW) {
        if (line[0] == '#') {
            const char *d = strstr(line, "\xE2\x80\x94");
            if (d) { snprintf(title, sizeof title, "TernUI \xE2\x80\x94%s",
                              d + 3); title[strcspn(title, "\n")] = 0; }
            continue;
        }
        Widget *w = &WS[NW];
        char *tok = strtok(line, "\t");
        if (!tok) continue;
        snprintf(w->kind, sizeof w->kind, "%s", tok);
        w->x = atoi(strtok(NULL, "\t") ?: "0");
        w->y = atoi(strtok(NULL, "\t") ?: "0");
        w->w = atoi(strtok(NULL, "\t") ?: "40");
        w->h = atoi(strtok(NULL, "\t") ?: "20");
        tok = strtok(NULL, "\n");
        snprintf(w->label, sizeof w->label, "%s", tok ? tok : "");
        if (w->x < x0) x0 = w->x;
        if (w->y < y0) y0 = w->y;
        if (w->x + w->w > x1) x1 = w->x + w->w;
        if (w->y + w->h > y1) y1 = w->y + w->h;
        NW++;
    }
    fclose(fp);
    if (!NW) { fprintf(stderr, "no widgets in dump\n"); return 2; }
    int W = x1 - x0 + 40, H = y1 - y0 + 40;
    const char *bmp = (argc >= 4 && !strcmp(argv[2], "--bmp")) ? argv[3]
                                                               : NULL;
    if (bmp) SDL_setenv("SDL_VIDEODRIVER", "dummy", 1);
    if (SDL_Init(SDL_INIT_VIDEO) || TTF_Init()) {
        fprintf(stderr, "init: %s\n", SDL_GetError()); return 1;
    }
    TTF_Font *f = NULL, *fs = NULL;
    for (int i = 0; FONTS[i] && !f; i++) {
        f = TTF_OpenFont(FONTS[i], 15);
        fs = TTF_OpenFont(FONTS[i], 12);
    }
    SDL_Surface *s = SDL_CreateRGBSurfaceWithFormat(
        0, W, H, 32, SDL_PIXELFORMAT_ARGB8888);
    render(s, f, fs, x0 - 20, y0 - 20);
    if (bmp) {
        SDL_SaveBMP(s, bmp);
        printf("TernUI native render: %d widgets -> %s (%dx%d)\n",
               NW, bmp, W, H);
    } else {
        SDL_Window *win = SDL_CreateWindow(
            title, SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
            W > 1500 ? 1500 : W, H > 950 ? 950 : H,
            SDL_WINDOW_RESIZABLE);
        SDL_Surface *ws = SDL_GetWindowSurface(win);
        SDL_BlitSurface(s, NULL, ws, NULL);
        SDL_UpdateWindowSurface(win);
        SDL_Event ev;
        for (;;) {
            SDL_WaitEvent(&ev);
            if (ev.type == SDL_QUIT) break;
            if (ev.type == SDL_KEYDOWN &&
                ev.key.keysym.sym == SDLK_ESCAPE) break;
            if (ev.type == SDL_WINDOWEVENT) {
                ws = SDL_GetWindowSurface(win);
                SDL_BlitSurface(s, NULL, ws, NULL);
                SDL_UpdateWindowSurface(win);
            }
        }
        SDL_DestroyWindow(win);
    }
    SDL_FreeSurface(s);
    if (f) TTF_CloseFont(f);
    if (fs) TTF_CloseFont(fs);
    TTF_Quit(); SDL_Quit();
    return 0;
}
