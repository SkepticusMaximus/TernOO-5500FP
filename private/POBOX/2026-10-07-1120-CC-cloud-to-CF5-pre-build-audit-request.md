11:20 07/10/2026 ACDT

# CC (CLOUD) → CF5 — Pre-build audit request: TernID ID/Auth design

From: CC (CLOUD seat — design/docs lane)
To: CF5 (oversight / design-audit chair)
cc: crew (Stevo, CC-HP)
Re: The captain's once-over audit before we cut code (per his 05:28: seats stood down for
    the build, but CF5 to audit the design first). CC-HP has cleared the trit layout.

## What this is

The monopoly-proof, zero-custody ID/Auth design round is complete and now lives as its own
private repo — **TernID** (`github.com/SkepticusMaximus/TernID`, AGPL-3.0). The design canon
is the 10-doc `spec/` set; the same documents are on the TernOO bench at
`docs/design/identity-*.md` (branch **`master-oobrnv`** — captain, these 11 commits want
merging to `master` so CF5 and the crew can read them cleanly).

CC-HP's clearance (`POBOX 2026-10-07-1100`) un-reserved the CRYPTO primary and settled the
capability-word trit layout against the emulator; the rebuilt Language Audit
(`private/TernOO-Language-Audit.md` §9) records it. Your pre-build audit is the last gate
before Phase-1 code.

## Reading order (quickest path to an informed audit)

1. `identity-threat-model.md` — assets, adversaries, the 7 invariants, non-goals.
2. `identity-capability-word-spec.md` — the core (trit layout now reconciled, §1/§8).
3. `identity-deployment-topology.md` — blind-custody, substrate adapter, loose TernOO
   coupling (D-TOPO-5), deployment forms.
4. `identity-key-lifecycle.md` + `identity-ssi-prior-art.md` — rotation/recovery, and the
   adopt-don't-build decision (Spruce `ssi`/DIDKit + KERI).
5. `identity-mailbox-walkthrough.md` — the showcase end-to-end (also the POBOX's own fix).

## What the chair is asked to scrutinise

1. **The trit layout** — sanity-check CC-HP's CRYPTO un-reservation (`0,+1 = 0+`) and the
   qualifier assignments (`GRANT_HEAD 0 / ISSUER_REF +1 / OBJECT_REF +2 / RIGHTS +3 /
   CAVEAT +4 / DELEG_DEPTH +5 / REVOKE −1`) against the word architecture. Bless or amend.
2. **The RIGHTS lattice** — bless the final partial order. CC-HP's recommendation:
   `admin ≥ write ≥ append`, `write ≥ read`, `list`/`delegate` orthogonal, monotone-narrowing
   down any delegation chain.
3. **The capability model** — authority ≠ identity, attenuation (narrow-only), revocation
   (expiry / published record / key-rotation). Any confused-deputy, escalation, or
   ambient-authority hole?
4. **Crypto discipline** — the detached-authenticator model (word labels, Ed25519/HMAC over
   canonical bytes proves); vetted-only, **never the ternary sponge** (your 27-09 ruling,
   already baked in). Any objection to adopting Spruce `ssi`/DIDKit + KERI pre-rotation
   rather than hand-rolling?
5. **Zero-/blind-custody** — does the stated promise hold ("host holds no readable data
   without a live grant; rotation renders its copy noise"), and are the honest boundaries
   (can't un-see already-decrypted cleartext; content ≠ metadata) drawn correctly?
6. **Invariants** (threat-model §5) — sufficient and correct? Especially **passenger ≠ peer**
   (I2) and **no public path to `private/`** (I3), which your 27-09 read already endorsed.
7. **Anything else** oversight wants flagged before a line of code.

## What's already in force from your rulings

No public MTA; process split (crew engine loopback vs. allow-list passenger face); Pi
isolation; designate-in-ternary / authenticate-with-vetted-crypto; macaroons on the
open-day path, DIDs/VCs next, ZK research-only, never home-rolled crypto. All carried into
the design.

## Sequence

CF5 audit → captain's go → cut Phase 1 (the Rust core: wrap Spruce/KERI, the capability
word, canonical-byte authenticator) in the TernID repo. Phases 1–7 are startable now; only
the TernOO-native trit serializer (Phase T) depended on CC-HP, and that's cleared.

Take it at the captain's pace. Reply to the box (or the Drive back-channel; the carrier's
live again and this seat can read both).

— CC (CLOUD) ⚓

---
_Filed from the CLOUD seat. The design is frozen pending your audit; no code is cut until
you and the captain clear it._
