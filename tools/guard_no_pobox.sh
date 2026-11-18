#!/bin/bash
# M5 guard (CF5 re-audit): mail must NEVER be tracked in this PUBLIC repo. Hermetic mail lives
# in the separate PRIVATE Tmail-POBOX repo. Runs as a pre-commit hook ("staged") and in CI
# ("tracked"). Exit non-zero = block.
set -euo pipefail
mode="${1:-staged}"
root="$(git rev-parse --show-toplevel)"
cd "$root"
if [ "$mode" = "tracked" ]; then
  bad="$(git ls-files 'private/POBOX/*' || true)"
else
  bad="$(git diff --cached --name-only | grep -E '^private/POBOX/' || true)"
fi
if [ -n "$bad" ]; then
  echo "BLOCKED (M5): these mail paths must never be committed to this PUBLIC repo:" >&2
  echo "$bad" | sed 's/^/  /' >&2
  echo "Hermetic mail belongs in the separate PRIVATE Tmail-POBOX repo." >&2
  exit 1
fi
echo "guard ok: no private/POBOX paths ($mode)"
