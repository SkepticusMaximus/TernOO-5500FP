/*
 * pigart_ascii.c — PIGART ASCII backend
 */
#define _GNU_SOURCE
/*
 *
 * Renders graphics to a 2D character grid and dumps it to stdout at each
 * PRESENT call. Headless — no display required. Suitable for CI, SSH, and
 * testing.
 *
 * Grid size: 80x24 by default. Override with env var PIGART_ASCII_SIZE=WxH
 * (e.g. PIGART_ASCII_SIZE=100x30).
 *
 * Coordinate scaling: pixel coords from the program are scaled from the
 * SDL window size (set at OPEN_WINDOW time) to the ASCII grid dimensions.
 *   grid_x = pixel_x * grid_w / window_w
 *   grid_y = pixel_y * grid_h / window_h
 *
 * Phase 7b-2, TernOO 5500FP project.
 * Date: 2026-06-19, Adelaide.
 */

#include "../include/pigart.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>

/* Forward declarations for trig helpers */
static double cos_approx(double t);
static double sin_approx(double t);

/* -----------------------------------------------------------------------
 * Grid state
 * --------------------------------------------------------------------- */
#define ASCII_MAX_W 256
#define ASCII_MAX_H 80

static int   g_grid_w = 80;
static int   g_grid_h = 24;
static char  g_grid[ASCII_MAX_H][ASCII_MAX_W + 1];  /* +1 for NUL */
static int   g_win_w  = 800;
static int   g_win_h  = 600;
static int   g_frame  = 0;
static int   g_open   = 0;

/* Time tracking for get_ticks */
static struct timespec g_open_time;

/* -----------------------------------------------------------------------
 * Internal helpers
 * --------------------------------------------------------------------- */

/* Scale pixel X to grid X (clamp to grid bounds) */
static int scale_x(int px) {
    if (g_win_w <= 0) return 0;
    int gx = px * g_grid_w / g_win_w;
    if (gx < 0) gx = 0;
    if (gx >= g_grid_w) gx = g_grid_w - 1;
    return gx;
}

/* Scale pixel Y to grid Y */
static int scale_y(int py) {
    if (g_win_h <= 0) return 0;
    int gy = py * g_grid_h / g_win_h;
    if (gy < 0) gy = 0;
    if (gy >= g_grid_h) gy = g_grid_h - 1;
    return gy;
}

/* Scale pixel W to grid columns (minimum 1) */
static int scale_w(int pw) {
    if (g_win_w <= 0 || pw <= 0) return 1;
    int gw = pw * g_grid_w / g_win_w;
    return gw < 1 ? 1 : gw;
}

/* Scale pixel H to grid rows (minimum 1) */
static int scale_h(int ph) {
    if (g_win_h <= 0 || ph <= 0) return 1;
    int gh = ph * g_grid_h / g_win_h;
    return gh < 1 ? 1 : gh;
}

/* Plot a single character at grid (x,y) — bounds-checked */
static void plot(int x, int y, char c) {
    if (x >= 0 && x < g_grid_w && y >= 0 && y < g_grid_h)
        g_grid[y][x] = c;
}

/* Bresenham line drawing */
static void draw_line_grid(int x0, int y0, int x1, int y1, char c_h, char c_v, char c_d1, char c_d2) {
    int dx  = abs(x1 - x0), dy = abs(y1 - y0);
    int sx  = (x0 < x1) ? 1 : -1;
    int sy  = (y0 < y1) ? 1 : -1;
    int err = dx - dy;
    while (1) {
        char ch;
        if (dx == 0) ch = c_v;
        else if (dy == 0) ch = c_h;
        else if ((sx > 0 && sy > 0) || (sx < 0 && sy < 0)) ch = c_d2; /* \ */
        else ch = c_d1;  /* / */
        plot(x0, y0, ch);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 > -dy) { err -= dy; x0 += sx; }
        if (e2 <  dx) { err += dx; y0 += sy; }
    }
}

/* -----------------------------------------------------------------------
 * Backend operations
 * --------------------------------------------------------------------- */

