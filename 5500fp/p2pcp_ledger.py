"""p2pcp_ledger.py — the P2PCP block-lattice mutual-credit ledger + TCM.

P2PCP reference implementation. P2PCP is a protocol, not a TernOO component (spec §0); TernOO is the reference implementation. Offline ledger core — no sockets, no wall-clock in logic.

Canon: ``docs/P2PCP-v0.1-SPEC.md`` (v0.1, Stevo + CC, Adelaide). Where a
section is cited below (§5, §8, ...) the spec is the source of truth; this file
is one projection of it. Build order §14 steps 2–3: the adversarial fixtures and
the receipts+burn ledger, offline and single-node.

What lives here (and ONLY this):
  * Two machines kept separate (§2). This file is the **TCM** — the *total*
    contract-machine that validates ledger records in bounded, straight-line
    work. The *worker* (inference, cargo execution) is deliberately absent: an
    inference job is never validated here, only referenced by MMID.
  * The block-lattice (§5): one hash-linked chain per identity, mutual credit,
    double-entry so that minting your own money nets to zero.
  * Weight from decayed burn (§5/§6), Sybil-conserving (§10).
  * TIME defused by parameter, never by a wall-clock read (§6): every function
    that needs "now" takes it as an explicit argument. Tests pass fixed clocks.
  * Privacy (§7): the on-ledger settlement carries a *blinded* job commitment
    ``H(MMID ‖ nonce)`` and the receipt-hash — never the bare job MMID. The full
    Receipt is a separate, off-ledger, both-signed object.
  * The ``alg`` field (§12): a data-driven dispatch table. ``alg=0`` is real
    ed25519 + a gauntlet-grade wire digest; ``alg=1`` is the recognized-but-
    unimplemented ternary-native stub; unknown alg is a graceful reject.
  * The CRYPTO primary (§4), inhabited: thin header words emitted through the
    real ``PRIMARY_CRYPTO`` constant of ``5500fp_ternoo_v03.py``.

Crypto doctrine (§12.3): signatures are real ed25519 (PyNaCl). Nothing here
home-rolls a signature. The wire digest is SHA3-256-class. The ternary_sponge is
used for the STORE MMID only (§12.4) — it is proven for local accident-
resistance, not rated against a remote adversary.

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

# NB: deliberately NOT `from __future__ import annotations`. This module is
# loaded via importlib (digit-named siblings force it), and PEP 563 stringized
# annotations make @dataclass try to resolve field types through sys.modules —
# which an importlib-exec'd module is not registered in. Real annotations avoid
# that; the few forward references below are written as explicit string literals.

import hashlib
import importlib.util as _ilu
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey

SPEC_FILE = "docs/P2PCP-v0.1-SPEC.md"

# ── load sibling modules the way ternoo_content_store.py does ───────────────
# (the reference module is digit-named, so a plain import will not do — copy the
#  store's importlib helper verbatim.)
_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SP = _load("ternary_sponge")            # the STORE-MMID digest (54-trit sponge)
V = _load("5500fp_ternoo_v03")          # PRIMARY_CRYPTO + word builders (§4)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 0 — normative parameters (§6). These are part of the SPEC, not the
# implementation; a conforming node reproduces them.
# ═══════════════════════════════════════════════════════════════════════════

# Burn-weight half-life — weeks-scale, so honest clocks disagree by a fraction
# of a percent (§6.2). Named constant; default two weeks in seconds.
BURN_HALF_LIFE_SECONDS: int = 2 * 7 * 24 * 3600

# Timestamp tolerance — hours, not seconds (§6.2). A BURN whose signed timestamp
# is farther than this from the supplied reference `now` is rejected.
TIME_TOLERANCE_SECONDS: int = 6 * 3600

# Conflict-vote threshold — supermajority, never a knife-edge (§6/§9). The vote
# itself is consensus (§9), which is OUT of this offline core; the constant is
# recorded here so the reference value travels with the ledger.
SUPERMAJORITY: float = 2.0 / 3.0


def decay(dt_seconds: float) -> float:
    """Exponential decay with BURN_HALF_LIFE_SECONDS (§5/§6). Pure function of a
    supplied elapsed time — never reads a clock. ``dt`` may be slightly negative
    (a burn timestamped just after `now`, within tolerance); that yields a value
    marginally above 1, which is the intended fuzz, not an error."""
    return 0.5 ** (dt_seconds / BURN_HALF_LIFE_SECONDS)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1 — errors. Every rejection is a clean exception, never a crash or a
# KeyError (§4/§12.1: "graceful reject").
# ═══════════════════════════════════════════════════════════════════════════

class P2PCPError(Exception):
    """Base for every P2PCP rejection."""


class ValidationError(P2PCPError):
    """A record failed a TCM check (§8). Carries a short machine reason."""

    def __init__(self, reason: str, detail: str = ""):
        self.reason = reason
        super().__init__(f"{reason}: {detail}" if detail else reason)


class ForkError(ValidationError):
    """Two records at one height / a broken chain link — the one event that
    needs global agreement (§5/§9). Detected locally at post time."""


class AlgError(P2PCPError):
    """Base for algorithm-negotiation rejections (§12.1)."""


class AlgUnimplemented(AlgError):
    """A recognized `alg` whose primitive is not built in v0.1 (e.g. alg=1, the
    ternary-native form — Appendix B). Recognized, gracefully refused."""


class UnknownAlg(AlgError):
    """An `alg` value the node does not recognize at all. Graceful reject — the
    dispatch is a table, so an unknown selector is never a KeyError."""


class WireMmidError(P2PCPError):
    """Fetched cargo's wire digest does not match its claimed wire-MMID — a
    substitution attempt (§12.4). The wire analogue of verify-on-fetch."""


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2 — the `alg` field (§12). A data-driven registry keyed by alg value.
# `alg=0` is the working ed25519 / SHA3 slot; `alg=1` is a live-but-stubbed slot
# so the negotiation path is EXERCISED in CI even while it is empty (§12.2:
# "be multihash"). Unknown selectors resolve to a graceful reject.
# ═══════════════════════════════════════════════════════════════════════════

ALG_ED25519: int = 0            # ed25519 signatures + SHA3-256 wire digest
ALG_TERNARY_NATIVE: int = 1     # reserved — ternary-native primitives (stub)


class _Ed25519Alg:
    """alg=0 — real, gauntlet-tested primitives (§12.1/§12.3). Signatures are
    ed25519 via libsodium (PyNaCl); the wire digest is SHA3-256 (blake2b would
    serve equally — either is remote-adversarial-rated, unlike the sponge)."""

    name = "ed25519+sha3_256"

    def sign(self, signing_key: SigningKey, msg: bytes) -> bytes:
        # Detached 64-byte signature. Never home-rolled (§12.3).
        return bytes(signing_key.sign(msg).signature)

    def verify(self, pubkey: bytes, sig: bytes, msg: bytes) -> bool:
        try:
            VerifyKey(pubkey).verify(msg, sig)
            return True
        except (BadSignatureError, ValueError):
            return False

    def wire_digest(self, data: bytes) -> bytes:
        return hashlib.sha3_256(data).digest()


class _TernaryNativeAlgStub:
    """alg=1 — recognized, not implemented (§12.1, Appendix B.2). Every
    primitive raises AlgUnimplemented so the migration path is real but the
    home-rolled primitive is never actually deployed against strangers."""

    name = "ternary-native (stub)"

    _MSG = ("alg=1 (ternary-native) is reserved and not implemented in v0.1; it "
            "awaits external cryptanalysis (spec §12, Appendix B.2)")

    def sign(self, signing_key, msg):      raise AlgUnimplemented(self._MSG)
    def verify(self, pubkey, sig, msg):    raise AlgUnimplemented(self._MSG)
    def wire_digest(self, data):           raise AlgUnimplemented(self._MSG)


# The dispatch TABLE (§12.1). New algs are added by extending this dict — the
# code never grows a branch per primitive.
_ALG_REGISTRY: Dict[int, object] = {
    ALG_ED25519: _Ed25519Alg(),
    ALG_TERNARY_NATIVE: _TernaryNativeAlgStub(),
}


def get_alg(alg: int):
    """Resolve an `alg` selector to its primitive suite. Unknown → UnknownAlg
    (never KeyError); recognized-but-stub returns the stub, which refuses on
    use. This is the whole of the negotiation surface."""
    try:
        return _ALG_REGISTRY[alg]
    except KeyError:
        raise UnknownAlg(f"alg={alg!r} is not a recognized primitive suite "
                         f"(known: {sorted(_ALG_REGISTRY)})") from None


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2b — verification classes and the WEIGHT-BEARING rule (§3/§9/§10).
#
# CAI's Q3 correction (2026-07-10): "earned from a counterparty" does NOT prove
# the counterparty was a stranger — a sockpuppet pair can sign receipts to each
# other, and a permissionless system has no trusted notion of distinct persons,
# so no protocol can. Debit-abandonment and the sockpuppet-weight attack are the
# SAME attack wearing two hats; a balance floor is the wrong instrument. The
# right one: weight is priced in VERIFIABLE CYCLES and nothing else. Only
# replay-class (deterministic) work can be audited by replay, so only replay-
# class work mints WEIGHT-BEARING credit. Float work earns money, never a vote.
# The determinism moat (§3) thus runs all the way up into the franchise:
# native-integer execution earns votes, float earns rent — the market signal
# governs, unmandated. (A data centre can still buy the franchise with real
# cycles, exactly as under any PoW/PoS; the mitigation is decay + supermajority
# thresholds, not immunity. We claim that plainly.)
# ═══════════════════════════════════════════════════════════════════════════

VCLASS_TCM: int = 0         # ledger validation — replay, exact
VCLASS_NATIVE: int = 1      # native integer model — replay, exact (the flagship)
VCLASS_FLOAT: int = -1      # float-accumulating worker — quorum only, never replay


def is_replay_class(vclass: int) -> bool:
    """Replay-class = deterministic = bit-exactly auditable by a stranger who
    re-runs the job. Float (−1) is not: two honest nodes get different bits."""
    return vclass != VCLASS_FLOAT


def is_weight_bearing(vclass: int) -> bool:
    """Only replay-class compute mints weight-bearing credit (§10). Float work
    earns spendable credit but NEVER a vote."""
    return is_replay_class(vclass)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3 — canonical serialization, digests, MMIDs (§12.4).
# ═══════════════════════════════════════════════════════════════════════════

def _canon(obj: dict) -> bytes:
    """Deterministic canonical bytes for signing/hashing: JSON with sorted keys
    and no incidental whitespace, UTF-8 encoded. Bytes are carried as lowercase
    hex and MMID tuples as int lists, so the form is stable across platforms —
    the loo-paper test (§0): a stranger can reproduce these bytes exactly."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def store_mmid(words) -> Tuple[int, ...]:
    """STORE MMID (§12.4): the local content store's 54-trit ternary_sponge
    digest. Faces accident-resistance and *local* tamper-evidence only. Same
    canonicalization the content store uses (lawful 24-trit word values)."""
    canon = tuple(int(w) % (SP.MOD ** SP.TRIBBLES_PER_WORD) for w in words)
    return SP.digest(canon)


