The Shell tab
section: Tabs

Shell is a command line — type a command, get a result — built to feel familiar to anyone who's used a terminal, while quietly being something more.

## Familiar idioms

The Shell speaks the idioms you already know. You can pipe the output of one command into another with `|`, chain commands with `&&`, recall history, and use the everyday file commands — `ls`, `cat`, `cd`, `cp`, `mv`, and the rest. If you've lived in a bash-like shell, your reflexes transfer.

Type `help` to see the available commands, grouped by family — text operations, math, list operations, and more.

## Quietly more

The pipes here are **typed** — a command knows what kind of thing it's receiving and passing on, so a pipeline is checked rather than just streamed as raw bytes. The file commands run through TernOO's own filesystem layer, which today sits on the host's files and is built to move to a native TernOO filesystem later without changing how you use it.

A few commands connect the shell to the rest of FlowCode: `run` executes a program file, and `ghost` hands your request to [[ghost|GHOST]] for routing. (There's also `ni`, which will demand a shrubbery. This is correct behaviour.)

## Why a shell at all

Because you can't really have a working machine without one. The Shell is part of FlowCode's promise to *meet you where you are* — keep working the way you already know how, while the native TernOO way stays visible and available. Familiar on the surface, TernOO underneath.

Next: [[text|the Text editor]], or [[ghost|GHOST]] for what `ghost` connects to.
