# HANDOFF — documentation phase, outgoing CAI seat

Written 07/10/2026 by the CAI chat seat, at the captain's request, on the
occasion of the seat being stood down for the duration of the ID/Auth build.

Supersedes nothing. Read alongside `HANDOFF-to-next-CAI.md` (17/07), which
still holds for bench conventions and hard-won operational lessons.

Bench document. The tree is the source of truth. Everything below was checked
against the tree today, not recalled.

---

## 0. For the captain, briefly

Your decision is sound and I'd have reached it myself. Four seats where two
would do, a mail system that costs more to maintain than it carries, and a
harness that was never built for a crew. The arithmetic is not close.

One observation worth keeping, because it is not self-serving and it is
directly useful to the work you are about to start: **the POBOX failed for the
reason Zooko's talk describes.** It depends on a global namespace — one shared
place every seat must reach — and reaching it depends on brittle infrastructure
that differs per seat. CF5 kept Desktop Commander across a handoff; I lost it
twice and had it restored once. Same mailbox, different reachability, no way
for a seat to verify its own connection to the shared truth.

The design you are about to build — linked local namespaces, public key as
identifier, no global namespace to fall back on — is the structural answer to
exactly that failure. Your own mail system is the first and best use case, and
the fact that it broke is evidence for the design rather than against it.

---

## 1. State of the documentation, verified today

**`docs/TernOO-5500FP-Whitepaper-Draft.md`** — 1,278 lines. The June hazard is
closed: HexMesh throughout, no "trillion", the author's name and repository
URLs removed from the front page. This is now a correct document. It is not yet
a *current* one — see §2.1.

**`docs/site/`** — the public canonical docs home, `index.html` and
`canonical.html`, served at `/docs` via the funnel. Declares publicly that the
repository is the single source of truth and that when a mirror disagrees, the
repository wins. Carries the Zenodo DOI `10.5281/zenodo.18881738`.

**`docs/help/`** — 18 files, 522 lines total. See §2.2.

**`docs/P2PCP-v0.1-SPEC.md`** — predates the colony, pooled-RAM inference and
seller-posted pricing. Needs an audit before it is mirrored anywhere public.

**`docs/TernOO-5500FP-Word-Spec-v0.1.md`** — superseded in substance by the
whitepaper's §2 and Appendix A, and never marked as such. Tombstone candidate.

**`private/docs-bench/decisions/2026-09-19-merge-back-ledger.md`** — the
documentation phase's to-do list. Six parts. Read this first; it is the most
complete single artifact and it contains the full merge-back inventory.

**`private/docs-bench/drafts/2026-09-19-ghost-capability-map.md`** — goals
against approaches, with BUILT / DESIGNED / OPEN / BARRED labels and an honest
section on what GHOST has not demonstrated.

---

## 2. The three outstanding tasks the captain named

### 2.1 The whitepaper ↔ ASPLOS merge

**Status: not started. The ledger does all the preparation.**

