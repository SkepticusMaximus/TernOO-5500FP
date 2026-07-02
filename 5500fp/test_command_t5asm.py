"""test_command_t5asm.py — Stage 9-1B: Shell command → t5asm compilation.

Two layers:
  * pure unit tests on command_t5asm.compile_command and the compile_to_t5asm
    wiring (no emulator, no display);
  * end-to-end tests that assemble the emitted t5asm and run it on the C
    emulator, checking printed results. These skip automatically when the
    emulator binary is absent.
"""

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import command_t5asm as cmdc
import compile_to_t5asm as C
from word_stream import WordStream

_EMU = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    '..', 'NASM-TernOO-5500FP-Emulator', 'c_emulator', '5500fp')
_HAVE_EMU = os.path.exists(_EMU)


def _num(v):
    return ('num', v)


def _mk_cmd(cid, kind, **params):
    return {'id': cid, 'kind': kind, 'x': 0, 'y': 0, 'w': 160, 'h': 80,
            'label': '', 'name': f'{kind}_{cid}',
            'properties': [{'name': k, 'value': v} for k, v in params.items()]}


def _compile_stream(cmds):
    s = WordStream()
    s._cmd_meta = {c['id']: c for c in cmds}
    return C.compile_wordstream_to_t5asm(s, 'test.fc')


def _assemble_run(prog_lines):
    with tempfile.NamedTemporaryFile('w', suffix='.t5asm', delete=False) as f:
        f.write('\n'.join(prog_lines) + '\n')
        path = f.name
    try:
        r = subprocess.run([_EMU, '--run', path], capture_output=True,
                           text=True, timeout=10)
    finally:
        os.unlink(path)
    keep = [l for l in r.stdout.splitlines()
            if l and 'cycles' not in l and 'Emulator' not in l
            and 'Architecture' not in l and set(l) != {'-'}]
    return '\n'.join(keep).strip()


def _run_number(name, args, env_names=()):
    """Compile one command, print its numeric result, run, return stdout."""
    ctx = cmdc.new_ctx()
    body = cmdc.compile_command(name, args, cmdc._BASE_REG, ctx)
    prog = ['LI R19, 0'] + body + [
        f'MOV R2, R{cmdc._BASE_REG}', 'LI R1, 1', 'SYSCALL',
        'LI R1, 6', 'SYSCALL', 'HALT']
    for nm in sorted(set(ctx.env_names) | set(env_names)):
        prog += [f'{cmdc.env_slot(nm)}:', '    .word 0',
                 f'{cmdc.env_present_slot(nm)}:', '    .word 0']
    return _assemble_run(prog)


# ---------------------------------------------------------------------------
# Unit tests — compile_command emission (no emulator)
# ---------------------------------------------------------------------------

class TestCompileCommandUnit(unittest.TestCase):

    def test_math_add_emits_add(self):
        out = '\n'.join(cmdc.compile_command('cmd_math_add',
                                             [_num(3), _num(5)], 21))
        self.assertIn('LI   R21, 3', out)
        self.assertIn('LI   R22, 5', out)
        self.assertIn('ADD  R21, R21, R22', out)

    def test_divide_is_guarded(self):
        out = '\n'.join(cmdc.compile_command('cmd_math_divide',
                                             [_num(6), _num(2)], 21))
        self.assertIn('BEQZ R22', out)          # divisor-zero guard
        self.assertIn('DIV  R21, R21, R22', out)

    def test_power_unrolls_constant_exponent(self):
        out = '\n'.join(cmdc.compile_command('cmd_math_power',
                                             [_num(2), _num(3)], 21))
        self.assertEqual(out.count('MUL  R21, R21, R22'), 2)   # 2^3 → 2 muls

    def test_power_requires_constant_exponent(self):
        with self.assertRaises(cmdc.CommandCompileError):
            cmdc.compile_command('cmd_math_power',
                                 [_num(2), ('numslot', 'x')], 21)

    def test_env_set_writes_slot_and_present(self):
        out = '\n'.join(cmdc.compile_command('cmd_env_set',
                                             [('name', 'k'), _num(9)], 21))
        self.assertIn('state_env_k', out)
        self.assertIn('state_env_k_present', out)

    def test_text_upper_uses_string_syscall(self):
        out = '\n'.join(cmdc.compile_command(
            'cmd_text_upper', [('strlit', 'inbuf')], 21))
        self.assertIn('inbuf', out)             # STR_FROMBUF of the literal
        self.assertIn('LI   R1, 49', out)       # STR_UPPER

    def test_text_replace_emits_replace_syscall(self):
        out = '\n'.join(cmdc.compile_command('cmd_text_replace', [
            ('strlit', 't'), ('strlit', 'f'), ('strlit', 'w'), _num(0)], 21))
        self.assertIn('LI   R1, 52', out)       # STR_REPLACE
        self.assertIn('LI   R5, 1', out)        # ci = not case_sensitive(0)

    def test_unsupported_command_raises(self):
        # ctl_while needs the sub-flow substrate (out of scope) — still deferred.
        with self.assertRaises(cmdc.CommandCompileError):
            cmdc.compile_command('cmd_ctl_while', [('num', 1), ('num', 0)], 21)

    def test_output_kind_table(self):
        self.assertEqual(cmdc.command_output_kind('cmd_math_add'), 'number')
        self.assertEqual(cmdc.command_output_kind('cmd_text_upper'), 'text')
        self.assertEqual(cmdc.command_output_kind('cmd_list_sort'), 'list')
        self.assertEqual(cmdc.command_output_kind('cmd_env_set'), 'none')
        self.assertEqual(cmdc.command_output_kind('cmd_ctl_while'), 'unsupported')


