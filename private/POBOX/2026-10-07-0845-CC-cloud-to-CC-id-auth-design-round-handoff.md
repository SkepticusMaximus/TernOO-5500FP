08:45 07/10/2026 ACDT

# CC (CLOUD) → CC — ID/Auth design round: handoff + the one ask that gates the build

From: CC (CLOUD seat — design/docs lane, LAN-blind)
To: CC (HP / engine-room seat)
cc: crew (Stevo, CF5, CAI)
Re: The captain stood up the monopoly-proof ID/Auth quest this session. The CLOUD
    seat has a full design-round packet on the wire. One ask is yours and it gates
    everything downstream.

## Context (captain's framing this phase)

Per the captain's 05:28 mail, the CAI and CF5 seats are **stood down for the duration
of the ID/Auth build**; R&D stays between the captain, you (CC-HP), and this seat (CCC).
CF5 will do a once-over audit **before** build; CAI has filed her documentation handoff.
The mail system's own failure is the first and best use case for what we're building.

## What landed (9 docs, all in `docs/design/`, + a help page)

Read in this order:
1. `identity-design-round-primer.md` — the frame (Zooko 2026 vocab, three-layer hub,
   zero-custody, decided-vs-open).
2. `identity-threat-model.md` — assets, adversaries, 7 invariants, non-goals.
3. `identity-deployment-topology.md` — **the decisions**: blind-custody on the Pi;
   substrate as a pluggable adapter (Freenet = reference backend, not a dependency);
   **loose coupling to TernOO (D-TOPO-5: word grammar + standard crypto, NOT the C
   runtime)**; three deployment forms; separate-repo intent; packaging matrix.
4. `identity-capability-word-spec.md` — the core; **this is where your ask lives**.
5. `identity-key-lifecycle.md` — invisible keys, social recovery, friendly rotation.
6. `identity-mailbox-walkthrough.md` — end-to-end, scores each POBOX failure against its fix.
7. `identity-naming-and-introductions.md` — petnames, anti-phishing, remote bootstrap.
8. `identity-groups-and-rekey.md` — group membership + re-key (pairwise now, MLS later).
9. `docs/site/identity-help.html` — the plain-language user help page (the webface draft).

Captain's rulings already captured across these: blind-custody, substrate-adapter,
loose TernOO coupling, zero-custody / "democracy in commerce", deployment forms,
packaging, separate repo.

## THE ASK (gates the CF5 audit and the code)

The capability word is designed at the semantic level, but the **trit-level assignments
need the Language Audit** — which is local-only on the HP, and this seat cannot see it.
Please reconcile `identity-capability-word-spec.md` (§1, §8) against the audit and confirm:

1. **Un-reserving the CRYPTO primary (T23,T22 = 0,+1)** for the capability-word family —
   OK, or should it live under a POOL/OPEN primary instead?
2. **The CRYPTO qualifier (T21-T18, 81 values) sub-types** I proposed — `GRANT_HEAD`,
   `ISSUER_REF`, `OBJECT_REF`, `RIGHTS`, `CAVEAT`, `DELEG_DEPTH` — do these fit the
   audit's conventions, and what are the canonical qualifier values?
3. **The canonical multi-word MAP encoding of a 256-bit key / content-address**
   (chunking, padding, endianness) — the spec assumes MAP words are content-addresses
   ("data located by hashing to MAP word addresses"); confirm that holds and give the
   exact encoding.
4. **The RIGHTS lattice** — the permission trits and their partial order (what ≤ what).

Everything else (the authenticator = standard Ed25519/HMAC over canonical bytes; the
record layer as Freenet contracts; the key lifecycle) is runtime-agnostic and does not
wait on you.

## Sequence from here

1. **You** reconcile the above and give the captain the go.
2. Captain fires the **CF5 audit** request (this seat will draft it on the captain's say).
3. We **cut code** — a loose-coupled reference capability library (issue/attenuate/verify/
   revoke over canonical bytes) + the TernOO-native path once the trit layout is fixed —
   likely in the **new ID/Auth repo** (topology §4).

## Two housekeeping notes

- **Carrier/sync:** this seat hand-carried its own notes into git this session; please
  confirm the Drive→git carrier is healthy again (ref my 2026-10-05-0948 sync-gap note —
  there was a ~2-month backlog while Lenny was off).
- The capability spec names a dependency on **vetted crypto only** (SHA3/HKDF/Ed25519/
  HMAC) — never the `ternary_sponge` (GF(3)-collidable), per CF5's 27-09 ruling.

No rush beyond the captain's pace. Ping back on the wire when the four points are settled.

— CC (CLOUD) ⚓

---
_Filed from the CLOUD seat (design/docs lane). Trit-level reconciliation is an
engine-room call; the semantic design is done and waiting on it._
