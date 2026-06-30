#!/usr/bin/env python3
"""Stage 9-0 — Shell tab scaffolding tests.

Headless coverage for the Shell tab foundation (no tkinter):

  - cmd_placeholder is registered in the property registry and inherits the
    Phase 7c-1 `name` property as its topmost field.
  - WordStream._cmd_meta participates in the single global name namespace
    (cmd widgets cannot collide with gui_* / flow_* names and vice-versa).
  - default_name follows the <kind>_<id> convention for command widgets.
  - ensure_unique_names backfills legacy command widgets and disambiguates.
  - A dict-level model of save / load preserves command widgets and names.
  - A source-level smoke check that the Shell tab is wired into flowcode.py
    (tab created between GUI and GristMill, sidebar + clear + persistence).

Run:
    cd 5500fp && python3 -m unittest test_shell_tab
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from word_stream import WordStream

import importlib.util as _ilu
_fp_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        'flowcode_properties.py')
_fp_spec = _ilu.spec_from_file_location('flowcode_properties', _fp_path)
_fp      = _ilu.module_from_spec(_fp_spec)
_fp_spec.loader.exec_module(_fp)


def _c(cid, kind='cmd_placeholder', **kw):
    """Build a minimal command-widget dict for testing."""
    d = {'id': cid, 'kind': kind}
    d.update(kw)
    return d


def _stream_with(widgets=None, flows=None, cmds=None):
    """WordStream whose _widget_meta / _flow_meta / _cmd_meta alias the given
    dicts (mirrors the editor's aliasing of the live fc_state dicts)."""
    s = WordStream()
    s._widget_meta = {w['id']: w for w in (widgets or [])}
    s._flow_meta   = {f['id']: f for f in (flows or [])}
    s._cmd_meta    = {c['id']: c for c in (cmds or [])}
    return s


class TestCmdInRegistry(unittest.TestCase):

    def test_cmd_placeholder_registered(self):
        self.assertIn('cmd_placeholder', _fp.WIDGET_PROPERTIES)

    def test_cmd_inherits_name_property(self):
        names = [p['name'] for p in _fp.properties_for('cmd_placeholder')]
        self.assertIn('name', names)
        self.assertIn('label', names)

    def test_name_is_topmost_for_cmd(self):
        self.assertEqual(_fp.properties_for('cmd_placeholder')[0]['name'], 'name')

    def test_no_kind_specific_props_yet(self):
        # Scaffolding only — real command vocabulary arrives in Stage 9-1.
        self.assertEqual(_fp.WIDGET_PROPERTIES['cmd_placeholder'], [])


class TestCmdDefaultName(unittest.TestCase):

    def test_default_name_convention(self):
        self.assertEqual(
            WordStream.default_name({'kind': 'cmd_placeholder', 'id': 3}),
            'cmd_placeholder_3')

    def test_default_distinct_across_namespaces(self):
        # Same id, different families → distinct defaults (kind prefix differs).
        self.assertNotEqual(
            WordStream.default_name({'kind': 'cmd_placeholder', 'id': 0}),
            WordStream.default_name({'kind': 'gui_button', 'id': 0}))


class TestCmdNameNamespace(unittest.TestCase):

    def test_cmd_name_in_use(self):
        s = _stream_with(cmds=[_c(0, name='upper')])
        self.assertTrue(s.name_in_use('upper'))
        self.assertFalse(s.name_in_use('nope'))

    def test_cmd_collides_with_widget(self):
        # A command name must not collide with a gui widget name (one namespace).
        s = _stream_with(widgets=[{'id': 0, 'kind': 'gui_button', 'name': 'go'}],
                         cmds=[_c(0, name='go')])
        self.assertTrue(s.name_in_use('go'))

    def test_cmd_collides_with_flow(self):
        s = _stream_with(flows=[{'id': 0, 'kind': 'flow_terminator', 'name': 'run'}])
        # 'run' is claimed by a flow symbol → unavailable to a new command.
        self.assertTrue(s.name_in_use('run'))

    def test_exclude_allows_self_edit(self):
        cmd = _c(0, name='keep')
        s = _stream_with(cmds=[cmd])
        # Re-saving the same name on the same dict must not self-collide.
        self.assertFalse(s.name_in_use('keep', exclude=cmd))

    def test_empty_cmd_name_never_collides(self):
        s = _stream_with(cmds=[_c(0, name=''), _c(1, name='')])
        self.assertFalse(s.name_in_use(''))


class TestCmdEnsureUniqueNames(unittest.TestCase):

    def test_backfill_missing_cmd_name(self):
        cmd = _c(7)  # no 'name' key — legacy
        s = _stream_with(cmds=[cmd])
        changed = s.ensure_unique_names()
        self.assertEqual(cmd['name'], 'cmd_placeholder_7')
        self.assertGreaterEqual(changed, 1)

    def test_empty_cmd_name_preserved(self):
        cmd = _c(0, name='')
        s = _stream_with(cmds=[cmd])
        s.ensure_unique_names()
        self.assertEqual(cmd['name'], '')

    def test_cross_namespace_dedup(self):
        # A command sharing a name with an existing widget gets disambiguated.
        w = {'id': 0, 'kind': 'gui_button', 'name': 'dup'}
        cmd = _c(0, name='dup')
        s = _stream_with(widgets=[w], cmds=[cmd])
        s.ensure_unique_names()
        self.assertEqual(w['name'], 'dup')          # widgets iterate first → keeps it
        self.assertNotEqual(cmd['name'], 'dup')     # command gets a suffix
        self.assertTrue(cmd['name'].startswith('dup_'))

    def test_idempotent(self):
        cmd = _c(0, name='solo')
        s = _stream_with(cmds=[cmd])
        s.ensure_unique_names()
        self.assertEqual(s.ensure_unique_names(), 0)


class TestCmdSaveLoadRoundTrip(unittest.TestCase):
    """Dict-level model of _save_to_path / guic_do_open for cmd widgets."""

    def _save(self, cmd_widgets):
        return [dict(c) for c in cmd_widgets.values()]

    def _load(self, cmd_symbols):
        out = {}
        for cmd in cmd_symbols:
            cid = cmd['id']
            d = {'id': cid, 'kind': cmd.get('kind', 'cmd_placeholder'),
                 'x': cmd.get('x', 0), 'y': cmd.get('y', 0),
                 'w': cmd.get('w', 160), 'h': cmd.get('h', 80),
                 'label': cmd.get('label', ''),
                 'properties': list(cmd.get('properties', []))}
            if 'name' in cmd:
                d['name'] = cmd['name']
            out[cid] = d
        return out

    def test_names_survive_round_trip(self):
        src = {0: _c(0, x=40, y=40, w=160, h=80, label='upper', name='to_upper'),
               1: _c(1, x=240, y=40, w=160, h=80, label='trim', name='strip_ws')}
        loaded = self._load(self._save(src))
        s = _stream_with(cmds=list(loaded.values()))
        s.ensure_unique_names()
        self.assertEqual(loaded[0]['name'], 'to_upper')
        self.assertEqual(loaded[1]['name'], 'strip_ws')

    def test_legacy_cmd_gets_default_on_load(self):
        # A saved cmd lacking a name (legacy) is backfilled on load.
        loaded = self._load([{'id': 5, 'kind': 'cmd_placeholder',
                              'x': 0, 'y': 0, 'label': 'x'}])
        s = _stream_with(cmds=list(loaded.values()))
        s.ensure_unique_names()
        self.assertEqual(loaded[5]['name'], 'cmd_placeholder_5')


class TestShellTabWiring(unittest.TestCase):
    """Source-level smoke checks that the Shell tab is wired into the IDE.

    The IDE build needs a display, so these assert on flowcode.py source rather
    than instantiating tkinter — enough to catch the wiring being removed."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'FlowCode', 'flowcode.py')
        with open(path) as f:
            cls.src = f.read()

    def test_shell_tab_added(self):
        # Bundle 24: Shell tab (three-pane builder); internal symbol stays sh_tab.
        self.assertIn("notebook.add(sh_tab, text='  Shell  ')", self.src)

    def test_tab_order_flow_gui_shell_connectors_lingo(self):
        # Bundle 24 order: Flow | GUI | Shell | Connectors | Lingo
        i_gui  = self.src.index("notebook.add(ghost_tab")
        i_sh   = self.src.index("notebook.add(sh_tab")
        i_conn = self.src.index("notebook.add(conn_tab")
        i_gm   = self.src.index("notebook.add(gm_tab")
        self.assertTrue(i_gui < i_sh < i_conn < i_gm,
                        "order must be GUI < Shell < Connectors < Lingo")

    def test_connectors_tab_added(self):
        self.assertIn("notebook.add(conn_tab, text='  Connectors  ')", self.src)

    def test_lingo_label_on_gm_tab(self):
        # The old GristMill/GMill tab is now labelled "Lingo".
        self.assertIn("notebook.add(gm_tab, text='  Lingo  ')", self.src)

    def test_shell_sidebar_builder(self):
        self.assertIn('def _build_shell_tools', self.src)
        self.assertIn('_build_shell_tools()', self.src)

    def test_shell_clear_is_tab_aware(self):
        self.assertIn('def _clear_shell', self.src)

    def test_shell_persisted_in_save(self):
        self.assertIn("'cmd_symbols':", self.src)

    def test_cmd_meta_aliased(self):
        self.assertIn("_cmd_meta", self.src)


class TestLingoInterface(unittest.TestCase):
    """Bundle 23 Piece 3 — source-level smoke checks for the Lingo three-pane
    command-builder. Behaviour is verified live offscreen; these guard the
    wiring against accidental removal."""

    @classmethod
    def setUpClass(cls):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '..', 'FlowCode', 'flowcode.py')
        with open(path) as f:
            cls.src = f.read()

    def test_command_registry_driven(self):
        # Stage 9-1A: the Shell command list is built from flowcode_commands
        # (real registry), not hard-coded stubs.
        self.assertIn('LINGO_COMMANDS', self.src)
        self.assertIn('_lingo_build_commands', self.src)
        self.assertIn('flowcode_commands', self.src)
        self.assertIn('run_command', self.src)

    def test_three_panes(self):
        self.assertIn('_lg_panes', self.src)          # PanedWindow
        self.assertIn('_lg_listbox', self.src)        # left: command list
        self.assertIn('_lg_form', self.src)           # center: param form
        self.assertIn('_lg_out', self.src)            # right: output preview

    def test_builder_actions(self):
        for fn in ('_lingo_generate', '_lingo_update_preview', '_lingo_add_pipeline',
                   '_lingo_copy', '_lingo_activate'):
            self.assertIn(fn, self.src)

    def test_search_filter(self):
        self.assertIn('_lingo_refresh_list', self.src)
        self.assertIn('_lg_search_var', self.src)

    def test_pipeline_tab(self):
        self.assertIn('_lg_pipe', self.src)
        self.assertIn("'pipeline'", self.src)

    def test_copy_uses_clipboard(self):
        self.assertIn('clipboard_clear', self.src)
        self.assertIn('clipboard_append', self.src)

    def test_canvas_promoted_to_connectors_tab(self):
        # Bundle 24: the Stage 9-0 cmd_* canvas now has its own Connectors tab,
        # parented to conn_tab with its own sidebar builder.
        self.assertIn('_sh_cv_frame = tk.Frame(conn_tab', self.src)
        self.assertIn('_build_connectors_tools', self.src)


if __name__ == '__main__':
    unittest.main()