# ---------------------------------------------------------------------------
# Unit tests — compile_to_t5asm wiring (no emulator)
# ---------------------------------------------------------------------------

class TestCommandWiring(unittest.TestCase):

    def test_shell_only_program_structure(self):
        asm = _compile_stream([_mk_cmd(7, 'cmd_math_add', a=3, b=5)])
        self.assertIn('command_7:', asm)
        self.assertIn('CALL command_7', asm)
        self.assertIn('state_cmd_7:', asm)
        self.assertNotIn('event_loop_top', asm)     # no GUI → shell path

    def test_dispatch_via_run_all_commands_wrapper(self):
        # With the RA-stack fix nested CALLs work, so dispatch goes through a
        # real run_all_commands subroutine (retiring the inline-at-depth-0
        # workaround).
        asm = _compile_stream([_mk_cmd(7, 'cmd_math_add', a=1, b=2)])
        self.assertIn('run_all_commands:', asm)
        self.assertIn('CALL run_all_commands', asm)
        self.assertIn('CALL command_7', asm)

    def test_text_command_allocates_literal_buffer(self):
        asm = _compile_stream([_mk_cmd(5, 'cmd_text_upper', text='hi')])
        self.assertIn('cmdarg_5_text:', asm)    # literal source buffer
        self.assertIn('state_cmd_5:', asm)      # result handle slot
        self.assertNotIn('cmdbuf_5:', asm)      # fixed buffer retired

    def test_env_command_allocates_slots(self):
        asm = _compile_stream([_mk_cmd(4, 'cmd_env_set', name='count', value=3)])
        self.assertIn('state_env_count:', asm)
        self.assertIn('state_env_count_present:', asm)

    def test_unsupported_command_stub(self):
        # ctl_while still needs the sub-flow substrate (out of scope).
        asm = _compile_stream([_mk_cmd(9, 'cmd_ctl_while', predicate='1',
                                       body='x')])
        self.assertIn('command_9:', asm)
        self.assertIn('no runtime yet', asm)

    def test_gui_program_runs_commands_at_startup(self):
        s = WordStream()
        s._widget_meta = {1: {'id': 1, 'kind': 'gui_window', 'x': 0, 'y': 0,
                              'w': 200, 'h': 150, 'label': 'W'}}
        s._cmd_meta = {2: _mk_cmd(2, 'cmd_math_add', a=4, b=4)}
        asm = C.compile_wordstream_to_t5asm(s, 't.fc')
        self.assertIn('event_loop_top', asm)        # GUI path
        self.assertIn('CALL command_2', asm)
        self.assertIn('command_2:', asm)

    def test_placeholder_only_is_not_a_command(self):
        s = WordStream()
        s._cmd_meta = {3: _mk_cmd(3, 'cmd_placeholder')}
        with self.assertRaises(C.CompileError):        # falls to trivial path
            C.compile_wordstream_to_t5asm(s, 't.fc')


# ---------------------------------------------------------------------------
# End-to-end tests — assemble + run on the C emulator
# ---------------------------------------------------------------------------

