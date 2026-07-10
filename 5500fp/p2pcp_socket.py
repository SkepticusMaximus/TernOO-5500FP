"""p2pcp_socket.py — THE socket organ. The one network limb (spec §1.5).

P2PCP reference implementation, build step 4 (§14). This is the I/O primary's
first citizen: the host network stack used as a PERIPHERAL behind one narrow,
auditable TernOO-shaped organ. Engelbart's framing, made literal — the network
is the operator's limb hanging off one controlling organ, never the master's
leash.

**This is the ONLY module in the whole tree permitted to import `socket`.**
`test_network_boundary.py` walks the imports and enforces it (allow-list ≤ 1).
Everything else — the daemon, the worker adapters, the tests — reaches the wire
THROUGH this organ, so a second network surface cannot appear unnoticed.

Design invariants (all from the spec, none negotiable here):
  * **Trustless (§2.1).** `accept()` takes ANY inbound connection. There is no
    peer allow-list, no "known hosts", no friends mode — trust is established
    ABOVE, by signature and burn-weight (the ledger), never by the socket.
    Strangers are the point.
  * **ONE mode (§2.2).** The organ binds and dials the same way always. No
    trusted tier, no dev/LAN variant that could become a downgrade target.
  * **Framed transport.** Length-prefixed frames (4-byte big-endian length +
    payload). The payload is OPAQUE here — the wire contract (step 5) puts
    self-describing TernOO words in it. The organ moves bytes; it reads none.
  * **Bounded (§13).** A frame length is capped (MAX_FRAME) and rejected before
    a byte is allocated — the first line against resource-exhaustion spam.
  * **No host-FS, no wall-clock in logic.** Timeouts are passed in.

Loopback (127.0.0.1) is today's substrate — the testnet-of-two on one box until
the second machine arrives. The wire is byte-identical for a remote peer.

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import socket   # the SINGLE permitted network import in the entire tree (§1.5)
import struct

SPEC_FILE = "docs/P2PCP-v0.1-SPEC.md"

# A frame length cap. 1 MiB is generous for a wire-contract frame of words; it
# exists to refuse an oversized declared length before allocating (§13).
MAX_FRAME: int = 1 << 20

_LEN = struct.Struct(">I")          # 4-byte unsigned big-endian length prefix


# ═══════════════════════════════════════════════════════════════════════════
# Errors — every failure is a clean P2PCP exception, so a caller never has to
# import `socket` to catch one (that would breach the one-organ boundary).
# ═══════════════════════════════════════════════════════════════════════════

class OrganError(Exception):
    """Base for every socket-organ failure. Wraps the underlying OSError so no
    caller needs to import `socket` to handle it (§1.5)."""


class FrameError(OrganError):
    """A malformed or oversized frame — declared length exceeds MAX_FRAME, or a
    payload too large to send. Rejected before allocation (§13)."""


class OrganTimeout(OrganError):
    """A blocking op exceeded its timeout (wraps socket.timeout)."""


class PeerClosed(OrganError):
    """The remote closed the connection mid-frame."""


# ═══════════════════════════════════════════════════════════════════════════
# Framing — pure functions, so the length cap is testable WITHOUT a socket
# (the test tree may not import `socket`). encode_frame caps the send side;
# read_frame caps the receive side, reading through any "read exactly n bytes"
# callable — a real socket in production, a stub in the test.
# ═══════════════════════════════════════════════════════════════════════════

def encode_frame(payload: bytes) -> bytes:
    """Length-prefix a payload. Refuses an oversized payload before it ever
    reaches the wire (§13)."""
    if len(payload) > MAX_FRAME:
        raise FrameError(f"payload {len(payload)} exceeds MAX_FRAME {MAX_FRAME}")
    return _LEN.pack(len(payload)) + payload


def read_frame(read_exactly) -> bytes:
    """Read one frame via a ``read_exactly(n) -> bytes`` callable. Rejects a
    declared length over MAX_FRAME BEFORE reading the body — an adversary cannot
    make us allocate a gigabyte by lying in the length prefix (§13)."""
    header = read_exactly(_LEN.size)
    (length,) = _LEN.unpack(header)
    if length > MAX_FRAME:
        raise FrameError(f"declared length {length} exceeds MAX_FRAME {MAX_FRAME}")
    return read_exactly(length) if length else b""


# ═══════════════════════════════════════════════════════════════════════════
# Peer — one connected, framed wire.
# ═══════════════════════════════════════════════════════════════════════════

class Peer:
    """A connected wire, speaking length-prefixed frames. Opaque payloads: the
    organ never interprets them (the wire contract does, step 5)."""

    def __init__(self, sock, addr):
        self._sock = sock
        self._addr = addr

    @property
    def remote(self):
        """The peer's (host, port). Informational only — NOT an identity and NOT
        a trust signal (§2.1). Identity is a signed key, established above."""
        return self._addr

    def _read_exactly(self, n: int, timeout=None) -> bytes:
        self._sock.settimeout(timeout)
        buf = bytearray()
        try:
            while len(buf) < n:
                chunk = self._sock.recv(n - len(buf))
                if not chunk:
                    raise PeerClosed("peer closed the connection mid-frame")
                buf += chunk
        except socket.timeout as e:
            raise OrganTimeout(f"recv timed out after {timeout}s") from e
        except OSError as e:
            raise OrganError(f"recv failed: {e}") from e
        return bytes(buf)

    def send(self, payload: bytes) -> None:
        """Send one framed message."""
        data = encode_frame(payload)
        try:
            self._sock.settimeout(None)
            self._sock.sendall(data)
        except OSError as e:
            raise OrganError(f"send failed: {e}") from e

    def recv(self, timeout=None) -> bytes:
        """Receive exactly one framed message (the whole payload, reassembled)."""
        return read_frame(lambda n: self._read_exactly(n, timeout))

    def close(self) -> None:
        try:
            self._sock.close()
        except OSError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


# ═══════════════════════════════════════════════════════════════════════════
# SocketOrgan — the node's single controlled network limb.
# ═══════════════════════════════════════════════════════════════════════════

class SocketOrgan:
    """The one organ (§1.5). Listen for strangers, dial strangers, move framed
    bytes. It decides NOTHING about trust — that lives in the ledger above."""

    def __init__(self):
        self._listener = None
        self._address = None

    @property
    def address(self):
        """The bound (host, port), or None if not listening."""
        return self._address

    def listen(self, host: str = "127.0.0.1", port: int = 0,
               backlog: int = 16):
        """Bind and listen. ``port=0`` asks the OS for an ephemeral port (used by
        the tests and the testnet-of-two). Returns the bound (host, port)."""
        try:
            lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            lsock.bind((host, port))
            lsock.listen(backlog)
        except OSError as e:
            raise OrganError(f"listen on {host}:{port} failed: {e}") from e
        self._listener = lsock
        self._address = lsock.getsockname()
        return self._address

    def accept(self, timeout=None) -> Peer:
        """Accept ONE inbound connection — from anyone (§2.1). Raises
        OrganTimeout if none arrives within `timeout`. Snapshots the listener into
        a local so a concurrent close() (the accept-loop shutdown race) surfaces as
        a clean OrganError, never an AttributeError on a None listener."""
        lsock = self._listener
        if lsock is None:
            raise OrganError("accept before listen")
        try:
            lsock.settimeout(timeout)
            csock, addr = lsock.accept()
        except socket.timeout as e:
            raise OrganTimeout(f"accept timed out after {timeout}s") from e
        except OSError as e:
            raise OrganError(f"accept failed: {e}") from e
        return Peer(csock, addr)

    def connect(self, host: str, port: int, timeout=10.0) -> Peer:
        """Dial a peer and return the connected wire."""
        try:
            csock = socket.create_connection((host, port), timeout=timeout)
        except socket.timeout as e:
            raise OrganTimeout(f"connect to {host}:{port} timed out") from e
        except OSError as e:
            raise OrganError(f"connect to {host}:{port} failed: {e}") from e
        return Peer(csock, csock.getpeername())

    def close(self) -> None:
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
            self._listener = None
            self._address = None