static int ascii_open_window(int w, int h, const char *title) {
    const char *env = getenv("PIGART_ASCII_SIZE");
    if (env) {
        int gw = 0, gh = 0;
        if (sscanf(env, "%dx%d", &gw, &gh) == 2 &&
            gw > 0 && gw <= ASCII_MAX_W && gh > 0 && gh <= ASCII_MAX_H) {
            g_grid_w = gw;
            g_grid_h = gh;
        }
    }
    g_win_w = (w > 0) ? w : 800;
    g_win_h = (h > 0) ? h : 600;
    g_frame = 0;
    g_open  = 1;
    clock_gettime(CLOCK_MONOTONIC, &g_open_time);

    /* Fill grid with spaces */
    for (int y = 0; y < g_grid_h; y++) {
        memset(g_grid[y], ' ', g_grid_w);
        g_grid[y][g_grid_w] = '\0';
    }

    fprintf(stderr, "[PIGART ASCII] Window: %dx%d px → grid %dx%d chars  title=\"%s\"\n",
            g_win_w, g_win_h, g_grid_w, g_grid_h, title ? title : "");
    return 1;
}

static void ascii_close_window(void) {
    g_open = 0;
    fprintf(stderr, "[PIGART ASCII] Window closed after %d frames.\n", g_frame);
}

static void ascii_clear(uint32_t color) {
    (void)color;  /* ASCII backend ignores color */
    for (int y = 0; y < g_grid_h; y++) {
        memset(g_grid[y], ' ', g_grid_w);
        g_grid[y][g_grid_w] = '\0';
    }
}

static void ascii_draw_rect(int x, int y, int w, int h,
                             uint32_t color, int filled) {
    (void)color;
    int gx = scale_x(x), gy = scale_y(y);
    int gw = scale_w(w), gh = scale_h(h);
    if (filled) {
        for (int row = gy; row < gy + gh && row < g_grid_h; row++)
            for (int col = gx; col < gx + gw && col < g_grid_w; col++)
                plot(col, row, '#');
    } else {
        /* Top and bottom borders */
        for (int col = gx; col < gx + gw; col++) {
            plot(col, gy,          '-');
            plot(col, gy + gh - 1, '-');
        }
        /* Left and right borders */
        for (int row = gy; row < gy + gh; row++) {
            plot(gx,          row, '|');
            plot(gx + gw - 1, row, '|');
        }
        /* Corners */
        plot(gx,          gy,          '+');
        plot(gx + gw - 1, gy,          '+');
        plot(gx,          gy + gh - 1, '+');
        plot(gx + gw - 1, gy + gh - 1, '+');
    }
}

static void ascii_draw_line(int x1, int y1, int x2, int y2, uint32_t color) {
    (void)color;
    int gx1 = scale_x(x1), gy1 = scale_y(y1);
    int gx2 = scale_x(x2), gy2 = scale_y(y2);
    draw_line_grid(gx1, gy1, gx2, gy2, '-', '|', '/', '\\');
}

static void ascii_draw_polygon(int n, const pigart_point_t *pts,
                                uint32_t color, int filled) {
    (void)filled;  /* ASCII backend draws outline only */
    if (n < 2) return;
    for (int i = 0; i < n; i++) {
        int j = (i + 1) % n;
        int gx1 = scale_x((int)pts[i].x), gy1 = scale_y((int)pts[i].y);
        int gx2 = scale_x((int)pts[j].x), gy2 = scale_y((int)pts[j].y);
        draw_line_grid(gx1, gy1, gx2, gy2, '-', '|', '/', '\\');
    }
    (void)color;
}

static void ascii_draw_oval(int x, int y, int w, int h,
                             uint32_t color, int filled) {
    (void)color; (void)filled;
    /* Coarse ellipse: plot 'o' at perimeter approximation points */
    int gx = scale_x(x), gy = scale_y(y);
    int gw = scale_w(w), gh = scale_h(h);
    /* Center and radii in grid space */
    double cx = gx + gw / 2.0;
    double cy = gy + gh / 2.0;
    double rx = gw / 2.0;
    double ry = gh / 2.0;
    /* Sample 32 points around the ellipse perimeter */
    for (int i = 0; i < 32; i++) {
        double t = (2.0 * 3.14159265358979323846 * i) / 32.0;
        double ex = cx + rx * cos_approx(t);
        double ey = cy + ry * sin_approx(t);
        plot((int)(ex + 0.5), (int)(ey + 0.5), 'o');
    }
}

/* Simple cos/sin approximations without math.h (avoids -lm dep) */
static double cos_approx(double t) {
    /* Taylor series: cos(t) ≈ 1 - t²/2 + t⁴/24, good for |t| < π */
    /* For full range, reduce modulo 2π */
    while (t >  3.14159265) t -= 2 * 3.14159265;
    while (t < -3.14159265) t += 2 * 3.14159265;
    double t2 = t * t;
    return 1.0 - t2/2.0 + t2*t2/24.0 - t2*t2*t2/720.0;
}