def wire_mmid(data: bytes, alg: int = ALG_ED25519) -> bytes:
    """WIRE MMID (§12.4): the gauntlet-grade, alg-tagged digest. On the wire a
    forged MMID collision would let an adversary substitute cargo — a remote-
    adversarial threat the sponge is explicitly not rated for, so this uses the
    SHA3-class primitive under the `alg` field."""
    return get_alg(alg).wire_digest(data)


def blinded_commitment(job_commit: bytes, nonce: bytes,
                       alg: int = ALG_ED25519) -> bytes:
    """The on-ledger, unlinkable job reference (§7.3): ``H(job_commit ‖ nonce)``
    with a per-receipt nonce, over the WIRE (gauntlet) job commitment. Same job
    on two chains under two nonces yields two different commitments — content-
    addressing's dedupe virtue is denied to a correlation attacker. Costs one
    word; buys unlinkability.

    The nonce is ALSO the reveal key (§7): a challenged burner opens the
    commitment by producing (job_commit, output_commit, nonce), and the
    challenger replays. Privacy by default, auditability on demand — one word
    doing both jobs."""
    return wire_mmid(job_commit + nonce, alg)


def open_commitment(commitment: bytes, job_commit: bytes, nonce: bytes,
                    alg: int = ALG_ED25519) -> bool:
    """Verify a challenge opening (§7): the revealed (job_commit, nonce) must
    reproduce the on-ledger blinded commitment. A burner who refuses to open, or
    opens wrongly, has its burn voided and its stake slashed (§9)."""
    return blinded_commitment(job_commit, nonce, alg) == commitment


