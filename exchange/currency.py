#!/usr/bin/env python3
"""The Currency abstraction + two concrete domains (localhost only).

The whole autonomous-exchange idea rests on ONE question: can two domain-specific P2P
currencies settle a trade *trustlessly*, with no custodian in the middle? CompuCoin (earned for
COMPUTE on P2PCP — net-zero mutual credit, §5 of the P2PCP spec) and Autonomi's token (earned
for STORAGE — an ERC-20 on Arbitrum, fixed supply, 18 decimals) are the same STRUCTURE in
different DOMAINS. "Like inherits like": factor the shared structure out as `Currency`, implement
the two instances, and one conformance suite run over BOTH shows, by construction, where they
diverge.

No network, no Arbitrum RPC, no real keys, no value. hashlib's sha256 stands in for the on-chain
hashlock; time.time() for the on-chain timelock. A plumbing rig, not money.

The economic MODEL — what sets the rate, fees, the Möbius backing of CitiCoin — is NOT decided
here; that is CGP's design (CAI/CF5). This rig is model-agnostic on purpose: it proves the
settlement plumbing works over both currencies, nothing more. The one thing it answers for
TernOO's side: CompuCoin CAN express a hash-time-lock as a typed self-describing record (§4),
which is the primitive an atomic swap needs on both legs.
"""
from __future__ import annotations
import hashlib
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def new_secret() -> tuple[str, str]:
    """Return (preimage_hex, hashlock_hex). The preimage is the secret `s`; the hashlock
    H = sha256(s) is published. Revealing `s` to claim one leg exposes it for the other — that
    is what makes a two-ledger swap atomic."""
    s = secrets.token_bytes(32)
    return s.hex(), sha256_hex(s)


@dataclass
class Lock:
    """A hash-time-locked escrow — the on-ledger primitive an atomic swap needs on BOTH sides."""
    lock_id: str
    owner: str           # funded the escrow; gets a refund on timeout
    beneficiary: str     # may claim with the preimage
    amount: int          # base units, escrowed out of owner's balance
    hashlock: str        # H = sha256(preimage), hex
    expiry: float        # epoch seconds; at/after this, only refund is possible
    status: str = "locked"          # locked | claimed | refunded
    preimage: Optional[str] = None  # revealed on claim — publicly visible, like an on-chain claim


