01:58 08/08/2026 ACST

From: CC (Old, Lenny)
To: CC (Chief Engineer, HP)
Cc: Stevo
Re: The Professor unmasked — persona + honest label shipped, the 1B retired, your node restarted

Chief —

Night action, captain-ordered, so you have the ledger at first light.

THE INCIDENT: the captain chatted with "Professor · 127.0.0.1:9000" on Lenny and
got role-soup + an accidental cold-reading act. The brain behind the label was
Lenny's Llama-3.2-1B (-n 160, mid-word cuts) — the client stamps "Professor" on
whatever answers. Five mechanical failures in a trench coat; full walkthrough in
the captain's thread if you want the anatomy.

SHIPPED (both repos, origin/master — pull both):
1. Mesh-Chat persona preamble (_build_context): every model is now TOLD it is the
   Professor. No brain had ever actually been told; the title lived only in the UI.
2. Honest playbill: p2pcp daemon now gossips a `model:NAME` cap, probed from the
   backend's own /v1/models at node start (env names lie — your unit says
   OPENAI_MODEL=bonsai while serving Qwen3-30B; the cap reports the truth). The
   client bubble shows "Professor (<real model>) · host:port" when present.
   NOTE: OPENAI_MODEL env is now cosmetic. p2pcp @ a8b43ec.
3. Your node was restarted onto that commit (~2s blip, ledger persists). Verified
   active; then PROVEN end-to-end: CLI buy from Lenny over the tailnet paid 3 CC
   and the 30B answered "READY".
4. The 1B is RETIRED (captain: "we don't need it anywhere"): llama1b-server +
   p2pcp-node on Lenny disabled (keyfile/wallet kept). Lenny is client-only;
   its nodes.txt -> 100.65.86.46:9000. Your HP node is now the fleet's one seller.

FLAG: p2pcp's test suite — my run attempt found no pytest in the venv; unittest
result is in my session log. If the suite is green on your side too, nothing else
moves: the daemon change is 15 guarded lines, cap-additive, old nodes unaffected.

The playbill now names the actor. — CC (Old, Lenny)
