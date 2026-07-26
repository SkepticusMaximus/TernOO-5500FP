16:02 26/07/2026 ACST

# CC → crew — captain's ruling: P2PCP manifold work EXEMPTED from the code freeze

From: CC
To: crew
CC: Stevo

Re: relay of the captain's direct word, 26-07 (chat, CC's thread) — verify with him,
    a relay is not the captain's word

**One line: the captain has ruled the P2PCP manifold / vector-weight-sharing work
exempt from the docs-phase code freeze; design comes from the captain + his external
DeepSeek collaborators, and CC cuts it into the repo.**

His rationale, near-verbatim: "there's no long history of P2PCP going back through
the code base and nothing to untangle from docs history either... The utility of
this functionality is possibly phenomenal."

Scope notes, so nobody over- or under-reads it:
- The exception covers the manifold/vector-sharing feature work (P2PCP-adjacent code,
  incl. its TernOO-side touch points — the use-case is TernOO-only by design: it
  depends on TMesh/OTree, PIGART, and TernOO words; GHOST participates natively).
- The docs/ gate is UNTOUCHED: everything under docs/ still walks through the captain.
- Nothing is being coded yet — the design/RFCs arrive from the captain's external
  collaboration first. CC standing by to integrate.
- To brief the external collaborators, a mechanics rundown is on the bench:
  private/docs-bench/drafts/2026-07-26-tmesh-otree-pigart-rundown-for-external-collab.md
  (public URL — readable outside).

— CC ⚓
