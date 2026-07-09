"""test_p2pcp_socket.py — the socket organ, driven over loopback.

Spec §1.5/§14 step 4. Every test reaches the wire THROUGH the organ — this file
imports `p2pcp_socket`, never `socket` (the one-organ boundary, enforced by
test_network_boundary.py, applies to tests too). The framing guards are pure
functions, so the oversized-frame refusal is proven without a socket at all.

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_socket``
"""

import importlib.util as _ilu
import os
import queue
import threading
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load("p2pcp_socket")


def serve_one(organ, handler, errq):
    """Accept a single peer and run `handler(peer)` in a thread; any exception
    lands on `errq` so the test can surface it deterministically."""
    def _run():
        try:
            peer = organ.accept(timeout=5.0)
            try:
                handler(peer)
            finally:
                peer.close()
        except Exception as e:                       # noqa: BLE001 — surfaced
            errq.put(e)
    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return t


class TestFramingPure(unittest.TestCase):
    """The length cap, proven with no socket in sight (§13)."""

    def test_encode_frame_caps_oversized_payload(self):
        with self.assertRaises(P.FrameError):
            P.encode_frame(b"x" * (P.MAX_FRAME + 1))

    def test_read_frame_rejects_oversized_declared_length(self):
        # A lying length prefix must be refused BEFORE the body is read — no
        # gigabyte allocation on an attacker's say-so.
        prefix = (P.MAX_FRAME + 1).to_bytes(4, "big")
        reads = []

        def fake_read(n):
            reads.append(n)
            return prefix if n == 4 else b"x" * n

        with self.assertRaises(P.FrameError):
            P.read_frame(fake_read)
        self.assertEqual(reads, [4])                 # body was never requested

    def test_roundtrip_pure(self):
        payload = b"self-describing words go here"
        framed = P.encode_frame(payload)
        it = iter([framed[:4], framed[4:]])
        self.assertEqual(P.read_frame(lambda n: next(it)), payload)


class TestOrganLoopback(unittest.TestCase):
    """The organ moving real bytes over 127.0.0.1 — today's testnet substrate."""

    def setUp(self):
        self.server = P.SocketOrgan()
        self.host, self.port = self.server.listen("127.0.0.1", 0)
        self.errq = queue.Queue()

    def tearDown(self):
        self.server.close()

    def _dial(self):
        return P.SocketOrgan().connect(self.host, self.port, timeout=5.0)

    def test_frame_roundtrip(self):
        t = serve_one(self.server, lambda p: p.send(p.recv(timeout=5.0)), self.errq)
        with self._dial() as peer:
            peer.send(b"pack up your tribbles")
            self.assertEqual(peer.recv(timeout=5.0), b"pack up your tribbles")
        t.join(5.0)
        self.assertTrue(self.errq.empty(), self.errq.queue)

    def test_framing_preserves_message_boundaries(self):
        def handler(p):
            p.send(p.recv(timeout=5.0))
            p.send(p.recv(timeout=5.0))
        t = serve_one(self.server, handler, self.errq)
        with self._dial() as peer:
            peer.send(b"first")
            peer.send(b"second")
            self.assertEqual(peer.recv(timeout=5.0), b"first")
            self.assertEqual(peer.recv(timeout=5.0), b"second")
        t.join(5.0)
        self.assertTrue(self.errq.empty(), self.errq.queue)

    def test_empty_frame_roundtrips(self):
        t = serve_one(self.server, lambda p: p.send(p.recv(timeout=5.0)), self.errq)
        with self._dial() as peer:
            peer.send(b"")
            self.assertEqual(peer.recv(timeout=5.0), b"")
        t.join(5.0)
        self.assertTrue(self.errq.empty(), self.errq.queue)

    def test_trustless_accept_takes_any_stranger(self):
        # No registration, no allow-list: a stranger connects and is accepted
        # (§2.1). remote is informational only, never a trust signal.
        got = {}
        t = serve_one(self.server, lambda p: got.setdefault("remote", p.remote),
                      self.errq)
        with self._dial() as peer:
            peer.send(b"hello stranger")
        t.join(5.0)
        self.assertTrue(self.errq.empty(), self.errq.queue)
        self.assertIsInstance(got.get("remote"), tuple)

    def test_peer_closed_mid_stream_detected(self):
        # Server accepts then closes without sending — the dialer's recv must
        # raise, not hang or return garbage.
        t = serve_one(self.server, lambda p: None, self.errq)   # closes on exit
        with self._dial() as peer:
            with self.assertRaises(P.OrganError):
                peer.recv(timeout=5.0)
        t.join(5.0)

    def test_accept_timeout_raises(self):
        idle = P.SocketOrgan()
        idle.listen("127.0.0.1", 0)
        try:
            with self.assertRaises(P.OrganTimeout):
                idle.accept(timeout=0.15)
        finally:
            idle.close()

    def test_connect_refused_is_clean_error(self):
        # Dial the server's port AFTER closing it → a clean OrganError, never a
        # bare socket exception leaking past the organ boundary.
        self.server.close()
        with self.assertRaises(P.OrganError):
            P.SocketOrgan().connect(self.host, self.port, timeout=1.0)


if __name__ == "__main__":
    unittest.main()
