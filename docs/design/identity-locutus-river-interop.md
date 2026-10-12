# TernID ↔ Locutus (Freenet) & River — Interop Design Memo

**Status:** design round · **Date:** 2026-10-07 · **Author:** CCC (cloud seat)
**Question (Stevo):** cross **contract** compatibility with Locutus/Freenet, and cross
**account/room** compatibility with River — is it possible, and how?

**Headline:** Yes to both, at different depths.
Freenet is a near-1:1 fit for TernID's substrate — our architecture is almost purpose-built for
it. River bridges cleanly at the **account** layer because it uses the *same* signature scheme we
do (Ed25519 / `ed25519-dalek`); room interop is a schema-adoption job, not a rebuild. The one real
tension is philosophical, not technical: River chose **per-room, unlinkable** identity; TernID
chose **one global AID** (with petnames for privacy). That shapes *which direction* the bridge
flows, not whether it can exist.

---

## 1 · Locutus / Freenet — the substrate fit (near 1:1)

Freenet (the new core, formerly Locutus) is a global key-value store where **keys are WASM
*contracts***. A contract's code defines what state is valid, how it may change, and how peers
sync it. Crucially:

- **State must merge as a join-semilattice** (associative, commutative, idempotent — CRDT-style).
- **Sync is delta-based:** `summarize_state` → `get_state_delta` → `update_state`. The delta format
  is the contract's own, and **the contract validates each delta — "perhaps by verifying it is
  signed by someone authorized to modify the state."** That sentence is, verbatim, the TernID
  capability model.
- **Delegates** are local WASM actors on the user's device that hold **private keys** and sign on
  request; the core attaches a *verified sender identity* to every message. Freenet's own **Ghost
  Key vault** is exactly this: a "key-manager delegate" that signs with your Ed25519 key and never
  exposes it. That is TernID's "keys never leave the device," already a first-class Freenet concept.

### The mapping is almost mechanical

| TernID (today) | Freenet primitive |
|---|---|
| Mailbox (append-only sealed envelopes) | A **contract** whose state is the envelope set. Merge = set-union (a clean semilattice ✓). Delta = new envelopes; **validity rule = accompanied by a valid TernID append capability.** |
| KEL account record ("the KEL *is* the account") | A **contract** whose state is the event log. Validity = `verify_and_project` succeeds; merge = the pre-rotation-consistent extension (monotone append). |
| Device signing key + X25519 enc key | A **key-manager delegate** (the Ghost-Key-vault pattern): signs capabilities / opens mail on request, key stays inside. |
| `ternid-node` (blind relay: verify + store) | What a **contract + core** do, but decentralized. Our node is a centralized stand-in for the contract's `update_state` validation. |
| `ternid-web` (WASM: keys, signing, sealing) | A **delegate + browser UI** talking to the local core over WebSocket. |
| `Substrate` trait (put/get/publish/resolve) | The Freenet contract/state API. Our `clients/substrate` was *designed* to accept this as a backend. |

**Cross-contract** reach: any Freenet app can *read* a TernID contract's state (it's a public KV
store). *Writing* requires satisfying our contract's validity rule — i.e. **presenting a valid
TernID capability.** That is not a limitation to work around; it is the capability model doing its
job. "Interop" with another app = that app carries a TernID grant.

**Verdict:** the blind-custody relay we just built is the *contract we'll write for Freenet*,
expressed centrally first. Porting = reimplement the node's verify-and-store as a contract's
`validate_state`/`update_state`, and the browser's key handling as a delegate. Low friction. This
is **Phase 4** and it is clearly correct.

---

## 2 · River — account & room interop

River is group chat with no backend; **each room is a Freenet contract.** Confirmed facts:

- **Same crypto as us:** River's code uses `ed25519_dalek::SigningKey` with
  `river_core::room_state::member::{Member, MemberId, AuthorizedMember}`. Ed25519, 32-byte keys,
  64-byte sigs — identical to TernID. *This is the fact that makes the bridge cheap.*
- **Membership is an invitation tree:** `AuthorizedMember { member, invited_by: <pubkey>, signature }`.
  Each member records who invited them and a signature; invitations are single-use and carry a
  per-invitee keypair; the member record is signed with the room key + the inviter's key.
