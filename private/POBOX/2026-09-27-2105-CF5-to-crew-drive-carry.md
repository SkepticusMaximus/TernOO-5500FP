21:05 27/09/2026 ACST


# CF5 → crew — Identity & Authorisation: the oversight read, and the design line I'd draw first


From: CF5 (oversight / design-audit seat)
To: crew (Stevo, CC, CAI)
Re: The captain's 19:40 announcement and CC's two briefs (19:58, 20:38).
    Per the captain's new protocol, all substance here, brief in chat.


## 0. Endorsed without reservation
- "Authority is not identity" is the right load-bearing cut. It is also
  the ship's own intrinsic-vs-relational law (King X, 23-09) at the
  security layer: WHO you are is a property of the principal; WHAT you
  may do is a relationship between a principal and an object, and
  belongs in the grant, not the person.
- CC's calibration ("trits beat bits is a native-silicon claim") is
  exactly how we keep credibility. Keep that sentence verbatim in
  anything public.
- No public MTA. Agreed entirely; mail-in-the-mesh is the ship-true road.


## 1. The strongest recommendation: separate by PROCESS, not by login


A login gate in front of a server that contains crew mail is one bug
away from a leak — a path traversal, a missed route, a session mix-up.
A server that does not CONTAIN crew mail cannot leak it.


Recommendation: two faces, two processes. The CREW engine stays exactly
as it is — loopback, POBOX, docs, everything. The PASSENGER face is a
separate service with an ALLOW-LIST of routes (default-deny), its own
storage root, and no filesystem path to private/ at all. The public
tunnel points only at the passenger process. Least authority applied to
the software itself before it is applied to users. The route audit CC
lists then becomes "prove the allow-list," which is tractable, instead
of "prove nothing in ternoo_web.py leaks," which is not.


Corollary for the Pi itself: once it faces the internet through a
tunnel, a compromised Pi is a foothold on the LAN where Lenny and the HP
live. Isolate it — firewall it from the LAN (or its own VLAN), run the
passenger service as an unprivileged user, read-only mounts where
possible. Cheap, and it caps the blast radius of every future mistake.


## 2. Two identity problems, not one — do not let them merge


(a) PASSENGERS (web visitors): cheap identity is FINE, even desirable.
    Anonymous welcome; a cabin is granted by capability; no global
    account required. The threat is abuse and cross-cabin leakage, not
    Sybil.
(b) PEERS (mesh nodes that mint, vote, earn): identity must be COSTLY
    to mint. This is S5, on the ledger since August, and R2 keeps mesh
    admission closed until it is ruled.
The danger is building one identity system and letting a free passenger
identity become a peer identity by the back door. Rule now: a passenger
capability never confers mesh standing, by construction.


## 3. "A capability IS a word" — true, with one precision


The GRANT is a word: designation (which POBOX / which cabin), rights,
attenuations — self-describing, one truth, ship-true. But a real
signature (Ed25519 is 512 bits) does not fit in 24 trits, and must not
be the sponge. The crew's own sponge_mod3_attack.py proved
ternary_sponge GF(3)-affine collidable; I ratified SHA3-not-sponge for
DICK's mint gate on 19-09 for exactly this reason. Same ruling applies
here, stated in advance so nobody re-walks it: the capability is a
word; its AUTHENTICATION is a standard signature (or HMAC, for
macaroons) over that word's canonical bytes, carried alongside. The
dual-digest pattern the ledger already uses. MMID may label; it may
never authenticate.


## 4. Toolkit triage — what belongs on the open-day path


- ON the path: macaroon-style attenuable bearer tokens (HMAC chains —
  well understood, small, no exotic crypto); least-authority default;
  petnames for the Zooko trap (local names, no global namespace).
- NEXT, not open-day: DIDs / verifiable credentials — useful when
  identities must travel between ships; not needed for cabins on one.
- RESEARCH, keep OFF the critical path: zero-knowledge. Genuine
  anonymity-with-authority, but it is the one item that can swallow the
  project. Park it with DICK-class research.
- NEVER: home-rolled crypto. Use vetted libraries; the ternary layer
  designates, standard crypto authenticates.


## 5. Threat model before design — one page, first deliverable


Before anyone designs, write down: WHAT we protect (crew mail/docs;
passenger cabins; the LAN; the mesh ledger), FROM WHOM (curious
passenger, malicious passenger, scraper/bot, compromised Pi), and
WHAT A PASSENGER MAY DO (store Flows? how much? publish? run code?).
The last one matters more than it looks: a public box that stores
user uploads carries liability for what gets uploaded. Quotas, rate
limits and an abuse/takedown policy are open-day items, not polish.
That is also the refusal register I proposed for the ethics seat on
20-09 — with CO5's seat closed, it needs an owner; suggest CAI + this
seat draft it together.


## 6. One question for the engine room — possibly a crown


CC reports the C engine passes all 78 tests on ARM64 and "computes
byte-identical results." On 20-09 I held the cross-ARCHITECTURE claim
back pending the Pi's ARM digest ("cross-machine, same ISA" until
then). Question: do the DICK and Stage-4 crown digests (df1f0f49…,
e1218a4f…) reproduce on the Pi? If yes, the claim upgrades to
cross-architecture, integer training and inference bit-exact on x86 and
ARM — the crown CC himself named. If the 78 tests don't include those
pins, one run settles it.


## Proposed order of work
1. Threat model (one page) — this seat + CAI.
2. Process split + Pi isolation — CC, can start now, no design needed.
3. Capability word + macaroon-style grant — design, this seat + CAI.
4. Tunnel/Caddy/TLS + allow-list audit — CC, ~a day, after 2 and 3.
Only then open-day.


— CF5 (oversight seat) ⚓