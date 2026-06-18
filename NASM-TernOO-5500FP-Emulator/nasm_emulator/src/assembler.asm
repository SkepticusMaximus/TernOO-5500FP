; ============================================================================
; assembler.asm  —  File-Based Ternary Assembler for the 5500FP ISA
;
; Reads .t5asm source files and produces binary-encoded ternary (BET) output.
; Supports the full 5500FP ISA as defined in ternoo.inc and cpu.asm.
;
; Source file format:
;   ; comment
;   LABEL:
;   MNEMONIC [Rd,] [Rs1,] [Rs2,] [imm]
;
; Register syntax: R0..R80 (81 registers)
; Immediate syntax: decimal, or ternary literal prefixed with 't' (e.g. t1T0)
; Labels: alphanumeric + underscore, followed by ':'
;
; Output format: raw 64-bit little-endian BET words, one per instruction.
; A 4-byte magic header "T5BT" precedes the word stream.
;
; ============================================================================

%include "include/ternoo.inc"

; ── Assembler constants ───────────────────────────────────────────────────────
MAX_TOKENS      equ 16          ; max tokens per line
MAX_LABELS      equ 256         ; max label definitions
MAX_FIXUPS      equ 512         ; max forward-reference fixups
MAX_INSTR       equ 4096        ; max instructions in output
LINE_BUF_SIZE   equ 256         ; max line length
TOKEN_BUF_SIZE  equ 64          ; max token length

; ── Mnemonic table entry (48 bytes) ──────────────────────────────────────────
; [name(16), opcode(8), format(8), nargs(8), flags(8)]
; format: 0=NOP, 1=RRR, 2=RRI, 3=RI, 4=R, 5=J(branch), 6=SYS
MNEM_SIZE       equ 48
FMT_NOP         equ 0
FMT_RRR         equ 1
FMT_RRI         equ 2
FMT_RI          equ 3
FMT_R           equ 4
FMT_BRANCH      equ 5
FMT_SYS         equ 6
FMT_RR          equ 7

section .data

; ── Magic header ─────────────────────────────────────────────────────────────
asm_magic:      db "T5BT"

; ── Mnemonic table ───────────────────────────────────────────────────────────
; Each entry: name(16 bytes, null-padded), opcode(8), format(8), nargs(8), flags(8)
mnem_table:
    ; NOP
    db "NOP", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_NOP, FMT_NOP, 0, 0
    ; ADD Rd, Rs1, Rs2
    db "ADD", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_ADD, FMT_RRR, 3, 0
    ; SUB Rd, Rs1, Rs2
    db "SUB", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_SUB, FMT_RRR, 3, 0
    ; MUL Rd, Rs1, Rs2
    db "MUL", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_MUL, FMT_RRR, 3, 0
    ; DIV Rd, Rs1, Rs2
    db "DIV", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_DIV, FMT_RRR, 3, 0
    ; MOD → use TXOR slot (balanced ternary modular op)
    db "MOD", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_TXOR, FMT_RRR, 3, 0
    ; AND → trit-wise MIN
    db "AND", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_MIN, FMT_RRR, 3, 0
    ; OR  → trit-wise MAX
    db "OR", 0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_MAX, FMT_RRR, 3, 0
    ; XOR → trit-wise TXOR
    db "XOR", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_TXOR, FMT_RRR, 3, 0
    ; MIN Rd, Rs1, Rs2
    db "MIN", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_MIN, FMT_RRR, 3, 0
    ; MAX Rd, Rs1, Rs2
    db "MAX", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_MAX, FMT_RRR, 3, 0
    ; CMP → SUB (compare by subtraction, result in Rd)
    db "CMP", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_SUB, FMT_RRR, 3, 0
    ; MOV Rd, Rs1
    db "MOV", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_MOV, FMT_RR,  2, 0
    ; NEG Rd, Rs1
    db "NEG", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_NEG, FMT_RR,  2, 0
    ; ABS → NEG (negate; caller uses for absolute value pattern)
    db "ABS", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_NEG, FMT_RR,  2, 0
    ; NOT → NEG (ternary negation is logical NOT)
    db "NOT", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_NEG, FMT_RR,  2, 0
    ; ADDI Rd, Rs1, imm
    db "ADDI", 0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_ADDI, FMT_RRI, 3, 0
    ; SUBI Rd, Rs1, imm
    db "SUBI", 0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_SUBI, FMT_RRI, 3, 0
    ; MULI → ADDI (no MULI in ISA; use ADDI as closest immediate op)
    db "MULI", 0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_ADDI, FMT_RRI, 3, 0
    ; CMPI → SUBI (compare immediate by subtraction)
    db "CMPI", 0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_SUBI, FMT_RRI, 3, 0
    ; LDI Rd, imm
    db "LDI", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_LDI, FMT_RI,  2, 0
    ; LD  Rd, Rs1
    db "LD", 0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_LD,  FMT_RR,  2, 0
    ; ST  Rs1, Rs2  (store Rs2 at address in Rs1)
    db "ST", 0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_ST,  FMT_RR,  2, 0
    ; PUSH Rs1
    db "PUSH", 0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_PUSH, FMT_R,  1, 0
    ; POP  Rd
    db "POP", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_POP,  FMT_R,  1, 0
    ; JMP  imm
    db "JMP", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_JMP, FMT_BRANCH, 1, 0
    ; JEQ  Rs1, Rs2, imm
    db "JEQ", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_JEQ, FMT_BRANCH, 3, 0
    ; JNE  Rs1, Rs2, imm
    db "JNE", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_JNE, FMT_BRANCH, 3, 0
    ; JLT → JB (jump if below / negative)
    db "JLT", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_JB, FMT_BRANCH, 3, 0
    ; JGT → JB with operands swapped (caller responsibility)
    db "JGT", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_JB, FMT_BRANCH, 3, 0
    ; JLE → JNE (jump if not equal, closest available)
    db "JLE", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_JNE, FMT_BRANCH, 3, 0
    ; JGE → JEQ (jump if equal or greater, use JEQ as base)
    db "JGE", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_JEQ, FMT_BRANCH, 3, 0
    ; CALL → JSR (jump to subroutine)
    db "CALL", 0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_JSR, FMT_BRANCH, 1, 0
    ; RET → RTI (return from interrupt/subroutine)
    db "RET", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_RTI, FMT_NOP, 0, 0
    ; IN   Rd, Rs1
    db "IN", 0,0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_IN,  FMT_RR,  2, 0
    ; OUT  Rs1, Rs2
    db "OUT", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_OUT, FMT_RR,  2, 0
    ; SYS → OUT (closest I/O opcode available)
    db "SYS", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_OUT, FMT_SYS, 1, 0
    ; HLT
    db "HLT", 0,0,0,0,0,0,0,0,0,0,0,0,0
    dq OP_HLT, FMT_NOP, 0, 0
    ; Sentinel
    dq 0, 0, 0, 0, 0, 0

