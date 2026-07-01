/*
 * pigart_sdl.c — PIGART SDL2 backend
 *
 * Renders PIGART drawing operations to an SDL2 window with SDL_ttf text.
 * This file is compiled only when SDL2 and SDL2_ttf are available (detected
 * via pkg-config in the Makefile); otherwise a stub backend is linked.
 *
 * Font search order (first existing file wins):
 *   /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf
 *   /usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf
 *   /usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf
 *   /usr/share/fonts/TTF/DejaVuSansMono.ttf
 *   /Library/Fonts/Courier New.ttf
 *
 * draw_oval: 32-point polygon approximation (no SDL2_gfx dependency).
 * draw_polygon fill: scanline algorithm.
 * sleep_ms: pumps SDL events at ~16ms intervals to keep window responsive.
 *
 * Phase 7b-2, TernOO 5500FP project.
 * Date: 2026-06-19, Adelaide.
 */

#ifdef PIGART_SDL_ENABLED

#include "../include/pigart.h"
#include <SDL2/SDL.h>
#include <SDL2/SDL_ttf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

/* M_PI is a POSIX extension, not guaranteed by C11 */
#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

/* -----------------------------------------------------------------------
 * Static SDL state
 * --------------------------------------------------------------------- */
static SDL_Window   *g_window   = NULL;
static SDL_Renderer *g_renderer = NULL;
static TTF_Font     *g_font     = NULL;
static int           g_font_size_cached = 0;
static Uint32        g_open_tick = 0;
static int           g_open      = 0;

/* Font search paths (D6) */
static const char *font_search_paths[] = {
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansMono-Regular.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    "/Library/Fonts/Courier New.ttf",
    NULL
};

/* -----------------------------------------------------------------------
 * Internal helpers
 * --------------------------------------------------------------------- */

static void set_draw_color(SDL_Renderer *r, uint32_t rgb, Uint8 alpha) {
    Uint8 red   = (rgb >> 16) & 0xFF;
    Uint8 green = (rgb >>  8) & 0xFF;
    Uint8 blue  =  rgb        & 0xFF;
    SDL_SetRenderDrawColor(r, red, green, blue, alpha);
}

/* Ensure font is loaded at (approximately) the given pixel size.
 * Caches one font at a time; reloads if size changes significantly. */
static TTF_Font *get_font(int size) {
    if (size <= 0) size = 16;
    if (g_font && abs(g_font_size_cached - size) < 2)
        return g_font;
    if (g_font) { TTF_CloseFont(g_font); g_font = NULL; }
    for (int i = 0; font_search_paths[i]; i++) {
        g_font = TTF_OpenFont(font_search_paths[i], size);
        if (g_font) {
            g_font_size_cached = size;
            return g_font;
        }
    }
    fprintf(stderr, "[PIGART SDL] Warning: no font found — text will not render.\n");
    return NULL;
}

/* -----------------------------------------------------------------------
 * Polygon scanline fill (pure SDL2, ~50 lines)
 * --------------------------------------------------------------------- */
static void scanline_fill(SDL_Renderer *r, int n, const SDL_Point *pts) {
    if (n < 3) return;
    /* Find y extents */
    int miny = pts[0].y, maxy = pts[0].y;
    for (int i = 1; i < n; i++) {
        if (pts[i].y < miny) miny = pts[i].y;
        if (pts[i].y > maxy) maxy = pts[i].y;
    }
    /* For each scan line */
    for (int y = miny; y <= maxy; y++) {
        /* Find intersections with polygon edges */
        int xs[256];
        int nxs = 0;
        for (int i = 0; i < n; i++) {
            int j = (i + 1) % n;
            int y0 = pts[i].y, y1 = pts[j].y;
            int x0 = pts[i].x, x1 = pts[j].x;
            if ((y0 <= y && y < y1) || (y1 <= y && y < y0)) {
                /* Intersection at x */
                int x = x0 + (x1 - x0) * (y - y0) / (y1 - y0);
                if (nxs < 256) xs[nxs++] = x;
            }
        }
        /* Sort xs */
        for (int a = 0; a < nxs - 1; a++)
            for (int b = a + 1; b < nxs; b++)
                if (xs[b] < xs[a]) { int t = xs[a]; xs[a] = xs[b]; xs[b] = t; }
        /* Draw horizontal spans */
        for (int k = 0; k + 1 < nxs; k += 2)
            SDL_RenderDrawLine(r, xs[k], y, xs[k+1], y);
    }
}

