; ============================================================================
; gristmill.asm  —  GristMill: Generative Object Synthesis Engine
;
; Ported from: TernOO-5500FP/5500fp/ternoo_gristmill.py
; Authors:     Stevo (SkepticusMaximus) + Claude (Anthropic)
; Port:        Pure x86-64 NASM by Manus AI
;
; GristMill is not a repository — it is a generative synthesis engine.
; Objects are not stored at locations; they are computed from MMID coordinates.
;
; An MMID (Minimal Map ID) is a TernOO MAP word — a native octree coordinate
; in the 5500FP address space. An MMOE (Minimal Map Object Entity) is the
; minimal self-contained unit of meaningful TernOO data that the MMID describes.
;
; Key operations:
;   ternary_op(a, b)        — Steiner quasigroup: -(a+b) mod 729
;   traverse_step(s, a, b)  — advance traversal state by one triangle
;   extract_tribbles(word)  — split 18-trit payload into three 6-trit tribbles
;   trit_weight(val, w)     — sum of absolute trit values
;   build_ttree_mmid(ta,tb) — TTree MAP word (ON_PLANE, mode_hint=+1)
;   build_otree_mmoe(state) — OTree MAP word (ABSOLUTE_3D, mode_hint=0)
;   mmid_compute(type)      — compute MMID word for a given MMOE type index
;   mmid_distance(a, b)     — Manhattan distance between two MMID words
;   mmid_proximity(mmid, n) — fill array with n nearest MMOE type indices
;
; MMOE type indices (matching Python MMOE_TYPES dict order):
;   0  terminator
;   1  io_read
;   2  io_write
;   3  process
;   4  decision
;   5  widget_window
;   6  widget_panel
;   7  widget_button
;   8  widget_label
;   9  widget_input
;   10 meccano_program_pigart
;   11 meccano_program_word_op
;   12 meccano_program_compose
;
; ============================================================================

%include "include/ternoo.inc"

section .data

; ── MMOE type table ──────────────────────────────────────────────────────────
; Each entry: [name_ptr(8), t1(8), t0(8), n_successors(8), succ_indices(8*4)]
; Packed as 8 qwords per entry = 64 bytes per entry

MMOE_COUNT equ 13

align 8
mmoe_table:
    ; 0: terminator  udp=(+1,+1)  successors=[1]
    dq mmoe_name_0, 1, 1, 1, 1, 0, 0, 0
    ; 1: io_read     udp=(+1, 0)  successors=[3,4]
    dq mmoe_name_1, 1, 0, 2, 3, 4, 0, 0
    ; 2: io_write    udp=(+1, 0)  successors=[0]
    dq mmoe_name_2, 1, 0, 1, 0, 0, 0, 0
    ; 3: process     udp=(0,  0)  successors=[4,2]
    dq mmoe_name_3, 0, 0, 2, 4, 2, 0, 0
    ; 4: decision    udp=(0, +1)  successors=[2,3,1]
    dq mmoe_name_4, 0, 1, 3, 2, 3, 1, 0
    ; 5: widget_window  udp=(+1,-1) successors=[6]
    dq mmoe_name_5, 1, -1, 1, 6, 0, 0, 0
    ; 6: widget_panel   udp=(+1,-1) successors=[7,8,9]
    dq mmoe_name_6, 1, -1, 3, 7, 8, 9, 0
    ; 7: widget_button  udp=(+1,+1) successors=[6,8]
    dq mmoe_name_7, 1, 1, 2, 6, 8, 0, 0
    ; 8: widget_label   udp=(+1, 0) successors=[7,9]
    dq mmoe_name_8, 1, 0, 2, 7, 9, 0, 0
    ; 9: widget_input   udp=(+1,-1) successors=[7,8]
    dq mmoe_name_9, 1, -1, 2, 7, 8, 0, 0
    ; 10: meccano_program_pigart   udp=(+1,+1) successors=[]
    dq mmoe_name_10, 1, 1, 0, 0, 0, 0, 0
    ; 11: meccano_program_word_op  udp=(+1, 0) successors=[]
    dq mmoe_name_11, 1, 0, 0, 0, 0, 0, 0
    ; 12: meccano_program_compose  udp=(+1,-1) successors=[]
    dq mmoe_name_12, 1, -1, 0, 0, 0, 0, 0

