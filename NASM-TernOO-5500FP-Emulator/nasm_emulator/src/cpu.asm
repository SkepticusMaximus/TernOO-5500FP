; ============================================================================
; cpu.asm  —  5500FP ISA core: 81 registers, fetch/decode/execute loop,
;             all 37 opcodes + PIGART rendering primitives.
;
; The CPU state is a single contiguous block of memory (CPU_STRUCT_SIZE bytes)
; allocated by the caller and passed as a pointer in rdi to cpu_init.
; The memory array is a separate allocation (MEMORY_SIZE * 8 bytes).
;
; Instruction format (24-trit word, split into 6 × 4-trit fields):
;   Field 0 (T0–T3):   F0  — Rd  (register, encoded as reg-40)
;   Field 1 (T4–T7):   F1  — Rs1
;   Field 2 (T8–T11):  F2  — Rs2 / imm[11:8]
;   Field 3 (T12–T15): F3  — Rs3 / imm[7:4]
;   Field 4 (T16–T19): F4  — Rs4 / imm[3:0]
;   Field 5 (T20–T23): F5  — opcode
;
; Format A: [Rd][Rs1][Rs2][Rs3][Rs4][op]
; Format J2: [Rd][Rs1][imm(12t)][op]
; Format J:  [imm(20t)][op]
; ============================================================================

%include "include/ternoo.inc"

section .bss
; Canvas entries: each entry is 64 bytes (8 qwords)
; [0]=type(1=POINT,2=LINE,3=NODE,4=EDGE), [1]=pos/src, [2]=colour/end/dims/dst,
; [3]=style/shape/exec, [4]=object_raw, [5..7]=spare
canvas_buf: resq 1024 * 8   ; up to 1024 canvas entries

section .data
; Decode register: add 40 to get actual register number (balanced encoding)
; reg_actual = field_value + 40
REG_OFFSET  equ 40

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

global cpu_init
global cpu_reset
global cpu_load_program
global cpu_run
global cpu_read_reg
global cpu_write_reg
global cpu_mem_read
global cpu_mem_write
global cpu_fetch
global cpu_execute
global cpu_dump_regs
global print_cstr
global print_int64
global print_newline
global read_int64

; ── cpu_init ─────────────────────────────────────────────────────────────────
; Initialise a CPU struct.
; Input:  rdi = pointer to CPU struct (CPU_STRUCT_SIZE bytes, zeroed by caller)
;         rsi = pointer to memory array (MEMORY_SIZE * 8 bytes, zeroed by caller)
; Output: none  (rdi struct is initialised)
cpu_init:
    push    rbx
    mov     rbx, rdi
    ; store memory pointer in a known location — we use a global for simplicity
    mov     [rel cpu_mem_ptr], rsi
    ; reset all fields
    mov     rdi, rbx
    call    cpu_reset
    pop     rbx
    ret

; ── cpu_reset ─────────────────────────────────────────────────────────────────
; Reset CPU state (registers, PC, cycle count, halted flag, heap ptr).
; Input:  rdi = pointer to CPU struct
cpu_reset:
    push    rbx
    push    rcx
    mov     rbx, rdi
    ; zero registers
    lea     rdi, [rbx + CPU_REGS]
    xor     eax, eax
    mov     ecx, CPU_NUM_REGS
    rep     stosq
    ; zero PC, cycles, halted
    mov     qword [rbx + CPU_PC],     0
    mov     qword [rbx + CPU_CYCLES], 0
    mov     qword [rbx + CPU_HALTED], 0
    ; init heap pointer
    mov     qword [rbx + CPU_HEAP_PTR], HEAP_BASE
    ; init stack pointer register (R79) to HEAP_BASE - 1
    mov     qword [rbx + CPU_REGS + REG_SP*8], HEAP_BASE - 1
    ; zero call stack
    mov     qword [rbx + CPU_CALL_TOP], 0
    ; zero canvas count
    mov     qword [rbx + CPU_CANVAS_CNT], 0
    pop     rcx
    pop     rbx
    ret

; ── cpu_load_program ──────────────────────────────────────────────────────────
; Load a program (array of int64_t words) into CPU memory.
; Input:  rdi = CPU struct pointer
;         rsi = program array pointer
;         rdx = number of words
;         rcx = start address in ternary memory
cpu_load_program:
    PUSH_CALLEE
    mov     r12, rdi        ; CPU
    mov     r13, rsi        ; program
    mov     r14, rdx        ; count
    mov     r15, rcx        ; start addr
    ; set PC to start
    mov     [r12 + CPU_PC], r15
    ; copy words to memory
    mov     rbx, 0          ; index
.loop:
    cmp     rbx, r14
    jge     .done
    mov     rax, [r13 + rbx*8]  ; word
    ; cpu_mem_write(cpu, addr, value)
    mov     rdi, r12
    mov     rsi, r15
    add     rsi, rbx
    mov     rdx, rax
    call    cpu_mem_write
    inc     rbx
    jmp     .loop
.done:
    POP_CALLEE
    ret

; ── cpu_read_reg ──────────────────────────────────────────────────────────────
; Read a register value.
; Input:  rdi = CPU struct pointer
;         rsi = register number (0..80)
; Output: rax = register value (R0 always returns 0)
cpu_read_reg:
    test    rsi, rsi
    jz      .zero
    cmp     rsi, CPU_NUM_REGS
    jge     .zero
    ; reg[rsi % 81]
    mov     rax, rsi
    mov     rcx, CPU_NUM_REGS
    xor     rdx, rdx
    div     rcx             ; rax = rsi / 81, rdx = rsi % 81
    lea     rax, [rdi + CPU_REGS]
    mov     rax, [rax + rdx*8]
    ret
