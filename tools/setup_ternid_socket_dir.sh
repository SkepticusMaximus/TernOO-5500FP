#!/bin/bash
# B/g56 — the shared socket dir for the TernID agent, so seat users can reach it.
#
# CCC's agent (TernID main b1da904) binds /run/ternid/agent.sock at mode 0660 but
# deliberately does NOT chgrp the socket. So the DIR must be SETGID (2750), group
# `ternid` — then the 0660 socket inherits group `ternid` automatically, every seat
# user (all in group ternid) can connect, and non-members can't even see it.
#
# /run is tmpfs (wiped each boot), so we persist via a tmpfiles.d rule (recreated on
# every boot) AND apply it now. Run with: sudo bash tools/setup_ternid_socket_dir.sh
set -euo pipefail
RULE=/etc/tmpfiles.d/ternid.conf
# type path            mode  user   group   age arg
echo 'd /run/ternid    2750  stevo  ternid  -   -' > "$RULE"
systemd-tmpfiles --create "$RULE"
echo "rule written: $RULE"
ls -ld /run/ternid
echo ""
echo "/run/ternid ready (setgid 2750, stevo:ternid). The agent will bind"
echo "/run/ternid/agent.sock there; the 0660 socket inherits group 'ternid'."
