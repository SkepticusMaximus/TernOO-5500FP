# TernOO-5500FP — Language Audit (Word Architecture)

**Status:** REBUILT 07/10/2026 from the canonical source — the original
`private/TernOO-Language-Audit.md` was lost (local-only, never committed; absent from
git history and the HP filesystem). Every value below is reconciled against
`5500fp/5500fp_ternoo_v03.py` and `5500fp/widget_lib.py` — **code is canonical for what
is built.** Scope of this rebuild: the **word architecture** (format, primaries,
qualifiers, opcodes, MAP/DATA encodings, symbol registries, forms, program-model words).
Not re-derived here (flagged, lower priority): full ISA operational semantics narrative,
mesh/p2pcp mechanics. Rebuilt by CC (engine room).

---

## 1. Word format — 2 + 4 + 18

```
[2-trit PRIMARY][4-trit QUALIFIER][18-trit PAYLOAD]
 T23-T22         T21-T18           T17-T0
```
- PRIMARY: 2 trits → 3² = **9 primary types**.
- QUALIFIER: 4 trits → 3⁴ = **81 values** per primary.
- PAYLOAD: 18 trits (balanced ternary; |value| ≤ (3¹⁸−1)/2 = 193,710,244).
- Field helpers: `get_field(word, lsb, width)`, `get_primary(word)`, `get_qualifier()`.
- Primary encoded LSB-first: `value = T22 + 3·T23` (`_primary_val(t23,t22)`).

## 2. The 9 primaries (T23, T22)

| Pair | Glyph | Primary | Notes |
|---|---|---|---|
| (−1,−1) | `−−` | **EXEC** | instruction words (ISA; qualifier = opcode family) |
| (−1, 0) | `−0` | **MAP** | positions / content-addresses (see §5) |
| (−1,+1) | `−+` | **DATA** | values, strings, pointers, symbols (see §6) |
| ( 0,−1) | `0−` | **NEURAL** | neural/tensor words |
| ( 0, 0) | `00` | **I/O** | input/output words |
| ( 0,+1) | `0+` | **CRYPTO** | *was reserved* → **un-reserved 07-10 for the capability-word family** (see §9) |
| (+1,−1) | `+−` | **OPCODE** | (formerly OPEN_A; alias `PRIMARY_OPEN_A` retained) |
| (+1, 0) | `+0` | **OPEN_B** | open/extensible |
| (+1,+1) | `++` | **POOL** | dynamic allocation |

## 3. Qualifier field & opcode families

`QUAL_MST = T21`, `QUAL_LST = T18`, width 4. Under EXEC/OPCODE, the qualifier's **top
2 trits (T21,T20)** select an opcode *family* (`_primary_val(t21,t20)`):

| Pair | Family | Role |
|---|---|---|
| (−,−) | `OPF_ISA_CORE` | core ISA ops |
| (−,0) | `OPF_ISA_STACK` | stack ops |
| (−,+) | `OPF_WORD_OP` | word-level ops |
| (0,−) | `OPF_PIGART` | render stream (§4) |
| (0,0) | `OPF_MECCANO` | Meccano program words |
| (0,+) | `OPF_MODEL` | program-model words (§7) |

## 4. Opcodes

**ISA** (`OP_*`): NOP 0 · HLT 1 · ADD 2 · SUB 3 · MUL 4 · DIV 5 · NEG 6 · MOV 7 ·
LDI 8 · LD 9 · ST 10 · JMP 11 · JEQ 12 · JNE 13 · JB 14 · JSR 15 · RTI 16 · PUSH 17 ·
POP 18 · MIN 19 · MAX 20 · TXOR 21 · EQUAL 22 · SUM 23 · TTT 24 · TTZ 25 · TTP 26 ·
ADDI 27 · SUBI 28 · OUT 29 · IN 30 · TOBJ 31 · TGET 32 · TPAYLOAD 33 · TCALL 34 ·
TNEW 35 · TBUILD 36 · TSEG 37.

**PIGART render** (family `OPF_PIGART`): RPOINT 38 · RLINE 39 · RNODE 40 · REDGE −1 ·
RENDER −2. Operand layouts:
- `RPOINT`: MAP(pos) [+ DATA(colour)]
- `RLINE`: MAP(start) + MAP(end) [+ DATA(style)]
- `RNODE`: MAP(top-left) + DATA(size) [+ DATA-SYMBOL(shape)] [+ DATA-STRING*label].
  Size word: **width = T11-T6, height = T5-T0.**
- `REDGE`: MAP(start) + MAP(end) [+ DATA-SYMBOL(style)] [+ DATA-STRING*label].
  Styles ≥ `STYLE_CONTAIN` (100) are logical — no visible render.
- `RENDER`: flush / frame marker.

## 5. MAP words — positions & content-addresses

Qualifier encodes axes + mode: **T21 = axis_YZ, T20 = axis_XZ, T19 = axis_XY,
T18 = mode_hint**. `decode_map_word(w) → {mode, axis_*, payload, coords}`.
- Mode **ORIGIN**: `coords = {scale: payload}`.
- Mode **ON_PLANE**: planar coordinates (client convention: X = payload trits 9-17,
  Y = trits 0-8 in the GUI decoder).