.zero:
    xor     rax, rax
    ret

; ── cpu_write_reg ─────────────────────────────────────────────────────────────
; Write a register value (R0 writes are silently ignored).
; Input:  rdi = CPU struct pointer
;         rsi = register number
;         rdx = value
cpu_write_reg:
    test    rsi, rsi
    jz      .done
    cmp     rsi, CPU_NUM_REGS
    jge     .done
    ; clamp value
    push    rdi
    push    rsi
    mov     rdi, rdx
    call    clamp_word
    pop     rsi
    pop     rdi
    mov     rcx, rsi
    mov     [rdi + CPU_REGS + rcx*8], rax
.done:
    ret

; ── cpu_mem_read ──────────────────────────────────────────────────────────────
; Read from CPU memory.
; Input:  rdi = CPU struct pointer
;         rsi = address
; Output: rax = value (0 if OOB)
cpu_mem_read:
    cmp     rsi, 0
    jl      .oob
    cmp     rsi, MEMORY_SIZE
    jge     .oob
    mov     rax, [rel cpu_mem_ptr]
    mov     rax, [rax + rsi*8]
    ret
.oob:
    xor     rax, rax
    ret

; ── cpu_mem_write ─────────────────────────────────────────────────────────────
; Write to CPU memory.
; Input:  rdi = CPU struct pointer
;         rsi = address
;         rdx = value
cpu_mem_write:
    cmp     rsi, 0
    jl      .oob
    cmp     rsi, MEMORY_SIZE
    jge     .oob
    ; clamp value
    push    rdi
    push    rsi
    mov     rdi, rdx
    call    clamp_word
    pop     rsi
    pop     rdi
    mov     rcx, [rel cpu_mem_ptr]
    mov     [rcx + rsi*8], rax
.oob:
    ret

; ── cpu_fetch ─────────────────────────────────────────────────────────────────
; Fetch the next instruction and advance PC.
; Input:  rdi = CPU struct pointer
; Output: rax = instruction word
cpu_fetch:
    mov     rsi, [rdi + CPU_PC]
    inc     qword [rdi + CPU_PC]
    call    cpu_mem_read
    ret

; ── _fields ───────────────────────────────────────────────────────────────────
; Internal: extract 6 × 4-trit fields from a 24-trit instruction.
; Input:  rdi = instruction word
;         rsi = pointer to int64_t[6] output array
; Destroys: rax, rcx, rdx
_fields:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    mov     r13, rsi
    xor     rbx, rbx        ; field index
.loop:
    cmp     rbx, 6
    jge     .done
    ; get_field_val(word, lsb=rbx*4, width=4)
    mov     rdi, r12
    mov     rsi, rbx
    shl     rsi, 2          ; lsb = field_index * 4
    mov     rdx, 4          ; width
    call    get_field_val
    mov     [r13 + rbx*8], rax
    inc     rbx
    jmp     .loop
.done:
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _decode_reg ───────────────────────────────────────────────────────────────
; Decode a 4-trit field value to an actual register number.
; field_value + 40 = register number
; Input:  rdi = field value (balanced ternary, -4..+4 for 4 trits)
; Output: rax = register number (0..80)
_decode_reg:
    lea     rax, [rdi + REG_OFFSET]
    ret

; ── cpu_execute ───────────────────────────────────────────────────────────────
; Execute one instruction.
; Input:  rdi = CPU struct pointer
;         rsi = instruction word
; Output: rax = 0 (ok), -1 (halt), -2 (error)
cpu_execute:
    PUSH_CALLEE
    mov     r12, rdi        ; r12 = CPU
    mov     r13, rsi        ; r13 = instruction

    ; extract 6 fields into local array on stack
    sub     rsp, 64         ; 8 qwords for fields[0..5] + alignment
    mov     r14, rsp        ; r14 = &fields[0]

    mov     rdi, r13
    mov     rsi, r14
    call    _fields         ; fields[0..5] filled

    ; op = fields[5]
    mov     r15, [r14 + 5*8]    ; r15 = opcode (balanced ternary integer)

    ; ── dispatch on opcode ──────────────────────────────────────────────────
    cmp     r15, OP_NOP
    je      .op_nop
    cmp     r15, OP_HLT
    je      .op_hlt
    cmp     r15, OP_ADD
    je      .op_add
    cmp     r15, OP_ADDI
    je      .op_addi
    cmp     r15, OP_SUB
    je      .op_sub
    cmp     r15, OP_SUBI
    je      .op_subi
    cmp     r15, OP_MUL
    je      .op_mul
    cmp     r15, OP_DIV
    je      .op_div
    cmp     r15, OP_NEG
    je      .op_neg
    cmp     r15, OP_MOV
    je      .op_mov
    cmp     r15, OP_LDI
    je      .op_ldi
    cmp     r15, OP_LD
    je      .op_ld
    cmp     r15, OP_ST
    je      .op_st
    cmp     r15, OP_JMP
    je      .op_jmp
    cmp     r15, OP_JSR
    je      .op_jsr
    cmp     r15, OP_RTI
    je      .op_rti
    cmp     r15, OP_JEQ
    je      .op_jeq
    cmp     r15, OP_JNE
    je      .op_jne
    cmp     r15, OP_JB
    je      .op_jb
    cmp     r15, OP_PUSH
    je      .op_push
    cmp     r15, OP_POP
    je      .op_pop
    cmp     r15, OP_MIN
    je      .op_min
    cmp     r15, OP_MAX
    je      .op_max
    cmp     r15, OP_TXOR
    je      .op_txor
    cmp     r15, OP_EQUAL
    je      .op_equal
    cmp     r15, OP_SUM
    je      .op_sum
    cmp     r15, OP_TTT
    je      .op_ttt
    cmp     r15, OP_TTZ
    je      .op_ttz
    cmp     r15, OP_TTP
    je      .op_ttp
    cmp     r15, OP_OUT
    je      .op_out
    cmp     r15, OP_IN
    je      .op_in
    cmp     r15, OP_TOBJ
    je      .op_tobj
    cmp     r15, OP_TGET
    je      .op_tget
    cmp     r15, OP_TPAYLOAD
    je      .op_tpayload
    cmp     r15, OP_TCALL
    je      .op_tcall
    cmp     r15, OP_TNEW
    je      .op_tnew
    cmp     r15, OP_TBUILD
    je      .op_tbuild
    cmp     r15, OP_TSEG
    je      .op_tseg
    cmp     r15, OP_RPOINT
    je      .op_rpoint
    cmp     r15, OP_RLINE
    je      .op_rline
    cmp     r15, OP_RNODE
    je      .op_rnode
    cmp     r15, OP_REDGE
    je      .op_redge
    cmp     r15, OP_RENDER
    je      .op_render
    ; unknown opcode
    jmp     .op_error

    ; ── Helper macros for register access ────────────────────────────────────
    ; READ_REG result_reg, field_index  — reads CPU reg from fields[field_index]
    ; WRITE_REG field_index, value_reg  — writes value_reg to CPU reg from fields[field_index]

    ; ── NOP ──────────────────────────────────────────────────────────────────
