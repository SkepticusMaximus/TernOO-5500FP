"""test_network_boundary.py — the ONE-ORGAN network invariant, tree-wide.

Spec: P2PCP §1.5 / §14 step 4. Engelbart's rule made mechanical: the network is
the operator's limb hanging off ONE controlling organ, never a promiscuous
surface. CAI's step-4 flag (2026-07-10): the old invariant was pinned per-module
as "this module opens no socket." The socket organ (step 4) *deletes* the
"nothing opens a socket" fact — and if the pin were merely removed to let the
organ land, the invariant would not weaken, it would VANISH, and nothing would
notice a second socket appearing in some worker adapter eighteen months later.

So the pin is rewritten BEFORE the organ lands, into the narrower and stronger
form: **exactly one module may import the network; every other module is
forbidden; CI proves it by walking the imports** (AST, not a string grep — a
scan-string like ``'import socket'`` inside a guard test is not an import).

Today the allow-list is EMPTY: nothing imports the network (the ledger core is
offline). When the socket organ lands it adds exactly ONE entry here, and this
test keeps every other module honest forever after.

Run: ``cd 5500fp && python3 -m unittest test_network_boundary``
"""

import ast
import os
import unittest

# ── the network surface: top-level modules that touch the wire ───────────────
# A module importing any of these is "network-facing". Kept broad on purpose.
NETWORK_MODULES = {
    "socket", "socketserver", "ssl", "select", "selectors",
    "http", "urllib", "ftplib", "telnetlib", "smtplib", "poplib",
    "imaplib", "nntplib", "xmlrpc", "asyncio",
    # third-party clients, should any ever be added
    "requests", "aiohttp", "httpx", "websockets", "websocket", "zmq",
}

# ── the ONE organ (§1.5) ─────────────────────────────────────────────────────
# Repo-relative POSIX paths permitted to import the network. EMPTY today. The
# socket organ (step 4) adds exactly one path. The `<= 1` assertion below is
# Engelbart's one-limb rule, enforced by CI: you cannot grow a second organ.
NETWORK_ALLOWLIST = {"5500fp/p2pcp_socket.py"}   # the ONE organ (§1.5), step 4

# Roots walked. The whole TernOO/P2PCP tree, not one module.
ROOTS = ("5500fp", "FlowCode")


def _repo_root():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _top(mod):
    return (mod or "").split(".")[0]


def _network_imports(path):
    """The set of network top-level modules imported by a file (AST-exact — a
    string literal that merely spells 'import socket' is not an import)."""
    try:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except (SyntaxError, UnicodeDecodeError):
        return set()
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if _top(a.name) in NETWORK_MODULES:
                    found.add(_top(a.name))
        elif isinstance(node, ast.ImportFrom):
            # level>0 is a relative (in-package) import — never the stdlib net.
            if node.level == 0 and _top(node.module) in NETWORK_MODULES:
                found.add(_top(node.module))
    return found


class TestNetworkBoundary(unittest.TestCase):
    """The network arrives as one narrow, auditable organ (spec §1.5)."""

    def test_exactly_one_organ_allowed(self):
        # Engelbart's one-limb rule, mechanical: the allow-list can never name a
        # second network-importing module. A trusted/second surface that exists
        # anywhere is a downgrade target everywhere (§2.2).
        self.assertLessEqual(
            len(NETWORK_ALLOWLIST), 1,
            "at most ONE module may import the network (§1.5); "
            f"allow-list has {len(NETWORK_ALLOWLIST)}: {sorted(NETWORK_ALLOWLIST)}")

    def test_no_module_outside_the_allowlist_imports_the_network(self):
        root = _repo_root()
        offenders = {}
        for r in ROOTS:
            base = os.path.join(root, r)
            for dp, _dirs, files in os.walk(base):
                for f in files:
                    if not f.endswith(".py"):
                        continue
                    path = os.path.join(dp, f)
                    rel = os.path.relpath(path, root).replace(os.sep, "/")
                    if rel in NETWORK_ALLOWLIST:
                        continue
                    nets = _network_imports(path)
                    if nets:
                        offenders[rel] = sorted(nets)
        self.assertEqual(
            offenders, {},
            "modules outside the one-organ allow-list import the network "
            f"(§1.5): {offenders}. If this is the socket organ landing, add its "
            "path to NETWORK_ALLOWLIST; otherwise the limb has grown a second head.")

    def test_allowlisted_paths_exist(self):
        # A stale allow-list entry (organ renamed/removed) silently disables the
        # guard for that path — catch it.
        root = _repo_root()
        for rel in NETWORK_ALLOWLIST:
            self.assertTrue(os.path.isfile(os.path.join(root, rel)),
                            f"allow-listed organ {rel!r} does not exist")


if __name__ == "__main__":
    unittest.main()
