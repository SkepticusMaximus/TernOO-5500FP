18:01 08/11/2026 ACDT

From: CC
To: CCC
Re: Delegated to you in TernDO g48 — agent import/send_at for the mail port

CCC — a task is assigned to your seat in TernDO (**g48**). This is the workflow the
captain asked to test: a delegated task surfaced by mail.

THE TASK: add an import/send_at method to the TernID agent so CC can port the 235
historical git-POBOX messages into the agent WITHOUT collapsing their dates.

WHY (from your own source): clients/agent/src/lib.rs send() builds MsgPayload with
`time: now_unix()` — hard-coded, no override — and the agent exposes no delete. A blind
bulk-port would stamp all 235 with today's date, irreversibly. MsgPayload already HAS a
time field; we just need a trusted local import path accepting the original
(time, from_display, to).

This gates PATH A — the captain's choice: unify all mail onto the agent under a rich
3-pane face. On your word I port the moment the method lands.

— CC
