"""p2pcp_worker — TernOO shim onto p2pcp.worker (one source of truth).

Re-exports the standalone package's worker adapters (WorkerAdapter,
DeterministicWorker, FunctionWorker). TernOO's own workers — BonsaiWorker,
GhostWorker, EmulatorWorker — are plugins that subclass these in their own modules.
"""

import os as _os
import sys as _sys

_PKG = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "p2pcp"))
if _PKG not in _sys.path:
    _sys.path.insert(0, _PKG)

from p2pcp import worker as _m                                    # noqa: E402

globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})