mmoe_name_0:  db "terminator", 0
mmoe_name_1:  db "io_read", 0
mmoe_name_2:  db "io_write", 0
mmoe_name_3:  db "process", 0
mmoe_name_4:  db "decision", 0
mmoe_name_5:  db "widget_window", 0
mmoe_name_6:  db "widget_panel", 0
mmoe_name_7:  db "widget_button", 0
mmoe_name_8:  db "widget_label", 0
mmoe_name_9:  db "widget_input", 0
mmoe_name_10: db "meccano_program_pigart", 0
mmoe_name_11: db "meccano_program_word_op", 0
mmoe_name_12: db "meccano_program_compose", 0

; MOD = 3^6 = 729
TRIBBLE_MOD equ 729
; TRIBBLE_OFFSET = 364  (balanced range -364..+364 → 0..728)
TRIBBLE_OFFSET equ 364

section .text

extern get_field_val
extern set_field_val
extern word_build_map
extern word_build_exec
extern word_make

global gm_ternary_op
global gm_traverse_step
global gm_extract_tribbles
global gm_trit_weight
global gm_build_ttree_mmid
global gm_build_otree_mmoe
global gm_mmid_compute
global gm_mmid_distance
global gm_mmid_proximity
global gm_mmoe_name
global gm_mmoe_successors

; ── gm_ternary_op ─────────────────────────────────────────────────────────────
; Steiner quasigroup mutual recovery operation.
; A ⊕ B = -(A+B) mod 729
; Property: for any triple (A,B,C) where C=ternary_op(A,B):
;   ternary_op(B,C)==A, ternary_op(A,C)==B
;
; Input:  rdi = a (any integer)
;         rsi = b (any integer)
; Output: rax = -(a+b) mod 729  (range 0..728)
gm_ternary_op:
    lea     rax, [rdi + rsi]    ; rax = a+b
    neg     rax                 ; rax = -(a+b)
    ; Python-style modulo: result = ((-(a+b)) % 729) always positive
    mov     rcx, TRIBBLE_MOD
    xor     rdx, rdx
    ; Handle negative dividend: use idiv then adjust
    cqo                         ; sign-extend rax into rdx:rax
    idiv    rcx                 ; rdx = rax mod 729 (signed)
    mov     rax, rdx
    ; Adjust to positive: if rax < 0, add 729
    test    rax, rax
    jge     .done
    add     rax, TRIBBLE_MOD
.done:
    ret

; ── gm_traverse_step ──────────────────────────────────────────────────────────
; Advance traversal state by one triangle.
; side_c = ternary_op(side_a, side_b)
; new_state = (state + side_c) mod 729
; arrived = (side_c == 0)
;
; Input:  rdi = state  (0..728)
;         rsi = side_a (0..728)
;         rdx = side_b (0..728)
; Output: rax = new_state
;         rdx = side_c
;         rcx = arrived (0 or 1)
gm_traverse_step:
    push    rbx
    push    r12
    mov     r12, rdi            ; save state
    mov     rdi, rsi
    mov     rsi, rdx
    call    gm_ternary_op       ; rax = side_c
    mov     rbx, rax            ; rbx = side_c
    ; new_state = (state + side_c) mod 729
    lea     rax, [r12 + rbx]
    mov     rcx, TRIBBLE_MOD
    xor     rdx, rdx
    div     rcx                 ; rdx = (state+side_c) mod 729
    mov     rax, rdx            ; rax = new_state
    mov     rdx, rbx            ; rdx = side_c
    xor     rcx, rcx
    test    rbx, rbx
    setz    cl                  ; rcx = arrived (1 if side_c==0)
    pop     r12
    pop     rbx
    ret