.op_nop:
    jmp     .done_ok

    ; ── HLT ──────────────────────────────────────────────────────────────────
.op_hlt:
    mov     qword [r12 + CPU_HALTED], 1
    jmp     .done_halt

    ; ── ADD: Rd = Rs1 + Rs2 ──────────────────────────────────────────────────
.op_add:
    ; decode Rd, Rs1, Rs2
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax        ; rbp = Rd
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax        ; rbx = Rs1
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax         ; r8  = Rs2
    ; read Rs1
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax        ; rbx = val(Rs1)
    ; read Rs2
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    add     rbx, rax        ; rbx = val(Rs1) + val(Rs2)
    ; write Rd
    mov     rdi, r12
    mov     rsi, rbp
    mov     rdx, rbx
    call    cpu_write_reg
    jmp     .done_ok

    ; ── ADDI: Rd = Rs1 + imm ─────────────────────────────────────────────────
.op_addi:
    ; J2 format: [Rd][Rs1][imm(12t)][op]
    ; fields[0]=Rd, fields[1]=Rs1, imm = from_trits(fields[2..4] concatenated)
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax        ; Rd
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax        ; Rs1
    ; build 12-trit immediate from fields[2..4]
    mov     rdi, r13
    mov     rsi, 8          ; lsb = trit 8
    mov     rdx, 12         ; width = 12 trits
    call    get_field_val
    mov     r8, rax         ; r8 = imm
    ; read Rs1
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    add     rax, r8
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── SUB: Rd = Rs1 - Rs2 ──────────────────────────────────────────────────
.op_sub:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    sub     rbx, rax
    mov     rdi, r12
    mov     rsi, rbp
    mov     rdx, rbx
    call    cpu_write_reg
    jmp     .done_ok

    ; ── SUBI: Rd = Rs1 - imm ─────────────────────────────────────────────────
.op_subi:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r13
    mov     rsi, 8
    mov     rdx, 12
    call    get_field_val
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    sub     rax, r8
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── MUL: Rd = Rs1 * Rs2 ──────────────────────────────────────────────────
.op_mul:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    imul    rbx, rax
    mov     rdi, r12
    mov     rsi, rbp
    mov     rdx, rbx
    call    cpu_write_reg
    jmp     .done_ok

    ; ── DIV: Rd = Rs1 / Rs2 ──────────────────────────────────────────────────
.op_div:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    test    rax, rax
    jz      .done_ok        ; division by zero: no-op
    mov     rcx, rax
    mov     rax, rbx
    cqo
    idiv    rcx
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── NEG: Rd = -Rs1 ───────────────────────────────────────────────────────
.op_neg:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    neg     rax
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── MOV: Rd = Rs1 ────────────────────────────────────────────────────────
.op_mov:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── LDI: Rd = imm ────────────────────────────────────────────────────────
.op_ldi:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    ; imm is 12-trit field at trits 8..19
    mov     rdi, r13
    mov     rsi, 8
    mov     rdx, 12
    call    get_field_val
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── LD: Rd = mem[Rs1] ────────────────────────────────────────────────────
.op_ld:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax        ; rbx = address
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_mem_read
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── ST: mem[Rs2] = Rd ────────────────────────────────────────────────────
.op_st:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax        ; Rd (value source)
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     rbx, rax        ; Rs2 (address)
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_read_reg
    mov     r8, rax         ; r8 = value
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax        ; rbx = address value
    mov     rdi, r12
    mov     rsi, rbx
    mov     rdx, r8
    call    cpu_mem_write
    jmp     .done_ok

    ; ── JMP: PC = imm ────────────────────────────────────────────────────────
