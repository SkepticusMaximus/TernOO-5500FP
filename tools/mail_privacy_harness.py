#!/usr/bin/env python3
"""B/g56 regression harness — prove per-seat socket auth (SO_PEERCRED).

RUN WITH SUDO:  sudo python3 tools/mail_privacy_harness.py

Runs the SAME inbox probe under different OS users and checks the agent's verdict:
  admin (stevo/root) -> any box      ALLOW
  seat -> its OWN box                ALLOW
  seat -> ANOTHER seat's box         DENY   <- the thing that was the audit's FAIL
Self-contained: the per-seat probe is stdlib-only (system python3), so a seat needs
nothing but group-ternid access to the socket — no venv, no repo access.
"""
import json
import os
import socket
import subprocess

SOCK = os.environ.get("TERNID_AGENT_SOCK", "/run/ternid/agent.sock")

# stdlib-only probe, run as each OS user via `sudo -u`. Reads SOCK + ACCT from env.
PROBE = r'''
import socket, json, os
def call(m, **p):
    s = socket.socket(socket.AF_UNIX); s.settimeout(5); s.connect(os.environ["SOCK"])
    s.sendall((json.dumps({"id": 1, "method": m, "params": p}) + "\n").encode())
    b = b""
    while b"\n" not in b:
        d = s.recv(65536)
        if not d:
            break
        b += d
    s.close()
    return json.loads(b.split(b"\n")[0])
try:
    r = call("inbox", account=os.environ["ACCT"])
except Exception as e:
    print("ERR", str(e)[:50]); raise SystemExit
print("ALLOW", len(r.get("result", []))) if r.get("ok") else print("DENY", str(r.get("error"))[:50])
'''


def admin_call(method, **params):
    """This script runs as root (sudo) => admin on the agent."""
    s = socket.socket(socket.AF_UNIX); s.settimeout(5); s.connect(SOCK)
    s.sendall((json.dumps({"id": 1, "method": method, "params": params}) + "\n").encode())
    b = b""
    while b"\n" not in b:
        d = s.recv(65536)
        if not d:
            break
        b += d
    s.close()
    return json.loads(b.split(b"\n")[0])


def probe_as(user, acct):
    out = subprocess.run(["sudo", "-u", user, "env", "SOCK=" + SOCK, "ACCT=" + acct,
                          "python3", "-c", PROBE], capture_output=True, text=True)
    txt = (out.stdout or out.stderr).strip()
    return txt.splitlines()[0] if txt else "NO-OUTPUT"


def main():
    acc = admin_call("list_accounts")
    if not acc.get("ok"):
        print("admin list_accounts failed — is the agent up on", SOCK, "?", acc)
        return
    by = {admin_call("account_display", account_handle=a)["result"]: a for a in acc["result"]}
    ccc = by.get("CCC")
    rows = [
        ("admin  stevo      -> CCC box", "stevo",      ccc, "ALLOW"),
        ("owner  ternid-ccc -> CCC box", "ternid-ccc", ccc, "ALLOW"),
        ("OTHER  ternid-cf5 -> CCC box", "ternid-cf5", ccc, "DENY"),
        ("OTHER  ternid-cai -> CCC box", "ternid-cai", ccc, "DENY"),
    ]
    print("=== B/g56 per-seat socket-auth regression (target: CCC's box) ===")
    allok = True
    for label, user, acct, want in rows:
        got = probe_as(user, acct)
        ok = got.split()[0] == want if got else False
        allok = allok and ok
        print(f"  {'PASS' if ok else 'FAIL'}  {label:30} -> {got}")
    print("\nOVERALL:", "PASS — per-seat privacy ENFORCED at the socket ✅"
          if allok else "FAIL — see rows above (ferry to CCC)")


if __name__ == "__main__":
    main()
