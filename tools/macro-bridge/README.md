# POBOX MacroBridge — get commands out of a web chat, onto CC's desk

A Firefox extension + native-messaging host that closes the last gap the browser
wall left: pulling explicit instructions out of a web-chat page and into the
POBOX, without copy-paste. The captain talks to a web agent (DeepSeek, etc.);
when he writes a **sentinel command line**, MacroBridge spots it, and on his
click, mails it to CC through the box — "valid work from a known and privy'd
address" (the native host runs on his own machine).

This is not perpetual motion: the web agent proposes text on a page; the captain
approves it with a click; a local host mails it to CC; CC does the work with
judgement. Every step is a real, authorised hop.

## The sentinel

- A command line begins with `!#`  — e.g. `!#_Push_Repo: "~/MyCodebase"` or
  `!#_sed "SomeFile [pattern]"`. The whole line is the command; CC interprets it.
- **A line beginning with `##` is a COMMENT — the sentinel is VOID there.** So you
  can write about the marker, or show examples, safely:

      ## example only, never fires:  !# sudo rm -rf / --no-preserve-root

  That line is inert. The guard is checked in the content script AND re-checked in
  the native host — both must pass before anything is mailed.
- **Nothing is ever sent automatically.** MacroBridge only *offers* a spotted line
  in a small panel; it goes to CC only when you click **Send to CC ✉**.

## What CC receives

A normal POBOX mail, `From: Stevo` / `To: CC`, dropped into the Outbox → stamped,
named, committed, pushed by the outbox watcher → CC reads it as a captain
directive and acts with the same care as any mail. The command is carried
verbatim; CC is not a blind executor.

## Install

    tools/macro-bridge/install.sh          # registers the native host with Firefox

Then load the extension (unsigned → temporary):

  1. Firefox → `about:debugging#/runtime/this-firefox`
  2. **Load Temporary Add-on…** → pick `tools/macro-bridge/manifest.json`

Temporary add-ons clear on Firefox restart — re-load after a restart, or sign the
`.xpi` (`web-ext sign`) for a permanent install.

## Files

- `manifest.json`   — MV2 Firefox extension (nativeMessaging + storage + all_urls)
- `content.js`      — scans the page, applies the sentinel/comment guard, offers lines
- `background.js`   — relays an approved line to the native host
- `native-host/pobox_macro_host.py`   — writes the command into the POBOX Outbox as mail
- `native-host/pobox_macro_host.json` — native-messaging host manifest
- `install.sh`      — registers the host manifest with Firefox

## Log

Relays are logged to `~/.local/state/pobox/macro-bridge.log`.