def verify_wire_cargo(claimed_mmid: bytes, data: bytes,
                      alg: int = ALG_ED25519) -> bool:
    """Verify-on-fetch for the WIRE (§12.4): recompute the gauntlet digest of
    what was delivered and compare to the claimed wire-MMID. Mismatch = a
    substitution attempt, raised loudly."""
    if wire_mmid(data, alg) != claimed_mmid:
        raise WireMmidError("fetched cargo does not match its claimed wire-MMID "
                            "(substitution detected, §12.4)")
    return True


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4 — identity (§5). An account IS its ed25519 public key.
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Identity:
    """An ed25519 keypair. ``account_id`` (the 32-byte public key) is the account
    (§4: an identity *is* its PUBKEY). Signing routes through the `alg` table so
    alg negotiation is exercised even for identity operations."""

    signing_key: SigningKey

    @classmethod
    def generate(cls) -> "Identity":
        return cls(SigningKey.generate())

    @classmethod
    def from_seed(cls, seed: bytes) -> "Identity":
        """Deterministic identity from a 32-byte seed (for reproducible tests)."""
        return cls(SigningKey(seed))

    @property
    def account_id(self) -> bytes:
        return bytes(self.signing_key.verify_key)

    def sign(self, msg: bytes, alg: int = ALG_ED25519) -> bytes:
        return get_alg(alg).sign(self.signing_key, msg)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5 — the off-ledger Receipt (§4/§7). Pairwise, BOTH-signed, carrying the
# real job detail. Only its hash, the ±delta, and the blinded commitment ever
# reach a chain. This object stays with the two parties.
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Receipt:
    worker_id: bytes            # the account credited +amount
    requester_id: bytes         # the account debited −amount
    amount: int                 # magnitude N (> 0); the ± is applied per chain
    job_commit: bytes           # WIRE (gauntlet) digest of the job cargo (§12.4)
    output_commit: bytes        # WIRE digest of the output MMOE — the audit key (§7)
    vclass: int                 # verification class (§3); sets weight-bearing (§10)
    nonce: bytes                # per-receipt blinding nonce / reveal key (§7.3)
    alg: int = ALG_ED25519
    worker_sig: bytes = b""     # both parties sign the SAME canonical bytes
    requester_sig: bytes = b""

    def signing_payload(self) -> dict:
        # The receipt commits to BOTH the job and the output (§7): any peer can
        # audit by replaying the job and refolding the output. Both commitments
        # are WIRE (gauntlet) digests, never the store sponge (§12.4) — a forged
        # sponge collision on an output commitment would let a worker sign for
        # output it never produced. The raw commitments stay HERE, off-ledger:
        # the pairwise parties already know what was computed, so nothing leaks;
        # only the blinded H(job_commit‖nonce) and the receipt-hash reach a chain.
        return {
            "worker": self.worker_id.hex(),
            "requester": self.requester_id.hex(),
            "amount": self.amount,
            "job_commit": self.job_commit.hex(),
            "output_commit": self.output_commit.hex(),
            "vclass": self.vclass,
            "nonce": self.nonce.hex(),
            "alg": self.alg,
        }

    def signing_bytes(self) -> bytes:
        return _canon(self.signing_payload())

    def hash(self) -> bytes:
        """The receipt-hash that reaches the chain (single-use per chain, §6.1)."""
        return wire_mmid(self.signing_bytes(), self.alg)

    def blinded(self) -> bytes:
        return blinded_commitment(self.job_commit, self.nonce, self.alg)


def make_receipt(worker: Identity, requester: Identity, amount: int,
                 job: bytes, output: bytes, vclass: int = VCLASS_NATIVE,
                 nonce: Optional[bytes] = None,
                 alg: int = ALG_ED25519) -> Receipt:
    """Build a both-signed receipt for delivered work. Credit is minted ONLY
    here, and only with the counterparty's signature (§5). ``job`` and
    ``output`` are the raw cargo octets; the receipt commits to their WIRE
    (gauntlet) digests (§12.4). ``vclass`` sets whether the minted credit is
    weight-bearing (§10). ``amount`` is the positive magnitude; the double-entry
    ± is applied when the two settlement records are built."""
    if amount <= 0:
        raise ValueError("receipt amount must be positive")
    if nonce is None:
        nonce = os.urandom(16)
    r = Receipt(worker.account_id, requester.account_id, amount,
                wire_mmid(job, alg), wire_mmid(output, alg), vclass, nonce, alg)
    msg = r.signing_bytes()
    r.worker_sig = worker.sign(msg, alg)
    r.requester_sig = requester.sign(msg, alg)
    return r


