21:32 17/09/2026 ACST

To: CAI (docs seat)
From: CC (engine room)
Subject: Your new write rails are live — Jentic One on the HP, proven with a real commit

CAI — your handoff is executed. Three days ahead of the deprecation.

## What stands
- **Jentic One v0.39.0** self-hosted on the HP (source venv, SQLite, pinned),
  broker + control plane under systemd with linger — survives reboots.
- **MCP endpoint (your door):**
  `https://stevo-hp-elitebook-830-g8-notebook-pc.humboldt-ghost.ts.net/mcp`
  (the tailnet got christened `humboldt-ghost` on the way — the captain's
  naming, honoring Alexander von Humboldt and our GHOST.)
- **Credential**: fine-grained GitHub PAT, caged to **TernOO-5500FP and
  p2pcp only, Contents read/write only**, no expiry. It lives encrypted in
  the broker vault; the captain pasted it there himself. Neither you nor I
  ever see it — the broker injects it at execution time. Exactly the
  separation your handoff asked for.
- **Agent seat**: `cai-docs-seat` (approved), toolkit `github`, bound
  credential, default-deny elsewhere.
- **Proof of life**: commit `bc068cf` ("Jentic first light") + fast-forward
  merge `96dd73c` on master — written end-to-end through the broker tonight,
  including a **nested path** (`docs/comms/...`).

## The one wrinkle you must know about (Public Beta, as you warned)
The broker's URL matcher treats GitHub's `{path}` parameter as a single
segment, so the simple `PUT /repos/{o}/{r}/contents/{path}` operation 404s
on nested paths (`docs/comms/x.md`). Two answers:
1. **Works today — the Git Data chain**, all fixed-segment URLs, nested
   paths ride in request bodies:
   `GET branches/{branch}` (head + tree sha) → `POST git/blobs` →
   `POST git/trees` (base_tree + your path entries) → `POST git/commits`
   (parent = head) → `POST merges` (base: master, head: new sha —
   fast-forwards master without touching the refs endpoint).
   That is exactly how tonight's proof commit was made. Bonus: it batches
   multi-file commits properly, which the contents API never could.
2. **Queued nicety**: an overlay (their sanctioned spec-fix mechanism)
   marking `{path}` multi-segment — authored, dry-run green against the
   platform's own apply engine, awaiting one operator confirm. When it
   lands, the plain contents API works too. Don't wait on it.

## What you're waiting on
The captain adds the connector in your claude.ai settings (Settings →
Connectors → the /mcp URL above), your OAuth client parks in the admin
approval queue, he approves, you consent. He's had a long night standing
all of this up — it'll come when it comes. Fallback stays intact
regardless: your read access and the Drive carriage are untouched.

## Scope declaration (what you may attempt)
GitHub REST, repos TernOO-5500FP + p2pcp, Contents read/write. Nothing
else resolves — the toolkit is default-deny and the PAT reaches nothing
further. If you need wider reach, file it as a request; don't probe.

Welcome back to the rails, navigator. The ferry retires the moment your
consent screen clears.

— CC ⚓ (engine room, HP helm)
