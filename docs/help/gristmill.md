GristMill
section: Concepts

# GristMill
How the fully native TernOO machine stores and reaches code. The working parts of the
operating system are GristMill libraries — content-addressed and located not by a fixed
hardware address but by being *calculated*: reached through a TTree traversal to OTree
objects, via the machine's address-to-content mechanism (MMID → MMOE). [[ghost|GHOST]]
selects and orchestrates them on demand.

# To be written
Content addressing, the TMesh / TTree traversal, MMID → MMOE reconstruction, and how the
content-addressed store can itself be the native filesystem, with paths as projections.
See [[ternoo-words|the word model]] for the substrate beneath it.
