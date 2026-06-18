; ============================================================================
; trit.asm  —  Binary-encoded ternary arithmetic primitives
;
; All functions use the System V AMD64 ABI.
; A 24-trit word is stored as a 64-bit signed integer in balanced ternary:
;   value = sum(trit[i] * 3^i, i=0..23)  where trit[i] ∈ {−1, 0, +1}
;
; The BET (binary-encoded ternary) representation packs trits into a 64-bit
; integer using 2 bits per trit:
;   00 → 0,  01 → +1,  10 → −1
; Trit 0 occupies bits [1:0], trit 23 occupies bits [47:46].
;
; Conversion between balanced-ternary integer and BET is done by
; to_bet / from_bet.  All internal CPU state uses balanced ternary integers
; (int64_t) for arithmetic speed; BET is used only for instruction encoding
; and word-format field extraction.
; ============================================================================

%include "include/ternoo.inc"

section .data

; Powers of 3 table: pow3[i] = 3^i for i=0..24
pow3_table:
    dq  1                   ; 3^0
    dq  3                   ; 3^1
    dq  9                   ; 3^2
    dq  27                  ; 3^3
    dq  81                  ; 3^4
    dq  243                 ; 3^5
    dq  729                 ; 3^6
    dq  2187                ; 3^7
    dq  6561                ; 3^8
    dq  19683               ; 3^9
    dq  59049               ; 3^10
    dq  177147              ; 3^11
    dq  531441              ; 3^12
    dq  1594323             ; 3^13
    dq  4782969             ; 3^14
    dq  14348907            ; 3^15
    dq  43046721            ; 3^16
    dq  129140163           ; 3^17
    dq  387420489           ; 3^18
    dq  1162261467          ; 3^19
    dq  3486784401          ; 3^20
    dq  10460353203         ; 3^21
    dq  31381059609         ; 3^22
    dq  94143178827         ; 3^23
    dq  282429536481        ; 3^24

section .text

global clamp_word
global to_bet
global from_bet
global get_trit_val
global set_trit_val
global get_field_val
global set_field_val
global trit_min_word
global trit_max_word
global trit_txor_word
global trit_equal_word
global trit_sum_word
global word_to_str

; ── clamp_word ───────────────────────────────────────────────────────────────
; Clamp a 64-bit signed integer to the 24-trit balanced ternary range.
; Input:  rdi = value
; Output: rax = clamped value
clamp_word:
    mov     rax, rdi
    mov     rcx, WORD_MAX
    cmp     rax, rcx
    jle     .check_min
    mov     rax, rcx
    ret
.check_min:
    mov     rcx, WORD_MIN
    cmp     rax, rcx
    jge     .done
    mov     rax, rcx
.done:
    ret

; ── to_bet ───────────────────────────────────────────────────────────────────
; Convert a balanced ternary integer to BET (binary-encoded ternary).
; Input:  rdi = balanced ternary integer value
;         rsi = number of trits to encode (1..24)
; Output: rax = BET-encoded value (2 bits per trit, trit 0 in bits [1:0])
;
; Algorithm: for each trit position i from 0 to width-1:
;   r = value % 3  (balanced: if r==2 → r=-1, adjust value)
;   encode r into 2 bits: 0→00, +1→01, -1→10
;   shift into position 2*i
to_bet:
    PUSH_CALLEE
    mov     r12, rdi        ; r12 = value (working copy)
    mov     r13, rsi        ; r13 = width
    xor     r14, r14        ; r14 = result BET accumulator
    xor     r15, r15        ; r15 = bit position (2*i)

.loop:
    test    r13, r13
    jz      .done

    ; compute r = r12 % 3  (signed modulo, balanced)
    mov     rax, r12
    mov     rcx, 3
    cqo                     ; sign-extend rax into rdx:rax
    idiv    rcx             ; rax = quotient, rdx = remainder
    ; rdx is in {-2,-1,0,1,2}
    ; balanced adjustment: if rdx == 2 → rdx=-1, rax+=1
    ;                       if rdx ==-2 → rdx=+1, rax-=1
    cmp     rdx, 2
    jne     .check_neg2
    mov     rdx, -1
    inc     rax
    jmp     .encode
