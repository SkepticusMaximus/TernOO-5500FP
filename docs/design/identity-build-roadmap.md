# ID/Auth — Build Roadmap & Repo Scaffold (DRAFT)

**Status:** DRAFT. Turns the 9-doc design packet into a phased build plan and the
separate-repo blueprint, marking what can start now vs. what waits on CC's trit
reconciliation. Gate: captain's side window. No code is cut until CF5's pre-build audit
(captain's sequence).
**Author:** CC (CLOUD seat) · **Date:** 07/10/2026 ACDT
**Reads with:** all `identity-*.md`; especially `identity-deployment-topology.md` (§4–§7).

---

## 1. Stack decisions (to confirm)

- **Core library in Rust.** One portable implementation that (a) compiles to **WASM** for
  Freenet contracts, (b) exposes **FFI bindings** for clients and the SDK, and (c) is
  memory-safe for crypto code. The TernOO C server consumes it via FFI, or re-implements
  the verifier natively in C for the on-5500FP path (loose coupling, D-TOPO-5).
- **Vetted crypto only** — Ed25519 / HKDF / SHA3 / HMAC via audited crates. Never the
  `ternary_sponge`.
- **Canonical bytes now, native trits later.** The protocol signs over a **canonical byte
  serialization** of the grant sentence. That format can be fixed *now*; the TernOO
  *trit* encoding becomes an equivalent native serializer added when CC clears the ask.
  So the crypto/verify core does **not** wait on the Language Audit.
- **Wrap prior art; don't rebuild it** (see `identity-ssi-prior-art.md`). The core
  **adopts** well-licensed Apache-2 stacks rather than hand-rolling: **Spruce `ssi`/DIDKit**
  (Rust) for DID/VC crypto + resolution, and **KERI pre-rotation** for the key
  rotation/recovery crux. This shrinks the from-scratch core to our genuine contribution —
  the capability *word*, the zero-custody mailbox, the substrate adapter, and the petname
  layer. Phase 1/2 become "wrap + integrate," not "invent."

## 2. Phased build

Legend: **NOW** = startable before CC's reconciliation · **GATED** = waits on it.

| Phase | What | Depends on | Status |
|---|---|---|---|
| **0 — Scaffold** | New repo, tree (§3), CI skeleton, spec docs lifted in | captain opens repo | **NOW** (blueprint ready) |
| **1 — Core capability lib** | canonical encoding; issue / attenuate / verify / revoke; authenticator (Ed25519/HMAC); unit tests | stack §1 | **NOW** |
| **2 — Records + key lifecycle** | account / group / mailbox / revocation records + validation; enroll (QR) / add / remove / social-recovery / rotate / panic | Phase 1 | **NOW** |
| **3 — Substrate adapter** | the 5-call interface; in-memory + local-file backend; **conformance suite** | Phase 1 | **NOW** |
| **4 — Freenet backend** | records as Freenet contracts (WASM); pass the conformance suite | Phase 3 + Freenet env | **NOW** (needs Freenet node) |
| **5 — Mailbox end-to-end** | send/receive, blind-custody delivery, capability anti-spam | Phases 1–3 | **NOW** |
| **6 — Desktop client** | messenger MVP (the showcase), petname UX, invisible keys | Phases 1–5 | **NOW** (UI) |
| **7 — Groups** | membership + re-key (pairwise first; MLS later) | Phases 1–5 | **NOW** |
| **T — TernOO-native encoding** | trit-level capability serializer; optional on-5500FP verify | **CC's 4-point ask** | **GATED** |
| **8 — Packaging** | desktop installers (Windows first) → SD-card node image → SDK | Phases 1–7 | later |

**Key point:** only Phase **T** is gated on CC. Phases 1–7 proceed on the canonical byte
format; the native trit serializer slots into Phase 1's `encoding/` when cleared. So the
audit gates *shipping on-ship-native*, not *progress*.

## 3. Repo scaffold (blueprint — instantiate on "open the repo")

```
<id-auth-repo>/                 # name = captain's call
├── README.md                   # what it is, the 3 deployment forms, how to build
├── spec/                       # the 9 design docs lift here as the canon
│   ├── primer.md  threat-model.md  deployment-topology.md
│   ├── capability-word.md  key-lifecycle.md  mailbox-walkthrough.md
│   ├── naming-and-introductions.md  groups-and-rekey.md
│   └── help/identity-help.html
├── core/                       # Rust reference library
│   ├── capability/             # issue · attenuate · verify · revoke
│   ├── records/                # account · group · mailbox · revocation + validation
│   ├── keys/                   # lifecycle: enroll · add · remove · recover · rotate
│   └── encoding/               # canonical bytes  (+ ternary/ native serializer — GATED)
├── substrate/
│   ├── interface/              # the 5 calls: put/get/publish/resolve/subscribe
│   ├── backends/               # memory · localfile · freenet · …
│   └── conformance/            # the suite every backend must pass
├── node/                       # self-hosted full node (SD-card build)
│   └── stack/                  # Tor · crypto · freenet · TernOO · p2pcp/p2pvp · CGP · id-auth wiring
├── sdk/                        # "sign in with sovereign ID" dev library + bindings
├── clients/
│   └── desktop/                # the messenger showcase (first)
├── packaging/                  # win/mac/linux installers · SD-card image · recipes
└── .github/workflows/          # CI: build core · run conformance · build artifacts
```

TernOO depends on this repo (as a consumer of the capability lib), not the reverse
(topology §4). The lift of the `spec/` docs happens when the capability-word + substrate
interface are stable — close now; final after CC's reconciliation.

## 4. The conformance suite (why it ships in Phase 3, not later)

It is the guard that keeps the substrate swappable and the platform-agnostic promise
honest. Written against the 5-call interface, it asserts: `put`→`get` round-trips a blob
by its content-address; `publish`→`resolve` returns the latest signed version and rejects
an unsigned or stale one; `subscribe` fires on a new signed version; a revoked record is
observable; **offline-both** delivery holds (an envelope put while the recipient is
offline is retrievable later). Every backend (memory, localfile, Freenet, future) must
pass the same suite. Write it before the second backend exists, or the interface quietly
rots into Freenet's shape.

## 5. First actions when the gates open

1. **Captain opens the repo** → this seat (or CC) instantiates the scaffold (§3) + CI.
2. **CF5 audit** (captain fires it; this seat drafts the request) → design frozen.
3. **CC clears the 4-point ask** → Phase T unblocks; the native serializer lands in `core/encoding/`.
4. Cut **Phase 1** (core lib + tests) first — everything else inherits from it.

## 6. Open items

1. **Repo name** — captain's.
2. **Core language = Rust?** — confirm (vs. Go/Zig); Rust recommended for WASM + FFI + crypto.
3. **First client target** — desktop (which OS first; Windows per the packaging note?) vs. a
   CLI reference client for faster end-to-end testing.
4. **MLS adoption point** — ship groups on pairwise/sender-keys; name the member-count that
   triggers the MLS move (groups spec §6).

---
*Lifts into the separate repo as `/spec/build-roadmap.md`. The scaffold (§3) is a blueprint;
this seat can instantiate it as real dirs + stub READMEs the moment the repo exists.*