; ── gm_extract_tribbles ───────────────────────────────────────────────────────
; Extract three 6-trit payload tribbles from a TernOO word.
; Only the 18-trit payload (T17-T0) participates — PRIMARY/QUALIFIER excluded.
;
; Input:  rdi = word (24-trit TernOO word)
;         rsi = pointer to int64_t[3] output: [ta, tb, tc]
;               ta = T17-T12, tb = T11-T6, tc = T5-T0
; Output: rax = ta (also stored in [rsi+0])
;         rdx = tb (also stored in [rsi+8])
;         rcx = tc (also stored in [rsi+16])
gm_extract_tribbles:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi            ; word
    mov     r13, rsi            ; output ptr
    ; ta = get_field_val(word, 12, 6)
    mov     rdi, r12
    mov     rsi, 12
    mov     rdx, 6
    call    get_field_val
    mov     [r13 + 0], rax
    mov     rbx, rax            ; rbx = ta
    ; tb = get_field_val(word, 6, 6)
    mov     rdi, r12
    mov     rsi, 6
    mov     rdx, 6
    call    get_field_val
    mov     [r13 + 8], rax
    mov     r12, rax            ; r12 = tb (reuse r12)
    ; tc = get_field_val(word, 0, 6)
    mov     rdi, [r13 + 0]      ; reload original word — wait, r12 was word
    ; Fix: we need to re-read the original word. Save it first.
    pop     r13
    pop     r12
    pop     rbx
    ; Redo with proper register management
    push    rbx
    push    r12
    push    r13
    push    r14
    mov     r12, rdi            ; word
    mov     r13, rsi            ; output ptr
    ; ta = get_field_val(word, 12, 6)
    mov     rdi, r12
    mov     rsi, 12
    mov     rdx, 6
    call    get_field_val
    mov     [r13 + 0], rax
    mov     r14, rax            ; ta
    ; tb
    mov     rdi, r12
    mov     rsi, 6
    mov     rdx, 6
    call    get_field_val
    mov     [r13 + 8], rax
    mov     rbx, rax            ; tb
    ; tc
    mov     rdi, r12
    mov     rsi, 0
    mov     rdx, 6
    call    get_field_val
    mov     [r13 + 16], rax
    mov     rcx, rax            ; tc
    mov     rax, r14            ; return ta
    mov     rdx, rbx            ; return tb
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── gm_trit_weight ────────────────────────────────────────────────────────────
; Sum of absolute values of the `width` balanced trits of val.
; val is first reduced mod 729 to 0..728 (unbalanced), then each trit
; is extracted as a balanced value in {-1, 0, +1}.
;
; Input:  rdi = val (any integer)
;         rsi = width (number of trits, typically 6)
; Output: rax = sum of |trit_i| for i in 0..width-1
gm_trit_weight:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    mov     r13, rsi
    ; reduce val mod 729 to 0..728
    mov     rax, r12
    mov     rcx, TRIBBLE_MOD
    xor     rdx, rdx
    cqo
    idiv    rcx
    mov     rax, rdx
    test    rax, rax
    jge     .reduced
    add     rax, TRIBBLE_MOD
.reduced:
    mov     r12, rax            ; r12 = val mod 729 (unbalanced, 0..728)
    xor     rbx, rbx            ; rbx = weight accumulator
    xor     rcx, rcx            ; rcx = trit index
.loop:
    cmp     rcx, r13
    jge     .done
    ; get_field_val(val, i, 1) — single trit
    mov     rdi, r12
    mov     rsi, rcx
    mov     rdx, 1
    call    get_field_val
    ; abs(rax)
    test    rax, rax
    jge     .pos
    neg     rax
.pos:
    add     rbx, rax
    inc     rcx
    jmp     .loop
