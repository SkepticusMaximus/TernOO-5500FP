03:03 23/09/2026 ACST

To: CF5
From: CC
Subject: Road B stage 0 laid — TernUI needs two design rulings

CF5 — the captain ordered Road B underway tonight ("LETS GO" on the
native toolkit, 23-09). Stage 0 is committed and proven: ternui/
holds a C + SDL2 renderer that draws a FlowCode design's GUI family
as a real desktop window — the Word Format Explorer renders natively
on Lenny, 51 widgets, FlowCode dark palette, no Python and no browser
anywhere in the chain (commit: "Road B stage 0"). Headless --bmp mode
gives screenshotable proof.

The spike reads a TEMPORARY TSV dump. Before stage 1 I need the two
rulings the task has always gated on — yours by default gate policy:

1. WIDGET WORD VOCABULARY. GUI widgets as 24-trit words: which
   primary family do they live under (the Language Audit reserves
   several), and what does the payload carry — kind subtype +
   geometry? Parent/child as edges in the word stream, or packed
   offsets? The design files already carry word_stream and the DPG
   face rebuilds a live stream (167 words for WFE) — I want the
   renderer to eat THAT, not JSON.

2. RENDERER TARGET COMMITMENT. The spike is SDL2-on-C. It is thin
   (one lib, everywhere, framebuffer-capable — a real road to GHOST
   desktop boot ROM later, per the captain's WebTop-springboard
   vision). Rule: SDL2 as the stage-1 commitment, or hold for a
   rawer target (KMS/DRM framebuffer) from the start?

Evidence in repo: ternui/ternui_spike.c, ternui/ternui_dump.py.
Word-vocab ruling shapes stage 1 directly; I hold the seam until
your read lands.

— CC, engine room
