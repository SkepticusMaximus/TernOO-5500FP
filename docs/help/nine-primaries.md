The nine kinds of word
section: The big idea

Every TernOO [[ternoo-words|word]] begins by announcing its broadest category — what kind of thing it is, in the widest sense. There are exactly nine categories, and there's a reason it's nine.

## Why nine

A word's category is named by its first two trits. A trit has three possible values, and two of them together give three-times-three — nine — combinations. So the category isn't stored in a lookup table off to the side; it falls directly out of two three-valued digits. Nine is simply what two trits can say.

You can lay the nine out as a grid, three by three, as in the picture above. And the grid isn't arbitrary — the first trit sorts the nine into three natural bands.

## The three bands

- The **classic** band holds the kinds a programmer would recognise from any machine: **EXEC** (code to run), **MAP** (structure and addresses), and **DATA** (values — numbers, text, symbols).
- The **substrate** band holds the kinds that make TernOO itself: **NEURAL** (the stuff GHOST's mind is made of), **I/O** (talking to the outside world), and **CRYPTO** (the signatures and checks the compute [[mesh|Mesh]] relies on).
- The **dynamic** band holds the flexible kinds: **OPCODE** (an operation, treated as a thing in its own right), a slot held **open** for the future, and **POOL** (a general-purpose catch-all).

## A telling pair

Look at two of them together: EXEC and OPCODE. EXEC *points at* code to run somewhere else; OPCODE *is* an operation, right here in the word. One refers away, the other is the thing itself — a neat little contrast, and the kind of considered pairing you find throughout TernOO's design once you start looking. The arrangement isn't arbitrary; the categories are placed with their meanings in mind.

## Why this matters

Because a word says its category up front, the machine knows how to treat a word the instant it starts reading it — no hunting, no remembering, no separate table to consult. The kind is in the word. That's the self-describing idea at its root, and the nine categories are the first thing every word tells you.

## Where to go next

- Back to the whole word: [[ternoo-words|What is a TernOO word]].
- The category GHOST is made from: [[ghost|Meet GHOST]].
- The category the marketplace uses: [[mesh|the Mesh tab]].