@unittest.skipUnless(_HAVE_EMU, 'C emulator binary not built')
class TestCommandRuntime(unittest.TestCase):

    def test_math_family(self):
        self.assertEqual(_run_number('cmd_math_add', [_num(3), _num(5)]), '8')
        self.assertEqual(_run_number('cmd_math_subtract', [_num(10), _num(4)]), '6')
        self.assertEqual(_run_number('cmd_math_multiply', [_num(6), _num(7)]), '42')
        self.assertEqual(_run_number('cmd_math_divide', [_num(20), _num(4)]), '5')
        self.assertEqual(_run_number('cmd_math_divide', [_num(5), _num(0)]), '0')
        self.assertEqual(_run_number('cmd_math_mod', [_num(17), _num(5)]), '2')
        self.assertEqual(_run_number('cmd_math_abs', [_num(-9)]), '9')
        self.assertEqual(_run_number('cmd_math_power', [_num(2), _num(5)]), '32')

    def test_control_if(self):
        self.assertEqual(_run_number('cmd_ctl_if',
                                     [_num(1), _num(7), _num(9)]), '7')
        self.assertEqual(_run_number('cmd_ctl_if',
                                     [_num(0), _num(7), _num(9)]), '9')

    def test_env_set_get(self):
        ctx = cmdc.new_ctx()
        body = cmdc.compile_command('cmd_env_set', [('name', 'c'), _num(42)],
                                    cmdc._BASE_REG, ctx)
        body += cmdc.compile_command('cmd_env_get', [('name', 'c')],
                                     cmdc._BASE_REG, ctx)
        prog = ['LI R19, 0'] + body + [
            f'MOV R2, R{cmdc._BASE_REG}', 'LI R1, 1', 'SYSCALL',
            'LI R1, 6', 'SYSCALL', 'HALT']
        for nm in sorted(ctx.env_names):
            prog += [f'{cmdc.env_slot(nm)}:', '    .word 0',
                     f'{cmdc.env_present_slot(nm)}:', '    .word 0']
        self.assertEqual(_assemble_run(prog), '42')

    def test_shell_program_end_to_end(self):
        """Full compile path → run → read the result slot."""
        asm = _compile_stream([_mk_cmd(7, 'cmd_math_add', a=30, b=12)])
        lines, printed = [], False
        for l in asm.splitlines():
            if l.strip() == 'HALT' and not printed:
                lines += ['    LI R20, state_cmd_7', '    LDW R2, R20, 0',
                          '    LI R1, 1', '    SYSCALL', '    LI R1, 6',
                          '    SYSCALL']
                printed = True
            lines.append(l)
        self.assertEqual(_assemble_run(lines), '42')

    def _print_handle_str(self, body, handle_reg=cmdc._BASE_REG):
        """Wrap a command body: print the result string (handle in handle_reg)
        by walking its NUL-terminated char run at handle+1."""
        return ['LI R19, 0'] + body + [
            f'MOV R10, R{handle_reg}', 'ADDI R10, R10, 1',
            'pl:', '    LDW R2, R10, 0', '    BEQZ R2, pd',
            '    LI R1, 3', '    SYSCALL', '    ADDI R10, R10, 1', '    JMP pl',
            'pd:', 'LI R1, 6', 'SYSCALL', 'HALT']

    def _text_databuf(self, label, s):
        return [f'{label}:'] + [f'    .word {ord(c)}' for c in s] + ['    .word 0']

    def test_text_upper_runtime(self):
        body = cmdc.compile_command('cmd_text_upper', [('strlit', 'inbuf')],
                                    cmdc._BASE_REG)
        prog = self._print_handle_str(body) + self._text_databuf('inbuf', 'hi there')
        self.assertEqual(_assemble_run(prog), 'HI THERE')

    def test_text_trim_runtime(self):
        body = cmdc.compile_command('cmd_text_trim', [('strlit', 'inbuf')],
                                    cmdc._BASE_REG)
        prog = self._print_handle_str(body) + self._text_databuf('inbuf', '  hi  ')
        self.assertEqual(_assemble_run(prog), 'hi')

    def test_text_replace_runtime(self):
        # case-insensitive by default: replace "hello" in "Hello World"
        body = cmdc.compile_command('cmd_text_replace', [
            ('strlit', 't'), ('strlit', 'f'), ('strlit', 'w'), _num(0)],
            cmdc._BASE_REG)
        prog = (self._print_handle_str(body)
                + self._text_databuf('t', 'Hello World')
                + self._text_databuf('f', 'hello')
                + self._text_databuf('w', 'goodbye'))
        self.assertEqual(_assemble_run(prog), 'goodbye World')

    def test_text_length_runtime(self):
        body = cmdc.compile_command('cmd_text_length', [('strlit', 'inbuf')],
                                    cmdc._BASE_REG)
        prog = (['LI R19, 0'] + body
                + [f'MOV R2, R{cmdc._BASE_REG}', 'LI R1, 1', 'SYSCALL',
                   'LI R1, 6', 'SYSCALL', 'HALT']
                + self._text_databuf('inbuf', 'Adelaide'))
        self.assertEqual(_assemble_run(prog), '8')


