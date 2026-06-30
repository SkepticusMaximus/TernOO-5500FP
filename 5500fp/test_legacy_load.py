#!/usr/bin/env python3
"""Step 12 — legacy .ternoo back-compat regression test (headless, CI-safe).

Bundle 20 made .fc canonical and deprecated .ternoo with a backward-compat load
path. button_click_demo.ternoo is kept (Phase 7b-3 demo) as the regression
fixture. This verifies the legacy file is intact and parses into the structure
the IDE's load path expects (without needing a display).

Run:
    cd 5500fp && python3 -m unittest test_legacy_load
"""

import json
import os
import unittest

_FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'FlowCode', 'button_click_demo.ternoo')


class TestLegacyTernooFixture(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(_FIX) as f:
            cls.data = json.load(f)

    def test_fixture_exists_as_ternoo(self):
        self.assertTrue(os.path.isfile(_FIX), "legacy .ternoo fixture missing")

    def test_legacy_version_marker(self):
        # The IDE's load path keys off ternoo_version / tgui_version.
        self.assertTrue('ternoo_version' in self.data or 'tgui_version' in self.data)

    def test_demo_structure(self):
        # The Phase 7b-3 button-click demo: a window + button, one terminator.
        kinds = [s.get('kind') for s in self.data.get('symbols', [])]
        self.assertIn('gui_button', kinds)
        flow_kinds = [s.get('kind') for s in self.data.get('flow_symbols', [])]
        self.assertIn('flow_terminator', flow_kinds)

    def test_load_shape_matches_ide_expectations(self):
        # Mirror the fields guic_do_open reads, so a schema drift is caught here.
        for sym in self.data.get('symbols', []):
            self.assertIn('id', sym)
            self.assertIn('kind', sym)
        for sym in self.data.get('flow_symbols', []):
            self.assertIn('id', sym)
            self.assertIn('kind', sym)


if __name__ == '__main__':
    unittest.main()
