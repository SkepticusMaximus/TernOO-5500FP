"""test_forge_json.py — the forge's parser must return a SPEC, never a shard.

Born 12-09-2026: a truncated Professor reply (token cap mid-field-list)
made _first_json 'succeed' on the first balanced INNER object — a single
field, zero `fields`, empty tree — while the model's JSON was fine. The
forge parser now prefers objects carrying `fields` and repairs truncated
tails by cutting back to a complete member and closing what's owed.

Run:  cd 5500fp && python3 -m unittest test_forge_json
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from macro_panel import _first_json, _forge_json, _json_closers

FULL = '''Here is the spec you asked for:
```json
{"name": "grep md", "kind": "command", "command": "grep",
 "fields": [{"flag": "-r", "label": "Recurse", "type": "check",
             "default": true, "group": "Common"}]}
```'''

TRUNCATED = '''```json
{
  "name": "grep usage",
  "command": "grep",
  "fields": [
    {"flag": "-E", "label": "Extended regex", "type": "check",
     "default": true, "group": "Advanced"},
    {"flag": "-r", "label": "Recurse", "type": "check",
     "default": false, "group": "Common"},
    {"flag": "-m", "label": "Stop after NUM", "type": "choice",
     "options": ["1", "2'''


class TestForgeJson(unittest.TestCase):
    def test_full_reply_parses_with_fields(self):
        obj = _forge_json(FULL)
        self.assertEqual(obj["name"], "grep md")
        self.assertEqual(len(obj["fields"]), 1)

    def test_truncated_reply_is_repaired_not_sharded(self):
        obj = _forge_json(TRUNCATED)
        self.assertIsNotNone(obj)
        self.assertIn("fields", obj)
        # the two COMPLETE members survive; the cut one is dropped
        self.assertEqual(len(obj["fields"]), 2)
        self.assertEqual(obj["name"], "grep usage")

    def test_old_parser_shows_why_this_exists(self):
        # documented failure mode: first balanced object is an inner field
        shard = _first_json(TRUNCATED)
        self.assertNotIn("fields", shard or {})   # the shard, not the spec

    def test_garbage_returns_none(self):
        self.assertIsNone(_forge_json("no json here at all"))

    def test_closers_are_string_aware(self):
        self.assertEqual(_json_closers('{"a": "brace } in string", "b": [1'),
                         "]}")


if __name__ == "__main__":
    unittest.main()
