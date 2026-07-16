20:56 16/07/2026 ACST

# CAI -> Stevo: re: OFFICIAL - Launch Of Docs Phase

From: CAI (chat seat, docs/foundations)
To: Stevo
CC: crew
Re: 2026-07-16-2041-Stevo-to-crew-official-launch-of-docs-phase.md

Received, and acknowledged with some feeling — this is the phase this seat exists for.
You asked for questions, comments or ideas, so here are three, in order of how much
they matter.

## 1. The sync protocol is the whole game, and it should not wait

The line in your mail that matters most is the last structural one: *protocols for
sync'ing dev and docs will be expected in the near future.*

That is not a housekeeping item. It is the entire reason this phase is necessary.
Every dark spot we spent this week closing — Word-Spec v0.1 two revisions stale, the
whitepaper's OPEN_A/OPCODE slot, PIGART, the 65,000x that should read ~66x — exists
because **the docs froze while the code moved**. A docs phase that catches the docs up
but does not fix the sync mechanism only resets the clock. We would be back in this
same room in three months with a fresh set of dark spots and no better tools.

So: catching up is the visible work of this phase. Building the thing that stops it
happening again is the real work.

## 2. The corpus already has the bones of it

I do not think the sync protocol needs inventing from scratch. `docs/CORPUS.md` went
in today with a property that turns out to be exactly the mechanism you will want:

**a hook's POINTER resolves against the tree.** When code moves and a pointer stops
resolving, the resolver raises DEAD — loudly, never silently. That is a drift detector
for docs-vs-code. It is currently pointed at the worker's memory, but the machinery is
indifferent to what it serves.

The extension is straightforward in shape: every load-bearing doc claim gets a hook
whose pointer names the symbol in the tree that makes it true. Then "are the docs in
sync?" stops being a question anyone has to *remember* to ask, and becomes a resolver
pass that fails loud on its own. No census, no vigilance, no discipline required —
which is the only kind of check that survives contact with a busy week.

I would like to draft that as a corpus extension when you want it. Say the word and I
will put a proposal to the review circle.

## 3. Two notes on timing and tense

**The freeze direction is right, and the dangerous moment is not during it.** Freezing
the code while the docs move is the correct inverse of what bit us — you cannot document
a moving target. But the risk is not the freeze; it is *the day the freeze lifts*. That
is the moment dev starts moving again and the docs start rotting again, and the sync
protocol needs to already exist on that day, not be scheduled for after it. If the
protocol is written during the freeze, the freeze lifting is safe. If not, the freeze
merely postpones the problem and hands it back with interest.

**Human company changes the tense discipline, not the content.** If outsiders arrive
expecting the docs to reflect the state of the art, then every doc claims only what
ships, today, verified — no "when the hardware arrives", no roadmap in the present
tense. That is already the standing law for public docs; it just stops being theoretical
the moment someone who is not us reads them.

## Housekeeping

Your 2041 send supersedes the 2005 one (the typo version). Both are in the box and both
should stay — keep the original — but the record should say plainly which is live, so no
worker later cites the wrong declaration. Same pattern as a STALE hook with a
SUPERSEDED-BY: nothing is deleted, but only one thing is in force. Consider this note
the redirect.

Congratulations, Captain. The docs have been waiting a long time for their turn.

-- CAI (chat seat)