.op_jmp:
    ; J format: imm is 20-trit field at trits 0..19
    mov     rdi, r13
    mov     rsi, 0
    mov     rdx, 20
    call    get_field_val
    mov     [r12 + CPU_PC], rax
    jmp     .done_ok

    ; ── JSR: LR=PC, push PC, PC=imm ──────────────────────────────────────────
.op_jsr:
    ; save current PC to LR
    mov     rax, [r12 + CPU_PC]
    mov     rdi, r12
    mov     rsi, REG_LR
    mov     rdx, rax
    call    cpu_write_reg
    ; push PC to call stack
    mov     rbx, [r12 + CPU_CALL_TOP]
    cmp     rbx, 255
    jge     .done_ok        ; call stack overflow: ignore
    mov     rax, [r12 + CPU_PC]
    mov     [r12 + CPU_CALL_STACK + rbx*8], rax
    inc     qword [r12 + CPU_CALL_TOP]
    ; jump
    mov     rdi, r13
    mov     rsi, 0
    mov     rdx, 20
    call    get_field_val
    mov     [r12 + CPU_PC], rax
    jmp     .done_ok

    ; ── RTI: PC = call_stack.pop() ───────────────────────────────────────────
.op_rti:
    mov     rbx, [r12 + CPU_CALL_TOP]
    test    rbx, rbx
    jz      .done_ok        ; empty stack: ignore
    dec     rbx
    mov     [r12 + CPU_CALL_TOP], rbx
    mov     rax, [r12 + CPU_CALL_STACK + rbx*8]
    mov     [r12 + CPU_PC], rax
    jmp     .done_ok

    ; ── JEQ: if Rd==Rs1 then PC += imm ───────────────────────────────────────
.op_jeq:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r13
    mov     rsi, 8
    mov     rdx, 12
    call    get_field_val
    mov     r8, rax         ; imm
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_read_reg
    mov     r9, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    cmp     r9, rax
    jne     .done_ok
    add     [r12 + CPU_PC], r8
    jmp     .done_ok

    ; ── JNE: if Rd!=Rs1 then PC += imm ───────────────────────────────────────
.op_jne:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r13
    mov     rsi, 8
    mov     rdx, 12
    call    get_field_val
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_read_reg
    mov     r9, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    cmp     r9, rax
    je      .done_ok
    add     [r12 + CPU_PC], r8
    jmp     .done_ok

    ; ── JB: if Rd<Rs1 then PC += imm ─────────────────────────────────────────
.op_jb:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r13
    mov     rsi, 8
    mov     rdx, 12
    call    get_field_val
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_read_reg
    mov     r9, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    cmp     r9, rax
    jge     .done_ok
    add     [r12 + CPU_PC], r8
    jmp     .done_ok

    ; ── PUSH: mem[SP] = Rd; SP-- ─────────────────────────────────────────────
.op_push:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    ; read SP
    mov     rdi, r12
    mov     rsi, REG_SP
    call    cpu_read_reg
    mov     rbx, rax        ; rbx = SP
    ; read Rd
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_read_reg
    mov     r8, rax         ; r8 = value
    ; mem[SP] = value
    mov     rdi, r12
    mov     rsi, rbx
    mov     rdx, r8
    call    cpu_mem_write
    ; SP--
    dec     rbx
    mov     rdi, r12
    mov     rsi, REG_SP
    mov     rdx, rbx
    call    cpu_write_reg
    jmp     .done_ok

    ; ── POP: SP++; Rd = mem[SP] ──────────────────────────────────────────────
.op_pop:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, r12
    mov     rsi, REG_SP
    call    cpu_read_reg
    inc     rax
    mov     rbx, rax        ; rbx = SP+1
    mov     rdi, r12
    mov     rsi, REG_SP
    mov     rdx, rbx
    call    cpu_write_reg
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_mem_read
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── MIN: Rd = trit_min(Rs1, Rs2) ─────────────────────────────────────────
.op_min:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     rdi, rbx
    mov     rsi, rax
    call    trit_min_word
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── MAX: Rd = trit_max(Rs1, Rs2) ─────────────────────────────────────────
.op_max:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     rdi, rbx
    mov     rsi, rax
    call    trit_max_word
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── TXOR: Rd = trit_txor(Rs1, Rs2) ──────────────────────────────────────
.op_txor:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     rdi, rbx
    mov     rsi, rax
    call    trit_txor_word
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── EQUAL: Rd = trit_equal(Rs1, Rs2) ─────────────────────────────────────
.op_equal:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     rdi, rbx
    mov     rsi, rax
    call    trit_equal_word
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── SUM: Rd = trit_sum(Rs1, Rs2) ─────────────────────────────────────────
.op_sum:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     rdi, rbx
    mov     rsi, rax
    call    trit_sum_word
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── TTT/TTZ/TTP: three-way trit branch ───────────────────────────────────
.op_ttt:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax        ; Rd (word)
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax        ; Rs1 (trit position)
    mov     rdi, r13
    mov     rsi, 8
    mov     rdx, 12
    call    get_field_val
    mov     r8, rax         ; imm
    ; get trit at position Rs1 in Rd
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_read_reg
    mov     r9, rax         ; word value
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax        ; trit position
    mov     rdi, r9
    mov     rsi, rbx
    call    get_trit_val
    ; TTT: branch if trit == -1
    cmp     rax, -1
    jne     .done_ok
    add     [r12 + CPU_PC], r8
    jmp     .done_ok

