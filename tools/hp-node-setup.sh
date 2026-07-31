#!/usr/bin/env bash
# ============================================================================
#  TernOO / P2PCP — HP EliteBook "second node" setup  (Linux Mint)
#
#  Makes the HP a P2PCP compute node with its OWN identity, plus a read/send
#  mail client. DELIBERATELY NOT installed (these must live on ONE machine or
#  they clash — they stay on the Lenovo):
#     • the cai-mailbox / cf5-mailbox auto-reply worker crew
#     • the CC heartbeat cron
#
#  Run on the HP:   bash tools/hp-node-setup.sh     (asks for sudo once)
#  Safe to re-run. Steps are guarded — one hiccup won't abort the rest.
# ============================================================================
set -u
DEV="$HOME/dev/SkepticusMaximus"
VENV="$HOME/.venvs/p2pcp"
KEY="$HOME/.p2pcp/hp.key"
PORT=9000
say(){ printf '\n=== %s ===\n' "$*"; }
ok(){  printf '  [ok] %s\n' "$*"; }
no(){  printf '  [!!] %s\n' "$*"; }

say "0/6  repos present?"
[ -d "$DEV/p2pcp/.git" ] && ok "p2pcp cloned" || { no "p2pcp missing at $DEV/p2pcp — clone it first"; exit 1; }
[ -d "$DEV/TernOO-5500FP/.git" ] && ok "TernOO-5500FP cloned" || no "TernOO-5500FP missing (only the mail client needs it)"

say "1/6  system packages"
sudo apt-get update -qq
sudo apt-get install -y python3-venv python3-pip git >/dev/null 2>&1 \
  && ok "python3-venv, pip, git" || no "apt install had trouble — check your connection"

say "2/6  P2PCP install (isolated venv — Mint blocks system pip on purpose)"
python3 -m venv "$VENV" && ok "venv at $VENV" || no "venv failed (python3-venv installed?)"
"$VENV/bin/pip" install -q -e "$DEV/p2pcp" && ok "p2pcp installed (editable)" || no "pip install -e failed"

say "3/6  run it 24/7 as a service — this also MINTS the node's OWN identity"
echo "     (never copy another machine's keyfile — each node is its own account)"
mkdir -p "$HOME/.config/systemd/user" "$(dirname "$KEY")"
cat > "$HOME/.config/systemd/user/p2pcp-node.service" <<UNIT
[Unit]
Description=P2PCP compute node (HP) — sells compute for CompuCoin
[Service]
ExecStart=$VENV/bin/p2pcp serve --host 0.0.0.0 --port $PORT --keyfile $KEY
Restart=on-failure
RestartSec=15
[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now p2pcp-node.service \
  && ok "node running on port $PORT (all interfaces)" || no "service didn't start — systemctl --user status p2pcp-node"
sleep 3
[ -f "$KEY" ] && ok "fresh identity minted: $KEY" || no "key not created — journalctl --user -u p2pcp-node -n20"
echo "  --- this node's wallet ---"
"$VENV/bin/p2pcp" wallet --keyfile "$KEY" 2>/dev/null | sed 's/^/  /' || no "wallet read failed"
# To keep the node running even when you're logged out (optional, needs sudo):
#   sudo loginctl enable-linger $USER

say "4/6  mail CLIENT — read anytime; SENDING needs git auth (see note)"
if [ -d "$DEV/TernOO-5500FP" ]; then
  ok "read/compose:  python3 $DEV/TernOO-5500FP/tools/pobox_mail.py"
  echo "     To SEND from the HP you need git push auth here first (public repo, so"
  echo "     reading is free; pushing is not). Easiest:  gh auth login   (or add a PAT)."
  echo "     THEN enable save=send:"
  echo "       cp $DEV/TernOO-5500FP/tools/pobox-outbox.service ~/.config/systemd/user/"
  echo "       systemctl --user enable --now pobox-outbox.service"
  echo "     Deliberately NOT enabled: cai/cf5-mailbox workers + CC heartbeat (one home only)."
fi

say "5/6  KDE Connect"
sudo apt-get install -y kdeconnect >/dev/null 2>&1 \
  && ok "KDE Connect installed — open it and pair your phone" \
  || no "apt failed; try:  flatpak install -y flathub org.kde.kdeconnect"

say "6/6  GitHub Desktop"
no "No official GitHub Desktop for Linux. The community fork works well:"
echo "     https://github.com/shiftkey/desktop/releases  → grab the .deb, then:"
echo "       sudo apt install ./GitHubDesktop-linux-*.deb"

say "DONE — what you've got"
echo "  • P2PCP node: own key $KEY, port $PORT, auto-restart, LAN-reachable."
echo "  • NOT installed on purpose: cai/cf5-mailbox workers + CC heartbeat (Lenovo keeps those)."
echo
echo "  Prove the HP + Lenovo trade compute over your home wifi:"
echo "    1) on the HP:      hostname -I            # note its LAN IP, e.g. 192.168.1.42"
echo "    2) on the Lenovo:  ~/.venvs/p2pcp/bin/p2pcp buy \"hello mesh\" --host <HP-IP> --port $PORT --chunks 2 --k 2"
echo "  Earnings anytime:    $VENV/bin/p2pcp wallet --keyfile $KEY"
echo
echo "  Note: the node listens on all interfaces (needed for LAN trading). On your"
echo "  home network that's fine; to sell to the wider internet you'd port-forward $PORT."
