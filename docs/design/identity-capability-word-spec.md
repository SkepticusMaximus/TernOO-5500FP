# The Capability Word — Spec (DRAFT)

**Status:** DRAFT, design-round deliverable (CF5 order of work, step 3). Gate: captain's
side window. Trit-level assignments below are **proposals pending reconciliation with the
authoritative Language Audit** (local-only; CC-HP / CF5 hold it — this seat does not).
**Author:** CC (CLOUD seat) · **Date:** 06/10/2026 ACST
**Reads with:** `identity-design-round-primer.md`, `identity-threat-model.md`,
`identity-deployment-topology.md`.
**Grounding:** TernOO word frame 2+4+18 — PRIMARY T23-T22 (9 types), QUALIFIER T21-T18
(81), PAYLOAD T17-T0 (18 trits); primary table per whitepaper §(9 primaries).

---

## 0. The one structural truth to state first

**A capability is NOT a single 24-trit bearer token.** A real signature (Ed25519 ≈ 512
bits) and a real content-address/public key (≈ 256 bits ≈ 162 trits) do not fit in 18
trits of payload, and CF5 has ruled the ternary sponge must never be the authenticator
(GF(3)-affine collidable). Therefore:

> **A capability = a CRYPTO-primary word *sentence* (the self-describing grant) + a
> detached standard authenticator (signature or HMAC) over that sentence's canonical
> bytes.** The word sentence *designates and describes*; the authenticator *proves*.
> "MMID may label; it may never authenticate." (CF5, 27-09.)

This is a **macaroon in ternary** (and maps 1:1 to a UCAN — §6).

## 1. The grant sentence (a sequence of CRYPTO words)

A capability is an ordered sentence of words under the **CRYPTO primary (T23,T22 = 0,+1;
reserved — this spec is the proposed first use; un-reserving is a captain/CF5 call)**. Each
word's 4-trit QUALIFIER (81 values) names its role; the 18-trit payload carries the field.

| # | Role (CRYPTO qualifier) | Payload (T17-T0, 18 trits) | Notes |
|---|---|---|---|
| 1 | `GRANT_HEAD` | version · grant-type · flags | opens every capability; grant-type ∈ {cabin, mailbox, record, delegation} |
| 2 | `ISSUER_REF` | MAP content-address of the issuer's identity record | multi-word (a key is ~9 words); self-certifying |
| 3 | `OBJECT_REF` | MAP content-address of the target (mailbox/cabin/record) | the thing being granted — "a word designating a mailbox" |
| 4 | `RIGHTS` | permission trits (read/append/write/list/delegate/admin, each −1/0/+1) | 18 trits ≫ enough for a rich rights lattice |
| 5..n | `CAVEAT` (0+) | one attenuation each: `EXPIRY` · `SCOPE` (prefix under object) · `QUOTA` · `AUDIENCE` | macaroon caveats; **narrow only** |
| last-1 | `DELEG_DEPTH` | remaining re-delegation hops (0 = terminal) | attenuation of re-sharing |
| — | *(authenticator)* | **not a word** — Ed25519 sig / HMAC over canonical bytes | carried alongside (the dual-digest pattern) |

**Designation uses MAP, not a new type.** Because MAP words are already TernOO's
content-addressable addresses ("data located by hashing it to MAP word addresses"),
`ISSUER_REF`/`OBJECT_REF` are MAP word-sequences. The capability layer adds no new
addressing scheme — it reuses the ship's own.

## 2. Canonical bytes & authentication

- The sentence serialises to a **canonical trit→byte encoding** (fixed word order, fixed
  field widths, no optional whitespace) — one sentence, one byte string, always.
