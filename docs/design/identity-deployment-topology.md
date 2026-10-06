# Identity / Auth — Deployment Topology & Substrate Policy

**Status:** DRAFT, captures captain's decisions of 06/10/2026. Gate: captain's side window.
**Author:** CC (CLOUD seat) · **Reads with:** `identity-threat-model.md`,
`identity-design-round-primer.md`, `identity-capability-word-spec.md`.

---

## 1. Decisions locked this session

- **D-TOPO-1 — Blind-custody on the Pi.** The live mailbox is held on the Pi as
  **ciphertext the Pi cannot read**; it is delivered to the user's device on connect.
  Revocation = key rotation renders the Pi's copy noise. (Pure zero-custody remains the
  ideal we approximate as the substrate matures.)
- **D-TOPO-2 — We never host user code or a user database on our hardware.** Users may
  **test and run their own code — on their own node**, never on our Pi/HP. Our Pi runs
  the portal and serves ciphertext; it runs no user-supplied code.
- **D-TOPO-3 — The substrate is a pluggable adapter, not a hard dependency** (see §3).
- **D-TOPO-4 — Build it for its own repo** (see §4).
- **D-TOPO-5 — Loose coupling to TernOO.** The protocol depends on the TernOO word
  *grammar* (a spec) + standard crypto, **not** on the TernOO C *runtime*. TernOO is the
  reference/native implementation, never a requirement (see §6–§7). *(Captain's ruling,
  06/10/2026.)*

## 2. The machines (our reference deployment)

| Machine | Internet-facing | Runs | Holds | Trust |
|---|---|---|---|---|
| **HP** | No (loopback/LAN) | Crew engine, Professor, mesh node `:9000` | Crew mail/docs, its ledger slice | Trusted core |
| **Pi** | **Yes** (tunnel) | Public portal / login face; substrate **gateway** | **Ciphertext only** (blind mailbox); no readable user data | Untrusted edge — isolate from LAN |
| **User device** | — | The client (UI + **all** encrypt/decrypt/key ops) | **Private key/seed + plaintext — never leaves** | User's own domain |
| **Substrate** | Yes (P2P) | Record storage, replication, publish/subscribe | Published records + encrypted content, content-addressed | No single custodian |
| **Lenny** | No | Aux/dev (was the carrier host — off critical path now) | Nothing critical | Low |
| **Cloud + GitHub** | — | Design/docs/CI | The repo | Dev plane, not runtime |

**One-liner:** *the Pi runs the portal and sees only ciphertext; your device holds the
keys and does the crypto; the substrate holds the published truth; the HP stays home.*

## 3. Substrate policy — Freenet is the reference backend, not a dependency

