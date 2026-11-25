#!/usr/bin/env python3
"""Cross-ledger HTLC atomic swap — the crux the whole exchange rests on.

Two parties, two ledgers, no custodian. Alice holds currency A and wants B; Bob the reverse. A
single secret `s` (hashlock H = sha256(s)) ties the two escrows together:

  1. Alice picks `s`, publishes H.
  2. Alice locks her A for Bob with hashlock H and a LONG timelock.
  3. Bob locks his B for Alice with the same H and a SHORT timelock (< Alice's, so Bob always has
     time to react once the secret appears).
  4. Alice claims B by revealing `s`  →  `s` is now on-ledger, visible.
  5. Bob reads `s` off Alice's claim and claims A.

Either both legs settle or both refund on timeout; nobody can take one leg without handing the
other party the key to theirs. This module runs the happy path and the abort/refund path, and
returns a human-readable trace so the localhost demo can show it step by step.
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field

from exchange.currency import Currency, new_secret


@dataclass
class SwapResult:
    ok: bool
    outcome: str                 # "settled" | "refunded"
    trace: list = field(default_factory=list)


def atomic_swap(ledger_a: Currency, ledger_b: Currency, alice: str, bob: str,
                amount_a: int, amount_b: int, *, long_timelock: float = 120,
                short_timelock: float = 60, now: float | None = None,
                abort: bool = False) -> SwapResult:
    """Swap `amount_a` of ledger_a (Alice→Bob) for `amount_b` of ledger_b (Bob→Alice), atomically.

    `abort=True` has Alice walk away after both legs are locked, to exercise the refund path.
    Timelocks are relative seconds; pass `now` for deterministic tests.
    """
    now = time.time() if now is None else now
    trace: list[str] = []
    s, H = new_secret()

    la = ledger_a.lock(alice, bob, amount_a, H, long_timelock, now=now)
    trace.append(f"{alice} locks {amount_a} {ledger_a.ticker} for {bob}  (H={H[:10]}…, +{long_timelock:g}s)")

    lb = ledger_b.lock(bob, alice, amount_b, H, short_timelock, now=now)
    trace.append(f"{bob} locks {amount_b} {ledger_b.ticker} for {alice} (same H, +{short_timelock:g}s)")

    if abort:
        # Alice (the initiator) never reveals. Each leg refunds to its owner after its own timelock.
        # No custodian ever held either side; the worst case is both parties get their own funds back.
        ledger_b.refund(lb, now=now + short_timelock + 1)
        ledger_a.refund(la, now=now + long_timelock + 1)
        trace.append(f"{alice} aborts → {bob} refunds {ledger_b.ticker}, {alice} refunds {ledger_a.ticker}; nobody is exposed")
        return SwapResult(False, "refunded", trace)

    ledger_b.claim(lb, s, now=now + 1)
    trace.append(f"{alice} claims {amount_b} {ledger_b.ticker}, revealing s={s[:10]}…")

    s_seen = ledger_b.revealed_preimage(lb)          # counterparty reads the secret off the on-ledger claim
    ledger_a.claim(la, s_seen, now=now + 2)
    trace.append(f"{bob} reads s off that claim, takes {amount_a} {ledger_a.ticker}  → settled, no custodian")
    return SwapResult(True, "settled", trace)
