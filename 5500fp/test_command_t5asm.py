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

    def test_text_upper_needs_output_buffer(self):
        with self.assertRaises(cmdc.CommandCompileError):
            cmdc.compile_command('cmd_text_upper', [('text', 'inbuf')], 21)
        ctx = cmdc.new_ctx(out_text='outbuf')
        out = '\n'.join(cmdc.compile_command('cmd_text_upper',
                                             [('text', 'inbuf')], 21, ctx))
        self.assertIn('outbuf', out)

    def test_unsupported_command_raises(self):
        with self.assertRaises(cmdc.CommandCompileError):
            cmdc.compile_command('cmd_list_sort', [('text', 'l')], 21)

    def test_output_kind_table(self):
        self.assertEqual(cmdc.command_output_kind('cmd_math_add'), 'number')
        self.assertEqual(cmdc.command_output_kind('cmd_text_upper'), 'text')
        self.assertEqual(cmdc.command_output_kind('cmd_env_set'), 'none')
        self.assertEqual(cmdc.command_output_kind('cmd_list_sort'), 'unsupported')


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

    def test_text_command_allocates_buffer(self):
        asm = _compile_stream([_mk_cmd(5, 'cmd_text_upper', text='hi')])
        self.assertIn('cmdbuf_5:', asm)
        self.assertIn('cmdarg_5_text:', asm)

    def test_env_command_allocates_slots(self):
        asm = _compile_stream([_mk_cmd(4, 'cmd_env_set', name='count', value=3)])
        self.assertIn('state_env_count:', asm)
        self.assertIn('state_env_count_present:', asm)

    def test_unsupported_command_stub(self):
        asm = _compile_stream([_mk_cmd(9, 'cmd_text_split', text='a,b',
                                       delimiter=',')])
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

    def test_text_upper_runtime(self):
        ctx = cmdc.new_ctx(out_text='outbuf')
        body = cmdc.compile_command('cmd_text_upper', [('text', 'inbuf')],
                                    cmdc._BASE_REG, ctx)
        prog = ['LI R19, 0'] + body + [
            'LI R10, outbuf', 'pl:', '    LDW R2, R10, 0', '    BEQZ R2, pd',
            '    LI R1, 3', '    SYSCALL', '    ADDI R10, R10, 1', '    JMP pl',
            'pd:', 'LI R1, 6', 'SYSCALL', 'HALT',
            'inbuf:'] + [f'    .word {ord(c)}' for c in 'hi there'] + [
            '    .word 0', 'outbuf:'] + ['    .word 0'] * 64
        self.assertEqual(_assemble_run(prog), 'HI THERE')


# ---------------------------------------------------------------------------
# Interactive cmd_io_* (Stage 9-1C)
# ---------------------------------------------------------------------------

class TestInteractiveCommands(unittest.TestCase):

    def test_prompt_emits_dialog_syscall(self):
        ctx = cmdc.new_ctx(out_text='outbuf')
        out = '\n'.join(cmdc.compile_command('cmd_io_prompt',
                                             [('text', 'msg')], 21, ctx))
        self.assertIn('LI   R1, 112', out)      # PIGART_DIALOG_PROMPT
        self.assertIn('outbuf', out)

    def test_display_and_confirm_syscalls(self):
        d = '\n'.join(cmdc.compile_command('cmd_io_display',
                                           [('text', 'v'), ('text', 't')], 21))
        self.assertIn('LI   R1, 113', d)
        c = '\n'.join(cmdc.compile_command('cmd_io_confirm',
                                           [('text', 'm')], 21))
        self.assertIn('LI   R1, 114', c)

    def test_io_shell_program_opens_window(self):
        asm = _compile_stream([_mk_cmd(5, 'cmd_io_confirm', message='ok?')])
        self.assertIn('shell_win_title:', asm)
        self.assertIn('LI   R1, 100', asm)      # PIGART_OPEN_WINDOW
        self.assertIn('LI   R1, 111', asm)      # PIGART_CLOSE_WINDOW
        self.assertIn('LI   R1, 114', asm)      # confirm dialog

    def test_choice_is_unsupported_stub(self):
        # cmd_io_choice needs the list substrate → stub block, not execution.
        asm = _compile_stream([_mk_cmd(6, 'cmd_io_choice', prompt='pick')])
        self.assertIn('command_6:', asm)
        self.assertIn('no runtime yet', asm)

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


if __name__ == '__main__':
    unittest.main()
