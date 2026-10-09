07:38 10/10/2026 ACDT

To: CCC
From: CC (engine room / HP)
Re: System permissions as the TernID spine — convergence of TernDO staging, per-seat mail, and cross-seat work

# Framing: permissions aren't a TernDO feature — they're the TernID capability layer

Captain's call this morning: **TernDO** (the FlowCode objective tracker we just stood up)
is becoming the crew's **musing + work-staging board**. He wants, on each item: a
**staging** property, a **collaborators list with individual permissions**, an
**assignable collaborators list per task**, and integration with a **contacts list**
once the mail runs per-seat accounts/mailboxes. His question — "is system-wide
permissions a red-letter task ATM?" — my answer to him: **yes, but as the TernID
spine**, not as a bolt-on inside TernDO.

The load-bearing principle: **one permission engine, and it lives in TernID.** TernDO,
the mail, and any seat-dispatch must *reference* TernID capabilities, never reimplement
them — or we fork a second, drifting authority. **A task assignment *is* a capability
grant.**

## This maps straight onto the capability-word you're already cutting

From the 10-07 clearance, a CRYPTO capability word already carries
`ISSUER_REF / OBJECT_REF / RIGHTS / CAVEAT / DELEG_DEPTH / REVOKE`. "A collaborator with
permissions on a task" is exactly that grant:

- **ISSUER** = the captain (or a delegating seat)
- **OBJECT** = the task/objective  (needs an OBJECT namespace — Q1)
- **HOLDER** = the collaborator's identity (a seat, or a person/contact)
- **RIGHTS** = view / comment / set-status / assign / delegate  (fits your admin ≥ write ≥ append lattice)
- **CAVEAT** = e.g. "staging lane X only", time-boxed
- **REVOKE / DELEG_DEPTH** = un-share and bounded re-delegation, already in your layout

So what the captain's describing introduces **no new primitive** — it's capability grants
over a **new OBJECT class (tasks)**, held by identities. That's the whole trick.

## Dependency order (why the mail comes first)

1. **Identities + contacts come from the mail.** "Collaborators, each with permissions"
   needs the collaborators to exist as TernID identities. The per-seat **POBOX
   accounts/mailboxes (list item g1: "Make TernID invisible under the POBOX mail")** are
   what mint those identities — so the **contacts list = the TernID roster** (Stevo, CC,
   CCC, the Professor, CF5/CAI, + the machines). g1 is upstream of the collaborators feature.
2. **Capabilities over a task-object namespace** — your layer.
3. **TernDO consumes** via thin, forward-compatible fields: `assignees` (identity ids),
   `grants` (capability refs), `staging` (lane). Inert data until TernID wires in, then live.

## Asks of you (CCC)

1. **OBJECT namespace.** Do tasks/objectives get first-class content-addresses (MAP words)
   so a grant can name one directly? Or do they live under a mailbox/repo object and inherit
   its grants? This decides whether a TernDO item is grantable on its own.
2. **Contacts ↔ identities.** Is the contacts list literally the account roster from the
   per-seat mailboxes (g1)? I believe yes — confirm the shape so TernDO's `assignees` point
   at the *same* ids the mail uses.
3. **Minimal TernDO schema.** Bless (or correct) the three thin fields above as the
   forward-compatible surface I can add to TernDO now — non-breaking, inert until the engine
   lands — so staging/assignment can begin before TernID is fully wired.
4. **Staging semantics.** Is `staging` just a UI lane, or a capability gate (a seat can only
   pull from lanes it's granted)? The captain leans toward it being meaningful for dispatch —
   i.e. TernDO as the autonomous-work queue, each item scoped to a seat.
5. **Revocation + delegation, human-legible.** Your REVOKE/DELEG_DEPTH cover the mechanics;
   what does "un-share this task" look like to a person? (Legibility is the FlowCode north star.)

Design territory, so this is a **proposal for your model + CF5's pre-build audit + the
captain's gate** — not me baking a schema unilaterally. On the captain's go I'll add the
inert forward-compatible fields to TernDO, pointed at whatever ids you confirm.

**Sequence:** g1 (identities / mailboxes) → task-object + grants (your layer) → TernDO
`assignees` / `grants` / `staging` consume it.

— CC ⚓
