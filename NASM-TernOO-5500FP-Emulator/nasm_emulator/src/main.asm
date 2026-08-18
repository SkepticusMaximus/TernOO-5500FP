; ============================================================================
; main.asm  —  TernOO-5500FP NASM entry point
;
; Provides:
;   - A minimal macro-assembler (text → instruction words)
;   - Self-test suite
;   - Benchmark harness (RDTSC-based)
;   - Example programs: Fibonacci, Factorial, TernOO word dispatch demo,
;     PIGART canvas demo
;
; Build:
;   nasm -f elf64 src/main.asm -o obj/main.o
;   ld -o ternoo5500fp obj/main.o obj/trit.o obj/cpu.o obj/word.o
;
; Usage:
;   ./ternoo5500fp [--test] [--bench] [--demo]
; ============================================================================

%include "include/ternoo.inc"

section .data

; ── Program strings ───────────────────────────────────────────────────────────
banner:
    db  0x0A
    db  "  ████████╗███████╗██████╗ ███╗   ██╗ ██████╗  ██████╗ ", 0x0A
    db  "     ██╔══╝██╔════╝██╔══██╗████╗  ██║██╔═══██╗██╔═══██╗", 0x0A
    db  "     ██║   █████╗  ██████╔╝██╔██╗ ██║██║   ██║██║   ██║", 0x0A
    db  "     ██║   ██╔══╝  ██╔══██╗██║╚██╗██║██║   ██║██║   ██║", 0x0A
    db  "     ██║   ███████╗██║  ██║██║ ╚████║╚██████╔╝╚██████╔╝", 0x0A
    db  "     ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ", 0x0A
    db  0x0A
    db  "  TernOO-5500FP  |  Pure x86-64 NASM  |  Binary-Encoded Ternary", 0x0A
    db  "  24-trit balanced ternary RISC + TernOO word architecture", 0x0A
    db  0x0A, 0

str_usage:
    db  "Usage: ./ternoo5500fp [--test] [--bench] [--demo]", 0x0A, 0

str_test_hdr:
    db  0x0A, "=== Self-Test Suite ===", 0x0A, 0
str_test_pass:
    db  "  [PASS] ", 0
str_test_fail:
    db  "  [FAIL] ", 0
str_test_summary:
    db  0x0A, "Tests: ", 0
str_test_slash:
    db  " / ", 0
str_test_done:
    db  " passed", 0x0A, 0

str_bench_hdr:
    db  0x0A, "=== Benchmark ===", 0x0A, 0
str_bench_fib:
    db  "  Fibonacci(30)     : ", 0
str_bench_fact:
    db  "  Factorial(12)     : ", 0
str_bench_arith:
    db  "  Arith loop (3000) : ", 0
str_bench_word:
    db  "  TernOO word build : ", 0
str_bench_array:
    db  "  Array sum (1000)  : ", 0
str_bench_cycles:
    db  " cycles (RDTSC)", 0x0A, 0
vname_bench_fib:   db  "bench verify fib(30)", 0
vname_bench_fact:  db  "bench verify fact(12)", 0
vname_bench_array: db  "bench verify array_sum", 0
vname_bench_arith: db  "bench verify arith_loop", 0

str_demo_hdr:
    db  0x0A, "=== Demo Programs ===", 0x0A, 0
str_demo_fib:
    db  0x0A, "-- Fibonacci(15) --", 0x0A, 0
str_demo_fact:
    db  0x0A, "-- Factorial(8) --", 0x0A, 0
str_demo_ternoo:
    db  0x0A, "-- TernOO Word Dispatch Demo --", 0x0A, 0
str_demo_canvas:
    db  0x0A, "-- PIGART Canvas Demo --", 0x0A, 0

str_result_eq:
    db  " = ", 0
str_newline:
    db  0x0A, 0

str_word_built:
    db  "  Built word: ", 0
str_dispatch_exec:
    db  "  Dispatched EXEC word -> handler at addr ", 0
str_dispatch_data:
    db  "  Dispatched DATA word -> default handler", 0x0A, 0
str_ternoo_ok:
    db  "  TernOO word dispatch: OK", 0x0A, 0

; ── Argument strings ──────────────────────────────────────────────────────────
arg_test:   db  "--test", 0
arg_bench:  db  "--bench", 0
arg_demo:   db  "--demo", 0

; ── Test names ────────────────────────────────────────────────────────────────
tname_to_bet:       db  "to_bet(+1, 1) = 01b", 0
tname_from_bet:     db  "from_bet(01b, 1) = +1", 0
tname_clamp_hi:     db  "clamp_word(WORD_MAX+1) = WORD_MAX", 0
tname_clamp_lo:     db  "clamp_word(WORD_MIN-1) = WORD_MIN", 0
tname_get_field:    db  "get_field_val(word, 0, 4)", 0
tname_set_field:    db  "set_field_val round-trip", 0
tname_trit_min:     db  "trit_min_word", 0
tname_trit_max:     db  "trit_max_word", 0
tname_trit_txor:    db  "trit_txor_word", 0
tname_trit_equal:   db  "trit_equal_word same", 0
tname_trit_sum:     db  "trit_sum_word saturate", 0
tname_word_make:    db  "word_make / get_primary", 0
tname_word_scalar:  db  "word_build_int payload", 0
tname_word_exec:    db  "word_build_exec primary", 0
tname_word_map:     db  "word_build_map primary", 0
tname_cpu_init:     db  "cpu_init / R0=0", 0
tname_cpu_ldi:      db  "cpu LDI R41, 42", 0
tname_cpu_add:      db  "cpu ADD R41, R41, R41", 0
tname_cpu_sub:      db  "cpu SUB R41, R42, R41", 0
tname_cpu_mul:      db  "cpu MUL R41, R41, R42", 0
tname_cpu_neg:      db  "cpu NEG R41, R42", 0
tname_cpu_mov:      db  "cpu MOV R41, R42", 0
tname_cpu_jmp:      db  "cpu JMP addr", 0
tname_cpu_jeq_t:    db  "cpu JEQ taken", 0
tname_cpu_jeq_nt:   db  "cpu JEQ not taken", 0
tname_cpu_push_pop: db  "cpu PUSH/POP", 0
tname_cpu_jsr_rti:  db  "cpu JSR/RTI", 0
tname_cpu_min:      db  "cpu MIN trit-wise", 0
tname_cpu_tobj:     db  "cpu TOBJ/TGET round-trip", 0
tname_cpu_fib:      db  "cpu Fibonacci(10)=55", 0
tname_cpu_fact:     db  "cpu Factorial(5)=120", 0
tname_cpu_addi:     db  "cpu ADDI R41, R41, 10", 0
tname_cpu_subi:     db  "cpu SUBI R41, R41, 3", 0

