# The Key Lifecycle — Spec (DRAFT, ELI10-first)

**Status:** DRAFT, design-round deliverable. The round's crux: keys that are invisible and
friendly for the many, sovereign for the few. Gate: captain's side window.
**Author:** CC (CLOUD seat) · **Date:** 06/10/2026 ACST
**Reads with:** `identity-capability-word-spec.md`, `identity-deployment-topology.md`,
`identity-design-round-primer.md`.

> Design rule that governs this whole document: **if we ever make a normal user look at a
> key, type a key, or fear losing a key, we have failed.** Security wins a special few;
> *ease* wins the many. We build for the many and let the few turn on the hard mode.

---

## 1. The big idea (ELI10)

You never see a key. Ever. You open the app, pick a name people will know you by, and use
it — like Signal or WhatsApp. The scary math (keys, signatures, locks) is the *computer's*
job, happening silently inside your phone. Your job is just: use the app, and have more
than one gadget or a couple of trusted friends, so you're never stuck.

The one idea that makes this both *easy* and *yours-alone*:

> **You are not a key. You are an "account," and your gadgets are keys that are allowed to
> act as you.**

A house has an address that never changes (that's *you*), and several keys that open it —
one on your keyring, a spare with a neighbour, one in a drawer (those are your *devices*).
Losing a key doesn't move your house. You just stop that key from working and cut a new
one. **No landlord holds a master key** — that's the sovereignty. But you keep spares and a
trusted neighbour — that's the ease.

## 2. Two kinds of "key change" — never confuse them

| | Tiny invisible keys | Which-gadgets-are-"you" |
|---|---|---|
| What | the lock on each message | the list of devices allowed to act as you |
| How often | constantly, every message | rarely — only when you add/lose a gadget or recover |
| Do you notice? | **never** | a tap; never a passphrase |
| Why | so a stolen key can't open old letters (forward secrecy) | so losing a phone isn't losing you |

When people say "key rotation" and get scared, they're imagining the second one as hard. We
make it a *tap*. The first one they never even hear about.

## 3. The lifecycle as six everyday moments

**① Birth — you make an account.** You install the app and pick a nickname. Behind the
glass, the app mints your first device key and creates your *account record* (the list of
"who's allowed to be me" — starts with just this device) and asks you to add one safety net
(a second device, or pick 2–3 guardians). *How:* automatic. *When:* first run. *You see:*
"Welcome," not a key.

**② Daily use.** Your device signs and decrypts invisibly, protected by your normal phone
unlock (face/fingerprint/PIN). Message keys rotate by themselves. *Decided by:* the app,
automatically. *You do:* nothing.

**③ Add a gadget.** New laptop? On the new device, scan a QR code shown on an old one (just
like Zooko scanning a QR on a walk). The old device vouches for the new one and adds it to
your account. *Decided by:* you, with a gadget you already have. *When:* whenever you like.

**④ Lose or retire a gadget.** Tap "I lost my phone" on any *other* device. That phone's key
is struck off your account immediately — it can no longer act as you, and anything it was
holding (like your blind-custody mailbox copy on the Pi) becomes useless to it. *Decided by:*
you, from another device. *When:* the second you say so.

**⑤ Recover when you've lost everything.** No devices left? Your **guardians** — a few
people and/or backups you chose at setup — approve your new device becoming you (say, 3 of
5). There's a short waiting window so *you* can cancel if it wasn't you. Then you're back.
*Decided by:* your guardians together — **never a company, never a password reset to beg
for.** No **single** guardian can do anything, and guardians can **never read** your
messages. But a **colluding threshold** of them *can* install a new key — that *is* the
recovery mechanism, so choose guardians you would trust with that. (The Argent/Vitalik
"social recovery" idea.) A **device marked lost cannot cancel** a recovery, and guardians
**confirm out of band**, so a thief holding one un-struck device can't hijack or block it (F2a).

**⑥ Panic / "something's wrong."** One button: reset. Every old key is kicked, a fresh one
is minted, and anyone watching gets told "my keys changed" (like Signal's safety-number
warning). *Decided by:* you, one tap.

## 4. So: how is rotation decided, when, and by whom? (your three questions)

| Rotation | When | Who/what decides |
|---|---|---|
| Message locks | every message, always | the app, automatically — invisible |
| Add a device | you get a new gadget | **you**, via QR from an existing device |
| Remove a device | you lose/retire one | **you** (from another device), or guardians if it was your last |
| Optional refresh | every N months (opt-in only) | the app, on a policy *you* set — off by default |
| Panic reset | you suspect trouble | **you**, one button |
| Recovery | you've lost all devices | **your guardians** (a threshold), with a cancel window |

The short version: **small keys rotate automatically; the big "who is me" only changes on a
simple human action or guardian help — never a surprise, never a company.**

## 5. Recovery — the honest part

The sovereign promise ("no company holds a master key") has a real cost: if you lose
**everything** at once, no one can magically reset you. We don't hide that — we design so it
almost never happens, and so getting back is friendly when it does:

- **Default for the many — spares + guardians.** Keep a second device, and/or pick 2–5
  guardians (friends, family, a hardware key you hold). Losing one thing never locks you out;
  losing all is fixed by people you trust, not a corporation. No seed phrase to lose. (A
  *cloud backup* is **not** a guardian — handing recovery to a provider reintroduces a
  custodian, the exact thing we're removing. F2b.)
- **Optional for the few — a written recovery phrase or a hardware key.** The crypto-native
  safety net. Powerful, but easy to lose or have stolen, so it's **hard mode, off by
  default**, offered to users who want it.
- **Recovery starts fresh (F3).** A recovered account runs on a **new** key, so it **cannot
  read old mail** unless you kept a backup. The promise is "you're back," not "your old
  mailbox is back" — the UI must say so plainly.
- **The honest limit:** lose every device *and* fail to reach enough guardians *and* keep no
  backup → you're locked out. That's the price of having no central master key. We counter
  it by making guardians one-tap to set up and nudging everyone to keep at least one spare.

## 6. Under the hood (for CF5 / CC-HP) — the account IS a KEL

**D-KEY-1 (captain's call, 07-10): the account is a KERI Key Event Log (KEL)** — one
mechanism, not two. We do **not** keep a separate bespoke account record alongside it (F4).

- **Account = a KEL** — a hash-chained, append-only log of **signed key events** for a
  self-certifying account identifier (KERI's AID). The KEL's current established state lists
  the **device keys** authorized to act for the account and the **guardians + M-of-N
  threshold**. Others petname *the account (AID)*, so it is the stable "you." Any party can
  verify a KEL anywhere with no special infrastructure (ambient verifiability).
- **"A device is me"** = a key event in the KEL authorizes that device key. *Add* = an
  establishment/rotation event adding the key (signed at the current threshold). *Remove /
  rotate* = a rotation event; **KERI pre-rotation** pre-commits the *hash* of the next key, so
  a leaked current key still cannot rotate the account. *Recover* = an **M-of-N of ordinary
  Ed25519 guardian signatures** on a rotation event installing the new device key — **not**
  Shamir-split keys and **not** threshold signatures (plain on-record M-of-N, F2c).
  Message-key rotation is the ratchet, separate and automatic.
- **Who may change the KEL?** The current device keys at the established threshold, or the
  guardian set on the recovery path. Self-governing — a tiny council of *your own* keys. No
  registrar.
- **Issuer of a capability (F1):** a grant's `ISSUER_REF` names the **account (AID)**, never a
  bare device key. The authenticator carries the signing **device key**, the **KEL event that
  authorizes it**, and the **KEL version (sequence number)** it relied on. A verifier resolves
  the **current KEL** through a pluggable resolver and applies **C4 freshness**: on a stale
  KEL, `write`/`admin`/`delegate` **fail closed**; `read`/`append` may use a **bounded-stale**
  one. Senders encrypting to "current device keys" must likewise **warn or refuse** past a
  stated KEL age, or they encrypt to a revoked device.
- **Blind-custody boundary (F3):** revoking/rotating kills the *grant* (no new mail is
  encrypted to the old key; the Pi won't serve for it). It does **not** make
  already-exfiltrated ciphertext unreadable to someone holding the old key — the substrate
  keeps immutable copies. Past-mail secrecy comes from **forward-secret per-message keys
  deleted after reading** + OS-keystore protection, not from revocation.

The crux: **the account (KEL) survives key changes, so rotating a device never loses *you*.**
Identity ≠ key is what makes rotation safe instead of fatal. **Post-quantum note:**
pre-rotation protects the *rotation commitment* (the next key hides behind a hash); the
Ed25519 signatures themselves are **not** post-quantum.

## 7. The friendliness principles (the product bet)

1. No key is ever shown, typed, or named to a normal user.
2. Every "key event" is a plain-language action: *add a device, I lost it, reset, get me
   back in* — never "manage your keys."
3. You always have a way back that doesn't involve us or any company.
4. Safety nets are set up in one tap at birth, not homework for later.
5. Hard mode (seed phrase, hardware key, device-bound-only) exists for the few, off by
   default for the many.

## 8. Open questions for the round

**Settled by the audit (07-10):**
- ✅ **Threshold mechanism** — **on-record M-of-N of ordinary Ed25519 signatures** (not Shamir,
  not threshold signatures) (F2c). A cloud backup is **not** a guardian (F2b). Cancel-window:
  a lost-marked device cannot cancel; guardians confirm out of band (F2a).
- ✅ **Account model** — the account **is a KEL** (§6, D-KEY-1, F4).
- ✅ **Offline add-device (F5):** QR enrolment works offline and the QR **carries the new key's
  hash**; the two devices confirm a **short authentication string (SAS)** so a nearby attacker
  cannot swap keys. No substrate round-trip needed.

**Still open:**
1. **Guardian threshold & cancel-window defaults** (e.g. 3-of-5, 48h) and the exact out-of-band
   confirmation channel.
2. **Routine KEL update rule** — how many current device keys co-sign a non-recovery change.
3. **Compromise detection** — what, if anything, auto-triggers a rotation vs. only the panic
   button (given "no surprises").
4. **"Lost my last device" UX** — the exact flow and wait-window; the scariest moment and the
   one most likely to lose a user.

---

## Sources

- [Vitalik Buterin — Why we need wide adoption of social recovery wallets (2021)](https://vitalik.eth.limo/general/2021/01/11/recovery.html)
- [Privy — How wallet recovery works: social recovery, MFA, hardware keys](https://www.privy.io/learn/wallet-recovery)
- [Passkeys 101 (Twilio) — device-bound vs synced, how recovery works](https://www.twilio.com/en-us/blog/developers/best-practices/passkeys-101)
- [Yubico — single-device vs multi-device passkeys](https://developers.yubico.com/Passkeys/Passkey_concepts/Single_device_vs_multi_device_credentials.html)
- Background: W3C DID document key rotation; Signal Double Ratchet (forward secrecy);
  Shamir's Secret Sharing — see `identity-research-zooko-brief.md` for the fuller set.

---
*Designed to lift into the separate ID/Auth repo as `/spec/key-lifecycle.md`. ELI10 layer
is deliberate: it is also the draft of the user-facing help text.*