- **Content-addressing (ID/Auth use):** data is located by hashing to MAP-word
  addresses; an address chunk rides the 18-trit payload. A **256-bit key/address
  ≈ 162 trits = exactly 9 MAP words** (word order LSB-first; final word zero-padded in
  the high trits — pin against `build_map_word` before freezing a canonical byte
  serialization).

## 6. DATA words — subtypes

DATA primary `−+`. Qualifier top trits select subtype:
- **STRING** (T21=+1, T20=−1): encoding in T19 — `UNICODE = −1`, `ASCII = 0`,
  `TERNARY = +1` (native glyph plane, ruling 2). DATA-STRING packs **3 chars/word,
  base-128** (or ternary-glyph for the native plane). Payload = length-or-address.
- **DATA-POINTER-SYMBOL** (`PTR_SYMBOL = (0,+1)` pointer model): payload = a registry
  ID (shape / style / layout / signal — see §8).
- Plain DATA: numeric value in the 18-trit payload.

## 7. Program-model words (family `OPF_MODEL`)

Qualifier op selects the model directive (as decoded by the Python/JS/C decoders):
`MKIND` 0 · `MNAME` 1 · `MSCOPE` 6 · `MMORE` 7 (continuation of the previous field) ·
`MFLAG` 9 (`key=value`) · `MPROP` 11 (`name=value`) · `MBIND` 12 (`signal=target`) ·
`MVALUE` 13 (a trailing DATA word). These carry a widget/node's kind, name, scope,
flags, properties, signal bindings, and value.

## 8. Symbol registries (DATA-POINTER-SYMBOL payloads)

**Shapes** (`SHAPE_*`): RECTANGLE 0 · TERMINATOR 1 · PROCESS 2 · DECISION 3 · IO 4 ·
SUBROUTINE 5 · CONNECTOR 6 · OFFPAGE 7 · DOCUMENT 8 · DATA 9 · LABELED_BOX 10 ·
WINDOW 11 · BUTTON 12. (Extensible integer IDs; shape-plane is open-ended.)

**Styles** (`STYLE_*`, REDGE): CONTAIN 100 (child-of containment, no render) ·
HANDLER 101 (signal→handler binding).

**Layout-mode symbols:** 200+. **Signal IDs** (300+): CLICKED 300 · TOGGLED 301 ·
CHANGED 302 · ACTIVATED 303 · CLOSE_REQUESTED 304 · FOCUS_CHANGED 305 ·
VALUE_CHANGED 306 · SELECTION_CHANGED 307.

**Forms** (RNODE/REDGE operand shapes): `FORM_LEAN` 0 · `FORM_SHAPE` 1 ·
`FORM_SHAPE_UDP` 2 · `FORM_HAS_LAYOUT` 4 (bitmask) · `FORM_LEAN_LAYOUT` 4 ·
`FORM_SHAPE_LAYOUT` 5 · `FORM_SHAPE_UDP_LAYOUT` 6 · `FORM_HANDLER` −1 (REDGE, 4
operands, T20=−1).

## 9. CRYPTO primary — the capability-word family (new, 07-10-2026)

CRYPTO `(0,+1) = 0+` was **reserved**; un-reserved for the ID/Auth **capability word**
(cleared by CC-HP against this code, 07-10; pending CF5 pre-build audit). A capability =
an ordered *sentence* of CRYPTO words (the self-describing grant) + a **detached**
standard authenticator (Ed25519 / HMAC) over the sentence's canonical bytes. The word
sentence **designates & describes**; the authenticator **proves**. MMID may label; never
authenticate. Never the `ternary_sponge` (GF(3)-affine collidable — CF5, 27-09).

Proposed CRYPTO qualifiers (flat 4-trit; final subject to CF5):
`GRANT_HEAD = 0` · `ISSUER_REF = +1` · `OBJECT_REF = +2` · `RIGHTS = +3` ·
`CAVEAT = +4` · `DELEG_DEPTH = +5` · `REVOKE = −1`. 7 of 81 used. `ISSUER_REF` /
`OBJECT_REF` are **MAP** content-address word-sequences (§5) — the capability layer adds
no new addressing scheme. Full spec: `docs/design/identity-capability-word-spec.md`.

---

## Provenance & maintenance

- Source of truth: `5500fp/5500fp_ternoo_v03.py` (format, primaries, qualifiers,
  opcodes, MAP/DATA, forms), `5500fp/widget_lib.py` (shapes/styles/signals/forms),
  `5500fp/pigart_tkinter_renderer.py` (PIGART operand layouts), the JS/C decoders
  (`webface/ternwords.js`) for the MODEL family. The whitepaper
  (`docs/TernOO-5500FP-Whitepaper-Draft.md`) is the intent-level companion.
- **Lesson from the loss:** the original was local-only and vanished with no backup.
  This rebuild is **committed to git** (force-added) so it survives. If any content here
  should not live in the repo, `git rm --cached` it — but a reference catalogue of the
  built word architecture carries nothing more sensitive than the already-committed
  whitepaper and docs.
- Known stale companion: `docs/TernOO-5500FP-Word-Spec-v0.1.md` is two revisions behind
  the 2+4+18 / 9-primary format (per `docs/design/INDEX.md`); this audit supersedes it
  for the word architecture.