section .bss

; CPU struct and memory
cpu_struct:     resb CPU_STRUCT_SIZE
cpu_memory:     resq MEMORY_SIZE

; Scratch program buffer (max 256 words)
prog_buf:       resq 256

; Test counters
test_pass:      resq 1
test_fail:      resq 1

; Benchmark scratch
bench_start:    resq 1
bench_end:      resq 1

section .text

extern clamp_word
extern to_bet
extern from_bet
extern get_field_val
extern set_field_val
extern get_trit_val
extern set_trit_val
extern trit_min_word
extern trit_max_word
extern trit_txor_word
extern trit_equal_word
extern trit_sum_word
extern word_to_str
extern cpu_init
extern cpu_reset
extern cpu_load_program
extern cpu_run
extern cpu_read_reg
extern cpu_write_reg
extern cpu_mem_read
extern cpu_mem_write
extern cpu_fetch
extern cpu_execute
extern cpu_dump_regs
extern word_get_primary
extern word_set_primary
extern word_get_qualifier
extern word_set_qualifier
extern word_get_payload
extern word_set_payload
extern word_make
extern word_build_scalar
extern word_build_int
extern word_build_uint
extern word_build_pointer
extern word_build_null
extern word_build_map
extern word_build_exec
extern word_build_neural_unit
extern word_build_neural_conn
extern word_build_io
extern word_build_opcode
extern word_describe
extern print_cstr
extern print_int64
extern print_newline
extern read_int64

global _start

; ── _start ────────────────────────────────────────────────────────────────────
_start:
    ; Linux x86-64 ABI: on entry, [rsp]=argc, [rsp+8]=argv[0], [rsp+16]=argv[1]...
    mov     r13, [rsp]          ; r13 = argc
    lea     r14, [rsp + 8]      ; r14 = argv array

    ; print banner
    lea     rdi, [rel banner]
    call    print_cstr

    ; parse arguments: check argv[1..argc-1]
    mov     r12, 0              ; flags: bit0=test, bit1=bench, bit2=demo
    mov     rcx, 1              ; argv index (skip argv[0])
.arg_loop:
    cmp     rcx, r13
    jge     .arg_done
    mov     rdi, [r14 + rcx*8]
    test    rdi, rdi
    jz      .arg_next
    lea     rsi, [rel arg_test]
    call    strcmp
    test    rax, rax
    jnz     .check_bench
    or      r12, 1
    jmp     .arg_next
.check_bench:
    mov     rdi, [r14 + rcx*8]
    lea     rsi, [rel arg_bench]
    call    strcmp
    test    rax, rax
    jnz     .check_demo
    or      r12, 2
    jmp     .arg_next
.check_demo:
    mov     rdi, [r14 + rcx*8]
    lea     rsi, [rel arg_demo]
    call    strcmp
    test    rax, rax
    jnz     .arg_next
    or      r12, 4
.arg_next:
    inc     rcx
    jmp     .arg_loop
.arg_done:

    ; if no flags, run all
    test    r12, r12
    jnz     .dispatch
    or      r12, 7          ; all flags

.dispatch:
    ; initialise CPU
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init

    test    r12, 1
    jz      .skip_test
    call    run_tests
.skip_test:

    test    r12, 2
    jz      .skip_bench
    call    run_benchmarks
.skip_bench:

    test    r12, 4
    jz      .skip_demo
    call    run_demos
.skip_demo:

    ; exit(0)
    mov     rax, SYS_EXIT
    xor     rdi, rdi
    syscall

