"""test_p2pcp_ledger.py — P2PCP v0.1 adversarial fixtures + happy path.

The Bundle-10 "law-test" discipline generalised to strangers (spec §13): every
threat in the model becomes a test written to FAIL the attacker, and the happy
path (§10 genesis) is proved last. Canon: ``docs/P2PCP-v0.1-SPEC.md``.

Run: ``cd 5500fp && python3 -m unittest test_p2pcp_ledger``

All clocks are fixed integers — the ledger never reads the wall clock, so every
decay/timestamp assertion here is deterministic (§6).

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import os
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


P = _load("p2pcp_ledger")

# A fixed reference clock for the whole suite (arbitrary epoch second).
NOW = 1_800_000_000
DAY = 24 * 3600


def ident(tag: bytes):
    """Deterministic identity from a short tag (padded to a 32-byte seed)."""
    return P.Identity.from_seed(tag.ljust(32, b"\x00"))


def fresh_pair():
    """Two opened accounts on a fresh ledger."""
    a, b = ident(b"worker"), ident(b"requester")
    led = P.Ledger()
    led.open_account(a)
    led.open_account(b)
    return led, a, b


# ═══════════════════════════════════════════════════════════════════════════
# §13 threat fixtures — one test per row of the threat table.
# ═══════════════════════════════════════════════════════════════════════════

class TestForgedReceipt(unittest.TestCase):
    """Threat: a peer signs a receipt its counterparty never signed.
    Defence: the counterparty-signature check (§8)."""

    def test_forged_receipt_rejected(self):
        led, worker, requester = fresh_pair()
        job = P.store_mmid([1, 2, 3, 4])
        # The worker forges the requester's signature (signs it himself).
        r = P.Receipt(worker.account_id, requester.account_id, 5, job,
                      nonce=b"n" * 16)
        msg = r.signing_bytes()
        r.worker_sig = worker.sign(msg)
        r.requester_sig = worker.sign(msg)            # forgery — wrong key
        rec = P.build_settle_record(worker, led.chains[worker.account_id], r)
        with self.assertRaises(P.ValidationError) as cm:
            led.post(rec, r)
        self.assertEqual(cm.exception.reason, "receipt-requester-sig")


class TestSelfMinting(unittest.TestCase):
    """Threat: one operator signs across two owned identities.
    Defence: net-zero double-entry (§5) — printing money is structural-impossible."""

    def test_self_minting_nets_zero(self):
        # One operator owns BOTH A and B and signs both sides.
        a, b = ident(b"op-A"), ident(b"op-B")
        led = P.Ledger()
        led.open_account(a)
        led.open_account(b)
        led.settle_work(a, b, 100)          # A "earns" 100 from B, both signed
        self.assertEqual(led.balance(a.account_id), +100)
        self.assertEqual(led.balance(b.account_id), -100)
        # The whole trick sums to zero: no free credit was created.
        self.assertEqual(led.total_supply(), 0)


class TestSelfBurn(unittest.TestCase):
    """Threat: burning un-earned (self-minted) credit for weight.
    Defence: only credit earned FROM A COUNTERPARTY may be burned (§10)."""

    def test_burn_with_no_earnings_rejected(self):
        led, a, _ = fresh_pair()
        rec = P.build_burn_record(a, led.chains[a.account_id], 1, NOW)
        with self.assertRaises(P.ValidationError) as cm:
            led.post(rec, now=NOW)
        self.assertEqual(cm.exception.reason, "unearned")

    def test_self_counterparty_credit_is_unburnable(self):
        # X posts a +N settlement whose counterparty is X itself. It is a valid
        # record but earns NO burnable weight, so the burn is refused.
        led = P.Ledger()
        x = ident(b"loner")
        led.open_account(x)
        r = P.make_receipt(x, x, 50, P.store_mmid([9, 9, 9, 9]), nonce=b"z" * 16)
        led.post(P.build_settle_record(x, led.chains[x.account_id], r), r)
        self.assertEqual(led.balance(x.account_id), 50)
        self.assertEqual(led.burnable(x.account_id), 0)     # self-earned ≠ earned
        rec = P.build_burn_record(x, led.chains[x.account_id], 50, NOW)
        with self.assertRaises(P.ValidationError) as cm:
            led.post(rec, now=NOW)
        self.assertEqual(cm.exception.reason, "unearned")


class TestDoubleSpendFork(unittest.TestCase):
    """Threat: two records at one height on one chain (a fork / double-spend).
    Defence: monotonic height + prev-link — detected locally at post (§5/§9)."""

    def test_fork_detected(self):
        led, worker, customer = fresh_pair()
        led.settle_work(worker, customer, 10)            # worker now has credit
        chain = led.chains[worker.account_id]
        # Two DIFFERENT burns both extending the same head at the same height.
        burn1 = P.build_burn_record(worker, chain, 1, NOW)
        burn2 = P.build_burn_record(worker, chain, 2, NOW)
        self.assertEqual(burn1.height, burn2.height)      # same height = a fork
        led.post(burn1, now=NOW)                          # first one wins locally
        with self.assertRaises(P.ForkError) as cm:
            led.post(burn2, now=NOW)                      # the fork is rejected
        self.assertEqual(cm.exception.reason, "height")


class TestReceiptReplay(unittest.TestCase):
    """Threat: re-post a stale receipt-hash.
    Defence: single-use per chain + monotonic height (§6.1)."""

    def test_receipt_replay_rejected(self):
        led, worker, requester = fresh_pair()
        job = P.store_mmid([7, 7, 7, 7])
        r = P.make_receipt(worker, requester, 20, job, nonce=b"once")
        chain = led.chains[worker.account_id]
        led.post(P.build_settle_record(worker, chain, r), r)     # first use — ok
        # Re-post the SAME receipt at the next (valid-link) height.
        replay = P.build_settle_record(worker, chain, r)
        with self.assertRaises(P.ValidationError) as cm:
            led.post(replay, r)
        self.assertEqual(cm.exception.reason, "receipt-replay")


class TestSybilWeightConservation(unittest.TestCase):
    """Threat: N identities split from one (a Sybil swarm).
    Defence: weight is conserved under identity-splitting (§10). Splitting buys
    NOTHING for voting."""

    def _burn_weight(self, led, customer, worker, amount, burn_time, eval_now):
        led.open_account(worker)
        led.settle_work(worker, customer, amount)        # earn from a counterparty
        led.burn(worker, amount, timestamp=burn_time, now=burn_time)
        return led.weight(worker.account_id, eval_now)

    def test_split_conserves_weight(self):
        burn_time = NOW
        eval_now = NOW + 5 * DAY                          # exercise real decay
        N = 1000

        # Swarm: 1000 identities, 1 burn each, all against a shared customer.
        led1 = P.Ledger()
        cust1 = ident(b"cust-1")
        led1.open_account(cust1)
        swarm_total = 0.0
        for i in range(N):
            w = P.Identity.from_seed(b"swarm" + i.to_bytes(27, "big"))
            swarm_total += self._burn_weight(led1, cust1, w, 1, burn_time, eval_now)

        # Whale: one identity, the whole 1000 burned at once, same clocks.
        led2 = P.Ledger()
        cust2 = ident(b"cust-2")
        led2.open_account(cust2)
        whale = ident(b"whale")
        whale_total = self._burn_weight(led2, cust2, whale, N, burn_time, eval_now)

        self.assertGreater(swarm_total, 0.0)
        self.assertAlmostEqual(swarm_total, whale_total, places=6)


class TestDeadbeatSettlementGranularity(unittest.TestCase):
    """Threat: a worker takes a job and returns nothing (or a requester stops
    paying). Defence: settlement granularity (§11) — settle per chunk, so
    neither party is exposed for more than k units."""

    def test_deadbeat_exposure_bounded(self):
        led, worker, requester = fresh_pair()
        n_chunks, k = 10, 1                               # k = 1 unit per chunk
        delivered = 6                                     # worker quits after 6
        for _ in range(delivered):
            led.settle_work(worker, requester, k)         # settle each chunk
        # The requester is debited ONLY for delivered chunks; the 4 undelivered
        # chunks left zero ledger footprint. Exposure never exceeds k.
        self.assertEqual(led.balance(worker.account_id), +delivered * k)
        self.assertEqual(led.balance(requester.account_id), -delivered * k)
        undelivered = n_chunks - delivered
        self.assertEqual(undelivered * k, 4)              # never posted, never owed
        # Per chunk the books balance exactly (delivered == paid at every
        # boundary), so the in-flight exposure is never more than one chunk = k.
        self.assertEqual(led.balance(worker.account_id),
                         -led.balance(requester.account_id))
        self.assertEqual(len(led.chains[worker.account_id].records) - 1, delivered)


class TestClockSkew(unittest.TestCase):
    """Threat: a BURN timestamp hours off the reference clock.
    Defence: ±tolerance reject (§6.2). Weight itself is computed locally."""

    def test_skewed_timestamp_rejected_and_within_accepted(self):
        led, worker, customer = fresh_pair()
        led.settle_work(worker, customer, 10)
        chain = led.chains[worker.account_id]

        # 7 hours skew > ±6h tolerance → rejected.
        far = P.build_burn_record(worker, chain, 3, NOW + 7 * 3600)
        with self.assertRaises(P.ValidationError) as cm:
            led.post(far, now=NOW)
        self.assertEqual(cm.exception.reason, "timestamp")

        # 1 hour skew is within tolerance → accepted.
        near = P.build_burn_record(worker, chain, 3, NOW + 3600)
        led.post(near, now=NOW)
        self.assertGreater(led.weight(worker.account_id, NOW), 0.0)


class TestAlgNegotiation(unittest.TestCase):
    """Threat: a word tagged with an unimplemented / unknown primitive.
    Defence: graceful reject via the data-driven `alg` table (§12.1). Never a
    crash or a KeyError."""

    def test_alg0_roundtrips(self):
        alg = P.get_alg(P.ALG_ED25519)
        idn = ident(b"a0")
        msg = b"hello mesh"
        sig = alg.sign(idn.signing_key, msg)
        self.assertTrue(alg.verify(idn.account_id, sig, msg))
        self.assertFalse(alg.verify(idn.account_id, sig, b"tampered"))
        self.assertEqual(len(alg.wire_digest(msg)), 32)

    def test_alg1_recognized_but_unimplemented(self):
        alg = P.get_alg(P.ALG_TERNARY_NATIVE)             # recognized...
        with self.assertRaises(P.AlgUnimplemented):       # ...but refuses on use
            alg.wire_digest(b"x")
        # A record tagged alg=1 is refused gracefully, not crashed.
        rec = P.Record(ident(b"z").account_id, 0, b"", P.KIND_OPEN, {}, alg=1,
                       sig=b"x")
        with self.assertRaises(P.AlgUnimplemented):
            P.validate_record(rec, P.Chain(rec.account))

    def test_unknown_alg_rejected(self):
        with self.assertRaises(P.UnknownAlg):
            P.get_alg(7)
        rec = P.Record(ident(b"q").account_id, 0, b"", P.KIND_OPEN, {}, alg=7,
                       sig=b"x")
        with self.assertRaises(P.UnknownAlg):
            P.validate_record(rec, P.Chain(rec.account))


class TestBlindedCommitment(unittest.TestCase):
    """Threat: correlation of a requester via a repeated job MMID.
    Defence: blinded commitment H(MMID‖nonce) with a per-receipt nonce (§7.3)."""

    def test_same_job_two_nonces_do_not_correlate(self):
        job = P.store_mmid([42, 42, 42, 42])
        c1 = P.blinded_commitment(job, b"nonce-one")
        c2 = P.blinded_commitment(job, b"nonce-two")
        self.assertNotEqual(c1, c2)                       # cannot be linked
        # And the commitment is never the bare MMID.
        self.assertNotEqual(c1, P._mmid_bytes(job))

    def test_ledger_stores_blinded_not_bare_mmid(self):
        led, worker, requester = fresh_pair()
        led.settle_work(worker, requester, 5, job_words=[1, 1, 1, 1])
        body = led.chains[worker.account_id].records[-1].body
        self.assertIn("blinded", body)
        self.assertIn("receipt_hash", body)
        self.assertNotIn("job_mmid", body)                # bare MMID never on-ledger


class TestWireMmidSubstitution(unittest.TestCase):
    """Threat: a forged wire digest substitutes cargo.
    Defence: gauntlet-grade wire digest + verify-on-fetch (§12.4)."""

    def test_substituted_cargo_detected(self):
        cargo = b"the real model shard bytes"
        claimed = P.wire_mmid(cargo)
        self.assertTrue(P.verify_wire_cargo(claimed, cargo))     # honest fetch
        with self.assertRaises(P.WireMmidError):
            P.verify_wire_cargo(claimed, b"a malicious substitute")


class TestCryptoPrimaryInhabited(unittest.TestCase):
    """The CRYPTO primary (§4), previously reserved/name-only, now inhabited.
    Header words decode with primary == CRYPTO."""

    def test_all_kinds_decode_as_crypto(self):
        for kind in P.CRYPTO_KIND_QUAL:
            w = P.crypto_header_word(kind)
            self.assertEqual(P.V.get_primary(w), P.V.PRIMARY_CRYPTO)
            self.assertEqual(P.V.decode_word(w)["type"], "CRYPTO")
            self.assertEqual(P.crypto_word_kind(w), kind)     # round-trips
        # The escape slot (+,+,+,+) is reserved (Word Spec P4) — no KIND uses it.
        self.assertNotIn(P.V.from_trits([1, 1, 1, 1]),
                         P.CRYPTO_KIND_QUAL.values())


# ═══════════════════════════════════════════════════════════════════════════
# The happy path (§10 genesis) — proved LAST, after the threats.
# ═══════════════════════════════════════════════════════════════════════════

class TestGenesisHappyPath(unittest.TestCase):
    """§10: the testnet-of-two IS the genesis. Two fresh nodes, zero credit and
    zero weight, do each other's work and gain weight — no faucet, no premine,
    no coordinator."""

    def test_two_nodes_bootstrap_and_a_third_cannot_vote(self):
        led = P.Ledger()
        a, b = ident(b"node-A"), ident(b"node-B")
        led.open_account(a)
        led.open_account(b)

        # Fresh nodes: zero credit, zero weight (§10).
        for n in (a, b):
            self.assertEqual(led.balance(n.account_id), 0)
            self.assertEqual(led.earned(n.account_id), 0)
            self.assertEqual(led.weight(n.account_id, NOW), 0.0)

        # They do each other's work (mutual SETTLE), symmetric magnitude.
        led.settle_work(a, b, 8)          # A computed for B
        led.settle_work(b, a, 8)          # B computed for A

        # Both end with POSITIVE earned credit...
        self.assertEqual(led.earned(a.account_id), 8)
        self.assertEqual(led.earned(b.account_id), 8)
        # ...and total credit across the mesh sums to ZERO (double-entry).
        self.assertEqual(led.total_supply(), 0)

        # Burning reduces total supply, monotonically (§9.5).
        supply0 = led.total_supply()
        led.burn(a, 3, timestamp=NOW, now=NOW)
        supply1 = led.total_supply()
        self.assertLess(supply1, supply0)
        led.burn(b, 5, timestamp=NOW, now=NOW)
        supply2 = led.total_supply()
        self.assertLess(supply2, supply1)
        self.assertEqual(supply2, -8)                     # −(total burned)

        # Both now carry weight and may vote.
        self.assertGreater(led.weight(a.account_id, NOW), 0.0)
        self.assertGreater(led.weight(b.account_id, NOW), 0.0)
        self.assertTrue(led.can_vote(a.account_id, NOW))
        self.assertTrue(led.can_vote(b.account_id, NOW))

        # A fresh third node has zero weight and CANNOT vote (§10).
        c = ident(b"node-C")
        led.open_account(c)
        self.assertEqual(led.weight(c.account_id, NOW), 0.0)
        self.assertFalse(led.can_vote(c.account_id, NOW))

    def test_transfer_moves_earned_credit_and_conserves(self):
        # TRANSFER is a first-class kind (§4/§8); prove the validator path.
        led = P.Ledger()
        x, y, cust = ident(b"tx-X"), ident(b"tx-Y"), ident(b"tx-cust")
        for n in (x, y, cust):
            led.open_account(n)
        led.settle_work(x, cust, 30)                      # X earns 30
        before = led.total_supply()
        led.transfer(x, y, 12)                            # X sends 12 to Y
        self.assertEqual(led.balance(x.account_id), 30 - 12)
        self.assertEqual(led.balance(y.account_id), +12)
        self.assertEqual(led.total_supply(), before)      # a transfer conserves


if __name__ == "__main__":
    unittest.main()
