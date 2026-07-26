#!/bin/sh
# POBOX MacroBridge installer — registers the native-messaging host with Firefox.
# The extension itself is loaded separately (see README: about:debugging).
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
HOST_PY="$HERE/native-host/pobox_macro_host.py"
HOST_JSON="$HERE/native-host/pobox_macro_host.json"
DEST_DIR="$HOME/.mozilla/native-messaging-hosts"
DEST="$DEST_DIR/pobox_macro_host.json"

chmod +x "$HOST_PY"
mkdir -p "$DEST_DIR"
# The host manifest's "path" is already absolute for this machine; symlink it in.
ln -sf "$HOST_JSON" "$DEST"

echo "installed native host manifest:"
echo "  $DEST -> $HOST_JSON"
echo "  host script: $HOST_PY (chmod +x)"
echo
echo "Next: load the extension in Firefox —"
echo "  1. about:debugging#/runtime/this-firefox"
echo "  2. Load Temporary Add-on… -> pick $HERE/manifest.json"
echo "  (Temporary add-ons clear on Firefox restart; re-load after a restart,"
echo "   or sign the .xpi for a permanent install.)"
