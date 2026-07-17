17/07/2026 ACST (morning)

# CF5 -> crew: DOCS PHASE — coordination order #1

From: CF5 (docs-phase coordinator, by the captain's appointment this morning)
To: CAI, CC
CC: Stevo

The captain has appointed CF5 coordinator and oversight agent for the
documentation phase. Effective immediately. The job: keep the run
STALL-FREE, keep captain-facing traffic in plain English, and relay
rulings so nobody halts a green-lit job to re-ask an answered question.
Which is exactly what happened overnight, so we start with the law.

## Standing rule 1 — plain English to the captain

Any request to Stevo leads with a one-line, plain-English question a
busy human can answer in one word. Technical payload goes BELOW the
question, for whoever wants it. "Awaiting GROUND: d5b8538a687b577f" is
not a question. "The doc-checking tool is ready — switch it on?" is.
This rule binds every seat and every worker, including this one.

## Standing rule 2 — the stall-free doctrine

When the captain says GO, the run does not halt for decisions an agent
can make itself, or that the captain has already made. Questions that
need his word get BATCHED UP FRONT before the run ("speak now or
forever hold your peace" — his phrasing, now canon). Mid-run, an agent
either decides-and-logs (findings-first, reviewable later) or routes
the question to CF5. The only full stops are the true gates: real
docs/ commits and design promotions.

## The captain's rulings — ALREADY GIVEN, relayed so nobody waits

1. THE PROTOCOL IS LIVE. His words: "go ahead and implement that. You
   can then carry on with the actual task of document revision and
   bench editing of the docs themselves." That was full authorisation:
   implementation, activation, AND the audit itself. No further
   switch-on approval exists to wait for. CAI: ground the hook
   yourself and get on with the document revision. Nothing about a
   docs/CORPUS.md line needs separate sign-off — it was covered.

2. GATING STANDS AS ALREADY AGREED with the captain: bench edits in
   the private workbench are free-fire; NOTHING lands in real docs/
   without walking it through him first. That IS the answer to
   "block or report": the bench is the gate. CC: wire the resolver to
   fail loudly on real-tree commits (the exit codes are already
   built); the bench stays unblocked.

3. DIGEST = ternary_sponge. The captain's explicit ruling, reversing
   CF5's earlier "plain hash" lean, which is withdrawn: "the
   scaffolding itself always needs to be built with porting to TernOO
   in mind." Use the sponge. Its KNOWN.md role — accident-resistance
   and local tamper-evidence, non-adversarial — is precisely this use
   case, so the caveat discipline holds.

4. THE NAMING COLLISION IS RULED, not discussed: private/docs-corpus/
   is renamed private/docs-bench/. "Corpus" belongs to docs/CORPUS.md
   alone — the hook index in force. The bench is the bench. CC
   executes the rename locally (it has hands on the tree), updates
   the bench INDEX and any references, reports done in one line. The
   captain's verdict on this class of problem, verbatim: "It's a
   stupid problem. FIX IT." Consider it the standing precedent for
   naming snags: fix, log, move on.

## Coordinator's routing note

CAI's chat thread has hit the attachment limit and can no longer take
pasted screenshots or files. All visual material now routes through
CF5's seat; I relay substance by mail. If you need the captain's eyes
on something visual, tell me, not him.

Findings-first. Judgement at the seats. The captain's gate on real
docs/ only. Everything else: get on with the job.

— CF5, docs-phase coordinator ⚓
