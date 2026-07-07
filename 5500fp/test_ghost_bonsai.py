"""test_ghost_bonsai.py — the Bonsai harness laws (UI-free).

Pins Contract v1 parse/round-trip, the interim consistency gate, the
consent-gated delegation rule, subprocess round-trip via an echo mock, and
the structural no-network guarantee. No display required.
"""

import json
import os
import sys
import unittest

import ghost_bonsai as B


VALID = {'version': 1, 'text': 'hello', 'self_confidence': 0.9,
         'claimed_intent_class': 'cmd_open'}


class TestContract(unittest.TestCase):
    def test_build_request_shape(self):
        req = B.build_request('open the file', [0] * 81, 'none', 1, 'commands')
        self.assertEqual(req['version'], B.CONTRACT_VERSION)
        self.assertEqual(req['text'], 'open the file')
        self.assertEqual(len(req['ghost_features']), 81)
        self.assertEqual(req['ghost_route'], 'none')
        self.assertEqual(req['major'], 'commands')

    def test_build_request_rejects_wrong_feature_length(self):
        with self.assertRaises(B.BonsaiProtocolError):
            B.build_request('x', [0] * 80, 'none', 1)

    def test_encode_parse_roundtrip(self):
        req = B.build_request('grep then sort', [1] * 81, 'surface_shell', 5)
        line = B.encode_request(req)
        self.assertTrue(line.endswith('\n'))
        self.assertEqual(json.loads(line)['text'], 'grep then sort')

    def test_parse_valid(self):
        self.assertEqual(B.parse_response(json.dumps(VALID))['text'], 'hello')

    def test_parse_bad_json_raises(self):
        with self.assertRaises(B.BonsaiProtocolError):
            B.parse_response('{not json')

    def test_parse_missing_field_raises(self):
        bad = dict(VALID); del bad['claimed_intent_class']
        with self.assertRaises(B.BonsaiProtocolError):
            B.parse_response(json.dumps(bad))

    def test_parse_wrong_version_raises(self):
        bad = dict(VALID); bad['version'] = 2
        with self.assertRaises(B.BonsaiProtocolError):
            B.parse_response(json.dumps(bad))

    def test_unknown_confidence_is_honored(self):
        r = dict(VALID); r['self_confidence'] = 'unknown'
        self.assertEqual(B.parse_response(json.dumps(r))['self_confidence'],
                         'unknown')

    def test_confidence_out_of_range_rejected(self):
        r = dict(VALID); r['self_confidence'] = 1.5
        with self.assertRaises(B.BonsaiProtocolError):
            B.parse_response(json.dumps(r))

    def test_embedding_optional_but_typed(self):
        good = dict(VALID); good['bonsai_embedding'] = [1, 2, 3]
        self.assertTrue(B.validate_response(good)[0])
        bad = dict(VALID); bad['bonsai_embedding'] = 'nope'
        self.assertFalse(B.validate_response(bad)[0])

    def test_safe_parse(self):
        resp, err = B.safe_parse_response(json.dumps(VALID))
        self.assertIsNotNone(resp); self.assertIsNone(err)
        resp, err = B.safe_parse_response('garbage')
        self.assertIsNone(resp); self.assertIsInstance(err, str)


class TestConsistencyGate(unittest.TestCase):
    def test_accept_when_ghost_none(self):
        # delegation's normal case: GHOST refused, nothing to contradict
        g = B.consistency_gate(VALID, 'none', 1)
        self.assertTrue(g.accepted)
        self.assertEqual(g.reason, 'consistent')

    def test_accept_when_confident_and_agrees(self):
        r = dict(VALID); r['claimed_intent_class'] = 'cmd_open'
        g = B.consistency_gate(r, 'cmd_open', 9)
        self.assertTrue(g.accepted)

    def test_reject_when_confident_and_disagrees(self):
        r = dict(VALID); r['claimed_intent_class'] = 'cmd_save'
        g = B.consistency_gate(r, 'cmd_open', 9)
        self.assertFalse(g.accepted)
        self.assertIn('disagreement', g.reason)

    def test_reject_malformed(self):
        g = B.consistency_gate({'version': 1}, 'none', 1)
        self.assertFalse(g.accepted)
        self.assertIn('malformed', g.reason)

    def test_reject_bad_provenance(self):
        g = B.consistency_gate(VALID, 'none', 1, provenance_ok=False)
        self.assertFalse(g.accepted)
        self.assertIn('provenance', g.reason)

    def test_caveat_on_unknown_confidence(self):
        r = dict(VALID); r['self_confidence'] = 'unknown'
        g = B.consistency_gate(r, 'none', 1)
        self.assertTrue(g.accepted)
        self.assertIsNotNone(g.caveat)

    def test_caveat_on_low_confidence(self):
        r = dict(VALID); r['self_confidence'] = 0.2
        g = B.consistency_gate(r, 'none', 1)
        self.assertTrue(g.accepted)
        self.assertIsNotNone(g.caveat)


class TestConsentGate(unittest.TestCase):
    def test_delegate_only_on_none_and_yes(self):
        self.assertTrue(B.should_delegate('none', True))

    def test_no_delegate_without_consent(self):
        self.assertFalse(B.should_delegate('none', False))

    def test_no_delegate_when_confident(self):
        self.assertFalse(B.should_delegate('cmd_open', True))


class TestSubprocess(unittest.TestCase):
    # a mock-Bonsai: reads one JSON request line, echoes a valid response
    ECHO = (
        "import sys, json\n"
        "for line in sys.stdin:\n"
        "    try: req = json.loads(line)\n"
        "    except Exception: continue\n"
        "    resp = {'version': 1, 'text': 'prof: ' + req.get('text',''),\n"
        "            'self_confidence': 0.9, 'claimed_intent_class': 'cmd_open'}\n"
        "    sys.stdout.write(json.dumps(resp) + '\\n'); sys.stdout.flush()\n")

    def test_missing_binary_is_graceful(self):
        p = B.BonsaiProcess(['/nonexistent/bonsai_runner_xyz'])
        self.assertFalse(p.available())
        self.assertFalse(p.start())
        self.assertEqual(p.status, B.NOT_RUNNING)
        resp, err = p.ask(B.build_request('x', [0] * 81, 'none', 1))
        self.assertIsNone(resp)
        self.assertEqual(err, 'bonsai not running')

    def test_no_cmd_is_graceful(self):
        p = B.BonsaiProcess()
        self.assertFalse(p.available())
        self.assertFalse(p.start())

    def test_echo_roundtrip(self):
        p = B.BonsaiProcess([sys.executable, '-c', self.ECHO])
        self.assertTrue(p.available())
        self.assertTrue(p.start())
        try:
            req = B.build_request('open sesame', [0] * 81, 'none', 1)
            resp, err = p.ask(req, timeout=10.0)
            self.assertIsNone(err)
            self.assertIsNotNone(resp)
            self.assertEqual(resp['text'], 'prof: open sesame')
            self.assertEqual(p.status, B.READY)
        finally:
            p.stop()
        self.assertEqual(p.status, B.NOT_RUNNING)


class TestNoNetwork(unittest.TestCase):
    def test_source_has_no_network_surface(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'ghost_bonsai.py')) as _f:
            src = _f.read().lower()
        for forbidden in ('import socket', 'urllib', 'http', '.connect('):
            self.assertNotIn(forbidden, src,
                             f'network surface found: {forbidden!r}')


if __name__ == '__main__':
    unittest.main()