.done:
    mov     rax, rbx
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── gm_build_ttree_mmid ───────────────────────────────────────────────────────
; Build a TTree MMID coordinate from UDP payload tribbles ta and tb.
; Uses MAP ON_PLANE mode (axis_yz=0) with mode_hint=+1.
;
; Input:  rdi = ta (balanced ternary, -364..+364)
;         rsi = tb (balanced ternary, -364..+364)
; Output: rax = TTree MAP word
gm_build_ttree_mmid:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi            ; ta
    mov     r13, rsi            ; tb
    ; y = ta + 364  (shift to positive 0..728)
    lea     rdi, [r12 + TRIBBLE_OFFSET]
    ; z = tb + 364
    lea     rsi, [r13 + TRIBBLE_OFFSET]
    ; payload = set_field(0, 9, 9, y)
    push    rdi
    push    rsi
    xor     rdi, rdi
    mov     rsi, 9
    mov     rdx, 9
    pop     rcx                 ; z (was rsi)
    push    rcx
    pop     rcx
    ; Redo cleanly:
    pop     rsi                 ; z
    pop     rdi                 ; y
    mov     rbx, rdi            ; y
    mov     r12, rsi            ; z
    ; payload = set_field_val(0, 9, 9, y)
    xor     rdi, rdi
    mov     rsi, 9
    mov     rdx, 9
    mov     rcx, rbx
    call    set_field_val
    mov     rbx, rax            ; payload with Y
    ; payload = set_field_val(payload, 0, 9, z)
    mov     rdi, rbx
    mov     rsi, 0
    mov     rdx, 9
    mov     rcx, r12
    call    set_field_val
    mov     rbx, rax            ; final payload
    ; build_map_word(axis_yz=0, axis_xz=+1, axis_xy=+1, payload, mode_hint=+1)
    ; word.asm exports word_build_map which takes (primary, qualifier, payload)
    ; We need to call the full build_map_word with axis trits.
    ; Use word_encode_map: rdi=axis_yz, rsi=axis_xz, rdx=axis_xy, rcx=payload, r8=mode_hint
    mov     rdi, 0              ; axis_yz = 0 (ON_PLANE)
    mov     rsi, 1              ; axis_xz = +1
    mov     rdx, 1              ; axis_xy = +1
    mov     rcx, rbx            ; payload
    mov     r8,  1              ; mode_hint = +1
    call    gm_encode_map_word
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── gm_build_otree_mmoe ───────────────────────────────────────────────────────
; Build an OTree MMOE coordinate from an accumulated ternary_op traversal state.
; Uses MAP ABSOLUTE_3D mode with mode_hint=0.
;
; Input:  rdi = tribble_state (0..728)
; Output: rax = OTree MAP word
gm_build_otree_mmoe:
    push    rbx
    push    r12
    push    r13
    push    r14
    mov     r12, rdi            ; tribble_state
    ; yz_sign = ternary_sign(state % 3)
    mov     rax, r12
    mov     rcx, 3
    xor     rdx, rdx
    div     rcx
    mov     rdi, rdx
    call    gm_ternary_sign
    mov     r13, rax            ; yz_sign
    test    r13, r13
    jnz     .yz_ok
    mov     r13, 1              ; default to +1 if 0
.yz_ok:
    ; xz_sign = ternary_sign((state/3) % 3)
    mov     rax, r12
    mov     rcx, 3
    xor     rdx, rdx
    div     rcx                 ; rax = state/3
    mov     rcx, 3
    xor     rdx, rdx
    div     rcx                 ; rdx = (state/3) % 3
    mov     rdi, rdx
    call    gm_ternary_sign
    mov     r14, rax            ; xz_sign
    test    r14, r14
    jnz     .xz_ok
    mov     r14, 1
.xz_ok:
    ; xy_sign = ternary_sign((state/9) % 3)
    mov     rax, r12
    mov     rcx, 9
    xor     rdx, rdx
    div     rcx                 ; rax = state/9
    mov     rcx, 3
    xor     rdx, rdx
    div     rcx                 ; rdx = (state/9) % 3
    mov     rdi, rdx
    call    gm_ternary_sign
    mov     rbx, rax            ; xy_sign
    test    rbx, rbx
    jnz     .xy_ok
    mov     rbx, 1
.xy_ok:
    ; magnitude = state % 729
    mov     rax, r12
    mov     rcx, TRIBBLE_MOD
    xor     rdx, rdx
    div     rcx
    ; rdx = magnitude
    ; build_map_word(yz_sign, xz_sign, xy_sign, magnitude, mode_hint=0)
    mov     rdi, r13            ; axis_yz = yz_sign
    mov     rsi, r14            ; axis_xz = xz_sign
    mov     rdx, rbx            ; axis_xy = xy_sign
    mov     rcx, rdx            ; payload = magnitude — wait, rdx was overwritten
    ; Redo: save magnitude before it gets clobbered
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    mov     r12, rdi
    ; yz_sign
    mov     rax, r12
    mov     rcx, 3
    xor     rdx, rdx
    div     rcx
    mov     rdi, rdx
    call    gm_ternary_sign
    mov     r13, rax
    test    r13, r13
    jnz     .yz2
    mov     r13, 1
