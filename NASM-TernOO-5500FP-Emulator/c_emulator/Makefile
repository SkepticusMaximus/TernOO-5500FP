# Makefile for 5500FP Balanced Ternary RISC Emulator
# Targets x86/x86-64 with GCC inline assembly support

CC      = gcc
CFLAGS  = -O2 -Wall -Wextra -std=c11 -I./include
# Enable x86 inline assembly (disable on non-x86 with -DNO_X86_ASM)
CFLAGS += -march=native
LDFLAGS = 

SRC     = src/cpu.c src/assembler.c src/main.c
OBJ     = $(SRC:.c=.o)
TARGET  = 5500fp

.PHONY: all clean test demo run-bubble run-gcd

all: $(TARGET)

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

interactive: $(TARGET)
	./$(TARGET) --interactive

clean:
	rm -f $(OBJ) $(TARGET)
