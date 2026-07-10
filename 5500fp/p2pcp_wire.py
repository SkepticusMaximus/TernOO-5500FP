"""p2pcp_wire — TernOO shim onto the standalone p2pcp package (one source of truth).

The portable P2PCP core now lives in the sibling `p2pcp` package
(~/dev/SkepticusMaximus/p2pcp). This thin module re-exports it so TernOO's flat
`_load("p2pcp_wire")` imports keep working while the code lives in exactly one place.
"""

import os as _os
import sys as _sys

_PKG = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "p2pcp"))
if _PKG not in _sys.path:
    _sys.path.insert(0, _PKG)

from p2pcp import wire as _m                                      # noqa: E402

globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
