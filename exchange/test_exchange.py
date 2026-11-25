#!/usr/bin/env python3
"""Differential conformance + plumbing tests for the CompuCoin ⇄ ANT exchange testbed.

Run from the repo root:   python3 -m unittest exchange.test_exchange

The `CurrencyConformance` mixin is the captain's rule of thumb made concrete: ONE suite, run over
BOTH currencies. The tests that pass on both are the inheritable core of the object model; the
`test_domain_differences` case pins where the two deliberately diverge (supply model, decimals,
overdraft). Then the atomic-swap and exchange tests prove the trustless settlement plumbing.
"""
from __future__ import annotations
import unittest
from fractions import Fraction

from exchange.currency import CompuCoin, AutonomiToken, new_secret, sha256_hex
from exchange.atomic_swap import atomic_swap
from exchange.exchange import Exchange


# ---------------------------------------------------------------------------
# One suite, run over BOTH currencies — "test the plumbing over both".
# ---------------------------------------------------------------------------
class CurrencyConformance:
    """Shared contract every Currency must honour. Subclasses supply a funded instance with
    accounts 'alice' and 'bob' each holding 1000 base units."""

    def make(self):                       # -> (currency, start_total)
        raise NotImplementedError

    def setUp(self):
        self.cur, self.start_total = self.make()

    def test_funded_start(self):
        self.assertEqual(self.cur.balance("alice"), 1000)
        self.assertEqual(self.cur.balance("bob"), 1000)

    def test_transfer_conserves_supply(self):
        t0 = self.cur.total_supply()
        self.cur.transfer("alice", "bob", 100)
        self.assertEqual(self.cur.balance("alice"), 900)
        self.assertEqual(self.cur.balance("bob"), 1100)
        self.assertEqual(self.cur.total_supply(), t0)   # supply is conserved across a transfer

    def test_htlc_claim_pays_beneficiary(self):
        t0 = self.cur.total_supply()
        pre, H = new_secret()
        lk = self.cur.lock("alice", "bob", 300, H, 100, now=0)
        self.assertEqual(self.cur.total_supply(), t0)   # conserved mid-escrow
        self.assertEqual(self.cur.balance("alice"), 700)
        self.assertTrue(self.cur.claim(lk, pre, now=1))
        self.assertEqual(self.cur.balance("bob"), 1300)
        self.assertEqual(self.cur.lock_status(lk), "claimed")
        self.assertEqual(self.cur.total_supply(), t0)

    def test_htlc_refund_returns_to_owner(self):
        t0 = self.cur.total_supply()
        pre, H = new_secret()
        lk = self.cur.lock("alice", "bob", 300, H, 10, now=0)
        self.assertTrue(self.cur.refund(lk, now=11))
        self.assertEqual(self.cur.balance("alice"), 1000)
        self.assertEqual(self.cur.lock_status(lk), "refunded")
        self.assertEqual(self.cur.total_supply(), t0)

    def test_claim_wrong_preimage_rejected(self):
        _, H = new_secret()
        wrong, _ = new_secret()
        lk = self.cur.lock("alice", "bob", 100, H, 100, now=0)
        with self.assertRaises(ValueError):
            self.cur.claim(lk, wrong, now=1)

    def test_claim_after_expiry_rejected(self):
        pre, H = new_secret()
        lk = self.cur.lock("alice", "bob", 100, H, 10, now=0)
        with self.assertRaises(ValueError):
            self.cur.claim(lk, pre, now=11)        # expired → only refund is possible

    def test_refund_before_expiry_rejected(self):
        _, H = new_secret()
        lk = self.cur.lock("alice", "bob", 100, H, 10, now=0)
        with self.assertRaises(ValueError):
            self.cur.refund(lk, now=5)

    def test_cannot_escrow_more_than_held(self):
        _, H = new_secret()
        with self.assertRaises(ValueError):
            self.cur.lock("alice", "bob", 10_000, H, 100, now=0)


class TestCompuCoinConforms(CurrencyConformance, unittest.TestCase):
    def make(self):
        c = CompuCoin()
        c.mint_earn("alice", 1000)
        c.mint_earn("bob", 1000)
        return c, c.total_supply()          # net-zero → 0


class TestAutonomiConforms(CurrencyConformance, unittest.TestCase):
    def make(self):
        a = AutonomiToken({"alice": 1000, "bob": 1000})
        return a, a.total_supply()          # fixed → 2000


