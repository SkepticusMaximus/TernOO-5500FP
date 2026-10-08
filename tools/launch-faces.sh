#!/usr/bin/env bash
# launch-faces.sh — open the TernOO localhost faces in one click.
#
#   • TernOO FlowCode webface   → http://127.0.0.1:8610/   (started here if not already running)
#   • TernID blind-custody demo → the Pi over the USB link  (opened only if reachable)
#
# TERNID_URL is the Pi's CURRENT USB-gadget address. When the Pi moves (e.g. onto
# Lenny at home), edit TERNID_URL below to the Pi's new address.
set -u
REPO="$HOME/dev/SkepticusMaximus/TernOO-5500FP"
WEBFACE_URL="http://127.0.0.1:8610/"
TERNID_URL="http://10.55.0.1:8620/"

open_url() { command -v xdg-open >/dev/null 2>&1 && (xdg-open "$1" >/dev/null 2>&1 &) ; }

echo "— TernOO faces —"

# 1) TernOO webface (localhost) — start it if it isn't already up
if curl -s -o /dev/null --max-time 2 "$WEBFACE_URL" 2>/dev/null; then
  echo "✓ webface already running on :8610"
else
  echo "… starting webface (python3 ternoo_web.py)"
  ( cd "$REPO/5500fp" && setsid nohup python3 ternoo_web.py > "$HOME/.ternoo-webface.log" 2>&1 < /dev/null & )
  if curl -s -o /dev/null --retry 20 --retry-delay 1 --retry-connrefused --max-time 25 "$WEBFACE_URL" 2>/dev/null; then
    echo "✓ webface up on :8610"
  else
    echo "✗ webface didn't start — see ~/.ternoo-webface.log"
  fi
fi
open_url "$WEBFACE_URL"; echo "  → $WEBFACE_URL"

# 2) TernID demo (on the Pi) — open it only if the cable's connected
if curl -s -o /dev/null --max-time 2 "${TERNID_URL}health" 2>/dev/null; then
  open_url "$TERNID_URL"; echo "✓ TernID demo online → $TERNID_URL"
else
  echo "· TernID demo: Pi not reachable (plug it into USB) — skipped"
fi
echo "done."
