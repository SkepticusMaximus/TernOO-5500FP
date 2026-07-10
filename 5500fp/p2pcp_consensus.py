"""p2pcp_consensus.py — the block-lattice conflict-vote (§9). Build step 6, v0.1 capstone.

Consensus is invoked RARELY and NARROWLY. In a block-lattice there is no global
total order to agree on; the ONLY event needing global agreement is a FORK — two
different records at the same height on ONE account's chain (a provable double-
spend, since both are self-signed by that account). Everything else is local and
asynchronous, balances optimistically final (§5).

This module is the deterministic RULE that resolves a fork, given votes weighted
by **decayed cumulative burn** (§6/§10), resolving at a **supermajority** — never
a knife-edge, because weight is locally fuzzy (§6). It is pure and offline: the
DECISION lives here and is testable alone; the vote GOSSIP (assembling a quorum
across many nodes, and eclipse-resistance) is the daemon's job and the honest
open problem of v0.2 (§9.3, Appendix B).

Two franchise facts fall straight out of the ledger and are enforced here:
  * weight is decayed burn, so a Sybil SPLIT does not multiply votes (§10) — the
    tally weighs weight, not heads;
  * a proven cheat is **slashed**: the fork's author (a double-spender), and a
    worker whose replay-class receipt fails a replay challenge (§7) — both lose
    their franchise.

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import json
import os
from dataclasses import dataclass

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


L = _load("p2pcp_ledger")

SUPERMAJORITY = L.SUPERMAJORITY        # ⅔ of participating weight (§6/§9)


def _canon(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


# ═══════════════════════════════════════════════════════════════════════════
# Fork detection. A node can only resolve a conflict it is SHOWN both sides of —
# that is the eclipse limit (§9.3), honest and unsolved: detect_fork over a
# single view returns nothing, because there is nothing to see.
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class Fork:
    account: bytes          # the account whose chain forked (the double-spender)
    height: int
    options: tuple          # 2+ conflicting record_ids (bytes), sorted


def detect_fork(view_a, view_b):
    """Given two views of ONE account's chain (record lists, height-ordered),
    return the Fork at the first divergent height, or None. Two records at the
    same height with different record_ids = a double-spend (each is self-signed
    by the account, so the fork is undeniable)."""
    for ra, rb in zip(view_a, view_b):
        ida, idb = ra.record_id(), rb.record_id()
        if ida != idb:
            return Fork(ra.account, ra.height, tuple(sorted((ida, idb))))
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Votes — authenticated. A vote is signed by its caster over (voter, account,
# height, choice); an unsigned or forged vote does not count (§9).
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Vote:
    voter: bytes            # the voter's account_id (its PUBKEY)
    account: bytes          # the forked account being voted on
    height: int
    choice: bytes           # the record_id this voter backs
    alg: int = L.ALG_ED25519
    sig: bytes = b""

    def _payload(self) -> dict:
        return {"voter": self.voter.hex(), "account": self.account.hex(),
                "height": self.height, "choice": self.choice.hex(), "alg": self.alg}

    def signing_bytes(self) -> bytes:
        return _canon(self._payload())

    def to_dict(self) -> dict:
        return {**self._payload(), "sig": self.sig.hex()}

    @classmethod
    def from_dict(cls, d) -> "Vote":
        v = cls(bytes.fromhex(d["voter"]), bytes.fromhex(d["account"]),
                int(d["height"]), bytes.fromhex(d["choice"]), int(d["alg"]))
        v.sig = bytes.fromhex(d["sig"])
        return v


def sign_vote(identity, account: bytes, height: int, choice: bytes,
              alg: int = L.ALG_ED25519) -> Vote:
    v = Vote(identity.account_id, account, height, choice, alg)
    v.sig = identity.sign(v.signing_bytes(), alg)
    return v


def verify_vote(vote: Vote) -> bool:
    """A vote counts only if it is validly signed by the voter it names (§9).
    Unknown/unimplemented alg → does not count, gracefully (§12)."""
    try:
        return L.get_alg(vote.alg).verify(vote.voter, vote.sig, vote.signing_bytes())
    except L.AlgError:
        return False


# ═══════════════════════════════════════════════════════════════════════════
# Tally and resolution. Winner iff a choice holds ≥ SUPERMAJORITY of the
# PARTICIPATING decayed weight (§6). Below that — a knife-edge, a bare majority —
# is UNDECIDED: the conflict waits, and honest nodes never notice (§9.4).
# ═══════════════════════════════════════════════════════════════════════════

def effective_weights(weights: dict, slashed: set) -> dict:
    """Drop slashed accounts — a cheat's franchise is gone (§9)."""
    return {a: w for a, w in weights.items() if a not in slashed}


def tally(votes, weights: dict, threshold: float = SUPERMAJORITY):
    """Sum decayed weight per choice (one vote per voter, first seen), and return
    the winning record_id iff it holds ≥ threshold of the participating weight,
    else None. Zero-weight voters contribute nothing, so a Sybil swarm of fresh
    identities cannot swing it (§10) — the tally weighs weight, not heads."""
    per, total, seen = {}, 0.0, set()
    for v in votes:
        if v.voter in seen:
            continue
        seen.add(v.voter)
        w = weights.get(v.voter, 0.0)
        if w <= 0.0:
            continue
        per[v.choice] = per.get(v.choice, 0.0) + w
        total += w
    if total <= 0.0:
        return None
    choice, top = max(per.items(), key=lambda kv: kv[1])
    return choice if top >= threshold * total else None


def resolve(fork: Fork, votes, weights: dict, slashed: set):
    """Resolve a fork. Count only validly-signed votes, weighted by effective
    (post-slash) decayed weight. If a supermajority decides, the losing branch is
    void AND the fork's author is slashed — a double-spend is undeniable, so its
    author forfeits its franchise (§9). Returns the winning record_id, or None if
    undecided (optimistic wait)."""
    winner = tally([v for v in votes if verify_vote(v)],
                   effective_weights(weights, slashed), )
    if winner is not None:
        slashed.add(fork.account)
    return winner


# ═══════════════════════════════════════════════════════════════════════════
# Franchise weights from the ledger, and the other slashable offence.
# ═══════════════════════════════════════════════════════════════════════════

def ledger_weights(ledger, now: int) -> dict:
    """Each account's decayed-burn weight at `now` (§6/§10). Only positive-weight
    accounts (they have burned earned credit) can vote."""
    out = {}
    for account in ledger.chains:
        w = ledger.weight(account, now)
        if w > 0.0:
            out[account] = w
    return out


def slash_forged_receipt(receipt, replayed_output: bytes, slashed: set) -> bool:
    """The other slashable offence (§7/§9): a worker whose replay-class receipt
    does not survive a replay challenge signed for work it never did. Slash it.
    Returns True if slashed. An honest receipt is untouched."""
    try:
        L.challenge_receipt(receipt, replayed_output)
        return False
    except L.WireMmidError:
        slashed.add(receipt.worker_id)
        return True
