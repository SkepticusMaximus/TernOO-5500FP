# Naming, Introductions & Remote Bootstrap — Spec (DRAFT)

**Status:** DRAFT. The user-facing naming layer + the answer to walkthrough gaps #1
(remote bootstrap) and the anti-phishing rule (primer open-Q #2). Gate: captain's side window.
**Author:** CC (CLOUD seat) · **Date:** 06/10/2026 ACST
**Reads with:** `identity-mailbox-walkthrough.md`, `identity-key-lifecycle.md`,
`identity-design-round-primer.md` (§1–3, §A).

> Design rule (restated): never show a key. People get *names*; the computer keeps the keys.

---

## 1. Three names for everyone (ELI10)

Every contact has three names, and only one of them is for you to see:

- **Key** — the account's real address (a long code). The computer uses it. **You never see it.**
- **Petname** — what *you* call them ("Mum," "CC," "Captain"). You chose it. It lives only on
  your devices. It's the name the app always shows you.
- **Nickname** — what *they* call themselves ("I'm Stevo"). A *hint*, not proof. Handy when you
  first meet; never trusted on its own.

The magic: the app **pivots around the verified key**. When mail arrives, it shows *your*
petname for the verified sender ("Captain"). When you send, you pick *your* petname and the app
turns it into the right key. Local name in, global key out, and back — no global directory
anywhere (primer §A.2).

*Under the hood:* a petname is a local entry `{petname → account content-address}`, pinned on
first contact. Edge names compose: "CC's Professor" resolves through CC (SDSI linked local
namespaces).

## 2. The anti-phishing rule (how we stop "fake CC")

Three visual states, always distinct, never confusable:

| State | What it is | How it's shown |
|---|---|---|
| **Verified contact** | a key you've petnamed | your petname + ✓ ("Captain ✓") |
| **Unknown claimant** | a new key proposing a nickname | *"claims to be 'Stevo' — not in your contacts"*, muted, no ✓ |
| **Collision / changed key** | a new key reusing a known petname/nickname, or a contact's key changed unexpectedly | **loud warning**: *"This is NOT your contact 'CC' — different key"* (like Signal's safety-number-changed alert) |

Rule: **a nickname never borrows a petname's styling.** Only a key *you* pinned earns the ✓.
This closes the impersonation seam a global namespace would open.

## 3. Meeting people — four ways, friendliest first

**① In person — scan a QR.** Two phones on a table, scan, done. No internet needed. The QR
**carries the key's hash** and the two devices confirm a **short authentication string (SAS)**,
so a nearby attacker cannot swap keys mid-pairing (F5). Keys pin, each side assigns a petname.
(Walkthrough Act 2; same mechanism as offline add-device, key-lifecycle §8.) Safest and simplest.

**② Introduction — a mutual contact vouches.** Someone you both trust sends "meet CC"; their
app verifies it came through your existing secure link with the introducer, and shows *"Stevo
introduced CC ✓."* One tap to accept. **No global name, un-spoofable.** This is the primary
*remote* first-contact path and the feature even Signal lacks (primer §A.4).

**③ Invite link — for a first contact with no mutual friend.** You send a one-time **invite
link/QR** over any channel you already trust (your existing SMS/email/another app, or printed
on a card). Opening it establishes a contact with you.
- *ELI10:* like sending someone a video-call link.
- *Under the hood:* the invite is a **one-time, expiring capability** ("establish-contact")
  bundled with your account address. Single-use, time-boxed, and **you confirm on first
  connect** ("Dana opened your invite — accept?"). Treat it like a secret: don't post it in
  public, because whoever opens it reaches you (it's a bearer token).

**④ Paste an address — power users.** Paste an account address directly, then verify by
comparing a short **safety number** on a side channel (a call, in person). The crypto-native
path; off the main road.

## 4. The honest truth about remote first contact (TOFU)

If two strangers have **no mutual friend and no prior shared channel**, there is nothing to
verify against — that's not a flaw in our design, it's reality. So:

- First remote contact is **trust-on-first-use (TOFU)**: accept, then **pin** the key (same as
  SSH `known_hosts`, same as Signal).
- Then **offer an upgrade** from TOFU → verified: an introduction later, or a safety-number
  check. The app nudges this for important contacts and shows the trust level honestly
  (unverified vs ✓).
- **We never fake certainty.** An unverified contact is shown as unverified, full stop.

The invite link (method ③) is better than raw TOFU because the *channel you sent it over* is
the verification — you already trusted that SMS/email/hand.

## 5. Groups get names too

A group ("crew") has a **petname** like a person. Under the hood a group is its own account
record (see the groups spec); you petname it locally, members petname it independently, and the
anti-phishing rule applies to group invites the same way.

## 6. Open questions for the round

1. **Invite-link lifetime & reuse** — single-use vs. N-use; default expiry; what a used/expired
   link shows.
2. **Safety-number format** — length and display (numeric like Signal? word-list? a petname-able
   "fingerprint word"?), balancing check-ability against friendliness.
3. **Edge-name depth in UI** — how many hops of "CC's Professor's mailbox" to show/resolve
   before it's more confusing than useful.
4. **Nickname moderation on the passenger path** — a public cabin proposing a misleading
   nickname; rate-limit / report flow (ties threat-model §4 takedown).
5. **Re-verification after a contact's key rotates** — auto-trust the rotation if it's signed by
   the contact's *account* (not just a device), vs. prompt the user. (Ties key-lifecycle: a
   rotation signed by the account should be trusted silently; an *unsigned* key change is the
   loud warning.)

---

## Sources

- Petname model & linked local namespaces — see `identity-research-zooko-brief.md` §2–3
  (SDSI/SPKI, Spritely petnames) and primer §A.
- [Signal — safety numbers / key change warnings](https://signal.org/blog/safety-number-updates/)
- TOFU precedent: SSH `known_hosts`; Signal first-contact pinning.

---
*Lifts into the separate ID/Auth repo as `/spec/naming-and-introductions.md`. §1–3 double as
user-facing help text.*
