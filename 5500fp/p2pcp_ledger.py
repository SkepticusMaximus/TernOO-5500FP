"""p2pcp_ledger — TernOO shim onto p2pcp.ledger PLUS the TernOO-native extras.

The block-lattice mutual-credit ledger (SHA3 wire, ed25519) now lives in the sibling
p2pcp package (one source of truth). This re-exports it, then re-adds the two
TernOO-only facilities the portable core deliberately dropped (§4/§12.4): the ternary
STORE digest (ternary_sponge) and the 24-trit CRYPTO-primary header words. Those need
the TernOO ternary modules, so they stay here as TernOO flavour on the portable core.
"""

import importlib.util as _ilu
import os as _os
import sys as _sys
from typing import Dict, Optional, Tuple

_PKG = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "p2pcp"))
if _PKG not in _sys.path:
    _sys.path.insert(0, _PKG)

from p2pcp import ledger as _m                                    # noqa: E402

globals().update({k: v for k, v in vars(_m).items() if not k.startswith("__")})


# ── TernOO-native extras (not in the portable core) ──────────────────────────
def _load(name):
    spec = _ilu.spec_from_file_location(
        name, _os.path.join(_os.path.dirname(__file__), name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SP = _load("ternary_sponge")            # the STORE-MMID digest (54-trit sponge)
V = _load("5500fp_ternoo_v03")          # PRIMARY_CRYPTO + word builders (§4)


def store_mmid(words) -> Tuple[int, ...]:
    """STORE MMID (§12.4): the local content store's 54-trit ternary_sponge digest.
    Faces accident-resistance and *local* tamper-evidence only (not a remote
    adversary — that is what the SHA3 wire MMID in the core is for)."""
    canon = tuple(int(w) % (SP.MOD ** SP.TRIBBLES_PER_WORD) for w in words)
    return SP.digest(canon)


# CRYPTO-primary header words (§4, Appendix C): thin, self-describing 24-trit words.
# The ledger logic works on the Record objects in the core, not on packed words.
_ESCAPE_QUAL = V.from_trits([1, 1, 1, 1])   # (+,+,+,+) = 40 — reserved

CRYPTO_KIND_QUAL: Dict[str, int] = {
    "OPEN": V.from_trits([-1, -1, 0, 0]),
    "SETTLE": V.from_trits([0, -1, 0, 0]),
    "TRANSFER": V.from_trits([1, -1, 0, 0]),
    "BURN": V.from_trits([-1, 0, 0, 0]),
    "SIG": V.from_trits([0, 0, 0, 0]),
    "DIGEST": V.from_trits([1, 0, 0, 0]),
    "PUBKEY": V.from_trits([-1, 1, 0, 0]),
    "NONCE": V.from_trits([0, 1, 0, 0]),
    "JOB": V.from_trits([1, 1, 0, 0]),
    "RESULT": V.from_trits([-1, -1, 1, 0]),
    "RECEIPT": V.from_trits([0, -1, 1, 0]),
}
assert _ESCAPE_QUAL not in CRYPTO_KIND_QUAL.values(), "escape slot must stay free"


def crypto_header_word(kind: str, alg: int = ALG_ED25519) -> int:  # noqa: F821
    """Emit the CRYPTO-primary header word for a record/protocol KIND (§4)."""
    if kind not in CRYPTO_KIND_QUAL:
        raise ValueError(f"no CRYPTO qualifier assigned for kind {kind!r}")
    return V._make_word(V.PRIMARY_CRYPTO, CRYPTO_KIND_QUAL[kind], alg)


def crypto_word_kind(word: int) -> Optional[str]:
    """Inverse of crypto_header_word: the KIND named by a CRYPTO-primary word."""
    if V.get_primary(word) != V.PRIMARY_CRYPTO:
        return None
    qual = V.get_qualifier(word)
    for kind, code in CRYPTO_KIND_QUAL.items():
        if code == qual:
            return kind
    return None