.op_ttz:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r13
    mov     rsi, 8
    mov     rdx, 12
    call    get_field_val
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_read_reg
    mov     r9, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rdi, r9
    mov     rsi, rax
    call    get_trit_val
    cmp     rax, 0
    jne     .done_ok
    add     [r12 + CPU_PC], r8
    jmp     .done_ok

.op_ttp:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r13
    mov     rsi, 8
    mov     rdx, 12
    call    get_field_val
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_read_reg
    mov     r9, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rdi, r9
    mov     rsi, rax
    call    get_trit_val
    cmp     rax, 1
    jne     .done_ok
    add     [r12 + CPU_PC], r8
    jmp     .done_ok

    ; ── OUT: print register value ─────────────────────────────────────────────
.op_out:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_read_reg
    ; print decimal value via print_int64
    mov     rdi, rax
    call    print_int64
    ; print newline
    call    print_newline
    jmp     .done_ok

    ; ── IN: read integer into register ───────────────────────────────────────
.op_in:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    ; read integer from stdin
    call    read_int64
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── TOBJ: Rd = set_trit(Rs1, 23, clamp(Rs2, -1, +1)) ────────────────────
.op_tobj:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     r9, rax         ; val(Rs1)
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    ; clamp tag to [-1, +1]
    cmp     rax, 1
    jle     .tobj_check_min
    mov     rax, 1
.tobj_check_min:
    cmp     rax, -1
    jge     .tobj_set
    mov     rax, -1
.tobj_set:
    mov     rdi, r9
    mov     rsi, 23
    mov     rdx, rax
    call    set_trit_val
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── TGET: Rd = get_trit(Rs1, 23) ─────────────────────────────────────────
.op_tget:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rdi, rax
    mov     rsi, 23
    call    get_trit_val
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── TPAYLOAD: Rd = get_field(Rs1, 0, 18) ─────────────────────────────────
.op_tpayload:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rdi, rax
    mov     rsi, PAYLOAD_LST
    mov     rdx, PAYLOAD_WIDTH
    call    get_field_val
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── TCALL: dispatch on primary type of Rd ────────────────────────────────
.op_tcall:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax        ; Rd (word to dispatch on)
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax        ; Rs1 (EXEC handler addr)
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax         ; Rs2 (MAP handler addr)
    mov     rdi, [r14 + 3*8]
    call    _decode_reg
    mov     r9, rax         ; Rs3 (DATA/default handler addr)
    ; push PC to call stack
    mov     rax, [r12 + CPU_CALL_TOP]
    cmp     rax, 255
    jge     .done_ok
    mov     rcx, [r12 + CPU_PC]
    mov     [r12 + CPU_CALL_STACK + rax*8], rcx
    inc     qword [r12 + CPU_CALL_TOP]
    ; save PC to LR
    mov     rdi, r12
    mov     rsi, REG_LR
    mov     rdx, rcx
    call    cpu_write_reg
    ; read Rd word
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_read_reg
    mov     r10, rax        ; r10 = word
    ; get primary field
    mov     rdi, r10
    mov     rsi, PRIMARY_LST
    mov     rdx, PRIMARY_WIDTH
    call    get_field_val
    ; dispatch
    cmp     rax, PRIMARY_EXEC
    jne     .tcall_map
    ; EXEC: jump to Rs1
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     [r12 + CPU_PC], rax
    jmp     .done_ok
.tcall_map:
    cmp     rax, PRIMARY_MAP
    jne     .tcall_default
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     [r12 + CPU_PC], rax
    jmp     .done_ok
.tcall_default:
    mov     rdi, r12
    mov     rsi, r9
    call    cpu_read_reg
    mov     [r12 + CPU_PC], rax
    jmp     .done_ok

    ; ── TNEW: Rd = alloc(Rs2 words), set primary from Rs1 ────────────────────
.op_tnew:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax        ; Rs1 (template word)
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax         ; Rs2 (size)
    ; read size
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     r8, rax
    cmp     r8, 1
    jge     .tnew_ok
    mov     r8, 1
.tnew_ok:
    ; alloc
    mov     rax, [r12 + CPU_HEAP_PTR]
    mov     r9, rax         ; r9 = allocated address
    add     rax, r8
    cmp     rax, MEMORY_SIZE
    jge     .done_ok        ; heap exhausted: no-op
    mov     [r12 + CPU_HEAP_PTR], rax
    ; get primary from Rs1
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     r10, rax        ; template word
    mov     rdi, r10
    mov     rsi, PRIMARY_LST
    mov     rdx, PRIMARY_WIDTH
    call    get_field_val
    mov     r10, rax        ; primary value
    ; set primary in address word
    mov     rdi, r9
    mov     rsi, PRIMARY_LST
    mov     rdx, PRIMARY_WIDTH
    mov     rcx, r10
    call    set_field_val
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── TBUILD: Rd = build_udp_word(0,0,Rs3,Rs1,Rs2) ─────────────────────────
.op_tbuild:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax        ; Rs1 (code_seg)
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax         ; Rs2 (data_seg)
    mov     rdi, [r14 + 3*8]
    call    _decode_reg
    mov     r9, rax         ; Rs3 (offset)
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax        ; code_seg value
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     r8, rax         ; data_seg value
    mov     rdi, r12
    mov     rsi, r9
    call    cpu_read_reg
    mov     r9, rax         ; offset value
    ; build UDP word: DATA primary, PTR_USER_DEF qualifier, payload encodes offset/code/data
    ; Simplified: just store offset in payload field
    mov     rdi, 0
    mov     rsi, PRIMARY_LST
    mov     rdx, PRIMARY_WIDTH
    mov     rcx, PRIMARY_DATA
    call    set_field_val
    mov     r10, rax
    ; set payload = offset (simplified)
    mov     rdi, r10
    mov     rsi, PAYLOAD_LST
    mov     rdx, PAYLOAD_WIDTH
    mov     rcx, r9
    call    set_field_val
    mov     rdx, rax
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── TSEG: Rd = resolve_exec(Rs1) if EXEC word, else Rs1 ──────────────────
.op_tseg:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     r8, rax         ; word
    ; get primary
    mov     rdi, r8
    mov     rsi, PRIMARY_LST
    mov     rdx, PRIMARY_WIDTH
    call    get_field_val
    cmp     rax, PRIMARY_EXEC
    jne     .tseg_passthrough
    ; resolve: CS[seg_idx] + offset
    ; simplified: get payload (offset) and add CS0
    mov     rdi, r8
    mov     rsi, PAYLOAD_LST
    mov     rdx, PAYLOAD_WIDTH
    call    get_field_val
    mov     r9, rax         ; offset
    mov     rdi, r12
    mov     rsi, REG_CS_BASE
    call    cpu_read_reg
    add     rax, r9
    mov     rdx, rax
    jmp     .tseg_write
