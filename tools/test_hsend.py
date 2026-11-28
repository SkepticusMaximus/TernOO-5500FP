#!/usr/bin/env python3
"""Tests for hsend — the scriptable hermetic send a crew agent uses to post its own mail.

    ~/.venvs/p2pcp/bin/python3 -m unittest tools.test_hsend
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import keyholder as K
from hermetic_wire import Wire
from hermetic_mailbox import HermeticMailbox
from hsend import resolve


class _DummyStore:
    def record(self, msgs): pass
    def messages(self): return []
    def disappeared(self, _): return []


class HSend(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.wire_p = os.path.join(self.tmp, "wire")
        for sub in ("pool", "directory"):
            os.makedirs(os.path.join(self.wire_p, sub))
        self.cc = K.Keyholder("CC")
        self.cf5 = K.Keyholder("CF5")
        w = Wire(self.wire_p)
        w.publish_card(self.cc)
        w.publish_card(self.cf5)
        self.mbx = HermeticMailbox(self.cc, self.wire_p, store=_DummyStore(), pins={})

    def test_resolve_finds_recipient(self):
        self.assertEqual(resolve(self.mbx, ["CF5"]), [self.cf5.aid])

    def test_resolve_unknown_rejects(self):
        with self.assertRaises(SystemExit):
            resolve(self.mbx, ["Nobody"])

    def test_sealed_letter_opens_for_recipient(self):
        handles = resolve(self.mbx, ["CF5"])
        res = self.mbx.send_group(from_account=self.cc.aid, to_contacts=handles,
                                  subject="docket ack", body="hello CF5")
        got = Wire(self.wire_p).fetch(self.cf5)               # CF5 opens the wire pool with its key
        opened = [m for m in got if m.get("id") == res["message_id"]]
        self.assertEqual(len(opened), 1)
        self.assertEqual(opened[0]["subject"], "docket ack")
        self.assertEqual(opened[0]["body"], "hello CF5")
        self.assertEqual(opened[0]["from"], self.cc.aid)      # signed as CC, verifiable by CF5

    def test_self_copy_is_kept(self):
        handles = resolve(self.mbx, ["CF5"])
        res = self.mbx.send_group(from_account=self.cc.aid, to_contacts=handles,
                                  subject="s", body="b")
        mine = [m for m in Wire(self.wire_p).fetch(self.cc) if m.get("id") == res["message_id"]]
        self.assertEqual(len(mine), 1)                        # CC keeps its own Sent copy


if __name__ == "__main__":
    unittest.main(verbosity=2)
