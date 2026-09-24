#!/bin/sh
# ternui/run.sh [design.fc] — runs the engine (drive) + the native
# window together, one command, with the good DejaVu font.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1
DESIGN="${1:-FlowCode/Font-Browser.fc}"
STREAM="/tmp/ternui_$$.tuw"
BIN=/tmp/ternui_native
[ -x "$BIN" ] || gcc -O2 -o "$BIN" ternui/ternui_native.c \
    $(pkg-config --cflags --libs sdl2 SDL2_ttf) || exit 1
export TERNUI_FONT="$ROOT/ternui/dejavu.thf"
command -v zenity >/dev/null 2>&1 || \
    echo "note: 'zenity' not found — Browse/Pick need it: sudo apt install zenity"
rm -f "$STREAM"*
python3 ternui/ternui_drive.py "$DESIGN" "$STREAM" &
DRIVE=$!
sleep 1
"$BIN" "$STREAM"
kill "$DRIVE" 2>/dev/null
rm -f "$STREAM"*
