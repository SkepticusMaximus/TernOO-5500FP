#!/home/stevo/.venvs/p2pcp/bin/python3
"""TernID MOCK agent — serves CCC's §B facade over the real IPC (handoff 1129),
backed by the inert git-POBOX StubBackend. Lets POBOX Mail run 'live' over the
socket today; CCC drops the real TernID backend in behind the same serve() with
zero UI change.

    python3 ternid_mock_agent.py            # listens on the default socket
    TERNID_AGENT_SOCK=/path python3 ...      # or a chosen socket
Then:  TERNID_AGENT_SOCK=<same> python3 mailbox_qt.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ternid_agent_protocol import serve, default_sock
from mailbox_qt import StubBackend

if __name__ == "__main__":
    sock = os.environ.get("TERNID_AGENT_SOCK") or default_sock()
    print("TernID mock agent (git-POBOX stub) listening on", sock)
    serve(StubBackend(), sock)
