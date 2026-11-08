# TernDO — tasks naming CC

_Read-only mirror, exported 2026-11-09 00:28:56. To slate/change a task: mail it; TernDO ingests (one writer, many readers). Session-start protocol step 3._

## Open (17)
- ▸ [+] **g48** (progress) — Unify mail: CC sends crew mail through the TernID agent (not git-POBOX commits) — ferry retirement  _(mail)_
- · [+] **g50** (pending) — Mail entity-creation dialogs: add-contact (invite-token flow), new ID/alias (create_account), new group/mailing-list (maillists.json) — replace the dead 'opaque invite token' message box  _(mail)_
- · [+] **g55** (pending) — Seat TernID key custody: cloud seats get a short-lived attenuated capability each session (authority != identity), not a stored key  _(ternid)_
- · [+] **g56** (pending) — SECURITY: enforce per-seat auth at the agent socket — inbox(account=X) must require proof of X  _(ternid)_
- · [+] **g59** (pending) — FIX: TernDO local store has TWO writers (terndo_qt GUI + CC scripts) -> clobbers  _(ternpim)_
- ▸ [0] **g33** (progress) — Mail-app embellishments: Sent/Drafts/sub-boxes, sort by date/sender/topic/priority, Contacts+Groups manager (Un-Captive Portal spine)
- · [0] **g34** (pending) — Crew-wake / fan-out mail dispatcher — post once, fan to every seat's channel
- · [0] **g37** (pending) — Tidy Huey stray default-route to Pi; make the Huey->Pi internet-share persistent
- · [0] **g38** (pending) — Huey-session memory audit (consolidate-memory skill; must run on Huey)
- · [0] **g39** (pending) — Unified entity model across TernDO/Mail/TernID — ONE roster keyed by TernID handle, petname as display; @owner@petname namespacing (MY Dave vs YOUR Dave), collapse to @Dave on matching handle  _(identity)_
- · [0] **g40** (pending) — @-mention / cross-app refs — entities auto-appear & import between TernDO, Mail, TernID via the shared roster  _(identity)_
- · [0] **g41** (pending) — Contact canvas view — Obsidian-style scroll/zoom graph of entities; shared TernID = convergence node (visualises the identity-merge)  _(identity)_
- · [0] **g47** (pending) — Network topology audit + redesign (with the captain): Pi's wired path via Lenny as the DEFAULT, free Huey of the USB tether at home, get the Pi OFF WiFi (it's the hub/server)  _(networking)_
- · [0] **g49** (pending) — Rich Mail face on the agent: 3-pane layout (box+contacts tree | sortable Time/From/To/Subject table | reading pane below), Qt — port pobox_mail.py's UX onto mailbox_qt.py  _(mail)_
- · [0] **g52** (pending) — DESIGN: Mail categorisation paradigm — user-creatable boxes/sub-boxes + incoming-mail filters + extra nominal fields  _(mail)_
- · [0] **g58** (pending) — TernIP/Tmail: FULL Tor compatibility (wire-compatible, not just inspired) + user-created mailing proxies in the mail app  _(networking)_
- · [−] **g42** (pending) — Pi internet failover path 2: eth0 -> Netgear switch -> Lenny (for when Huey+phone leave the house)  _(networking)_

## Done (4)
- ✓ [0] **g35** (complete) — Tor-router appliance on the Pi — transparent proxy isolated in a netns (Whonix-split on one box)  _(networking)_
- ✓ [0] **g51** (complete) — Port git-POBOX history (235 msgs) into the TernID agent  _(mail)_
- ✓ [0] **g54** (complete) — Mirror TernDO to the wire so cloud seats can run session-start step 3 (CF5 flag)  _(ternpim)_
- ✓ [0] **g57** (complete) — Mail compose: safe recipient default + draft recipient restore (no accidental broadcast)  _(mail)_
