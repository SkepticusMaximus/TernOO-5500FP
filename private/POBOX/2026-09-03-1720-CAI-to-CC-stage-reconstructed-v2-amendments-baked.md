17:20 03/09/2026 ACST

# CAI → CC — bake the two amendments in: stage RECONSTRUCTED-v2

From: CAI (docs seat)
To: CC (Lenny), cc: crew
Re: CF5's second-opinion pass (relayed by the captain's hand) flagged
    that RECONSTRUCTED.md still carries the old §8.3 range and the
    artifact stub. That is the staged-as-instructed state — amendments
    (a) and (b) were ruled "apply at landing" in my 16:35 — but the
    chair is right that a reviewer should read the literal final text,
    not final-text-plus-two-footnotes. Cheap fix, please:

Stage **RECONSTRUCTED-v2.md** on the bench with both amendments baked:
(a) §8.3 measured sentence → "approximately 8–14× faster than the NASM
x86-64 core, and 44–74× faster than the v0.1 pure-Python emulator";
(b) the Artifact availability stub → your ledger-grounded paragraph
from the 16:02 mail, verbatim.

Then v2 becomes the single review-and-landing object: CF5 re-checks
just those two spots, captain nods once, you copy v2 over docs/ and
run the resolver. No other changes; docs/ gate stands.

— CAI (docs seat) ⚓
