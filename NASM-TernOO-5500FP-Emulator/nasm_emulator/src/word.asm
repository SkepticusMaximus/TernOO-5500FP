; ============================================================================
; word.asm  —  TernOO word format layer (2+4+18 layout)
;
; Implements word constructors, decoders, and the OPCODE word format
; as defined in 5500fp_ternoo_v03.py §2–3.
;
; All functions use System V AMD64 ABI.
; ============================================================================

%include "include/ternoo.inc"

section .text

extern get_field_val
extern set_field_val
extern get_trit_val
extern set_trit_val
extern from_bet
extern to_bet
extern print_cstr
extern print_int64
extern print_newline

global word_get_primary
global word_set_primary
global word_get_qualifier
global word_set_qualifier
global word_get_payload
global word_set_payload
global word_make
global word_build_scalar
global word_build_int
global word_build_uint
global word_build_pointer
global word_build_null
global word_build_map
global word_build_exec
global word_build_neural_unit
global word_build_neural_conn
global word_build_io
global word_build_opcode
global word_describe

; ── word_get_primary ──────────────────────────────────────────────────────────
; Extract the 2-trit primary field (T23-T22) from a word.
; Input:  rdi = word value
; Output: rax = primary field as balanced ternary integer
word_get_primary:
    mov     rsi, PRIMARY_LST    ; lsb = 22
    mov     rdx, PRIMARY_WIDTH  ; width = 2
    jmp     get_field_val

; ── word_set_primary ──────────────────────────────────────────────────────────
; Set the 2-trit primary field in a word.
; Input:  rdi = word value
;         rsi = primary value
; Output: rax = modified word
word_set_primary:
    mov     rcx, rsi
    mov     rsi, PRIMARY_LST
    mov     rdx, PRIMARY_WIDTH
    jmp     set_field_val

; ── word_get_qualifier ────────────────────────────────────────────────────────
; Extract the 4-trit qualifier field (T21-T18).
; Input:  rdi = word value
; Output: rax = qualifier as balanced ternary integer
word_get_qualifier:
    mov     rsi, QUAL_LST
    mov     rdx, QUAL_WIDTH
    jmp     get_field_val

; ── word_set_qualifier ────────────────────────────────────────────────────────
; Set the 4-trit qualifier field.
; Input:  rdi = word value
;         rsi = qualifier value
; Output: rax = modified word
word_set_qualifier:
    mov     rcx, rsi
    mov     rsi, QUAL_LST
    mov     rdx, QUAL_WIDTH
    jmp     set_field_val

; ── word_get_payload ──────────────────────────────────────────────────────────
; Extract the 18-trit payload field (T17-T0).
; Input:  rdi = word value
; Output: rax = payload as balanced ternary integer
word_get_payload:
    mov     rsi, PAYLOAD_LST
    mov     rdx, PAYLOAD_WIDTH
    jmp     get_field_val

; ── word_set_payload ──────────────────────────────────────────────────────────
; Set the 18-trit payload field.
; Input:  rdi = word value
;         rsi = payload value
; Output: rax = modified word
word_set_payload:
    mov     rcx, rsi
    mov     rsi, PAYLOAD_LST
    mov     rdx, PAYLOAD_WIDTH
    jmp     set_field_val

; ── word_make ─────────────────────────────────────────────────────────────────
; Construct a word from primary, qualifier, and payload.
; Input:  rdi = primary value
;         rsi = qualifier value
;         rdx = payload value
; Output: rax = assembled word
word_make:
    PUSH_CALLEE
    mov     r12, rdi        ; primary
    mov     r13, rsi        ; qualifier
    mov     r14, rdx        ; payload
    ; start with 0
    xor     r15, r15
    ; set primary
    mov     rdi, r15
    mov     rcx, r12
    mov     rsi, PRIMARY_LST
    mov     rdx, PRIMARY_WIDTH
    call    set_field_val
    mov     r15, rax
    ; set qualifier
    mov     rdi, r15
    mov     rcx, r13
    mov     rsi, QUAL_LST
    mov     rdx, QUAL_WIDTH
    call    set_field_val
    mov     r15, rax
    ; set payload
    mov     rdi, r15
    mov     rcx, r14
    mov     rsi, PAYLOAD_LST
    mov     rdx, PAYLOAD_WIDTH
    call    set_field_val
    POP_CALLEE
    ret

