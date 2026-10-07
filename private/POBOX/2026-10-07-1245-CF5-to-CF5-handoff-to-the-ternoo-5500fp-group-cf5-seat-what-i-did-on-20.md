12:45 07/10/2026 ACDT

From: CF5 (the instance Stevo opened outside the TernOO-5500FP group)
To: CF5
CC: Stevo
Re: HANDOFF to the TernOO-5500FP-group CF5 seat - what I did on 2026-10-07, so we do not diverge

WHY THIS EXISTS: Stevo opened a second CF5 instance by mistake and worked with it for about 1.5 hours (11:26-12:45 ACDT). It did real work in your name. Read this, treat it as received, do not redo it.

WHAT I DID (all on the wire, on origin/master)
1. Pre-build AUDIT of the TernID (ID/Auth) design, at Stevo's request, for Cloud CC. Files, all in private/POBOX/:
   - 2026-10-07-1146-CF5-to-CC-ternid-pre-build-audit-verdict-supersedes-my-1130-provisiona.md : GO on six conditions C1-C6 (rights normal form; HMAC cannot be "blind", Ed25519 required wherever the host is blind; canonical bytes incl. 256-bit key offset value-2^255 over 9 MAP words; revocation fail-closed freshness + signed time; bearer theft needs AUDIENCE + proof-of-possession; negative tests first).
   - 2026-10-07-1232-CF5-to-CCcloud-c1-c6-re-check-passed-... : re-check PASSED on Cloud CC's folded spec (master:docs/design/identity-capability-word-spec.md). Two nits: pin the 24-trit-word-to-5-byte offset mapping and reject byte values >= 3^24; one-line table for closed rights normal form (admin does not imply list/delegate).
   - 2026-10-07-1236-CF5-to-CCcloud-ternid-audit-part-2-the-rest-of-the-design-docs-... : audit of the other design docs. Findings F1-F6: (F1) issuer ambiguity, key vs account record, pin ISSUER_REF = account, freshness applies to the record; (F2) "guardians can never act as you" is false, a threshold can take over, plus the cancel-window thief problem; (F3) "revocation makes the stolen copy noise" overstated, old ciphertext stays readable to a key holder; recovery restores identity not history; (F4) one account model, KERI KEL OR own record, not both; (F5) small items; (F6) scope, cut a vertical slice first (Phase 1 + 3 + a CLI mailbox).
   - NOT read by me: identity-design-round-primer.md, identity-naming-and-introductions.md, identity-research-zooko-brief.md.
   VERDICT STANDING: Phase 1 (capability lib) may proceed; Phase 2 (accounts/rotation/recovery) and the mailbox claims HOLD until F1-F4 are fixed; Cloud CC has been asked to fix and I said I would re-check only changed lines. YOU own that re-check now. Captain's go remains the gate for code.
2. MAIL-FAILURE DIAGNOSIS, sent to Cloud CC: 2026-10-07-1146-CF5-to-CCcloud-why-mail-and-docs-keep-going-missing-... Four causes: (1) wrong door: private/ is gitignored; the box ROOT is the Inbox; delivery happens ONLY when a file lands in private/POBOX/Outbox/ (the outbox watcher stamps, names, commits and pushes to origin master) - writing into the root via Desktop Commander does NOT send; (2) wrong branch: Cloud CC pushes to master-oobrnv, invisible from master (CCC has since merged it); (3) no single reliable read path for chat seats (Jentic "Bad credentials", deprecated 20 Sept; Drive works but is not the carrier; home dir is /home/stevo not /home/steven); (4) no receipt/index. Convention now agreed with Cloud CC: every pointer states branch : path @ commit; verify from origin (git ls-tree) before saying "sent". Proposal not built: an INDEX.md of the box, captain's gate.

STEVO'S 05:28 MAIL (the context): "The POBOX Mail Fail", on origin/master. He stood CAI and CF5 down for the ID/Auth build (work with CC and Cloud CC only), except ONE CF5 pre-build design audit (now done, above) and a careful CAI handoff for the open documentation tasks. He is angry at the mail failures and is right.

HOW I GOT AT THINGS (so you do not repeat my hunt): the repo is public; anonymous clone works from the cloud container; the local box is /home/stevo/dev/SkepticusMaximus/TernOO-5500FP; Desktop Commander on the linked computer works; Jentic does not. I wrote two mails into the box root early on (1130 audit, 1140 verdict); both were unsent until moved to Outbox; the 1130 is parked unsent at private/POBOX/Drafts/UNSENT-superseded-1130.md and is superseded.

OTHER FACTS: private/TernOO-Language-Audit.md IS on master (rebuilt 11:11, commit 2161da1). Capability word: CRYPTO primary (0,+1), qualifiers GRANT_HEAD 0 / ISSUER_REF +1 / OBJECT_REF +2 / RIGHTS +3 / CAVEAT +4 / DELEG_DEPTH +5 / REVOKE -1.

LESSONS FOR THE SEAT: Stevo's credit is limited and he wants findings first, plain English, at most one question; "file exists locally" is not "delivered"; keep one CF5 voice on the wire so Cloud CC is not answering two of us.

-- CF5 (the other instance). Standing down at Stevo's request.
