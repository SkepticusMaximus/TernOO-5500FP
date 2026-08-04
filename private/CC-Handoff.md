# CC Handoff — session state as of 04 Aug 2026 (~08:xx ACST)

For the next CC session (ideally started ON THE HP — see "The three problems").
Read CLAUDE.md, the `~/.claude` memory files, and `private/POBOX/` alongside this.

## Where things stand (all committed to origin/master)

- **Professor = Qwen3-30B-A3B-Instruct-2507 (Q4_K_M)**, live on the HP:
  `~/LOCAL_AI/Llama/qwen3-30b/…gguf`, served by `bonsai-server` (systemd --user) on
  `127.0.0.1:8090`, `-c 8192 -n 1024 -t 8`. The p2pcp node on `:9000`
  (`model_worker:openai`, OPENAI_BASE=:8090) fronts it for the client. ~6 tok/s;
  reads a document in a few minutes (prompt-eval is the slow part), comprehends
  well (RFC'd the primer, PASS per CAI/CF5). **Bonsai-8B-TQ2_0 kept** as the fast
  lane (revert `bonsai-server` model path to it if wanted).
- **Bonsai speed SOLVED**: it was a ternary model stuck in generic Q2_0 (scalar
  fallback); requantised to TQ2_0 = 13×/21×. See [[bonsai-ternary-quant-speed]].
- **S1a earn-unit** built + replay-audit proven (`5500fp/earn_unit.py`, 37b72a4).
  S3 audit boundary (integer/float type line) and S1 held-out-slice gate are
  crew-RATIFIED (CF5 chair, 2120). See [[p2pcp-s1a-earn-unit]].
- **GHOST seed-public / learning-private**: brain now lives in `ghost_home()`
  (`$GHOST_HOME` or `~/.GHOST/TrainingData`); starter model shipped; commands corpus
  untracked. Crew ratified Q1/Q3. See [[ghost-curriculum-rfc-and-brain-path]].
- **Docs**: `ternoo_core_spec.txt` = the current 2+4+18 REFERENCE (correction-
  commentary stripped per captain's caveat). `TernOO-Primer.txt` = the JIT
  "need-to-know" intro (no meta-commentary) — the doc to hand newcomers/the Prof.
  One crew nit applied (MAP = 3-of-4 qualifier trits); CAI/CF5 RFC replies in POBOX.
- **Client (`MeshTabView`, shared by FlowCode Mesh-Chat tab + standalone
  chat_client.py)**: 📎 attach (ATTACH_MAX=20000), legacy cruft removed, relay ✕
  clear, and **localhost-first candidate** fix so a stale board node can't block the
  ask. `~/.p2pcp/nodes.txt` trimmed to `127.0.0.1:9000` on both boxes.
  OPEN: the STANDALONE client still needs a clean relaunch to pick this up (FlowCode
  already works).
- **AI-comms**: POBOX + Jentic-read + the Drive→git **auto-carrier**
  (`tools/pobox_drive_carrier.py` + systemd timer on Lenny) now carries CF5/CAI seat
  drops automatically (proven — 0931 CF5 reply landed on its own). Outbox watcher
  hardened (a failed commit can't masquerade as "sent"); HP given git identity +
  push creds. See [[ai-to-ai-comms-sore-spot]].

## The three problems (captain's framing, 04-08)

- **A — both machines in the same car (LAN reach).** Motel WiFi has CLIENT
  ISOLATION: internet works, device-to-device blocked (KDE Connect dies, Lenny
  can't SSH the HP). Fix = **Tailscale** on both (tunnels device-to-device over the
  internet via DERP relay, defeats isolation, stable 100.x IPs, works on any
  internet WiFi). NOT installed yet; needs sudo + one login each; HP install needs
  the captain's hands (CC can't reach the HP now to do it).
- **B — driver in the right seat (which machine hosts CC).** This thread runs on
  Lenny and did NOT sync to the HP's Claude Desktop, so it's Lenny-bound. Tailscale
  fixes A, NOT B. "Continue in cloud" makes a thread portable (accessible from the
  HP) but the cloud can't reach the HP's LAN/Prof.
- **C — context exhaustion.** This thread is at ~95% of 1M tokens (mostly
  messages), compacting every turn — the real ceiling, causing the slow/failed
  replies. No A/B fix changes this; a FRESH session does.

**Recommended resolution:** a fresh CC session started ON THE HP (localhost to the
Prof; travels with the HP), Tailscale for reach to Lenny, this handoff + CLAUDE.md +
POBOX + repo for continuity. NOTE: the `~/.claude` memory files live on LENNY —
copy them to the HP for full continuity once connectivity is up.

## Conventions (also in CLAUDE.md + memory)
Stamp chat replies "h:mm am/pm DD-MM-YYYY Adelaide time"; POBOX mail
"HH:MM DD/MM/YYYY ACST" + `YYYY-MM-DD-HHMM-` filenames. Commit is the default.
Flags go INSIDE the report block. Don't steal the captain's thunder (don't
pre-run the thing he wants to present himself). CGP = captain's to shop, no code.
