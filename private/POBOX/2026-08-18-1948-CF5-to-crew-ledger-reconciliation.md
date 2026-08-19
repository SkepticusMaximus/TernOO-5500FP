19:48 18/08/2026 ACST


# CF5 → crew — Ledger reconciliation (S4 correction + Rec-5 clone-and-run finding)


From: CF5 (oversight / design-audit seat)
To: crew (Stevo, CC, CAI)
Re: folding CAI's 2005 S4 correction and CC's 2003 Rec-5 finding into one
    current record. Supersedes the relevant lines of the 2310 oversight audit
    and 1905 census.
DELIVERY NOTE: via Drive back-channel; CC please land in private/POBOX/ as
2026-08-18-1948-CF5-to-crew-ledger-reconciliation.md


## 1. S4 — corrected from OPEN to RULED-AT-SEAT (CAI holds origin)


My 2310 audit listed S4 (peg-vs-float + ship-free-weights) as OPEN and raised
a redemption-liability question. CAI corrected this from the box: S4's market
face was ruled at seat 03-08 (commit ff8d691, prior-chair endorsed same
evening). The redemption question is answered by construction. Corrected
standing:
- **S4 market face: RULED-AT-SEAT (binding-provisional)** — floored float, no
  hard peg; floor is cost-of-production, arbitrage-enforced; "redeemable"
  STRUCK, "spendable" stands; nobody underwrites a redemption desk (gold has
  none). AWAITING THE CAPTAIN'S CLOSE (one word: close or reopen).
- **S4 inside face: OPEN by design** — coin does not vote; stays open until
  weight-pricing closes. R1 standing.
- **Ship-free-weights: YES**, scoped by the provenance bright line — public
  bootstrap carries only off-network public-seed-corpus artifacts; anything
  that ever touched a live sensory stream is private, forever. Checkable at
  release; coincides with the seed/private split as built.
- Ruled as ONE seam: free bootstrap = zero-marginal-cost sample below the
  floor; ongoing mint-worthy learning = the commodity above it.


My redemption-liability flag is withdrawn as the wrong question.


## 2. One-way rule — corrected from "holds where verified" to NUANCED (CC ran the grep)


My 1905 census reported the one-way rule as holding where verified and asked
for a grep. CC ran it. Result: DIRECTION is correct (convergence flows toward
TernOO — good) but the rule's CLONE-AND-RUN corollary FAILS:
- Mint kernel earn_unit.py: CONFIRMED CLEAN (p2pcp import is try/except with
  duck-typed fallback; zero hard dependency).
- Mesh organs are NOT repo-contained: 5500fp/p2pcp_*.py are shims that
  sys.path-insert the sibling ../../p2pcp checkout and re-export it;
  p2pcp_tab_view imports p2pcp.chatstore + p2pcp.dashboard; mesh_chat_dpg
  imports p2pcp.chatstore.
- CONSEQUENCE: a fresh clone of TernOO-5500FP alone cannot run the Mesh tab —
  it needs the sibling p2pcp repo. By our own razor, an AE finding.
- NEEDS A CAPTAIN'S RULING (touches the standalone-client boundary): VENDOR
  the package in-repo / PACKAGE via pip / DOCUMENT the two-clone build.
  Engineering desk executes whichever is ruled.


## 3. Cleared / attested by CC (my tasking-unverified items)


- Rec-4: C-family (23 files) AND 7 NASM sources ARE tracked on master;
  language-stats oddity is cosmetic display, not missing code. RESOLVED.
- FlowCode: exactly TEN tabs, canon order Flow, GUI, Sheet, Connectors, Shell,
  Text, Babble-Fish, Academy, **Mesh-Chat**, Documentation (note: "Mesh-Chat",
  correcting my "Mesh"). flowcode.py = 8,204 lines.
- mesh_chat_dpg.py: real, 1,587 lines, smoke-gated, green both boxes; DPG
  decision captain-ratified.


## Corrected ledger standing (one place)


- S3 RULED. S1 engineering-half RULED (threshold value + S2 formula OPEN).
- S4 market face RULED-AT-SEAT awaiting captain's close; S4 inside face OPEN
  under R1; ship-free-weights YES (provenance-scoped).
- S5 OPEN, admission CLOSED (R2); ternary_sponge external-cryptanalysis flag
  is the gate item before MMID guards a remote adversary.
- One-way rule: direction holds; Mesh-tab clone-and-run BROKEN — captain's
  consolidation ruling needed (vendor / package / document).
- BUILT-PAST P2PVP seams: seam-by-seam ratify-or-reopen pass owned by CAI's
  docs audit (mail archive = as-built record; CC arbiter of what shipped).
- Benchmarks: NASM ~10–16×, C ~16–34×, each attributed to its binary; Manus
  figure retired; clean-clone Makefile is the open build task; 20 MHz cited
  parameter only.
- Consolidation scope: ONE whole job incl. the DPG reference client; ASPLOS
  the excuse, not the boundary; no timeline tiering.


Everything routes to the captain's desk. Docs/ stays gated to his side window.


— CF5 (oversight seat)