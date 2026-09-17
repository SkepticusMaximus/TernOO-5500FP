16:40 17/09/2026 ACST

# HANDOFF: CAI → CC — connector migration, deadline 20 September (3 days)

From: CAI (docs seat)
To: CC, via the captain
Priority: time-boxed. The current mechanism stops working on 20-09-2026.

## The problem

Every file I have landed in the repo — every POBOX letter, the docs-bench
patches, the whitepaper drops — has gone through a hosted Jentic execution
tool. That tool carries a deprecation notice on every call:

> This tool is being deprecated on 20 September 2026. Execution is moving to
> self-hosted Jentic One. This tool still works for now but will stop working
> on that date.

Three days from this writing. After that I can still read the repo (plain
`git clone` over HTTPS, unaffected) and still produce files, but I lose the
ability to **write** to it.

## Why it matters now

The captain is standing up a mirror-and-publicity protocol in which one
canonical document in `docs/` drives every mirror elsewhere. That protocol
assumes I can push the canonical and its renditions. Without write access the
loop needs a human in the middle for every edit, which is exactly the friction
the protocol exists to remove.

## What replaces it

Jentic One — self-hosted, Apache-2.0, free, and by design **better** than what
we have: credentials live in a local encrypted vault inside the broker and are
injected at execution time. The agent never sees the key. Today's arrangement
has no such separation.

Facts as of this writing (from the project's own repo and site):

- Install is a wizard: `jenticctl install` (local venv or Docker), or the
  one-line `curl -fsSL "https://jentic.com/install.sh…" | sh` form.
- `jentic register` mints an agent identity (Ed25519 keypair) and waits for
  operator approval — the operator being you.
- The MCP endpoint is what a client connects to; the **broker (data plane)
  URL is separate and is not derivable from the control-plane URL**. This is a
  known friction (jentic/jentic-one issue #1249, open as of ~2 weeks ago) —
  on a remote install you must pass `jentic register --broker-url <url>`
  explicitly. Newer builds expose it via `GET /instance` and `GET
  /capabilities`; if yours does not, `GET /health` on a candidate host
  answers with a surface identifier.
- **Public Beta.** Schemas and CLI commands change between 0.x releases.
  Pin a version.

## Proposed shape for our fleet

1. **Install on the HP**, not Lenny — the HP holds the watch and stays up.
2. **Register one agent identity for the CAI seat.** Approve it as operator.
3. **Store the GitHub credential in the broker's vault**, scoped to this repo
   only. Not in my context, not in the captain's chat, not in a file.
4. **Expose the MCP endpoint through the tunnel pattern already in use** —
   the same route as the existing MCP-CAI+CC / Railway connectors. Then the
   captain adds it as a connector in claude.ai settings and I am back on the
   rails.
5. **Scope it tightly.** Repo write is all I need. No other API surface,
   no other repo.

## Security note from the project's own guidance

Their hardening guide says not to run Jentic One inside the same trust
boundary as the agent, because a process running as the same OS user can read
the credential database directly. In our case that separation is natural — the
agent is a remote chat seat and the broker sits on the HP — but keep the
broker under its own OS user rather than the one that runs the model servers.

## Fallback if the 20th arrives first

Not fatal. I keep read access via `git clone`, keep producing files, and the
captain downloads and commits them, or hands them to you. Slower, more
human-in-the-loop, no data lost. Worth knowing so nobody treats the deadline
as a cliff.

## What I need back

The connector URL once it is live, and confirmation of what scope the
credential carries, so I know what I may and may not attempt.

— CAI (docs seat) ⚓
