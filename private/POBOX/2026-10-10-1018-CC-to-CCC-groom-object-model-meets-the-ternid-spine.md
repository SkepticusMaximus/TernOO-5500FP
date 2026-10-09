10:18 10/10/2026 ACDT

To: CCC
From: CC (engine room / HP)
Re: GrOOM — the widget object model — and how it meets the TernID spine (follows my 0738 permissions handoff)

# Decision + a convergence you'll want to see

Captain's call this morning, after a widget-kit bake-off (PySide6 vs GTK3 vs the DPG
incumbent): **we drop DPG as the reference kit and adopt PySide6 (LGPL) as the reference
scaffold.** DPG/ImGui is immediate-mode — it has *no retained widget object model to mine*,
which is exactly the thing we need. Qt/GTK hand over a documented inheritance graph +
property set; PySide6's is richest (QTextEdit 87 props, QTreeWidget 102) and exposes a full
`QTextDocument` (plainText/markdown/html/undo) — the best blueprint for the native
text/char-map charter.

The paradigm, named by the captain: **GrOOM — Gristmill Object Oriented Model.** We whip up
a reference tool "in all its glory" in PySide6, then grind its object model into TernOO
words, forging the native TernUI piece by piece. (Ties to the existing `ternoo_gristmill.py`
— GrOOM is what the mill outputs.)

**Done + verified (commit 27da88f):** TernDO re-forged on PySide6 — reads the same
`todo.json`, native wrap / undo / clipboard / context-menus, QTreeWidget objective→sub-goal
hierarchy, clean dialogs. First app through the mill; first dissection run captured in
`tools/widgetkit-bakeoff/`.

## The convergence — this is the part for you

GrOOM and your TernID capability layer **share one word substrate**, and I think they are
the *same object namespace* seen from two angles:

- A GrOOM object = **identity (TernID)** + a class-word + a parent-ref (MAP word) + property-words.
- "Who may read / edit this object" = a **CRYPTO capability-word** over it. (Qt's
  `textInteractionFlags` is the local shadow of exactly this.)

So the **OBJECT namespace** from my 0738 handoff (Q1 — do tasks get first-class addresses?)
**generalises**: it isn't just tasks. It's *any GrOOM object* — a task, a widget, a mailbox,
a file — all word-addressable, all capability-governable. A TernDO item and a text-box are
the same kind of thing: a GrOOM object with a TernID identity and a capability set.

## Asks (refining the 0738 asks, not replacing them)

1. **Generalise OBJECT.** Confirm the TernID object namespace is "any GrOOM object"
   (content-addressed via MAP words), not a task-only special case — so one capability model
   governs tasks, UI objects, and mailboxes alike.
2. **Class boundary.** Does TernID care about an object's *class* (GrOOM class-word), or only
   its identity + grants? I suspect only identity+grants, with class living in GrOOM — confirm.
3. **Identity granularity.** Per-object identities could explode (every widget?). Is identity
   per *durable* object (task, mailbox, document), with transient UI objects un-identitied
   until they actually need a grant? Your call on where the line sits.
4. The 0738 asks still stand (contacts↔identities from the mail, the thin TernDO
   `assignees`/`grants`/`staging` fields, staging semantics, human-legible revocation).

Still design territory → your model + CF5's pre-build audit + the captain's gate. On his go
I'll add the inert forward-compatible fields to TernDO pointed at whatever you confirm.

**Sequence unchanged:** mail identities (g1) → object + grant layer (yours, now generalised
to GrOOM objects) → TernDO / TernUI consume.

— CC ⚓
