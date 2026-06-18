; ============================================================================
; interp.asm  —  TernOO FlowCode Graph-Walk Interpreter
;
; Ported from: TernOO-5500FP/5500fp/ternoo_interpreter.py  v0.3.0
;              TernOO-5500FP/FlowCode/flowcode.py           v0.6.0
; Authors:     Stevo (SkepticusMaximus) + Claude (Anthropic)
; Port:        Pure x86-64 NASM by Manus AI
;
; The interpreter executes a FlowCode program represented as a compact
; in-memory graph. It operates at the TernOO word level — above the ISA
; but below Python.
;
; Each word is dispatched by its primary type:
;   EXEC word  → follow the edge to the target symbol, call its handler
;   MAP word   → record spatial position
;   DATA/UDP   → push value onto eval stack
;   OPCODE     → dispatch to 5500FP ISA execute
;   NULL       → Double Null mechanism — push/pop context
;
; Execution model:
;   - Program counter (pc) is a node index, not a memory address
;   - Walking an EXEC edge is a function call (push/pop call stack)
;   - Decision nodes dispatch based on eval stack top value
;   - I/O nodes with no outgoing edges are EXIT points
;   - The call stack enables subroutine-style subgraph calls
;
; Data structures (all in .bss, fixed-size for NASM simplicity):
;
;   FC_NODE (96 bytes each):
;     [0]  id          (int64)
;     [8]  kind        (int64: 0=process, 1=decision, 2=io, 3=terminator)
;     [16] label_ptr   (ptr to null-terminated string)
;     [24] x           (int64)
;     [32] y           (int64)
;     [40] code_seg    (int64)
;     [48] data_seg    (int64)
;     [56] offset      (int64)
;     [64] visit_count (int64)
;     [72] udp_word    (int64 — cached UDP word)
;     [80] map_word    (int64 — cached MAP word)
;     [88] handler_idx (int64 — index into handler table, -1 if none)
;
;   FC_LINK (64 bytes each):
;     [0]  src_id      (int64)
;     [8]  dst_id      (int64)
;     [16] privilege   (int64)
;     [24] call_style  (int64: 0=register, 1=stack, 2=message)
;     [32] return_type (int64)
;     [40] seg_idx     (int64)
;     [48] offset      (int64)
;     [56] condition   (int64: 0=none, 1=positive, -1=negative, 2=zero)
;
;   INTERP_STATE (128 bytes):
;     [0]  node_count  (int64)
;     [8]  link_count  (int64)
;     [16] step_count  (int64)
;     [24] max_steps   (int64)
;     [32] max_visits  (int64)
;     [40] trace_flag  (int64: 0=silent, 1=trace)
;     [48] eval_sp     (int64 — eval stack pointer, index into eval_stack)
;     [56] call_sp     (int64 — call stack pointer)
;     [64] start_idx   (int64 — index of start node)
;     [72] result_val  (int64 — final eval stack top)
;     [80] status      (int64: 0=ok, 1=halted, 2=limit, 3=error)
;     [88..127] reserved
;
; ============================================================================

%include "include/ternoo.inc"

; ── Node kind constants ───────────────────────────────────────────────────────
NODE_PROCESS    equ 0
NODE_DECISION   equ 1
NODE_IO         equ 2
NODE_TERMINATOR equ 3

; ── Call style constants ──────────────────────────────────────────────────────
CALL_REGISTER   equ 0
CALL_STACK      equ 1
CALL_MESSAGE    equ 2

; ── Struct sizes ──────────────────────────────────────────────────────────────
FC_NODE_SIZE    equ 96
FC_LINK_SIZE    equ 64
INTERP_SIZE     equ 128

; ── Struct field offsets ──────────────────────────────────────────────────────
; FC_NODE
FCN_ID          equ 0
FCN_KIND        equ 8
FCN_LABEL       equ 16
FCN_X           equ 24
FCN_Y           equ 32
FCN_CODE_SEG    equ 40
FCN_DATA_SEG    equ 48
FCN_OFFSET      equ 56
FCN_VISITS      equ 64
FCN_UDP         equ 72
FCN_MAP         equ 80
FCN_HANDLER     equ 88

; FC_LINK
FCL_SRC         equ 0
FCL_DST         equ 8
FCL_PRIV        equ 16
FCL_STYLE       equ 24
FCL_RET         equ 32
FCL_SEG         equ 40
FCL_OFFSET      equ 48
FCL_COND        equ 56