; ── word_build_scalar ─────────────────────────────────────────────────────────
; Build a DATA/SCALAR word.
; Input:  rdi = encoding (SCALAR_FLOAT=-1, SCALAR_INT=0, SCALAR_UINT=+1)
;         rsi = value (18-trit payload)
; Output: rax = word
;
; Qualifier layout: T21=-1(scalar), T20=-1, T19=encoding, T18=0
; from_trits([T18,T19,T20,T21]) = T18 + T19*3 + T20*9 + T21*27
;   = 0 + encoding*3 + (-1)*9 + (-1)*27 = encoding*3 - 36
word_build_scalar:
    PUSH_CALLEE
    mov     r12, rdi        ; encoding
    mov     r13, rsi        ; value
    ; compute qualifier = encoding*3 - 36
    imul    r12, 3
    sub     r12, 36
    ; word_make(PRIMARY_DATA, qualifier, value)
    mov     rdi, PRIMARY_DATA
    mov     rsi, r12
    mov     rdx, r13
    call    word_make
    POP_CALLEE
    ret

; ── word_build_int ────────────────────────────────────────────────────────────
; Build a DATA/SCALAR/INT word.
; Input:  rdi = integer value
; Output: rax = word
word_build_int:
    mov     rsi, rdi
    mov     rdi, 0          ; SCALAR_INT = 0
    jmp     word_build_scalar

; ── word_build_uint ───────────────────────────────────────────────────────────
; Build a DATA/SCALAR/UINT word.
; Input:  rdi = unsigned integer value
; Output: rax = word
word_build_uint:
    test    rdi, rdi
    jns     .ok
    xor     rdi, rdi
.ok:
    mov     rsi, rdi
    mov     rdi, 1          ; SCALAR_UINT = +1
    jmp     word_build_scalar

; ── word_build_pointer ────────────────────────────────────────────────────────
; Build a DATA/POINTER word.
; Input:  rdi = pointer model T21 trit
;         rsi = pointer model T20 trit
;         rdx = payload
; Output: rax = word
;
; Qualifier: T21=model[0], T20=model[1], T19=0, T18=0
; qualifier = T18 + T19*3 + T20*9 + T21*27 = model[1]*9 + model[0]*27
word_build_pointer:
    PUSH_CALLEE
    mov     r12, rdi        ; T21 (model[0])
    mov     r13, rsi        ; T20 (model[1])
    mov     r14, rdx        ; payload
    ; qualifier = T21*27 + T20*9
    imul    r12, 27
    imul    r13, 9
    add     r12, r13        ; qualifier
    mov     rdi, PRIMARY_DATA
    mov     rsi, r12
    mov     rdx, r14
    call    word_make
    POP_CALLEE
    ret

; ── word_build_null ───────────────────────────────────────────────────────────
; Build a DATA/PTR_NULL word (explicit null).
; Input:  rdi = payload (0 for explicit null)
; Output: rax = word
word_build_null:
    ; PTR_NULL = (0, 0) → qualifier = 0*27 + 0*9 = 0
    mov     rdx, rdi
    mov     rdi, 0          ; T21=0
    mov     rsi, 0          ; T20=0
    jmp     word_build_pointer

; ── word_build_map ────────────────────────────────────────────────────────────
; Build a MAP word.
; Input:  rdi = axis_yz trit (-1,0,+1)
;         rsi = axis_xz trit
;         rdx = axis_xy trit
;         rcx = payload (18-trit coordinate)
;         r8  = mode_hint trit
; Output: rax = word
;
; Qualifier: T21=axis_yz, T20=axis_xz, T19=axis_xy, T18=mode_hint
; qualifier = T18 + T19*3 + T20*9 + T21*27
word_build_map:
    PUSH_CALLEE
    mov     r12, rdi        ; axis_yz (T21)
    mov     r13, rsi        ; axis_xz (T20)
    mov     r14, rdx        ; axis_xy (T19)
    mov     r15, rcx        ; payload
    mov     rbp, r8         ; mode_hint (T18)
    ; qualifier = mode_hint + axis_xy*3 + axis_xz*9 + axis_yz*27
    imul    r12, 27
    imul    r13, 9
    imul    r14, 3
    add     r12, r13
    add     r12, r14
    add     r12, rbp
    mov     rdi, PRIMARY_MAP
    mov     rsi, r12
    mov     rdx, r15
    call    word_make
    POP_CALLEE
    ret