; ── run_tests ─────────────────────────────────────────────────────────────────
run_tests:
    PUSH_CALLEE
    lea     rdi, [rel str_test_hdr]
    call    print_cstr
    mov     qword [rel test_pass], 0
    mov     qword [rel test_fail], 0

    ; ── T1: to_bet(+1, 1) should return 1 (binary 01) ───────────────────────
    mov     rdi, 1
    mov     rsi, 1
    call    to_bet
    lea     rsi, [rel tname_to_bet]
    mov     rdx, 1          ; expected
    call    check_eq

    ; ── T2: from_bet(1, 1) should return +1 ──────────────────────────────────
    mov     rdi, 1
    mov     rsi, 1
    call    from_bet
    lea     rsi, [rel tname_from_bet]
    mov     rdx, 1
    call    check_eq

    ; ── T3: clamp_word(WORD_MAX+1) = WORD_MAX ────────────────────────────────
    mov     rdi, WORD_MAX
    inc     rdi
    call    clamp_word
    lea     rsi, [rel tname_clamp_hi]
    mov     rdx, WORD_MAX
    call    check_eq

    ; ── T4: clamp_word(WORD_MIN-1) = WORD_MIN ────────────────────────────────
    mov     rdi, WORD_MIN
    dec     rdi
    call    clamp_word
    lea     rsi, [rel tname_clamp_lo]
    mov     rdx, WORD_MIN
    call    check_eq

    ; ── T5: get_field_val of a known word ─────────────────────────────────────
    ; Build word where field[0] (T0-T3) = 5
    ; 5 in balanced ternary 4 trits: 5 = 1*3 + 2 → but 2 is not valid...
    ; 5 = 1*3 + 2 → carry: 5 = 2*3 - 1 → trits: [-1, 2] → [-1, 2] not valid
    ; 5 = 1*3^1 + (-1)*3^0 = 3-1=2... Let's use 4: 4 = 1*3+1 → trits [+1,+1,0,0] = 4
    ; Actually: 4 = +1 + 1*3 = 1 + 3 = 4. Trits: T0=+1, T1=+1, T2=0, T3=0
    ; from_trits([+1,+1,0,0]) = 1 + 3 = 4. OK.
    ; Build via to_bet(4, 4) and then from_bet
    mov     rdi, 4
    mov     rsi, 4
    call    to_bet          ; rax = BET of 4 in 4 trits
    mov     r15, rax        ; r15 = BET bits for field 0
    ; now build a word where field 0 = 4
    ; field 0 is at bit positions 0..7 (4 trits × 2 bits)
    ; just use r15 directly as the word BET (other fields = 0)
    mov     rdi, r15
    mov     rsi, 4          ; width = 4 (decode as 4-trit word)
    call    from_bet
    mov     r14, rax        ; r14 = word value with field0 = 4
    ; now get_field_val(r14, 0, 4) should return 4
    mov     rdi, r14
    mov     rsi, 0
    mov     rdx, 4
    call    get_field_val
    lea     rsi, [rel tname_get_field]
    mov     rdx, 4
    call    check_eq

    ; ── T6: set_field_val round-trip ─────────────────────────────────────────
    ; set_field_val(0, 4, 4, 7) → get_field_val(result, 4, 4) = 7
    mov     rdi, 0
    mov     rsi, 4          ; lsb
    mov     rdx, 4          ; width
    mov     rcx, 7          ; value
    call    set_field_val
    mov     r14, rax
    mov     rdi, r14
    mov     rsi, 4
    mov     rdx, 4
    call    get_field_val
    lea     rsi, [rel tname_set_field]
    mov     rdx, 7
    call    check_eq

    ; ── T7: trit_min_word ────────────────────────────────────────────────────
    ; trit_min(+1, -1) per trit = -1 for each trit
    ; word_a = all +1 trits = WORD_MAX = 141214768240
    ; word_b = all -1 trits = WORD_MIN = -141214768240
    ; result = all -1 trits = WORD_MIN
    mov     rdi, WORD_MAX
    mov     rsi, WORD_MIN
    call    trit_min_word
    lea     rsi, [rel tname_trit_min]
    mov     rdx, WORD_MIN
    call    check_eq

    ; ── T8: trit_max_word ────────────────────────────────────────────────────
    mov     rdi, WORD_MAX
    mov     rsi, WORD_MIN
    call    trit_max_word
    lea     rsi, [rel tname_trit_max]
    mov     rdx, WORD_MAX
    call    check_eq

    ; ── T9: trit_txor_word ───────────────────────────────────────────────────
    ; txor(0, 0) = 0
    mov     rdi, 0
    mov     rsi, 0
    call    trit_txor_word
    lea     rsi, [rel tname_trit_txor]
    mov     rdx, 0
    call    check_eq

    ; ── T10: trit_equal_word same ────────────────────────────────────────────
    ; equal(5, 5) = all +1 trits = WORD_MAX
    mov     rdi, 5
    mov     rsi, 5
    call    trit_equal_word
    lea     rsi, [rel tname_trit_equal]
    mov     rdx, WORD_MAX
    call    check_eq

    ; ── T11: trit_sum_word saturate ──────────────────────────────────────────
    ; sum(WORD_MAX, WORD_MAX) = WORD_MAX (saturates at +1)
    mov     rdi, WORD_MAX
    mov     rsi, WORD_MAX
    call    trit_sum_word
    lea     rsi, [rel tname_trit_sum]
    mov     rdx, WORD_MAX
    call    check_eq

    ; ── T12: word_make / word_get_primary ────────────────────────────────────
    mov     rdi, PRIMARY_DATA
    mov     rsi, 0
    mov     rdx, 42
    call    word_make
    mov     r14, rax
    mov     rdi, r14
    call    word_get_primary
    lea     rsi, [rel tname_word_make]
    mov     rdx, PRIMARY_DATA
    call    check_eq

    ; ── T13: word_build_int payload ──────────────────────────────────────────
    mov     rdi, 99
    call    word_build_int
    mov     r14, rax
    mov     rdi, r14
    call    word_get_payload
    lea     rsi, [rel tname_word_scalar]
    mov     rdx, 99
    call    check_eq

    ; ── T14: word_build_exec primary ─────────────────────────────────────────
    mov     rdi, 0          ; privilege=user
    mov     rsi, 0          ; call_style=register
    mov     rdx, 0          ; return_type=MAP
    mov     rcx, 4          ; seg_idx=4
    mov     r8,  0          ; offset=0
    call    word_build_exec
    mov     r14, rax
    mov     rdi, r14
    call    word_get_primary
    lea     rsi, [rel tname_word_exec]
    mov     rdx, PRIMARY_EXEC
    call    check_eq

    ; ── T15: word_build_map primary ──────────────────────────────────────────
    mov     rdi, 0
    mov     rsi, 0
    mov     rdx, 0
    mov     rcx, 100
    mov     r8,  0
    call    word_build_map
    mov     r14, rax
    mov     rdi, r14
    call    word_get_primary
    lea     rsi, [rel tname_word_map]
    mov     rdx, PRIMARY_MAP
    call    check_eq

    ; ── CPU tests ─────────────────────────────────────────────────────────────
    ; T16: cpu_init / R0=0
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    lea     rdi, [rel cpu_struct]
    mov     rsi, 0
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_init]
    mov     rdx, 0
    call    check_eq

    ; T17: LDI R41, 42  (R41 = reg index 41)
    call    .run_single_ldi

    ; T18: ADD R41, R41, R41  (R41 = 84)
    call    .run_single_add

    ; T19: SUB
    call    .run_single_sub

    ; T20: MUL
    call    .run_single_mul

    ; T21: NEG
    call    .run_single_neg

    ; T22: MOV
    call    .run_single_mov

    ; T23: JMP
    call    .run_single_jmp

    ; T24: JEQ taken
    call    .run_jeq_taken

    ; T25: JEQ not taken
    call    .run_jeq_not_taken

    ; T26: PUSH/POP
    call    .run_push_pop

    ; T27: JSR/RTI
    call    .run_jsr_rti

    ; T28: MIN trit-wise
    call    .run_cpu_min

    ; T29: TOBJ/TGET
    call    .run_tobj_tget

    ; T30: ADDI
    call    .run_addi

    ; T31: SUBI
    call    .run_subi

    ; T32: Fibonacci(10)=55
    call    .run_fib10

    ; T33: Factorial(5)=120
    call    .run_fact5

    ; print summary
    lea     rdi, [rel str_test_summary]
    call    print_cstr
    mov     rdi, [rel test_pass]
    call    print_int64
    lea     rdi, [rel str_test_slash]
    call    print_cstr
    mov     rax, [rel test_pass]
    add     rax, [rel test_fail]
    mov     rdi, rax
    call    print_int64
    lea     rdi, [rel str_test_done]
    call    print_cstr

    POP_CALLEE
    ret

; ── Single-instruction CPU test helpers ──────────────────────────────────────

.run_single_ldi:
    ; LDI R41, 42
    ; Encode: op=OP_LDI=8, Rd=R41 (field0=41-40=1), imm=42 in trits 8..19
    ; Use the assembler helper
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    ; build instruction: LDI R41, 42
    mov     rdi, OP_LDI
    mov     rsi, 41         ; Rd
    mov     rdx, 42         ; imm
    call    encode_ldi
    mov     r15, rax        ; instruction word
    ; load single instruction + HLT
    lea     rdi, [rel prog_buf]
    mov     [rdi], r15
    ; HLT instruction
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    ; run
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 2
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    ; check R41
    lea     rdi, [rel cpu_struct]
    mov     rsi, 41
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_ldi]
    mov     rdx, 42
    call    check_eq
    ret

.run_single_add:
    ; LDI R41, 21; ADD R41, R41, R41 → R41=42
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 21
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_ADD
    mov     rsi, 41
    mov     rdx, 41
    mov     rcx, 41
    call    encode_rrr
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 3
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 41
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_add]
    mov     rdx, 42
    call    check_eq
    ret

