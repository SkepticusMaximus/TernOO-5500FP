The Shell tab
section: The tabs

Shell is a command line — type a command, get a result. If you've used a terminal before, your habits carry straight over.

## Familiar from the first line

The Shell speaks the shortcuts you already know. Pipe one command's output into the next with `|`, chain commands with `&&`, recall earlier commands from history, and use the everyday file commands — `ls`, `cat`, `cd`, `cp`, `mv`, and the rest. Type `help` to see what's available, grouped by family: text operations, maths, list operations, and more.

If you live in a terminal, this will feel like home. That's the intent — you shouldn't have to abandon a way of working you're already fluent in.

## Quietly sturdier than it looks

The pipes here carry *typed* values — each command knows what kind of thing it's receiving and passing on, so a pipeline is checked as it's built rather than just streamed as raw text. And the file commands run through TernOO's own file layer, so what you do at the prompt sits on the same foundation as everything else you build.

A couple of commands open doors to the rest of FlowCode. `run` executes a program file. `ghost` hands your request to [[ghost|GHOST]], the built-in assistant, which will point you toward the right tool for what you're describing. (There is also `ni`. It will demand a shrubbery. This is correct.)

## Where to go next

- Meet the assistant behind `ghost`: [[ghost|GHOST]].
- Prefer editing files to typing commands? [[text|the Text tab]].
- Build visually instead: [[flow|Flow]].
