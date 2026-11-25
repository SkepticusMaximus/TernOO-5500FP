#!/usr/bin/env python3
"""Localhost end-to-end demo of the CompuCoin ⇄ ANT exchange. No network, no value.

    python3 exchange/demo.py        (or  python3 -m exchange.demo)

Shows a reciprocal swap settle trustlessly through the order book + HTLC, then shows an aborted
swap refunding everyone. Watch the balances: no custodian account ever holds either side.
"""
from __future__ import annotations
import os
import sys
from fractions import Fraction

# make `python3 exchange/demo.py` work as well as `-m exchange.demo`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from exchange.currency import CompuCoin, AutonomiToken
from exchange.exchange import Exchange
from exchange.atomic_swap import atomic_swap


def bal(ex, who):
    return f"{who}: {ex.comp.balance(who)} COMP / {ex.ant.balance(who)} ANT"


def rule(t=""):
    print("\n" + t + "\n" + "─" * 68)


def main():
    rule("1 · A reciprocal swap, matched by the book and settled by an HTLC")
    comp = CompuCoin(); comp.mint_earn("Sol", 1000)       # Sol earned COMP for compute, wants ANT
    ant = AutonomiToken({"Vera": 100_000})                # Vera earned ANT for storage, wants COMP
    ex = Exchange(comp, ant)

    print("before        ", bal(ex, "Sol"), "|", bal(ex, "Vera"))
    print("Sol posts ASK : 120 COMP, wants ≥ 3 ANT per COMP")
    ex.submit("Sol", "ask", Fraction(3), 120, now=0)
    print("Vera posts BID: wants 120 COMP, pays up to 3 ANT per COMP  → crosses")
    trades = ex.submit("Vera", "bid", Fraction(3), 120, now=0)
    t = trades[0]
    print(f"  matched      : {t.cc} COMP ⇄ {t.ant} ANT  @ {t.price} ANT/COMP   settled={t.settled}")
    print("after         ", bal(ex, "Sol"), "|", bal(ex, "Vera"))
    assert ex.comp.total_supply() == 0 and ex.ant.total_supply() == 100_000, "supply must be conserved"
    print("  ✓ COMP net-zero preserved (0); ANT fixed supply preserved (100000)")

    rule("2 · The HTLC step by step (the crux: no custodian, atomic across two ledgers)")
    comp2 = CompuCoin(); comp2.mint_earn("Sol", 300)
    ant2 = AutonomiToken({"Vera": 1000})
    res = atomic_swap(comp2, ant2, "Sol", "Vera", 100, 300, now=0)
    for i, step in enumerate(res.trace, 1):
        print(f"  {i}. {step}")

    rule("3 · An aborted swap refunds everyone — the safety property")
    comp3 = CompuCoin(); comp3.mint_earn("Sol", 300)
    ant3 = AutonomiToken({"Vera": 1000})
    before = (comp3.balance("Sol"), ant3.balance("Vera"))
    res = atomic_swap(comp3, ant3, "Sol", "Vera", 100, 300, now=0, abort=True)
    for i, step in enumerate(res.trace, 1):
        print(f"  {i}. {step}")
    after = (comp3.balance("Sol"), ant3.balance("Vera"))
    print(f"  Sol COMP {before[0]}→{after[0]}, Vera ANT {before[1]}→{after[1]}   outcome={res.outcome}")
    assert before == after, "an abort must leave everyone exactly as they started"
    print("  ✓ nobody was exposed; both got their own funds back")

    rule("Done — localhost only, no network touched, no real value moved.")


if __name__ == "__main__":
    main()