/* Draw outline of a polygon */
static void poly_outline(SDL_Renderer *r, int n, const SDL_Point *pts) {
    for (int i = 0; i < n; i++) {
        int j = (i + 1) % n;
        SDL_RenderDrawLine(r, pts[i].x, pts[i].y, pts[j].x, pts[j].y);
    }
}

/* -----------------------------------------------------------------------
 * Oval helper: 32-point polygon approximation
 * --------------------------------------------------------------------- */
static void draw_oval_approx(SDL_Renderer *r, int x, int y, int w, int h,
                              uint32_t color, int filled) {
    set_draw_color(r, color, 255);
    double cx = x + w / 2.0;
    double cy = y + h / 2.0;
    double rx = w / 2.0;
    double ry = h / 2.0;
    const int N = 32;
    SDL_Point pts[32];
    for (int i = 0; i < N; i++) {
        double t = (2.0 * M_PI * i) / N;
        pts[i].x = (int)(cx + rx * cos(t));
        pts[i].y = (int)(cy + ry * sin(t));
    }
    if (filled)
        scanline_fill(r, N, pts);
    else
        poly_outline(r, N, pts);
}

/* -----------------------------------------------------------------------
 * Backend operations
 * --------------------------------------------------------------------- */

static int sdl_open_window(int w, int h, const char *title) {
    if (SDL_Init(SDL_INIT_VIDEO | SDL_INIT_TIMER) < 0) {
        fprintf(stderr, "[PIGART SDL] SDL_Init failed: %s\n", SDL_GetError());
        return 0;
    }
    if (TTF_Init() < 0) {
        fprintf(stderr, "[PIGART SDL] TTF_Init failed: %s\n", TTF_GetError());
        SDL_Quit();
        return 0;
    }
    g_window = SDL_CreateWindow(
        title ? title : "5500FP PIGART",
        SDL_WINDOWPOS_CENTERED, SDL_WINDOWPOS_CENTERED,
        w, h, SDL_WINDOW_SHOWN);
    if (!g_window) {
        fprintf(stderr, "[PIGART SDL] CreateWindow failed: %s\n", SDL_GetError());
        TTF_Quit(); SDL_Quit();
        return 0;
    }
    g_renderer = SDL_CreateRenderer(g_window, -1,
        SDL_RENDERER_ACCELERATED | SDL_RENDERER_PRESENTVSYNC);
    if (!g_renderer) {
        /* Fallback to software renderer */
        g_renderer = SDL_CreateRenderer(g_window, -1, SDL_RENDERER_SOFTWARE);
    }
    if (!g_renderer) {
        fprintf(stderr, "[PIGART SDL] CreateRenderer failed: %s\n", SDL_GetError());
        SDL_DestroyWindow(g_window); g_window = NULL;
        TTF_Quit(); SDL_Quit();
        return 0;
    }
    SDL_SetRenderDrawBlendMode(g_renderer, SDL_BLENDMODE_BLEND);
    /* Raise and focus window immediately so WM close-button clicks register
     * on the first click rather than first focusing then closing. */
    SDL_RaiseWindow(g_window);
    SDL_SetWindowInputFocus(g_window);
    /* Enable SDL text input so SDL_TEXTINPUT events deliver the actual typed
     * character (respecting Shift/CapsLock/layout).  gui_entry text relies on
     * this rather than raw keysyms — see SDL_TEXTINPUT handling in poll. */
    SDL_StartTextInput();
    g_open_tick = SDL_GetTicks();
    g_open = 1;
    return 1;
}

static void sdl_close_window(void) {
    if (g_font)     { TTF_CloseFont(g_font); g_font = NULL; }
    if (g_renderer) { SDL_DestroyRenderer(g_renderer); g_renderer = NULL; }
    if (g_window)   { SDL_DestroyWindow(g_window);   g_window   = NULL; }
    TTF_Quit();
    SDL_Quit();
    g_open = 0;
}

