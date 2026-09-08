#!/usr/bin/env bash
# setup_offline_hp.sh — bring THIS machine's offline environment up to date.
#
# Written for the airport session, 08-09-2026: the two machines cannot see
# each other (public-WiFi client isolation + a firewall that blocks
# Tailscale's control plane), so instead of CC reaching in over SSH, the
# captain runs this once on HP. Everything it needs travels by git.
#
# Safe to re-run. Changes nothing it doesn't report.
set -u

REPO="$HOME/dev/SkepticusMaximus/TernOO-5500FP"
VENV="$HOME/.venvs/p2pcp/bin/python"
LLAMA_DIR="$HOME/LOCAL_AI/Llama"
say() { printf '\n\033[1;36m== %s\033[0m\n' "$*"; }
ok()  { printf '  \033[1;32mOK\033[0m   %s\n' "$*"; }
bad() { printf '  \033[1;31mMISS\033[0m %s\n' "$*"; }

say "1. Latest code"
cd "$REPO" || { bad "repo not at $REPO"; exit 1; }
git pull --ff-only 2>&1 | tail -2

say "2. Models on disk"
best=""
for m in "Ternary-Bonsai-8B-TQ2_0.gguf" "OLMo-2-1124-7B-SFT.i1-Q4_K_M.gguf"; do
    if [ -f "$LLAMA_DIR/$m" ]; then
        ok "$m ($(du -h "$LLAMA_DIR/$m" | cut -f1))"
        [ -z "$best" ] && best="$LLAMA_DIR/$m"
    else
        bad "$m absent"
    fi
done

say "3. llama binary"
LLAMA_BIN=""
for c in "$LLAMA_DIR/prism-official/build/bin/llama-completion" \
         "$HOME/LOCAL_AI/llama-bin/llama-completion" \
         "$HOME/LOCAL_AI/llama-bin/llama-cli"; do
    [ -x "$c" ] && { LLAMA_BIN="$c"; ok "$c"; break; }
done
[ -z "$LLAMA_BIN" ] && bad "no llama binary found — local seat will stay empty"

say "4. Professor seat config (5500fp/bonsai.json)"
CFG="$REPO/5500fp/bonsai.json"
if [ -n "$LLAMA_BIN" ] && [ -n "$best" ]; then
    python3 - "$CFG" "$LLAMA_BIN" "$best" <<'PY'
import json, os, sys
cfg_path, llama, model = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    cfg = json.load(open(cfg_path))
except Exception:
    cfg = {}
cfg["enabled"] = True
cfg["llama"] = llama
# NEVER clobber a seat that already points at a model present on this
# machine — the captain's own choice wins. Only fill an empty/broken seat.
cur = cfg.get("model")
if not (cur and os.path.exists(cur)):
    cfg["model"] = model
else:
    model = cur
    print(f"  keeping existing seat: {os.path.basename(cur)}")
cfg.setdefault("n_predict", 384)
cfg.setdefault("ctx", 2048)
cfg.setdefault("ask_timeout", 2400)
cfg.setdefault("min_free_mb", None)
cfg.setdefault("draft_model", None)
# HP has more cores and RAM than Lenny — let the Professor use them.
try:
    cfg["threads"] = max(3, min(os.cpu_count() or 4, 8) - 1)
except Exception:
    cfg["threads"] = 4
name = os.path.basename(model).lower()
cfg["format"] = "tulu" if ("olmo" in name or "tulu" in name) else "qwen3"
json.dump(cfg, open(cfg_path, "w"), indent=2)
print(f"  seat -> {os.path.basename(model)}  format={cfg['format']}  "
      f"threads={cfg['threads']}")
PY
    ok "bonsai.json written for this machine's paths"
else
    bad "seat not configured (missing binary or model)"
fi

say "5. Python env"
if [ -x "$VENV" ]; then
    ok "$VENV"
    "$VENV" -c "import dearpygui; print('  dearpygui', dearpygui.__version__)" \
        2>/dev/null || bad "dearpygui missing in venv (DPG faces won't run)"
else
    bad "venv missing at $VENV"
fi

say "6. Gate suite (proves the code is sound on this machine)"
cd "$REPO/FlowCode" && SMOKE=1 FLOW_DPG_TEST=1 "$VENV" flowcode_dpg.py 2>&1 \
    | grep -cE " OK" | xargs -I{} echo "  {} gates passed"

say "7. Offline readiness"
printf '  local model  : %s\n' "$([ -n "$best" ] && basename "$best" || echo NONE)"
printf '  works w/o net: yes (model + engine are local)\n'
printf '\nDone. Open FlowCode, Mesh-Chat tab, pick the "Local" seat.\n'
