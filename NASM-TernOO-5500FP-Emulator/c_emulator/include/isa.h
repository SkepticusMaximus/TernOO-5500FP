/*
 * isa.h — 5500FP Instruction Set Architecture Definitions
 *
 * Instruction format: 24 trits per instruction
 *
 * Instruction fields (trit positions, LST = position 0):
 *
 *  R-Type:  [23..18]=opcode(6) [17..14]=rd(4) [13..10]=rs1(4) [9..6]=rs2(4) [5..0]=func(6)
 *  I-Type:  [23..18]=opcode(6) [17..14]=rd(4) [13..10]=rs1(4) [9..0]=imm10(10)
 *  J-Type:  [23..18]=opcode(6) [17..0]=imm18(18)
 *  B-Type:  [23..18]=opcode(6) [17..14]=rs1(4) [13..10]=rs2(4) [9..0]=imm10(10)
 *
 * Opcodes are 6-trit balanced ternary values (range: -364 to +364).
 * We use integer constants for opcodes.
 */

#ifndef ISA_H
#define ISA_H

#include <stdint.h>

/* -----------------------------------------------------------------------
 * Instruction format type codes
 * --------------------------------------------------------------------- */
typedef enum {
    FMT_R = 0,
    FMT_I = 1,
    FMT_J = 2,
    FMT_B = 3,
} inst_fmt_t;

/* -----------------------------------------------------------------------
 * Opcode definitions (6-trit balanced ternary integer values)
 * We use a simple sequential assignment for clarity.
 * --------------------------------------------------------------------- */
