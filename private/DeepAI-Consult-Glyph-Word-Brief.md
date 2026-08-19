# Consultation Brief — TernOO Native Glyph Word (Ternary Character Architecture)

Consultant: DeepAI (GPT OSS 120B)
Requested by: Stevo (TernOO-5500FP project)
Focus: structural versatility and expressive power, NOT ordinal range economics.

## Background (context you need, briefly)

TernOO-5500FP is a balanced-ternary computing platform (trits: -1, 0, +1)
with 24-trit self-describing words: a type header (~5 trits) plus an
18-trit payload organised as three 6-trit groups called "tribbles"
(1 tribble = 729 values, balanced range -364..+364). A reserved string
encoding plane exists for a native character set independent of ASCII
and Unicode (both remain available as separate projection planes).
Rendering is by a vector scene-graph engine (PIGART); a glyph's shape
is a stored stroke sequence in an object tree, so a "font" is an
object, not a bitmap. Characters may carry a pointer (registry index)
to their font object.

## The candidate design ("XYZ glyph word") — 18-trit payload

Top payload trit T18 is the MODE field:
- T18 = +1 : positive numeric literal. Remaining 18 trits = magnitude.
- T18 = -1 : negative numeric literal. Remaining 18 trits = magnitude.
- T18 =  0 : text character. The three tribbles then mean, unconditionally:
  - X (tribble 1): position of this character in its containing list
    (charmaps and collation orders are user-defined list objects; the
    word carries its own position, so any character can sit anywhere
    in any list).
  - Y (tribble 2): identity. Top trit = case (+1 upper, -1 lower,
    0 caseless). Remaining 5 trits = signed ordinal (A=1..Z=26;
    punctuation/specials/controls occupy the rest of the +/-121 range
    by list-declared convention).
  - Z (tribble 3): font registry index (0..728) resolving to the
    vector font object that renders this character.

Design intent: one word fully describes a character — where it sits,
what it is, how it draws. A string is then a 2D array whose cells each
carry a 3rd dimension (font), i.e. text is a lattice; plain text,
rich text, and re-collated text are three projections of one stored
original. No sentinel values anywhere; every field means one thing
always (mode lives only in T18).

## Rejected/rival designs (for comparison, argue against or for freely)

R1. Signed-ordinal-only: case as sign of the ordinal (+n upper,
    -n lower). Elegant negation, but caseless storage is impossible
    (exactly one zero exists); caseless comparison via |n| only.
R2. Register-paged case: lowercase in tribble 1, uppercase read from
    tribble 2 behind a zero sentinel, specials behind an all-+1
    sentinel. Rejected for conditional field semantics.
R3. Full 6-axis lattice: every trit of a tribble is an independent
    semantic axis (case, script, role, variant...). Maximal structure,
    judged overweight for a character map.

## Questions — in priority order

Q1. STRUCTURAL SOUNDNESS. Does the XYZ design contain any hidden
    conditional-semantics traps, ambiguities, or closure failures?
    (e.g. interaction of mode trit with type header; null/zero-word
    meaning; the all-zeros Y = null convention vs caseless-space
    characters.) Identify anything that would force a future sentinel.

Q2. THE Z QUESTION (most wanted). Font-per-character (Z in the glyph
    word) versus font-per-list (font as a property of the string/list
    object, freeing Z). Compare for EXPRESSIVE POWER: what text
    structures does each make natural or impossible? Consider mixed-
    font runs, mathematical notation, annotation layers, diffing and
    equality semantics (are two characters "equal" if fonts differ?),
    memory/locality behaviour of each, and whether a hybrid (list-level
    default + per-character override flag or offset) beats both.
    If Z leaves the glyph word, propose the strongest alternative use
    of that tribble consistent with the design's philosophy — or argue
    for reserving it.

Q3. CASE AS A TRIT vs CASE AS GEOMETRY. Y spends its top trit on case
    (three states, caseless storable). Compare against Eisenstein-
    integer treatment: the three case states as multiplications by
    omega = e^(2*pi*i/3), i.e. rotation among states as a single
    algebraic operation. On balanced-ternary hardware with cheap
    negation and trit-field writes, does the Eisenstein view offer any
    real operational or structural advantage for 3-state properties,
    or is it mathematically pretty but operationally void here?

Q4. ORDER WITHOUT CONVENTION. X carries list position, making
    collation an explicit stored property rather than an implicit
    table. Are there formal problems with position-carrying elements
    (e.g. invariants when lists are edited, duplicated characters in
    one list, characters shared between lists)? Recommend the cleanest
    invariant set: what must be true of X for list operations (insert,
    delete, reorder, merge) to remain coherent, and is a relative/
    gap-based positioning scheme superior to dense ordinals?

Q5. THE LATTICE READING. Formally characterise the "text as 3D array"
    claim: a string as a rank-2 array of glyph words each bearing a
    rank-3 coordinate. Is there established theory (multi-dimensional
    coding, fibre bundles over sequences, attributed strings, anything
    apt) that gives us vocabulary and known results for projections of
    this structure (flatten-to-plain, render-rich, re-collate)? We want
    the right names for what we are building and any known pitfalls.

Q6. NUMERIC LITERAL MODE. T18 = +/-1 turns the whole payload into a
    signed magnitude, making string-to-scalar a field read. Any
    structural objections to mixing value-words and glyph-words in one
    list (a "string" containing live numbers)? What invariants should
    govern when a literal renders (via digit glyphs) versus computes
    (as value)?

## Constraints and non-goals

- Balanced ternary is fixed; do not propose binary encodings.
- ASCII/Unicode compatibility is handled by separate projection
  planes; do not spend design budget on it here.
- Ordinal range maximisation is explicitly NOT a goal; versatility,
  compositional structure, and one-meaning-per-field discipline are.
- Prefer answers with worked micro-examples over prose assurances.