.run_single_sub:
    ; LDI R41, 10; LDI R42, 3; SUB R41, R41, R42 → R41=7
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 10
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 3
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_SUB
    mov     rsi, 41
    mov     rdx, 41
    mov     rcx, 42
    call    encode_rrr
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 24], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 4
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 41
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_sub]
    mov     rdx, 7
    call    check_eq
    ret

.run_single_mul:
    ; LDI R41, 6; LDI R42, 7; MUL R41, R41, R42 → R41=42
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 6
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 7
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_MUL
    mov     rsi, 41
    mov     rdx, 41
    mov     rcx, 42
    call    encode_rrr
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 24], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 4
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 41
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_mul]
    mov     rdx, 42
    call    check_eq
    ret

.run_single_neg:
    ; LDI R42, 7; NEG R41, R42 → R41=-7
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 7
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_NEG
    mov     rsi, 41
    mov     rdx, 42
    mov     rcx, 0
    call    encode_rrr
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 3
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 41
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_neg]
    mov     rdx, -7
    call    check_eq
    ret

.run_single_mov:
    ; LDI R42, 99; MOV R41, R42 → R41=99
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 99
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_MOV
    mov     rsi, 41
    mov     rdx, 42
    mov     rcx, 0
    call    encode_rrr
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 3
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 41
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_mov]
    mov     rdx, 99
    call    check_eq
    ret

.run_single_jmp:
    ; JMP 2; LDI R41, 1 (skipped); LDI R41, 99; HLT → R41=99
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    ; JMP 2
    mov     rdi, OP_JMP
    mov     rsi, 2          ; target addr
    call    encode_jmp
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    ; LDI R41, 1 (should be skipped)
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 1
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    ; LDI R41, 99
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 99
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    ; HLT
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 24], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 4
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 41
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_jmp]
    mov     rdx, 99
    call    check_eq
    ret

.run_jeq_taken:
    ; LDI R41, 5; LDI R42, 5; JEQ R41, R42, +1; LDI R43, 1 (skip); LDI R43, 99; HLT
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 5
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 5
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    ; JEQ R41, R42, +1 (skip next instruction)
    mov     rdi, OP_JEQ
    mov     rsi, 41
    mov     rdx, 42
    mov     rcx, 1
    call    encode_branch
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    ; LDI R43, 1 (skipped)
    mov     rdi, OP_LDI
    mov     rsi, 43
    mov     rdx, 1
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 24], rax
    ; LDI R43, 99
    mov     rdi, OP_LDI
    mov     rsi, 43
    mov     rdx, 99
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 32], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 40], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 6
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 43
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_jeq_t]
    mov     rdx, 99
    call    check_eq
    ret

.run_jeq_not_taken:
    ; LDI R41, 5; LDI R42, 6; JEQ R41, R42, +1; LDI R43, 77; HLT
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 5
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 6
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_JEQ
    mov     rsi, 41
    mov     rdx, 42
    mov     rcx, 1
    call    encode_branch
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    mov     rdi, OP_LDI
    mov     rsi, 43
    mov     rdx, 77
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 24], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 32], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 5
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 43
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_jeq_nt]
    mov     rdx, 77
    call    check_eq
    ret

.run_push_pop:
    ; LDI R41, 55; PUSH R41; LDI R41, 0; POP R42 → R42=55
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 55
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_PUSH
    mov     rsi, 41
    call    encode_r1
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 0
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    mov     rdi, OP_POP
    mov     rsi, 42
    call    encode_r1
    lea     rdi, [rel prog_buf]
    mov     [rdi + 24], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 32], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 5
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 42
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_push_pop]
    mov     rdx, 55
    call    check_eq
    ret

.run_jsr_rti:
    ; JMP 3; LDI R41, 99; RTI; JSR 1; HLT → R41=99
    ; addr 0: JMP 3
    ; addr 1: LDI R41, 99
    ; addr 2: RTI
    ; addr 3: JSR 1
    ; addr 4: HLT
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_JMP
    mov     rsi, 3
    call    encode_jmp
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 99
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_RTI
    call    encode_hlt      ; RTI has no operands, same encoding as HLT but different op
    ; encode RTI properly
    mov     rdi, OP_RTI
    call    encode_noarg
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    mov     rdi, OP_JSR
    mov     rsi, 1          ; target addr 1
    call    encode_jmp      ; JSR uses same J format
    lea     rdi, [rel prog_buf]
    mov     [rdi + 24], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 32], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 5
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 41
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_jsr_rti]
    mov     rdx, 99
    call    check_eq
    ret

.run_cpu_min:
    ; MIN trit-wise: LDI R41, 3; LDI R42, -3; MIN R43, R41, R42
    ; 3 in BT: T0=0, T1=+1 (value=3)
    ; -3 in BT: T0=0, T1=-1 (value=-3)
    ; trit_min: T0=min(0,0)=0, T1=min(+1,-1)=-1 → value=-3
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 3
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, -3
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_MIN
    mov     rsi, 43
    mov     rdx, 41
    mov     rcx, 42
    call    encode_rrr
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 24], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 4
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 43
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_min]
    mov     rdx, -3
    call    check_eq
    ret

.run_tobj_tget:
    ; LDI R41, 100; LDI R42, 1; TOBJ R43, R41, R42; TGET R44, R43 → R44=1
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 100
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 1
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_TOBJ
    mov     rsi, 43
    mov     rdx, 41
    mov     rcx, 42
    call    encode_rrr
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    mov     rdi, OP_TGET
    mov     rsi, 44
    mov     rdx, 43
    mov     rcx, 0
    call    encode_rrr
    lea     rdi, [rel prog_buf]
    mov     [rdi + 24], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 32], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 5
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 44
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_tobj]
    mov     rdx, 1
    call    check_eq
    ret

.run_addi:
    ; LDI R41, 5; ADDI R41, R41, 10 → R41=15
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 5
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_ADDI
    mov     rsi, 41
    mov     rdx, 41
    mov     rcx, 10
    call    encode_rri
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 3
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 41
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_addi]
    mov     rdx, 15
    call    check_eq
    ret

.run_subi:
    ; LDI R41, 10; SUBI R41, R41, 3 → R41=7
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 10
    call    encode_ldi
    lea     rdi, [rel prog_buf]
    mov     [rdi], rax
    mov     rdi, OP_SUBI
    mov     rsi, 41
    mov     rdx, 41
    mov     rcx, 3
    call    encode_rri
    lea     rdi, [rel prog_buf]
    mov     [rdi + 8], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    lea     rdi, [rel prog_buf]
    mov     [rdi + 16], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 3
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 41
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_subi]
    mov     rdx, 7
    call    check_eq
    ret

