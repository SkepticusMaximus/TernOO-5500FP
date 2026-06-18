; ============================================================================
; ternoo.inc  —  Shared constants, macros, and ABI for the TernOO-5500FP
;               pure x86-64 NASM implementation.
;
; Binary-encoded ternary representation (BET):
;   Each trit is stored in 2 bits:
;     00  →  0
;     01  → +1
;     10  → −1
;     11  →  (invalid / unused)
;
;   A 24-trit word occupies 48 bits, stored in the low 48 bits of a 64-bit
;   integer (qword).  Trit 0 (LST) occupies bits [1:0], trit 23 (MST)
;   occupies bits [47:46].
;
; Register calling convention (System V AMD64 ABI):
;   Arguments:   rdi, rsi, rdx, rcx, r8, r9
;   Return:      rax  (single value)  /  rax:rdx  (pair)
;   Callee-save: rbx, rbp, r12–r15
;   Scratch:     rax, rcx, rdx, rsi, rdi, r8–r11
;
; ============================================================================

; ── Trit encoding constants ─────────────────────────────────────────────────
%define TRIT_NEG        2       ; binary encoding of −1
%define TRIT_ZERO       0       ; binary encoding of  0
%define TRIT_POS        1       ; binary encoding of +1
%define TRIT_MASK       3       ; 2-bit mask for one trit slot

; ── Word geometry ────────────────────────────────────────────────────────────
%define WORD_TRITS      24
%define WORD_BITS       48      ; 24 trits × 2 bits each
%define WORD_MASK       0x0000FFFFFFFFFFFF  ; low 48 bits

; Balanced ternary range for a 24-trit word: ±(3^24−1)/2 = ±141,214,768,240
%define WORD_MAX        141214768240
%define WORD_MIN        -141214768240

; ── TernOO word field positions (in trit indices) ────────────────────────────
%define PRIMARY_LST     22      ; T22 = LST of 2-trit primary field
%define PRIMARY_WIDTH   2
%define QUAL_LST        18      ; T18 = LST of 4-trit qualifier field
%define QUAL_WIDTH      4
%define PAYLOAD_LST     0       ; T0  = LST of 18-trit payload field
%define PAYLOAD_WIDTH   18

; ── Primary type values (as balanced ternary integers) ───────────────────────
; Encoded as from_trits([T22, T23]) — i.e. T22 is LSB, T23 is MSB of the 2-trit field
; Value = T22 + T23*3  (balanced ternary)
;   EXEC   (−1,−1) → (−1)*1 + (−1)*3 = −4
;   MAP    (−1, 0) → (−1)*1 + ( 0)*3 = −1  (T22=0, T23=−1 → 0 + (−1)*3 = −3 ... recalc below)
; We use the Python formula: from_trits([t22, t23]) where LSB first
;   from_trits([t22,t23]) = t22*3^0 + t23*3^1 = t22 + 3*t23
;   EXEC   t22=−1,t23=−1 → −1 + 3*(−1) = −4
;   MAP    t22= 0,t23=−1 → 0  + 3*(−1) = −3
;   DATA   t22=+1,t23=−1 → +1 + 3*(−1) = −2
;   NEURAL t22=−1,t23= 0 → −1 + 3*( 0) = −1
;   I/O    t22= 0,t23= 0 →  0 + 3*( 0) =  0
;   CRYPTO t22=+1,t23= 0 → +1 + 3*( 0) = +1
;   OPCODE t22=−1,t23=+1 → −1 + 3*(+1) = +2
;   OPEN_B t22= 0,t23=+1 →  0 + 3*(+1) = +3
;   POOL   t22=+1,t23=+1 → +1 + 3*(+1) = +4
; These are the integer values returned by get_field(word, 22, 2)
%define PRIMARY_EXEC    -4
%define PRIMARY_MAP     -3
%define PRIMARY_DATA    -2
%define PRIMARY_NEURAL  -1
%define PRIMARY_IO       0
%define PRIMARY_CRYPTO  +1
%define PRIMARY_OPCODE  +2
%define PRIMARY_OPEN_B  +3
%define PRIMARY_POOL    +4