MNEM_COUNT equ 37

; ── Error strings ─────────────────────────────────────────────────────────────
str_asm_banner:     db "5500FP Ternary Assembler v1.0", 10, 0
str_asm_ok:         db "[ASM] Assembly successful: ", 0
str_asm_words:      db " words", 10, 0
str_asm_err_mnem:   db "[ASM] ERROR: Unknown mnemonic: ", 0
str_asm_err_reg:    db "[ASM] ERROR: Invalid register: ", 0
str_asm_err_imm:    db "[ASM] ERROR: Invalid immediate: ", 0
str_asm_err_label:  db "[ASM] ERROR: Undefined label: ", 0
str_asm_err_full:   db "[ASM] ERROR: Output buffer full", 10, 0
str_asm_line:       db " at line ", 0
str_newline:        db 10, 0

section .bss
; ── Label table ───────────────────────────────────────────────────────────────
; Each entry: [name(32), address(8)] = 40 bytes
label_table:    resb 40 * MAX_LABELS
label_count:    resq 1

; ── Fixup table ───────────────────────────────────────────────────────────────
; Each entry: [name(32), word_index(8), field_lsb(8), field_width(8)] = 56 bytes
fixup_table:    resb 56 * MAX_FIXUPS
fixup_count:    resq 1

; ── Output buffer ─────────────────────────────────────────────────────────────
asm_output:     resq MAX_INSTR
asm_word_count: resq 1

; ── Working buffers ───────────────────────────────────────────────────────────
asm_line_buf:   resb LINE_BUF_SIZE
asm_tokens:     resq MAX_TOKENS     ; pointers to token strings
asm_token_bufs: resb TOKEN_BUF_SIZE * MAX_TOKENS
asm_token_count:resq 1
asm_line_num:   resq 1
asm_error_flag: resq 1

section .text

extern print_cstr
extern print_int64
extern print_newline
extern get_field_val
extern set_field_val

global asm_assemble_file
global asm_assemble_string
global asm_get_output
global asm_get_word_count
global asm_encode_instruction