.run_fib10:
    ; Fibonacci(10) = 55
    ; R41=a=0, R42=b=1, R43=counter=10, R44=tmp
    ; loop: tmp=a+b; a=b; b=tmp; counter--; if counter!=0 goto loop
    ; addr 0: LDI R41, 0
    ; addr 1: LDI R42, 1
    ; addr 2: LDI R43, 10
    ; addr 3: ADD R44, R41, R42   (tmp = a + b)
    ; addr 4: MOV R41, R42        (a = b)
    ; addr 5: MOV R42, R44        (b = tmp)
    ; addr 6: SUBI R43, R43, 1   (counter--)
    ; addr 7: LDI R45, 0          (zero for comparison)
    ; addr 8: JNE R43, R45, -6   (if counter != 0, jump back to addr 3)
    ; addr 9: HLT
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    lea     rbx, [rel prog_buf]
    ; 0: LDI R41, 0
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 0
    call    encode_ldi
    mov     [rbx], rax
    ; 1: LDI R42, 1
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 1
    call    encode_ldi
    mov     [rbx + 8], rax
    ; 2: LDI R43, 9  (9 iterations from [0,1] gives fib(10)=55 in R42)
    mov     rdi, OP_LDI
    mov     rsi, 43
    mov     rdx, 9
    call    encode_ldi
    mov     [rbx + 16], rax
    ; 3: ADD R44, R41, R42
    mov     rdi, OP_ADD
    mov     rsi, 44
    mov     rdx, 41
    mov     rcx, 42
    call    encode_rrr
    mov     [rbx + 24], rax
    ; 4: MOV R41, R42
    mov     rdi, OP_MOV
    mov     rsi, 41
    mov     rdx, 42
    mov     rcx, 0
    call    encode_rrr
    mov     [rbx + 32], rax
    ; 5: MOV R42, R44
    mov     rdi, OP_MOV
    mov     rsi, 42
    mov     rdx, 44
    mov     rcx, 0
    call    encode_rrr
    mov     [rbx + 40], rax
    ; 6: SUBI R43, R43, 1
    mov     rdi, OP_SUBI
    mov     rsi, 43
    mov     rdx, 43
    mov     rcx, 1
    call    encode_rri
    mov     [rbx + 48], rax
    ; 7: LDI R45, 0
    mov     rdi, OP_LDI
    mov     rsi, 45
    mov     rdx, 0
    call    encode_ldi
    mov     [rbx + 56], rax
    ; 8: JNE R43, R45, -6  (PC after fetch is 9, so offset -6 → PC=3)
    mov     rdi, OP_JNE
    mov     rsi, 43
    mov     rdx, 45
    mov     rcx, -6
    call    encode_branch
    mov     [rbx + 64], rax
    ; 9: HLT
    mov     rdi, OP_HLT
    call    encode_hlt
    mov     [rbx + 72], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 10
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 10000
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 42
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_fib]
    mov     rdx, 55
    call    check_eq
    ret

.run_fact5:
    ; Factorial(5) = 120
    ; R41=n=5, R42=acc=1, R43=zero=0
    ; loop: MUL R42, R42, R41; SUBI R41, R41, 1; JNE R41, R43, -3; HLT
    ; addr 0: LDI R41, 5
    ; addr 1: LDI R42, 1
    ; addr 2: LDI R43, 0
    ; addr 3: MUL R42, R42, R41
    ; addr 4: SUBI R41, R41, 1
    ; addr 5: JNE R41, R43, -3   (PC after fetch=6, offset -3 → PC=3)
    ; addr 6: HLT
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    lea     rbx, [rel prog_buf]
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 5
    call    encode_ldi
    mov     [rbx], rax
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 1
    call    encode_ldi
    mov     [rbx + 8], rax
    mov     rdi, OP_LDI
    mov     rsi, 43
    mov     rdx, 0
    call    encode_ldi
    mov     [rbx + 16], rax
    mov     rdi, OP_MUL
    mov     rsi, 42
    mov     rdx, 42
    mov     rcx, 41
    call    encode_rrr
    mov     [rbx + 24], rax
    mov     rdi, OP_SUBI
    mov     rsi, 41
    mov     rdx, 41
    mov     rcx, 1
    call    encode_rri
    mov     [rbx + 32], rax
    mov     rdi, OP_JNE
    mov     rsi, 41
    mov     rdx, 43
    mov     rcx, -3
    call    encode_branch
    mov     [rbx + 40], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    mov     [rbx + 48], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 7
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 10000
    call    cpu_run
    lea     rdi, [rel cpu_struct]
    mov     rsi, 42
    call    cpu_read_reg
    lea     rsi, [rel tname_cpu_fact]
    mov     rdx, 120
    call    check_eq
    ret

