P2PCP — the trustless compute mesh
section: Concepts

# What it is
P2PCP is the protocol beneath the [[mesh|Mesh tab]]: strangers trade compute for
CompuCoin with no coordinator and no company in the middle. It is also a standalone
package that runs three ways — a native node, a headless cloud node, and an in-browser
buyer.

# Replay, not reputation
For deterministic (native) work the buyer re-runs the job itself and pays only if the
bits match, so a forger is caught before a coin moves. That same verifiable work is
what earns a **governance vote**; float work (like an LLM answer, which can't be re-run
bit-for-bit) earns money but never a vote, and is checked by redundancy instead.

# To be written
The three verification classes, the block-lattice ledger, burn-weighted consensus and
slashing, and the earn -> burn -> vote governance loop. (Content author: CAI.)