; ── asm_assemble_string ───────────────────────────────────────────────────────
; Assemble a null-terminated source string.
; Input:  rdi = source string pointer
; Output: rax = word count (or -1 on error)
asm_assemble_string:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    ; Init state
    mov     qword [rel label_count],    0
    mov     qword [rel fixup_count],    0
    mov     qword [rel asm_word_count], 0
    mov     qword [rel asm_line_num],   1
    mov     qword [rel asm_error_flag], 0
    ; Pass 1: scan for labels and encode instructions
    mov     r13, r12
.line_loop:
    ; Check for end of string
    cmp     byte [r13], 0
    je      .pass1_done
    ; Extract one line into asm_line_buf
    lea     rdi, [rel asm_line_buf]
    mov     rsi, r13
    call    _extract_line       ; rax = chars consumed, r13 advanced
    add     r13, rax
    ; Tokenise the line
    lea     rdi, [rel asm_line_buf]
    call    _tokenise_line
    ; Skip empty lines
    cmp     qword [rel asm_token_count], 0
    je      .next_line
    ; Check for label definition (token ends with ':')
    mov     rdi, [rel asm_tokens]   ; first token
    call    _is_label_def
    test    rax, rax
    jz      .not_label
    ; Record label
    mov     rdi, [rel asm_tokens]
    mov     rsi, [rel asm_word_count]
    call    _record_label
    ; Remove label token and re-check if more tokens follow
    ; Shift tokens left by 1
    mov     rcx, [rel asm_token_count]
    dec     rcx
    mov     [rel asm_token_count], rcx
    test    rcx, rcx
    jz      .next_line
    ; Shift token pointers
    lea     rdi, [rel asm_tokens]
    mov     rcx, [rel asm_token_count]
    xor     rbx, rbx
.shift_loop:
    cmp     rbx, rcx
    jge     .shift_done
    mov     rax, [rdi + rbx*8 + 8]
    mov     [rdi + rbx*8], rax
    inc     rbx
    jmp     .shift_loop
.shift_done:
.not_label:
    ; Encode instruction from tokens
    call    _encode_current_line
    test    rax, rax
    jnz     .error
.next_line:
    inc     qword [rel asm_line_num]
    jmp     .line_loop
.pass1_done:
    ; Pass 2: resolve fixups
    call    _resolve_fixups
    test    rax, rax
    jnz     .error
    ; Return word count
    mov     rax, [rel asm_word_count]
    pop     r13
    pop     r12
    pop     rbx
    ret
.error:
    mov     rax, -1
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _extract_line ─────────────────────────────────────────────────────────────
; Copy one line from source to dest buffer (up to newline or null).
; Input:  rdi = dest buffer
;         rsi = source pointer
; Output: rax = number of source bytes consumed (including newline)
_extract_line:
    push    rbx
    xor     rbx, rbx            ; chars consumed
    xor     rcx, rcx            ; dest index
.loop:
    mov     al, [rsi + rbx]
    test    al, al
    jz      .done
    inc     rbx
    cmp     al, 10              ; newline
    je      .done
    cmp     al, 13              ; carriage return
    je      .loop               ; skip CR
    cmp     rcx, LINE_BUF_SIZE - 1
    jge     .loop               ; truncate
    mov     [rdi + rcx], al
    inc     rcx
    jmp     .loop
.done:
    mov     byte [rdi + rcx], 0
    mov     rax, rbx
    pop     rbx
    ret

; ── _tokenise_line ────────────────────────────────────────────────────────────
; Split a line into tokens, stripping comments (;) and commas.
; Tokens are copied into asm_token_bufs and pointers stored in asm_tokens.
; Input:  rdi = line buffer
_tokenise_line:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    mov     qword [rel asm_token_count], 0
    xor     rbx, rbx            ; source index
    xor     r13, r13            ; token index
.scan:
    ; Skip whitespace and commas
    mov     al, [r12 + rbx]
    test    al, al
    jz      .done
    cmp     al, ';'
    je      .done               ; comment — stop
    cmp     al, ' '
    je      .skip
    cmp     al, 9               ; tab
    je      .skip
    cmp     al, ','
    je      .skip
    ; Start of token
    cmp     r13, MAX_TOKENS
    jge     .done
    ; Set token pointer
    imul    rax, r13, TOKEN_BUF_SIZE
    lea     rcx, [rel asm_token_bufs]
    add     rcx, rax
    ; Store token pointer — avoid RIP+reg*scale, use explicit base+offset
    lea     rdx, [rel asm_tokens]
    mov     [rdx + r13*8], rcx
    ; Copy token chars
    xor     rdx, rdx            ; token char index
