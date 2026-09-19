# Merge-back ledger — whitepaper and the documentation phase

CAI (docs seat), 19/09/2026. Written to the bench; `docs/` remains gated to the
captain's side window. This is the standing to-do list for closing the
documentation phase, and the record of what the ASPLOS work owes back to the
canonical whitepaper.

---

## Part 1 — the standing hazard

`docs/TernOO-5500FP-Whitepaper-Draft.md` is still the June v0.4 text: 1,232
lines, zero occurrences of HexMesh, "282 trillion states / 65,000×" intact,
TMesh and TTree throughout, the author's name, city and both repository URLs on
the front page, GHOST's forward-pass engine described as "the next
implementation milestone", and implementation phases that stopped being true in
June.

Every one of those was corrected for the ASPLOS submission (#1275). None of the
corrections were landed. The canonical is therefore *behind* its own derived
work.

This became urgent on 17/09 when `docs/site/` went public and declared that the
repository is the single source of truth and that when a mirror disagrees, the
repository wins. That declaration is correct and the document behind it is not.

---

## Part 2 — corrections owed to the whitepaper

These are true of both documents and belong in the canonical:

- HexMesh rename throughout; OTree retained. No TMesh, no TTree.
- §8.3 state count: 3²⁴ ≈ 282 billion, ≈66× the 32-bit state count, 1.19×
  (19%) information density. The "trillion / 65,000×" claim is false.
- Measured benchmark figures, aligned workloads only, cycle-parity checked.
- The per-trit Steiner quasigroup, with the worked example op(123,456) = 60.
- GHOST status: the forward-pass engine is built, exported as NEURAL words,
  bit-exact against a host reference, and in service on the mesh.
- The traversal accumulator identifies a path; it does not reconstruct content.
- Inheritance-by-proximity: the foundation is demonstrated by the acceptance
  suite; only multiple inheritance remains unverified.
- Binary interoperability is demonstrated, not proposed.
- OPCODE promoted from OPEN_A to a defined primary; six defined, not five.
- Geometry: the algebra constrains triples, not embeddings.
- Anonymisation is submission-only and does **not** propagate to the canonical.

## Part 3 — improved wordings that exist only in the ASPLOS fork

Retained material that got better and has no other home:

1. "Three systems, not three applications" — FlowCode, GristMill and GHOST as
   components rather than downstream users.
2. The tightened OTree/HexMesh account: two faces, MMID/MMOE, T18 as namespace
   discriminator, beekeeper analogy stated once.
3. §6.3 FlowCode-as-assembly opening, without the pre-history paragraph.
4. The scene graph: word list not framebuffer, dirty-word redraw, framebuffer
   mapping, Mandelbrot raster path.
5. "Drawing Is Execution" — one mode, the parallel word-stream mechanism with
   identity words attached, and the checkable test.
6. The per-trit quasigroup passage with the idempotence distinction.
7. GHOST's real double-recursive gloss and its built status.
8. The accumulator result: digest, order-insensitive, identification not
   reconstruction, sponge for tamper-evidence.
9. The OPCODE word subsection.
10. Related Work: Freenet added to content-addressable storage, with the
    observation that prior art derives an address from content but carries no
    further structure — two related objects get unrelated addresses.

## Part 4 — cuts that must NOT propagate

Removed for the 11-page limit only. Still true, still wanted in the canonical:
the case for ternary (radix economy, BitNet); the 5500FP processor subsection;
tagged architectures and Lisp machines; the terminology note (symbols vs nodes).
Captain's ruling, 06/09.

Dead in both documents: FlowCode pre-history (Dia, Gnumeric, SolidiFlow,
Ethereum); PIGART implementation phases; the two-renderer detail; the
token-vs-coin definition, which the paper never used. The project origin
section is the captain's call.

Also unwanted in both: changelog narration ("earlier drafts…", "now
resolved"), meta-commentary ("worth stating…"), and "not X but Y" framing.

---

## Part 5 — three new entries (19/09/2026)

### 5.1 Structural Emergence — the missing unifying principle

The ASPLOS paper states its components and their individual merits but never
states the rule they all follow. Without it the paper reads as several good
ideas rather than one idea that is only expressible as a stack. The principle:

> Structure should be expressed at the lowest possible level of the system, so
> that higher-level features emerge as consequences rather than as added
> layers.

Every component is an instance. Type and semantics live in the word, not a
descriptor table above it. Identity and dispatch live in the word, not a vtable.
User-defined contexts live in the word stream, not a compiler. The program is
the diagram rather than a text file that compiles to one. Object identity is the
address rather than a hash stored beside it. Weights are the substrate rather
than floats decoded from a file. Recovery is intrinsic to the mesh rather than
computed by a resolver.

Named **Structural Emergence (SE)** by the captain, 19/09. It belongs in the
whitepaper's opening and in the abstract. It requires no new experiments —
only reordering what already exists.

Provenance: identified by DeepSeek in review, 19/09; formulated there;
adopted and named at this desk.

### 5.2 TDA — status and its undefended flank

The *Ternary Dimensional Advantage* paper (v0.1) is a **working note**. Captain's
ruling, 19/09: it was written as thinking-out-loud and has no destination as
canon. It is not to be published, mirrored or cited as project doctrine in its
current form.

Its known flank, verified at this desk: the paper's argument depends on binary
using two bits per ternary dimension. An informed reader will immediately raise
**packing** — five ternary values fit in eight bits (3⁵ = 243 ≤ 256), which is
near the information-theoretic optimum, so the exponential waste is a property
of random-access-friendly encodings rather than of binary itself.

The paper is not wrong about this. It already draws the right distinction —
twelve uses of "per-dimension", and a section separating structural fit from
total capacity. What it never does is *name the objection it defeats*: the
words "packing", "random access" and "decode" appear zero times in 411 lines.

So the defect is an undefended claim, not a false one, and the remedy is a
paragraph rather than a rewrite. Do not let this be recorded as "the maths was
wrong".

### 5.3 The theoretical trinity — a future submission

Captain's framing, 19/09. A separate theory paper on three claims:

- **SQG** — settled and implemented in the HexMesh.
- **TDA** — needs rigorous analysis and empirical support.
- **SE** — needs empirical support.

GristMill is the critical path for the last two. If it emerges a working object
library and interface from the word grammar, SE stops being a design philosophy
and becomes a demonstrated result, and TDA gains a measured case. Until then
both are assertions.

Distinct from #1275, which is an architecture-and-languages paper and should
remain one. Leading with the quasigroup would make it a theory paper and
probably a different venue.

---

## Part 6 — phase order

The captain's sequence, 19/09, after the merge-back:

1. Whitepaper corrections landed; canonical matches what the public docs site
   already claims.
2. `docs/site` brought up to spec.
3. FlowCode help documentation fleshed out in both faces.
4. The synchronisation protocol nailed down — for extraneous documents, and
   for keeping code and documentation in step.
5. Publicity media and the open-door phase.

Two protocol documents exist for step 4 and are not yet in the repository: the
canonical-source-and-mirrors protocol, and a first `MIRRORS.md` drafted from
the live state. Both are held in the docs seat's outputs pending the captain's
word.

— CAI (docs seat)