static void sdl_clear(uint32_t color) {
    set_draw_color(g_renderer, color, 255);
    SDL_RenderClear(g_renderer);
}

static void sdl_draw_rect(int x, int y, int w, int h,
                           uint32_t color, int filled) {
    set_draw_color(g_renderer, color, 255);
    SDL_Rect r = { x, y, w, h };
    if (filled)
        SDL_RenderFillRect(g_renderer, &r);
    else
        SDL_RenderDrawRect(g_renderer, &r);
}

static void sdl_draw_polygon(int n, const pigart_point_t *pts,
                              uint32_t color, int filled) {
    if (n < 2) return;
    set_draw_color(g_renderer, color, 255);
    /* Convert to SDL_Point */
    SDL_Point sp[256];
    int cn = (n > 256) ? 256 : n;
    for (int i = 0; i < cn; i++) {
        sp[i].x = (int)pts[i].x;
        sp[i].y = (int)pts[i].y;
    }
    if (filled)
        scanline_fill(g_renderer, cn, sp);
    else
        poly_outline(g_renderer, cn, sp);
}

static void sdl_draw_oval(int x, int y, int w, int h,
                           uint32_t color, int filled) {
    draw_oval_approx(g_renderer, x, y, w, h, color, filled);
}

static void sdl_draw_text(int x, int y, const char *text,
                           int size, uint32_t color) {
    if (!text || !text[0]) return;
    TTF_Font *font = get_font(size);
    if (!font) return;

    SDL_Color c = {
        (Uint8)((color >> 16) & 0xFF),
        (Uint8)((color >>  8) & 0xFF),
        (Uint8)( color        & 0xFF),
        255
    };
    SDL_Surface *surf = TTF_RenderUTF8_Blended(font, text, c);
    if (!surf) return;
    SDL_Texture *tex  = SDL_CreateTextureFromSurface(g_renderer, surf);
    SDL_FreeSurface(surf);
    if (!tex) return;

    int tw, th;
    SDL_QueryTexture(tex, NULL, NULL, &tw, &th);
    SDL_Rect dst = { x, y, tw, th };
    SDL_RenderCopy(g_renderer, tex, NULL, &dst);
    SDL_DestroyTexture(tex);
}

static void sdl_draw_line(int x1, int y1, int x2, int y2, uint32_t color) {
    set_draw_color(g_renderer, color, 255);
    SDL_RenderDrawLine(g_renderer, x1, y1, x2, y2);
}

static void sdl_present(void) {
    SDL_RenderPresent(g_renderer);
}

