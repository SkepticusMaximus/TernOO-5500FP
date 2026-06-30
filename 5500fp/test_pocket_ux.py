#!/usr/bin/env python3
"""Phase 7c-4 — Pocket UX tests.

Source-level wiring checks for the Flow-canvas pocket machinery (the live
behaviour — drilldown, breadcrumb, 📦 click, Escape, Properties Pocket section,
cross-scope rejection, 7c-3 drilldown — is verified offscreen). The data model
(parent_scope, scope-local edges) is the testable core.

Run:
    cd 5500fp && python3 -m unittest test_pocket_ux
"""

import os
import unittest

_FC = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   '..', 'FlowCode', 'flowcode.py')
with open(_FC) as f:
    SRC = f.read()


class TestPocketDataModel(unittest.TestCase):
    def test_parent_scope_field(self):
        # New symbols get parent_scope = current scope.
        self.assertIn("'parent_scope': fc_state.get('flow_scope')", SRC)

    def test_flow_scope_state(self):
        self.assertIn("'flow_scope':", SRC)

    def test_container_kinds(self):
        self.assertIn('_FC_CONTAINER_KINDS', SRC)
        self.assertIn("'flow_process'", SRC)
        self.assertIn("'flow_subroutine'", SRC)

    def test_entry_exit_hooks(self):
        # Stubbed cross-scope hooks on container kinds.
        self.assertIn("sym['entry_points'] = []", SRC)
        self.assertIn("sym['exit_points'] = []", SRC)


class TestScopeHelpers(unittest.TestCase):
    def test_helpers_present(self):
        for fn in ('_fc_children_of', '_fc_pocket_contents', '_fc_has_pocket',
                   '_fc_scope_path', '_fc_set_scope', '_fc_sym_by_name'):
            self.assertIn(f'def {fn}', SRC)


class TestDrilldownAndUI(unittest.TestCase):
    def test_scope_filtered_render(self):
        self.assertIn("if s.get('parent_scope') == _scope", SRC)

    def test_sym_at_scope_filtered(self):
        self.assertIn("only symbols in the current pocket scope", SRC)

    def test_pocket_indicator(self):
        self.assertIn('_fc_has_pocket(s)', SRC)
        self.assertIn('\U0001F4E6', SRC)   # 📦

    def test_breadcrumb(self):
        self.assertIn('_fc_breadcrumb', SRC)
        self.assertIn('def _fc_build_breadcrumb', SRC)
        self.assertIn('MainFlow', SRC)

    def test_escape_closes_pocket(self):
        self.assertIn('Closed pocket', SRC)

    def test_properties_pocket_section(self):
        self.assertIn('Open pocket →', SRC)
        self.assertIn('_fc_pocket_contents(s)', SRC)


class TestScopeLocalEdges(unittest.TestCase):
    def test_cross_scope_rejected(self):
        self.assertIn("edges are scope-local", SRC)

    def test_load_preserves_parent_scope(self):
        self.assertIn("'parent_scope': sym.get('parent_scope')", SRC)

    def test_scope_resets_on_load(self):
        self.assertIn("fc_state['flow_scope'] = None", SRC)


class TestNavIntegration(unittest.TestCase):
    def test_ctrl_click_drills(self):
        # _nav_center_flow_on drills into the target's pocket scope.
        self.assertIn("drill into the target's pocket scope", SRC)


if __name__ == '__main__':
    unittest.main()
