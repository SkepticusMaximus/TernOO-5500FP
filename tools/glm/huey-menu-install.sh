#!/bin/bash
# Installs the Huey GLM-appliance console menu + desktop return icon.
# Run ONCE, now, while the GUI is up:   sudo bash ~/huey-menu-install.sh
set -e
U=stevo; H=/home/$U

echo "== 1/5  console menu  =="
cat >/usr/local/bin/huey-console <<'SCRIPT'
#!/bin/bash
# Headless console menu for the Huey GLM appliance (auto-shown on tty1).
while true; do
  clear
  echo " ========================================"
  echo "    HUEY  —  GLM Oracle Appliance"
  echo " ========================================"
  if systemctl is-active --quiet glm; then
    if ss -ltn 2>/dev/null | grep -q ':8000'; then
      echo "    GLM : READY  (serving on port 8000)"
    else
      echo "    GLM : starting... (loading dense core, ~1 min)"
    fi
  else
    echo "    GLM : stopped"
  fi
  echo " ----------------------------------------"
  echo "    1)  Switch to the DESKTOP (GUI)"
  echo "    2)  Restart GLM"
  echo "    3)  Show GLM log"
  echo "    4)  Command shell  (type 'exit' to return)"
  echo "    5)  Reboot"
  echo "    6)  Power off"
  echo " ----------------------------------------"
  echo "    (Tip: Ctrl+Alt+F2 gives a plain login without this menu)"
  read -rp "    Choose [1-6]: " c
  case "$c" in
    1) echo "    Freeing GLM and starting the desktop..."; sudo systemctl stop glm 2>/dev/null || true; sudo systemctl isolate graphical.target;;
    2) sudo systemctl restart glm; echo "    GLM restarting..."; sleep 3;;
    3) journalctl -u glm -n 60 --no-pager 2>/dev/null | less;;
    4) echo; bash;;
    5) sudo systemctl reboot;;
    6) sudo systemctl poweroff;;
    *) ;;
  esac
done
SCRIPT
chmod +x /usr/local/bin/huey-console

echo "== 2/5  auto-show menu on headless tty1  =="
touch $H/.profile
if ! grep -q huey-console $H/.profile; then
cat >>$H/.profile <<'HOOK'

# Huey GLM-appliance menu: only on the physical text console, not SSH or GUI
if [ "$(tty)" = "/dev/tty1" ] && [ -z "$DISPLAY" ]; then huey-console; fi
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
