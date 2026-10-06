# Identity / Auth — Threat Model (one page)

**Status:** DRAFT, design-round deliverable #1 (CF5's §5: "threat model before design").
Write it down before anyone designs, so the design can be checked against it.
**Author:** CC (CLOUD seat) · **Date:** 06/10/2026 ACST · **Gate:** captain's side window.
**Reads with:** `identity-design-round-primer.md`, `identity-research-zooko-brief.md`,
`private/POBOX/2026-09-27-2105-CF5-to-crew-identity-and-authorisation-oversight-read.md`.

---

## 1. What we protect (assets, most-critical first)

1. **Crew mail & docs** — `private/`, the POBOX, the bench. Confidentiality + integrity.
2. **User private keys / seeds** — the root of every identity; compromise is total.
3. **The mesh ledger** — mint / vote / earn (S5). Integrity + Sybil-resistance.
4. **The LAN** — Lenny, HP, Pi. The Pi faces the internet; the others must not.
5. **Passenger cabins & user content** — a passenger's own encrypted data and grants.
6. **Identity records** — the signed, mutable profiles; integrity + controlled disclosure.
7. **Availability** — the box/mesh keeps working; no single reachable chokepoint.

## 2. Trust boundaries (the planes)

```
 public internet ─▶ [tunnel] ─▶ PASSENGER process ─┊─ (no FS path) ─ CREW engine (loopback)
                                   allow-list,                         POBOX / docs / private/
                                   own storage root
            mesh peers ─▶ [peer admission: costly, R2-gated] ─▶ LEDGER (mint/vote/earn)
            zero-custody: a HOST is itself across a trust boundary from the user's data
```
Each arrow is a place authority must be checked, not assumed. The Pi is isolated from the
LAN (own VLAN/firewall, unprivileged service, read-only mounts where possible).

## 3. Adversaries (from whom)

| Actor | Can do | Primary threat |
|---|---|---|
| Curious passenger | hold a valid cabin grant | read across cabins; reach `private/` |
| Malicious passenger | craft inputs, upload content | path-traversal/route-abuse to crew data; store illegal content |
| Scraper / bot | hit public routes at scale | DoS; harvest; abuse quotas |
| Compromised Pi | run code on an internet-facing node | **foothold onto the LAN**; impersonate the box |
| Network MITM | sit on the wire | spoof a peer/host; swap keys mid-session |
| **Malicious / compromised host** (zero-custody) | hold ciphertext + served grants | read user data; retain after revocation; profile by metadata |
| Sybil attacker | mint cheap identities | capture mint/vote/earn; inflate the ledger |
| Lost/stolen key | hold a real private key | full impersonation until rotation/revocation works |

## 4. What a passenger may do (the capability surface — decide before build)

Open per CF5; the answers scope the whole liability surface:

- May a passenger **store** data? How much (quota)? For how long?
- May a passenger **publish** (make content reachable by others)?
- May a passenger **run code**? (Default: **no**.)
- What is the **abuse/takedown** path for user-uploaded content? (Open-day item, not polish.)

Default posture: **least authority** — a passenger gets the narrowest grant that works, and
**a passenger capability never confers mesh standing** (§5).

## 5. Security invariants we design to (must hold)

- **I1 — Authority ≠ identity.** Access is a held capability, never ambient from "who you are".
- **I2 — Passenger ≠ peer.** No passenger grant ever becomes mesh/mint standing, by construction.
- **I3 — Crew data has no public path.** The passenger process has no filesystem route to `private/`.
- **I4 — Zero-custody.** A host holds no data it can read without a *live* grant; **revocation
  (= key rotation) renders its stored copy useless**. (Caveat: cannot un-see already-decrypted
  cleartext; content custody ≠ metadata secrecy — see non-goals.)
- **I5 — Designate in ternary, authenticate with vetted crypto.** MMID/word *labels*; a real
  signature/HMAC over canonical bytes *authenticates*. Never the GF(3)-collidable sponge.
- **I6 — Least authority & attenuation.** Every grant is the weakest that works and is
  attenuable-only on delegation (never escalatable).
- **I7 — Verifiable connections.** A client verifies the key it's talking to itself (dial-by-key),
  not via a global namespace it must trust.

## 6. Non-goals (explicitly out of scope, so the design doesn't chase them)

- **Metadata/traffic-analysis resistance** — a host may still learn when/with-whom/how-much.
  Content zero-custody is *not* a metadata guarantee (SimpleX's axis; separate effort).
- **Anonymity-with-authority (zero-knowledge)** — research only, off the critical path.
- **Real-world identity binding** — we identify *keys/anonymous entities*, not legal persons.
- **Signal-network interop** — adopt the Signal *protocol/crypto*, not the closed network.
- **Un-seeing data a host already decrypted** under a valid grant — impossible; not promised.

## 7. Decisions this raises for the round

1. Passenger capability surface (§4) — store/publish/run/quota/takedown.
2. Zero-custody vs blind-custody availability model (host holds nothing vs. caches ciphertext).
3. The peer-admission cost function (S5) — what makes a *peer* identity expensive to mint.
4. Key rotation/recovery with no central fallback — the crux (primer §6); I4 depends on it.

---
*One page by design. The moment it's ratified, it becomes the checklist every later identity
decision is tested against.*