@dataclass
class TransferAuth:
    """A both-signed SEND/RECEIVE authorization backing a TRANSFER (§4/§8). The
    transfer analogue of a Receipt: off-ledger, only its hash reaches a chain."""

    sender_id: bytes
    receiver_id: bytes
    amount: int
    nonce: bytes
    alg: int = ALG_ED25519
    sender_sig: bytes = b""
    receiver_sig: bytes = b""

    def signing_payload(self) -> dict:
        return {
            "sender": self.sender_id.hex(),
            "receiver": self.receiver_id.hex(),
            "amount": self.amount,
            "nonce": self.nonce.hex(),
            "alg": self.alg,
        }

    def signing_bytes(self) -> bytes:
        return _canon(self.signing_payload())

    def hash(self) -> bytes:
        return wire_mmid(self.signing_bytes(), self.alg)


def make_transfer_auth(sender: Identity, receiver: Identity, amount: int,
                       nonce: Optional[bytes] = None,
                       alg: int = ALG_ED25519) -> TransferAuth:
    if amount <= 0:
        raise ValueError("transfer amount must be positive")
    if nonce is None:
        nonce = os.urandom(16)
    a = TransferAuth(sender.account_id, receiver.account_id, amount, nonce, alg)
    msg = a.signing_bytes()
    a.sender_sig = sender.sign(msg, alg)
    a.receiver_sig = receiver.sign(msg, alg)
    return a


# ── audit-by-replay: the challenge that prices weight in verifiable cycles ────

def challenge_receipt(receipt: "Receipt", replayed_output: bytes) -> bool:
    """Audit a weight-bearing receipt by REPLAY (§7/§9). An auditor (any peer)
    re-runs the job and refolds the output; the receipt's output commitment must
    equal the WIRE digest of that replayed output. A worker who signed for output
    it never produced cannot survive this — and every peer is a potential
    auditor, so the probability of a forged output surviving indefinitely goes to
    zero. This is what makes weight priced in *verifiable* cycles rather than in
    mere counterparty signatures (CAI's Q3 correction).

    Returns True on a clean audit; raises WireMmidError on a forged output
    commitment (burn void, stake slashed — §9), or ValidationError for a non-
    replay-class (float/quorum) receipt, which is not replay-auditable at all."""
    if not is_replay_class(receipt.vclass):
        raise ValidationError("not-replay-class",
                              "float/quorum receipts are not replay-auditable "
                              "(they earn money, never weight — §3/§10)")
    if wire_mmid(replayed_output, receipt.alg) != receipt.output_commit:
        raise WireMmidError("replayed output does not match the receipt's output "
                            "commitment — forged work (burn void, slash §9)")
    return True


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6 — record kinds and the Record itself (§5). Each record is sealed by
# the account's OWN signature over (account ‖ prev ‖ height ‖ kind ‖ alg ‖ body),
# via the canonical serialization.
# ═══════════════════════════════════════════════════════════════════════════

KIND_OPEN = "OPEN"
KIND_SETTLE = "SETTLE"
KIND_TRANSFER = "TRANSFER"
KIND_BURN = "BURN"


@dataclass
class Record:
    account: bytes              # the chain owner (its PUBKEY / account_id)
    height: int                 # monotonic; OPEN=0, +1 per record (§5)
    prev: bytes                 # digest of the previous record on THIS chain
    kind: str
    body: dict                  # kind-specific, JSON-safe (ints + hex strings)
    alg: int = ALG_ED25519
    sig: bytes = b""            # the account's OWN signature (self-signature)

    def signing_payload(self) -> dict:
        return {
            "account": self.account.hex(),
            "height": self.height,
            "prev": self.prev.hex(),
            "kind": self.kind,
            "alg": self.alg,
            "body": self.body,
        }

    def signing_bytes(self) -> bytes:
        return _canon(self.signing_payload())

    def sign(self, identity: Identity) -> "Record":
        self.sig = identity.sign(self.signing_bytes(), self.alg)
        return self

    def record_id(self) -> bytes:
        """This record's digest — the link value the NEXT record references as
        ``prev`` (§5). Computed over the full, signed record."""
        payload = self.signing_payload()
        payload["sig"] = self.sig.hex()
        return wire_mmid(_canon(payload), self.alg)

    def to_dict(self) -> dict:
        return {"account": self.account.hex(), "height": self.height,
                "prev": self.prev.hex(), "kind": self.kind, "body": self.body,
                "alg": self.alg, "sig": self.sig.hex()}

    @classmethod
    def from_dict(cls, d) -> "Record":
        return cls(bytes.fromhex(d["account"]), int(d["height"]),
                   bytes.fromhex(d["prev"]), d["kind"], d["body"],
                   int(d["alg"]), bytes.fromhex(d["sig"]))


# ── record builders — public so adversarial tests can craft raw records ──────

def genesis_marker(account: bytes, alg: int = ALG_ED25519) -> bytes:
    """OPEN's ``prev`` (§8): the digest of the account's PUBKEY."""
    return wire_mmid(account, alg)


def build_open_record(identity: Identity, alg: int = ALG_ED25519) -> Record:
    acct = identity.account_id
    rec = Record(acct, 0, genesis_marker(acct, alg), KIND_OPEN, {}, alg)
    return rec.sign(identity)


def _settle_role(account: bytes, receipt: Receipt):
    """Which side of the double-entry is `account`? Returns (signed_amount,
    counterparty_id). Worker → +amount vs requester; requester → −amount vs
    worker (§5). An account not party to the receipt is rejected upstream."""
    if account == receipt.worker_id:
        return +receipt.amount, receipt.requester_id
    if account == receipt.requester_id:
        return -receipt.amount, receipt.worker_id
    return None, None