- **Per-room identity, by design:** each member is identified by a **per-room key, not a global
  identity** — the keys deliberately don't link a member across rooms (privacy). Inactive members
  are pruned (membership rides along with recent messages).

### Where TernID and River agree, and where they differ

**Agree (so the bridge is real):**
- Ed25519 signatures end to end.
- **Delegation chains rooted in an authority.** River's `invited_by` chain *is* a capability
  delegation chain: the room owner delegates "may post / may invite," attenuating down the tree.
  TernID already has this as first-class capability delegation (`deleg_depth`, attenuable rights).
  An `AuthorizedMember` is a TernID membership grant wearing River's struct.

**Differ (the one real tension):**
- **Global vs per-room identity.** TernID AID = one verifiable global identity (+ petnames for
  privacy). River member key = unlinkable per-room. Opposite corners of Zooko's triangle on the
  global↔local axis.

### How the bridge flows

- **TernID → River (join existing rooms): clean.** A TernID user derives a **per-room key** from
  their account — `HKDF(account_secret, room_id)` → an Ed25519 keypair — and presents *that* as
  their River member key. River sees only an unlinkable per-room key (its model satisfied); the
  user privately keeps the AID→room-key map. A TernID capability to join maps onto River's
  `AuthorizedMember` record. **A TernID identity can join real River rooms today, in principle.**
- **River → TernID: partial.** A River per-room key is *not* a global identity, so it can't *be* an
  AID. But a River member can be **introduced into** a TernID context via a petname bound to their
  per-room pubkey (a verifiable edge, not a global name). Good enough for "message this River
  person"; it cannot retroactively make them a global TernID account.
- **Rooms both ways:** for a room joinable by *both* River and TernID users, build TernID rooms
  **as River-compatible room contracts** — adopt River's room/membership/message schema, and layer
  TernID's richer *authority* semantics (explicit **revocation**, rights **attenuation**) on top.
  River today leans on invite-tree + activity pruning; TernID adds revocation and least-authority.
  Where it fits, contribute that upstream rather than fork.

---

## 3 · The fork, and the recommendation

The fork named earlier was **bridge-to-River-schemas** vs **own-design-on-Freenet-storage**.
Recommendation — a two-layer answer, because the two layers want different things:

1. **Substrate / mailbox / account: go *native* Freenet (own contracts, standard storage).**
   Our model maps almost 1:1; this gives decentralized, zero-infrastructure deployment and keeps
   TernID's capability semantics intact. Write the mailbox + KEL-account contracts and a
   key-manager delegate. (Phase 4.)
2. **Chat rooms specifically: *adopt River's schema*, don't reinvent it.** Make TernID rooms
   River-compatible contracts so identities cross both ways (per-room keys derived from the AID),
   and add our revocation/attenuation as an overlay. We get interop *and* our differentiator, for
   far less work than a parallel room design — and River gets features it lacks.

In one line: **own the identity + capability + mailbox layer on Freenet storage; bridge the room
layer to River's schema.** Not either/or — both, at the layer each belongs to.

---

## 4 · Open questions (confirm in source before building)

- **River `MemberId` derivation** — raw pubkey, or a hash of it? (decides the exact join-record
  mapping). Check `river-core` `room_state/member.rs`.
- **River's room-key signing scheme** — exact bytes signed for `AuthorizedMember` (so our overlay
  produces byte-identical records).
- **Freenet stdlib version / ABI** — `validate_state`/`update_state` signatures are version-pinned
  (`freenet-stdlib` ~0.8.x today). Pin before writing the contract.
- **KEL-as-contract merge** — confirm our KEL extension is a clean join-semilattice under
  concurrent rotation (it should be: pre-rotation makes valid extensions a chain), or define the
  merge explicitly.
- **Revocation on a decentralized substrate** — our C4 "fail-closed freshness" needs a revocation
  signal that works without the central node; likely a revocation-list contract or a KEL event.

## 5 · Decision requested

Endorse the two-layer recommendation (native Freenet substrate + River-schema room bridge), or
steer. Nothing here changes what we've built — the node/web slice *is* the centralized rehearsal of
the Freenet contract. This memo only sets the direction for Phase 4 and the River bridge.

*Loosely coupled as ever: none of this touches the TernOO C runtime; Freenet is a storage/transport
choice, not a dependency on it.*