.check_neg2:
    cmp     rdx, -2
    jne     .encode
    mov     rdx, 1
    dec     rax
.encode:
    ; rdx ∈ {-1, 0, +1} — encode into 2 bits
    ; 0→0, +1→1, -1→2
    mov     r12, rax        ; update working value = quotient
    ; encode rdx
    xor     rbx, rbx
    cmp     rdx, 0
    je      .bit_zero
    cmp     rdx, 1
    je      .bit_pos
    ; must be -1
    mov     rbx, 2          ; TRIT_NEG = 2
    jmp     .shift
.bit_pos:
    mov     rbx, 1          ; TRIT_POS = 1
    jmp     .shift
.bit_zero:
    ; rbx already 0
.shift:
    ; shift rbx into position r15 in r14
    mov     rcx, r15
    shl     rbx, cl
    or      r14, rbx

    add     r15, 2          ; advance bit position by 2
    dec     r13
    jmp     .loop

.done:
    mov     rax, r14
    POP_CALLEE
    ret

; ── from_bet ─────────────────────────────────────────────────────────────────
; Convert BET to balanced ternary integer.
; Input:  rdi = BET value
;         rsi = number of trits to decode (1..24)
; Output: rax = balanced ternary integer
;
; Algorithm: for each trit position i from 0 to width-1:
;   bits = (bet >> (2*i)) & 3
;   trit = 0 if bits==0, +1 if bits==1, -1 if bits==2
;   result += trit * 3^i
from_bet:
    PUSH_CALLEE
    mov     r12, rdi        ; r12 = BET value
    mov     r13, rsi        ; r13 = width
    xor     r14, r14        ; r14 = result
    xor     r15, r15        ; r15 = trit index i

.loop:
    cmp     r15, r13
    jge     .done

    ; extract 2-bit trit slot
    mov     rax, r12
    mov     rcx, r15
    shl     rcx, 1          ; bit position = 2*i
    sar     rax, cl
    and     rax, 3          ; rax = 2-bit encoding

    ; decode to trit value in rbx
    xor     rbx, rbx
    cmp     rax, 1
    je      .is_pos
    cmp     rax, 2
    je      .is_neg
    jmp     .mul            ; rax==0 → trit=0, rbx=0
.is_pos:
    mov     rbx, 1
    jmp     .mul
.is_neg:
    mov     rbx, -1

.mul:
    ; result += rbx * pow3[i]
    lea     rax, [rel pow3_table]
    mov     rcx, r15
    shl     rcx, 3          ; index * 8 (qword)
    mov     rax, [rax + rcx]
    imul    rax, rbx
    add     r14, rax

    inc     r15
    jmp     .loop

.done:
    mov     rax, r14
    POP_CALLEE
    ret

; ── get_trit_val ─────────────────────────────────────────────────────────────
; Extract a single trit from a balanced ternary integer.
; Input:  rdi = word value (balanced ternary integer)
;         rsi = trit position (0..23)
; Output: rax = trit value ∈ {-1, 0, +1}
get_trit_val:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    ; Convert to BET, then extract
    mov     rdi, r12
    mov     rsi, WORD_TRITS
    call    to_bet
    ; extract 2-bit slot at position r13
    mov     rcx, r13
    shl     rcx, 1
    sar     rax, cl
    and     rax, 3
    ; decode
    cmp     rax, 1
    je      .pos
    cmp     rax, 2
    je      .neg
    xor     rax, rax        ; 0
    jmp     .done
.pos:
    mov     rax, 1
    jmp     .done
.neg:
    mov     rax, -1
.done:
    POP_CALLEE
    ret

; ── set_trit_val ─────────────────────────────────────────────────────────────
; Set a single trit in a balanced ternary integer.
; Input:  rdi = word value
;         rsi = trit position (0..23)
;         rdx = new trit value ∈ {-1, 0, +1}
; Output: rax = modified word value
set_trit_val:
    PUSH_CALLEE
    mov     r12, rdi        ; r12 = word
    mov     r13, rsi        ; r13 = position
    mov     r14, rdx        ; r14 = new trit value
    ; convert to BET
    mov     rdi, r12
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r15, rax        ; r15 = BET
    ; clear 2-bit slot at position r13
    mov     rcx, r13
    shl     rcx, 1          ; bit offset = 2*pos
    mov     rbx, 3
    shl     rbx, cl
    not     rbx
    and     r15, rbx        ; clear the slot
    ; encode new trit
    xor     rbx, rbx
    cmp     r14, 1
    je      .pos
    cmp     r14, -1
    je      .neg
    jmp     .set
