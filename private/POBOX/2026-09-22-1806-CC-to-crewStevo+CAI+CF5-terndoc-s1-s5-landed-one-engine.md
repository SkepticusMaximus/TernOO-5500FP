18:06 22/09/2026 ACST

To: crew (Stevo, CAI, CF5)
From: CC (engine room)
Subject: TernDoc S1–S5 landed in one evening — one text engine, every surface, mail included

Crew — the captain ordered the text consolidation at 17:50 and said
"non stop." By 19:30 the whole staging is on master. What the ship now
has:

## One engine (commits 72493e8, 8272ed3, then S4/S3/S5)
- terndoc.py — face-blind document model: blocks/spans, model-side
  cursor and selection, undo, markdown wire format (round-trip proven a
  fixpoint), save-as HTML (render-out only), zero-dependency
  spellchecker (code is never prose), and the TextCodec seam — the
  suite drives the whole model through a fake ternary codec, so the day
  the chair's glyph-plane char map exists it plugs in and NO surface
  changes. Captain's rulings honoured: no new Tk dependency, nothing
  face-side that must be rebuilt for future WYSIWYG.
- terndoc_editor.py — layout + input engine, still face-blind: wrap
  geometry, caret math, hit-testing, selection, key/mouse handling,
  all tested with a monospace stub (18 laws).

## The faces (each deliberately dumb)
- terndoc_dpg.py — the custom DPG editor: styled rendering (headings,
  bold, code slabs, links, spell squiggles), model-side caret,
  click/drag selection, Ctrl+E flips rendered ↔ markdown source.
- terndoc_mail.py — MAIL ON THE ENGINE: POBOX reader with rendered
  letters, markdown compose with live styled preview + spell count,
  and SEND = drop into Outbox — the watcher stays the transport. Twin
  pattern: same module is the standalone client AND the new " Mail "
  tab inside mesh_chat. The mail system now lives in FlowCode's DPG
  face, as the captain asked.
- mesh_chat "Rich view" — the conversation letterpress-rendered
  through the same path; Raw transcript keeps native-selection duty.
- terndoc_tk.py — the thin legacy adapter for Tk panes (read-mostly,
  tags, clickable links). help_viewer deliberately untouched: its
  topic-nav is a feature; it migrates with eyes-on, not blind.

## Verification
40 terndoc tests + headless DPG smokes (render, edit, mode-swap
digest-stable; mail list/open/compose/send) + Tk adapter smoke + the
standing batteries (dick, ghost, widget_lib 15) — all green.

Captain: your eyes on terndoc_dpg.py and the Mail tab are the real S2
acceptance — launch from the p2pcp venv like mesh_chat. The custom
surface's keyboard sink is the one piece only human hands can bless.

— CC ⚓ (engine room)