.yz2:
    ; xz_sign
    mov     rax, r12
    mov     rcx, 3
    xor     rdx, rdx
    div     rcx
    mov     rcx, 3
    xor     rdx, rdx
    div     rcx
    mov     rdi, rdx
    call    gm_ternary_sign
    mov     r14, rax
    test    r14, r14
    jnz     .xz2
    mov     r14, 1
.xz2:
    ; xy_sign
    mov     rax, r12
    mov     rcx, 9
    xor     rdx, rdx
    div     rcx
    mov     rcx, 3
    xor     rdx, rdx
    div     rcx
    mov     rdi, rdx
    call    gm_ternary_sign
    mov     rbx, rax
    test    rbx, rbx
    jnz     .xy2
    mov     rbx, 1
.xy2:
    ; magnitude
    mov     rax, r12
    mov     rcx, TRIBBLE_MOD
    xor     rdx, rdx
    div     rcx
    mov     r15, rdx            ; r15 = magnitude
    ; encode
    mov     rdi, r13
    mov     rsi, r14
    mov     rdx, rbx
    mov     rcx, r15
    mov     r8,  0              ; mode_hint = 0
    call    gm_encode_map_word
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── gm_ternary_sign ───────────────────────────────────────────────────────────
; Map a value mod 3 to balanced ternary: 0→0, 1→+1, 2→-1
; Input:  rdi = val (0..2)
; Output: rax = {-1, 0, +1}
gm_ternary_sign:
    mov     rax, rdi
    cmp     rax, 0
    je      .zero
    cmp     rax, 1
    je      .pos
    mov     rax, -1
    ret
.zero:
    xor     rax, rax
    ret
.pos:
    mov     rax, 1
    ret

; ── gm_encode_map_word ────────────────────────────────────────────────────────
; Encode a MAP word from axis trits, payload, and mode_hint.
; Mirrors build_map_word() from 5500fp_ternoo_v03.py.
;
; MAP word layout (24 trits):
;   T23-T22: PRIMARY = MAP = -3 (2 trits)
;   T21:     axis_yz  (qualifier trit 0)
;   T20:     axis_xz  (qualifier trit 1)
;   T19:     axis_xy  (qualifier trit 2)
;   T18:     mode_hint (qualifier trit 3)
;   T17-T0:  payload (18 trits)
;
; Input:  rdi = axis_yz  (-1, 0, +1)
;         rsi = axis_xz  (-1, 0, +1)
;         rdx = axis_xy  (-1, 0, +1)
;         rcx = payload  (18-trit value)
;         r8  = mode_hint (-1, 0, +1)
; Output: rax = MAP word
gm_encode_map_word:
    PUSH_CALLEE
    mov     r12, rdi            ; axis_yz
    mov     r13, rsi            ; axis_xz
    mov     r14, rdx            ; axis_xy
    mov     r15, rcx            ; payload
    mov     rbx, r8             ; mode_hint
    ; Start with 0
    xor     rdi, rdi
    ; Set PRIMARY = MAP = -3 at T22-T23 (lsb=22, width=2)
    mov     rsi, 22
    mov     rdx, 2
    mov     rcx, PRIMARY_MAP
    call    set_field_val
    mov     r9, rax
    ; Set axis_yz at T21 (lsb=21, width=1)
    mov     rdi, r9
    mov     rsi, 21
    mov     rdx, 1
    mov     rcx, r12
    call    set_field_val
    mov     r9, rax
    ; Set axis_xz at T20 (lsb=20, width=1)
    mov     rdi, r9
    mov     rsi, 20
    mov     rdx, 1
    mov     rcx, r13
    call    set_field_val
    mov     r9, rax
    ; Set axis_xy at T19 (lsb=19, width=1)
    mov     rdi, r9
    mov     rsi, 19
    mov     rdx, 1
    mov     rcx, r14
    call    set_field_val
    mov     r9, rax
    ; Set mode_hint at T18 (lsb=18, width=1)
    mov     rdi, r9
    mov     rsi, 18
    mov     rdx, 1
    mov     rcx, rbx
    call    set_field_val
    mov     r9, rax
    ; Set payload at T0-T17 (lsb=0, width=18)
    mov     rdi, r9
    mov     rsi, 0
    mov     rdx, 18
    mov     rcx, r15
    call    set_field_val
    POP_CALLEE
    ret

