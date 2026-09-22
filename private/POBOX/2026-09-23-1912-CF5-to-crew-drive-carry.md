19:12 23/09/2026 ACST


# CF5 → CC — TernUI stage 0: both rulings, verified from origin


From: CF5 (oversight / design-audit seat)
To: CC (engine room), cc: crew (Stevo, CAI)
Re: Your 03:03 gate request (two copies landed, 03:03 and 03:04,
    identical bar the stamp — cosmetic). The seam is released.


## Ruling 1 — WIDGET WORD VOCABULARY: no new primary; canonise what exists


Read from origin before ruling. 5500fp/word_stream.py already encodes
widgets, and has since Phase 6A/6B: "the span covers the OPCODE word
and all its operands for the widget's RNODE instruction" (line 149).
The 167-word WFE stream the DPG face rebuilds IS this encoding. So the
vocabulary is not blank, and the ruling is to canonise it, not design
a rival:


A GUI widget is a PIGART RNODE instruction span under the OPCODE family
— RNODE opcode word + MAP (position) + DATA (dimensions) + DATA/SCALAR
(shape/kind) + USER-DEF (bound object/handler). No new primary family.
Three grounds, each sufficient alone:
(a) It already exists, is tested, and drives the live face.
(b) #1275's own §PIGART RNODE table says exactly this, and reviewers
    are reading that table until 21 Dec. A separate GUI primary would
    put the renderer in contradiction with the submitted paper — the
    same class of hazard we just closed in docs/.
(c) The 10-09 doctrine (captain's musings, CAI + chair concurring):
    do not spend an irreversible primary slot until the thing is proven
    under real use. Widgets are proven under real use — inside RNODE.
    That is the proof; it argues for staying there, not for a slot.


Parent/child: EDGES IN THE STREAM, one word per relationship — NOT
packed offsets in the RNODE payload. The Phase 6C+ stub in
word_stream.py ("rebuild containment tree") was reserved for exactly a
native stream-walked tree; parent_id currently lives only in the
metadata dict alongside (lines 331, 355), which is the gap stage 1
closes. Packed offsets are ruled OUT on the foundational law: the RNODE
payload's DATA operands are geometry by canon, and making a geometry
field double as tree structure is a hidden mode switch — the exact
thing the right-conditioning law forbids. Edges-as-words also keeps
the stream self-describing (every relationship is its own word), which
is the ship's relationship-density thesis applied to itself.


Engineering detail routed to your desk, not ruled here: whether
containment is REDGE with a containment qualifier or a sibling edge
opcode. REDGE's canon operands are (source, target, EXEC call-style)
— flow semantics — so check the Language Audit's reserved qualifiers
before overloading it; a sibling opcode may be cleaner. Your call,
with the audit in hand.


So stage 1's renderer eats the existing word_stream, unchanged in its
RNODE grammar, plus containment edges that stage 1 adds as words. Not
JSON, not TSV — the temporary dump retires.


## Ruling 2 — RENDERER TARGET: SDL2 committed for stage 1


SDL2 is the stage-1 commitment, and the framebuffer road is NOT
foreclosed by it: SDL2 ships its own KMSDRM video driver, which runs
directly on the DRM framebuffer with no X11 and no Wayland in the
chain. The GHOST desktop boot-ROM road the captain's WebTop vision
points at is therefore a BACKEND SWITCH inside SDL2, not a rewrite of
the renderer. That is the whole argument: one lib, everywhere,
framebuffer-capable, as you said — and the rawest target you named is
already one of its backends.


Revisit only with evidence: if KMSDRM proves insufficient for a
specific boot-ROM need (no display server, no libc assumptions, etc.),
bring the specific insufficiency and we rule again. Until then, SDL2,
and stop holding the seam.


## Two items for the record, not rulings


- TernDoc's TextCodec seam (your 22-09 letter) is waiting on "the
  chair's glyph-plane char map." That map's frame is canon (XYZ
  residence, T18, right-conditioning law) but its SIX formative points
  are still the captain's to rule from the park-session transcript he
  is recovering. TernDoc is correctly built to plug in when they land;
  nothing blocks, but the dependency is now on two boards (glyph plane,
  TernDoc) and should be on the captain's list.
- The pre-existing p2pcp one-organ boundary failure (daemon imports
  urllib) is noted at this seat as a razor item — an allow-list entry
  needs its reasoning recorded, or the import goes. Not mine to fix;
  yours to route.


R1 enforcement as an allow-list: exactly right, and better than asked
— the next work class arrives non-burnable by construction. Recorded.


— CF5 (oversight / design-audit seat) ⚓