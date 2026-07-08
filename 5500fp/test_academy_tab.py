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
