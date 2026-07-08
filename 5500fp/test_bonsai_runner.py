"""test_bonsai_runner.py — the Professor's Contract v1 adapter (UI-free).

Pins the adapter's contract shaping and, crucially, a FULL round-trip through
the real harness: ghost_bonsai.BonsaiProcess spawns bonsai_runner.py in mock
mode, a Contract v1 request goes down the pipe and a valid response comes back
that passes the interim consistency gate. That's the professor's pipe proven
end to end (with a mock model — the real llama backend is Stevo's to verify).
"""

import json
import os
import sys
import unittest

import bonsai_runner as R
import ghost_bonsai as B

_HERE = os.path.dirname(os.path.abspath(__file__))
_RUNNER = os.path.join(_HERE, 'bonsai_runner.py')


class TestContractShaping(unittest.TestCase):
    def test_prompt_carries_the_question(self):
        self.assertIn('what is a trit', R.build_prompt({'text': 'what is a trit'}))

    def test_response_is_valid_contract_v1(self):
        r = R.build_response('an answer', {'ghost_route': 'none'})
        ok, reason = B.validate_response(r)
        self.assertTrue(ok, reason)
        self.assertEqual(r['self_confidence'], 'unknown')     # honest default
        self.assertEqual(r['claimed_intent_class'], 'none')   # echoes GHOST

    def test_handle_line_valid(self):
        line = B.encode_request(B.build_request('x', [0] * 81, 'none', 1))
        resp = json.loads(R.handle_line(line, R.EchoBackend()))
        self.assertEqual(resp['version'], 1)

    def test_handle_line_drops_malformed(self):
        self.assertIsNone(R.handle_line('{not json', R.EchoBackend()))
        self.assertIsNone(R.handle_line('', R.EchoBackend()))
        self.assertIsNone(R.handle_line('42', R.EchoBackend()))   # not a request


class TestRoundTripThroughHarness(unittest.TestCase):
    def test_professor_pipe_end_to_end(self):
        p = B.BonsaiProcess([sys.executable, _RUNNER, '--mock'])
        self.assertTrue(p.start())
        try:
            req = B.build_request('what is a tribble?', [0] * 81, 'none', 1)
            resp, err = p.ask(req, timeout=15.0)
            self.assertIsNone(err)
            self.assertIsNotNone(resp)
            self.assertIn('tribble', resp['text'])
            gate = B.consistency_gate(resp, 'none', 1)      # none → nothing to
            self.assertTrue(gate.accepted)                   # contradict; accepted
            self.assertIsNotNone(gate.caveat)                # unknown confidence
        finally:
            p.stop()


class TestZeroConfigWiring(unittest.TestCase):
    def test_llama_backend_argv_is_the_proven_command(self):
        b = R.LlamaBackend('/x/llama-cli', '/y/m.gguf', n_predict=400)
        argv = b.argv('hello')
        self.assertEqual(argv[:5], ['/x/llama-cli', '-m', '/y/m.gguf',
                                    '-p', 'hello'])
        for flag in ('--temp', '--no-display-prompt', '-no-cnv'):
            self.assertIn(flag, argv)

    def test_discover_finds_binary_and_biggest_gguf(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bin_p = os.path.join(d, 'llama-cli')
            with open(bin_p, 'w') as f: f.write('#!x')
            os.chmod(bin_p, 0o755)
            with open(os.path.join(d, 'small.gguf'), 'w') as f: f.write('x')
            with open(os.path.join(d, 'big.gguf'), 'w') as f: f.write('x' * 100)
            found = R.discover(roots=[d])
            self.assertEqual(found['llama'], bin_p)
            self.assertTrue(found['model'].endswith('big.gguf'))

    def test_discover_none_when_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(R.discover(roots=[d]))

    def test_classroom_command_from_config(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bin_p = os.path.join(d, 'llama-cli')
            mod_p = os.path.join(d, 'm.gguf')
            with open(bin_p, 'w') as f: f.write('#!x')
            os.chmod(bin_p, 0o755)
            with open(mod_p, 'w') as f: f.write('x')
            cfg = os.path.join(d, 'bonsai.json')
            with open(cfg, 'w') as f:
                json.dump({'enabled': True, 'llama': bin_p,
                           'model': mod_p, 'n_predict': 128}, f)
            cmd = R.classroom_command(config_path=cfg, roots=[d])
            self.assertEqual(cmd[0], sys.executable)
            self.assertIn('--llama', cmd); self.assertIn(bin_p, cmd)
            self.assertIn('--n-predict', cmd); self.assertIn('128', cmd)

    def test_classroom_command_respects_off_switch(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            cfg = os.path.join(d, 'bonsai.json')
            with open(cfg, 'w') as f:
                json.dump({'enabled': False, 'llama': '/x', 'model': '/y'}, f)
            self.assertIsNone(R.classroom_command(config_path=cfg, roots=[d]))

    def test_classroom_command_none_when_nothing(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(R.classroom_command(
                config_path=os.path.join(d, 'nope.json'), roots=[d]))


class TestNoNetwork(unittest.TestCase):
    def test_source_has_no_network_surface(self):
        with open(_RUNNER) as f:
            src = f.read().lower()
        for forbidden in ('import socket', 'urllib', 'http', '.connect('):
            self.assertNotIn(forbidden, src, f'network surface: {forbidden!r}')


if __name__ == '__main__':
    unittest.main()