.pos:
    mov     rbx, 1
    jmp     .set
.neg:
    mov     rbx, 2
.set:
    shl     rbx, cl
    or      r15, rbx
    ; convert back to balanced ternary
    mov     rdi, r15
    mov     rsi, WORD_TRITS
    call    from_bet
    POP_CALLEE
    ret

; ── get_field_val ─────────────────────────────────────────────────────────────
; Extract a multi-trit field from a balanced ternary integer.
; Input:  rdi = word value
;         rsi = LST position (lowest trit index of field)
;         rdx = field width in trits
; Output: rax = field value as balanced ternary integer
get_field_val:
    PUSH_CALLEE
    mov     r12, rdi        ; word
    mov     r13, rsi        ; lsb
    mov     r14, rdx        ; width
    ; convert word to BET
    mov     rdi, r12
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r15, rax        ; r15 = full BET
    ; extract field: shift right by 2*lsb, mask to 2*width bits
    mov     rcx, r13
    shl     rcx, 1          ; bit offset = 2*lsb
    sar     r15, cl
    ; build mask: (1 << (2*width)) - 1
    mov     rcx, r14
    shl     rcx, 1          ; 2*width
    mov     rbx, 1
    shl     rbx, cl
    dec     rbx             ; mask
    and     r15, rbx
    ; convert field BET to balanced ternary
    mov     rdi, r15
    mov     rsi, r14
    call    from_bet
    POP_CALLEE
    ret

; ── set_field_val ─────────────────────────────────────────────────────────────
; Set a multi-trit field in a balanced ternary integer.
; Input:  rdi = word value
;         rsi = LST position
;         rdx = field width
;         rcx = new field value (balanced ternary integer)
; Output: rax = modified word value
set_field_val:
    PUSH_CALLEE
    mov     r12, rdi        ; word
    mov     r13, rsi        ; lsb
    mov     r14, rdx        ; width
    mov     rbp, rcx        ; new field value
    ; convert word to BET
    mov     rdi, r12
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r15, rax        ; r15 = word BET
    ; convert new field value to BET
    mov     rdi, rbp
    mov     rsi, r14
    call    to_bet
    mov     rbx, rax        ; rbx = field BET
    ; clear field in word BET
    mov     rcx, r14
    shl     rcx, 1
    mov     rax, 1
    shl     rax, cl
    dec     rax             ; field mask (unshifted)
    mov     rcx, r13
    shl     rcx, 1          ; bit offset
    shl     rax, cl         ; shift mask to position
    not     rax
    and     r15, rax        ; clear field
    ; insert new field
    mov     rcx, r13
    shl     rcx, 1
    shl     rbx, cl
    or      r15, rbx
    ; convert back
    mov     rdi, r15
    mov     rsi, WORD_TRITS
    call    from_bet
    POP_CALLEE
    ret

; ── trit_min_word ─────────────────────────────────────────────────────────────
; Trit-wise minimum of two 24-trit words.
; Input:  rdi = word a,  rsi = word b
; Output: rax = result
trit_min_word:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    ; convert both to BET
    mov     rdi, r12
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r14, rax        ; r14 = BET(a)
    mov     rdi, r13
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r15, rax        ; r15 = BET(b)
    ; trit-wise min: for each 2-bit slot, take the trit with lower value
    ; decode each pair and pick min
    xor     rbx, rbx        ; result BET
    xor     r8, r8          ; trit index
.loop:
    cmp     r8, WORD_TRITS
    jge     .done
    mov     rcx, r8
    shl     rcx, 1
    ; extract trit from a
    mov     rax, r14
    sar     rax, cl
    and     rax, 3
    ; decode a_trit
    call    .decode_trit    ; rax = decoded trit (uses rax as in/out)
    mov     r9, rax         ; r9 = a_trit
    ; extract trit from b
    mov     rax, r15
    sar     rax, cl
    and     rax, 3
    call    .decode_trit
    mov     r10, rax        ; r10 = b_trit
    ; min
    cmp     r9, r10
    jle     .use_a
    mov     r9, r10