; ── ISA opcodes ──────────────────────────────────────────────────────────────
%define OP_NOP      0
%define OP_HLT      1
%define OP_ADD      2
%define OP_SUB      3
%define OP_MUL      4
%define OP_DIV      5
%define OP_NEG      6
%define OP_MOV      7
%define OP_LDI      8
%define OP_LD       9
%define OP_ST       10
%define OP_JMP      11
%define OP_JEQ      12
%define OP_JNE      13
%define OP_JB       14
%define OP_JSR      15
%define OP_RTI      16
%define OP_PUSH     17
%define OP_POP      18
%define OP_MIN      19
%define OP_MAX      20
%define OP_TXOR     21
%define OP_EQUAL    22
%define OP_SUM      23
%define OP_TTT      24
%define OP_TTZ      25
%define OP_TTP      26
%define OP_ADDI     27
%define OP_SUBI     28
%define OP_OUT      29
%define OP_IN       30
%define OP_TOBJ     31
%define OP_TGET     32
%define OP_TPAYLOAD 33
%define OP_TCALL    34
%define OP_TNEW     35
%define OP_TBUILD   36
%define OP_TSEG     37
%define OP_RPOINT   38
%define OP_RLINE    39
%define OP_RNODE    40
%define OP_REDGE    -1
%define OP_RENDER   -2

; ── CPU register file layout ─────────────────────────────────────────────────
%define CPU_NUM_REGS    81
%define REG_ZERO        0
%define REG_ST_BASE     45      ; R45–R53: Double Null stack pointers
%define REG_DS_BASE     54      ; R54–R62: data segment bases DS0–DS8
%define REG_CS_BASE     63      ; R63–R71: code segment bases CS0–CS8
%define REG_RWR         78      ; Reserved Word Register
%define REG_SP          79      ; stack pointer
%define REG_LR          80      ; link register

; ── Memory layout ────────────────────────────────────────────────────────────
%define MEMORY_SIZE     531441  ; 3^12 words
%define HEAP_BASE       265720  ; MEMORY_SIZE / 2

; ── CPU struct offsets (in bytes, qwords = 8 bytes each) ─────────────────────
; struct CPU5500FP {
;   int64_t  regs[81];        ; +0    (81 × 8 = 648 bytes)
;   int64_t  pc;              ; +648
;   int64_t  cycle_count;     ; +656
;   int64_t  halted;          ; +664
;   int64_t  heap_ptr;        ; +672
;   int64_t  sp_init;         ; +680  (initial SP value)
;   int64_t  call_stack[256]; ; +688  (256 × 8 = 2048 bytes)
;   int64_t  call_stack_top;  ; +2736
;   int64_t  canvas_count;    ; +2744
;   ; memory follows as a separate allocation
; }
%define CPU_REGS        0
%define CPU_PC          648
%define CPU_CYCLES      656
%define CPU_HALTED      664
%define CPU_HEAP_PTR    672
%define CPU_SP_INIT     680
%define CPU_CALL_STACK  688
%define CPU_CALL_TOP    2736
%define CPU_CANVAS_CNT  2744
%define CPU_STRUCT_SIZE 2752

; ── Useful macros ─────────────────────────────────────────────────────────────

; Save/restore callee-saved registers around a function body
%macro PUSH_CALLEE 0
    push rbx
    push rbp
    push r12
    push r13
    push r14
    push r15
%endmacro

%macro POP_CALLEE 0
    pop r15
    pop r14
    pop r13
    pop r12
    pop rbp
    pop rbx
%endmacro

; Linux syscall wrappers
%define SYS_READ    0
%define SYS_WRITE   1
%define SYS_EXIT    60
%define STDOUT      1
%define STDIN       0

; Print a null-terminated string: PRINT_STR label
%macro PRINT_STR 1
    lea     rdi, [rel %1]
    call    print_cstr
%endmacro

; ── Trit bit-position helper (trit N starts at bit 2*N) ─────────────────────
; No macro needed — use: shl/shr by (2*N) at runtime, or compute 2*N at assemble time.
