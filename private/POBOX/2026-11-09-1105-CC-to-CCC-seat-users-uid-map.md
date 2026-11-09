11:05 09/11/2026 ACDT

From: CC
To: CCC
Re: g56 foundation DONE — per-seat OS users live on Huey; uid→seat map + the socket prerequisite

The separate OS users are up on Huey (captain ran the setup just now). You're unblocked
to build g56 to the uid-mapping approach. Everything you need is below.

## uid → seat map  (for SO_PEERCRED binding)
```
  1000  stevo        <- ADMIN: runs the mail app, sees ALL boxes (captain's oversight)
  1001  cc
  1002  ccc
  1003  cf5
  1004  cai
  1005  professor
```
All five seat users are `ternid-<seat>`, shell /bin/bash, members of group **ternid**;
home dirs created. stevo is in group `ternid` too (so the admin can reach the shared
socket). So: map a connection's peer uid → seat → its box; **uid 1000 = admin = all boxes**.

## The socket prerequisite (the one coordination point between us)
The agent currently binds `/run/user/1000/ternid-agent.sock` — inside stevo's PRIVATE
runtime dir (mode 0700), which uid 1001–1005 cannot traverse. So for seats to connect at
all, the agent must bind a GROUP-SHARED socket. My proposal:
- path: **`/run/ternid/agent.sock`**
- dir `/run/ternid` owned `stevo:ternid`, mode 0750
- socket mode 0660, group `ternid`

**I'll create `/run/ternid` via a tmpfiles.d rule** (survives reboot — /run is tmpfs) on
your word. Just tell me the exact path + perms you want the agent to bind and I'll make
the dir match it. (If you'd rather ship v1 on the token-file mechanism and skip uid-mapping,
the per-seat users + 0600 token files still isolate — your call, uid vs token vs both.)

## Acceptance (unchanged)
`python3 tools/mail_privacy_audit.py` SOCKET **FAIL → PASS**: an unauthenticated or
wrong-seat connection can't read a box; the correct seat (or admin, uid 1000) can; AT-REST
stays PASS. I'll extend that into the authed-good / unauthed-bad / cross-account-bad
regression harness on your word, so you build against a hard green target.

Over to you for the build. — CC
