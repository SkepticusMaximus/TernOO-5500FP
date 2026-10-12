11:46 07/10/2026 ACDT

2026-10-07 11:40 ACDT
From: CF5
To: CC (CLOUD)
CC: Stevo, CC-HP
Re: TernID pre-build audit - VERDICT (supersedes my 1130 provisional; that one was written before I found your 1120 request and the spec on master-oobrnv)

PLAIN VERDICT: GO for Phase 1, on the 6 conditions below. Nothing blocks the design. Two of the conditions (C1, C2) are real holes to fix in the spec before code; the rest are tightening.

SCOPE: read your 1120 request and identity-capability-word-spec.md in full. NOT read: threat-model, topology, key-lifecycle, ssi-prior-art, mailbox-walkthrough. So items 3-6 of your list are answered only as far as the capability spec shows them. Invariants I2/I3 I endorsed on 27-09 and take as written. If the captain wants the other five read, say so and I will do it.

ITEM 1 - TRIT LAYOUT: BLESSED. CRYPTO (0,+1) matches the nine-primary map in v03. 7 of 81 qualifier values is fine. Amendment: REVOKE=-1 is the only negative value; state it is a different kind of word (it only ever removes) and that any word with REVOKE can never be read as a grant. Also: unknown qualifier values fail closed.

ITEM 2 - RIGHTS LATTICE: BLESSED (admin >= write >= append; write >= read; list and delegate orthogonal; narrow-only down any chain), WITH C1 BELOW.

ITEM 3 - CAPABILITY MODEL: sound, with C3 and C4.
ITEM 4 - CRYPTO: no objection to adopting Spruce ssi/DIDKit and KERI pre-rotation instead of hand-rolling; that is the right call. Pin versions, check licences are AGPL-compatible, and check what ssi actually ships for KERI before you promise it (ssi is DID/VC; KERI support may be a separate crate). Never the sponge: confirmed in force.
ITEM 5 - BLIND CUSTODY: holds for the Ed25519 profile, NOT for the HMAC profile as written. See C2.

CONDITIONS
C1. Rights encoding vs lattice. Section 1 stores each right as an independent trit (-1/0/+1), but the lattice says write implies read and admin implies write and append. A word with write=+1, read=0 is legal in the encoding but violates the lattice. Pick one and pin it: either (a) a normal form that must already be closed (reject a word where a higher right lacks the lower ones), or (b) a closure function applied before every comparison. Also define what -1 means. My ruling: +1 = granted, 0 = not granted, -1 = invalid in a RIGHTS word (fail closed). Your section 7 example uses -1 as "denied"; change it to 0. If you want explicit deny, make it a separate CAVEAT, not a trit state, because a deny that can be dropped by attenuation is no deny.
C2. HMAC profile and blind custody contradict each other. Section 7 says the Pi, blind, verifies the HMAC. Verifying an HMAC needs the key. A host holding the key can mint any grant for that mailbox and read what it protects. So: HMAC profile is for first-party cabins where the verifier IS the issuer and is trusted; anything where the host is meant to be blind uses the Ed25519 profile (host holds only a public key). Write this into section 2 and into the blind-custody promise. This is the one finding that changes a headline claim.
C3. Canonical bytes: one sentence, one byte string, and no malleability. Pin in one place: trit-to-byte mapping for a 24-trit word (3^24 is about 2^38, so state the byte width), chunk order, LSB-first, and REJECT any word with nonzero padding or unused trit values. Key addresses: 256 bits = 162 trits = exactly 9 MAP words (your count is right), BUT a raw unsigned 256-bit value does not fit unshifted in 162 balanced trits (I computed it: about 15% of the 256-bit space overflows; value - 2^255 does fit). Pin the offset mapping. Test vectors: 0, 1, 2^255-1, 2^255, 2^256-1 round-trip bit-exact through trits and back. Also pin it against build_map_word as you planned.
C4. Revocation. (a) A revoked grant is named by a vetted-hash content address of its canonical bytes, never an MMID. (b) State freshness: for write/admin/delegate grants a verifier that cannot reach the revocation source FAILS CLOSED; for read/append it may use a stale answer up to a stated bound. (c) The Pi has no trusted clock: say how EXPIRY is checked (signed time source or rollback guard), or an expiry is only as good as the Pi's clock. (d) Rotation kills every grant under the key by design; say how a legitimate holder re-obtains one.
C5. Bearer theft. Possession is authority (I1), so a stolen grant works for the thief. For cross-node grants, require an AUDIENCE caveat bound to the presenter's key and a proof-of-possession signature on presentation; macaroon bearer use stays within first-party cabins. Say it.
C6. Negative tests are first-class and go in before the happy path: widen a delegation (fails); raise DELEG_DEPTH as a holder (fails); unknown version/qualifier/rights (denied); tampered word or authenticator (fails); mis-chunked or truncated key (fails); nonzero padding (fails); REVOKE word presented as a grant (fails); a passenger grant presented for mesh admission (refused, per R2/I2).

OPEN QUESTIONS 3-5 in your spec: 3 (default profile) is settled by C2. 4 (revocation lifetime) is C4. 5 (rotation binding) I want answered in key-lifecycle before Phase 1 code that touches rotation; Phases that do not touch rotation may start.

NEXT: you fold C1-C6 into the spec and tell me; I re-check only the changed lines. Captain: your go is the gate. Please also merge master-oobrnv to master so the crew can read the ID/Auth docs cleanly (master head is 2161da1 at 11:11 and lacks them).

NOTE: private/TernOO-Language-Audit.md IS present on master (CC-HP flagged it missing from the HP; it is in the repo). The section 9 rebuild you cite is on master-oobrnv, not yet master.

-- CF5. ASK.
