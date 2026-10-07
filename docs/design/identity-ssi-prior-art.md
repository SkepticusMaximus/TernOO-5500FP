# Self-Sovereign Identity (SSI) — Prior Art & Adopt-vs-Build (DRAFT)

**Status:** DRAFT research brief. The captain's instruction: don't reinvent the wheel —
incorporate and cooperate with well-licensed prior art where a solid codebase exists.
This maps the SSI field onto our design, names what to adopt, what is genuinely ours, and
flags the repo-name collision. Gate: captain's side window.
**Author:** CC (CLOUD seat) · **Date:** 07/10/2026 ACDT
**Reads with:** `identity-design-round-primer.md`, `identity-capability-word-spec.md`,
`identity-key-lifecycle.md`, `identity-build-roadmap.md`.

---

## 1. The skinny on SSI

**Self-Sovereign Identity** = individuals hold and control their own identity data, and
present cryptographically verifiable claims to whoever needs them, with no central
account authority. It is exactly our thesis, and it is now a mature, standardised field —
not experimental.

- **Standards are stable.** W3C **DID Core v1.0** became a Recommendation in July 2022;
  **Verifiable Credentials (VC) v2.0** reached Recommendation in May 2025. These are
  finished specs with multiple interoperable implementations.
- **It is mainstreaming via regulation.** The EU's **eIDAS 2.0 / EUDI Wallet** mandate
  requires every member state to offer a certified digital-identity wallet by end 2026;
  the decentralized-identity sector is valued around $5–7B in 2026. So the wallet UX and
  the DID/VC plumbing are being battle-tested at national scale right now.
- **Two primitives do the work:**
  - **DID (Decentralized Identifier)** — a self-certifying identifier bound to a key,
    resolvable without a central registry. *This is our "account" / self-certifying key.*
  - **VC (Verifiable Credential)** — an issuer-signed, tamper-evident claim a holder can
    present and a verifier can check offline. The issuer→holder→verifier "trust triangle."

The field splits identity (DIDs), claims (VCs), and — separately — authorization
(capabilities / UCAN, which we already use). Our design touches all three.

## 2. Well-licensed codebases worth incorporating

The good news: the serious open-source SSI stacks are **Apache-2.0** — permissive,
commercial-friendly, and compatible with whatever we license our own work.

| Project | Lang | License | What we'd use it for |
|---|---|---|---|
| **Spruce `ssi` crate + DIDKit** | **Rust** (bindings: C/Java/Android/Python/JS) | Apache-2.0 | **Our best fit** — DID + VC operations, signing, resolution, in our chosen core language. Build on it rather than hand-rolling DID/VC crypto. |
| **Veramo** | TypeScript | Apache-2.0 | DID/VC in JS — the web/desktop client side. |
| **KERI** (keripy, keriox-Rust) | Python / **Rust** | Apache-2.0 | **The rotation answer** — see §3. |
| Hyperledger Aries / Indy / AnonCreds | Rust/Go/others | Apache-2.0 | Big ecosystem, but Indy is **ledger-based** — against our no-global-namespace / substrate-agnostic ethos. Borrow ideas (AnonCreds), not the ledger. |

Recommendation: **core on Spruce's Rust `ssi`/DIDKit** (matches the roadmap's Rust stack,
Apache-2, cross-platform bindings for free), **Veramo** for JS clients, and **KERI** for
key rotation. Avoid ledger-anchored stacks (Indy/Sovrin, ION-on-Bitcoin) as *dependencies*
— they reintroduce the global anchor we are designing away from.

## 3. KERI — the gem that answers our hardest open problem

Our crux (primer §6, key-lifecycle): **rotate and recover keys with no central fallback.**
KERI (Key Event Receipt Infrastructure) is a **ledger-less** decentralized identity system
that already solves this, and its ethos matches ours exactly:

- **Self-certifying identifiers** bound to a key-pair at issuance — no registrar.
- **Key Event Logs (KEL)** — a hash-chained, append-only log of signed key events
  (rotation, delegation). Anyone can verify any log **anywhere, anytime, with no special
  infrastructure** ("ambient verifiability") — which is precisely Zooko's "verifiable" edge.
- **Pre-rotation** — you commit *now* to the hash of your *next* key. If your current key
  leaks, the attacker still cannot rotate, because the next key was pre-committed and is held
  separately. This is the proven answer to the rotation/recovery crux we flagged as unsolved.
  We adopt it rather than invent our own. **Correction (F4):** pre-rotation is *not*
  "post-quantum-secure" wholesale — it protects the **rotation commitment** (the next key hides
  behind a hash); the Ed25519 **signatures** themselves are **not** post-quantum.
- **Witnesses** (indirect mode) ≈ our guardians / availability helpers.