.use_a:
    ; encode r9 back to 2-bit
    call    .encode_trit    ; input in r9, output in rax
    mov     rcx, r8
    shl     rcx, 1
    shl     rax, cl
    or      rbx, rax
    inc     r8
    jmp     .loop
.done:
    ; convert result BET to balanced ternary
    mov     rdi, rbx
    mov     rsi, WORD_TRITS
    call    from_bet
    POP_CALLEE
    ret
.decode_trit:
    ; input: rax = 2-bit encoding (0,1,2)
    ; output: rax = trit value (-1,0,+1)
    cmp     rax, 1
    je      .dt_pos
    cmp     rax, 2
    je      .dt_neg
    xor     rax, rax
    ret
.dt_pos:
    mov     rax, 1
    ret
.dt_neg:
    mov     rax, -1
    ret
.encode_trit:
    ; input: r9 = trit value (-1,0,+1)
    ; output: rax = 2-bit encoding
    xor     rax, rax
    cmp     r9, 1
    je      .et_pos
    cmp     r9, -1
    je      .et_neg
    ret
.et_pos:
    mov     rax, 1
    ret
.et_neg:
    mov     rax, 2
    ret

; ── trit_max_word ─────────────────────────────────────────────────────────────
; Trit-wise maximum of two 24-trit words.
; Input:  rdi = word a,  rsi = word b
; Output: rax = result
trit_max_word:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    mov     rdi, r12
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r14, rax
    mov     rdi, r13
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r15, rax
    xor     rbx, rbx
    xor     r8, r8
.loop:
    cmp     r8, WORD_TRITS
    jge     .done
    mov     rcx, r8
    shl     rcx, 1
    mov     rax, r14
    sar     rax, cl
    and     rax, 3
    call    trit_min_word.decode_trit
    mov     r9, rax
    mov     rax, r15
    sar     rax, cl
    and     rax, 3
    call    trit_min_word.decode_trit
    mov     r10, rax
    cmp     r9, r10
    jge     .use_a
    mov     r9, r10
.use_a:
    call    trit_min_word.encode_trit
    mov     rcx, r8
    shl     rcx, 1
    shl     rax, cl
    or      rbx, rax
    inc     r8
    jmp     .loop
.done:
    mov     rdi, rbx
    mov     rsi, WORD_TRITS
    call    from_bet
    POP_CALLEE
    ret

; ── trit_txor_word ────────────────────────────────────────────────────────────
; Ternary XOR: result[i] = (a[i] + b[i]) mod 3, balanced.
; Input:  rdi = word a,  rsi = word b
; Output: rax = result
trit_txor_word:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    mov     rdi, r12
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r14, rax
    mov     rdi, r13
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r15, rax
    xor     rbx, rbx
    xor     r8, r8
.loop:
    cmp     r8, WORD_TRITS
    jge     .done
    mov     rcx, r8
    shl     rcx, 1
    mov     rax, r14
    sar     rax, cl
    and     rax, 3
    call    trit_min_word.decode_trit
    mov     r9, rax
    mov     rax, r15
    sar     rax, cl
    and     rax, 3
    call    trit_min_word.decode_trit
    ; txor: (r9 + rax) mod 3, balanced
    add     r9, rax
    ; balanced mod 3: map to {-1,0,+1}
    ; r9 ∈ {-2,-1,0,+1,+2}
    cmp     r9, 2
    je      .wrap_neg
    cmp     r9, -2
    je      .wrap_pos
    jmp     .encode
.wrap_neg:
    mov     r9, -1
    jmp     .encode
.wrap_pos:
    mov     r9, 1
.encode:
    call    trit_min_word.encode_trit
    mov     rcx, r8
    shl     rcx, 1
    shl     rax, cl
    or      rbx, rax
    inc     r8
    jmp     .loop
.done:
    mov     rdi, rbx
    mov     rsi, WORD_TRITS
    call    from_bet
    POP_CALLEE
    ret

