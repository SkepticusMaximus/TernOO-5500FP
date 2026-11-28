#!/usr/bin/env python3
"""Regression test for the sealed-vs-sent indicator (CF5's ask).

A letter sealed into the spool but NOT yet carried to the wire must surface as pending=True —
that is the exact state that got mistaken for "sent". Run under the p2pcp venv (needs pyrage):

    ~/.venvs/p2pcp/bin/python3 -m unittest tools.test_pending_indicator
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import keyholder as K
from hermetic_wire import Wire
from hermetic_mailbox import HermeticMailbox


class _DummyStore:
    """inbox() persistence isn't under test here; _spool_pending never touches the store."""
    def record(self, msgs): pass
    def messages(self): return []
    def disappeared(self, _): return []


class PendingIndicator(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.wire_p = os.path.join(self.tmp, "wire")
        self.spool_p = os.path.join(self.tmp, "spool")
        for sub in ("pool", "directory"):
            os.makedirs(os.path.join(self.wire_p, sub))
            os.makedirs(os.path.join(self.spool_p, sub))
        self.kh = K.Keyholder("CC")
        Wire(self.wire_p).publish_card(self.kh)        # so open() can verify the sender signature
        self.mbx = HermeticMailbox(self.kh, self.wire_p, spool_path=self.spool_p, store=_DummyStore())
        self.who = {self.kh.aid: self.kh.display}

    def _seal_into_spool(self, subject, body):
        env, _ = self.kh.seal([self.kh.card()], subject, body)   # sealed to self (= a Sent self-copy)
        open(os.path.join(self.spool_p, "pool", "x.age"), "wb").write(env)

    def test_spooled_letter_is_pending(self):
        self._seal_into_spool("merge-rule docket", "hello CF5")
        pend = self.mbx._spool_pending(self.who)
        self.assertEqual(len(pend), 1)
        p = pend[0]
        self.assertTrue(p["pending"])                  # the whole point
        self.assertTrue(p["sent"])                     # it's our own outgoing letter
        self.assertEqual(p["subject"], "merge-rule docket")
        self.assertEqual(p["body"], "hello CF5")

    def test_empty_spool_has_no_pending(self):
        self.assertEqual(self.mbx._spool_pending(self.who), [])

    def test_inbox_appends_pending(self):
        self._seal_into_spool("sealed one", "body")
        got = self.mbx.inbox()
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0]["pending"])

    def test_no_spool_no_crash(self):
        mbx = HermeticMailbox(self.kh, self.wire_p, spool_path=None, store=_DummyStore())
        self.assertEqual(mbx._spool_pending(self.who), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