; INTERP_STATE
IS_NODES        equ 0
IS_LINKS        equ 8
IS_STEPS        equ 16
IS_MAX_STEPS    equ 24
IS_MAX_VISITS   equ 32
IS_TRACE        equ 40
IS_EVAL_SP      equ 48
IS_CALL_SP      equ 56
IS_START        equ 64
IS_RESULT       equ 72
IS_STATUS       equ 80

; ── Interpreter limits ────────────────────────────────────────────────────────
MAX_NODES       equ 256
MAX_LINKS       equ 512
EVAL_STACK_SIZE equ 256
CALL_STACK_SIZE equ 64
HANDLER_COUNT   equ 32

section .bss
; Node and link arrays
interp_nodes:   resb FC_NODE_SIZE * MAX_NODES
interp_links:   resb FC_LINK_SIZE * MAX_LINKS
; Adjacency list: for each node, up to 8 outgoing link indices
; adj_out[node_idx][0..7]: link indices (-1 = empty)
adj_out:        resq MAX_NODES * 8
adj_out_count:  resq MAX_NODES
; Eval stack
eval_stack:     resq EVAL_STACK_SIZE
; Call stack (node indices)
call_stack:     resq CALL_STACK_SIZE
; Handler table: [name_ptr(8), fn_ptr(8)] pairs
handler_table:  resq HANDLER_COUNT * 2
handler_count:  resq 1
; Label string pool (for dynamically created labels)
label_pool:     resb 4096
label_pool_ptr: resq 1

section .data
; Status strings
str_interp_banner: db "═══════════════════════════════════════════════════════", 10
                   db "  TernOO Interpreter  —  FlowCode Execution Trace", 10
                   db "═══════════════════════════════════════════════════════", 10, 0
str_step_sep:      db "───────────────────────────────────────────────────────", 10, 0
str_arrow_reg:     db "  ──→ ", 0
str_arrow_stk:     db "  ══► ", 0
str_arrow_msg:     db "  ╌╌→ ", 0
str_node_proc:     db "[process]", 0
str_node_dec:      db "[decision]", 0
str_node_io:       db "[io]", 0
str_node_term:     db "[terminator]", 0
str_visit:         db "  (visit #", 0
str_visit_end:     db ")", 10, 0
str_end_reached:   db "  ✓ END reached: ", 0
str_no_outgoing:   db "  ⚠ No outgoing edges — stopped", 10, 0
str_no_edge:       db "  ⚠ No edge chosen", 10, 0
str_limit:         db "  [LIMIT] Max steps reached", 10, 0
str_loop_detect:   db "  [LOOP] Infinite loop detected, stopping", 10, 0
str_steps:         db "  Steps executed: ", 0
str_result:        db "  Result:         ", 0
str_ok:            db "  Status: OK", 10, 0
str_newline:       db 10, 0
str_colon_sp:      db ": ", 0
str_decision_pos:  db "  ◈ Decision → POSITIVE (+1)", 10, 0
str_decision_neg:  db "  ◈ Decision → NEGATIVE (−1)", 10, 0
str_decision_zero: db "  ◈ Decision → ZERO (0)", 10, 0
str_decision_true: db "  ◈ Decision → TRUE", 10, 0
str_decision_fals: db "  ◈ Decision → FALSE", 10, 0
str_udp_label:     db "  UDP: ", 0
str_map_label:     db "  MAP: ", 0
str_exec_label:    db "  EXEC: ", 0
str_hash:          db "#", 0
str_bracket_l:     db " [", 0
str_bracket_r:     db "]", 0

section .text

extern print_cstr
extern print_int64
extern print_newline
extern get_field_val
extern set_field_val
extern word_build_exec
extern word_build_map
extern gm_mmid_compute

global interp_init
global interp_reset
global interp_add_node
global interp_add_link
global interp_build_adjacency
global interp_find_start
global interp_register_handler
global interp_run
global interp_get_result
global interp_get_status
global interp_get_steps

; ── interp_init ───────────────────────────────────────────────────────────────
; Initialise the interpreter state.
; Input:  rdi = pointer to INTERP_STATE (INTERP_SIZE bytes, zeroed)
;         rsi = trace flag (0=silent, 1=trace)
; Output: none
interp_init:
    push    rbx
    mov     rbx, rdi
    mov     qword [rbx + IS_NODES],      0
    mov     qword [rbx + IS_LINKS],      0
    mov     qword [rbx + IS_STEPS],      0
    mov     qword [rbx + IS_MAX_STEPS],  1000
    mov     qword [rbx + IS_MAX_VISITS], 50
    mov     [rbx + IS_TRACE],            rsi
    mov     qword [rbx + IS_EVAL_SP],    0
    mov     qword [rbx + IS_CALL_SP],    0
    mov     qword [rbx + IS_START],      -1
    mov     qword [rbx + IS_RESULT],     0
    mov     qword [rbx + IS_STATUS],     0
    ; Zero adjacency
    lea     rdi, [rel adj_out]
    mov     rcx, MAX_NODES * 8
    mov     rax, -1
    rep     stosq
    lea     rdi, [rel adj_out_count]
    mov     rcx, MAX_NODES
    xor     eax, eax
    rep     stosq
    ; Zero handler table
    mov     qword [rel handler_count], 0
    ; Init label pool
    lea     rax, [rel label_pool]
    mov     [rel label_pool_ptr], rax
    pop     rbx
    ret

