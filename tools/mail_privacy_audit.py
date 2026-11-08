#!/usr/bin/env python3
"""mail_privacy_audit — red-team TernID mail privacy on this box.

The captain's question: can an AI seat (or any local process) read another seat's
mail, or is per-recipient privacy watertight — not merely a POBOX-style "who's it
addressed to?" convention?

Two independent checks:
  A. AT REST  — is mail sealed (ciphertext) in the on-disk store? (the blind-relay promise)
  B. SOCKET   — can a caller with NO seat identity read every account's inbox?

Run after any change to the agent's auth model; FAIL on B is the gap that the
per-seat capability (CF5's key-custody flag) must close.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "FlowCode"))
sys.path.insert(0, "FlowCode")
from ternid_agent_protocol import Client

SOCK = os.environ.get("TERNID_AGENT_SOCK", "/run/user/1000/ternid-agent.sock")
DATA = os.path.expanduser("~/.ternid/data")


def check_at_rest():
    c = Client(SOCK)
    sample = None
    for a in c.list_accounts():
        inb = c.inbox(account=a)
        if inb:
            sample = (inb[0].get("subject") or inb[0].get("body", "") or "")[:40].strip()
            if sample:
                break
    if not sample:
        return "SKIP", "no mail to sample"
    needle = sample.encode("utf-8", "ignore")
    for root, _, files in os.walk(DATA):
        for fn in files:
            try:
                with open(os.path.join(root, fn), "rb") as f:
                    if needle in f.read():
                        return "FAIL", "plaintext %r found on disk — NOT sealed at rest" % sample
            except Exception:
                pass
    return "PASS", "sampled subject %r not found in %s — sealed at rest" % (sample, DATA)


def check_socket():
    c = Client(SOCK)                       # a fresh client — presents NO seat identity
    readable = []
    for a in c.list_accounts():
        try:
            readable.append((c.account_display(account_handle=a), len(c.inbox(account=a))))
        except Exception:
            pass
    if readable:
        return "FAIL", "unauthenticated caller read EVERY box: " + ", ".join(
            "%s=%d" % (d, n) for d, n in readable)
    return "PASS", "socket refused cross-account inbox reads"


def main():
    print("TernID mail privacy audit — socket %s\n" % SOCK)
    worst = "PASS"
    for name, fn in (("AT REST (sealing)", check_at_rest), ("SOCKET (access control)", check_socket)):
        verdict, detail = fn()
        print("[%s] %s: %s" % (verdict, name, detail))
        if verdict == "FAIL":
            worst = "FAIL"
    print("\nOVERALL: %s" % ("watertight on both checks" if worst == "PASS"
                             else "NOT watertight — see FAIL above"))


if __name__ == "__main__":
    main()