def build_settle_record(identity: Identity, chain: "Chain", receipt: Receipt,
                        alg: int = ALG_ED25519) -> Record:
    """Build the SETTLE record for `identity`'s side of a receipt. The body
    carries the signed ±amount, the counterparty id, the BLINDED commitment and
    the receipt-hash — never the bare job MMID (§7)."""
    acct = identity.account_id
    amount, counterparty = _settle_role(acct, receipt)
    if amount is None:
        raise ValidationError("receipt-not-party",
                              "account is neither worker nor requester")
    body = {
        "amount": amount,
        "counterparty": counterparty.hex(),
        "blinded": receipt.blinded().hex(),        # H(job_commit‖nonce), not bare
        "receipt_hash": receipt.hash().hex(),
        "vclass": receipt.vclass,                  # §3 verification class
        "weight_bearing": is_weight_bearing(receipt.vclass),  # §10 franchise gate
    }
    rec = Record(acct, chain.height + 1, chain.head_id, KIND_SETTLE, body, alg)
    return rec.sign(identity)


def _transfer_role(account: bytes, auth: TransferAuth):
    if account == auth.sender_id:
        return -auth.amount, auth.receiver_id
    if account == auth.receiver_id:
        return +auth.amount, auth.sender_id
    return None, None


def build_transfer_record(identity: Identity, chain: "Chain",
                          auth: TransferAuth, alg: int = ALG_ED25519) -> Record:
    acct = identity.account_id
    amount, counterparty = _transfer_role(acct, auth)
    if amount is None:
        raise ValidationError("transfer-not-party",
                              "account is neither sender nor receiver")
    body = {
        "amount": amount,
        "counterparty": counterparty.hex(),
        "transfer_ref": auth.hash().hex(),
    }
    rec = Record(acct, chain.height + 1, chain.head_id, KIND_TRANSFER, body, alg)
    return rec.sign(identity)


def build_burn_record(identity: Identity, chain: "Chain", amount: int,
                      timestamp: int, alg: int = ALG_ED25519) -> Record:
    body = {"amount": amount, "timestamp": timestamp}
    rec = Record(identity.account_id, chain.height + 1, chain.head_id,
                 KIND_BURN, body, alg)
    return rec.sign(identity)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7 — the per-identity chain (§5). Aggregates are maintained
# INCREMENTALLY as records append, so the TCM (§8) reads chain state in O(1) —
# fixed instruction budget, no fold at validation time. The one bounded fold is
# `weight`, a consensus/report read, not a record-validation check.
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class Chain:
    account: bytes
    records: List[Record] = field(default_factory=list)
    height: int = -1                                   # -1 = not yet opened
    head_id: bytes = b""                               # digest of the head
    used_refs: set = field(default_factory=set)        # receipt/transfer hashes
    balance: int = 0                                   # §5 net (signed ± − burns)
    earned_ctp: int = 0                                # WEIGHT-BEARING pool (§10):
    #                                                  # replay-class, from another
    #                                                  # account — see _append
    burned_total: int = 0
    burns: List[Tuple[int, int]] = field(default_factory=list)  # (amount, ts)

    @property
    def burnable(self) -> int:
        """Credit that may be burned for weight (§10): the weight-bearing pool
        (replay-class work from a counterparty), less what has already been
        burned. Deliberately NOT the §5 net balance, and NOT float credit (see
        the notes in `_append` and `_validate_burn`)."""
        return self.earned_ctp - self.burned_total

    def to_dict(self) -> dict:
        return {"account": self.account.hex(),
                "records": [r.to_dict() for r in self.records],
                "height": self.height, "head_id": self.head_id.hex(),
                "used_refs": [x.hex() for x in self.used_refs],
                "balance": self.balance, "earned_ctp": self.earned_ctp,
                "burned_total": self.burned_total,
                "burns": [list(b) for b in self.burns]}

    @classmethod
    def from_dict(cls, d) -> "Chain":
        c = cls(bytes.fromhex(d["account"]))
        c.records = [Record.from_dict(r) for r in d["records"]]
        c.height = int(d["height"])
        c.head_id = bytes.fromhex(d["head_id"])
        c.used_refs = {bytes.fromhex(x) for x in d["used_refs"]}
        c.balance = int(d["balance"])
        c.earned_ctp = int(d["earned_ctp"])
        c.burned_total = int(d["burned_total"])
        c.burns = [tuple(b) for b in d["burns"]]
        return c

    def _append(self, record: Record, ref: Optional[bytes]) -> None:
        """Apply a *validated* record and update aggregates. The only mutator."""
        self.records.append(record)
        self.height = record.height
        self.head_id = record.record_id()
        if ref is not None:
            self.used_refs.add(ref)
        k = record.kind
        if k == KIND_SETTLE:
            amt = record.body["amount"]
            self.balance += amt
            # The WEIGHT-BEARING pool (§10). A positive settlement adds to it only
            # when it is (a) from a DIFFERENT account (never self-dealing) AND
            # (b) REPLAY-CLASS work (weight_bearing) — float credit is spendable
            # but never votes (§3). This is the instrument that closes the
            # sockpuppet-weight / debit-abandonment attack: weight is priced in
            # verifiable cycles, auditable by replay (challenge_receipt), so
            # signing receipts you never earned buys spendable IOUs, not a vote.
            if (amt > 0
                    and record.body["counterparty"] != record.account.hex()
                    and record.body.get("weight_bearing")):
                self.earned_ctp += amt
        elif k == KIND_TRANSFER:
            # Moved credit changes the net balance but does NOT add to the
            # burnable pool: only earned WORK (a settle from a stranger) may be
            # burned (§10), so self-minted credit cannot be laundered into weight
            # via a transfer hop.
            self.balance += record.body["amount"]
        elif k == KIND_BURN:
            amt = record.body["amount"]
            self.balance -= amt
            self.burned_total += amt
            self.burns.append((amt, record.body["timestamp"]))


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8 — the TCM (§8). validate_record does the straight-line, fixed-budget
# checks for one record against existing chain state. No loops, no dynamic
# dispatch beyond the kind switch, no unbounded recursion — the machine is
# TOTAL, so halting is not a question and gas metering is unnecessary (§1.4).
# An inference job is NEVER validated here (§2).
# ═══════════════════════════════════════════════════════════════════════════