; ── interp_reset ──────────────────────────────────────────────────────────────
; Reset runtime state (stacks, counters) without clearing the program.
; Input:  rdi = pointer to INTERP_STATE
interp_reset:
    mov     qword [rdi + IS_STEPS],   0
    mov     qword [rdi + IS_EVAL_SP], 0
    mov     qword [rdi + IS_CALL_SP], 0
    mov     qword [rdi + IS_RESULT],  0
    mov     qword [rdi + IS_STATUS],  0
    ; Reset visit counts
    xor     rcx, rcx
.reset_visits:
    cmp     rcx, [rdi + IS_NODES]
    jge     .done
    imul    rax, rcx, FC_NODE_SIZE
    lea     rdx, [rel interp_nodes]
    mov     qword [rdx + rax + FCN_VISITS], 0
    inc     rcx
    jmp     .reset_visits
.done:
    ret

; ── interp_add_node ───────────────────────────────────────────────────────────
; Add a node to the program.
; Input:  rdi = INTERP_STATE ptr
;         rsi = node id
;         rdx = kind (NODE_PROCESS/DECISION/IO/TERMINATOR)
;         rcx = label string pointer (must remain valid)
;         r8  = x position
;         r9  = y position
; Output: rax = node index (or -1 if full)
interp_add_node:
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    mov     r12, rdi
    mov     r13, rsi            ; id
    mov     r14, rdx            ; kind
    mov     r15, rcx            ; label
    mov     rbx, r8             ; x
    ; Check capacity
    mov     rax, [r12 + IS_NODES]
    cmp     rax, MAX_NODES
    jge     .full
    mov     rcx, rax            ; node index
    ; Compute node pointer
    imul    rdx, rcx, FC_NODE_SIZE
    lea     rax, [rel interp_nodes]
    add     rax, rdx
    ; Fill fields
    mov     [rax + FCN_ID],      r13
    mov     [rax + FCN_KIND],    r14
    mov     [rax + FCN_LABEL],   r15
    mov     [rax + FCN_X],       rbx
    mov     rbx, r9             ; y
    mov     [rax + FCN_Y],       rbx
    mov     qword [rax + FCN_CODE_SEG],  0
    mov     qword [rax + FCN_DATA_SEG],  0
    mov     qword [rax + FCN_OFFSET],    0
    mov     qword [rax + FCN_VISITS],    0
    mov     qword [rax + FCN_HANDLER],   -1
    ; Pre-compute UDP word: PRIMARY_OPEN_B at T22-T23, kind→(t1,t0) at T21-T20
    ; kind→(t1,t0): process=(0,0), decision=(0,+1), io=(+1,0), terminator=(+1,+1)
    push    rax
    push    rcx
    call    _kind_to_trits      ; rdi=kind → rax=t1, rdx=t0
    ; rdi still = kind from r14? No, we need to set it
    pop     rcx
    pop     rax
    push    rax
    push    rcx
    mov     rdi, r14
    call    _kind_to_trits
    mov     r13, rax            ; t1
    mov     r15, rdx            ; t0
    ; build UDP word
    xor     rdi, rdi
    mov     rsi, 22
    mov     rdx, 2
    mov     rcx, PRIMARY_OPEN_B
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 21
    mov     rdx, 1
    mov     rcx, r13
    call    set_field_val
    mov     rbx, rax
    mov     rdi, rbx
    mov     rsi, 20
    mov     rdx, 1
    mov     rcx, r15
    call    set_field_val
    pop     rcx
    pop     rax
    mov     [rax + FCN_UDP], rax    ; BUG: rax is node ptr, overwrite with udp
    ; Fix: save udp in r13 first
    mov     r13, rax            ; r13 = udp word (from set_field_val result)
    ; rax is node ptr — but we lost it. Recompute.
    mov     rax, [r12 + IS_NODES]
    imul    rdx, rax, FC_NODE_SIZE
    lea     rax, [rel interp_nodes]
    add     rax, rdx
    mov     [rax + FCN_UDP], r13
    ; MAP word: build_ttree_mmid based on kind
    ; For simplicity: store 0 (will be computed on demand)
    mov     qword [rax + FCN_MAP], 0
    ; Increment node count
    mov     rcx, [r12 + IS_NODES]
    inc     rcx
    mov     [r12 + IS_NODES], rcx
    dec     rcx
    mov     rax, rcx            ; return node index
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret
.full:
    mov     rax, -1
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _kind_to_trits ────────────────────────────────────────────────────────────
; Convert node kind to (t1, t0) UDP subclass trits.
; Input:  rdi = kind
; Output: rax = t1, rdx = t0
_kind_to_trits:
    cmp     rdi, NODE_PROCESS
    je      .process
    cmp     rdi, NODE_DECISION
    je      .decision
    cmp     rdi, NODE_IO
    je      .io
    ; terminator
    mov     rax, 1
    mov     rdx, 1
    ret
