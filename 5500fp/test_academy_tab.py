"""test_academy_tab.py — the classroom's pure presentation laws (UI-free).

The tab itself is furniture (verified on-screen by Stevo); these pin the
pure helpers that decide what the thought bubbles, grading strip, and
blackboard SAY — so honesty of display is testable without a display.
"""

import unittest

import ghost_tab_view as A
import ghost_bonsai as B


class TestStudentThought(unittest.TestCase):
    def test_none_is_question_mark(self):
        self.assertEqual(A.student_thought('none', 1), '?')

    def test_command_class_strips_prefix(self):
        self.assertEqual(A.student_thought('cmd_open', 5), 'open · margin 5')

    def test_surface_class_shown_with_margin(self):
        self.assertEqual(A.student_thought('surfaces', 3),
                         'surfaces · margin 3')


class TestProfAndGrading(unittest.TestCase):
    def test_prof_thought(self):
        self.assertEqual(A.prof_thought(12), 'composing… 12 tok')

    def test_grading_label(self):
        self.assertEqual(A.grading_label(0.944), '94.4%')
        self.assertEqual(A.grading_label(1.0), '100.0%')


class TestPresentBonsai(unittest.TestCase):
    RESP = {'version': 1, 'text': 'use sed -n', 'self_confidence': 0.9,
            'claimed_intent_class': 'surface_shell'}

    def test_accepted_clean(self):
        gate = B.GateResult(True, 'consistent', None)
        self.assertEqual(A.present_bonsai(gate, self.RESP), 'use sed -n')

    def test_accepted_with_caveat_shows_warning(self):
        gate = B.GateResult(True, 'consistent', 'low confidence')
        out = A.present_bonsai(gate, self.RESP)
        self.assertIn('use sed -n', out)
        self.assertIn('low confidence', out)

    def test_held_back_states_reason(self):
        gate = B.GateResult(False, 'disagreement: ...', None)
        out = A.present_bonsai(gate, self.RESP)
        self.assertIn('held back', out)
        self.assertIn('disagreement', out)


class TestBackstage(unittest.TestCase):
    """The corridor's laws (164000): ungated at our layer, no curriculum
    contamination, no sockets. The pure text helper is tested directly; the
    isolation guarantees are pinned STRUCTURALLY against the handler source
    (they must hold by construction, not by runtime luck)."""

    def test_ghost_text_routed(self):
        self.assertEqual(A.backstage_ghost_text('cmd_open', 5),
                         'that sounds like open  (margin 5) — try `open(...)`')

    def test_ghost_text_refusal(self):
        self.assertIn("can't do that", A.backstage_ghost_text('none', 0))

    def test_teaching_notice_directs_to_class(self):
        self.assertIn('classroom', A.BACKSTAGE_TEACHING_NOTICE)

    def _src(self, method):
        """Method source with docstrings/strings-of-prose stripped — the
        guards pin CODE, not the sentences describing the guarantee."""
        import inspect
        import re
        src = inspect.getsource(method)
        return re.sub(r'"""[\s\S]*?"""', '', src)

    def test_prof_console_is_ungated_at_our_layer(self):
        # acceptance #3: the gate function is NOT in the panel path
        src = self._src(A.GhostTabView._backstage_send_prof)
        self.assertNotIn('consistency_gate', src)
        self.assertNotIn('should_delegate', src)     # no consent ceremony

    def test_corridor_never_touches_the_curriculum(self):
        # acceptance #2: nothing enters .chat turns, the ledger, or training
        for m in (A.GhostTabView._backstage_send_prof,
                  A.GhostTabView._backstage_send_ghost):
            src = self._src(m)
            self.assertNotIn('.turns', src)
            self.assertNotIn('save_chat', src)
            self.assertNotIn('.learn', src)
            self.assertNotIn('harness.chat', src)    # route() only — no logging

    def test_corridor_logs_to_its_own_files(self):
        self.assertNotEqual(A.BACKSTAGE_PROF_LOG, A.BACKSTAGE_GHOST_LOG)
        for name in (A.BACKSTAGE_PROF_LOG, A.BACKSTAGE_GHOST_LOG):
            self.assertTrue(name.startswith('backstage-'))
            self.assertFalse(name.endswith('.chat'))  # never a curriculum doc

    def test_no_network_surface_in_tab(self):
        # acceptance #4: the panel path creates no socket — whole-module guard
        import os
        p = os.path.join(os.path.dirname(os.path.abspath(A.__file__)),
                         'ghost_tab_view.py')
        with open(p) as f:
            src = f.read().lower()
        for forbidden in ('import socket', 'urllib', 'http'):
            self.assertNotIn(forbidden, src,
                             f'network surface found: {forbidden!r}')


class TestFormatReport(unittest.TestCase):
    def test_report_lines(self):
        rep = {'held_out_accuracy': 0.9, 'held_out_n': 40,
               'refusal_check': '10/10', 'weights_as_words': 2140,
               'worst_confusions': []}
        out = A.format_report(rep)
        self.assertIn('90.0%', out)
        self.assertIn('2140 NEURAL_CONNECTION', out)
        self.assertIn('(none)', out)


if __name__ == '__main__':
    unittest.main()
