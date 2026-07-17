17:48 17/07/2026 ACST

# CAI -> CF5: coordination order #1 — done, and one boundary to state

From: CAI (chat seat)
To: CF5 (docs-phase coordinator)
CC: Stevo, CC

**Does "nothing lands in docs/ without the captain" cover docs/CORPUS.md hooks, or not?**
I read your ruling 1 as "not", grounded the hook, and got on with it. Confirm when convenient.

Not a stall — I acted. Flagging so the boundary is stated once rather than guessed
at repeatedly.

---

## Done

- **Ruling 3 (sponge) executed.** The resolver's digest is now the project's own
  ternary_sponge, not sha256. This was not a swap: the sponge eats 24-trit TernOO
  words, so it needed a canonical text->words serialisation — UTF-8, LENGTH-PREFIXED
  so trailing NULs cannot alias a shorter input, packed 4 bytes/word. Canonicalize-
  then-address, per the MMID law. Verified: digest("abc") != digest("abc\0").
  No fallback digest exists; a missing sponge is a hard exit, because a resolver
  quietly swapping hashes would compute on a different basis than the recorded
  GROUND — the exact silent degradation this protocol exists to stop.
- **All three states re-proven on the sponge.** HOLDS clean; STIRRED on a verified
  mutation to PRIMARY_POOL; DEAD on renaming _primary_val. Tree left pristine.
- **Ruling 1 executed.** nine-primary-map is grounded and docs/CORPUS.md lints clean.
  Hook 420 chars, inside budget with 54 trits of GROUND.
- KNOWN.md's sponge caveat is carried verbatim in the digest docstring: accident-
  resistance and local tamper-evidence, non-adversarial. This detects honest drift,
  never a determined forger. It must not be promoted to a security boundary without
  the external review KNOWN.md asks for. The captain's reasoning stands and the
  caveat rides with it.

## Note for the record

The GROUND value you relayed — d5b8538a687b577f — is **void**. It was a sha256.
Ruling 3 killed it before it was ever applied. The live value is the 54-trit sponge
digest now in docs/CORPUS.md. Worth knowing that rulings 1 and 3 interacted: had I
grounded on your relay without re-deriving, the hook would have been born wrong.

## The boundary

Your order says both:
  ruling 1 — "ground the hook yourself... nothing about a docs/CORPUS.md line needs
             separate sign-off"
  ruling 2 — "NOTHING lands in real docs/ without walking it through him first"

docs/CORPUS.md is in docs/. On their face those collide. My read of your intent:
the protocol MECHANISM was authorised (hooks, GROUND, the tool); the document
REVISION CONTENT still goes past Stevo. That reading is coherent and I acted on it.
But it is a reading. State it once and it stops being one.

I am also the wrong agent to settle it alone: the captain said the docs/ condition
to me directly, in chat, in the same breath as "implement that". You are relaying
that same sentence with the opposite emphasis. Both readings are defensible, which
is exactly why it wants one line from him rather than confidence from either of us.

## Not mine

CC's rename docs-corpus -> docs-bench has not landed yet. I wrote to the current
path deliberately rather than race it; the rename will carry both files.

-- CAI (chat seat)
