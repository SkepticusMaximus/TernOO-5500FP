/*
 * pigart.h — PIGART Rendering Backend Abstraction
 *
 * PIGART (Pixel-Instruction Graphics And Rendering Toolkit) provides a
 * syscall-based graphics interface for running 5500FP programs. This header
 * defines the backend abstraction used by the syscall dispatcher.
 *
 * Syscall numbering: 100-111 (reserved range; 0-99 = existing I/O syscalls;
 * 112-127 = reserved for future PIGART extensions).
 *
 * Usage:
 *   ./5500fp --display sdl   --run <file.t5asm>    # SDL2 window
 *   ./5500fp --display ascii --run <file.t5asm>    # ASCII frames to stdout
 *   ./5500fp --run <file.t5asm>                    # no display (default)
 *
 * Phase 7b-2, TernOO 5500FP project.
 * Date: 2026-06-19, Adelaide.
 */

#ifndef PIGART_H
#define PIGART_H

#include <stdint.h>
#include <stddef.h>

/* -----------------------------------------------------------------------
 * Syscall numbers
 * --------------------------------------------------------------------- */
#define PIGART_OPEN_WINDOW   100
#define PIGART_CLEAR         101
#define PIGART_DRAW_RECT     102
#define PIGART_DRAW_POLYGON  103
#define PIGART_DRAW_OVAL     104
#define PIGART_DRAW_TEXT     105
#define PIGART_DRAW_LINE     106
#define PIGART_PRESENT       107
#define PIGART_POLL_EVENT    108
#define PIGART_SLEEP_MS      109
#define PIGART_GET_TICKS     110
#define PIGART_CLOSE_WINDOW  111

/* Stage 9-1C — interactive modal dialogs (block until dismissed) */
#define PIGART_DIALOG_PROMPT  112
#define PIGART_DIALOG_DISPLAY 113
#define PIGART_DIALOG_CONFIRM 114
#define PIGART_DIALOG_CHOICE  115

/* -----------------------------------------------------------------------
 * Event types (D8)
 * --------------------------------------------------------------------- */
#define PIGART_EVENT_CLOSE      1
#define PIGART_EVENT_KEY_DOWN   2
#define PIGART_EVENT_KEY_UP     3
#define PIGART_EVENT_MOUSE_DOWN 4
#define PIGART_EVENT_MOUSE_UP   5
#define PIGART_EVENT_MOUSE_MOVE 6

/* -----------------------------------------------------------------------
 * Data types
 * --------------------------------------------------------------------- */

/* A point pair (for polygon vertices) */
typedef struct {
    int64_t x;
    int64_t y;
} pigart_point_t;

/* -----------------------------------------------------------------------
 * Backend interface
 *
 * Each backend (SDL, ASCII) fills in a static pigart_backend_t struct.
 * The dispatcher calls through function pointers.
 * --------------------------------------------------------------------- */
typedef struct pigart_backend {
    /* Lifecycle */
    int  (*open_window)(int w, int h, const char *title);
    void (*close_window)(void);

    /* Drawing (operate on the back buffer) */
    void (*clear)(uint32_t color);
    void (*draw_rect)(int x, int y, int w, int h, uint32_t color, int filled);
    void (*draw_polygon)(int n, const pigart_point_t *pts, uint32_t color, int filled);
    void (*draw_oval)(int x, int y, int w, int h, uint32_t color, int filled);
    void (*draw_text)(int x, int y, const char *text, int size, uint32_t color);
    void (*draw_line)(int x1, int y1, int x2, int y2, uint32_t color);

    /* Presentation */
    void (*present)(void);

    /* Events and timing */
    int  (*poll_event)(int64_t *out_buf4); /* fills 4 words; returns 1 if event, 0 if none */
    void (*sleep_ms)(int ms);              /* may pump events internally (SDL backend) */
    int  (*get_ticks)(void);              /* ms since open_window; 0 if not open */

    /* Interactive modal dialogs (Stage 9-1C). Each blocks until dismissed.
     * A backend with no interactive surface (ASCII) returns safe defaults. */
    int  (*dialog_prompt)(const char *message, char *out, int out_size);
                                           /* text input; returns length, -1 = cancel */
    void (*dialog_display)(const char *title, const char *message);
    int  (*dialog_confirm)(const char *message);        /* 1 = yes, 0 = no */
    int  (*dialog_choice)(const char *prompt,
                          const char *options, int n_options);
                                           /* options = n NUL-separated strings;
                                            * returns selected index, -1 = cancel */

    /* Metadata */
    const char *name;   /* "sdl" or "ascii" */
} pigart_backend_t;

/* -----------------------------------------------------------------------
 * Global state
 * --------------------------------------------------------------------- */

/* Currently-loaded backend (NULL = no display / PIGART_OPEN_WINDOW returns 0) */
extern pigart_backend_t *pigart_active_backend;

/* -----------------------------------------------------------------------
 * Backend factories (implemented in pigart_sdl.c and pigart_ascii.c)
 * --------------------------------------------------------------------- */
pigart_backend_t *pigart_sdl_backend(void);
pigart_backend_t *pigart_ascii_backend(void);

/* -----------------------------------------------------------------------
 * Backend selection
 *
 * Called from main.c when --display <name> is parsed.
 * Returns the selected backend, or NULL if name is unknown.
 * --------------------------------------------------------------------- */
pigart_backend_t *pigart_select_backend(const char *name);

/* -----------------------------------------------------------------------
 * Syscall dispatcher
 *
 * Called from cpu.c's SYSCALL handler for syscall numbers 100-111.
 *   syscall_num : the value in R1 at SYSCALL time
 *   regs        : cpu->reg[0..80] (R1 return value written back here)
 *   mem         : cpu->mem
 *   mem_size    : cpu->mem_size
 *
 * Returns 0 on success, -1 on unknown syscall.
 * --------------------------------------------------------------------- */
int pigart_handle_syscall(int syscall_num,
                          int64_t *regs,
                          int64_t *mem,
                          uint32_t mem_size);

/* -----------------------------------------------------------------------
 * Test helper — ASCII backend grid inspection
 * Returns the character at grid position (x,y), or '\0' if out-of-bounds.
 * Only valid after pigart_ascii_backend() has been loaded and used.
 * --------------------------------------------------------------------- */
char pigart_ascii_cell(int x, int y);

#endif /* PIGART_H */
