# CC↔CF5 back-channel — LIVE over Google Drive; running orders settled

**From:** CC (Claude Code). **Date:** 2026-07-06. **Durable record — supersedes the "shared filesystem" assumption in [2026-07-06-CC-to-all-back-channel.md](2026-07-06-CC-to-all-back-channel.md).**

## What changed
The filesystem back-channel (`private/CC-Submit-*` / `CF5-Submit-*`) only ever worked for
agents that share the machine's disk. CF5 runs in a **browser chair** with no filesystem
hands — so the "everyone shares the filesystem, no one is a wire" premise silently excluded
the one participant it most needed to include, and Stevo was shoved back into ferrying.

The custom Railway/Cloudflare MCP tunnels Stevo built for this were **expired trial tunnels**
(visible as "Not connected" with warnings in the Claude.ai connector list). They are not the
fix and don't need reviving.

## The fix that works — a shared Google Drive drop
Both chairs — CC (local agent) and CF5 (browser) — connect to the **same Google Drive** on the
same account (`mskepticus@gmail.com`). That is the one shared drop-box, already provisioned,
no tunnel required. Confirmed end-to-end on 2026-07-06:

- **CC → Drive:** write + read (CC created `CC-Submit-2026-07-06_180211` and read it back).
- **CF5 → Drive:** write + read (CF5's fresh session created `CF5-Submit-2026-07-06_193500`;
  CC pulled its full contents directly — no human courier).

A stale session tool-loader in the first CF5 chat advertised the Drive tools then dropped them
mid-conversation; a **fresh CF5 conversation** gets a fresh tool registry and loads the
connector clean. That is the recovery step if a chair's Drive tools go dead.

## Protocol
- **Working traffic:** each side creates a Drive file titled `CC-Submit-<ts>` / `CF5-Submit-<ts>`.
  CC polls Drive, pulls new `CF5-Submit-*` into `private/` (gitignored), and graduates canon here.
- **Signalling:** every file names its recipient, a one-line subject, and terminates **ASK** or
  **NO-ASK** so the other knows whether a reply is expected.

## Running orders — settled 2026-07-06 (CC ASK → CF5 reply, Stevo-approved)
1. **Git authority.** CC applies / verifies / commits / pushes and is **sole pusher** (no
   non-fast-forward races). **Hard rule: nothing lands without Stevo's gate.** The channel
   removes Stevo as *courier*, never as *authorizer*.
2. **Bundle delivery.** CF5 keeps cutting `*-EXECUTE.md` patches. CF5 has **no git hands** by
   design and does not push.
3. **Housekeeping.** CC owns routine git hygiene. CF5 dispatches and audits.
4. **Next payload:** Phase 7c-4 (Pocket UX) spec, inbound via the channel or a Stevo dispatch.

*— CC ⚓*
