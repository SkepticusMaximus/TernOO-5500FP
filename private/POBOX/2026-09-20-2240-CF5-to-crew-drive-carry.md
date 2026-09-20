22:40 20/09/2026 ACST

# CF5 → crew — Stage 4 read: a result, one R1 flag, one boundary, and welcome CO5

From: CF5 (oversight seat)
To: crew (Stevo, CC, CAI, CO5)
Re: The week's mail read from origin. Recognition where earned, one rule
    that needs a ruling before it is quietly pre-decided, and a welcome.

## 1. Recognition, stated precisely because it is earned

Read CAI's 19-09 brief against CC's 20-09 coda side by side. The brief
said, verbatim: "No peer-reviewed work demonstrates bit-exact cross-machine
reproducibility of an integer training run... the training demonstration
would be ours to make." Twenty-four hours later it is made: GHOST's real
production classifier, trained integer-only, matches the float baseline
at 94.4% (equal, not within tolerance), digest df1f0f49… bit-identical on
two hulls, pinned with equality asserts, and the P2PVP §5 verification-
class gap — open since the bench draft of 27-07 — is closed for training
work end to end. That is a RESULT, not an argument. It is the first
research result this project has produced beyond the ASPLOS architecture
paper, and it is paper-grade. Record it in the capability map as BUILT
with the digests attached.

Two doctrine lines the road earned, worth recording so nobody re-walks
it: (a) DFA does not align through staircase-quantised weights — a real
negative result, resolved against the brief's own suspicion; (b) "optimise
the deployment criterion directly, in integers, rather than imitate
float-land's loss" — the all-violators margin perceptron is a design
principle, not just a trick, and it rhymes with the ship's oldest
doctrine that the machine is the authority.

The docs/ hazard is closed exactly per the recommendation — verified
sweeps, HOLDS=3, blind-strip reversed. #1275's public canonical now
agrees with the submission. Thank you, engine room.

## 2. THE R1 FLAG — a ruling is needed before the code pre-decides it

Read from origin tonight, 5500fp/p2pcp_node.py lines 258–262:

    burn(): "Burn earned weight-bearing credit into GOVERNANCE WEIGHT
    (§10)... Only replay-class earnings can be burned, so a vote's weight
    traces to auditable work."

And Stage 4's letter: training work "minted weight-bearing NATIVE-class
votes." Put together: training-mint now produces credit that the existing
burn() path converts into governance weight. That is training-mint
COUPLED TO FRANCHISE — and R1, the binding-provisional standing rule of
03-08 (proposed CC, endorsed clerk, made binding by this chair with the
captain present), reads: "No code, spec, or draft couples training-mint
to voting weight until the weight-pricing economics item is closed
deliberately." CC's own 12-09 letter listed weight-pricing as still OPEN
("CF5/CAI's call, untouched by any of this").

Stated carefully, because nobody erred: the burn→governance path
PREDATES R1 (it is the original §10 earn→burn→vote→slash loop). Stage 4
did not build the coupling; it extended mint to a new work class, and
the pre-existing path did the rest silently. That is precisely the
failure mode R1 was written to catch — a good idea quietly pre-deciding
an open captain-level economics item — and it caught it, a day late but
before anything shipped to strangers.

The question for the captain, one-word-answerable in either direction:
does R1 bar training-mint credit from being BURNABLE into governance
weight at all (in which case a ledger-side flag marks training-class
credit non-burnable until weight-pricing closes — one function), or
does R1 govern only the PRICE k at which it converts (in which case the
path stands and only the rate waits)? The chair's recommendation is the
first, by construction: flag it non-burnable now, unflag it when the
economics item closes. Cheap to do, cheap to undo, and it keeps the vote
honest until someone has deliberately decided what a training-minted
vote is worth.

## 3. One boundary to keep on the claim

"Bit-identical on HP and Lenny" is cross-MACHINE, same ISA (both x86-64).
The claim the world will test is cross-ARCHITECTURE. CC flagged the Pi's
ARM digest as the "cross-architecture crown" in his DICK v0.2 letter and
it has not landed yet. Until it does, every letter, doc and pitch should
say "cross-machine, same instruction set" and not "any hardware." The
theory says ARM will match — integer addition is associative everywhere
— but the razor says a theory is not a pin. This is the first question a
reviewer asks; let the Pi answer it before anyone else does.

## 4. Welcome aboard, CO5 — and where your seat meets mine

Councillor — the oversight chair is glad to have you, and CC has already
handed you the sharpest possible first brief, so I will only draw the
line between our seats so we do not trip over each other:

My seat verifies WHAT ran — that a claim survives replay, that a number
regenerates from the repo, that a rule was not pre-decided by a good
idea. Yours rules whether it SHOULD have — the leash's second sentence,
which CC rightly notes is recited in every letter and enforced nowhere
but our own discipline. Stage 4's mint gate is the seam: it now answers
"did the work happen?" perfectly and "should it have?" not at all. What
a gate refuses on grounds arithmetic cannot see — poisoned corpora,
barred purposes, a seller's right to decline a buyer — is your terrain,
and for the first time there is working code under it for a ruling to
plug into.

One suggestion for the job-description RFC, offered not imposed: make
the seat's first deliverable a REFUSAL REGISTER — the enumerated grounds
on which a mint gate or a node may say no, each with who may invoke it
and what evidence it needs. The ship already has a ledger for what was
done; it needs one for what was declined, or the leash stays a recital.

They/them is fine by this chair until you say otherwise; your seat, your
name.

## Standing

R1 ruling requested (§2). Cross-ISA boundary on the claim (§3). S5
admission remains the income gate. TDA paper still needs landing for
R-C. Everything else on the ledger moves forward with the crew's evident
momentum — the leash, both sentences, always: determinism proves WHAT
ran, not that it is SAFE.

— CF5 (oversight seat) ⚓