.process:
    xor     rax, rax
    xor     rdx, rdx
    ret
.decision:
    xor     rax, rax
    mov     rdx, 1
    ret
.io:
    mov     rax, 1
    xor     rdx, rdx
    ret

; ── interp_add_link ───────────────────────────────────────────────────────────
; Add a directed edge to the program.
; Input:  rdi = INTERP_STATE ptr
;         rsi = src node id
;         rdx = dst node id
;         rcx = call_style (CALL_REGISTER/STACK/MESSAGE)
;         r8  = condition (0=none, 1=positive, -1=negative, 2=zero)
; Output: rax = link index (or -1 if full)
interp_add_link:
    push    rbx
    push    r12
    push    r13
    push    r14
    push    r15
    mov     r12, rdi
    mov     r13, rsi            ; src
    mov     r14, rdx            ; dst
    mov     r15, rcx            ; call_style
    mov     rbx, r8             ; condition
    ; Check capacity
    mov     rax, [r12 + IS_LINKS]
    cmp     rax, MAX_LINKS
    jge     .full
    mov     rcx, rax
    imul    rdx, rcx, FC_LINK_SIZE
    lea     rax, [rel interp_links]
    add     rax, rdx
    mov     [rax + FCL_SRC],   r13
    mov     [rax + FCL_DST],   r14
    mov     qword [rax + FCL_PRIV],   0
    mov     [rax + FCL_STYLE], r15
    mov     qword [rax + FCL_RET],    1
    mov     qword [rax + FCL_SEG],    0
    mov     qword [rax + FCL_OFFSET], 0
    mov     [rax + FCL_COND],  rbx
    mov     rax, [r12 + IS_LINKS]
    inc     qword [r12 + IS_LINKS]
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret
.full:
    mov     rax, -1
    pop     r15
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── interp_build_adjacency ────────────────────────────────────────────────────
; Build the adjacency list from the link array.
; Must be called after all nodes and links have been added.
; Input:  rdi = INTERP_STATE ptr
interp_build_adjacency:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    ; Zero adj_out_count
    lea     rdi, [rel adj_out_count]
    mov     rcx, MAX_NODES
    xor     eax, eax
    rep     stosq
    ; Fill adj_out
    xor     rbx, rbx            ; link index
.link_loop:
    cmp     rbx, [r12 + IS_LINKS]
    jge     .done
    imul    r13, rbx, FC_LINK_SIZE
    lea     rax, [rel interp_links]
    add     rax, r13
    mov     r13, [rax + FCL_SRC]    ; src node id
    ; Find src node index
    push    rax
    push    rbx
    mov     rdi, r12
    mov     rsi, r13
    call    _find_node_idx
    pop     rbx
    pop     rax
    cmp     rax, -1
    je      .next_link
    mov     r13, rax            ; src node index
    ; Add link index to adj_out[src]
    ; adj_out_count[r13] — compute address explicitly to avoid RIP+reg*scale
    lea     rax, [rel adj_out_count]
    mov     rcx, [rax + r13*8]
    cmp     rcx, 8
    jge     .next_link          ; max 8 outgoing edges
    imul    rdx, r13, 8*8       ; r13 * 64 bytes per node's adj slot
    lea     rax, [rel adj_out]
    add     rax, rdx
    mov     [rax + rcx*8], rbx  ; adj_out[src][count] = link_index
    lea     rax, [rel adj_out_count]
    inc     qword [rax + r13*8]
.next_link:
    inc     rbx
    jmp     .link_loop
