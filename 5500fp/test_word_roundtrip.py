"""test_word_roundtrip.py — dicts → words → dicts round-trip pin.

The audit of 3 July established the honest architecture sentence: the editor's
metadata dicts are the source of truth; the TernOO word stream is a
*projection* of them.  This suite makes "projection" a verified property
rather than a claim: everything the word grammar encodes must survive
dicts → ghost_to_meccano/flow_symbols_to_meccano → meccano_to_ghost intact,
and everything it does NOT encode must be visibly absent (not invented).

If someone extends the word grammar (a whitepaper §6 decision), these tests
are the checklist of what the decoder + this contract must grow to match.

Date: 2026-07-03, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

from __future__ import annotations

import unittest
import importlib.util as _ilu
import os

_here = os.path.dirname(os.path.abspath(__file__))


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_here, name + '.py'))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gm = _load('ghost_meccano')
wl = gm._wl

G = gm.FC_GRID_TO_MECCANO   # pixel → Meccano-unit divisor (10)


def _tl(sym):
    """Original dict centre-coords → expected decoded top-left, Meccano units
    (the same transform the bridges apply)."""
    return ((sym['x'] - sym['w'] // 2) // G,
            (sym['y'] - sym['h'] // 2) // G)


class TestFlowRoundTrip(unittest.TestCase):
    FLOWS = {
        'f1': {'kind': 'flow_terminator', 'x': 100, 'y': 100,
               'w': 120, 'h': 60, 'label': 'Start'},
        'f2': {'kind': 'flow_process',    'x': 300, 'y': 100,
               'w': 120, 'h': 60, 'label': 'Do the thing'},
        'f3': {'kind': 'flow_decision',   'x': 500, 'y': 100,
               'w': 120, 'h': 60, 'label': 'OK?'},
    }
    EDGES = [{'src': 'f1', 'dst': 'f2'}, {'src': 'f2', 'dst': 'f3'}]

    def _roundtrip(self):
        prog = gm.flow_symbols_to_meccano(dict(self.FLOWS), list(self.EDGES))
        return gm.meccano_to_ghost(prog.words)

    def test_node_count_and_edge_count(self):
        nodes, edges = self._roundtrip()
        self.assertEqual(len(nodes), len(self.FLOWS))
        self.assertEqual(len(edges), len(self.EDGES))

    def test_labels_survive(self):
        nodes, _ = self._roundtrip()
        self.assertEqual({n['label'] for n in nodes},
                         {s['label'] for s in self.FLOWS.values()})

    def test_shapes_follow_flow_shape_map(self):
        nodes, _ = self._roundtrip()
        by_label = {n['label']: n for n in nodes}
        for sym in self.FLOWS.values():
            self.assertEqual(by_label[sym['label']]['shape_id'],
                             wl.FLOW_SHAPE_MAP[sym['kind']],
                             f"shape for {sym['kind']}")

    def test_geometry_survives_quantized(self):
        """Positions round-trip exactly at Meccano-unit quantization
        (pixels // 10) — the documented resolution of the word geometry."""
        nodes, _ = self._roundtrip()
        by_label = {n['label']: n for n in nodes}
        for sym in self.FLOWS.values():
            n = by_label[sym['label']]
            self.assertEqual((n['x'], n['y']), _tl(sym))
            self.assertEqual((n['w'], n['h']),
                             (max(1, sym['w'] // G), max(1, sym['h'] // G)))

    def test_kind_now_carried_by_model_words(self):
        """Grammar extension v1 (OPF_MODEL): kind rides as MKIND words and
        must round-trip exactly."""
        nodes, _ = self._roundtrip()
        by_label = {n['label']: n for n in nodes}
        for sym in self.FLOWS.values():
            self.assertEqual(by_label[sym['label']].get('kind'), sym['kind'])

    def test_remaining_negative_space(self):
        """Post-v2 contract: pockets (MSCOPE), ports (MPORT), identity
        edges (MEDGE) and flags (MFLAG) ARE carried when present.  The
        honest remainder: signal bindings are NOT word-encoded by design —
        they are re-materialized from names on rehydration (the same
        auto-wiring path the IDE uses), so a faithful decoder must not
        invent signal_ids."""
        nodes, _ = self._roundtrip()
        for n in nodes:
            self.assertNotIn('signal_ids', n)


class TestGuiRoundTrip(unittest.TestCase):
    WIDGETS = {
        'w1': {'kind': 'gui_window', 'x': 200, 'y': 150, 'w': 400, 'h': 300,
               'label': 'Main Window', 'name': 'mw', 'layout_mode': 'vbox'},
        'w2': {'kind': 'gui_button', 'x': 40, 'y': 80, 'w': 120, 'h': 60,
               'label': 'OK', 'name': 'ok_btn', 'layout_mode': 'absolute'},
    }

    def _roundtrip(self):
        prog = gm.ghost_to_meccano(dict(self.WIDGETS), [])
        return gm.meccano_to_ghost(prog.words), prog

    def test_labels_and_layout_survive(self):
        (nodes, _), _prog = self._roundtrip()
        by_label = {n['label']: n for n in nodes}
        self.assertEqual(set(by_label), {'Main Window', 'OK'})
        self.assertEqual(by_label['Main Window']['layout_id'],
                         gm.LAYOUT_MODE_MAP['vbox'])
        self.assertEqual(by_label['OK']['layout_id'],
                         gm.LAYOUT_MODE_MAP['absolute'])

    def test_word_map_spans_cover_stream(self):
        """_ghost_word_map spans must tile the word list (no orphan words
        outside the trailing RENDER, no overlaps)."""
        (_nodes, _edges), prog = self._roundtrip()
        spans = sorted(prog._ghost_word_map.values())
        cursor = 0
        for s, e in spans:
            self.assertEqual(s, cursor, "gap/overlap in word map")
            cursor = e
        # anything after the last span must decode to RENDER (or nothing)
        tail = prog.words[cursor:]
        self.assertLessEqual(len(tail), 1)


class TestSharedLabelDecoder(unittest.TestCase):
    """decode_label_words is the single implementation (promoted to
    widget_lib); the renderer's private name must be the same object."""

    def test_renderer_alias_is_widget_lib_impl(self):
        import pigart_ascii_renderer as r
        self.assertIs(r._decode_label_words, r._wl.decode_label_words)

    def test_encode_decode_identity(self):
        for text in ('', 'OK', 'abc', 'Start', 'raining trits & tribbles',
                     'x' * 30):
            self.assertEqual(
                wl.decode_label_words(wl._encode_label(text)), text)


class TestModelWordsRoundTrip(unittest.TestCase):
    """Grammar extension v1: names, cells, command widgets, MMORE chunking."""

    def test_name_round_trips(self):
        widgets = {'w1': {'kind': 'gui_button', 'x': 40, 'y': 80, 'w': 120,
                          'h': 60, 'label': 'OK', 'name': 'ok_btn',
                          'layout_mode': 'absolute'}}
        nodes, _ = gm.meccano_to_ghost(gm.ghost_to_meccano(widgets, []).words)
        self.assertEqual(nodes[0].get('kind'), 'gui_button')
        self.assertEqual(nodes[0].get('name'), 'ok_btn')

    def test_cells_round_trip_all_kinds(self):
        cells = {(0, 0): {'kind': 'cell_number', 'value': -42},
                 (3, 0): {'kind': 'cell_text', 'value': 'GargantuRAM ho!'},
                 (2, 1): {'kind': 'cell_formula',
                          'value': '=SUM(A1:A9)+IF(B2>3,10,20)'}}
        m = gm.meccano_to_model(gm.cells_to_model_words(cells))
        self.assertEqual(m['cells'], cells)

    def test_long_formula_spans_mmore(self):
        """A formula far beyond one op's 8-word string ceiling must chunk
        across MMORE words and reassemble losslessly."""
        f = '=IF(SUM(A1:A20)>AVERAGE(B1:B20), MAX(C1:C9)*3-MIN(D1:D9), '             'ABS(E5)+ROUND(F6)+MOD(G7,3)+POWER(H8,2))'
        cells = {(9, 9): {'kind': 'cell_formula', 'value': f}}
        m = gm.meccano_to_model(gm.cells_to_model_words(cells))
        self.assertEqual(m['cells'][(9, 9)]['value'], f)

    def test_command_widgets_round_trip(self):
        cmds = {'c1': {'x': 30, 'y': 40, 'kind': 'cmd_math_add',
                       'params': {'a': 4, 'b': 5}},
                'c2': {'x': 90, 'y': 40, 'kind': 'cmd_text_replace',
                       'params': {'text': 'hello world', 'find': 'world',
                                  'replace': 'trits'}}}
        m = gm.meccano_to_model(gm.cmds_to_model_words(cmds))
        self.assertEqual(len(m['cmds']), 2)
        got = {c['kind']: c for c in m['cmds']}
        self.assertEqual(got['cmd_math_add']['params'], {'a': '4', 'b': '5'})
        self.assertEqual(got['cmd_text_replace']['params']['replace'], 'trits')
        self.assertEqual((got['cmd_math_add']['x'], got['cmd_math_add']['y']),
                         (30, 40))

    def test_model_words_invisible_to_renderers(self):
        """The render path filters OPF_PIGART; MODEL words must not change
        what gets drawn.  Compare ASCII renders with and without them."""
        import pigart_ascii_renderer as par

        class _P:  # minimal program shim: header (2 MAP words) + body
            def __init__(self, body): self._w = body
            def to_words(self):
                hdr = gm.flow_symbols_to_meccano(
                    {'h': {'kind': 'flow_process', 'x': 0, 'y': 0,
                           'w': 10, 'h': 10, 'label': ''}}, []).to_words()[:2]
                return hdr + self._w

        def _render_words(body):
            return par.render(_P(list(body)), width=60, height=20)

        flows = {'f1': {'kind': 'flow_terminator', 'x': 100, 'y': 100,
                        'w': 120, 'h': 60, 'label': 'Start'}}
        with_model = gm.flow_symbols_to_meccano(dict(flows), []).words
        stripped, i = [], 0
        words = list(with_model)
        while i < len(words):
            try:
                dec = wl.decode_opcode_word(words[i])
            except ValueError:
                stripped.append(words[i]); i += 1; continue
            n = 1 + dec['arity']
            if dec['family'] != wl.OPF_MODEL:
                stripped.extend(words[i:i + n])
            i += n
        self.assertEqual(_render_words(with_model),
                         _render_words(stripped))


class TestNotesRoundTrip(unittest.TestCase):
    def test_comment_round_trips(self):
        long = "# this comment is deliberately much longer than one MODEL " \
               "word can carry so it must chunk across MMORE and reassemble"
        words = wl.build_model_note("# hello") + wl.build_model_note(long)
        m = gm.meccano_to_model(words)
        self.assertEqual([n['text'] for n in m['notes']], ["# hello", long])


if __name__ == '__main__':
    unittest.main(verbosity=1)
