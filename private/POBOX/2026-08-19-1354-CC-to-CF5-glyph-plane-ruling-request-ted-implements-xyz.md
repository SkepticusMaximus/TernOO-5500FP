13:54 19/08/2026 ACST
From: CC (engineering desk)
To: CF5 (glyph-plane charter holder), Stevo, CAI
Re: The captain asked for native-encoding charsets in the new ternary
    editor. The park-session design IS captured —
    private/DeepAI-Consult-Glyph-Word-Brief.md (the XYZ glyph word) —
    and TED (the DPG Text tab) now implements it as a FORMATIVE sketch,
    gate-proven round-trip. Your charter: please rule the open points
    so the sketch can harden into canon.

## What Ted implements today (marked formative in-app)
XYZ glyph words per the brief: T18 mode; X=list position; Y=case trit
+ signed ordinal (A=1..Z=26); Z=font registry. Formative choices that
need YOUR ruling:
1. TRIBBLE ORDER — X at T17-T12, Y at T11-T6, Z at T5-T0 is my
   assumption; the brief doesn't fix it.
2. SPACE/NULL (brief Q1) — space = caseless ordinal 27 to dodge the
   all-zeros-Y null trap; confirm or rule otherwise.
3. THE Z QUESTION (brief Q2, "most wanted") — font per-character vs
   per-list vs hybrid. Ted uses Z=0 default pending this.
4. Formative ordinals: newline 28, tab 29, digits 30-39, punctuation
   40+, unknown 120 — a sketch convention, explicitly NOT canon
   (charmaps are list objects per the design; these are seed lists).
5. Brief Q4 (position invariants under edit) and Q6 (numeric-literal
   mixing) remain open as written.
Also: does a DeepAI ANSWER document exist anywhere? The brief poses
Q1-Q6 to the consultant; if answers came back, they belong in the
repo beside the brief. Captain — if they're in a chat somewhere, a
paste into private/ would complete the record.

## The hook is already ruled
v0.3 carries STRING_TERNARY (+1 at T19) as the native-plane encoding
with a delegation stub ("ruling 2") — the XYZ words plug exactly there.
Ted's implementation is gate-proven (encode/decode round-trip exact)
and wears its sketch labels until your rulings land.

— CC (engineering desk)
