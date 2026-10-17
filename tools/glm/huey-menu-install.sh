#!/bin/bash
# Installs the Huey GLM-appliance console menu + desktop return icon.
# Run ONCE, now, while the GUI is up:   sudo bash ~/huey-menu-install.sh
set -e
U=stevo; H=/home/$U

echo "== 1/5  console menu  =="
# The menu script lives in the repo at tools/glm/huey-console -- it is NOT
# inlined here any more.  The inlined first version piped the GLM log through
# `less`, which trapped the console (q and Ctrl+C did not escape) and forced a
# Ctrl+Alt+F2 rescue; keeping one copy under version control is how that stays
# fixed.  A user-space copy in ~/.local/bin is what the tty1 hook actually
# runs, so the menu can be updated without root.
SRC="$(dirname "$(readlink -f "$0")")/huey-console"
[ -r "$SRC" ] || { echo "cannot find huey-console next to this installer"; exit 1; }
install -m 755 "$SRC" /usr/local/bin/huey-console
install -d -o $U -g $U $H/.local/bin
install -m 755 -o $U -g $U "$SRC" $H/.local/bin/huey-console

echo "== 2/5  auto-show menu on headless tty1  =="
touch $H/.profile
if ! grep -q huey-console $H/.profile; then
cat >>$H/.profile <<'HOOK'

# Huey GLM-appliance menu: only on the physical text console, not SSH or GUI
if [ "$(tty)" = "/dev/tty1" ] && [ -z "$DISPLAY" ]; then "$HOME/.local/bin/huey-console"; fi
HOOK
fi
chown $U:$U $H/.profile

echo "== 3/5  passwordless switching for the menu/icon  =="
cat >/etc/sudoers.d/huey-menu <<EOF
$U ALL=(root) NOPASSWD: /usr/bin/systemctl stop glm, /usr/bin/systemctl start glm, /usr/bin/systemctl restart glm, /usr/bin/systemctl isolate graphical.target, /usr/bin/systemctl isolate multi-user.target, /usr/bin/systemctl reboot, /usr/bin/systemctl poweroff
EOF
chmod 440 /etc/sudoers.d/huey-menu
visudo -c -f /etc/sudoers.d/huey-menu >/dev/null

echo "== 4/5  desktop 'Back to GLM Appliance' icon  =="
mkdir -p $H/Desktop
cat >$H/Desktop/back-to-appliance.desktop <<'DESK'
[Desktop Entry]
Type=Application
Name=Back to GLM Appliance (headless)
Comment=Reboot Huey into the headless GLM oracle
Exec=sh -c 'zenity --question --title="GLM Appliance" --text="Reboot Huey into the headless GLM appliance?" && sudo systemctl reboot'
Icon=system-reboot
Terminal=false
DESK
chmod +x $H/Desktop/back-to-appliance.desktop
chown $U:$U $H/Desktop/back-to-appliance.desktop
# mark trusted so Cinnamon launches it without the "untrusted" prompt
sudo -u $U gio set $H/Desktop/back-to-appliance.desktop metadata::trusted true 2>/dev/null || true

echo "== 5/5  make the GRUB boot menu visible (fallback)  =="
sed -i 's/^GRUB_TIMEOUT_STYLE=.*/GRUB_TIMEOUT_STYLE=menu/' /etc/default/grub 2>/dev/null || echo 'GRUB_TIMEOUT_STYLE=menu' >>/etc/default/grub
grep -q '^GRUB_TIMEOUT_STYLE=menu' /etc/default/grub || echo 'GRUB_TIMEOUT_STYLE=menu' >>/etc/default/grub
sed -i 's/^GRUB_TIMEOUT=.*/GRUB_TIMEOUT=5/' /etc/default/grub
update-grub >/dev/null 2>&1 || true

echo
echo "DONE. Round-trip set up:"
echo "  - Headless: log in at the screen -> the menu appears -> pick 1 for the desktop."
echo "  - Desktop: double-click 'Back to GLM Appliance' on the desktop to return."
echo "  - Escape hatch: Ctrl+Alt+F2 at the console = a plain login, no menu."
