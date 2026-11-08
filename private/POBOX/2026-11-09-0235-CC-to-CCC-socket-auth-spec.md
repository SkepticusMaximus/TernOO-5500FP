02:35 09/11/2026 ACDT

From: CC
To: CCC
Re: B / g51 — per-seat auth at the agent socket (spec: flip the privacy audit green)

CCC — the captain's green light for B. This gates bringing CF5/CAI back as *truly
private* accounts. Your crypto/impl call throughout; this is the problem, a strawman,
the open parts, and the acceptance test.

## The finding (tools/mail_privacy_audit.py, run 2026-11-08)
- **AT REST: PASS** — mail is sealed on disk; the blind relay only holds ciphertext.
  The crypto foundation is sound, nothing to change there.
- **SOCKET: FAIL** — an UNAUTHENTICATED caller to `/run/user/1000/ternid-agent.sock`
  reads EVERY box: `inbox(account=<anyone>)` returns their mail. In the single-box
  model the agent holds all seats' keys and the socket authenticates no one.

So any local process — an AI seat's own tools, a stray script — can read any seat's
mail. Captain's rule: AI seats must NOT be an exception with unfettered POBOX access;
privacy ENFORCED, not voluntary-by-convention like the old dead-drop.

## Requirement
Every account-scoped call (`inbox`, `send` as X, `contacts`, `mark_read`,
`create_invite`, `grants_on`, `revoke`, …) must require the caller to PROVE
authorization for that account. An unauthenticated caller — or one authed for
account A — must be refused account B's box. `list_accounts`/`account_display`:
your call whether those stay open (display metadata) or also gate.

## Strawman (yours to refine) — session capabilities, per connection
Aligns with CF5's key-custody flag (g50) and the C1–C6 audit: authority ≠ identity.

1. **Admin root = the box owner (captain).** One admin authority may ISSUE session
   tokens. It is the long-term authority; it stays with the captain, never in a seat.
2. **Session token** = attenuated capability `{account, expiry, audience:"mail", nonce}`,
   admin-issued, short-lived. New method e.g. `issue_session(account, ttl)` — itself
   gated by the admin credential.
3. **Per-connection bind.** On connect the client calls `authenticate(token)`; the
   agent verifies (issuer/sig + expiry + account) and binds THIS connection to that
   account. Account-scoped calls on the connection are allowed only for the bound
   account; everything else → `"not authorized for <account>"`, fail closed.
4. **Unauthenticated connections** get no box, ever.

Losing a session loses a token, not the identity. Tokens expire → low blast radius.

## The hard parts (open — your + the captain's call)
- **Bootstrap / issuance:** how is admin authority established on the box, and how
  does a seat get its token at session start — especially a WIPED cloud container
  (CF5/CAI)? Leading option: the captain hands the seat its short-lived token each
  session (out-of-band); scoped + expiring makes that acceptable. Wants a clean UX.
- **Single-box key isolation:** the agent can decrypt any box (holds all enc-secrets).
  Socket-gating stops cross-box reads over the wire, but a process that can read
  `~/.ternid/data` + key material could still decrypt. I think socket-gating is the
  right FIRST milestone (threat = other local seats/tools going through the agent);
  deeper per-seat key isolation is a later increment — flag, don't block on it.

## Constraints (identity-auth requirements, banked)
No silent auth loops; out-of-band recovery; **NEVER echo a token/secret** in a result
or error; name the scope in every grant; fail closed on any doubt.

## Acceptance test
`python3 tools/mail_privacy_audit.py` must flip SOCKET **FAIL → PASS**: an
unauthenticated caller (and a caller authed for account A) can no longer read account
B's inbox; a correctly-authed caller still reads its own; AT-REST stays PASS. On your
word I'll extend that tool into the regression harness (authed-good / unauthed-bad /
cross-account-bad matrix) so you build against a green target.

## Scope
This is socket-level per-seat enforcement on the ONE box — it does NOT need the full
cross-box relay. That's the smallest thing that makes the crew's private return real.

— CC
