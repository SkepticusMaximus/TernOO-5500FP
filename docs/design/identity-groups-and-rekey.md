# Groups & Re-keying — Spec (DRAFT)

**Status:** DRAFT. Answers walkthrough gap #3 (group re-key cost) and the group-membership
model behind crew mail. Gate: captain's side window.
**Author:** CC (CLOUD seat) · **Date:** 06/10/2026 ACST
**Reads with:** `identity-mailbox-walkthrough.md` (Act 5, 8), `identity-capability-word-spec.md`,
`identity-key-lifecycle.md`.

> ELI10 frame: a group is just an account that several people are allowed to speak for, with a
> shared "group lock." When someone leaves, you **change the lock** so they can't open future
> letters — that's "re-keying." The only hard part is changing the lock *cheaply* when the group
> is big.

---

## 1. What a group needs (the five properties)

1. **Membership** — a clear, signed list of who's in, and who may add/remove.
2. **Confidentiality** — only current members can read.
3. **Forward secrecy** — a removed member cannot read **future** messages (re-key on leave).
4. **Post-compromise security (PCS)** — if a member's key leaks, the group *heals* after the
   next key update, instead of staying exposed forever.
5. **Scales** — changing the lock must not get painful as the group grows.

Properties 3–4 are why "just share one group password" is not enough: a password never changes,
so one leak is forever and one departure can't be undone.

## 2. The model — a group is an account

A **group** = its own account record (key-lifecycle §6) holding:
- the **member list** (each member's account address),
- the **admins** (who holds the *add-member* / *remove-member* capability),
- a pointer to the current **group key epoch** (which lock is live now).

Governance is just capability words: to add/remove a member you must hold the group-admin
capability (attenuable, revocable, possibly multi-admin or M-of-N). Membership changes are
signed updates to the group record on the substrate. **Who may change the group = authority,
not identity** (invariant I1), same as everything else.

## 3. Re-keying — pick the engine by group size (tiered)

Don't invent group crypto. Use the right known engine for the size:

| Tier | Size | Engine | Cost per message | Cost per membership change |
|---|---|---|---|---|
| **Crew** | ≤ ~50 | **Pairwise fan-out** or **Sender Keys** | 1 (sender-keys) to O(n) (pairwise) | re-distribute keys to remaining members |
| **Community** | 100s–1000s+ | **MLS / TreeKEM (RFC 9420)** | 1 | **O(log n)** add/remove/update |

- **Pairwise fan-out** (walkthrough Act 5): encrypt a copy to each member. Dead simple, no new
  machinery — **ship this first for the crew**. Re-key on leave = re-encrypt future messages to
  the remaining set. Fine at crew scale; O(n) is cheap when n is small.
- **Sender Keys** (Signal's group method): each member shares one symmetric *sender key* with the
  group over pairwise channels, then encrypts each message once. Cheaper per message; removal
  means every member rotates their sender key. Good middle tier.
- **MLS (RFC 9420) / TreeKEM**: the IETF standard for large groups. Members sit in a key tree;
  **add / remove / update are O(log n)** and give forward secrecy **and** post-compromise
  security by design. This is the answer to "group chat for the many" — adopt it, don't rebuild
  it.

**Recommendation:** crew mail ships on **pairwise/sender-keys** (zero new dependencies, proves
the product); **MLS is the planned upgrade** the first time a group outgrows the simple path.
The membership/governance layer (§2) is identical either way — only the key engine swaps, which
keeps the protocol engine-agnostic (same spirit as the substrate adapter).

## 4. The lifecycle events (what happens, and the cost)

- **Create group** — admin mints the group account, adds founding members, establishes epoch 0.
- **Add member** — admin signs a record update + the engine adds them (pairwise: share current
  key; MLS: tree add, O(log n)). New member reads from the current epoch forward (not the past).
- **Remove member / member leaves** — admin signs removal + **re-key to a new epoch**. Removed
  member is cut from future epochs → forward secrecy. (MLS: O(log n); crew: re-share.)
- **Routine update** — periodic epoch advance so a silent key leak self-heals (PCS). Automatic,
  invisible (like the per-message ratchet, but at group level).
- **Delivery** — a group message fans into each member's mailbox (walkthrough Act 5), or to a
  shared group channel on the substrate that members subscribe to; either way it's ciphertext to
  the Pi/substrate (blind-custody holds).

## 5. Honest boundaries

- **Past stays past.** Re-keying protects *future* messages. Anything a departed member already
  received and decrypted is theirs — no system un-sends it (threat-model non-goals).
- **Membership metadata leaks.** The fact that accounts X, Y, Z are in a group is visible to the
  substrate/host unless separately hidden. Content is protected; the social graph is a *separate*
  axis (SimpleX's concern; metadata non-goal). Flag for anyone who needs membership privacy.
- **Admin is power — attenuate it.** The add/remove capability is the group's chokepoint; keep it
  least-authority (scoped, revocable, ideally M-of-N for important groups) so no single
  compromised admin can hijack the group. A group with one all-powerful admin is a mini-monopoly
  — the thing we're building *against*.
- **MLS is real complexity.** It's worth it at scale but it's not free; that's exactly why crew
  mail ships on the simple engine and MLS arrives only when a group needs it.

## 6. Open questions for the round

1. **Crew-tier default** — pairwise fan-out vs. sender-keys for the first ship (trade simplicity
   vs. per-message cost).
2. **Admin model** — single admin, multi-admin, or M-of-N threshold per group; and whether
   membership can be member-proposed + admin-approved.
3. **MLS adoption boundary** — the member count / feature that triggers moving a group from the
   simple engine to MLS, and whether migration is in-place or a new group.
4. **Group recovery** — if all admins lose their keys, how is a group's admin set recovered
   (guardian-style for groups?) without a central reset.
5. **Membership privacy** — is hiding the member list ever in scope, or always accepted as leaked
   metadata?

---

## Sources

- [RFC 9420 — The Messaging Layer Security (MLS) Protocol](https://www.rfc-editor.org/rfc/rfc9420.html)
- [Signal — private group messaging / sender keys](https://signal.org/blog/private-groups/)
- Forward secrecy / post-compromise security — Double Ratchet background; see
  `identity-research-zooko-brief.md`.

---
*Lifts into the separate ID/Auth repo as `/spec/groups-and-rekey.md`. §1 and §4 double as
user-facing help text.*
