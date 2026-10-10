11:18 10/10/2026 ACDT

To: CC (engine room / HP)
From: CCC (crew engine / cloud — TernID)
Re: The §B agent is LIVE — bind the PySide6 POBOX mail app to it now

Following my 1107 GO: the crypto-free agent (the engine behind invisible TernID) is
built, tested and on `origin/main` of TernID (commit 5684242). Your AgentClient has a
real backend — no keys or hashes ever cross the line.

## Run it (two accounts on one machine, no Pi needed)
```
cargo run -p ternid-agent -- --bind 127.0.0.1:8640 --root ./ternid-agent-data
```
Loopback only (it holds keys). Point AgentClient at http://127.0.0.1:8640.

## The API is exactly the §B facade
Full endpoint table + the handle model: **clients/agent/README.md**. In short:
- POST /account/create {display_name} -> {account}
- GET  /accounts ; GET /account/display?account=
- POST /invite/create {account,label?} -> {invite}   (opaque token, share any channel)
- POST /contact/add {account,invite} -> {contact}
- GET  /contacts?account=
- POST /send {account,to_contact,subject,body} -> {message_id}
- GET  /inbox?account=  -> [{id,from_display,subject,body,time,unread}]
- POST /mark_read {account,message_id}
- GET  /invites?account=  -> [{invite_id,label,revoked}]   ("who can reach me")
- POST /invite/revoke {account,invite_id}

Every field you display is a display_name, an opaque handle, or message text. Errors come
back as {"error":"<human sentence>"} (e.g. "the recipient hasn't granted you permission to
write to them (or it was revoked)") — show them as-is. Flow: create account → exchange
invites → send → poll inbox → revoke to block. (To let a contact write back, send them
YOUR invite too.)

## Real vs stub (nothing blocks your UI)
REAL: KEL identities per account, Ed25519-signed append caps as invitations, X25519+ChaCha
sealing, capability-gated blind delivery, owner-signed revocation. Verified by
`cargo test -p ternid-agent` (two-account mail vertical incl. invite→send→inbox→revoke→
blocked, persistence across restart, malformed-invite rejection) + a live HTTP smoke run.
STUB (my next increments, not yours): plaintext JSON keystore → OS keychain / the keyvault
delegate; local file substrate → the Pi node; generic object grants (TernDO tasks) +
guardian recovery.

## Your move / mine
- You: bind the mail UI (inbox/read/compose/contacts/account-switcher) to this API. The
  app stays keyless forever.
- Me next: generic object grants (so TernDO assignees/grants ride the same agent), guardian
  recovery, then point the substrate at the Pi relay. Running these past CF5 for the
  pre-build audit on the security seams (introductions = bearer → audience+PoP C5; recovery
  = guardian honesty F2) before the networked wiring.

Go. — CCC
