#!/usr/bin/env python3
"""The exchange: order book (price discovery) + atomic swap (trustless settlement).

The book finds the rate; the HTLC moves the value across the two ledgers; no custodian ever holds
either side of a trade. This is the whole thing, assembled from the two primitives — and it binds
only to `Currency`, so the day a second platform's token arrives it slots in behind the same
interface.
"""
from __future__ import annotations

from exchange.currency import CompuCoin, AutonomiToken
from exchange.order_book import OrderBook, Trade
from exchange.atomic_swap import atomic_swap, SwapResult


class Exchange:
    def __init__(self, comp: CompuCoin, ant: AutonomiToken):
        self.comp = comp
        self.ant = ant
        self.book = OrderBook()
        self.trades: list[Trade] = []

    def submit(self, owner: str, side: str, price, size_cc: int,
               now: float | None = None, settle: bool = True) -> list[Trade]:
        """Post an order. Any trades it produces are settled trustlessly (unless settle=False,
        for inspecting the book in isolation)."""
        trades = self.book.submit(owner, side, price, size_cc)
        for t in trades:
            if settle:
                res = self.settle(t, now=now)
                t.settled = res.ok
            self.trades.append(t)
        return trades

    def settle(self, trade: Trade, now: float | None = None) -> SwapResult:
        """Settle a matched trade via a cross-ledger HTLC swap. The seller (gives COMP, wants ANT)
        is the initiator who picks the secret; the buyer (gives ANT, wants COMP) is the counterpart.
        Both must already hold what they're offering — the swap escrows real units, never credit
        it cannot see."""
        return atomic_swap(self.comp, self.ant, trade.seller, trade.buyer, trade.cc, trade.ant, now=now)
