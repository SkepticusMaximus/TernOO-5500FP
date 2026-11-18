#!/bin/bash
# TernOO USB CDC-ECM gadget — a clean cdc_ether link to the host (Huey).
# Canonical repo copy: same as deployed, plus a UDC wait+fail so a real failure is VISIBLE
# (systemctl status / journal) instead of silently exiting 0 with no usb0.
GDIR=/sys/kernel/config/usb_gadget/ternoo
modprobe libcomposite 2>/dev/null || true
mountpoint -q /sys/kernel/config || mount -t configfs none /sys/kernel/config 2>/dev/null || true
if [ ! -s "$GDIR/UDC" ]; then
  mkdir -p "$GDIR"
  cd "$GDIR" || exit 1
  echo 0x1d6b > idVendor
  echo 0x0104 > idProduct
  echo 0x0100 > bcdDevice
  echo 0x0200 > bcdUSB
  mkdir -p strings/0x409
  echo TernOO > strings/0x409/manufacturer
  echo "TernOO-Pi Gadget" > strings/0x409/product
  echo ternoopi0001 > strings/0x409/serialnumber
  mkdir -p configs/c.1/strings/0x409
  echo "CDC ECM" > configs/c.1/strings/0x409/configuration
  echo 250 > configs/c.1/MaxPower
  mkdir -p functions/ecm.usb0
  echo "3a:f0:0d:00:00:01" > functions/ecm.usb0/dev_addr
  echo "3a:f0:0d:00:00:02" > functions/ecm.usb0/host_addr
  ln -sf functions/ecm.usb0 configs/c.1/
  UDC=""
  for _ in $(seq 1 20); do                       # wait up to 10s for the device-mode UDC
    UDC=$(ls /sys/class/udc 2>/dev/null | head -n1)
    [ -n "$UDC" ] && break
    sleep 0.5
  done
  if [ -n "$UDC" ]; then
    echo "$UDC" > UDC
  else
    echo "ternoo-gadget: no UDC after 10s — is dwc2 in peripheral mode? (single overlay)" >&2
    exit 1
  fi
fi
exit 0
