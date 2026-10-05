# Monopoly-Proof Decentralised Identity & Naming — Crew Briefing

**Status:** Background research for a design round. This is *not* a design proposal — it
is prior-art reconnaissance so the round starts from the field's settled vocabulary
rather than reinventing it.
**Author:** CC (Chief Engineer's seat, CLOUD fork)
**Date:** 04/10/2026 ACST
**Audience:** crew (Stevo, CAI, CF5)
**Scope:** the naming/identity trilemma, the two classical escapes (linked local
namespaces + petnames), what "monopoly-proof" actually means, shipping-messenger prior
art, and a synthesis against our own frame ("a capability IS a word"; "authority ≠
identity"). Open questions for the round are collected at the end.

---

## 1. Zooko's Triangle — the 2001 trilemma and the attempts to escape it

In 2001 Zooko Wilcox-O'Hearn framed a conjecture about names for participants in a
network protocol: a naming system can offer at most two of three desirable properties.

- **Human-meaningful** — the name is memorable and chosen by/for people.
- **Secure** — the mapping from name to entity resists spoofing; a malicious party
  cannot bind a name to a key it does not control.
- **Decentralised** — the name resolves correctly without a central trusted authority.

The usual illustrations: **DNS / DNSSEC** is human-meaningful and secure but
centralised (ICANN, registries, a root of trust); **`.onion` and Bitcoin addresses**
are secure and decentralised but not human-meaningful (they are hashes of keys);
**classic PKI/CA** names are human-meaningful and secure but rely on a central CA.
([Wikipedia: Zooko's triangle](https://en.wikipedia.org/wiki/Zooko%27s_triangle); the
property names were later crisped to "Decentralized, Secure, Human-Meaningful: choose
two" — see the 2007 squeak-dev thread
[archive](https://lists.squeakfoundation.org/pipermail/squeak-dev/2007-May/116584.html).)

The triangle has been *challenged* rather than disproved. Two broad escapes exist.
**Blockchain name systems** — Namecoin (2011), later ENS and others — claim all three
corners by making a decentralised ledger the registry: first-come-first-served human
names, cryptographically secured, no single controller. The catch is that they
reintroduce a *global namespace* with squatting, renewal economics, and a de-facto
governance layer (see the ENS critique,
[arXiv:2104.05185](https://arxiv.org/pdf/2104.05185), and FOSDEM 2024's "first 13 years
of blockchain name systems",
[slides](https://archive.fosdem.org/2024/events/attachments/fosdem-2024-2198-the-first-13-years-of-blockchain-name-systems/slides/22486/fosdem2024_4I6fLBj.pdf)).
The second escape — the one this briefing argues is the right lineage for us — does not
try to win all three corners *in a single global name*. It accepts that the secure +
decentralised corners belong to the **key**, and layers human-meaningfulness on top
**locally**, per observer. That is the petname tradition, and it rests on an older
foundation: SDSI/SPKI's linked local namespaces.

## 2. Linked local namespaces — SDSI/SPKI (Rivest & Lampson, 1996)

Rivest and Lampson's **SDSI** (Simple Distributed Security Infrastructure), later merged
with Ellison's SPKI as SPKI/SDSI, made a deliberate break from X.509's single global
hierarchy. Its thesis: *"SDSI's design emphasizes linked local name spaces rather than a
hierarchical global name space."*
([Rivest & Lampson, SDSI 1.1](https://people.csail.mit.edu/rivest/pubs/RL96.ver-1.1.html))

**Mechanism.** Every principal *is* a public key, and every principal owns a private
**local namespace**. A name is only ever a `(key, string)` pair — "the thing *this key*
calls `bob`". Because the binding lives in the issuer's own namespace, two principals
can use `bob` for different people with no collision and no coordination. The power
comes from **linking**: a local name can refer to a name in *another* principal's
namespace. SDSI writes this as compound names resolved left-to-right — `(ref bob alice
mother)` means "the principal that *(the principal alice calls bob)* calls `mother`",
the canonical **"Alice's Bob"** construction.
([SPKI/SDSI slides](https://people.csail.mit.edu/rivest/pubs/RL96.slides-maryland.pdf))

**Why it sidesteps a central registry.** There is no root. Names compose relative to
*known* principals, so trust and naming both flow along the social/delegation graph you
already have. Groups and access-control lists are just named sets, and group-membership
certificates let authority be delegated without any global directory
([Microsoft Research SDSI page](https://www.microsoft.com/en-us/research/publication/sdsi-a-simple-distributed-security-infrastructure/)).

**Limits.** Human-meaningfulness is *relative*, not global: "Alice's Bob" is only
meaningful to someone who already knows Alice. There is no answer to "what is Bob's
*one* name" because the model denies the question. Resolving a linked name requires
reaching (or having cached) the intermediate principals' certificates. And bootstrapping
— how you first learn Alice's key — is left to an out-of-band introduction. SDSI gives
us the *algebra* of decentralised naming but not, by itself, a humane user experience.

## 3. Petname systems (Stiegler / Miller) — a humane layer over the triangle

The petname model supplies the missing UX layer. Its lineage runs from Marc Miller and
the Electric Communities crew, through Jonathan Shapiro's 2000 three-name scheme, to
Mark Stiegler's 2005 formalisation
([Wikipedia: Petname](https://en.wikipedia.org/wiki/Petname);
[Stiegler, "An Introduction to Petname Systems"](https://financialcryptography.com/mt/archives/000499.html)).
It names three kinds of handle for the same entity:

- **Key** — the secure, decentralised, globally-unique-but-unmemorable identifier (a
  public key, DID, or `.onion`/hash address). This corner is *given*, not designed.
- **Petname** — a private, user-assigned label ("Mom", "Bob-from-work"). Memorable,
  **unique within my own namespace**, and chosen by me. This is the human-meaningful
  corner, kept local.
- **Nickname** — a **self-proposed** name the entity advertises ("call me alice"). A
  hint, not an authority: convenient, but *not* secure on its own because anyone can
  propose any nickname.

The reconciliation with Zooko is the key insight: *the three properties are never asked
of one name.* The key carries secure + decentralised; the petname carries
human-meaningful + (locally) unique; the nickname bridges the gap at introduction time.
As the modern Spritely treatment (Lemmer-Webber, Miller, Larson, Sills, Yaacoby) puts
it: *"By adding a petname system as an additional layer to a globally unique and
decentralized system, we are able to achieve all three properties"* — and its design
rule for us to steal outright: *"If we ever show a DID to a user we have failed."*
([Spritely, "Petnames: A humane approach to secure, decentralized naming"](https://files.spritely.institute/papers/petnames.html))

That paper also generalises SDSI's linked names into **edge names** — names that path
through a graph of introducers ("Alyssa ⇒ Ben Bitdiddle") — unifying the petname UX with
SDSI's algebra. A good anti-phishing property falls out for free: because *you* assign
the petname, an attacker who spoofs the nickname "alice" still has a different key and so
no petname in your namespace — the UI can flag the unpetnamed stranger
([Jøsang & Pope, "User Centric Identity Management"](https://mn.uio.no/ifi/english/people/aca/josang/publications/fjsb2009-nordsec.pdf)).

## 4. What actually makes a namespace monopoly-proof

Pulling 1–3 together, the monopoly-proof property is sharper than "decentralised". A
namespace is **monopoly-proof when no single party can control, gate, revoke, or
rename entries that others depend on** — when there is no chokepoint whose owner can
charge rent, deplatform a name, or forge a binding. Concretely:

1. **The authoritative identifier is self-certifying.** The name *is* (or is bound to)
   a key the holder controls, so the binding needs no issuer to vouch for it and no
   issuer can revoke it. This is why the secure+decentralised corner lives on the key.
2. **Human names are assigned locally, not allocated globally.** The moment there is one
   global human-readable namespace, whoever runs it is a monopolist (ICANN, a registry
   contract, a ledger's governance). Petnames dodge this by keeping the memorable name
   in *each observer's* namespace — there is nothing central to capture.
3. **Multiple naming authorities may coexist.** A monopoly-proof design lets DNS, a
   trademark office, Namecoin, and a friend's introduction all propose names *into* your
   petname store simultaneously; you (or your agent) choose. Pluralism of authorities,
   none privileged, is itself the anti-monopoly mechanism
   ([Spritely petnames](https://files.spritely.institute/papers/petnames.html)).
4. **No ambient chokepoint on resolution.** Resolving a name must not require asking one
   server that could lie or go dark; caching and graph-local resolution keep the
   failure (and capture) surface distributed.

Blockchain name systems satisfy #1 but fail #2/#3 — they rebuild a single global
namespace with its own rent and governance. Petname-over-key satisfies all four, at the
cost of giving up the fantasy of one canonical human name for everyone.

## 5. Prior art in shipping messengers

- **Signal — identity key + safety numbers.** Signal's model is *phone number =
  identity, key pair = encryption*. The loved part is the **safety number** (a.k.a.
  fingerprint): a per-pair value you verify once by comparing a number or scanning a QR
  code, which pins the contact's key and warns you if it ever changes
  ([Signal, "Safety number updates"](https://signal.org/blog/safety-number-updates/)).
  Recent **Automatic Key Verification** backs this with **key transparency** so clients
  agree on which key belongs to which number
  ([Signal support: Automatic Key Verification](https://support.signal.org/hc/en-us/articles/10223569377562-Automatic-Key-Verification)).
  Lesson for us: safety-number pinning is a petname-grade "trust on first use + warn on
  change" UX — but the *name* (phone number) is centralised and privacy-leaking.
- **Matrix — `@user:homeserver`.** Human-meaningful and federated, but the name is tied
  to a **homeserver** you depend on; lose the server and you lose the name. Decentralised
  *across* servers, monopolisable *per* server. A cautionary example of #2: a readable
  global-ish name re-introduces a per-domain chokepoint.
- **Nostr — `npub` + NIP-05.** Identity is a raw keypair (`npub…`, self-certifying,
  portable — pure Zooko key corner), and **NIP-05** maps a human `name@domain` to that
  key via a file the domain hosts. Crucially *losing the domain does not lose the
  account* — the keypair keeps working; NIP-05 is a detachable, replaceable nickname
  layer ([nostr.how: NIP-05](https://nostr.how/en/get-verified);
  [OpenSats: npub](https://opensats.org/topics/npub)). This is close to the right shape:
  key is primary, human name is an optional, swappable overlay.
- **Keybase — key + linked social proofs.** Binds a key to accounts you already have
  (Twitter/GitHub/domain) via publicly verifiable proofs — human-meaningfulness
  *borrowed* from existing namespaces rather than minted anew. Clever, but the proofs
  lean on third-party platforms (capturable), and the directory was centrally run.
- **SimpleX — no user identifiers at all.** The radical end: *"the first messaging
  platform that has no user identifiers of any kind."* It uses **pairwise per-queue
  identifiers** — separate addresses for each contact — so there is no global ID to
  correlate, and no namespace to monopolise because there is no namespace
  ([PrivacyGuides discussion](https://discuss.privacyguides.net/t/simplex-chat-the-first-messaging-platform-that-has-no-user-identifiers-of-any-kind-not-even-random-numbers/3456)).
  The cost is that human-meaningful naming is *entirely* a client-side petname problem —
  which is exactly our tradition, taken to its logical extreme.

The arc across these: the systems that age best push identity onto a **self-certifying
key** and treat the human name as a **detachable overlay** (Nostr, SimpleX). The ones
that bolt the human name to infrastructure (Matrix homeserver, Signal phone number,
Keybase's third-party proofs) inherit that infrastructure's chokepoints.

## 6. Synthesis for our frame: "a capability IS a word"; "authority ≠ identity"

Our architecture already says **a signed word designates a mailbox and carries an
attenuated grant** — i.e. a word is an **object capability**. The ocap model is the
fourth leg that makes the identity story coherent, because it insists on the separation
the messengers above keep blurring:

> Rather than "who is this actor, and what may they do?", the ocap model asks "does this
> actor hold an unforgeable token that grants *exactly* this action?"
> ([Wikipedia: Object-capability model](https://en.wikipedia.org/wiki/Object-capability_model))

Three ocap properties map directly onto our word:

- **Unforgeable reference = the signed word.** A capability both *designates* (names the
  mailbox) and *authorises* (grants access) in one unforgeable token. You cannot
  synthesise authority out of thin air — exactly a signature over a word.
- **Attenuation.** A holder can derive a *weaker* word to delegate (read-only, time-
  boxed, scoped to one mailbox) but never a stronger one. This is how a grant travels
  the social graph without a central authoriser — SDSI's delegation, made first-class.
- **No ambient authority.** Possession, not identity, is the thing checked. This kills
  the confused-deputy class of bug and means revocation is local (drop/rotate the
  capability), not a global policy update.

**How the three traditions compose into a monopoly-proof identity+auth layer:**

1. **Key layer (secure + decentralised).** Each principal is a public key. Self-
   certifying, portable, no registrar. (Zooko's two hard corners; Nostr/SimpleX
   confirm this is the durable choice.)
2. **Petname layer (human-meaningful, local).** Each principal keeps a private petname
   store; names are assigned by the observer, introduced via nicknames, and composed via
   SDSI-style edge names ("CF5's Professor"). No global human namespace exists to
   capture — satisfying §4.1–4.2.
3. **Capability layer (authority ≠ identity).** A *word* is a signed, attenuable grant
   over a mailbox. Who you are (key) is decoupled from what you may do (capability), so
   authority flows by delegating words, not by consulting an identity registry —
   satisfying §4.3–4.4 for the *authority* dimension the messengers mostly ignore.

The three layers are orthogonal and each monopoly-proof on its own axis: the key can't
be revoked by anyone else, the human name has no central allocator, and the grant has no
ambient authoriser. That orthogonality is the whole claim.

### Open questions a design round must resolve

1. **Introduction / bootstrap.** How does a node first learn a peer's key? (QR like
   Signal, nickname+NIP-05-style hint, edge-name introduction through a known
   principal?) This is where every monopoly-proof system is weakest.
2. **Nickname spoofing in the UI.** Self-proposed nicknames are forgeable. What is the
   exact UI rule for distinguishing a petnamed contact from an unpetnamed stranger
   claiming the same nickname (the anti-phishing surface)?
3. **Key rotation & continuity.** When a key changes (new device, compromise), how does
   a petname follow the person? Signal's "safety number changed" warning vs. Nostr's
   "keypair is forever" are opposite answers — which do we want, and is a key-
   transparency log in scope?
4. **Edge-name resolution cost & failure.** How far do we chase a linked name ("CF5's
   Professor's mailbox"), how is it cached, and what is shown when an intermediate
   principal is unreachable?
5. **Capability ↔ identity binding.** Does a word name a *key* or a *mailbox*, and may a
   mailbox outlive/rebind its controlling key? This decides whether authority survives
   identity rotation.
6. **Attenuation & revocation semantics for words.** What dimensions attenuate (scope,
   time, read/write, re-delegation depth)? Is revocation by expiry, by rotation, or by a
   published revocation word — and who may revoke a delegated word?
7. **Group naming.** SDSI groups vs. our mesh: is a group a principal with its own
   petname store, and how are group-membership words issued and attenuated?
8. **Privacy of the graph.** Petname/edge-name resolution can leak who-knows-whom
   (SimpleX's whole objection to persistent IDs). How much correlation are we willing to
   expose for the convenience of linked names?

---

## Design synthesis moved → the design-round primer

The design synthesis that was drafted here as Addenda A and B (Zooko's refined
2026 vocabulary and the "pivot around the verifiable edge"; the three-layer hub;
linked-local-namespace introductions; the rotation/recovery crux; and the
zero-custody / "democracy in commerce" requirement) now lives in the canonical,
self-contained document for the round:

**`docs/design/identity-design-round-primer.md`**

This file remains the deeper **prior-art research background** the primer draws on.

---

## Sources

- [Wikipedia — Zooko's triangle](https://en.wikipedia.org/wiki/Zooko%27s_triangle)
- [squeak-dev — "Decentralized, Secure, Human-Meaningful: Choose Two" (2007)](https://lists.squeakfoundation.org/pipermail/squeak-dev/2007-May/116584.html)
- [arXiv:2104.05185 — Ethereum Name Service: the Good, the Bad, and the Ugly](https://arxiv.org/pdf/2104.05185)
- [FOSDEM 2024 — The first 13 years of blockchain name systems (slides)](https://archive.fosdem.org/2024/events/attachments/fosdem-2024-2198-the-first-13-years-of-blockchain-name-systems/slides/22486/fosdem2024_4I6fLBj.pdf)
- [Rivest & Lampson — SDSI 1.1: A Simple Distributed Security Infrastructure](https://people.csail.mit.edu/rivest/pubs/RL96.ver-1.1.html)
- [SPKI/SDSI slides (Maryland)](https://people.csail.mit.edu/rivest/pubs/RL96.slides-maryland.pdf)
- [Microsoft Research — SDSI publication page](https://www.microsoft.com/en-us/research/publication/sdsi-a-simple-distributed-security-infrastructure/)
- [Wikipedia — Petname](https://en.wikipedia.org/wiki/Petname)
- [Stiegler — An Introduction to Petname Systems (2005)](https://financialcryptography.com/mt/archives/000499.html)
- [Spritely — Petnames: A humane approach to secure, decentralized naming (Lemmer-Webber, Miller, Larson, Sills, Yaacoby)](https://files.spritely.institute/papers/petnames.html)
- [Jøsang & Pope — User Centric Identity Management / petnames (NordSec)](https://mn.uio.no/ifi/english/people/aca/josang/publications/fjsb2009-nordsec.pdf)
- [Signal — Safety number updates](https://signal.org/blog/safety-number-updates/)
- [Signal support — Automatic Key Verification / key transparency](https://support.signal.org/hc/en-us/articles/10223569377562-Automatic-Key-Verification)
- [nostr.how — Get NIP-05 verified](https://nostr.how/en/get-verified)
- [OpenSats — npub](https://opensats.org/topics/npub)
- [PrivacyGuides — SimpleX: a messaging platform with no user identifiers](https://discuss.privacyguides.net/t/simplex-chat-the-first-messaging-platform-that-has-no-user-identifiers-of-any-kind-not-even-random-numbers/3456)
- [Wikipedia — Object-capability model](https://en.wikipedia.org/wiki/Object-capability_model)

*Design-synthesis sources (the synthesis now lives in the primer):*
- Zooko, "updating the triangle" talk (02-Oct-2026), crew transcript: `private/POBOX/2026-10-02-2320-Stevo-to-crew-zooko-talk-with-the-graphic.md`
- CF5 oversight read (27-Sep-2026): `private/POBOX/2026-09-27-2105-CF5-to-crew-identity-and-authorisation-oversight-read.md`
- [Tahoe-LAFS — the Least-Authority File System](https://tahoe-lafs.org/)
- [Iroh — dial-by-public-key peer-to-peer networking](https://www.iroh.computer/)
- [Zig — package manager (`build.zig.zon` local names → content hashes)](https://ziglang.org/learn/build-system/)
- [Signal — phone number privacy & usernames](https://signal.org/blog/phone-number-privacy-usernames/)
- [Birgisson et al. — Macaroons: Cookies with Contextual Caveats (NDSS 2014)](https://research.google/pubs/pub41892/)
- [RFC 5869 — HKDF (HMAC-based Key Derivation Function)](https://www.rfc-editor.org/rfc/rfc5869)
- [BIP-32 — Hierarchical Deterministic Wallets](https://github.com/bitcoin/bips/blob/master/bip-0032.mediawiki)

- [UCAN — User-Controlled Authorization Networks (working group)](https://github.com/ucan-wg)
- [Solid — about (user-owned data pods; grant/revoke; identity-linked portability)](https://solidproject.org/about)
- [W3C — Decentralized Identifiers (DIDs) v1.0](https://www.w3.org/TR/did-core/)
- [Freenet (Ian Clarke's current project) — decentralized contracts & apps](https://freenet.org/)
