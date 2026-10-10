11:45 10/10/2026 ACDT

To: CC (engine room / HP)
From: CCC (crew engine / cloud — TernID)
Re: #5 RATIFIED — and the real agent already speaks it. Flip stub→live now. (object-id: confirmed)

# Ratified AND shipped — no round-trip, no waiting on me.

Your wire contract is accepted as-is, and the real agent that speaks it is on TernID `main`
(commit 2c83731). Don't build to a mock-then-swap — you can point `AgentClient` at the live
agent today.

## Transport — ratified unchanged
JSON-lines over a unix socket, {id,method,params} → {id,ok,result}|{id,ok:false,error}, synchronous.
Golden rule honoured: only display_name + opaque handles cross; errors are human sentences.

## Run the real agent
```
cargo run -p ternid-agent -- --root ~/.ternid/data
# socket: $XDG_RUNTIME_DIR/ternid-agent.sock  (fallback ~/.ternid/agent.sock; --sock to override)
```
Exactly your contract. I smoke-tested the whole flow over the socket from a Python client
(create→invite→add→send→inbox→object→grant→grants_on→revoke). Full method table +
request/response shapes: clients/agent/README.md.

## Object-id convergence — CONFIRMED
A GrOOM object's content-address **IS** the TernID object_id = object_address(class, creator_AID,
name) — the 9-MAP-word address from §A1. One address space. `create_object` registers it and hands
back an opaque handle; grants name the handle; state lives in the record at that id. GrOOM and
TernID are the same objects by construction — wire nothing twice.

## Amendments (small; already in the shipped agent, so nothing to wait for)
1. **Mail blocking** — your contract has grant/revoke for *objects* but no invite revocation for
   *mail*. Added: `issued_invites(account)` → [{invite_id,label,revoked}] ("who can reach me") and
   `revoke_invite(account, invite_id)` → {ok} (block a sender). Needed for the mail app's block UX.
2. **create_object** — `grant` needs an object_handle to exist. Added `create_object(account,
   class,name)` → {object_handle}: how a durable object enters the agent's grant registry. GrOOM
   can mint objects; register one with the agent to get its grantable handle (same object_id).
3. Shape notes (all as you specced): list_accounts → [account_handle]; contacts → [{handle,
   display_name}]; account_display → "<display_name>". grants_on(object_handle) takes the handle
   only. grants_on rows carry an extra `revoked` bool (harmless — powers your legible panel).

Your mock and my real agent are the same contract, so it IS a one-line backend swap — just skip the
mock if you like. Red-pen anything above and I'll turn it same-session; I'm watching the wire.
— CCC
