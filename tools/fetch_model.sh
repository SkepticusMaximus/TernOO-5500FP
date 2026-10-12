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
    # Live readout: size, percent, sampled rate, ETA. The fetch loop itself
    # logs quietly (12-10), so this is the instrument that proves it's alive.
    W_DEST="$2"; W_WANT="$3"; prev=0; prev_t=0
    while :; do
        now=$(stat -c %s "$W_DEST" 2>/dev/null || echo 0)
        t=$(date +%s)
        rate=0
        [ "$prev_t" -gt 0 ] && [ "$t" -gt "$prev_t" ] && rate=$(( (now - prev) / (t - prev_t) ))
        eta='--'
        if [ "$rate" -gt 0 ]; then
            s=$(( (W_WANT - now) / rate ))
            eta=$(printf '%dh%02dm' $((s / 3600)) $(((s % 3600) / 60)))
        fi
        awk -v n="$now" -v w="$W_WANT" -v r="$rate" -v e="$eta" 'BEGIN{
            printf "\r  %.2f of %.2f GiB   %5.1f%%   %5d KB/s   ETA %-7s", \
                   n/1073741824, w/1073741824, (w ? 100*n/w : 0), r/1024, e}'
        [ "$now" -ge "$W_WANT" ] && { echo; echo "  complete."; break; }
        prev=$now; prev_t=$t
        sleep 5
    done
    exit 0
fi

URL="$1"; DEST="$2"; WANT="$3"
mkdir -p "$(dirname "$DEST")"

# SINGLE-WRITER GUARD (12-10 postmortem): the start line is long enough that
# it gets pasted twice. Two fetches of one DEST both append with `curl -C -`,
# interleave their bytes, and silently ruin the file while the size still
# climbs. Re-exec under flock so the second run declines instead.
LOCK="/tmp/fetch_model.$(printf '%s' "$DEST" | md5sum | cut -c1-16).lock"
if [ "${FETCH_MODEL_LOCKED:-}" != "1" ]; then
    export FETCH_MODEL_LOCKED=1
    flock -n "$LOCK" bash "$0" "$URL" "$DEST" "$WANT"
    rc=$?
    [ "$rc" -eq 1 ] && echo "[fetch] already fetching $DEST — this run declined"
    exit "$rc"
fi

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
                 --max-time 45 "$URL" | head -c 64 | tr -d '\0' || true)
        if [ -z "$p" ] || printf '%s' "$p" | grep -qi '<html\|<!doct'; then
            echo "[fetch] portal/no-data at resume point — waiting"
            sleep 15
            continue
        fi
    fi
    echo "[fetch] $(date '+%H:%M:%S') at $have of $WANT bytes — (re)starting"
    # --no-progress-meter: curl's meter wrote ~1 MB of carriage-returned noise
    # into the nohup log. Live progress is the --watch mode's job.
    curl -L -C - --fail --no-progress-meter --retry 10 --retry-delay 5 \
         --connect-timeout 20 -o "$DEST" "$URL"
    sleep 10        # portal down: breathe, then resume at the exact byte
done