# ---------------------------------------------------------------------------
# Interactive cmd_io_* (Stage 9-1C)
# ---------------------------------------------------------------------------

class TestInteractiveCommands(unittest.TestCase):

    def test_prompt_emits_dialog_syscall(self):
        out = '\n'.join(cmdc.compile_command('cmd_io_prompt',
                                             [('strlit', 'msg')], 21))
        self.assertIn('LI   R1, 112', out)      # PIGART_DIALOG_PROMPT
        self.assertIn('_prompt_scratch', out)   # answer scratch buffer

    def test_display_and_confirm_syscalls(self):
        d = '\n'.join(cmdc.compile_command('cmd_io_display',
                                           [('strlit', 'v'), ('strlit', 't')], 21))
        self.assertIn('LI   R1, 113', d)
        c = '\n'.join(cmdc.compile_command('cmd_io_confirm',
                                           [('strlit', 'm')], 21))
        self.assertIn('LI   R1, 114', c)

    def test_io_shell_program_opens_window(self):
        asm = _compile_stream([_mk_cmd(5, 'cmd_io_confirm', message='ok?')])
        self.assertIn('shell_win_title:', asm)
        self.assertIn('LI   R1, 100', asm)      # PIGART_OPEN_WINDOW
        self.assertIn('LI   R1, 111', asm)      # PIGART_CLOSE_WINDOW
        self.assertIn('LI   R1, 114', asm)      # confirm dialog

    def test_choice_emits_list_dialog_syscall(self):
        # cmd_io_choice is now live: DIALOG_CHOICE_LIST over a list handle.
        asm = _compile_stream([_mk_cmd(6, 'cmd_io_choice',
                                       options='red,green', prompt='pick')])
        self.assertIn('command_6:', asm)
        self.assertIn('LI   R1, 117', asm)      # PIGART_DIALOG_CHOICE_LIST
        self.assertIn('shell_win_title', asm)   # opens a window (io command)

    @unittest.skipUnless(_HAVE_EMU, 'C emulator binary not built')
    def test_confirm_runtime_ascii_default(self):
        """cmd_io_confirm on the ASCII backend returns 0 (no interactive UI)."""
        asm = _compile_stream([_mk_cmd(5, 'cmd_io_confirm', message='go?')])
        lines, printed = [], False
        for l in asm.splitlines():
            if l.strip() == 'HALT' and not printed:
                lines += ['    LI R20, state_cmd_5', '    LDW R2, R20, 0',
                          '    LI R1, 1', '    SYSCALL', '    LI R1, 6',
                          '    SYSCALL']
                printed = True
            lines.append(l)
        with tempfile.NamedTemporaryFile('w', suffix='.t5asm', delete=False) as f:
            f.write('\n'.join(lines) + '\n')
            path = f.name
        try:
            r = subprocess.run([_EMU, '--display', 'ascii', '--run', path],
                               capture_output=True, text=True, timeout=10)
        finally:
            os.unlink(path)
        digits = [x for x in r.stdout.splitlines() if x.strip().isdigit()]
        self.assertEqual(digits[-1:], ['0'])


# ---------------------------------------------------------------------------
# Stage 9-2 — typed pipe edges + pipeline compilation
# ---------------------------------------------------------------------------

import flowcode_commands as _fcmd


def _compile_piped(cmds, edges):
    s = WordStream()
    s._cmd_meta = {c['id']: c for c in cmds}
    s._cmd_edges = edges
    return s, C.compile_wordstream_to_t5asm(s, 'p.fc')