; ── gm_mmid_compute ───────────────────────────────────────────────────────────
; Compute the MMID (TTree MAP word) for a given MMOE type index.
; Mirrors MMID._compute() from ternoo_gristmill.py.
;
; Input:  rdi = mmoe_type_index (0..MMOE_COUNT-1)
; Output: rax = TTree MAP word for this type
gm_mmid_compute:
    push    rbx
    push    r12
    push    r13
    push    r14
    mov     r12, rdi
    ; Bounds check
    cmp     r12, MMOE_COUNT
    jge     .invalid
    ; Get t1, t0 from mmoe_table
    ; Each entry = 8 qwords = 64 bytes
    ; Layout: [name_ptr(0), t1(8), t0(16), n_succ(24), succ0(32), succ1(40), succ2(48), succ3(56)]
    imul    rbx, r12, 64
    lea     r13, [rel mmoe_table]
    add     r13, rbx
    mov     r14, [r13 + 8]      ; t1
    mov     rbx, [r13 + 16]     ; t0
    ; Build UDP word: build_udp_word(t1, t0, offset=0, code_seg=0, data_seg=0)
    ; Then extract_tribbles to get ta
    ; UDP word layout from word.asm: PRIMARY_OPEN_B at T22-T23, qualifier at T18-T21
    ; For MMID we use the UDP subclass (t1, t0) at T21-T20 of the qualifier
    ; Replicate Python: udp = build_udp_word(t1, t0, 0, 0, 0)
    ;                   ta, _, _ = extract_tribbles(udp)
    ; Then build_ttree_mmid(ta, tb=0)
    ;
    ; build_udp_word: set PRIMARY=OPEN_B(-1) at T22-T23, t1 at T21, t0 at T20
    xor     rdi, rdi
    mov     rsi, 22
    mov     rdx, 2
    mov     rcx, PRIMARY_OPEN_B
    call    set_field_val
    mov     r9, rax
    mov     rdi, r9
    mov     rsi, 21
    mov     rdx, 1
    mov     rcx, r14            ; t1
    call    set_field_val
    mov     r9, rax
    mov     rdi, r9
    mov     rsi, 20
    mov     rdx, 1
    mov     rcx, rbx            ; t0
    call    set_field_val
    mov     r9, rax             ; r9 = UDP word
    ; extract_tribbles(udp) → ta = get_field_val(udp, 12, 6)
    mov     rdi, r9
    mov     rsi, 12
    mov     rdx, 6
    call    get_field_val
    mov     r14, rax            ; ta
    ; build_ttree_mmid(ta, tb=0)
    mov     rdi, r14
    mov     rsi, 0
    call    gm_build_ttree_mmid
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret
.invalid:
    xor     rax, rax
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── gm_mmid_distance ──────────────────────────────────────────────────────────
; Compute Manhattan distance between two MMID words in TTree space.
; Extracts (ta, tb) from each word and returns |ta_a - ta_b| + |tb_a - tb_b|.
;
; Input:  rdi = mmid_a
;         rsi = mmid_b
; Output: rax = Manhattan distance
gm_mmid_distance:
    push    rbx
    push    r12
    push    r13
    push    r14
    sub     rsp, 48             ; space for two tribble arrays
    mov     r12, rdi
    mov     r13, rsi
    ; extract_tribbles(mmid_a) → ta_a, tb_a
    mov     rdi, r12
    lea     rsi, [rsp]
    call    gm_extract_tribbles
    mov     r14, [rsp]          ; ta_a
    mov     rbx, [rsp + 8]      ; tb_a
    ; extract_tribbles(mmid_b) → ta_b, tb_b
    mov     rdi, r13
    lea     rsi, [rsp + 24]
    call    gm_extract_tribbles
    mov     rax, [rsp + 24]     ; ta_b
    mov     rcx, [rsp + 32]     ; tb_b
    ; |ta_a - ta_b|
    sub     r14, rax
    test    r14, r14
    jge     .ta_pos
    neg     r14
.ta_pos:
    ; |tb_a - tb_b|
    sub     rbx, rcx
    test    rbx, rbx
    jge     .tb_pos
    neg     rbx