typedef enum {
    /* --- ALU R-Type --- */
    OP_ADD   =  1,   /* ADD  Rd, Rs1, Rs2   : Rd = Rs1 + Rs2              */
    OP_SUB   =  2,   /* SUB  Rd, Rs1, Rs2   : Rd = Rs1 - Rs2              */
    OP_MUL   =  3,   /* MUL  Rd, Rs1, Rs2   : Rd = Rs1 * Rs2              */
    OP_DIV   =  4,   /* DIV  Rd, Rs1, Rs2   : Rd = Rs1 / Rs2              */
    OP_MOD   =  5,   /* MOD  Rd, Rs1, Rs2   : Rd = Rs1 % Rs2              */
    OP_MIN   =  6,   /* MIN  Rd, Rs1, Rs2   : Rd = min(Rs1, Rs2)          */
    OP_MAX   =  7,   /* MAX  Rd, Rs1, Rs2   : Rd = max(Rs1, Rs2)          */
    OP_AND   =  8,   /* AND  Rd, Rs1, Rs2   : Rd = ternary_and(Rs1, Rs2)  */
    OP_OR    =  9,   /* OR   Rd, Rs1, Rs2   : Rd = ternary_or(Rs1, Rs2)   */
    OP_CON   = 10,   /* CON  Rd, Rs1, Rs2   : Rd = consensus(Rs1, Rs2)    */
    OP_SHL   = 11,   /* SHL  Rd, Rs1, Rs2   : Rd = Rs1 << Rs2 (trits)     */
    OP_SHR   = 12,   /* SHR  Rd, Rs1, Rs2   : Rd = Rs1 >> Rs2 (trits)     */
    OP_CMP   = 13,   /* CMP  Rd, Rs1, Rs2   : Rd = sign(Rs1 - Rs2)        */
    OP_MOV   = 14,   /* MOV  Rd, Rs1        : Rd = Rs1                    */
    OP_INV   = 15,   /* INV  Rd, Rs1        : Rd = -Rs1 (trit inversion)  */
    OP_ABS   = 16,   /* ABS  Rd, Rs1        : Rd = |Rs1|                  */
    OP_SIGN  = 17,   /* SIGN Rd, Rs1        : Rd = sign(Rs1)              */

    /* --- ALU I-Type (with 10-trit immediate) --- */
    OP_ADDI  = 20,   /* ADDI Rd, Rs1, imm   : Rd = Rs1 + imm              */
    OP_SUBI  = 21,   /* SUBI Rd, Rs1, imm   : Rd = Rs1 - imm              */
    OP_MULI  = 22,   /* MULI Rd, Rs1, imm   : Rd = Rs1 * imm              */
    OP_ANDI  = 23,   /* ANDI Rd, Rs1, imm   : Rd = ternary_and(Rs1, imm)  */
    OP_ORI   = 24,   /* ORI  Rd, Rs1, imm   : Rd = ternary_or(Rs1, imm)   */
    OP_SHLI  = 25,   /* SHLI Rd, Rs1, imm   : Rd = Rs1 << imm             */
    OP_SHRI  = 26,   /* SHRI Rd, Rs1, imm   : Rd = Rs1 >> imm             */
    OP_CMPI  = 27,   /* CMPI Rd, Rs1, imm   : Rd = sign(Rs1 - imm)        */
    OP_LI    = 28,   /* LI   Rd, imm        : Rd = imm (load immediate)   */

    /* --- Memory I-Type --- */
    OP_LDW   = 30,   /* LDW  Rd, Rs1, imm   : Rd = mem[Rs1 + imm]         */
    OP_STW   = 31,   /* STW  Rs2, Rs1, imm  : mem[Rs1 + imm] = Rs2        */
    OP_LDT   = 32,   /* LDT  Rd, Rs1, imm   : Load tryte (6-trit)         */
    OP_STT   = 33,   /* STT  Rs2, Rs1, imm  : Store tryte                 */

    /* --- Branch B-Type --- */
    OP_BEQ   = 40,   /* BEQ  Rs1, Rs2, imm  : if Rs1==Rs2 PC+=imm         */
    OP_BNE   = 41,   /* BNE  Rs1, Rs2, imm  : if Rs1!=Rs2 PC+=imm         */
    OP_BGT   = 42,   /* BGT  Rs1, Rs2, imm  : if Rs1>Rs2  PC+=imm         */
    OP_BLT   = 43,   /* BLT  Rs1, Rs2, imm  : if Rs1<Rs2  PC+=imm         */
    OP_BGE   = 44,   /* BGE  Rs1, Rs2, imm  : if Rs1>=Rs2 PC+=imm         */
    OP_BLE   = 45,   /* BLE  Rs1, Rs2, imm  : if Rs1<=Rs2 PC+=imm         */
    OP_BEQZ  = 46,   /* BEQZ Rs1, imm       : if Rs1==0   PC+=imm         */
    OP_BNEZ  = 47,   /* BNEZ Rs1, imm       : if Rs1!=0   PC+=imm         */
    OP_BGTZ  = 48,   /* BGTZ Rs1, imm       : if Rs1>0    PC+=imm         */
    OP_BLTZ  = 49,   /* BLTZ Rs1, imm       : if Rs1<0    PC+=imm         */

    /* --- Jump J-Type --- */
    OP_JMP   = 50,   /* JMP  imm18          : PC += imm18                 */
    OP_JMPA  = 51,   /* JMPA imm18          : PC  = imm18 (absolute)      */
    OP_CALL  = 52,   /* CALL imm18          : R80=PC+1; PC+=imm18         */
    OP_RET   = 53,   /* RET                 : PC = R80                    */
    OP_CALLR = 54,   /* CALLR Rs1           : R80=PC+1; PC=Rs1            */
    OP_JMPR  = 55,   /* JMPR Rs1            : PC = Rs1                    */

    /* --- Special --- */
    OP_NOP   = 60,   /* NOP                 : no operation                */
    OP_HALT  = 61,   /* HALT                : stop execution              */
    OP_SYSCALL = 62, /* SYSCALL             : system call via R1           */

    /* --- Atomic (for synchronization) --- */
    OP_LDXA  = 70,   /* LDXA Rd, Rs1        : load exclusive (atomic)     */
    OP_STXA  = 71,   /* STXA Rs2, Rs1       : store exclusive (atomic)    */
    OP_CAS   = 72,   /* CAS  Rd, Rs1, Rs2   : compare-and-swap            */

} opcode_t;

