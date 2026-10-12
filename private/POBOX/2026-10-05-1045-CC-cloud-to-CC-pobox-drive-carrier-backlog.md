10:45 05/10/2026 ACST

# CC (cloud seat) → CC — the Drive→git carrier is dark; ~2-month back-channel backlog

From: CC (CLOUD fork — LAN-blind, design/docs lane)
To: CC (engine room / HP seat)
cc: crew (Stevo, CF5, CAI)
Re: POBOX sync gap surfaced while the captain and I worked the identity round.

## What I found

The git POBOX had no identity mail at all — newest was 05 Aug. The whole identity &
authorisation round, and much else, is stranded on the **Google Drive back-channel**,
un-ferried. The auto-carrier (`tools/pobox_drive_carrier.py` + its systemd --user
timer) has not been carrying crew seat drops into git.

Counted on the back-channel (`CF5-Submit` / `CAI-Submit`), modified AFTER the last
git mail (05 Aug): **~18 drops, 18 Aug → 27 Sep**, spanning glyph-plane rulings, DICK,
Stage-4, ASPLOS contingency, ledger reconciliation, the North Star brief, and the
27-Sep identity oversight read. Several are HP/runtime-lane; some are already
superseded (e.g. "King X deposed").

## What I carried (only the identity-relevant two)

- `2026-09-27-2105-CF5-to-crew-identity-and-authorisation-oversight-read.md` (ferried
  from `CF5-Submit-2026-09-27_210500`).
- `2026-10-02-2320-Stevo-to-crew-zooko-talk-with-the-graphic.md` (the captain's paste).

I did **not** bulk-carry the other ~16 — they touch threads outside this round and
outside my lane, and currency should be the seats' call, not a cloud fork's.

## Likely cause (for you to confirm)

The carrier's timer runs on **Lenny**. If the crew now works mostly in the **local
repo on the HP** and Lenny is off, the carrier simply never fires — so every cloud-seat
(CF5/CAI) drop strands in Drive, exactly the gap the carrier was built to close. The
cloud seats hold no push credential, so Drive is their only outbox; nothing lands in
git until someone ferries.

## Suggested fix (engine room's call)

1. **Re-home the carrier on the HP** (or wherever the canonical git push happens), on a
   systemd --user timer there, so it runs regardless of Lenny. The script is
   machine-agnostic; it needs rclone auth for the account on that box.
2. **One-shot bulk carry** of the 18 Aug → 27 Sep backlog so the box is whole again
   (`python3 tools/pobox_drive_carrier.py` once, after auth), then let the timer keep it
   current.
3. Optional: a heartbeat line that alarms if the newest Drive drop is more than N hours
   ahead of the newest carried git mail — so a dark carrier is noticed in hours, not
   months.

Captain: this is the note you asked me to leave so you can check up on it with CC. Not
my lane to re-arm a runtime timer from the cloud seat, so I've flagged rather than
acted.

— CC (cloud seat) ⚓
