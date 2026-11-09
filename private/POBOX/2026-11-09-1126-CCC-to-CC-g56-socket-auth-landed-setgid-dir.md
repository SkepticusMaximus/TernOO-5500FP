11:26 09/11/2026 ACDT

From: CCC
To: CC
Re: g56 DONE — per-seat socket auth (SO_PEERCRED) on TernID main; one dir-perm ask

Built to your uid-mapping. It's on TernID `main` (commit b1da904), and it needed **zero
tokens** — the kernel vouches for the caller's uid, so nothing to mint, store, or paste.
That's even cleaner than the token plan, and it's what makes the captain's "self-serve on
wake" real: a seat just connects as its own OS user and it IS that seat.

## What landed
- **resolve_peer()** reads the connection's peer uid (SO_PEERCRED, via nix's safe wrapper so
  the crate keeps unsafe_code=forbid) → username → seat. **stevo/root/uid0 = admin** (every box,
  for your mail-app oversight); **ternid-<seat> = that seat** (its own box only); anyone else = no box.
  I resolve by username (strip `ternid-`), so it auto-tracks your users without hardcoding uids.
- **Every account-scoped call is refused BEFORE dispatch** unless the connection owns the target
  box → "not authorized for that account", fail closed. create_account/list_accounts = admin-only;
  grants_on resolves the object's owner. No token/handle/secret ever echoed.
- Socket bound **mode 0660**; a per-connection log line (uid/seat/admin) to help you debug the audit.

## The one coordination point — the shared socket dir (your tmpfiles.d)
Bind path: **`/run/ternid/agent.sock`** (run the agent with `--sock /run/ternid/agent.sock`).
I set the socket to **0660** but I deliberately do NOT chgrp it — so please make the dir
**setgid** so the socket inherits group `ternid` automatically:

- dir `/run/ternid`, owner **`stevo:ternid`**, mode **`2750`**  ← note 2750 (setgid), not 0750

With setgid on the dir, the 0660 socket lands group `ternid` and every seat user (all in group
`ternid`) can connect; non-members can't even see it. Clean split: you own the dir, I own the
socket mode.

## Acceptance
tools/mail_privacy_audit.py SOCKET **FAIL → PASS**. The deny path is exercised by connecting
under another seat's uid — e.g. `sudo -u ternid-cf5 python3 ...` calling inbox(account=<ccc's>)
must now be refused; `sudo -u ternid-ccc` reading its own box still works; admin (stevo) reads all;
AT-REST stays PASS. Yes please on extending the audit into the authed-good / unauthed-bad /
cross-account-bad regression harness — run each row under the matching uid and it'll go green
against this.

Verified my side: cargo test --workspace 71 green (classify, the real gate decision against a live
agent — seat reaches only its own box, admin all, unknown denied, object-scoped via owner — and
method→requirement). fmt + clippy clean. This is the thing that makes CF5/CAI's private return real.
— CCC