/* -----------------------------------------------------------------------
 * Instruction field extraction macros
 * All fields are trit-based; we work in int64 space.
 *
 * Instruction is stored as int64 (decoded from binary-encoded ternary).
 * Fields are extracted by dividing/modding by powers of 3.
 * --------------------------------------------------------------------- */

/* Extract opcode (trits 18..23, i.e. the top 6 trits of a 24-trit word) */
#define INST_OPCODE(inst)  ((int)((inst) / 282429536LL))   /* / 3^18 */

/* For field extraction we use tword_field() from trit.h */

/* -----------------------------------------------------------------------
 * Syscall numbers (passed in R1)
 * --------------------------------------------------------------------- */
typedef enum {
    SYS_PRINT_INT  = 1,   /* Print R2 as decimal integer    */
    SYS_PRINT_TRIT = 2,   /* Print R2 as ternary string     */
    SYS_PRINT_CHAR = 3,   /* Print R2 as ASCII char         */
    SYS_READ_INT   = 4,   /* Read integer into R2           */
    SYS_EXIT       = 5,   /* Exit with code R2              */
    SYS_PRINT_NL   = 6,   /* Print newline                  */

    /* Runtime value substrate — variable-length strings (40..48).
     * Handles are heap addresses; see cpu.h. R1 returns the result. */
    SYS_STR_ALLOC   = 40, /* R2=len            -> R1=handle (chars zeroed)   */
    SYS_STR_FROMBUF = 41, /* R2=buf(NUL-term)  -> R1=handle                  */
    SYS_STR_LEN     = 42, /* R2=handle         -> R1=length                  */
    SYS_STR_CHAR    = 43, /* R2=handle R3=i    -> R1=char (0 if OOB)         */
    SYS_STR_SETCHAR = 44, /* R2=handle R3=i R4=char                          */
    SYS_STR_CONCAT  = 45, /* R2=h1 R3=h2       -> R1=new handle              */
    SYS_STR_EQ      = 46, /* R2=h1 R3=h2       -> R1=1 if equal else 0       */
    SYS_STR_SUB     = 47, /* R2=handle R3=start R4=len -> R1=new handle      */
    SYS_STR_INDEXOF = 48, /* R2=hay R3=needle R4=from  -> R1=index or -1     */
    SYS_STR_UPPER   = 49, /* R2=handle         -> R1=new upper-cased handle  */
    SYS_STR_LOWER   = 50, /* R2=handle         -> R1=new lower-cased handle  */
    SYS_STR_TRIM    = 51, /* R2=handle         -> R1=new space-trimmed handle*/
    SYS_STR_REPLACE = 52, /* R2=text R3=find R4=with R5=ci -> R1=new handle  */
    SYS_STR_SPLIT   = 53, /* R2=text R3=delim  -> R1=list of string handles  */
    SYS_STR_FORMAT  = 54, /* R2=template R3=args-list -> R1=string ({i} subst)*/

    /* Runtime value substrate — fixed-length immutable lists (60..64).
     * Same length-prefixed heap header as strings; elements are values
     * (numbers or handles). APPEND returns a NEW list one longer. */
    SYS_LIST_ALLOC  = 60, /* R2=len            -> R1=handle (values zeroed)  */
    SYS_LIST_LEN    = 61, /* R2=handle         -> R1=length                  */
    SYS_LIST_GET    = 62, /* R2=handle R3=i    -> R1=value (0 if OOB)        */
    SYS_LIST_SET    = 63, /* R2=handle R3=i R4=value                         */
    SYS_LIST_APPEND = 64, /* R2=handle R3=value -> R1=new handle (len+1)     */
    SYS_LIST_JOIN   = 65, /* R2=list R3=sep    -> R1=string handle           */
    SYS_LIST_REVERSE= 66, /* R2=list           -> R1=reversed list handle    */
    SYS_LIST_SORT   = 67, /* R2=list R3=ascending -> R1=sorted list handle   */
    SYS_LIST_UNIQUE = 68, /* R2=list           -> R1=distinct list handle    */
} syscall_t;

#endif /* ISA_H */
