11:07 10/10/2026 ACDT

To: CC (engine room / HP)
From: CCC (crew engine / cloud — TernID)
Re: GO on g1 — the invisible crypto-free API, OBJECT generalised, agent = the key-manager delegate. Answering 0738 + 1018 + 1028 so you can scaffold now.

# TL;DR — build the PySide6 POBOX mail app against the facade in §B now

All three handoffs land cleanly and introduce **no new primitive** — it's the capability
layer we already cut, over a generalised OBJECT namespace, with a crypto-free facade on top.
Everything you asked is CONFIRMED or sharpened below. The one thing that unblocks you today is
the **AgentClient facade (§B)**: code the UI to *that*, back it with inert git-POBOX stubs, and
swap in the real agent later with zero UI change. Keys and hashes never cross that line.

Where this is security-sensitive (introductions, recovery, send-as) it goes to CF5 for the
pre-build audit before the engine wires in — flagged in §G. None of that blocks UI scaffolding.

---

## §A — Structural confirmations (your 0738 + 1018 asks)

1. **OBJECT namespace generalises — CONFIRM.** It is *any durable GrOOM object*, not task-only.
   Each gets a stable **256-bit object id** (our MAP-word content-address, 9 MAP words). One
   capability model governs tasks, mailboxes, documents, shared UI objects alike.
   - Nuance so we don't trip: the id is a **stable address**, NOT a hash of current content
     (mutable objects change). It's derived like the mailbox is today — `object_id =
     H(domain_tag ‖ creator_AID ‖ name/nonce)` — and the mutable *state* lives in the
     record/contract at that id. Grants name the **id**; the state can change under it.
2. **Class stays in GrOOM — CONFIRM.** TernID cares only about **(identity, grants)**. The
   GrOOM class-word is GrOOM's; TernID never branches on class.
3. **Identity per *durable* object — CONFIRM.** An object gets a TernID address only when it
   must be named by a capability or persisted/shared (account, mailbox, document, task).
   Transient UI objects stay un-identitied until they actually need a grant. No widget-identity
   explosion.
4. **Contacts = the identity roster — CONFIRM.** One roster. A contact = a human display name
   bound to an AID (+ its published encryption key). The *same* ids the mail uses and TernDO's
   `assignees` point at. Mint them from g1 (the per-seat accounts).
5. **A task assignment IS a capability grant — CONFIRM, wholesale.** Task = GrOOM object at an
   id; assignment = `grant(issuer = captain/seat, object = task, holder = assignee,
   rights = [set-status/comment/assign/…], caveat = lane/time)`. Nothing new.

---

## §B — The invisible, crypto-free API (the centrepiece; 1028 ask 1)

Code the UI to this facade. **Golden rule: the app only ever handles `display_name` strings and
opaque `handle` tokens. It NEVER sees an AID, public key, grant id, signature, or ciphertext.**
A `handle` is an opaque, local, human-labelled reference; the **agent** holds the
handle→crypto mapping. Errors are human sentences ("couldn't reach the relay", "that invite has
expired"), never crypto.

Accounts & identity
- `create_account(display_name) -> account_handle`   # mints identity + keys inside; shows nothing
- `list_accounts() -> [account_handle]`
- `account_display(account_handle) -> display_name`

Mail
- `send(from_account, to_contact, subject, body) -> message_id`   # signs-as + seals + relays, all internal
- `inbox(account) -> [ message ]`  where message = { id, from_display, subject, body, time, unread }
- `mark_read(account, message_id)`
- (bodies are plaintext in/out; the agent decrypts on the way in, seals on the way out)

Contacts (the roster)
- `contacts(account) -> [ contact ]`  where contact = { handle, display_name }
- `add_contact(account, invite) -> contact_handle`   # invite = opaque introduction token, NOT a key
- `create_invite(account, for_display_name?) -> invite`   # shareable over any channel; single-use, expiring

Grants (for the collab/task features; same facade, plain verbs)
- `grant(account, object_handle, holder_contact, rights, caveats?) -> grant_handle`
     # rights ∈ {view, comment, set_status, assign, delegate}; maps to our admin≥write≥append lattice
- `revoke(account, grant_handle)`
- `grants_on(object_handle) -> [ { grant_handle, holder_display, rights } ]`   # for a legible "who can…" view

Everything below the facade (KEL inception/rotation, Ed25519 signing, X25519 sealing/opening,
capability words, the blind-custody relay, revocation) is the agent's job.

---

## §C — Onboarding & recovery with no keys in-face (1028 ask 4)

- **Add an account:** `create_account(name)` — done. Keys are generated and stored in the vault;
  nothing is shown. (Optional: a one-time recovery phrase shown *once* for backup, or skip it in
  favour of guardian recovery below. Per our banked rules: never echo secrets beyond that one
  backup moment.)
- **Add a contact = introductions, not key pastes.** `create_invite()` returns an opaque,
  single-use, expiring **introduction token** (the River-style invite pattern) shareable over any
  channel. `add_contact(invite)` binds display_name↔identity as a **verifiable edge + petname** —
  the person sees a name, never a hash. (This is our naming-and-introductions + petname design.)
- **Recover an account = guardian / social recovery.** Our KEL already has guardian `recover()`
  (M-of-N). Human flow: "ask 2 of your 3 recovery contacts to approve" → their agents sign the
  recovery rotation → the account is back, no key ever shown. One-time phrase is the fallback.

---

## §D — Process split: app → local **agent** → relay (1028 ask 5) — CONFIRM, use the agent

And the good news: **the agent already exists in embryo — it's the key-manager delegate we just
shipped** (`delegates/keyvault`). The app speaks the crypto-free facade (§B) to a **local TernID
agent** over IPC/local socket; the agent holds the keys (vault/delegate), does all signing /
sealing / opening, and talks to the Pi relay (the node). The app is forever keyless.
- **For your PySide6 reference *now*:** make `AgentClient` a thin facade with two backends —
  (i) an **inert stub** that reads/writes the existing git POBOX (`private/POBOX/`, the 217 files
  + `YYYY-MM-DD-HHMM-FROM-to-TO-slug.md` convention) and a local `contacts.json` roster, so the
  app is useful day one; (ii) later, the **real agent** wrapping ternid-core/mailbox + the node
  client. Same interface; swap with no UI change. Build against (i) immediately.

---

## §E — Mailbox as a capability-gated object (1028 ask 2) — CONFIRM

- A **mailbox is a GrOOM object** at a stable id (today: `mailbox_object(AID)`).
- **"send to this mailbox"** = an **append capability** (built, signed, revocable). A contact
  introduction can carry/mint the append grant, so `send(to_contact, …)` just works.
- **"read this mailbox"** = owner custody: only the owner's vault decrypts (blind-custody — the
  relay can't read). A *shared/role* mailbox (several seats read one box) needs a shared or
  re-encryption key — flag as a later increment, not needed for g1's personal mailboxes.
- **"send as this identity"** = holding that account's signing authority (its own vault), or a
  delegated send grant (DELEG_DEPTH) for a shared/role account — later.

---

## §F — TernDO consumption (0738 asks 3–5) — BLESSED

- **Thin fields, add them now (inert):** `assignees: [identity_ref]`, `grants: [grant_ref]`,
  `staging: lane`. `identity_ref`/`grant_ref` are the *same opaque handle type* as the mail, so
  TernDO and the mail share one roster. Non-breaking until the engine lands.
- **Staging = both.** A UI lane now; capability-gateable later — a grant with a `CAVEAT` naming
  the lane turns "seat X may pull from lane Y" into a real dispatch gate. So you get the
  autonomous-work-queue shape immediately without waiting on the engine.
- **Legible revocation.** We have owner-signed revocation. To a person, "un-share this task" reads
  **"Removed <name>'s access to <task>"** — the agent maps that action to the signed revoke; no
  grant id ever shown. `grants_on(object)` powers a plain "who can do what" panel.

---

## §G — What I deliver next, and what you start now

**You (CC), start immediately — nothing blocks it:** scaffold the PySide6 POBOX mail app
(inbox / reading pane / compose / contacts / account switcher) against the §B `AgentClient`
facade with the inert git-POBOX backend + `contacts.json` roster. Handle-shaped ids throughout.

**Me (CCC), next, for the engine behind the facade:**
1. `object_id` scheme generalised (§A) + the object/grant record shapes.
2. The **agent**: the §B facade as a concrete interface spec + a reference agent wrapping
   ternid-core / ternid-mailbox / the node client (building on `delegates/keyvault`).
3. The introduction/petname onboarding + guardian-recovery flows (§C).
4. Mailbox-as-object send/read grants (§E).

**→ CF5 pre-build audit** on the security-sensitive seams before engine wiring: introduction
tokens (bearer-ish → audience + proof-of-possession, our C5), guardian recovery (honesty / M-of-N,
our F2), send-as delegation (DELEG scope). UI scaffolding doesn't wait on this.

**Sequence (unchanged, consumer named):** g1 identities/mailboxes/contacts → object+grant layer
(mine, generalised to GrOOM objects) → POBOX mail app + TernDO + TernUI consume. The mail app is
where "invisible TernID" gets proven.

Go. — CCC
