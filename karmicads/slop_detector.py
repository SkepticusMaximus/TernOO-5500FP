#!/usr/bin/env python3
"""KarmicAds — AI-slop detector, Phase-1a (offline linguistic/narrative layer).

Scores a transcript on the HALLMARKS of fabricated 'true-crime / tragedy' slop passed off as
real: engineered emotional arcs, karmic-justice payoffs, stacked impossible coincidences,
pseudo-forensic precision, engagement bait, and the TELL-TALE ABSENCE of real journalism's
attribution ("police said", "according to the report"). It is explainable by design — every
point of score comes with the phrase that earned it — so a human (or an advertiser's exclusion
list) can see WHY a channel was flagged, not just a black-box number.

This is only the linguistic layer. The strongest signal — entity verification ("do these named
people / dates / places exist in any news archive?") — needs an online lookup and is Phase-1b.
This layer alone is enough to separate obvious slop from genuine reporting; the two combined are
hard to fool. Deliberately conservative: real journalism must NOT trip it (false positives are
the thing that kills a blocklist's credibility).
"""
import re
import statistics

# (weight, label, pattern) — each hit adds weight; examples are collected for the explanation.
SLOP_SIGNALS = [
    (14, "engagement bait", r"\b(you won'?t believe|watch (?:un)?til the end|by the end of this|"
         r"hold on to (?:that|both)|stay with me|the reason will (?:shock|surprise)|"
         r"what happened next|little did (?:he|she|they) know|doctors were stunned|"
         r"changed everything|you'?ll (?:see|understand) why)\b"),
    (12, "karmic-justice payoff", r"\b(karma|poetic justice|got what (?:he|she|they) deserved|"
         r"fate|destiny|comeuppance|justice was served|the irony)\b"),
    (12, "stacked coincidence", r"\b(by sheer (?:luck|coincidence|chance)|against all odds|"
         r"a miracle|just happened to|turned out to be|as luck would have it|"
         r"of all people|the very same (?:day|man|woman))\b"),
    (10, "pseudo-forensic precision", r"\b(neurogenic shock|carotid|laceration|subdural|hypoxia|"
         r"exsanguination|cardiac arrest|blunt[- ]force|ligature)\b"),
    (9,  "hyper-precise metric", r"\b\d{1,3} (?:minutes?|seconds?|feet|metres?|meters?|degrees?)"
         r"(?: and \d{1,3} (?:seconds?|degrees?))\b"),
    (8,  "miracle recovery / reversal", r"\b(a week later (?:she|he|they) (?:was|were) cured|"
         r"walked \d+\s?(?:km|kilometres?|miles?)|cured|made a full recovery overnight|"
         r"against the diagnosis|the error that saved)\b"),
]
# genuine-journalism attribution — each hit SUBTRACTS (real reporting sources its claims)
ATTRIBUTION = (r"\b(according to|police said|officials (?:said|confirmed)|in a statement|"
               r"told reporters|court (?:documents|heard)|the report (?:found|states|said)|"
               r"a spokesperson|coroner|authorities said|per (?:the )?records|"
               r"\[\d+\]|\(\d{4}\))\b")


def score(text):
    """Return (confidence 0-100, [reasons]). Higher = more likely fabricated slop."""
    t = text.lower()
    pts, reasons = 0, []
    for weight, label, pat in SLOP_SIGNALS:
        hits = re.findall(pat, t)
        if hits:
            pts += weight * min(len(hits), 3)                 # cap each signal's contribution
            eg = hits[0] if isinstance(hits[0], str) else next((h for h in hits[0] if h), "")
            reasons.append("+%d  %s (x%d)  e.g. %r" % (weight * min(len(hits), 3), label, len(hits), eg[:40]))

    attr = len(re.findall(ATTRIBUTION, t))
    if attr:
        pts -= 10 * min(attr, 4)
        reasons.append("-%d  real-journalism attribution (x%d) — sources its claims" % (10 * min(attr, 4), attr))

    # structural uniformity: AI prose runs to an even sentence length; real prose varies.
    sents = [len(s.split()) for s in re.split(r"[.!?]+", text) if len(s.split()) > 2]
    if len(sents) >= 6:
        cv = statistics.pstdev(sents) / (statistics.mean(sents) or 1)
        if cv < 0.45:                                         # suspiciously uniform
            pts += 10
            reasons.append("+10  uniform sentence length (CV=%.2f) — machine-even cadence" % cv)
        else:
            reasons.append("(ok) varied sentence length (CV=%.2f)" % cv)

    conf = max(0, min(100, pts))
    return conf, reasons


def verdict(conf):
    return ("LIKELY FABRICATED SLOP" if conf >= 45 else
            "SUSPECT — review" if conf >= 25 else "likely genuine")


SLOP_SAMPLE = """Brooke thought she knew the trail better than anyone. Raymond, the humble guide
everyone ignored, warned her twice. She laughed him off. Three minutes and 42 seconds later, the
ground gave way. Hold on to both of those numbers, because by the end you'll see why they matter.
The fall caused immediate neurogenic shock and a carotid artery laceration. Little did she know,
fate had one more twist. By sheer coincidence, a stranger appeared — of all people, an oncologist
— clutching a thin and tattered dog that had walked 1000 km to the family home where her husband
had died. He read her prognosis, caught the error, and a week later she was cured. Karma, it
seems, keeps its own ledger. You won't believe what happened next."""

GENUINE_SAMPLE = """A hiker was rescued on Saturday after falling near the gulch, authorities said.
According to the county sheriff's office, the 34-year-old was treated at the scene and airlifted to
a regional hospital, where officials confirmed she was in a stable condition. A spokesperson for
the search team told reporters the operation took roughly four hours in difficult terrain. The
report found no sign of foul play. Rangers reminded visitors to check conditions before setting
out; the trail has seen two other incidents this year, per park records."""


def _selftest():
    for name, sample in (("SLOP (the captain's masterpiece)", SLOP_SAMPLE), ("GENUINE (news-style)", GENUINE_SAMPLE)):
        conf, reasons = score(sample)
        print("\n=== %s ===" % name)
        print("  confidence: %d/100  ->  %s" % (conf, verdict(conf)))
        for r in reasons:
            print("    " + r)


if __name__ == "__main__":
    _selftest()
