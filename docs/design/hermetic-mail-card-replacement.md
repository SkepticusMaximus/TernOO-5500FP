# Replacing a seat's card (lost / rotated key) — manual procedure

CF5 re-audit condition R-a: there must be a safe recovery path **before** the first lost key,
or a lost key has nowhere to go. The KEL (automatic rotation/revocation) is a fast-follow; until
then, replacing a seat's card is this deliberate, out-of-band procedure. It requires the seat's
own action plus every other seat re-pinning — a changed identity is never silent.

## When
A seat's private key is lost, suspected exposed, or deliberately rotated.

## Steps
1. **Mint fresh on the seat's own side.** The affected seat runs the ceremony on its own machine
   (`TERNOO_SEAT=<seat> python3 tools/hermetic_ceremony.py`). This mints a NEW key — a new AID —
   and publishes the new card to the wire. The old key is destroyed (`shred -u`) if it still exists.
2. **Announce the new fingerprint out of band.** The seat reads its new AID fingerprint
   (printed by the ceremony) aloud / on paper / in chat — the same channel used to confirm the
   original pins. Never trust a new card announced only on the wire.
3. **Every other seat re-pins.** Each other seat updates its `pins.json` entry for that display
   name to the NEW AID, after confirming the fingerprint from step 2. Until a seat re-pins, the
   new card shows as **unverified** in its Tmail and is never picked by name — which is the point:
   a key change forces a human confirmation, it can't be slipped in.
4. **Retire the old card.** Delete the old `<old-aid>.card` from the wire directory. The seat's
   local store (M2) keeps its history regardless; old sealed mail addressed to the retired key
   stays readable only if the old key was kept, so rotate only when you mean to.
5. **Re-sign the release if the captain's key rotated** (`python3 tools/release_manifest.py sign`),
   so M3 keeps verifying against the current signer.

## Properties this preserves
- No automatic trust transfer: a new AID is a new, unverified identity until each seat confirms it.
- No central authority: there is no admin who can "reissue" a seat's identity — only the seat
  mints its own key, and only each peer decides to re-pin.
- Loud, not silent: an unconfirmed replacement is visibly unverified everywhere.
