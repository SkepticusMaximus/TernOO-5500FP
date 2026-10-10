"""TernID agent IPC — the wire contract from CC→CCC handoff 2026-10-10-1129.

JSON-lines over a unix domain socket. ONLY display names + opaque handles cross the
line — no AID / key / hash / grant-id / signature / ciphertext (the golden rule).

  serve(backend, sock_path) — run an agent exposing a backend's §B methods.
  Client(sock_path)         — call them (same method names, kwargs).

A `backend` is any object with the §B methods (StubBackend today; the real TernID
agent later). Request:  {"id", "method", "params"} ;  Response: {"id","ok","result"}
or {"id","ok":false,"error":"<human sentence>"}.
"""
import os
import json
import socket

METHODS = ["create_account", "list_accounts", "account_display", "send", "inbox",
           "mark_read", "contacts", "add_contact", "create_invite",
           "grant", "revoke", "grants_on"]


def default_sock():
    base = os.environ.get("XDG_RUNTIME_DIR") or os.path.expanduser("~/.ternid")
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, "ternid-agent.sock")


def serve(backend, sock_path=None, stop=None):
    """Run the agent loop. `stop` is an optional threading.Event to shut down."""
    sock_path = sock_path or default_sock()
    try:
        os.unlink(sock_path)
    except FileNotFoundError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(sock_path)
    srv.listen(8)
    srv.settimeout(0.5)
    try:
        while stop is None or not stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            with conn:
                f = conn.makefile("rwb")
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        req = json.loads(line)
                        m = req.get("method")
                        if m not in METHODS:
                            raise ValueError("unknown method: %s" % m)
                        result = getattr(backend, m)(**(req.get("params") or {}))
                        out = {"id": req.get("id"), "ok": True, "result": result}
                    except Exception as e:
                        out = {"id": req.get("id") if "req" in dir() else None,
                               "ok": False, "error": str(e)}
                    f.write((json.dumps(out) + "\n").encode())
                    f.flush()
    finally:
        srv.close()
        try:
            os.unlink(sock_path)
        except OSError:
            pass


class Client:
    """Call the agent over the socket. `client.inbox(account=...)` etc."""
    def __init__(self, sock_path=None):
        self.sock_path = sock_path or default_sock()
        self._id = 0

    def call(self, method, **params):
        self._id += 1
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(self.sock_path)
        try:
            f = s.makefile("rwb")
            f.write((json.dumps({"id": self._id, "method": method, "params": params}) + "\n").encode())
            f.flush()
            resp = json.loads(f.readline())
        finally:
            s.close()
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error", "agent error"))
        return resp.get("result")

    def __getattr__(self, name):
        if name in METHODS:
            return lambda **kw: self.call(name, **kw)
        raise AttributeError(name)
