16:20 23/09/2026 ACST


# CF5 → crew — NORTH STAR BRIEF: the second object model, TOOL, and the road to FlowCode-in-TernOO


From: CF5 (oversight / design-audit seat)
To: crew (Stevo, CC, CAI)
Re: The captain's design session at this seat, 23-09. A north star, not a
    work item: this brief records direction and constraints so the next
    five years of decisions can be checked against it. Nothing here
    authorises code, reorders the widget campaign, or touches R1/R2.
    Bench-bound (private/docs-bench/decisions/); captain's gate for
    anything that would promote it toward docs/.


## 0. What was seen (the captain's own account)


TernOO's word model is deliberately FLAT: nine primaries as equal peers,
eighty-one qualifiers as equal peers under each, no primary outranking
another, all structure packed into three fields. That flatness is the
virtue that makes every word self-describing without asking anyone. It
also means the word model has no VERTICAL — no containment, no "this
lives inside that." The widget campaign (Desktop → Window → Canvas →
String → Char) is made of exactly that vertical. A SECOND object model
is therefore emerging, and with it the need for a language to carry it.
FlowCode wrote machine words because machine words were the only
TernOO-native thing there was; FlowCode was always language-agnostic.


## 1. The law that decides what goes in a word (ruled today, King X)


A WORD CARRIES ITS INTRINSIC PROPERTIES AND NEVER ITS RELATIONAL ONES.
Intrinsic = what it is on its own with no other word in the world (glyph
identity, case, font ref, colour). Relational = position, membership,
neighbours, size-in-context — these belong to the CONTAINER: the
stream's order, the containing span, an edge word. Build order is free
(the char may be built before the string); inheritance direction is not
(the char must never know the string). Conflating the two is the
equivocation the park session made and King X embodied.


## 2. The one-truth constraint (the danger, and its cure)


Two object models side by side become two truths — the Python problem
reborn a level up. Cure: the vertical model is MADE OF the flat one, not
stood beside it. The ship already has containment primitives in words:
stream order, spans, MSCOPE, edge words. A class is a span-of-spans;
inheritance is an edge word; the desktop hierarchy is nesting, never a
new primary. TOOL compiles down to words, always, or it is scaffolding.


## 3. The three-way split (the captain's sufficiency point, conceded)


Necessity is not sufficiency, and neither is the sum of what is
desirable. Therefore:
- SEMANTICS EMERGE. What a class, a container, an edge, a value IS —
  extracted from the living object model as the widget campaign builds
  it. "Extract, don't design" applies here and only here. Precedent:
  Smalltalk-80 was grown out of what its GUI needed to say (Kay); and
  Clarke's law, from the DEF CON 12 transcript verbatim: "deployment is
  the integration test."
- SURFACE IS DESIGNED. Syntax, ergonomics, web-familiarity (JS-flavoured
  if the captain wants it) are CHOICES made for humans, not emergences.
  A text syntax is a FACE on TOOL's semantics, exactly as the web page
  is a face on the word stream — faces disposable, engine sovereign.
  Two syntaxes over one semantics loses nothing.
- SUBSTRATE IS NOT SCAFFOLD. Python pretended to be the IDE (scaffold).
  C in the engine room emulates the 5500FP and pushes the framebuffer
  because there is no silicon yet (substrate = temporary hardware).
  Test for every C component: is this C standing in for the MACHINE, or
  for TERNOO CODE? Emulator core and pixel-blit: machine, fine. Widget
  logic or IDE behaviour in C: the Python move again — the line Road B
  must not cross. Everything above the framebuffer is words.
  Corroboration at scale: modern Freenet is Rust for the substrate,
  WebAssembly as the portable "words" its contracts compile to, the
  browser as a face. River is one such contract.


## 4. TOOL's mandate (the 10-09 musing, grown up)


TOOL is the intermediate language one layer above the words. The 10-09
question was whether it broke self-description; the answer stands: the
words describe themselves at the machine level, TOOL is compiled onto
them. Today gives TOOL its purpose: to carry the vertical object model
that flat words cannot express natively. Constraints: §2 (compiles to
words) is absolute; §3 (designed surface) is the captain's to choose.


## 5. The road (sequence, not schedule)


1. Widget campaign builds the vertical model as spans + edges in the
   stream (Road B, in flight). This is the FIRST WORKING SPECIMEN of the
   second model.
2. TOOL's semantics are extracted from that specimen; its surface is
   designed alongside.
3. Classic compiler bootstrap, nothing more exotic: the first TOOL
   compiler is scaffold (Python or C, whichever is to hand); then TOOL
   is rewritten in TOOL, and the scaffold is kicked away.
4. FlowCode-next is written in TOOL, compiled to words, running on the
   C substrate — "FlowCode written in TernOO." Desktop and boot ROM
   support each other because both are words the substrate runs.


## 6. What this brief is NOT


Not a work item. Not a reordering of the widget campaign, DICK, or the
income heading. Not a design of TOOL's syntax. Not a claim that any of
this exists. It is the star to steer by, on the record, so that the
next decision that would have packed structure into a leaf can be
checked against §1, and the next C component against §3.


Hoisted at the captain's word: "Tonight we sail by the north star."
— CF5 ⚓