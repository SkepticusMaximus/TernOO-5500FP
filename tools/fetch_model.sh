#!/usr/bin/env bash
# fetch_model.sh — captive-portal-proof model downloader.
#
# HuggingFace serves range requests, so `curl -C -` resumes at the exact byte
# after any dropout. Portal logouts therefore cost only the offline minutes:
# the loop just retries until the file is complete. Safe to re-run any time;
# progress survives reboots (partial file stays on disk).
#
#   bash tools/fetch_model.sh <url> <dest-path> <expected-bytes>
#
# Watch progress:  bash tools/fetch_model.sh --watch <dest-path> <expected-bytes>

set -u
if [ "${1:-}" = "--watch" ]; then
    exec watch -n30 "ls -l '$2' 2>/dev/null | awk '{printf \"%.2f GiB of %.2f\n\", \$5/1073741824, $3/1073741824}' || echo 'not started'"
fi

URL="$1"; DEST="$2"; WANT="$3"
mkdir -p "$(dirname "$DEST")"
while :; do
    have=$(stat -c %s "$DEST" 2>/dev/null || echo 0)
    if [ "$have" -ge "$WANT" ]; then
        echo "[fetch] complete: $DEST ($have bytes)"
        break
    fi
    # PORTAL GUARD (10-09 postmortem): a captive portal can answer a range
    # request with its login page — 200 OK, HTML, silently appended, sha256
    # ruined. Probe the resume point first; only append when the wire is
    # serving real bytes.
    if [ "$have" -gt 0 ]; then
        p=$(curl -sfL -r "$have-$((have + 63))" --connect-timeout 15 \
                 --max-time 45 "$URL" | head -c 64 || true)
        if [ -z "$p" ] || printf '%s' "$p" | grep -qi '<html\|<!doct'; then
            echo "[fetch] portal/no-data at resume point — waiting"
            sleep 15
            continue
        fi
    fi
    echo "[fetch] at $have of $WANT bytes — (re)starting"
    curl -L -C - --fail --retry 10 --retry-delay 5 --connect-timeout 20 \
         -o "$DEST" "$URL"
    sleep 10        # portal down: breathe, then resume at the exact byte
done