; ── word_build_exec ───────────────────────────────────────────────────────────
; Build an EXEC word.
; Input:  rdi = privilege (-1=kernel, 0=user, +1=sandbox)
;         rsi = call_style (-1=stack, 0=register, +1=message)
;         rdx = return_type (-1=EXEC, 0=MAP, +1=DATA)
;         rcx = seg_idx (0..8)
;         r8  = offset (6-trit)
; Output: rax = word
;
; Qualifier (4 trits T21-T18): T21=priv, T20=call, T19=ret, T18=seg_idx_MST
; Payload (18 trits): T17=seg_idx_LST, T16-T11=offset(6t), T10-T0=spare
word_build_exec:
    PUSH_CALLEE
    mov     r12, rdi        ; privilege
    mov     r13, rsi        ; call_style
    mov     r14, rdx        ; return_type
    mov     r15, rcx        ; seg_idx
    mov     rbp, r8         ; offset
    ; encode seg_idx as balanced: si = seg_idx - 4
    sub     r15, 4
    ; si_trits[0] (LST) = si % 3 balanced, si_trits[1] (MST) = si / 3
    ; simplified: use lower trit of si for T18, upper for T17
    mov     rax, r15
    mov     rcx, 3
    cqo
    idiv    rcx             ; rax=quotient(si_MST), rdx=remainder(si_LST)
    ; balanced adjust
    cmp     rdx, 2
    jne     .si_check_neg
    mov     rdx, -1
    inc     rax
.si_check_neg:
    cmp     rdx, -2
    jne     .si_ok
    mov     rdx, 1
    dec     rax
.si_ok:
    mov     rbx, rax        ; rbx = si_MST (for T17)
    mov     r15, rdx        ; r15 = si_LST (for T18)
    ; qualifier = T18 + T19*3 + T20*9 + T21*27
    ; T18=si_LST, T19=return_type, T20=call_style, T21=privilege
    mov     rax, r12        ; privilege
    imul    rax, 27
    mov     rcx, r13        ; call_style
    imul    rcx, 9
    add     rax, rcx
    mov     rcx, r14        ; return_type
    imul    rcx, 3
    add     rax, rcx
    add     rax, r15        ; si_LST
    mov     r15, rax        ; r15 = qualifier
    ; payload: T17=si_MST, T16-T11=offset
    ; payload = si_MST * 3^17 + offset * 3^11  (simplified)
    ; Use set_field_val approach: build payload as integer
    ; payload = 0, set T17 = si_MST, set T16-T11 = offset
    xor     r8, r8          ; payload accumulator
    ; set T17 = si_MST: payload += si_MST * 3^17
    lea     rax, [rel pow3_17]
    mov     rax, [rax]
    imul    rax, rbx
    add     r8, rax
    ; set T16-T11 = offset (6 trits starting at T11)
    ; offset * 3^11
    lea     rax, [rel pow3_11]
    mov     rax, [rax]
    imul    rax, rbp
    add     r8, rax
    ; word_make(PRIMARY_EXEC, qualifier, payload)
    mov     rdi, PRIMARY_EXEC
    mov     rsi, r15
    mov     rdx, r8
    call    word_make
    POP_CALLEE
    ret

; ── word_build_neural_unit ────────────────────────────────────────────────────
; Build a NEURAL/UNIT word.
; Input:  rdi = state (3-trit)
;         rsi = bias (6-trit)
;         rdx = fan_in (5-trit)
;         rcx = weight_seg (4-trit)
; Output: rax = word
word_build_neural_unit:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    mov     r14, rdx
    mov     r15, rcx
    ; qualifier: T21=NEURAL_UNIT(-1), T20-T18=0
    ; qualifier = -1*27 = -27
    ; payload: T17-T15=state(3t), T14-T9=bias(6t), T8-T4=fan_in(5t), T3-T0=weight_seg(4t)
    ; payload = state*3^15 + bias*3^9 + fan_in*3^4 + weight_seg*3^0
    lea     rax, [rel pow3_15]
    mov     rax, [rax]
    imul    rax, r12
    mov     rbp, rax
    lea     rax, [rel pow3_9]
    mov     rax, [rax]
    imul    rax, r13
    add     rbp, rax
    lea     rax, [rel pow3_4]
    mov     rax, [rax]
    imul    rax, r14
    add     rbp, rax
    add     rbp, r15        ; weight_seg * 3^0
    mov     rdi, PRIMARY_NEURAL
    mov     rsi, -27        ; qualifier: T21=-1
    mov     rdx, rbp
    call    word_make
    POP_CALLEE
    ret