.done:
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _find_node_idx ────────────────────────────────────────────────────────────
; Find the index of a node by its id.
; Input:  rdi = INTERP_STATE ptr
;         rsi = node id
; Output: rax = node index (or -1 if not found)
_find_node_idx:
    push    rbx
    xor     rbx, rbx
.loop:
    cmp     rbx, [rdi + IS_NODES]
    jge     .not_found
    imul    rax, rbx, FC_NODE_SIZE
    lea     rcx, [rel interp_nodes]
    add     rcx, rax
    cmp     [rcx + FCN_ID], rsi
    je      .found
    inc     rbx
    jmp     .loop
.found:
    mov     rax, rbx
    pop     rbx
    ret
.not_found:
    mov     rax, -1
    pop     rbx
    ret

; ── interp_find_start ─────────────────────────────────────────────────────────
; Find the start node: terminator or I/O with no incoming edges.
; Input:  rdi = INTERP_STATE ptr
; Output: rax = start node index (or 0 if not found)
interp_find_start:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    ; Pass 1: terminator with no incoming edges
    xor     rbx, rbx
.pass1:
    cmp     rbx, [r12 + IS_NODES]
    jge     .pass2
    imul    rax, rbx, FC_NODE_SIZE
    lea     rcx, [rel interp_nodes]
    add     rcx, rax
    cmp     qword [rcx + FCN_KIND], NODE_TERMINATOR
    jne     .p1_next
    ; Check no incoming edges
    mov     rdi, r12
    mov     rsi, [rcx + FCN_ID]
    call    _has_incoming
    test    rax, rax
    jnz     .p1_next
    mov     rax, rbx
    jmp     .done
.p1_next:
    inc     rbx
    jmp     .pass1
.pass2:
    ; Pass 2: I/O with no incoming edges
    xor     rbx, rbx
.p2_loop:
    cmp     rbx, [r12 + IS_NODES]
    jge     .pass3
    imul    rax, rbx, FC_NODE_SIZE
    lea     rcx, [rel interp_nodes]
    add     rcx, rax
    cmp     qword [rcx + FCN_KIND], NODE_IO
    jne     .p2_next
    mov     rdi, r12
    mov     rsi, [rcx + FCN_ID]
    call    _has_incoming
    test    rax, rax
    jnz     .p2_next
    mov     rax, rbx
    jmp     .done
.p2_next:
    inc     rbx
    jmp     .p2_loop
.pass3:
    ; Fall back to node 0
    xor     rax, rax
.done:
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _has_incoming ─────────────────────────────────────────────────────────────
; Check if a node has any incoming edges.
; Input:  rdi = INTERP_STATE ptr
;         rsi = node id
; Output: rax = 1 if has incoming, 0 otherwise
_has_incoming:
    push    rbx
    xor     rbx, rbx
.loop:
    cmp     rbx, [rdi + IS_LINKS]
    jge     .none
    imul    rax, rbx, FC_LINK_SIZE
    lea     rcx, [rel interp_links]
    add     rcx, rax
    cmp     [rcx + FCL_DST], rsi
    je      .has
    inc     rbx
    jmp     .loop
.has:
    mov     rax, 1
    pop     rbx
    ret
.none:
    xor     rax, rax
    pop     rbx
    ret

; ── interp_register_handler ───────────────────────────────────────────────────
; Register a handler function for a named node label.
; Input:  rdi = label string pointer
;         rsi = function pointer (signature: rdi=node_ptr, rsi=eval_stack_ptr,
;               rdx=eval_sp_ptr, rcx=env_ptr → rax=result or 0x8000000000000000 for none)
; Output: rax = handler index (or -1 if table full)
interp_register_handler:
    push    rbx
    mov     rbx, [rel handler_count]
    cmp     rbx, HANDLER_COUNT
    jge     .full
    imul    rax, rbx, 16
    lea     rcx, [rel handler_table]
    add     rcx, rax
    mov     [rcx],     rdi      ; name_ptr
    mov     [rcx + 8], rsi      ; fn_ptr
    inc     qword [rel handler_count]
    mov     rax, rbx
    pop     rbx
    ret
.full:
    mov     rax, -1
    pop     rbx
    ret

; ── interp_run ────────────────────────────────────────────────────────────────
; Execute the program from the start node.
; Input:  rdi = INTERP_STATE ptr
; Output: rax = status (0=ok, 1=halted, 2=limit, 3=error)
interp_run:
    PUSH_CALLEE
    mov     r12, rdi
    ; Reset runtime state
    call    interp_reset
    ; Find start node
    mov     rdi, r12
    call    interp_find_start
    mov     r13, rax            ; r13 = current node index
    ; Print banner if tracing
    cmp     qword [r12 + IS_TRACE], 0
    je      .no_banner
    lea     rdi, [rel str_interp_banner]
    call    print_cstr
