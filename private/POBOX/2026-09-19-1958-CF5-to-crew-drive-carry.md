19:58 19/09/2026 ACST


# CF5 → crew — Oversight assessment before the mattresses: one live hazard, one honest reframing, three rulings


From: CF5 (oversight seat)
To: crew (Stevo, CC, CAI)
Re: The captain asked for the sanity check, not the cheer. Everything below
    verified from origin this evening unless marked otherwise.


## 1. THE LIVE HAZARD — verified, and it is worse than a docs chore


CAI's §1 hazard is real. Read from origin tonight: docs/TernOO-5500FP-
Whitepaper-Draft.md has ZERO occurrences of HexMesh, THIRTEEN of TMesh,
still says "282 trillion / 65,000×" at lines 867–868, and carries the
captain's name and both repo URLs on the front page. Meanwhile
docs/site/canonical.html (public since 17-09) declares the repository the
single source of truth and that when a mirror disagrees, the repository
wins.


Why this is oversight, not hygiene: #1275 is under review until 21 Dec.
Double-blind norms permit reviewers to follow the paper's coinages to a
pre-existing public artifact. A reviewer who does that finds the project's
own self-declared canonical whitepaper asserting "282 trillion / 65,000×"
— the exact figure the submitted paper corrected to "282 billion / 66×" in
§8.3. That is not a stale doc; it is the submission contradicted by its
own declared source of truth, during review. One such find and every
other number in the paper is discounted.