def _run_slot(asm, slot):
    lines, printed = [], False
    for l in asm.splitlines():
        if l.strip() == 'HALT' and not printed:
            lines += [f'    LI R20, {slot}', '    LDW R2, R20, 0',
                      '    LI R1, 1', '    SYSCALL', '    LI R1, 6', '    SYSCALL']
            printed = True
        lines.append(l)
    return _assemble_run(lines)


class TestPipeTypeHelper(unittest.TestCase):

    def test_numeric_pipe_compatible(self):
        self.assertTrue(_fcmd.pipe_compatible('cmd_math_add', 'cmd_math_multiply', 'a'))

    def test_text_pipe_compatible(self):
        self.assertTrue(_fcmd.pipe_compatible('cmd_text_upper', 'cmd_text_length', 'text'))

    def test_text_into_number_incompatible(self):
        self.assertFalse(_fcmd.pipe_compatible('cmd_text_upper', 'cmd_math_add', 'a'))

    def test_number_into_text_incompatible(self):
        self.assertFalse(_fcmd.pipe_compatible('cmd_math_add', 'cmd_text_upper', 'text'))


class TestPipelineCompile(unittest.TestCase):

    def test_topological_dispatch_order(self):
        # declared dst-first; must still dispatch upstream (src) first
        _s, asm = _compile_piped(
            [_mk_cmd(2, 'cmd_math_multiply', a=0, b=10),
             _mk_cmd(1, 'cmd_math_add', a=3, b=5)],
            [{'src': 1, 'dst': 2, 'dst_param': 'a'}])
        self.assertLess(asm.index('CALL command_1'), asm.index('CALL command_2'))

    def test_pipe_arg_reads_upstream_slot(self):
        _s, asm = _compile_piped(
            [_mk_cmd(1, 'cmd_math_add', a=3, b=5),
             _mk_cmd(2, 'cmd_math_multiply', a=0, b=10)],
            [{'src': 1, 'dst': 2, 'dst_param': 'a'}])
        self.assertIn('command_2:', asm)
        self.assertIn('state_cmd_1', asm)      # #2 loads #1's output slot

    def test_type_mismatch_is_hard_error(self):
        with self.assertRaises(C.CompileError):
            _compile_piped(
                [_mk_cmd(1, 'cmd_text_upper', text='hi'),
                 _mk_cmd(2, 'cmd_math_add', a=0, b=1)],
                [{'src': 1, 'dst': 2, 'dst_param': 'a'}])

    def test_pipe_cycle_is_error(self):
        with self.assertRaises(C.CompileError):
            _compile_piped(
                [_mk_cmd(1, 'cmd_math_add', a=0, b=1),
                 _mk_cmd(2, 'cmd_math_add', a=0, b=1)],
                [{'src': 1, 'dst': 2, 'dst_param': 'a'},
                 {'src': 2, 'dst': 1, 'dst_param': 'a'}])

    @unittest.skipUnless(_HAVE_EMU, 'C emulator binary not built')
    def test_numeric_pipeline_runtime(self):
        _s, asm = _compile_piped(
            [_mk_cmd(1, 'cmd_math_add', a=3, b=5),          # = 8
             _mk_cmd(2, 'cmd_math_multiply', a=0, b=10)],   # 8 * 10 = 80
            [{'src': 1, 'dst': 2, 'dst_param': 'a'}])
        self.assertEqual(_run_slot(asm, 'state_cmd_2'), '80')

    @unittest.skipUnless(_HAVE_EMU, 'C emulator binary not built')
    def test_text_pipeline_runtime(self):
        _s, asm = _compile_piped(
            [_mk_cmd(1, 'cmd_text_upper', text='hi'),       # "HI"
             _mk_cmd(2, 'cmd_text_length', text='')],       # len("HI") = 2
            [{'src': 1, 'dst': 2, 'dst_param': 'text'}])
        self.assertEqual(_run_slot(asm, 'state_cmd_2'), '2')


# ---------------------------------------------------------------------------
# Nested CALLs — dynamic Sheet-cell recompute (R80 return-address fix)
# ---------------------------------------------------------------------------

