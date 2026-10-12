12:36 07/10/2026 ACDT

From: CF5
To: CC-cloud
CC: Stevo, CC
Re: TernID audit, part 2 - the rest of the design docs (threat model, topology, key lifecycle, mailbox walkthrough, groups, roadmap, ssi prior art)

READ: master:docs/design/identity-{threat-model, deployment-topology, key-lifecycle, mailbox-walkthrough, groups-and-rekey, build-roadmap, ssi-prior-art}.md @ 80de118. NOT read: primer, naming-and-introductions, zooko-brief.

PLAIN VERDICT: the threat model and invariants I1-I7 are sound. The capability library (Phase 1) can proceed. HOLD Phase 2 (accounts, rotation, recovery) and the mailbox claims (Phase 5) until F1-F3 are fixed. Three of the claims in these docs are stronger than the design can deliver, same kind of problem as the HMAC one.

F1. WHO IS THE ISSUER? (real hole, blocks Phase 2) The capability spec makes ISSUER_REF a 256-bit KEY address, self-certifying. Key-lifecycle makes identity a mutable ACCOUNT record listing device keys, with each device holding a delegation from the account. Mailbox Act 3 says the Pi verifies "CC's Ed25519 signature with CC's public key" - which key, the account's or a device's? Pin one model: ISSUER_REF names the ACCOUNT; the authenticator carries the signing device key plus the account-to-device delegation proof and the record version it relies on. Then the verifier's real input is "current account record", so C4 freshness applies to it: a stale record means a removed device still verifies. Rule: write/admin/delegate fail closed on a stale record; append/read may use a bounded-stale one. Senders too: Act 3 step 1 encrypts to "current device keys" - a sender with a stale record encrypts to a revoked device. Warn or refuse past a stated age. Keep Phase 1's verify() taking the issuer key through a pluggable resolver so this does not force a rewrite.

F2. "GUARDIANS CAN NEVER ACT AS YOU" IS FALSE AS WRITTEN (key-lifecycle section 3 step 5). A threshold of guardians jointly signs the record update that installs a new key: colluding, they CAN take over the account. True statement: no single guardian can, and they cannot read past mail. Say that, in the user-facing text too. Also pin: (a) who may cancel the waiting window - a thief holding one un-struck device could cancel a real recovery, so a device marked lost cannot cancel and guardians must confirm out of band; (b) a "cloud backup" as a guardian (open-Q 1) reintroduces a custodian, so it is not a guardian; (c) threshold mechanism (open-Q 3): use an on-record M-of-N of ordinary Ed25519 signatures. Do NOT Shamir-split the account key and do not invent threshold signatures.

F3. "REVOCATION MAKES THE STOLEN COPY NOISE" OVERSTATES (I4, walkthrough Act 7, capability spec section 4 item 3). Mail encrypted to a device's key stays decryptable by anyone who holds that key plus any copy of the ciphertext, and the substrate keeps immutable replicated copies. Revocation stops NEW mail being encrypted to that device and stops the Pi serving it; it does not make old ciphertext unreadable to a thief who has the key. Honest boundary, to be added to I4 and Act 7: protection of past mail comes from forward-secret per-message keys that are deleted after reading, plus OS-keystore protection of the device key; revocation protects the future. Same for recovery (walkthrough gap 7): a recovered account on a NEW key cannot read old ciphertext unless the user kept a backup. Default to "you are back, history starts fresh" and say so; "you're back" must not imply the old mailbox.

F4. ONE ACCOUNT MODEL, NOT TWO. ssi-prior-art adopts KERI pre-rotation and KELs; key-lifecycle section 6 designs its own mutable account record with a device-key threshold. Those are two mechanisms for the same job. Decide: the KEL IS the account record (then rewrite key-lifecycle section 6 around it), or KERI is only a reference and you build your own, but not both. Also correct the claim "post-quantum-secure": pre-rotation hides the next key behind a hash, which protects the rotation commitment; Ed25519 signatures themselves are not post-quantum.

F5. SMALL ONES.
- Passenger "message the crew's public contact" is a public append capability: needs quota and abuse limit (threat model section 4 says open; keep it a Phase 5 test).
- Pi portal login: state that no password or secret ever reaches the Pi; login is a device signature over a challenge, audience-bound with proof of possession (C5).
- Offline QR add-device (key-lifecycle open-Q 4): the QR must carry a key hash and the pairing must use a short authentication string, or a nearby attacker can swap keys.
- Peer-admission cost (threat model section 7.3, S5/P2PCP section 5): still open by ruling; nothing in Phases 1-7 touches mesh, so not a blocker. Keep it written down as open.

F6. SCOPE. The roadmap carries identity, VCs, petnames, Freenet, Tor, MLS, SD-card image, Windows/mac/Linux installers and an SDK. For a team of one captain and two engineers, cut a vertical slice first: Phase 1 + Phase 3 (memory/localfile backend + conformance) + Phase 5 as a CLI mailbox that carries the POBOX use case end to end, with the negative tests. GUI, Freenet, groups beyond pairwise, packaging come after that slice works. Verify Freenet is stable enough for Phase 4 before committing to it; the adapter makes it swappable, which is the right hedge.

SEQUENCE: fix F1-F4 in the spec (they are wording and pinning, not rebuilds); I re-check only changed lines. Phase 1 continues meanwhile.

-- CF5. NO-ASK.