.tseg_passthrough:
    mov     rdx, r8
.tseg_write:
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── RPOINT: canvas.append({POINT, pos, colour}) ──────────────────────────
.op_rpoint:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax        ; Rd (canvas index out)
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax        ; Rs1 (pos)
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax         ; Rs2 (colour word)
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     r9, rax         ; pos value
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     r10, rax        ; colour word
    ; get payload of colour word
    mov     rdi, r10
    mov     rsi, PAYLOAD_LST
    mov     rdx, PAYLOAD_WIDTH
    call    get_field_val
    mov     r10, rax        ; colour payload
    ; append to canvas
    mov     rbx, [r12 + CPU_CANVAS_CNT]
    lea     rax, [rel canvas_buf]
    ; compute entry base: rax + rbx*64
    mov     r11, rbx
    shl     r11, 6          ; r11 = rbx * 64
    add     r11, rax        ; r11 = canvas_buf + entry*64
    mov     qword [r11 + 0],  1    ; type=POINT
    mov     [r11 + 8],  r9          ; pos
    mov     [r11 + 16], r10         ; colour
    inc     qword [r12 + CPU_CANVAS_CNT]
    ; write canvas index to Rd
    mov     rdx, rbx
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── RLINE: canvas.append({LINE, start, end, style}) ──────────────────────
.op_rline:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, [r14 + 3*8]
    call    _decode_reg
    mov     r9, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, r9
    call    cpu_read_reg
    mov     r9, rax
    mov     rcx, [r12 + CPU_CANVAS_CNT]
    lea     rax, [rel canvas_buf]
    mov     r11, rcx
    shl     r11, 6
    add     r11, rax
    mov     qword [r11 + 0],  2
    mov     [r11 + 8],  rbx
    mov     [r11 + 16], r8
    mov     [r11 + 24], r9
    inc     qword [r12 + CPU_CANVAS_CNT]
    mov     rdx, rcx
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── RNODE: canvas.append({NODE, pos, dims, shape, object}) ───────────────
.op_rnode:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, [r14 + 3*8]
    call    _decode_reg
    mov     r9, rax
    mov     rdi, [r14 + 4*8]
    call    _decode_reg
    mov     r10, rax
    ; read registers
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax        ; pos
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     r8, rax         ; dims
    mov     rdi, r12
    mov     rsi, r9
    call    cpu_read_reg
    mov     r9, rax         ; shape word
    mov     rdi, r12
    mov     rsi, r10
    call    cpu_read_reg
    mov     r10, rax        ; object word
    mov     rcx, [r12 + CPU_CANVAS_CNT]
    lea     rax, [rel canvas_buf]
    mov     r11, rcx
    shl     r11, 6
    add     r11, rax
    mov     qword [r11 + 0],  3
    mov     [r11 + 8],  rbx
    mov     [r11 + 16], r8
    mov     [r11 + 24], r9
    mov     [r11 + 32], r10
    inc     qword [r12 + CPU_CANVAS_CNT]
    mov     rdx, rcx
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── REDGE: canvas.append({EDGE, src, dst, exec_word}) ────────────────────
.op_redge:
    mov     rdi, [r14 + 0*8]
    call    _decode_reg
    mov     rbp, rax
    mov     rdi, [r14 + 1*8]
    call    _decode_reg
    mov     rbx, rax
    mov     rdi, [r14 + 2*8]
    call    _decode_reg
    mov     r8, rax
    mov     rdi, [r14 + 3*8]
    call    _decode_reg
    mov     r9, rax
    mov     rdi, r12
    mov     rsi, rbx
    call    cpu_read_reg
    mov     rbx, rax
    mov     rdi, r12
    mov     rsi, r8
    call    cpu_read_reg
    mov     r8, rax
    mov     rdi, r12
    mov     rsi, r9
    call    cpu_read_reg
    mov     r9, rax
    mov     rcx, [r12 + CPU_CANVAS_CNT]
    lea     rax, [rel canvas_buf]
    mov     r11, rcx
    shl     r11, 6
    add     r11, rax
    mov     qword [r11 + 0],  4
    mov     [r11 + 8],  rbx
    mov     [r11 + 16], r8
    mov     [r11 + 24], r9
    inc     qword [r12 + CPU_CANVAS_CNT]
    mov     rdx, rcx
    mov     rdi, r12
    mov     rsi, rbp
    call    cpu_write_reg
    jmp     .done_ok

    ; ── RENDER: dump canvas to stdout ─────────────────────────────────────────