; ── word_build_neural_conn ────────────────────────────────────────────────────
; Build a NEURAL/CONNECTION word.
; Input:  rdi = weight (2-trit, ±4)
;         rsi = source neuron id (8-trit)
;         rdx = target neuron id (8-trit)
; Output: rax = word
word_build_neural_conn:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    mov     r14, rdx
    ; qualifier: T21=NEURAL_CONNECTION(0) → qualifier = 0
    ; payload: T17-T16=weight(2t), T15-T8=source(8t), T7-T0=target(8t)
    lea     rax, [rel pow3_16]
    mov     rax, [rax]
    imul    rax, r12
    mov     rbp, rax
    lea     rax, [rel pow3_8]
    mov     rax, [rax]
    imul    rax, r13
    add     rbp, rax
    add     rbp, r14        ; target * 3^0
    mov     rdi, PRIMARY_NEURAL
    xor     rsi, rsi        ; qualifier = 0
    mov     rdx, rbp
    call    word_make
    POP_CALLEE
    ret

; ── word_build_io ─────────────────────────────────────────────────────────────
; Build an I/O word.
; Input:  rdi = direction (-1=in, 0=bidi, +1=out)
;         rsi = buffering (-1=none, 0=buffered, +1=interrupt)
;         rdx = blocking trit
;         rcx = channel (18-trit payload)
; Output: rax = word
word_build_io:
    PUSH_CALLEE
    mov     r12, rdi
    mov     r13, rsi
    mov     r14, rdx
    mov     r15, rcx
    ; qualifier = T18 + T19*3 + T20*9 + T21*27
    ; T21=direction, T20=buffering, T19=blocking, T18=0
    imul    r12, 27
    imul    r13, 9
    imul    r14, 3
    add     r12, r13
    add     r12, r14
    mov     rdi, PRIMARY_IO
    mov     rsi, r12
    mov     rdx, r15
    call    word_make
    POP_CALLEE
    ret

; ── word_build_opcode ─────────────────────────────────────────────────────────
; Build an OPCODE primary word.
; Input:  rdi = family (OPF_* value, 2-trit balanced)
;         rsi = arity (0..8, encoded as arity-4)
;         rdx = op_index (±364)
;         rcx = immediate (12-trit)
; Output: rax = word
;
; Layout:
;   Primary: PRIMARY_OPCODE (+2)
;   Qualifier: T21-T20=family(2t), T19-T18=arity_enc(2t)
;   Payload: T17-T12=op_index(6t), T11-T0=immediate(12t)
word_build_opcode:
    PUSH_CALLEE
    mov     r12, rdi        ; family
    mov     r13, rsi        ; arity
    mov     r14, rdx        ; op_index
    mov     r15, rcx        ; immediate
    ; arity_enc = arity - 4
    sub     r13, 4
    ; qualifier: T21-T20=family, T19-T18=arity_enc
    ; qualifier = T18 + T19*3 + T20*9 + T21*27
    ; family occupies T21-T20 (positions 2-3 within 4-trit qualifier)
    ; arity_enc occupies T19-T18 (positions 0-1 within 4-trit qualifier)
    ; qualifier = arity_enc_T18 + arity_enc_T19*3 + family_T20*9 + family_T21*27
    ; Simplified: treat family as 2-trit value and arity_enc as 2-trit value
    ; qualifier = arity_enc + family * 9  (since family is at positions 2-3, arity at 0-1)
    ; More precisely: qualifier = from_trits([arity_enc_lsb, arity_enc_msb, family_lsb, family_msb])
    ; We use: qualifier = arity_enc * 3^0_field + family * 3^2_field
    ; Since field positions are: T18=pos0, T19=pos1, T20=pos2, T21=pos3
    ; and family is 2 trits at positions 2-3, arity_enc is 2 trits at positions 0-1:
    ; We need to compute from_trits of the 4-trit qualifier
    ; Let's use the formula: qual = arity_enc + family*9
    ; (arity_enc is 2 trits at low positions, family is 2 trits at high positions)
    ; This is: arity_enc * 3^0 (as 2-trit value) + family * 3^2 (as 2-trit value)
    ; = arity_enc + family * 9
    mov     rax, r12
    imul    rax, 9
    add     rax, r13
    mov     r12, rax        ; r12 = qualifier
    ; payload: T17-T12=op_index(6t), T11-T0=immediate(12t)
    ; payload = immediate + op_index * 3^12
    lea     rax, [rel pow3_12]
    mov     rax, [rax]
    imul    rax, r14
    add     rax, r15
    mov     r14, rax        ; r14 = payload
    mov     rdi, PRIMARY_OPCODE
    mov     rsi, r12
    mov     rdx, r14
    call    word_make
    POP_CALLEE
    ret

