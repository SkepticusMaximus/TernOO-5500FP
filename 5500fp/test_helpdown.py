"""Law tests for helpdown. The one law above all: NEVER raise on content."""
import unittest

from helpdown import (parse_inline, parse_topic, topic_links, plain_text,
                      PLAIN, BOLD, CODE, H1, H2, BULLET, PARA)


class InlineLaws(unittest.TestCase):
    def test_plain(self):
        s = parse_inline("hello world")
        self.assertEqual(s, [{"text": "hello world", "style": PLAIN,
                              "link": None}])

    def test_bold(self):
        s = parse_inline("a **b** c")
        self.assertEqual([x["style"] for x in s], [PLAIN, BOLD, PLAIN])
        self.assertEqual(s[1]["text"], "b")

    def test_code(self):
        s = parse_inline("run `p2pcp serve` now")
        self.assertEqual(s[1]["style"], CODE)
        self.assertEqual(s[1]["text"], "p2pcp serve")

    def test_link_bare(self):
        s = parse_inline("see [[mesh]] tab")
        self.assertEqual(s[1]["link"], "mesh")
        self.assertEqual(s[1]["text"], "mesh")

    def test_link_labelled(self):
        s = parse_inline("see [[mesh|the Mesh tab]]")
        self.assertEqual(s[1]["link"], "mesh")
        self.assertEqual(s[1]["text"], "the Mesh tab")

    # --- the never-crash law: malformed syntax is literal ---
    def test_unmatched_bold_is_literal(self):
        s = parse_inline("a ** b")
        self.assertEqual("".join(x["text"] for x in s), "a ** b")

    def test_unmatched_code_is_literal(self):
        s = parse_inline("tick ` alone")
        self.assertEqual("".join(x["text"] for x in s), "tick ` alone")

    def test_unclosed_link_is_literal(self):
        s = parse_inline("bad [[link and on")
        self.assertEqual("".join(x["text"] for x in s), "bad [[link and on")

    def test_empty_link_target_is_literal(self):
        s = parse_inline("weird [[]] thing")
        self.assertEqual("".join(x["text"] for x in s), "weird [[]] thing")

    def test_empty_bold_is_literal(self):
        s = parse_inline("x **** y")
        self.assertEqual("".join(x["text"] for x in s), "x **** y")

    def test_adjacent_styles(self):
        s = parse_inline("**a**`b`[[c]]")
        self.assertEqual([x["style"] for x in s], [BOLD, CODE, PLAIN])
        self.assertEqual(s[2]["link"], "c")


class TopicLaws(unittest.TestCase):
    SAMPLE = ("The Mesh Tab\n"
              "section: Tabs\n"
              "\n"
              "# Your stall\n"
              "Sell compute to strangers, buy it from them,\n"
              "**no middleman**.\n"
              "\n"
              "- open a stall with `Open stall`\n"
              "- see also [[p2pcp|the protocol]]\n"
              "\n"
              "## Trust\n"
              "Replay, not reputation.")

    def test_title_and_section(self):
        t = parse_topic(self.SAMPLE)
        self.assertEqual(t["title"], "The Mesh Tab")
        self.assertEqual(t["section"], "Tabs")

    def test_block_kinds(self):
        t = parse_topic(self.SAMPLE)
        kinds = [b["kind"] for b in t["blocks"]]
        self.assertEqual(kinds, [H1, PARA, BULLET, BULLET, H2, PARA])

    def test_paragraph_joins_lines(self):
        t = parse_topic(self.SAMPLE)
        para = t["blocks"][1]
        text = "".join(s["text"] for s in para["spans"])
        self.assertEqual(text,
                         "Sell compute to strangers, buy it from them, "
                         "no middleman.")

    def test_links_collected(self):
        t = parse_topic(self.SAMPLE)
        self.assertEqual(topic_links(t), ["p2pcp"])

    def test_plain_text_searchable(self):
        t = parse_topic(self.SAMPLE)
        flat = plain_text(t)
        self.assertIn("Mesh", flat)
        self.assertIn("no middleman", flat)
        self.assertIn("Replay", flat)

    def test_no_section_line(self):
        t = parse_topic("Title only\n\nBody here.")
        self.assertIsNone(t["section"])
        self.assertEqual(t["blocks"][0]["kind"], PARA)

    # --- never-crash laws ---
    def test_empty_input(self):
        t = parse_topic("")
        self.assertEqual(t["title"], "(untitled)")
        self.assertEqual(t["blocks"], [])

    def test_title_only(self):
        t = parse_topic("Just a title")
        self.assertEqual(t["title"], "Just a title")
        self.assertEqual(t["blocks"], [])

    def test_garbage_never_raises(self):
        horror = ("T\nsection:\n# **[[\n`\n- [[|]]\n**bold `mix[[a|b]]** "
                  "unclosed\n\x00\x07 control chars \n[[x|y|z]]\n")
        t = parse_topic(horror)  # must not raise
        self.assertTrue(isinstance(t["blocks"], list))

    def test_pipe_in_label_kept(self):
        s = parse_inline("[[x|y|z]]")
        self.assertEqual(s[0]["link"], "x")
        self.assertEqual(s[0]["text"], "y|z")

    def test_section_empty_value_is_none(self):
        t = parse_topic("T\nsection:   \nBody")
        self.assertIsNone(t["section"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