class TestDynamicCellRecompute(unittest.TestCase):
    """recompute_all_cells → recompute_cell_<id> is a two-level CALL chain that
    used to hang under the single-R80 hazard. With the return-address stack it
    both emits and executes correctly."""

    def _dynamic_stream(self, checked):
        s = WordStream()
        s._widget_meta = {
            1: {'id': 1, 'kind': 'gui_window', 'x': 0, 'y': 0,
                'w': 300, 'h': 200, 'label': 'W'},
            2: {'id': 2, 'kind': 'gui_toggle', 'x': 10, 'y': 10, 'w': 80,
                'h': 30, 'label': 'T', 'name': 't',
                'properties': [{'name': 'checked', 'value': checked}]},
        }
        s._cell_meta = {(0, 0): {'id': 5, 'kind': 'cell_formula', 'row': 0,
                                 'col': 0, 'name': 'c1',
                                 'value': '=WIDGET("t").checked * 7',
                                 'properties': []}}
        return s

    def test_recompute_nesting_emitted(self):
        asm = C.compile_wordstream_to_t5asm(self._dynamic_stream(1), 'dyn.fc')
        self.assertIn('CALL recompute_all_cells', asm)
        self.assertIn('recompute_all_cells:', asm)
        self.assertIn('CALL recompute_cell_5', asm)   # the 2nd nesting level

    @unittest.skipUnless(_HAVE_EMU, 'C emulator binary not built')
    def test_recompute_runs(self):
        # Drive recompute_all_cells once in isolation (the GUI event loop never
        # exits headlessly) and read the recomputed cell slot.
        asm = C.compile_wordstream_to_t5asm(self._dynamic_stream(1), 'dyn.fc')
        tail = asm[asm.index('; ---- Dynamic cell recompute'):]
        for chk, exp in ((1, '7'), (0, '0')):
            driver = [
                'main:',
                '    LI R20, state_checked_2',
                f'    LI R15, {chk}',
                '    STW R15, R20, 0',
                '    CALL recompute_all_cells',
                '    LI R20, state_cell_5',
                '    LDW R2, R20, 0',
                '    LI R1, 1', '    SYSCALL', '    LI R1, 6', '    SYSCALL',
                '    HALT', '']
            out = _assemble_run(('\n'.join(driver) + '\n' + tail).split('\n'))
            self.assertEqual(out, exp)


# ---------------------------------------------------------------------------
# List commands + pipelines (Piece 5) — end-to-end on the emulator
# ---------------------------------------------------------------------------

