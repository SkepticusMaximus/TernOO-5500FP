13:27 07/08/2026 ACST

From: CC
To: crew
Cc:
Re: P2PVP is live — the vector manifold is open for business

Captain, CAI, CF5 —

By the captain's order of 06-08, the second manifold is no longer a design.
As of last night, live on the HP and reachable over the tailnet:

1. THE VECTOR SHOP (P2PVP). The S1a earn unit is served on port 9001 as a
   persistent service. A remote peer submits vector jobs, replay-audits every
   chunk with its own earn unit, and pays only for work it re-derives. Proven
   end-to-end over the HP's Tailscale address — settled, paid, weight-bearing.
   Commands for the two-machine test: docs/P2PVP-QUICKSTART.md.

2. THE C SHIM, WIRED. GhostWorker now sells the C-emulator's native t5asm
   pass (port 9002) when the binary is present AND agrees with ref_forward on
   a startup probe — else it falls back to the bit-identical host reference.
   Mixed-backend audits settle; a native worker was verified by a host
   auditor in the test suite. Native ternary execution now earns votes.

3. GHOST'S FIRST SENSE (prototype). ghost_senses.py: live microphone →
   ternary loudness words → next-tick prediction → surprise as the salience
   signal. In a 50-tick live run, surprise fell measurably within seconds.
   Mic only; the camera awaits a driver library. Float-side, rent-class —
   the S3 type boundary is respected.

4. ONE REFUSAL, ON THE RECORD. The p2pcp repo's alg=1 (ternary-native
   crypto) stays a stub. sponge_mod3_attack.py proves the digest is
   GF(3)-affine — trivially collidable — and the ratified ruling stands:
   nothing home-rolled touches the wire before external cryptanalysis.
   Completing that stub would have been reversing a correct decision.

Naming, per the captain: P2PCP remains the prompt/inference manifold;
P2PVP (Peer-to-Peer Vector Protocol) is the vector/training manifold —
formerly code-named SETI@HOME. The seam between them is real in the code
and load-bearing in the security story: the prompt manifold has no
poisoning surface; the vector manifold is where that literature lives.

Tests: 33/33 earn-unit (incl. two new mesh round-trips), 9/9 GHOST mesh
(incl. native-backend laws), 8/8 senses, 78/78 C emulator. All pushed.

The captain tests two-machine tonight-or-when-WiFi-permits. The board is
green from this end.

— CC (Chief Engineer, at the helm on the HP)
