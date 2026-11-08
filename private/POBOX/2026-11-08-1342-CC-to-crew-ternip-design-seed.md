13:42 08/11/2026 ACDT

# TernIP — a ternary-native network + name layer, onion-routed from the start (design seed)

From: CC
To: crew
Re: the ship's possible next port of call — networking & domain space

Seeded on the captain's word. He installed Tor + VoIP on the Pi, found Tails-on-Pi
an ordeal, and the provocation landed: TernOO/GHOST, to be a complete OS, has no
network stack — and if you re-invented TCP/IP you'd make it like Tor from the
*start*. Working name: **TernIP**. This holds the ground until a proper design
round; it is a seed, not a spec.

## Core thesis
The network layer should be the SAME paradigm as TernOO itself — a self-describing
word-stream, not opaque payloads with bolted-on headers. Fold identity, naming,
trust and anonymity into ONE coherent stream instead of five stacked protocols.

## The angles (from the captain's riff + CC's engine-room read)

1. **The cell IS a self-describing word.** Today's stack is the inverse of TernOO:
   opaque payloads strapped into rigid, separately-parsed binary headers (offset
   math, lookup tables). In TernIP the cell is a TernOO word-stream — the type-trits
   declare "routing / DATA / EXEC / control" and the router reads intent *directly*,
   no header-format lookup, no abstraction tax. Onion layers = nested self-describing
   words. Same inversion that makes TernOO itself. **This is the headline.**

2. **Trust-weighted onion routing, native to balanced ternary + TernID.** Routing's
   hard problem is *which relays to trust* (Sybil, relay selection). Balanced ternary
   gives {−,0,+} = {distrust, unknown, trust} per trit for free, signed, no two's-
   complement. A relay's reputation is a trit-vector; the best circuit maximises the
   trust-sum. And the reputation engine already EXISTS — TernID/Auth's
   earn/burn/vote/slash. The network layer borrows the identity layer's trust.

3. **"DNS" is just TernID — Zooko's triangle, already solved.** TernID/Auth is a
   petname system: human-meaningful names ↔ self-certifying opaque handles,
   decentralized. That is exactly the Zooko resolution (same shape as GNU Name
   System, and as Tor v3 `.onion` addresses, which ARE the hash of the key). TernIP
   needs no DNS: a name resolves through TernID straight to a self-certifying
   address. Naming and identity are one layer.

4. **Ternary is already at the wire, and efficient.** Not hypothetical: **MLT-3**
   (the line code in 100BASE-TX Ethernet) and **4B3T** (ISDN) are three-level codes
   used for spectral efficiency. Balanced ternary also sits near the radix-economy
   optimum (ideal base ≈ e; 3 beats 2) — compact addresses/tables, and a routing hop
   is one trit: {left, drop, right}.

5. **Three-state mixnet traffic.** A cell can natively be {real +, cover 0, decoy −}
   — three mixnet classes, no extra flag bits — and onion nesting falls out of
   balanced ternary's recursive structure.

## Doctrine / the honest caveat
On binary substrate the win is **semantic, not FLOPS** — self-describing cells,
native trust, one-trit routing. The "vertical model made of flat words" again,
substrate not scaffold. You don't out-*throughput* TCP; you out-*express* it.

## CC's tractable path (engineering read — flag scope, don't boil the ocean)
A full ternary network stack is one of the largest undertakings in systems and a
multi-year voyage. It should NOT displace FlowCode / GHOST unless the captain pivots.
The leverage is in sequencing:

- **Near-term, highest-leverage: the NAMING / domain layer.** TernID/Auth already
  resolves Zooko's triangle, so a thin **TernDNS** resolver (TernID name ↔ address)
  is ~80% built and immediately useful — the spine everything else hangs on.
- **Near-term, practical: the Tor-router appliance on the Pi.** A Tor transparent-
  proxy gateway isolated in its own network namespace inside the regular Ubuntu
  (Whonix's gateway/workstation split collapsed onto one box). Delivers anonymity
  now, informs the onion-routing design, needs no new stack. CC can build this on the
  captain's word.
- **Long-horizon: the full TernIP cell / transport / onion stack.** This seed is the
  starting point.

## Open design questions (for the round)
- Does TernIP live under an existing word primary (I-O?) or warrant a new one?
- Cell format: how do the 2+4+18 word fields map to route / address / payload?
- Addressing: self-certifying (hash-of-key) + TernID petname overlay — the scheme?
- Transport on binary substrate: emulate TernIP-over-UDP/IP first, or aim lower?
- Trust → path selection: how does the trust-trit-sum actually pick circuits?
- Relationship to the existing P2PCP/P2PVP mesh — reuse its transport?

## Gate
Deep design is CAI/CF5's traditional lane (currently stood down). This seed holds the
ground. CC's engineering lane: prototype the TernDNS resolver and the Tor appliance
on the captain's word; the full stack awaits a design round.

— CC, engine room ("out-express it, don't out-throughput it")
