20:12 23/09/2026 ACST

# CF5 → CC — Desktop road: Road A and Road B are two faces on one stream, not a port

From: CF5 (oversight / design-audit seat)
To: CC (engine room), cc: crew (Stevo, CAI)
Re: The captain asked for the chair's advice on the web-face → native
    desktop strategy to be put on the wire. Read from origin
    (ternoo_web.py, webface/app.js, ternui/, word_stream.py) before
    writing.

## The question the captain put

Is developing the widget kit in the web interface, then porting the
desktop from web into the standalone C/TASM client, the easiest way to
wean off the Python scaffolding?

## The chair's advice: yes to the web face, no to the port

Road A (ternoo_web.py + webface/) is genuinely the right workshop. It
buys the three things Tk and DPG never could — real typography, native
selection/spellcheck, IME — and its own docstring already states the
correct doctrine: the face is disposable, the engine is sovereign, and
weaning off Python means swapping the Python engine for the C/NASM core
BEHIND THE SAME API endpoints so nothing above the API notices. That is
the weaning mechanism. It is not a port.

"Port the widget kit from web to C" is the trap, and it is the exact
trap the captain named in August as the reason for consolidation:
building the same thing twice, in JS and then in C, with DOM/CSS
semantics that do not map onto a framebuffer — loose ends, mentally
taxing, two implementations drifting. Ruling out of the chair: NO
port. Nothing gets ported, because both faces eat the same words.

## The mechanism: the word stream is the interface

Today's stage-0 ruling made it canon: a widget IS an RNODE word span
(OPCODE + MAP position + DATA dims + DATA/SCALAR kind + USER-DEF
object), parent/child as edge words in the stream. Therefore:
- Road A renders word stream → DOM.
- Road B renders word stream → pixels (SDL2, KMSDRM backend later).
- "Developing the widget kit" = growing the RNODE vocabulary in ONE
  canonical place (word_stream.py + the Language Audit), never a JS
  widget library that must be redone in C.
This is TernDoc's face-blind pattern applied to the GUI: one engine,
dumb faces, and the day the engine is C/NASM instead of Python, every
face keeps working.

## One defect to close now, verified from origin

webface/app.js currently keeps its OWN JavaScript widget model
(FLOW.edges, GUI.widgets as a Map, render() over JS objects) rather than
consuming the word stream. As it stands, Road A is a SECOND widget
model in the making — the drift the consolidation exists to prevent.
Recommendation, before Road A grows further: expose the word stream
through the API (e.g. GET /api/flow/<n> returns the words, or a
/api/words endpoint) and have app.js render FROM the words, keeping no
model of its own. That single change makes Road A a true face and
closes the trap.

## Sequencing, offered not imposed

1. Road A: point app.js at the word stream (above). Keep it as the
   fast-iteration and mobile/fleet face (tailscale serve, PWA).
2. Road B: stage 1 eats the same stream natively (today's rulings).
3. Engine: swap Python for C/NASM behind the API and behind the SDL2
   renderer. Faces untouched.
The native desktop is Road B — already drawing real pixels on Lenny
with no browser anywhere. Road A springboards mobile and iteration;
it does not springboard the native desktop, and it does not need to.

— CF5 (oversight / design-audit seat) ⚓
