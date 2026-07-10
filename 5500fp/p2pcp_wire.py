"""p2pcp_wire.py — the wire contract frames (spec §4 L2, Appendix C).

Contract v1 generalized over the wire: JOB / RESULT / RECEIPT / RECEIPT_ACK /
DONE, as self-describing JSON envelopes carried inside the socket organ's framed
transport. Pure functions — no socket, no ledger state, no clock — so the framing
and the receipt serialization are testable on their own.

The exchange (spec §11 settlement granularity — settle per chunk, so neither
party is exposed for more than one chunk of k units):

  requester → JOB {job cargo + wire MMID, n_chunks, k, vclass}
  worker    → RESULT {chunk i output + its wire MMID}          (per chunk)
  requester → RECEIPT {a receipt for k, requester-signed}      (per chunk)
  worker    → RECEIPT_ACK {the same receipt, now both-signed}  (per chunk)
  worker    → DONE {reason}                                    (at the end)

A Receipt (p2pcp_ledger.Receipt) is carried as a flat dict of hex fields; the
receiving side re-instantiates it into its OWN Receipt class, so the wire crossing
is agnostic to which module instance built it.

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import json

# frame type tags
JOB = "JOB"
RESULT = "RESULT"
RECEIPT = "RECEIPT"
RECEIPT_ACK = "RECEIPT_ACK"
DONE = "DONE"
VOTE = "VOTE"                  # a signed conflict-vote (§9 / step 6)
PEERS_REQ = "PEERS_REQ"        # ask a peer for its known listen-addresses (v0.2)
PEERS = "PEERS"                # response: a list of [host, port] listen-addresses
RECORD = "RECORD"              # a gossiped ledger record (v0.2 — witness a branch)
STATUS_REQ = "STATUS_REQ"      # ask a node for its public status (observability)
STATUS = "STATUS"              # response: {account, caps, peers, jobs_served, ...}


def encode(frame: dict) -> bytes:
    """Canonical bytes for a frame (sorted keys, tight separators, UTF-8)."""
    return json.dumps(frame, sort_keys=True, separators=(",", ":")).encode("utf-8")


def decode(payload: bytes) -> dict:
    """Parse a frame. Contract: returns a dict, or raises ValueError — so a hostile
    payload that is valid JSON but NOT an object (e.g. ``[1,2]`` or ``42``) is
    rejected here, not later as an AttributeError on ``frame.get(...)``. json's
    JSONDecodeError is already a ValueError subclass, so callers catch one type."""
    frame = json.loads(payload)
    if not isinstance(frame, dict):
        raise ValueError("frame must be a JSON object")
    return frame


def receipt_to_dict(r) -> dict:
    """Flatten a Receipt to hex fields for the wire (nothing secret leaks that a
    pairwise counterparty does not already hold — §7)."""
    return {
        "worker": r.worker_id.hex(),
        "requester": r.requester_id.hex(),
        "amount": r.amount,
        "job_commit": r.job_commit.hex(),
        "output_commit": r.output_commit.hex(),
        "vclass": r.vclass,
        "nonce": r.nonce.hex(),
        "alg": r.alg,
        "worker_sig": r.worker_sig.hex(),
        "requester_sig": r.requester_sig.hex(),
    }


def record_to_dict(r) -> dict:
    """Flatten a ledger Record for gossip (v0.2). Its body is already JSON-safe
    (ints + hex strings). The receiver re-validates the self-signature."""
    return {
        "account": r.account.hex(),
        "height": r.height,
        "prev": r.prev.hex(),
        "kind": r.kind,
        "body": r.body,
        "alg": r.alg,
        "sig": r.sig.hex(),
    }


def record_from_dict(Record, d) -> "Record":
    return Record(
        bytes.fromhex(d["account"]),
        int(d["height"]),
        bytes.fromhex(d["prev"]),
        d["kind"],
        d["body"],
        int(d["alg"]),
        bytes.fromhex(d["sig"]),
    )


def receipt_from_dict(Receipt, d) -> "Receipt":
    """Re-instantiate a Receipt from its wire dict, into the caller's own
    Receipt class."""
    return Receipt(
        bytes.fromhex(d["worker"]),
        bytes.fromhex(d["requester"]),
        int(d["amount"]),
        bytes.fromhex(d["job_commit"]),
        bytes.fromhex(d["output_commit"]),
        int(d["vclass"]),
        bytes.fromhex(d["nonce"]),
        int(d["alg"]),
        bytes.fromhex(d["worker_sig"]),
        bytes.fromhex(d["requester_sig"]),
    )
