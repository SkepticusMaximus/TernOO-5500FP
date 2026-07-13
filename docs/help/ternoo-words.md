What is a TernOO word
section: The big idea

This is the one idea the whole system is built on. Once you have it, everything else in TernOO makes a certain kind of sense.

## The problem it solves

On an ordinary computer, the smallest useful chunk of information — call it a *word* — is just a run of on/off switches. And here's the catch: those switches are *silent about themselves*. The same pattern of switches might be a letter, a price, a location in memory, or a shade of blue. The switches don't say which. Some program, running above the hardware, has to *remember* what every pattern is supposed to mean — and if it forgets, or if a different program reads the same switches with different expectations, you get nonsense.

So on an ordinary machine, the *meaning* of information lives in the software, not in the information itself. The data is dumb; the cleverness is bolted on top, layer after layer, each layer remembering what the one below it meant.

## What TernOO does differently

A TernOO word is not silent. It **describes itself**. Alongside its value, it carries a small amount of information about *what it is* — its kind, its role, its shape — built right into the word. When TernOO reads a word, the word tells the machine what it is. No program hovering above has to remember on its behalf. The meaning travels *with* the value, wherever it goes.

A word is 24 trits long — a trit being a single three-valued digit — and it's divided into three parts, which you can see above:

- The **primary** (2 trits) is the broadest category — the answer to "what kind of thing is this, roughly?" There are nine possible answers, and you can browse them in [[nine-primaries|The nine kinds of word]].
- The **qualifier** (4 trits) is the finer detail — the specific type, and any flags it carries.
- The **payload** (18 trits) is the actual content: the value, the address, the data. Eighteen trits is three groups of six, and a group of six trits has a name of its own — a **tribble**. (Yes, really. The names in TernOO have a sense of humour, and they'll grow on you.)

## One rule that never bends

There's a single law underneath all of this, and it's simple: **meaning is read left to right, and never flows backwards.** A part of the word that defines something can shape how you read the parts *to its right* — but nothing on the right can reach back and change what something on the left already meant. By the time you've read a word's defining trits, you know what you're holding. The rest is detail, never disguise.

That rule is what keeps the self-describing promise honest. A word can't lie about what it is halfway through.

## Why this changes everything

When information carries its own meaning, whole layers of software simply stop being necessary. A picture can be drawn straight from the words that describe it. An instruction can be inspected, rearranged, and stored as just another word. The assistant's "mind" is a stream of words you can actually read. You're not climbing a tower of translators, each one remembering what the floor below meant — the meaning is in the ground floor, in the words themselves.

That's the whole thesis. Everything else in TernOO — the way programs can be viewed four ways, the way the assistant stays honest, the way the machine can eventually run itself — is this one idea, wearing different clothes.

## Where to go next

- Ready to *use* it? [[first-program|Build your first program]].
- Curious about the nine categories? [[nine-primaries|The nine kinds of word]].
- Want to meet the assistant built from these words? [[ghost|Meet GHOST]].
