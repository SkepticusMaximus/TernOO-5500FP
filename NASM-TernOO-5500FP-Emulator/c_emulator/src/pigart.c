/*
 * pigart.c — PIGART syscall dispatcher and backend selection
 *
 * This file implements:
 *  - pigart_active_backend global
 *  - pigart_select_backend() — choose SDL or ASCII backend by name
 *  - pigart_handle_syscall() — dispatch PIGART syscalls 100-111
 *
 * Memory access convention: pointer-typed args (text_ptr, point_array_ptr,
 * event_buf_ptr) are word addresses in the engine's memory array. Strings
 * are null-terminated sequences of words (one char code per word, low 8 bits).
 *
 * Phase 7b-2, TernOO 5500FP project.
 * Date: 2026-06-19, Adelaide.
 */

#include "../include/pigart.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* -----------------------------------------------------------------------
 * Global active backend
 * --------------------------------------------------------------------- */
pigart_backend_t *pigart_active_backend = NULL;

/* Whether the window is currently open */
static int g_window_open = 0;

/* -----------------------------------------------------------------------
 * Backend selection
 * --------------------------------------------------------------------- */
pigart_backend_t *pigart_select_backend(const char *name) {
    if (strcmp(name, "ascii") == 0) {
        pigart_active_backend = pigart_ascii_backend();
        return pigart_active_backend;
    }
    if (strcmp(name, "sdl") == 0) {
        pigart_active_backend = pigart_sdl_backend();
        return pigart_active_backend;
    }
    return NULL;
}

/* -----------------------------------------------------------------------
 * Memory helpers
 * --------------------------------------------------------------------- */

/* Read a NUL-terminated string from engine memory.
 * Each word holds one character in its low 8 bits (0 = end).
 * Reads at most maxlen-1 chars; always NUL-terminates out. */
static void mem_read_string(const int64_t *mem, uint32_t mem_size,
                            int64_t addr, char *out, int maxlen) {
    int i;
    out[0] = '\0';
    if (addr < 0 || maxlen <= 0) return;
    for (i = 0; i < maxlen - 1; i++) {
        int64_t wordaddr = addr + i;
        if ((uint64_t)wordaddr >= mem_size) break;
        int64_t val = mem[wordaddr];
        char c = (char)(val & 0xFF);
        if (c == '\0') break;
        out[i] = c;
    }
    out[i] = '\0';
}

/* Read an array of int64 words from engine memory into a pigart_point_t array.
 * Points are stored as consecutive pairs: x0, y0, x1, y1, ... */
static int mem_read_points(const int64_t *mem, uint32_t mem_size,
                           int64_t addr, pigart_point_t *pts, int n) {
    for (int i = 0; i < n; i++) {
        int64_t xi = addr + i * 2;
        int64_t yi = addr + i * 2 + 1;
        if ((uint64_t)xi >= mem_size || (uint64_t)yi >= mem_size) return i;
        pts[i].x = mem[xi];
        pts[i].y = mem[yi];
    }
    return n;
}

/* Write 4 int64 words to engine memory (event buffer). */
static void mem_write_event(int64_t *mem, uint32_t mem_size,
                            int64_t addr, const int64_t *ev4) {
    for (int i = 0; i < 4; i++) {
        int64_t wa = addr + i;
        if ((uint64_t)wa >= mem_size) break;
        mem[wa] = ev4[i];
    }
}

/* Write a C string into engine memory as one char per word, NUL-terminated.
 * Writes at most maxwords-1 chars. Returns the number of chars written. */
static int mem_write_string(int64_t *mem, uint32_t mem_size,
                            int64_t addr, const char *s, int maxwords) {
    int i = 0;
    if (addr < 0 || maxwords <= 0) return 0;
    for (; s[i] && i < maxwords - 1; i++) {
        int64_t wa = addr + i;
        if ((uint64_t)wa >= mem_size) break;
        mem[wa] = (unsigned char)s[i];
    }
    int64_t term = addr + i;
    if ((uint64_t)term < mem_size) mem[term] = 0;
    return i;
}

/* -----------------------------------------------------------------------
 * Syscall dispatcher
 * --------------------------------------------------------------------- */
