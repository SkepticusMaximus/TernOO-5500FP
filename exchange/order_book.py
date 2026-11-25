#!/usr/bin/env python3
"""A limit order book for the COMP/ANT market — price discovery, Austrian by construction.

A maker posts the ratio it will accept and a size; it is never *told* a price. A taker that
crosses the book trades at the MAKER's resting price. The book only reports where willingness
meets willingness — no authority sets value, buyers decide how much they'll part with. That is
the captain's requirement ("buyers don't fix the price, they decide how much they'll exchange")
expressed as a matching rule.

Price is carried as an exact `Fraction`: ANT base units per COMP base unit. Matching is done in
base units, so decimals (9 for COMP, 18 for ANT) are metadata, not arithmetic — the differential
harness records the difference without the book having to care about it.
"""
from __future__ import annotations
from dataclasses import dataclass
from fractions import Fraction


@dataclass
class Order:
    owner: str
    side: str          # "bid" (wants COMP, gives ANT) | "ask" (gives COMP, wants ANT)
    price: Fraction    # ANT base units per COMP base unit
    size_cc: int       # COMP base units
    oid: int = 0


@dataclass
class Trade:
    buyer: str         # receives COMP, gives ANT
    seller: str        # gives COMP, receives ANT
    cc: int            # COMP base units
    ant: int           # ANT base units
    price: Fraction
    settled: bool | None = None


class OrderBook:
    def __init__(self):
        self.bids: list[Order] = []   # resting buyers  (want COMP, give ANT)
        self.asks: list[Order] = []   # resting sellers (give COMP, want ANT)
        self._seq = 0

    def _next(self) -> int:
        self._seq += 1
        return self._seq

    def submit(self, owner: str, side: str, price, size_cc: int) -> list[Trade]:
        """Insert an order, match it against the resting book, return the trades produced. A
        leftover remainder rests. Clearing is at the maker's (resting order's) price."""
        if side not in ("bid", "ask"):
            raise ValueError("side must be 'bid' or 'ask'")
        if size_cc <= 0:
            raise ValueError("size must be positive")
        order = Order(owner, side, Fraction(price), size_cc, self._next())
        trades: list[Trade] = []

        book = self.asks if side == "bid" else self.bids
        # best maker first: lowest ask for an incoming bid, highest bid for an incoming ask
        book.sort(key=lambda m: m.price, reverse=(side == "ask"))

        def crosses(m: Order) -> bool:
            return (m.price <= order.price) if side == "bid" else (m.price >= order.price)

        while order.size_cc > 0 and book and crosses(book[0]):
            m = book[0]
            qty = min(order.size_cc, m.size_cc)
            clearing = m.price                     # maker price
            ant = int(qty * clearing)              # base-unit ANT (floor); pick clean ratios in tests
            if side == "bid":
                buyer, seller = order.owner, m.owner
            else:
                buyer, seller = m.owner, order.owner
            trades.append(Trade(buyer, seller, qty, ant, clearing))
            order.size_cc -= qty
            m.size_cc -= qty
            if m.size_cc == 0:
                book.pop(0)                        # maker fully filled
            # if the maker survives, the taker is exhausted and the loop ends

        if order.size_cc > 0:
            (self.bids if side == "bid" else self.asks).append(order)
        return trades

    def depth(self) -> dict:
        return {"bids": [(str(o.price), o.size_cc) for o in sorted(self.bids, key=lambda o: -o.price)],
                "asks": [(str(o.price), o.size_cc) for o in sorted(self.asks, key=lambda o: o.price)]}
