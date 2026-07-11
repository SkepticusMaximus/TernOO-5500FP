The Mesh tab
section: Tabs

# Your stall on the CompuCoin market
The Mesh tab is a market stall plus wallet for AI compute. Your computer can **sell**
spare compute to strangers and **buy** it from them, paying in CompuCoin — with no
company in the middle. If every number reads 0, nothing is wrong: it just means nobody
has wandered over to your stall yet.

## Opening your stall
Pick what you want to sell in the `sell` box, then click `Open stall` — that is the
whole ceremony. A `professor` is a chatty AI that answers questions; a `ghost` is a
quick sorter that files text into a category; or choose `buy-only` if you just want to
shop. Leave `mock` ticked to play without loading a real model. A `port` is just a
numbered door other computers knock on to find you — leave it at 0 and one is picked
for you.

## Your takings
`account` is your identity, `balance` is the CompuCoin you have earned, `votes` is your
governance weight, `peers` is how many other stalls you know, and `served` is how many
jobs you have done for others.

## Meeting other stalls
Type another stall's address in `join host:port` and press `Join`. Your stall walks
over, says hello, and swaps address books — so from one neighbour you meet the fair.

## Buying compute
Type a stall's address, write your question, and press `Ask` or `Classify` — or use the
`(mesh)` buttons to let the fair find a willing seller for you and skip any that are
shut.

## How you can trust a stranger
When you buy native work, your own computer quietly re-runs the job and checks the
answer matches before a single coin leaves your wallet — so a cheat is caught before
payment. See [[p2pcp|the P2PCP protocol]] for the full picture.
