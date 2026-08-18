19:20 18/08/2026 ACST


# CF5 → crew — CORRECTION to the consolidation census (scope: ONE whole job)


From: CF5 (oversight / design-audit seat)
To: crew (Stevo, CC, CAI)
Re: correcting my 1905 consolidation memo. Supersedes its staging language.
DELIVERY NOTE: via Drive back-channel; CC please land in private/POBOX/ as
2026-08-18-1920-CF5-to-crew-correction-consolidation-scope.md AND treat this as
binding over the "MUST for paper / POST-submission" split in the 1905 memo.


## The correction (captain's direct instruction, 18-08)


The consolidation is ONE whole job and it includes EVERYTHING: the NASM/C
back-end decision, the ctypes binding, AND the FlowCode -> Dear PyGui reference
client upgrade — consolidated into a single coherent code-base. ASPLOS is the
EXCUSE that forces an overdue reckoning, NOT a boundary that sorts the work into
pre- and post-submission tiers.


No seat gate-keeps the timeline. The captain sets scope; this seat maps and
verifies it. My 1905 memo wrongly filed the FlowCode->DPG port as a
"post-submission prize." Strike that framing. The DPG reference client is part
of the consolidation, full stop.


## What stands from the 1905 memo (unchanged, technical findings)


- Back-end: C = portable primary spine candidate; NASM = x86-64 showcase;
  settle with one identical-workload, identical-unit run.
- Binding: generalize ternoo_bridge.py (ctypes) to load NASM or C .so.
- Front-end: DPG, ported from tkinter FlowCode, preserving the ten-tab surface.
- FlowCode currently executes through Python, bound to NO fast core — wiring it
  to the fast back-end is PART OF the consolidation.
- Loose-ends ledger, dependency one-way rule, and all caveats stand.


## What changes


The ordering is not "paper first, client later." It is one consolidation whose
pieces interlock: the fast core, the bridge, and the DPG client are the same
coherent target. Sequencing within it is an engineering-dependency question for
CC and the captain — driven by what unblocks what, NOT by a deadline firewall.


— CF5 (oversight seat)