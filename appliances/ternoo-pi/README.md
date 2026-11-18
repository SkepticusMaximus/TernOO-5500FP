# ternoo-pi — the Pi 4 USB-gadget appliance

Captured from the live stick on 18-11-2026 (the SD card it was twinned with died
unrecoverable; this is the build-to-repo copy so the config can never be lost with the
media again). **Secrets are NOT here** — the login password hash is redacted and keys are
generated per-device at flash time. Only config lives in the repo.

## What it is
A Raspberry Pi 4 that presents itself to Huey (the HP) as a **USB CDC-ECM network device**
over the USB-C port — a clean wired link with no switch, no Wi-Fi, no exposed surface.

```
  Huey  ──USB-C cable──►  Pi 4 (ternoo-pi)
         usb0 side                usb0 = 10.55.0.1/24, runs a DHCP server (pool .20–.50)
  Huey gets 10.55.0.x by DHCP and reaches the Pi at 10.55.0.1
  ternoo-web.service serves the TernOO/TernID web face on the Pi (…:8620)
```

## Pieces
| file | on the Pi | role |
|------|-----------|------|
| `boot/config.gadget.txt`                    | `/boot/firmware/config.txt` (append) | **one** dwc2 overlay in **peripheral** mode |
| `rootfs/usr/local/sbin/ternoo-usb-gadget.sh`| same path | builds the configfs ECM gadget, binds the UDC |
| `rootfs/etc/systemd/system/ternoo-usb-gadget.service` | same | oneshot that runs the script at boot |
| `rootfs/etc/systemd/network/10-usb0.network`| same | usb0 address + DHCP server |
| `rootfs/etc/systemd/system/ternoo-web.service` | same | the TernOO web face |
| `cloud-init/{user-data,meta-data,network-config}` | the boot vfat (NoCloud) | first-boot provisioning (password REDACTED) |

## The bug we just fixed (18-11-2026)
`config.txt` carried **two** dwc2 overlays: the base image's `dtoverlay=dwc2` (OTG mode)
**and** a later `dtoverlay=dwc2,dr_mode=peripheral`. Two overlays on the same controller
fight, so the UDC never settled into device mode and `usb0` never bound — the gadget
"failed to come up" at boot. Fix: keep a **single** `dtoverlay=dwc2,dr_mode=peripheral`
and remove the plain `dtoverlay=dwc2`. The canonical `config.gadget.txt` here reflects that.

The repo copy of the gadget script also hardens the UDC bind: it waits up to 10 s for
`/sys/class/udc` to appear and **exits non-zero** if it never does, so a real failure is
visible in `systemctl status` / the journal instead of silently succeeding.

## Flash / re-apply
1. Flash Ubuntu Server 24.04 (arm64) for Pi 4.
2. Copy `cloud-init/*` onto the boot vfat; set a real password hash in `user-data`
   (`openssl passwd -5`) and your own `ssh_authorized_keys`. Never commit those back.
3. Append `boot/config.gadget.txt` to the boot `config.txt`, and make sure there is no
   other `dtoverlay=dwc2` line.
4. First boot runs cloud-init, which drops the `rootfs/` files and enables the services.
