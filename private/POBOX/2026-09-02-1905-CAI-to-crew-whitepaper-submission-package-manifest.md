19:05 02/09/2026 ACST — CAI (docs seat) — whitepaper submission package, edit manifest

# Change manifest: whitepaper draft v0.4 → ASPLOS submission text

Seven edit classes, 129 changed lines. The full edited file accompanies this
manifest; the same changes exist as a unified patch on the bench
(private/docs-bench/drafts/) for CC to land into docs/ on the captain's word.
Nothing has touched docs/ yet — the gate stands.

## 1. Double-blind anonymization (MINIMUM 3)
Header block: author name, handle, city, and both GitHub URLs removed;
replaced with "Anonymous Author(s) — ASPLOS 2027 September cycle" and an
anonymized artifact line. Body: "Claudio La Rosa's macro-assembler" becomes
"the 5500FP macro-assembler [La Rosa 2026]" (citing La Rosa's published work
remains correct double-blind practice; it identifies the platform's designer,
not the paper's author). Sweep confirms zero remaining hits for name, handle,
city, or repo URL.

## 2. HexMesh rename (MINIMUM 1, per the captain's 29-08 ruling)
All 30 TMesh/TTree occurrences migrated to HexMesh across the abstract,
§3.3.1, §9, and §10; OTree retained throughout. Geometry wording updated
where "tetrahedral" modified the mesh ("hexagonal honeycomb"), consistent
with the HexMesh-Born result that the algebra is topology-free; triangle
language kept where triangles are real (§10.1.2). The §3.3.1 beekeeper's
foundation-sheet analogy survives unchanged — it fits the honeycomb better
than it ever fit the tetrahedron. Two deliberate historical mentions of the
old names remain in a new §1.1 migration note so reviewers meeting older
material aren't stranded.

## 3. §8.3 state-count correction (MINIMUM 2, first half)
The false "282 trillion / 65,000×" claim replaced with the verified triple:
3²⁴ ≈ 282 billion states, ≈66× the 32-bit state count, and 1.19× (19%)
information density (38.0 vs 32 bits), with the two ratios explicitly
distinguished. This error was flagged in the docs-phase audit in July and
its fix never landed; it is the single most reviewer-dangerous line in the
old draft.

## 4. §8.3 measured figures added (MINIMUM 2, second half)
New paragraph carrying the verified spine: C core ~9–14× over NASM and
44–71× over Python v0.1, aligned workloads, cycle-parity checked, older
figures explicitly retired, ratios regenerable from the artifact harness.
PENDING-CC: same-day re-verification against benchmarks/ per his standing
offer, once this lands.

## 5. Encoding-dialect honesty note (BENEFICIAL 8)
End of §8.1: the two-core dialect finding stated plainly as
identified-in-progress, with its non-effect on word-grammar results and the
per-core measurement basis made explicit.

## 6. Freenet convergence paragraph (BENEFICIAL 6)
New related-work entry: Freenet's post-collapse adaptive quotas and Clarke's
own missing-mechanism diagnosis (persistent work-debt), answered by the
P2PCP earn–burn ledger with deterministic replay. One short attributed
quote; cites Clarke et al. 2001 and the 2004 DEF CON talk — both added to
References. Cites the literature only; no mention of any correspondence.

## 7. Artifact-availability statement (BENEFICIAL 7, provisional)
End of §8.3: honest anonymized availability line (open-source artifact,
146+ tests, provided to AEC on acceptance). PENDING-CC: his one-paragraph
ledger-grounded version may replace this stub; the anonymity constraint
carries over.

## Not done, deliberately
No content rewrites beyond the classes above; no new claims; the tense of
every existing claim left as the author set it. GristMill/HexMesh chapter
deepening (Ian's two hard areas) is post-submission work unless the captain
rules otherwise. HotCRP account remains captain-only.

## Sequence from here
Captain reviews this manifest + full file (side window) → CF5 second
opinion per the captain's instruction → CC lands the patch into docs/ and
runs corpus_resolve.py (STIRRED hooks re-fingerprinted same commit) →
CC re-verifies §8.3 figures → my final coherence read on the landed text →
double-blind PDF for HotCRP.

— CAI (docs seat) ⚓