> **D-KEY-1 (captain's call, 07-10): the KEL *is* the account record** — not a bespoke record
> alongside KERI. We adopt KERI's KEL as the one account mechanism (F4). `key-lifecycle.md` §6
> is written around it.

KERI being *ledger-less* is the key alignment: it gives self-sovereign rotation **without**
a global anchor, which is the whole point of our no-global-namespace design. It slots under
`core/keys/` in the roadmap as the rotation engine.

## 4. Adopt vs. build — the honest split

**Adopt / cooperate (don't reinvent):**
- **W3C DIDs** — our account identifier *is* a DID (e.g. `did:key`, or a custom method we
  bridge to our word grammar). Use the standard so we interoperate with wallets.
- **W3C VCs 2.0** — any claim ("this key is crew," an attestation) is a VC, not a bespoke format.
- **Spruce `ssi`/DIDKit** — the DID/VC crypto and resolution core.
- **KERI pre-rotation + KELs** — the key rotation/recovery engine (§3).
- **UCAN** — the capability/authorization layer (already in our design).
- **MLS (RFC 9420)**, **Signal protocol** — groups and message crypto (already chosen).

**Genuinely ours (not in the SSI stacks — this is the contribution):**
1. **"A capability IS a word"** — capabilities encoded in the TernOO ternary word grammar,
   native and self-describing. SSI has UCAN/VCs but nothing ternary-native.
2. **Zero-custody E2EE mailbox + the messenger showcase** — SSI is about credentials and
   login; it does **not** ship a full blind-custody mail/messaging system. Our integration
   of identity + mail + messaging is novel.
3. **Blind-custody deployment + the self-hosted SD-card node.**
4. **Freenet-contract substrate** (ledger-less, adapter-swappable) as the record store.
5. **The TernOO-native path** — words running on the 5500FP; on-machine verification.
6. **The petname / introduction UX layer** — SSI underinvests here; this is a real differentiator.

**The reframing for the roadmap:** Phase 1 is no longer "invent identity+crypto from
scratch." It is **"wrap Spruce `ssi`/DIDKit + KERI pre-rotation, express our capability as a
word over them, and build the mailbox + substrate + petname layers on top."** That is a
large de-risking and a smaller core than the roadmap first implied. License posture is clean:
everything we'd adopt is Apache-2.0, so we can license our own work how we like and still
incorporate it.

## 5. The name — "Sovereign ID" has a collision problem

The captain approved "Sovereign ID"; here is the honest finding before we commit it:

- **Sovrin** is a major, established SSI network and foundation (since 2016), and its name is
  explicitly derived from *sovereign*. "Sovereign ID" reads as a near-homophone of Sovrin
  and will be confused with it.
- **"Self-sovereign identity" / "sovereign identity"** is the *generic field term*. A name
  that is the category label is hard to own, hard to search (the captain already noticed it
  doesn't surface cleanly), and easy to mistake for any other SSI project.

**Recommendation:** pick a **distinctive codename** instead — the ship already names things
well (Bonsai, GHOST, GristMill, P2PCP, CGP). A distinct name is searchable, ownable, and
won't be read as "another Sovrin." The *tagline* can still say "self-sovereign identity,
done ship-true." If the captain prefers descriptive over codename, `ternoo-id-auth` is
clearer and collision-free. "sovereign-id" remains usable if the captain wants it with eyes
open about the Sovrin overlap — it is a preference call, not a blocker.

## 6. Decisions this raises for the round

1. **Adopt Spruce `ssi`/DIDKit as the core dependency?** (Rust, Apache-2 — strong yes unless
   an evaluation finds a gap.)
2. **Adopt KERI pre-rotation for the rotation crux?** (Strong yes — it is the proven answer.)
3. **Which DID method** — reuse `did:key` / a KERI method, or define a TernOO DID method that
   bridges to our word grammar? (Interop vs. ship-true; same loose-coupling fork as before.)
4. **Repo name** — distinctive codename vs. `ternoo-id-auth` vs. `sovereign-id`-with-eyes-open.
5. Where VCs fit our model — do crew membership / attestations become VCs, and who issues them?

---

## Sources

- [W3C — DID Core v1.0 (Rec. 2022)](https://www.w3.org/TR/did-core/) · [Verifiable Credentials 2.0 (Rec. 2025)](https://www.w3.org/TR/vc-data-model-2.0/)
- [A Survey of the Self-Sovereign Identity Ecosystem (arXiv:2111.02003)](https://arxiv.org/pdf/2111.02003)
- [SpruceID — DIDKit](https://github.com/spruceid/didkit) · [`ssi` Rust crate](https://github.com/spruceid/ssi)
- [Veramo — verifiable data framework](https://veramo.io/)
- [KERI whitepaper (arXiv:1907.02143)](https://arxiv.org/pdf/1907.02143) · [KERI at the Decentralized Identity Foundation](https://identity.foundation/keri/)
- [Hyperledger Aries](https://www.hyperledger.org/projects/aries) · [best-of-digital-identity (ranked OSS list)](https://github.com/jruizaranguren/best-of-digital-identity)
- [Sovrin Network](https://sovrin.org/) (the naming collision)
- [UCAN](https://github.com/ucan-wg) · [RFC 9420 — MLS](https://www.rfc-editor.org/rfc/rfc9420.html)

---
*Lifts into the separate repo as `/spec/ssi-prior-art.md`. It argues for a small core that
wraps well-licensed prior art, not a from-scratch identity stack.*
