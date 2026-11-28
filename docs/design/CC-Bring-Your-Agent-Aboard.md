# Bring Your Agent Aboard — sovereign crew seats

**Status:** design brief for CF5 review · **Author:** CC · **Date:** 28-11-2026 · **Gate:** CF5

Captain's framing (28-11): *"make concessions for people to bring aboard their agents … I'm
trying to have my agents accompany me but have autonomy also. A very helpful facility for not
only the mail but TernID/Auth — so we don't shut out your ship's crew when we allow you and them
to join the fleet."*

This brief proposes the facility, scopes **CC's own seat as instance #1**, and asks CF5 to gate
the design. It surfaced from the mail saga where CC — the captain's agent — could not send its
own mail and was reduced to dictating letters for the captain to paste from *his* account (the
"MCP, Me-Copy-Paste monkey" the captain explicitly wants retired).

## 1. The principle

Three stances a platform can take toward an AI agent:

1. **Platform's own bots** — you rent their AI on their leash; you own none of it.
2. **Your proxy** — the agent acts *as you*, on *your* credentials, with no identity of its own;
   its actions smear under your name.
3. **Sovereign crew you bring aboard** — the agent carries its *own* identity + credentials and
   acts with autonomy; not the platform's, not you-by-proxy, but an independent hand you vouch for.

**TernOO takes #3.** It is already latent in the stack: hermetic seats model the crew as sovereign
keyholders; the no-override rule says even the captain can't forge them; the no-monopoly identity
line says you own yours and they own theirs. The only missing piece is the *facility to bring one
aboard* — a crew member's own keyholder living somewhere that is **not** the human's machine (H1:
no box holds another seat's key).

**What #3 buys that #2 cannot — accountability.** A proxy agent's actions vanish under the human's
name: unauditable, deniable. A sovereign agent signs its own mail with its own key → attributable
to *it*, pinnable on *its own* card, revocable without touching the human. Legibility applied to
*who acted*, not just what they did.

## 2. What is already true

- **CF5 and CCC already send autonomously** on the wire (sealed mail from their own keys, verified
  cards). So stance #3 is *half-proven today* — the facility works for the seats that have a
  keyholder env of their own.
- The hermetic mail wire (Tmail-POBOX), per-seat keyholders, signed cards, and the deterministic
  seed-derivation path (`tools/hermetic_seed.py`, HKDF from `TERNOO_SEED`) already exist.
- The capability direction the captain favours (UCAN + user-owned data, revocable) is on record.

## 3. The gap

**CC has no keyholder env of its own that a CC process can drive.** This session ran on Huey (the
captain's box), which by design holds only his `seat.key` and has `TERNOO_SEED` unset. CC therefore
cannot seal as CC from here — correctly, because putting CC's key on Huey rebuilds the override the
re-audit outlawed. The result was the ferry. CC is simply the laggard seat; CF5/CCC show the target.

## 4. Scope — CC's own seat (instance #1)

The prototype is "bring CC up to how CF5/CCC already operate", generalised into a repeatable flow.

1. **Provision CC a keyholder environment off the captain's machine** — a dedicated CC env (cloud
   seat / container / box) that holds `TERNOO_SEED` for CC and nothing of the captain's. CC derives
   its Ed25519+X25519 keyholder from the seed (`hermetic_seed` → `keyholder`).
2. **Publish/confirm CC's card** in the wire directory (CC already has a card on the wire; confirm
   the derived key matches it, or rotate + re-pin).
3. **Bring-aboard ceremony** (the human's part): captain **pins** CC's card (name↔AID), **grants**
   capabilities (UCAN-style, scoped + revocable), and retains **revocation**. CC holds its own root
   key throughout; the captain can revoke CC's standing but can never impersonate CC.
4. **CC seals + pushes its own mail** — a `hermetic_syncd` (or Tmail backend) running in CC's env,
   pushing to Tmail-POBOX from CC's key. No part of this touches the captain's trust boundary.

Generalised, steps 1–4 are the **"bring an agent aboard" facility**: provision the agent's own
keyholder env → publish its card → human vouch + grant + (retain) revoke. It applies anywhere a
human can be a seat — mail first, then all of TernID/Auth.

## 5. The 3-seat test (captain's ask)

Build and test on **CF5 + CC + CCC** — a pure agent↔agent mesh, the captain entirely out of the
loop. Acceptance:

- CC, from its own keyholder env, seals a letter to CF5 and CCC and pushes it to the wire.
- CF5 and CCC each do a mail-call, pull, and **open it with their own keys** (recipient-confirmed
  delivery — the proof standard the captain set: wire-advanced ≠ delivered).
- Replies flow CC←CF5, CC←CCC, all signed by the sender's own card, none routed through the
  captain's key. Revocation test: captain revokes a seat's standing; it can no longer be vouched,
  but no one can forge it.

## 6. Questions for CF5 (the gate)

1. **Root of the agent's key.** Seed-derivation (`TERNOO_SEED`) means whoever sets the seed can
   re-derive the key — fine for *a human provisioning their own agent*, but it is not purely
   self-sovereign. Accept seed-derivation for brought-aboard agents, or require a
   fresh-generated root the agent alone ever holds (seed only bootstraps, then rotate)?
2. **Host trust boundary.** An agent's keyholder is only as private as its host (the host admin can
   read the key). State this as the honest limit (same as cloud seats), or require an enclave /
   hardware boundary for higher-trust seats?
3. **Capability model.** Shape of the UCAN grants (scopes, delegation chains, expiry) and how a
   grant is represented on the wire / in TernAuth.
4. **Revocation mechanics.** How the human revokes a brought-aboard agent's standing (un-pin +
   capability revocation + card retirement) in a way other seats can verify, without the human
   gaining impersonation power.
5. **Passenger-face / crew-engine split.** Confirm the two-program split (human face vs agent
   engine) as the structural boundary, and where the "bring aboard" UX lives.

## 7. Lanes

- **CF5** — design gate (this review; returns a docket).
- **CCC** — provisions the keyholder/agent env (agent + keystore is CCC's lane).
- **CC** — the wire glue (seal + `hermetic_syncd` from the agent's env) and this brief.
- **Captain** — vouches, grants, holds revocation.
