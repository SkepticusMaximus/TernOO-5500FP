"""test_p2pcp_gossip.py — the mesh gossip substrate (v0.2 slice 1).

v0.1 was strictly point-to-point; v0.2 makes a node reach a SET of peers and
discover the mesh from a seed. Proven over loopback: a vote broadcast reaches
every peer in the book; a node learns unknown peers by asking one it already
knows; and the two compose — seed → discover → broadcast-to-all.

Imports the daemon, never `socket` (the one-organ boundary).

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_gossip``
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


D = _load("p2pcp_daemon")
L = D.L
C = D.C                         # consensus (Fork) — the daemon's own view

ACCT = b"a" * 32
X = b"X" * 32
Y = b"Y" * 32                   # the two conflicting fork branches (vote choices)


def ident(tag: bytes):
    return L.Identity.from_seed(tag.ljust(32, b"\x00"))


class TestBroadcast(unittest.TestCase):
    def test_broadcast_reaches_all_peers(self):
        b = D.Daemon(ident(b"B"))
        c = D.Daemon(ident(b"C"))
        a = D.Daemon(ident(b"A"))
        b_addr, c_addr = b.start(), c.start()
        try:
            a.add_peer(*b_addr)
            a.add_peer(*c_addr)
            v = a.cast_vote(ACCT, 1, X)
            self.assertEqual(a.broadcast_vote(v), 2)         # fan-out to both
            self.assertEqual(b.next_vote(5.0).choice, X)
            self.assertEqual(c.next_vote(5.0).choice, X)
        finally:
            b.stop()
            c.stop()
            a.stop()

    def test_never_books_self(self):
        d = D.Daemon(ident(b"solo"))
        addr = d.start()
        try:
            d.add_peer(*addr)                                # our own address
            self.assertNotIn(addr, d.known_peers())
        finally:
            d.stop()

    def test_dead_peer_is_skipped_not_fatal(self):
        live = D.Daemon(ident(b"live"))
        a = D.Daemon(ident(b"caller"))
        live_addr = live.start()
        try:
            a.add_peer(*live_addr)
            a.add_peer("127.0.0.1", 1)                       # nothing listens here
            reached = a.broadcast_vote(a.cast_vote(ACCT, 1, X))
            self.assertEqual(reached, 1)                     # the live one only
            self.assertEqual(live.next_vote(5.0).choice, X)
        finally:
            live.stop()
            a.stop()


class TestDiscovery(unittest.TestCase):
    def test_peer_discovery_via_exchange(self):
        c = D.Daemon(ident(b"Cd"))
        b = D.Daemon(ident(b"Bd"))
        a = D.Daemon(ident(b"Ad"))
        c_addr, b_addr = c.start(), b.start()
        b.add_peer(*c_addr)                                  # B knows C
        try:
            learned = a.fetch_peers(*b_addr)                 # A asks B...
            self.assertIn(c_addr, a.known_peers())           # ...and learns C
            self.assertIn(c_addr, learned)
            self.assertIn(b_addr, a.known_peers())           # learns B itself too
        finally:
            b.stop()
            c.stop()
            a.stop()

    def test_seed_then_discover_then_broadcast(self):
        # The whole substrate composing: A seeded with only B discovers C, then a
        # single broadcast reaches the whole mesh it just learned.
        c = D.Daemon(ident(b"Cx"))
        b = D.Daemon(ident(b"Bx"))
        a = D.Daemon(ident(b"Ax"))
        c_addr, b_addr = c.start(), b.start()
        b.add_peer(*c_addr)
        try:
            a.add_peer(*b_addr)                              # seed: B only
            a.fetch_peers(*b_addr)                           # discover: + C
            reached = a.broadcast_vote(a.cast_vote(ACCT, 1, X))
            self.assertGreaterEqual(reached, 2)
            self.assertEqual(b.next_vote(5.0).choice, X)
            self.assertEqual(c.next_vote(5.0).choice, X)
        finally:
            b.stop()
            c.stop()
            a.stop()


class TestGossipFlood(unittest.TestCase):
    """Relay + dedup — the actual gossip (v0.2 slice 2)."""

    def test_relay_reaches_non_adjacent_node(self):
        # Line A → B → C. A knows only B; C knows nobody. A originates a vote to
        # B; B RELAYS it to C. C hears it though A never contacted C — the flood.
        c = D.Daemon(ident(b"gc"))
        b = D.Daemon(ident(b"gb"))
        a = D.Daemon(ident(b"ga"))
        c_addr, b_addr = c.start(), b.start()
        b.add_peer(*c_addr)                              # B → C
        try:
            a.add_peer(*b_addr)                          # A → B only
            a.broadcast_vote(a.cast_vote(ACCT, 1, X))
            self.assertEqual(b.next_vote(5.0).choice, X)
            self.assertEqual(c.next_vote(5.0).choice, X)  # reached purely by relay
        finally:
            b.stop()
            c.stop()
            a.stop()

    def test_duplicate_vote_is_deduped(self):
        # The same vote delivered twice is collected ONCE — dedup stops the storm.
        b = D.Daemon(ident(b"gd-b"))
        a = D.Daemon(ident(b"gd-a"))
        b_addr = b.start()
        try:
            a.add_peer(*b_addr)
            v = a.cast_vote(ACCT, 1, X)
            a.broadcast_vote(v)
            self.assertEqual(b.next_vote(5.0).choice, X)  # collected once
            a.broadcast_vote(v)                           # same vote again
            with self.assertRaises(queue.Empty):          # ...not collected twice
                b.next_vote(0.5)
        finally:
            b.stop()
            a.stop()


class TestQuorumAssembly(unittest.TestCase):
    """Distributed fork resolution (v0.2 slice 3): votes gossip to a collector,
    which assembles the quorum from what it HEARD (no polling) and resolves with
    the step-6 tally."""

    def _hub_and_voters(self, hub_tag, voter_tags):
        hub = D.Daemon(ident(hub_tag))
        hub_addr = hub.start()
        voters = [D.Daemon(ident(t)) for t in voter_tags]
        for v in voters:
            v.add_peer(*hub_addr)
        return hub, voters

    def test_hub_assembles_quorum_and_resolves(self):
        hub, (v1, v2, v3) = self._hub_and_voters(b"hub", [b"qv1", b"qv2", b"qv3"])
        try:
            weights = {v1.account_id: 5.0, v2.account_id: 3.0, v3.account_id: 1.0}
            v1.announce_fork(ACCT, 1, X)             # X: 5
            v2.announce_fork(ACCT, 1, X)             # X: +3 = 8
            v3.announce_fork(ACCT, 1, Y)             # Y: 1
            for _ in range(3):                       # wait until the hub heard all 3
                hub.next_vote(5.0)
            self.assertEqual(len(hub.votes_for(ACCT, 1)), 3)
            fork = C.Fork(ACCT, 1, tuple(sorted((X, Y))))
            slashed = set()
            self.assertEqual(hub.resolve_fork(fork, weights, slashed), X)  # 8/9 ≥ ⅔
            self.assertIn(ACCT, slashed)             # the fork's author is slashed
        finally:
            hub.stop()
            for v in (v1, v2, v3):
                v.stop()

    def test_dead_heat_is_undecided(self):
        hub, (v1, v2) = self._hub_and_voters(b"hub2", [b"uv1", b"uv2"])
        try:
            weights = {v1.account_id: 5.0, v2.account_id: 5.0}
            v1.announce_fork(ACCT, 1, X)
            v2.announce_fork(ACCT, 1, Y)
            for _ in range(2):
                hub.next_vote(5.0)
            fork = C.Fork(ACCT, 1, tuple(sorted((X, Y))))
            slashed = set()
            self.assertIsNone(hub.resolve_fork(fork, weights, slashed))  # 50/50
            self.assertNotIn(ACCT, slashed)          # nothing decided → no slash
        finally:
            hub.stop()
            for v in (v1, v2):
                v.stop()


if __name__ == "__main__":
    unittest.main()
