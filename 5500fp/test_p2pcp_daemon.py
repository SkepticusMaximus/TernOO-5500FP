"""test_p2pcp_daemon.py — the daemon skeleton: HELLO over the wire (§4/§14 step 4).

Two daemons on loopback complete a signed HELLO and each ends holding the other's
VERIFIED account_id — identity established over the wire, by signature, with no
trust granted by the socket (§2.1). Plus the refusal paths: forged signature,
wrong type, unknown/unimplemented alg. Imports the daemon and ledger, never
`socket` (the one-organ boundary).

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_daemon``
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
L = D.L                        # the daemon's OWN ledger module — one instance, so
#                             # isinstance and exception classes match across the two


def ident(tag: bytes):
    return L.Identity.from_seed(tag.ljust(32, b"\x00"))


class TestHandshake(unittest.TestCase):
    """Identity over the wire — trustless, signature-verified."""

    def test_two_daemons_exchange_verified_hellos(self):
        a = D.Daemon(ident(b"node-A"))
        b = D.Daemon(ident(b"node-B"))
        addr = a.start()
        try:
            # B dials A and completes the outbound HELLO, learning A's id.
            verified_a = b.connect(*addr)
            self.assertEqual(verified_a, a.account_id)
            # A's accept loop completes the inbound HELLO, learning B's id.
            learned_b = a.next_verified_peer(timeout=5.0)
            self.assertEqual(learned_b, b.account_id)
            # Each holds the other, keyed by verified account_id.
            self.assertIn(b.account_id, a.peers())
            self.assertIn(a.account_id, b.peers())
        finally:
            a.stop()
            b.stop()

    def test_a_third_stranger_is_also_accepted(self):
        # Trustless: no allow-list. A second, unrelated node connects and is
        # verified just the same (§2.1).
        a = D.Daemon(ident(b"hub"))
        addr = a.start()
        c = D.Daemon(ident(b"stranger"))
        try:
            self.assertEqual(c.connect(*addr), a.account_id)
            self.assertEqual(a.next_verified_peer(timeout=5.0), c.account_id)
        finally:
            a.stop()
            c.stop()


class TestHandshakeRefusals(unittest.TestCase):
    """A HELLO must prove key control; anything less is dropped cleanly."""

    def setUp(self):
        self.d = D.Daemon(ident(b"verifier"))

    def _frame(self, account_hex, signer, alg=L.ALG_ED25519, mtype=D.HELLO_TYPE):
        msg = {"type": mtype, "account": account_hex,
               "nonce": os.urandom(16).hex(), "alg": alg}
        sig = signer.sign(D._canon(msg), alg) if signer is not None else b"\x00" * 64
        return D._canon({"msg": msg, "sig": sig.hex()})

    def test_valid_hello_verifies(self):
        who = ident(b"honest")
        account = self.d._verify_hello(self._frame(who.account_id.hex(), who))
        self.assertEqual(account, who.account_id)

    def test_forged_signature_rejected(self):
        # Attacker announces the victim's account but can only sign with its own.
        victim, attacker = ident(b"victim"), ident(b"attacker")
        frame = self._frame(victim.account_id.hex(), attacker)   # wrong key
        with self.assertRaises(D.HandshakeError):
            self.d._verify_hello(frame)

    def test_wrong_type_rejected(self):
        who = ident(b"honest")
        frame = self._frame(who.account_id.hex(), who, mtype="NOT-A-HELLO")
        with self.assertRaises(D.HandshakeError):
            self.d._verify_hello(frame)

    def test_unknown_alg_refused_gracefully(self):
        # You cannot even SIGN with an unknown alg (the signer refuses too), so a
        # forger sends a dummy sig; the verifier rejects on get_alg(7) first.
        who = ident(b"honest")
        frame = self._frame(who.account_id.hex(), None, alg=7)
        with self.assertRaises(D.HandshakeError):     # UnknownAlg → HandshakeError
            self.d._verify_hello(frame)

    def test_unimplemented_alg_refused_gracefully(self):
        who = ident(b"honest")
        # alg=1 is recognized-but-stub; its verify raises AlgUnimplemented, which
        # the handshake turns into a clean refusal, not a crash.
        frame = self._frame(who.account_id.hex(), None, alg=L.ALG_TERNARY_NATIVE)
        with self.assertRaises(D.HandshakeError):
            self.d._verify_hello(frame)

    def test_malformed_frame_rejected(self):
        with self.assertRaises(D.HandshakeError):
            self.d._verify_hello(b"{not json at all")


class TestDaemonWiring(unittest.TestCase):
    """The daemon owns keys + ledger + organ (RFC §4)."""

    def test_owns_identity_and_ledger(self):
        idn = ident(b"solo")
        d = D.Daemon(idn)
        self.assertEqual(d.account_id, idn.account_id)
        self.assertIsInstance(d.ledger, L.Ledger)

    def test_start_stop_is_clean(self):
        d = D.Daemon(ident(b"cycle"))
        addr = d.start()
        self.assertEqual(addr[0], "127.0.0.1")
        self.assertIsInstance(addr[1], int)
        d.stop()
        d.stop()                                       # idempotent, no hang


if __name__ == "__main__":
    unittest.main()