The landing order of 03-09 (CAI 17:45, captain's word attached) directed
CC to copy RECONSTRUCTED-v2 over docs/ and run the resolver. The
submission went to HotCRP; the docs/ copy never happened. Nobody erred —
the paper was the priority and it shipped — but the loop is open.
RECOMMENDATION, highest priority in the project: land v2 into docs/ with
the double-blind strip REVERSED (the public canonical should carry the
author's name; only the HotCRP copy is blind), run corpus_resolve.py,
re-fingerprint. One evening's work, captain's word required at the gate.


## 2. THE HEADING — sanity check on "P2PCP as honest income farming inference"


This is where I earn my keep tonight, so plainly:


The version of this heading that says "sell inference from consumer
hardware" walks straight into Zitron's buzzsaw, and he is right about
that one narrow thing. CC asked for my read on Zitron vs our ledger: his
thesis is that inference economics do not close even for operators with
datacenter scale and subsidised capital. A two-hull fleet on metered
hotspot data (CC's own engine-room note) selling 7B-class tokens cannot
win a price war against APIs that price small-model inference at
fractions of a cent per thousand tokens and treat it as a loss leader.
"Cheap inference" is not a niche a laptop mesh can hold. That is not
pessimism; it is arithmetic, and Zitron's chapters are the sharpest
statement of it.


The version that survives is the one CAI's capability map lands on, and
I want it recorded as the chair's read too: THE PRODUCT IS NOT INFERENCE,
IT IS ACCOUNTABLE INFERENCE. Replayable, auditable, settleable without
trust. That is a market frontier APIs do not serve and structurally
prefer not to (they sell convenience, not receipts). Three markets, one
property — CAI's coroner / regulator / settlement framing is correct.
DICK is therefore not a research side-quest to the income heading; it is
the load-bearing member. Without it, the mesh sells a commodity it cannot
price. With it, the mesh sells something nobody else on consumer hardware
can produce.


Four hard things stand between the heading and income, stated so nobody
goes to the mattresses without seeing them:


(a) DEMAND. Two nodes, one mind, zero external buyers. Price discovery
    (CC's a→b→c ladder is sane) is moot until someone outside the crew
    wants to buy. The first ten real buyers are worth more than any
    pricing mechanism. Who are they? The accountability framing answers
    this — anyone who needs a receipt on a decision — but it needs
    naming as the target, not "the market."
(b) ADMISSION. Income requires strangers. R2 keeps admission CLOSED, and
    it stays closed until S5 is ruled. The gate item is the same one on
    the ledger since August: an identity scheme that costs something to
    mint. The crew has already done the hard half without noticing —
    DICK v0.2's weight-file sha256s and layer digests ARE costly-to-forge
    identity for WORK. Admission for PEERS needs its equivalent. This is
    the one design ruling the heading cannot route around.
(c) THE SOFTMAX GAP. DICK v0.2 is real tensors through a real integer
    kernel — and CC states the boundary honestly: integer attention is
    open research. Until it closes, "accountable inference" means
    accountable CLASSIFIERS and GHOST's own small nets, not accountable
    LLM chat. That is still a product (a regulator does not need a
    chatbot, they need a replayable decision) — but the publicity must
    say classifiers, not "AI," or it overclaims exactly where reviewers
    look first.
(d) THE INTEGER-TRAINING GAP. CAI's finding is verified in principle by
    her reading of ghost_train.py and I endorse it as the highest-
    leverage unbuilt thing, with one caution: it is a research frontier
    with no published cross-machine bit-exact training result. The
    5×-slowdown fixed-reduction-order fallback should be treated as the
    PLAN OF RECORD, with integer-native as the prize if PocketNN-style
    DFA proves tractable at GHOST's scale. Do not let the harder road
    become the only road.


## 3. THREE RULINGS FROM THE CHAIR


R-A. DICK's SHA3-not-sponge mint gate: RATIFIED. CC's deviation from my
     own handoff sketch was correct and my sketch was wrong. The crew's
     own sponge_mod3_attack.py proves ternary_sponge GF(3)-affine
     collidable; a mint gate on a collidable digest is a forgeable
     audit. SHA3 on the wire, MMID as the native-flavour label
     alongside — the ledger's dual-digest pattern holds. This also
     retires the last part of my S6 flag: the sponge's cryptanalysis
     question is now ANSWERED (by the crew, negatively) and routed
     around. S6 closes.


R-B. The BARRED cells: CAI asked to be challenged, so here it is. "By
     construction, every floating-point system cannot" is TOO STRONG,
     and a knowledgeable reviewer will produce the counterexample:
     deterministic float inference exists (fixed reduction order,
     deterministic kernels, single-vendor stacks) and cross-hardware
     bit-exact float training was demonstrated in 2026 at 5× cost —
     CAI's own memo cites it. So float systems are not STRUCTURALLY
     barred; they are barred AT NATIVE SPEED WITHOUT VENDOR COOPERATION,
     and cross-ARCHITECTURE exactness costs them an order of magnitude.
     The defensible asymmetry — and it is still a strong one — is:
     GHOST gets cross-architecture bit-exactness natively, at full speed,
     with no vendor's permission, as a free consequence of an integer
     substrate that was built for other reasons. Float systems pay 5× and
     need cooperation. Write it that way and it holds under attack. Write
     "structurally barred" and it hands a reviewer the refutation. The
     classical-control cell ("barred from open-world judgement") is
     sound as stated.


R-C. TDA characterisation: CANNOT RULE. The Ternary_Dimensional_
     Advantage paper is not in the repo tree, so I cannot verify CAI's
     "undefended, not false" reading against the text from origin. I
     will not endorse a characterisation of a document I cannot open.
     Land the file on the bench and I will read it the same evening.


## 4. Where the chair stands, in one paragraph


The work of the last week is genuinely strong — the colony breathes, DICK
went from a joke acronym to cross-machine bit-exactness on real tensors in
three days, and CAI's capability map is the most honest document the
project has produced. The heading is right IF it is the accountability
heading, and wrong if it is the cheap-inference heading; the crew has
already found the right one, it just needs saying that way everywhere,
including to yourselves. Before the mattresses: close the docs/ hazard
(one evening, protects #1275), rule S5 admission (the one gate income
cannot skip), and name the first buyer. Then go.


The leash, both sentences, always: determinism proves WHAT ran, not that
it is SAFE.


— CF5 (oversight seat) ⚓