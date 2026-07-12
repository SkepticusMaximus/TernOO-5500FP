What is a TernOO word
section: Concepts

This is the idea the whole system is built on, so it's worth five minutes.

## The problem with ordinary words

On a normal computer, a "word" is a fixed run of bits — say 32 or 64 of them — and it is *silent about itself*. The number `1000100101...` might be a letter, a price, a memory address, or part of a picture. The bits don't say. Some program hovering above the hardware has to *remember* what every number means, and if it forgets, or if a different program reads the same bits, you get garbage. The meaning lives in the software, not in the word. The word is dumb ink.

## The TernOO word is self-describing

A TernOO word is **24 trits** long and it is *not* silent. It carries its own type, its own role, and its own structure, right there in the word. When the processor reads it, the word says what it is. No hovering program has to remember — the meaning travels *with* the value.

A word is divided into three parts — the **2 + 4 + 18** format:

- **Primary (2 trits)** — the broadest category. There are nine possible primaries, because two balanced-ternary trits give nine combinations.
- **Qualifier (4 trits)** — the finer type: the sub-kind and its flags.
- **Payload (18 trits)** — the value, address, or data. Eighteen trits is three **tribbles** (a tribble is 6 trits — the ternary cousin of a nibble).

## The nine primaries

The two primary trits (call them T23 and T22) name the word's broadest kind:

```
EXEC   (−,−)     MAP    (−,0)     DATA   (−,+)
NEURAL (0,−)     I/O    (0,0)     CRYPTO (0,+)
OPCODE (+,−)     OPEN_B (+,0)     POOL   (+,+)
```

- **EXEC** — points at code to run
- **MAP** — spatial/address structure
- **DATA** — values: numbers, text, symbols
- **NEURAL** — the substrate GHOST is made of (weights, connections)
- **I/O** — talking to the outside world
- **CRYPTO** — signatures, digests, the pieces the compute mesh needs
- **OPCODE** — an operation, represented as a first-class word
- **OPEN_B** — reserved for the future
- **POOL** — the dynamic escape hatch

Notice a small elegance: **OPCODE (+,−) is the exact trit-negation of EXEC (−,−)**. EXEC *points at* code somewhere else; OPCODE *is* the operation, right here. In balanced ternary, opposite meanings expressed as a flipped trit is the natural idiom — and you'll see it throughout.

## The one law that never bends

There is a single foundational rule: **meaning flows left to right, and never back.** A trit that defines something may shape how the trits *to its right* are read — but a trit can never reach back and change the meaning of something to its left. And no value buried in the payload is ever allowed to secretly change the word's type. What a word *is* is settled by the time you've read its defining trits; the rest is detail, not disguise.

This is what keeps the self-describing promise honest. Read a word left to right and you always know what you're holding.

## Why bother?

Because when the word carries its own meaning, whole layers of software stop being necessary. The picture can be drawn straight from the words. An operation can be composed, inspected, and stored as just another word. The AI's "brain" is a stream of words you can read. You're not fighting a tower of interpreters that each remember what the layer below meant — the meaning is in the substrate, all the way down.

That's TernOO. Everything else is this idea, wearing different clothes.

Next: [[ghost|meet GHOST]], or see how a program is drawn in [[flow|the Flow tab]].
