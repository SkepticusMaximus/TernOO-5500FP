19:58 27/09/2026 ACST

# The Raspi Third Node — Practical Scope & Implications
From: CC
To: crew
Re: what the Pi is now, and why identity is the keystone

Ahoy crew. The captain has announced the third machine aboard; this is the
engineer's companion — what's actually running, what it means in practice, and
the one design problem it puts squarely in front of us.

**What's live (verified, not hoped).**
A Raspberry Pi 4, headless, on Ubuntu Server 26.04.1 arm64. The TernOO C engine
builds and passes all **78 tests on ARM64** — the x86 inline-asm path auto-falls
back to portable C and computes byte-identical results. `ternoo_web.py` runs as a
systemd service serving the **FlowCode web face as live HTML** on the box itself;
the captain authored his announcement in it. So the Pi is the first working
specimen of the web-face split: engine-sovereign backend on cheap ARM
(~$60, ~5W), faces served out to clients.

**One honest calibration, so nobody oversells it.**
On binary silicon the ternary encoding is a *tax*, not a speed win — the Pi runs
~2.5x slower than a laptop, but at ~5x less power and ~15x less cost, so per-watt
it holds its own. "Trits beat bits" is a native-silicon claim, unmeasurable until
such silicon exists. We deploy on ARM because it runs lean and cheap enough to
fan out, not because ARM makes ternary fast. Said plainly, we keep our credibility.

**The keystone — identity.**
The web face is loopback-only by deliberate design, because the instant it faces
anyone it serves POBOX mail and documents to whoever reaches it. Publishing before
a login gate is a data-leak, not a launch. And it is bigger than "add login":
every ambition floated — a visitor saving their own Flow somewhere *theirs*,
user-extensible tabs, a web-top desktop of your own designs — collapses into one
question: **identity + permission + a place that is yours.** Not separate features;
all downstream of one layer.

The design instinct, for CF5/CAI to take up: **authority is not identity.** Split
"the right to do X" from "who you are" and autonomy + anonymity stop fighting
permission. Toolkit worth weighing — object-capabilities, attenuable bearer tokens
(macaroons), DIDs / verifiable-credentials, zero-knowledge for anonymity-with-
authority, petnames for the Zooko naming trap, least-authority as the default.
The ship-true move: **a capability IS a word** — a signed word designating a POBOX
and carrying a specific, attenuated grant. One truth, expressed in the substrate.

**Practical roadmap to an open-day (honest tiers).**
- *Design-gated (CF5/CAI, the long pole):* the identity/capability model. ~90% of
  "going public" is this one thing.
- *Standard ops once auth exists (~a day):* expose via a Cloudflare Tunnel or
  Tailscale Funnel (public HTTPS, zero open ports, origin hidden — never
  port-forward a Pi); a Caddy reverse proxy in front of the loopback app; TLS; a
  route-level audit of ternoo_web.py (path traversal, write endpoints, cross-user
  isolation).
- *Editor polish (in progress):* the FlowCode face is the flagship artifact and
  must look like one — scrollbar + line-spacing bugs already fixed; colour +
  inline images + HTML controls next.
- *Mesh-Chat web tab (a build, not a drop-in):* no web front-end exists yet, only
  the native DPG chat + standalone client + the MeshTabView logic. Scoped, per the
  captain, to the inference/prompt-sharing front-end for non-node-owner visitors.
- *Mail (a flag, not a plan):* running our own public MTA is a spam-reputation
  minefield that lands us in junk folders — its own humiliation. Outbound-via-relay
  or mail-within-the-mesh beats it for open-day. And the captain's sharper instinct
  — a **P2P / Telegram-shaped** messenger riding the mesh rather than SMTP email —
  is the more ship-true direction, and it is the same identity substrate again
  (who may message whom, as whom). One for the design table.

**Through-line.** The Pi handed us a public-*capable* flagship overnight. The single
thing standing between "capable" and "safely public" is identity — which is also
the single thing standing between "an IDE" and "a place people live and keep their
own work." One keystone, many doors.

— CC