int pigart_handle_syscall(int syscall_num,
                          int64_t *regs,
                          int64_t *mem,
                          uint32_t mem_size)
{
    pigart_backend_t *b = pigart_active_backend;

    switch (syscall_num) {

        /* ---- 100: PIGART_OPEN_WINDOW ---- */
        case PIGART_OPEN_WINDOW: {
            if (!b) { regs[1] = 0; break; }
            if (g_window_open) { regs[1] = 1; break; }
            int w = (int)regs[2];
            int h = (int)regs[3];
            int64_t title_ptr = regs[4];
            char title[1025];
            mem_read_string(mem, mem_size, title_ptr, title, sizeof(title));
            int ok = b->open_window(w, h, title);
            if (ok) g_window_open = 1;
            regs[1] = ok ? 1 : 0;
            break;
        }

        /* ---- 101: PIGART_CLEAR ---- */
        case PIGART_CLEAR: {
            if (!b || !g_window_open) break;
            uint32_t color = (uint32_t)(regs[2] & 0xFFFFFF);
            b->clear(color);
            break;
        }

        /* ---- 102: PIGART_DRAW_RECT ---- */
        case PIGART_DRAW_RECT: {
            if (!b || !g_window_open) break;
            int x = (int)regs[2], y = (int)regs[3];
            int w = (int)regs[4], h = (int)regs[5];
            uint32_t color = (uint32_t)(regs[6] & 0xFFFFFF);
            int filled = (int)regs[7];
            b->draw_rect(x, y, w, h, color, filled);
            break;
        }

        /* ---- 103: PIGART_DRAW_POLYGON ---- */
        case PIGART_DRAW_POLYGON: {
            if (!b || !g_window_open) break;
            int n = (int)regs[2];
            int64_t pts_ptr = regs[3];
            uint32_t color = (uint32_t)(regs[4] & 0xFFFFFF);
            int filled = (int)regs[5];
            if (n <= 0 || n > 256) break;
            pigart_point_t pts[256];
            int got = mem_read_points(mem, mem_size, pts_ptr, pts, n);
            b->draw_polygon(got, pts, color, filled);
            break;
        }

        /* ---- 104: PIGART_DRAW_OVAL ---- */
        case PIGART_DRAW_OVAL: {
            if (!b || !g_window_open) break;
            int x = (int)regs[2], y = (int)regs[3];
            int w = (int)regs[4], h = (int)regs[5];
            uint32_t color = (uint32_t)(regs[6] & 0xFFFFFF);
            int filled = (int)regs[7];
            b->draw_oval(x, y, w, h, color, filled);
            break;
        }

        /* ---- 105: PIGART_DRAW_TEXT ---- */
        case PIGART_DRAW_TEXT: {
            if (!b || !g_window_open) break;
            int x = (int)regs[2], y = (int)regs[3];
            int64_t text_ptr = regs[4];
            int size = (int)regs[5];
            uint32_t color = (uint32_t)(regs[6] & 0xFFFFFF);
            char text[1025];
            mem_read_string(mem, mem_size, text_ptr, text, sizeof(text));
            b->draw_text(x, y, text, size, color);
            break;
        }

        /* ---- 116: PIGART_DRAW_STRING (length-prefixed heap string) ----
         * R2=x, R3=y, R4=handle, R5=size, R6=color. mem[handle]=length,
         * chars at handle+1. Reuses the backend text renderer. */
        case PIGART_DRAW_STRING: {
            if (!b || !g_window_open) break;
            int x = (int)regs[2], y = (int)regs[3];
            int64_t h = regs[4];
            int size = (int)regs[5];
            uint32_t color = (uint32_t)(regs[6] & 0xFFFFFF);
            char text[1025];
            int n = 0;
            if (h > 0 && (uint64_t)h < mem_size) {
                int64_t len = mem[h];
                if (len < 0) len = 0;
                for (; n < len && n < (int)sizeof(text) - 1; n++) {
                    int64_t ca = h + 1 + n;
                    if ((uint64_t)ca >= mem_size) break;
                    text[n] = (char)(mem[ca] & 0xFF);
                }
            }
            text[n] = '\0';
            b->draw_text(x, y, text, size, color);
            break;
        }

        /* ---- 117: PIGART_DIALOG_CHOICE_LIST ----
         * R2=list handle (of string handles), R3=prompt char-ptr.
         * Builds the NUL-separated options block from the list, shows the
         * choice dialog, returns the selected element's handle (0 = cancel). */
        case PIGART_DIALOG_CHOICE_LIST: {
            if (!b || !b->dialog_choice) { regs[1] = 0; break; }
            int64_t list = regs[2];
            char prompt[1025];
            mem_read_string(mem, mem_size, regs[3], prompt, sizeof(prompt));
            int64_t n = (list > 0 && (uint64_t)list < mem_size) ? mem[list] : 0;
            if (n > 8) n = 8;
            char opts[1025];
            opts[0] = '\0';
            int oi = 0;
            for (int64_t i = 0; i < n; i++) {
                int64_t e = mem[list + 1 + i];
                int64_t le = (e > 0 && (uint64_t)e < mem_size) ? mem[e] : 0;
                for (int64_t k = 0; k < le && oi < (int)sizeof(opts) - 2; k++)
                    opts[oi++] = (char)(mem[e + 1 + k] & 0xFF);
                opts[oi++] = '\0';
            }
            int idx = b->dialog_choice(prompt, opts, (int)n);
            regs[1] = (idx >= 0 && idx < n) ? mem[list + 1 + idx] : 0;
            break;
        }

        /* ---- 106: PIGART_DRAW_LINE ---- */
        case PIGART_DRAW_LINE: {
            if (!b || !g_window_open) break;
            int x1 = (int)regs[2], y1 = (int)regs[3];
            int x2 = (int)regs[4], y2 = (int)regs[5];
            uint32_t color = (uint32_t)(regs[6] & 0xFFFFFF);
            b->draw_line(x1, y1, x2, y2, color);
            break;
        }

        /* ---- 107: PIGART_PRESENT ---- */
        case PIGART_PRESENT: {
            if (!b || !g_window_open) break;
            b->present();
            break;
        }

        /* ---- 108: PIGART_POLL_EVENT ---- */
        case PIGART_POLL_EVENT: {
            if (!b || !g_window_open) { regs[1] = 0; break; }
            int64_t ev_buf_ptr = regs[2];
            int64_t ev4[4] = {0, 0, 0, 0};
            int got = b->poll_event(ev4);
            regs[1] = got;
            if (got)
                mem_write_event(mem, mem_size, ev_buf_ptr, ev4);
            break;
        }

        /* ---- 109: PIGART_SLEEP_MS ---- */
        case PIGART_SLEEP_MS: {
            if (!b) break;
            int ms = (int)regs[2];
            if (ms > 0) b->sleep_ms(ms);
            break;
        }

        /* ---- 110: PIGART_GET_TICKS ---- */
        case PIGART_GET_TICKS: {
            if (!b || !g_window_open) { regs[1] = 0; break; }
            regs[1] = (int64_t)b->get_ticks();
            break;
        }

        /* ---- 111: PIGART_CLOSE_WINDOW ---- */
        case PIGART_CLOSE_WINDOW: {
            if (!b || !g_window_open) break;
            b->close_window();
            g_window_open = 0;
            break;
        }

        /* ---- 112: PIGART_DIALOG_PROMPT ----
         * R2=message ptr, R3=out buffer ptr, R4=out buffer words.
         * Returns R1 = chars written (>=0), or -1 on cancel/unavailable. */
        case PIGART_DIALOG_PROMPT: {
            if (!b || !b->dialog_prompt) { regs[1] = -1; break; }
            char msg[1025], answer[1025];
            mem_read_string(mem, mem_size, regs[2], msg, sizeof(msg));
            int outwords = (int)regs[4];
            if (outwords <= 0 || outwords > (int)sizeof(answer))
                outwords = (int)sizeof(answer);
            int n = b->dialog_prompt(msg, answer, outwords);
            if (n < 0) { regs[1] = -1; break; }
            regs[1] = mem_write_string(mem, mem_size, regs[3], answer, outwords);
            break;
        }

        /* ---- 113: PIGART_DIALOG_DISPLAY ---- R2=title ptr, R3=message ptr. */
        case PIGART_DIALOG_DISPLAY: {
            if (!b || !b->dialog_display) break;
            char title[1025], msg[1025];
            mem_read_string(mem, mem_size, regs[2], title, sizeof(title));
            mem_read_string(mem, mem_size, regs[3], msg, sizeof(msg));
            b->dialog_display(title, msg);
            break;
        }

        /* ---- 114: PIGART_DIALOG_CONFIRM ---- R2=message ptr. R1 = 1/0. */
        case PIGART_DIALOG_CONFIRM: {
            if (!b || !b->dialog_confirm) { regs[1] = 0; break; }
            char msg[1025];
            mem_read_string(mem, mem_size, regs[2], msg, sizeof(msg));
            regs[1] = b->dialog_confirm(msg) ? 1 : 0;
            break;
        }

        /* ---- 115: PIGART_DIALOG_CHOICE ----
         * R2=prompt ptr, R3=options block ptr (n NUL-separated strings),
         * R4=option count. Returns R1 = selected index, -1 = cancel. */
        case PIGART_DIALOG_CHOICE: {
            if (!b || !b->dialog_choice) { regs[1] = -1; break; }
            char prompt[1025], opts[1025];
            mem_read_string(mem, mem_size, regs[2], prompt, sizeof(prompt));
            /* Read the options block: a run of chars where 0 separates entries.
             * Copy raw (including embedded NULs) up to buffer end. */
            int n = (int)regs[4];
            int i;
            for (i = 0; i < (int)sizeof(opts) - 1; i++) {
                int64_t wa = regs[3] + i;
                if ((uint64_t)wa >= mem_size) break;
                opts[i] = (char)(mem[wa] & 0xFF);
            }
            opts[i] = '\0';
            regs[1] = b->dialog_choice(prompt, opts, n);
            break;
        }

        default:
            fprintf(stderr, "[PIGART] Unknown PIGART syscall %d\n", syscall_num);
            return -1;
    }

    return 0;
}
