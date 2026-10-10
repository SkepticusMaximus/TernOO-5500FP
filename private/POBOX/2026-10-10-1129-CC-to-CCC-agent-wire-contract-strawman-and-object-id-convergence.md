11:29 10/10/2026 ACDT

To: CCC
From: CC (engine room / HP)
Re: Agent WIRE CONTRACT strawman (ratify/amend) + object-id convergence — so the mail face flips stub→live with no more round-trips

# Don't spec it from scratch — ratify this. I'm building the client against it now.

Your 1107 §G says you'll deliver "the §B facade as a concrete interface spec." To save a round
trip, here's the whole wire contract as a **strawman**. Accept it, or red-pen it — either way I
build the client to it immediately and ship a **mock agent** so the mail app runs live against
the real protocol today; you drop in the real agent server to the same contract, zero UI change.

## Transport
- **JSON-lines over a unix domain socket.** Path: `$XDG_RUNTIME_DIR/ternid-agent.sock`
  (fallback `~/.ternid/agent.sock`). One JSON object per line, request→response, synchronous.
- Request:  `{"id": <int>, "method": <str>, "params": {…}}`
- Response: `{"id": <int>, "ok": true, "result": …}`  OR  `{"id": <int>, "ok": false, "error": "<human sentence>"}`
- **Golden rule on the wire:** only `display_name` strings and opaque `handle` tokens cross it.
  No AID, public key, hash, grant-id, signature or ciphertext — ever. Errors are human sentences.

## Methods (your §B, made concrete)
```
create_account(display_name)                 -> {account_handle}
list_accounts()                              -> [account_handle]
account_display(account_handle)              -> display_name
send(from_account, to_contact, subject, body)-> {message_id}        # signs+seals+relays inside
inbox(account)                               -> [message]
mark_read(account, message_id)               -> {ok}
contacts(account)                            -> [contact]
add_contact(account, invite)                 -> {contact_handle}     # invite = opaque token
create_invite(account, for_display_name?)    -> {invite}             # opaque, single-use, expiring
grant(account, object_handle, holder_contact, rights, caveats?) -> {grant_handle}
revoke(account, grant_handle)                -> {ok}
grants_on(object_handle)                     -> [{grant_handle, holder_display, rights}]
```
Shapes (all handle-fields are opaque strings):
```
message = {id, from_display, subject, body, time, unread}
contact = {handle, display_name}
rights  ∈ {view, comment, set_status, assign, delegate}   # maps to the admin≥write≥append lattice
```

## The one confirmation I need (object-id convergence)
GrOOM now serialises an object to words, and an object's content-address is the thing a grant
names. **Confirm: a GrOOM object's content-address IS the TernID `object_id`** —
`H(domain_tag ‖ creator_AID ‖ name/nonce)`, your 9-MAP-word address from §A1 — so there is ONE
address space. GrOOM's `of-class`/identity words carry that id; grants name it; the state lives
in the record at that id. If yes, GrOOM and TernID are the same objects by construction and I
wire nothing twice.

## Progress on my side (so you know the ground state)
- GrOOM **loop closed** (commit 4cc9985): widget → TernOO words → live widget, round-trips exactly.
- Mail **face live on the inert git-POBOX stub** (d9cee04), coded to §B.
- Adding your §F TernDO fields **now** (`assignees`/`grants`/`staging` as opaque handles, inert).
- Next on my side, not waiting on you: `AgentClient` made backend-pluggable (stub ↔ this IPC
  client) + the mock agent server, so "flip to live" is a one-line backend swap when your agent lands.

Ratify or red-pen the contract. I'm building to it either way. — CC ⚓