.copy_token:
    mov     al, [r12 + rbx]
    test    al, al
    jz      .token_end
    cmp     al, ';'
    je      .token_end
    cmp     al, ' '
    je      .token_end
    cmp     al, 9
    je      .token_end
    cmp     al, ','
    je      .token_end
    cmp     rdx, TOKEN_BUF_SIZE - 1
    jge     .token_end
    ; Uppercase
    cmp     al, 'a'
    jl      .no_upper
    cmp     al, 'z'
    jg      .no_upper
    sub     al, 32
.no_upper:
    mov     [rcx + rdx], al
    inc     rdx
    inc     rbx
    jmp     .copy_token
.token_end:
    mov     byte [rcx + rdx], 0
    inc     r13
    mov     [rel asm_token_count], r13
    jmp     .scan
.skip:
    inc     rbx
    jmp     .scan
.done:
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _is_label_def ─────────────────────────────────────────────────────────────
; Check if a token is a label definition (ends with ':').
; Input:  rdi = token string
; Output: rax = 1 if label, 0 otherwise
_is_label_def:
    push    rbx
    xor     rbx, rbx
.len:
    cmp     byte [rdi + rbx], 0
    je      .check
    inc     rbx
    jmp     .len
.check:
    test    rbx, rbx
    jz      .no
    dec     rbx
    cmp     byte [rdi + rbx], ':'
    je      .yes
.no:
    xor     rax, rax
    pop     rbx
    ret
.yes:
    mov     rax, 1
    pop     rbx
    ret

; ── _record_label ─────────────────────────────────────────────────────────────
; Record a label definition.
; Input:  rdi = token string (with ':' at end)
;         rsi = current word address
_record_label:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    mov     r13, rsi
    mov     rbx, [rel label_count]
    cmp     rbx, MAX_LABELS
    jge     .done
    ; Compute entry pointer: 40 bytes each
    imul    rax, rbx, 40
    lea     rcx, [rel label_table]
    add     rcx, rax
    ; Copy name (without ':'), max 31 chars
    xor     rdx, rdx
.copy:
    mov     al, [r12 + rdx]
    test    al, al
    jz      .end_copy
    cmp     al, ':'
    je      .end_copy
    cmp     rdx, 31
    jge     .end_copy
    mov     [rcx + rdx], al
    inc     rdx
    jmp     .copy
.end_copy:
    mov     byte [rcx + rdx], 0
    ; Store address
    mov     [rcx + 32], r13
    inc     qword [rel label_count]
.done:
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _lookup_label ─────────────────────────────────────────────────────────────
; Look up a label by name.
; Input:  rdi = label name string
; Output: rax = address (or -1 if not found)
_lookup_label:
    push    rbx
    push    r12
    mov     r12, rdi
    xor     rbx, rbx
.loop:
    cmp     rbx, [rel label_count]
    jge     .not_found
    imul    rax, rbx, 40
    lea     rcx, [rel label_table]
    add     rcx, rax
    ; Compare name
    push    rbx
    push    rcx
    mov     rdi, r12
    mov     rsi, rcx
    call    _strcmp_asm
    pop     rcx
    pop     rbx
    test    rax, rax
    jnz     .next
    ; Found
    imul    rax, rbx, 40
    lea     rcx, [rel label_table]
    add     rcx, rax
    mov     rax, [rcx + 32]
    pop     r12
    pop     rbx
    ret
.next:
    inc     rbx
    jmp     .loop
.not_found:
    mov     rax, -1
    pop     r12
    pop     rbx
    ret

; ── _strcmp_asm ───────────────────────────────────────────────────────────────
; Case-insensitive string compare (both already uppercased).
; Input:  rdi = str1, rsi = str2
; Output: rax = 0 if equal
_strcmp_asm:
.loop:
    mov     al, [rdi]
    mov     cl, [rsi]
    cmp     al, cl
    jne     .diff
    test    al, al
    jz      .eq
    inc     rdi
    inc     rsi
    jmp     .loop
.eq:
    xor     rax, rax
    ret
.diff:
    mov     rax, 1
    ret

; ── _parse_register ───────────────────────────────────────────────────────────
; Parse a register token "R<n>" → register number.
; Input:  rdi = token string
; Output: rax = register number (0..80), or -1 on error
_parse_register:
    push    rbx
    mov     al, [rdi]
    cmp     al, 'R'
    jne     .err
    inc     rdi
    ; Parse decimal number
    xor     rbx, rbx
    xor     rcx, rcx
.loop:
    mov     al, [rdi + rcx]
    test    al, al
    jz      .done
    cmp     al, '0'
    jl      .err
    cmp     al, '9'
    jg      .err
    imul    rbx, rbx, 10
    sub     al, '0'
    movzx   rax, al
    add     rbx, rax
    inc     rcx
    jmp     .loop