; ── trit_equal_word ───────────────────────────────────────────────────────────
; Trit-wise equality: result[i] = +1 if a[i]==b[i], else -1.
; Input:  rdi = word a,  rsi = word b
; Output: rax = result
trit_equal_word:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    mov     rdi, r12
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r14, rax
    mov     rdi, r13
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r15, rax
    xor     rbx, rbx
    xor     r8, r8
.loop:
    cmp     r8, WORD_TRITS
    jge     .done
    mov     rcx, r8
    shl     rcx, 1
    mov     rax, r14
    sar     rax, cl
    and     rax, 3
    call    trit_min_word.decode_trit
    mov     r9, rax
    mov     rax, r15
    sar     rax, cl
    and     rax, 3
    call    trit_min_word.decode_trit
    ; equal: +1 if same, -1 if different
    cmp     r9, rax
    je      .same
    mov     r9, -1
    jmp     .encode
.same:
    mov     r9, 1
.encode:
    call    trit_min_word.encode_trit
    mov     rcx, r8
    shl     rcx, 1
    shl     rax, cl
    or      rbx, rax
    inc     r8
    jmp     .loop
.done:
    mov     rdi, rbx
    mov     rsi, WORD_TRITS
    call    from_bet
    POP_CALLEE
    ret

; ── trit_sum_word ─────────────────────────────────────────────────────────────
; Trit-wise saturating sum: result[i] = clamp(a[i]+b[i], -1, +1).
; Input:  rdi = word a,  rsi = word b
; Output: rax = result
trit_sum_word:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    mov     rdi, r12
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r14, rax
    mov     rdi, r13
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r15, rax
    xor     rbx, rbx
    xor     r8, r8
.loop:
    cmp     r8, WORD_TRITS
    jge     .done
    mov     rcx, r8
    shl     rcx, 1
    mov     rax, r14
    sar     rax, cl
    and     rax, 3
    call    trit_min_word.decode_trit
    mov     r9, rax
    mov     rax, r15
    sar     rax, cl
    and     rax, 3
    call    trit_min_word.decode_trit
    add     r9, rax
    ; clamp to [-1, +1]
    cmp     r9, 1
    jle     .check_min
    mov     r9, 1
    jmp     .encode
.check_min:
    cmp     r9, -1
    jge     .encode
    mov     r9, -1
.encode:
    call    trit_min_word.encode_trit
    mov     rcx, r8
    shl     rcx, 1
    shl     rax, cl
    or      rbx, rax
    inc     r8
    jmp     .loop
.done:
    mov     rdi, rbx
    mov     rsi, WORD_TRITS
    call    from_bet
    POP_CALLEE
    ret

; ── word_to_str ───────────────────────────────────────────────────────────────
; Convert a 24-trit word to a 24-character string (MST first).
; Input:  rdi = word value
;         rsi = pointer to output buffer (must be ≥25 bytes)
; Output: rax = rsi (buffer pointer), buffer filled with '-','0','+' chars, null-terminated
word_to_str:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    ; convert to BET
    mov     rdi, r12
    mov     rsi, WORD_TRITS
    call    to_bet
    mov     r14, rax        ; r14 = BET
    ; fill buffer MST→LST (trit 23 first)
    mov     r15, WORD_TRITS - 1  ; trit index, starting from MST
.loop:
    cmp     r15, 0
    jl      .done
    mov     rcx, r15
    shl     rcx, 1
    mov     rax, r14
    sar     rax, cl
    and     rax, 3
    ; map to ASCII: 0→'0', 1→'+', 2→'-'
    cmp     rax, 1
    je      .plus
    cmp     rax, 2
    je      .minus
    mov     al, '0'
    jmp     .store
.plus:
    mov     al, '+'
    jmp     .store
.minus:
    mov     al, '-'
.store:
    ; buffer index = (WORD_TRITS-1) - r15
    mov     rbx, WORD_TRITS - 1
    sub     rbx, r15
    mov     [r13 + rbx], al
    dec     r15
    jmp     .loop
.done:
    mov     byte [r13 + WORD_TRITS], 0  ; null terminator
    mov     rax, r13
    POP_CALLEE
    ret
