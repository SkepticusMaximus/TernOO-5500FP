#!/usr/bin/env bash
# Provision CC's own seat on Huey — the ternid-cc user — per CF5 docket R3 (28-11-2026).
#
# REVIEW THIS before you run it. It is deliberately minimal: it stands up an ISOLATED home for
# CC so CC holds its OWN key in a keystore your login user cannot read. It does NOT touch
# ~stevo/.config, your seat.key, your session, your repo, or any sudo rule. Those boundary bits
# are left for you + CCC + CF5 to sign off separately (see the end).
#
#   sudo bash tools/provision_ternid_cc.sh
set -euo pipefail

CC_USER=ternid-cc
[ "$(id -u)" = 0 ] || { echo "run with sudo: sudo bash $0"; exit 1; }

# 1. the crew group (shared standing for the fleet's agents; no rights by itself)
getent group crew >/dev/null || groupadd crew

# 2. CC's own user + home, a member of crew
id "$CC_USER" >/dev/null 2>&1 || useradd -m -G crew -s /bin/bash "$CC_USER"

# 3. CC's keystore: 0700, owned by CC alone. Your login user cannot read CC's key through any
#    normal path — only a deliberate root act could (card custody = host-uid, stated honestly).
install -d -m 0700 -o "$CC_USER" -g "$CC_USER" "/home/$CC_USER/.config/ternoo/keys"

echo "OK — $CC_USER created; keystore /home/$CC_USER/.config/ternoo/keys (0700, $CC_USER-only)."
echo "Your user (${SUDO_USER:-you}) cannot read CC's key through the mail system; only root could,"
echo "by a deliberate act. That is the custody=host-uid limit, out loud."
echo
echo "LEFT FOR YOUR / CCC / CF5 SIGN-OFF (the trust boundary — not guessed here):"
echo "  • the narrow sudo rule: 'stevo ALL=(ternid-cc) NOPASSWD: <CC's mail entrypoint>'."
echo "    Proposed entrypoint = CC's mail ops only (hsend + the hermetic_syncd carrier via one"
echo "    wrapper), nothing else. Confirm the wrapper path, then add /etc/sudoers.d/ternid-cc."
echo "  • crew-group write on the dev trees, if/when CC commits code as itself (not needed for mail)."