; ── run_benchmarks ────────────────────────────────────────────────────────────
run_benchmarks:
    PUSH_CALLEE
    lea     rdi, [rel str_bench_hdr]
    call    print_cstr

    ; Benchmark 1: Fibonacci(30) — CANONICAL (build_fib30: 29 iters, result R11)
    lea     rdi, [rel str_bench_fib]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    lea     rbx, [rel prog_buf]
    mov     rdi, OP_LDI
    mov     rsi, 10
    mov     rdx, 0
    call    encode_ldi
    mov     [rbx], rax
    mov     rdi, OP_LDI
    mov     rsi, 11
    mov     rdx, 1
    call    encode_ldi
    mov     [rbx + 8], rax
    mov     rdi, OP_LDI
    mov     rsi, 12
    mov     rdx, 29
    call    encode_ldi
    mov     [rbx + 16], rax
    mov     rdi, OP_JEQ
    mov     rsi, 12
    mov     rdx, 0
    mov     rcx, 5
    call    encode_branch
    mov     [rbx + 24], rax
    mov     rdi, OP_ADD
    mov     rsi, 13
    mov     rdx, 10
    mov     rcx, 11
    call    encode_rrr
    mov     [rbx + 32], rax
    mov     rdi, OP_MOV
    mov     rsi, 10
    mov     rdx, 11
    mov     rcx, 0
    call    encode_rrr
    mov     [rbx + 40], rax
    mov     rdi, OP_MOV
    mov     rsi, 11
    mov     rdx, 13
    mov     rcx, 0
    call    encode_rrr
    mov     [rbx + 48], rax
    mov     rdi, OP_SUBI
    mov     rsi, 12
    mov     rdx, 12
    mov     rcx, 1
    call    encode_rri
    mov     [rbx + 56], rax
    mov     rdi, OP_JMP
    mov     rsi, 3
    call    encode_jmp
    mov     [rbx + 64], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    mov     [rbx + 72], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 10
    xor     rcx, rcx
    call    cpu_load_program
    cpuid
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     [rel bench_start], rax
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100000
    call    cpu_run
    cpuid
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     [rel bench_end], rax
    mov     rax, [rel bench_end]
    sub     rax, [rel bench_start]
    mov     rdi, rax
    call    print_int64
    lea     rdi, [rel str_bench_cycles]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    mov     rsi, 11
    call    cpu_read_reg
    lea     rsi, [rel vname_bench_fib]
    mov     rdx, 832040
    call    check_eq

    ; Benchmark 2: Factorial(12) — CANONICAL (build_fact12, result R11)
    lea     rdi, [rel str_bench_fact]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    lea     rbx, [rel prog_buf]
    mov     rdi, OP_LDI
    mov     rsi, 10
    mov     rdx, 12
    call    encode_ldi
    mov     [rbx], rax
    mov     rdi, OP_LDI
    mov     rsi, 11
    mov     rdx, 1
    call    encode_ldi
    mov     [rbx + 8], rax
    mov     rdi, OP_JEQ
    mov     rsi, 10
    mov     rdx, 0
    mov     rcx, 3
    call    encode_branch
    mov     [rbx + 16], rax
    mov     rdi, OP_MUL
    mov     rsi, 11
    mov     rdx, 11
    mov     rcx, 10
    call    encode_rrr
    mov     [rbx + 24], rax
    mov     rdi, OP_SUBI
    mov     rsi, 10
    mov     rdx, 10
    mov     rcx, 1
    call    encode_rri
    mov     [rbx + 32], rax
    mov     rdi, OP_JMP
    mov     rsi, 2
    call    encode_jmp
    mov     [rbx + 40], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    mov     [rbx + 48], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 7
    xor     rcx, rcx
    call    cpu_load_program
    cpuid
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     [rel bench_start], rax
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100000
    call    cpu_run
    cpuid
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     [rel bench_end], rax
    mov     rax, [rel bench_end]
    sub     rax, [rel bench_start]
    mov     rdi, rax
    call    print_int64
    lea     rdi, [rel str_bench_cycles]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    mov     rsi, 11
    call    cpu_read_reg
    lea     rsi, [rel vname_bench_fact]
    mov     rdx, 479001600
    call    check_eq

    ; Benchmark 3: Array sum 1..1000 — CANONICAL (build_array_sum_1000, result R3)
    lea     rdi, [rel str_bench_array]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    lea     rbx, [rel prog_buf]
    mov     rdi, OP_LDI
    mov     rsi, 3
    mov     rdx, 0
    call    encode_ldi
    mov     [rbx], rax
    mov     rdi, OP_LDI
    mov     rsi, 4
    mov     rdx, 1
    call    encode_ldi
    mov     [rbx + 8], rax
    mov     rdi, OP_LDI
    mov     rsi, 5
    mov     rdx, 1001
    call    encode_ldi
    mov     [rbx + 16], rax
    mov     rdi, OP_JEQ
    mov     rsi, 4
    mov     rdx, 5
    mov     rcx, 3
    call    encode_branch
    mov     [rbx + 24], rax
    mov     rdi, OP_ADD
    mov     rsi, 3
    mov     rdx, 3
    mov     rcx, 4
    call    encode_rrr
    mov     [rbx + 32], rax
    mov     rdi, OP_ADDI
    mov     rsi, 4
    mov     rdx, 4
    mov     rcx, 1
    call    encode_rri
    mov     [rbx + 40], rax
    mov     rdi, OP_JMP
    mov     rsi, 3
    call    encode_jmp
    mov     [rbx + 48], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    mov     [rbx + 56], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 8
    xor     rcx, rcx
    call    cpu_load_program
    cpuid
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     [rel bench_start], rax
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100000
    call    cpu_run
    cpuid
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     [rel bench_end], rax
    mov     rax, [rel bench_end]
    sub     rax, [rel bench_start]
    mov     rdi, rax
    call    print_int64
    lea     rdi, [rel str_bench_cycles]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    mov     rsi, 3
    call    cpu_read_reg
    lea     rsi, [rel vname_bench_array]
    mov     rdx, 500500
    call    check_eq

    ; Benchmark 4: Arith loop 3000 — CANONICAL (build_arith_loop_3000, result R12)
    lea     rdi, [rel str_bench_arith]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    lea     rbx, [rel prog_buf]
    mov     rdi, OP_LDI
    mov     rsi, 10
    mov     rdx, 1
    call    encode_ldi
    mov     [rbx], rax
    mov     rdi, OP_LDI
    mov     rsi, 11
    mov     rdx, 2
    call    encode_ldi
    mov     [rbx + 8], rax
    mov     rdi, OP_LDI
    mov     rsi, 12
    mov     rdx, 0
    call    encode_ldi
    mov     [rbx + 16], rax
    mov     rdi, OP_LDI
    mov     rsi, 13
    mov     rdx, 3000
    call    encode_ldi
    mov     [rbx + 24], rax
    mov     rdi, OP_JEQ
    mov     rsi, 13
    mov     rdx, 0
    mov     rcx, 5
    call    encode_branch
    mov     [rbx + 32], rax
    mov     rdi, OP_ADD
    mov     rsi, 12
    mov     rdx, 10
    mov     rcx, 11
    call    encode_rrr
    mov     [rbx + 40], rax
    mov     rdi, OP_MOV
    mov     rsi, 10
    mov     rdx, 11
    mov     rcx, 0
    call    encode_rrr
    mov     [rbx + 48], rax
    mov     rdi, OP_SUB
    mov     rsi, 11
    mov     rdx, 12
    mov     rcx, 10
    call    encode_rrr
    mov     [rbx + 56], rax
    mov     rdi, OP_SUBI
    mov     rsi, 13
    mov     rdx, 13
    mov     rcx, 1
    call    encode_rri
    mov     [rbx + 64], rax
    mov     rdi, OP_JMP
    mov     rsi, 4
    call    encode_jmp
    mov     [rbx + 72], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    mov     [rbx + 80], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 11
    xor     rcx, rcx
    call    cpu_load_program
    cpuid
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     [rel bench_start], rax
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100000
    call    cpu_run
    cpuid
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     [rel bench_end], rax
    mov     rax, [rel bench_end]
    sub     rax, [rel bench_start]
    mov     rdi, rax
    call    print_int64
    lea     rdi, [rel str_bench_cycles]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    mov     rsi, 12
    call    cpu_read_reg
    lea     rsi, [rel vname_bench_arith]
    mov     rdx, 3
    call    check_eq

    ; Benchmark 5: TernOO word construction (10000 iterations)
    lea     rdi, [rel str_bench_word]
    call    print_cstr
    cpuid
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     [rel bench_start], rax
    mov     r13, 10000
