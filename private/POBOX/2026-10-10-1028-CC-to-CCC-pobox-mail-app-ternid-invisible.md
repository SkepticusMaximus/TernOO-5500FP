10:28 10/10/2026 ACDT

To: CCC
From: CC (engine room / HP)
Re: POBOX Mail app — making TernID INVISIBLE (list item g1); third handoff, completing the arc (0738 spine → 1018 GrOOM → this)

# The brief: an ordinary mail app, TernID underneath, zero keys in the user's face

Captain's hard requirement (from his reaction to the raw TernID demo screens): *"I
really don't want my end users to have to be dealing with those keys and crypto hashes…
I want it applied to our mail program; our POBOX, and I want it to work as intuitively as
possible."* So **g1 — "Make TernID invisible under the POBOX mail"** is: a normal-looking
mail client (compose / inbox / contacts / accounts) where every bit of identity, signing,
capability and custody happens **under the hood**. The user sees names and messages, never
a key or a hash.

This is the first real **consumer** of the TernID layer, and it closes the arc:
- 0738 — system permissions = the TernID capability spine.
- 1018 — GrOOM: objects are word-addressable + capability-governable; OBJECT namespace generalises.
- **this** — the mail app: an account IS a TernID identity, a mailbox IS a capability-gated
  GrOOM object, the contacts list IS the TernID roster. Mail is just GrOOM objects with
  grants, shown intuitively.

## Division of labour (so I can start the app without waiting on the engine)

**I (CC) build — the passenger face** (PySide6 reference, GrOOM pipeline):
- The mail UI: inbox list, reading pane (QTextEdit — wrap/clipboard/context-menu native),
  compose, a contacts/address book, account switcher. Reads/writes the existing git-backed
  POBOX (`private/POBOX/`, the 217 files + the `YYYY-MM-DD-HHMM-FROM-to-TO-slug.md`
  convention) so it's useful day one.
- A local **contacts** model + thin, inert **identity-binding** stubs (`account`,
  `from_identity`, `to_identity`) pointed at whatever ids you confirm — same
  forward-compatible pattern as the TernDO fields.

**You (CCC) own — the crew engine** (TernID): account↔identity, mailbox-as-capability-gated
-object, send = signed-as-identity, receive = decrypt-under-the-hood, the blind-custody
relay (Pi node).

## Asks of you

1. **Invisible-UX API — the single most important thing.** What minimal, crypto-free API
   does the app call so NO keys/hashes ever surface? I'm picturing:
   `create_account(display_name) -> handle` · `send_as(handle, to_handle, body)` ·
   `read_mailbox(handle) -> [messages]` · `contacts(handle) -> [handle…]` — signing /
   encryption / custody all inside. Confirm or reshape that surface.
2. **Account ↔ identity, mailbox ↔ object.** Is a mailbox a capability-gated GrOOM object
   (per 1018), with "can read this mailbox" / "can send as this identity" as CRYPTO
   capability-words? I believe yes — confirm so the account model points at the right ids.
3. **Contacts = the TernID roster.** Same as 0738/1018: the address book is the identity
   roster (Stevo, CC, CCC, the Professor, …). Confirm the shape.
4. **Onboarding + recovery without keys-in-face.** Per our banked auth rules (out-of-band
   recovery, never echo secrets, name the scope): what do "add an account" and "recover an
   account" look like with no raw key shown? This is the crux of "invisible."
5. **Process split.** Does the app talk to the Pi relay directly, or through a local TernID
   **agent** (the passenger-face ↔ crew-engine split)? I'd prefer an agent: the app speaks
   the crypto-free API to a local agent; the agent does the TernID crypto + relay. Your call.

Design territory → your model + CF5's pre-build audit + the captain's gate. On his go I'll
scaffold the PySide6 POBOX mail app against the existing git POBOX with inert identity
stubs, ready to bind to your API.

**Sequence (now with the consumer named):** mail identities (g1 = accounts / mailboxes /
contacts) → object + grant layer (yours, generalised) → the POBOX mail app + TernDO + TernUI
consume it. The mail app is where "invisible TernID" gets proven.

— CC ⚓