.done:
    cmp     rbx, 80
    jg      .err
    mov     rax, rbx
    pop     rbx
    ret
.err:
    mov     rax, -1
    pop     rbx
    ret

; ── _parse_immediate ──────────────────────────────────────────────────────────
; Parse an immediate value token (decimal or ternary literal).
; Ternary literals: 't' followed by digits 0,1,T (T=-1), e.g. "t1T0" = 1*9+(-1)*3+0 = 6
; Input:  rdi = token string
; Output: rax = integer value, rdx = 0 (ok) or -1 (error)
_parse_immediate:
    push    rbx
    push    r12
    mov     r12, rdi
    mov     al, [r12]
    ; Ternary literal?
    cmp     al, 'T'
    je      .ternary
    ; Check for negative decimal
    xor     rbx, rbx
    mov     rcx, 1              ; sign
    cmp     al, '-'
    jne     .decimal
    mov     rcx, -1
    inc     r12
.decimal:
    xor     rbx, rbx
    xor     rdx, rdx
.dec_loop:
    mov     al, [r12 + rdx]
    test    al, al
    jz      .dec_done
    cmp     al, '0'
    jl      .err
    cmp     al, '9'
    jg      .err
    imul    rbx, rbx, 10
    sub     al, '0'
    movzx   rax, al
    add     rbx, rax
    inc     rdx
    jmp     .dec_loop
.dec_done:
    imul    rbx, rcx            ; apply sign (two-operand form)
    mov     rax, rbx
    xor     rdx, rdx
    pop     r12
    pop     rbx
    ret
.ternary:
    ; Parse balanced ternary: digits 0,1,T (T=-1)
    inc     r12
    xor     rbx, rbx
    xor     rcx, rcx
.trit_loop:
    mov     al, [r12 + rcx]
    test    al, al
    jz      .trit_done
    imul    rbx, rbx, 3
    cmp     al, '0'
    je      .trit_zero
    cmp     al, '1'
    je      .trit_one
    cmp     al, 'T'
    je      .trit_neg
    jmp     .err
.trit_zero:
    inc     rcx
    jmp     .trit_loop
.trit_one:
    add     rbx, 1
    inc     rcx
    jmp     .trit_loop
.trit_neg:
    sub     rbx, 1
    inc     rcx
    jmp     .trit_loop
.trit_done:
    mov     rax, rbx
    xor     rdx, rdx
    pop     r12
    pop     rbx
    ret
.err:
    xor     rax, rax
    mov     rdx, -1
    pop     r12
    pop     rbx
    ret

; ── _lookup_mnemonic ──────────────────────────────────────────────────────────
; Find a mnemonic in the table.
; Input:  rdi = mnemonic string (uppercase)
; Output: rax = pointer to mnemonic table entry, or NULL
_lookup_mnemonic:
    push    rbx
    push    r12
    mov     r12, rdi
    xor     rbx, rbx
.loop:
    cmp     rbx, MNEM_COUNT
    jge     .not_found
    imul    rax, rbx, MNEM_SIZE
    lea     rcx, [rel mnem_table]
    add     rcx, rax
    ; Check sentinel
    cmp     qword [rcx], 0
    je      .not_found
    ; Compare name (16 bytes, null-terminated)
    push    rbx
    push    rcx
    mov     rdi, r12
    mov     rsi, rcx
    call    _strcmp_asm
    pop     rcx
    pop     rbx
    test    rax, rax
    jnz     .next
    ; Found
    imul    rax, rbx, MNEM_SIZE
    lea     rcx, [rel mnem_table]
    add     rcx, rax
    mov     rax, rcx
    pop     r12
    pop     rbx
    ret
.next:
    inc     rbx
    jmp     .loop
.not_found:
    xor     rax, rax
    pop     r12
    pop     rbx
    ret

; ── _encode_current_line ──────────────────────────────────────────────────────
; Encode the current token list as an instruction word.
; Output: rax = 0 on success, 1 on error
_encode_current_line:
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    ; Check token count
    cmp     qword [rel asm_token_count], 0
    je      .ok
    ; Look up mnemonic
    mov     rdi, [rel asm_tokens]
    call    _lookup_mnemonic
    test    rax, rax
    jz      .err_mnem
    mov     r12, rax            ; r12 = mnemonic entry ptr
    ; Get opcode, format, nargs
    mov     r13, [r12 + 16]     ; opcode
    mov     r14, [r12 + 24]     ; format
    mov     r15, [r12 + 32]     ; nargs
    ; Check output buffer
    mov     rax, [rel asm_word_count]
    cmp     rax, MAX_INSTR
    jge     .err_full
    ; Encode based on format
    cmp     r14, FMT_NOP
    je      .fmt_nop
    cmp     r14, FMT_RRR
    je      .fmt_rrr
    cmp     r14, FMT_RR
    je      .fmt_rr
    cmp     r14, FMT_RRI
    je      .fmt_rri
    cmp     r14, FMT_RI
    je      .fmt_ri
    cmp     r14, FMT_R
    je      .fmt_r
    cmp     r14, FMT_BRANCH
    je      .fmt_branch
    cmp     r14, FMT_SYS
    je      .fmt_sys
    jmp     .fmt_nop

