"""test_p2pcp_consensus.py — the block-lattice conflict-vote (§9). Step 6 core.

Offline and deterministic, like the ledger: fork detection, the burn-weighted
supermajority tally, resolution + slashing, and the honest limits (eclipse; bare
majority never decides). Real decayed-burn weights come from a real ledger.

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_consensus``
"""

import importlib.util as _ilu
import os
import queue
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


C = _load("p2pcp_consensus")
L = C.L                         # the consensus module's OWN ledger view (one instance)
D = _load("p2pcp_daemon")       # for the vote-over-the-wire test

NOW = 1_800_000_000
X = b"X" * 32                   # two conflicting record_ids, as vote choices
Y = b"Y" * 32
ACCT = b"a" * 32                # a nominal forked account id (for standalone votes)


def voter(tag: bytes):
    return L.Identity.from_seed(tag.ljust(32, b"\x00"))


def vote(who, choice, weights, w, account=ACCT, height=1):
    weights[who.account_id] = w
    return C.sign_vote(who, account, height, choice)


class TestForkDetection(unittest.TestCase):
    def _divergent_views(self):
        led = L.Ledger()
        a = voter(b"double-spender")
        led.open_account(a)
        chain = led.chains[a.account_id]
        # Two DIFFERENT records at the same next height = a fork (each self-signed).
        b1 = L.build_burn_record(a, chain, 1, NOW)
        b2 = L.build_burn_record(a, chain, 2, NOW)
        return a, list(chain.records) + [b1], list(chain.records) + [b2], b1, b2

    def test_detects_divergence(self):
        a, va, vb, b1, b2 = self._divergent_views()
        fork = C.detect_fork(va, vb)
        self.assertIsNotNone(fork)
        self.assertEqual(fork.account, a.account_id)
        self.assertEqual(fork.height, 1)
        self.assertEqual(set(fork.options), {b1.record_id(), b2.record_id()})

    def test_identical_views_no_fork(self):
        _a, va, _vb, _b1, _b2 = self._divergent_views()
        self.assertIsNone(C.detect_fork(va, va))

    def test_eclipse_single_view_sees_nothing(self):
        # The honest limit (§9.3): you cannot detect a conflict you are not shown.
        _a, va, _vb, _b1, _b2 = self._divergent_views()
        self.assertIsNone(C.detect_fork(va, va))     # only one side → nothing


class TestTally(unittest.TestCase):
    def test_supermajority_decides(self):
        w = {}
        votes = [vote(voter(b"1"), X, w, 5.0), vote(voter(b"2"), X, w, 3.0),
                 vote(voter(b"3"), Y, w, 1.0)]              # X=8/9 ≈ 89% ≥ ⅔
        self.assertEqual(C.tally(votes, w), X)

    def test_bare_majority_is_undecided(self):
        w = {}
        votes = [vote(voter(b"1"), X, w, 5.0), vote(voter(b"2"), Y, w, 4.0)]  # X=55%
        self.assertIsNone(C.tally(votes, w))           # a bare majority never decides

    def test_knife_edge_is_undecided(self):
        w = {}
        votes = [vote(voter(b"1"), X, w, 1.0), vote(voter(b"2"), Y, w, 1.0)]
        self.assertIsNone(C.tally(votes, w))

    def test_zero_weight_does_not_count(self):
        w = {}
        votes = [vote(voter(b"fresh"), X, w, 0.0)]      # newcomer, no burned weight
        self.assertIsNone(C.tally(votes, w))

    def test_whale_outweighs_headcount(self):
        w = {}
        votes = [vote(voter(b"whale"), X, w, 10.0)]
        for i in range(3):
            votes.append(vote(voter(b"small-%d" % i), Y, w, 1.0))
        self.assertEqual(C.tally(votes, w), X)          # 10/13 ≈ 77% — weight, not heads

    def test_sybil_split_manufactures_no_quorum(self):
        # 3 weight for X vs 2 for Y = 60% < ⅔ → undecided. Splitting the 3 into
        # three 1-weight identities changes nothing: weight is conserved (§10).
        w1 = {}
        one = [vote(voter(b"solid"), X, w1, 3.0), vote(voter(b"opp"), Y, w1, 2.0)]
        self.assertIsNone(C.tally(one, w1))
        w2 = {}
        split = [vote(voter(b"s0"), X, w2, 1.0), vote(voter(b"s1"), X, w2, 1.0),
                 vote(voter(b"s2"), X, w2, 1.0), vote(voter(b"opp"), Y, w2, 2.0)]
        self.assertIsNone(C.tally(split, w2))           # same weight, same (non-)decision

    def test_no_participation_is_undecided(self):
        self.assertIsNone(C.tally([], {}))              # optimistic wait (§9.4)

    def test_one_vote_per_voter(self):
        # A voter that double-votes is counted once (first seen).
        w = {}
        v = voter(b"flipflop")
        first = vote(v, X, w, 9.0)
        second = C.sign_vote(v, ACCT, 1, Y)             # same voter, other choice
        self.assertEqual(C.tally([first, second], w), X)


