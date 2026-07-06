"""test_harness.py — GHOST Academy engine.

The tribble-song test is the heart: first contact's confidently-wrong
route ("Pack up your tribbles…" → math_round) must become a refusal after
being taught via !learn none — the humility bug fixed by the mechanism it
inspired.

Date: 2026-07-05, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import os
import tempfile
import unittest

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


H = _load('ghost_harness')
FS = _load('filesystem')
G = _load('ghost_train')

_EMU_OK = os.path.exists(H._EMU) and os.access(H._EMU, os.X_OK)
TRIBBLE = "Pack up your tribbles in your old trit bag and smile smile smile"


def _fresh():
    return H.Harness(fs=FS.HostFileSystem(tempfile.mkdtemp()))


class TestCurriculumAndLearn(unittest.TestCase):
    def setUp(self):
        self.h = _fresh()

    def test_corpus_seeds_from_templates(self):
        self.assertIn('cmd_text_upper', self.h.corpus)
        self.assertIn('none', self.h.corpus)
        self.assertTrue(self.h.fs.exists(H.CORPUS_FILE))

    def test_learn_appends_and_logs(self):
        out = self.h.learn('text_upper', 'crank the volume of the letters')
        self.assertIn('learned', out)
        self.assertIn('crank the volume of the letters',
                      self.h.corpus['cmd_text_upper'])
        self.assertIn('crank the volume', self.h.learn_log())

    def test_learn_unknown_class_rejected(self):
        with self.assertRaises(H.HarnessError):
            self.h.learn('summon_demons', 'do the thing')

    def test_learn_undo(self):
        self.h.learn('none', TRIBBLE)
        self.assertIn(TRIBBLE, self.h.corpus['none'])
        out = self.h.learn_undo()
        self.assertIn('unlearned', out)
        self.assertNotIn(TRIBBLE, self.h.corpus['none'])
        self.assertEqual(self.h.learn_undo(), 'nothing to undo')

    def test_learnlog_is_append_only(self):
        self.h.learn('none', 'one')
        self.h.learn_undo()
        self.h.learn('none', 'two')
        raw = self.h.fs.read(H.LEARNLOG_FILE).splitlines()
        self.assertEqual(len(raw), 3)          # learn, undo, learn — no edits

    def test_parse_bang(self):
        self.assertEqual(H.parse_bang('!learn text_upper "shout it"'),
                         ('learn', 'text_upper', 'shout it'))
        self.assertEqual(H.parse_bang('!learn-undo'), ('undo',))
        self.assertEqual(H.parse_bang('!learn-log'), ('log',))
        self.assertIsNone(H.parse_bang('ls'))
        with self.assertRaises(H.HarnessError):
            H.parse_bang('!learn onlyclass')


class TestTabAndReplHeadless(unittest.TestCase):
    def test_format_report_pure(self):
        gtv = _load('ghost_tab_view')
        txt = gtv.format_report({'held_out_accuracy': 0.944,
                                 'held_out_n': 195,
                                 'refusal_check': '10/10',
                                 'worst_confusions': [('a → b', 2)],
                                 'weights_as_words': 2140})
        self.assertIn('94.4%', txt)
        self.assertIn('a → b', txt)

    def test_repl_learn_roundtrip(self):
        R = _load('flowcode_repl')
        r = R.Repl(fs=self.fsdir)
        out = r.execute('!learn none "flatten the moon with a spoon"')
        self.assertIn('learned', out)
        self.assertIn('flatten the moon', r.execute('!learn-log'))
        self.assertIn('unlearned', r.execute('!learn-undo'))

    def setUp(self):
        self.fsdir = FS.HostFileSystem(tempfile.mkdtemp())


class TestChatFormat(unittest.TestCase):
    def test_roundtrip(self):
        turns = [{'user': 'make this loud',
                  'ghost': 'that sounds like text_upper  (margin 30) — …',
                  'route': 'cmd_text_upper', 'margin': 30, 'ts': 0},
                 {'user': TRIBBLE,
                  'ghost': "I'm sorry, I can't do that — yet.  (margin 5)",
                  'route': 'none', 'margin': 5, 'ts': 0}]
        model = {'classes': ['a'], 'margin': 3}
        text = H.format_chat(turns, model, title='first contact')
        parsed = H.parse_chat(text)
        self.assertEqual(parsed['meta']['title'], 'first contact')
        self.assertEqual(parsed['meta']['chat-version'], '1')
        self.assertEqual(len(parsed['turns']), 2)
        self.assertEqual(parsed['turns'][0]['route'], 'cmd_text_upper')
        self.assertEqual(parsed['turns'][0]['margin'], 30)
        self.assertEqual(parsed['turns'][1]['user'], TRIBBLE)

    def test_missing_frontmatter_rejected(self):
        with self.assertRaises(H.HarnessError):
            H.parse_chat('> hi\nghost: hello\n')


@unittest.skipUnless(_EMU_OK, "emulator binary not built")
class TestMajors(unittest.TestCase):
    """Spec A: majors mechanism + the Surface Advisor (Major #1)."""

    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.h = H.Harness(fs=FS.HostFileSystem(cls.d), major='surfaces')

    def test_unknown_major_rejected(self):
        with self.assertRaises(H.HarnessError):
            H.Harness(fs=FS.HostFileSystem(self.d), major='astrology')

    def test_surfaces_corpus_seeded_from_repo(self):
        self.assertIn('surface_flow', self.h.corpus)
        self.assertIn('none', self.h.corpus)
        self.assertTrue(self.h.fs.exists('ghost_corpus_surfaces.json'))

    def test_repo_model_routes_all_surfaces_natively(self):
        """The shipped ghost_major_surfaces.json routes one exemplar per
        surface on the EMULATOR, and refuses out-of-domain."""
        cases = {"track an order through its states": 'surface_flow',
                 "monthly totals per region": 'surface_sheet',
                 "grep then sort these lines": 'surface_shell',
                 "a settings dialog with two buttons": 'surface_gui',
                 "draft the readme for the project": 'surface_text',
                 "solve world hunger": 'none'}
        for text, want in cases.items():
            with self.subTest(text=text):
                got, margin = self.h.route(text)
                self.assertEqual(got, want)

    def test_majors_are_isolated(self):
        """A lesson taught to surfaces never leaks into commands."""
        cmd = H.Harness(fs=FS.HostFileSystem(self.d), major='commands')
        self.h.learn('surface_flow', 'sequence the ceremony of the keys')
        self.assertNotIn('sequence the ceremony of the keys',
                         sum(cmd.corpus.values(), []))
        self.assertFalse(cmd.fs.exists('ghost_learnlog_surfaces.jsonl')
                         and 'ceremony' in cmd.learn_log())

    def test_command_major_untouched(self):
        """Invariant 1 witness: default major still the original files."""
        cmd = H.Harness(fs=FS.HostFileSystem(self.d), major='commands')
        self.assertIn('cmd_text_upper', cmd.corpus)
        self.assertEqual(cmd._files['model'], 'ghost_model.json')


@unittest.skipUnless(_EMU_OK, "emulator binary not built")
class TestAcademy(unittest.TestCase):
    """The slow, real ones: train + native routing + the tribble redemption."""

    @classmethod
    def setUpClass(cls):
        cls.h = _fresh()
        # teach the first-contact refusal + a friend, then train once
        cls.h.learn('none', TRIBBLE)
        cls.h.learn('none', 'pack up your troubles in your old kit bag')
        cls.report = cls.h.train()

    def test_report_card_floor(self):
        self.assertGreaterEqual(self.report['held_out_accuracy'], 0.90)
        self.assertGreater(self.report['weights_as_words'], 1000)

    def test_native_routing_still_works(self):
        cls_, margin = self.h.route('make this text loud')
        self.assertEqual(cls_, 'cmd_text_upper')
        self.assertGreaterEqual(margin, self.h.model['margin'])

    def test_tribble_song_now_refused(self):
        """First contact's misroute, fixed by !learn none — the humility
        bug repaired through the mechanism it inspired."""
        cls_, _m = self.h.route(TRIBBLE)
        self.assertEqual(cls_, 'none')

    def test_chat_logs_and_saves(self):
        self.h.chat('make this text loud')
        self.h.chat('open the pod bay doors')
        p = self.h.save_chat('session.chat', title='academy test')
        parsed = H.parse_chat(self.h.fs.read(p))
        self.assertEqual(len(parsed['turns']), 2)
        self.assertEqual(parsed['turns'][1]['route'], 'none')


if __name__ == '__main__':
    unittest.main(verbosity=1)