static int sdl_poll_event(int64_t *out_buf4) {
    SDL_Event ev;
    /* Pump to get next event */
    while (SDL_PollEvent(&ev)) {
        switch (ev.type) {
            case SDL_QUIT:
                out_buf4[0] = PIGART_EVENT_CLOSE;
                out_buf4[1] = 0; out_buf4[2] = 0; out_buf4[3] = 0;
                return 1;
            case SDL_WINDOWEVENT:
                /* On Linux/X11 the WM sends WINDOWEVENT_CLOSE when the user
                 * clicks the title-bar X; SDL_QUIT may or may not follow.
                 * Treat WINDOWEVENT_CLOSE identically to SDL_QUIT. */
                if (ev.window.event == SDL_WINDOWEVENT_CLOSE) {
                    out_buf4[0] = PIGART_EVENT_CLOSE;
                    out_buf4[1] = 0; out_buf4[2] = 0; out_buf4[3] = 0;
                    return 1;
                }
                continue;
            case SDL_TEXTINPUT:
                /* Actual typed character(s), UTF-8.  For entry text we only
                 * consume printable ASCII (32-126); the compiler's key handler
                 * filters the same range.  This is what lets Shift/uppercase
                 * and symbols reach the text buffer — raw keysyms cannot. */
                out_buf4[0] = PIGART_EVENT_KEY_DOWN;
                out_buf4[1] = (unsigned char)ev.text.text[0];
                out_buf4[2] = 0;
                out_buf4[3] = 0;
                return 1;
            case SDL_KEYDOWN:
                /* Printable keys are delivered via SDL_TEXTINPUT (above); skip
                 * them here so a character is not emitted twice.  Non-printable
                 * keys (Backspace, Enter, Escape, arrows, …) still pass through
                 * as raw keysyms for any handler that wants them. */
                if (ev.key.keysym.sym >= 32 && ev.key.keysym.sym < 127)
                    continue;
                out_buf4[0] = PIGART_EVENT_KEY_DOWN;
                out_buf4[1] = ev.key.keysym.sym;
                out_buf4[2] = ev.key.keysym.mod;
                out_buf4[3] = 0;
                return 1;
            case SDL_KEYUP:
                out_buf4[0] = PIGART_EVENT_KEY_UP;
                out_buf4[1] = ev.key.keysym.sym;
                out_buf4[2] = ev.key.keysym.mod;
                out_buf4[3] = 0;
                return 1;
            case SDL_MOUSEBUTTONDOWN:
                out_buf4[0] = PIGART_EVENT_MOUSE_DOWN;
                out_buf4[1] = ev.button.x;
                out_buf4[2] = ev.button.y;
                out_buf4[3] = ev.button.button;
                return 1;
            case SDL_MOUSEBUTTONUP:
                out_buf4[0] = PIGART_EVENT_MOUSE_UP;
                out_buf4[1] = ev.button.x;
                out_buf4[2] = ev.button.y;
                out_buf4[3] = ev.button.button;
                return 1;
            case SDL_MOUSEMOTION:
                out_buf4[0] = PIGART_EVENT_MOUSE_MOVE;
                out_buf4[1] = ev.motion.x;
                out_buf4[2] = ev.motion.y;
                out_buf4[3] = 0;
                return 1;
            default:
                continue; /* ignore other events */
        }
    }
    /* No event */
    out_buf4[0] = 0; out_buf4[1] = 0; out_buf4[2] = 0; out_buf4[3] = 0;
    return 0;
}

static void sdl_sleep_ms(int ms) {
    /* Pump events every ~16ms to keep window responsive */
    int remaining = ms;
    while (remaining > 0) {
        int chunk = (remaining > 16) ? 16 : remaining;
        SDL_Delay(chunk);
        remaining -= chunk;
        /* Pump OS messages so the WM sees a responsive window, but do NOT
         * consume events from the queue.  Any mouse clicks or close events
         * that arrive during sleep must survive to be picked up by the
         * next sdl_poll_event call — SDL_PollEvent would discard them. */
        SDL_PumpEvents();
    }
}

static int sdl_get_ticks(void) {
    return (int)(SDL_GetTicks() - g_open_tick);
}

/* -----------------------------------------------------------------------
 * Backend factory
 * --------------------------------------------------------------------- */
static pigart_backend_t s_sdl_backend = {
    .open_window  = sdl_open_window,
    .close_window = sdl_close_window,
    .clear        = sdl_clear,
    .draw_rect    = sdl_draw_rect,
    .draw_polygon = sdl_draw_polygon,
    .draw_oval    = sdl_draw_oval,
    .draw_text    = sdl_draw_text,
    .draw_line    = sdl_draw_line,
    .present      = sdl_present,
    .poll_event   = sdl_poll_event,
    .sleep_ms     = sdl_sleep_ms,
    .get_ticks    = sdl_get_ticks,
    .name         = "sdl",
};

pigart_backend_t *pigart_sdl_backend(void) {
    return &s_sdl_backend;
}

#else /* PIGART_SDL_ENABLED not defined — stub */

#include "../include/pigart.h"
#include <stdio.h>

pigart_backend_t *pigart_sdl_backend(void) {
    fprintf(stderr,
        "[PIGART] SDL2 backend not compiled in (SDL2/SDL2_ttf not found).\n"
        "         Install: sudo apt install libsdl2-dev libsdl2-ttf-dev\n"
        "         Then:    cd c_emulator && make clean && make\n");
    return NULL;
}

#endif /* PIGART_SDL_ENABLED */
