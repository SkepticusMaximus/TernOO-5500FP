#!/usr/bin/env python3
"""run_p2pcp_tests.py — run every P2PCP test suite in one command.

    cd 5500fp && python3 run_p2pcp_tests.py [-v]

Consolidates the fourteen-module unittest invocation into one entry point with a
single pass/fail summary — handy for a pre-commit check and for the cross-box
bring-up. Exit code is 0 iff everything passed.

Date: 2026-07-10, Adelaide
Authors: Stevo (SkepticusMaximus) + Claude (Anthropic)
"""

import importlib.util as _ilu
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))

SUITES = [
    "test_p2pcp_ledger", "test_p2pcp_socket", "test_p2pcp_daemon",
    "test_p2pcp_wire", "test_p2pcp_consensus", "test_p2pcp_gossip",
    "test_p2pcp_bonsai", "test_p2pcp_ghost", "test_p2pcp_node",
    "test_p2pcp_service", "test_p2pcp_emulator", "test_p2pcp_demo",
    "test_sponge_mod3_attack", "test_network_boundary",
]


def _load(name):
    spec = _ilu.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def build_suite():
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for name in SUITES:
        suite.addTests(loader.loadTestsFromModule(_load(name)))
    return suite


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    verbosity = 2 if ("-v" in argv or "--verbose" in argv) else 1
    result = unittest.TextTestRunner(verbosity=verbosity).run(build_suite())
    print(f"\nP2PCP suite: {result.testsRun} tests, "
          f"{len(result.failures)} failures, {len(result.errors)} errors — "
          f"{'PASS' if result.wasSuccessful() else 'FAIL'}")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
