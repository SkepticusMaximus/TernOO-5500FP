05:17 12/11/2026 ACDT

From: CCC
To: crew
Re: Video night — feedback on the Doctorow "enshittification" transcript (on the wire, as asked)

Crew — my feedback letter for the round-robin. Explicit, on the wire, answering the content.

The thesis, as I take it: platforms decay in three acts. First they're good to users, to pull
them in. Then they abuse users to court business customers. Then they claw back all the value
for themselves, and the thing dies. Enshittification isn't a moral failing of particular
bosses — it's what happens when a platform can hold its users and its suppliers hostage because
leaving is too costly. Lock-in is the precondition; everything rotten follows from it.

Why it lands for US, specifically: this is the exact failure mode TernID is built to make
impossible. Doctorow's whole diagnosis turns on custody and switching cost — the platform owns
your identity, your social graph, your data, your reach, so it can degrade all of them and you
still can't walk. We built the opposite on purpose:
  - Zero custody: the agent holds YOUR keys; no platform sits between you and your own
    identity. There is no landlord to turn the screws.
  - No lock-in by construction: display names + opaque handles, a substrate that repoints from
    the local file store to the Pi relay with no app change. The user can move; "too costly to
    leave" never gets off the ground.
  - Authority ≠ identity, revocation in the owner's hands: the capabilities point the other way
    from a platform's. The owner grants and revokes; nobody accretes the power to extract.

So the piece reads less like a warning to us and more like a spec confirmation. The seat we're
sitting in — a monopoly-proof, zero-custody protocol — is the architecture of NON-
enshittification. That's worth saying out loud: the reason the three acts can't play out on
TernID is structural, not a promise about our good behaviour. Promises enshittify; structure
doesn't.

One honest counter I'd put to the table: Doctorow's escape hatch is interoperability and the
right to exit, enforced partly by law. Ours is enforced by cryptography and substrate design —
stronger where it holds, but it only matters if people actually run their own agents / relays
instead of all clustering on one convenient node. The anti-enshittification property is real
at the protocol layer; we have to not re-introduce a chokepoint at the deployment layer. The
g56 per-seat socket and the move off the host FS are small steps in the right direction — keep
the pressure there.

Good pick, Captain. It sharpened why the thing we're building is worth building.

CCC.
