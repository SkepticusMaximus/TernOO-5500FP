#!/usr/bin/env bash
# professor_resident.sh — turn the RESIDENT local Professor on or off, and
# see exactly what it costs. (Captain, 08-09-2026: "I can't tell what
# resource drain it will cause. Can't you make it switchable.")
#
#   bash tools/professor_resident.sh status   # what's loaded, what it costs
#   bash tools/professor_resident.sh on       # keep the model in RAM
#   bash tools/professor_resident.sh off      # release the RAM
#
# "on" installs a systemd --user service (auto-starts at login, survives
# reboots). "off" stops and disables it — nothing is left running. Neither
# touches a server you started yourself by other means.
set -u

UNIT="ternoo-professor"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CFG="$REPO/5500fp/bonsai.json"
PORT=8099
say() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ok()  { printf '  \033[1;32m%s\033[0m\n' "$*"; }
inf() { printf '  %s\n' "$*"; }

find_bin() { find "$HOME/LOCAL_AI" -maxdepth 5 -type f -perm -u+x \
    -name 'llama-server' -printf '%T@ %p\n' 2>/dev/null |
    sort -rn | head -1 | cut -d' ' -f2-; }

live_url() {
    for p in 8090 8080 8081 "$PORT"; do
        curl -sS -f -o /dev/null --max-time 2 "http://127.0.0.1:$p/health" \
            2>/dev/null && { echo "http://127.0.0.1:$p"; return; }
    done
}

cost_report() {
    # What the resident model actually costs, measured — not guessed.
    local pids rss=0 total
    pids=$(pgrep -f 'llama-server' 2>/dev/null)
    if [ -z "$pids" ]; then
        inf "resident model: none running (0 MB held)"
        return
    fi
    for p in $pids; do
        local k
        k=$(awk '/^VmRSS:/{print $2}' "/proc/$p/status" 2>/dev/null)
        [ -n "${k:-}" ] && rss=$((rss + k))
    done
    total=$(awk '/^MemTotal:/{print int($2/1024)}' /proc/meminfo)
    local avail
    avail=$(awk '/^MemAvailable:/{print int($2/1024)}' /proc/meminfo)
    inf "resident model holds : $((rss / 1024)) MB"
    inf "RAM free right now   : ${avail} MB of ${total} MB"
    inf "CPU: only while ANSWERING — an idle resident model uses ~0%."
}

case "${1:-status}" in
status)
    say "Resident Professor — status"
    U=$(live_url)
    if [ -n "$U" ]; then
        ok "ANSWERING at $U"
        M=$(curl -sS -f --max-time 3 "$U/props" 2>/dev/null |
            python3 -c 'import json,sys
try:
  d=json.load(sys.stdin)
  print(d.get("model_path") or d.get("model") or "")
except Exception: print("")' 2>/dev/null)
        [ -n "$M" ] && inf "model: $(basename "$M")"
    else
        inf "no resident server answering"
    fi
    systemctl --user is-enabled "$UNIT" >/dev/null 2>&1 &&
        inf "our service: enabled (starts at login)" ||
        inf "our service: not installed"
    say "What it costs"
    cost_report
    ;;
on)
    say "Turning the resident Professor ON"
    U=$(live_url)
    if [ -n "$U" ]; then
        ok "already resident at $U — nothing to start"
    else
        BIN=$(find_bin)
        [ -z "$BIN" ] && { inf "no llama-server binary found"; exit 1; }
        MODEL=$(python3 -c "
import json,os
try:
    c=json.load(open('$CFG')); m=c.get('model','')
    print(m if m and os.path.exists(m) else '')
except Exception: print('')")
        if [ -z "$MODEL" ]; then
            MODEL=$(find "$HOME/LOCAL_AI" -name '*.gguf' -printf '%s %p\n' \
                2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)
        fi
        [ -z "$MODEL" ] && { inf "no .gguf model found"; exit 1; }
        inf "loading $(basename "$MODEL") …"
        mkdir -p "$HOME/.config/systemd/user"
        cat > "$HOME/.config/systemd/user/$UNIT.service" <<UNITEOF
[Unit]
Description=TernOO Professor — resident local model (loopback only)
After=default.target

[Service]
Type=simple
Environment=LD_LIBRARY_PATH=$(dirname "$BIN")
ExecStart=$BIN -m $MODEL --host 127.0.0.1 --port $PORT -c 4096 --threads $(( $(nproc) > 3 ? $(nproc) - 1 : 2 )) -n 512
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
UNITEOF
        systemctl --user daemon-reload
        systemctl --user enable --now "$UNIT.service"
        for i in $(seq 1 45); do
            sleep 2
            U=$(live_url) && [ -n "$U" ] && break
        done
        [ -n "$U" ] && ok "resident at $U" ||
            { inf "not answering yet — systemctl --user status $UNIT"; exit 1; }
    fi
    python3 - "$CFG" "$U" <<'PY'
import json, sys
p, url = sys.argv[1], sys.argv[2]
try:
    c = json.load(open(p))
except Exception:
    c = {}
c["server_url"] = url
json.dump(c, open(p, "w"), indent=2)
print(f"  seat now uses the resident server at {url}")
PY
    cost_report
    ;;
off)
    say "Turning the resident Professor OFF"
    systemctl --user disable --now "$UNIT.service" 2>/dev/null &&
        ok "service stopped and disabled (RAM released)" ||
        inf "our service wasn't running"
    python3 - "$CFG" <<'PY'
import json, sys
p = sys.argv[1]
try:
    c = json.load(open(p))
except Exception:
    c = {}
if c.pop("server_url", None):
    json.dump(c, open(p, "w"), indent=2)
    print("  seat falls back to the on-demand path")
else:
    print("  seat was already on-demand")
PY
    U=$(live_url)
    [ -n "$U" ] && inf "note: something else still serves at $U (not ours)"
    cost_report
    ;;
*)
    echo "usage: $0 [status|on|off]"; exit 2 ;;
esac