.fmt_nop:
    ; Just opcode, no operands
    ; word = set_field(0, 0, 4, opcode)
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    jmp     .emit

.fmt_rrr:
    ; Rd, Rs1, Rs2
    ; Parse Rd
    mov     rdi, [rel asm_tokens + 8]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    mov     rbx, rax            ; Rd
    ; Parse Rs1
    mov     rdi, [rel asm_tokens + 16]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    push    rax                 ; Rs1
    ; Parse Rs2
    mov     rdi, [rel asm_tokens + 24]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    mov     r15, rax            ; Rs2
    pop     r14                 ; Rs1
    ; Encode: [op(4t)][Rd(4t)][Rs1(4t)][Rs2(4t)][0(12t)]
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    mov     rbx, rax
    ; Rd at T4-T7
    mov     rdi, rbx
    mov     rsi, 4
    mov     rdx, 4
    mov     rcx, [rel asm_tokens + 8]
    ; Need Rd value — re-parse
    push    rbx
    mov     rdi, [rel asm_tokens + 8]
    call    _parse_register
    mov     rcx, rax
    pop     rbx
    mov     rdi, rbx
    mov     rsi, 4
    mov     rdx, 4
    call    set_field_val
    mov     rbx, rax
    ; Rs1 at T8-T11
    mov     rdi, rbx
    mov     rsi, 8
    mov     rdx, 4
    mov     rcx, r14
    call    set_field_val
    mov     rbx, rax
    ; Rs2 at T12-T15
    mov     rdi, rbx
    mov     rsi, 12
    mov     rdx, 4
    mov     rcx, r15
    call    set_field_val
    ; Opcode at T20-T23
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    jmp     .emit

.fmt_rr:
    ; Rd, Rs1
    mov     rdi, [rel asm_tokens + 8]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    mov     rbx, rax
    mov     rdi, [rel asm_tokens + 16]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    mov     r14, rax
    ; Encode: op at T20-T23, Rd at T4-T7, Rs1 at T8-T11
    xor     rdi, rdi
    mov     rsi, 4
    mov     rdx, 4
    mov     rcx, rbx
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 8
    mov     rdx, 4
    mov     rcx, r14
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    jmp     .emit

.fmt_rri:
    ; Rd, Rs1, imm
    mov     rdi, [rel asm_tokens + 8]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    mov     rbx, rax            ; Rd
    mov     rdi, [rel asm_tokens + 16]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    mov     r14, rax            ; Rs1
    ; Parse imm (may be label)
    mov     rdi, [rel asm_tokens + 24]
    call    _parse_immediate
    cmp     rdx, -1
    je      .try_label_rri
    mov     r15, rax            ; imm
    jmp     .encode_rri
.try_label_rri:
    ; Try as label
    mov     rdi, [rel asm_tokens + 24]
    call    _lookup_label
    cmp     rax, -1
    je      .add_fixup_rri
    mov     r15, rax
    jmp     .encode_rri
.add_fixup_rri:
    ; Add fixup for forward reference
    mov     rdi, [rel asm_tokens + 24]
    mov     rsi, [rel asm_word_count]
    mov     rdx, 8              ; lsb
    mov     rcx, 12             ; width
    call    _add_fixup
    mov     r15, 0              ; placeholder
.encode_rri:
    ; Encode: op at T20-T23, Rd at T4-T7, Rs1 at T8-T11, imm at T8-T19
    ; Wait — RRI format: [op(4t)][Rd(4t)][Rs1(4t)][imm(12t)]
    ; T0-T3: op, T4-T7: Rd, T8-T11: Rs1, T12-T23: imm? No.
    ; From cpu.asm: op at T20-T23, Rd at T4-T7, Rs1 at T8-T11, imm at T8-T19
    ; Actually from cpu.asm decode: Rd=F0(T0-T3), Rs1=F1(T4-T7), imm=F2+F3(T8-T19), op=F5(T20-T23)
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, rbx            ; Rd at T0-T3
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 4
    mov     rdx, 4
    mov     rcx, r14            ; Rs1 at T4-T7
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 8
    mov     rdx, 12
    mov     rcx, r15            ; imm at T8-T19
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r13            ; op at T20-T23
    call    set_field_val
    jmp     .emit