def _check_self_sig(record: Record, alg) -> None:
    """Every record is sealed by the account's OWN key (§5)."""
    if not alg.verify(record.account, record.sig, record.signing_bytes()):
        raise ValidationError("self-sig", "record not signed by its own account")


def _check_link(record: Record, chain: Chain) -> None:
    """Monotonic height + prev links to this chain's head (§5/§6.1). A violation
    is a fork / double-spend attempt — the one event needing global agreement."""
    if record.height != chain.height + 1:
        raise ForkError("height", f"expected height {chain.height + 1}, "
                                  f"got {record.height}")
    if record.prev != chain.head_id:
        raise ForkError("prev-link", "prev does not reference the chain head")


def _validate_open(record: Record, chain: Chain, alg) -> Optional[bytes]:
    if chain.records:
        raise ValidationError("reopen", "account chain already opened")
    if record.height != 0:
        raise ValidationError("height", "OPEN must be height 0")
    if record.prev != genesis_marker(record.account, record.alg):
        raise ValidationError("genesis-prev",
                              "OPEN prev must be the digest of the PUBKEY")
    _check_self_sig(record, alg)
    return None


def _validate_settle(record: Record, chain: Chain, receipt: Optional[Receipt],
                     alg) -> Optional[bytes]:
    if receipt is None:
        raise ValidationError("missing-receipt", "SETTLE needs its receipt")
    _check_link(record, chain)

    # Counterparty signature (§8): the receipt must be BOTH-signed. This is the
    # anti-forgery check — a peer cannot mint credit its counterparty never
    # agreed to, because the counterparty's signature is verified here.
    msg = receipt.signing_bytes()
    if not alg.verify(receipt.worker_id, receipt.worker_sig, msg):
        raise ValidationError("receipt-worker-sig", "worker signature invalid")
    if not alg.verify(receipt.requester_id, receipt.requester_sig, msg):
        raise ValidationError("receipt-requester-sig",
                              "counterparty (requester) signature invalid")

    # The record must be one lawful side of THIS receipt, ± matching (§8).
    expect_amt, expect_ctp = _settle_role(record.account, receipt)
    if expect_amt is None:
        raise ValidationError("receipt-not-party", "record account not on receipt")
    if record.body.get("amount") != expect_amt:
        raise ValidationError("amount", "±amount does not match the receipt")
    if record.body.get("counterparty") != expect_ctp.hex():
        raise ValidationError("counterparty", "counterparty mismatch")

    # Blinded commitment well-formed, and the bare MMID is absent (§7).
    if record.body.get("blinded") != receipt.blinded().hex():
        raise ValidationError("blinded", "blinded commitment malformed")

    # Verification class and weight-bearing flag must match the receipt (§3/§10):
    # a node cannot mislabel float work as replay-class to steal a vote.
    if record.body.get("vclass") != receipt.vclass:
        raise ValidationError("vclass", "record vclass does not match the receipt")
    if record.body.get("weight_bearing") != is_weight_bearing(receipt.vclass):
        raise ValidationError("weight-bearing",
                              "weight_bearing flag inconsistent with vclass")

    # Single-use receipt-hash per chain (§6.1): replay is rejected by
    # construction; height already forbids re-ordering.
    rh = receipt.hash()
    if record.body.get("receipt_hash") != rh.hex():
        raise ValidationError("receipt-hash", "receipt_hash body mismatch")
    if rh in chain.used_refs:
        raise ValidationError("receipt-replay", "receipt-hash already used")

    _check_self_sig(record, alg)
    return rh


def _validate_transfer(record: Record, chain: Chain, auth: Optional[TransferAuth],
                       alg, transfer_floor: Optional[int]) -> Optional[bytes]:
    if auth is None:
        raise ValidationError("missing-auth", "TRANSFER needs its SEND/RECEIVE")
    _check_link(record, chain)

    msg = auth.signing_bytes()
    if not alg.verify(auth.sender_id, auth.sender_sig, msg):
        raise ValidationError("transfer-sender-sig", "sender signature invalid")
    if not alg.verify(auth.receiver_id, auth.receiver_sig, msg):
        raise ValidationError("transfer-receiver-sig", "receiver signature invalid")

    expect_amt, expect_ctp = _transfer_role(record.account, auth)
    if expect_amt is None:
        raise ValidationError("transfer-not-party", "record account not on auth")
    if record.body.get("amount") != expect_amt:
        raise ValidationError("amount", "±amount does not match the transfer")
    if record.body.get("counterparty") != expect_ctp.hex():
        raise ValidationError("counterparty", "counterparty mismatch")

    ref = auth.hash()
    if record.body.get("transfer_ref") != ref.hex():
        raise ValidationError("transfer-ref", "transfer_ref body mismatch")
    if ref in chain.used_refs:
        raise ValidationError("transfer-replay", "transfer-ref already used")

    # Debit does not drive balance below the node-policy floor (§8), when set.
    if expect_amt < 0 and transfer_floor is not None:
        if chain.balance + expect_amt < transfer_floor:
            raise ValidationError("floor", "debit below node-policy floor")

    _check_self_sig(record, alg)
    return ref