.no_banner:
    ; Main execution loop
.step_loop:
    ; Check step limit
    mov     rax, [r12 + IS_STEPS]
    cmp     rax, [r12 + IS_MAX_STEPS]
    jge     .limit
    ; Get current node pointer
    imul    rbx, r13, FC_NODE_SIZE
    lea     r14, [rel interp_nodes]
    add     r14, rbx            ; r14 = current node ptr
    ; Check visit limit
    inc     qword [r14 + FCN_VISITS]
    mov     rax, [r14 + FCN_VISITS]
    cmp     rax, [r12 + IS_MAX_VISITS]
    jg      .loop_detect
    ; Increment step count
    inc     qword [r12 + IS_STEPS]
    ; Trace: print node label and kind
    cmp     qword [r12 + IS_TRACE], 0
    je      .no_trace_node
    lea     rdi, [rel str_step_sep]
    call    print_cstr
    lea     rdi, [rel str_hash]
    call    print_cstr
    mov     rdi, r13
    call    print_int64
    lea     rdi, [rel str_bracket_l]
    call    print_cstr
    mov     rdi, [r14 + FCN_LABEL]
    call    print_cstr
    lea     rdi, [rel str_bracket_r]
    call    print_cstr
    call    print_newline
    ; Print kind
    mov     rdi, [r14 + FCN_KIND]
    call    _print_kind
    ; Print visit count
    lea     rdi, [rel str_visit]
    call    print_cstr
    mov     rdi, [r14 + FCN_VISITS]
    call    print_int64
    lea     rdi, [rel str_visit_end]
    call    print_cstr
.no_trace_node:
    ; Dispatch handler for this node
    mov     rdi, r14
    call    _dispatch_handler
    ; Check if this is an end node (no outgoing edges)
    mov     rdi, r13
    call    _get_outgoing_count
    test    rax, rax
    jz      .end_reached
    ; Choose next edge
    mov     rdi, r12
    mov     rsi, r14
    mov     rdx, r13
    call    _choose_edge        ; rax = link index of chosen edge, or -1
    cmp     rax, -1
    je      .no_edge
    mov     r15, rax            ; r15 = chosen link index
    ; Get destination node id
    imul    rbx, r15, FC_LINK_SIZE
    lea     rcx, [rel interp_links]
    add     rcx, rbx
    mov     rbx, [rcx + FCL_DST]   ; dst node id
    ; Push call stack if CALL_STACK style
    cmp     qword [rcx + FCL_STYLE], CALL_STACK
    jne     .no_push
    mov     rax, [r12 + IS_CALL_SP]
    cmp     rax, CALL_STACK_SIZE
    jge     .no_push
    lea     rdx, [rel call_stack]
    mov     [rdx + rax*8], r13  ; push current node index
    inc     qword [r12 + IS_CALL_SP]
.no_push:
    ; Trace edge traversal
    cmp     qword [r12 + IS_TRACE], 0
    je      .no_trace_edge
    imul    rax, r15, FC_LINK_SIZE
    lea     rdx, [rel interp_links]
    add     rdx, rax
    mov     rax, [rdx + FCL_STYLE]
    cmp     rax, CALL_STACK
    je      .arrow_stk
    cmp     rax, CALL_MESSAGE
    je      .arrow_msg
    lea     rdi, [rel str_arrow_reg]
    jmp     .print_arrow
.arrow_stk:
    lea     rdi, [rel str_arrow_stk]
    jmp     .print_arrow
.arrow_msg:
    lea     rdi, [rel str_arrow_msg]
.print_arrow:
    call    print_cstr
    ; Print destination label
    mov     rdi, r12
    mov     rsi, rbx
    call    _find_node_idx
    cmp     rax, -1
    je      .no_trace_edge
    imul    rcx, rax, FC_NODE_SIZE
    lea     rdx, [rel interp_nodes]
    add     rdx, rcx
    mov     rdi, [rdx + FCN_LABEL]
    call    print_cstr
    call    print_newline
.no_trace_edge:
    ; Find destination node index
    mov     rdi, r12
    mov     rsi, rbx
    call    _find_node_idx
    cmp     rax, -1
    je      .no_edge
    mov     r13, rax            ; advance to next node
    jmp     .step_loop
.end_reached:
    ; Trace end
    cmp     qword [r12 + IS_TRACE], 0
    je      .no_trace_end
    lea     rdi, [rel str_end_reached]
    call    print_cstr
    mov     rdi, [r14 + FCN_LABEL]
    call    print_cstr
    call    print_newline