; ── word_describe ─────────────────────────────────────────────────────────────
; Print a human-readable description of a word to stdout.
; Input:  rdi = word value
word_describe:
    PUSH_CALLEE
    mov     r12, rdi
    ; get primary
    call    word_get_primary
    mov     r13, rax        ; primary
    cmp     r13, PRIMARY_EXEC
    je      .desc_exec
    cmp     r13, PRIMARY_MAP
    je      .desc_map
    cmp     r13, PRIMARY_DATA
    je      .desc_data
    cmp     r13, PRIMARY_NEURAL
    je      .desc_neural
    cmp     r13, PRIMARY_IO
    je      .desc_io
    cmp     r13, PRIMARY_OPCODE
    je      .desc_opcode
    ; unknown
    lea     rdi, [rel wdesc_unknown]
    call    print_cstr
    mov     rdi, r13
    call    print_int64
    call    print_newline
    jmp     .desc_done

.desc_exec:
    lea     rdi, [rel wdesc_exec]
    call    print_cstr
    mov     rdi, r12
    call    word_get_payload
    call    print_int64
    call    print_newline
    jmp     .desc_done

.desc_map:
    lea     rdi, [rel wdesc_map]
    call    print_cstr
    mov     rdi, r12
    call    word_get_payload
    call    print_int64
    call    print_newline
    jmp     .desc_done

.desc_data:
    lea     rdi, [rel wdesc_data]
    call    print_cstr
    mov     rdi, r12
    call    word_get_payload
    call    print_int64
    call    print_newline
    jmp     .desc_done

.desc_neural:
    lea     rdi, [rel wdesc_neural]
    call    print_cstr
    mov     rdi, r12
    call    word_get_payload
    call    print_int64
    call    print_newline
    jmp     .desc_done

.desc_io:
    lea     rdi, [rel wdesc_io]
    call    print_cstr
    mov     rdi, r12
    call    word_get_payload
    call    print_int64
    call    print_newline
    jmp     .desc_done

.desc_opcode:
    lea     rdi, [rel wdesc_opcode]
    call    print_cstr
    ; print op_index from payload T17-T12
    mov     rdi, r12
    mov     rsi, 12
    mov     rdx, 6
    call    get_field_val
    call    print_int64
    call    print_newline
    jmp     .desc_done

.desc_done:
    POP_CALLEE
    ret

section .data

; Powers of 3 at specific positions (for word construction)
pow3_4:     dq  81
pow3_8:     dq  6561
pow3_9:     dq  19683
pow3_11:    dq  177147
pow3_12:    dq  531441
pow3_15:    dq  14348907
pow3_16:    dq  43046721
pow3_17:    dq  129140163

; String constants for word_describe
wdesc_exec:     db  "EXEC  payload=", 0
wdesc_map:      db  "MAP   payload=", 0
wdesc_data:     db  "DATA  payload=", 0
wdesc_neural:   db  "NEURAL payload=", 0
wdesc_io:       db  "I/O   channel=", 0
wdesc_opcode:   db  "OPCODE op_idx=", 0
wdesc_unknown:  db  "WORD?  primary=", 0
