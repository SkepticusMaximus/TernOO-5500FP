#!/usr/bin/env bash
# ============================================================================
#  One-time: let the Lenovo (where CC lives) drive THIS HP over SSH on the LAN.
#  After this runs, CC can execute commands on the HP directly — no more
#  emailing/retyping commands between your two machines.
#
#  Run on the HP:   bash tools/hp-ssh-bootstrap.sh      (asks for sudo once)
#
#  Security: the key below is CC's Lenovo *public* key — safe to publish. Only
#  the private half (which never leaves the Lenovo) can actually log in, and
#  only from your own LAN.
# ============================================================================
set -u
PUBKEY='ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPK8dRmq6sq8zLMdSYlrMr1oEZ+aX4HKBjmyC2OzMRjr cc-on-lenovo'

echo "=== 1/3  install + start the SSH server ==="
sudo apt-get update -qq
sudo apt-get install -y openssh-server >/dev/null 2>&1 && echo "  openssh-server installed"
sudo systemctl enable --now ssh 2>/dev/null || sudo systemctl enable --now sshd 2>/dev/null
if systemctl is-active ssh >/dev/null 2>&1 || systemctl is-active sshd >/dev/null 2>&1; then
  echo "  SSH service active ✓"
else
  echo "  [!!] SSH not active — run: sudo systemctl status ssh"
fi

echo "=== 2/3  authorize the Lenovo's key ==="
mkdir -p ~/.ssh && chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
grep -qF "$PUBKEY" ~/.ssh/authorized_keys || echo "$PUBKEY" >> ~/.ssh/authorized_keys
echo "  Lenovo key authorized ✓"

echo "=== 3/3  this HP's address (tell CC these) ==="
echo "  user: $USER"
echo "  host: $(hostname)"
echo "  IP:   $(hostname -I | awk '{print $1}')"
echo
echo "DONE. Tell CC the user + IP above, and it'll SSH in from the Lenovo,"
echo "passwordless, to drive this machine directly."
