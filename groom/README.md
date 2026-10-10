# GrOOM — Gristmill Object Oriented Model

The mill that grinds a reference-kit (PySide6) widget's **retained** object model
into TernOO **24-trit balanced-ternary words** — the native substrate for TernUI.
DPG/ImGui is immediate-mode: it has no retained object model to grind; PySide6
gives a documented inheritance graph + property set, and the mill turns that into
words.

## Word layout  (24 trits = 2 PRIMARY · 4 QUALIFIER/role · 18 PAYLOAD)
```
identity   CRYPTO · IDENTITY · serial     the TernID handle — meets the spine
class      I/O    · CLASS    · class-id
parent     MAP    · PARENT   · super-class-id    (one inheritance edge)
property   DATA   · PROP     · prop-id
value      DATA   · VALUE    · value
of-class   MAP    · CONTENT  · class-id
```
A GrOOM object's IDENTITY is a TernID identity and "who may touch it" is a CRYPTO
capability-word — so GrOOM objects are capability-governable by construction
(see the CC→CCC handoffs 1018 + 1028 in `private/POBOX/`).

## Run
```bash
QT_QPA_PLATFORM=offscreen ~/.venvs/p2pcp/bin/python3 groom.py   # widgets -> words
~/.venvs/p2pcp/bin/python3 test_groom.py                        # 14/14
```
`dissect()` reads a live widget's metaObject (off-screen is fine); the word layer
(`pack`/`unpack`/`Registry`) is pure Python, no Qt.

## Example (QTextEdit → 98 words)
```
IDENTITY #1   0+00++00000000000000000+   (CRYPTO,IDENTITY,1)
OF-CLASS      −00+−000000000000000000+   (MAP,CONTENT,1)
ancestry: QTextEdit -> QAbstractScrollArea -> QFrame -> QWidget -> QObject
87 property-words  (DATA·PROP·<id>)
```

## Loop closer (`groom_render.py`)
```bash
QT_QPA_PLATFORM=offscreen ~/.venvs/p2pcp/bin/python3 groom_render.py
```
`spec()` encodes a widget's class + property VALUES into words (+ a string pool;
strings are MAP content-addressed — the native char-map plane fills the pool
later). `render()` reads the words back to a spec; `build_qt()` reconstructs a
live PySide6 widget. Proven: `QLabel("Hello TernOO")` → 7 words → a live `QLabel`
whose text round-trips exactly. **reference → words → native closes.** 11/11.

## Status
Built + tested: word pack/unpack (2+4+18), bidirectional id registry, dissector,
GrOOM objects, flatten-to-words, **value-word encoding + a renderer that closes
the loop**. Next: a **persisted** registry (cross-run stable class/prop ids),
richer value kinds (enums-by-name, colors, refs), a **full-widget** renderer
(layouts + children, not just leaf props), and the native **char-map string pool**
(CF5 charter) so strings are words too, not a side table.
