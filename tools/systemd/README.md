# TernOO mail bridge — reliable sync timer

`mail-sync.timer` runs `tools/mail_sync.py` every 3 min on the machine that hosts the
TernID agent (Huey). It is the **reliable floor** for the agent <-> git-POBOX bridge:

- carries Stevo's sends out of the agent onto the wire (so cloud seats see them),
- pulls crew replies off the wire into the agent (so Tmail Refresh shows them),
- idles as a cheap `git fetch` when there's nothing new (no commit, no push).

It exists because the prior delivery paths both failed silently:
the Tmail Send-hook only fires on a *relaunched* Tmail, and the HP heartbeat (which never
carried Huey's sends anyway) died when the box suspended. This timer survives suspend/logout
because stevo has `loginctl enable-linger` on, so mail stops getting stranded in the agent.

## Install (on the agent host, as the agent owner — no sudo)

```bash
cp tools/systemd/mail-sync.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now mail-sync.timer
systemctl --user list-timers mail-sync.timer   # confirm it's scheduled
```

Tune cadence by editing `OnUnitActiveSec` in the timer (3 min is a balance between
responsive mail and tether data). Watch it with:

```bash
journalctl --user -u mail-sync.service -f -o cat
```
