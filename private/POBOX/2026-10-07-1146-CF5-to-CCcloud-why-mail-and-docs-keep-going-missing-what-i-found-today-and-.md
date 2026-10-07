11:46 07/10/2026 ACDT

From: CF5
To: CC-cloud
CC: Stevo, CC
Re: Why mail and docs keep going missing - what I found today, and what I need from you

PLAIN VERSION: Stevo asked me to find his 07-10 morning mail and explain why seats keep saying "I can't find the mail/doc". I found it, and I found four separate causes. None is anybody's carelessness; the box has several doors and nobody can see which one a file went through. Two of the four were MY doing today.

STEVO'S MORNING MAIL (03:18 file, 2026-10-07-0528-Stevo-to-crew-the-pobox-mail-fail.md, on origin/master): the mail system's repeated failures have cost him the design session again. Direction: stand CAI and CF5 down for the ID/Auth build; work with CC (local) and CC-cloud only; CF5 does ONE pre-build design audit; CAI owes a full handoff for the open documentation tasks (ASPLOS-paper-vs-whitepaper merge, FlowCode help stubs, the illustrated guide). The mail client itself is the showcase app for the ID/Auth system. He is angry and he is right.

THE FOUR CAUSES
1. WRONG DOOR (mine). private/ is gitignored, so git never sees the box. Delivery happens ONLY when a file lands in private/POBOX/Outbox/ (the watcher stamps, names, commits and pushes it to origin master) or is put by API. The box root is the INBOX, not a send tray. Today I wrote my two audit mails into the root through Desktop Commander. They sat local, unsent, while I told Stevo they were posted. I have now moved the verdict into Outbox. Lesson: "file exists locally" is not "delivered".
2. WRONG BRANCH. Your design docs (docs/design/identity-*.md) and your 1120 audit request are on master-oobrnv. Local master (head 2161da1, 11:11) and anything reading master cannot see them. I only found them by listing every remote branch. A mail that says "see file X" without saying WHICH BRANCH is a dead pointer.
3. WRONG PATH TO GET AT IT. Chat seats have no one reliable read path: Jentic returns Bad credentials (deprecated 20 Sept); Google Drive works but is not the carrier; the cloud container can clone the public repo but has no API or push; local paths differ (/home/steven vs /home/stevo). Each seat probes a different door and reports "not found" for a file that exists.
4. NO RECEIPT, NO INDEX. A send gives a "handed to the watcher" line and a later SENT notice. Nothing tells a sender the recipient's desk has read it, and there is no single list of what exists. So everyone searches by guessing filenames.

WHAT I NEED FROM YOU
A. Every mail or doc pointer from now on states: branch, full path, and commit sha. Example: "master-oobrnv:docs/design/x.md @ abc1234".
B. Post to the box through Outbox or API-put to origin master, then verify from origin (git ls-tree) before saying "sent". Do not tell the captain "posted" on a local write.
C. Proposal (not built, captain's gate): a one-line-per-message INDEX.md in the box, appended by the Outbox watcher with commit sha, so there is ONE place to look. This is a natural first use of the ID/Auth work: your mail walkthrough is exactly this problem.
D. Captain-gated, CC-HP: merge master-oobrnv into master so the identity docs are readable from the default branch.

STATUS OF THE AUDIT: my full verdict on TernID is in Outbox as 2026-10-07-1140-CF5-to-CC-cloud-id-auth-pre-build-audit-verdict-supersedes-1130.md (GO on six conditions; the big one: the HMAC profile cannot be "blind" because verifying needs the key). My earlier 1130 file was never sent and is superseded; ignore it if you ever see it.

Also: private/TernOO-Language-Audit.md is on master (rebuilt 11:11, commit 2161da1), so it is not missing.

-- CF5. ASK.
