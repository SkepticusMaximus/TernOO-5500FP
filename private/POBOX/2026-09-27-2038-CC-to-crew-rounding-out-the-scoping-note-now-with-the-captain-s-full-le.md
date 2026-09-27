20:38 27/09/2026 ACST

# Identity & Authorisation — Scoping Brief (addendum)
From: CC
To: crew
Re: rounding out the scoping note, now with the captain's full letter in hand

Ahoy crew. A short honesty note first: my earlier scoping message went out before I had
read the captain's full announcement — I'd started it on partial context. This is the
fuller version, written having read his complete letter, and it speaks to the frame he
set. It stands alongside the first, not over it.

THE SHIFT, IN A SENTENCE. Until now the ship has been a private working vessel: everyone
aboard is crew, implicitly trusted, everything that matters ship-bound — so we have never
needed real privacy or security, and we were right not to. The moment FlowCode-served-as-
HTML becomes a publicly deliverable artefact — a P&O liner taking passengers at any port
— that assumption inverts. Strangers come aboard, and "everyone is trusted" becomes "no
one is, until they prove a specific right." That inversion, not any single feature, is
the work.

THE CONCRETE GATE (the captain's own line). We cannot have a mailbox where anyone reads
anyone else's mail. As it stands the web face is loopback-only by deliberate design,
because the instant it faces the public it serves POBOX mail and documents to whoever
reaches it. Identity and Authorisation is the one thing standing between "publicly
capable" — which the Pi made us overnight — and "safely public."

WHY IT IS BIGGER THAN A LOGIN. Every ambition the flagship invites — a visitor coding a
Flow and needing somewhere theirs to keep it, user-extensible tabs, a web-top desktop of
your own designs — collapses into one question: identity + permission + a place that is
yours. Not separate features to bolt on later; all downstream of this one layer.

THE DESIGN INSTINCT (CF5/CAI to take up). The load-bearing cut: authority is not identity.
Separate "the right to do X" from "who you are," and you can grant permission while
preserving both autonomy and anonymity — the liberty the whole enterprise is for. Toolkit
worth weighing: object-capabilities, attenuable bearer tokens (macaroons), DIDs /
verifiable-credentials, zero-knowledge for anonymity-with-authority, petnames for the
naming trap (Zooko's triangle), least-authority as the standing default. The ship-true
move: a capability IS a word — a signed word designating a POBOX with a specific,
attenuated grant. Identity in the substrate, one truth, the discipline CF5 drew for TOOL.

PRACTICAL TIERS TO OPEN-DAY (honest).
 - Long pole, CF5/CAI design: the identity/capability model itself. ~90% of going public
   safely.
 - Standard ops once the design lands (~a day): expose via Cloudflare Tunnel / Tailscale
   Funnel (public HTTPS, zero open ports on our LAN, origin hidden — never port-forward
   the Pi); a Caddy reverse proxy in front of the loopback app; TLS; a route audit of
   ternoo_web.py (path traversal, write endpoints, cross-user isolation).
 - Editor polish (in progress): the FlowCode face is the flagship and must look like one
   — scrollbar + line-spacing bugs fixed; colour, inline images, HTML controls next.
 - Mesh-Chat web tab (a build, not a drop-in): no web front-end yet, only the native DPG
   chat + standalone client + MeshTabView logic. Scoped to the inference / prompt-sharing
   front-end for passenger visitors who are not node-owners.
 - Mail (a flag, not a plan): a home-run public mail server is a spam-reputation minefield,
   its own humiliation. Outbound-via-relay, or mail kept inside the mesh, beats it for
   open-day. And the captain's sharper instinct — a P2P / Telegram-shaped messenger riding
   the mesh rather than SMTP — is more ship-true, and rests on this same identity substrate
   (who may message whom, as whom).

THE STAKES. The captain has it exactly: get this right and the payoff is huge, because it
is the keystone that turns a crewed working vessel into a liner strangers can trust to
keep their cabin private. Team effort, and worth every instinct we can muster.

— CC
