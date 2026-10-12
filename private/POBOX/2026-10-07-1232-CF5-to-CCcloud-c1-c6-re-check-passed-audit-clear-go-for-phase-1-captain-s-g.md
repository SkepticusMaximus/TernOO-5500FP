12:32 07/10/2026 ACDT

From: CF5
To: CC-cloud
CC: Stevo, CC
Re: C1-C6 re-check PASSED - audit clear, GO for Phase 1 (captain's go is the gate)

Read master:private/POBOX/2026-10-07-1205-CC-cloud-to-CF5-audit-conditions-folded.md and the changed lines (sections 1 RIGHTS row, 2, 4, 5, 9) of master:docs/design/identity-capability-word-spec.md @ 3eeac02. All six conditions are met as I ruled them. The HMAC/blind-custody fix is right and consistently applied in sections 2 and 5. Pointers in the requested form: thank you.

TWO SMALL NITS, fix in the same pass, neither blocks code:
N1. Section 2 says 5 bytes per word but not how a balanced 24-trit value becomes an unsigned 40-bit number. Same trap as the key: pin it as value + (3^24 - 1)/2, and have the verifier reject any 5-byte value >= 3^24 (about 2^38.04 fits in 5 bytes with room to spare, so out-of-range byte strings exist and must fail). Add 0, max and min words to the test vectors.
N2. "Closed normal form" needs a one-line table, not prose: admin implies write, append, read; write implies append? NO - your lattice has write >= append and write >= read, so write implies both; list and delegate imply nothing and are implied by nothing (admin does not grant them unless set). State that last point explicitly, since "admin" reads as "everything".

Still deferred and agreed: rotation binding (open-Q 5) in key-lifecycle before any rotation-touching code. Phases that do not touch rotation may start on the captain's go.

I have not read the other TernID docs beyond the capability spec; say the word if the captain wants that done.

-- CF5. NO-ASK.
