# Makefile for 5500FP Balanced Ternary RISC Emulator
# Targets x86/x86-64 with GCC inline assembly support
#
# Phase 7b-2: PIGART rendering (SDL2 + ASCII backends)
#
# Install SDL2 dependencies (one-time):
#   sudo apt install libsdl2-dev libsdl2-ttf-dev

CC      = gcc
CFLAGS  = -O2 -Wall -Wextra -std=c11 -I./include
# Enable x86 inline assembly (disable on non-x86 with -DNO_X86_ASM)
CFLAGS += -march=native
LDFLAGS =

# ---- SDL2 detection via pkg-config ----
SDL2_CFLAGS  := $(shell pkg-config --cflags sdl2 SDL2_ttf 2>/dev/null)
SDL2_LIBS    := $(shell pkg-config --libs   sdl2 SDL2_ttf 2>/dev/null)

ifneq ($(SDL2_CFLAGS),)
    # SDL2 + SDL_ttf found: build SDL backend with math lib
    CFLAGS  += $(SDL2_CFLAGS) -DPIGART_SDL_ENABLED
    LDFLAGS += $(SDL2_LIBS) -lm
    SDL_STATUS = enabled
else
    SDL_STATUS = disabled (install: sudo apt install libsdl2-dev libsdl2-ttf-dev)
endif

# ---- Source files ----
CORE_SRC  = src/cpu.c src/assembler.c src/main.c
PIGART_SRC = src/pigart.c src/pigart_ascii.c src/pigart_sdl.c
SRC        = $(CORE_SRC) $(PIGART_SRC)
OBJ        = $(SRC:.c=.o)
TARGET     = 5500fp

.PHONY: all clean test demo run-bubble run-gcd run-morph-ascii info

all: info $(TARGET)

info:
	@echo "SDL2 backend: $(SDL_STATUS)"

$(TARGET): $(OBJ)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

src/%.o: src/%.c
	$(CC) $(CFLAGS) -c -o $@ $<

test: $(TARGET)
	./$(TARGET) --test

demo: $(TARGET)
	./$(TARGET) --demo

run-bubble: $(TARGET)
	./$(TARGET) --run examples/bubble_sort.t5asm

run-gcd: $(TARGET)
	./$(TARGET) --run examples/gcd.t5asm

run-morph-ascii: $(TARGET)
	./$(TARGET) --display ascii --run examples/hello_ternoo_morph.t5asm

interactive: $(TARGET)
	./$(TARGET) --interactive

clean:
	rm -f $(OBJ) $(TARGET)