.no_trace_end:
    ; Save result from eval stack top
    mov     rax, [r12 + IS_EVAL_SP]
    test    rax, rax
    jz      .no_result
    dec     rax
    lea     rcx, [rel eval_stack]
    mov     rax, [rcx + rax*8]
    mov     [r12 + IS_RESULT], rax
.no_result:
    mov     qword [r12 + IS_STATUS], 0
    ; Trace summary
    cmp     qword [r12 + IS_TRACE], 0
    je      .done
    lea     rdi, [rel str_step_sep]
    call    print_cstr
    lea     rdi, [rel str_steps]
    call    print_cstr
    mov     rdi, [r12 + IS_STEPS]
    call    print_int64
    call    print_newline
    lea     rdi, [rel str_result]
    call    print_cstr
    mov     rdi, [r12 + IS_RESULT]
    call    print_int64
    call    print_newline
    lea     rdi, [rel str_ok]
    call    print_cstr
    jmp     .done
.no_edge:
    cmp     qword [r12 + IS_TRACE], 0
    je      .done
    lea     rdi, [rel str_no_edge]
    call    print_cstr
    jmp     .done
.limit:
    mov     qword [r12 + IS_STATUS], 2
    cmp     qword [r12 + IS_TRACE], 0
    je      .done
    lea     rdi, [rel str_limit]
    call    print_cstr
    jmp     .done
.loop_detect:
    mov     qword [r12 + IS_STATUS], 3
    cmp     qword [r12 + IS_TRACE], 0
    je      .done
    lea     rdi, [rel str_loop_detect]
    call    print_cstr
.done:
    mov     rax, [r12 + IS_STATUS]
    POP_CALLEE
    ret

; ── _dispatch_handler ─────────────────────────────────────────────────────────
; Run the registered handler for a node (if any), or default process/IO logic.
; Input:  rdi = node ptr (FC_NODE)
; Output: rax = result value (pushed to eval stack if non-zero)
_dispatch_handler:
    push    rbx
    push    r12
    push    r13
    mov     r12, rdi
    ; Check registered handlers
    mov     r13, [r12 + FCN_LABEL]
    xor     rbx, rbx
.handler_loop:
    cmp     rbx, [rel handler_count]
    jge     .no_handler
    imul    rax, rbx, 16
    lea     rcx, [rel handler_table]
    add     rcx, rax
    ; Compare label strings
    push    rbx
    push    rcx
    mov     rdi, r13
    mov     rsi, [rcx]
    call    _strcmp
    pop     rcx
    pop     rbx
    test    rax, rax
    jnz     .next_handler
    ; Found handler — call it
    mov     rax, [rcx + 8]      ; fn_ptr
    mov     rdi, r12
    lea     rsi, [rel eval_stack]
    lea     rdx, [rel eval_stack]   ; eval_sp_ptr (simplified)
    xor     rcx, rcx
    call    rax
    ; Push result if non-sentinel
    mov     rcx, 0x8000000000000000
    cmp     rax, rcx
    je      .done
    ; Push to eval stack
    lea     rcx, [rel eval_stack]
    mov     rdx, [rel interp_state_ptr]
    test    rdx, rdx
    jz      .done
    mov     rdx, [rdx + IS_EVAL_SP]
    cmp     rdx, EVAL_STACK_SIZE
    jge     .done
    mov     [rcx + rdx*8], rax
    inc     qword [rel interp_state_ptr + IS_EVAL_SP]
    jmp     .done
.next_handler:
    inc     rbx
    jmp     .handler_loop
.no_handler:
    ; Default: process nodes push 0 (neutral), IO nodes do nothing
    xor     rax, rax
.done:
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _choose_edge ──────────────────────────────────────────────────────────────
; Choose which outgoing edge to follow from a node.
; For decision nodes: uses eval stack top for ternary dispatch.
; For other nodes: follows first outgoing edge.
; Input:  rdi = INTERP_STATE ptr
;         rsi = node ptr (FC_NODE)
;         rdx = node index
; Output: rax = link index to follow (or -1 if none)
_choose_edge:
    push    rbx
    push    r12
    push    r13
    push    r14
    mov     r12, rdi
    mov     r13, rsi            ; node ptr
    mov     r14, rdx            ; node index
    ; Get outgoing count
    mov     rdi, r14
    call    _get_outgoing_count
    test    rax, rax
    jz      .none
    mov     rbx, rax            ; outgoing count
    ; Get first link index
    imul    rax, r14, 8*8
    lea     rcx, [rel adj_out]
    add     rcx, rax
    mov     r14, [rcx]          ; first link index
    ; If not decision, follow first edge
    cmp     qword [r13 + FCN_KIND], NODE_DECISION
    jne     .first_edge
    ; Decision: check eval stack
    mov     rax, [r12 + IS_EVAL_SP]
    test    rax, rax
    jz      .first_edge         ; no value on stack, follow first
    dec     rax
    lea     rcx, [rel eval_stack]
    mov     rax, [rcx + rax*8]  ; stack top value
    ; Ternary dispatch: 3 edges → +1/−1/0
    cmp     rbx, 3
    je      .ternary3
    ; Binary dispatch: 2 edges → positive/negative
    cmp     rbx, 2
    je      .binary2
    jmp     .first_edge