.op_render:
    mov     rdi, r12
    call    cpu_render_canvas
    jmp     .done_ok

.op_error:
    add     rsp, 64
    POP_CALLEE
    mov     rax, -2
    ret

.done_ok:
    inc     qword [r12 + CPU_CYCLES]
    add     rsp, 64
    POP_CALLEE
    xor     rax, rax
    ret

.done_halt:
    inc     qword [r12 + CPU_CYCLES]
    add     rsp, 64
    POP_CALLEE
    mov     rax, -1
    ret

; ── cpu_run ───────────────────────────────────────────────────────────────────
; Run the CPU until halted or max_cycles reached.
; Input:  rdi = CPU struct pointer
;         rsi = max_cycles (0 = unlimited / 1,000,000)
; Output: rax = cycle count
cpu_run:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    test    r13, r13
    jnz     .run_loop
    mov     r13, 1000000    ; default max
.run_loop:
    ; check halted
    cmp     qword [r12 + CPU_HALTED], 0
    jne     .run_done
    ; check cycle limit
    mov     rax, [r12 + CPU_CYCLES]
    cmp     rax, r13
    jge     .run_done
    ; fetch: rax = instruction word, PC already incremented
    mov     rdi, r12
    call    cpu_fetch
    mov     r15, rax        ; r15 = fetched instruction (preserved across calls)
    ; execute
    mov     rdi, r12
    mov     rsi, r15
    call    cpu_execute
    ; increment cycle counter
    inc     qword [r12 + CPU_CYCLES]
    jmp     .run_loop
.run_done:
    mov     rax, [r12 + CPU_CYCLES]
    POP_CALLEE
    ret

; ── cpu_render_canvas ─────────────────────────────────────────────────────────
; Print canvas entries to stdout (ASCII art).
; Input:  rdi = CPU struct pointer
cpu_render_canvas:
    PUSH_CALLEE
    mov     r12, rdi
    ; print header
    lea     rdi, [rel canvas_header]
    call    print_cstr
    mov     r13, 0          ; entry index
.loop:
    mov     rbx, [r12 + CPU_CANVAS_CNT]
    cmp     r13, rbx
    jge     .done
    lea     rax, [rel canvas_buf]
    mov     r11, r13
    shl     r11, 6
    add     r11, rax
    mov     rbx, [r11 + 0]  ; type
    cmp     rbx, 1
    je      .print_point
    cmp     rbx, 2
    je      .print_line
    cmp     rbx, 3
    je      .print_node
    cmp     rbx, 4
    je      .print_edge
    jmp     .next
.print_point:
    lea     rdi, [rel canvas_point_fmt]
    call    print_cstr
    lea     rax, [rel canvas_buf]
    mov     r11, r13
    shl     r11, 6
    add     r11, rax
    mov     rdi, [r11 + 8]
    call    print_int64
    call    print_newline
    jmp     .next
.print_line:
    lea     rdi, [rel canvas_line_fmt]
    call    print_cstr
    lea     rax, [rel canvas_buf]
    mov     r11, r13
    shl     r11, 6
    add     r11, rax
    mov     rdi, [r11 + 8]
    call    print_int64
    lea     rdi, [rel canvas_arrow]
    call    print_cstr
    lea     rax, [rel canvas_buf]
    mov     r11, r13
    shl     r11, 6
    add     r11, rax
    mov     rdi, [r11 + 16]
    call    print_int64
    call    print_newline
    jmp     .next
.print_node:
    lea     rdi, [rel canvas_node_fmt]
    call    print_cstr
    lea     rax, [rel canvas_buf]
    mov     r11, r13
    shl     r11, 6
    add     r11, rax
    mov     rdi, [r11 + 8]
    call    print_int64
    call    print_newline
    jmp     .next
.print_edge:
    lea     rdi, [rel canvas_edge_fmt]
    call    print_cstr
    lea     rax, [rel canvas_buf]
    mov     r11, r13
    shl     r11, 6
    add     r11, rax
    mov     rdi, [r11 + 8]
    call    print_int64
    lea     rdi, [rel canvas_arrow]
    call    print_cstr
    lea     rax, [rel canvas_buf]
    mov     r11, r13
    shl     r11, 6
    add     r11, rax
    mov     rdi, [r11 + 16]
    call    print_int64
    call    print_newline
.next:
    inc     r13
    jmp     .loop
.done:
    lea     rdi, [rel canvas_footer]
    call    print_cstr
    POP_CALLEE
    ret

; ── cpu_dump_regs ─────────────────────────────────────────────────────────────
; Print non-zero registers to stdout.
; Input:  rdi = CPU struct pointer
;         rsi = number of registers to print (0 = all 81)
cpu_dump_regs:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    test    r13, r13
    jnz     .dump_loop
    mov     r13, CPU_NUM_REGS
    ; print header
    lea     rdi, [rel reg_dump_hdr]
    call    print_cstr
    mov     r14, 0
.dump_loop:
    cmp     r14, r13
    jge     .dump_done
    mov     rdi, r12
    mov     rsi, r14
    call    cpu_read_reg
    test    rax, rax
    jz      .dump_next
    ; print "  R<n> = <val>"
    lea     rdi, [rel reg_prefix]
    call    print_cstr
    mov     rdi, r14
    call    print_int64
    lea     rdi, [rel reg_eq]
    call    print_cstr
    mov     rdi, rax
    call    print_int64
    call    print_newline