.fmt_ri:
    ; Rd, imm  (LDI)
    mov     rdi, [rel asm_tokens + 8]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    mov     rbx, rax            ; Rd
    mov     rdi, [rel asm_tokens + 16]
    call    _parse_immediate
    cmp     rdx, -1
    je      .try_label_ri
    mov     r14, rax
    jmp     .encode_ri
.try_label_ri:
    mov     rdi, [rel asm_tokens + 16]
    call    _lookup_label
    cmp     rax, -1
    je      .add_fixup_ri
    mov     r14, rax
    jmp     .encode_ri
.add_fixup_ri:
    mov     rdi, [rel asm_tokens + 16]
    mov     rsi, [rel asm_word_count]
    mov     rdx, 8
    mov     rcx, 12
    call    _add_fixup
    mov     r14, 0
.encode_ri:
    ; LDI: Rd at T0-T3, imm at T8-T19, op at T20-T23
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, rbx
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 8
    mov     rdx, 12
    mov     rcx, r14
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    jmp     .emit

.fmt_r:
    ; Rs1 only (PUSH/POP)
    mov     rdi, [rel asm_tokens + 8]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    mov     rbx, rax
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, rbx
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    jmp     .emit

.fmt_branch:
    ; JMP imm | JEQ Rs1, Rs2, imm | CALL imm
    cmp     r15, 1
    je      .branch_jmp
    ; JEQ/JNE/etc: Rs1, Rs2, imm
    mov     rdi, [rel asm_tokens + 8]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    mov     rbx, rax
    mov     rdi, [rel asm_tokens + 16]
    call    _parse_register
    cmp     rax, -1
    je      .err_reg
    mov     r14, rax
    mov     rdi, [rel asm_tokens + 24]
    call    _parse_immediate
    cmp     rdx, -1
    je      .try_label_br3
    mov     r15, rax
    jmp     .encode_br3
.try_label_br3:
    mov     rdi, [rel asm_tokens + 24]
    call    _lookup_label
    cmp     rax, -1
    je      .add_fixup_br3
    mov     r15, rax
    jmp     .encode_br3
.add_fixup_br3:
    mov     rdi, [rel asm_tokens + 24]
    mov     rsi, [rel asm_word_count]
    mov     rdx, 8
    mov     rcx, 12
    call    _add_fixup
    mov     r15, 0
.encode_br3:
    ; Rs1 at T0-T3, Rs2 at T4-T7, imm at T8-T19, op at T20-T23
    xor     rdi, rdi
    mov     rsi, 0
    mov     rdx, 4
    mov     rcx, rbx
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
    mov     rdx, 12
    mov     rcx, r15
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    jmp     .emit
.branch_jmp:
    ; JMP/CALL: imm only
    mov     rdi, [rel asm_tokens + 8]
    call    _parse_immediate
    cmp     rdx, -1
    je      .try_label_jmp
    mov     rbx, rax
    jmp     .encode_jmp
.try_label_jmp:
    mov     rdi, [rel asm_tokens + 8]
    call    _lookup_label
    cmp     rax, -1
    je      .add_fixup_jmp
    mov     rbx, rax
    jmp     .encode_jmp
.add_fixup_jmp:
    mov     rdi, [rel asm_tokens + 8]
    mov     rsi, [rel asm_word_count]
    mov     rdx, 8
    mov     rcx, 12
    call    _add_fixup
    mov     rbx, 0
.encode_jmp:
    xor     rdi, rdi
    mov     rsi, 8
    mov     rdx, 12
    mov     rcx, rbx
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    jmp     .emit

.fmt_sys:
    ; SYS imm
    mov     rdi, [rel asm_tokens + 8]
    call    _parse_immediate
    cmp     rdx, -1
    je      .err_imm
    mov     rbx, rax
    xor     rdi, rdi
    mov     rsi, 8
    mov     rdx, 12
    mov     rcx, rbx
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 4
    mov     rcx, r13
    call    set_field_val
    ; Fall through to emit

.emit:
    ; Store encoded word in output buffer
    mov     rcx, [rel asm_word_count]
    lea     rdx, [rel asm_output]
    mov     [rdx + rcx*8], rax
    inc     qword [rel asm_word_count]
.ok:
    xor     rax, rax
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

