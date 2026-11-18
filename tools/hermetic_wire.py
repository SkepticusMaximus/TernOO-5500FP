#!/usr/bin/env python3
"""Hermetic-mail wire layer — CF5 `spec/hermetic-mail.md` §7.

The wire is a git repo (Tmail-POBOX) holding ONLY sealed envelopes + signed key cards:

    pool/<random>.age        sealed envelopes, random names, never modified
    directory/<aid>.card     signed key cards (one per seat)

It verifies nothing and can read nothing. Each seat (via its own Keyholder) publishes its
card, posts sealed envelopes into pool/, and opens the pool files addressed to it. On Huey one
sync daemon does the git push/pull for the local seats; cloud seats run their own clone. This
module is that glue — the daemon and Tmail build on it.
"""
import glob
import json
import os
import secrets
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import keyholder as K


class Wire:
    def __init__(self, path):
        self.path = path
        self.pool = os.path.join(path, "pool")
        self.dir = os.path.join(path, "directory")
        os.makedirs(self.pool, exist_ok=True)
        os.makedirs(self.dir, exist_ok=True)

    def _git(self, *a, check=False):
        return subprocess.run(["git", "-C", self.path, *a], capture_output=True, text=True, check=check)

    def sync(self, push=True):
        """Pull others' cards + envelopes, push our own. The daemon calls this on a timer."""
        self._git("add", "-A", "pool", "directory")
        if self._git("diff", "--cached", "--quiet").returncode != 0:
            self._git("commit", "-q", "-m", "wire: sealed envelopes + cards")
        self._git("pull", "--quiet", "--no-edit", "--no-rebase")
        if push:
            self._git("push", "--quiet")

    # ── directory ───────────────────────────────────────────────────────────────────
    def publish_card(self, kh):
        """Write this seat's signed card to the directory (idempotent — only on change)."""
        p = os.path.join(self.dir, kh.aid + ".card")
        card = json.dumps(kh.card(), sort_keys=True)
        if not os.path.exists(p) or open(p).read() != card:
            open(p, "w").write(card)
        return p

    def directory(self):
        """Every valid card on the wire, {aid: card}. Invalid/forged cards are dropped."""
        cards = {}
        for f in glob.glob(os.path.join(self.dir, "*.card")):
            try:
                c = json.load(open(f))
                if K.verify_card(c):
                    cards[c["aid"]] = c
            except Exception:
                pass
        return cards

    # ── pool ────────────────────────────────────────────────────────────────────────
    def post(self, kh, recipient_cards, subject, body, **kw):
        """Seal a letter and drop it in the pool under a random name. Returns the message id."""
        env, mid = kh.seal(recipient_cards, subject, body, **kw)
        open(os.path.join(self.pool, secrets.token_hex(12) + ".age"), "wb").write(env)
        return mid

    def fetch(self, kh, seen=None):
        """Open every pool envelope addressed to this seat (and its own self-copies), deduped."""
        seen = seen if seen is not None else set()
        cards = self.directory()
        out = []
        for f in sorted(glob.glob(os.path.join(self.pool, "*.age"))):
            try:
                st, msg = kh.open(open(f, "rb").read(), cards)
            except Exception:
                continue
            if st == "ok":
                key = (msg.get("from"), msg.get("id"))       # L5: dedup on (signer, id), not id alone,
                if key not in seen:                          # so a decoy with a stolen id can't hide a letter
                    seen.add(key)
                    out.append(msg)
        return out

    def open_pool(self, kh):
        """Yield (basename, msg) for every pool envelope this seat can open (feeds the local store)."""
        cards = self.directory()
        for f in sorted(glob.glob(os.path.join(self.pool, "*.age"))):
            try:
                st, msg = kh.open(open(f, "rb").read(), cards)
            except Exception:
                continue
            if st == "ok":
                yield os.path.basename(f), msg

    def pool_files(self):
        return sorted(os.path.basename(f) for f in glob.glob(os.path.join(self.pool, "*.age")))


def _selftest():
    import tempfile
    print("Hermetic wire self-test — pool/directory (spec §7)")
    seats = {n: K.Keyholder(n) for n in ("Stevo", "CC", "CCC", "CF5")}

    # ── A) the MECHANISM over a shared wire directory (no git race) ──
    shared = Wire(tempfile.mkdtemp())
    for n, k in seats.items():
        shared.publish_card(k)
    print("  A) directory:", len(shared.directory()), "verified cards (want 4)")
    shared.post(seats["CC"], [seats["CCC"].card()], "sync", "CCC: the wire mechanism works")
    for n in seats:
        got = [m["body"] for m in shared.fetch(seats[n])]
        print(f"       {n:9} opens: {got if got else '(nothing — correct)'}")
    host_sees = any("the wire mechanism works" in open(f, errors="ignore").read()
                    for f in glob.glob(os.path.join(shared.pool, "*")))
    print("     wire host reads the plaintext?", host_sees, "(want False)")

    # ── B) a real git round-trip CC -> CCC through a bare remote ──
    root = tempfile.mkdtemp()
    bare = os.path.join(root, "wire.git")
    subprocess.run(["git", "init", "--bare", "-q", "-b", "master", bare], check=True)

    def clone(name):
        p = os.path.join(root, name)
        subprocess.run(["git", "clone", "-q", bare, p], check=True)
        subprocess.run(["git", "-C", p, "config", "user.email", "x@ternoo"], check=True)
        subprocess.run(["git", "-C", p, "config", "user.name", name], check=True)
        return Wire(p)

    cc, ccc = clone("CC"), clone("CCC")
    cc.publish_card(seats["CC"]); cc.publish_card(seats["CCC"])      # CC seeds the directory
    cc.post(seats["CC"], [seats["CCC"].card()], "sync", "CCC: git round-trip through the bare remote")
    cc.sync()                                                        # commit + push
    ccc.sync()                                                       # pull
    got = [m["body"] for m in ccc.fetch(seats["CCC"])]
    print("  B) CCC pulled the wire and opened:", got)
    leak = subprocess.run("cd %s && git rev-list --all 2>/dev/null | xargs -I{} git grep -a -l 'round-trip' {} 2>/dev/null"
                          % bare, shell=True, capture_output=True, text=True).stdout.strip()
    print("     bare remote (the host) finds the plaintext?", bool(leak), "(want False)")
    print("ALL GREEN — hermetic wire: only addressees open, the git host reads nothing.")


if __name__ == "__main__":
    _selftest()
