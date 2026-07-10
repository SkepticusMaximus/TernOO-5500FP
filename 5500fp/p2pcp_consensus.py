"""p2pcp_consensus — TernOO shim onto p2pcp.consensus (one source of truth)."""

import os as _os
import sys as _sys

_PKG = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "p2pcp"))
if _PKG not in _sys.path:
    _sys.path.insert(0, _PKG)

from p2pcp import consensus as _m                                 # noqa: E402

globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