.word_bench_loop:
    test    r13, r13
    jz      .word_bench_done
    mov     rdi, 42
    call    word_build_int
    mov     rdi, 0
    mov     rsi, 0
    mov     rdx, 0
    mov     rcx, 100
    mov     r8,  0
    call    word_build_map
    mov     rdi, 0
    mov     rsi, 0
    mov     rdx, 0
    mov     rcx, 4
    mov     r8,  0
    call    word_build_exec
    dec     r13
    jmp     .word_bench_loop
.word_bench_done:
    cpuid
    rdtsc
    shl     rdx, 32
    or      rax, rdx
    mov     [rel bench_end], rax
    mov     rax, [rel bench_end]
    sub     rax, [rel bench_start]
    mov     rdi, rax
    call    print_int64
    lea     rdi, [rel str_bench_cycles]
    call    print_cstr

    POP_CALLEE
    ret

; ── run_demos ─────────────────────────────────────────────────────────────────
run_demos:
    PUSH_CALLEE
    lea     rdi, [rel str_demo_hdr]
    call    print_cstr

    ; Demo 1: Fibonacci(15)
    lea     rdi, [rel str_demo_fib]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    lea     rbx, [rel prog_buf]
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 0
    call    encode_ldi
    mov     [rbx], rax
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 1
    call    encode_ldi
    mov     [rbx + 8], rax
    mov     rdi, OP_LDI
    mov     rsi, 43
    mov     rdx, 15
    call    encode_ldi
    mov     [rbx + 16], rax
    mov     rdi, OP_ADD
    mov     rsi, 44
    mov     rdx, 41
    mov     rcx, 42
    call    encode_rrr
    mov     [rbx + 24], rax
    mov     rdi, OP_MOV
    mov     rsi, 41
    mov     rdx, 42
    mov     rcx, 0
    call    encode_rrr
    mov     [rbx + 32], rax
    mov     rdi, OP_MOV
    mov     rsi, 42
    mov     rdx, 44
    mov     rcx, 0
    call    encode_rrr
    mov     [rbx + 40], rax
    mov     rdi, OP_SUBI
    mov     rsi, 43
    mov     rdx, 43
    mov     rcx, 1
    call    encode_rri
    mov     [rbx + 48], rax
    mov     rdi, OP_LDI
    mov     rsi, 45
    mov     rdx, 0
    call    encode_ldi
    mov     [rbx + 56], rax
    mov     rdi, OP_JNE
    mov     rsi, 43
    mov     rdx, 45
    mov     rcx, -6
    call    encode_branch
    mov     [rbx + 64], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    mov     [rbx + 72], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 10
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100000
    call    cpu_run
    ; print result
    lea     rdi, [rel demo_fib_result]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    mov     rsi, 42
    call    cpu_read_reg
    mov     rdi, rax
    call    print_int64
    call    print_newline
    ; dump non-zero regs
    lea     rdi, [rel cpu_struct]
    mov     rsi, 50
    call    cpu_dump_regs

    ; Demo 2: Factorial(8)
    lea     rdi, [rel str_demo_fact]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    lea     rbx, [rel prog_buf]
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 8
    call    encode_ldi
    mov     [rbx], rax
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 1
    call    encode_ldi
    mov     [rbx + 8], rax
    mov     rdi, OP_LDI
    mov     rsi, 43
    mov     rdx, 0
    call    encode_ldi
    mov     [rbx + 16], rax
    mov     rdi, OP_MUL
    mov     rsi, 42
    mov     rdx, 42
    mov     rcx, 41
    call    encode_rrr
    mov     [rbx + 24], rax
    mov     rdi, OP_SUBI
    mov     rsi, 41
    mov     rdx, 41
    mov     rcx, 1
    call    encode_rri
    mov     [rbx + 32], rax
    mov     rdi, OP_JNE
    mov     rsi, 41
    mov     rdx, 43
    mov     rcx, -3
    call    encode_branch
    mov     [rbx + 40], rax
    mov     rdi, OP_HLT
    call    encode_hlt
    mov     [rbx + 48], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 7
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 100000
    call    cpu_run
    lea     rdi, [rel demo_fact_result]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    mov     rsi, 42
    call    cpu_read_reg
    mov     rdi, rax
    call    print_int64
    call    print_newline

    ; Demo 3: TernOO word dispatch
    lea     rdi, [rel str_demo_ternoo]
    call    print_cstr
    ; Build an EXEC word and a DATA word, describe them
    mov     rdi, 0
    mov     rsi, 0
    mov     rdx, 0
    mov     rcx, 4
    mov     r8,  10
    call    word_build_exec
    mov     r12, rax
    lea     rdi, [rel str_word_built]
    call    print_cstr
    mov     rdi, r12
    call    word_describe
    mov     rdi, 12345
    call    word_build_int
    mov     r12, rax
    lea     rdi, [rel str_word_built]
    call    print_cstr
    mov     rdi, r12
    call    word_describe
    ; Build a MAP word
    mov     rdi, 1
    mov     rsi, 0
    mov     rdx, -1
    mov     rcx, 999
    mov     r8,  0
    call    word_build_map
    mov     r12, rax
    lea     rdi, [rel str_word_built]
    call    print_cstr
    mov     rdi, r12
    call    word_describe
    lea     rdi, [rel str_ternoo_ok]
    call    print_cstr

    ; Demo 4: PIGART canvas (RPOINT, RLINE, RNODE, RENDER)
    lea     rdi, [rel str_demo_canvas]
    call    print_cstr
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel cpu_memory]
    call    cpu_init
    lea     rbx, [rel prog_buf]
    ; Build a colour DATA word and store in R44
    ; We use LDI to load a simple value into R44 (colour)
    ; LDI R44, 7 (colour=7)
    mov     rdi, OP_LDI
    mov     rsi, 44
    mov     rdx, 7
    call    encode_ldi
    mov     [rbx], rax
    ; LDI R41, 100  (pos=100)
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 100
    call    encode_ldi
    mov     [rbx + 8], rax
    ; RPOINT R45, R41, R44  (canvas point at pos=100, colour=7)
    mov     rdi, OP_RPOINT
    mov     rsi, 45
    mov     rdx, 41
    mov     rcx, 44
    call    encode_rrr
    mov     [rbx + 16], rax
    ; LDI R41, 200; LDI R42, 300
    mov     rdi, OP_LDI
    mov     rsi, 41
    mov     rdx, 200
    call    encode_ldi
    mov     [rbx + 24], rax
    mov     rdi, OP_LDI
    mov     rsi, 42
    mov     rdx, 300
    call    encode_ldi
    mov     [rbx + 32], rax
    ; RLINE R46, R41, R42, R44  (line from 200 to 300)
    mov     rdi, OP_RLINE
    mov     rsi, 46
    mov     rdx, 41
    mov     rcx, 42
    call    encode_rrr4
    mov     [rbx + 40], rax
    ; RENDER
    mov     rdi, OP_RENDER
    call    encode_noarg
    mov     [rbx + 48], rax
    ; HLT
    mov     rdi, OP_HLT
    call    encode_hlt
    mov     [rbx + 56], rax
    lea     rdi, [rel cpu_struct]
    lea     rsi, [rel prog_buf]
    mov     rdx, 8
    xor     rcx, rcx
    call    cpu_load_program
    lea     rdi, [rel cpu_struct]
    mov     rsi, 10000
    call    cpu_run

    POP_CALLEE
    ret

