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


def _stub_binary(path, rc=0):
    """A tiny runnable stand-in that answers --version with exit code rc —
    runnable() actually executes candidates now (the CUDA-corpse lesson)."""
    with open(path, 'w') as f:
        f.write(f'#!/bin/sh\nexit {rc}\n')
    os.chmod(path, 0o755)


class TestZeroConfigWiring(unittest.TestCase):
    def test_llama_backend_argv_single_turn_chat(self):
        b = R.LlamaBackend('/x/llama-cli', '/y/m.gguf', n_predict=128)
        argv = b.argv('hello')
        self.assertEqual(argv[:3], ['/x/llama-cli', '-m', '/y/m.gguf'])
        # identity-crisis fix: persona as a REAL system prompt, single turn
        self.assertIn('-sys', argv)
        self.assertIn(R.SYSTEM_PROMPT, argv)
        self.assertIn('-st', argv)
        self.assertNotIn('-no-cnv', argv)          # raw completion retired
        self.assertEqual(argv[argv.index('-p') + 1], 'hello')
        for flag in ('--temp', '--no-display-prompt',
                     '-c', '-t', '--prio'):        # memory/desktop kindness
            self.assertIn(flag, argv)

    def test_prompt_is_bare_question_persona_in_system(self):
        # the user turn carries ONLY the question; "You are Bonsai" lives in
        # SYSTEM_PROMPT (the board's identity crisis must not recur)
        p = R.build_prompt({'text': 'what is a tribble?'})
        self.assertEqual(p, 'what is a tribble?')
        self.assertNotIn('You are Bonsai', p)
        self.assertIn('You are Bonsai', R.SYSTEM_PROMPT)
        self.assertIn('/no_think', R.SYSTEM_PROMPT)

    def test_clean_reply_strips_think_blocks(self):
        self.assertEqual(
            R.clean_reply('<think>hmm, x is odd</think>A trit is a '
                          'balanced-ternary digit.'),
            'A trit is a balanced-ternary digit.')

    def test_clean_reply_drops_unterminated_think(self):
        # token budget ran out mid-thought → no answer, not a monologue
        self.assertEqual(R.clean_reply('<think>maybe it is a placeholder'), '')

    def test_only_thought_raises_with_hint(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            thinker = os.path.join(d, 'llama-completion')
            with open(thinker, 'w') as f:
                f.write('#!/bin/sh\necho "<think>endless musing"\nexit 0\n')
            os.chmod(thinker, 0o755)
            b = R.LlamaBackend(thinker, os.path.join(d, 'm.gguf'))
            with _RoomIsBig(), self.assertRaises(R.BackendError) as cm:
                b.generate('hello')
            self.assertIn('n_predict', str(cm.exception))

    def test_discover_finds_binary_and_biggest_gguf(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bin_p = os.path.join(d, 'llama-cli')
            _stub_binary(bin_p)
            with open(os.path.join(d, 'small.gguf'), 'w') as f: f.write('x')
            with open(os.path.join(d, 'big.gguf'), 'w') as f: f.write('x' * 100)
            found = R.discover(roots=[d])
            self.assertEqual(found['llama'], bin_p)
            self.assertTrue(found['model'].endswith('big.gguf'))

    def test_discover_skips_binary_that_cannot_run(self):
        # the top-level CUDA builds die instantly (rc 127) — discovery must
        # walk past them to one that actually runs here
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            dead = os.path.join(d, 'a-dead'); os.mkdir(dead)
            live = os.path.join(d, 'b-live'); os.mkdir(live)
            _stub_binary(os.path.join(dead, 'llama-completion'), rc=127)
            _stub_binary(os.path.join(live, 'llama-completion'), rc=0)
            with open(os.path.join(d, 'm.gguf'), 'w') as f: f.write('x')
            found = R.discover(roots=[d])
            self.assertEqual(found['llama'],
                             os.path.join(live, 'llama-completion'))

    def test_discover_none_when_empty(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            self.assertIsNone(R.discover(roots=[d]))

    def test_classroom_command_from_config(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            bin_p = os.path.join(d, 'llama-cli')
            mod_p = os.path.join(d, 'm.gguf')
            _stub_binary(bin_p)
            with open(mod_p, 'w') as f: f.write('x')
            cfg = os.path.join(d, 'bonsai.json')
            with open(cfg, 'w') as f:
                json.dump({'enabled': True, 'llama': bin_p,
                           'model': mod_p, 'n_predict': 128,
                           'ctx': 512, 'ask_timeout': 900}, f)
            cmd = R.classroom_command(config_path=cfg, roots=[d])
            self.assertEqual(cmd[0], sys.executable)
            self.assertIn('--llama', cmd); self.assertIn(bin_p, cmd)
            self.assertIn('--n-predict', cmd); self.assertIn('128', cmd)
            self.assertIn('--ctx', cmd); self.assertIn('512', cmd)
            self.assertEqual(R.ask_timeout(cfg), 900.0)

    def test_ask_timeout_default(self):
        self.assertEqual(R.ask_timeout('/nonexistent/bonsai.json'), 2400.0)

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


class _RoomIsBig:
    """Pin mem_available_mb high so stub-generate tests don't depend on the
    test machine's RAM of the moment."""

    def __enter__(self):
        self._real = R.mem_available_mb
        R.mem_available_mb = lambda: 999999
        return self

    def __exit__(self, *a):
        R.mem_available_mb = self._real


class TestRoomCheck(unittest.TestCase):
    def test_guard_refuses_when_room_too_small(self):
        real = R.mem_available_mb
        R.mem_available_mb = lambda: 1200          # 1.2GB free
        try:
            msg = R.mem_guard('/nonexistent.gguf')  # auto → ~2300+800 needed
            self.assertIsNotNone(msg)
            self.assertIn('1200 MB available', msg)
        finally:
            R.mem_available_mb = real

    def test_guard_passes_when_room_is_big(self):
        with _RoomIsBig():
            self.assertIsNone(R.mem_guard('/nonexistent.gguf'))

    def test_guard_honours_explicit_threshold(self):
        real = R.mem_available_mb
        R.mem_available_mb = lambda: 500
        try:
            self.assertIsNone(R.mem_guard('/x.gguf', min_free_mb=400))
            self.assertIsNotNone(R.mem_guard('/x.gguf', min_free_mb=600))
        finally:
            R.mem_available_mb = real

    def test_generate_refuses_before_spawning(self):
        # the whole point: refuse > thrash — no llama process is even run
        real = R.mem_available_mb
        R.mem_available_mb = lambda: 100
        try:
            b = R.LlamaBackend('/nonexistent/llama', '/nonexistent.gguf')
            with self.assertRaises(R.BackendError) as cm:
                b.generate('hello')
            self.assertIn('MB available', str(cm.exception))
        finally:
            R.mem_available_mb = real


class _FailingBackend:
    def generate(self, prompt):
        raise R.BackendError('llama exited rc=127: libcudart.so.12 missing')


class TestHonestFailure(unittest.TestCase):
    def test_backend_failure_emits_backend_error_line(self):
        line = B.encode_request(B.build_request('x', [0] * 81, 'none', 1))
        out = R.handle_line(line, _FailingBackend())
        obj = json.loads(out)
        self.assertIn('backend_error', obj)
        self.assertIn('libcudart', obj['backend_error'])

    def test_harness_surfaces_backend_error(self):
        # a child that answers every request with a backend_error line —
        # ask() must return (None, the real reason), not a parse complaint
        child = ("import sys, json\n"
                 "for line in sys.stdin:\n"
                 "    sys.stdout.write(json.dumps({'backend_error':"
                 " 'llama exited rc=1: failed to load model'}) + '\\n')\n"
                 "    sys.stdout.flush()\n")
        p = B.BonsaiProcess([sys.executable, '-c', child])
        self.assertTrue(p.start())
        try:
            req = B.build_request('why?', [0] * 81, 'none', 1)
            resp, err = p.ask(req, timeout=15.0)
            self.assertIsNone(resp)
            self.assertIn('failed to load model', err)
        finally:
            p.stop()

    def test_empty_generation_raises_not_ships(self):
        # LlamaBackend must never ship silence (the mute-professor lesson);
        # a stub that exits 0 with no stdout must raise BackendError
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            quiet = os.path.join(d, 'llama-completion')
            _stub_binary(quiet, rc=0)                  # prints nothing
            b = R.LlamaBackend(quiet, os.path.join(d, 'm.gguf'))
            with _RoomIsBig(), self.assertRaises(R.BackendError):
                b.generate('hello')


class TestNoNetwork(unittest.TestCase):
    def test_source_has_no_network_surface(self):
        with open(_RUNNER) as f:
            src = f.read().lower()
        for forbidden in ('import socket', 'urllib', 'http', '.connect('):
            self.assertNotIn(forbidden, src, f'network surface: {forbidden!r}')


if __name__ == '__main__':
    unittest.main()
