"""p2pcp_daemon — TernOO shim onto p2pcp.daemon (one source of truth).

The node (keys, ledger, gossip, quorum, forks, eclipse, discovery, admission
control, reputation, persistence) lives in the sibling p2pcp package; this re-exports
it. TernOO code keeps using `_load("p2pcp_daemon")` unchanged.
"""

import os as _os
import sys as _sys

_PKG = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "p2pcp"))
if _PKG not in _sys.path:
    _sys.path.insert(0, _PKG)

from p2pcp import daemon as _m                                    # noqa: E402

globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