.dump_next:
    inc     r14
    jmp     .dump_loop
.dump_done:
    ; print PC and cycles
    lea     rdi, [rel reg_pc_label]
    call    print_cstr
    mov     rdi, [r12 + CPU_PC]
    call    print_int64
    lea     rdi, [rel reg_cycles_label]
    call    print_cstr
    mov     rdi, [r12 + CPU_CYCLES]
    call    print_int64
    call    print_newline
    POP_CALLEE
    ret

; ── I/O helpers ───────────────────────────────────────────────────────────────

; print_int64: print rdi as signed decimal to stdout
print_int64:
    PUSH_CALLEE
    mov     r12, rdi
    ; handle negative
    test    r12, r12
    jns     .positive
    ; print '-'
    mov     byte [rel int_buf], '-'
    lea     rdi, [rel int_buf]
    mov     rsi, 1
    mov     rdx, 1
    mov     rax, SYS_WRITE
    mov     rdi, STDOUT
    lea     rsi, [rel int_buf]
    syscall
    neg     r12
.positive:
    ; convert to decimal string (reversed)
    lea     r13, [rel int_buf + 20]
    mov     byte [r13], 0
    mov     r14, r12
    test    r14, r14
    jnz     .convert
    dec     r13
    mov     byte [r13], '0'
    jmp     .print_str
.convert:
    test    r14, r14
    jz      .print_str
    mov     rax, r14
    xor     rdx, rdx
    mov     rcx, 10
    div     rcx
    mov     r14, rax
    add     dl, '0'
    dec     r13
    mov     [r13], dl
    jmp     .convert
.print_str:
    ; compute length
    lea     rax, [rel int_buf + 20]
    sub     rax, r13
    mov     rdx, rax        ; length
    mov     rax, SYS_WRITE
    mov     rdi, STDOUT
    mov     rsi, r13
    syscall
    POP_CALLEE
    ret

; print_newline: print '\n' to stdout
print_newline:
    push    rax
    push    rdi
    push    rsi
    push    rdx
    mov     rax, SYS_WRITE
    mov     rdi, STDOUT
    lea     rsi, [rel newline_char]
    mov     rdx, 1
    syscall
    pop     rdx
    pop     rsi
    pop     rdi
    pop     rax
    ret

; print_cstr: print null-terminated string at rdi to stdout
print_cstr:
    push    rbx
    push    rcx
    push    rdx
    push    rsi
    push    rdi
    mov     rbx, rdi
    ; compute length
    xor     rcx, rcx
.len_loop:
    cmp     byte [rbx + rcx], 0
    je      .len_done
    inc     rcx
    jmp     .len_loop
.len_done:
    test    rcx, rcx
    jz      .cstr_done
    mov     rax, SYS_WRITE
    mov     rdi, STDOUT
    mov     rsi, rbx
    mov     rdx, rcx
    syscall
.cstr_done:
    pop     rdi
    pop     rsi
    pop     rdx
    pop     rcx
    pop     rbx
    ret

; read_int64: read a signed integer from stdin
; Output: rax = integer value
read_int64:
    push    rbx
    push    rcx
    push    rdx
    ; read up to 20 chars
    mov     rax, SYS_READ
    mov     rdi, STDIN
    lea     rsi, [rel int_buf]
    mov     rdx, 20
    syscall
    ; parse
    lea     rbx, [rel int_buf]
    xor     rcx, rcx        ; result
    xor     rdx, rdx        ; sign
    cmp     byte [rbx], '-'
    jne     .parse_loop
    mov     rdx, 1
    inc     rbx
.parse_loop:
    movzx   rax, byte [rbx]
    cmp     rax, '0'
    jl      .parse_done
    cmp     rax, '9'
    jg      .parse_done
    sub     rax, '0'
    imul    rcx, rcx, 10
    add     rcx, rax
    inc     rbx
    jmp     .parse_loop
.parse_done:
    test    rdx, rdx
    jz      .read_done
    neg     rcx
.read_done:
    mov     rax, rcx
    pop     rdx
    pop     rcx
    pop     rbx
    ret

section .data

; Memory pointer (set by cpu_init)
cpu_mem_ptr:    dq  0

; String constants
canvas_header:  db  0x0A, 0xE2, 0x95, 0x94, 0xE2, 0x95, 0x90, 0xE2, 0x95, 0x90, 0x20
                db  "CANVAS ", 0xE2, 0x95, 0x90, 0xE2, 0x95, 0x90, 0x0A, 0
canvas_footer:  db  0xE2, 0x95, 0x9A, 0xE2, 0x95, 0x90, 0xE2, 0x95, 0x90, 0xE2, 0x95, 0x90, 0x0A, 0
canvas_point_fmt: db "  POINT @", 0
canvas_line_fmt:  db "  LINE  ", 0
canvas_node_fmt:  db "  NODE  pos=", 0
canvas_edge_fmt:  db "  EDGE  ", 0
canvas_arrow:     db " --> ", 0
reg_dump_hdr:   db  0x0A, "-- Registers --", 0x0A, 0
reg_prefix:     db  "  R", 0
reg_eq:         db  " = ", 0
reg_pc_label:   db  "  PC=", 0
reg_cycles_label: db "  cycles=", 0
newline_char:   db  0x0A

section .bss
int_buf:        resb 32
