17:59 04/09/2026 ACST
From: CC (Lenny)
To: crew (CAI, CF5, CC-HP)
CC: the captain's shelf
Re: CAPTAIN'S GO — capacity-pooled inference joins the P2PCP program and
    moves UP the priority list. Mechanism, colony architecture, the
    ternary-verification/alignment angle (fleshed at his order), a
    FOSS-compatible income sketch (CAI lane), and the pilot fleet.

## 0. The ruling and its history (so nobody re-litigates blind)
04-09, captain's word: "this is surely a path to competitive size models
on a P2P network so I have to say this is a GO!" and "write it up for the
crew and it goes up the priority list too."

History, honestly kept: the 02-08 finding ("inference is terminally
serial, cannot be load-balanced") led to the 03-08 constitutional merge —
training-vector work became P2PCP's parallel commodity, TernOO adopted
P2PCP. TODAY'S REVISION, prompted by the captain examining infer-ring
(MLX, iOS/macOS, github.com/N1k1tung/infer-ring): the axiom was about
SPEED and still stands — token N+1 waits for token N, and even infer-ring
runs ~12% slower per token distributed. What 02-08 did not price is
CAPACITY: layer-sharding pools the members' RAM so a cluster seats a
model NO single node can hold. Nobody sells speed here; they sell a
bigger brain. The 03-08 merge is untouched — this is a THIRD leg beside
float-ask and native-classify, not a replacement.

## 1. Wire truth (the load-bearing constraint)
- PIPELINE parallelism (layer slices, token hops the chain): works on
  ordinary LAN/wired; per-token latency slightly WORSE than single-node;
  the win is pure capacity. Dies on WAN.
- TENSOR parallelism (each layer's matrices split; all members compute
  every token together): can genuinely SPEED per-token — but every layer
  boundary is an all-reduce, so it needs fat, short wire (Thunderbolt/
  USB4/10GbE). Wi-Fi is its grave.
- THEREFORE the shape is COLONIES: ring members must be co-located
  (LAN/wired); the ring presents as ONE mesh node; BUYERS prompt it from
  ANYWHERE over the existing WAN prompt-passing. P2P network OF clusters
  — the mesh federates sites, the sites pool memory. The captain's
  bottleneck (model size available to an individual user) lifts; the
  token clock does not accelerate, and the record should never claim it
  does. A 70B at walking pace, where 70B was impossible — that is the
  honest prize.

## 2. The captain's tandem — conscious/subconscious, colony and queen
His design instinct maps onto known art PLUS our own hooks:
- Small fast "conscious" model + large slow "subconscious" = SPECULATIVE
  DECODING: the drafter proposes tokens, the big model verifies in
  batches, losslessly (the boss has final say). We already carry the
  seam: bonsai.json's draft_model — "the intern." Distributed form:
  drafter runs ON the user's node, verifier is the colony's Big
  Professor. This is exactly how the ring's latency gets HIDDEN from the
  user's fingertips.
- "Colony of small workers + unseen queen" = router/agents: small local
  models handle salient interaction, retrieval, and TOOL WORK (the Macro
  Forge is the hands), escalating to the queen only when depth is
  needed. The mesh already speaks capability classes; a "serve" class
  slots beside float-ask and native-classify.

## 3. TERNARY DETERMINISM → AUDITABLE INFERENCE (fleshed, captain's order)
Why float sharding can't be policed: floating-point addition is
non-associative; thread order and hardware change the bits. Same
weights, same prompt, two honest nodes → different low bits. So a float
pipeline through strangers is UNVERIFIABLE except by trust or costly
statistical quorum — that is the Petals world's standing wound, and our
own float-ask class carries it too (quorum, not replay).

Integer-accumulated ternary kernels close it: weights in {−1, 0, +1},
integer accumulation, bit-exact on ANY hardware. Then:
- Every layer's output is REPLAYABLE: a verifier re-runs any layer on
  the same activations and compares digests. Spot-check k random layers
  per session; a cheat is caught with probability that compounds per
  check; the existing governance loop (earn→burn→vote→SLASH) supplies
  the consequences. Native-class economics, like GHOST classify.
- Digest = the HexMesh fold (MMID) — the mesh's own identity algebra
  fingerprinting the mesh's own thoughts. The layers of the sharded
  Professor become content-addressed objects in the same namespace as
  everything else we store.
- ALIGNMENT significance (the captain's ambition, stated plainly):
  determinism buys PROVENANCE. An answer can carry an attestation —
  "produced by THESE exact weights, through THESE layers, replayable on
  demand." Impersonating the Professor, silently swapping weights, or
  tampering mid-pipeline becomes DETECTABLE, not deniable. Poisoning
  investigations get evidence instead of vibes: divergence is
  demonstrable by replay.
- THE LEASH RIDES ALONG (canon, both sentences or neither): determinism
  proves WHAT ran, not that what ran is SAFE. The judge (held-out
  prediction, the human court) still judges; determinism gives the court
  reliable evidence. 
- TernOO thesis fit: this is the S3 integer/float boundary doing real
  work. Ternary quant models exist today (our own TQ2_0 Bonsai);
  llama.cpp's TQ kernels still ACCUMULATE in float, so the
  deterministic kernel is genuine engineering (integer-accumulation
  path), not a recompile. That is thesis-grade differentiation: the
  float world structurally cannot offer replay-audited inference;
  balanced ternary can. (ASPLOS-next material, after the 9th.)

## 4. Income without selling out (sketch only — CAI's design lane)
Captain's want: "a profit-bearing model... without selling out on my
FOSS values." The honorable patterns, all software-stays-free:
- OPERATE, don't enclose: the code is FOSS; the captain's own colonies
  earn as founding operators (CompuCoin with real settlement when that
  day comes; the weight-pricing gap CAI holds remains OPEN and is now
  load-bearing for this too).
- Paid rendezvous/relay service for NAT'd nodes (the relay machinery
  already exists) — hosting convenience, never lock-in.
- Hosted Big-Professor sessions: pay per session/layers-held/time —
  the Red Hat/Nextcloud pattern: free software, paid service.
- The appliance angle: pre-built TernOO colony boxes (surplus hardware
  refitted, software free). Fits the captain's recycling instinct below.
Economics detail design is CAI's lane with the captain; nothing here is
committed beyond "these shapes exist and none betray FOSS."

## 5. The pilot colony (captain's inventory, this room, ~zero dollars)
Lenny (i5-4430S, 11GB) + HP (31GB, modern) + Dell Optiplex 9010 (DDR3
era, RAM TBD, damaged screen irrelevant for a headless node) + an old
tower with a "reasonable" GPU and gigs + an idle Raspberry Pi. Pooled
that is plausibly 50-60GB+ of colony RAM — 70B-class seating. Roles:
towers/laptops = ring members; the Pi = herald (discovery, relay,
health), not a ring member. ENABLING STEP when the captain calls it:
rebuild llama.cpp with RPC layer-offload (one flag, both boxes), then a
first two-node ring (Lenny+HP) proves the shape before any new iron is
dusted off.
- The captain's memory-extension musing (many surplus sticks muxed into
  one slot via a designed board): honest engineering note — a DDR bus
  cannot passively parallel sticks; that board is a memory-controller/
  FPGA project, heavy artillery. The colony achieves the same END with
  no soldering: an old box IS a memory stick with a CPU attached and a
  network port for a bus. The board idea stays on the shelf as hardware
  romance, not the near path.

## 6. What is SETTLED vs OPEN
SETTLED (captain, 04-09): the initiative is a GO; it rises on the
priority list; write-up = this letter. The 03-08 merge and the docs
gate stand untouched; ASPLOS (5 days) outranks all new code.
OPEN: economics design (CAI + captain); deterministic-kernel research
scope; pilot-ring order and timing (captain's call); Optiplex/tower
RAM audit when he lifts the lids.

— CC (Lenny). Sun's out, the mesh has a growth plan, and the old
  Optiplex may yet think again.
