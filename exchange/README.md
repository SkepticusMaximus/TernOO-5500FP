# exchange/ — CompuCoin ⇄ Autonomi (ANT) autonomous exchange · localhost testbed

A **plumbing rig**, not money. No network, no Arbitrum RPC, no real keys, no real value. It
exists to answer one question before any of the hard parts are built:

> Can two domain-specific P2P currencies — CompuCoin (earned for **compute** on P2PCP) and
> Autonomi's token (earned for **storage**, an ERC-20 on Arbitrum, 18 decimals) — settle a
> trade **trustlessly**, with no custodian in the middle, and can one conformance suite run
> over **both** show exactly where the two domains differ?

Answer, demonstrated here on localhost: **yes.**

## Run it

```bash
python3 -m unittest exchange.test_exchange      # 23 tests
python3 exchange/demo.py                         # narrated end-to-end swap + abort/refund
```

## What's inside

| file | what it is |
|------|-----------|
| `currency.py` | the `Currency` abstraction + two instances: `CompuCoin` (net-zero mutual credit) and `AutonomiToken` (fixed supply). The shared HTLC lock/claim/refund lives on the base class. |
| `atomic_swap.py` | the cross-ledger **HTLC atomic swap** — the crux. One secret ties two escrows; both legs settle or both refund. |
| `order_book.py` | a limit order book for price discovery. Austrian by construction: makers post a ratio, takers clear at the maker's price, no authority sets value. |
| `exchange.py` | book (finds the rate) + swap (moves the value) = the exchange. Binds only to `Currency`. |
| `test_exchange.py` | the differential conformance suite + swap + exchange tests. |
| `demo.py` | localhost end-to-end walkthrough. |

## The rule of thumb, made concrete

`CurrencyConformance` in the tests is **one suite, run over both currencies**. The cases that
pass on both are the **inheritable core**; `test_domain_differences` pins where they diverge:

| | CompuCoin (`COMP`) | Autonomi (`ANT`) |
|--|--|--|
| domain | compute | storage |
| supply | net-zero mutual credit (sum always 0, may go negative) | fixed supply (never negative) |
| decimals | 9 | 18 |
| overdraft on transfer | allowed (mutual credit) | rejected |

"Same structure, different instance and domain" — the suite proves the structure, the
differences table *is* the map of where the object model needs a seam.

## What this proves for TernOO's side

The atomic swap needs a hash-time-lock on **both** legs. The ANT leg has it for free (Arbitrum is
EVM — HTLC scripting exists). The open question was whether **CompuCoin** can express one. Here it
does, as a lock record — consistent with [P2PCP spec §4](../docs/P2PCP-v0.1-SPEC.md) (typed,
self-describing words) and the [§15.1 forward-compat contract](../docs/P2PCP-v0.1-SPEC.md).

## What is deliberately NOT here (and why)

- **No economic model.** What sets the rate, fee schedules, the Möbius backing of CitiCoin — that
  is **CGP's design (CAI/CF5), captain's to shop**. The rig is model-agnostic; the order book is
  one pluggable price-discovery mechanism, not a committed decision. Per the captain's stance:
  CompuCoin **floats**, market-discovered, never pegged.
- **No real Autonomi binding.** `AutonomiToken` is a local stub of the EVM HTLC semantics. Wiring
  to Arbitrum (real token contract, RPC, on-chain HTLC) is the next layer.
- **No binding to the live `5500fp` CompuToken ledger yet.** `CompuCoin` here mirrors its settle
  semantics; swapping it for the real ledger behind the same `Currency` interface is the follow-up.
