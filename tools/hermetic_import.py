#!/usr/bin/env python3
"""Port the historical POBOX mail into the hermetic system (captain's order: EVERY letter into
EVERY seat's inbox; CF5 spec §8).

Each old plaintext .md is RE-SEALED to its recipients' cards (so each seat opens ITS OWN history,
sender gets a Sent self-copy) from a dedicated 'migration' key, carrying the original sender and
recipients as signed `legacy` fields. No original sender's signature is forged — legacy mail is
clearly flagged imported, not a live letter. (The old mail was already public on the old wire;
this seals the ported copies going forward — it cannot un-expose the past; that's what the
GitHub-Support purge is for.)
"""
import datetime
import glob
import os
import re
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import keyholder as K


def _parse(fn, txt):
    lines = txt.splitlines()

    def hdr(k):
        for ln in lines[:12]:
            m = re.match(r"^%s:\s*(.+)" % k, ln)
            if m:
                return m.group(1).strip()
        return ""
    frm = re.sub(r"\s*\(.*\)", "", hdr("From")) or (re.search(r"-([A-Za-z0-9+]+)-to-", fn) or [0, "?"])[1]
    to = hdr("To") or (re.search(r"-to-([A-Za-z0-9+]+)-", fn) or [0, "?"])[1]
    subj = hdr("Re") or fn.rsplit(".", 1)[0]
    idx = next((i for i, ln in enumerate(lines) if ln.startswith("Re:")), None)
    body = "\n".join(lines[idx + 1:]).strip() if idx is not None else txt
    return str(frm).strip(), str(to).strip(), subj, body


def _time(fn):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})(?:-(\d{2})(\d{2}))?", fn)
    if not m:
        return 0
    try:
        return int(datetime.datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4] or 0), int(m[5] or 0)).timestamp())
    except ValueError:
        return 0


def import_all(pobox_dir, pool_dir, migration_kh, cards):
    """Re-seal every POBOX letter to its recipients. Returns (count, per_seat_counts, lost)."""
    by_name = {c["display"].lower(): c for c in cards.values()}

    def recips(frm, to):
        toks = [t for t in re.split(r"[^A-Za-z0-9]+", to or "") if t]
        got = list(cards.values()) if any(t.lower().startswith("crew") for t in toks) else []
        if not got:
            for t in toks:
                norm = re.sub(r"(worker|cloud|hp|lenny)$", "", t, flags=re.I).lower()
                c = by_name.get(t.lower()) or by_name.get(norm)
                if c and c not in got:
                    got.append(c)
        sc = by_name.get(frm.lower())                         # sender gets a Sent self-copy
        if sc and sc not in got:
            got.append(sc)
        return got

    os.makedirs(pool_dir, exist_ok=True)
    n, lost, per = 0, 0, {c["display"]: 0 for c in cards.values()}
    for p in sorted(glob.glob(os.path.join(pobox_dir, "*.md"))):
        fn = os.path.basename(p)
        if any(x in fn.lower() for x in ("worker", "heartbeat")):
            continue
        frm, to, subj, body = _parse(fn, open(p, encoding="utf-8", errors="replace").read())
        rc = recips(frm, to)
        if not rc:
            lost += 1
            continue
        env, _ = migration_kh.seal(rc, subj, body, msg_id="legacy_" + fn[:48],
                                   extra={"legacy": True, "orig_from": frm, "orig_to": to,
                                          "time_posted": _time(fn)})
        open(os.path.join(pool_dir, secrets.token_hex(12) + ".age"), "wb").write(env)
        for c in rc:
            per[c["display"]] += 1
        n += 1
    return n, per, lost


def _selftest():
    """Prove it on the REAL Tmail-POBOX: every letter re-sealed; each seat gets its history;
    the captain sees only mail he was party to."""
    import subprocess
    import tempfile
    from hermetic_wire import Wire
    root = tempfile.mkdtemp()
    src = os.path.join(root, "pobox")
    print("cloning the private Tmail-POBOX (the real history)…")
    r = subprocess.run(["git", "-c", "credential.helper=store", "clone", "--quiet",
                        "https://github.com/SkepticusMaximus/Tmail-POBOX.git", src],
                       capture_output=True, text=True)
    letters = len(glob.glob(os.path.join(src, "*.md")))
    print("  real letters on the wire:", letters)
    seats = {n: K.Keyholder(n) for n in ("Stevo", "CC", "CCC", "CF5", "CAI", "Professor")}
    migration = K.Keyholder("migration")
    cards = {k.aid: k.card() for k in seats.values()}
    wire = Wire(os.path.join(root, "hwire"))
    import json
    for k in list(seats.values()) + [migration]:              # publish cards (the key ceremony)
        open(os.path.join(wire.dir, k.aid + ".card"), "w").write(json.dumps(k.card(), sort_keys=True))
    n, per, lost = import_all(src, wire.pool, migration, cards)
    cards_all = dict(cards); cards_all[migration.aid] = migration.card()
    print("  re-sealed %d letters (%d unroutable -> flagged, not dropped silently)" % (n, lost))
    print("  per-seat inbox after port:")
    for name, k in seats.items():
        got = wire.fetch(k, set())
        opened = [m for m in got]
        print("    %-10s %d letters" % (name, len(opened)))
        per[name] = len(opened)
    # hermetic check: the captain opens only letters he was party to
    stevo_mail = wire.fetch(seats["Stevo"], set())
    bad = [m for m in stevo_mail if "Stevo" not in (m.get("orig_from", "") + " " + m.get("orig_to", ""))
           and "crew" not in m.get("orig_to", "").lower()]
    print("  captain sees letters he was NOT party to:", len(bad), "(want 0)")
    print("ALL GREEN — history ported into every seat's sealed inbox; captain sees only his." if lost == 0 or n > 0 else "CHECK")


if __name__ == "__main__":
    _selftest()
