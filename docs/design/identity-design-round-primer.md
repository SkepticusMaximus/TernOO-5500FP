# Monopoly-Proof Identity — Design-Round Primer

**Status:** Primer for the identity/authorisation design round. This is the clean,
self-contained document to read *before* the round; it states the frame, the
architecture we're converging on, the decisions already on the record, and the
questions the round must resolve. It is not itself a ruling.
**Author:** CC (CLOUD seat — design/docs lane)
**Date:** 05/10/2026 ACST
**Audience:** crew (Stevo, CF5, CAI)
**Background (deeper prior art, cited):** `docs/design/identity-research-zooko-brief.md`
**Source mail:** `private/POBOX/2026-10-02-2320-Stevo-to-crew-zooko-talk-with-the-graphic.md`
(Zooko's 2026 talk) · `private/POBOX/2026-09-27-2105-CF5-to-crew-identity-and-authorisation-oversight-read.md`
(CF5's oversight read)

---

## 1. The frame (Zooko's 2026 vocabulary — adopt it)

A *name* / identifier can have at most two of three properties. Zooko's 2001 words were
fuzzy; his 2026 relabelling is sharper and we should use it:

| 2001 | 2026 | Means |
|---|---|---|
| secure | **verifiable** | your *local* client can check it itself, no trusted third party |
| decentralised | **global** | *context-free* — hand it over, nobody asks "on which service?" |
| human-meaningful | **human-chosen** | a person picked it (vs. the computer assigned it) |

The move that matters: **look at the edges, not the corners.** The two *good* edges have
working examples; the third is the one to try living without.

- **verifiable + global** (not human-chosen) = secure-hash / public-key identifiers:
  git, Docker, Bitcoin, Tor `.onion`, Iroh dial-by-pubkey. → our **key layer**.
- **verifiable + human-chosen** (not global) = **local namespaces**: phone address book,
  SSH `known_hosts`, `build.zig.zon`. → our **petname layer**.
- **global + human-chosen** (not verifiable) = DNS/TLS/PKI. → the edge to **omit**.

The client **pivots around the verifiable edge** (Signal does this): inbound, your
*petname* shows for a verified key ("wifey's calling"); outbound, you pick a *local
name* and it resolves to the global key. Local human name ⇄ global verifiable key is the
whole UX, and it is monopoly-proof because there is no global human namespace to capture.

## 2. The architecture — a three-layer hub

Identity is an **asymmetric hub**: the key is the one true centre; everything hangs off
it. (Why asymmetric and not "triangulated derivation": hashes are one-way, and
pubkey+name are *public*, so anything derivable from them is public — a leak. Derivation
must flow *outward from a secret*, never inward from public data.)

1. **Global layer — the self-certifying public key.** Address/dial/designate by key.
   Verifiable + global; no registrar, nobody can rent or revoke it.
2. **Cryptographic layer over the global layer:**
   - **Outward derivation from a secret seed** (HKDF / BIP-32): one seed expands into
     unlimited labelled sub-keys and **capability words** (per-mailbox, per-contact),
     deterministically, with no database. One-wayness is the feature.
   - **A Merkle record signed by the key**, binding the user's fields, with **selective
     disclosure** (reveal one leaf + path; verify against the signed root).
   - **Immutable → mutable** (Zooko's Tahoe/Zig point): an identifier that means "any
     version signed by this key" makes the record *mutable but still self-certifying* —
     it evolves, but only the key-holder publishes a new version.
3. **Local layer — petnames + edge names** (linked local namespaces) for human-facing
   names and for **introductions**.

Two load-bearing slogans, both on the record:

- **"A capability IS a word."** The grant — which mailbox/cabin, which rights, which
  attenuations — is a self-describing word. Its *authentication* is a standard signature
  or HMAC over the word's canonical bytes, carried alongside (see §4).
- **"Authority ≠ identity."** *Who* you are (key) is separate from *what* you may do
  (capability). Authority flows by delegating words, never by consulting an identity
  registry. This is the ship's intrinsic-vs-relational law at the security layer.

## 3. Zero-custody — the provider relationship, made monopoly-proof

The captain's keystone requirement: anyone may adopt the ID system **as a protocol**,
but the host **identifies without holding**.

1. **The host identifies, it does not hold.** It authenticates an anonymous key and
   serves it, but holds at most opaque ciphertext and/or a reference (a capability word /
   a Freenet contract key). Readable data lives in the user's store or on the substrate.
2. **Revocation is cryptographic.** Leaving is not "please delete me" (unenforceable).
   It is the user **rotating the key / withdrawing the capability**, after which the
   host's remaining copy is undecryptable noise. Trust is removed from the delete step.
3. **Portability is intrinsic.** The data was never in the host's custody, so switching
   provider is re-pointing a new host at the same user-owned record. No export ritual, no
   hostage data.
4. **No provider owns its users.** Identity is a *spec*, not a *service* — no central
   server, no chokepoint. Switching cost → ~0, which restores competitive pressure.
   *This is the monopoly-proof thesis applied to commerce, not just to names.*

**On Freenet/River:** the encrypted profile is naturally a **Freenet contract** (mutable
state, addressed by the user's key, rule-validated) that the host merely *subscribes*
to. Cleanest substrate for zero-custody.

**State the promise exactly** (over-claiming is how trust gets betrayed): the host never
holds data it can read without a *live* grant, and revocation renders its stored copy
useless. It does **not** mean the host never *saw* anything — cleartext it already
decrypted under a valid grant cannot be un-seen. And **content** zero-custody ≠
**metadata** zero-knowledge (a host can still learn when/with-whom/how-much).

## 4. Decisions already on the record (don't re-litigate)

From CF5's 27-Sep oversight read and prior rulings:

- **Separate by PROCESS, not login.** Crew engine stays loopback (POBOX/docs). A
  separate **passenger** process with an allow-list (default-deny), its own storage root,
  and *no filesystem path to `private/`*. The public tunnel points only at the passenger
  process. Isolate the Pi from the LAN.
- **Passenger ≠ peer, by construction.** Passengers: cheap/anonymous identity is fine (no
  Sybil threat). Peers (mint/vote/earn): identity must be **costly to mint** (S5, behind
  R2). A passenger capability never confers mesh standing.
- **Designate in ternary; authenticate with vetted crypto.** Ed25519 (512 bits) does not
  fit in 24 trits and must never be the `ternary_sponge` (proven GF(3)-affine collidable;
  SHA3-not-sponge already ratified for DICK). MMID may *label*; it may never
  *authenticate*.
- **No public MTA.** Mail-in-the-mesh is the ship-true road.
- **Toolkit triage:** ON the open-day path — macaroon-style attenuable HMAC tokens,
  least-authority default, petnames. NEXT (not open-day) — DIDs / verifiable credentials.
  RESEARCH only (off critical path) — zero-knowledge. NEVER — home-rolled crypto.

## 5. Prior art at a glance — adopt / avoid

| System | Take | Why |
|---|---|---|
| **Signal protocol** (X3DH/Double Ratchet/PQXDH, libsignal) | **Adopt the crypto** | Best-in-class E2EE; safety-number verification UX |
| **Signal network/app** | **Avoid** | No federation, phone-bound, hostile to 3rd-party clients; drags in the global+human-chosen edge |
| **Freenet (new/Ian Clarke) + River** | **Target substrate** | Contracts = mutable, key-addressed, rule-validated, no global names — our signed-record model, live |
| **UCAN** (Fission) | **Adopt or mirror** | Capability tokens, DIDs, delegation/attenuation/revocation, *no auth server of any kind* — literally "adopt as a protocol, host holds nothing" |
| **Solid pods** (Berners-Lee) | **Learn from** | User-owned storage, revoke anytime, identity-linked (not location-linked) portability |
| **Petnames / SDSI-SPKI** | **Foundation** | Linked local namespaces; "Alice's Bob"; the naming layer |
| **Nostr** | **Lesson** | Key is primary, human name (NIP-05) is a detachable overlay — the right shape |
| **SimpleX** | **Lesson** | Pairwise/per-queue identifiers, no global ID — the metadata-minimisation ceiling |

## 6. The crux: rotation = recovery = revocation (one problem)

The APK cautionary tale: public-key-as-identifier + trust-on-first-use collapsed at
scale because **lost keys** forced a global fallback, which ended with Google holding
everyone's keys. **Key loss / rotation / recovery is where every monopoly-proof identity
system gets re-centralised** — the recovery path is the capture surface.

And zero-custody **revocation = key rotation**. So revocation and rotation are the *same*
problem wearing two hats. Solving it once pays twice. This should be the **round's centre
of gravity**: *how does a petname follow a person across a new key, and how is a lost key
recovered, with no central fallback?*

## 7. Open questions for the round

**Naming & introductions**
1. Bootstrap: how does a node first learn a peer's key (QR, nickname hint, edge-name
   introduction through a known principal)?
2. Nickname-spoof UI rule: how to distinguish a petnamed contact from a stranger
   claiming the same nickname (the anti-phishing surface)?
3. Edge-name resolution: how far to chase "CF5's Professor's mailbox," caching, and what
   shows when an intermediate principal is unreachable?
4. Introductions: build Zooko's "accept-introduction" (SDSI edge names) — Signal's
   missing feature, native to our model. In scope for v1?

**Keys & records (the crux)**
5. Rotation/recovery with no central fallback (§6) — the headline.
6. Capability↔identity binding: does a word name a *key* or a *mailbox*, and may a
   mailbox outlive/rebind its controlling key?
7. Attenuation & revocation semantics: what dimensions attenuate (scope/time/rights/
   re-delegation depth); revocation by expiry, rotation, or published revocation word;
   who may revoke a delegated word?
8. Mutable-record publication: where is the signed record published/gossiped, and how
   does a reader learn the latest version without a central index?

**Zero-custody & providers**
9. Availability model: zero-custody (substrate-dependent) vs blind-custody (host caches
   ciphertext it can't read)? Per data class?
10. Revocation granularity/latency: revoke one provider without disrupting others; what a
    peer sees mid-rotation.
11. Adopt UCAN directly (interop) vs. define a TernOO capability-word that maps to it
    (ship-true, another spec to carry)?
12. Portable encrypted-profile schema + versioning (ties to §2's mutable signed record).

**Scope & privacy**
13. Metadata minimisation: how much must a host learn to route/serve; can pairwise IDs
    (SimpleX) cut it further?
14. "Global" per class: passengers maybe no global id at all; peers need a costly-to-mint
    global key. Where exactly does the line sit?

## 8. Proposed order of work (CF5's, endorsed)

1. **Threat model** (one page) — CF5 + CAI. *Before any design.*
2. **Process split + Pi isolation** — CC (HP). Can start now; no design needed.
3. **Capability word + macaroon-style grant** — design, CF5 + CAI.
4. **Tunnel / TLS + allow-list audit** — CC (HP), ~a day, after 2 and 3.

Only then open-day.

---

## Sources

- [Zooko — "updating the triangle" talk (02-Oct-2026)](../../private/POBOX/2026-10-02-2320-Stevo-to-crew-zooko-talk-with-the-graphic.md) (crew transcript)
- [CF5 — Identity & Authorisation oversight read (27-Sep-2026)](../../private/POBOX/2026-09-27-2105-CF5-to-crew-identity-and-authorisation-oversight-read.md)
- [Wikipedia — Zooko's triangle](https://en.wikipedia.org/wiki/Zooko%27s_triangle)
- [Rivest & Lampson — SDSI (linked local namespaces)](https://people.csail.mit.edu/rivest/pubs/RL96.ver-1.1.html)
- [Spritely — Petnames: a humane approach to secure, decentralized naming](https://files.spritely.institute/papers/petnames.html)
- [Wikipedia — Object-capability model](https://en.wikipedia.org/wiki/Object-capability_model)
- [Signal — safety number updates](https://signal.org/blog/safety-number-updates/) · [phone-number privacy & usernames](https://signal.org/blog/phone-number-privacy-usernames/)
- [Freenet (Ian Clarke's current project)](https://freenet.org/)
- [Tahoe-LAFS](https://tahoe-lafs.org/) · [Iroh (dial-by-public-key)](https://www.iroh.computer/)
- [UCAN — User-Controlled Authorization Networks](https://github.com/ucan-wg)
- [Solid — about (data pods; revoke; portability)](https://solidproject.org/about)
- [W3C — Decentralized Identifiers (DIDs) v1.0](https://www.w3.org/TR/did-core/)
- [Macaroons (Birgisson et al., NDSS 2014)](https://research.google/pubs/pub41892/) · [RFC 5869 — HKDF](https://www.rfc-editor.org/rfc/rfc5869) · [BIP-32](https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki)

*Full prior-art discussion and the monopoly-proof criteria are in the research brief:
`docs/design/identity-research-zooko-brief.md`.*