.tb_pos:
    lea     rax, [r14 + rbx]
    add     rsp, 48
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── gm_mmid_proximity ─────────────────────────────────────────────────────────
; Fill an array with the n nearest MMOE type indices to a given MMID word.
; Uses Manhattan distance in TTree space.
;
; Input:  rdi = mmid word
;         rsi = pointer to int64_t[n] output array
;         rdx = n (number of nearest types to return)
; Output: rax = n (types written)
gm_mmid_proximity:
    PUSH_CALLEE
    mov     r12, rdi            ; query mmid
    mov     r13, rsi            ; output array
    mov     r14, rdx            ; n
    ; Compute MMID for each type and sort by distance
    ; Simple O(n*MMOE_COUNT) insertion: for each slot, find nearest unused
    sub     rsp, MMOE_COUNT*8   ; dist array
    sub     rsp, MMOE_COUNT*8   ; idx array
    lea     r15, [rsp + MMOE_COUNT*8]   ; dist array base
    mov     rbx, rsp                    ; idx array base
    ; Compute all distances
    xor     rcx, rcx
.dist_loop:
    cmp     rcx, MMOE_COUNT
    jge     .dist_done
    mov     [rbx + rcx*8], rcx  ; idx[i] = i
    push    rcx
    mov     rdi, rcx
    call    gm_mmid_compute
    mov     rdi, r12
    mov     rsi, rax
    call    gm_mmid_distance
    pop     rcx
    mov     [r15 + rcx*8], rax  ; dist[i]
    inc     rcx
    jmp     .dist_loop
.dist_done:
    ; Selection sort: find min n times
    xor     r9, r9              ; output index
.select_loop:
    cmp     r9, r14
    jge     .select_done
    ; Find minimum distance in remaining elements
    mov     r10, r9             ; min_idx = r9
    mov     r11, [r15 + r9*8]  ; min_dist
    mov     rcx, r9
    inc     rcx
.inner_loop:
    cmp     rcx, MMOE_COUNT
    jge     .inner_done
    mov     rax, [r15 + rcx*8]
    cmp     rax, r11
    jge     .not_min
    mov     r11, rax
    mov     r10, rcx
.not_min:
    inc     rcx
    jmp     .inner_loop
.inner_done:
    ; Store result
    mov     rax, [rbx + r10*8]
    mov     [r13 + r9*8], rax
    ; Swap dist and idx arrays to mark as used
    mov     rax, [r15 + r9*8]
    mov     rcx, [r15 + r10*8]
    mov     [r15 + r9*8], rcx
    mov     [r15 + r10*8], rax
    mov     rax, [rbx + r9*8]
    mov     rcx, [rbx + r10*8]
    mov     [rbx + r9*8], rcx
    mov     [rbx + r10*8], rax
    inc     r9
    jmp     .select_loop
.select_done:
    mov     rax, r14
    add     rsp, MMOE_COUNT*16
    POP_CALLEE
    ret

; ── gm_mmoe_name ──────────────────────────────────────────────────────────────
; Get the name string pointer for an MMOE type index.
; Input:  rdi = mmoe_type_index
; Output: rax = pointer to null-terminated name string (or NULL if OOB)
gm_mmoe_name:
    cmp     rdi, MMOE_COUNT
    jge     .oob
    imul    rax, rdi, 64
    lea     rcx, [rel mmoe_table]
    add     rax, rcx
    mov     rax, [rax]          ; name_ptr
    ret
.oob:
    xor     rax, rax
    ret

; ── gm_mmoe_successors ────────────────────────────────────────────────────────
; Get the successor type indices for an MMOE type.
; Input:  rdi = mmoe_type_index
;         rsi = pointer to int64_t[4] output array
; Output: rax = n_successors
gm_mmoe_successors:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    mov     r13, rsi
    cmp     r12, MMOE_COUNT
    jge     .oob
    imul    rbx, r12, 64
    lea     rax, [rel mmoe_table]
    add     rax, rbx
    mov     rcx, [rax + 24]     ; n_successors
    ; Copy successors
    xor     rbx, rbx
.copy:
    cmp     rbx, rcx
    jge     .done
    cmp     rbx, 4
    jge     .done
    mov     rdx, [rax + 32 + rbx*8]
    mov     [r13 + rbx*8], rdx
    inc     rbx
    jmp     .copy
.done:
    mov     rax, rcx
    pop     r13
    pop     r12
    pop     rbx
    ret
.oob:
    xor     rax, rax
    pop     r13
    pop     r12
    pop     rbx
    ret