# ---------------------------------------------------------------------------
# Where the two domains deliberately diverge — the map of seams.
# ---------------------------------------------------------------------------
class TestDomainDifferences(unittest.TestCase):
    def test_overdraft_only_in_mutual_credit(self):
        comp = CompuCoin(); comp.mint_earn("alice", 1000)
        comp.transfer("alice", "bob", 5000)             # mutual credit: sender may go negative
        self.assertEqual(comp.balance("alice"), -4000)
        self.assertEqual(comp.total_supply(), 0)        # …and the net is still zero

        ant = AutonomiToken({"alice": 1000})
        with self.assertRaises(ValueError):             # fixed supply: overdraft forbidden
            ant.transfer("alice", "bob", 5000)

    def test_supply_models_and_decimals_differ(self):
        self.assertEqual(CompuCoin().supply_model, "net-zero-mutual-credit")
        self.assertEqual(AutonomiToken().supply_model, "fixed-supply")
        self.assertEqual(CompuCoin().decimals, 9)
        self.assertEqual(AutonomiToken().decimals, 18)
        self.assertTrue(CompuCoin().allows_overdraft)
        self.assertFalse(AutonomiToken().allows_overdraft)


# ---------------------------------------------------------------------------
# The crux: trustless cross-ledger settlement.
# ---------------------------------------------------------------------------
class TestAtomicSwap(unittest.TestCase):
    def _mkt(self):
        comp = CompuCoin(); comp.mint_earn("alice", 500)      # Alice holds COMP, wants ANT
        ant = AutonomiToken({"bob": 1000})                    # Bob holds ANT, wants COMP
        return comp, ant

    def test_swap_settles_both_legs(self):
        comp, ant = self._mkt()
        res = atomic_swap(comp, ant, "alice", "bob", 100, 300, now=0)
        self.assertTrue(res.ok)
        self.assertEqual(res.outcome, "settled")
        self.assertEqual(comp.balance("alice"), 400)          # gave 100 COMP
        self.assertEqual(comp.balance("bob"), 100)            # got 100 COMP
        self.assertEqual(ant.balance("bob"), 700)             # gave 300 ANT
        self.assertEqual(ant.balance("alice"), 300)           # got 300 ANT
        self.assertEqual(comp.total_supply(), 0)
        self.assertEqual(ant.total_supply(), 1000)

    def test_abort_refunds_everyone(self):
        comp, ant = self._mkt()
        res = atomic_swap(comp, ant, "alice", "bob", 100, 300, now=0, abort=True)
        self.assertFalse(res.ok)
        self.assertEqual(res.outcome, "refunded")
        self.assertEqual(comp.balance("alice"), 500)          # nobody lost anything
        self.assertEqual(comp.balance("bob"), 0)
        self.assertEqual(ant.balance("bob"), 1000)
        self.assertEqual(ant.balance("alice"), 0)


# ---------------------------------------------------------------------------
# Book + settlement assembled.
# ---------------------------------------------------------------------------
class TestExchange(unittest.TestCase):
    def _ex(self):
        comp = CompuCoin(); comp.mint_earn("seller", 1000)
        ant = AutonomiToken({"buyer": 100_000})
        return Exchange(comp, ant)

    def test_crossing_orders_match_and_settle(self):
        ex = self._ex()
        ex.submit("seller", "ask", Fraction(3), 100, now=0)   # rests: 100 COMP at >=3 ANT/COMP
        trades = ex.submit("buyer", "bid", Fraction(3), 100, now=0)  # crosses
        self.assertEqual(len(trades), 1)
        t = trades[0]
        self.assertEqual((t.cc, t.ant), (100, 300))
        self.assertTrue(t.settled)
        self.assertEqual(ex.comp.balance("seller"), 900)
        self.assertEqual(ex.comp.balance("buyer"), 100)
        self.assertEqual(ex.ant.balance("buyer"), 99_700)
        self.assertEqual(ex.ant.balance("seller"), 300)

    def test_non_crossing_orders_rest(self):
        ex = self._ex()
        ex.submit("seller", "ask", Fraction(5), 100, now=0)   # wants >=5
        trades = ex.submit("buyer", "bid", Fraction(3), 100, now=0)  # offers <=3 → no cross
        self.assertEqual(trades, [])
        self.assertEqual(len(ex.book.asks), 1)
        self.assertEqual(len(ex.book.bids), 1)

    def test_clearing_at_maker_price(self):
        ex = self._ex()
        ex.submit("seller", "ask", Fraction(2), 100, now=0)   # maker rests at 2
        trades = ex.submit("buyer", "bid", Fraction(4), 100, now=0)  # willing up to 4, trades at 2
        self.assertEqual(trades[0].ant, 200)                  # 100 COMP * 2 = 200 ANT (maker price)


if __name__ == "__main__":
    unittest.main(verbosity=2)
