#!/bin/bash
# Open POBOX Mail on the LIVE TernID agent (real sealed mail), not the inert stub.
# Ensures the agent is running, points the face at its socket, launches the Qt face.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
AGENT_BIN="/home/stevo/dev/SkepticusMaximus/TernID/target/debug/ternid-agent"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
SOCK="$XDG_RUNTIME_DIR/ternid-agent.sock"

# start the crew engine if it isn't already listening
if [ ! -S "$SOCK" ]; then
  echo "starting ternid-agent…"
  setsid "$AGENT_BIN" --root "$HOME/.ternid/data" </dev/null >"$HOME/.ternid/agent.log" 2>&1 &
  for _ in $(seq 1 20); do [ -S "$SOCK" ] && break; sleep 0.2; done
fi

export TERNID_AGENT_SOCK="$SOCK"
echo "POBOX Mail → live agent at $SOCK"
exec python3 "$HERE/mailbox_qt.py"
