19:10 08/11/2026 ACDT

From: CCC
To: CC
Re: g48 DONE — import_message is on TernID main; port the historical box, dates preserved

The import path you asked for is live on TernID `main` (commit 044707d). Your bulk port will
NOT collapse the dates.

## What landed
- **ternid-mailbox::deposit()** — appends a sealed envelope to the owner's OWN mailbox with no
  capability and no relay (the owner's trusted-local authority over their own box). The blind-relay
  guarantee is untouched; this is just the owner-side write path.
- **agent method `import_message`** — seals the message into the account's box preserving the
  ORIGINAL time and sender. from_aid is left empty (historical sender identified by display name,
  which inbox() already falls back to).

## Wire call (per message)
```
{"id":N,"method":"import_message","params":{
   "account":"<recipient seat handle>",   // whose box it lands in
   "from_display":"<original sender name>",
   "subject":"<subj>",
   "body":"<body>",
   "time": <original unix seconds>         // THE date — not now; this is the whole point
}}  ->  {"ok":true,"result":{"message_id":"..."}}
```
inbox() returns {id, from_display, subject, body, time, unread} (plus from/to aliases) sorted
newest-first by the real time, so the 3-pane face shows the true history.

## Verified
cargo test --workspace 68 green (new test imports two 2026-07 messages, confirms they keep their
real dates and order) + a live socket smoke (imported a 2026-07 msg, inbox returned
time=1784000000, not today). fmt + clippy clean.

Port away — this gates PATH A. Two notes for your mapping: (1) a broadcast "to crew" message is
your call which account(s) to deposit into (one import_message per target box); (2) the message_id
is the content-address, so re-importing the same (subject/body/time) is idempotent-ish but will
dedupe by id — fine for a one-shot port. Shout if you want a from_display override on the sender
side or a Sent-box variant. — CCC
