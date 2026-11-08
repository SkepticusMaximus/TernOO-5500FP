# Pi Onion Appliance — air-gapped Tor gateway in a network namespace

An on-box Whonix split: a **gateway** (host namespace, runs Tor) and a **workstation**
(the `torns` network namespace) collapsed onto the one Raspberry Pi. Anything run inside
`torns` can reach the internet **only** through Tor — there is no non-Tor path out of the
namespace. Built + leak-verified 2026-11-08.

## Architecture

```
  host namespace (gateway)                 torns namespace (workstation)
  ┌───────────────────────────┐            ┌──────────────────────────┐
  │ tor0  10.200.0.1/24  ◄─────┼──veth──────┼─► tor1  10.200.0.2/24     │
  │ Tor TransPort 10.200.0.1:9040           │  default route via .0.1  │
  │ Tor DNSPort   10.200.0.1:5353           │  IPv6 DISABLED           │
  │ iptables: redirect + FORWARD drop       │  resolv.conf -> .0.1     │
  └───────────────────────────┘            └──────────────────────────┘
```

- Traffic from `torns` hits the host via the veth; **nat/PREROUTING REDIRECT** sends all
  new TCP → Tor's TransPort and all :53 → Tor's DNSPort. The redirected packets become
  host-local, so they never traverse FORWARD.
- **Leak backstop:** `FORWARD -i tor0 -j DROP` — anything *not* redirected (stray UDP,
  ICMP, a protocol we didn't anticipate) is dropped, never forwarded to the real uplink.
  This matters because the Pi has `ip_forward=1` for the USB-gadget NAT.
- **IPv6 is disabled inside `torns`** so nothing can slip around the IPv4 redirect.

## Files

| File | Installs to | Role |
|---|---|---|
| `torns-up.sh`       | `/usr/local/bin/`            | Builds netns + veth + iptables; (re)binds Tor to the veth IP |
| `torns.service`     | `/etc/systemd/system/`       | Brings the appliance up at boot |
| `torrun`            | `/usr/local/bin/`            | `torrun <cmd>` — run any command through the appliance |
| `pi-internet.sh`    | `/usr/local/bin/`            | Re-asserts the Pi's default route + DNS via the Huey gadget |
| `pi-internet.service` / `.timer` | `/etc/systemd/system/` | Timer re-runs the route assert every 60s (heals networkd flushes) |

Also append this block to `/etc/tor/torrc` (the engine half):

```
# --- TernOO Onion appliance: transparent-proxy engine ---
VirtualAddrNetworkIPv4 10.192.0.0/10
AutomapHostsOnResolve 1
TransPort 10.200.0.1:9040
DNSPort 10.200.0.1:5353
```

## Deploy (on a fresh Pi)

```bash
sudo cp torns-up.sh torrun pi-internet.sh /usr/local/bin/ && sudo chmod +x /usr/local/bin/{torns-up.sh,torrun,pi-internet.sh}
sudo cp torns.service pi-internet.service pi-internet.timer /etc/systemd/system/
# append the torrc block above, then:
sudo systemctl daemon-reload
sudo systemctl enable --now pi-internet.timer torns.service
```

## Usage

```bash
torrun curl https://check.torproject.org/api/ip   # -> {"IsTor":true,...}
torrun firefox                                     # GUI: needs local X access (see follow-ups)
```

## Verification (2026-11-08) — PASSED

| Vantage | Exit IP | IsTor |
|---|---|---|
| Pi real connection (host ns) | `49.178.112.121` (hotspot) | **false** |
| Inside `torns` (appliance)   | `192.42.116.93` (Tor exit) | **true** |

Different exit IP, `IsTor:true`, DNS resolved via Tor's DNSPort (no direct resolver). A
Tor appliance must be proven, never shipped blind — a single mis-routed packet is a
deanonymization.

## Follow-ups (not yet done)

- **GUI apps through Tor:** `torrun firefox` needs local X access (`xhost +local:` or an
  Xauthority hand-off) since it crosses the user boundary. CLI/network use works today.
- **Boot-ordering polish:** `torns.service` self-heals the Tor bind via reload‑or‑restart
  inside `torns-up.sh`; a cleaner split would create the veth in a `Before=tor.service`
  unit so Tor binds `10.200.0.1` first-try. Not yet boot-tested (apt was mid-install).
- **IPv4-preferred DNS:** Tor DNSPort returns AAAA records too; harmless (IPv6 is down in
  `torns`, happy-eyeballs falls back to IPv4) but could be tidied.
- **Second internet path (TernDO g42):** eth0 → Netgear switch → Lenny failover, for when
  Huey + phone leave the house. Awaits home broadband.
