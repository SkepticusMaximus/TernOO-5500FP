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
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


D = _load("p2pcp_daemon")
L = D.L

ACCT = b"a" * 32
X = b"X" * 32


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


if __name__ == "__main__":
    unittest.main()