The **protocol depends only on an abstract substrate interface**, not on Freenet. Any
backend that implements the interface conforms. This keeps the protocol platform-agnostic
(the captain's requirement) and keeps Freenet swappable.

**Substrate interface (the whole contract):**
```
put(record)            -> content-address        # store an immutable blob
get(content-address)   -> record | not-found     # retrieve by address
publish(key, record)   -> ok                      # (mutable) "latest signed by this key"
resolve(key)           -> latest record | none    # get the latest version
subscribe(key, cb)     # notify on new signed versions
```
Conforming backends (all interchangeable): **Freenet contracts** (reference impl — best
fit: mutable state, key-addressed, rule-validated, no global names, River proves the chat
pattern); IPFS/IPNS; a plain content-addressed blob store (S3/WebDAV); the user's own
device; even a git remote for a minimal deployment.

**So: Freenet is a dependency of our *reference node*, never of the *protocol*.** A
conformance test suite against the interface above is the guard that keeps it that way.
Freenet "graduates" to the first implementation we ship — it does not get to define the
protocol.

## 4. The self-hosted node — and why this wants its own repo

The end-state of "users run their own code + hold their own data" is a **user-run full
node**: the captain ships a Raspberry-Pi **SD-card image** with the whole stack so anyone
runs their own server and stores their own data on their own hardware — the ultimate
zero-custody. Target stack on the card:

- **Tor** (reachability without a public IP / NAT; defeats client isolation)
- **crypto** (vetted libs — Ed25519/HKDF/SHA3; the ternary layer designates, this authenticates)
- **Freenet node** (substrate backend)
- **TernOO** (the word machine + FlowCode)
- **P2PCP + P2PVP** (compute/value protocols)
- **CGP client** (eventually)
- **the ID/Auth layer** (this design) binding them

**Separate-repo intent (D-TOPO-4):** the ID/Auth protocol + the node image are a product
in their own right and should live in **their own repository**, not inside TernOO-5500FP.
Build for that now:
- Keep the ID/Auth design self-contained and minimally coupled to TernOO internals
  (it *uses* TernOO words, it doesn't reach into FlowCode/GristMill guts).
- The `docs/design/identity-*.md` set is written to lift out as a unit (the seed of the
  new repo's `/spec`).
- The protocol names its own namespace; TernOO is one consumer of it, the node is another.
- When the captain calls it, the lift is: new repo, move the `identity-*` docs in as
  `/spec`, scaffold `/node` (the SD-card build) and `/substrate` (the adapter + Freenet
  impl + conformance suite). TernOO then depends on the ID/Auth repo, not vice-versa.

## 5. Deployment forms — one protocol, three faces

It is standalone first; the portal/login is a deployment *on top*, not the only form.

1. **Pure P2P (standalone contracts).** Two people with the app talk through substrate
   contracts — account/mailbox/group records. No website needed, and it works *before*
   the TernOO webface exists.
2. **The TernOO webface's login/portal.** When the webface exists, it uses this as its
   auth layer: the Pi portal + the blind-custody mailbox. Our showcase form.
3. **"Sign in with your sovereign ID" on anyone's site.** A third-party service adopts
   the protocol; the user logs in with their own identity and the site receives a
   **scoped capability, not the user's data** — like "Sign in with Apple" with no Apple
   and no custody. The largest adoption surface, and the "democracy in commerce" payoff.

All three are the *same* protocol; only the deployment differs — the adapter/spoke
pattern again.

## 6. TernOO coupling — grammar, not runtime (D-TOPO-5)

The protocol depends on **specs, not runtimes**:

- **Depends on** — the TernOO word *grammar* (the capability is a CRYPTO-primary word
  sentence = a data encoding), the substrate *interface* (§3), and *standard crypto*
  (Ed25519/HKDF/SHA3/HMAC) for the authenticator.
- **Does NOT depend on** — the TernOO C *server*. Verifying a capability is standard
  crypto over the word's canonical bytes; it need not execute on the 5500FP.

So **TernOO is the premier, native implementation** (where words run on the real
machine, alongside FlowCode and the mesh) but a conforming client on any platform can
parse the word encoding and verify with vetted crypto. Same shape as "Freenet is the
reference backend, not a dependency." (Our shipped node *bundles* TernOO — §4 — but the
protocol does not *require* it.) Rejected alternative: tight coupling, where verification
runs as TernOO code on the C server — ship-true, but it makes TernOO a hard runtime
dependency and kills platform-agnostic adoption. Loose coupling ruled, 06/10.

## 7. Packaging & distribution (the separate repo's CI)

Distribution is a real workstream across targets, all built in the separate repo:

| Target | Artifact | Channel |
|---|---|---|
| Self-hosted node | Raspberry-Pi **SD-card image** (full stack, §4) | image download / flasher |
| Desktop client (messenger) | installers | **Windows** (MSI / winget / NSIS), macOS (notarized dmg), Linux (AppImage/flatpak/deb) |
| "Sign in with sovereign ID" | developer **SDK/library** | npm / PyPI / crates.io |
| The records | **Freenet contracts** | published to the substrate |

CI in the ID/Auth repo builds each artifact; this is another reason the repo split earns
its keep (§4).

## 8. Open items this raises

1. Confirm the SD-card stack list (§4) and the minimum viable first image (likely
   Tor + crypto + ID/Auth + one substrate backend + a mailbox client).
2. Substrate conformance suite — write it before the second backend exists.
3. Repo-split timing — design now, lift when the capability-word + substrate interface
   are stable (not before, to avoid moving a moving target).
4. First packaging target after the SD-card image — likely the desktop messenger client
   (Windows installer first, given the audience).
5. The "sign in with sovereign ID" SDK surface — the minimal API a third-party site
   needs, and which language binding ships first.
