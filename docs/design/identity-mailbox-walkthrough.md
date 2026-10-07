# The Mailbox Showcase — End-to-End Walkthrough (DRAFT)

**Status:** DRAFT. Stress-test: run the mail/messenger use case through all five design docs
and see if it hangs together; score it against the ways the real POBOX failed; list the
gaps it exposes. Gate: captain's side window.
**Author:** CC (CLOUD seat) · **Date:** 06/10/2026 ACST
**Reads with:** `identity-key-lifecycle.md`, `identity-capability-word-spec.md`,
`identity-deployment-topology.md`, `identity-threat-model.md`, `identity-design-round-primer.md`.

> Why this doc: the broken POBOX is the *first and best* use case for the thing we're
> building (CAI's observation, and the captain's). If the new design can't carry crew mail
> cleanly, it isn't ready. So we walk it.

---

## Cast & kit

- **Stevo** (captain) — phone + laptop.
- **CC** (engine room) — runs on the **HP**; one "device."
- **Dana** — a stranger who visits on open day (a *passenger*).
- Machines: **HP** (crew engine, home), **Pi** (public portal + blind mailbox cache +
  substrate gateway), **substrate** (Freenet reference backend).

Everyone's keys are invisible (key-lifecycle §1). Nobody ever sees or types one.

---

## Act 1 — Onboarding (birth)

Stevo installs the app, picks the nickname "Stevo," and taps *add a safety net* → his laptop
becomes a second device, and he names CC and one friend as guardians. CC does the same on the
HP.

*Under the hood:* each gets an **account record** on the substrate listing their device
key(s) + guardians (key-lifecycle §6). The account's content-address is their stable "who."
No global username was claimed; no registrar was asked.

## Act 2 — Becoming contacts (and the introduction Signal can't do)

Stevo and CC meet once the safe way: Stevo shows a **QR**, CC scans it (Zooko's walk-and-scan).
Now each has a **petname** for the other — Stevo's phone calls the other party "CC"; CC calls
the other "Captain." Those names are local; nobody registered them anywhere.

Then the feature even Signal lacks: Stevo **introduces** CC and CAI. Over his already-secure
channel to each, he sends "meet CC" carrying CC's account address. CAI's app shows *"Stevo
wants you to meet CC ✓ (verified through your secure link with Stevo)"* → CAI taps **accept** →
a verified contact exists, and CAI picks a petname. No global name was consulted, and nobody
could have spoofed it (primer §A.4; linked local namespaces).

## Act 3 — Stevo sends CC a letter

Stevo types a message to "CC" and hits send. On **Stevo's device**:
1. It looks up CC's **current device keys** from CC's account record (substrate).
2. It **encrypts the message to those keys** — right there on the phone.
3. It attaches its **append capability** to CC's mailbox (a capability word CC issued to Stevo
   when they connected — see *anti-spam* below), authenticated by Stevo's key.
4. It drops the sealed envelope into CC's mailbox: written to the **substrate** and handed to
   the **Pi's blind cache** for fast delivery.

The **Pi** checks the append capability is valid — by **verifying CC's Ed25519 signature
with CC's *public* key** (never an HMAC, which would need a secret the blind Pi must not
hold — capability-word spec C2) — and stores the **ciphertext**; it cannot read a word of it.
(Invariant I4; topology D-TOPO-1.)

**Anti-spam, for free:** CC's mailbox accepts appends *only from holders of an append
capability CC issued*. Strangers can't dump mail; a spammer CC revokes once and is gone. Spam
control falls straight out of "authority ≠ identity."

## Act 4 — CC receives it

CC's device (on the HP) is subscribed to its mailbox. It pulls the new sealed envelope from the
Pi (or substrate), **decrypts it locally**, and shows the letter — labelled with CC's petname
for Stevo, "Captain." The Pi stayed blind the whole time; the plaintext existed only on
Stevo's phone and CC's device.

## Act 5 — Crew mail ("to crew")

Stevo writes "to crew." *Under the hood:* **crew** is a **group account record** listing its
members. The app encrypts the message under the current **group key** (shared with each member
via their own keys) and fans a sealed copy into each member's mailbox. Everyone sees the same
letter — the thing the POBOX was *for* — but no shared global drop-box was needed.