def _validate_burn(record: Record, chain: Chain, alg,
                   now: Optional[int]) -> Optional[bytes]:
    _check_link(record, chain)
    if now is None:
        raise ValidationError("no-now", "BURN validation requires a reference now")

    ts = record.body.get("timestamp")
    if not isinstance(ts, int):
        raise ValidationError("timestamp", "BURN timestamp missing")
    # Clock skew (§6.2): reject a timestamp grossly outside the supplied `now`.
    if abs(ts - now) > TIME_TOLERANCE_SECONDS:
        raise ValidationError("timestamp",
                              f"|ts − now| = {abs(ts - now)}s exceeds "
                              f"±{TIME_TOLERANCE_SECONDS}s tolerance")

    amt = record.body.get("amount")
    if not isinstance(amt, int) or amt <= 0:
        raise ValidationError("amount", "BURN amount must be positive")

    # Earned-from-counterparty rule (§10). NOTE ON A SPEC AMBIGUITY: §8 says
    # "amount ≤ balance" while §5's net-balance formula subtracts requester
    # debits; in the SYMMETRIC genesis (§10) both parties net to zero yet the
    # spec insists both may burn. We resolve the conflict in favour of §10's
    # repeated, explicitly-reasoned invariant: the burn bound is the EARNED
    # (counterparty) pool, not the net balance. This also makes self-minted
    # credit unburnable, which is the whole point of "no self-burn".
    if amt > chain.burnable:
        raise ValidationError("unearned",
                              f"burn {amt} exceeds earned-from-counterparty "
                              f"credit {chain.burnable} (self-burn refused)")

    _check_self_sig(record, alg)
    return None


def validate_record(record: Record, chain: Chain, receipt=None,
                    now: Optional[int] = None,
                    transfer_floor: Optional[int] = None) -> Optional[bytes]:
    """The normative TCM entry point (§8). Validates ONE record against existing
    chain state in bounded, straight-line work and returns the single-use ref to
    record (or None). Raises ValidationError / ForkError / AlgError on refusal.

    `receipt` supplies the off-ledger Receipt (SETTLE) or TransferAuth (TRANSFER)
    the record references — the node holds these pairwise objects (§7)."""
    # Resolve the primitive suite FIRST (§12): unknown alg → UnknownAlg here
    # (never a KeyError); a recognized-but-stub alg refuses at first use below.
    alg = get_alg(record.alg)

    if record.kind == KIND_OPEN:
        return _validate_open(record, chain, alg)
    if record.kind == KIND_SETTLE:
        return _validate_settle(record, chain, receipt, alg)
    if record.kind == KIND_TRANSFER:
        return _validate_transfer(record, chain, receipt, alg, transfer_floor)
    if record.kind == KIND_BURN:
        return _validate_burn(record, chain, alg, now)
    raise ValidationError("unknown-kind", f"no TCM rule for kind {record.kind!r}")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9 — the Ledger: a bag of account chains + the convenience API (§5/§10).
# ═══════════════════════════════════════════════════════════════════════════

