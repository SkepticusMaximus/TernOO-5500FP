#!/usr/bin/env bash
# repair_model.sh — find where a resumed download went bad, cut, re-fetch.
#
# A captive portal can answer a ranged resume with its login page: 200 OK,
# HTML bytes, silently appended — byte count right, sha256 wrong (10-09,
# the 32B). Corruption starts at ONE offset; everything before it is good.
# Binary-search the first divergent 4 KiB block with ranged probes (~22
# probes), truncate there, then fetch_model.sh finishes the tail.
#
#   bash tools/repair_model.sh <url> <file> <expected-bytes> [expected-sha256]

set -eu
URL="$1"; F="$2"; WANT="$3"; SHA="${4:-}"
PROBE=$(mktemp); trap 'rm -f "$PROBE"' EXIT
B=4096

probe_ok() {                    # does local block at offset $1 match remote?
    local off="$1"
    local end=$((off + B - 1)); [ "$end" -ge "$WANT" ] && end=$((WANT - 1))
    for _try in 1 2 3; do
        if curl -sfL -r "$off-$end" -o "$PROBE" --connect-timeout 20 \
                --max-time 60 "$URL"; then
            # a portal page masquerading as data is not a valid probe
            if ! head -c 64 "$PROBE" | grep -qi '<html\|<!doct'; then
                cmp -s <(dd if="$F" bs=1 skip="$off" count=$((end - off + 1)) \
                         2>/dev/null) "$PROBE" && return 0 || return 1
            fi
        fi
        sleep 5
    done
    echo "[repair] probe at $off failed repeatedly — portal down?" >&2
    exit 2
}

lo=0; hi=$(stat -c %s "$F")
[ "$hi" -gt "$WANT" ] && hi=$WANT
if probe_ok $((hi - B)); then
    echo "[repair] tail block matches — corruption not found by suffix probe;"
    echo "         doing full binary search anyway."
fi
# invariant: block at lo matches (offset 0 assumed good), block at hi-B bad
# find first bad block via binary search on block index
good=0; bad=$(( (hi - 1) / B ))
if probe_ok $((bad * B)); then
    echo "[repair] last block matches remote — corruption is mid-file only;"
fi
while [ $((bad - good)) -gt 1 ]; do
    mid=$(( (good + bad) / 2 ))
    if probe_ok $((mid * B)); then
        good=$mid
    else
        bad=$mid
    fi
    echo "[repair] good<=$good bad>=$bad ($(( (bad - good) )) blocks between)"
done
CUT=$((bad * B))
echo "[repair] first divergent block at byte $CUT — truncating"
truncate -s "$CUT" "$F"
echo "[repair] handing the tail to fetch_model.sh ($((WANT - CUT)) bytes to go)"
bash "$(dirname "$0")/fetch_model.sh" "$URL" "$F" "$WANT"
if [ -n "$SHA" ]; then
    echo "[repair] verifying sha256..."
    have=$(sha256sum "$F" | cut -d' ' -f1)
    if [ "$have" = "$SHA" ]; then
        echo "[repair] sha256 VERIFIED — file is sound"
    else
        echo "[repair] sha256 STILL WRONG ($have) — corruption elsewhere; rerun me"
        exit 3
    fi
fi
