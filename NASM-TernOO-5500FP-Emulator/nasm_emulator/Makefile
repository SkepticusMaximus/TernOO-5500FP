# ============================================================================
# Makefile  —  TernOO-5500FP pure x86-64 NASM emulator
# ============================================================================

NASM    = nasm
LD      = ld
NASMFLAGS = -f elf64 -g -F dwarf -I./include/
LDFLAGS   =

TARGET  = ternoo5500fp
SRCDIR  = src
OBJDIR  = obj

SRCS    = trit.asm cpu.asm word.asm main.asm
OBJS    = $(SRCS:%.asm=$(OBJDIR)/%.o)

.PHONY: all clean test bench demo

all: $(OBJDIR) $(TARGET)

$(OBJDIR):
	mkdir -p $(OBJDIR)

$(OBJDIR)/%.o: $(SRCDIR)/%.asm
	$(NASM) $(NASMFLAGS) -o $@ $<

$(TARGET): $(OBJS)
	$(LD) $(LDFLAGS) -o $@ $^

test: all
	./$(TARGET) --test

bench: all
	./$(TARGET) --bench

demo: all
	./$(TARGET) --demo

clean:
	rm -rf $(OBJDIR) $(TARGET)
