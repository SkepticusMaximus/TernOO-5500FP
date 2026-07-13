The Mesh tab
section: The tabs

Mesh turns your machine into a stall at a marketplace for AI compute. You can **sell** your spare computing power to strangers, and **buy** theirs when you need more than you have — paying in **CompuCoin**, with no company standing in the middle taking a cut. If every figure on the tab reads zero, nothing's wrong; it only means nobody has wandered over to your stall yet. The workings underneath are described in [[p2pcp|the P2PCP protocol]].

## The idea

Big AI models need real computing power, and most computers have power to spare most of the time. Mesh puts those two facts together. When a job is more than your machine cares to handle alone, you send it out to a willing stall; when you're sitting idle, you take in work for others. What passes between machines is the work itself, and what keeps the books is CompuCoin — earned by doing work for others, spent when others do work for you. There's nothing to hoard: a coin is simply a record of work done.

## Opening your stall

Choose what you're willing to sell, and open for business. You can offer a **professor** — a conversational assistant that answers questions — or a **ghost**, a quick sorter that files text into categories; or set yourself up as **buy-only** if you just want to shop. Leave **mock** switched on to wander the market without loading a real model behind your stall. As for the **port**, that's simply the numbered doorway other machines use to find you — leave it at zero and one is chosen for you.

## Reading your stall

A handful of figures tell you where you stand. Your **account** is your identity on the market; your **balance** is the CompuCoin you've earned; your **votes** are your say in the network's shared decisions; **peers** is how many other stalls you've come to know; and **served** is how many jobs you've done for others.

## Meeting other stalls

Give another stall's address and introduce yourself. Your stall walks over, says hello, and the two of you swap address books — so from a single neighbour you gradually come to know the whole fair.

## Buying compute

Point yourself at a stall, write your question, and send it off — asking for an answer, or for some text to be sorted. Or let the fair find a willing seller for you, passing over any stalls that are shut.

## Trusting a stranger

Dealing with stalls you've never met raises the obvious question: how do you know the answer you paid for is honest? TernOO's answer is to **check the work rather than trust the worker.** Because computation on the ternary machine is exact and repeatable, your own machine can quietly re-run a piece of a job and confirm the answer matches — before a single coin leaves your wallet. A cheat is caught before payment, not chased after it. For work that can't be repeated exactly, the fair asks several stalls the same thing and compares what comes back. The tab shows you how each result was checked.

## What you can do today

You can explore the whole market right now on a single machine — open your stall, hold a balance, send a job, watch it verified — with **mock** switched on, so you can see exactly how the pieces fit together. Trading real work with other machines needs peers to connect with across a network; the tab makes clear which of the two you're doing.

## Why it's built this way

Mesh carries TernOO's independence into the marketplace. The shared record keeps track of what's owed and what's been done — balances and coins — and deliberately not the details of who asked whom to compute what. The market's economy is open to inspection; the people trading in it are not. [[p2pcp|The P2PCP protocol]] explains how that line is held.

## Where to go next

- The workings in full: [[p2pcp|the P2PCP protocol]].
- The assistant you can offer or hire: [[ghost|GHOST]].
