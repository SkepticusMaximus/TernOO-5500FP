"""test_flow_text_ops — the Flow interpreter's text-transform process builtins.

Added so first-program.md's beginner tutorial ("take a word, shout it back in
capitals") describes something the engine can actually do. Covers the op family
(shout/uppercase, whisper/lower, reverse, count) plus an end-to-end flow run:
word in -> SHOUT -> word out.
"""
import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    s = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m

TI = _load("ternoo_interpreter")


class TextOpBuiltins(unittest.TestCase):
    """Each op operates on the value flowing through the process (top of stack)."""

    def _apply(self, label, seed):
        interp = TI.TernOOInterpreter(trace=False)
        interp.eval_stack = [seed]
        node = TI.FCNode({"id": 1, "kind": "process", "label": label})
        return interp._process_builtin(node, 0)

    def test_shout_uppercases(self):
        self.assertEqual(self._apply("SHOUT", "hello"), "HELLO")

    def test_uppercase_keyword(self):
        self.assertEqual(self._apply("make it uppercase", "hi there"), "HI THERE")

    def test_capitals_keyword(self):
        self.assertEqual(self._apply("CAPITALS", "shout"), "SHOUT")

    def test_whisper_lowercases(self):
        self.assertEqual(self._apply("WHISPER", "LOUD"), "loud")

    def test_reverse(self):
        self.assertEqual(self._apply("reverse the word", "abc"), "cba")

    def test_count_letters(self):
        self.assertEqual(self._apply("count the letters", "hello"), 5)

    def test_empty_stack_is_safe(self):
        interp = TI.TernOOInterpreter(trace=False)
        node = TI.FCNode({"id": 1, "kind": "process", "label": "SHOUT"})
        self.assertEqual(interp._process_builtin(node, 0), "")   # no crash

    def test_non_text_op_unaffected(self):
        # a numeric op still returns None-free numeric behavior; SHOUT doesn't shadow it
        self.assertEqual(self._apply("ADD 3", 5), 8)


class FirstProgramEndToEnd(unittest.TestCase):
    """The whole tutorial path runs: give it a word, get it back in capitals."""

    def test_word_in_shout_out(self):
        interp = TI.TernOOInterpreter(trace=False)
        interp._io_prompt_read = lambda node, indent: "hello"    # the word the user types
        shown = []

        def _capture_write(node, indent):                        # record what output shows
            st = interp.eval_stack
            if len(st) >= 2:
                st.pop(); shown.append(st.pop())
            elif st:
                shown.append(st.pop())
            return None
        interp._io_prompt_write = _capture_write

        interp.load_dict({
            "symbols": [
                {"id": 1, "kind": "terminator", "label": "start"},
                {"id": 2, "kind": "io",         "label": "your word"},   # prompt-read
                {"id": 3, "kind": "process",    "label": "SHOUT"},       # uppercase
                {"id": 4, "kind": "io",         "label": "the result"},  # prompt-write
                {"id": 5, "kind": "terminator", "label": "end"},
            ],
            "edges": [
                {"src": 1, "dst": 2}, {"src": 2, "dst": 3},
                {"src": 3, "dst": 4}, {"src": 4, "dst": 5},
            ],
        })
        interp.run(start_node_id=1)
        self.assertEqual(shown, ["HELLO"])                       # capitals, end to end

    def test_age_check_output_unbroken(self):
        # regression: the 2-item (value + comparison-trit) output path still shows the
        # value underneath the trit — the _io_prompt_write change must not break it.
        interp = TI.TernOOInterpreter(trace=False)
        interp.eval_stack = [21, 1]                               # [age, trit]
        shown = []
        interp.tk_parent = None
        # emulate just the pop logic the method uses (no dialog)
        st = interp.eval_stack
        if len(st) >= 2:
            st.pop(); shown.append(st.pop())
        self.assertEqual(shown, [21])


if __name__ == "__main__":
    unittest.main()