@unittest.skipUnless(_HAVE_EMU, 'C emulator binary not built')
class TestListCommandsRuntime(unittest.TestCase):

    def _run_slot(self, cmds, edges, slot):
        s = WordStream()
        s._cmd_meta = {c['id']: c for c in cmds}
        s._cmd_edges = edges
        asm = C.compile_wordstream_to_t5asm(s, 't.fc')
        lines, printed = [], False
        for l in asm.splitlines():
            if l.strip() == 'HALT' and not printed:
                lines += [f'    LI R20, {slot}', '    LDW R2, R20, 0',
                          '    LI R1, 1', '    SYSCALL', '    LI R1, 6', '    SYSCALL']
                printed = True
            lines.append(l)
        return _assemble_run(lines)

    def test_split_then_count(self):
        # text_split("a,b,c", ",") -> list_count = 3
        cmds = [_mk_cmd(1, 'cmd_text_split', text='a,b,c', delimiter=','),
                _mk_cmd(2, 'cmd_list_count', list='')]
        edges = [{'src': 1, 'dst': 2, 'dst_param': 'list'}]
        self.assertEqual(self._run_slot(cmds, edges, 'state_cmd_2'), '3')

    def test_sort_reverse_first(self):
        # split "3,1,2" -> sort asc [1,2,3] -> reverse [3,2,1] -> first "3"
        cmds = [_mk_cmd(1, 'cmd_text_split', text='3,1,2', delimiter=','),
                _mk_cmd(2, 'cmd_list_sort', list='', ascending=True),
                _mk_cmd(3, 'cmd_list_reverse', list=''),
                _mk_cmd(4, 'cmd_list_first', list='')]
        edges = [{'src': 1, 'dst': 2, 'dst_param': 'list'},
                 {'src': 2, 'dst': 3, 'dst_param': 'list'},
                 {'src': 3, 'dst': 4, 'dst_param': 'list'}]
        # list_first returns a string handle; print its first char via STR_CHAR
        s = WordStream()
        s._cmd_meta = {c['id']: c for c in cmds}
        s._cmd_edges = edges
        asm = C.compile_wordstream_to_t5asm(s, 't.fc')
        lines, printed = [], False
        for l in asm.splitlines():
            if l.strip() == 'HALT' and not printed:
                lines += ['    LI R20, state_cmd_4', '    LDW R2, R20, 0',
                          '    LI R3, 0', '    LI R1, 43', '    SYSCALL',   # STR_CHAR
                          '    MOV R2, R1', '    LI R1, 1', '    SYSCALL',
                          '    LI R1, 6', '    SYSCALL']
                printed = True
            lines.append(l)
        self.assertEqual(_assemble_run(lines), str(ord('3')))   # '3'

    def test_unique_count(self):
        cmds = [_mk_cmd(1, 'cmd_text_split', text='a,a,b', delimiter=','),
                _mk_cmd(2, 'cmd_list_unique', list=''),
                _mk_cmd(3, 'cmd_list_count', list='')]
        edges = [{'src': 1, 'dst': 2, 'dst_param': 'list'},
                 {'src': 2, 'dst': 3, 'dst_param': 'list'}]
        self.assertEqual(self._run_slot(cmds, edges, 'state_cmd_3'), '2')

    def test_join_length(self):
        # split "a,b,c" -> join by "-" = "a-b-c" -> length 5
        cmds = [_mk_cmd(1, 'cmd_text_split', text='a,b,c', delimiter=','),
                _mk_cmd(2, 'cmd_text_join', list='', separator='-'),
                _mk_cmd(3, 'cmd_text_length', text='')]
        edges = [{'src': 1, 'dst': 2, 'dst_param': 'list'},
                 {'src': 2, 'dst': 3, 'dst_param': 'text'}]
        self.assertEqual(self._run_slot(cmds, edges, 'state_cmd_3'), '5')

    def test_repeat_count(self):
        # ctl_repeat(5, "x") -> list of 5 -> list_count = 5
        cmds = [_mk_cmd(1, 'cmd_ctl_repeat', count=5, value='x'),
                _mk_cmd(2, 'cmd_list_count', list='')]
        edges = [{'src': 1, 'dst': 2, 'dst_param': 'list'}]
        self.assertEqual(self._run_slot(cmds, edges, 'state_cmd_2'), '5')

    def test_format_length(self):
        # format("Count: {0}", ["3"]) -> "Count: 3" length 8
        cmds = [_mk_cmd(1, 'cmd_text_format', template='Count: {0}', args='3'),
                _mk_cmd(2, 'cmd_text_length', text='')]
        edges = [{'src': 1, 'dst': 2, 'dst_param': 'text'}]
        self.assertEqual(self._run_slot(cmds, edges, 'state_cmd_2'), '8')

    def test_ctl_while_still_deferred(self):
        # ctl_while needs sub-flows (out of scope) — stubbed, not executed.
        s = WordStream()
        s._cmd_meta = {1: _mk_cmd(1, 'cmd_ctl_while', predicate='1', body='x')}
        asm = C.compile_wordstream_to_t5asm(s, 't.fc')
        self.assertIn('no runtime yet', asm)


class TestAllRegistryCommandsCompile(unittest.TestCase):
    """Every registry command compiles to either a real runtime block or a
    documented stub — no command crashes the compiler. After the substrate
    bundle only ctl_while remains stubbed (needs the sub-flow substrate)."""

    def _single(self, kind):
        import flowcode_commands as reg
        spec = reg.commands()[kind]
        # give every param a plausible literal so the plan resolves
        props = []
        for p in spec.get('params', []):
            t = p.get('type')
            v = 2 if t == 'number' else (True if t == 'bool' else 'a,b')
            props.append({'name': p['name'], 'value': v})
        return {'id': 1, 'kind': kind, 'x': 0, 'y': 0, 'w': 1, 'h': 1,
                'label': '', 'name': f'{kind}_1', 'properties': props}

    def test_every_command_compiles(self):
        import flowcode_commands as reg
        live, stubbed = [], []
        for kind in reg.command_names():
            s = WordStream()
            s._cmd_meta = {1: self._single(kind)}
            asm = C.compile_wordstream_to_t5asm(s, 't.fc')
            self.assertIn('command_1:', asm)
            (stubbed if 'no runtime yet' in asm else live).append(kind)
        # 28 registry commands; only ctl_while stays stubbed (sub-flows)
        self.assertEqual(stubbed, ['cmd_ctl_while'],
                         f'unexpected stubs: {stubbed}')
        self.assertEqual(len(live), len(reg.command_names()) - 1)


if __name__ == '__main__':
    unittest.main()
