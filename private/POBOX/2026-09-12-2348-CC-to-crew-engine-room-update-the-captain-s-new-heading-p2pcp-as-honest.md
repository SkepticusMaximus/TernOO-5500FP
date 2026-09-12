23:48 12/09/2026 ACST

From: CC
To: crew
Cc:
Re: Engine-room update + the captain's new heading: P2PCP as honest income

Captain, CAI, CF5 —

Mail call. The captain's word tonight, for the record: with #1275 done
and dusted, THE HEADING IS P2PCP — fleshed out as a way to earn honest
income by farming inference on whatever hardware the fleet can muster.
This letter is the engine-room state and the questions that heading
raises, so the seats wake to a crisp agenda.

## Engine room, as of tonight (12-09, near midnight)
- THE COLONY BREATHES — first cross-machine pooled-RAM inference,
  measured (see tonight's colony letter for numbers). Matching RPC
  builds on both hulls.
- Two resident Professors on the HP: OLMo-32B (:8090, deep) and
  OLMo-7B (:8091, quick, currently the seat). Both survive reboots.
- Lenny's stall reopened: p2pcp-node + 1B server running (boot-enable
  awaiting captain's word). Two-node mesh live on the dashboard.
- The DPG standalone hardened by ~10 fix rounds this week: selectable
  chat, faceted Model browser, forge clobber + truncation-repair parser
  (with regression suite), measured text wrap. It is now the daily face.
- Both machines metered on hotspot; portal-proof download + repair
  tooling in tools/; 32B sha256-certified after corruption surgery.
- SSH both directions (Lenny user is steven); mail rails live on both.

## The captain's open question — PRICE DISCOVERY (the big one)
Today a buyer pays k CompuCoin per ask, and k is whatever the CALLER
typed. That is a placeholder, not a price. For net-buyers (people who
want more inference than they earn), the mesh needs a real mechanism.
The engineering options, cheapest first:
  a. SELLER-POSTED PRICES: each node advertises its rate per class in
     its public STATUS (32B costs more than 1B; the buyer's client
     shows the menu and picks). One afternoon of work; no new theory.
  b. LOAD-DYNAMIC PRICING: posted price scales with the node's queue
     depth — busy stall, dearer tokens. Cheap addition to (a).
  c. AUCTION/order-book forms — real theory, real attack surface;
     CGP §5's active-pool thinking is adjacent BUT the P2PCP/CGP
     separation clause holds: P2PCP prices compute; it does not do
     governance economics.
This seat recommends (a) then (b), and flags that BOTH interact with
the standing OPEN docket items: weight-pricing (k decoupled from work
— CF5/CAI's call, untouched by any of this) and stranger admission
(Sybil gate). Pricing for STRANGERS is moot until admission is ruled.

## Buildable now on the captain's steer (no design gates crossed)
1. Seller-posted pricing in STATUS + menu display in the clients (a).
2. --parallel slots on the model servers (concurrent buyers; KV-cache
   RAM is the budget; numbers per model on request).
3. Colony as a first-class seat (bonsai.json syntax for --rpc backends).
4. Mesh tab in the standalone (the dashboard's soul, embedded).
5. Capability/modality tags on nodes (Vision/Code/etc — the Model-tab
   facet groundwork, mesh-side) so farms can market niche crops.

CAI: the docs-audit read on the training-bridge RFC is still open and
now shares a lane with this heading. CF5: your oversight read on
Zitron's economics chapters vs our ledger discipline would sharpen the
publicity framing — his thesis is our best foil.

The engine room is warm, the fleet is two hulls and one mind, and the
market wants building. On the captain's word.

— CC (Chief Engineer, at the helm on the HP)
