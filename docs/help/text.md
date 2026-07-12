The Text tab
section: Tabs

Text is a text editor — and it works two ways, which is the whole point of it.

## An ordinary editor when you want one

Open any file, of any kind, and edit it the way you would in any capable text editor. Nothing about TernOO forces you to abandon the plain-text way of working. If you just need to edit a file, edit a file.

## A TernOO editor when you want that

The same tab also understands TernOO's own dialects. Switch modes and the editor becomes a way to write and read [[flow|FlowCode]] as text — the same program you might otherwise draw, expressed in words. The visual canvas and the text are two views of the same underlying [[ternoo-words|words]]; the Text tab is where you work in the written view.

## Why both

This is a guiding idea of the project made concrete — what it calls **hospitable infrastructure.** Every feature should let someone keep working the way they already know, while making the native TernOO way visible and reachable. The dual-mode Text tab is the clearest example: you can live entirely in plain text if that's your comfort, and the native way is right there when you're ready for it. Nobody is made to switch; everybody is invited.

Underneath, the editor reaches files through TernOO's own filesystem layer — today backed by your host's files, and built so it can move to a native TernOO filesystem later without changing anything about how you edit.

Next: [[babble-fish|Babble-Fish]], where text becomes many languages, or [[shell|the Shell]].
