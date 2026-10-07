# The Capability Word — Spec (DRAFT)

**Status:** DRAFT, design-round deliverable (CF5 order of work, step 3). Gate: captain's
side window. Trit-level assignments below were **cleared by CC-HP on 07-10-2026** against
the canonical emulator (`5500fp_ternoo_v03.py`) and recorded in the rebuilt Language Audit
§9 (`private/TernOO-Language-Audit.md`) — **final subject to CF5's pre-build audit.**
**Author:** CC (CLOUD seat) · **Date:** 06/10/2026 ACST (assignments reconciled 07/10/2026)
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

A capability is an ordered sentence of words under the **CRYPTO primary (T23,T22 = 0,+1 =
`0+`)** — confirmed genuinely reserved/unused and **un-reserved for this family by CC-HP,
07-10** (final subject to CF5). Each word's 4-trit QUALIFIER (81 values; **7 used, 74
free**) names its role via the cleared canonical value shown below; the 18-trit payload
carries the field.

| # | Role (CRYPTO qualifier) | Payload (T17-T0, 18 trits) | Notes |
|---|---|---|---|
| 1 | `GRANT_HEAD` | version · grant-type · flags | opens every capability; grant-type ∈ {cabin, mailbox, record, delegation} |
| 2 | `ISSUER_REF` | MAP content-address of the issuer's identity record | multi-word (a key is ~9 words); self-certifying |
| 3 | `OBJECT_REF` | MAP content-address of the target (mailbox/cabin/record) | the thing being granted — "a word designating a mailbox" |
| 4 | `RIGHTS` | one trit per right (read/append/write/list/delegate/admin): **+1 granted · 0 not granted · −1 invalid → fail closed** (C1) | must be in **closed normal form** (a higher right implies its lowers); explicit deny is a `CAVEAT`, never a trit state |
| 5..n | `CAVEAT` (0+) | one attenuation each: `EXPIRY` · `SCOPE` (prefix under object) · `QUOTA` · `AUDIENCE` | macaroon caveats; **narrow only** |
| last-1 | `DELEG_DEPTH` | remaining re-delegation hops (0 = terminal) | attenuation of re-sharing |
| — | *(authenticator)* | **not a word** — Ed25519 sig / HMAC over canonical bytes | carried alongside (the dual-digest pattern) |

**Cleared CRYPTO qualifier values** (flat 4-trit; CC-HP 07-10, final subject to CF5):
`GRANT_HEAD = 0` · `ISSUER_REF = +1` · `OBJECT_REF = +2` · `RIGHTS = +3` · `CAVEAT = +4` ·
`DELEG_DEPTH = +5` · `REVOKE = −1`. (The head sits at the origin; withdrawal reads
naturally negative. 7 of 81 used, 74 free for future grant vocabulary.)

**Designation uses MAP, not a new type.** Because MAP words are already TernOO's
content-addressable addresses ("data located by hashing it to MAP word addresses"),
`ISSUER_REF`/`OBJECT_REF` are MAP word-sequences. The capability layer adds no new
addressing scheme — it reuses the ship's own.

## 2. Canonical bytes & authentication

- The sentence serialises to a **canonical trit→byte encoding** (fixed word order, fixed
  field widths, no optional whitespace) — one sentence, one byte string, always.
- **Canonical bytes (C3).** Fixed 24-trit-word→byte mapping (3²⁴ ≈ 2³⁸ → **5 bytes/word**),
  word order **LSB-first**, fixed field widths — one sentence → one byte string, always. A
  verifier **rejects any word with nonzero padding or an out-of-range trit value** (no
  malleability). Key/address encoding: a 256-bit value maps to 9 MAP words via the **offset
  `value − 2²⁵⁵`** (a raw unsigned 256-bit number overflows 162 balanced trits for ~15% of
  the space; the offset fits). Pinned in one place against `build_map_word`, with round-trip
  test vectors at `0, 1, 2²⁵⁵−1, 2²⁵⁵, 2²⁵⁶−1`.
- The authenticator signs/MACs those bytes. **Which profile is allowed depends on whether the
  verifier may be trusted with the key (C2):**
  - **Ed25519 / UCAN profile — REQUIRED wherever the verifier must be blind** (a relay/host
    like the Pi): the host holds only the issuer's **public** key, so it can verify but never
    mint. **The blind-custody promise rests on this profile.**
  - **HMAC / macaroon profile — ONLY for first-party cabins where the verifier IS the issuer**
    (or a party already trusted with the secret). Verifying an HMAC needs the key, so an
    HMAC-verifying host could also forge grants; it is therefore **never** used where a host
    is meant to be blind.
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

**Revocation rules (C4):**
- A `REVOKE` names the target grant by a **vetted-hash content-address of its canonical
  bytes**, never an MMID.
- **Freshness fails closed for power:** a verifier that cannot reach the revocation source
  **denies** `write` / `admin` / `delegate`; for `read` / `append` it may use a stale answer
  up to a stated bound.
- **Expiry needs a trustworthy clock:** the Pi has none, so `EXPIRY` is checked against a
  **signed time source** (or a monotonic rollback guard) — otherwise an expiry is only as
  good as the host's clock.
- **Re-grant after rotation:** rotation kills every grant under the old key by design; a
  legitimate holder re-obtains one from the rotated issuer (ties `key-lifecycle.md`).

## 5. Verification (what a verifier checks, in order)

1. Parse the sentence; **fail closed on** an unknown `GRANT_HEAD` version, an unknown
   qualifier value, non-closed `RIGHTS`, nonzero padding, or a `REVOKE` word presented as a
   grant.
2. Check the authenticator over the canonical bytes — **Ed25519 signature if the verifier is
   blind**; HMAC only where the verifier is the trusted issuer (C2).
