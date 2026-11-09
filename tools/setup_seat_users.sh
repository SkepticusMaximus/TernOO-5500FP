#!/bin/bash
# B / g51 foundation — per-seat OS users on Huey.
#
# Why: so the TernID agent can enforce per-seat mail privacy for real. Each seat as
# its OWN OS user means (a) a seat's 0600 token file genuinely isolates — no other
# seat can read it, and (b) the agent can tie an incoming socket connection to a seat
# by its PEER UID (SO_PEERCRED), no token-matching guesswork (CCC's "even tighter").
#
# stevo (uid 1000) stays the ADMIN seat: runs the mail app, sees all boxes (oversight).
# The 5 AI seats get restricted users: ternid-cc / -ccc / -cf5 / -cai / -professor.
#
# Run with: sudo bash tools/setup_seat_users.sh   (review it first — it creates users)
set -euo pipefail
GROUP=ternid
SEATS="cc ccc cf5 cai professor"

getent group "$GROUP" >/dev/null || groupadd "$GROUP"
id -nG stevo | grep -qw "$GROUP" || usermod -aG "$GROUP" stevo   # admin shares the group (socket reach)

for s in $SEATS; do
  u="ternid-$s"
  if id "$u" >/dev/null 2>&1; then
    echo "exists: $u"
  else
    useradd -m -G "$GROUP" -s /bin/bash -c "TernID seat $s" "$u"
    echo "created: $u (uid $(id -u "$u"))"
  fi
done

echo ""
echo "== uid -> seat map (hand this to CCC for the SO_PEERCRED binding) =="
printf "  uid %-6s %-12s [ADMIN — sees all]\n" "$(id -u stevo)" stevo
for s in $SEATS; do printf "  uid %-6s %-12s\n" "$(id -u "ternid-$s")" "$s"; done
echo ""
echo "NEXT (coordination with CCC, not done here): the agent socket is currently at"
echo "  /run/user/1000/ternid-agent.sock — inside stevo's PRIVATE runtime dir (0700),"
echo "  which the seat users cannot reach. For them to connect, the agent must bind a"
echo "  group-shared socket (e.g. /run/ternid/agent.sock, group $GROUP, mode 0660)."
echo "  That's a CCC build detail; CC will set up the shared dir (tmpfiles.d) on the word."