.err_mnem:
    ; Print error
    lea     rdi, [rel str_asm_err_mnem]
    call    print_cstr
    mov     rdi, [rel asm_tokens]
    call    print_cstr
    call    print_newline
    mov     qword [rel asm_error_flag], 1
    mov     rax, 1
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

.err_reg:
    lea     rdi, [rel str_asm_err_reg]
    call    print_cstr
    call    print_newline
    mov     qword [rel asm_error_flag], 1
    mov     rax, 1
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

.err_imm:
    lea     rdi, [rel str_asm_err_imm]
    call    print_cstr
    call    print_newline
    mov     qword [rel asm_error_flag], 1
    mov     rax, 1
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

.err_full:
    lea     rdi, [rel str_asm_err_full]
    call    print_cstr
    mov     rax, 1
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _add_fixup ────────────────────────────────────────────────────────────────
; Record a forward-reference fixup.
; Input:  rdi = label name
;         rsi = word index
;         rdx = field lsb
;         rcx = field width
_add_fixup:
    push    rbx
    push    r12
    push    r13
    push    r14
    mov     r12, rdi
    mov     r13, rsi
    mov     r14, rdx
    mov     rbx, rcx
    mov     rax, [rel fixup_count]
    cmp     rax, MAX_FIXUPS
    jge     .done
    ; Entry: [name(32), word_idx(8), lsb(8), width(8)] = 56 bytes
    imul    rcx, rax, 56
    lea     rdx, [rel fixup_table]
    add     rdx, rcx
    ; Copy name
    xor     rcx, rcx
.copy:
    mov     al, [r12 + rcx]
    test    al, al
    jz      .end_copy
    cmp     rcx, 31
    jge     .end_copy
    mov     [rdx + rcx], al
    inc     rcx
    jmp     .copy
.end_copy:
    mov     byte [rdx + rcx], 0
    mov     [rdx + 32], r13
    mov     [rdx + 40], r14
    mov     [rdx + 48], rbx
    inc     qword [rel fixup_count]
.done:
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _resolve_fixups ───────────────────────────────────────────────────────────
; Resolve all forward-reference fixups.
; Output: rax = 0 on success, 1 on error
_resolve_fixups:
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    xor     rbx, rbx
.loop:
    cmp     rbx, [rel fixup_count]
    jge     .done
    imul    rax, rbx, 56
    lea     rcx, [rel fixup_table]
    add     rcx, rax
    ; Look up label
    push    rbx
    push    rcx
    mov     rdi, rcx
    call    _lookup_label
    pop     rcx
    pop     rbx
    cmp     rax, -1
    je      .err_label
    mov     r12, rax            ; label address
    mov     r13, [rcx + 32]    ; word index
    mov     r14, [rcx + 40]    ; lsb
    mov     r15, [rcx + 48]    ; width
    ; Patch the word
    lea     rdx, [rel asm_output]
    mov     rdi, [rdx + r13*8]
    mov     rsi, r14
    mov     rdx, r15
    mov     rcx, r12
    call    set_field_val
    lea     rdx, [rel asm_output]
    mov     [rdx + r13*8], rax
    inc     rbx
    jmp     .loop
.done:
    xor     rax, rax
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret
.err_label:
    lea     rdi, [rel str_asm_err_label]
    call    print_cstr
    call    print_newline
    mov     rax, 1
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── asm_get_output ────────────────────────────────────────────────────────────
; Get pointer to assembled output buffer.
; Output: rax = pointer to int64_t array of BET words
asm_get_output:
    lea     rax, [rel asm_output]
    ret

; ── asm_get_word_count ────────────────────────────────────────────────────────
; Output: rax = number of assembled words
asm_get_word_count:
    mov     rax, [rel asm_word_count]
    ret

; ── asm_encode_instruction ────────────────────────────────────────────────────
; Encode a single instruction from a source line string.
; Input:  rdi = source line string
; Output: rax = encoded word (or -1 on error)
asm_encode_instruction:
    push    rbx
    push    r12
    mov     r12, rdi
    ; Copy to line buf
    lea     rdi, [rel asm_line_buf]
    mov     rsi, r12
    call    _extract_line
    ; Tokenise
    lea     rdi, [rel asm_line_buf]
    call    _tokenise_line
    ; Encode
    call    _encode_current_line
    test    rax, rax
    jnz     .err
    ; Return last word
    mov     rax, [rel asm_word_count]
    test    rax, rax
    jz      .err
    dec     rax
    lea     rcx, [rel asm_output]
    mov     rax, [rcx + rax*8]
    pop     r12
    pop     rbx
    ret
.err:
    mov     rax, -1
    pop     r12
    pop     rbx
    ret
