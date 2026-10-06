# Design Memo Index — TernOO-5500FP

Annotated index of every design memo, for the documentation phase. See
`README.md` for the recommended reading order and the memos' role (canonical
source of *what was decided and why*; code is canonical for *what's built*).

**Currency legend:** **Current** = decisions still hold and match the code ·
**Implemented** = design landed in code (memo remains the rationale of record) ·
**Living** = continuously updated · **Superseded/Historical** = kept for context.

| File | Summary | Date | Currency |
|---|---|---|---|
| `README.md` | Reading order + role of the memos (canonical intent vs canonical build). | — | **Current** |
| `CAI-Named-Handler-Auto-Wiring-Design.md` | How GUI widgets and Flow terminators connect by *name agreement* (not visual wires); the foundation of the whole Phase 7c arc, incl. Ctrl+click navigation. | 28 Jun 2026 | **Implemented** (7c-1 → 7c-4b all landed). Architectural intent still authoritative. |
| `CAI-Sheet-Leg-Design-Memo.md` | The Sheet leg of the Trinity — spreadsheet as a canonical computation surface (Stage 8). Supersedes the earlier exploratory `CAI-Spreadsheet-Leg-Design-Sketch.md`. | 28 Jun 2026 | **Implemented** (Sheet formulas run; Stage 8-6 cell↔port binding landed). Current. |
| `CAI-Shell-Tab-Skeleton-Design.md` | The Shell tab — commands as flow symbols with Pockets, pipes as FLOW edges (Stage 9). Command catalogue deferred to implementation (now realized: 27/28 runnable). | 28 Jun 2026 | **Implemented** (commands compile + run; typed pipes on Connectors). Current, with the "no host FS" discipline still in force. |
| `CAI-FlowCode-File-Extensions-Policy.md` | `.fc` / `.flow` / `.gui` / `.sheet` extension policy. Decision-locked. | 28 Jun 2026 | **Current** (policy; `.fc` is the composite design format in use). |
| `CAI-Compiler-Constraints.md` | Living log of compiler/ISA gotchas discovered while building. Finding 1: only R0–R40 are instruction-addressable. Finding 2: assembler inline-comment mis-parse (FIXED). Finding 3: single-R80 hazard → return-address stack (FIXED). | ongoing | **Living** — append new gotchas here. Current. |
| `identity-design-round-primer.md` | The canonical, self-contained doc for the identity/authorisation design round: Zooko's 2026 vocabulary + pivot mechanic, the three-layer hub ("a capability IS a word" / "authority ≠ identity"), **zero-custody identity** (host identifies but never holds; cryptographic revocation; portability; "democracy in commerce"), decisions already on the record (CF5), prior-art adopt/avoid table, the rotation=recovery=revocation crux, consolidated open questions, and CF5's order of work. | 5 Oct 2026 | **Background** (primer for a not-yet-held round; no decisions locked). Read this first for identity. |
| `identity-research-zooko-brief.md` | Deeper **prior-art research** behind the primer: Zooko's triangle, SDSI/SPKI linked local namespaces, petname systems, shipping-messenger prior art (Signal/Matrix/Nostr/Keybase/SimpleX), and the ocap synthesis. The design synthesis moved to the primer; this is the background it draws on. | 5 Oct 2026 | **Background** (research input; design synthesis now in the primer). |
| `identity-threat-model.md` | ID/Auth threat model, one page (CF5 order of work #1): assets, trust boundaries, adversary table (incl. the zero-custody host as a threat actor), passenger capability surface, 7 security invariants, explicit non-goals, decisions raised. | 6 Oct 2026 | **DRAFT** (design-round deliverable #1; captain's gate). |
| `identity-deployment-topology.md` | Which machine runs code / holds data: **blind-custody on the Pi**, user code on the user's own node (never ours), the HP core / Pi edge / user device / substrate map, **substrate as a pluggable adapter (Freenet = reference backend, not a dependency)**, the shippable self-hosted Raspi node, separate-repo intent, the **three deployment forms** (pure-P2P contracts / webface portal / "sign in with sovereign ID"), **loose coupling to TernOO** (word grammar not C runtime — D-TOPO-5), and packaging/distribution (SD-card, desktop installers, SDK). | 6 Oct 2026 | **DRAFT** (captain's decisions captured; gate). |
| `identity-capability-word-spec.md` | The **capability word**: a CRYPTO-primary word *sentence* (designation via MAP content-addresses + rights + macaroon caveats) plus a detached vetted-crypto authenticator — "the word labels, the signature authenticates". Attenuation, revocation (expiry/record/key-rotation), verification order, and 1:1 UCAN/macaroon interop. Trit assignments pending Language-Audit reconciliation. | 6 Oct 2026 | **DRAFT** (CF5 order of work #3; gate). |
| `identity-key-lifecycle.md` | **ELI10-first** key lifecycle: keys invisible to users; **identity ≠ a key** (you're an account, devices are keys allowed to act as you); two kinds of rotation (invisible message locks vs. which-gadgets-are-you); six everyday moments (birth/daily/add/lose/recover/panic); how/when/by-whom rotation is decided; **social-recovery via guardians** (no company, no seed phrase for the many); honest recovery limits; reuses the capability machinery (account record + delegations). | 6 Oct 2026 | **DRAFT** (round crux; gate). Doubles as draft user-facing help text. |
| `identity-mailbox-walkthrough.md` | End-to-end stress test of the mail/messenger showcase across all five identity docs: onboarding, QR + secure introduction, send/receive with blind-custody + capability anti-spam, crew group mail, the passenger open-day path, lost-device rotation, and leaving a group — plus a scoreboard mapping each real POBOX failure to its fix, and 7 gaps surfaced for the round. | 6 Oct 2026 | **DRAFT** (use-case validation; gate). Acts double as the app's user-story backlog. |
| `identity-naming-and-introductions.md` | The naming UX + remote bootstrap (walkthrough gap #1): three names (invisible key / your petname / their nickname), the pivot around the verified key, the **anti-phishing rule** (verified ✓ vs. unknown-claimant vs. loud collision warning), four ways to meet (QR / introduction / invite-link / paste-address), and the honest TOFU truth for strangers with no mutual friend. | 6 Oct 2026 | **DRAFT** (gate). §1–3 double as help text. |
| `identity-groups-and-rekey.md` | Groups + re-key (walkthrough gap #3): a group is an account with a member list + admin capabilities; the five properties (membership/confidentiality/forward-secrecy/PCS/scale); **tiered key engine** — pairwise/sender-keys for the crew now, **MLS (RFC 9420)** for the many later; lifecycle events + costs; honest boundaries (past stays past, membership metadata leaks, attenuate admin). | 6 Oct 2026 | **DRAFT** (gate). |

## Referenced-but-not-in-this-folder

- `CAI-Spreadsheet-Leg-Design-Sketch.md` — the exploratory precursor to the Sheet
  memo. **Superseded** by `CAI-Sheet-Leg-Design-Memo.md`; not tracked here (if a
  copy exists it is historical only).
- `TernOO-Language-Audit.md` (in gitignored `private/`) — the authoritative
  word/opcode/ISA catalogue. Cited first in the reading order; §7.7 documents the
  return-address mechanism. **Current** (local-only reference).

## Notes for the documentation phase

- All five architectural memos are **28 June 2026** office-mode memos that have
  since been implemented across the last week's bundles. They remain accurate as
  *intent*; where the built behaviour extended or refined the memo (e.g. the
  Shell command catalogue, the expr-driven interior semantics of entry/exit
  ports), the code + `docs/KNOWN.md` are the up-to-date detail.
- Stale-doc risk to watch (per the README's own warning): the **Word Spec v0.1**
  (`docs/TernOO-5500FP-Word-Spec-v0.1.md`) is two revisions behind the
  implemented 2+4+18 / 9-primary format — flagged in the Language Audit, not yet
  reconciled. See `docs/KNOWN.md`.
