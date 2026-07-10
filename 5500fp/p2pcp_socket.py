"""p2pcp_socket — TernOO shim onto p2pcp.organ, THE one network organ (§1.5).

Re-exports the package's socket organ. This module remains TernOO's single
network-facing face (it imports `socket`, keeping the one-organ boundary invariant
literally true); all socket work happens in the package organ it re-exports.
"""

import os as _os
import sys as _sys

_PKG = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "p2pcp"))
if _PKG not in _sys.path:
    _sys.path.insert(0, _PKG)

import socket  # noqa: F401 — this module IS TernOO's one network organ (§1.5)
from p2pcp import organ as _m                                     # noqa: E402

globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