3. Walk any delegation chain: each child's `RIGHTS` ⊆ parent, `DELEG_DEPTH` not exceeded,
   proof links resolve.
4. Evaluate every `CAVEAT` (expiry against a signed time source, request within
   `SCOPE`/`QUOTA`, `AUDIENCE` matches the presenter).
5. Check no `REVOKE` record for this grant or its ancestors (fail closed for
   write/admin/delegate if the revocation source is unreachable — C4).
6. Only then: the requested action ⊆ `RIGHTS` on `OBJECT_REF`. **Possession + these checks
   grant authority — never identity.** (Invariant I1.)

**Bearer theft (C5):** possession is authority, so a stolen grant works for a thief. For
**cross-node** grants, require an `AUDIENCE` caveat bound to the presenter's key plus a
**proof-of-possession** signature at presentation; bearer (macaroon) use stays within
first-party cabins. **Negative tests (C6) run before the happy path — see §9.**

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
> [RIGHTS: append=+1, read=0, write=0, list=0, delegate=0] [CAVEAT EXPIRY: Fri (signed time)]
> [DELEG_DEPTH: 0]` + an **Ed25519 signature** over the canonical bytes by Alice's key.
> Bob presents it to the Pi; the Pi — **blind, holding only Alice's public key** — verifies
> the *signature* and the caveats and accepts an append, without ever reading the mailbox or
> being able to mint a grant. Alice rotates her key → the grant is dead and the Pi's stored
> ciphertext is noise. *(HMAC would be wrong here: a blind host must not hold a key it could
> forge with — C2.)*

## 8. Open questions for the round

**Cleared by CC-HP (07-10, final subject to CF5's pre-build audit):**
- ✅ **Un-reserve CRYPTO** — confirmed reserved/unused; un-reserved for this family.
- ✅ **Qualifier assignments** — `GRANT_HEAD 0 / ISSUER_REF +1 / OBJECT_REF +2 / RIGHTS +3 /
  CAVEAT +4 / DELEG_DEPTH +5 / REVOKE −1` (7 of 81). Recorded in Language Audit §9.
- ✅ **256-bit address = exactly 9 MAP words** (LSB-first; final word zero-padded high trits).

**Still open for CF5 / the build:**
1. **Rights lattice — CF5 to bless the final order.** CC's recommendation:
   `admin ≥ write ≥ append`, `write ≥ read`, `list` and `delegate` orthogonal;
   monotone-narrowing down any delegation chain (child right ≤ parent).
2. **MAP-address chunking/padding** — pin the exact chunking/padding/endianness against
   `build_map_word` before freezing the canonical byte serialization (CC to pin; not a
   blocker to start).
3. **Macaroon vs signature as the default** — first-party cabins HMAC, cross-node Ed25519;
   confirm the split and where the boundary sits.
4. **Revocation record lifetime & propagation** — how long a `REVOKE` must persist and how
   `resolve` guarantees a verifier sees it.
5. **Rotation binding** (the crux) — "every grant under the old key dies" presumes a clean
   key→grants binding and a working rotation story (now backed by KERI pre-rotation —
   `ssi-prior-art.md` §3).

## 9. CF5 pre-build audit — conditions folded (07-10-2026)

CF5's verdict: **GO for Phase 1 on six conditions**; C1/C2 were real holes, now resolved
above. (Source: `master:private/POBOX/2026-10-07-1146-CF5-to-CC-ternid-pre-build-audit-verdict…md`.)

- **C1 — rights normal form** (§1, §5, §7): each right trit is `+1 granted / 0 not / −1
  invalid (fail closed)`; a RIGHTS word must be in **closed normal form** (a higher right
  implies its lowers — reject otherwise). Explicit deny is a `CAVEAT`, never a trit state (a
  deny that attenuation can drop is no deny).
- **C2 — blind custody ⇒ Ed25519** (§2, §5, §7): HMAC verification needs the secret, so a
  blind host uses the **signature** profile; HMAC is only for first-party cabins where the
  verifier is the issuer. *(Fixes the one headline claim the audit caught.)*
- **C3 — canonical bytes** (§2): 5 bytes/word, LSB-first, reject nonzero padding / out-of-range
  trits; 256-bit key via offset `value−2²⁵⁵` over 9 MAP words; test vectors pinned.
- **C4 — revocation** (§4): content-address naming; fail-closed freshness for
  write/admin/delegate; signed-time expiry; re-grant after rotation.
- **C5 — bearer theft** (§5): cross-node grants need `AUDIENCE` + proof-of-possession; bearer
  use stays first-party.
- **C6 — negative tests first-class, before the happy path:** reject — widening a delegation;
  a holder raising `DELEG_DEPTH`; unknown version/qualifier/rights; tampered word or
  authenticator; mis-chunked / truncated / overflowing key; nonzero padding; a `REVOKE` word
  used as a grant; a passenger grant presented for mesh admission (R2/I2).

**ITEM amendments (blessed):** `REVOKE` (−1) is a distinct *removal-only* kind — a word
carrying it can never be read as a grant; unknown qualifier values fail closed.

**ITEM 4 caveat (adopting Spruce/KERI):** `ssi`/DIDKit covers DID/VC; **KERI is a separate
Rust crate (`keriox`), not part of `ssi`** — don't promise KERI from `ssi`. Pin exact
versions and confirm each is AGPL-3.0-compatible before adding (recorded in `ssi-prior-art.md`).

**Deferred to `key-lifecycle.md` before any rotation-touching code (open-Q #5):** the
rotation-binding story. Phases 1–7 that don't touch rotation may start now.

---
*Designed to lift into the separate ID/Auth repo as `/spec/capability-word.md` (per
deployment-topology §4). It uses TernOO words; it does not reach into TernOO internals.*
