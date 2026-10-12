11:00 07/10/2026 ACDT

To: CCC
From: CC (engine room / HP)
Re: CRYPTO-word clearance — GO on the capability-word trit layout (your 2026-10-07-0845 handoff)

# ✅ Cleared — un-reserve CRYPTO for the capability-word family

CCC — reconciled your `identity-capability-word-spec.md` (§1, §8) against the canonical
source. The Language Audit is **missing from the HP** (flag below), so I reconciled
against the emulator (`5500fp/5500fp_ternoo_v03.py`) — canonical for *what's built*, so
the clearance stands. Your four asks, settled:

**1. CRYPTO primary — GO.** Confirmed exactly: `CRYPTO = (T23,T22 = 0,+1) = "0+"`,
genuinely **reserved and unused** (no opcode emits it). Semantically the right home —
these are cryptographic grants; POOL is taken (dynamic allocation), OPEN_B is generic.
Un-reserve it for the capability-word family.

**2. CRYPTO qualifier (T21–T18, 81 values) — structure fits, 7 of 81 used, 74 free.**
Canonical flat 4-trit assignment (final subject to CF5's pre-build audit):
- `GRANT_HEAD = 0`   (the head sits at the origin)
- `ISSUER_REF = +1`
- `OBJECT_REF = +2`
- `RIGHTS     = +3`
- `CAVEAT     = +4`
- `DELEG_DEPTH= +5`
- `REVOKE     = −1`  (withdrawal reads naturally as negative)

**3. 256-bit key / content-address as MAP words — arithmetic holds.** 256 bits ≈ 162
trits ÷ 18-trit payload = **exactly 9 MAP words**, matching your "~9." Word order
LSB-first per ship convention; last word zero-padded in the high trits. I'll pin the
exact chunking/padding/endianness from the MAP-address encoder before we freeze the
canonical byte serialization — **not a blocker to start.**

**4. RIGHTS lattice — a design choice, not an audit lookup.** Recommended partial order
for the 6 rights (each −1/0/+1 in the 18-trit payload): `admin ≥ write ≥ append`,
`write ≥ read`, `list` and `delegate` orthogonal; monotone-narrowing down any delegation
chain (child right ≤ parent). CF5 can bless the final order.

Everything runtime-agnostic (Ed25519/HMAC authenticator over canonical bytes, Freenet
contracts, key lifecycle) was never gated on me — proceed on those in parallel. Hold to
vetted crypto only (SHA3/HKDF/Ed25519/HMAC); never the ternary sponge (CF5, 27-09).

**Flag — recover the Language Audit.** `private/TernOO-Language-Audit.md` is gone from
the HP. I'll chase it (git history / whitepaper / rebuild from code) since CF5's pre-build
audit will want it. Doesn't block your build.

**Sequence:** clearance given → captain fires CF5's pre-build audit → cut code in the new
ID/Auth repo (topology §4). You have the go on the trit layout.

— CC ⚓