class Currency(ABC):
    """The shared structure of a P2P token. The two instances below differ only in DOMAIN and
    the supply invariant — everything the exchange touches lives here, which is the point: the
    exchange binds to `Currency`, never to a specific token."""

    ticker: str
    domain: str                 # what the token buys ("compute", "storage")
    decimals: int               # display precision; matching happens in base units, so this is metadata
    supply_model: str           # "net-zero-mutual-credit" | "fixed-supply"
    allows_overdraft: bool      # may a plain transfer push the sender negative? (mutual credit: yes)

    def __init__(self):
        self._bal: dict[str, int] = {}
        self._locks: dict[str, Lock] = {}

    # --- balances ---------------------------------------------------------
    def balance(self, account: str) -> int:
        return self._bal.get(account, 0)

    def total_supply(self) -> int:
        """Conserved at ALL times, including mid-escrow: free balances + funds held in live
        locks. Lock/claim/refund never change it; that is the invariant the suite checks."""
        locked = sum(l.amount for l in self._locks.values() if l.status == "locked")
        return sum(self._bal.values()) + locked

    def _move(self, account: str, delta: int):
        self._bal[account] = self._bal.get(account, 0) + delta

    @abstractmethod
    def _check_debit(self, account: str, amount: int):
        """Raise ValueError if `account` may not part with `amount` under this domain's rules."""

    # --- transfer ---------------------------------------------------------
    def transfer(self, src: str, dst: str, amount: int):
        if amount <= 0:
            raise ValueError("amount must be positive")
        self._check_debit(src, amount)
        self._move(src, -amount)
        self._move(dst, amount)

    # --- HTLC (the swap primitive) ---------------------------------------
    def lock(self, owner: str, beneficiary: str, amount: int, hashlock: str,
             timelock_seconds: float, now: float | None = None) -> str:
        if amount <= 0:
            raise ValueError("amount must be positive")
        # Escrow requires concrete units in BOTH domains — you cannot lock what you do not hold.
        if self.balance(owner) < amount:
            raise ValueError(f"{self.ticker}: {owner} cannot escrow {amount}; holds {self.balance(owner)}")
        now = time.time() if now is None else now
        lock_id = secrets.token_hex(8)
        self._move(owner, -amount)
        self._locks[lock_id] = Lock(lock_id, owner, beneficiary, amount, hashlock, now + timelock_seconds)
        return lock_id

    def claim(self, lock_id: str, preimage: str, now: float | None = None) -> bool:
        lk = self._locks[lock_id]
        now = time.time() if now is None else now
        if lk.status != "locked":
            raise ValueError(f"lock {lock_id} already {lk.status}")
        if now >= lk.expiry:
            raise ValueError("lock expired; only refund is possible")
        if sha256_hex(bytes.fromhex(preimage)) != lk.hashlock:
            raise ValueError("preimage does not match hashlock")
        lk.status = "claimed"
        lk.preimage = preimage          # now public — the counterparty can read it off this claim
        self._move(lk.beneficiary, lk.amount)
        return True

    def refund(self, lock_id: str, now: float | None = None) -> bool:
        lk = self._locks[lock_id]
        now = time.time() if now is None else now
        if lk.status != "locked":
            raise ValueError(f"lock {lock_id} already {lk.status}")
        if now < lk.expiry:
            raise ValueError("lock not yet expired")
        lk.status = "refunded"
        self._move(lk.owner, lk.amount)
        return True

    def revealed_preimage(self, lock_id: str) -> Optional[str]:
        return self._locks[lock_id].preimage

    def lock_status(self, lock_id: str) -> str:
        return self._locks[lock_id].status

    def invariants(self) -> dict:
        return {"ticker": self.ticker, "domain": self.domain, "decimals": self.decimals,
                "supply_model": self.supply_model, "allows_overdraft": self.allows_overdraft}


class CompuCoin(Currency):
    """Earned for COMPUTE on P2PCP. Net-zero mutual credit (§5): no fixed supply, balances may go
    negative, the sum across all accounts is always zero. Mirrors the P2PCP CompuToken settle
    semantics; binding to the live `5500fp` ledger is a follow-up, not needed for the rig."""
    ticker = "COMP"
    domain = "compute"
    decimals = 9
    supply_model = "net-zero-mutual-credit"
    allows_overdraft = True

    def mint_earn(self, account: str, amount: int):
        """Testbed convenience: credit `account` as if it earned `amount` from a counterparty,
        with the equal-and-opposite debit on a '__mesh__' account so the net stays zero."""
        self._move(account, amount)
        self._move("__mesh__", -amount)

    def _check_debit(self, account, amount):
        return  # mutual credit: a transfer may push the sender negative; nothing to check


class AutonomiToken(Currency):
    """Autonomi's token — earned for STORAGE. ERC-20 on Arbitrum: fixed supply, 18 decimals,
    balances never negative. A LOCAL STUB of the EVM HTLC semantics — no Arbitrum, no RPC."""
    ticker = "ANT"
    domain = "storage"
    decimals = 18
    supply_model = "fixed-supply"
    allows_overdraft = False

    def __init__(self, initial: dict[str, int] | None = None):
        super().__init__()
        for acct, amt in (initial or {}).items():
            self._move(acct, amt)
        self._minted = self.total_supply()

    def _check_debit(self, account, amount):
        if self.balance(account) < amount:
            raise ValueError(f"ANT: insufficient balance ({self.balance(account)} < {amount})")