class TestResolveAndSlash(unittest.TestCase):
    def test_resolve_decides_and_slashes_double_spender(self):
        dsp = voter(b"cheat")
        fork = C.Fork(dsp.account_id, 1, tuple(sorted((X, Y))))
        w = {}
        votes = [vote(voter(b"h1"), X, w, 5.0), vote(voter(b"h2"), X, w, 3.0),
                 vote(voter(b"h3"), Y, w, 1.0)]
        slashed = set()
        self.assertEqual(C.resolve(fork, votes, w, slashed), X)
        self.assertIn(dsp.account_id, slashed)          # double-spend → franchise gone

    def test_undecided_does_not_slash(self):
        dsp = voter(b"cheat2")
        fork = C.Fork(dsp.account_id, 1, tuple(sorted((X, Y))))
        w = {}
        votes = [vote(voter(b"a"), X, w, 1.0), vote(voter(b"b"), Y, w, 1.0)]
        slashed = set()
        self.assertIsNone(C.resolve(fork, votes, w, slashed))
        self.assertNotIn(dsp.account_id, slashed)

    def test_forged_vote_is_not_counted(self):
        w = {}
        v = voter(b"forger")
        bad = vote(v, X, w, 100.0)
        bad.sig = b"\x00" * 64                          # invalid signature
        self.assertFalse(C.verify_vote(bad))
        fork = C.Fork(voter(b"z").account_id, 1, tuple(sorted((X, Y))))
        self.assertIsNone(C.resolve(fork, [bad], w, set()))   # forged vote ignored

    def test_slashed_weight_is_dropped(self):
        v = voter(b"gone")
        w = {v.account_id: 5.0}
        self.assertEqual(C.effective_weights(w, {v.account_id}), {})


class TestFranchiseFromLedger(unittest.TestCase):
    def test_weights_come_from_real_decayed_burn(self):
        led = L.Ledger()
        a, cust = voter(b"worker"), voter(b"cust")
        led.open_account(a)
        led.open_account(cust)
        led.settle_work(a, cust, 10)                    # a earns weight-bearing credit
        led.burn(a, 5, timestamp=NOW, now=NOW)          # ...and burns for weight
        weights = C.ledger_weights(led, NOW)
        self.assertIn(a.account_id, weights)
        self.assertGreater(weights[a.account_id], 0.0)
        self.assertNotIn(cust.account_id, weights)      # never burned → no vote

    def test_slash_forged_receipt(self):
        w_id, r_id = voter(b"w"), voter(b"r")
        slashed = set()
        honest = L.make_receipt(w_id, r_id, 5, b"job", b"OUT",
                                vclass=L.VCLASS_NATIVE, nonce=b"n" * 16)
        self.assertFalse(C.slash_forged_receipt(honest, b"OUT", slashed))
        self.assertNotIn(w_id.account_id, slashed)
        forged = L.make_receipt(w_id, r_id, 5, b"job", b"LIE",
                                vclass=L.VCLASS_NATIVE, nonce=b"n" * 16)
        self.assertTrue(C.slash_forged_receipt(forged, b"OUT", slashed))
        self.assertIn(w_id.account_id, slashed)

    def test_vote_signature_authenticity(self):
        v = voter(b"honest")
        good = C.sign_vote(v, ACCT, 1, X)
        self.assertTrue(C.verify_vote(good))
        good.choice = Y                                 # tamper after signing
        self.assertFalse(C.verify_vote(good))


class TestVoteOverWire(unittest.TestCase):
    """A signed vote crosses the one organ, and only a valid one is collected."""

    def test_signed_vote_crosses_and_is_collected(self):
        a = D.Daemon(voter(b"voter-A"))
        b = D.Daemon(voter(b"voter-B"))
        addr = b.start()
        try:
            v = a.cast_vote(ACCT, 1, X)
            a.send_vote(addr[0], addr[1], v)
            got = b.next_vote(timeout=5.0)
            self.assertEqual(got.choice, X)
            self.assertEqual(got.voter, a.account_id)
            self.assertTrue(C.verify_vote(got))
        finally:
            b.stop()

    def test_forged_vote_over_wire_is_dropped(self):
        a = D.Daemon(voter(b"voter-A2"))
        b = D.Daemon(voter(b"voter-B2"))
        addr = b.start()
        try:
            v = a.cast_vote(ACCT, 1, X)
            v.sig = b"\x00" * 64                        # forge after signing
            a.send_vote(addr[0], addr[1], v)
            with self.assertRaises(queue.Empty):        # never collected (§9)
                b.next_vote(timeout=0.5)
        finally:
            b.stop()


if __name__ == "__main__":
    unittest.main()