- The authenticator signs/MACs *those bytes*. Two profiles:
  - **HMAC / macaroon profile** (first-party cabins; CF5's open-day path): the authenticator
    is an HMAC chain. Cheap, no asymmetric crypto, offline-verifiable by the issuer.
  - **Signature / UCAN profile** (third-party, cross-node; CF5's "next"): Ed25519 over the
    bytes, issuer = a DID-equivalent (the issuer's key content-address). Publicly verifiable.
- **Vetted crypto only** — SHA3 / HKDF / Ed25519 / HMAC. The ternary layer never computes
  the digest.

## 3. Attenuation (delegate weaker, never stronger)

- **Macaroon profile:** append a `CAVEAT` word and re-HMAC using the previous signature as
  the key. Anyone can narrow; no one can widen or forge; the holder needs no contact with
  the issuer to attenuate.
- **Signature profile:** mint a child grant whose `RIGHTS` ⊆ parent, carrying the parent
  grant's content-address as a proof link; sign with the delegator's key. (UCAN proof chain.)
- `DELEG_DEPTH` caps the chain length; `RIGHTS` is monotone-narrowing down the chain
  (enforced at verification: a child right must be ≤ its parent's).

## 4. Revocation (three mechanisms, strongest last)

1. **Expiry caveat** — passive; the grant simply dies at a time. Cheap, always include one.
2. **Published revocation record** — a `CRYPTO/REVOKE` word naming the grant's
   content-address, published to the substrate; verifiers check it on `resolve`.
3. **Key rotation** — the issuer rotates its key; *every* grant under the old key dies at
   once. This is the **zero/blind-custody revocation**: after rotation, the Pi's blind
   ciphertext is undecryptable and any grant it held is dead. (Depends on the rotation
   design — the round's crux; see primer §6.)

## 5. Verification (what a verifier checks, in order)

1. Parse the sentence; reject unknown `GRANT_HEAD` version.
2. Check the authenticator over the canonical bytes (HMAC key or issuer signature).
3. Walk any delegation chain: each child's `RIGHTS` ⊆ parent, `DELEG_DEPTH` not exceeded,
   proof links resolve.
4. Evaluate every `CAVEAT` (expiry in the future, request within `SCOPE`/`QUOTA`, audience
   matches).
5. Check no `REVOKE` record for this grant or its ancestors.
6. Only then: the requested action ⊆ `RIGHTS` on `OBJECT_REF`. **Possession + these checks
   grant authority — never identity.** (Invariant I1.)

## 6. Interop — this *is* a UCAN / macaroon, in ternary

| Ours | Macaroon | UCAN |
|---|---|---|
| `OBJECT_REF` | location | capability resource |
| `GRANT_HEAD` | identifier | header |
| `ISSUER_REF` / `AUDIENCE` caveat | — | iss / aud (DIDs) |
| `RIGHTS` | — (implicit) | ability |
| `CAVEAT` words | caveats | caveats / conditions |
| proof link / HMAC chain | signature chain | prf (proof chain) |
| authenticator | HMAC | Ed25519 sig |

Because the mapping is 1:1, a TernOO capability can **export to a UCAN** for cross-system
interop (primer open question "adopt vs mirror UCAN": we *mirror* in ternary and *bridge*
at the boundary — ship-true inside, interoperable outside).

## 7. Worked example (informal)

> Alice grants Bob append-only access to her mailbox until Friday, no re-delegation:
> `[GRANT_HEAD: v1,mailbox] [ISSUER_REF: <Alice-key addr>] [OBJECT_REF: <Alice-mailbox addr>]
> [RIGHTS: append=+1, read=−1, write=−1, delegate=−1] [CAVEAT EXPIRY: Fri] [DELEG_DEPTH: 0]`
> + HMAC over the canonical bytes keyed by Alice's mailbox secret.
> Bob presents it to the Pi; the Pi (blind) verifies the HMAC and the caveats and accepts
> an append — without ever reading the mailbox. Alice rotates her key → the grant is dead
> and the Pi's stored ciphertext is noise.

## 8. Open questions for the round

1. **Un-reserve CRYPTO for this use** — ratify with CF5 + reconcile exact
   qualifier assignments against the Language Audit (this seat can't see it).
2. **Rights lattice** — the exact permission set and its partial order (what ≤ what).
3. **Macaroon vs signature as the default** — first-party cabins HMAC, cross-node Ed25519;
   confirm the split and where the boundary sits.
4. **Key/address word-encoding** — the canonical multi-word MAP encoding of a 256-bit key
   (chunking, padding, endianness) — needs the audit.
5. **Revocation record lifetime & propagation** — how long a `REVOKE` must persist and how
   `resolve` guarantees a verifier sees it.
6. **Rotation binding** (the crux) — "every grant under the old key dies" presumes a clean
   key→grants binding and a working rotation story. That design is step-0 of §4.3.

---
*Designed to lift into the separate ID/Auth repo as `/spec/capability-word.md` (per
deployment-topology §4). It uses TernOO words; it does not reach into TernOO internals.*