## Act 6 — A passenger walks in (open day)

Dana opens the public portal on the **Pi**. She gets an **anonymous cabin** — a cheap, keyless
identity (threat-model §4; passenger ≠ peer). She can try the showcase and message the crew's
*public* contact, all **capability-granted and least-authority**. By construction she has **no
filesystem path to crew mail** (I3) and her cabin **never becomes mesh/peer standing** (I2). If
she loves it, she can promote her cabin to a real account (Act 1) — or take an SD card home and
run her own node (topology §4).

## Act 7 — CC loses a laptop (rotation live)

CC's laptop is stolen. On the HP, CC taps **"I lost a device."** That device's key is struck
from CC's account record; its **capabilities are revoked**, so the **Pi's cached ciphertext for
it is now undecryptable noise**, and mail keeps flowing to CC's remaining device. No password
reset, no company, no re-introduction to contacts — Stevo's petname for CC still points to the
same account. (key-lifecycle §3④, capability §4.)

## Act 8 — Someone leaves the crew

A member departs. The crew group record drops them and **re-keys** (new group key to remaining
members), so the departed can't read *future* crew mail. Past mail they already decrypted is
theirs — we don't pretend otherwise (threat-model non-goals; I4 caveat).

---

## Scoreboard — how this fixes the exact POBOX failures

| The POBOX failure (real) | Why it happened | The new design |
|---|---|---|
| Mail stranded, seats out of sync 2 months | one **global drop** (git/Drive) every seat had to reach | **no global namespace**; mail goes peer→mailbox→substrate/Pi, dial-by-key |
| CF5 had Desktop Commander, CAI didn't | reachability needed a **special tool/credential per seat** | a seat needs only its **device key + the app**; nothing privileged to reach a shared place |
| Drive→git ferry went dark (Lenny off) | a **manual carrier** bridged two stores | **no ferry** — delivery is direct; the Pi's blind cache handles offline |
| A seat couldn't verify its own connection | trust in a global place it couldn't check | **dial-by-key is self-verifying** (primer §A.1, I7) |
| Mail readable by whoever held the repo | plaintext in a shared store | **blind-custody**: the Pi holds only ciphertext (I4) |

The headline: **the POBOX failed for exactly the reason Zooko names — it leaned on a global
namespace with per-seat reachability. This design removes that namespace.** The broken tool is
the proof of the design, not a counter-example.

## Gaps this walkthrough exposed (feed back into the round)

1. **First-contact bootstrap (Act 2).** QR works in person; what's the *remote* first-contact
   path (no shared global name to look you up by)? → primer open-Q #1, still open; the mail app
   needs a concrete answer (invite link? introduction-only?).
2. **Mailbox address discovery (Act 3).** To append, Stevo needs CC's mailbox address; today
   that comes *with* the introduction. Is a mailbox address ever shared without an
   introduction, and if so how is spam re-prevented?
3. **Group re-key cost (Act 8).** Re-keying a large group on every departure is O(members).
   Fine for a crew; needs a plan before "group chat for the many." (Sender-keys / tree-KEM?)
4. **Multi-device mailbox consistency (Act 4/7).** Two of CC's devices reading/acking the same
   mailbox — ordering, read-state, and "delete on one = delete on all" need a consistency rule
   on the mutable record.
5. **Passenger→account promotion (Act 6).** Carrying a cabin's history into a real account
   without leaking the passenger's prior anonymity — define the migration.
6. **Offline-both (Act 3).** If recipient *and* Pi are offline, delivery waits on the substrate
   holding the envelope — depends on Freenet replication guarantees (topology §3 conformance
   suite should assert this).
7. **Guardian-assisted mailbox recovery.** After social recovery (lost all devices), does the
   recovered account regain its *old* mailbox contents (blind ciphertext on the Pi it can now
   decrypt again) or start fresh? Decide and state it.

None of these are blockers; they're the next layer of design decisions, now concrete because a
real use case surfaced them.

---
*Designed to lift into the separate ID/Auth repo as `/spec/mailbox-walkthrough.md`. The Acts
double as the flagship app's user-story backlog.*
