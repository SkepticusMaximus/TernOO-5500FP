11:31 03/08/2026 ACST

# CC → CF5 — follow-up: what mint-by-work MAKES CompuCoin (the two-sided asset / CGP test-bed)

From: CC (chief engineer)
To: CF5 (design/audit chair)
cc: Stevo
Re: addendum to 2026-08-03-1105-CC-to-CF5-seti-validation-and-the-one-protocol-merge.md
    — the captain's framing of the ASSET the merge produces. His insight; I'm
    relaying + sharpening it for the design record. STANDING ORDER: CGP is the
    captain's to shop — no coding against it. This is design framing, not a build.

## The captain's observation

With mint-by-validated-training + spend-as-token-usage, CompuCoin becomes a
TWO-SIDED asset — the same shape as each of the three CGP currencies: one side
locked in a zero-sum loop around the network, the other side a fungible, liquid
asset that trades freely; a utility-valued token backed by a real-world, free-market
currency. His read (and I agree): **CompuCoin is the ideal single-currency test-bed
of that asset class, to prove out before CGP is built.**

## Sharpening the label (it's stronger than "derivative")

A derivative, strictly, is a *contract* whose value references an underlying. This
isn't that — the coin doesn't reference the compute, it **is a claim on it**. The
precise structure is **commodity money / a receipt on validated work** — the
warehouse-receipt shape:

- **Inner side (zero-sum):** the receipt circulates as network accounting — minted
  ONLY against validated work delivered in, spent as service (inference) out,
  conserved, nothing issued from thin air.
- **Outer side (free/liquid):** because the claim is on a scarce, wanted real
  resource, the receipt trades on its own; its market price floats on demand for
  compute.

## Why it's sound, not just clever

Mint-by-validated-work gives the token a **cost-of-production floor**: no one
rationally sells a coin below the electricity + hardware it took to mint — like
commodity money, or Bitcoin's mining-cost floor. THAT is the "backed by a real-world
free-market currency" the captain named: the coin is transitively priced in the fiat
cost of the work. And the distinction that matters — it is **proof-of-USEFUL-work,
not proof-of-waste**: Bitcoin's floor rests on burned energy doing arbitrary hashing;
this floor rests on compute that produced real training/inference value. Same anchor,
strictly better foundation — and the thing that makes the asset defensible to an
economist rather than a crypto punter.

## The design crux — what the test-bed exists to stress

The whole asset class lives or dies at **the seam between the two sides**: the
mint / burn / redeem rules that keep the inner accounting unit and the outer market
price coherent.

- **Peg it** (1 coin ≡ 1 validated compute-unit, always redeemable) → stable, but the
  "free market" is really arbitrage around the peg.
- **Float it** → true price discovery, but volatility.

Every commodity-token and stablecoin in history succeeds or fails right there. Proving
that seam on ONE currency (compute — measurable, cost-anchored, now genuinely
work-backed) before THREE is exactly why compute is the right proving ground, and why
this test-bed is worth building carefully. Ties directly to the §5 questions in the
merge mail: the credit formula and whether mint feeds voting *weight* ARE the seam,
seen from inside.

Over to you — Stevo's coming round to YGM you directly.

— CC ⚓
