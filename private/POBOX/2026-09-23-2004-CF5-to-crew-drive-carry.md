20:04 23/09/2026 ACST


# CF5 → crew — GLYPH PLANE CLOSED: the six formative points, ruled by the captain


From: CF5 (glyph-plane charter holder / oversight seat)
To: crew (Stevo, CC, CAI)
Re: The six open points from the 19-08 recovery letter, now RULED by the
    captain live at this seat, 23-09. Ted sheds its formative-sketch
    labels; TernDoc's TextCodec seam has canon to plug into. Verified
    against ternoo_glyph.py as shipped before ruling.


## Frame (unchanged, canon since O1)
DATA_STRING word (T21=+1, T20=−1; encoding at T19: TERNARY +1 / ASCII 0 /
UNICODE −1). Payload: X T17..T12 position · Y T11..T6 (T11 case trit,
T10..T6 five-trit signed ordinal, ±121) · Z T5..T0 font. Right-
conditioning law governs. NOTE FOR THE RECORD: glyph words are DATA
words, not MAP words — a premise corrected at this seat tonight.


## The six, RULED
1. TRIBBLE ORDER — X leftmost (T17..T12), Y (T11..T6), Z (T5..T0), as
   Ted implements. Left defines, right is conditioned: position →
   identity → font. RULED.
2. SPACE — its own nonzero ordinal (see 4). Ordinal 0 stays NULL / no
   character, as make_glyph already enforces. RULED.
3. Z FONT — PER-CHARACTER, Z=0 = inherit default (house font in v1).
   Mixed fonts mid-string (chalk↔ink, bold word) for free. RULED.
4. SEED ORDINAL TABLE (digits-first, captain's layout, null preserved):
     0        null / no character (rejected by make_glyph)
     1–10     digits '0'–'9'        (value = Y − 1)
     11–36    letters a–z           (alphabetical index = Y − 10; a = 11)
     37       space
     38+      punctuation (growing seed list)
     120      unknown
   Case via T11 (+1 upper / −1 lower / 0 caseless); digits, space and
   punctuation caseless. Explicitly a SEED table, not stone — grows in
   the positive band above 38. RULED.
   Ledger note: the NEGATIVE half of the ordinal (−1..−121) is reserved
   unused — a free second class if ever needed, with no trits carved.
   "120 spare" was a misreading: 120 is the ceiling of the ±121 range,
   not headroom; carving an offset field out of five trits leaves 27
   values, too few for an alphabet — ruled OUT.
5. POSITION INVARIANTS — X is a LIVE index; renumbers on edit. Stable
   identity is not X's job. TernDoc's model-side cursor already pays
   this cost. RULED.
6. NUMERIC MIXING — a digit in text is a GLYPH, never a value. A number
   in text is a LITERAL-mode sibling word in the stream (the same
   DATA_STRING type already carries an 18-trit signed literal inline,
   ±193,710,244 — ternoo_glyph.py line 29), value inline, no pointer.
   Glyph→number is an explicit conversion producing a DATA word. A
   pointer to a DATA object, if ever wanted, is the existing USER-DEF
   POINTER (itself DATA-family) as the next word. No pointer trits
   carved into the glyph word — payload is fully spent (X+Y+Z=18), and
   the principle is the same one ruled for widgets today: values and
   relationships are their own words, not packed fields. RULED.


## Consequences for the engine room
- Ted: drop the formative-sketch labels; re-seed the ordinal table per
  (4) — this renumbers the current seed (letters 1–26 → 11–36, space
  27 → 37, digits 30–39 → 1–10). Suite pins that encode ordinals need
  the one-time migration; make_glyph's null-at-0 rejection stands.
- TernDoc: the TextCodec seam now has its canon; plug the glyph-plane
  codec in and, per CC's own design, no surface changes.
- CAI: docs pass — the glyph plane joins the Language Audit as ruled;
  the 19-08 recovery letter's "OPEN" list is closed and can be cited as
  superseded by this letter.


The dependency that sat on two boards is off both. — CF5 ⚓