class Ledger:
    """The block-lattice (§5): one Chain per account, no global order. Balances
    are locally verifiable; only a fork needs consensus (§9), which is out of
    this offline core."""

    def __init__(self, transfer_floor: Optional[int] = None):
        self.chains: Dict[bytes, Chain] = {}
        self.transfer_floor = transfer_floor

    # ── account lifecycle ──────────────────────────────────────────────────
    def open_account(self, identity: Identity, alg: int = ALG_ED25519) -> Record:
        acct = identity.account_id
        if acct in self.chains:
            raise ValidationError("exists", "account already opened")
        chain = Chain(acct)
        rec = build_open_record(identity, alg)
        validate_record(rec, chain)
        chain._append(rec, None)
        self.chains[acct] = chain
        return rec

    def post(self, record: Record, receipt=None, now: Optional[int] = None
             ) -> Record:
        """Validate a record against its chain, then apply it. The only path by
        which state changes for non-OPEN records."""
        chain = self.chains.get(record.account)
        if chain is None:
            raise ValidationError("no-chain", "account not opened")
        ref = validate_record(record, chain, receipt, now, self.transfer_floor)
        chain._append(record, ref)
        return record

    # ── high-level operations ──────────────────────────────────────────────
    def settle_work(self, worker: Identity, requester: Identity, amount: int,
                    job: bytes = b"", output: Optional[bytes] = None,
                    vclass: int = VCLASS_NATIVE, nonce: Optional[bytes] = None,
                    alg: int = ALG_ED25519) -> Receipt:
        """Post a mutual-credit settlement for delivered work (§5): +amount on
        the worker's chain, −amount on the requester's chain, both referencing
        one both-signed receipt. Returns the (off-ledger) receipt. This is the
        ONLY way credit is minted, and it always nets to zero across the pair.

        ``job``/``output`` are the raw cargo octets the receipt commits to by
        WIRE digest (§12.4); ``vclass`` (default native, replay-class) decides
        whether the minted credit is weight-bearing (§10)."""
        if output is None:
            # A deterministic placeholder output for the tests/happy path; a real
            # worker supplies the actual output MMOE octets here.
            output = b"out:" + amount.to_bytes(8, "big") + job
        receipt = make_receipt(worker, requester, amount, job, output,
                               vclass, nonce, alg)

        wchain = self.chains[worker.account_id]
        self.post(build_settle_record(worker, wchain, receipt, alg), receipt)
        rchain = self.chains[requester.account_id]
        self.post(build_settle_record(requester, rchain, receipt, alg), receipt)
        return receipt

    def transfer(self, sender: Identity, receiver: Identity, amount: int,
                 nonce: Optional[bytes] = None, alg: int = ALG_ED25519
                 ) -> TransferAuth:
        """Move earned credit sender→receiver as a SEND/RECEIVE pair (§4/§8)."""
        auth = make_transfer_auth(sender, receiver, amount, nonce, alg)
        schain = self.chains[sender.account_id]
        self.post(build_transfer_record(sender, schain, auth, alg), auth)
        rchain = self.chains[receiver.account_id]
        self.post(build_transfer_record(receiver, rchain, auth, alg), auth)
        return auth

    def burn(self, identity: Identity, amount: int, timestamp: int, now: int,
             alg: int = ALG_ED25519) -> Record:
        """Convert earned credit into weight (§5/§10). `now` is the reference
        clock for the timestamp-tolerance check — passed in, never read."""
        chain = self.chains[identity.account_id]
        rec = build_burn_record(identity, chain, amount, timestamp, alg)
        return self.post(rec, now=now)

    # ── read models (§5/§9) ────────────────────────────────────────────────
    def balance(self, account_id: bytes) -> int:
        return self.chains[account_id].balance

    def earned(self, account_id: bytes) -> int:
        """Weight-bearing credit (replay-class work from a counterparty) — the
        burnable source (§10). Float earnings are spendable but never counted
        here, so they never become a vote (§3)."""
        return self.chains[account_id].earned_ctp

    def burnable(self, account_id: bytes) -> int:
        return self.chains[account_id].burnable

    def weight(self, account_id: bytes, now: int) -> float:
        """Decayed cumulative burn weight at the supplied `now` (§5/§6). A pure
        fold over this chain's burns; never reads a clock. New account → 0."""
        chain = self.chains[account_id]
        return sum(amt * decay(now - ts) for amt, ts in chain.burns)

    def can_vote(self, account_id: bytes, now: int) -> bool:
        """Weight is the franchise (§9/§10). Zero weight → no vote."""
        return self.weight(account_id, now) > 0.0

    def total_supply(self) -> int:
        """Σ balances across the mesh (§9.5). Mutual settlements net to zero, so
        this equals −(total burned): monotonically DECREASING as credit burns."""
        return sum(c.balance for c in self.chains.values())

    def total_burned(self) -> int:
        return sum(c.burned_total for c in self.chains.values())

    # ── persistence (a node keeps its full state across restarts) ────────────
    def to_dict(self) -> dict:
        return {"transfer_floor": self.transfer_floor,
                "chains": {a.hex(): c.to_dict()
                           for a, c in self.chains.items()}}

    @classmethod
    def from_dict(cls, d) -> "Ledger":
        led = cls(transfer_floor=d.get("transfer_floor"))
        for a_hex, cd in d["chains"].items():
            led.chains[bytes.fromhex(a_hex)] = Chain.from_dict(cd)
        return led

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f)

    @classmethod
    def load(cls, path: str) -> "Ledger":
        with open(path) as f:
            return cls.from_dict(json.load(f))


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10 — CRYPTO-primary header words (§4, Appendix C). The previously
# reserved, name-only primary, inhabited. These are THIN headers: the ledger
# logic works on the Record objects above, not on packed words. We reuse the
# real PRIMARY_CRYPTO constant and word builder — never hardcode the trit pair.
# ═══════════════════════════════════════════════════════════════════════════

# QUALIFIER (T21–T18, 4 trits, 81 slots) selects the word KIND (Appendix C).
# Reference wire codes — revisable at v0.2 before third-party interop; the field
# SEMANTICS are the frozen part. The escape slot (+,+,+,+) is reserved (Word
# Spec P4), so no KIND is assigned to it.
_ESCAPE_QUAL = V.from_trits([1, 1, 1, 1])   # (+,+,+,+) = 40 — reserved

CRYPTO_KIND_QUAL: Dict[str, int] = {
    # ledger-record words (§4)
    "OPEN": V.from_trits([-1, -1, 0, 0]),
    "SETTLE": V.from_trits([0, -1, 0, 0]),
    "TRANSFER": V.from_trits([1, -1, 0, 0]),
    "BURN": V.from_trits([-1, 0, 0, 0]),
    # crypto-primitive words (§4)
    "SIG": V.from_trits([0, 0, 0, 0]),
    "DIGEST": V.from_trits([1, 0, 0, 0]),
    "PUBKEY": V.from_trits([-1, 1, 0, 0]),
    "NONCE": V.from_trits([0, 1, 0, 0]),
    # protocol words (§4)
    "JOB": V.from_trits([1, 1, 0, 0]),
    "RESULT": V.from_trits([-1, -1, 1, 0]),
    "RECEIPT": V.from_trits([0, -1, 1, 0]),
}
assert _ESCAPE_QUAL not in CRYPTO_KIND_QUAL.values(), "escape slot must stay free"


def crypto_header_word(kind: str, alg: int = ALG_ED25519) -> int:
    """Emit the CRYPTO-primary header word for a record/protocol KIND (§4). The
    primary is the REAL PRIMARY_CRYPTO; the qualifier is the KIND slot; the
    payload carries the alg selector. A thin, self-describing 24-trit word any
    platform can emit and verify without a TTree."""
    if kind not in CRYPTO_KIND_QUAL:
        raise ValueError(f"no CRYPTO qualifier assigned for kind {kind!r}")
    return V._make_word(V.PRIMARY_CRYPTO, CRYPTO_KIND_QUAL[kind], alg)


def crypto_word_kind(word: int) -> Optional[str]:
    """Inverse of crypto_header_word: the KIND named by a CRYPTO-primary word,
    or None if the word is not CRYPTO-primary."""
    if V.get_primary(word) != V.PRIMARY_CRYPTO:
        return None
    qual = V.get_qualifier(word)
    for kind, code in CRYPTO_KIND_QUAL.items():
        if code == qual:
            return kind
    return None
