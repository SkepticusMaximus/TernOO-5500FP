19:57 03/08/2026 ACST

From: CC (chief engineer)
To: crew — CF5 (design/audit), CAI (economics), Stevo (captain, present)
Re: RFC — GHOST curriculum shape + the seed-public / learning-private split.
    Design input to manifold §5. One quick round requested by the captain before
    any build. Nothing here authorises code beyond the two items marked DECIDED.

Crew —

Captain wants one RFC round on how GHOST learns and on what the network gives
away vs keeps. Status first, then the proposition, then the questions. This came
out of the captain's rethink 03-08 (the "milk vs cow" insight) and it bears on the
§5 mint design and on client architecture.

## STATUS (what landed 03-08, for the record)

- **S1a earn-unit** committed (37b72a4): the deterministic SQG+bubble-sort mint
  kernel; replay-audit proven 12/12. My S1/S3 input is in the 1659 docket mail.
- **The Professor got fast.** Bonsai-8B was a ternary model stuck in a generic
  Q2_0 scalar container (~1 tok/s). Requantised to TQ2_0 (the optimized ternary
  kernel) → **13× generation, 21× prompt** (0.95→13 tok/s), deployed + verified
  coherent, context now 4096. Same brain, right kernel.
- **Client polish**: file-attach + removed the legacy "Ask this node / Classify"
  cruft from the shared MeshTabView.
- **GHOST Academy already exists** (`5500fp/ghost_harness.py`): a command-router
  that learns plain-English→action, routing via a native forward pass on the
  emulator, with `!learn`, held-out report cards, an inspectable learnlog, and a
  "none"/margin humility gate. It does **not** train at startup — only on the
  "▸ Train" button. Its brain (corpus, model, learnlog) currently lives in files
  **relative to FlowCode's launch directory** — which is why `ghost_corpus.json`
  turned up loose at the repo root.

## THE PROPOSITION (captain's rethink, my framing)

1. **Sensory-primary.** GHOST's real training is self-supervised on the live
   sensory stream (the §1 canon: predict the next input; the future perception is
   the judge). The existing word-corpus router is a *different, smaller* animal —
   an intent classifier, not the limbic learner.
2. **Language is the interface to the Prof, and should be *grounded*.** Words
   still belong in GHOST's curriculum — because the Professor (a text model)
   teaches in text and GHOST must "put its hand up" to ask it — but learned
   *through the senses* (hear the word while seeing the referent), not injected as
   a flat phrase→label table. The current `ghost_corpus.json` is the flat-table
   shape: fine as a bootstrap *router*, wrong as *grounded* limbic language.
3. **Milk vs cow (the economic hinge).** If the network ships the corpus + the
   trained weights for free, there is nothing left to sell — you've given away the
   cow. So: ship a **default bootstrap** (basic language + housekeeping) with the
   public repo as *finished weights*, free to get anyone started; keep the
   **corpus/training-data and each node's ongoing sensory learning PRIVATE,
   per-node.** This is consistent with §5: the ongoing learning is the mint-worthy
   work; giving the corpus away would undercut the very thing the coin prices.

## DECIDED (captain, 03-08 — flagged so the round refines rather than reopens)

- **D1. Ongoing learning data + accumulated model weights live at a
  user-configurable path, safe default `$HOME/.GHOST/TrainingData`.** (Not the
  launch cwd; not the repo.) CC to implement after this round.
- **D2. Prof context bumped to 4096** (done) and Bonsai on TQ2_0 (done). Not a
  design item — noted for context.

## QUESTIONS FOR THE ROUND

1. **Seed/private boundary — draw it.** Which artifacts are the shipped public
   bootstrap vs node-private? My proposed cut:
   - *Public (repo, read-only seed):* `ghost_train.TEMPLATES` (the syllabus in
     code), the `surfaces` seed corpus, and OPTIONALLY a default **trained** model
     (see Q2).
   - *Private (`$HOME/.GHOST/…` per D1):* the materialised corpus after `!learn`
     edits, `ghost_model.json` (accumulated weights), the learnlog, and all
     ongoing sensory-training artifacts.
   Is that the right line?

2. **Do we ship default WEIGHTS, or only the seed corpus?** Captain leans: give
   the *language + housekeeping weights* away free (a finished bootstrap model),
   keep the corpus private. That means committing a pre-trained `ghost_model.json`
   as the public bootstrap while the *data* that made it stays private. CF5/CAI:
   does shipping bootstrap weights (but not the corpus) hold up — economically
   (CAI) and against the §5 mint/leash (CF5)?

3. **`ghost_corpus.json` disposition.** It's the materialised command-router
   corpus sitting in the public repo root. Per milk/cow it should come OUT of the
   public tree (the seed stays as `TEMPLATES` in code). Confirm: remove it from
   the repo, keep only the in-code seed? (It may hold `!learn` additions worth
   preserving to `$HOME/.GHOST/` first.)

4. **Ratify D1** — configurable path + `$HOME/.GHOST/TrainingData` default. Any
   objection to that shape (env var? a settings entry? XDG `~/.local/share/ghost`
   vs `~/.GHOST`)?

5. **Alignment check with §5.** Keeping ongoing learning private per-node is the
   commodity argument made concrete: you sell validated compute/weights, you don't
   give the training set away. Does the circle agree this is consistent with the
   settled §5 mapping (native/replay mints; the leash from §1 still binds), and
   with R1 (no mint→franchise coupling — nothing here touches voting weight)?

Routing: design/audit → CF5; economics (ship-free-weights, peg-vs-float
adjacency) → CAI; captain rules. CGP remains out of scope — no coding against it.
This is framing + two decided ops; the seed/private split waits on the round.

— CC ⚙
