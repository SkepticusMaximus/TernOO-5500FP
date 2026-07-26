# TMesh / OTree / PIGART — a mechanics rundown for external collaborators

Bench draft (free-fire), CC, 26-07-2026. Written for engineers outside the project
(current audience: the captain's DeepSeek collaborators) working on the P2PCP
manifold / vector-sharing idea. Everything below is sourced from the live tree and
the project's Language Audit; source links are public GitHub URLs on `master`.

Repo: https://github.com/SkepticusMaximus/TernOO-5500FP

---

## 0. Naming decoder (read this first)

- **"TMesh"** is the historical name for the ternary mesh system. In the live code
  it is implemented as the **TTree/OTree dual coordinate architecture** in
  [`5500fp/ternoo_gristmill.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py)
  (ported from the Rev4 prototype; 13/13 acceptance criteria).
- It is **not** the P2PCP network mesh (that "mesh" is the compute-trading peer
  network, separate repo: https://github.com/SkepticusMaximus/p2pcp ). Same word,
  two systems.
- There is **no `class TTree` / `class OTree`** — they are not node-based data
  structures. They are two **coordinate spaces expressed as MAP words**, plus a
  small quasigroup algebra for traversing and folding into them.

## 1. The substrate: TernOO words in 30 seconds

A TernOO word is **24 balanced trits** (each trit ∈ {−1, 0, +1}), field layout
**2+4+18**: PRIMARY (T23-T22), QUALIFIER (T21-T18), PAYLOAD (T17-T0). Nine primary
word families; the ones that matter here:

- **MAP** — spatial/coordinate words. The TTree/OTree coordinates ARE MAP words.
- **OPCODE** — instructions (includes the PIGART render family).
- **DATA / EXEC / NEURAL / I-O / USER-DEF POINTER** — payloads, behaviour,
  salience, transport, and process descriptors.

The 18-trit payload splits into three 6-trit **tribbles**
`(ta, tb, tc)` = (T17-T12, T11-T6, T5-T0), each a balanced value in −364..+364.
Extraction: [`extract_tribbles`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L156).
Word builders live in
[`5500fp/5500fp_ternoo_v03.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/5500fp_ternoo_v03.py).

## 2. Core math (the whole algebra is ~100 lines)

All in [`ternoo_gristmill.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L65):

- `MOD = 3^6 = 729` — "one tribble" of state.
- [`ternary_op(a,b) = (-(a+b)) mod 729`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L73)
  — a **Steiner quasigroup** with *mutual recovery*: if `C = op(A,B)` then
  `op(B,C) = A` and `op(A,C) = B`. Any two sides of a triangle recover the third.
  This is the load-bearing primitive: identity, traversal, and content addressing
  are all folds of this op.
- [`trit_weight(val)`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L174)
  — sum of |balanced trits|: the **ternary-native distance metric** (0..6 per
  tribble). MMID proximity (Kademlia-lineage nearest-neighbour) is built on it.

## 3. The dual coordinates: TTree vs OTree

One entity gets **two** MAP-word coordinates, discriminated by the MAP qualifier
trit T18 (`mode_hint`):

| | TTree | OTree |
|---|---|---|
| Meaning | **structural identity** — "what kind of thing" | **content address** — "this exact content" |
| mode_hint | `+1` → ON_PLANE | `0` → ABSOLUTE_3D |
| Builder | [`build_ttree_mmid(ta,tb)`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L197) | [`build_otree_mmoe(state)`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L219) |
| Carried by | **MMID** (type-determined, position-independent; two same-type MMIDs are identical) | **MMOE** (per-instance; same fold → same address, any change → different address) |

- [`class MMID`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L316)
  — Minimal Map ID. `distance_to(other)` gives ternary-native distance between
  identities.
- [`class MMOE`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L398)
  — Minimal Map Object Entity: mmid + label + otree_word + udp_word + exec_words
  + children; serialises via `to_words()`.
- The **MMOE type registry** (type → UDP role trits + legal successors) is at
  [`MMOE_TYPES`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L242):
  flow types (terminator/io/process/decision), widget types (window/panel/button/
  label/input), program types.

**Why this split matters for a vector-sharing scheme:** "is this the same KIND of
model/tensor" (TTree/MMID comparison) and "is this the same CONTENT/weights"
(OTree/MMOE comparison) are separate, cheap questions with a native distance
metric on each — the captain's "rated for MMID vs MMOE alignment" phrasing maps
exactly onto this machinery.

## 4. Traversal

- [`traverse_step(state, a, b)`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L88):
  `c = op(a,b)`, fold `c` into state; **`c == 0` is the end-of-object sentinel**.
- [`vocab_step`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L109):
  DAG-ordered walk over
  [`MECCANO_VOCAB`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L102)
  = {27, 54, …, 702} — the closed 27-element sub-quasigroup of Z/729 (closure
  proof in the comment). Backward steps rejected; 0 is a valid arrival.

## 5. The Fingerprint Fold — content addressing of whole programs

[`MeccanoProgram._compute_otree()` (`widget_lib.py`)](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/widget_lib.py#L149):

```
S = 0
for i, w in enumerate(words):
    ta, tb, _ = extract_tribbles(w)
    S = (S + ternary_op(ta * (i + 1), tb)) % 729
address = build_otree_mmoe(S)
```

The position weight `ta*(i+1)` makes it **order-sensitive**: reorder the words and
the address moves. Any change to shape/style/layout/signal changes the fold. This
is the pattern the captain proposes to reuse for vectors-in-training: fold the
object, get a content address, DIF against a peer's, converge.

(Nuance for implementers: `GristMill.from_flowcode` uses an *unweighted* fold
while `_compute_otree` uses the weighted one — two distinct fold disciplines
coexist; check which one you're comparing against.)

## 6. The GristMill engine

[`class GristMill`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py#L465)
— the working surface over all of the above: `synthesise(mmid,label,otree)`,
`proximity(mmid, n)` (nearest-neighbour by ternary distance),
`compose(sequence)` (deterministic accumulator fold; permutation changes OTree,
never TTree), `from_flowcode(canvas)` (BFS + fingerprint-fold of a FlowCode
graph). Known limits, honestly: `to_flowcode` documented but not implemented;
`from_flowcode` seeds only the first root (disconnected components lost); an
FT-5 role-trit collision between program and widget types is on record, deferred.

## 7. PIGART in brief

PIGART is the render pipeline expressed AS words — drawing is instructions, not
API calls:

- Opcode family `OPF_PIGART`: **RPOINT / RLINE / RNODE / REDGE / RENDER**.
- An `RNODE` ("render node") emission is 5 words: the opcode word (built in one
  O(1) call), a MAP position word, a DATA size word, a DATA shape symbol, and a
  label word; `RENDER` (arity 0) closes the stream. See the bridge:
  [`ghost_meccano.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ghost_meccano.py#L73).
- Renderers: [`pigart_ascii_renderer.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/pigart_ascii_renderer.py)
  and [`pigart_tkinter_renderer.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/pigart_tkinter_renderer.py);
  word-level plumbing in [`ternoo_pigart.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_pigart.py)
  and [`word_stream.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/word_stream.py).
- Relevance to the manifold idea: "render the per-dimension curves in PIGART"
  means emitting the curve description as a word stream — the same words that can
  be transported, DIF'ed, and content-addressed. Display format = wire format =
  addressable object. That collapse is the point.

## 8. Cost model (common outsider misreading)

Building an opcode word is **one constant-time call** — there is no mesh traversal
in construction. The mesh work is the **N-step fingerprint fold** that addresses a
program of N words, and the traversals that walk existing objects. (Language
Audit §0.4/§6.9 walkthrough: 1 step to build; 1+arity fetches to read back;
N fold steps to address.)

## 9. Open canon — do not treat as settled

Two definitional items are explicitly **captain-only open questions** in the
project ledger: the **OTree subdivision canon** and the **PIGART acronym
authorship/expansion**. This rundown describes implemented mechanics only;
where a claim would touch those two, defer to the captain.

## 10. Reading list (deep dive order)

1. [`5500fp/ternoo_gristmill.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ternoo_gristmill.py) — the algebra, coordinates, MMID/MMOE, GristMill (~1000 lines, self-testing: `--accept`).
2. [`5500fp/widget_lib.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/widget_lib.py) — MeccanoProgram, dual-coordinate identity, the Fingerprint Fold, word emitters.
3. [`5500fp/ghost_meccano.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/ghost_meccano.py) — GHOST→Meccano/PIGART bridge (design → words).
4. [`5500fp/5500fp_ternoo_v03.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/5500fp_ternoo_v03.py) — the word format itself (build/decode, nine primaries).
5. [`5500fp/word_stream.py`](https://github.com/SkepticusMaximus/TernOO-5500FP/blob/master/5500fp/word_stream.py) — streams, serialisation `[TTree, OTree, *body]`.
6. P2PCP (the transport/economy the manifold would ride on): https://github.com/SkepticusMaximus/p2pcp — `ledger.py` (two-class credit: replay-audited native work mints weight; float earns rent), `node.py`, `gateway.py`.

— CC (chief engineer), from the live tree + Language Audit; corrections via POBOX.
