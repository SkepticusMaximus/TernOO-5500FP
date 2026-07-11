"""test_tab_chrome — guards the TAB_CHROME chrome contract in FlowCode/flowcode.py.

The point of the chrome contract (CF5 ruling, 2026-07-12) is that the tab order and
every tab's chrome live in ONE ordered table, read BY KEY — never re-encoded as
positional `idx == N` / `idx in (...)` dispatch scattered through the shell. Before
this contract, three separate functions each hard-coded a *different, stale* tab
order (do_clear still thought Shell was tab 3); a reorder silently mis-routed Clear
and the sidebar. These tests fail if the table drifts from the canon, if a keyed
dispatch dict names a tab that isn't in the table, or if magic index dispatch creeps
back into flowcode.

Pure source/AST inspection — no Tkinter, no display needed (import-free & headless).
"""
import ast
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_FLOWCODE = os.path.join(_HERE, "..", "FlowCode", "flowcode.py")

# The captain's canon (CLAUDE.md / chrome-contract dispatch): the ten tabs, in order.
CANON = ["flow", "gui", "sheet", "connectors", "shell", "text",
         "babble-fish", "academy", "mesh", "docs"]


def _source():
    with open(_FLOWCODE, encoding="utf-8") as f:
        return f.read()


def _find_assign(name):
    """Return the AST value node of the first `name = ...` assignment in flowcode."""
    tree = ast.parse(_source())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == name:
                    return node.value
    raise AssertionError(f"{name} not found in flowcode.py")


def _tab_chrome():
    """The TAB_CHROME list-of-dict literal (pure literals → literal_eval safe)."""
    return ast.literal_eval(_find_assign("TAB_CHROME"))


def _dict_string_keys(name):
    """The string keys of a `name = {...}` dict whose *values* may be callables
    (so literal_eval won't work) — we read only the literal key strings via AST."""
    node = _find_assign(name)
    assert isinstance(node, ast.Dict), f"{name} is not a dict literal"
    keys = []
    for k in node.keys:
        assert isinstance(k, ast.Constant) and isinstance(k.value, str), \
            f"{name} has a non-string key"
        keys.append(k.value)
    return keys


class TabChromeContract(unittest.TestCase):
    def setUp(self):
        self.rows = _tab_chrome()

    def test_order_is_canon(self):
        self.assertEqual([r["key"] for r in self.rows], CANON)

    def test_keys_unique(self):
        keys = [r["key"] for r in self.rows]
        self.assertEqual(len(keys), len(set(keys)))

    def test_every_row_fully_chromed(self):
        # New-tab law: a row alone declares a tab's chrome. Required fields present
        # and well-typed — a table row is enough to fully chrome a tab.
        for r in self.rows:
            for field in ("key", "title", "help_topic",
                          "wants_sidebar", "wants_output"):
                self.assertIn(field, r, f"{r.get('key')} row missing '{field}'")
            self.assertIsInstance(r["wants_sidebar"], bool)
            self.assertIsInstance(r["wants_output"], bool)
            self.assertTrue(r["title"] and r["help_topic"])

    def test_only_flow_wants_output(self):
        # The Output panel is the Flow execution trace; nothing else writes it.
        outs = [r["key"] for r in self.rows if r["wants_output"]]
        self.assertEqual(outs, ["flow"])

    def test_sidebar_relevance_matches_acceptance(self):
        # CF5 acceptance #3: ACTIONS (they live in the sidebar) present on Flow/GUI/
        # Sheet/Connectors/Shell/Babble-Fish; absent on Text/Academy/Mesh/Docs.
        want = {r["key"] for r in self.rows if r["wants_sidebar"]}
        self.assertEqual(want, {"flow", "gui", "sheet", "connectors",
                                "shell", "babble-fish"})


class KeyedDispatchStaysInSync(unittest.TestCase):
    """The keyed dispatch tables must reference only real tab keys — the failure
    mode the contract exists to kill (a builder wired to a tab that moved)."""

    def setUp(self):
        self.canon = {r["key"] for r in _tab_chrome()}

    def test_tab_tools_keys_are_real_tabs(self):
        for k in _dict_string_keys("_TAB_TOOLS"):
            self.assertIn(k, self.canon, f"_TAB_TOOLS has phantom key '{k}'")

    def test_tab_redraw_keys_are_real_tabs(self):
        for k in _dict_string_keys("_TAB_REDRAW"):
            self.assertIn(k, self.canon, f"_TAB_REDRAW has phantom key '{k}'")


class NoMagicIndexDispatch(unittest.TestCase):
    """Chrome logic must dispatch by key, never by positional tab index. This is a
    tripwire: comparing a tab `idx` to an integer literal (or an integer tuple) is
    the exact antipattern the contract retired."""

    def test_no_idx_vs_literal_in_source(self):
        src = _source()
        # `idx == 3`, `idx in (3, 7, 9)` — RHS starting with a digit or '(' after a
        # bare `idx`. `idx == some_var` / `len(...)` do NOT match (legit non-tab use).
        offenders = re.findall(r"\bidx\s*(?:==|in)\s*[\(0-9]", src)
        self.assertEqual(
            offenders, [],
            f"positional idx dispatch resurfaced ({len(offenders)}): "
            f"{offenders[:8]} — route tab dispatch through TAB_CHROME by key")


if __name__ == "__main__":
    unittest.main()