static double sin_approx(double t) {
    return cos_approx(t - 1.5707963267948966);
}

static void ascii_draw_text(int x, int y, const char *text, int size, uint32_t color) {
    (void)size; (void)color;
    int gx = scale_x(x), gy = scale_y(y);
    if (!text) return;
    for (int i = 0; text[i] && gx + i < g_grid_w; i++) {
        if (gx + i >= 0 && gy >= 0 && gy < g_grid_h)
            g_grid[gy][gx + i] = text[i];
    }
}

static void ascii_present(void) {
    /* Print frame separator */
    printf("---- frame %d (sdl pixel space %dx%d → ascii %dx%d) ----\n",
           g_frame, g_win_w, g_win_h, g_grid_w, g_grid_h);
    /* Print grid rows */
    for (int row = 0; row < g_grid_h; row++) {
        printf("%s\n", g_grid[row]);
    }
    fflush(stdout);
    g_frame++;
}

static int ascii_poll_event(int64_t *out_buf4) {
    /* ASCII mode: no input in this phase */
    out_buf4[0] = 0; out_buf4[1] = 0; out_buf4[2] = 0; out_buf4[3] = 0;
    return 0;
}

static void ascii_sleep_ms(int ms) {
    if (ms > 0) usleep((useconds_t)ms * 1000);
}

static int ascii_get_ticks(void) {
    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    long sec  = now.tv_sec  - g_open_time.tv_sec;
    long nsec = now.tv_nsec - g_open_time.tv_nsec;
    if (nsec < 0) { sec--; nsec += 1000000000L; }
    return (int)(sec * 1000 + nsec / 1000000);
}

/* -----------------------------------------------------------------------
 * Interactive dialogs — ASCII backend has no interactive surface.
 * Report to stderr and return safe, deterministic defaults so headless runs
 * (and the --test suite) are reproducible.
 * --------------------------------------------------------------------- */
static int ascii_dialog_prompt(const char *message, char *out, int out_size) {
    (void)message;
    if (out && out_size > 0) out[0] = '\0';
    fprintf(stderr, "[PIGART ascii] prompt (no input): \"%s\"\n",
            message ? message : "");
    return 0;                 /* empty answer, not a cancel */
}

static void ascii_dialog_display(const char *title, const char *message) {
    fprintf(stderr, "[PIGART ascii] display: %s — %s\n",
            title ? title : "", message ? message : "");
}

static int ascii_dialog_confirm(const char *message) {
    fprintf(stderr, "[PIGART ascii] confirm (default no): \"%s\"\n",
            message ? message : "");
    return 0;
}

static int ascii_dialog_choice(const char *prompt, const char *options,
                               int n_options) {
    (void)options;
    fprintf(stderr, "[PIGART ascii] choice (default 0 of %d): \"%s\"\n",
            n_options, prompt ? prompt : "");
    return n_options > 0 ? 0 : -1;
}

/* -----------------------------------------------------------------------
 * Test helper
 * --------------------------------------------------------------------- */
char pigart_ascii_cell(int x, int y) {
    if (x < 0 || x >= g_grid_w || y < 0 || y >= g_grid_h) return '\0';
    return g_grid[y][x];
}

/* -----------------------------------------------------------------------
 * Backend factory
 * --------------------------------------------------------------------- */
static pigart_backend_t s_ascii_backend = {
    .open_window  = ascii_open_window,
    .close_window = ascii_close_window,
    .clear        = ascii_clear,
    .draw_rect    = ascii_draw_rect,
    .draw_polygon = ascii_draw_polygon,
    .draw_oval    = ascii_draw_oval,
    .draw_text    = ascii_draw_text,
    .draw_line    = ascii_draw_line,
    .present      = ascii_present,
    .poll_event   = ascii_poll_event,
    .sleep_ms     = ascii_sleep_ms,
    .get_ticks    = ascii_get_ticks,
    .dialog_prompt  = ascii_dialog_prompt,
    .dialog_display = ascii_dialog_display,
    .dialog_confirm = ascii_dialog_confirm,
    .dialog_choice  = ascii_dialog_choice,
    .name         = "ascii",
};

pigart_backend_t *pigart_ascii_backend(void) {
    return &s_ascii_backend;
}