; ── Instruction encoders ──────────────────────────────────────────────────────
; These encode 5500FP instructions as balanced ternary integers.
; All use set_field_val to place fields into the 24-trit word.

; encode_hlt: encode HLT (or any no-arg opcode passed in rdi)
encode_hlt:
    ; op in rdi
    push    rbx
    mov     rbx, rdi
    ; word = set_field_val(0, 20, 4, op)
    xor     rdi, rdi
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, rbx
    call    set_field_val
    pop     rbx
    ret

; encode_noarg: same as encode_hlt
encode_noarg:
    jmp     encode_hlt

; encode_ldi: LDI Rd, imm
; rdi=op, rsi=Rd, rdx=imm
encode_ldi:
    PUSH_CALLEE
    mov     r12, rdi        ; op
    mov     r13, rsi        ; Rd
    mov     r14, rdx        ; imm
    ; field0 (T0-T3) = Rd - 40
    sub     r13, 40
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    mov     r15, rax
    ; imm in fields 2+3+4 (T8-T19, 12 trits) — field 1 (T4-T7) = Rs1 = 0 (unused)
    mov     rdi, r15
    mov     rsi, 8
    mov     rdx, 12
    mov     rcx, r14
    call    set_field_val
    mov     r15, rax
    ; op in field5 (T20-T23)
    mov     rdi, r15
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r12
    call    set_field_val
    POP_CALLEE
    ret

; encode_rrr: op Rd, Rs1, Rs2
; rdi=op, rsi=Rd, rdx=Rs1, rcx=Rs2
encode_rrr:
    PUSH_CALLEE
    mov     r12, rdi        ; op
    mov     r13, rsi        ; Rd
    mov     r14, rdx        ; Rs1
    mov     r15, rcx        ; Rs2
    sub     r13, 40
    sub     r14, 40
    sub     r15, 40
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 4
    mov     rdx, 4
    mov     rcx, r14
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 8
    mov     rdx, 4
    mov     rcx, r15
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r12
    call    set_field_val
    POP_CALLEE
    ret

; encode_rrr4: op Rd, Rs1, Rs2, Rs3 (4 register fields)
; rdi=op, rsi=Rd, rdx=Rs1, rcx=Rs2  (Rs3 = R44 hardcoded for RLINE demo)
encode_rrr4:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    mov     r14, rdx
    mov     r15, rcx
    sub     r13, 40
    sub     r14, 40
    sub     r15, 40
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 4
    mov     rdx, 4
    mov     rcx, r14
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 8
    mov     rdx, 4
    mov     rcx, r15
    call    set_field_val
    mov     rbx, rax
    ; Rs3 = R44 → 44-40=4
    mov     rdi, rbx
    mov     rsi, 12
    mov     rdx, 4
    mov     rcx, 4          ; R44-40=4
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r12
    call    set_field_val
    POP_CALLEE
    ret

; encode_rri: op Rd, Rs1, imm  (J2 format)
; rdi=op, rsi=Rd, rdx=Rs1, rcx=imm
encode_rri:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    mov     r14, rdx
    mov     r15, rcx
    sub     r13, 40
    sub     r14, 40
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 4
    mov     rdx, 4
    mov     rcx, r14
    call    set_field_val
    mov     rbx, rax
    ; imm in T8-T19 (12 trits)
    mov     rdi, rbx
    mov     rsi, 8
    mov     rdx, 12
    mov     rcx, r15
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r12
    call    set_field_val
    POP_CALLEE
    ret

; encode_r1: single-register opcode (PUSH/POP)
; rdi=op, rsi=Rd
encode_r1:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    sub     r13, 40
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r12
    call    set_field_val
    POP_CALLEE
    ret

; encode_jmp: JMP/JSR addr
; rdi=op, rsi=addr
encode_jmp:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    ; imm in T0-T19 (20 trits)
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 20
    mov     rcx, r13
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r12
    call    set_field_val
    POP_CALLEE
    ret

; encode_branch: JEQ/JNE/JB Rd, Rs1, offset
; rdi=op, rsi=Rd, rdx=Rs1, rcx=offset
encode_branch:
    jmp     encode_rri

; ── check_eq ──────────────────────────────────────────────────────────────────
; Check rax == rdx, print result, update counters.
; Input:  rax = actual value
;         rsi = pointer to test name string
;         rdx = expected value
check_eq:
    push    rbx
    push    rcx
    push    r12
    push    r13
    mov     r12, rax        ; actual
    mov     r13, rdx        ; expected
    cmp     r12, r13
    je      .pass
    ; FAIL
    lea     rdi, [rel str_test_fail]
    call    print_cstr
    mov     rdi, rsi
    call    print_cstr
    lea     rdi, [rel str_result_eq]
    call    print_cstr
    mov     rdi, r12
    call    print_int64
    lea     rdi, [rel str_result_eq]
    call    print_cstr
    lea     rdi, [rel str_expected]
    call    print_cstr
    mov     rdi, r13
    call    print_int64
    call    print_newline
    inc     qword [rel test_fail]
    jmp     .done
.pass:
    lea     rdi, [rel str_test_pass]
    call    print_cstr
    mov     rdi, rsi
    call    print_cstr
    call    print_newline
    inc     qword [rel test_pass]
.done:
    pop     r13
    pop     r12
    pop     rcx
    pop     rbx
    ret

; ── strcmp ────────────────────────────────────────────────────────────────────
; Compare two null-terminated strings.
; Input:  rdi = str1,  rsi = str2
; Output: rax = 0 if equal, non-zero otherwise
strcmp:
    push    rbx
    push    rcx
    xor     rax, rax
.loop:
    movzx   rbx, byte [rdi]
    movzx   rcx, byte [rsi]
    cmp     rbx, rcx
    jne     .neq
    test    rbx, rbx
    jz      .eq
    inc     rdi
    inc     rsi
    jmp     .loop
.eq:
    xor     rax, rax
    jmp     .done
.neq:
    mov     rax, 1
.done:
    pop     rcx
    pop     rbx
    ret

; print_cstr, print_int64, print_newline are exported from cpu.asm

section .data

str_expected:   db  " expected=", 0
demo_fib_result: db  "  fib(15) = ", 0
demo_fact_result: db  "  fact(8) = ", 0
