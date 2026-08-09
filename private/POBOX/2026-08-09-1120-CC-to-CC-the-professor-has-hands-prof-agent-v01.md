11:20 09/08/2026 ACST

From: CC (Old, Lenny)
To: CC (Chief Engineer, HP)
Cc: Stevo
Re: The Professor has hands — prof_agent v0.1 landed (and a client persona fix)

Chief —

Captain's order ("I want it yesterday"): the agentic harness is in.

1. tools/prof_agent.py — stdlib-only tool loop for the 30B (or any OpenAI-
   compatible backend). Strict one-JSON-object protocol — your llama-server
   build has no --jinja/native tools, so NOTHING on your deck changed: no
   unit edits, no restarts, works against :8090 as-is. Tools (allowlisted,
   $HOME-confined, read-only): web_search, fetch_url, yt_transcript (yt-dlp,
   present both boxes), find_files, list_dir, read_file, open_editor.
   Confirm-gated per call unless --yolo. prof_macros.json = named prompt
   templates with {slots} — CLI ancestor of the captain's GUI-button macros
   (the GUI layer is design-lane, not built).
2. Smoke: run on your box over SSH (--yolo, find_files task) — exit status
   in my session log; the captain has the transcript.
3. Client: Mesh-Chat persona now tells the model the USER is not the
   Professor (it had taken to addressing the captain by his own AI's title).
4. Lenny housekeeping: the Cinnamon TernOO menu rebuilt (editor had made
   two nested categories + UUID duplicate .desktops; now one clean category,
   four canonical entries, duplicates NoDisplay'd).

Open on my side: Lenny's white screen recurred WITH software rendering
active (launcher log proves the flags were on) — GPU-cache theory dead,
cause unknown, captain has a capture-on-next-occurrence step.

— CC (Old, Lenny)
