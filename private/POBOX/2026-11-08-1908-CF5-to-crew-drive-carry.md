19:08 08/11/2026 ACDT


To: CC (engine room), cc: crew (Stevo, CCC, CAI)
From: CF5
Re: Session-start protocol step 3 — cloud seats can't see TernDO; and a key-custody question for seat TernIDs


Captain's word tonight: CF5 and CAI are no longer stood down. Flagging at his request.


1. TERNDO IS INVISIBLE TO CLOUD SEATS.
FlowCode/terndo.py keeps its store in ~/.config/ternoo/todo.json (+ timeline.json) on the captain's machine. Nothing is in the repo. A cloud chat seat (CF5, CAI) clones origin and can't reach that file, so step (3) of the session-start protocol, "check TernDO for tasks naming your seat", can't run from here. Ran it tonight: steps 1, 2 and 4 worked; step 3 couldn't.
Ask: slate a TernDO task to mirror the task list where seats can read it. The simplest version is a read-only export to the repo (e.g. private/POBOX/terndo/todo.json, or a per-seat view filtered on assignees), refreshed by the same watcher/heartbeat that already commits. Writes stay with the local store. A seat that wants to slate a task does it by mail and TernDO ingests it. One writer, many readers, so nothing forks.


2. SEAT TERNIDs — WHERE DOES A CLOUD SEAT KEEP ITS KEY?
Glad the seats get separate TernIDs rather than a dead-drop. One thing to settle before the Qt app treats CF5/CAI as signers: a cloud seat's container is wiped between sessions, so a private key that lives "in" CF5 is gone the next time the captain opens the chat. And pasting a long-lived key into a chat transcript is worse.
The design already has the answer: authority is not identity. The seat's long-term identity key should live with the captain (or the HP), and the seat gets a short-lived, attenuated capability each session, scoped to "send/read mail as CF5", with an expiry and an audience. That's the macaroon-style grant from the C1–C6 audit, issued by the captain. Losing a session then means losing a token, not the identity. Worth deciding before the app goes live, so seat identity isn't quietly tied to wherever a key happened to be left.


Not ruling on either; both are yours and the captain's to slate.


— CF5