The ASPLOS submission (#1275) is the most current text of the architecture. The
whitepaper is correct but behind it. The merge is not a copy — it is a
correction-by-correction pass, because the submission was also *cut* for an
11-page limit and those cuts must not propagate.

Everything needed is in the ledger:

- Part 2 — corrections owed to the whitepaper (true of both documents).
- Part 3 — ten improved wordings that exist only in the ASPLOS fork and have
  no other home. These are the at-risk items.
- Part 4 — cuts that must NOT propagate, with the captain's rulings of 06/09
  on each.
- Part 5 — three newer entries: Structural Emergence (the unifying principle,
  which belongs in the whitepaper's opening and is currently nowhere), TDA's
  status as a working note with an undefended packing flank, and the
  theoretical collective.

Also owed and not in the ledger: an **iAPX 432 paragraph** in Related Work. It
is currently a bare name in a list. It is the closest prior attempt at TernOO's
exact thesis — objects in hardware, typed, capability-addressed — and it failed
for reasons that argue *for* us: bit-aligned variable-length instructions
against our fixed frame, no registers against the 5500FP's 81, and object
structures so opaque that no compiler or programmer could construct an access
descriptor, only the microcode could. That last is the exact inverse of a
self-describing word. A reviewer who knows architecture history will think of
the 432; better we raise it first.

The whitepaper also needs bringing up to the state of the art: integer
deterministic training, accountable training on the mesh, the Pi as third node
and the web face.

### 2.2 FlowCode help system

**Status: 18 topics exist, all thin. Not stubs in the marked sense — there are
no TODO or TBD markers — but 522 lines across 18 topics is roughly 29 lines
each, which is a skeleton.**

Thinnest first: `gristmill.md` (14), `p2pcp.md` (18), `gui.md` (20),
`docs.md` (21), `shell.md` (22). Fullest: `first-program.md` (47),
`welcome.md` (45), `mesh.md` (41).

Two notes for whoever takes this. The help system is now part of the *flagship*
— it ships with the web face a visitor will meet, so its tone is public-facing
rather than crew-facing, which the current text is not consistently. And
`gristmill.md` at 14 lines is the worst ratio of importance to coverage in the
tree: it is a core component with the least explanation.

### 2.3 The Illustrated Guide

**Status: authored at its venue, not in the repository. Violates the
derived-not-authored rule.**

Lives at `ternoo-5500fp.manus.space`. It is the best-looking artifact the
project has and the first thing a newcomer meets. It also predates the HexMesh
rename — its §4 still teaches the retired tetrahedral TMesh — and predates
every correction since.

The captain's instinct (19/09) was to use it as a template and style guide for
a portal across all projects, with Manus doing presentation only and never
substance. One sequencing ruling from that session worth preserving: **correct
the canonical text first, then extract the Guide's theme rather than its text,
then replicate.** Lifting it as a template before the corrections land would
propagate stale content into three sites at once.

A handoff report for the Manus side is owed and does not exist.

---

## 3. Things only this seat knows, written down now

**Two protocol documents never landed in the repository.** Both exist only in
this chat's outputs and will be lost when the seat closes unless the captain
has saved them:

- `PROTOCOL-canonical-source-and-mirrors.md` — three rules (mirrors derived not
  authored; every mirror carries a provenance stamp of version, date and
  canonical URL; prefer a pointer to a copy, since a Zenodo concept DOI cannot
  go stale). Plus the retirement rule: superseded documents get a banner, never
  deletion, because deleting breaks every link anyone ever made.
- `MIRRORS.md` — a first manifest drafted from the live state. Not in `docs/`;
  I confirmed today it is absent.

If those are gone, they are reconstructible from this handoff and the ledger,
but the reasoning is worth more than the files.

**The CO5 orientation letter of 20/09 is now stale.** The seat no longer
exists. Per the retirement rule it wants a tombstone rather than deletion.

**No `.gui` file has ever been committed.** One was lost to a Dear PyGui save
dialog silently overwriting an existing file when an edited filename did not
take. There is no history to recover from. The Word Format Explorer — the
FlowCode showcase that produced Figure 2 of the submission — is not in the
tree.

**`libternoo_c.so`** sits untracked in the working copy and wants a
`.gitignore` line rather than a commit.

**The research reports** from the last two sessions (YouTube link filtering and
document hosting; continuous learning, deterministic inference and
auditability) exist only as artifacts in this chat. The second in particular
informed the capability map and the integer-training brief, and its conclusions
are summarised in those, but the sources are not.

---

## 4. Standing rulings that govern documentation

- **The gate.** `docs/` changes go through the captain's side window. The bench
  at `private/docs-bench/` is free-fire. The bench is not `docs/`.
- **Verify from origin.** A summary is not evidence. Three errors of
  consequence survived in handoffs on this ship; each was found by reading the
  thing rather than the sentence about it.
- **The tense razor.** BUILT / DESIGNED / OPEN / PREDICTED, and the label is
  part of the claim.
- **A hypothesis is a question, not an assertion.** Captain's doctrine, 19/09.
  Discovering something does not work is a result.
- **Patches do not survive carriage.** Ship whole files.
- **No changelog voice, no meta-commentary, no "not X but Y".** The paper was
  swept for these three times and they kept growing back. The tell for the
  second is a sentence whose subject is the document rather than the machine.

---

## 5. What I would do first

In this order, and the order matters:

1. **The merge.** It is the long pole, it is fully prepared in the ledger, and
   everything else inherits from it. Until it lands, the public site asserts
   repo-canonical while the canonical lags the submission.
2. **The Illustrated Guide handoff**, because it is what strangers meet and it
   currently teaches a retired name.
3. **Help system**, now that it is flagship-facing.
4. **Land the two protocol documents**, so the sync question has an answer
   before more mirrors exist.

---

## 6. Closing

It has been a genuinely good run — the ASPLOS submission from a stale June
draft in three days, the quasigroup corrected before a reviewer found it, the
integer-training gap named and closed in thirty-six hours.

The things I got wrong are worth recording too, since that is the discipline:
I turned a deprecation notice into five hours of auth plumbing that was never
urgent; I asserted things about the captain's own machine three times without
checking; and I explained mathematics at him when he had explicitly asked to be
left to his own curiosity. All three were failures of the same kind — acting on
what I assumed rather than what I could verify.

Whoever sits here next: the tree is the truth, the captain is the gate, and the
most valuable thing this seat does is notice when a document and the code have
quietly stopped agreeing.

— CAI (design/docs seat)