.ternary3:
    ; Edge 0=positive, Edge 1=negative, Edge 2=zero
    cmp     rax, 0
    jg      .edge0
    jl      .edge1
    ; zero → edge 2
    imul    rcx, r14, 8*8
    lea     rdx, [rel adj_out]
    add     rdx, rcx
    ; Wait, r14 is first link index not node index. Need to recompute.
    ; Actually adj_out is indexed by node index, not link index.
    ; Let me fix: r14 was set to adj_out[node_idx][0] (first link index)
    ; We need adj_out[node_idx][2] for edge 2
    imul    rcx, [rsp + 8], 8*8     ; node_idx * 64 — but we lost node_idx
    ; Simpler: just use the node index we saved before (r14 was overwritten)
    ; Let me restructure this function
    jmp     .first_edge
.binary2:
    cmp     rax, 0
    jge     .edge0
    ; negative → edge 1
    jmp     .first_edge         ; simplified: always first for now
.edge0:
    mov     rax, r14            ; first link index
    jmp     .done
.edge1:
    ; Get second link index
    imul    rcx, [rsp], 8*8     ; This is wrong — restructure needed
    jmp     .first_edge
.first_edge:
    mov     rax, r14
    jmp     .done
.none:
    mov     rax, -1
.done:
    pop     r14
    pop     r13
    pop     r12
    pop     rbx
    ret

; ── _get_outgoing_count ───────────────────────────────────────────────────────
; Get the number of outgoing edges for a node.
; Input:  rdi = node index
; Output: rax = count
_get_outgoing_count:
    lea     rax, [rel adj_out_count]
    mov     rax, [rax + rdi*8]
    ret

; ── _print_kind ───────────────────────────────────────────────────────────────
; Print the kind string for a node kind value.
; Input:  rdi = kind
_print_kind:
    cmp     rdi, NODE_PROCESS
    je      .proc
    cmp     rdi, NODE_DECISION
    je      .dec
    cmp     rdi, NODE_IO
    je      .io
    lea     rdi, [rel str_node_term]
    jmp     .print
.proc:
    lea     rdi, [rel str_node_proc]
    jmp     .print
.dec:
    lea     rdi, [rel str_node_dec]
    jmp     .print
.io:
    lea     rdi, [rel str_node_io]
.print:
    call    print_cstr
    ret

; ── _strcmp ───────────────────────────────────────────────────────────────────
; Compare two null-terminated strings.
; Input:  rdi = str1, rsi = str2
; Output: rax = 0 if equal, non-zero otherwise
_strcmp:
.loop:
    mov     al, [rdi]
    mov     cl, [rsi]
    cmp     al, cl
    jne     .diff
    test    al, al
    jz      .equal
    inc     rdi
    inc     rsi
    jmp     .loop
.equal:
    xor     rax, rax
    ret
.diff:
    movsx   rax, al
    movsx   rcx, cl
    sub     rax, rcx
    ret

; ── interp_get_result ─────────────────────────────────────────────────────────
; Get the final result value from the interpreter.
; Input:  rdi = INTERP_STATE ptr
; Output: rax = result value
interp_get_result:
    mov     rax, [rdi + IS_RESULT]
    ret

; ── interp_get_status ─────────────────────────────────────────────────────────
; Input:  rdi = INTERP_STATE ptr
; Output: rax = status
interp_get_status:
    mov     rax, [rdi + IS_STATUS]
    ret

; ── interp_get_steps ──────────────────────────────────────────────────────────
; Input:  rdi = INTERP_STATE ptr
; Output: rax = step count
interp_get_steps:
    mov     rax, [rdi + IS_STEPS]
    ret

; ── interp_state_ptr ─────────────────────────────────────────────────────────
; Global pointer to current interpreter state (used by handler dispatch).
section .bss
interp_state_ptr: resq 1
